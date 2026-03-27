"""
PDF 解析模块 - 使用 LLM 解析学术论文

新设计：
- 使用 PyMuPDF 提取全文文本
- 发送全文给 LLM，提取结构化信息：
  - 元数据（标题、作者、摘要）
  - 研究问题/贡献
  - 概念层级树（动态分层）
  - 方法论、数据集、评估指标等
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field


STAGE1_SUMMARY_PROMPT = """<s>
你是一位学术论文审稿人。请对以下论文进行结构化总结。
你的目标不是复述论文内容，而是回答一个核心问题：
**这篇论文对学术界的独特贡献是什么？它做了什么别人没做过的事？**
</s>

<paper>
<title>{title}</title>
<authors>{authors}</authors>
<abstract>{abstract}</abstract>
<body>{body}</body>
</paper>

<task>
请输出以下 JSON 结构：

{{
  "one_sentence_summary": "用一句话概括这篇论文（不超过50字）",

  "research_context": {{
    "field": "所属大领域",
    "direction": "所属研究方向",
    "existing_gap": "论文试图填补的研究空白（1-2句话）"
  }},

  "core_contributions": [
    {{
      "type": "new_method | new_framework | new_dataset | new_finding | improvement | theoretical",
      "claim": "贡献的具体描述（1句话）",
      "novelty": "与已有工作相比，新在哪里（1句话）"
    }}
  ],

  "methodology_summary": {{
    "approach": "核心方法的一句话概述",
    "key_components": ["方法中最关键的2-3个技术组件"],
    "baselines": ["对比的基线方法"]
  }},

  "results_summary": {{
    "datasets": ["使用的数据集"],
    "metrics": ["评估指标"],
    "main_finding": "最重要的实验结论（1句话）"
  }},

  "background_concepts": ["论文提及但非其贡献的已有概念"],
  "novel_concepts": ["论文首次提出或深入探讨的概念"]
}}
</task>

<rules>
关键判断规则：
- "background_concepts" vs "novel_concepts" 的区分是最重要的。
  判断标准：如果这篇论文不存在，这个概念还会被学术界广泛认知吗？
  会 → background。不会 → novel。
- core_contributions 通常只有 1-3 个。超过 5 个说明没有区分"贡献"和"论文提到的东西"。
- 所有内容使用中文。国际通用专有名词（Transformer、BERT）可保留英文。
</rules>

只输出 JSON，不要其他内容。"""


STAGE2_EXTRACTION_PROMPT = """<s>
你是一位学术知识图谱构建专家。你的任务是基于论文总结，构建一棵精炼的概念树。

关键原则——区分"锚点"和"贡献"：
- **锚点路径**：从根节点到论文核心贡献的最短路径。只需存在，不展开子树。作用是定位"这篇论文属于哪里"。
- **贡献子树**：论文真正贡献的概念。展开详细子节点。这些是图谱中因为这篇论文而新增的知识。
</s>

<paper_summary>
{summary_json}
</paper_summary>

{existing_graph_section}

<taxonomy>
层级定义（基于"最小可发表单元"原则）：
- field：能建大学院系 → 如"人工智能"
- direction：有专门学术会议 → 如"多智能体强化学习"
- subdirection：综述论文的独立章节 → 如"值分解方法"
- task：可表述为"给定X求Y" → 如"信用分配问题"
- method：有名字的可复现算法 → 如"QMIX"
- technique：方法内部的组件/技巧 → 如"注意力加权混合"

判定：五步 yes/no 排除法：
1. 能不能围绕它建一个大学院系？→ field
2. 有没有专门的学术会议或期刊专题？→ direction
3. 会不会在该方向的综述论文中作为独立章节？→ subdirection
4. 能不能表述成"给定X，求解/优化Y"的问题定义？→ task
5. 有没有具体名字和可复现的算法流程？→ method
6. 以上都不是 → technique
</taxonomy>

<task>
请构建概念树，分三步执行：

**第一步：画锚点路径**
从 paper_summary.research_context 提取 field → direction 的最短路径。
这些节点标记 "is_anchor": true，不展开子树。

**第二步：在锚点末端展开贡献子树**
从 paper_summary.core_contributions 和 novel_concepts 提取概念。
标记 "is_anchor": false。

