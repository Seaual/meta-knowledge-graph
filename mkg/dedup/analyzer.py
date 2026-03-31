"""
LLM 分析器 - 判断概念是否应该合并
"""

import json
import re
import logging
from typing import List, Optional, Literal
from dataclasses import dataclass, field
from pydantic import BaseModel, validator


logger = logging.getLogger("mkg.dedup")


@dataclass
class MergeSuggestion:
    """合并建议"""
    source_id: str
    target_id: str
    target_text: str = ""
    target_category: str = ""
    merge_type: str = ""  # synonym/absorption/translation
    confidence: float = 0.8
    rationale: str = ""


# ============ Pydantic 模型用于验证 LLM 响应 ============

class MergeSuggestionItem(BaseModel):
    """单个合并建议的验证模型"""
    pair_id: int
    should_merge: bool
    merge_type: Optional[Literal["synonym", "absorption", "bilingual"]] = None
    target_id: Optional[str] = None
    target_text: Optional[str] = None
    target_category: Optional[str] = None
    confidence: Optional[float] = None
    rationale: str = ""
    reason_type: Optional[Literal["hierarchical", "parallel", "partial_overlap", "category_gap"]] = None

    @validator('confidence')
    def validate_confidence(cls, v):
        if v is not None and not (0 <= v <= 1):
            logger.warning(f"Confidence out of range: {v}, clamping to [0, 1]")
            return max(0, min(1, v))
        return v

    @validator('target_id', always=True)
    def validate_target_required_when_merge(cls, v, values):
        if values.get('should_merge') and not v:
            raise ValueError('target_id required when should_merge=true')
        return v


class MergeResponse(BaseModel):
    """LLM 响应的验证模型"""
    merge_suggestions: List[MergeSuggestionItem]


