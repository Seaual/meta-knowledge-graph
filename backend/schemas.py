"""
Pydantic schemas for API
"""

from typing import Any

from pydantic import BaseModel, field_validator


# Paper schemas
class PaperBase(BaseModel):
    doi: str
    title: str
    abstract: str | None = None
    authors: list[str] = []
    keywords: list[str] = []
    contributions: list[str] = []
    published_date: str | None = None
    pdf_path: str | None = None
    status: str = "pending"
    s2_paper_id: str | None = None
    s2_doi: str | None = None
    venue: str | None = None
    year: int | None = None
    citation_count: int | None = None
    tldr: str | None = None
    s2_fields_of_study: list[str] | None = []


class PaperCreate(BaseModel):
    title: str
    abstract: str | None = None
    authors: list[str] = []
    keywords: list[str] = []
    contributions: list[str] = []


class PaperResponse(PaperBase):
    created_at: str | None = None
    updated_at: str | None = None

    class Config:
        from_attributes = True


# Concept schemas
class ConceptBase(BaseModel):
    id: str
    text: str
    text_en: str | None = None
    category: str | None = None
    paper_count: int = 0


class ConceptResponse(ConceptBase):
    depth_cache: int = -1

    class Config:
        from_attributes = True


class ConceptTreeNode(ConceptBase):
    children: list["ConceptTreeNode"] = []
    papers: list[dict] = []


class ConceptDetail(ConceptResponse):
    parents: list[ConceptResponse] = []
    children: list[ConceptResponse] = []
    papers: list[dict] = []


# Graph schemas
class GraphStats(BaseModel):
    papers: dict
    concepts: dict
    relations: int
    root_concepts: int


class GraphNode(BaseModel):
    id: str
    label: str
    label_en: str | None = None
    category: str
    paper_count: int


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str = "parent-child"


