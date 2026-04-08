# Backend Routes 模块化重构设计

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将过大的路由文件（papers.py 1258行, concepts.py 793行）拆分为职责单一的小模块，引入 Service 层分离业务逻辑。

**Architecture:** 路由层只处理 HTTP 请求/响应，业务逻辑移到 Service 层，依赖注入提供服务实例。

**Tech Stack:** FastAPI, Python 3.10+, Depends 注入

---

## 问题分析

当前 `backend/routes/` 存在以下问题：

| 文件 | 行数 | 端点数 | 问题 |
|------|------|--------|------|
| papers.py | 1258 | 15+ | CRUD + 上传 + 处理 + S2集成混在一起 |
| concepts.py | 793 | 12+ | CRUD + 树操作 + 去重 + 研究点发现混在一起 |

**具体问题：**
- 单文件过大，难以维护
- 业务逻辑与路由处理耦合
- 难以单独测试业务逻辑
- 多人协作容易冲突

---

## 解决方案

### 架构概览

```
backend/
├── routes/                 # 路由层 - HTTP 请求/响应处理
│   ├── __init__.py
│   ├── papers.py           # 论文基础 CRUD (~150行)
│   ├── papers_upload.py    # 上传相关端点 (~200行)
│   ├── papers_process.py   # 处理相关端点 (~250行)
│   ├── concepts.py         # 概念基础 CRUD (~100行)
│   ├── concepts_tree.py    # 树操作端点 (~100行)
│   ├── concepts_research.py # 研究点发现 (~150行)
│   ├── dedup.py            # 去重端点 (~200行)
│   ├── graph.py            # 保持不变
│   ├── agent.py            # 保持不变
│   ├── conversations.py    # 保持不变
│   ├── folders.py          # 保持不变
│   ├── llm.py              # 保持不变
│   └── s2.py               # 保持不变
├── services/               # 服务层 - 业务逻辑
│   ├── __init__.py
│   ├── paper_service.py    # 论文操作
│   ├── upload_service.py   # 上传处理
│   ├── process_service.py  # PDF处理、概念提取
│   ├── concept_service.py  # 概念操作
│   ├── dedup_service.py    # 去重逻辑
│   └── research_service.py # 研究点发现
├── dependencies.py         # 依赖注入配置
└── schemas.py              # 保持不变
```

### papers.py 拆分详情

**原文件端点分布：**

| 端点 | 方法 | 新位置 | 说明 |
|------|------|--------|------|
| `/papers/` | GET | papers.py | 列表 |
| `/papers/{doi}` | GET | papers.py | 获取 |
| `/papers/{doi}` | DELETE | papers.py | 删除 |
| `/papers/{doi}/metadata` | PATCH | papers.py | 更新元数据 |
| `/papers/{doi}/text` | GET | papers.py | 获取文本 |
| `/papers/{doi}/contribution` | GET | papers.py | 获取贡献 |
| `/papers/{doi}/move` | PATCH | papers.py | 移动文件夹 |
| `/papers/upload` | POST | papers_upload.py | 单文件上传 |
| `/papers/batch-upload` | POST | papers_upload.py | 批量上传 |
| `/papers/batch-process` | POST | papers_upload.py | 批量处理 |
| `/papers/batch-status/{job_id}` | GET | papers_upload.py | 批处理状态 |
| `/papers/process` | POST | papers_process.py | 处理论文 |
| `/papers/process-single` | POST | papers_process.py | 单篇处理 |
| `/papers/add-from-s2` | POST | papers_process.py | 从S2添加 |
| `/papers/download-and-process` | POST | papers_process.py | 下载处理 |

### concepts.py 拆分详情

**原文件端点分布：**

| 端点 | 方法 | 新位置 | 说明 |
|------|------|--------|------|
| `/concepts/` | GET | concepts.py | 列表 |
| `/concepts/{id}` | GET | concepts.py | 获取 |
| `/concepts/search` | GET | concepts.py | 搜索 |
| `/concepts/roots` | GET | concepts_tree.py | 根概念 |
| `/concepts/tree` | GET | concepts_tree.py | 概念树 |
| `/concepts/{id}/children` | GET | concepts_tree.py | 子概念 |
| `/concepts/{id}/parents` | GET | concepts_tree.py | 父概念 |
| `/concepts/{id}/papers` | GET | concepts.py | 关联论文 |
| `/concepts/{id}/search-papers` | GET | concepts_research.py | 搜索论文 |
| `/concepts/{id}/research-points` | GET | concepts_research.py | 研究点发现 |
| `/concepts/dedup/scan` | POST | dedup.py | 开始扫描 |
| `/concepts/dedup/scan-status/{id}` | GET | dedup.py | 扫描状态 |
| `/concepts/dedup/execute` | POST | dedup.py | 执行合并 |