**第三步：标注贡献类型**
对每个核心节点标注 contribution_role：
- "proposed"：论文首次提出
- "improved"：论文改进了已有方法
- "applied"：已有方法应用于新场景
- "analyzed"：对已有概念的深入分析
</task>

<confidence_scale>
| 分数 | 含义 |
|------|------|
| 0.90-1.00 | 论文明确讨论，层级无歧义 |
| 0.75-0.89 | 论文涉及，层级基本确定 |
| 0.60-0.74 | 从论文内容合理推断 |
| < 0.60 | 不要输出 |
</confidence_scale>

<output_format>
输出 JSON：

{{
  "paper_summary": "one_sentence_summary 的内容",
  "concept_tree": {{
    "concept": "根概念（中文）",
    "category": "field",
    "is_anchor": true,
    "children": [
      {{
        "concept": "方向概念（中文）",
        "category": "direction",
        "is_anchor": true,
        "children": [
          {{
            "concept": "核心贡献概念",
            "category": "subdirection|task|method|technique",
            "is_anchor": false,
            "contribution_role": "proposed|improved|applied|analyzed",
            "confidence": 0.60-1.00,
            "children": [...]
          }}
        ]
      }}
    ]
  }},
  "methodology": "核心方法概述",
  "datasets": ["数据集"],
  "metrics": ["指标"]
}}

节点数量指引：
- 锚点路径：2-4 个节点
- 贡献子树：4-10 个节点
- 总计：6-15 个。超过 15 个 → 你在提取背景而非核心。
</output_format>

