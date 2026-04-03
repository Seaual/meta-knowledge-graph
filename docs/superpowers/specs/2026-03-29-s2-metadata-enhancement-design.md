# Semantic Scholar 元数据增强功能设计

## Context

Meta Knowledge Graph 目前依赖用户手动上传 PDF，论文元数据仅来自 PDF 解析（标题、摘要、作者），信息不完整且可能不准确。通过集成 Semantic Scholar API，可以在上传时自动增强元数据，获取更丰富的学术信息（引用数、期刊、年份等），同时为后续的论文发现和推荐功能打下基础。

---

## 功能概述

**上传 PDF 时自动调用 Semantic Scholar API 查询论文信息，增强元数据。**

- 触发时机：PDF 上传后自动执行
- 匹配策略：优先用标题搜索，取第一个匹配结果
- 失败处理：静默跳过，使用 PDF 解析的数据

---

## 数据库扩展

### 新增字段（papers 表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `s2_paper_id` | TEXT | Semantic Scholar 论文 ID（用于后续引用/推荐功能） |
| `venue` | TEXT | 期刊/会议名称 |
| `year` | INTEGER | 发表年份 |
| `citation_count` | INTEGER | 引用数 |
| `reference_count` | INTEGER | 参考文献数 |
| `influential_citation_count` | INTEGER | 影响力引用数 |
| `open_access_pdf` | TEXT | 开放获取 PDF 信息（JSON 格式） |

### 新增配置表（s2_config）

| 字段 | 类型 | 说明 |
|------|------|------|
| `api_key` | TEXT | Semantic Scholar API Key |
| `enabled` | BOOLEAN | 是否启用自动增强 |
| `created_at` | TIMESTAMP | 创建时间 |

---

## 新增模块

### mkg/semantic_scholar.py

```python
class SemanticScholarClient:
    """Semantic Scholar API 客户端"""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"x-api-key": api_key}
        self.last_request_time = 0

    def search_by_title(self, title: str) -> Optional[dict]:
        """用标题搜索论文，返回第一个匹配结果"""
        # 速率限制：1 req/sec
        # 返回字段：paperId, title, abstract, authors, year, venue,
        #           citationCount, referenceCount, influentialCitationCount, openAccessPdf

    def enhance_paper_metadata(self, title: str) -> Optional[dict]:
        """增强论文元数据，返回增强后的字段字典"""
```

### backend/routes/semantic_scholar.py

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/s2/config` | GET | 获取配置状态（是否有 API Key、是否启用） |
| `/api/s2/config` | POST | 保存 API Key 和启用状态 |
| `/api/s2/test` | POST | 测试 API Key 是否有效 |
| `/api/papers/{doi}/enhance` | POST | 手动重新增强指定论文的元数据 |

---

## 上传流程修改

### backend/routes/papers.py - upload_paper

现有流程：
```
上传 PDF → PyMuPDF 解析 → 存入数据库 → 返回结果
```

修改后流程：
```
上传 PDF → PyMuPDF 解析标题 → Semantic Scholar 搜索 → 增强元数据 → 存入数据库 → 返回结果
```

### 具体修改点

1. 在 `upload_paper` 和 `batch_upload_papers` 中，PDF 解析后调用 `SemanticScholarClient.search_by_title`

2. 如果搜索成功，合并增强字段到 paper_data：
   ```python
   if s2_result:
       paper_data.update({
           's2_paper_id': s2_result['paperId'],
           'abstract': s2_result.get('abstract') or paper_data['abstract'],
           'authors': [a['name'] for a in s2_result.get('authors', [])],
           'venue': s2_result.get('venue'),
           'year': s2_result.get('year'),
           'citation_count': s2_result.get('citationCount'),
           'reference_count': s2_result.get('referenceCount'),
           'influential_citation_count': s2_result.get('influentialCitationCount'),
           'open_access_pdf': json.dumps(s2_result.get('openAccessPdf'))
       })
   ```

3. 搜索失败不报错，继续使用 PDF 解析的数据

---

## 前端修改

### 设置页面新增 Semantic Scholar 配置

新建 `frontend/src/components/S2ConfigModal.tsx` 组件：

- API Key 输入框
- 启用/禁用开关
- 测试连接按钮
- 状态显示（已配置/未配置）

在 `frontend/src/App.tsx` 添加入口按钮（与 LLM 配置并列）。

### 论文列表显示增强信息

在 `frontend/src/pages/Papers.tsx` 论文卡片中可选显示：
- 发表年份
- 期刊/会议
- 引用数（可选）

---

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| API Key 未配置 | 静默跳过增强，使用 PDF 数据 |
| 标题搜索无结果 | 静默跳过增强 |
| API 请求失败（网络/超时） | 静默跳过增强 |
| API 速率限制触发 | 等待后重试，或静默跳过 |

---

## 速率限制策略

Semantic Scholar API 限制：1 request/second

实现方式：
```python
def _wait_for_rate_limit(self):
    elapsed = time.time() - self.last_request_time
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)
    self.last_request_time = time.time()
```

批量上传时，每个 PDF 增强请求间隔 1.1 秒。

---

## 验证方式

1. **单元测试**：测试 `SemanticScholarClient.search_by_title` 返回格式
2. **集成测试**：上传 PDF，检查数据库字段是否正确填充
3. **手动测试**：
   - 配置 API Key
   - 上传一篇已知论文（如 Attention is All You Need）
   - 验证元数据是否正确增强
   - 测试无 API Key 时的静默失败行为

---

## 关键文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `mkg/database.py` | 修改 | 新增 papers 表字段、s2_config 表 |
| `mkg/semantic_scholar.py` | 新增 | API 客户端模块 |
| `backend/routes/papers.py` | 修改 | 上传流程集成增强 |
| `backend/routes/semantic_scholar.py` | 新增 | 配置管理路由 |
| `backend/main.py` | 修改 | 注册新路由 |
| `backend/schemas.py` | 修改 | 新增响应模型 |
| `frontend/src/components/S2ConfigModal.tsx` | 新增 | 配置界面组件 |
| `frontend/src/pages/Papers.tsx` | 修改 | 显示增强信息 |
| `frontend/src/App.tsx` | 修改 | 配置入口 |

---

## 后续功能预留

本次实现为后续功能打下基础：

- `s2_paper_id` 字段用于：引用网络、论文推荐
- `open_access_pdf` 字段用于：一键下载开放 PDF
- API Key 配置统一用于后续所有 Semantic Scholar 功能