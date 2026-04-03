# Chat PDF Upload Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add drag-and-drop PDF upload to Chat page with AI-powered paper Q&A and folder management.

**Architecture:** Frontend drag zone triggers existing upload API, sets context for AI. New Paper QA Agent answers paper questions. Lead Agent dispatches to paper_qa and move_paper intents.

**Tech Stack:** React, Zustand, FastAPI, LiteLLM, PDFParser

---

## File Structure

```
frontend/src/
├── components/
│   └── DragUploadZone.tsx       # NEW - Drag & drop upload component
├── pages/
│   └── Chat.tsx                 # MODIFY - Add drag zone integration
├── stores/
│   └── agentStore.ts            # MODIFY - Add uploadedPapers state
└── lib/
    └── api.ts                   # EXISTING - papersApi.upload

backend/routes/
└── agent.py                     # MODIFY - Add paper_qa, move_paper dispatch

mkg/agent/
├── lead_agent.py                # MODIFY - Add new intent handlers
├── paper_qa_agent.py            # NEW - Paper Q&A agent
└── prompts.py                   # MODIFY - Add paper_qa, move_paper prompts
```

---

### Task 1: Create DragUploadZone Component

**Files:**
- Create: `frontend/src/components/DragUploadZone.tsx`

- [ ] **Step 1: Create the component file with full implementation**

```tsx
// frontend/src/components/DragUploadZone.tsx
import { useState, useCallback, useRef } from 'react'
import { Upload, FileText, X, Loader2 } from 'lucide-react'
import { papersApi } from '../lib/api'

interface UploadedPaper {
  doi: string
  title: string
}

interface DragUploadZoneProps {
  onUploadSuccess: (papers: UploadedPaper[]) => void
  onUploadError: (error: string) => void
}

export default function DragUploadZone({ onUploadSuccess, onUploadError }: DragUploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const dragCounterRef = useRef(0)

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    dragCounterRef.current++
    if (e.dataTransfer.types.includes('Files')) {
      setIsDragging(true)
    }
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    dragCounterRef.current--
    if (dragCounterRef.current === 0) {
      setIsDragging(false)
    }
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    dragCounterRef.current = 0

    const files = Array.from(e.dataTransfer.files).filter(
      file => file.type === 'application/pdf'
    )

    if (files.length === 0) {
      onUploadError('请上传 PDF 文件')
      return
    }

    setIsUploading(true)
    setUploadProgress(0)

    const uploadedPapers: UploadedPaper[] = []
    const totalFiles = files.length

    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      try {
        const res = await papersApi.upload(file)
        if (res.data?.success && res.data?.doi) {
          uploadedPapers.push({
            doi: res.data.doi,
            title: res.data.title || file.name,
          })
        }
      } catch (err: any) {
        console.error(`Upload failed for ${file.name}:`, err)
      }
      setUploadProgress(Math.round(((i + 1) / totalFiles) * 100))
    }

    setIsUploading(false)
    setUploadProgress(0)

    if (uploadedPapers.length > 0) {
      onUploadSuccess(uploadedPapers)
    } else {
      onUploadError('上传失败，请重试')
    }
  }, [onUploadSuccess, onUploadError])

  if (!isDragging && !isUploading) {
    return null
  }

  return (
    <div
      className="absolute inset-0 z-50 flex items-center justify-center"
      style={{
        background: 'rgba(250, 248, 245, 0.95)',
        backdropFilter: 'blur(4px)',
      }}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      <div
        className="w-full max-w-md mx-4 p-8 rounded-2xl text-center"
        style={{
          border: '2px dashed rgba(184, 134, 11, 0.4)',
          background: 'rgba(255, 254, 249, 0.8)',
        }}
      >
        {isUploading ? (
          <>
            <Loader2 className="w-12 h-12 mx-auto mb-4 animate-spin" style={{ color: 'var(--color-amber)' }} />
            <p className="font-body text-sm" style={{ color: 'var(--color-sepia)' }}>
              上传中... {uploadProgress}%
            </p>
          </>
        ) : (
          <>
            <Upload className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--color-amber)' }} />
            <p className="font-display text-lg mb-2" style={{ color: 'var(--color-sepia)' }}>
              拖放 PDF 文件到此处上传
            </p>
            <p className="font-body text-sm" style={{ color: 'var(--color-muted)' }}>
              支持单个或多个 PDF 文件
            </p>
          </>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/DragUploadZone.tsx
git commit -m "feat: add DragUploadZone component for PDF upload

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Update agentStore with uploadedPapers State

**Files:**
- Modify: `frontend/src/stores/agentStore.ts`

- [ ] **Step 1: Add uploadedPapers to ContextSummary and state**

Update the ContextSummary interface and add the new action:

```typescript
// In ContextSummary interface, add after currentTarget:
export interface ContextSummary {
  currentTarget?: {
    type: 'concept' | 'paper'
    id: string
    name: string
  }
  uploadedPapers?: Array<{
    doi: string
    title: string
  }>
  contextTags: string[]
  keyFindings: string[]
  intentHistory: string[]
  lastActiveAgent: 'lead' | 'citation' | 'research' | 'deep_research' | 'paper_qa'
}
```

- [ ] **Step 2: Update currentAgent type**

```typescript
// In Message interface and AgentState:
currentAgent: 'lead' | 'citation' | 'research' | 'deep_research' | 'merge' | 'paper_qa'
```

- [ ] **Step 3: Add addUploadedPapers action to interface**

```typescript
// In AgentState interface, add after setLoading:
addUploadedPapers: (papers: Array<{ doi: string; title: string }>) => void
clearUploadedPapers: () => void
```

- [ ] **Step 4: Implement the actions in the store**

```typescript
// In the create function, add after resetResearch:
addUploadedPapers: (papers) => set((state) => ({
  contextSummary: {
    ...state.contextSummary,
    uploadedPapers: [...(state.contextSummary.uploadedPapers || []), ...papers],
  },
})),

