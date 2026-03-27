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
    merge_type: Optional[Literal["synonym", "absorption", "translation"]] = None
    target_id: Optional[str] = None
    target_text: Optional[str] = None
    target_category: Optional[str] = None
    confidence: Optional[float] = None
    rationale: str = ""
    reason_type: Optional[Literal["hierarchical", "parallel", "granularity", "semantic"]] = None

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

        return f"""你是一位学术术语标准化专家。你的任务是判断概念对是否应该合并，并维护知识图谱的结构完整性。

核心原则：宁可不合并（保留两个独立节点），也不可错误合并（把不同概念混为一谈）。

## 候选概念对

{json.dumps(candidate_info, ensure_ascii=False, indent=2)}

## 合并判断规则

### 应该合并的三种情况

**A 类：同义表述** — 完全相同的概念，仅表述不同
- "强化学习" ↔ "强化学习方法" ✅
- "卷积神经网络" ↔ "CNN" ✅
- "注意力机制" ↔ "Attention 机制" ✅

**B 类：粒度吸收** — 一方是另一方加上无实质区分意义的修饰词
- "深度学习方法" ↔ "深度学习" ✅（保留更简洁的）
- "基于 Transformer 的方法" ↔ "Transformer" ✅

**C 类：翻译对应** — 同一概念的中英文版本
- "知识蒸馏" ↔ "Knowledge Distillation" ✅（保留中文）

### 不应该合并的情况（严格执行）

**1. 上下位关系（父子关系）** — 绝对禁止合并
- "人工智能" ↔ "具身人工智能" ❌（人工智能是父概念，具身人工智能是子方向）
- "人工智能" ↔ "生成式人工智能" ❌（人工智能是父概念，生成式人工智能是子方向）
- "机器学习" ↔ "深度学习" ❌（机器学习是父概念）
- "深度学习" ↔ "CNN" ❌（深度学习是父概念）

**判断方法**：如果 A 是 B 的一个"类型"或"分支"，则不能合并。

**2. 并列关系** — 同级不同方向
- "强化学习" ↔ "监督学习" ❌
- "计算机视觉" ↔ "自然语言处理" ❌

**3. 粒度差异过大** — 跨多个层级
- "人工智能" ↔ "梯度下降" ❌

**4. 名似义不同** — 不同领域
- "图网络" ↔ "图数据库" ❌

### 保留策略（选择 target_id）

1. 保留 paper_count 更高的
2. paper_count 相同则保留子节点更多的
3. 以上都相同则保留更简洁的中文名称

### category 层级检查（关键）

层级顺序：field > direction > subdirection > method > task > technique

**差两级及以上，坚决不合并**：
- field vs direction ❌（如"人工智能"与"具身人工智能"）
- field vs subdirection ❌
- direction vs method ❌

**差一级需谨慎**：
- direction vs subdirection：检查是否真的是同义词，而非上下位

## 输出格式

只输出 JSON，不要其他内容：

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
      "rationale": "一句话合并理由"
    }},
    {{
      "pair_id": 1,
      "should_merge": false,
      "reason_type": "hierarchical | parallel | granularity | semantic",
      "rationale": "一句话不合并理由"
    }}
  ]
}}"""

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