class GraphData(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# Process schemas
class ProcessRequest(BaseModel):
    doi: str


class ProcessResponse(BaseModel):
    success: bool
    message: str
    concept_tree: dict | None = None


# Skill submission schema
class SkillConceptSubmission(BaseModel):
    """Skill 提交的概念提取结果"""

    concept_tree: dict
    raw_response: str | None = None


# Batch processing schemas
class BatchUploadResponse(BaseModel):
    """批量上传响应"""

    job_id: str
    uploaded: list[dict]
    total: int


class BatchProcessRequest(BaseModel):
    """批量处理请求"""

    job_id: str
    dois: list[str]


class BatchProcessResult(BaseModel):
    """单个论文处理结果"""

    doi: str
    status: str  # success, failed, pending
    concepts: int | None = None
    error: str | None = None


class BatchProcessResponse(BaseModel):
    """批量处理响应"""

    job_id: str
    status: str  # pending, processing, completed, failed
    total: int
    completed: int = 0
    successful: int = 0
    failed: int = 0
    results: list[BatchProcessResult] = []


class BatchJobStatus(BaseModel):
    """批量任务状态"""

    job_id: str
    status: str
    total: int
    completed: int
    successful: int
    failed: int
    created_at: str | None = None


# Export schemas
class ExportResponse(BaseModel):
    """导出响应"""

    content: str
    stats: dict


# LLM Configuration schemas
class LLMProviderConfig(BaseModel):
    """单个 LLM 服务商配置"""

    function_group: str | None = None  # paper_parsing, concept_extraction, research_analysis
    provider: str  # openai, anthropic, google, dashscope, openrouter, minimax, claude_cli
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    is_active: bool = True


class LLMConfigResponse(BaseModel):
    """LLM 配置响应"""

    mode: str  # single, per_function
    providers: list[LLMProviderConfig]


class LLMConfigRequest(BaseModel):
    """LLM 配置请求"""

    mode: str
    providers: list[LLMProviderConfig]


class LLMTestRequest(BaseModel):
    """LLM 连接测试请求"""

    provider: str
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None


class LLMTestResponse(BaseModel):
    """LLM 连接测试响应"""

    success: bool
    message: str
    model: str | None = None


# Folder schemas
class FolderBase(BaseModel):
    id: str
    name: str
    description: str | None = None
    paper_count: int = 0


class FolderCreate(BaseModel):
    name: str
    description: str | None = None


class FolderUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class FolderResponse(FolderBase):
    created_at: str | None = None

    class Config:
        from_attributes = True


class PaperContribution(BaseModel):
    """论文贡献信息"""

    node_count: int
    root_concept: str | None = None


class PaperWithContribution(PaperResponse):
    """带贡献信息的论文响应"""

    node_count: int = 0
    root_concept: str | None = None


# Semantic Scholar Configuration schemas
class S2ConfigResponse(BaseModel):
    """S2 配置响应"""

    has_api_key: bool
    enabled: bool
    masked_key: str | None = None  # 脱敏后的 API Key


class S2ConfigRequest(BaseModel):
    """S2 配置请求"""

    api_key: str
    enabled: bool = True


class S2TestResponse(BaseModel):
    """S2 连接测试响应"""

    success: bool
    message: str


class S2Citation(BaseModel):
    """S2 引用论文"""

    paper_id: str | None = None
    title: str | None = None
    year: int | None = None
    venue: str | None = None
    authors: list[str] = []


class S2CitationsResponse(BaseModel):
    """S2 引用列表响应"""

    citations: list[S2Citation]
    total: int


class S2Reference(BaseModel):
    """S2 参考文献"""

    paper_id: str | None = None
    title: str | None = None
    year: int | None = None
    venue: str | None = None
    authors: list[str] = []


class S2ReferencesResponse(BaseModel):
    """S2 参考文献 列表响应"""

    references: list[S2Reference]
    total: int


# Agent schemas
class AgentMessage(BaseModel):
    """Single message in conversation history"""

    role: str  # 'user' | 'assistant'
    content: str
    agent: str | None = None


class ContextSummary(BaseModel):
    """Agent context summary for chat requests"""

    currentTarget: dict | None = None
    uploadedPapers: list[dict] | None = None
    contextTags: list[str] = []
    keyFindings: list[str] = []
    intentHistory: list[str] = []
    lastActiveAgent: str = "lead"


class ConceptGraphData(BaseModel):
    """概念图谱数据 - 用于在聊天中嵌入迷你图谱"""

    id: str
    name: str
    category: str | None = None
    paper_count: int = 0
    children: list["ConceptGraphData"] = []
    parents: list["ConceptGraphData"] = []


class AgentChatRequest(BaseModel):
    """Request for agent chat endpoint"""

    message: str
    context: ContextSummary
    history: list[AgentMessage] = []
    conversationId: str | None = None


class AgentChatResponse(BaseModel):
    """Response from agent chat endpoint"""

    message: str
    agent: str
    toolUsed: str | None = None  # 使用的工具名称
    contextUpdate: dict | None = None
    researchSessionId: str | None = None
    conceptData: ConceptGraphData | None = None  # deprecated，向后兼容
    attachments: list[dict] | None = None  # 新增：结构化附件列表


class DeepResearchStartRequest(BaseModel):
    """Request to start deep research on a target"""

    targetId: str
    targetType: str  # 'concept' | 'paper'
    query: str


class DeepResearchStatusResponse(BaseModel):
    """Response for deep research status"""

    status: str
    progress: int
    dimensions: list[str]
    completedDimensions: list[str]


# Conversation schemas
class ConversationBase(BaseModel):
    """对话基础信息"""

    id: str
    title: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class ConversationCreate(BaseModel):
    """创建对话请求"""

    device_id: str


class ConversationUpdate(BaseModel):
    """更新对话请求"""

    title: str


class MessageBase(BaseModel):
    """消息基础信息"""

    id: str
    role: str  # 'user' | 'assistant'
    content: str
    agent: str | None = None
    attachments: list[dict] | None = None
    created_at: str | None = None

    class Config:
        from_attributes = True


class ConversationDetail(ConversationBase):
    """对话详情（含消息列表）"""

    messages: list[MessageBase] = []

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    """创建消息请求"""

    role: str
    content: str
    agent: str | None = None
    attachments: list[dict] | None = None


# Memory schemas
class MemoryCreate(BaseModel):
    """创建研究记忆请求"""

    title: str
    content: str
    memory_type: str  # discovery/method/experiment/insight
    tags: list[str] = []
    concept_ids: list[str] = []
    paper_doi: str | None = None
    source_section: str | None = None

    @field_validator("memory_type")
    @classmethod
    def validate_memory_type(cls, v: str) -> str:
        valid_types = {"discovery", "method", "experiment", "insight"}
        if v not in valid_types:
            raise ValueError(f"memory_type must be one of {valid_types}")
        return v


class MemoryResponse(BaseModel):
    """研究记忆响应"""

    id: str
    title: str
    content: str | None
    memory_type: str
    tags: list[str]
    concept_ids: list[str]
    paper_doi: str | None
    source_section: str | None
    created_at: str

    class Config:
        from_attributes = True


class PreferencesUpdate(BaseModel):
    """更新偏好请求"""

    key: str
    value: Any
