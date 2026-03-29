"""
Pydantic schemas for API
"""

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# Paper schemas
class PaperBase(BaseModel):
    doi: str
    title: str
    abstract: Optional[str] = None
    authors: List[str] = []
    keywords: List[str] = []
    contributions: List[str] = []
    published_date: Optional[str] = None
    pdf_path: Optional[str] = None
    status: str = "pending"


class PaperCreate(BaseModel):
    title: str
    abstract: Optional[str] = None
    authors: List[str] = []
    keywords: List[str] = []
    contributions: List[str] = []


class PaperResponse(PaperBase):
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


# Concept schemas
class ConceptBase(BaseModel):
    id: str
    text: str
    category: Optional[str] = None
    paper_count: int = 0


class ConceptResponse(ConceptBase):
    depth_cache: int = -1

    class Config:
        from_attributes = True


class ConceptTreeNode(ConceptBase):
    children: List['ConceptTreeNode'] = []
    papers: List[dict] = []


class ConceptDetail(ConceptResponse):
    parents: List[ConceptResponse] = []
    children: List[ConceptResponse] = []
    papers: List[dict] = []


# Graph schemas
class GraphStats(BaseModel):
    papers: dict
    concepts: dict
    relations: int
    root_concepts: int


class GraphNode(BaseModel):
    id: str
    label: str
    category: str
    paper_count: int


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str = "parent-child"


class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# Process schemas
class ProcessRequest(BaseModel):
    doi: str


class ProcessResponse(BaseModel):
    success: bool
    message: str
    concept_tree: Optional[dict] = None


# Skill submission schema
class SkillConceptSubmission(BaseModel):
    """Skill 提交的概念提取结果"""
    concept_tree: dict
    raw_response: Optional[str] = None


# Batch processing schemas
class BatchUploadResponse(BaseModel):
    """批量上传响应"""
    job_id: str
    uploaded: List[dict]
    total: int


class BatchProcessRequest(BaseModel):
    """批量处理请求"""
    job_id: str
    dois: List[str]


class BatchProcessResult(BaseModel):
    """单个论文处理结果"""
    doi: str
    status: str  # success, failed, pending
    concepts: Optional[int] = None
    error: Optional[str] = None


class BatchProcessResponse(BaseModel):
    """批量处理响应"""
    job_id: str
    status: str  # pending, processing, completed, failed
    total: int
    completed: int = 0
    successful: int = 0
    failed: int = 0
    results: List[BatchProcessResult] = []


class BatchJobStatus(BaseModel):
    """批量任务状态"""
    job_id: str
    status: str
    total: int
    completed: int
    successful: int
    failed: int
    created_at: Optional[str] = None


# Export schemas
class ExportResponse(BaseModel):
    """导出响应"""
    content: str
    stats: dict


# LLM Configuration schemas
class LLMProviderConfig(BaseModel):
    """单个 LLM 服务商配置"""
    function_group: Optional[str] = None  # paper_parsing, concept_extraction, research_analysis
    provider: str  # openai, anthropic, google, dashscope, openrouter, minimax, claude_cli
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    is_active: bool = True


class LLMConfigResponse(BaseModel):
    """LLM 配置响应"""
    mode: str  # single, per_function
    providers: List[LLMProviderConfig]


class LLMConfigRequest(BaseModel):
    """LLM 配置请求"""
    mode: str
    providers: List[LLMProviderConfig]


class LLMTestRequest(BaseModel):
    """LLM 连接测试请求"""
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class LLMTestResponse(BaseModel):
    """LLM 连接测试响应"""
    success: bool
    message: str
    model: Optional[str] = None


# Folder schemas
class FolderBase(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    paper_count: int = 0


class FolderCreate(BaseModel):
    name: str
    description: Optional[str] = None


class FolderUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class FolderResponse(FolderBase):
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class PaperContribution(BaseModel):
    """论文贡献信息"""
    node_count: int
    root_concept: Optional[str] = None


class PaperWithContribution(PaperResponse):
    """带贡献信息的论文响应"""
    node_count: int = 0
    root_concept: Optional[str] = None


# Semantic Scholar Configuration schemas
class S2ConfigResponse(BaseModel):
    """S2 配置响应"""
    has_api_key: bool
    enabled: bool
    masked_key: Optional[str] = None  # 脱敏后的 API Key


class S2ConfigRequest(BaseModel):
    """S2 配置请求"""
    api_key: str
    enabled: bool = True


class S2TestResponse(BaseModel):
    """S2 连接测试响应"""
    success: bool
    message: str