---

## 服务层设计

### 依赖注入配置

```python
# backend/dependencies.py
from functools import lru_cache
from typing import Generator
from mkg.database import Database
from mkg.semantic_scholar import S2Client
from mkg.pdf_parser import PDFParser

_db_instance = None
_s2_client = None
_pdf_parser = None

def get_db() -> Database:
    global _db_instance
    if _db_instance is None:
        from pathlib import Path
        db_path = Path(__file__).parent.parent / "mkg.db"
        _db_instance = Database(str(db_path))
        _db_instance.connect()
    return _db_instance

def get_s2_client() -> S2Client:
    global _s2_client
    if _s2_client is None:
        _s2_client = S2Client()
    return _s2_client

def get_pdf_parser() -> PDFParser:
    global _pdf_parser
    if _pdf_parser is None:
        _pdf_parser = PDFParser()
    return _pdf_parser

# Service factories
def get_paper_service():
    from .services.paper_service import PaperService
    return PaperService(get_db())

def get_upload_service():
    from .services.upload_service import UploadService
    return UploadService(get_db())

def get_process_service():
    from .services.process_service import ProcessService
    return ProcessService(get_db(), get_pdf_parser())

def get_concept_service():
    from .services.concept_service import ConceptService
    return ConceptService(get_db())

def get_dedup_service():
    from .services.dedup_service import DedupService
    return DedupService(get_db())

def get_research_service():
    from .services.research_service import ResearchService
    return ResearchService(get_db(), get_s2_client())
```

### PaperService 设计

```python
# backend/services/paper_service.py
"""
论文服务 - 论文 CRUD 操作
"""

from typing import Optional, List, Dict
from mkg.database import Database


class PaperService:
    def __init__(self, db: Database):
        self.db = db
    
    def list(self, status: str = None, folder: str = None) -> List[Dict]:
        """获取论文列表"""
        return self.db.papers.get_all(folder_id=folder, status=status)
    
    def get(self, doi: str) -> Optional[Dict]:
        """获取单个论文"""
        return self.db.papers.get(doi)
    
    def get_by_folder(self, folder_id: str) -> List[Dict]:
        """获取文件夹中的论文"""
        return self.db.papers.get_by_folder(folder_id)
    
    def delete(self, doi: str) -> bool:
        """删除论文及其关联数据"""
        # 获取关联的概念
        concepts = self.db.papers.get_concepts(doi)
        
        # 删除论文（级联删除 paper_concepts）
        self.db.papers.delete_cascade(doi)
        
        # 清理孤立概念
        for concept in concepts:
            self.db.concepts._delete_orphaned(concept['id'])
        
        return True
    
    def update_metadata(self, doi: str, metadata: dict) -> bool:
        """更新论文元数据"""
        self.db.papers.update_metadata(doi, metadata)
        return True
    
    def move_to_folder(self, doi: str, folder_id: str) -> bool:
        """移动论文到文件夹"""
        self.db.papers.move_to_folder(doi, folder_id)
        return True
    
    def get_text(self, doi: str) -> Optional[str]:
        """获取论文文本"""
        paper = self.db.papers.get(doi)
        if not paper or not paper.get('pdf_path'):
            return None
        # 读取 PDF 文本
        from mkg.pdf_parser import PDFParser
        parser = PDFParser()
        return parser.extract_text(paper['pdf_path'])
    
    def get_contribution(self, doi: str) -> Dict:
        """获取论文贡献统计"""
        return self.db.papers.get_contribution(doi)
```

### UploadService 设计

