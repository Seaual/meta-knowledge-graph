"""
LLM 分析器 - 判断概念是否应该合并及合并后的层级关系
"""

import json
import re
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class MergeSuggestion:
    """合并建议"""
    source_id: str
    target_id: str
    confidence: float
    rationale: str
    merged_relations: Dict[str, List[str]]


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
        """构建 LLM prompt"""
        candidate_info = []
        for i, pair in enumerate(candidates):
            candidate_info.append({
                "pair_id": i,
                "concept1": {
                    "id": pair.concept1['id'],
                    "text": pair.concept1['text'],
                    "paper_count": pair.concept1.get('paper_count', 0),
                    "parents": self._get_parent_names(pair.concept1['id']),
                    "children": self._get_child_names(pair.concept1['id'])
                },
                "concept2": {
                    "id": pair.concept2['id'],
                    "text": pair.concept2['text'],
                    "paper_count": pair.concept2.get('paper_count', 0),
                    "parents": self._get_parent_names(pair.concept2['id']),
                    "children": self._get_child_names(pair.concept2['id'])
                },
                "similarity": round(pair.similarity, 2)
            })

        return f"""你是一个学术知识图谱维护助手。请分析以下概念对，判断哪些应该合并。

## 候选概念对

{json.dumps(candidate_info, ensure_ascii=False, indent=2)}

## 任务

对于每一对概念，判断它们是否应该合并。合并的判断标准：
1. 两个概念是否指向同一学术概念（只是名称略有不同）
2. 例如"强化学习"和"强化学习方法"应该合并
3. 但"强化学习"和"监督学习"不应该合并

## 输出格式

请输出 JSON 格式：

```json
{{
  "merge_suggestions": [
    {{
      "pair_id": 0,
      "should_merge": true,
      "target_id": "保留的概念ID",
      "confidence": 0.95,
      "rationale": "简短说明",
      "merged_parents": ["父概念ID列表"],
      "merged_children": ["子概念ID列表"]
    }},
    {{
      "pair_id": 1,
      "should_merge": false,
      "rationale": "不应该合并的原因"
    }}
  ]
}}
```

只输出 JSON，不要其他内容。"""

    def _parse_response(self, response: str, candidates: List) -> List[MergeSuggestion]:
        """解析 LLM 响应"""
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

                suggestions.append(MergeSuggestion(
                    source_id=source_id,
                    target_id=target_id,
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