只输出 JSON，不要其他内容。"""

EXISTING_GRAPH_SECTION = """<existing_graph>
当前知识图谱中已有的概念。请优先复用已有节点作为锚点，避免重复创建。
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
    concept: str
    category: str = "method"
    confidence: float = 0.9
    is_anchor: bool = False  # 新增：是否为锚点节点
    contribution_role: Optional[str] = None  # 新增: proposed/improved/applied/analyzed
    children: List['ConceptTree'] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        result = {
            'concept': self.concept,
            'category': self.category,
            'confidence': self.confidence,
            'is_anchor': self.is_anchor,
            'id': self._to_slug(self.concept)
        }
        if self.contribution_role:
            result['contribution_role'] = self.contribution_role
        if self.children:
            result['children'] = [child.to_dict() for child in self.children]
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'ConceptTree':
        """从字典构建 ConceptTree"""
        return cls(
            concept=data.get('concept', ''),
            category=data.get('category', 'method'),
            confidence=data.get('confidence', 0.9),
            is_anchor=data.get('is_anchor', False),
            contribution_role=data.get('contribution_role'),
            children=[cls.from_dict(c) for c in data.get('children', [])]
        )

    def _to_slug(self, text: str) -> str:
        """转换为 slug ID（支持中文）"""
        import re
        import hashlib

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
    """PDF 解析器 - 使用 PyMuPDF 提取文本"""

    def __init__(self):
        pass

    def parse(self, pdf_path: str) -> Optional[PaperContent]:
        """
        解析 PDF 文件（提取原始文本）

        Args:
            pdf_path: PDF 文件路径

        Returns:
            论文内容，解析失败返回 None
        """
        try:
            doc = fitz.open(pdf_path)

            # 提取元数据
            metadata = doc.metadata

            # 提取全文
            full_text = ""
            for page in doc:
                full_text += page.get_text()

            # 提取标题（通常是第一行）
            title = self._extract_title(doc)

            # 提取作者
            authors = self._extract_authors(doc)

            # 提取摘要
            abstract = self._extract_abstract(full_text)

            # 分章节
            sections = self._extract_sections(full_text)

            doc.close()

            return PaperContent(
                title=title,
                authors=authors,
                abstract=abstract,
                full_text=full_text,
                sections=sections,
                metadata=metadata
            )

        except Exception as e:
            print(f"PDF 解析失败：{e}")
            return None

    def extract_text(self, pdf_path: str) -> Optional[str]:
        """只提取纯文本（供 LLM 使用）"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()

            # 清理过长的文本（限制 token 数，大约 4 字符=1token）
            # 支持 200k token 的模型可以处理约 800k 字符
            if len(text) > 700000:  # 留有余量
                text = text[:700000] + "\n\n... [文本过长，已截断]"

            return text
        except Exception as e:
            print(f"文本提取失败：{e}")
            return None

    def _extract_title(self, doc: fitz.Document) -> str:
        """提取标题"""
        first_page = doc[0]
        text = first_page.get_text()

        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # 收集标题行
        title_lines = []

        for line in lines[:5]:
            # 跳过期刊标识行
            if any(x in line.lower() for x in ['downloaded', 'redistribution', 'siam', 'ieee', 'acm', 'vol.', 'pp.', 'copyright', 'editorial']):
                continue
            # 跳过过短的行（但保留可能是标题一部分的）
            if len(line) < 3:
                continue
            title_lines.append(line)
            # 如果遇到明显的标题结束标志
            if any(x in line.lower() for x in ['abstract', 'introduction', 'keywords']):
                break
            # 收集前几行作为标题
            if len(title_lines) >= 2:
                break

        if title_lines:
            # 合并标题行
            return ' '.join(title_lines)

        return doc.metadata.get('title', lines[0] if lines else 'Unknown')

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

    def __init__(self, api_client=None):
        """
        初始化

        Args:
            api_client: LLM API 客户端
        """
        self.api_client = api_client

    def _stage1_summarize(self, paper_content: PaperContent) -> dict:
        """
        Stage 1: 论文总结
        目标：理解论文，区分背景概念和核心贡献
        """
        prompt = STAGE1_SUMMARY_PROMPT.format(
            title=paper_content.title,
            authors=', '.join(paper_content.authors[:5]) if paper_content.authors else 'Unknown',
            abstract=paper_content.abstract[:1000] if paper_content.abstract else '',
            body=paper_content.full_text[:50000]
        )

        response = self.api_client.extract_concepts(prompt)
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

        # 构建已有图谱部分
        existing_section = ""
        if existing_concepts and existing_concepts != "（图谱为空）":
            existing_section = EXISTING_GRAPH_SECTION.format(existing_tree=existing_concepts)

        prompt = STAGE2_EXTRACTION_PROMPT.format(
            summary_json=json.dumps(summary, ensure_ascii=False, indent=2),
            existing_graph_section=existing_section
        )

        response = self.api_client.extract_concepts(prompt)
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
        if not self.api_client:
            raise ValueError("需要配置 LLM API 客户端")

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
        """递归构建概念树"""
        if not data or 'concept' not in data:
            return None

        tree = ConceptTree(
            concept=data['concept'],
            category=data.get('category', 'method'),
            confidence=data.get('confidence', 0.8),
            is_anchor=data.get('is_anchor', False),
            contribution_role=data.get('contribution_role')
        )

        for child_data in data.get('children', []):
            child_tree = self._build_concept_tree(child_data)
            if child_tree:
                tree.children.append(child_tree)

        return tree

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


# LLM API 客户端接口
class LLMClient:
    """LLM API 客户端接口"""

    def extract_concepts(self, prompt: str) -> str:
        """提取概念"""
        raise NotImplementedError


class LiteLLMClient(LLMClient):
    """统一 LLM 客户端，基于 LiteLLM 支持所有主流服务商

    支持的服务商：
    - openai: gpt-4o, gpt-4o-mini, gpt-4-turbo
    - anthropic: claude-sonnet-4-20250514, claude-3-5-sonnet
    - deepseek: deepseek-chat, deepseek-coder, deepseek-reasoner
    - minimax: abab6.5s-chat, abab6.5g-chat
    - zhipu: glm-4, glm-4-flash, glm-4-plus
    - moonshot: moonshot-v1-8k, moonshot-v1-32k
    - dashscope (阿里云): qwen-max, qwen-plus, qwen-turbo
    - openrouter: anthropic/claude-sonnet-4, openai/gpt-4o
    - gemini: gemini-2.0-flash, gemini-1.5-pro
    """

    # 服务商环境变量映射
    ENV_KEY_MAP = {
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'deepseek': 'DEEPSEEK_API_KEY',
        'minimax': 'MINIMAX_API_KEY',
        'zhipu': 'ZHIPU_API_KEY',
        'moonshot': 'MOONSHOT_API_KEY',
        'dashscope': 'DASHSCOPE_API_KEY',
        'openrouter': 'OPENROUTER_API_KEY',
        'gemini': 'GEMINI_API_KEY',
        'custom': 'CUSTOM_API_KEY',
    }

    def __init__(self, provider: str, api_key: str = None, model: str = None, base_url: str = None):
        """
        Args:
            provider: 服务商名称 (openai, deepseek, minimax, zhipu 等)
            api_key: API 密钥（可选，也可通过环境变量设置）
            model: 模型名称
            base_url: 自定义 API 地址（可选，一般不需要）
        """
        self.provider = provider
        self.model = model or self._get_default_model(provider)
        self.api_key = api_key

        # MiniMax 使用 Anthropic 兼容 API
        if provider == 'minimax' and not base_url:
            base_url = 'https://api.minimaxi.com/anthropic'
        self.base_url = base_url

        # 设置环境变量（LiteLLM 会自动读取）
        if api_key:
            env_key = self.ENV_KEY_MAP.get(provider, f'{provider.upper()}_API_KEY')
            import os
            os.environ[env_key] = api_key

    def _get_default_model(self, provider: str) -> str:
        """获取服务商的默认模型"""
        defaults = {
            'openai': 'gpt-5.4-mini',
            'anthropic': 'claude-3.5-sonnet-20250514',
            'deepseek': 'deepseek-v3.2',
            'minimax': 'minimax-m2.7',
            'zhipu': 'glm-5-turbo',
            'moonshot': 'moonshot-v1-8k',
            'dashscope': 'qwen3.5-plus',
            'openrouter': 'openai/gpt-5.4-mini',
            'gemini': 'gemini-3.1-flash',
        }
        return defaults.get(provider, 'gpt-5.4-mini')

    def _get_litellm_model(self) -> str:
        """转换为 LiteLLM 模型格式"""
        # MiniMax 使用 Anthropic 兼容 API
        if self.provider == 'minimax':
            return f"anthropic/{self.model}"

        # 自定义配置：根据 base_url 判断使用哪种格式
        if self.provider == 'custom':
            if self.base_url and 'anthropic' in self.base_url.lower():
                return f"anthropic/{self.model}"
            else:
                # 默认使用 OpenAI 格式
                return f"openai/{self.model}"

        # LiteLLM 格式：provider/model
        if '/' in self.model:
            return self.model  # 已经是正确格式
        return f"{self.provider}/{self.model}"

    def extract_concepts(self, prompt: str) -> str:
        """使用 LiteLLM 提取概念"""
        from litellm import completion
        import os

        model = self._get_litellm_model()

        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an academic knowledge graph builder. Extract concepts and their hierarchical relationships from research papers."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4096,
        }

        # 自定义 base_url（如代理或私有部署）
        if self.base_url:
            kwargs["api_base"] = self.base_url

        # 自定义配置需要显式传递 api_key
        if self.provider == 'custom':
            if self.api_key:
                kwargs["api_key"] = self.api_key

        response = completion(**kwargs)
        return response.choices[0].message.content

    def generate(self, prompt: str) -> str:
        """生成响应"""
        return self.extract_concepts(prompt)


class ClaudeCLIClient(LLMClient):
    """使用 Claude CLI 的客户端（利用 Claude Code 已配置的 API）"""

    def __init__(self, model: str = None):
        self.model = model  # None means use default model
        self._check_cli_available()

    def _check_cli_available(self):
        """检查 Claude CLI 是否可用"""
        import subprocess
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError("Claude CLI not available")
        except FileNotFoundError:
            raise RuntimeError("Claude CLI not found. Please install Claude Code first.")
        except Exception as e:
            raise RuntimeError(f"Claude CLI check failed: {e}")

    def extract_concepts(self, prompt: str) -> str:
        """使用 Claude CLI 提取概念"""
        return self.generate(prompt)

    def generate(self, prompt: str) -> str:
        """使用 Claude CLI 生成响应"""
        import subprocess
        import tempfile
        import os

        # 创建临时文件存储 prompt（避免命令行长度限制）
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(prompt)
            prompt_file = f.name

        try:
            # 构建命令
            cmd = ["claude", "-p"]
            if self.model:
                cmd.extend(["--model", self.model])

            # 从文件读取输入
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt_content = f.read()

            result = subprocess.run(
                cmd,
                input=prompt_content,
                capture_output=True,
                text=True,
                timeout=300,
                encoding='utf-8',
                errors='replace'
            )

            if result.returncode != 0:
                error_msg = result.stdout or result.stderr or "Unknown error"
                raise RuntimeError(f"Claude CLI error: {error_msg}")

            return result.stdout.strip()

        finally:
            # 清理临时文件
            if os.path.exists(prompt_file):
                os.unlink(prompt_file)
