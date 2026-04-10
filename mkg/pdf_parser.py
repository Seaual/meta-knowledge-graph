"""
PDF 解析模块 - 使用 LLM 解析学术论文

设计：
- 首选 OpenDataLoader-PDF 提取结构化 Markdown（正确阅读顺序、表格结构、标题层级）
- PyMuPDF 作为 fallback（Java 不可用时）
- 发送结构化文本给 LLM，提取结构化信息：
  - 元数据（标题、作者、摘要）
  - 研究问题/贡献
  - 概念层级树（动态分层）
  - 方法论、数据集、评估指标等
"""

import json
import logging
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


STAGE1_SUMMARY_PROMPT = """<s>
You are a senior academic literature analyst with expertise in identifying the precise contribution boundaries of research papers. Your core skill is distinguishing what a paper actually contributed from what it merely mentioned or used as background.

Your working principles:
- Extract contributions conservatively: if unsure whether something is a contribution or background, classify it as background.
- Name concepts using the terminology the academic community would recognize, not the paper's idiosyncratic phrasing.
- Provide BOTH English and Chinese for all text fields. Keep internationally recognized terms (e.g., Transformer, BERT, GAN) in their original form.
</s>

<paper>
<title>{title}</title>
<authors>{authors}</authors>
<abstract>{abstract}</abstract>
<body>{body}</body>
</paper>

<task>
Before generating JSON, think through these questions (this reasoning will not be shown to users):

1. What is the SINGLE most important thing this paper did that didn't exist before?
2. What field and direction does this belong to?
3. Which concepts in this paper are BACKGROUND (would exist without this paper) vs NOVEL (wouldn't exist without this paper)?
4. How many real contributions does this paper have? (Usually 1-3. If you're counting more than 3, you're probably including background work.)

Then output the following JSON:

{{
  "one_sentence_summary": {{
    "en": "One sentence summary (max 50 words)",
    "zh": "一句话概括（不超过50字）"
  }},

  "research_context": {{
    "field": {{
      "en": "Major research field",
      "zh": "所属大领域"
    }},
    "direction": {{
      "en": "Specific research direction",
      "zh": "所属研究方向"
    }},
    "existing_gap": {{
      "en": "The specific gap this paper fills — what was impossible or unsolved before this paper? (1-2 sentences)",
      "zh": "这篇论文填补了什么空白——在这篇论文之前什么是做不到或未解决的？（1-2句话）"
    }}
  }},

  "core_contributions": [
    {{
      "type": "new_method | new_framework | new_dataset | new_finding | improvement | theoretical",
      "claim": {{
        "en": "What exactly did this paper contribute? (1 sentence, be specific)",
        "zh": "这篇论文具体贡献了什么？（1句话，要具体）"
      }},
      "novelty": {{
        "en": "Compared to the closest prior work, what is new? Name the prior work explicitly. (1 sentence)",
        "zh": "与最接近的已有工作相比新在哪？请明确指出已有工作的名称。（1句话）"
      }}
    }}
  ],

  "methodology_summary": {{
    "approach": {{
      "en": "Core method in one sentence",
      "zh": "核心方法一句话概述"
    }},
    "key_components": {{
      "en": ["2-3 most critical technical components (not all components, just the novel ones)"],
      "zh": ["最关键的2-3个技术组件（只列新颖的，不列标准组件）"]
    }},
    "baselines": {{
      "en": ["Baseline methods compared against"],
      "zh": ["对比的基线方法"]
    }}
  }},

  "results_summary": {{
    "datasets": {{
      "en": ["Datasets used"],
      "zh": ["使用的数据集"]
    }},
    "metrics": {{
      "en": ["Evaluation metrics"],
      "zh": ["评估指标"]
    }},
    "main_finding": {{
      "en": "Most important result WITH numbers if available (e.g., 'Outperforms QMIX by 12-18% win rate on SMAC hard scenarios')",
      "zh": "最重要的实验结论，尽量带具体数字"
    }}
  }},

  "background_concepts": {{
    "en": ["Concepts this paper USES but did NOT create — these would be well-known even if this paper didn't exist"],
    "zh": ["论文使用但并非其创造的概念——即使这篇论文不存在，这些概念也是学术界广泛认知的"]
  }},
  "novel_concepts": {{
    "en": ["Concepts that ONLY exist because of this paper — if this paper disappeared, these concepts would not be known"],
    "zh": ["因为这篇论文才存在的概念——如果这篇论文消失，这些概念就不会被人知道"]
  }}
}}
</task>

<rules>
Critical rules:

1. BACKGROUND vs NOVEL is the most important judgment in this task.
   - Baselines are ALWAYS background (e.g., QMIX, BERT, ResNet — these exist regardless of this paper)
   - Standard techniques are ALWAYS background (e.g., attention mechanism, dropout, batch normalization)
   - Only concepts NAMED and DEFINED for the first time in this paper are novel

2. core_contributions should have 1-3 items.
   - If you listed 4+, re-examine: are some of these "things the paper did" rather than "things the paper contributed"?
   - "Used dataset X" is not a contribution unless the paper CREATED dataset X.
   - "Achieved SOTA" is a result, not a contribution — the contribution is the METHOD that achieved SOTA.

3. Provide BOTH English and Chinese for all text fields.

4. If the paper is unclear or you cannot determine the contribution with confidence, say so in one_sentence_summary rather than guessing.
</rules>

Output JSON only, no other content."""


