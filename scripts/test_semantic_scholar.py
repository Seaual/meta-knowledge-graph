"""
Semantic Scholar API 测试脚本
临时文件，用于验证 API 功能和了解返回数据结构
测试完成后可删除
"""

import time

import requests

API_KEY = "HdvhTeK6be5JUDCMKhwXa66QibQ2Qn171FL0Kkns"
BASE_URL = "https://api.semanticscholar.org/graph/v1"

HEADERS = {"x-api-key": API_KEY}


def make_request(endpoint, params=None, method="GET", data=None):
    """发送请求，自动处理速率限制"""
    url = f"{BASE_URL}{endpoint}"

    print(f"\n请求: {method} {endpoint}")
    if params:
        print(f"参数: {params}")

    time.sleep(1.1)  # 速率限制: 1 req/sec

    if method == "GET":
        response = requests.get(url, params=params, headers=HEADERS)
    else:
        response = requests.post(url, params=params, json=data, headers=HEADERS)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"错误: {response.status_code} - {response.text}")
        return None


def print_summary(name, data, key_fields=None):
    """打印数据摘要，避免输出过长"""
    print(f"\n{'='*50}")
    print(f"【{name}】")
    print(f"{'='*50}")

    if data is None:
        print("无数据")
        return

    # 打印顶层结构
    print(f"顶层字段: {list(data.keys())}")

    # 如果有 data 字段，打印条数和第一条摘要
    if "data" in data:
        items = data["data"]
        if items is None:
            print("data 字段为 None（可能该论文没有相关数据）")
        elif len(items) == 0:
            print("返回条数: 0（空列表）")
        else:
            print(f"返回条数: {len(items)}")
            print("第一条完整数据:")
            first = items[0]
            for k, v in first.items():
                if isinstance(v, str) and len(v) > 100:
                    v = v[:100] + "..."
                elif isinstance(v, list):
                    v = f"[{len(v)} items]"
                print(f"  {k}: {v}")

    # 其他常见字段
    if "total" in data:
        print(f"总数估计: {data['total']}")
    if "token" in data:
        print(f"分页token: {data['token'][:20]}..." if data['token'] else "无")

    # 如果是单条数据，打印所有字段
    if "paperId" in data:
        print("完整字段:")
        for k, v in data.items():
            if isinstance(v, str) and len(v) > 100:
                v = v[:100] + "..."
            elif isinstance(v, list):
                v = f"[{len(v)} items]"
            print(f"  {k}: {v}")


def test_paper_search():
    """测试论文搜索"""
    params = {
        "query": '"generative AI"',
        "fields": "title,year,citationCount,authors,openAccessPdf",
        "year": "2022-",  # 稍早一点的论文，更有可能有引用数据
        "limit": 5,
        "sort": "citationCount:desc"  # 按引用数降序排序
    }
    data = make_request("/paper/search/bulk", params)
    print_summary("论文搜索", data, ["paperId", "title", "year", "citationCount"])
    return data


def test_paper_details(paper_id):
    """测试论文详情"""
    params = {
        "fields": "title,abstract,year,venue,citationCount,referenceCount,authors,fieldsOfStudy,openAccessPdf"
    }
    data = make_request(f"/paper/{paper_id}", params)
    print_summary("论文详情", data)
    return data


def test_references(paper_id):
    """测试参考文献"""
    params = {
        "fields": "paperId,title,year,authors",
        "limit": 10
    }
    data = make_request(f"/paper/{paper_id}/references", params)
    print_summary("参考文献", data, ["paperId", "title", "year"])
    return data


def test_citations(paper_id):
    """测试引用论文"""
    params = {
        "fields": "paperId,title,year,citationCount",
        "limit": 10
    }
    data = make_request(f"/paper/{paper_id}/citations", params)
    print_summary("引用论文", data, ["paperId", "title", "year", "citationCount"])
    return data


def test_author_batch(author_ids):
    """测试批量作者信息"""
    params = {
        "fields": "name,url,paperCount,hIndex,citationCount"
    }
    data = make_request("/author/batch", params, method="POST", data={"ids": author_ids})
    print_summary("作者批量查询", data)
    return data


def main():
    print("=" * 60)
    print("Semantic Scholar API 全流程测试")
    print("=" * 60)

    # 1. 论文搜索
    search_result = test_paper_search()

    if not search_result or "data" not in search_result or not search_result["data"]:
        print("\n搜索失败，无法继续后续测试")
        return

    # 取第一篇论文作为后续测试的样本
    sample_paper = search_result["data"][0]
    paper_id = sample_paper["paperId"]
    print(f"\n使用论文 ID: {paper_id} 进行后续测试")
    print(f"论文标题: {sample_paper.get('title', 'N/A')}")

    # 2. 论文详情
    test_paper_details(paper_id)

    # 3. 参考文献
    refs_result = test_references(paper_id)

    # 4. 引用论文
    test_citations(paper_id)

    # 5. 作者批量查询 (从搜索结果中提取作者ID)
    if refs_result and "data" in refs_result and refs_result["data"]:
        author_ids = []
        for ref in refs_result["data"][:4]:
            if "authors" in ref and ref["authors"]:
                for author in ref["authors"][:1]:
                    if "authorId" in author:
                        author_ids.append(author["authorId"])

        if author_ids:
            test_author_batch(author_ids)

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
