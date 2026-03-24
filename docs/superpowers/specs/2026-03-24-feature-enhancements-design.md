# 知识图谱功能增强设计

**日期**: 2026-03-24
**状态**: 设计评审中

## 概述

本设计涵盖三个功能增强：
1. 优化概念提取提示词，提高准确性
2. 增加批量PDF上传与并行处理
3. 增加Obsidian图谱导出功能

## 1. 概念提取提示词优化

### 1.1 当前问题

现有提示词位于 `openclaw/pdf_parser.py` 的 `_build_extraction_prompt()` 方法。主要问题：
- 概念层级边界不清晰
- 缺少高质量示例引导
- 无自我验证机制

### 1.2 改进方案

#### 提示词结构重构

```
1. 角色定义 + 任务说明
2. 概念层级定义（明确边界）
3. Few-shot 示例
4. 提取要求 + 质量检查清单
5. JSON 输出格式
```

#### 层级定义优化

| 层级 | 英文 | 定义 | 判断标准 | 示例 |
|------|------|------|----------|------|
| 大领域 | field | 学科或研究领域 | 能否包含多个研究方向 | 人工智能、机器学习 |
| 研究方向 | direction | 具体研究方向 | 是否有明确的研究目标 | 强化学习、目标检测 |
| 方法 | method | 可执行的算法或方法 | 能否直接实现 | 近端策略优化、A*算法 |
| 技术 | technique | 技术细节或组件 | 是否是方法的一部分 | 梯度裁剪、注意力机制 |

#### Few-shot 示例

添加1-2个高质量提取示例，展示：
- 正确的层级深度（3-5层）
- 概念命名的规范性
- 边界情况的正确处理

#### 自我验证指令

在提示词末尾添加：
```
输出前请自检：
1. 概念数量是否合理（建议5-15个核心概念）？
2. 层级关系是否正确（子概念是否真正属于父概念）？
3. 是否有遗漏的核心概念？
```

### 1.3 实现位置

- 文件: `openclaw/pdf_parser.py`
- 方法: `LLMConceptExtractor._build_extraction_prompt()`
- 涉及行: 427-523

---

## 2. 批量PDF上传与并行处理

### 2.1 API 设计

#### 新增端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/papers/batch-upload` | POST | 批量上传多个PDF |
| `/api/papers/batch-process` | POST | 并行处理多个论文 |
| `/api/papers/batch-status/{job_id}` | GET | 查询批量任务状态 |

#### 请求/响应格式

**批量上传请求:**
```json
POST /api/papers/batch-upload
Content-Type: multipart/form-data

files: [file1.pdf, file2.pdf, ...]
```

**批量上传响应:**
```json
{
  "job_id": "batch_20240324_001",
  "uploaded": [
    {"doi": "paper1", "title": "...", "status": "pending"},
    {"doi": "paper2", "title": "...", "status": "pending"}
  ],
  "total": 2
}
```

**批量处理请求:**
```json
POST /api/papers/batch-process
{
  "job_id": "batch_20240324_001",
  "dois": ["paper1", "paper2"]
}
```

**批量处理响应:**
```json
{
  "job_id": "batch_20240324_001",
  "status": "processing",
  "total": 2,
  "completed": 1,
  "results": [
    {"doi": "paper1", "status": "success", "concepts": 8},
    {"doi": "paper2", "status": "pending"}
  ]
}
```

### 2.2 并行处理实现

```python
import asyncio
from typing import List

async def process_single_paper(doi: str, db, parser, extractor) -> dict:
    """处理单个论文"""
    paper = db.get_paper(doi)
    content = parser.parse(paper['pdf_path'])
    extracted = extractor.extract(content)
    # ... 保存结果
    return {"doi": doi, "status": "success", "concepts": len(...)}

async def batch_process_papers(dois: List[str]) -> dict:
    """并行处理多个论文"""
    db = get_db()
    parser = get_parser()
    extractor = get_extractor()

    tasks = [process_single_paper(doi, db, parser, extractor) for doi in dois]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    return {
        "total": len(dois),
        "results": results
    }
```

### 2.3 数据库扩展

新增 `batch_jobs` 表：

