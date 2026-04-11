"""
漂浮概念修复器 - 检测并修复丢失父节点的概念
"""

import json
import logging
import re
import sqlite3

logger = logging.getLogger("mkg.dedup")


# 层级结构定义
CATEGORY_HIERARCHY = ['field', 'direction', 'subdirection', 'task', 'method', 'technique', 'dataset', 'finding']


def find_floating_concepts(db) -> list[dict]:
    """找出需要修复的漂浮概念（有子节点但无父节点，非顶层 field）

    Args:
        db: Database 实例

    Returns:
        [{'id', 'text', 'category', 'paper_count', 'children': [...], 'paper_titles': [...]}]
    """
    conn = db.conn
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute('''
        SELECT c.id, c.text, c.text_en, c.text_zh, c.category, c.paper_count,
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

            # 获取关联论文标题
            cur.execute('''
                SELECT DISTINCT p.title
                FROM papers p
                JOIN paper_concepts pc ON p.doi = pc.paper_doi
                WHERE pc.concept_id = ?
                LIMIT 5
            ''', (row['id'],))
            papers = cur.fetchall()

            floating.append({
                'id': row['id'],
                'text': row['text'],
                'text_en': row['text_en'],
                'text_zh': row['text_zh'],
                'category': row['category'],
                'paper_count': row['paper_count'],
                'children': [{'text': c['text'], 'category': c['category']} for c in children],
                'paper_titles': [p['title'] for p in papers if p['title']]
            })

    logger.info(f"发现 {len(floating)} 个漂浮概念")
    return floating


def get_candidate_parents(db, category: str) -> list[dict]:
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


def infer_parent(db, llm_client, floating_concept: dict, candidates: list[dict]) -> str | None:
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

    children_names = [c['text'] for c in floating_concept.get('children', [])]
    paper_titles = floating_concept.get('paper_titles', [])[:5]  # 最多取5篇论文

    prompt = f"""<s>
You are an academic knowledge graph structure expert. Your task is to find the correct parent node for a floating concept (a concept that currently has no parent in the graph).

Key principles:
- The parent must be the MOST DIRECT upper-level concept — not a grandparent.
- If no candidate is a good direct parent, output null. Do NOT force a bad connection.
- A wrong parent is worse than no parent.
</s>

<floating_concept>
- Name: {floating_concept['text']}
- English: {floating_concept.get('text_en', 'N/A')}
- Chinese: {floating_concept.get('text_zh', 'N/A')}
- Category: {floating_concept['category']}
- Current children: {json.dumps(children_names, ensure_ascii=False)}
- Associated papers: {json.dumps(paper_titles, ensure_ascii=False)}
</floating_concept>

<candidates>
{candidates_json}
</candidates>

<rules>
## Category hierarchy (strict order)

field > direction > subdirection > task > method > technique > dataset > finding

## Selection rules

1. **Category constraint**: Parent category MUST be strictly higher than the floating concept's category.
   - If floating concept is "method", parent must be task, subdirection, direction, or field.
   - If floating concept is "direction", parent must be field.
   - NEVER assign a parent at the same level or lower level.

2. **Prefer the most specific valid parent** (closest in hierarchy):
   - If candidates include both a "direction" and a "subdirection" for a "method" concept → pick the "subdirection" (it's closer).
   - Rule: among valid candidates, choose the one whose category is LOWEST (most specific) while still being above the floating concept.

3. **Semantic relevance**: The parent must be semantically related to the floating concept.
   - "QMIX" → parent "值分解方法" ✅ (QMIX is a value decomposition method)
   - "QMIX" → parent "计算机视觉" ❌ (wrong field entirely)

4. **Check consistency with children**: If the floating concept has children, the chosen parent should make sense as a grandparent of those children.

5. **When to output null**:
   - No candidate has a strictly higher category → null
   - No candidate is semantically related → null
   - The closest valid candidate is 2+ levels above AND there's no intermediate concept → null
</rules>

<examples>
Example 1: Clear match
- Floating: "QMIX算法" (method)
- Candidates: ["多智能体强化学习" (direction), "值分解方法" (subdirection)]
- Answer: {{"parent_id": "值分解方法的ID"}}
- Reason: "值分解方法" is subdirection, one level above method. "多智能体强化学习" is direction, two levels above — too far.

Example 2: Only distant candidate
- Floating: "注意力加权混合" (technique)
- Candidates: ["强化学习" (direction)]
- Answer: {{"parent_id": null}}
- Reason: direction is 4 levels above technique. No valid direct parent exists.

Example 3: Semantic mismatch
- Floating: "YOLO" (method)
- Candidates: ["自然语言处理" (direction), "目标检测" (subdirection)]
- Answer: {{"parent_id": "目标检测的ID"}}
- Reason: YOLO is an object detection method. "自然语言处理" is wrong field.

Example 4: Same level — reject
- Floating: "PPO算法" (method)
- Candidates: ["QMIX算法" (method), "强化学习" (direction)]
- Answer: {{"parent_id": "强化学习的ID"}}
- Reason: QMIX is same level (method), cannot be parent.
</examples>

<output_format>
Output JSON only:

{{"parent_id": "xxx"}}

or if no suitable parent:

{{"parent_id": null, "reason": "brief explanation"}}
</output_format>"""

    try:
        response = llm_client.extract_concepts(prompt)
        json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result.get('parent_id')
    except Exception as e:
        logger.error(f"LLM 推断父节点失败: {e}")

    return None


def fix_floating_concepts(db, llm_client) -> dict:
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
