# Research Agent Phase 4: Deep Research Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Deep Research Agent with multi-agent architecture, ReAct loops, async execution, and web report generation.

**Architecture:** Deep Research Agent creates a Lead Researcher that spawns Sub-agents for different dimensions. Uses ReAct pattern (Reasoning → Action → Observation) with task contracts. Results stored in database and rendered as web report exportable to MD/PDF.

**Tech Stack:** Python, FastAPI, SQLite, LiteLLM, asyncio, SSE for streaming

---

## File Structure

```
mkg/agent/
├── deep_research_agent.py   # Deep Research Agent implementation
├── research_session.py      # Session management and storage
└── report_generator.py      # Report generation (HTML/MD/PDF)

backend/routes/
└── agent.py                 # Modify deep-research endpoints

frontend/src/components/
└── DeepResearchProgress.tsx # Progress display component
```

---

### Task 1: Create Research Session Model

**Files:**
- Modify: `mkg/database.py`

- [ ] **Step 1: Add research session tables**

Add to `mkg/database.py` (after existing table definitions):

```python
# Research session tables
self.conn.execute("""
CREATE TABLE IF NOT EXISTS research_sessions (
    id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_name TEXT NOT NULL,
    query TEXT,
    status TEXT DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    dimensions TEXT,
    completed_dimensions TEXT DEFAULT '[]',
    report TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

self.conn.execute("""
CREATE TABLE IF NOT EXISTS research_findings (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    finding_type TEXT,
    content TEXT,
    sources TEXT,
    confidence REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES research_sessions(id)
)
""")
```

- [ ] **Step 2: Add session management methods**

Add methods to Database class:

```python
def create_research_session(self, session_id: str, target_type: str, target_id: str, 
                             target_name: str, query: str, dimensions: List[str]) -> None:
    """Create a new research session"""
    self.conn.execute("""
        INSERT INTO research_sessions (id, target_type, target_id, target_name, query, dimensions)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_id, target_type, target_id, target_name, query, json.dumps(dimensions)))
    self.conn.commit()

def get_research_session(self, session_id: str) -> Optional[Dict]:
    """Get research session by ID"""
    row = self.conn.execute("""
        SELECT * FROM research_sessions WHERE id = ?
    """, (session_id,)).fetchone()
    if row:
        return dict(row)
    return None

def update_research_progress(self, session_id: str, progress: int, 
                              completed_dimensions: List[str]) -> None:
    """Update research progress"""
    self.conn.execute("""
        UPDATE research_sessions 
        SET progress = ?, completed_dimensions = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (progress, json.dumps(completed_dimensions), session_id))
    self.conn.commit()

def save_research_finding(self, finding_id: str, session_id: str, dimension: str,
                          finding_type: str, content: str, sources: List[str],
                          confidence: float) -> None:
    """Save a research finding"""
    self.conn.execute("""
        INSERT INTO research_findings (id, session_id, dimension, finding_type, content, sources, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (finding_id, session_id, dimension, finding_type, content, json.dumps(sources), confidence))
    self.conn.commit()

def get_research_findings(self, session_id: str) -> List[Dict]:
    """Get all findings for a session"""
    rows = self.conn.execute("""
        SELECT * FROM research_findings WHERE session_id = ?
        ORDER BY created_at
    """, (session_id,)).fetchall()
    return [dict(row) for row in rows]

def save_research_report(self, session_id: str, report: str) -> None:
    """Save completed research report"""
    self.conn.execute("""
        UPDATE research_sessions 
        SET report = ?, status = 'completed', updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (report, session_id))
    self.conn.commit()
```

- [ ] **Step 3: Commit**

```bash
git add mkg/database.py
git commit -m "feat: add research session tables and methods"
```

---

### Task 2: Create Deep Research Agent

**Files:**
- Create: `mkg/agent/deep_research_agent.py`

- [ ] **Step 1: Create DeepResearchAgent class**

