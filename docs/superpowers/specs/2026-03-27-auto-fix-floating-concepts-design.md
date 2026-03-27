# 合并后自动修复漂浮概念

## 背景

概念合并过程中可能丢失父节点关系，导致某些概念"漂浮"（有子节点但无父节点）。当前修复逻辑在独立脚本 `fix_floating_concepts.py` 中，需要手动运行。

## 目标

合并完成后自动检测并修复漂浮概念，无需用户干预。

## 设计

### 改动位置

`mkg/dedup/deduplicator.py` 的 `execute_merge()` 方法

### 新增模块

`mkg/dedup/floating_fixer.py`

```
mkg/dedup/
├── analyzer.py      # LLM 分析合并建议
├── candidate.py     # 候选对生成
├── deduplicator.py  # 主控制器（修改）
├── executor.py      # 合并执行器
└── floating_fixer.py # 漂浮概念修复（新增）
```

### 模块接口

```python
# floating_fixer.py

def find_floating_concepts(db) -> list[dict]:
    """查找需要修复的漂浮概念

    Returns:
        [{'id', 'text', 'category', 'children': [...]}]
    """

def infer_parent(db, llm_client, floating_concept, candidates) -> str | None:
    """推断单个概念的父节点"""

def fix_floating_concepts(db, llm_client) -> dict:
    """修复所有漂浮概念

    Returns:
        {'fixed': int, 'details': [...]}
    """
```

### 流程变更

```python
# deduplicator.py

def execute_merge(self, scan_id: str, merge_ids: List[str]) -> dict:
    # 1. 执行合并（现有逻辑）
    ...

    # 2. 如果有成功的合并 → 自动修复漂浮概念
    if executed > 0:
        fix_result = fix_floating_concepts(self.db, self.llm_client)
        return {
            "executed": executed,
            "details": details,
            "floating_fixed": fix_result['fixed'],
            "floating_details": fix_result['details']
        }

    return {"executed": executed, "details": details}
```

### 前端适配

`DedupPanel.tsx` 结果页面显示修复信息：

```
已完成 5 项合并
修复了 3 个漂浮概念
```

## 文件变更

| 文件 | 操作 |
|------|------|
| `mkg/dedup/floating_fixer.py` | 新增 |
| `mkg/dedup/deduplicator.py` | 修改 |
| `fix_floating_concepts.py` | 删除（功能已集成） |
| `frontend/src/components/DedupPanel.tsx` | 修改（显示修复信息） |

## 风险

- LLM 调用失败：跳过修复，不影响合并结果
- 父节点推断错误：用户可手动修正