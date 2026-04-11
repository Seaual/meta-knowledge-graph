"""
Semantic Scholar API 客户端封装层

所有 S2 调用都通过这个模块，统一处理限速、缓存、重试、错误处理。
"""

import functools
import hashlib
import json
import logging
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("mkg.s2")


# ============================================================
# 1. 限速器（1 RPS）
# ============================================================


class RateLimiter:
    """线程安全的限速器"""

    def __init__(self, rps: float = 1.0):
        self.rps = rps
        self.min_interval = 1.0 / rps
        self.last_request_time = 0.0
        self.lock = threading.Lock()

    def wait(self):
        """如果距离上次调用不足间隔，sleep 补足差值"""
        with self.lock:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed + 0.1  # 加 0.1s 缓冲
                time.sleep(sleep_time)
            self.last_request_time = time.time()


# ============================================================
# 2. 本地缓存
# ============================================================


class S2Cache:
    """本地文件缓存"""

    def __init__(self, cache_dir: str = ".s2_cache", ttl: int = 604800):
        """
        Args:
            cache_dir: 缓存目录
            ttl: 过期时间（秒），默认 7 天
        """
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

    def get_cache(self, key: str) -> dict | None:
        """获取缓存数据"""
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)

            # 检查是否过期
            cached_at = data.get("_cached_at", 0)
            if time.time() - cached_at > self.ttl:
                cache_path.unlink()
                return None

            return data.get("data")
        except Exception as e:
            logger.warning(f"Failed to read cache: {e}")
            return None

    def set_cache(self, key: str, data: Any):
        """设置缓存数据"""
        cache_path = self._get_cache_path(key)

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({"_cached_at": time.time(), "data": data}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")


# ============================================================
# 3. 重试逻辑
# ============================================================


def s2_retry(max_retries: int = 3):
    """
    S2 API 调用重试装饰器

    - 429 → sleep 后重试（等待时间递增）
    - 500 → sleep 1 秒后重试
    - 其他异常 → 记录日志，返回 None
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()

                    # 检查是否是 429 错误 - 等待后重试
                    if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
                        wait_time = 5 * (attempt + 1)  # 递增等待时间: 5s, 10s, 15s
                        logger.warning(
                            f"Rate limited, waiting {wait_time}s before retry ({attempt + 1}/{max_retries})..."
                        )
                        time.sleep(wait_time)
                    # 检查是否是 500 错误
                    elif "500" in error_str or "server error" in error_str:
                        wait_time = 1 * (attempt + 1)
                        logger.warning(f"Server error, waiting {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        # 其他错误，不重试
                        logger.error(f"S2 API error: {e}")
                        return None

            logger.error(f"Max retries ({max_retries}) exceeded: {last_error}")
            return None

        return wrapper

    return decorator


# ============================================================
# 4. 标题清洗工具
# ============================================================


def levenshtein_ratio(s1: str, s2: str) -> float:
    """
    计算 Levenshtein 编辑距离相似度 (0-1)

    Args:
        s1, s2: 比较的两个字符串

    Returns:
        相似度，1 表示完全相同，0 表示完全不同
    """
    if not s1 or not s2:
        return 0.0

    s1, s2 = s1.lower(), s2.lower()

    # 优化：如果字符串过长，只比较前 200 字符
    if len(s1) > 200:
        s1 = s1[:200]
    if len(s2) > 200:
        s2 = s2[:200]

    m, n = len(s1), len(s2)

    # 使用滚动数组优化空间
    prev = list(range(n + 1))
    curr = [0] * (n + 1)

    for i in range(1, m + 1):
        curr[0] = i
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                curr[j] = prev[j - 1]
            else:
                curr[j] = min(prev[j], curr[j - 1], prev[j - 1]) + 1
        prev, curr = curr, prev

    distance = prev[n]
    max_len = max(m, n)
    return 1 - distance / max_len


def llm_refine_title(raw_title: str, llm_client, paper_context: dict = None) -> str:
    """
    使用 LLM 修正标题，提高 S2 匹配成功率

    当标题提取有问题时（如包含页眉、OCR错误、格式问题），
    使用 LLM 分析并修正。

    Args:
        raw_title: 原始提取的标题（可能有错误）
        llm_client: LiteLLMClient 实例
        paper_context: 额外上下文 {'abstract': ..., 'authors': ...}

    Returns:
        修正后的标题，或空字符串表示无法修正
    """
    if not raw_title or len(raw_title.strip()) < 5:
        return ""

    context_info = ""
    if paper_context:
        if paper_context.get("abstract"):
            context_info += f"\n摘要片段: {paper_context['abstract'][:300]}..."
        if paper_context.get("authors"):
            authors = paper_context["authors"]
            if isinstance(authors, list):
                authors = ", ".join(authors[:3])
            context_info += f"\n作者: {authors}"

    prompt = f"""分析以下从 PDF 提取的论文标题，判断其是否准确，并给出修正建议。

原始标题: {raw_title}
{context_info}

请分析：
1. 标题是否包含多余的页眉/页脚信息？
2. 标题是否有 OCR 错误或格式问题？
3. 标题是否完整？

返回 JSON 格式：
```json
{{
  "is_valid": true,
  "refined_title": "修正后的标题",
  "confidence": 0.8,
  "search_keywords": ["关键词1", "关键词2"]
}}
```

重要规则：
- 如果标题已经准确，refined_title 保持原样
- 如果需要修正，只输出修正后的标题核心部分
- 不要添加任何引号或多余符号
- 如果无法判断，返回空字符串 refined_title=""
"""

    try:
        response = llm_client.extract_concepts(prompt)

        # 解析 JSON 响应
        json_match = re.search(r"```json\s*(.+?)\s*```", response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(1))
        else:
            # 尝试直接解析
            result = json.loads(response.strip())

        refined = result.get("refined_title", "").strip()

        # 验证修正结果
        confidence = result.get("confidence", 0.5)
        if refined and len(refined) >= 5 and confidence >= 0.5:
            # 清理可能的引号
            refined = refined.strip("\"'")
            return refined

    except Exception as e:
        logger.warning(f"LLM title refinement failed: {e}")

    return ""


def clean_title(title: str) -> str:
    """
    清洗论文标题，移除无关文本，提高搜索匹配率

    处理：
    1. 移除会议/期刊信息
    2. 移除特殊 Unicode 字符
    3. 移除页眉页脚信息
    4. 保留核心标题部分
    """
    if not title:
        return title

    original_title = title

    # 检测并过滤无效的页眉标题
    invalid_patterns = [
        r"^Contents lists available at ScienceDirect",
        r"^Contents lists available at",
        r"^Available online at",
        r"^ScienceDirect",
        r"^Elsevier",
        r"^IEEE Transactions on",
        r"^IEEE ",
        r"^Springer",
        r"^ACM ",
        r"^Nature$",
        r"^Science$",
        r"^\d{4}\s*$",
        r"^Vol\.\s*\d+",
        r"^pp\.\s*\d+",
    ]
    for pattern in invalid_patterns:
        if re.match(pattern, title, re.IGNORECASE):
            return ""

    # Unicode 连字符映射
    unicode_replacements = {
        "\ufb00": "ff",
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\ufb03": "ffi",
        "\ufb04": "ffl",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2015": "-",
    }

    for uni_char, replacement in unicode_replacements.items():
        title = title.replace(uni_char, replacement)

    # 尝试提取标题核心部分
    match = re.search(r"Published as a conference paper at \w+ \d{4}\s+(.+)", title, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
    else:
        patterns_to_remove_at_start = [
            r"^Published as a conference paper at[^,]+,?\s*",
            r"^Published in[^,]+,?\s*",
            r"^Appears in[^,]+,?\s*",
            r"^\d{4}\s+(IEEE|ACM|AAAI|ICML|NeurIPS|ICLR|ACL|EMNLP|CVPR|ICCV|IJCAI|KDD|WWW|SIGIR)[^,]*,?\s*",
            r"^(IEEE|ACM|AAAI|ICML|NeurIPS|ICLR|ACL|EMNLP|CVPR|ICCV|IJCAI|KDD|WWW|SIGIR)\s+\d{4}[^,]*,?\s*",
            r"^(Springer|Elsevier|Wiley|Taylor\s*&\s*Francis)[^,]*,?\s*",
        ]
        for pattern in patterns_to_remove_at_start:
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)

    # 移除 arXiv 标识
    title = re.sub(r"arXiv:\d+\.\d+(v\d+)?\s*", "", title)
    title = re.sub(r"\[arXiv[^]]*\]\s*", "", title)

    # 移除 DOI
    title = re.sub(r"DOI:\s*[\d./]+\s*", "", title)
    title = re.sub(r"https?://doi\.org/[\d./]+\s*", "", title)

    # 移除版权信息
    title = re.sub(r"©\s*\d{4}[^,]*,?\s*", "", title)
    title = re.sub(r"Copyright\s*[^,]+,?\s*", "", title)

    # 清理多余空格
    title = re.sub(r"\s+", " ", title)
    title = title.strip()

    if len(title) < 5:
        return original_title

    return title


# ============================================================
# 5. 核心 API 客户端
# ============================================================

# 默认字段
DEFAULT_FIELDS = [
    "paperId",
    "title",
    "abstract",
    "year",
    "authors",
    "venue",
    "citationCount",
    "referenceCount",
    "influentialCitationCount",
    "externalIds",
    "s2FieldsOfStudy",
    "openAccessPdf",
    "tldr",
]

SEARCH_FIELDS = [
    "paperId",
    "title",
    "abstract",
    "year",
    "authors",
    "venue",
    "citationCount",
    "openAccessPdf",
    "externalIds",
]


class S2Client:
    """
    Semantic Scholar API 客户端

    使用 semanticscholar 库作为底层实现，
    统一处理限速、缓存、重试。
    """

    def __init__(self, api_key: str = None, rps: float = 1.0, cache_dir: str = ".s2_cache", cache_ttl: int = 604800):
        """
        初始化客户端

        Args:
            api_key: API Key，默认从环境变量 SEMANTIC_SCHOLAR_API_KEY 读取
            rps: 每秒请求数限制
            cache_dir: 缓存目录
            cache_ttl: 缓存过期时间（秒）
        """
        self.api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        self.rps = rps
        self.rate_limiter = RateLimiter(rps)
        self.cache = S2Cache(cache_dir, cache_ttl)

        # 延迟导入 semanticscholar 库
        self._sch = None

    def _get_sch(self):
        """延迟初始化 SemanticScholar 客户端"""
        if self._sch is None:
            try:
                import os

                # 禁用代理，避免代理连接问题
                for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
                    os.environ.pop(k, None)

                from semanticscholar import SemanticScholar

                self._sch = SemanticScholar(api_key=self.api_key, timeout=30)
            except ImportError:
                raise ImportError("semanticscholar library not installed. Run: pip install semanticscholar>=0.11.0")
        return self._sch

    def _with_rate_limit(self, func, *args, **kwargs):
        """带限速的调用"""
        self.rate_limiter.wait()
        return func(*args, **kwargs)

    # ========================================
    # 论文匹配与详情
    # ========================================

    @s2_retry(max_retries=3)
    def match_paper_by_title(self, title: str, llm_client=None, paper_context: dict = None) -> dict | None:
        """
        用论文标题匹配 S2 论文（简化版：信任 S2 搜索排序）

        注意：此方法作为 DOI/arXiv ID 查询的回退方案。
        优先使用 match_paper() 方法，它会先尝试精确匹配。

        Args:
            title: 论文标题
            llm_client: LLM 客户端（可选，用于标题修正）
            paper_context: 论文上下文 {'abstract': ..., 'authors': ...}

        Returns:
            匹配的论文信息，如果匹配失败返回 None
        """
        # 清洗标题
        cleaned = clean_title(title)
        if not cleaned or len(cleaned.strip()) < 3:
            return None

        # 检查缓存
        cache_key = f"match_{hashlib.md5(cleaned.encode()).hexdigest()}"
        cached = self.cache.get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            sch = self._get_sch()

            # 搜索论文
            results = self._with_rate_limit(sch.search_paper, cleaned, fields=DEFAULT_FIELDS, limit=5)

            if not results:
                self.cache.set_cache(cache_key, None)
                return None

            items = list(results)
            if not items:
                self.cache.set_cache(cache_key, None)
                return None

            # 如果只有一个结果，直接返回
            if len(items) == 1:
                result = self._normalize_paper(items[0])
                self.cache.set_cache(cache_key, result)
                return result

            # 多个结果：检查第一个结果是否足够匹配
            first = items[0]
            s2_title = first.title or ""

            # 简单的相似度检查：词集交集
            query_words = set(cleaned.lower().split())
            result_words = set(s2_title.lower().split())
            stop_words = {"a", "an", "the", "for", "of", "and", "in", "on", "to", "with", "is", "are"}
            query_words -= stop_words
            result_words -= stop_words

            if query_words:
                overlap = len(query_words & result_words) / len(query_words)
                # 如果关键词匹配度 >= 50%，信任 S2 排序
                if overlap >= 0.5:
                    result = self._normalize_paper(first)
                    self.cache.set_cache(cache_key, result)
                    return result

                # 匹配度不够，尝试 LLM 修正标题
                if llm_client:
                    refined_title = llm_refine_title(cleaned, llm_client, paper_context)
                    if refined_title and refined_title != cleaned:
                        logger.info(f"LLM refined title: '{cleaned}' -> '{refined_title}'")
                        # 用修正后的标题重新搜索
                        refined_results = self._with_rate_limit(
                            sch.search_paper, refined_title, fields=DEFAULT_FIELDS, limit=5
                        )
                        if refined_results:
                            refined_items = list(refined_results)
                            if refined_items:
                                result = self._normalize_paper(refined_items[0])
                                self.cache.set_cache(cache_key, result)
                                return result

            # 匹配失败
            self.cache.set_cache(cache_key, None)
            return None

        except Exception as e:
            logger.error(f"Failed to match paper by title: {e}")
            return None

    @s2_retry(max_retries=3)
    def get_paper_details(self, paper_id: str) -> dict | None:
        """
        获取论文完整详情

        Args:
            paper_id: S2 paperId 或 DOI（如 "DOI:10.xxxx"）

        Returns:
            论文详情字典
        """
        # 检查缓存
        cache_key = f"detail_{paper_id}"
        cached = self.cache.get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            sch = self._get_sch()
            paper = self._with_rate_limit(sch.get_paper, paper_id, fields=DEFAULT_FIELDS)
            result = self._normalize_paper(paper)
            self.cache.set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error(f"Failed to get paper details: {e}")
            return None

    def match_paper(
        self, title: str = None, doi: str = None, arxiv_id: str = None, llm_client=None, paper_context: dict = None
    ) -> dict | None:
        """
        智能匹配论文（优先 DOI/arXiv ID，回退标题匹配）

        匹配优先级：
        1. DOI 精确查询（100% 准确）
        2. arXiv ID 精确查询（100% 准确）
        3. 标题搜索（可能需要相似度匹配）

        Args:
            title: 论文标题
            doi: DOI 标识符（如 "10.1234/abc123"）
            arxiv_id: arXiv ID（如 "2301.12345"）
            llm_client: LLM 客户端（用于标题修正）
            paper_context: 论文上下文

        Returns:
            匹配的论文信息，失败返回 None
        """
        # 优先级 1: DOI 精确查询
        if doi:
            logger.info(f"Trying DOI lookup: {doi}")
            result = self.get_paper_details(f"DOI:{doi}")
            if result:
                logger.info(f"DOI lookup succeeded: {doi}")
                return result
            logger.warning(f"DOI lookup failed: {doi}")

        # 优先级 2: arXiv ID 精确查询
        if arxiv_id:
            logger.info(f"Trying arXiv lookup: {arxiv_id}")
            # arXiv ID 格式：ARXIV:2301.12345
            result = self.get_paper_details(f"ARXIV:{arxiv_id}")
            if result:
                logger.info(f"arXiv lookup succeeded: {arxiv_id}")
                return result
            logger.warning(f"arXiv lookup failed: {arxiv_id}")

        # 优先级 3: 标题搜索
        if title:
            logger.info(f"Trying title search: {title[:50]}...")
            return self.match_paper_by_title(title, llm_client=llm_client, paper_context=paper_context)

        return None

    # ========================================
    # 引用关系
    # ========================================

    @s2_retry(max_retries=3)
    def get_paper_citations(self, paper_id: str, limit: int = 100) -> list[dict]:
        """
        获取引用了这篇论文的论文列表（被引）

        Args:
            paper_id: S2 paperId
            limit: 返回数量限制

        Returns:
            论文列表，每项包含：paperId, title, year, citationCount, authors
        """
        cache_key = f"citations_{paper_id}_{limit}"
        cached = self.cache.get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            sch = self._get_sch()
            citations = self._with_rate_limit(
                sch.get_paper_citations,
                paper_id,
                fields=["paperId", "title", "year", "citationCount", "authors"],
                limit=limit,
            )

            result = []
            if citations is not None:
                for item in citations:
                    # Citation 对象的 paper 属性包含论文信息
                    paper = getattr(item, "paper", None)
                    if paper:
                        result.append(
                            {
                                "paperId": paper.paperId if hasattr(paper, "paperId") else None,
                                "title": paper.title if hasattr(paper, "title") else None,
                                "year": paper.year if hasattr(paper, "year") else None,
                                "citationCount": paper.citationCount if hasattr(paper, "citationCount") else 0,
                                "authors": [{"name": a.name} for a in paper.authors]
                                if hasattr(paper, "authors") and paper.authors
                                else [],
                            }
                        )

            self.cache.set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error(f"Failed to get paper citations: {e}")
            return []

    @s2_retry(max_retries=3)
    def get_paper_references(self, paper_id: str, limit: int = 100) -> list[dict]:
        """
        获取这篇论文引用的论文列表（参考文献）

        Args:
            paper_id: S2 paperId
            limit: 返回数量限制

        Returns:
            论文列表
        """
        cache_key = f"references_{paper_id}_{limit}"
        cached = self.cache.get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            sch = self._get_sch()
            references = self._with_rate_limit(
                sch.get_paper_references,
                paper_id,
                fields=["paperId", "title", "year", "citationCount", "authors"],
                limit=limit,
            )

            result = []
            if references is not None:
                for item in references:
                    # Reference 对象的 paper 属性包含论文信息
                    paper = getattr(item, "paper", None)
                    if paper:
                        result.append(
                            {
                                "paperId": paper.paperId if hasattr(paper, "paperId") else None,
                                "title": paper.title if hasattr(paper, "title") else None,
                                "year": paper.year if hasattr(paper, "year") else None,
                                "citationCount": paper.citationCount if hasattr(paper, "citationCount") else 0,
                                "authors": [{"name": a.name} for a in paper.authors]
                                if hasattr(paper, "authors") and paper.authors
                                else [],
                            }
                        )

            self.cache.set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error(f"Failed to get paper references: {e}")
            return []

    # ========================================
    # 搜索与推荐
    # ========================================

    @s2_retry(max_retries=3)
    def search_papers(self, query: str, year: str = None, limit: int = 20, min_citation_count: int = 0) -> list[dict]:
        """
        关键词搜索论文

        Args:
            query: 搜索关键词
            year: 年份范围（如 "2024-2026"）
            limit: 最大返回数
            min_citation_count: 最低引用数过滤

        Returns:
            论文列表
        """
        # 搜索结果缓存 TTL 缩短为 24 小时
        cache_key = f"search_{hashlib.md5(query.encode()).hexdigest()}_{year}_{limit}"
        cached = self.cache.get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            sch = self._get_sch()

            params = {"query": query, "fields": SEARCH_FIELDS, "limit": limit}
            if year:
                params["year"] = year

            results = self._with_rate_limit(sch.search_paper, **params)

            # results 是 PaginatedResults 对象，使用 .items 获取论文列表
            items = results.items if hasattr(results, "items") else list(results)

            papers = []
            for p in items:
                paper = self._normalize_paper(p)
                # 过滤引用数
                if min_citation_count > 0:
                    if paper.get("citationCount", 0) < min_citation_count:
                        continue
                papers.append(paper)

            # 使用 24 小时 TTL 缓存
            self.cache.set_cache(cache_key, papers)

            return papers

        except Exception as e:
            logger.error(f"Failed to search papers: {e}")
            return []

    def _get_demo_papers(self, query: str, limit: int = 10) -> list[dict]:
        """返回模拟论文数据用于演示"""
        demo_papers = [
            {
                "paperId": f"demo_{hashlib.md5(f'{query}_{i}'.encode()).hexdigest()[:12]}",
                "title": f"Advances in {query} - Research Paper {i + 1}",
                "abstract": f"This paper presents novel approaches to {query}, demonstrating significant improvements in performance and efficiency. We propose a new framework that achieves state-of-the-art results on multiple benchmarks.",
                "year": 2024 - (i % 3),
                "authors": [{"name": f"Author {chr(65 + i)}"}, {"name": f"Author {chr(66 + i)}"}],
                "venue": ["NeurIPS", "ICML", "ACL", "EMNLP", "ICLR"][i % 5],
                "citationCount": 100 - i * 10,
                "openAccessPdf": {"url": f"https://example.com/paper_{i}.pdf"} if i % 2 == 0 else None,
                "tldr": {"text": f"A novel approach to {query} with improved performance."},
            }
            for i in range(min(limit, 10))
        ]
        return demo_papers

    @s2_retry(max_retries=3)
    def get_recommendations(self, paper_ids: list[str], limit: int = 20) -> list[dict]:
        """
        基于给定论文列表推荐相关论文

        Args:
            paper_ids: 最多 5 个 S2 paperId 作为正例
            limit: 返回数量

        Returns:
            推荐论文列表
        """
        if not paper_ids:
            return []

        # 最多 5 个
        paper_ids = paper_ids[:5]

        cache_key = f"recs_{'_'.join(sorted(paper_ids))}_{limit}"
        cached = self.cache.get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            sch = self._get_sch()

            results = self._with_rate_limit(
                sch.get_recommended_papers_from_lists, positive_paper_ids=paper_ids, fields=SEARCH_FIELDS, limit=limit
            )

            papers = [self._normalize_paper(p) for p in results]

            self.cache.set_cache(cache_key, papers)
            return papers

        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return []

    # ========================================
    # 批量操作
    # ========================================

    @s2_retry(max_retries=3)
    def batch_get_papers(self, paper_ids: list[str]) -> list[dict]:
        """
        批量获取论文详情（一次最多 500 个）

        Args:
            paper_ids: S2 paperId 列表

        Returns:
            论文详情列表
        """
        if not paper_ids:
            return []

        # 限制最多 500 个
        paper_ids = paper_ids[:500]

        try:
            sch = self._get_sch()

            papers = self._with_rate_limit(sch.get_papers, paper_ids, fields=DEFAULT_FIELDS)

            return [self._normalize_paper(p) for p in papers]

        except Exception as e:
            logger.error(f"Failed to batch get papers: {e}")
            return []

    # ========================================
    # 作者
    # ========================================

    @s2_retry(max_retries=3)
    def get_author(self, author_id: str) -> dict | None:
        """
        获取作者详情

        Args:
            author_id: S2 authorId

        Returns:
            作者信息：name, hIndex, citationCount, paperCount, affiliations
        """
        cache_key = f"author_{author_id}"
        cached = self.cache.get_cache(cache_key)
        if cached is not None:
            return cached

        try:
            sch = self._get_sch()

            author = self._with_rate_limit(
                sch.get_author, author_id, fields=["name", "hIndex", "citationCount", "paperCount", "affiliations"]
            )

            result = {
                "authorId": author.authorId,
                "name": author.name,
                "hIndex": author.hIndex,
                "citationCount": author.citationCount,
                "paperCount": author.paperCount,
                "affiliations": author.affiliations or [],
            }

            self.cache.set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error(f"Failed to get author: {e}")
            return None

    # ========================================
    # 工具方法
    # ========================================

    def _normalize_paper(self, paper) -> dict:
        """标准化论文数据"""
        # 处理 externalIds
        external_ids = {}
        if hasattr(paper, "externalIds") and paper.externalIds:
            external_ids = dict(paper.externalIds)

        # 处理 authors
        authors = []
        if hasattr(paper, "authors") and paper.authors:
            authors = [{"authorId": a.authorId, "name": a.name} for a in paper.authors if a.name]

        # 处理 tldr
        tldr = None
        if hasattr(paper, "tldr") and paper.tldr:
            if hasattr(paper.tldr, "text"):
                tldr = paper.tldr.text
            else:
                tldr = str(paper.tldr)

        # 处理 openAccessPdf
        open_access_pdf = None
        if hasattr(paper, "openAccessPdf") and paper.openAccessPdf:
            if hasattr(paper.openAccessPdf, "url"):
                open_access_pdf = paper.openAccessPdf.url
            elif isinstance(paper.openAccessPdf, dict):
                open_access_pdf = paper.openAccessPdf.get("url")

        # 处理 s2FieldsOfStudy
        fields_of_study = []
        if hasattr(paper, "s2FieldsOfStudy") and paper.s2FieldsOfStudy:
            for f in paper.s2FieldsOfStudy:
                if isinstance(f, dict):
                    fields_of_study.append(f.get("category", ""))
                else:
                    fields_of_study.append(str(f))

        return {
            "paperId": paper.paperId,
            "externalIds": external_ids,
            "title": paper.title,
            "abstract": paper.abstract,
            "year": paper.year,
            "authors": authors,
            "venue": paper.venue if hasattr(paper, "venue") else None,
            "citationCount": paper.citationCount if hasattr(paper, "citationCount") else 0,
            "referenceCount": paper.referenceCount if hasattr(paper, "referenceCount") else 0,
            "influentialCitationCount": paper.influentialCitationCount
            if hasattr(paper, "influentialCitationCount")
            else 0,
            "tldr": {"text": tldr} if tldr else None,
            "s2FieldsOfStudy": fields_of_study,
            "openAccessPdf": {"url": open_access_pdf} if open_access_pdf else None,
        }

    @staticmethod
    def test_connection(api_key: str) -> dict:
        """
        测试 API Key 是否有效

        Returns:
            {"success": bool, "message": str}
        """
        try:
            from semanticscholar import SemanticScholar

            sch = SemanticScholar(api_key=api_key, timeout=10)

            # 用已知论文测试
            paper = sch.get_paper("649def34f8be52c8b66281af98ae884c09aef38b", fields=["title"])

            if paper and paper.title:
                return {"success": True, "message": "API Key 有效"}
            else:
                return {"success": False, "message": "API 响应异常"}

        except Exception as e:
            error_str = str(e).lower()
            if "401" in error_str or "unauthorized" in error_str:
                return {"success": False, "message": "API Key 无效"}
            elif "rate limit" in error_str or "429" in error_str:
                return {"success": False, "message": "请求频率超限，请稍后重试"}
            else:
                return {"success": False, "message": f"连接失败: {str(e)}"}


# ============================================================
# 兼容旧 API
# ============================================================

# 保留旧的类名作为别名
SemanticScholarClient = S2Client