clearUploadedPapers: () => set((state) => ({
  contextSummary: {
    ...state.contextSummary,
    uploadedPapers: [],
  },
})),
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/agentStore.ts
git commit -m "feat: add uploadedPapers state to agentStore

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Integrate DragUploadZone into Chat Page

**Files:**
- Modify: `frontend/src/pages/Chat.tsx`

- [ ] **Step 1: Add import and use the store**

Add at the top of the file after existing imports:

```typescript
import DragUploadZone from '../components/DragUploadZone'
```

- [ ] **Step 2: Get addUploadedPapers from store**

Update the useAgentStore destructuring:

```typescript
const {
  messages,
  isLoading,
  contextSummary,
  addMessage,
  setLoading,
  setCurrentAgent,
  updateContext,
  addUploadedPapers,
} = useAgentStore()
```

- [ ] **Step 3: Add upload handlers**

Add before the return statement:

```typescript
// Handle upload success
const handleUploadSuccess = useCallback((papers: Array<{ doi: string; title: string }>) => {
  addUploadedPapers(papers)

  // Set the last uploaded paper as current target
  const lastPaper = papers[papers.length - 1]
  updateContext({
    currentTarget: {
      type: 'paper',
      id: lastPaper.doi,
      name: lastPaper.title,
    },
  })

  // Generate AI message
  const titles = papers.map(p => `《${p.title}》`).join('、')
  const message = papers.length === 1
    ? `已上传论文${titles}，你可以问我关于这篇论文的问题。`
    : `已上传 ${papers.length} 篇论文：${titles}。你可以问我关于这些论文的问题。`

  addMessage({
    role: 'assistant',
    content: message + '\n\n默认存放在"全部论文"文件夹，如需移动到其他文件夹请告诉我。',
  })
}, [addUploadedPapers, updateContext, addMessage])

// Handle upload error
const handleUploadError = useCallback((error: string) => {
  addMessage({
    role: 'assistant',
    content: `上传失败：${error}`,
  })
}, [addMessage])
```

