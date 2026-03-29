"""
Semantic Scholar API 客户端
"""

import requests
import time
import json
from typing import Optional, Dict, List


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
        用标题搜索论文，返回第一个匹配结果

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
        if not title or len(title.strip()) < 3:
            return None

        self._wait_for_rate_limit()

        params = {
            "query": title,
            "fields": "paperId,title,abstract,authors,year,venue,citationCount,referenceCount,influentialCitationCount,openAccessPdf",
            "limit": 1
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

            return data["data"][0]

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
            response = requests.get(
                "https://api.semanticscholar.org/graph/v1/paper/search/bulk",
                params={"query": "test", "limit": 1},
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