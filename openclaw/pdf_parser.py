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


@dataclass
class PaperContent:
    """论文内容（原始文本）"""
    title: str
    authors: List[str]
    abstract: str
    full_text: str
    sections: Dict[str, str]
    metadata: Dict


@dataclass
class ConceptTree:
    """
    概念树结构

    示例结构:
    {
        "concept": "人工智能",
        "category": "field",
        "confidence": 0.95,
        "children": [
            {
                "concept": "机器学习",
                "category": "field",
                "confidence": 0.9,
                "children": [
                    {
                        "concept": "强化学习",
                        "category": "direction",
                        "confidence": 0.85,
                        "children": [
                            {
                                "concept": "多智能体强化学习",
                                "category": "direction",
                                "confidence": 0.8
                            }
                        ]
                    }
                ]
            }
        ]
    }
    """
    concept: str
    category: str
    confidence: float = 1.0
    children: List['ConceptTree'] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'concept': self.concept,
            'category': self.category,
            'confidence': self.confidence,
            'children': [child.to_dict() for child in self.children],
            'id': self._to_slug(self.concept)
        }

    def _to_slug(self, text: str) -> str:
        """转换为 slug ID"""
        import re
        slug = text.lower()
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        slug = slug.strip('-')
        return slug[:100]


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
        if lines:
            return lines[0]

        return doc.metadata.get('title', '')

    def _extract_authors(self, doc: fitz.Document) -> List[str]:
        """提取作者"""
        if doc.metadata.get('author'):
            return [a.strip() for a in doc.metadata['author'].split(',')]

        first_page = doc[0]
        text = first_page.get_text()
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        authors = []
        for i in range(1, min(4, len(lines))):
            line = lines[i]
            if ' ' in line and len(line) < 200:
                if any(x in line.lower() for x in ['university', 'institute', 'lab', 'dept']):
                    continue
                authors.append(line)

        return authors[:5]

    def _extract_abstract(self, full_text: str) -> str:
        """提取摘要"""
        text_lower = full_text.lower()

        keywords = ['abstract', 'abstract:', 'summary']
        for kw in keywords:
            idx = text_lower.find(kw)
            if idx != -1:
                start = idx + len(kw)
                end_markers = ['1 introduction', '1.', 'introduction', '\n\n\n']
                end = len(full_text)
                for marker in end_markers:
                    marker_idx = text_lower.find(marker, start)
                    if marker_idx != -1 and marker_idx < end:
                        end = marker_idx

                abstract = full_text[start:end].strip()
                abstract = '\n'.join([l for l in abstract.split('\n')
                                     if l.strip() and len(l.strip()) > 10])
                return abstract[:2000]

        return full_text[:500]

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

    def extract(self, paper_content: PaperContent) -> LLMExtractedContent:
        """
        从论文内容提取概念树和结构化信息

        Args:
            paper_content: 论文原始内容

        Returns:
            LLM 提取的结构化内容
        """
        if not self.api_client:
            raise ValueError("需要配置 LLM API 客户端")

        # 构建 prompt
        prompt = self._build_extraction_prompt(paper_content)

        # 调用 LLM
        response = self.api_client.extract_concepts(prompt)

        # 解析响应
        return self._parse_response(response, paper_content)

    def _build_extraction_prompt(self, paper_content: PaperContent) -> str:
        """
        构建概念提取 Prompt

        核心设计：
        - 让 LLM 理解论文的层次结构
        - 提取概念间的包含关系（父子关系）
        - 支持多标签归属
        """
        return f"""
你是一名学术知识图谱构建助手。请从这篇论文中提取概念层级结构和研究信息。

## 论文信息
标题：{paper_content.title}
作者：{', '.join(paper_content.authors[:3]) if paper_content.authors else 'Unknown'}
摘要：{paper_content.abstract[:500]}...

## 论文全文
{paper_content.full_text[:100000]}  # 限制长度，避免超出上下文

## 任务要求

### 1. 提取研究问题（1-3 个）
论文试图解决什么核心问题？

### 2. 提取主要贡献（1-5 个）
论文的创新点是什么？

### 3. 构建概念层级树（核心任务）
从论文中提取概念，并组织成树状层级结构。

**重要原则：**
- 根节点应该是最宏观的研究领域（如"人工智能"、"机器学习"）
- 子节点应该是更具体的研究方向、方法或技术
- 层级应该反映"包含关系"或"从属关系"
- 同一概念可以出现在不同分支下（如果论文涉及多个方向）

**层级示例：**
```
人工智能 (field)
└── 机器学习 (field)
    └── 强化学习 (direction)
        └── 多智能体强化学习 (direction)
            ├── MAPPO (method)
            └── QMIX (method)
```

**类别定义：**
- field: 大领域/学科（如"人工智能"、"机器学习"）
- direction: 研究方向（如"强化学习"、"计算机视觉"）
- method: 具体方法/算法（如"PPO"、"BERT"）
- technique: 技术细节（如"注意力机制"、"clip 机制"）
- detail: 实现细节/参数

### 4. 提取方法论
论文使用的核心方法是什么？

### 5. 提取数据集
论文使用了哪些数据集或实验环境？

### 6. 提取评估指标
论文使用了哪些评估指标？

## 输出格式

请输出严格的 JSON 格式：

```json
{{
    "title": "论文标题",
    "authors": ["作者 1", "作者 2"],
    "abstract": "摘要...",
    "research_questions": ["问题 1", "问题 2"],
    "contributions": ["贡献 1", "贡献 2"],
    "concept_tree": {{
        "concept": "根概念",
        "category": "field",
        "confidence": 0.95,
        "children": [
            {{
                "concept": "子概念",
                "category": "direction",
                "confidence": 0.9,
                "children": [...]
            }}
        ]
    }},
    "methodology": "方法描述",
    "datasets": ["数据集 1", "数据集 2"],
    "metrics": ["指标 1", "指标 2"]
}}
```

只输出 JSON，不要其他内容。
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
            confidence=data.get('confidence', 0.8)
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


class AnthropicClient(LLMClient):
    """Anthropic Claude 客户端"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def extract_concepts(self, prompt: str) -> str:
        """使用 Claude 提取概念"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text


class GoogleClient(LLMClient):
    """Google AI Studio 客户端"""

    def __init__(self, api_key: str):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def extract_concepts(self, prompt: str) -> str:
        """使用 Gemini 提取概念"""
        response = self.model.generate_content(prompt)
        return response.text


class OpenAICompatibleClient(LLMClient):
    """OpenAI 兼容 API 客户端（支持 DashScope、DeepSeek 等）"""

    def __init__(self, api_key: str, base_url: str = None, model: str = None):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = model or "qwen-plus"

    def extract_concepts(self, prompt: str) -> str:
        """使用 OpenAI 兼容 API 提取概念"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an academic knowledge graph builder. Extract concepts and their hierarchical relationships from research papers."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4096
        )
        return response.choices[0].message.content
