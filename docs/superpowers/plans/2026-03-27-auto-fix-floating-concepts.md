# 自动修复漂浮概念实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 合并完成后自动检测并修复漂浮概念，无需用户干预。

**Architecture:** 新增 `floating_fixer.py` 模块，修改 `deduplicator.py` 在合并后调用修复函数，前端显示修复结果。

**Tech Stack:** Python, SQLite, React/TypeScript

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `mkg/dedup/floating_fixer.py` | 新增 | 漂浮概念检测与修复逻辑 |
| `mkg/dedup/deduplicator.py` | 修改 | 在 execute_merge 结尾调用修复函数 |
| `frontend/src/components/DedupPanel.tsx` | 修改 | 显示漂浮概念修复信息 |
| `fix_floating_concepts.py` | 删除 | 功能已集成到模块中 |

---

### Task 1: 创建 floating_fixer.py 模块

**Files:**
- Create: `mkg/dedup/floating_fixer.py`

- [ ] **Step 1: 创建模块文件，包含所有核心函数**

```python
"""
漂浮概念修复器 - 检测并修复丢失父节点的概念
"""

import json
import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger("mkg.dedup")


# 层级结构定义
CATEGORY_HIERARCHY = ['field', 'direction', 'subdirection', 'method', 'task', 'technique']


def find_floating_concepts(db) -> List[Dict]:
    """找出需要修复的漂浮概念（有子节点但无父节点，非顶层 field）

    Args:
        db: Database 实例

    Returns:
        [{'id', 'text', 'category', 'paper_count', 'children': [...]}]
    """
    import sqlite3

    conn = db.conn
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute('''
        SELECT c.id, c.text, c.category, c.paper_count,
               (SELECT COUNT(*) FROM concept_relations WHERE child_id = c.id) as parent_count,
               (SELECT COUNT(*) FROM concept_relations WHERE parent_id = c.id) as child_count
        FROM concepts c
        WHERE (SELECT COUNT(*) FROM concept_relations WHERE child_id = c.id) = 0
        AND c.category != 'field'
        ORDER BY child_count DESC, c.paper_count DESC
    ''')

    floating = []
    for row in cur.fetchall():
        if row['child_count'] > 0:  # 有子节点的才需要修复
            # 获取子节点
            cur.execute('''
                SELECT c.text, c.category
                FROM concepts c
                JOIN concept_relations r ON c.id = r.child_id
                WHERE r.parent_id = ?
            ''', (row['id'],))
            children = cur.fetchall()

            floating.append({
                'id': row['id'],
                'text': row['text'],
                'category': row['category'],
                'paper_count': row['paper_count'],
                'children': [{'text': c['text'], 'category': c['category']} for c in children]
            })

    logger.info(f"发现 {len(floating)} 个漂浮概念")
    return floating


def get_candidate_parents(db, category: str) -> List[Dict]:
    """获取可能作为父节点的候选列表

    Args:
        db: Database 实例
        category: 当前概念的 category

    Returns:
        [{'id', 'text', 'category'}]
    """
    import sqlite3

    conn = db.conn
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    current_idx = CATEGORY_HIERARCHY.index(category) if category in CATEGORY_HIERARCHY else 3
    candidate_categories = CATEGORY_HIERARCHY[:current_idx + 1]

    cur.execute(f'''
        SELECT c.id, c.text, c.category
        FROM concepts c
        WHERE c.category IN ({','.join(['?'] * len(candidate_categories))})
        ORDER BY c.paper_count DESC
        LIMIT 50
    ''', candidate_categories)

    return [{'id': r['id'], 'text': r['text'], 'category': r['category']} for r in cur.fetchall()]


def infer_parent_with_llm(llm_client, floating: Dict, candidates: List[Dict]) -> Optional[str]:
    """让 LLM 推断父节点

    Args:
        llm_client: LLM 客户端
        floating: 漂浮概念信息
        candidates: 候选父节点列表

    Returns:
        parent_id 或 None
    """
    candidates_json = json.dumps(
        [{'id': c['id'], 'text': c['text'], 'category': c['category']} for c in candidates[:50]],
        ensure_ascii=False,
        indent=2
    )

    children_names = [c['text'] for c in floating['children']]

    prompt = f"""为以下概念从候选列表中选择最合适的父节点。

## 待匹配概念
- 名称：{floating['text']}
- 层级：{floating['category']}
- 子节点：{json.dumps(children_names, ensure_ascii=False)}

## 候选父概念
{candidates_json}

## 选择规则
1. 父节点的 category 必须严格高于子节点（field > direction > subdirection > task > method > technique）
2. 优先选择语义距离最近的父节点（即最直接的上位概念，不要跳级）
3. 如果有多个候选都合理，选层级更低（更具体）的那个作为直接父节点
4. 如果没有合适的候选 → 输出 {{"parent_id": null}}

示例：
- "QMIX 算法"(method) 的候选有 "多智能体强化学习"(direction) 和 "值分解方法"(subdirection)
  → 选 "值分解方法" ✅（更直接的上位概念）
  → 不选 "多智能体强化学习" ❌（隔了一级，应该是祖父而非父亲）

只输出 JSON：{{"parent_id": "xxx"}} 或 {{"parent_id": null}}"""

    try:
        response = llm_client.extract_concepts(prompt)
        json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result.get('parent_id')
    except Exception as e:
        logger.error(f"LLM 推断父节点失败: {e}")

    return None


def fix_floating_concepts(db, llm_client) -> Dict:
    """修复所有漂浮概念

    Args:
        db: Database 实例
        llm_client: LLM 客户端（可为 None）

    Returns:
        {'fixed': int, 'details': [...]}
    """
    if not llm_client:
        logger.warning("LLM 客户端未配置，跳过漂浮概念修复")
        return {'fixed': 0, 'details': [], 'error': 'LLM not configured'}

    floating_concepts = find_floating_concepts(db)

    if not floating_concepts:
        return {'fixed': 0, 'details': []}

    fixes = []
    details = []

    for fc in floating_concepts:
        candidates = get_candidate_parents(db, fc['category'])

        if not candidates:
            details.append({
                'concept': fc['text'],
                'status': 'skipped',
                'reason': 'no candidates'
            })
            continue

        parent_id = infer_parent_with_llm(llm_client, fc, candidates)

        if parent_id:
            parent = db.get_concept(parent_id)
            if parent:
                # 执行修复
                cursor = db.conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO concept_relations (parent_id, child_id)
                    VALUES (?, ?)
                ''', (parent_id, fc['id']))
                db.conn.commit()

                fixes.append({
                    'concept': fc['text'],
                    'parent': parent['text']
                })
                details.append({
                    'concept': fc['text'],
                    'parent': parent['text'],
                    'status': 'fixed'
                })
                logger.info(f"修复漂浮概念: {fc['text']} -> {parent['text']}")
            else:
                details.append({
                    'concept': fc['text'],
                    'status': 'failed',
                    'reason': f'parent {parent_id} not found'
                })
        else:
            details.append({
                'concept': fc['text'],
                'status': 'failed',
                'reason': 'no parent inferred'
            })

    logger.info(f"漂浮概念修复完成: {len(fixes)}/{len(floating_concepts)}")
    return {'fixed': len(fixes), 'details': details}
```