```python
# backend/services/upload_service.py
"""
上传服务 - 论文上传处理
"""

import uuid
from typing import List, Dict
from pathlib import Path
from fastapi import UploadFile

from mkg.database import Database


class UploadService:
    def __init__(self, db: Database):
        self.db = db
        self.upload_dir = Path(__file__).parent.parent.parent / "papers"
        self.upload_dir.mkdir(exist_ok=True)
    
    async def upload_single(self, file: UploadFile, folder: str = "default") -> Dict:
        """上传单个论文"""
        # 生成唯一文件名
        job_id = str(uuid.uuid4())[:8]
        file_path = self.upload_dir / f"{job_id}_{file.filename}"
        
        # 保存文件
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # 提取 DOI 或生成临时 ID
        doi = f"upload:{job_id}"
        
        # 添加到数据库
        self.db.papers.add({
            "doi": doi,
            "title": file.filename.replace(".pdf", ""),
            "pdf_path": str(file_path),
            "status": "uploaded"
        })
        
        # 移动到指定文件夹
        if folder != "default":
            self.db.papers.move_to_folder(doi, folder)
        
        return {
            "doi": doi,
            "title": file.filename,
            "filename": file.filename,
            "success": True
        }
    
    async def upload_batch(self, files: List[UploadFile], folder: str = "default") -> Dict:
        """批量上传论文"""
        job_id = str(uuid.uuid4())
        results = []
        
        for file in files:
            try:
                result = await self.upload_single(file, folder)
                results.append(result)
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(e)
                })
        
        # 创建批处理任务
        self.db.execute_write(
            "INSERT INTO batch_jobs (id, total, status) VALUES (?, ?, 'pending')",
            (job_id, len(files))
        )
        
        return {
            "job_id": job_id,
            "uploaded": results,
            "total": len(files)
        }
    
    def get_batch_status(self, job_id: str) -> Dict:
        """获取批处理状态"""
        cursor = self.db.execute_read(
            "SELECT * FROM batch_jobs WHERE id = ?",
            (job_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
```

### ProcessService 设计

```python
# backend/services/process_service.py
"""
处理服务 - PDF 解析和概念提取
"""

from typing import Dict, Optional
from mkg.database import Database
from mkg.pdf_parser import PDFParser
from mkg.llm import init_llm_from_db


class ProcessService:
    def __init__(self, db: Database, pdf_parser: PDFParser):
        self.db = db
        self.pdf_parser = pdf_parser
    
    def process_paper(self, doi: str) -> Dict:
        """处理单篇论文"""
        paper = self.db.papers.get(doi)
        if not paper:
            return {"success": False, "error": "Paper not found"}
        
        if not paper.get('pdf_path'):
            return {"success": False, "error": "No PDF path"}
        
        try:
            # 更新状态
            self.db.papers.update_status(doi, "processing")
            
            # 提取文本
            text = self.pdf_parser.extract_text(paper['pdf_path'])
            
            # 初始化 LLM
            init_llm_from_db(self.db)
            
            # 提取概念
            from mkg.concept_extractor import ConceptExtractor
            extractor = ConceptExtractor()
            hierarchy = extractor.extract(text)
            
            # 保存概念
            self._save_concepts(doi, hierarchy)
            
            # 更新状态
            self.db.papers.update_status(doi, "processed")
            
            return {
                "success": True,
                "doi": doi,
                "concepts_count": self._count_concepts(hierarchy)
            }
        except Exception as e:
            self.db.papers.update_status(doi, "failed", str(e))
            return {"success": False, "error": str(e)}
    
    def _save_concepts(self, doi: str, hierarchy: Dict):
        """保存提取的概念到数据库"""
        def save_node(node, parent_id=None):
            # 添加概念
            concept_id = self.db.concepts.add({
                "text": node["name"],
                "category": node.get("category")
            })
            
            # 添加关系
            if parent_id:
                self.db.concepts.add_relation(parent_id, concept_id)
            
            # 添加论文关联
            self.db.concepts.add_paper_concept(doi, concept_id)
            
            # 递归处理子节点
            for child in node.get("children", []):
                save_node(child, concept_id)
        
        save_node(hierarchy)
    
    def _count_concepts(self, hierarchy: Dict) -> int:
        """统计概念数量"""
        count = 1
        for child in hierarchy.get("children", []):
            count += self._count_concepts(child)
        return count
```

### ConceptService 设计

```python
# backend/services/concept_service.py
"""
概念服务 - 概念 CRUD 操作
"""

from typing import Optional, List, Dict
from mkg.database import Database


class ConceptService:
    def __init__(self, db: Database):
        self.db = db
    
    def list(self) -> List[Dict]:
        """获取所有概念"""
        return self.db.concepts.get_all()
    
    def get(self, concept_id: str) -> Optional[Dict]:
        """获取单个概念"""
        concept = self.db.concepts.get(concept_id)
        if concept:
            concept['children'] = self.db.concepts.get_children(concept_id)
            concept['parents'] = self.db.concepts.get_parents(concept_id)
        return concept
    
    def search(self, query: str) -> List[Dict]:
        """搜索概念"""
        cursor = self.db.execute_read(
            "SELECT * FROM concepts WHERE text LIKE ? ORDER BY paper_count DESC",
            (f"%{query}%",)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_tree(self, root_id: str = None) -> Dict:
        """获取概念树"""
        return self.db.concepts.get_tree(root_id)
    
    def get_papers(self, concept_id: str, limit: int = 20) -> List[Dict]:
        """获取概念关联的论文"""
        return self.db.concepts.get_papers(concept_id)[:limit]
```