class MergeAnalyzer:
    """LLM 分析器"""

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def analyze(self, candidates: List) -> List[MergeSuggestion]:
        """分析候选对，返回合并建议"""
        if not candidates:
            return []

        prompt = self._build_prompt(candidates)
        try:
            response = self.llm_client.extract_concepts(prompt)
            return self._parse_response(response, candidates)
        except Exception as e:
            logger.error(f"LLM 分析失败: {e}")
            return []

    def _build_prompt(self, candidates: List) -> str:
        """构建 LLM prompt"""
        candidate_info = []
        for i, pair in enumerate(candidates):
            cat1 = pair.concept1.get('category', 'method')
            cat2 = pair.concept2.get('category', 'method')

            candidate_info.append({
                "pair_id": i,
                "concept1": {
                    "id": pair.concept1['id'],
                    "text": pair.concept1['text'],
                    "category": cat1,
                    "paper_count": pair.concept1.get('paper_count', 0)
                },
                "concept2": {
                    "id": pair.concept2['id'],
                    "text": pair.concept2['text'],
                    "category": cat2,
                    "paper_count": pair.concept2.get('paper_count', 0)
                },
                "similarity": round(pair.similarity, 2)
            })

        return f"""<s>
You are an academic terminology standardization expert. Your task is to judge whether concept pairs should be merged, maintaining the structural integrity of the knowledge graph.

Core principle: It is BETTER to keep two separate nodes (false negative) than to wrongly merge two different concepts (false positive). When in doubt, do NOT merge.
</s>

<candidates>
{json.dumps(candidate_info, ensure_ascii=False, indent=2)}
</candidates>

<rules>
## Category hierarchy (memorize this order)

field > direction > subdirection > task > method > technique > dataset > finding

Example mapping:
- field: 人工智能, 运筹学
- direction: 强化学习, 计算机视觉
- subdirection: 多智能体强化学习, 小样本学习
- task: 信用分配问题, 域适应
- method: QMIX, YOLOv5
- technique: 注意力机制, 梯度裁剪
- dataset: ImageNet, SMAC
- finding: Scaling Laws

## MERGE: Three situations where merging is correct

**Type A: Synonym** — Same concept, different wording
Tests: Would a researcher use these interchangeably in the same sentence?
- "强化学习" ↔ "强化学习方法" ✅ (redundant suffix)
- "卷积神经网络" ↔ "CNN" ✅ (abbreviation)
- "注意力机制" ↔ "Attention Mechanism" ✅ (translation)
- "Graph Neural Network" ↔ "图神经网络" ✅ (translation)

**Type B: Absorption** — One is the other plus a meaningless modifier
Tests: Does removing the modifier change which specific concept is referred to? If NO → merge.
- "深度学习方法" ↔ "深度学习" ✅ ("方法" adds no specificity)
- "基于Transformer的方法" ↔ "Transformer" ✅ ("基于...的方法" is a filler phrase)
- BUT: "多智能体强化学习" ↔ "强化学习" ❌ ("多智能体" is NOT a meaningless modifier — it specifies a subfield)

**Type C: Bilingual match** — Same concept in Chinese and English
Tests: Do the English and Chinese names refer to the exact same concept in academic literature?
- "知识蒸馏" ↔ "Knowledge Distillation" ✅
- Retain the one that already has both en/zh fields populated. If both do, retain the one with higher paper_count.

## DO NOT MERGE: Four situations (strictly enforced)

**1. Hierarchical (parent-child) relationship** — ABSOLUTE BAN
One concept is a TYPE or SUBFIELD of the other.

Quick test: Can you say "B is a kind of A" or "B is a subfield of A"? If yes → DO NOT merge.
- "人工智能" ↔ "具身人工智能" ❌ (具身AI is a subfield of AI)
- "人工智能" ↔ "生成式人工智能" ❌ (生成式AI is a subfield of AI)
- "机器学习" ↔ "深度学习" ❌ (深度学习 is a subfield of 机器学习)
- "强化学习" ↔ "多智能体强化学习" ❌ (MARL is a subfield of RL)
- "Transformer" ↔ "Vision Transformer" ❌ (ViT is a variant of Transformer)

WARNING: This is the most common error. "X" and "X的一个方向" look similar but MUST NOT be merged.

**2. Parallel relationship** — Same level, different directions
- "强化学习" ↔ "监督学习" ❌
- "计算机视觉" ↔ "自然语言处理" ❌
- "QMIX" ↔ "MAPPO" ❌

**3. Partial overlap** — Shared words but different concepts
- "多智能体强化学习" ↔ "多智能体系统" ❌ (different fields despite sharing "多智能体")
- "知识图谱" ↔ "知识蒸馏" ❌ (different concepts despite sharing "知识")
- "图神经网络" ↔ "图数据库" ❌ (different despite sharing "图")

**4. Category gap ≥ 2 levels** — Never merge across two or more hierarchy levels
- field ↔ subdirection ❌
- direction ↔ method ❌
- field ↔ method ❌
- Category gap of 1 (e.g., direction ↔ subdirection): merge ONLY if it's clearly a synonym (Type A), not a parent-child relationship.

## Target selection (which concept to keep)

Priority order:
1. Keep the one with higher paper_count
2. If equal, keep the one with more child nodes
3. If still equal, keep the one with shorter, cleaner Chinese name
4. If one has bilingual names and the other doesn't, keep the bilingual one
</rules>

<output_format>
Output JSON only:

{{
  "merge_suggestions": [
    {{
      "pair_id": 0,
      "should_merge": true,
      "merge_type": "synonym | absorption | bilingual",
      "target_id": "ID of concept to keep",
      "target_text": "Name after merge (use the cleaner name)",
      "target_category": "Category after merge (keep the higher level if different)",
      "confidence": 0.60-1.00,
      "rationale": "One sentence explaining why"
    }},
    {{
      "pair_id": 1,
      "should_merge": false,
      "reason_type": "hierarchical | parallel | partial_overlap | category_gap",
      "rationale": "One sentence explaining why not"
    }}
  ]
}}
</output_format>"""

    def _parse_response(self, response: str, candidates: List) -> List[MergeSuggestion]:
        """解析 LLM 响应，带验证"""
        suggestions = []

        # 1. 提取 JSON（支持 markdown 包裹）
        try:
            json_match = re.search(r'```json\s*(.+?)\s*```', response, re.DOTALL)
            json_str = json_match.group(1) if json_match else response.strip()
            raw_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            # 尝试提取花括号内容
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    raw_data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    logger.error("二次解析也失败")
                    return []
            else:
                return []

        # 2. 验证响应结构
        try:
            validated = MergeResponse(**raw_data)
        except Exception as e:
            logger.error(f"响应验证失败: {e}")
            return []

        # 3. 转换为 MergeSuggestion
        seen_targets = set()  # 检测冲突

        for item in validated.merge_suggestions:
            if not item.should_merge:
                continue

            # pair_id 范围检查
            if item.pair_id < 0 or item.pair_id >= len(candidates):
                logger.warning(f"pair_id {item.pair_id} 超出范围，跳过")
                continue

            pair = candidates[item.pair_id]

            # 验证 target_id 在候选对中存在
            if item.target_id not in [pair.concept1['id'], pair.concept2['id']]:
                logger.warning(f"target_id {item.target_id} 不在候选对中，跳过")
                continue

            # 检测冲突（同一概念被合并到多个目标）
            source_id = pair.concept2['id'] if item.target_id == pair.concept1['id'] else pair.concept1['id']
            if source_id in seen_targets:
                logger.warning(f"概念 {source_id} 已被合并，跳过重复建议")
                continue
            seen_targets.add(source_id)

            # 获取 target_text 和 target_category 的默认值
            target_text = item.target_text or ""
            if not target_text:
                target_text = pair.concept1['text'] if item.target_id == pair.concept1['id'] else pair.concept2['text']

            target_category = item.target_category or ""
            if not target_category:
                target_category = pair.concept1.get('category', 'method') if item.target_id == pair.concept1['id'] else pair.concept2.get('category', 'method')

            suggestions.append(MergeSuggestion(
                source_id=source_id,
                target_id=item.target_id,
                target_text=target_text,
                target_category=target_category,
                merge_type=item.merge_type or 'synonym',
                confidence=item.confidence or 0.8,
                rationale=item.rationale or ""
            ))

        logger.info(f"解析完成: {len(suggestions)} 条合并建议")
        return suggestions