- [ ] **Step 4: Add DragUploadZone to JSX**

Wrap the main container with drag detection. Find the outermost div and add:

```tsx
<div className="h-full flex flex-col" style={{ background: 'var(--color-cream)' }}>
  {/* Add drag upload zone */}
  <DragUploadZone
    onUploadSuccess={handleUploadSuccess}
    onUploadError={handleUploadError}
  />
  
  {/* Rest of the component... */}
</div>
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Chat.tsx
git commit -m "feat: integrate DragUploadZone into Chat page

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Create Paper QA Agent

**Files:**
- Create: `mkg/agent/paper_qa_agent.py`

- [ ] **Step 1: Create the Paper QA Agent**

```python
# mkg/agent/paper_qa_agent.py
"""
Paper QA Agent - 回答论文内容相关问题
"""

import os
from typing import Dict, Any, Optional
from .prompts import PAPER_QA_PROMPT


class PaperQAAgent:
    """论文内容问答 Agent"""

    def __init__(self, llm_client, db, pdf_parser=None):
        """
        初始化 Paper QA Agent

        Args:
            llm_client: LLM 客户端
            db: Database 实例
            pdf_parser: PDFParser 实例（可选，用于读取全文）
        """
        self.llm_client = llm_client
        self.db = db
        self.pdf_parser = pdf_parser

        # 简单问题关键词（基于元数据回答）
        self.simple_keywords = [
            '讲什么', '关于什么', '摘要', '关键词', '作者',
            '发表', '期刊', '会议', '年份', '标题',
            '是什么', '简介', '概述',
        ]

    def answer(self, question: str, paper_doi: str) -> Dict[str, Any]:
        """
        回答关于论文的问题

        Args:
            question: 用户问题
            content: 论文 DOI

        Returns:
            包含回答的字典
        """
        # 获取论文信息
        paper = self.db.get_paper(paper_doi)
        if not paper:
            return {'error': f'未找到论文: {paper_doi}'}

        # 判断问题类型
        is_simple = self._is_simple_question(question)

        if is_simple and self._has_metadata(paper):
            # 基于存储的元数据回答
            return self._answer_from_metadata(question, paper)
        else:
            # 读取 PDF 全文回答
            return self._answer_from_fulltext(question, paper)

    def _is_simple_question(self, question: str) -> bool:
        """判断是否是简单问题"""
        question_lower = question.lower()
        return any(kw in question_lower for kw in self.simple_keywords)

    def _has_metadata(self, paper: Dict) -> bool:
        """检查论文是否有足够的元数据"""
        return bool(paper.get('abstract') or paper.get('title'))

    def _answer_from_metadata(self, question: str, paper: Dict) -> Dict[str, Any]:
        """基于元数据回答"""
        # 构建上下文
        context = f"""论文信息：
标题：{paper.get('title', '未知')}
作者：{', '.join(paper.get('authors') or [])}
发表年份：{paper.get('year', '未知')}
期刊/会议：{paper.get('venue', '未知')}
关键词：{', '.join(paper.get('keywords') or [])}
引用数：{paper.get('citation_count', 0)}

摘要：
{paper.get('abstract', '无摘要')}
"""
        if paper.get('tldr'):
            context += f"\nTL;DR: {paper['tldr']}"

        prompt = PAPER_QA_PROMPT.format(
            question=question,
            context=context,
            paper_title=paper.get('title', '未知'),
        )

        try:
            response = self.llm_client.generate(prompt)
            return {
                'answer': response,
                'source': 'metadata',
                'paper_title': paper.get('title'),
            }
        except Exception as e:
            return {'error': f'回答生成失败: {str(e)}'}

    def _answer_from_fulltext(self, question: str, paper: Dict) -> Dict[str, Any]:
        """读取 PDF 全文回答"""
        pdf_path = paper.get('pdf_path')
        if not pdf_path or not os.path.exists(pdf_path):
            # 回退到元数据回答
            if self._has_metadata(paper):
                return self._answer_from_metadata(question, paper)
            return {'error': '无法访问论文全文'}

        try:
            # 读取 PDF 全文
            from mkg.pdf_parser import PDFParser
            if not self.pdf_parser:
                self.pdf_parser = PDFParser()

            full_text = self.pdf_parser.extract_text(pdf_path)

            # 截取前 10000 字符（避免过长）
            if len(full_text) > 10000:
                full_text = full_text[:10000] + '...(内容过长，已截断)'

            context = f"""论文信息：
标题：{paper.get('title', '未知')}
作者：{', '.join(paper.get('authors') or [])}

论文内容：
{full_text}
"""
            prompt = PAPER_QA_PROMPT.format(
                question=question,
                context=context,
                paper_title=paper.get('title', '未知'),
            )

            response = self.llm_client.generate(prompt)
            return {
                'answer': response,
                'source': 'fulltext',
                'paper_title': paper.get('title'),
            }

        except Exception as e:
            return {'error': f'读取论文失败: {str(e)}'}

    def format_response(self, result: Dict[str, Any]) -> str:
        """格式化响应"""
        if 'error' in result:
            return result['error']

        answer = result.get('answer', '')
        source = result.get('source', 'metadata')
        source_note = '（基于论文摘要）' if source == 'metadata' else '（基于论文全文）'

        return f"{answer}\n\n_{source_note}_"
