# PDF 提取引擎替换设计：PyMuPDF → OpenDataLoader-PDF

**日期**：2026-04-10
**状态**：Draft

## 1. 问题陈述

当前 PDF 解析模块（`mkg/pdf_parser.py`）使用 PyMuPDF（fitz）提取纯文本，存在以下固有缺陷：

- **阅读顺序错误**：双栏/多栏学术论文的文本按页面线性提取，左右栏拼接导致上下文断裂
- **表格结构丢失**：表格退化为纯文本行，行列关系完全丢失
- **公式不可读**：数学公式变成 Unicode 碎片或完全丢失
- **标题识别脆弱**：1400+ 行代码中大量字体大小启发式和正则匹配，对非标准 PDF 可靠性低

OpenDataLoader-PDF（14k+ stars，Benchmark #1 0.907）提供结构化 Markdown 输出，包含正确的阅读顺序、表格结构、标题层级。

## 2. 方案决策

采用 **方案 B：替换底层引擎**——用 OpenDataLoader-PDF 替换 PyMuPDF 做文本提取，保留已验证的两阶段 LLM 提取逻辑不变。

- 改动集中在 `PDFParser` 类，风险可控
- LLM prompt 和业务逻辑几乎不需要改
- Markdown 格式对 LLM 更友好

## 3. 架构设计

### 3.1 核心变更

```
Before: PDF → PyMuPDF(fitz) → 纯文本 → LLM Stage1 → LLM Stage2 → 概念树
After:  PDF → OpenDataLoader-PDF → Markdown+JSON → LLM Stage1 → LLM Stage2 → 概念树
```

### 3.2 文件改动

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `mkg/pdf_parser.py` | 重写 `PDFParser` 类 | 添加 OpenDataLoader 提取路径，保留 PyMuPDF fallback |
| `mkg/pdf_parser.py` | 删除启发式方法 | `_extract_title_by_font_size`, `_extract_authors`, `_extract_abstract`, `_extract_sections` 等可删除或大幅简化 |
| `requirements.txt` | 添加依赖 | `opendataloader-pdf>=0.1.0` |
| `Dockerfile` | 添加 Java 运行时 | `apt-get install -y default-jre-headless` |

### 3.3 新 PDFParser 结构

```python
class PDFParser:
    def __init__(self):
        self._java_available = self._check_java()

    def _check_java(self) -> bool:
        """检测 Java 是否可用"""

    def parse(self, pdf_path: str) -> Optional[PaperContent]:
        """主入口：自动选择最佳可用引擎"""
        if self._java_available:
            return self._parse_with_opendataloader(pdf_path)
        return self._parse_with_pymupdf(pdf_path)  # 现有逻辑

    def extract_text(self, pdf_path: str) -> Optional[str]:
        """提取纯文本（供 LLM 使用）"""
        if self._java_available:
            return self._extract_text_opendataloader(pdf_path)
        return self._extract_text_pymupdf(pdf_path)

    def _parse_with_opendataloader(self, pdf_path: str) -> Optional[PaperContent]:
        """使用 OpenDataLoader-PDF 解析"""

    def _extract_text_opendataloader(self, pdf_path: str) -> Optional[str]:
        """使用 OpenDataLoader-PDF 提取 Markdown 文本"""
```

### 3.4 OpenDataLoader 到 PaperContent 的映射

OpenDataLoader 输出两种格式：
- **Markdown**：用于 LLM 输入（保留结构）
- **JSON**：用于提取元数据（标题、作者、DOI、边界框等）

映射规则：
- `title`：JSON metadata 中的标题，或 Markdown 第一个 `# Heading`
- `authors`：JSON 元数据中的作者列表
- `abstract`：Markdown 中 `## Abstract` 段落
- `full_text`：完整 Markdown 内容（LLM 能理解 Markdown 语法）
- `sections`：按 `## Heading` 分割 Markdown
- `doi` / `arxiv_id`：从 JSON metadata 或 Markdown 正文中正则提取

### 3.5 Fallback 策略

```
启动时检测 Java → 标记 self._java_available
parse() / extract_text() 根据标志选择路径
Java 不可用时自动退回 PyMuPDF（现有行为完全保留）
后端启动时日志输出: "PDF engine: OpenDataLoader-PDF (Java available)" 或 "PDF engine: PyMuPDF (Java not available)"
```

## 4. 数据流

```
用户上传 PDF
  → UploadService 保存文件
  → ProcessService.process_paper(doi)
    → pdf_parser.extract_text(pdf_path)  ← 这里切换引擎
      → OpenDataLoader: convert(format="markdown,json")
      → 解析 Markdown + JSON → PaperContent
    → LLMConceptExtractor.extract(paper_content)
      → Stage 1: 论文总结（输入质量提升）
      → Stage 2: 概念树构建（表格/公式/章节结构正确）
    → 保存概念到数据库
```

## 5. 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| Java 不可用 | PyMuPDF fallback，行为与现在一致 |
| Markdown 输出过长 | 截断策略不变（700k 字符），Markdown 比纯文本略长但在可控范围 |
| OpenDataLoader 元数据不包含作者/摘要 | 保留 PyMuPDF 的启发式提取作为二级 fallback |
| Docker 镜像体积增加 | JRE headless 约 100MB，可接受 |

## 6. 验证标准

- 双栏论文的阅读顺序正确（左栏→右栏不再混排）
- 表格在 Markdown 中保留行列结构
- 标题层级（`# ## ###`）准确反映论文章节
- LLM 提取的概念质量提升（带表格/公式的论文效果更明显）
- PyMuPDF fallback 路径与现有行为一致

## 7. 不做的事

- 不使用 OpenDataLoader 的混合模式（hybrid/AI backend）——只需 fast 模式即可
- 不提取公式 LaTeX、图片描述等新字段（那是后续增强，不在本次范围）
- 不改 LLM 的 prompt 逻辑（Stage 1/Stage 2 prompt 保持不变）