```python
# mkg/agent/deep_research_agent.py
"""
Deep Research Agent - 多维度深入研究
"""

import asyncio
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime


class SubAgent:
    """子代理 - 负责单一维度的研究"""
    
    def __init__(self, dimension: str, llm_client, db, s2_client=None):
        self.dimension = dimension
        self.llm_client = llm_client
        self.db = db
        self.s2_client = s2_client
    
    async def research(self, target: Dict[str, Any], context: str) -> Dict[str, Any]:
        """
        执行单一维度研究
        
        Args:
            target: 研究目标（概念或论文）
            context: 已有上下文
            
        Returns:
            研究发现
        """
        # 构建 ReAct prompt
        prompt = self._build_react_prompt(target, context)
        
        # 执行 ReAct 循环（最多 3 步）
        findings = await self._react_loop(prompt, max_steps=3)
        
        return {
            'dimension': self.dimension,
            'findings': findings,
            'confidence': self._calculate_confidence(findings),
        }
    
    def _build_react_prompt(self, target: Dict, context: str) -> str:
        """构建 ReAct 循环提示词"""
        return f"""<s>
你是研究助理，专注于「{self.dimension}」维度的分析。

目标对象：{target.get('name')} ({target.get('type')})
已有上下文：{context}
</s>

<react_pattern>
按照以下格式思考和行动：
Thought: 思考下一步应该做什么
Action: 选择一个行动（search | analyze | synthesize）
Action_Input: 行动的输入
Observation: 行动的结果（由系统提供）
... (重复直到得出结论)
Final_Answer: 该维度的最终发现
</react_pattern>

<available_actions>
- search: 搜索相关论文或概念（需要关键词）
- analyze: 分析已有数据（需要具体对象）
- synthesize: 综合信息得出结论（需要待综合的内容）
</available_actions>

开始分析！先给出你的第一个 Thought。
"""
    
    async def _react_loop(self, prompt: str, max_steps: int = 3) -> List[Dict]:
        """执行 ReAct 循环"""
        findings = []
        current_prompt = prompt
        
        for step in range(max_steps):
            try:
                response = self.llm_client.generate(current_prompt)
                
                # 解析 Thought/Action/Action_Input
                action_data = self._parse_action(response)
                
                if action_data.get('final_answer'):
                    findings.append({
                        'type': 'conclusion',
                        'content': action_data['final_answer'],
                        'step': step,
                    })
                    break
                
                # 执行 Action
                observation = await self._execute_action(action_data)
                
                # 添加 Observation 到 prompt
                current_prompt = f"{current_prompt}\n\n{response}\nObservation: {observation}"
                
                findings.append({
                    'type': action_data.get('action', 'unknown'),
                    'content': observation,
                    'step': step,
                })
                
            except Exception as e:
                findings.append({
                    'type': 'error',
                    'content': str(e),
                    'step': step,
                })
                break
        
        return findings
    
    def _parse_action(self, response: str) -> Dict:
        """解析 LLM 响应中的 Action"""
        result = {}
        
        lines = response.strip().split('\n')
        for line in lines:
            if line.startswith('Action:'):
                result['action'] = line.replace('Action:', '').strip()
            elif line.startswith('Action_Input:'):
                result['action_input'] = line.replace('Action_Input:', '').strip()
            elif line.startswith('Final_Answer:'):
                result['final_answer'] = line.replace('Final_Answer:', '').strip()
        
        return result
    
    async def _execute_action(self, action_data: Dict) -> str:
        """执行具体行动"""
        action = action_data.get('action', '')
        input_data = action_data.get('action_input', '')
        
        if action == 'search':
            return await self._search(input_data)
        elif action == 'analyze':
            return await self._analyze(input_data)
        elif action == 'synthesize':
            return self._synthesize(input_data)
        
        return f"未知行动: {action}"
    
    async def _search(self, query: str) -> str:
        """搜索相关内容"""
        if not self.s2_client:
            return "S2 API 未配置"
        
        try:
            results = self.s2_client.search_papers(query, limit=5)
            if not results:
                return "未找到相关论文"
            
            papers = []
            for p in results[:5]:
                papers.append(f"- {p.get('title')} ({p.get('year')}) - {p.get('citationCount')} 引用")
            return "相关论文:\n" + "\n".join(papers)
        except Exception as e:
            return f"搜索失败: {str(e)}"
    
    async def _analyze(self, target_name: str) -> str:
        """分析概念或论文"""
        # 尝试从数据库获取概念
        concepts = self.db.get_all_concepts()
        for c in concepts:
            if c['text'].lower() == target_name.lower():
                # 获取结构信息
                ancestors = self.db.get_concept_parents(c['id'])
                children = self.db.get_concept_children(c['id'])
                return f"概念: {c['text']}\n上级: {len(ancestors)} 个\n下级: {len(children)} 个\n论文数: {c.get('paper_count', 0)}"
        
        return f"未找到概念: {target_name}"
    
    def _synthesize(self, content: str) -> str:
        """综合信息"""
        prompt = f"综合以下信息，给出简洁结论:\n{content}"
        try:
            return self.llm_client.generate(prompt)
        except Exception as e:
            return f"综合失败: {str(e)}"
    
    def _calculate_confidence(self, findings: List[Dict]) -> float:
        """计算置信度"""
        if not findings:
            return 0.0
        
        # 基于是否有结论和错误计算
        has_conclusion = any(f['type'] == 'conclusion' for f in findings)
        has_error = any(f['type'] == 'error' for f in findings)
        
        if has_error:
            return 0.3
        if has_conclusion:
            return 0.85
        
        return 0.6


class DeepResearchAgent:
    """深入研究 Agent - 协调多维度研究"""
    
    DEFAULT_DIMENSIONS = [
        '理论基础',
        '应用场景',
        '技术演进',
        '研究前沿',
        '潜在挑战',
    ]
    
    def __init__(self, llm_client, db, s2_client=None):
        self.llm_client = llm_client
        self.db = db
        self.s2_client = s2_client
    
    def start_research(self, target_type: str, target_id: str, 
                       target_name: str, query: str,
                       dimensions: Optional[List[str]] = None) -> str:
        """
        启动深入研究
        
        Returns:
            session_id: 研究会话 ID
        """
        session_id = str(uuid.uuid4())
        dims = dimensions or self.DEFAULT_DIMENSIONS
        
        # 创建会话
        self.db.create_research_session(
            session_id, target_type, target_id, target_name, query, dims
        )
        
        # 异步启动研究任务
        asyncio.create_task(self._run_research(session_id))
        
        return session_id
    
    async def _run_research(self, session_id: str) -> None:
        """执行多维度研究"""
        session = self.db.get_research_session(session_id)
        if not session:
            return
        
        target = {
            'type': session['target_type'],
            'id': session['target_id'],
            'name': session['target_name'],
        }
        
        dimensions = json.loads(session['dimensions'])
        completed = []
        total = len(dimensions)
        
        # 逐维度执行
        for i, dim in enumerate(dimensions):
            try:
                # 创建子代理
                sub_agent = SubAgent(dim, self.llm_client, self.db, self.s2_client)
                
                # 执行研究
                result = await sub_agent.research(target, session.get('query', ''))
                
                # 保存发现
                finding_id = str(uuid.uuid4())
                self.db.save_research_finding(
                    finding_id, session_id, dim,
                    result.get('findings', [])[-1].get('type', 'unknown') if result.get('findings') else 'unknown',
                    json.dumps(result.get('findings', []), ensure_ascii=False),
                    [], result.get('confidence', 0.5)
                )
                
                completed.append(dim)
                progress = int((i + 1) / total * 100)
                self.db.update_research_progress(session_id, progress, completed)
                
            except Exception as e:
                print(f"Dimension {dim} failed: {e}")
                completed.append(dim)
        
        # 生成报告
        report = self._generate_report(session_id)
        self.db.save_research_report(session_id, report)
    
    def _generate_report(self, session_id: str) -> str:
        """生成研究报告"""
        session = self.db.get_research_session(session_id)
        findings = self.db.get_research_findings(session_id)
        
        lines = [
            f"# {session['target_name']} 深入研究报告",
            f"",
            f"**研究时间**: {session['created_at']}",
            f"**研究维度**: {session['dimensions']}",
            f"",
        ]
        
        for f in findings:
            lines.append(f"## {f['dimension']}")
            lines.append(f"")
            content = f['content']
            if isinstance(content, str):
                try:
                    parsed = json.loads(content)
                    for item in parsed:
                        if isinstance(item, dict):
                            lines.append(f"**{item.get('type', 'Step')}**: {item.get('content', '')}")
                        else:
                            lines.append(str(item))
                except:
                    lines.append(content)
            else:
                lines.append(str(content))
            lines.append(f"置信度: {f['confidence']}")
            lines.append(f"")
        
        lines.append("---")
        lines.append("报告生成完毕")
        
        return "\n".join(lines)
    
    def get_status(self, session_id: str) -> Dict[str, Any]:
        """获取研究状态"""
        session = self.db.get_research_session(session_id)
        if not session:
            return {'error': 'Session not found'}
        
        return {
            'status': session['status'],
            'progress': session['progress'],
            'dimensions': json.loads(session['dimensions']),
            'completed_dimensions': json.loads(session['completed_dimensions']),
        }
    
    def get_report(self, session_id: str) -> Dict[str, Any]:
        """获取研究报告"""
        session = self.db.get_research_session(session_id)
        if not session:
            return {'error': 'Session not found'}
        
        return {
            'report': session['report'] or '研究进行中...',
            'format': 'markdown',
        }
```