- [ ] **Step 2: 提交**

```bash
git add mkg/dedup/floating_fixer.py
git commit -m "feat(dedup): add floating concept fixer module"
```

---

### Task 2: 修改 deduplicator.py 集成修复逻辑

**Files:**
- Modify: `mkg/dedup/deduplicator.py:103-136`

- [ ] **Step 1: 添加 import 和修改 execute_merge 方法**

在文件顶部添加 import：

```python
from .floating_fixer import fix_floating_concepts
```

修改 `execute_merge` 方法：

```python
def execute_merge(self, scan_id: str, merge_ids: List[str]) -> dict:
    """执行合并操作"""
    # Pass db to get_scan_result to check database
    scan_result = get_scan_result(scan_id, self.db)
    if not scan_result:
        return {"executed": 0, "error": "Scan result not found or expired"}

    suggestions_map = {s['id']: s for s in scan_result.get('merge_suggestions', [])}

    details = []
    executed = 0

    for merge_id in merge_ids:
        suggestion = suggestions_map.get(merge_id)
        if not suggestion:
            details.append({"merge_id": merge_id, "status": "failed", "message": "Merge suggestion not found"})
            continue

        result = self.merge_executor.execute(
            source_id=suggestion['source']['id'],
            target_id=suggestion['target']['id']
        )

        details.append({
            "source": suggestion['source']['id'],
            "target": suggestion['target']['id'],
            "status": result.status,
            "message": result.message
        })

        if result.status == 'success':
            executed += 1

    # 自动修复漂浮概念
    floating_result = {'fixed': 0, 'details': []}
    if executed > 0:
        floating_result = fix_floating_concepts(self.db, self.llm_client)

    return {
        "executed": executed,
        "details": details,
        "floating_fixed": floating_result['fixed'],
        "floating_details": floating_result.get('details', [])
    }
```

- [ ] **Step 2: 提交**

```bash
git add mkg/dedup/deduplicator.py
git commit -m "feat(dedup): auto-fix floating concepts after merge"
```

---

### Task 3: 更新前端显示修复结果

**Files:**
- Modify: `frontend/src/components/DedupPanel.tsx:374-416`

- [ ] **Step 1: 更新状态类型和显示逻辑**

