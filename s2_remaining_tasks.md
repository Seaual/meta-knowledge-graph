# S2 集成剩余任务 — Claude Code 实施方案

> 前提：任务 1（S2 客户端）、任务 2（数据库 Schema）、任务 3（PDF 匹配）已完成。
> 下面是任务 4（引用网络）、任务 5（论文推荐）、任务 6（研究点增强）的具体实施方案。

---

## 任务 4：引用网络

### 它是什么

用户上传了 27 篇论文。这些论文之间互相引用（论文 A 的参考文献里有论文 B）。
引用网络就是把这些引用关系画成一张图：
- 节点 = 论文
- 有向边 = A 引用了 B（箭头从 A 指向 B）
- 节点大小 = 被引次数越多越大

### 数据从哪来

S2 API 提供两个端点：
- `get_paper_references(paperId)` → 这篇论文引用了哪些论文（它的参考文献列表）
- `get_paper_citations(paperId)` → 哪些论文引用了这篇论文

对图谱中每篇已匹配 S2 的论文调用这两个端点，就拿到了全部引用关系。

### 4.1 后端：拉取引用数据

请创建 `openclaw/citation_graph.py`：

```python
"""
引用网络构建模块。

核心流程：
1. 从 papers 表查出所有 s2_paper_id 不为空的论文
2. 对每篇论文：
   a. 调 s2_client.get_paper_references(s2_paper_id) → 拿到它引用了谁
   b. 对每条引用关系，检查被引论文是否也在我们的 papers 表中
      - 如果是（两篇都在图谱里）→ is_internal = True
      - 如果不是（被引论文不在图谱里）→ is_internal = True, 但只保存基本信息
   c. 写入 paper_citations 表

注意事项：
- 1 RPS 限速，27 篇论文大约需要 27 秒
- 用 logger 打印进度（"Processing 3/27: xxx"）
- 出错跳过该论文，继续下一篇
- 用 INSERT OR IGNORE 避免重复插入
"""

from openclaw.s2_client import S2Client
from openclaw.database import get_db
import logging

logger = logging.getLogger("openclaw.citations")

def build_citation_network():
    """
    主函数：为所有已匹配 S2 的论文构建引用网络。
    
    步骤：
    1. 查 papers 表，获取所有 s2_paper_id IS NOT NULL 的论文
    2. 构建一个 s2_paper_id → paper_id 的映射表（用于后面判断 is_internal）
    3. 遍历每篇论文：
       a. 调 s2_client.get_paper_references(s2_paper_id)
       b. 对每条 reference：
          - 如果 reference.paperId 在映射表中 → is_internal=True, cited_paper_id=映射表[paperId]
          - 如果不在 → is_internal=False, cited_paper_id=NULL
       c. 插入 paper_citations 表
    4. 返回统计信息：处理了多少论文，找到多少内部引用边
    """
    pass

def get_citation_graph_data():
    """
    获取前端渲染引用图谱所需的数据。
    
    只返回 is_internal=True 的边（两端都在用户图谱中的引用关系）。
    
    返回格式：
    {
        "nodes": [
            {
                "id": "paper_id",
                "title": "论文标题",
                "year": 2024,
                "citation_count": 42,
                "s2_paper_id": "xxx"
            },
            ...
        ],
        "edges": [
            {
                "source": "paper_id_1",   -- 引用者
                "target": "paper_id_2",    -- 被引者
            },
            ...
        ]
    }
    
    SQL 参考：
    -- 获取所有内部引用边
    SELECT 
        c.citing_paper_id, c.cited_paper_id,
        p1.title as source_title, p2.title as target_title
    FROM paper_citations c
    JOIN papers p1 ON c.citing_paper_id = p1.id
    JOIN papers p2 ON c.cited_paper_id = p2.id
    WHERE c.is_internal = 1
    
    -- 获取涉及到的论文节点
    SELECT DISTINCT id, title, publication_year, citation_count, s2_paper_id
    FROM papers
    WHERE id IN (
        SELECT citing_paper_id FROM paper_citations WHERE is_internal = 1
        UNION
        SELECT cited_paper_id FROM paper_citations WHERE is_internal = 1
    )
    """
    pass

def get_paper_citation_context(paper_id: str):
    """
    获取单篇论文的引用上下文。
    
    返回格式：
    {
        "references": [   -- 这篇论文引用了谁
            {"title": "...", "year": 2023, "citation_count": 100, "is_internal": True},
            ...
        ],
        "cited_by": [     -- 谁引用了这篇论文（在图谱中的）
            {"title": "...", "year": 2025, "citation_count": 5, "is_internal": True},
            ...
        ],
        "total_references": 35,  -- 总引用数（包括不在图谱中的）
        "total_cited_by": 8,     -- 总被引数
        "internal_references": 5, -- 图谱内的引用数
        "internal_cited_by": 2    -- 图谱内的被引数
    }
    """
    pass
```