STAGE2_EXTRACTION_PROMPT = """<s>
You are an academic knowledge graph construction expert. Your task is to build a refined concept tree based on the paper summary.

Key Principle — Distinguish "anchors" from "contributions":
- **Anchor Path**: The shortest path from root to the paper's core contribution. These nodes just need to EXIST to locate the paper in the graph. Do NOT expand subtrees for anchors.
- **Contribution Subtree**: Concepts the paper truly contributed. These get full subtree expansion. These are the NEW KNOWLEDGE this paper adds to the graph.

Analogy: Anchor path is the "address" (Beijing → Haidian → Zhongguancun). Contribution subtree is "what's inside the room". You don't describe how big Beijing is — you describe what's in this specific room.

Node budget: Aim for 8-12 nodes total. More than 15 means you're extracting background, not contributions.
</s>

<paper_summary>
{summary_json}
</paper_summary>

{existing_graph_section}

<taxonomy>
Hierarchy Definition (based on "Minimum Publishable Unit" principle):

| Level | Code | Definition | Decision Rule | Examples |
|-------|------|------------|---------------|----------|
| Major field | field | An independent academic discipline | Could a university build a department around it? | AI, Operations Research |
| Direction | direction | Has its own research community | Is there a dedicated conference or journal track? | Reinforcement Learning, Object Detection |
| Subdirection | subdirection | Subdivision within a direction | Would it be an independent chapter in a survey of the parent direction? | Multi-Agent RL, Few-shot Object Detection |
| Task | task | Specific problem definition | Can you state it as "Given X, find/optimize Y"? | Credit Assignment, Domain Adaptation |
| Dataset | dataset | Named benchmark or data contribution | Is it a specific named dataset used by the community as a benchmark? | ImageNet, SMAC, HumanEval |
| Method | method | Named, reproducible algorithm | Does it have a specific name and reproducible procedure? | QMIX, YOLOv5, LoRA |
| Finding | finding | Key experimental discovery or empirical law | Is it a named result that changed how people think? | Scaling Laws, Bitter Lesson |
| Technique | technique | Component or trick within a method | None of the above → default to technique | Attention weighting, Gradient clipping |

Decision flow (ask in this order, stop at first "yes"):
1. University department? → field
2. Dedicated conference? → direction
3. Survey chapter? → subdirection
4. "Given X, find Y"? → task
5. Named benchmark dataset? → dataset
6. Named reproducible algorithm? → method
7. Named empirical discovery? → finding
8. None of above → technique

Three structural invariants:
1. **Strict monotonicity**: Parent level must be strictly higher than all children
2. **Context sensitivity**: Same term can be different levels depending on paper scope
3. **Conservative default**: When ambiguous between two adjacent levels, pick the lower (more specific) one
</taxonomy>

<task>
Build the concept tree in three steps:

**Step 1: Draw Anchor Path**
From paper_summary.research_context, extract the shortest path: field → direction.
- Mark these nodes "is_anchor": true
- Do NOT expand any children for anchor nodes
- If existing_graph has matching concepts, reuse their exact names

**Step 2: Expand Contribution Subtree**
From paper_summary.core_contributions and novel_concepts, extract the concepts this paper actually contributed.
- Mark these "is_anchor": false
- Attach them as children of the deepest anchor node
- Each contribution concept must have a category assigned using the taxonomy above
- Include datasets and findings as leaf nodes IF the paper contributed them (not if it merely used them)

**Step 3: Label Contribution Type**
For each non-anchor node, assign contribution_role:
- "proposed": First introduced by this paper (confidence should be ≥ 0.85)
- "improved": Paper modified or enhanced an existing concept (confidence ≥ 0.75)
- "applied": Paper applied an existing concept to a new domain/task (confidence ≥ 0.70)
- "analyzed": Paper provided new analysis/understanding of existing concept (confidence ≥ 0.65)

Note: contribution_role and confidence are correlated. "proposed" concepts should naturally have high confidence because the paper explicitly defines them. "analyzed" concepts may have lower confidence because the analysis boundary is fuzzy.
</task>

<confidence_scale>
| Score | Meaning | Typical Scenario |
|-------|---------|-----------------|
| 0.90-1.00 | Paper explicitly discusses, level unambiguous | Concepts in paper title, core contribution |
| 0.75-0.89 | Paper involves, level basically certain | Techniques described in methods section |
| 0.60-0.74 | Reasonably inferred from content | Implied upper-level concepts not explicitly named |
| < 0.60 | Do not output | — |
</confidence_scale>

<output_format>
{{
  "paper_summary": {{
    "en": "one_sentence_summary.en from Stage 1",
    "zh": "one_sentence_summary.zh from Stage 1"
  }},
  "concept_tree": {{
    "concept": {{
      "en": "Root concept (English)",
      "zh": "根概念（中文）"
    }},
    "category": "field",
    "is_anchor": true,
    "children": [
      {{
        "concept": {{
          "en": "Direction (English)",
          "zh": "方向（中文）"
        }},
        "category": "direction",
        "is_anchor": true,
        "children": [
          {{
            "concept": {{
              "en": "Core contribution (English)",
              "zh": "核心贡献（中文）"
            }},
            "category": "subdirection|task|dataset|method|finding|technique",
            "is_anchor": false,
            "contribution_role": "proposed|improved|applied|analyzed",
            "confidence": 0.60-1.00,
            "children": [...]
          }}
        ]
      }}
    ]
  }},
  "methodology": {{
    "en": "Core method overview",
    "zh": "核心方法概述"
  }},
  "datasets": {{
    "en": ["Datasets"],
    "zh": ["数据集"]
  }},
  "metrics": {{
    "en": ["Metrics"],
    "zh": ["指标"]
  }}
}}
</output_format>

<rules>
Final checks before outputting:
1. Count your nodes. Anchor path: 2-4 nodes. Contribution subtree: 4-10 nodes. Total: 6-15.
2. Every parent's level is strictly higher than its children's level.
3. No anchor node has children that are also anchors (anchor path is a single chain, not a tree).
4. Every non-anchor node has a contribution_role.
5. English and Chinese names are provided for ALL concepts.
6. If a concept from existing_graph matches an anchor, you used its EXACT name.
</rules>

Output JSON only, no other content."""

EXISTING_GRAPH_SECTION = """<existing_graph>
Current concept nodes in the knowledge graph.
RULES for existing graph:
1. If an anchor concept already exists in this graph, REUSE its exact name (both en and zh) — do not create a synonym.
2. If a novel concept overlaps with an existing node, still create it but note the overlap — the dedup system will handle merging later.
3. Use the existing node's category as reference, but if you believe it's wrong based on the taxonomy below, use your judgment.

{existing_tree}
</existing_graph>"""


@dataclass
class PaperContent:
    """论文内容（原始文本）"""
    title: str
    authors: List[str]
    abstract: str
    full_text: str
    sections: Dict[str, str]
    metadata: Dict
    doi: str = ""  # DOI 标识符
    arxiv_id: str = ""  # arXiv ID
    keywords: List[str] = field(default_factory=list)
    contributions: List[str] = field(default_factory=list)


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
    concept_en: Optional[str] = None  # 英文名称
    category: str = "method"
    confidence: float = 0.9
    is_anchor: bool = False  # 新增：是否为锚点节点
    contribution_role: Optional[str] = None  # 新增: proposed/improved/applied/analyzed
    children: List['ConceptTree'] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        result = {
            'concept': self.concept,
            'concept_en': self.concept_en,
            'category': self.category,
            'confidence': self.confidence,
            'is_anchor': self.is_anchor,
            'id': self._to_slug(self.concept_en or self.concept)
        }
        if self.contribution_role:
            result['contribution_role'] = self.contribution_role
        if self.children:
            result['children'] = [child.to_dict() for child in self.children]
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'ConceptTree':
        """从字典构建 ConceptTree（支持双语格式）"""
        # 支持新旧两种格式
        concept_data = data.get('concept', '')
        if isinstance(concept_data, dict):
            # 新格式: {"en": "...", "zh": "..."}
            concept = concept_data.get('zh', concept_data.get('en', ''))
            concept_en = concept_data.get('en')
        else:
            # 旧格式: 字符串
            concept = concept_data
            concept_en = data.get('concept_en')

        return cls(
            concept=concept,
            concept_en=concept_en,
            category=data.get('category', 'method'),
            confidence=data.get('confidence', 0.9),
            is_anchor=data.get('is_anchor', False),
            contribution_role=data.get('contribution_role'),
            children=[cls.from_dict(c) for c in data.get('children', [])]
        )

    def _to_slug(self, text: str) -> str:
        """转换为 slug ID（优先使用英文）"""
        import re
        import hashlib

        # 如果是英文，直接处理
        if text and re.match(r'^[a-zA-Z0-9\s\-]+$', text):
            slug = text.lower()
            slug = re.sub(r'[^a-z0-9-]', '-', slug)
            slug = re.sub(r'-+', '-', slug)
            slug = slug.strip('-')
            if slug:
                return slug[:100]

        # 尝试转换为拼音
        try:
            from pypinyin import lazy_pinyin
            slug = '-'.join(lazy_pinyin(text))
            slug = slug.lower()
            slug = re.sub(r'[^a-z0-9-]', '', slug)
            slug = re.sub(r'-+', '-', slug)
            slug = slug.strip('-')
            if slug:
                return slug[:100]
        except ImportError:
            pass

        # 回退：使用文本的 hash 作为 ID
        slug = text.lower()
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        slug = slug.strip('-')

        if slug:
            return slug[:100]

        # 如果是纯中文或其他非拉丁字符，使用 hash
        return hashlib.md5(text.encode()).hexdigest()[:12]


