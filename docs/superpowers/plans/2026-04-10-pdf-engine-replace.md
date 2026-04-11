# PDF 提取引擎替换：PyMuPDF → OpenDataLoader-PDF

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 OpenDataLoader-PDF 替换 PyMuPDF 作为 PDF 文本提取的首选引擎，保留 PyMuPDF 作为 fallback。

**Architecture:** 在 `PDFParser` 类中新增 OpenDataLoader 提取路径，通过启动时 Java 可用性检测自动选择引擎。LLM 两阶段提取逻辑（`LLMConceptExtractor`）和所有 prompt 保持不变。

**Tech Stack:** Python, opendataloader-pdf, PyMuPDF (fallback), subprocess (Java detection)

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `requirements.txt` | 修改 | 添加 `opendataloader-pdf` 依赖 |
| `Dockerfile` | 修改 | 添加 Java 运行时 |
| `mkg/pdf_parser.py:1-18` | 修改 | 修改 imports，添加 `subprocess`、`json`、`tempfile` |
| `mkg/pdf_parser.py:419-1010` | 重写 | `PDFParser` 类：添加 OpenDataLoader 路径，保留 PyMuPDF fallback |
| `mkg/pdf_parser.py:1013+` | 保留 | `LLMConceptExtractor` 类完全不变 |

---

### Task 1: 添加依赖

**Files:**
- Modify: `requirements.txt`
- Modify: `Dockerfile`

- [ ] **Step 1: 添加 `opendataloader-pdf` 到 `requirements.txt`**

在 `requirements.txt` 的 `# PDF Processing` 部分，PyMuPDF 行下方添加 OpenDataLoader：

```diff
 # PDF Processing
 pymupdf>=1.24.0
+opendataloader-pdf>=0.1.0
```

当前 `requirements.txt` 第 11-12 行：
```
# PDF Processing
pymupdf>=1.24.0
```

改为：
```
# PDF Processing
pymupdf>=1.24.0
opendataloader-pdf>=0.1.0
```

- [ ] **Step 2: 在 Dockerfile 中添加 Java 运行时**

在 `Dockerfile` 的 `python:3.11-slim-bookworm` 阶段（Stage 2），`pip install` 之前添加 Java 安装：

当前 `Dockerfile` 第 21-27 行：
```dockerfile
FROM python:3.11-slim-bookworm

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
```

改为：
```dockerfile
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install Java runtime (required by OpenDataLoader-PDF)
RUN apt-get update && \
    apt-get install -y --no-install-recommends default-jre-headless && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
```

- [ ] **Step 3: Commit**

```bash
git add requirements.txt Dockerfile
git commit -m "chore(deps): add opendataloader-pdf and Java runtime for improved PDF parsing"
```

---

### Task 2: 添加 Java 检测和新 imports

**Files:**
- Modify: `mkg/pdf_parser.py:1-18` (imports section)

- [ ] **Step 1: 修改文件顶部 docstring 和 imports**

当前文件第 1-17 行：
```python
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
import re
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
```

改为：
```python
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

import fitz  # PyMuPDF
import re
import json
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)
```

- [ ] **Step 2: Commit**

```bash
git add mkg/pdf_parser.py
git commit -m "refactor(pdf_parser): update docstring and imports for OpenDataLoader support"
```

---

### Task 3: 重写 PDFParser 类核心方法

**Files:**
- Modify: `mkg/pdf_parser.py:439-520` (PDFParser class: `__init__`, `parse`, `extract_text`, and new helper methods)

这是核心改动。`PDFParser` 类需要：
1. 新增 `__init__` 检测 Java 可用性
2. 新增 `_parse_with_opendataloader` 方法
3. 新增 `_extract_text_opendataloader` 方法
4. 修改 `parse()` 和 `extract_text()` 根据 `_java_available` 选择路径
5. 保留现有 PyMuPDF 方法，重命名以 `_pymupdf` 后缀标识

- [ ] **Step 1: 替换 PDFParser 类的 `__init__` 和公共方法**

当前第 439-520 行（`class PDFParser` 的开头到 `extract_text` 方法结束）：

```python
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

            # 首页文本（用于提取 DOI/arXiv ID）
            first_page_text = doc[0].get_text() if len(doc) > 0 else ""

            # 提取 DOI 和 arXiv ID（优先级高于标题）
            doi = self._extract_doi(doc, first_page_text)
            arxiv_id = self._extract_arxiv_id(doc, first_page_text)

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
                metadata=metadata,
                doi=doi,
                arxiv_id=arxiv_id
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
```

替换为以下完整代码：

```python
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
```

- [ ] **Step 2: 添加 OpenDataLoader 解析方法**

在上面的 `extract_text` 方法之后（即新的第 490 行之后），添加以下三个新方法：