- [ ] **Step 2: Commit**

```bash
git add mkg/agent/deep_research_agent.py
git commit -m "feat: add DeepResearchAgent with ReAct pattern"
```

---

### Task 3: Update Agent API Routes

**Files:**
- Modify: `backend/routes/agent.py`
- Modify: `mkg/agent/__init__.py`

- [ ] **Step 1: Update __init__.py**

```python
from .lead_agent import LeadAgent
from .citation_agent import CitationAgent
from .research_agent import ResearchPointAgent
from .deep_research_agent import DeepResearchAgent

__all__ = ['LeadAgent', 'CitationAgent', 'ResearchPointAgent', 'DeepResearchAgent']
```

- [ ] **Step 2: Update agent.py deep-research endpoints**

Replace placeholder endpoints in `backend/routes/agent.py`:

```python
from mkg.agent.deep_research_agent import DeepResearchAgent
from mkg.semantic_scholar import S2Client
import uuid
import asyncio

# Add singleton for deep research agent
_deep_research_agent = None

def get_deep_research_agent():
    global _deep_research_agent
    if _deep_research_agent is None:
        db = get_db()
        config = db.get_llm_config()
        
        llm_client = None
        if config and config.get('providers'):
            provider_config = db.get_active_llm_provider()
            if not provider_config:
                provider_config = config['providers'][0]
            
            if provider_config:
                llm_client = LiteLLMClient(
                    provider=provider_config.get('provider'),
                    api_key=provider_config.get('api_key'),
                    model=provider_config.get('model'),
                    base_url=provider_config.get('base_url')
                )
        
        s2_client = S2Client()
        
        if llm_client:
            _deep_research_agent = DeepResearchAgent(llm_client, db, s2_client)
    
    return _deep_research_agent


@router.post("/deep-research/start")
def start_deep_research(request: DeepResearchStartRequest):
    """启动深入研究任务"""
    agent = get_deep_research_agent()
    
    if not agent:
        raise HTTPException(
            status_code=500,
            detail="LLM 未配置，请先在设置中配置 API Key"
        )
    
    session_id = agent.start_research(
        target_type=request.targetType,
        target_id=request.targetId,
        target_name=request.targetName,
        query=request.query,
        dimensions=request.dimensions,
    )
    
    return {"sessionId": session_id, "status": "started"}


@router.get("/deep-research/{session_id}/status")
def get_research_status(session_id: str):
    """获取研究进度"""
    agent = get_deep_research_agent()
    
    if not agent:
        raise HTTPException(status_code=500, detail="Agent 未初始化")
    
    status = agent.get_status(session_id)
    
    if 'error' in status:
        raise HTTPException(status_code=404, detail=status['error'])
    
    return DeepResearchStatusResponse(**status)


@router.get("/deep-research/{session_id}/report")
def get_research_report(session_id: str):
    """获取研究报告"""
    agent = get_deep_research_agent()
    
    if not agent:
        raise HTTPException(status_code=500, detail="Agent 未初始化")
    
    report = agent.get_report(session_id)
    
    if 'error' in report:
        raise HTTPException(status_code=404, detail=report['error'])
    
    return report
```

