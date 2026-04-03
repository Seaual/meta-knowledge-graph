# Semantic Scholar API 申请说明

## 英文版本（直接提交用）

---

I am an independent developer building an open-source academic knowledge graph tool called **Meta Knowledge Graph (MKG)**. The project automatically extracts hierarchical concepts from PDF papers and visualizes them as interactive force-directed graphs. It is available on GitHub at https://github.com/Seaual/meta-knowledge-graph.

### Endpoints and Fields Needed

**Paper Search & Retrieval:**
- `/paper/search` - Search papers by keywords, DOI, or authors to expand paper collection beyond manual PDF uploads
- `/paper/{paper_id}` - Retrieve paper metadata (title, authors, abstract, year, venue, citationCount, referenceCount, fieldsOfStudy)
- `/paper/{paper_id}/references` - Fetch reference list to build citation relationships in the knowledge graph
- `/paper/{paper_id}/citations` - Fetch citing papers to identify research trends and impact
- `/author/{author_id}` - Retrieve author profiles and publication history

**Fields:**
- Core: paperId, title, abstract, authors, year, venue, citationCount
- References: paperId, title, authors (for building citation graph)
- External identifiers: externalIds (DOI, ArXiv) for paper linking and deduplication

### Expected Usage

Currently, my project processes papers uploaded manually by users. I plan to integrate Semantic Scholar as an automated paper discovery layer:

- **Initial Phase**: Starting with ~300-500 API calls per month for testing and development
- **Production Phase**: Gradually scaling to ~2,000-5,000 calls per month as the user base grows
- **Peak Usage**: Batch operations during literature review sessions (e.g., importing 50-100 related papers at once)

### Efficiency Strategy

I will structure requests efficiently by:
1. **Local caching** - Store retrieved metadata in SQLite database to avoid duplicate calls for the same paper
2. **Selective fields** - Request only necessary fields to reduce payload size
3. **Client-side rate limiting** - Implement throttling to stay within API limits
4. **Batch processing** - Group related queries when possible to minimize request count

### Future Roadmap

1. **Semantic Paper Discovery** - Allow users to discover related papers through Semantic Scholar recommendations, automatically enriching the knowledge graph
2. **Citation Network Visualization** - Build a citation network layer showing how papers relate through citations
3. **Research Trend Analysis** - Use citation counts and year data to identify emerging research directions
4. **Author Network Integration** - Connect concepts to author expertise, helping users identify key researchers in specific fields
5. **DOI-based Deduplication** - Use externalIds to detect duplicate papers uploaded by different users
6. **Neo4j Migration** - Plan to migrate from SQLite to Neo4j for better graph querying, with Semantic Scholar data populating the citation graph layer

This API integration will transform MKG from a manual paper-upload tool into an intelligent research assistant that can automatically discover, connect, and analyze academic knowledge.

---

## 中文版本（备用参考）

---

我是一名独立开发者，正在开发一个开源的学术知识图谱工具 **Meta Knowledge Graph (MKG)**。该项目可以自动从 PDF 论文中提取层次化概念并可视化为交互式力导向图。项目已发布在 GitHub：https://github.com/Seaual/meta-knowledge-graph。

### 需要的 API 端点和字段

**论文搜索与获取：**
- `/paper/search` - 通过关键词、DOI 或作者搜索论文，扩展论文收集渠道
- `/paper/{paper_id}` - 获取论文元数据（标题、作者、摘要、年份、期刊、引用数、参考文献数、研究领域）
- `/paper/{paper_id}/references` - 获取参考文献列表，构建知识图谱中的引用关系
- `/paper/{paper_id}/citations` - 获取引用论文，识别研究趋势和影响力
- `/author/{author_id}` - 获取作者信息和发表历史

**字段需求：**
- 核心：paperId、title、abstract、authors、year、venue、citationCount
- 参考文献：paperId、title、authors（用于构建引用图谱）
- 外部标识：externalIds（DOI、ArXiv）用于论文链接和去重

### 预期使用量

- **开发测试期**：每月约 300-500 次 API 调用
- **生产期**：随用户增长，逐步扩展到每月 2,000-5,000 次
- **峰值**：文献综述批量导入时（如一次性导入 50-100 篇相关论文）

### 效率策略

1. 本地 SQLite 缓存，避免重复请求同一论文
2. 只请求必要字段减少传输量
3. 客户端限速遵守 API 限制
4. 尽量批量处理减少请求数

### 未来计划

1. **语义论文发现** - 用户可通过 Semantic Scholar 推荐发现相关论文
2. **引用网络可视化** - 在概念图谱上叠加引用关系层
3. **研究趋势分析** - 利用引用数和年份识别热门研究方向
4. **作者网络** - 将概念关联到作者专长领域
5. **DOI 去重** - 利用 externalIds 检测重复论文
6. **Neo4j 迁移** - 从 SQLite 迁移到 Neo4j，Semantic Scholar 数据将填充引用图谱层

---

## 备注

如果申请失败，可以调整以下内容后重新申请：
- 进一步降低用量估算
- 强调是个人研究项目而非商业用途
- 简化申请内容，只保留核心用途说明