### 4.2 后端：API 路由

在 `backend/routes/` 中新增（可以加到 `graph.py` 或创建 `s2.py`）：

```python
# POST /api/citations/build
# 触发引用网络构建
# 因为是耗时操作（27篇约30秒），有两种实现方式：
#   方式A（简单）：同步执行，前端显示 loading
#   方式B（更好）：后台任务 + SSE 推送进度
# 建议先用方式A，后续优化为方式B
# 响应：{"status": "ok", "papers_processed": 27, "internal_edges": 15}

# GET /api/citations/graph
# 返回引用图谱数据（调用 get_citation_graph_data）
# 响应格式同上面的 get_citation_graph_data 返回值

# GET /api/papers/{paper_id}/citation-context
# 返回单篇论文的引用上下文（调用 get_paper_citation_context）
```

### 4.3 前端：引用图谱视图

在现有的概念图谱页面上添加一个视图切换：

```
实现思路：

1. 在图谱页面顶部添加两个 tab 按钮：
   [概念图谱] [引用图谱]
   
   默认显示概念图谱（当前已有的）。
   点击"引用图谱"时：
   - 调用 GET /api/citations/graph 获取数据
   - 用同一个 force-graph 组件渲染，但数据不同

2. 引用图谱的渲染规则：
   - 节点 = 论文
   - 节点标签 = 论文标题的前 20 个字 + "..."
   - 节点大小 = Math.max(5, Math.sqrt(citation_count) * 2)
     （被引越多越大，但用 sqrt 避免差距太大）
   - 节点颜色 = 按 year 映射到颜色梯度
     2020及以前 → 灰色
     2021-2022 → 浅蓝
     2023-2024 → 蓝色
     2025-2026 → 亮绿色（最新的最醒目）
   - 边 = 有向箭头（从引用者指向被引者）
   - 边颜色 = 浅灰色

3. 交互：
   - 点击论文节点 → 右侧面板显示：
     - 论文标题、作者、年份、venue
     - 被引次数
     - TLDR 摘要
     - 引用了图谱中的哪些论文（列表）
     - 被图谱中哪些论文引用（列表）
   
4. 首次打开引用图谱 tab 时：
   - 检查 paper_citations 表是否有数据
   - 如果没有 → 显示"构建引用网络"按钮
   - 点击按钮 → 调用 POST /api/citations/build
   - 显示 loading（"正在从 Semantic Scholar 拉取引用关系..."）
   - 完成后自动渲染图谱
```

---

## 任务 5：论文推荐

### 它是什么

用户图谱里有 27 篇论文，系统基于这些论文推荐"你应该还要读的论文"。

### 5.1 后端

在 `backend/routes/` 中新增：

```python
# GET /api/recommendations
# 
# 实现逻辑：
# 
# Step 1: 从 papers 表获取所有有 s2_paper_id 的论文
# Step 2: 按 citation_count 降序排列，取前 5 篇的 s2_paper_id
#         （选最有影响力的作为推荐种子）
# Step 3: 调用 s2_client.get_recommendations(top5_ids, limit=30)
# Step 4: 过滤掉已在图谱中的论文
#         （用 s2_paper_id 与 papers 表对比）
# Step 5: 按 citation_count 降序排列返回前 20 篇
#
# 响应格式：
{
    "recommendations": [
        {
            "s2_paper_id": "abc123",
            "title": "Attention Is All You Need",
            "abstract": "We propose a new simple network architecture...",
            "year": 2017,
            "citation_count": 90000,
            "tldr": "The dominant sequence transduction models are based on...",
            "open_access_pdf_url": "https://arxiv.org/pdf/1706.03762",
            "authors": [{"name": "Ashish Vaswani"}, ...],
            "venue": "NeurIPS"
        },
        ...
    ],
    "based_on": [
        {"title": "种子论文1", "citation_count": 500},
        {"title": "种子论文2", "citation_count": 300},
        ...
    ]
}

# GET /api/concepts/{concept_id}/search-papers
#
# 实现逻辑：
#
# Step 1: 从 concepts 表获取概念的 text 字段
# Step 2: 调用 s2_client.search_papers(
#             query=concept_text,
#             year=request.args.get("year", "2023-2026"),
#             limit=request.args.get("limit", 20),
#             min_citation_count=request.args.get("min_citations", 0)
#         )
# Step 3: 过滤掉已在图谱中的论文
# Step 4: 返回结果
#
# 查询参数示例：
#   /api/concepts/abc/search-papers?year=2024-2026&min_citations=5&limit=10
#
# 响应格式同 recommendations，但外层 key 为 "papers"
```

