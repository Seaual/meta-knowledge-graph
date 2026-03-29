"""
Semantic Scholar API 客户端
"""

import requests
import time
import json
import re
from typing import Optional, Dict, List


def clean_title(title: str) -> str:
    """
    清洗论文标题，移除无关文本，提高搜索匹配率

    处理：
    1. 移除会议/期刊信息（如 "Published as a conference paper at ICLR 2024"）
    2. 移除特殊 Unicode 字符（如连字符 ﬂ, ﬁ 等）
    3. 移除页眉页脚信息
    4. 保留核心标题部分
    """
    if not title:
        return title

    original_title = title

    # Unicode 连字符映射
    unicode_replacements = {
        '\ufb00': 'ff',  # ﬀ
        '\ufb01': 'fi',  # ﬁ
        '\ufb02': 'fl',  # ﬂ
        '\ufb03': 'ffi', # ﬃ
        '\ufb04': 'ffl', # ﬄ
        '\u2010': '-',   # ‐
        '\u2011': '-',   # ‑
        '\u2012': '-',   # ‒
        '\u2013': '-',   # –
        '\u2014': '-',   # —
        '\u2015': '-',   # ―
    }

    for uni_char, replacement in unicode_replacements.items():
        title = title.replace(uni_char, replacement)

    # 尝试提取标题核心部分（通常是大写字母开头的部分或冒号后的部分）
    # 策略：如果标题包含 "Published as a conference paper at XXX YEAR TITLE"，
    # 尝试提取 TITLE 部分

    # 模式1: "Published as a conference paper at VENUE YEAR TITLE"
    match = re.search(r'Published as a conference paper at \w+ \d{4}\s+(.+)', title, re.IGNORECASE)
    if match:
        title = match.group(1).strip()
    else:
        # 模式2: "YEAR CONFERENCE NAME (ACRONYM) TITLE"
        match = re.search(r'^\d{4}\s+[\w/]+\s+Conference[^)]+\)\s*(.+)', title, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
        else:
            # 模式3: 移除开头的会议信息
            patterns_to_remove_at_start = [
                r'^Published as a conference paper at[^,]+,?\s*',
                r'^Published in[^,]+,?\s*',
                r'^Appears in[^,]+,?\s*',
                r'^\d{4}\s+(IEEE|ACM|AAAI|ICML|NeurIPS|ICLR|ACL|EMNLP|CVPR|ICCV)[^,]*,?\s*',
                r'^(IEEE|ACM|AAAI|ICML|NeurIPS|ICLR|ACL|EMNLP|CVPR|ICCV)\s+\d{4}[^,]*,?\s*',
            ]

            for pattern in patterns_to_remove_at_start:
                title = re.sub(pattern, '', title, flags=re.IGNORECASE)

    # 移除 arXiv 标识
    title = re.sub(r'arXiv:\d+\.\d+(v\d+)?\s*', '', title)
    title = re.sub(r'\[arXiv[^]]*\]\s*', '', title)

    # 移除 DOI
    title = re.sub(r'DOI:\s*[\d./]+\s*', '', title)

    # 移除版权信息
    title = re.sub(r'©\s*\d{4}[^,]*,?\s*', '', title)
    title = re.sub(r'Copyright\s*[^,]+,?\s*', '', title)

    # 清理多余空格
    title = re.sub(r'\s+', ' ', title)
    title = title.strip()

    # 如果清洗后太短或为空，返回原标题（已处理Unicode）
    if len(title) < 5:
        return original_title

    return title.strip()


class SemanticScholarClient:
    """Semantic Scholar API 客户端"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"x-api-key": api_key}
        self.last_request_time = 0

    def _wait_for_rate_limit(self):
        """速率限制：1 request/second"""
        elapsed = time.time() - self.last_request_time
        if elapsed < 1.1:
            time.sleep(1.1 - elapsed)
        self.last_request_time = time.time()

    def search_by_title(self, title: str) -> Optional[Dict]:
        """
        用标题搜索论文，返回最佳匹配结果

        Args:
            title: 论文标题

        Returns:
            匹配的论文信息，包含：
            - paperId: S2 论文 ID
            - title: 标题
            - abstract: 摘要
            - authors: 作者列表
            - year: 发表年份
            - venue: 期刊/会议
            - citationCount: 引用数
            - referenceCount: 参考文献数
            - influentialCitationCount: 影响力引用数
            - openAccessPdf: 开放获取 PDF 信息
        """
        # 清洗标题
        cleaned_title = clean_title(title)

        if not cleaned_title or len(cleaned_title.strip()) < 3:
            return None

        self._wait_for_rate_limit()

        params = {
            "query": cleaned_title,
            "fields": "paperId,title,abstract,authors,year,venue,citationCount,referenceCount,influentialCitationCount,openAccessPdf",
            "limit": 5  # 获取多个结果，选择最佳匹配
        }

        try:
            response = requests.get(
                f"{self.BASE_URL}/paper/search/bulk",
                params=params,
                headers=self.headers,
                timeout=10
            )

            if response.status_code != 200:
                return None

            data = response.json()
            if not data.get("data"):
                return None

            results = data["data"]
            if len(results) == 1:
                return results[0]

            # 多个结果时，选择标题最匹配的
            # 使用简单的词重叠率来匹配
            def title_similarity(s2_title: str) -> float:
                """计算标题相似度"""
                if not s2_title:
                    return 0.0
                # 提取关键词
                query_words = set(cleaned_title.lower().split())
                result_words = set(s2_title.lower().split())
                # 移除常见停用词
                stop_words = {'a', 'an', 'the', 'for', 'of', 'and', 'in', 'on', 'to', 'with', 'is', 'are'}
                query_words -= stop_words
                result_words -= stop_words
                if not query_words:
                    return 0.0
                # 计算重叠率
                overlap = len(query_words & result_words)
                return overlap / len(query_words)

            # 按相似度排序，选择最匹配的
            best_match = max(results, key=lambda r: title_similarity(r.get('title', '')))
            return best_match

        except Exception as e:
            print(f"Semantic Scholar API error: {e}")
            return None

    def enhance_paper_data(self, title: str, existing_data: Optional[Dict] = None) -> Dict:
        """
        增强论文数据

        Args:
            title: 论文标题
            existing_data: 已有的论文数据（用于合并）

        Returns:
            增强后的论文数据字典
        """
        s2_result = self.search_by_title(title)

        result = existing_data.copy() if existing_data else {}

        if s2_result:
            # 只在 S2 有数据时覆盖
            result['s2_paper_id'] = s2_result.get('paperId')

            if s2_result.get('abstract'):
                result['abstract'] = s2_result['abstract']

            if s2_result.get('authors'):
                result['authors'] = [a['name'] for a in s2_result['authors'] if 'name' in a]

            if s2_result.get('venue'):
                result['venue'] = s2_result['venue']

            if s2_result.get('year'):
                result['year'] = s2_result['year']

            if s2_result.get('citationCount') is not None:
                result['citation_count'] = s2_result['citationCount']

            if s2_result.get('referenceCount') is not None:
                result['reference_count'] = s2_result['referenceCount']

            if s2_result.get('influentialCitationCount') is not None:
                result['influential_citation_count'] = s2_result['influentialCitationCount']

            if s2_result.get('openAccessPdf'):
                result['open_access_pdf'] = json.dumps(s2_result['openAccessPdf'])

        return result

    @staticmethod
    def test_connection(api_key: str) -> Dict:
        """
        测试 API Key 是否有效

        Returns:
            {"success": bool, "message": str}
        """
        headers = {"x-api-key": api_key}

        try:
            # 使用 paper details 端点测试，更可靠
            # 使用一个已知的论文 ID 进行测试
            response = requests.get(
                "https://api.semanticscholar.org/graph/v1/paper/649def34f8be52c8b66281af98ae884c09aef38b",
                params={"fields": "title"},
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                return {"success": True, "message": "API Key 有效"}
            elif response.status_code == 401:
                return {"success": False, "message": "API Key 无效"}
            else:
                return {"success": False, "message": f"请求失败: {response.status_code}"}

        except Exception as e:
            return {"success": False, "message": f"连接失败: {str(e)}"}