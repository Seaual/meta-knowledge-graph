# S2 深度集成设计规格

## 概述

为 Meta Knowledge Graph 深度集成 Semantic Scholar API，实现：
- 论文元数据自动增强（引用数、venue、TLDR 等）
- 引用网络可视化
- 论文推荐系统
- 增强的研究点发现

---

## 任务 1：S2 客户端封装层

### 文件
`mkg/semantic_scholar.py`（重写）

### 依赖
```
# requirements.txt 新增
semanticscholar>=0.11.0
```

### 核心组件

#### 1. RateLimiter（限速器）
```python
class RateLimiter:
    """1 RPS 限速，线程安全"""
    def __init__(self, rps: float = 1.0)
    def wait(self)  # 调用前等待，确保不超过限制
```

#### 2. CacheManager（本地缓存）
```python
class S2Cache:
    """本地文件缓存"""
    - 缓存目录：`.s2_cache/`
    - 过期时间：7 天（搜索结果 24 小时）
    - get_cache(key) → dict | None
    - set_cache(key, data)
```

#### 3. @s2_retry 装饰器
```python
@s2_retry(max_retries=3)
def api_call(...):
    """
    自动重试逻辑：
    - 429 → sleep 2s 重试
    - 500 → sleep 1s 重试
    - 超过重试次数 → 返回 None
    """
```

#### 4. S2Client 类
```python
class S2Client:
    def __init__(
        self,
        api_key: str = None,  # 默认从环境变量读取
        rps: float = 1.0,
        cache_dir: str = ".s2_cache",
        cache_ttl: int = 604800
    )

    # 核心方法
    def match_paper_by_title(self, title: str) -> Optional[Dict]
    def get_paper_details(self, paper_id: str) -> Optional[Dict]
    def get_paper_citations(self, paper_id: str, limit: int = 100) -> List[Dict]
    def get_paper_references(self, paper_id: str, limit: int = 100) -> List[Dict]
    def search_papers(self, query: str, year: str = None, limit: int = 20, min_citation_count: int = 0) -> List[Dict]
    def get_recommendations(self, paper_ids: List[str], limit: int = 20) -> List[Dict]
    def batch_get_papers(self, paper_ids: List[str]) -> List[Dict]
    def get_author(self, author_id: str) -> Optional[Dict]
```

### 配置文件更新
```bash
# .env.example 新增
SEMANTIC_SCHOLAR_API_KEY=

# .gitignore 新增
.s2_cache/
```

---

## 任务 2：数据库 Schema 扩展

### 文件
`mkg/database.py`（修改）

### papers 表新增字段
```sql
ALTER TABLE papers ADD COLUMN s2_paper_id TEXT;
ALTER TABLE papers ADD COLUMN doi TEXT;
ALTER TABLE papers ADD COLUMN citation_count INTEGER DEFAULT 0;
ALTER TABLE papers ADD COLUMN reference_count INTEGER DEFAULT 0;
ALTER TABLE papers ADD COLUMN influential_citation_count INTEGER DEFAULT 0;
ALTER TABLE papers ADD COLUMN venue TEXT;
ALTER TABLE papers ADD COLUMN publication_year INTEGER;
ALTER TABLE papers ADD COLUMN tldr TEXT;
ALTER TABLE papers ADD COLUMN s2_fields_of_study TEXT;  -- JSON
ALTER TABLE papers ADD COLUMN open_access_pdf_url TEXT;
ALTER TABLE papers ADD COLUMN s2_matched_at TIMESTAMP;
```

### 新表：paper_citations
```sql
CREATE TABLE IF NOT EXISTS paper_citations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    citing_paper_id TEXT NOT NULL,
    cited_paper_id TEXT NOT NULL,
    citing_s2_id TEXT,
    cited_s2_id TEXT,
    cited_title TEXT,
    cited_year INTEGER,
    cited_citation_count INTEGER,
    is_internal BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(citing_paper_id, cited_paper_id)
);
```

### 新表：s2_recommendations
```sql
CREATE TABLE IF NOT EXISTS s2_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_type TEXT NOT NULL,  -- "graph" | "paper" | "concept"
    source_id TEXT NOT NULL,
    recommended_s2_id TEXT NOT NULL,
    recommended_title TEXT,
    recommended_abstract TEXT,
    recommended_year INTEGER,
    recommended_citation_count INTEGER,
    recommended_tldr TEXT,
    recommended_open_access_pdf TEXT,
    score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 迁移策略
- 应用启动时自动执行
- 检查字段/表是否存在，不存在则创建
- 使用 `ALTER TABLE ... ADD COLUMN` 增量迁移

---

## 任务 3：PDF 处理流程集成

### 文件
`mkg/pdf_parser.py`（修改）

### 新流程
```
上传 PDF
  → PyMuPDF 提取标题
  → S2 匹配（新增）
    → 成功：保存 S2 元数据
    → 失败：标记 s2_matched_at=NULL，继续
  → LLM 概念提取
  → 保存到数据库