```python
    def _parse_with_opendataloader(self, pdf_path: str) -> Optional[PaperContent]:
        """
        使用 OpenDataLoader-PDF 解析 PDF

        输出 Markdown（结构化文本，供 LLM 使用）和 JSON（元数据）。
        """
        import opendataloader_pdf

        try:
            # 使用临时目录存放输出
            with tempfile.TemporaryDirectory() as tmpdir:
                opendataloader_pdf.convert(
                    input_path=[pdf_path],
                    output_dir=tmpdir,
                    format="markdown,json"
                )

                # 读取输出文件（与输入同名，扩展名不同）
                base_name = Path(pdf_path).stem
                md_path = Path(tmpdir) / f"{base_name}.md"
                json_path = Path(tmpdir) / f"{base_name}.json"

                # 提取 Markdown 全文
                full_text = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
                if not full_text:
                    return None

                # 提取 JSON 元数据
                metadata = {}
                if json_path.exists():
                    with open(json_path, encoding="utf-8") as f:
                        metadata = json.load(f)

                # 从 Markdown 和 JSON 提取各字段
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

                # 截断过长的文本（700k 字符 ≈ 175k tokens，留有余量）
                if len(text) > 700000:
                    text = text[:700000] + "\n\n... [文本过长，已截断]"

                return text

        except ImportError:
            return None
        except Exception as e:
            logger.error(f"OpenDataLoader text extraction failed: {e}")
            return None
```

- [ ] **Step 3: Commit**

```bash
git add mkg/pdf_parser.py
git commit -m "feat(pdf): add OpenDataLoader-PDF engine with Java detection and PyMuPDF fallback"
```

---

### Task 4: 添加 Markdown 辅助提取方法

**Files:**
- Modify: `mkg/pdf_parser.py` (在 Task 3 添加的方法之后)

- [ ] **Step 1: 添加所有 Markdown 辅助方法**

在 `_extract_text_opendataloader` 方法之后，添加以下 Markdown 辅助提取方法。这些方法从 OpenDataLoader 的 Markdown/JSON 输出中提取标题、作者、摘要、章节等信息：

```python
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
```

- [ ] **Step 2: 重命名 PyMuPDF 的 `extract_text` 方法**

当前 `extract_text` 的 PyMuPDF 实现（在旧代码中约第 502-519 行），需要重命名为 `_extract_text_pymupdf`。

找到原来的 `_extract_text` 方法体（即 `def extract_text(self, pdf_path: str) -> Optional[str]:` 的 PyMuPDF 实现），将其重命名为：

```python
    def _extract_text_pymupdf(self, pdf_path: str) -> Optional[str]:
        """只提取纯文本（PyMuPDF fallback 路径）"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()

            # 清理过长的文本（限制 token 数，大约 4 字符=1token）
            if len(text) > 700000:
                text = text[:700000] + "\n\n... [文本过长，已截断]"

            return text
        except Exception as e:
            print(f"文本提取失败：{e}")
            return None
```

- [ ] **Step 3: Commit**

```bash
git add mkg/pdf_parser.py
git commit -m "refactor(pdf): add Markdown extraction helpers and rename PyMuPDF extract method"
```

---

### Task 5: 重命名 PyMuPDF `parse` 方法并保留 fallback

**Files:**
- Modify: `mkg/pdf_parser.py` (找到原来的 `parse` 方法体中调用的 PyMuPDF 私有方法)

- [ ] **Step 1: 将原来的 `parse` 方法重命名为 `_parse_with_pymupdf`**

找到原来的 `parse` 方法实现（在 Task 3 中，我们已经把公共 `parse()` 方法替换为自动路由版本，但原来的 PyMuPDF 逻辑还在私有方法中）。确保以下 PyMuPDF 私有方法都保持可用：

- `_extract_title` → 保持不变（只在 PyMuPDF 路径中调用）
- `_extract_title_from_metadata` → 保持不变
- `_is_suspicious_title` → 保持不变（也被 Markdown 路径复用）
- `_extract_title_from_text` → 保持不变
- `_looks_like_non_title` → 保持不变
- `_extract_title_by_font_size` → 保持不变
- `_extract_doi` → 重命名为 `_extract_doi_pymupdf`
- `_extract_arxiv_id` → 重命名为 `_extract_arxiv_id_pymupdf`
- `_is_valid_doi` → 保持不变（也被 Markdown 路径复用）
- `_is_valid_arxiv_id` → 保持不变（也被 Markdown 路径复用）
- `_extract_authors` → 重命名为 `_extract_authors_pymupdf`
- `_extract_abstract` → 重命名为 `_extract_abstract_pymupdf`
- `_extract_sections` → 重命名为 `_extract_sections_pymupdf`

将以下方法的签名从：
```python
    def _extract_doi(self, doc: fitz.Document, first_page_text: str = None) -> str:
```
改为：
```python
    def _extract_doi_pymupdf(self, doc: fitz.Document, first_page_text: str = None) -> str:
```