```sql
CREATE TABLE batch_jobs (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total INTEGER,
    completed INTEGER DEFAULT 0,
    successful INTEGER DEFAULT 0,
    failed INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending'  -- pending, processing, completed, failed
);
```

### 2.4 前端设计

**上传组件:**
- 支持多文件选择 (`<input multiple>`)
- 拖拽上传区域
- 文件列表显示（文件名、大小、状态）

**处理状态:**
- 进度条显示
- 实时状态更新（轮询或WebSocket）
- 成功/失败统计

### 2.5 实现位置

| 文件 | 变更 |
|------|------|
| `backend/routes/papers.py` | 添加批量上传/处理端点 |
| `backend/schemas.py` | 添加批量相关Schema |
| `openclaw/database.py` | 添加batch_jobs表操作 |
| `frontend/src/pages/Papers.tsx` | 添加批量上传UI |

---

## 3. Obsidian 图谱导出

### 3.1 导出格式

导出单个 Markdown 文件，使用 Obsidian 双链格式：

```markdown
# 知识图谱总览

> 生成时间: 2024-03-24 15:30 | 论文: 50 篇 | 概念: 120 个

## 概念层级

### 人工智能
- [[机器学习]]
  - [[深度学习]]
    - [[卷积神经网络]]
    - [[Transformer]]
  - [[强化学习]]

### 运筹学
- [[组合优化]]
  - [[车辆路径问题]]

## 概念详情

### 机器学习
- **类别**: field
- **关联论文**: 15 篇
- **子概念**: [[深度学习]], [[强化学习]], [[监督学习]]
- **描述**: 研究如何让计算机从数据中学习的学科

### 深度学习
- **类别**: direction
- **父概念**: [[机器学习]]
- **关联论文**: 8 篇
- **子概念**: [[卷积神经网络]], [[循环神经网络]]
```

### 3.2 API 设计

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/export/obsidian` | GET | 导出并返回Markdown内容 |
| `/api/export/obsidian/download` | GET | 下载Markdown文件 |

**请求参数:**
```
GET /api/export/obsidian?include_papers=true&max_depth=4
```

**响应:**
```json
{
  "content": "# 知识图谱总览\n...",
  "stats": {
    "papers": 50,
    "concepts": 120,
    "generated_at": "2024-03-24T15:30:00"
  }
}
```

### 3.3 导出器改进

修改现有 `openclaw/obsidian_exporter.py`：

```python
class ObsidianExporter:
    def export_overview(self, db, graph) -> str:
        """导出图谱总览（单个Markdown文件）"""
        concepts = db.get_all_concepts()
        papers = db.get_all_papers()

        lines = []
        lines.append("# 知识图谱总览\n")
        lines.append(f"> 论文: {len(papers)} 篇 | 概念: {len(concepts)} 个\n")

        # 按根概念分组
        root_concepts = self._find_root_concepts(concepts, graph)
        lines.append("## 概念层级\n")
        for root in root_concepts:
            lines.append(self._format_concept_tree(root, db))

        # 概念详情
        lines.append("## 概念详情\n")
        for concept in concepts[:50]:  # 限制数量
            lines.append(self._format_concept_detail(concept, db))

        return "\n".join(lines)
```

### 3.4 实现位置

| 文件 | 变更 |
|------|------|
| `backend/routes/graph.py` | 添加导出端点 |
| `openclaw/obsidian_exporter.py` | 添加 `export_overview()` 方法 |
| `frontend/src/pages/Concepts.tsx` | 添加导出按钮 |

---

## 实现顺序

1. **提示词优化** - 核心功能，影响后续处理质量
2. **批量上传** - 需要前端和后端配合
3. **Obsidian导出** - 相对独立，可最后实现

## 测试要点

### 提示词优化
- 对比优化前后的提取质量
- 测试不同领域论文的提取效果
- 验证 JSON 格式稳定性

### 批量上传
- 测试 10+ 文件并行上传
- 验证并发处理不会导致数据库冲突
- 测试错误处理和重试机制

### Obsidian导出
- 在 Obsidian 中验证双链格式
- 测试大量概念的性能
- 验证导出内容的完整性