# 概念合并扫描性能优化设计

## 概述

优化知识图谱概念去重扫描的性能，实现**快速扫描 + 进度反馈**，将几百个概念的扫描时间从数分钟降低到 10-20 秒。

## 问题分析

### 当前性能瓶颈

在 `backend/routes/concepts.py` 的 `run_dedup_scan_background` 函数（第 571-593 行）：

```python
# 当前实现：每个候选对单独调用 LLM
for i, candidate in enumerate(candidates):
    result = deduplicator.merge_analyzer.analyze([candidate])  # 传的是单元素列表！
```

**问题**：
- `MergeAnalyzer.analyze()` 已支持批量分析（接受 `List[ConceptPair]`）
- 但 caller 每次只传入一个候选对 `[candidate]`
- 50 个候选对 × 3 秒/LLM调用 = **2.5 分钟**

### 性能对比

| 场景 | 当前实现 | 优化后 |
|------|----------|--------|
| 100 个候选对 | ~5 分钟 | ~15 秒 |
| 50 个候选对 | ~2.5 分钟 | ~10 秒 |
| 20 个候选对 | ~1 分钟 | ~5 秒 |

## 优化方案：智能预筛选 + 批量分组

### 方案架构

```
候选对生成
    ↓
智能预筛选（本地算法，无 LLM）
    ↓
批量分组
    ↓
分组 LLM 分析
    ↓
合并建议聚合
    ↓
用户确认 → 批量执行合并
```

### 第一阶段：智能预筛选

在候选对生成阶段减少不必要的 LLM 调用。

#### 规则 1：已有父子关系跳过

如果两个概念已经是父子关系，不需要判断是否合并。

```python
def has_parent_child_relation(db, concept1_id, concept2_id) -> bool:
    """检查两个概念是否已是父子关系"""
    parents1 = set(p['id'] for p in db.get_concept_parents(concept1_id))
    parents2 = set(p['id'] for p in db.get_concept_parents(concept2_id))
    children1 = set(c['id'] for c in db.get_concept_children(concept1_id))
    children2 = set(c['id'] for c in db.get_concept_children(concept2_id))

    # 任一方是另一方的父或子
    return (concept2_id in parents1 or concept2_id in children1 or
            concept1_id in parents2 or concept1_id in children2)
```

#### 规则 2：共享论文检测

如果两个概念已被同一篇论文引用，说明它们在该论文中被区分，不太可能是同义词。

```python
def has_shared_papers(db, concept1_id, concept2_id) -> bool:
    """检查两个概念是否有共享的论文"""
    papers1 = set(p['doi'] for p in db.get_papers_by_concept(concept1_id))
    papers2 = set(p['doi'] for p in db.get_papers_by_concept(concept2_id))
    return bool(papers1 & papers2)
```

#### 规则 3：高相似度直接标记

相似度 > 0.9 的候选对直接标记为"高置信度合并"，不消耗 LLM。

```python
HIGH_SIMILARITY_THRESHOLD = 0.9

if similarity > HIGH_SIMILARITY_THRESHOLD:
    # 直接生成合并建议，跳过 LLM
    return MergeSuggestion(
        source_id=...,
        target_id=...,
        confidence=0.95,
        rationale="文本高度相似",
        merge_type="synonym"
    )
```

#### 规则 4：文本包含关系

如果一个文本完全包含另一个（如"深度学习"包含在"深度学习方法"中），直接标记为"吸收型合并"。

```python
def check_text_containment(text1: str, text2: str) -> Optional[str]:
    """检查文本包含关系，返回吸收型合并的目标文本"""
    t1, t2 = text1.lower().strip(), text2.lower().strip()

    # 完全包含
    if t1 in t2 and len(t1) < len(t2):
        return text1  # 保留更短的
    if t2 in t1 and len(t2) < len(t1):
        return text2  # 保留更短的

    # 常见后缀模式
    suffixes = ['方法', '方法 ', ' method', ' methods', '技术', '技术 ']
    for suffix in suffixes:
        if t1 + suffix == t2:
            return text1
        if t2 + suffix == t1:
            return text2

    return None
```

#### 预筛效果预估

