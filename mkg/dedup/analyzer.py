"""
LLM 分析器 - 判断概念是否应该合并及合并后的层级关系
"""

import json
import re
from typing import List, Dict
from dataclasses import dataclass, field


@dataclass
class MergeSuggestion:
    """合并建议"""
    source_id: str
    target_id: str
    target_text: str = ""  # 新增：合并后的概念名称
    target_category: str = ""  # 新增：合并后的 category
    merge_type: str = ""  # 新增：synonym/absorption/translation
    confidence: float = 0.8
    rationale: str = ""
    merged_relations: Dict[str, List[str]] = field(default_factory=dict)


class MergeAnalyzer:
    """LLM 分析器"""

    def __init__(self, llm_client):
        self.llm_client = llm_client
        # 这些方法会在 deduplicator 中注入
        self._get_parent_names = lambda cid: []
        self._get_child_names = lambda cid: []

    def analyze(self, candidates: List) -> List[MergeSuggestion]:
        """分析候选对，返回合并建议"""
        if not candidates:
            return []

        prompt = self._build_prompt(candidates)
        try:
            response = self.llm_client.extract_concepts(prompt)
            return self._parse_response(response, candidates)
        except Exception as e:
            print(f"LLM 分析失败: {e}")
            return []

    def _build_prompt(self, candidates: List) -> str:
        """构建 LLM prompt（增强版）"""
        candidate_info = []
        for i, pair in enumerate(candidates):
            # 获取 category
            cat1 = pair.concept1.get('category', 'method')
            cat2 = pair.concept2.get('category', 'method')

            candidate_info.append({
                "pair_id": i,
                "concept1": {
                    "id": pair.concept1['id'],
                    "text": pair.concept1['text'],
                    "category": cat1,
                    "paper_count": pair.concept1.get('paper_count', 0),
                    "parents": self._get_parent_names(pair.concept1['id']),
                    "children": self._get_child_names(pair.concept1['id'])
                },
                "concept2": {
                    "id": pair.concept2['id'],
                    "text": pair.concept2['text'],
                    "category": cat2,
                    "paper_count": pair.concept2.get('paper_count', 0),
                    "parents": self._get_parent_names(pair.concept2['id']),
                    "children": self._get_child_names(pair.concept2['id'])
                },
                "similarity": round(pair.similarity, 2)
            })

        return """<s>
你是一位学术术语标准化专家。你的任务是判断概念对是否应该合并，并维护知识图谱的结构完整性。

核心原则：宁可不合并（保留两个独立节点），也不可错误合并（把不同概念混为一谈）。
</s>

<task>
请逐一分析以下候选概念对，判断是否应该合并。
</task>

<candidates>
{candidates_json}
</candidates>

<merge_rules>
## 应该合并的三种情况

**A 类：同义表述** — 指向完全相同的概念，仅表述不同
- "强化学习" ↔ "强化学习方法" ✅
- "卷积神经网络" ↔ "CNN" ✅
- "注意力机制" ↔ "Attention 机制" ✅
- "图神经网络" ↔ "GNN" ✅

**B 类：粒度吸收** — 一方是另一方加上无实质区分意义的修饰词
- "深度学习方法" ↔ "深度学习" ✅（"方法"是冗余后缀）
- "基于 Transformer 的方法" ↔ "Transformer" ✅
- 保留更简洁的那个作为 target

**C 类：翻译对应** — 同一概念的中英文版本
- "知识蒸馏" ↔ "Knowledge Distillation" ✅（保留中文）

## 不应该合并的四种情况

**1. 上下位关系**："机器学习" ↔ "深度学习" ❌（父子关系，不是同义词）
**2. 并列关系**："强化学习" ↔ "监督学习" ❌（同级别不同方向）
**3. 粒度差异过大**："人工智能" ↔ "梯度下降" ❌（跨多个层级）
**4. 名似义不同**："图网络" ↔ "图数据库" ❌（不同领域概念）

## 保留策略（选择 target_id）

按优先级排序：
1. 保留 paper_count 更高的（被更多论文引用的）
2. 保留子节点更多的（图谱连接更丰富的）
3. 以上相同时，保留更简洁的中文名称

## category 冲突处理

- 差一级（如 direction vs subdirection）：可合并，保留更高层级的 category
- 差两级及以上（如 field vs method）：不合并，这通常说明它们是不同概念
</merge_rules>

<output_format>
输出 JSON：

{{
  "merge_suggestions": [
    {{
      "pair_id": 0,
      "should_merge": true,
      "merge_type": "synonym | absorption | translation",
      "target_id": "保留的概念 ID",
      "target_text": "合并后的概念名称",
      "target_category": "合并后的 category",
      "confidence": 0.60-1.00,
      "rationale": "一句话合并理由",
      "merged_parents": ["合并后父概念 ID 列表（两者并集去重）"],
      "merged_children": ["合并后子概念 ID 列表（两者并集去重）"]
    }},
    {{
      "pair_id": 1,
      "should_merge": false,
      "reason_type": "hierarchical | parallel | granularity | semantic",
      "rationale": "一句话不合并理由"
    }}
  ]
}}
</output_format>

只输出 JSON，不要其他内容。""".format(candidates_json=json.dumps(candidate_info, ensure_ascii=False, indent=2))

    def _parse_response(self, response: str, candidates: List) -> List[MergeSuggestion]:
        """解析 LLM 响应（增强版）"""
        suggestions = []
        try:
            json_match = re.search(r'```json\s*(.+?)\s*```', response, re.DOTALL)
            json_str = json_match.group(1) if json_match else response.strip()
            data = json.loads(json_str)

            for item in data.get('merge_suggestions', []):
                if not item.get('should_merge', False):
                    continue

                pair_id = item.get('pair_id')
                if pair_id is None or pair_id >= len(candidates):
                    continue

                pair = candidates[pair_id]
                target_id = item.get('target_id', pair.concept1['id'])
                source_id = pair.concept2['id'] if target_id == pair.concept1['id'] else pair.concept1['id']

                # 获取 target_text
                target_text = item.get('target_text', '')
                if not target_text:
                    target_text = pair.concept1['text'] if target_id == pair.concept1['id'] else pair.concept2['text']

                # 获取 target_category
                target_category = item.get('target_category', '')
                if not target_category:
                    target_category = pair.concept1.get('category', 'method') if target_id == pair.concept1['id'] else pair.concept2.get('category', 'method')

                suggestions.append(MergeSuggestion(
                    source_id=source_id,
                    target_id=target_id,
                    target_text=target_text,
                    target_category=target_category,
                    merge_type=item.get('merge_type', 'synonym'),
                    confidence=item.get('confidence', 0.8),
                    rationale=item.get('rationale', ''),
                    merged_relations={
                        'parents': item.get('merged_parents', []),
                        'children': item.get('merged_children', [])
                    }
                ))
        except (json.JSONDecodeError, KeyError) as e:
            print(f"解析 LLM 响应失败: {e}")

        return suggestions