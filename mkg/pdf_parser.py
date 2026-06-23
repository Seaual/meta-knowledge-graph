"""
PDF 解析模块 - 使用 LLM 解析学术论文

设计：
- 首选 MarkItDown 提取结构化 Markdown（轻量、无需 Java、支持多种格式）
- PyMuPDF 作为 fallback
- 发送结构化文本给 LLM，提取结构化信息：
  - 元数据（标题、作者、摘要）
  - 研究问题/贡献
  - 概念层级树（动态分层）
  - 方法论、数据集、评估指标等
"""

import json
import logging
import re
import statistics
from pathlib import Path

import fitz  # PyMuPDF

from mkg.pdf_models import PaperContent

logger = logging.getLogger(__name__)


class PDFParser:
    """PDF 解析器 - 首选 MarkItDown，PyMuPDF fallback"""

    def __init__(self, allowed_base_dirs: list[str | Path] | None = None):
        """
        Args:
            allowed_base_dirs: 允许解析的 PDF 所在基础目录列表。
                为 None 时不限制（保留 CLI 等场景的自由度）。
        """
        if allowed_base_dirs is None:
            self._allowed_base_dirs = None
        else:
            self._allowed_base_dirs = [Path(d).resolve() for d in allowed_base_dirs]

    def _validate_pdf_path(self, pdf_path: str) -> Path:
        """校验 PDF 路径安全并返回解析后的 Path。"""
        path = Path(pdf_path)
        if self._allowed_base_dirs is not None:
            resolved = path.resolve()
            if not any(resolved.is_relative_to(base) for base in self._allowed_base_dirs):
                raise ValueError(f"PDF path outside allowed directories: {pdf_path}")
        return path

    def parse(self, pdf_path: str) -> PaperContent | None:
        """
        解析 PDF 文件（自动选择引擎）

        Args:
            pdf_path: PDF 文件路径

        Returns:
            论文内容，解析失败返回 None
        """
        self._validate_pdf_path(pdf_path)
        result = self._parse_with_markitdown(pdf_path)
        if result:
            return result
        logger.warning("[PDF] MarkItDown 解析失败，回退到 PyMuPDF")
        return self._parse_with_pymupdf(pdf_path)

    def extract_text(self, pdf_path: str) -> str | None:
        """
        只提取纯文本（供 LLM 使用，自动选择引擎）
        """
        self._validate_pdf_path(pdf_path)
        text = self._extract_text_markitdown(pdf_path)
        if text:
            return text
        logger.warning("MarkItDown text extraction failed, falling back to PyMuPDF")
        return self._extract_text_pymupdf(pdf_path)

    def _parse_with_markitdown(self, pdf_path: str) -> PaperContent | None:
        """
        使用 MarkItDown 解析 PDF

        输出 Markdown（结构化文本，供 LLM 使用）。
        """
        from markitdown import MarkItDown

        try:
            md = MarkItDown()
            result = md.convert(pdf_path)
            full_text = result.text_content if result else ""

            if not full_text:
                return None

            if len(full_text) > 700000:
                full_text = full_text[:700000] + "\n\n... [文本过长，已截断]"

            metadata = {}
            title = self._extract_title_from_markdown(full_text, metadata)
            authors = self._extract_authors_from_metadata(metadata, full_text)
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
                arxiv_id=arxiv_id,
            )

        except ImportError:
            logger.warning("markitdown not installed, falling back to PyMuPDF")
            return None
        except Exception as e:
            logger.error(f"MarkItDown parsing failed: {e}")
            return None

    def _extract_text_markitdown(self, pdf_path: str) -> str | None:
        """
        使用 MarkItDown 提取 Markdown 文本（供 LLM 使用）
        """
        from markitdown import MarkItDown

        try:
            md = MarkItDown()
            result = md.convert(pdf_path)
            text = result.text_content if result else ""

            if not text:
                return None

            if len(text) > 700000:
                text = text[:700000] + "\n\n... [文本过长，已截断]"

            return text

        except ImportError:
            return None
        except Exception as e:
            logger.error(f"MarkItDown text extraction failed: {e}")
            return None

    def _extract_text_pymupdf(self, pdf_path: str) -> str | None:
        """只提取纯文本（PyMuPDF fallback 路径）"""
        doc = fitz.open(pdf_path)
        try:
            text = ""
            for page in doc:
                text += page.get_text()

            if len(text) > 700000:
                text = text[:700000] + "\n\n... [文本过长，已截断]"

            return text
        except Exception as e:
            logger.error(f"文本提取失败：{e}")
            return None
        finally:
            doc.close()

    def _parse_with_pymupdf(self, pdf_path: str) -> PaperContent | None:
        """
        使用 PyMuPDF 解析 PDF（fallback 路径）
        """
        doc = fitz.open(pdf_path)
        try:
            metadata = doc.metadata
            full_text = ""
            for page in doc:
                full_text += page.get_text()

            first_page_text = doc[0].get_text() if len(doc) > 0 else ""

            doi = self._extract_doi_pymupdf(doc, first_page_text)
            arxiv_id = self._extract_arxiv_id_pymupdf(doc, first_page_text)
            title = self._extract_title_pymupdf(doc)
            authors = self._extract_authors_pymupdf(doc)
            abstract = self._extract_abstract_pymupdf(full_text)
            sections = self._extract_sections_pymupdf(full_text)

            return PaperContent(
                title=title,
                authors=authors,
                abstract=abstract,
                full_text=full_text,
                sections=sections,
                metadata=metadata,
                doi=doi,
                arxiv_id=arxiv_id,
            )
        except Exception as e:
            logger.error(f"PDF 解析失败（PyMuPDF）：{e}")
            return None
        finally:
            doc.close()

    # ========== Markdown 辅助方法 ==========

    def _extract_title_from_markdown(self, markdown: str, metadata: dict) -> str:
        """
        从 Markdown 或 JSON 元数据提取标题

        优先级: JSON 元数据 → H2 标题 → H1 标题（跳过 arxiv/日期模式）
        """
        # 优先级1: JSON 元数据中的标题
        meta_title = metadata.get("title", "")
        if meta_title and len(meta_title) > 10 and not self._is_suspicious_title(meta_title):
            return meta_title.strip()

        # 优先级2: 第一个 H2 标题（学术论文标题通常是 H2）
        match_h2 = re.search(r"^##\s+(.+)$", markdown, re.MULTILINE)
        if match_h2:
            title = match_h2.group(1).strip()
            if len(title) > 10 and not self._is_suspicious_title(title):
                return title

        # 优先级3: H1 标题（跳过 arxiv/日期/期刊信息模式）
        h1_matches = re.findall(r"^#\s+(.+)$", markdown, re.MULTILINE)
        for candidate in h1_matches:
            candidate = candidate.strip()
            if len(candidate) > 10 and not self._is_suspicious_title(candidate):
                return candidate

        return meta_title or "Unknown"

    def _extract_authors_from_metadata(self, metadata: dict, markdown: str = "") -> list[str]:
        """
        从 JSON 元数据提取作者列表，若元数据为空则从 Markdown 中提取
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
                if len(name) > 2 and not any(
                    x in name.lower()
                    for x in ["university", "institute", "lab", "department", "dept", "college", "school"]
                ):
                    cleaned.append(name)
            authors = cleaned

        if not authors:
            authors = self._extract_authors_from_markdown_fallback(markdown)

        return authors[:10]

    def _extract_authors_from_markdown_fallback(self, markdown: str) -> list[str]:
        """
        从 Markdown 提取作者（当 JSON 元数据为空时的 fallback）
        策略：查找标题后、摘要/正文前的作者行
        """
        text_lower = markdown.lower()

        # 找到标题位置
        title_match = re.search(r"^##\s+(.+)$", markdown, re.MULTILINE)
        if not title_match:
            return []

        start = title_match.end()
        # 在标题后 500 字符内搜索作者行
        candidate = markdown[start : start + 800]
        candidate_lower = candidate.lower()

        # 找摘要或 introduction 之前的行
        abstract_idx = candidate_lower.find("## abstract")
        intro_idx = candidate_lower.find("## introduction")
        end_idx = min(
            abstract_idx if abstract_idx != -1 else len(candidate), intro_idx if intro_idx != -1 else len(candidate)
        )
        candidate = candidate[:end_idx]

        # 提取作者行（排除 URL、邮箱、机构行）
        lines = [l.strip() for l in candidate.split("\n") if l.strip()]
        author_lines = []
        for line in lines:
            low = line.lower()
            if low.startswith(("http", "ftp", "mailto", "email", "correspond")):
                break  # 遇到 URL/邮箱，作者行结束
            if "university" in low or "institute" in low or "department" in low:
                break  # 遇到机构行
            if line.startswith(("## ", "### ")):
                continue  # 跳过 H2/H3 标题行（通常是论文标题和小节标题）
            if re.match(r"^#{4,6}\s+(.+)$", line):
                # H4+ 标题行（作者信息常用）
                text = re.sub(r"#{4,6}\s+", "", line).strip()
                if text and not text.startswith("http"):
                    author_lines.append(text)
            elif not line.startswith("#"):
                # 非标题行，可能是作者（有引用标记或逗号分隔）
                if any(c in line for c in ["*", "∗", "†", ","]) and len(line) > 5:
                    author_lines.append(line)

        if author_lines:
            # 合并并分割作者
            raw = " ".join(author_lines)
            # 策略：用引用标记 (∗*†‡) 作为分隔符，因为学术论文作者常带这些标记
            parts = re.split(r"[∗*†‡]+", raw)
            # 对每个部分进一步按逗号或 " and " 分割
            names = []
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                if "," in part:
                    names.extend([n.strip() for n in part.split(",") if n.strip()])
                elif " and " in part.lower():
                    names.extend([n.strip() for n in re.split(r"\s+and\s+", part, flags=re.IGNORECASE) if n.strip()])
                else:
                    names.append(part)

            return [n for n in names if len(n) > 2][:10]

        return []

    def _extract_abstract_from_markdown(self, markdown: str) -> str:
        """
        从 Markdown 提取摘要
        查找 ## Abstract 或 # Abstract 部分的内容
        """
        text_lower = markdown.lower()

        # 常见的摘要标记
        abstract_markers = [
            "## abstract",
            "# abstract",
            "## abstract:",
            "### abstract",
            "## summary",
            "# summary",
            "## 摘要",
            "# 摘要",
        ]

        for marker in abstract_markers:
            idx = text_lower.find(marker)
            if idx == -1:
                continue

            start = idx + len(marker)
            # 跳过冒号和空格
            while start < len(markdown) and markdown[start] in ": \n\t":
                start += 1

            # 查找摘要结束：下一个 ## 标题或引言
            end = len(markdown)
            end_patterns = [
                "\n## ",
                "\n# ",
                "\n1 introduction",
                "\n1. introduction",
                "\nintroduction",
                "\n引言",
                "\n## keywords",
                "\n关键词",
            ]
            for pat in end_patterns:
                marker_idx = text_lower.find(pat, start)
                if marker_idx != -1 and marker_idx < end:
                    end = marker_idx

            abstract = markdown[start:end].strip()
            # 清理：移除 Markdown 格式标记
            abstract = re.sub(r"\*\*|\*|__", "", abstract)
            # 合并多行
            lines = [line.strip() for line in abstract.split("\n") if line.strip()]
            cleaned = [l for l in lines if len(l) > 20 and not l.isdigit()]
            if cleaned:
                result = " ".join(cleaned)
                return result[:3000]

        # 找不到摘要时返回前 1000 字符
        return markdown[:1000]

    def _extract_sections_from_markdown(self, markdown: str) -> dict[str, str]:
        """
        从 Markdown 提取章节结构
        按 H2 和 H3 标题分割
        """
        sections = {}
        target_sections = [
            "introduction",
            "method",
            "methods",
            "approach",
            "experiment",
            "experiments",
            "results",
            "discussion",
            "conclusion",
            "related work",
            "methodology",
        ]

        # 按 H2 和 H3 标题分割
        heading_pattern = re.compile(r"^#{2,3}\s+(.+)$", re.MULTILINE)
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
                    clean_content = re.sub(r"#{1,4}\s+", "", content)
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
            r"\b(10\.\d{4,}/[^\s,;)\]]+)",
            r"https?://doi\.org/(10\.\d{4,}/[^\s,;)\]]+)",
            r"DOI:\s*(10\.\d{4,}/[^\s,;)\]]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, markdown, re.IGNORECASE)
            if match:
                doi = re.sub(r"[.,;)\]]+$", "", match.group(1).strip())
                if self._is_valid_doi(doi):
                    return doi.lower()

        return ""

    def _extract_arxiv_id_from_metadata(self, metadata: dict, markdown: str) -> str:
        """
        从 JSON 元数据或 Markdown 正文提取 arXiv ID
        """
        # 优先级1: 元数据
        for key in ["arxiv_id", "arxiv", "eprint"]:
            arxiv_id = metadata.get(key, "")
            if arxiv_id and self._is_valid_arxiv_id(arxiv_id):
                return arxiv_id.strip()

        # 优先级2: Markdown 正文
        pattern = r"arxiv:\s*(\d{4}\.\d{4,5}(v\d+)?)"
        match = re.search(pattern, markdown, re.IGNORECASE)
        if match:
            arxiv_id = match.group(1).strip()
            if self._is_valid_arxiv_id(arxiv_id):
                return arxiv_id

        return ""

    def _extract_title_pymupdf(self, doc: fitz.Document) -> str:
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
        return doc.metadata.get("title", "") or "Unknown"

    def _extract_title_from_metadata(self, doc: fitz.Document) -> str:
        """从 PDF 元数据提取标题"""
        # PDF Info dict
        title = doc.metadata.get("title", "")
        if title and len(title) > 5:
            return title.strip()

        # XMP 元数据（如果有的话）
        try:
            if hasattr(doc, "xref_xml_metadata"):
                xmp = doc.xref_xml_metadata()
                if xmp:
                    match = re.search(r"<dc:title>.*?<rdf:li[^>]*>(.*?)</rdf:li>", xmp, re.DOTALL | re.IGNORECASE)
                    if match:
                        return match.group(1).strip()
        except Exception as e:
            logger.debug("XMP title extraction failed: %s", e)
            pass

        return ""

    def _is_suspicious_title(self, title: str) -> bool:
        """检测可疑的标题（可能是元数据错误）"""
        low = title.lower().strip()
        suspicious = [
            "untitled",
            "title",
            "document",
            "paper",
            "article",
            "microsoft word",
            "latex",
            "tex",
            "pdf",
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
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        title_lines = []
        for line in lines[:15]:
            if self._looks_like_non_title(line):
                continue
            title_lines.append(line)
            if len(title_lines) >= 3:
                break

        if title_lines:
            return " ".join(title_lines)
        return ""

    def _looks_like_non_title(self, text: str) -> bool:
        """判断是否看起来不像标题"""
        low = text.lower()

        # 太短
        if len(text) < 5:
            return True

        # 页眉关键词
        header_keywords = [
            "downloaded",
            "redistribution",
            "copyright",
            "editorial",
            "sciencedirect",
            "elsevier",
            "springer",
            "ieee",
            "acm",
            "siam",
            "procedia",
            "available online",
            "www.",
            "http://",
            "https://",
            "peer-review",
            "journal of",
            "vol.",
            "pp.",
            "abstract",
            "keywords",
            "introduction",
            "contents",
            "received",
            "accepted",
            "published",
            "arxiv:",
            "arxiv.org",  # arXiv 标识
        ]
        for kw in header_keywords:
            if kw in low:
                return True

        # arXiv 格式：[cs.LG], [math.NA] 等
        if re.match(r"^\[([a-z]+\.)*[a-z]+\]", low):
            return True

        # 邮箱
        if "@" in text:
            return True

        # 纯数字
        if text.isdigit():
            return True

        # 章节标题
        section_patterns = [
            r"^\d+\.\s+[A-Z]",  # "1. Introduction"
            r"^abstract$",
            r"^introduction$",
            r"^keywords$",
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
                        text_lines.append({"text": text, "font_size": max_font, "y_pos": y_pos})
                        all_font_sizes.append(max_font)

            if not text_lines:
                return ""

            # 计算正文字体大小（中位数）
            body_font_size = statistics.median(all_font_sizes)

            # 标题阈值：比正文大至少2个点
            title_threshold = body_font_size + 2

            # 页眉关键词（即使字体大也要跳过）
            header_keywords = [
                "sciencedirect",
                "elsevier",
                "springer",
                "ieee",
                "acm",
                "siam",
                "procedia",
                "available online",
                "www.",
                "downloaded",
                "copyright",
                "vol.",
                "pp.",
                "editorial",
                "journal of",
                "arxiv:",
                "arxiv.org",
                "[cs.",
                "[math.",
                "[stat.",  # arXiv 标识
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
                return " ".join(title_parts)

        except Exception as e:
            logger.warning("字体大小提取失败: %s", e)

        return ""

    def _extract_doi_pymupdf(self, doc: fitz.Document, first_page_text: str = None) -> str:
        """
        提取 DOI

        来源优先级：
        1. PDF 元数据 (/doi)
        2. 首页正文中的 DOI 格式

        Returns:
            DOI 字符串（如 "10.1234/abc123"），未找到返回空字符串
        """
        # 方法1: PDF 元数据
        doi = doc.metadata.get("doi", "")
        if doi and self._is_valid_doi(doi):
            return doi.strip().lower()

        # 方法2: 从首页文本中搜索
        if first_page_text is None and len(doc) > 0:
            first_page_text = doc[0].get_text()

        if first_page_text:
            # 常见 DOI 格式（优先匹配直接的 10. 格式，这是最通用的）
            patterns = [
                r"\b(10\.\d{4,}/[^\s,;)\]]+)",  # 直接的 DOI 格式（最常见）
                r"https?://doi\.org/(10\.\d{4,}/[^\s,;)\]]+)",  # https://doi.org/10.xxxx/xxx
                r"https?://dx\.doi\.org/(10\.\d{4,}/[^\s,;)\]]+)",
                r"DOI:\s*(10\.\d{4,}/[^\s,;)\]]+)",  # DOI: 10.xxxx/xxx
                r"doi:\s*(10\.\d{4,}/[^\s,;)\]]+)",
            ]

            for pattern in patterns:
                match = re.search(pattern, first_page_text, re.IGNORECASE)
                if match:
                    doi = match.group(1).strip()
                    # 清理末尾的标点（双重保险）
                    doi = re.sub(r"[.,;)\]]+$", "", doi)
                    if self._is_valid_doi(doi):
                        return doi.lower()

        return ""

    def _extract_arxiv_id_pymupdf(self, doc: fitz.Document, first_page_text: str = None) -> str:
        """
        提取 arXiv ID

        来源优先级：
        1. PDF 元数据
        2. 首页正文中的 arXiv 格式

        Returns:
            arXiv ID（如 "2301.12345"），未找到返回空字符串
        """
        # 方法1: PDF 元数据
        for key in ["arxiv_id", "arxiv", "eprint"]:
            arxiv_id = doc.metadata.get(key, "")
            if arxiv_id and self._is_valid_arxiv_id(arxiv_id):
                return arxiv_id.strip()

        # 方法2: 从首页文本中搜索
        if first_page_text is None and len(doc) > 0:
            first_page_text = doc[0].get_text()

        if first_page_text:
            # arXiv ID 格式
            patterns = [
                r"arXiv:\s*(\d{4}\.\d{4,5}(v\d+)?)",  # arXiv:2301.12345 或 arXiv:2301.12345v2
                r"arxiv:\s*(\d{4}\.\d{4,5}(v\d+)?)",
                r"arXiv:\s*([a-z-]+/\d{7}(v\d+)?)",  # 旧格式：arXiv:hep-th/9901001
                r"arxiv:\s*([a-z-]+/\d{7}(v\d+)?)",
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
        if not doi.lower().startswith("10."):
            return False
        # 必须包含 /
        if "/" not in doi:
            return False
        return True

    def _is_valid_arxiv_id(self, arxiv_id: str) -> bool:
        """验证 arXiv ID 格式是否有效"""
        if not arxiv_id or len(arxiv_id) < 5:
            return False
        # 新格式：2301.12345
        if re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", arxiv_id):
            return True
        # 旧格式：hep-th/9901001
        if re.match(r"^[a-z-]+/\d{7}(v\d+)?$", arxiv_id, re.IGNORECASE):
            return True
        return False

    def _extract_authors_pymupdf(self, doc: fitz.Document) -> list[str]:
        """提取作者 - 改进版"""
        first_page = doc[0]
        text = first_page.get_text()
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        authors = []

        # 方法1: 从 PDF 元数据获取
        if doc.metadata.get("author"):
            meta_authors = [a.strip() for a in doc.metadata["author"].split(",")]
            # 检查是否像人名（不是机构名）
            for a in meta_authors:
                if len(a) > 2 and not any(
                    x in a.lower()
                    for x in ["university", "institute", "lab", "department", "dept", "college", "school"]
                ):
                    authors.append(a)
            if authors:
                return authors[:10]

        # 方法2: 查找作者模式
        # 作者通常在标题之后，摘要之前
        title_found = False
        for i, line in enumerate(lines[:15]):
            # 跳过期刊标识
            if any(x in line.lower() for x in ["downloaded", "redistribution", "siam", "ieee", "acm"]):
                continue

            # 检测作者名模式
            # 模式1: "LastName, FirstName" 或 "FirstName LastName"
            # 模式2: 多个作者用逗号或 "and" 分隔

            # 跳过机构行
            if any(
                x in line.lower()
                for x in ["university", "institute", "lab", "department", "dept", "college", "school", "@", "email"]
            ):
                continue

            # 跳过摘要、引言等标题
            if any(x in line.lower() for x in ["abstract", "introduction", "keywords", "key words"]):
                break

            # 可能是作者行
            # 检查是否有名字特征（首字母大写，包含空格）
            if " " in line and len(line) < 100 and len(line) > 5:
                # 检查是否像人名
                words = line.split()
                if len(words) >= 2 and len(words) <= 10:
                    # 检查每个词首字母是否大写（英文名特征）
                    name_like = sum(1 for w in words if w[0].isupper() or w[0].isdigit())
                    if name_like >= len(words) * 0.5:
                        # 可能是作者行，尝试分割
                        # 处理 "A, B, and C" 或 "A and B" 格式
                        # 分割作者
                        parts = re.split(r",\s*(?:and\s+)?|\s+and\s+", line)
                        for p in parts:
                            p = p.strip()
                            if p and len(p) > 2:
                                # 检查不是机构
                                if not any(x in p.lower() for x in ["university", "institute", "lab", "dept"]):
                                    authors.append(p)

        return authors[:10]

    def _extract_abstract_pymupdf(self, full_text: str) -> str:
        """提取摘要 - 改进版"""
        text_lower = full_text.lower()

        # 常见的摘要标记
        abstract_markers = ["abstract", "abstract:", "a b s t r a c t", "summary", "摘要"]

        for marker in abstract_markers:
            idx = text_lower.find(marker)
            if idx == -1:
                continue

            start = idx + len(marker)

            # 跳过冒号和空格
            while start < len(full_text) and full_text[start] in ": \n\t":
                start += 1

            # 查找摘要结束位置
            end = len(full_text)
            end_markers = [
                "\n1 introduction",
                "\n1. introduction",
                "\nintroduction",
                "\n1 ",
                "\nkeywords",
                "\nkey words",
                "\n关键词",
                "\n\n\n\n",  # 多个空行
            ]

            for end_marker in end_markers:
                marker_idx = text_lower.find(end_marker, start)
                if marker_idx != -1 and marker_idx < end:
                    end = marker_idx

            abstract = full_text[start:end].strip()

            # 清理摘要
            # 移除开头的数字（页码等）
            lines = abstract.split("\n")
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
                if any(x in line.lower() for x in ["downloaded", "redistribution", "siam"]):
                    continue
                cleaned_lines.append(line)

            if cleaned_lines:
                abstract = " ".join(cleaned_lines)
                return abstract[:3000]

        # 如果找不到摘要，返回前 1000 字符
        return full_text[:1000]

    def _extract_sections_pymupdf(self, full_text: str) -> dict[str, str]:
        """提取章节"""
        sections = {}

        section_patterns = [
            ("introduction", r"\d+\s+introduction"),
            ("method", r"\d+\s+method"),
            ("methods", r"\d+\s+methods"),
            ("approach", r"\d+\s+approach"),
            ("experiment", r"\d+\s+experiment"),
            ("experiments", r"\d+\s+experiments"),
            ("results", r"\d+\s+results"),
            ("discussion", r"\d+\s+discussion"),
            ("conclusion", r"\d+\s+conclusion"),
            ("related work", r"\d+\s+related"),
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


# 向后兼容：确保从 mkg.pdf_parser 导入原有符号仍然工作
from mkg.concept_extractor import LLMConceptExtractor  # noqa: F401, E402
from mkg.pdf_models import ConceptTree, LLMExtractedContent  # noqa: F401, E402