```

- [ ] **Step 2: Commit**

```bash
git add mkg/agent/paper_qa_agent.py
git commit -m "feat: add Paper QA Agent for paper content questions

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Update Prompts for New Agents

**Files:**
- Modify: `mkg/agent/prompts.py`

- [ ] **Step 1: Add paper_qa and move_paper to system prompt**

Update LEAD_AGENT_SYSTEM_PROMPT to include new agents:

```python
LEAD_AGENT_SYSTEM_PROMPT = """<s>
你是 Meta Knowledge Graph 的研究助手协调器。你的任务是理解用户的意图，并决定应该由哪个专业 Agent 来处理。

可用的 Agent：
1. **citation** - 引用分析 Agent
   - 分析论文的引用和被引用关系
   - 触发词：引用、被引、citation、谁引用了、引用了谁

2. **research** - 研究点分析 Agent
   - 分析概念的研究机会
   - 触发词：研究点、研究方向、研究机会、概念分析

3. **deep_research** - 深入研究 Agent
   - 系统化的深入研究，生成完整报告
   - 触发词：深入研究、系统分析、详细研究、全面分析

4. **paper_qa** - 论文问答 Agent
   - 回答关于论文内容的问题
   - 触发词：这篇论文讲了什么、论文内容、论文创新点、论文摘要

5. **move_paper** - 论文移动 Agent
   - 将论文移动到指定文件夹
   - 触发词：移动到、放到、新建文件夹

6. **lead** - 通用对话
   - 一般性问题、帮助说明、澄清问题

**代词处理**：
- 如果用户使用"这篇论文"、"这篇文章"、"这个论文"，target_type 应为 "paper"
- 如果用户使用"这个概念"、"这个节点"、"这个主题"，target_type 应为 "concept"
- 如果上下文中已有 currentTarget，代词引用应使用上下文中的目标名称
</s>

<task>
分析用户消息，识别意图，返回 JSON 格式的决策。
</task>

<output_format>
返回 JSON：
{{
  "intent": "citation | research | deep_research | paper_qa | move_paper | lead",
  "target_type": "paper | concept | null",
  "target_name": "用户提到的论文或概念名称。如果用户使用代词，从上下文中提取实际名称",
  "target_folder": "目标文件夹名称（仅用于 move_paper 意图）",
  "create_folder": true | false（是否需要新建文件夹，仅用于 move_paper）,
  "confidence": 0.0-1.0,
  "reasoning": "简要说明为什么选择这个意图"
}}
</output_format>
"""
```