### 5.2 前端

```
两个入口：

入口 1: 图谱页面 → 侧边栏 → "发现论文" 按钮
  - 点击 → 调用 GET /api/recommendations
  - 弹出推荐面板（可以是侧边抽屉或模态框）
  - 显示推荐论文卡片列表，每张卡片包含：
    - 标题（加粗）
    - 年份 | venue | 被引 {N} 次
    - TLDR 一句话摘要（灰色小字）
    - 两个按钮：
      [下载 PDF 并处理]（如果有 open_access_pdf_url）
      [仅添加元数据]
  - 底部显示 "推荐依据：基于你图谱中被引最高的 5 篇论文"

入口 2: 点击概念节点 → 右侧面板 → "搜索相关论文" 按钮
  - 点击 → 调用 GET /api/concepts/{id}/search-papers
  - 展示搜索结果，卡片格式同上

"下载 PDF 并处理" 按钮的逻辑：
  1. 前端调用后端接口，传入 open_access_pdf_url
  2. 后端下载 PDF 到 papers/pending/ 目录
  3. 自动触发论文处理流程（PyMuPDF + S2 匹配 + LLM 提取）
  4. 处理完成后图谱自动更新

"仅添加元数据" 按钮的逻辑：
  1. 前端调用后端接口，传入 s2_paper_id
  2. 后端在 papers 表创建一条记录，只填 S2 元数据，不做 LLM 提取
  3. 这篇论文会出现在论文列表中，但不会有概念树
  4. 它的引用关系仍然会在引用图谱中显示
```

---

## 任务 6：增强研究点发现

### 它是什么

你现在的研究点发现完全靠 LLM 根据图谱拓扑"猜"。
增强后，LLM 在"猜"之前会先看到 S2 提供的真实数据：
- 这个方向每年发多少论文？（热度）
- 平均被引多少次？（影响力）
- 最近两年是增长还是下降？（趋势）
- 最高被引的论文是什么？（标杆）

这些数据让 LLM 的建议从"可能有意义"变成"数据支撑下有意义"。

### 具体改动

找到 `backend/routes/concepts.py` 中的研究点发现函数（大约在第 304 行附近），做以下修改：