在 Result State 部分（约第 374 行），修改显示逻辑：

找到 `{panelState === 'result' && (` 这一段，将其替换为：

```tsx
        {/* Result State */}
        {panelState === 'result' && (
          <div>
            <div className="mb-4">
              <p className="text-sm text-gray-500">
                已完成 <span className="font-semibold text-green-600">{executeDetails.filter(d => d.status === 'success').length}</span> 项合并
                {floatingFixed > 0 && (
                  <span className="ml-2">
                    ，修复 <span className="font-semibold text-blue-600">{floatingFixed}</span> 个漂浮概念
                  </span>
                )}
              </p>
            </div>

            <div className="space-y-2">
              {executeDetails.map((detail, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-lg ${
                    detail.status === 'success'
                      ? 'bg-green-50 border border-green-200'
                      : 'bg-red-50 border border-red-200'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    {detail.status === 'success' ? (
                      <Check className="w-4 h-4 text-green-500" />
                    ) : (
                      <AlertCircle className="w-4 h-4 text-red-500" />
                    )}
                    <span className="text-sm">
                      {detail.source} → {detail.target}
                    </span>
                  </div>
                  {detail.message && (
                    <p className="text-xs text-red-600 mt-1 ml-6">{detail.message}</p>
                  )}
                </div>
              ))}
            </div>

            {/* 漂浮概念修复详情 */}
            {floatingDetails && floatingDetails.length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <p className="text-xs font-semibold text-gray-500 mb-2">漂浮概念修复</p>
                <div className="space-y-1">
                  {floatingDetails.filter(d => d.status === 'fixed').map((detail, index) => (
                    <div key={index} className="text-xs text-gray-600 flex items-center gap-1">
                      <Check className="w-3 h-3 text-blue-500" />
                      {detail.concept} → {detail.parent}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button
              onClick={handleReset}
              className="w-full mt-4 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            >
              重新扫描
            </button>
          </div>
        )}
```

- [ ] **Step 2: 添加状态变量**

在组件顶部状态定义处（约第 47 行），添加：

```tsx
  const [floatingFixed, setFloatingFixed] = useState(0)
  const [floatingDetails, setFloatingDetails] = useState<Array<{concept: string; parent?: string; status: string}>>([])
```

- [ ] **Step 3: 更新 handleExecute 函数**

找到 `handleExecute` 函数（约第 153 行），修改为：

```tsx
  const handleExecute = async () => {
    setPanelState('executing')
    setError(null)
    try {
      const res = await dedupApi.execute(scanId, Array.from(selectedIds))
      setExecuteDetails(res.data.details)
      setFloatingFixed(res.data.floating_fixed || 0)
      setFloatingDetails(res.data.floating_details || [])
      setPanelState('result')
    } catch (err: any) {
      setError(err.response?.data?.detail || '执行失败')
      setPanelState('review')
    }
  }
```

- [ ] **Step 4: 在 handleReset 中重置状态**

找到 `handleReset` 函数，添加重置：

```tsx
  const handleReset = () => {
    setPanelState('idle')
    setScanId('')
    setSuggestions([])
    setSelectedIds(new Set())
    setExecuteDetails([])
    setFloatingFixed(0)
    setFloatingDetails([])
    setError(null)
    // ... 其他重置逻辑
  }
```

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/DedupPanel.tsx
git commit -m "feat(frontend): show floating concept fix results in dedup panel"
```

---

### Task 4: 删除旧的独立脚本

**Files:**
- Delete: `fix_floating_concepts.py`

- [ ] **Step 1: 删除文件**

```bash
git rm fix_floating_concepts.py
git commit -m "refactor: remove standalone floating concepts script (integrated into dedup module)"
```

---

### Task 5: 验证功能

- [ ] **Step 1: 启动后端服务**

```bash
cd D:/meta-knowledge-graph-main
python -m uvicorn backend.main:app --reload
```

- [ ] **Step 2: 启动前端**

```bash
cd D:/meta-knowledge-graph-main/frontend
npm run dev
```

- [ ] **Step 3: 测试流程**

1. 打开前端页面，进入知识图谱
2. 点击"去重扫描"按钮
3. 扫描完成后，选择一些合并建议
4. 点击"执行合并"
5. 验证结果显示中是否包含"修复了 X 个漂浮概念"

- [ ] **Step 4: 最终提交（如有修改）**

```bash
git add -A
git commit -m "chore: final cleanup for floating concepts auto-fix"
```

---

## 检查清单

- [ ] `mkg/dedup/floating_fixer.py` 已创建
- [ ] `mkg/dedup/deduplicator.py` 已修改
- [ ] `frontend/src/components/DedupPanel.tsx` 已修改
- [ ] `fix_floating_concepts.py` 已删除
- [ ] 功能已验证