- [ ] **Step 2: Add PAPER_QA_PROMPT**

Add after existing prompts:

```python
PAPER_QA_PROMPT = """<s>
你是学术论文阅读助手。你需要基于给定的论文内容，回答用户的问题。

回答要求：
1. 准确：只基于论文内容回答，不要编造
2. 简洁：回答要清晰明了，避免冗长
3. 专业：使用学术语言，但易于理解
</s>

<论文标题>
{paper_title}
</论文标题>

<论文内容>
{context}
</论文内容>

<用户问题>
{question}
</用户问题>

请回答用户的问题。如果论文中没有相关信息，请明确说明。
"""
```

- [ ] **Step 3: Commit**

```bash
git add mkg/agent/prompts.py
git commit -m "feat: add paper_qa and move_paper prompts

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 6: Update Lead Agent with New Intent Handlers

**Files:**
- Modify: `mkg/agent/lead_agent.py`

- [ ] **Step 1: Add dispatch_to_paper_qa_agent method**

Add after `dispatch_to_deep_research` method:

```python
def dispatch_to_paper_qa_agent(self, paper_identifier: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """分发到 Paper QA Agent"""
    from .paper_qa_agent import PaperQAAgent
    from mkg.pdf_parser import PDFParser

    # 创建 PDF Parser
    pdf_parser = PDFParser()

    # 创建 Paper QA Agent
    paper_qa_agent = PaperQAAgent(self.llm_client, self.db, pdf_parser)

    # 获取论文 DOI（可能是标题或 DOI）
    paper = self._find_paper(paper_identifier)
    if not paper:
        return {
            'message': f'未找到论文: {paper_identifier}',
            'agent': 'paper_qa',
            'contextUpdate': None
        }

    # 执行问答
    result = paper_qa_agent.answer(context.get('last_question', ''), paper['doi'])

    if 'error' in result:
        return {
            'message': result['error'],
            'agent': 'paper_qa',
            'contextUpdate': None
        }

    formatted = paper_qa_agent.format_response(result)

    return {
        'message': formatted,
        'agent': 'paper_qa',
        'contextUpdate': {
            'currentTarget': {
                'type': 'paper',
                'id': paper['doi'],
                'name': paper.get('title', paper_identifier),
            },
        }
    }

def dispatch_to_move_paper(self, paper_identifier: str, target_folder: str,
                           create_folder: bool, context: Dict[str, Any]) -> Dict[str, Any]:
    """处理论文移动请求"""
    # 获取论文
    paper = self._find_paper(paper_identifier)
    if not paper:
        return {
            'message': f'未找到论文: {paper_identifier}',
            'agent': 'lead',
            'contextUpdate': None
        }

    # 查找目标文件夹
    folders = self.db.get_all_folders()
    target = None
    for folder in folders:
        if folder['name'] == target_folder or folder['id'] == target_folder:
            target = folder
            break

    if not target and create_folder:
        # 创建新文件夹
        folder_id = self.db.create_folder({'name': target_folder})
        target = {'id': folder_id, 'name': target_folder}
    elif not target:
        return {
            'message': f'未找到文件夹「{target_folder}」。需要我新建一个吗？',
            'agent': 'lead',
            'contextUpdate': None
        }

    # 移动论文
    self.db.move_paper_to_folder(paper['doi'], target['id'])

    return {
        'message': f'已将论文《{paper.get("title", paper_identifier)}》移动到文件夹「{target["name"]}」',
        'agent': 'lead',
        'contextUpdate': None
    }

def _find_paper(self, identifier: str) -> Optional[Dict]:
    """查找论文（通过 DOI 或标题）"""
    # 尝试作为 DOI 查找
    paper = self.db.get_paper(identifier)
    if paper:
        return paper

    # 尝试模糊匹配标题
    papers = self.db.get_papers_by_status('processed')
    papers.extend(self.db.get_papers_by_status('pending'))

    for p in papers:
        if identifier.lower() in (p.get('title') or '').lower():
            return p

    return None
```

- [ ] **Step 2: Update recognize_intent to handle new intents**

Update the pronoun patterns list:

```python
# 更新代词模式
pronoun_patterns = ['这篇论文', '这篇文章', '这个论文', '这个概念', '这个节点', '这个主题', '刚才上传的论文', '上传的论文']

# 在意图判断中添加 paper_qa 和 move_paper
if intent_result.target_name is None and current_target_obj:
    if intent_result.intent in ['citation', 'research', 'deep_research', 'paper_qa']:
        intent_result.target_name = current_target_obj.get('name')
        intent_result.target_type = current_target_obj.get('type')
```

- [ ] **Step 3: Commit**

```bash
git add mkg/agent/lead_agent.py
git commit -m "feat: add paper_qa and move_paper dispatch to Lead Agent

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 7: Update Agent Router Endpoint

**Files:**
- Modify: `backend/routes/agent.py`

- [ ] **Step 1: Import new agent and add dispatch handlers**

Find the `chat` function and add handling for new intents:

```python
# In the chat function, after getting intent_result:

if intent_result.get('intent') == 'paper_qa':
    # Get the question from user message
    paper_name = intent_result.get('target_name')
    if paper_name:
        # Store the question for the agent
        context_with_question = {**request.context.model_dump(), 'last_question': request.message}
        result = lead_agent.dispatch_to_paper_qa_agent(paper_name, context_with_question)
        return {
            'message': result['message'],
            'agent': result['agent'],
            'contextUpdate': result.get('contextUpdate'),
        }

elif intent_result.get('intent') == 'move_paper':
    paper_name = intent_result.get('target_name')
    target_folder = intent_result.get('target_folder', '')
    create_folder = intent_result.get('create_folder', False)
    
    if paper_name:
        result = lead_agent.dispatch_to_move_paper(
            paper_name, target_folder, create_folder, request.context.model_dump()
        )
        return {
            'message': result['message'],
            'agent': result['agent'],
            'contextUpdate': result.get('contextUpdate'),
        }
```

- [ ] **Step 2: Commit**

```bash
git add backend/routes/agent.py
git commit -m "feat: add paper_qa and move_paper routing in agent endpoint

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 8: Update Backend Schemas

**Files:**
- Modify: `backend/schemas.py`

- [ ] **Step 1: Add new agent types to ContextSummary**

Update ContextSummary to include uploadedPapers:

```python
class ContextSummary(BaseModel):
    """Agent context summary for chat requests"""
    currentTarget: Optional[dict] = None
    uploadedPapers: Optional[List[dict]] = None  # NEW
    contextTags: List[str] = []
    keyFindings: List[str] = []
    intentHistory: List[str] = []
    lastActiveAgent: str = 'lead'
```

- [ ] **Step 2: Commit**

```bash
git add backend/schemas.py
git commit -m "feat: add uploadedPapers to ContextSummary schema

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Self-Review Checklist

| Spec Requirement | Task | Status |
|------------------|------|--------|
| Drag-and-drop upload | Task 1, 3 | ✅ |
| Single/multi file support | Task 1 | ✅ |
| AI notification after upload | Task 3 | ✅ |
| uploadedPapers state | Task 2 | ✅ |
| Paper QA Agent | Task 4 | ✅ |
| Hybrid reading strategy | Task 4 | ✅ |
| Folder move intent | Task 5, 6 | ✅ |
| Backend routing | Task 7 | ✅ |

**Placeholder Scan:** No TBD, TODO, or vague requirements found.

**Type Consistency:** All agent types, method names, and state properties are consistent across tasks.

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-02-chat-pdf-upload.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**