### DedupService 设计

```python
# backend/services/dedup_service.py
"""
去重服务 - 概念去重扫描和执行
"""

import uuid
import asyncio
from typing import Dict, List, Optional
from mkg.database import Database


class DedupService:
    def __init__(self, db: Database):
        self.db = db
    
    def start_scan(self, folder_id: str = None) -> Dict:
        """开始去重扫描"""
        scan_id = str(uuid.uuid4())
        
        # 获取概念数量
        concepts = self.db.concepts.get_by_folder(folder_id) if folder_id else self.db.concepts.get_all()
        
        # 创建扫描任务
        self.db.execute_write("""
            INSERT INTO dedup_scans (id, folder_id, total_concepts, status, progress)
            VALUES (?, ?, ?, 'pending', 0)
        """, (scan_id, folder_id, len(concepts)))
        
        return {"scan_id": scan_id, "total_concepts": len(concepts)}
    
    def get_scan_status(self, scan_id: str) -> Optional[Dict]:
        """获取扫描状态"""
        cursor = self.db.execute_read(
            "SELECT * FROM dedup_scans WHERE id = ?",
            (scan_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def execute_merge(self, scan_id: str, merge_ids: List[str]) -> Dict:
        """执行概念合并"""
        # 获取扫描结果
        scan = self.get_scan_status(scan_id)
        if not scan:
            return {"executed": 0, "error": "Scan not found"}
        
        executed = 0
        details = []
        
        for merge_id in merge_ids:
            # 获取合并建议
            # 执行合并...
            executed += 1
            details.append({"merge_id": merge_id, "status": "success"})
        
        return {"executed": executed, "details": details}
```

### ResearchService 设计

```python
# backend/services/research_service.py
"""
研究服务 - 研究点发现和论文推荐
"""

from typing import Dict, List, Optional
from mkg.database import Database
from mkg.semantic_scholar import S2Client
from mkg.llm import init_llm_from_db, get_llm_or_raise


class ResearchService:
    def __init__(self, db: Database, s2_client: S2Client = None):
        self.db = db
        self.s2_client = s2_client
    
    def discover_research_points(self, concept_id: str) -> Dict:
        """发现概念的研究点"""
        concept = self.db.concepts.get(concept_id)
        if not concept:
            return {"error": "Concept not found"}
        
        # 获取相关上下文
        children = self.db.concepts.get_children(concept_id)
        parents = self.db.concepts.get_parents(concept_id)
        papers = self.db.concepts.get_papers(concept_id)
        
        # 初始化 LLM
        init_llm_from_db(self.db)
        llm = get_llm_or_raise()
        
        # 构建提示
        prompt = self._build_research_prompt(concept, children, parents, papers)
        
        # 调用 LLM
        response = llm.invoke(prompt)
        
        return {
            "concept_name": concept["text"],
            "research_points": self._parse_research_points(response.content)
        }
    
    def search_papers(self, concept_id: str, year: str = None, 
                      min_citations: int = None, limit: int = 10) -> Dict:
        """搜索概念相关论文"""
        concept = self.db.concepts.get(concept_id)
        if not concept:
            return {"error": "Concept not found"}
        
        if not self.s2_client:
            return {"error": "S2 client not configured"}
        
        # 使用 S2 搜索
        query = concept["text"]
        papers = self.s2_client.search_papers(query, limit=limit)
        
        # 过滤
        if year:
            papers = [p for p in papers if str(p.get("year")) == year]
        if min_citations:
            papers = [p for p in papers if p.get("citationCount", 0) >= min_citations]
        
        return {
            "concept_id": concept_id,
            "concept_text": concept["text"],
            "papers": papers,
            "total": len(papers)
        }
    
    def _build_research_prompt(self, concept, children, parents, papers) -> str:
        """构建研究点发现提示"""
        return f"""分析以下概念的研究机会：

概念：{concept['text']}
子概念：{', '.join([c['text'] for c in children[:5]])}
父概念：{', '.join([p['text'] for p in parents[:3]])}
相关论文数：{len(papers)}

请提供 3-5 个研究点，包括标题、假设和描述。"""
    
    def _parse_research_points(self, content: str) -> List[Dict]:
        """解析研究点"""
        # 简单解析逻辑
        points = []
        lines = content.split("\n")
        current = None
        
        for line in lines:
            if line.startswith("##") or line.startswith("**"):
                if current:
                    points.append(current)
                current = {"title": line.strip("#* "), "description": ""}
            elif current and line.strip():
                current["description"] += line + " "
        
        if current:
            points.append(current)
        
        return points[:5]
```

