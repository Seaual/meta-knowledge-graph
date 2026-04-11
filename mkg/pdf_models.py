"""PDF 解析数据模型"""

import hashlib
import re
from dataclasses import dataclass, field


@dataclass
class PaperContent:
    """论文内容（原始文本）"""

    title: str
    authors: list[str]
    abstract: str
    full_text: str
    sections: dict[str, str]
    metadata: dict
    doi: str = ""  # DOI 标识符
    arxiv_id: str = ""  # arXiv ID
    keywords: list[str] = field(default_factory=list)
    contributions: list[str] = field(default_factory=list)


@dataclass
class ConceptTree:
    """
    概念树结构

    示例结构:
    {
        "concept": "人工智能",
        "category": "field",
        "confidence": 0.95,
        "is_anchor": true,  # 新增：是否为锚点节点
        "contribution_role": null,  # 新增：proposed/improved/applied/analyzed
        "children": [...]
    }
    """

    concept: str  # 中文名称
    concept_en: str | None = None  # 英文名称
    category: str = "method"
    confidence: float = 0.9
    is_anchor: bool = False  # 新增：是否为锚点节点
    contribution_role: str | None = None  # 新增: proposed/improved/applied/analyzed
    children: list["ConceptTree"] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        result = {
            "concept": self.concept,
            "concept_en": self.concept_en,
            "category": self.category,
            "confidence": self.confidence,
            "is_anchor": self.is_anchor,
            "id": self._to_slug(self.concept_en or self.concept),
        }
        if self.contribution_role:
            result["contribution_role"] = self.contribution_role
        if self.children:
            result["children"] = [child.to_dict() for child in self.children]
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "ConceptTree":
        """从字典构建 ConceptTree（支持双语格式）"""
        # 支持新旧两种格式
        concept_data = data.get("concept", "")
        if isinstance(concept_data, dict):
            # 新格式: {"en": "...", "zh": "..."}
            concept = concept_data.get("zh", concept_data.get("en", ""))
            concept_en = concept_data.get("en")
        else:
            # 旧格式: 字符串
            concept = concept_data
            concept_en = data.get("concept_en")

        return cls(
            concept=concept,
            concept_en=concept_en,
            category=data.get("category", "method"),
            confidence=data.get("confidence", 0.9),
            is_anchor=data.get("is_anchor", False),
            contribution_role=data.get("contribution_role"),
            children=[cls.from_dict(c) for c in data.get("children", [])],
        )

    def _to_slug(self, text: str) -> str:
        """转换为 slug ID（优先使用英文）"""
        # 如果是英文，直接处理
        if text and re.match(r"^[a-zA-Z0-9\s\-]+$", text):
            slug = text.lower()
            slug = re.sub(r"[^a-z0-9-]", "-", slug)
            slug = re.sub(r"-+", "-", slug)
            slug = slug.strip("-")
            if slug:
                return slug[:100]

        # 尝试转换为拼音
        try:
            from pypinyin import lazy_pinyin

            slug = "-".join(lazy_pinyin(text))
            slug = slug.lower()
            slug = re.sub(r"[^a-z0-9-]", "", slug)
            slug = re.sub(r"-+", "-", slug)
            slug = slug.strip("-")
            if slug:
                return slug[:100]
        except ImportError:
            pass

        # 回退：使用文本的 hash 作为 ID
        slug = text.lower()
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"[^a-z0-9-]", "", slug)
        slug = slug.strip("-")

        if slug:
            return slug[:100]

        # 如果是纯中文或其他非拉丁字符，使用 hash
        return hashlib.md5(text.encode()).hexdigest()[:12]


@dataclass
class LLMExtractedContent:
    """LLM 提取的结构化内容"""

    title: str
    authors: list[str]
    abstract: str
    research_questions: list[str]
    contributions: list[str]
    concept_tree: ConceptTree
    methodology: str | None
    datasets: list[str]
    metrics: list[str]
    raw_response: str
    # 新增 Stage 1 摘要字段
    one_sentence_summary: str | None = None
    research_context: dict | None = None  # {field, direction, existing_gap}
    background_concepts: list[str] = field(default_factory=list)
    novel_concepts: list[str] = field(default_factory=list)