```python
# 在现有的 prompt 构建逻辑中，找到组装 context 的部分。
# 在 ancestors/descendants/siblings 等图谱信息之后，追加 S2 数据：

from openclaw.s2_client import S2Client
import json

def get_s2_field_analysis(concept_text: str) -> str:
    """
    用 S2 搜索该概念相关论文，计算领域热度统计。
    返回一段文本，直接追加到 LLM prompt 的 context 中。
    """
    s2 = S2Client()
    
    try:
        results = s2.search_papers(
            query=concept_text,
            year="2020-2026",
            limit=100
        )
    except Exception as e:
        logger.warning(f"S2 search failed for '{concept_text}': {e}")
        return "\n（Semantic Scholar 数据暂不可用）\n"
    
    if not results:
        return f"\n## 领域热度数据\n未在 Semantic Scholar 中找到 \"{concept_text}\" 的相关论文。这可能是一个较新或较冷门的方向——如果是，这本身就是研究机会。\n"
    
    # 1. 基本统计
    total = len(results)
    recent = len([p for p in results if (p.get("year") or 0) >= 2024])
    citations = [p.get("citationCount", 0) for p in results]
    avg_citations = sum(citations) / total if total > 0 else 0
    
    # 2. 找最高被引论文
    top_paper = max(results, key=lambda p: p.get("citationCount", 0))
    
    # 3. 按年分组
    by_year = {}
    for p in results:
        y = p.get("year")
        if y and y >= 2020:
            by_year[y] = by_year.get(y, 0) + 1
    
    # 4. 判断趋势
    years = sorted(by_year.keys())
    if len(years) >= 3:
        recent_2yr = sum(by_year.get(y, 0) for y in years[-2:]) / 2
        earlier_avg = sum(by_year.get(y, 0) for y in years[:-2]) / max(len(years) - 2, 1)
        if recent_2yr > earlier_avg * 1.3:
            trend = "上升（近两年论文数明显增多）"
        elif recent_2yr < earlier_avg * 0.7:
            trend = "下降（近两年论文数减少）"
        else:
            trend = "平稳"
    else:
        trend = "数据不足，无法判断"
    
    # 5. 找热门子方向（从论文标题中提取高频关键词——简单版）
    # 这一步可选，先不做也行
    
    # 6. 组装文本
    text = f"""
## 领域热度数据（来自 Semantic Scholar，搜索词："{concept_text}"）

- 搜索结果：{total} 篇相关论文
- 2024-2026 年新论文：{recent} 篇（占比 {recent * 100 // max(total, 1)}%）
- 平均引用数：{avg_citations:.1f}
- 年度趋势：{trend}
- 年度论文数分布：{json.dumps(by_year, ensure_ascii=False)}
- 最高被引论文：「{top_paper.get('title', '未知')}」（{top_paper.get('citationCount', 0)} 次引用，{top_paper.get('year', '未知')}年）
"""
    
    # 如果有 TLDR，附上最高被引论文的一句话摘要
    top_tldr = top_paper.get("tldr", {})
    if top_tldr and top_tldr.get("text"):
        text += f"- 该论文摘要：{top_tldr['text']}\n"
    
    return text


# 然后在研究点发现的主函数中调用：

def discover_research_points(concept_id):
    concept = get_concept(concept_id)
    
    # === 已有代码：收集图谱拓扑信息 ===
    ancestors = ...
    descendants = ...
    siblings = ...
    related_papers = ...
    
    # === 新增：S2 领域热度数据 ===
    s2_analysis = get_s2_field_analysis(concept["text"])
    
    # === 组装 prompt ===
    # 在现有 prompt 的 <context> 部分追加 s2_analysis
    # 具体位置：在"相关论文"信息之后，"输出格式"之前
    
    prompt = f"""
... （已有的 system prompt 和 task 定义） ...

<context>
{已有的 ancestors/descendants/siblings 信息}

{已有的 related_papers 信息}

{s2_analysis}
</context>

... （已有的 output_format） ...
"""
    
    # === 调用 LLM 生成研究点（已有代码，不变） ===
    result = call_llm(prompt)
    return result
```

### 效果示例

改动前，LLM 只看到：
```
焦点概念：多智能体强化学习
上游路径：人工智能 → 强化学习 → 多智能体强化学习
下游分支：值分解方法、通信机制、信用分配...
```

改动后，LLM 额外看到：
```
## 领域热度数据（来自 Semantic Scholar）
- 搜索结果：100 篇相关论文
- 2024-2026 年新论文：45 篇（占比 45%）
- 平均引用数：23.4
- 年度趋势：上升（近两年论文数明显增多）
- 年度论文数分布：{"2020": 8, "2021": 10, "2022": 12, "2023": 15, "2024": 20, "2025": 25, "2026": 10}
- 最高被引论文：「QMIX: Monotonic Value Function Factorisation」（1500 次引用，2018年）
```

LLM 就能给出更靠谱的建议：
- "该方向论文数年均增长 30%，说明是热门方向"
- "但值分解方法的最新论文（2025-2026）只占 15%，说明这个子方向增速放缓"
- "通信机制相关论文在 2025 年突然增多，可能是新的增长点"

---

## 执行顺序

```
任务 6（研究点增强）→ 最简单，改动最小，1小时
  ↓
任务 4（引用网络后端）→ 创建 citation_graph.py + API 路由，2小时
  ↓
任务 4（引用网络前端）→ 图谱页面加 tab 切换 + 引用图渲染，2-3小时
  ↓
任务 5（论文推荐后端）→ API 路由，1小时
  ↓
任务 5（论文推荐前端）→ 推荐面板 + 概念搜索按钮，2小时
```

建议先做任务 6（研究点增强），因为改动最小（只改一个函数），但效果最明显。

每个任务完成后输出：修改了哪些文件、改动摘要、如何测试。