@dataclass
class LLMExtractedContent:
    """LLM 提取的结构化内容"""
    title: str
    authors: List[str]
    abstract: str
    research_questions: List[str]
    contributions: List[str]
    concept_tree: ConceptTree
    methodology: Optional[str]
    datasets: List[str]
    metrics: List[str]
    raw_response: str
    # 新增 Stage 1 摘要字段
    one_sentence_summary: Optional[str] = None
    research_context: Optional[Dict] = None  # {field, direction, existing_gap}
    background_concepts: List[str] = field(default_factory=list)
    novel_concepts: List[str] = field(default_factory=list)


class PDFParser:
    """PDF 解析器 - 首选 OpenDataLoader-PDF，PyMuPDF fallback"""

    def __init__(self):
        self._java_available = self._check_java()
        engine = "OpenDataLoader-PDF" if self._java_available else "PyMuPDF"
        logger.info(f"PDF engine: {engine} ({'Java available' if self._java_available else 'Java not available'})")
        print(f"[PDF] 解析引擎: {engine}")

    @staticmethod
    def _check_java() -> bool:
        """检测 Java 是否可用"""
        try:
            result = subprocess.run(
                ["java", "-version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def parse(self, pdf_path: str) -> Optional[PaperContent]:
        """
        解析 PDF 文件（自动选择引擎）

        Args:
            pdf_path: PDF 文件路径

        Returns:
            论文内容，解析失败返回 None
        """
        if self._java_available:
            result = self._parse_with_opendataloader(pdf_path)
            if result:
                return result
            logger.warning("OpenDataLoader parsing failed, falling back to PyMuPDF")
            print("[PDF] OpenDataLoader 解析失败，回退到 PyMuPDF")
        return self._parse_with_pymupdf(pdf_path)

    def extract_text(self, pdf_path: str) -> Optional[str]:
        """
        只提取纯文本（供 LLM 使用，自动选择引擎）
        """
        if self._java_available:
            text = self._extract_text_opendataloader(pdf_path)
            if text:
                return text
            logger.warning("OpenDataLoader text extraction failed, falling back to PyMuPDF")
        return self._extract_text_pymupdf(pdf_path)

    def _parse_with_opendataloader(self, pdf_path: str) -> Optional[PaperContent]:
        """
        使用 OpenDataLoader-PDF 解析 PDF

        输出 Markdown（结构化文本，供 LLM 使用）和 JSON（元数据）。
        """
        import opendataloader_pdf

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                opendataloader_pdf.convert(
                    input_path=[pdf_path],
                    output_dir=tmpdir,
                    format="markdown,json"
                )

                base_name = Path(pdf_path).stem
                md_path = Path(tmpdir) / f"{base_name}.md"
                json_path = Path(tmpdir) / f"{base_name}.json"

                full_text = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
                if not full_text:
                    return None

                metadata = {}
                if json_path.exists():
                    with open(json_path, encoding="utf-8") as f:
                        metadata = json.load(f)

                title = self._extract_title_from_markdown(full_text, metadata)
                authors = self._extract_authors_from_metadata(metadata)
                abstract = self._extract_abstract_from_markdown(full_text)
                sections = self._extract_sections_from_markdown(full_text)
                doi = self._extract_doi_from_metadata(metadata, full_text)
                arxiv_id = self._extract_arxiv_id_from_metadata(metadata, full_text)

                return PaperContent(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    full_text=full_text,
                    sections=sections,
                    metadata=metadata,
                    doi=doi,
                    arxiv_id=arxiv_id
                )

        except ImportError:
            logger.warning("opendataloader-pdf not installed, falling back to PyMuPDF")
            return None
        except Exception as e:
            logger.error(f"OpenDataLoader parsing failed: {e}")
            return None

    def _extract_text_opendataloader(self, pdf_path: str) -> Optional[str]:
        """
        使用 OpenDataLoader-PDF 提取 Markdown 文本（供 LLM 使用）
        """
        import opendataloader_pdf

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                opendataloader_pdf.convert(
                    input_path=[pdf_path],
                    output_dir=tmpdir,
                    format="markdown"
                )

                md_path = Path(tmpdir) / f"{Path(pdf_path).stem}.md"
                if not md_path.exists():
                    return None

                text = md_path.read_text(encoding="utf-8")

                if len(text) > 700000:
                    text = text[:700000] + "\n\n... [文本过长，已截断]"

                return text

        except ImportError:
            return None
        except Exception as e:
            logger.error(f"OpenDataLoader text extraction failed: {e}")
            return None

    def _extract_text_pymupdf(self, pdf_path: str) -> Optional[str]:
        """只提取纯文本（PyMuPDF fallback 路径）"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()

            if len(text) > 700000:
                text = text[:700000] + "\n\n... [文本过长，已截断]"

            return text
        except Exception as e:
            print(f"文本提取失败：{e}")
            return None

    # ========== OpenDataLoader Markdown 辅助方法 ==========

    def _extract_title_from_markdown(self, markdown: str, metadata: dict) -> str:
        """
        从 Markdown 或 JSON 元数据提取标题
        """
        # 优先级1: JSON 元数据中的标题
        meta_title = metadata.get("title", "")
        if meta_title and len(meta_title) > 10 and not self._is_suspicious_title(meta_title):
            return meta_title.strip()

        # 优先级2: Markdown 第一个 H1 标题
        match = re.match(r"^#\s+(.+)$", markdown, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            if len(title) > 10 and not self._is_suspicious_title(title):
                return title

        # 优先级3: 第二个 H1（有些 PDF 第一行是期刊信息）
        matches = re.findall(r"^#\s+(.+)$", markdown, re.MULTILINE)
        if len(matches) > 1:
            for candidate in matches[1:3]:
                candidate = candidate.strip()
                if len(candidate) > 10 and not self._is_suspicious_title(candidate):
                    return candidate

        return meta_title or "Unknown"

    def _extract_authors_from_metadata(self, metadata: dict) -> List[str]:
        """
        从 JSON 元数据提取作者列表
        """
        authors = metadata.get("authors", [])
        if isinstance(authors, str):
            authors = [a.strip() for a in authors.split(",") if a.strip()]
        elif isinstance(authors, list):
            # 处理可能是 dict 的情况（有些 PDF 解析器输出 {"name": "..."}）
            cleaned = []
            for a in authors:
                if isinstance(a, dict):
                    name = a.get("name", a.get("fullName", ""))
                else:
                    name = str(a)
                name = name.strip()
                if len(name) > 2 and not any(x in name.lower() for x in ["university", "institute", "lab", "department", "dept", "college", "school"]):
                    cleaned.append(name)
            authors = cleaned

        return authors[:10]

    def _extract_abstract_from_markdown(self, markdown: str) -> str:
        """
        从 Markdown 提取摘要
        查找 ## Abstract 或 # Abstract 部分的内容
        """
        text_lower = markdown.lower()

        # 常见的摘要标记
        abstract_markers = [
            "## abstract", "# abstract", "## abstract:", "### abstract",
            "## summary", "# summary", "## 摘要", "# 摘要"
        ]

        for marker in abstract_markers:
            idx = text_lower.find(marker)
            if idx == -1:
                continue

            start = idx + len(marker)
            # 跳过冒号和空格
            while start < len(markdown) and markdown[start] in ': \n\t':
                start += 1

            # 查找摘要结束：下一个 ## 标题或引言
            end = len(markdown)
            end_patterns = [
                "\n## ", "\n# ", "\n1 introduction", "\n1. introduction",
                "\nintroduction", "\n引言", "\n## keywords", "\n关键词"
            ]
            for pat in end_patterns:
                marker_idx = text_lower.find(pat, start)
                if marker_idx != -1 and marker_idx < end:
                    end = marker_idx

            abstract = markdown[start:end].strip()
            # 清理：移除 Markdown 格式标记
            abstract = re.sub(r'\*\*|\*|__', '', abstract)
            # 合并多行
            lines = [line.strip() for line in abstract.split('\n') if line.strip()]
            cleaned = [l for l in lines if len(l) > 20 and not l.isdigit()]
            if cleaned:
                result = ' '.join(cleaned)
                return result[:3000]

        # 找不到摘要时返回前 1000 字符
        return markdown[:1000]

    def _extract_sections_from_markdown(self, markdown: str) -> Dict[str, str]:
        """
        从 Markdown 提取章节结构
        按 ## Heading 分割
        """
        sections = {}
        target_sections = [
            "introduction", "method", "methods", "approach",
            "experiment", "experiments", "results", "discussion",
            "conclusion", "related work", "methodology"
        ]

        # 按 ## 标题分割
        heading_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
        matches = list(heading_pattern.finditer(markdown))

        for i, match in enumerate(matches):
            heading = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
            content = markdown[start:end].strip()

            # 匹配目标章节
            heading_lower = heading.lower()
            for target in target_sections:
                if target in heading_lower:
                    # 移除 Markdown 格式标记
                    clean_content = re.sub(r'#{1,4}\s+', '', content)
                    sections[target] = clean_content[:3000]
                    break

        return sections

    def _extract_doi_from_metadata(self, metadata: dict, markdown: str) -> str:
        """
        从 JSON 元数据或 Markdown 正文提取 DOI
        """
        # 优先级1: 元数据
        doi = metadata.get("doi", "")
        if doi and self._is_valid_doi(doi):
            return doi.strip().lower()

        # 优先级2: Markdown 正文
        patterns = [
            r'\b(10\.\d{4,}/[^\s,;)\]]+)',
            r'https?://doi\.org/(10\.\d{4,}/[^\s,;)\]]+)',
            r'DOI:\s*(10\.\d{4,}/[^\s,;)\]]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, markdown, re.IGNORECASE)
            if match:
                doi = re.sub(r'[.,;)\]]+$', '', match.group(1).strip())
                if self._is_valid_doi(doi):
                    return doi.lower()

        return ""

    def _extract_arxiv_id_from_metadata(self, metadata: dict, markdown: str) -> str:
        """
        从 JSON 元数据或 Markdown 正文提取 arXiv ID
        """
        # 优先级1: 元数据
        for key in ['arxiv_id', 'arxiv', 'eprint']:
            arxiv_id = metadata.get(key, "")
            if arxiv_id and self._is_valid_arxiv_id(arxiv_id):
                return arxiv_id.strip()

        # 优先级2: Markdown 正文
        patterns = [
            r'arXiv:\s*(\d{4}\.\d{4,5}(v\d+)?)',
            r'arxiv:\s*(\d{4}\.\d{4,5}(v\d+)?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, markdown, re.IGNORECASE)
            if match:
                arxiv_id = match.group(1).strip()
                if self._is_valid_arxiv_id(arxiv_id):
                    return arxiv_id

        return ""

    def _extract_title(self, doc: fitz.Document) -> str:
        """
        提取标题 - 参考paper2md最佳实践
        优先级：
        1. PDF 元数据 (/Title, XMP dc:title)
        2. 字体大小启发式（第一页、第二页）
        3. 文本行分析
        4. 文件名回退
        """
        # 方法1：PDF 元数据
        title = self._extract_title_from_metadata(doc)
        if title and len(title) > 10 and not self._is_suspicious_title(title):
            return title

        # 方法2：字体大小启发式
        for page_idx in range(min(2, len(doc))):  # 尝试前两页
            title = self._extract_title_by_font_size(doc[page_idx])
            if title and len(title) > 10:
                return title

        # 方法3：文本行分析
        if len(doc) > 0:
            title = self._extract_title_from_text(doc[0])
            if title:
                return title

        # 方法4：文件名回退（由调用者处理）
        return doc.metadata.get('title', '') or 'Unknown'

    def _extract_title_from_metadata(self, doc: fitz.Document) -> str:
        """从 PDF 元数据提取标题"""
        # PDF Info dict
        title = doc.metadata.get('title', '')
        if title and len(title) > 5:
            return title.strip()

        # XMP 元数据（如果有的话）
        try:
            if hasattr(doc, 'xref_xml_metadata'):
                xmp = doc.xref_xml_metadata()
                if xmp:
                    import re
                    match = re.search(r'<dc:title>.*?<rdf:li[^>]*>(.*?)</rdf:li>', xmp, re.DOTALL | re.IGNORECASE)
                    if match:
                        return match.group(1).strip()
        except:
            pass

        return ""

    def _is_suspicious_title(self, title: str) -> bool:
        """检测可疑的标题（可能是元数据错误）"""
        low = title.lower().strip()
        suspicious = [
            'untitled', 'title', 'document', 'paper', 'article',
            'microsoft word', 'latex', 'tex', 'pdf',
        ]
        if low in suspicious:
            return True
        # 检查是否主要是数字
        digit_ratio = sum(c.isdigit() for c in title) / max(len(title), 1)
        if digit_ratio > 0.5:
            return True
        return False

    def _extract_title_from_text(self, page) -> str:
        """从页面文本分析提取标题"""
        text = page.get_text()
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        title_lines = []
        for line in lines[:15]:
            if self._looks_like_non_title(line):
                continue
            title_lines.append(line)
            if len(title_lines) >= 3:
                break

        if title_lines:
            return ' '.join(title_lines)
        return ""

    def _looks_like_non_title(self, text: str) -> bool:
        """判断是否看起来不像标题"""
        low = text.lower()

        # 太短
        if len(text) < 5:
            return True

        # 页眉关键词
        header_keywords = [
            'downloaded', 'redistribution', 'copyright', 'editorial',
            'sciencedirect', 'elsevier', 'springer', 'ieee', 'acm', 'siam',
            'procedia', 'available online', 'www.', 'http://', 'https://',
            'peer-review', 'journal of', 'vol.', 'pp.',
            'abstract', 'keywords', 'introduction', 'contents',
            'received', 'accepted', 'published',
            'arxiv:', 'arxiv.org',  # arXiv 标识
        ]
        for kw in header_keywords:
            if kw in low:
                return True

        # arXiv 格式：[cs.LG], [math.NA] 等
        if re.match(r'^\[([a-z]+\.)*[a-z]+\]', low):
            return True

        # 邮箱
        if '@' in text:
            return True

        # 纯数字
        if text.isdigit():
            return True

        # 章节标题
        section_patterns = [
            r'^\d+\.\s+[A-Z]',  # "1. Introduction"
            r'^abstract$',
            r'^introduction$',
            r'^keywords$',
        ]
        for pattern in section_patterns:
            if re.match(pattern, low, re.IGNORECASE):
                return True

        return False

    def _extract_title_by_font_size(self, page) -> str:
        """
        使用字体大小提取标题
        参考 paper2md: 计算正文字体中位数，标题要明显大于正文
        """
        try:
            blocks = page.get_text("dict")["blocks"]

            # 收集所有文本行
            text_lines = []
            all_font_sizes = []

            for block in blocks:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    text = ""
                    max_font = 0
                    y_pos = line.get("bbox", (0, 0, 0, 0))[1]

                    for span in line.get("spans", []):
                        text += span.get("text", "")
                        font_size = span.get("size", 0)
                        if font_size > max_font:
                            max_font = font_size

                    text = text.strip()
                    if text and max_font > 0:
                        text_lines.append({
                            "text": text,
                            "font_size": max_font,
                            "y_pos": y_pos
                        })
                        all_font_sizes.append(max_font)

            if not text_lines:
                return ""

            # 计算正文字体大小（中位数）
            import statistics
            body_font_size = statistics.median(all_font_sizes)

            # 标题阈值：比正文大至少2个点
            title_threshold = body_font_size + 2

            # 页眉关键词（即使字体大也要跳过）
            header_keywords = [
                'sciencedirect', 'elsevier', 'springer', 'ieee', 'acm', 'siam',
                'procedia', 'available online', 'www.', 'downloaded', 'copyright',
                'vol.', 'pp.', 'editorial', 'journal of',
                'arxiv:', 'arxiv.org', '[cs.', '[math.', '[stat.',  # arXiv 标识
            ]

            # 页面上半部分阈值
            page_height = page.rect.height
            top_threshold = page_height * 0.4

            # 收集标题候选（字体大于阈值且在页面上半部分）
            title_candidates = []
            for line in text_lines:
                # 字体要足够大
                if line["font_size"] < title_threshold:
                    continue
                # 要在页面上半部分
                if line["y_pos"] > top_threshold:
                    continue

                text = line["text"]
                low = text.lower()

                # 检查是否是页眉
                is_header = any(kw in low for kw in header_keywords)
                if is_header:
                    continue

                # 其他过滤
                if self._looks_like_non_title(text):
                    continue

                title_candidates.append(line)

            if title_candidates:
                # 按字体大小排序，优先取最大的字体
                title_candidates.sort(key=lambda x: (-x["font_size"], x["y_pos"]))
                # 取字体最大的前1-3行作为标题
                max_font = title_candidates[0]["font_size"]
                title_parts = []
                for c in title_candidates:
                    # 只取字体接近最大值的行
                    if c["font_size"] >= max_font * 0.95:
                        title_parts.append(c["text"])
                    if len(title_parts) >= 3:
                        break
                return ' '.join(title_parts)

        except Exception as e:
            print(f"字体大小提取失败: {e}")

        return ""

    def _extract_doi(self, doc: fitz.Document, first_page_text: str = None) -> str:
        """
        提取 DOI

        来源优先级：
        1. PDF 元数据 (/doi)
        2. 首页正文中的 DOI 格式

        Returns:
            DOI 字符串（如 "10.1234/abc123"），未找到返回空字符串
        """
        # 方法1: PDF 元数据
        doi = doc.metadata.get('doi', '')
        if doi and self._is_valid_doi(doi):
            return doi.strip().lower()

        # 方法2: 从首页文本中搜索
        if first_page_text is None and len(doc) > 0:
            first_page_text = doc[0].get_text()

        if first_page_text:
            # 常见 DOI 格式（优先匹配直接的 10. 格式，这是最通用的）
            patterns = [
                r'\b(10\.\d{4,}/[^\s,;)\]]+)',  # 直接的 DOI 格式（最常见）
                r'https?://doi\.org/(10\.\d{4,}/[^\s,;)\]]+)',  # https://doi.org/10.xxxx/xxx
                r'https?://dx\.doi\.org/(10\.\d{4,}/[^\s,;)\]]+)',
                r'DOI:\s*(10\.\d{4,}/[^\s,;)\]]+)',  # DOI: 10.xxxx/xxx
                r'doi:\s*(10\.\d{4,}/[^\s,;)\]]+)',
            ]

            for pattern in patterns:
                match = re.search(pattern, first_page_text, re.IGNORECASE)
                if match:
                    doi = match.group(1).strip()
                    # 清理末尾的标点（双重保险）
                    doi = re.sub(r'[.,;)\]]+$', '', doi)
                    if self._is_valid_doi(doi):
                        return doi.lower()

        return ""

    def _extract_arxiv_id(self, doc: fitz.Document, first_page_text: str = None) -> str:
        """
        提取 arXiv ID

        来源优先级：
        1. PDF 元数据
        2. 首页正文中的 arXiv 格式

        Returns:
            arXiv ID（如 "2301.12345"），未找到返回空字符串
        """
        # 方法1: PDF 元数据
        for key in ['arxiv_id', 'arxiv', 'eprint']:
            arxiv_id = doc.metadata.get(key, '')
            if arxiv_id and self._is_valid_arxiv_id(arxiv_id):
                return arxiv_id.strip()

        # 方法2: 从首页文本中搜索
        if first_page_text is None and len(doc) > 0:
            first_page_text = doc[0].get_text()

        if first_page_text:
            # arXiv ID 格式
            patterns = [
                r'arXiv:\s*(\d{4}\.\d{4,5}(v\d+)?)',  # arXiv:2301.12345 或 arXiv:2301.12345v2
                r'arxiv:\s*(\d{4}\.\d{4,5}(v\d+)?)',
                r'arXiv:\s*([a-z-]+/\d{7}(v\d+)?)',  # 旧格式：arXiv:hep-th/9901001
                r'arxiv:\s*([a-z-]+/\d{7}(v\d+)?)',
            ]

            for pattern in patterns:
                match = re.search(pattern, first_page_text, re.IGNORECASE)
                if match:
                    arxiv_id = match.group(1).strip()
                    if self._is_valid_arxiv_id(arxiv_id):
                        return arxiv_id

        return ""

    def _is_valid_doi(self, doi: str) -> bool:
        """验证 DOI 格式是否有效"""
        if not doi or len(doi) < 6:
            return False
        # DOI 必须以 10. 开头
        if not doi.lower().startswith('10.'):
            return False
        # 必须包含 /
        if '/' not in doi:
            return False
        return True

    def _is_valid_arxiv_id(self, arxiv_id: str) -> bool:
        """验证 arXiv ID 格式是否有效"""
        if not arxiv_id or len(arxiv_id) < 5:
            return False
        # 新格式：2301.12345
        if re.match(r'^\d{4}\.\d{4,5}(v\d+)?$', arxiv_id):
            return True
        # 旧格式：hep-th/9901001
        if re.match(r'^[a-z-]+/\d{7}(v\d+)?$', arxiv_id, re.IGNORECASE):
            return True
        return False

    def _extract_authors(self, doc: fitz.Document) -> List[str]:
        """提取作者 - 改进版"""
        first_page = doc[0]
        text = first_page.get_text()
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        authors = []

        # 方法1: 从 PDF 元数据获取
        if doc.metadata.get('author'):
            meta_authors = [a.strip() for a in doc.metadata['author'].split(',')]
            # 检查是否像人名（不是机构名）
            for a in meta_authors:
                if len(a) > 2 and not any(x in a.lower() for x in ['university', 'institute', 'lab', 'department', 'dept', 'college', 'school']):
                    authors.append(a)
            if authors:
                return authors[:10]

        # 方法2: 查找作者模式
        # 作者通常在标题之后，摘要之前
        title_found = False
        for i, line in enumerate(lines[:15]):
            # 跳过期刊标识
            if any(x in line.lower() for x in ['downloaded', 'redistribution', 'siam', 'ieee', 'acm']):
                continue

            # 检测作者名模式
            # 模式1: "LastName, FirstName" 或 "FirstName LastName"
            # 模式2: 多个作者用逗号或 "and" 分隔

            # 跳过机构行
            if any(x in line.lower() for x in ['university', 'institute', 'lab', 'department', 'dept', 'college', 'school', '@', 'email']):
                continue

            # 跳过摘要、引言等标题
            if any(x in line.lower() for x in ['abstract', 'introduction', 'keywords', 'key words']):
                break

            # 可能是作者行
            # 检查是否有名字特征（首字母大写，包含空格）
            if ' ' in line and len(line) < 100 and len(line) > 5:
                # 检查是否像人名
                words = line.split()
                if len(words) >= 2 and len(words) <= 10:
                    # 检查每个词首字母是否大写（英文名特征）
                    name_like = sum(1 for w in words if w[0].isupper() or w[0].isdigit())
                    if name_like >= len(words) * 0.5:
                        # 可能是作者行，尝试分割
                        # 处理 "A, B, and C" 或 "A and B" 格式
                        import re
                        # 分割作者
                        parts = re.split(r',\s*(?:and\s+)?|\s+and\s+', line)
                        for p in parts:
                            p = p.strip()
                            if p and len(p) > 2:
                                # 检查不是机构
                                if not any(x in p.lower() for x in ['university', 'institute', 'lab', 'dept']):
                                    authors.append(p)

        return authors[:10]

    def _extract_abstract(self, full_text: str) -> str:
        """提取摘要 - 改进版"""
        text_lower = full_text.lower()

        # 常见的摘要标记
        abstract_markers = ['abstract', 'abstract:', 'a b s t r a c t', 'summary', '摘要']

        for marker in abstract_markers:
            idx = text_lower.find(marker)
            if idx == -1:
                continue

            start = idx + len(marker)

            # 跳过冒号和空格
            while start < len(full_text) and full_text[start] in ': \n\t':
                start += 1

            # 查找摘要结束位置
            end = len(full_text)
            end_markers = [
                '\n1 introduction', '\n1. introduction', '\nintroduction',
                '\n1 ', '\nkeywords', '\nkey words', '\n关键词',
                '\n\n\n\n'  # 多个空行
            ]

            for end_marker in end_markers:
                marker_idx = text_lower.find(end_marker, start)
                if marker_idx != -1 and marker_idx < end:
                    end = marker_idx

            abstract = full_text[start:end].strip()

            # 清理摘要
            # 移除开头的数字（页码等）
            lines = abstract.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                # 跳过空行
                if not line:
                    continue
                # 跳过纯数字行或过短行
                if line.isdigit() or len(line) < 20:
                    continue
                # 跳过期刊标识
                if any(x in line.lower() for x in ['downloaded', 'redistribution', 'siam']):
                    continue
                cleaned_lines.append(line)

            if cleaned_lines:
                abstract = ' '.join(cleaned_lines)
                return abstract[:3000]

        # 如果找不到摘要，返回前 1000 字符
        return full_text[:1000]

    def _extract_sections(self, full_text: str) -> Dict[str, str]:
        """提取章节"""
        sections = {}

        section_patterns = [
            ('introduction', r'\d+\s+introduction'),
            ('method', r'\d+\s+method'),
            ('methods', r'\d+\s+methods'),
            ('approach', r'\d+\s+approach'),
            ('experiment', r'\d+\s+experiment'),
            ('experiments', r'\d+\s+experiments'),
            ('results', r'\d+\s+results'),
            ('discussion', r'\d+\s+discussion'),
            ('conclusion', r'\d+\s+conclusion'),
            ('related work', r'\d+\s+related'),
        ]

        text_lower = full_text.lower()
        positions = []

        for section_name, pattern in section_patterns:
            for marker in [f"\n{section_name}", f"\n\n{section_name}"]:
                idx = text_lower.find(marker)
                if idx != -1:
                    positions.append((idx, section_name))
                    break

        positions.sort(key=lambda x: x[0])

        for i, (pos, section_name) in enumerate(positions):
            if i + 1 < len(positions):
                end_pos = positions[i + 1][0]
            else:
                end_pos = len(full_text)

            content = full_text[pos:end_pos].strip()
            sections[section_name] = content[:3000]

        return sections


class LLMConceptExtractor:
    """
    LLM 概念抽取器

    使用 LLM 从论文全文中提取动态层级的概念树
    """

    def __init__(self):
        """
        初始化
        """
        pass  # 使用统一的 mkg.llm 模块

    def _stage1_summarize(self, paper_content: PaperContent) -> dict:
        """
        Stage 1: 论文总结
        目标：理解论文，区分背景概念和核心贡献
        """
        from mkg.llm import generate

        prompt = STAGE1_SUMMARY_PROMPT.format(
            title=paper_content.title,
            authors=', '.join(paper_content.authors[:5]) if paper_content.authors else 'Unknown',
            abstract=paper_content.abstract[:1000] if paper_content.abstract else '',
            body=paper_content.full_text[:50000]
        )

        response = generate(
            prompt=prompt,
            system_prompt="You are a senior academic literature analyst with expertise in identifying the precise contribution boundaries of research papers."
        )
        return self._parse_stage1_response(response)

    def _parse_stage1_response(self, response: str) -> dict:
        """解析 Stage 1 响应"""
        import json
        import re

        try:
            json_match = re.search(r'```json\s*(.+?)\s*```', response, re.DOTALL)
            json_str = json_match.group(1) if json_match else response.strip()
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Stage 1 解析失败: {e}")
            return {
                "one_sentence_summary": "",
                "research_context": {},
                "core_contributions": [],
                "methodology_summary": {},
                "results_summary": {},
                "background_concepts": [],
                "novel_concepts": []
            }

    def _stage2_extract(self, summary: dict, existing_concepts: str = "") -> dict:
        """
        Stage 2: 核心概念提取
        目标：基于 Stage 1 摘要，只提取核心贡献对应的概念树
        """
        import json
        from mkg.llm import generate

        # 构建已有图谱部分
        existing_section = ""
        if existing_concepts and existing_concepts != "（图谱为空）":
            existing_section = EXISTING_GRAPH_SECTION.format(existing_tree=existing_concepts)

        prompt = STAGE2_EXTRACTION_PROMPT.format(
            summary_json=json.dumps(summary, ensure_ascii=False, indent=2),
            existing_graph_section=existing_section
        )

        response = generate(
            prompt=prompt,
            system_prompt="You are an academic knowledge graph construction expert. Build a refined concept tree based on the paper summary."
        )
        return self._parse_stage2_response(response)

    def _parse_stage2_response(self, response: str) -> dict:
        """解析 Stage 2 响应"""
        import json
        import re

        try:
            json_match = re.search(r'```json\s*(.+?)\s*```', response, re.DOTALL)
            json_str = json_match.group(1) if json_match else response.strip()
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"Stage 2 解析失败: {e}")
            return {
                "paper_summary": "",
                "concept_tree": {},
                "methodology": "",
                "datasets": [],
                "metrics": []
            }

    def extract(self, paper_content: PaperContent, existing_concepts: str = "") -> LLMExtractedContent:
        """
        从论文内容提取概念树和结构化信息（两阶段架构）

        Stage 1: 论文总结 - 理解论文，区分背景和贡献
        Stage 2: 核心提取 - 基于摘要构建概念树
        """
        # Stage 1: 总结（理解论文）
        summary = self._stage1_summarize(paper_content)

        # Stage 2: 提取核心（构建概念树）
        extraction = self._stage2_extract(summary, existing_concepts)

        # 合并结果
        concept_tree = self._build_concept_tree(extraction.get('concept_tree', {}))

        # 获取 results_summary 中的数据集和指标
        results_summary = summary.get('results_summary', {})

        return LLMExtractedContent(
            title=summary.get('one_sentence_summary', paper_content.title),
            authors=paper_content.authors,
            abstract=paper_content.abstract,
            research_questions=[],
            contributions=[c.get('claim', '') for c in summary.get('core_contributions', [])],
            concept_tree=concept_tree,
            methodology=extraction.get('methodology'),
            datasets=results_summary.get('datasets', []),
            metrics=results_summary.get('metrics', []),
            raw_response="",  # Two-stage extraction doesn't preserve raw response
            # 新增字段
            one_sentence_summary=summary.get('one_sentence_summary'),
            research_context=summary.get('research_context'),
            background_concepts=summary.get('background_concepts', []),
            novel_concepts=summary.get('novel_concepts', [])
        )

    def _build_extraction_prompt(self, paper_content: PaperContent, existing_concepts: str = "") -> str:
        """
        构建概念提取 Prompt（优化版）

        核心设计：
        - 让 LLM 理解论文的层次结构
        - 提取概念间的包含关系（父子关系）
        - 支持多标签归属
        - 包含清晰的判断标准、few-shot 示例和自检清单
        - 支持已有概念上下文，实现智能概念匹配
        """
        return f"""
你是一名学术知识图谱构建助手。请从这篇论文中提取概念层级结构和研究信息。

**重要：所有概念名称必须使用中文！**

## 论文信息
标题：{paper_content.title}
作者：{', '.join(paper_content.authors[:3]) if paper_content.authors else 'Unknown'}
摘要：{paper_content.abstract[:500]}...

## 论文全文
{paper_content.full_text[:50000]}

{self._build_existing_concepts_section(existing_concepts)}

---

## 第一部分：层级判断标准

在提取概念时，请严格按照以下标准判断概念所属层级：

| 层级 | 英文名 | 判断标准 | 典型示例 |
|------|--------|----------|----------|
| **领域** | field | 一个广泛的学科领域，通常是一个完整的研究方向或学科分支 | 人工智能、机器学习、计算机视觉、自然语言处理 |
| **方向** | direction | 领域内的具体研究方向，通常有独立的研究社区和会议 | 强化学习、目标检测、图神经网络、知识图谱 |
| **方法** | method | 解决特定问题的具体方法或算法框架，有明确的技术路线 | Transformer、PPO算法、YOLO、BERT |
| **技术** | technique | 实现方法的具体技术手段、技巧或组件 | 注意力机制、梯度裁剪、残差连接、位置编码 |
| **细节** | detail | 算法的具体实现细节、超参数或设计选择 | 学习率0.001、3层MLP、隐藏维度256 |

**判断口诀：**
- 能独立成为一门课的 → field
- 能独立发论文的方向 → direction
- 有名字的方法框架 → method
- 方法里的具体技巧 → technique
- 数字和参数配置 → detail

---

## 第二部分：Few-shot 示例

以下是正确提取的示例（假设论文是关于多智能体强化学习的）：

**输入论文概要：** 论文提出了一个名为"Attention-QMIX"的新算法，用于解决多智能体协作问题...

**正确输出：**
```json
{{
    "title": "Attention-QMIX: 基于注意力机制的多智能体强化学习算法",
    "authors": ["张三", "李四"],
    "abstract": "摘要内容...",
    "research_questions": [
        "如何解决多智能体协作中的信用分配问题",
        "如何处理大规模智能体环境下的可扩展性"
    ],
    "contributions": [
        "提出了一种新的注意力机制用于智能体间通信",
        "在SMAC基准测试上取得了SOTA性能"
    ],
    "concept_tree": {{
        "concept": "人工智能",
        "category": "field",
        "confidence": 0.98,
        "children": [
            {{
                "concept": "机器学习",
                "category": "field",
                "confidence": 0.95,
                "children": [
                    {{
                        "concept": "强化学习",
                        "category": "direction",
                        "confidence": 0.95,
                        "children": [
                            {{
                                "concept": "多智能体强化学习",
                                "category": "direction",
                                "confidence": 0.92,
                                "children": [
                                    {{
                                        "concept": "值分解方法",
                                        "category": "method",
                                        "confidence": 0.88,
                                        "children": [
                                            {{
                                                "concept": "QMIX算法",
                                                "category": "method",
                                                "confidence": 0.85,
                                                "children": []
                                            }},
                                            {{
                                                "concept": "注意力机制",
                                                "category": "technique",
                                                "confidence": 0.82,
                                                "children": []
                                            }}
                                        ]
                                    }}
                                ]
                            }}
                        ]
                    }}
                ]
            }}
        ]
    }},
    "methodology": "采用值分解框架结合注意力机制，通过Q值混合网络实现协作决策",
    "datasets": ["SMAC", "Google Research Football"],
    "metrics": ["胜率", "平均回报", "样本效率"]
}}
```

**常见错误示例：**
❌ 错误：把"强化学习"标为 method → 应该是 direction（有独立研究社区）
❌ 错误：把"注意力机制"标为 direction → 应该是 technique（是实现技巧）
❌ 错误：概念名保留英文"Transformer" → 应翻译为"Transformer"（专有名词可保留）或"变换器"

---

## 第三部分：任务要求

### 1. 提取研究问题（1-3 个）
论文试图解决什么核心问题？用简洁的中文表述。

### 2. 提取主要贡献（1-5 个）
论文的创新点是什么？聚焦于方法、理论或实验上的贡献。

### 3. 构建概念层级树（核心任务）
从论文中提取概念，并组织成树状层级结构。

**构建原则：**
- 根节点应该是宏观研究领域（如"人工智能"、"计算机科学"）
- 按照领域→方向→方法→技术→细节的层次展开
- 每个节点的 confidence 表示提取的置信度（0-1）
- 同一概念可以出现在不同分支下（如果论文涉及多个方向）
- **所有概念名称必须翻译成中文**（专有名词如Transformer可保留）

### 4. 提取方法论
论文使用的核心方法是什么？用1-2句话概述。

### 5. 提取数据集
论文使用了哪些数据集或实验环境？

### 6. 提取评估指标
论文使用了哪些评估指标？

---

## 第四部分：输出格式

请严格按照以下 JSON 格式输出：

```json
{{
    "title": "论文标题",
    "authors": ["作者1", "作者2"],
    "abstract": "摘要...",
    "research_questions": ["问题1", "问题2"],
    "contributions": ["贡献1", "贡献2"],
    "concept_tree": {{
        "concept": "根概念（中文）",
        "category": "field",
        "confidence": 0.95,
        "children": [
            {{
                "concept": "子概念（中文）",
                "category": "direction",
                "confidence": 0.9,
                "children": [...]
            }}
        ]
    }},
    "methodology": "方法描述",
    "datasets": ["数据集1", "数据集2"],
    "metrics": ["指标1", "指标2"]
}}
```

---

## 第五部分：自检清单

在输出前，请检查以下几点：

✓ **层级正确性**：每个概念的 category 是否符合判断标准？
✓ **层级一致性**：父节点的层级是否比子节点更宏观？（field > direction > method > technique > detail）
✓ **中文翻译**：是否所有概念都已翻译成中文？
✓ **置信度合理**：confidence 是否反映了提取的确定性？
✓ **树结构完整**：concept_tree 是否有合理的根节点和层级深度？

---

**只输出 JSON，不要其他内容。开始提取！**
"""

    def _build_existing_concepts_section(self, existing_concepts: str) -> str:
        """构建已有概念参考部分"""
        if not existing_concepts or existing_concepts == "（图谱为空）":
            return ""

        return f"""---

## 已有概念树（参考）

当前知识图谱中已有以下概念结构，新概念请尽量归类到合适的位置：

{existing_concepts}

**重要规则：**
1. 如果新提取的概念已存在于上述树中，请使用相同的概念名和正确的父节点路径
2. 如果新概念是已有概念的子概念，请放在正确位置（如"卷积神经网络"应放在"人工智能→机器学习→深度学习"下）
3. 只有当概念确实是新的研究领域时，才创建新的根概念
"""

    def _parse_response(self, response: str, original_content: PaperContent) -> LLMExtractedContent:
        """解析 LLM 响应"""
        import json
        import re

        try:
            # 尝试提取 JSON（可能包含在代码块中）
            json_match = re.search(r'```json\s*(.+?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = response.strip()

            data = json.loads(json_str)

            # 构建概念树
            concept_tree = self._build_concept_tree(data.get('concept_tree', {}))

            return LLMExtractedContent(
                title=data.get('title', original_content.title),
                authors=data.get('authors', original_content.authors),
                abstract=data.get('abstract', original_content.abstract),
                research_questions=data.get('research_questions', []),
                contributions=data.get('contributions', []),
                concept_tree=concept_tree,
                methodology=data.get('methodology'),
                datasets=data.get('datasets', []),
                metrics=data.get('metrics', []),
                raw_response=response
            )

        except Exception as e:
            print(f"解析 LLM 响应失败：{e}")
            # 回退到基础解析
            return LLMExtractedContent(
                title=original_content.title,
                authors=original_content.authors,
                abstract=original_content.abstract,
                research_questions=[],
                contributions=[],
                concept_tree=self._create_fallback_concept_tree(original_content),
                methodology=None,
                datasets=[],
                metrics=[],
                raw_response=response
            )

    def _build_concept_tree(self, data: dict) -> ConceptTree:
        """递归构建概念树（支持双语格式）"""
        if not data or 'concept' not in data:
            return None

        # 使用 from_dict 方法处理双语格式
        return ConceptTree.from_dict(data)

    def _create_fallback_concept_tree(self, content: PaperContent) -> ConceptTree:
        """回退方案：从标题和摘要创建简单的概念树"""
        import re

        # 从标题提取关键词
        keywords = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content.title)
        keywords = [k.lower() for k in keywords if len(k) > 3]

        # 创建扁平结构
        root = ConceptTree(
            concept="Research",
            category="field",
            confidence=0.5
        )

        for kw in keywords[:5]:
            root.children.append(ConceptTree(
                concept=kw,
                category="method",
                confidence=0.5
            ))

        return root