- [ ] **Step 3: Add imports at top of agent.py**

Add after existing imports:

```python
from backend.schemas import DeepResearchStartRequest, DeepResearchStatusResponse
```

- [ ] **Step 4: Commit**

```bash
git add backend/routes/agent.py mkg/agent/__init__.py
git commit -m "feat: implement deep research API endpoints"
```

---

### Task 4: Add Deep Research Progress UI

**Files:**
- Create: `frontend/src/components/DeepResearchProgress.tsx`
- Modify: `frontend/src/components/ResearchAgentBubble.tsx`

- [ ] **Step 1: Create DeepResearchProgress component**

```tsx
// frontend/src/components/DeepResearchProgress.tsx
import { useEffect, useState } from 'react'
import { Loader2, CheckCircle, FileText } from 'lucide-react'
import { agentApi } from '../lib/api'

interface ProgressProps {
  sessionId: string
  onComplete: (report: string) => void
}

export function DeepResearchProgress({ sessionId, onComplete }: ProgressProps) {
  const [status, setStatus] = useState<string>('pending')
  const [progress, setProgress] = useState(0)
  const [dimensions, setDimensions] = useState<string[]>([])
  const [completed, setCompleted] = useState<string[]>([])

  useEffect(() => {
    const poll = async () => {
      try {
        const result = await agentApi.getResearchStatus(sessionId)
        setStatus(result.status)
        setProgress(result.progress)
        setDimensions(result.dimensions)
        setCompleted(result.completedDimensions)

        if (result.status === 'completed') {
          const report = await agentApi.getResearchReport(sessionId)
          onComplete(report.report)
        }
      } catch (e) {
        console.error('Poll error:', e)
      }
    }

    // Poll every 2 seconds
    const interval = setInterval(poll, 2000)
    poll() // Initial poll

    return () => clearInterval(interval)
  }, [sessionId, onComplete])

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">深入研究进度</span>
        <span className="text-sm text-gray-500">{progress}%</span>
      </div>

      <div className="w-full bg-gray-100 rounded-full h-2">
        <div
          className="bg-amber-500 h-2 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      <div className="space-y-2">
        {dimensions.map((dim) => (
          <div key={dim} className="flex items-center gap-2 text-sm">
            {completed.includes(dim) ? (
              <CheckCircle className="w-4 h-4 text-green-500" />
            ) : (
              <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
            )}
            <span className={completed.includes(dim) ? 'text-gray-700' : 'text-gray-400'}>
              {dim}
            </span>
          </div>
        ))}
      </div>

      {status === 'completed' && (
        <div className="flex items-center gap-2 text-sm text-green-600">
          <FileText className="w-4 h-4" />
          <span>研究完成，报告已生成</span>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Update ResearchAgentBubble to show progress**

Add import and conditionally render progress:

```tsx
import { DeepResearchProgress } from './DeepResearchProgress'

