"""
漂浮概念修复器 - 检测并修复丢失父节点的概念
"""

import json
import re
import logging
import sqlite3
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


def infer_parent(db, llm_client, floating_concept: Dict, candidates: List[Dict]) -> Optional[str]:
    """让 LLM 推断父节点

    Args:
        db: Database 实例（保留用于未来扩展）
        llm_client: LLM 客户端
        floating_concept: 漂浮概念信息
        candidates: 候选父节点列表

    Returns:
        parent_id 或 None
    """
    candidates_json = json.dumps(
        [{'id': c['id'], 'text': c['text'], 'category': c['category']} for c in candidates[:50]],
        ensure_ascii=False,
        indent=2
    )

    children_names = [c['text'] for c in floating_concept['children']]

    prompt = f"""为以下概念从候选列表中选择最合适的父节点。

## 待匹配概念
- 名称：{floating_concept['text']}
- 层级：{floating_concept['category']}
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

        parent_id = infer_parent(db, llm_client, fc, candidates)

        if parent_id:
            parent = db.get_concept(parent_id)
            if parent:
                # 使用线程安全的方式执行写操作
                with db._lock:
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