同样将 `_extract_arxiv_id` 改为 `_extract_arxiv_id_pymupdf`，`_extract_authors` 改为 `_extract_authors_pymupdf`，`_extract_abstract` 改为 `_extract_abstract_pymupdf`，`_extract_sections` 改为 `_extract_sections_pymupdf`。

- [ ] **Step 2: 添加 `_parse_with_pymupdf` 方法**

在 Markdown 辅助方法之后，添加完整的 PyMuPDF fallback 解析方法。这需要将原来 `parse` 方法的逻辑提取为一个独立方法：

```python
    def _parse_with_pymupdf(self, pdf_path: str) -> Optional[PaperContent]:
        """
        使用 PyMuPDF 解析 PDF（fallback 路径）
        """
        try:
            doc = fitz.open(pdf_path)

            metadata = doc.metadata
            full_text = ""
            for page in doc:
                full_text += page.get_text()

            first_page_text = doc[0].get_text() if len(doc) > 0 else ""

            doi = self._extract_doi_pymupdf(doc, first_page_text)
            arxiv_id = self._extract_arxiv_id_pymupdf(doc, first_page_text)
            title = self._extract_title(doc)
            authors = self._extract_authors_pymupdf(doc)
            abstract = self._extract_abstract_pymupdf(full_text)
            sections = self._extract_sections_pymupdf(full_text)

            doc.close()

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

        except Exception as e:
            print(f"PDF 解析失败（PyMuPDF）：{e}")
            return None
```

- [ ] **Step 3: Commit**

```bash
git add mkg/pdf_parser.py
git commit -m "refactor(pdf): rename PyMuPDF methods with _pymupdf suffix and add fallback parse method"
```

---

### Task 6: 验证与测试

**Files:**
- Verify: `mkg/pdf_parser.py`
- Verify: `backend/services/process_service.py`
- Verify: `backend/services/paper_service.py`
- Verify: `mkg/agent/tools.py`

- [ ] **Step 1: 验证接口兼容性**

确认以下调用方不受影响（方法签名不变，只是内部实现切换了引擎）：

- `backend/services/process_service.py:33` — `self.pdf_parser.extract_text(paper['pdf_path'])`
- `backend/services/paper_service.py:78` — `parser.extract_text(str(pdf_path))`
- `mkg/agent/tools.py:162` — `_pdf_parser.extract_text(pdf_path)`

这些都是通过 `extract_text(pdf_path) -> Optional[str]` 接口调用，签名完全一致。

- [ ] **Step 2: 验证 Python 语法**

```bash
python -c "import mkg.pdf_parser; print('Import OK')"
```

Expected: `Import OK` (如果 Java 不可用，会显示 `[PDF] 解析引擎: PyMuPDF`)

- [ ] **Step 3: 验证 `PDFParser` 实例化**

```bash
python -c "from mkg.pdf_parser import PDFParser; p = PDFParser(); print(f'Java: {p._java_available}')"
```

Expected: `Java: True` (如果有 Java) 或 `Java: False` (如果没有 Java)

- [ ] **Step 4: Commit（如果有验证相关改动）**

如果验证过程中做了修复：

```bash
git add mkg/pdf_parser.py
git commit -m "fix(pdf): address any issues found during verification"
```

---

## 自审

### 1. Spec 覆盖检查

| Spec 要求 | 对应 Task |
|-----------|-----------|
| 用 OpenDataLoader-PDF 替换 PyMuPDF | Task 3 (`_parse_with_opendataloader`, `_extract_text_opendataloader`) |
| 保留 PyMuPDF fallback | Task 3 (自动路由逻辑), Task 5 (`_parse_with_pymupdf`, `_extract_text_pymupdf`) |
| Java 可用性检测 | Task 3 (`_check_java`) |
| Markdown 输出格式 | Task 3 (`_extract_text_opendataloader` 返回 Markdown) |
| OpenDataLoader 到 PaperContent 映射 | Task 3 + Task 4 (所有 `_extract_*_from_markdown` 方法) |
| requirements.txt 添加依赖 | Task 1 |
| Dockerfile 添加 Java | Task 1 |
| 启动日志输出 | Task 3 (`__init__` 中的 `print` 和 `logger.info`) |
| 不改 LLM prompt | 所有 Task 都不涉及 LLM prompt 修改 |
| 不添加混合模式 | Task 3 只使用 `opendataloader_pdf.convert()` 的 fast 模式 |

### 2. Placeholder 扫描

Plan 中无 TBD/TODO/类似"稍后添加"的占位符。所有代码步骤都包含完整代码。

### 3. 类型一致性

- `parse() -> Optional[PaperContent]`: 签名不变
- `extract_text() -> Optional[str]`: 签名不变
- `_check_java() -> bool`: 新方法
- 所有 `_extract_*_from_markdown` 方法返回类型与原有 PyMuPDF 方法一致

### 4. 接口兼容性

所有调用方（process_service, paper_service, agent/tools）都通过 `extract_text(pdf_path)` 或 `parse(pdf_path)` 调用，签名完全不变。