---

## 路由层设计

### papers.py（精简后）

```python
# backend/routes/papers.py
"""
论文基础 CRUD 路由
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from ..dependencies import get_paper_service
from ..services.paper_service import PaperService
from ..schemas import PaperResponse, PaperMetadataUpdate

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.get("/")
def list_papers(
    status: Optional[str] = None,
    folder: Optional[str] = None,
    service: PaperService = Depends(get_paper_service)
):
    """获取论文列表"""
    return service.list(status=status, folder=folder)


@router.get("/{doi}")
def get_paper(
    doi: str,
    service: PaperService = Depends(get_paper_service)
):
    """获取单个论文"""
    paper = service.get(doi)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.delete("/{doi}")
def delete_paper(
    doi: str,
    service: PaperService = Depends(get_paper_service)
):
    """删除论文"""
    if not service.delete(doi):
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"status": "deleted"}


@router.patch("/{doi}/metadata")
def update_metadata(
    doi: str,
    update: PaperMetadataUpdate,
    service: PaperService = Depends(get_paper_service)
):
    """更新论文元数据"""
    service.update_metadata(doi, update.dict(exclude_unset=True))
    return {"status": "updated"}


@router.get("/{doi}/text")
def get_paper_text(
    doi: str,
    service: PaperService = Depends(get_paper_service)
):
    """获取论文文本"""
    text = service.get_text(doi)
    if text is None:
        raise HTTPException(status_code=404, detail="Text not available")
    return {"text": text}


@router.get("/{doi}/contribution")
def get_contribution(
    doi: str,
    service: PaperService = Depends(get_paper_service)
):
    """获取论文贡献"""
    return service.get_contribution(doi)


@router.patch("/{doi}/move")
def move_paper(
    doi: str,
    folder_id: str,
    service: PaperService = Depends(get_paper_service)
):
    """移动论文到文件夹"""
    service.move_to_folder(doi, folder_id)
    return {"status": "moved"}
```

---

## 迁移策略

### Phase 1: 创建基础设施
1. 创建 `backend/dependencies.py`
2. 创建 `backend/services/__init__.py`
3. 更新 `backend/main.py` 使用依赖注入

### Phase 2: 拆分 papers.py
1. 创建 `services/paper_service.py`
2. 创建 `services/upload_service.py`
3. 创建 `services/process_service.py`
4. 创建 `routes/papers_upload.py`
5. 创建 `routes/papers_process.py`
6. 精简 `routes/papers.py`

### Phase 3: 拆分 concepts.py
1. 创建 `services/concept_service.py`
2. 创建 `services/dedup_service.py`
3. 创建 `services/research_service.py`
4. 创建 `routes/concepts_tree.py`
5. 创建 `routes/concepts_research.py`
6. 创建 `routes/dedup.py`
7. 精简 `routes/concepts.py`

### Phase 4: 注册路由
更新 `main.py`:
```python
from backend.routes import papers, papers_upload, papers_process
from backend.routes import concepts, concepts_tree, concepts_research, dedup

app.include_router(papers.router)
app.include_router(papers_upload.router)
app.include_router(papers_process.router)
app.include_router(concepts.router)
app.include_router(concepts_tree.router)
app.include_router(concepts_research.router)
app.include_router(dedup.router)
```

---

## 预期收益

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| 最大路由文件行数 | 1258 | ~200 |
| 单文件端点数 | 15+ | ~5 |
| 业务逻辑可测试 | ❌ | ✅ |
| 职责清晰度 | 低 | 高 |
| 多人协作冲突 | 高 | 低 |

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| API 路径变化 | 保持原有路径，通过不同 router 文件注册相同 prefix |
| 依赖注入复杂度 | 使用简单的工厂函数，避免过度抽象 |
| 迁移遗漏 | 渐进迁移，保留旧文件作为备份 |
| 测试覆盖 | 为 Service 层添加单元测试 |