# Chat 页面论文上传功能设计

**日期：** 2026-04-02
**状态：** 待审核

---

## 概述

在 AI 对话页面（Chat）添加 PDF 论文上传功能，支持用户：
1. 拖拽上传论文，AI 感知上传内容并回答相关问题
2. 通过自然语言对话管理论文文件夹

---

## 功能需求

### 1. 拖拽上传

- 位置：Chat 页面底部，输入框上方
- 交互：用户拖拽 PDF 文件到页面时显示上传区域
- 支持：单文件 / 多文件上传
- 格式：仅接受 `.pdf`

### 2. 智能论文问答

- 上传后自动添加到论文库（pending 状态）
- AI 可回答关于论文内容的问题
- 混合读取策略：摘要快速回答 + 按需读取全文

### 3. 文件夹管理

- 默认上传到"全部论文"文件夹
- AI 提示用户可移动到其他文件夹
- 支持自然语言创建文件夹、移动论文

---

## 架构设计

### 前端组件

```
Chat.tsx
├── DragUploadZone (新增)
│   ├── 拖拽检测
│   ├── 上传进度
│   └── 上传成功提示
├── MessageList
├── InputArea
└── ...
```

### 后端 Agent 架构

```
Lead Agent
├── Citation Agent (现有) - 引用分析
├── Research Agent (现有) - 研究点分析
├── Deep Research Agent (现有) - 深入研究
├── Paper QA Agent (新增) - 论文内容问答
└── Move Paper Handler (新增) - 文件夹移动
```

---

## 详细设计

### 1. 拖拽上传区域

**视觉设计：**
- 高度：120px
- 边框：虚线，暖色调 (amber)
- 内容：图标 + 提示文字"拖放 PDF 文件到此处上传"
- 背景：半透明渐变

**状态流转：**
```
默认隐藏 → 检测到拖拽 → 显示上传区域 → 松开鼠标 → 上传中 → 成功/失败
```

**上传成功后：**
1. 调用 `/api/papers/upload` 接口
2. 设置 `currentTarget` 为上传的论文
3. AI 发送提示消息：
   - 单文件："已上传论文《XXX》，你可以问我关于这篇论文的问题。"
   - 多文件："已上传 N 篇论文：《A》、《B》... 你可以问我关于这些论文的问题。"
4. 提示："默认存放在"全部论文"文件夹，需要移动到其他文件夹请告诉我。"

### 2. Context Summary 扩展

```typescript
interface ContextSummary {
  currentTarget?: {
    type: 'concept' | 'paper'
    id: string
    name: string
  }
  uploadedPapers?: Array<{
    doi: string
    title: string
  }>
  // ... 其他现有字段
}
```

### 3. Paper QA Agent

**触发条件：**
- 用户使用"这篇论文"、"刚才上传的论文"等代词
- 用户询问论文相关内容（"讲了什么"、"创新点"等）

**读取策略：**

| 问题类型 | 数据来源 | 响应速度 |
|----------|----------|----------|
| 论文概述 | 存储的摘要 | 快 |
| 关键词/作者 | 存储的元数据 | 快 |
| 具体章节内容 | PDF 全文 | 较慢 |
| 创新点分析 | PDF 全文 + LLM 分析 | 较慢 |

**实现：**
```python
class PaperQAAgent:
    def __init__(self, llm_client, db, pdf_parser):
        self.llm_client = llm_client
        self.db = db
        self.pdf_parser = pdf_parser

    def answer(self, question: str, paper_doi: str) -> str:
        paper = self.db.get_paper(paper_doi)

        # 判断问题类型
        if self._is_simple_question(question):
            # 基于存储内容回答
            return self._answer_from_metadata(question, paper)
        else:
            # 读取 PDF 全文回答
            full_text = self.pdf_parser.extract_text(paper['pdf_path'])
            return self._answer_from_fulltext(question, paper, full_text)
```

### 4. 文件夹移动处理

**意图识别：**
- "移动到XXX文件夹"
- "把这篇论文放到XXX"
- "新建文件夹叫XXX"

**处理流程：**

```
用户请求移动论文
    ↓
Lead Agent 识别意图 → move_paper
    ↓
检查目标文件夹是否存在
    ├─ 存在 → 调用 PATCH /api/papers/{doi}/folder
    └─ 不存在 → 询问是否新建
           ├─ 确认 → POST /api/folders 创建 → 再移动
           └─ 取消 → 结束
```

---

## API 变更

### 现有 API（无需修改）

| API | 用途 |
|-----|------|
| `POST /api/papers/upload` | 上传论文 |
| `GET /api/folders` | 获取文件夹列表 |
| `POST /api/folders` | 创建文件夹 |
| `PATCH /api/papers/{doi}/folder` | 移动论文到文件夹 |

### Agent 扩展

**意图类型新增：**
```python
class IntentType(Enum):
    CITATION = "citation"
    RESEARCH = "research"
    DEEP_RESEARCH = "deep_research"
    MERGE = "merge"
    LEAD = "lead"
    PAPER_QA = "paper_qa"      # 新增
    MOVE_PAPER = "move_paper"  # 新增
```

---

## 实现文件清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `frontend/src/pages/Chat.tsx` | 修改 | 添加拖拽上传区域 |
| `frontend/src/components/DragUploadZone.tsx` | 新增 | 拖拽上传组件 |
| `frontend/src/stores/agentStore.ts` | 修改 | 添加 uploadedPapers 状态 |
| `mkg/agent/lead_agent.py` | 修改 | 添加 paper_qa、move_paper 意图识别 |
| `mkg/agent/paper_qa_agent.py` | 新增 | 论文内容问答 Agent |
| `mkg/agent/prompts.py` | 修改 | 添加相关 prompt |

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 大 PDF 读取耗时 | 异步处理 + 加载提示 |
| 上传失败 | 错误提示 + 重试按钮 |
| 意图识别错误 | 置信度判断 + 确认机制 |

---

## 测试场景

1. **单文件上传**：拖拽一个 PDF，验证上传成功、AI 提示正确
2. **多文件上传**：拖拽多个 PDF，验证全部上传、提示包含所有论文
3. **论文问答**：上传后询问"这篇论文讲什么"，验证回答正确
4. **文件夹移动**：说"移动到机器学习文件夹"，验证移动成功
5. **新建文件夹**：说"新建文件夹叫深度学习并移动"，验证创建+移动