```

### 代码改动
```python
from mkg.semantic_scholar import S2Client

s2 = S2Client()

async def process_paper(paper_content, existing_graph):
    title = paper_content.title

    # S2 匹配（新增）
    s2_data = s2.match_paper_by_title(title)
    if s2_data:
        update_paper_s2_metadata(paper_id, {
            "s2_paper_id": s2_data["paperId"],
            "doi": s2_data.get("externalIds", {}).get("DOI"),
            "citation_count": s2_data.get("citationCount", 0),
            # ... 其他字段
            "s2_matched_at": datetime.now().isoformat(),
        })

    # LLM 概念提取（不变）
    # ...
```

---

## 任务 4：引用网络构建

### 新文件
`mkg/citation_graph.py`

### 核心函数
```python
def build_citation_graph(db, s2_client):
    """为所有已匹配 S2 的论文拉取引用关系"""

def get_internal_citation_edges(db) -> List[Dict]:
    """获取图谱内部的引用边（is_internal=True）"""

def get_citation_context(db, paper_id: str) -> Dict:
    """获取某篇论文的引用上下文"""
```

### API 路由
文件：`backend/routes/s2.py`（新建）

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/citations/graph` | GET | 返回引用图谱数据（节点+边） |
| `/api/papers/{id}/citations` | GET | 论文引用上下文 |
| `/api/citations/build` | POST | 触发引用网络构建 |
| `/api/papers/{id}/s2-info` | GET | 论文 S2 元数据 |

### 前端：引用图谱视图
- 在概念图谱页面添加切换：「概念图谱」/「引用图谱」
- 节点 = 论文，大小 = citation_count
- 颜色 = 按年份渐变
- 边 = 有向引用关系
- 点击节点显示论文详情

---

## 任务 5：论文推荐系统

### API 路由
文件：`backend/routes/s2.py`

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/recommendations` | GET | 基于图谱论文推荐新论文 |
| `/api/concepts/{id}/search-papers` | GET | 基于概念搜索 S2 论文 |

### 推荐逻辑
1. 获取图谱中所有有 `s2_paper_id` 的论文
2. 按 `citation_count` 降序，取前 5 篇作为正例
3. 调用 `s2_client.get_recommendations(top5_ids, limit=20)`
4. 过滤已在图谱中的论文
5. 返回推荐列表

### 前端
- 图谱页面添加「发现论文」按钮
- 推荐论文卡片：标题、年份、引用数、TLDR、venue
- Open Access PDF → 显示「下载并添加」按钮

---

## 任务 6：增强研究点发现

### 文件
`backend/routes/concepts.py`（修改）

### 改动
在调用 LLM 前，收集 S2 领域热度数据：

```python
# 新增：S2 领域热度数据
s2 = S2Client()
search_results = s2.search_papers(
    concept["text"],
    year="2020-2026",
    limit=100
)

if search_results:
    # 计算统计数据
    total = len(search_results)
    recent = len([p for p in search_results if p.get("year", 0) >= 2024])
    avg_citations = sum(p.get("citationCount", 0) for p in search_results) / total
    trend = "rising" | "declining" | "stable"  # 年度趋势分析

    s2_context = f"""
## 领域热度数据（来自 Semantic Scholar）
- 相关论文：{total} 篇
- 2024-2026 年新论文：{recent} 篇
- 平均引用数：{avg_citations:.1f}
- 年度趋势：{trend}
"""
    # 注入 LLM prompt
```

---

## 执行顺序

| 顺序 | 任务 | 依赖 | 预计时间 |
|------|------|------|----------|
| 1 | 任务 1：S2 客户端 | 无 | 1-2h |
| 2 | 任务 2：数据库 Schema | 无 | 30m |
| 3 | 任务 3：PDF 处理集成 | 任务 1+2 | 1h |
| 4 | 任务 6：研究点增强 | 任务 1 | 1h |
| 5 | 任务 4：引用网络 | 任务 1+2+3 | 2-3h |
| 6 | 任务 5：论文推荐 | 任务 1+2+3 | 2h |

---

## 文件改动总结

| 文件 | 操作 |
|------|------|
| `mkg/semantic_scholar.py` | 重写 |
| `mkg/database.py` | 修改（迁移逻辑） |
| `mkg/pdf_parser.py` | 修改（集成 S2 匹配） |
| `mkg/citation_graph.py` | 新建 |
| `backend/routes/s2.py` | 新建 |
| `backend/routes/concepts.py` | 修改 |
| `requirements.txt` | 修改 |
| `.env.example` | 修改 |
| `.gitignore` | 修改 |