// In MessageList, add special rendering for research session:
{msg.agent === 'deep_research' && msg.researchSessionId && (
  <DeepResearchProgress
    sessionId={msg.researchSessionId}
    onComplete={(report) => {
      addMessage({
        role: 'assistant',
        content: report,
        agent: 'deep_research',
      })
    }}
  />
)}
```

- [ ] **Step 3: Update agentStore to track session**

Add to Message interface in `agentStore.ts`:

```typescript
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  agent?: 'lead' | 'citation' | 'research' | 'deep_research'
  researchSessionId?: string  // Add this
  timestamp: number
}
```

- [ ] **Step 4: Update handleSend in ResearchAgentBubble**

Add handling for deep research response:

```tsx
if (response.researchSessionId) {
  setResearchSession(response.researchSessionId)
  addMessage({
    role: 'assistant',
    content: '深入研究已启动，正在分析多个维度...',
    agent: 'deep_research',
    researchSessionId: response.researchSessionId,
  })
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/DeepResearchProgress.tsx \
        frontend/src/components/ResearchAgentBubble.tsx \
        frontend/src/stores/agentStore.ts
git commit -m "feat: add deep research progress UI"
```

---

### Task 5: Add Deep Research Dispatch to Lead Agent

**Files:**
- Modify: `mkg/agent/lead_agent.py`
- Modify: `backend/routes/agent.py`

- [ ] **Step 1: Add dispatch method to LeadAgent**

Add to `mkg/agent/lead_agent.py`:

```python
def dispatch_to_deep_research(self, target_name: str, target_type: str,
                               target_id: str, query: str, 
                               context: Dict[str, Any]) -> Dict[str, Any]:
    """分发到 Deep Research Agent"""
    from .deep_research_agent import DeepResearchAgent
    from mkg.semantic_scholar import S2Client

    # 创建 S2 客户端
    s2_client = S2Client()

    # 创建 Deep Research Agent
    deep_agent = DeepResearchAgent(self.llm_client, self.db, s2_client)

    # 启动研究
    session_id = deep_agent.start_research(
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        query=query,
    )

    return {
        'message': f'已启动「{target_name}」的深入研究，预计需要 1-2 分钟...',
        'agent': 'deep_research',
        'researchSessionId': session_id,
        'contextUpdate': {
            'currentTarget': {
                'type': target_type,
                'id': target_id,
                'name': target_name,
            },
        }
    }
```

- [ ] **Step 2: Add deep_research dispatch in agent.py route**

Add after research dispatch:

```python
# 分发到 Deep Research Agent
if intent == 'deep_research' and target_name:
    # 确定 target_type 和 target_id
    target_type = intent_result.get('target_type', 'concept')
    target_id = target_name  # 简化处理，使用名称作为 ID
    
    deep_result = lead_agent.dispatch_to_deep_research(
        target_name, target_type, target_id, request.message, context_dict
    )
    return AgentChatResponse(
        message=deep_result['message'],
        agent=deep_result['agent'],
        contextUpdate=deep_result.get('contextUpdate'),
        researchSessionId=deep_result.get('researchSessionId')
    )
```

- [ ] **Step 3: Update AgentChatResponse schema**

Add field to `backend/schemas.py` AgentChatResponse:

```python
researchSessionId: Optional[str] = None
```

- [ ] **Step 4: Update frontend api.ts AgentChatResponse**

Add field to interface in `frontend/src/lib/api.ts`:

```typescript
interface AgentChatResponse {
  message: string
  agent: string
  contextUpdate?: Partial<AgentContextSummary>
  researchSessionId?: string  // Add this
}
```

- [ ] **Step 5: Commit**

```bash
git add mkg/agent/lead_agent.py backend/routes/agent.py backend/schemas.py frontend/src/lib/api.ts
git commit -m "feat: integrate deep research dispatch"
```

---

### Task 6: Test Deep Research Flow

**Files:**
- No new files

- [ ] **Step 1: Verify backend imports**

```bash
cd D:/meta-knowledge-graph-main && python -c "from mkg.agent import DeepResearchAgent; print('OK')"
```

- [ ] **Step 2: Verify frontend build**

```bash
cd D:/meta-knowledge-graph-main/frontend && npm run build
```

---

## Summary

Phase 4 delivers:
- ✅ Research session persistence (database tables)
- ✅ DeepResearchAgent with multi-agent architecture
- ✅ Sub-agents with ReAct pattern
- ✅ Async execution with progress tracking
- ✅ Web report generation (markdown)
- ✅ Progress UI component
- ✅ Integration with Lead Agent dispatch