| 规则 | 预估减少 | 适用场景 |
|------|----------|----------|
| 父子关系 | 5-10% | 已有层级结构 |
| 共享论文 | 10-20% | 多论文共同引用 |
| 高相似度 | 10-15% | 完全相同或缩写 |
| 文本包含 | 5-10% | 冗余后缀 |
| **总计** | **30-55%** | - |

### 第二阶段：批量分组 LLM 调用

将预筛后的候选对分组，每组一次性发给 LLM。

#### 分组策略

```python
# 批次大小考虑 token 限制
# 每个候选对约 200-300 tokens（含 parents/children 信息）
# 目标模型输入限制 ~100k tokens，实际安全值 50k
# 安全批次：50k / 300 ≈ 150，取 10 作为安全值
BATCH_SIZE = 10

def batch_analyze(candidates: List[ConceptPair], analyzer) -> List[MergeSuggestion]:
    """批量分析候选对"""
    suggestions = []

    for batch_start in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[batch_start:batch_start + BATCH_SIZE]

        try:
            # 直接使用现有的 analyze 方法（它已支持 List 输入）
            batch_suggestions = analyzer.analyze(batch)
            suggestions.extend(batch_suggestions)
        except Exception as e:
            # 批次失败时，尝试逐个分析
            for candidate in batch:
                try:
                    single_result = analyzer.analyze([candidate])
                    suggestions.extend(single_result)
                except Exception:
                    pass  # 记录日志，继续处理

        # 更新进度
        update_scan_progress(batch_start // BATCH_SIZE,
                            (len(candidates) + BATCH_SIZE - 1) // BATCH_SIZE)

    return suggestions
```

**关键变更点**：修改 `backend/routes/concepts.py` 中的 `run_dedup_scan_background` 函数，将逐个调用改为批量调用。

#### Prompt 说明

现有的 `MergeAnalyzer._build_prompt()` 已支持多候选对格式，无需修改。每个候选对包含：
- pair_id
- concept1/concept2（含 id, text, category, paper_count, parents, children）
- similarity

### 第三阶段：进度追踪

#### 进度阶段划分

扫描过程分为三个阶段，每个阶段都有进度反馈：

1. **预筛选阶段**（本地计算，约 1-2 秒）
   - 状态：`prefiltering`
   - 进度：显示"正在预筛选候选对..."

2. **LLM 分析阶段**（主要耗时）
   - 状态：`analyzing`
   - 进度：批次完成数 / 总批次数

3. **完成阶段**
   - 状态：`completed`
   - 返回所有合并建议

#### 数据库字段

使用项目现有的 `_ensure_columns` 模式添加新字段：

```python
# database.py 的 _ensure_columns 方法中添加
cursor.execute("""
    INSERT OR IGNORE INTO pragma_table_info('scan_jobs')
    SELECT 'batches_total', 'INTEGER', 0, 0, NULL
""")
cursor.execute("""
    INSERT OR IGNORE INTO pragma_table_info('scan_jobs')
    SELECT 'batches_completed', 'INTEGER', 0, 0, NULL
""")
cursor.execute("""
    INSERT OR IGNORE INTO pragma_table_info('scan_jobs')
    SELECT 'high_confidence_count', 'INTEGER', 0, 0, 0
""")
cursor.execute("""
    INSERT OR IGNORE INTO pragma_table_info('scan_jobs')
    SELECT 'filtered_count', 'INTEGER', 0, 0, 0
""")
```

#### API 响应增强

```json
{
  "scan_id": "scan-xxx",
  "status": "analyzing",
  "phase": "prefiltering | analyzing | completed",
  "progress": 60,
  "batches_total": 5,
  "batches_completed": 3,
  "concepts_scanned": 45,
  "total_concepts": 75,
  "filtered_by_rules": 20,
  "high_confidence_auto": 5,
  "estimated_time": 8,
  "suggestions_found": 12
}
```

### 第四阶段：合并执行

用户确认后执行合并。由于每个合并操作删除一个概念，如果用户选择了多个合并且其中某个概念同时作为 source 和 target，需要按顺序执行。

#### 依赖排序说明

```python
def sort_merges_by_dependency(merge_ids: List[str], scan_result: dict) -> List[str]:
    """按依赖关系排序合并操作

    场景：用户选择合并 A→B 和 B→C
    - 如果先执行 A→B，A 被删除
    - 然后执行 B→C 时，B 已不存在（如果 A 合并到 B 后 B 又被合并到 C）

    解决：拓扑排序，确保 source 概念不会被后续操作用作 target
    """
    suggestions = {s['id']: s for s in scan_result.get('merge_suggestions', [])}
    selected = [suggestions[mid] for mid in merge_ids if mid in suggestions]

    # 构建依赖图：如果 merge1 的 target 是 merge2 的 source，则 merge1 依赖 merge2
    # （merge2 必须先执行，这样 merge1 的 target 才存在）
    # 实际上，我们只需确保：先执行 target 不会变成 source 的合并

    # 简化处理：按 paper_count 降序执行（保留被更多论文引用的概念）
    selected.sort(key=lambda s: s['target']['paper_count'], reverse=True)

    return [s['id'] for s in selected]
```

## 文件变更

### 修改文件

| 文件 | 变更内容 |
|------|----------|
| `mkg/dedup/candidate.py` | 添加预筛选规则方法 |
| `backend/routes/concepts.py` | 改造 `run_dedup_scan_background`，将逐个调用改为批量调用 |
| `mkg/database.py` | 在 `_ensure_columns` 中添加 scan_jobs 新字段 |

### 新增方法

```python
# candidate.py
class CandidateGenerator:
    def generate_candidates_with_prefilter(self, folder_id: str) -> dict:
        """生成候选对并应用预筛选规则"""
        return {
            "candidates": [...],  # 需要 LLM 分析的
            "high_confidence": [...],  # 高置信度直接合并的
            "filtered": [...],  # 被规则过滤掉的
            "stats": {...}
        }

    def _apply_prefilter_rules(self, pair: ConceptPair) -> Optional[dict]:
        """应用预筛选规则，返回 None 表示需要 LLM 分析"""
        ...

# backend/routes/concepts.py
def run_dedup_scan_background(scan_id: str, folder_id: str):
    """后台扫描任务（改造后）"""
    # 1. 预筛选阶段
    prefiltered = deduplicator.candidate_generator.generate_candidates_with_prefilter(folder_id)
    db.update_scan_job(scan_id, status='analyzing',
                       filtered_count=len(prefiltered['filtered']),
                       high_confidence_count=len(prefiltered['high_confidence']))

    # 2. 批量分析阶段
    candidates = prefiltered['candidates']
    suggestions = prefiltered['high_confidence']  # 已包含高置信度建议

    for batch_start in range(0, len(candidates), BATCH_SIZE):
        batch = candidates[batch_start:batch_start + BATCH_SIZE]
        batch_suggestions = deduplicator.merge_analyzer.analyze(batch)  # 批量调用！
        # ... 处理结果并更新进度
```

## 性能目标

| 指标 | 当前 | 目标 |
|------|------|------|
| 100 个候选对扫描时间 | ~5 分钟 | < 20 秒 |
| 进度反馈更新频率 | 逐个 | 逐批次 |
| 预筛减少 LLM 调用 | 0% | 30-55% |
| 单次 LLM 调用处理量 | 1 个 | 10 个 |

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| 预筛选阶段异常 | 降级为原有流程，记录日志 |
| LLM 调用超时 | 重试当前批次，最多 2 次 |
| 批次解析失败 | 降级为逐个分析该批次的候选对 |
| 单个候选对解析失败 | 跳过，继续处理其他候选对 |

## 测试计划

1. **单元测试**：预筛选规则覆盖率
2. **集成测试**：批量分析流程
3. **性能测试**：100/200/500 概念扫描时间
4. **回归测试**：确保不漏掉有效合并
5. **边界测试**：批次失败降级逻辑

## 实现优先级

1. **P0**：批量分组 LLM 调用（最核心优化，修改 `run_dedup_scan_background`）
2. **P1**：预筛选规则（高相似度 + 文本包含）
3. **P2**：进度追踪增强（预筛选阶段反馈）
4. **P3**：其他预筛选规则（父子关系、共享论文）