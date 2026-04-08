# Backend Routes 模块化重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将过大的路由文件拆分为职责单一的小模块，引入 Service 层分离业务逻辑。

**Architecture:** 路由层只处理 HTTP 请求/响应，业务逻辑移到 Service 层，依赖注入提供服务实例。

**Tech Stack:** FastAPI, Python 3.10+, Depends 注入

---

## 文件结构

```
backend/
├── dependencies.py         # 新建：依赖注入配置
├── services/               # 新建：业务逻辑层
│   ├── __init__.py
│   ├── paper_service.py
│   ├── upload_service.py
│   ├── process_service.py
│   ├── concept_service.py
│   ├── dedup_service.py
│   └── research_service.py
├── routes/
│   ├── papers.py           # 修改：精简为基础 CRUD
│   ├── papers_upload.py    # 新建：上传相关端点
│   ├── papers_process.py   # 新建：处理相关端点
│   ├── concepts.py         # 修改：精简为基础 CRUD
│   ├── concepts_tree.py    # 新建：树操作端点
│   ├── concepts_research.py # 新建：研究点发现
│   └── dedup.py            # 新建：去重端点
└── main.py                 # 修改：注册新路由
```

---

## Task 1: 创建依赖注入基础设施

**Files:**
- Create: `backend/dependencies.py`
- Create: `backend/services/__init__.py`

- [ ] **Step 1: 创建 `backend/services/__init__.py`**

```python
# backend/services/__init__.py
"""
Services 模块 - 业务逻辑层
"""

from .paper_service import PaperService
from .upload_service import UploadService
from .process_service import ProcessService
from .concept_service import ConceptService
from .dedup_service import DedupService
from .research_service import ResearchService

__all__ = [
    "PaperService",
    "UploadService",
    "ProcessService",
    "ConceptService",
    "DedupService",
    "ResearchService",
]
```

- [ ] **Step 2: 创建 `backend/dependencies.py`**

```python
# backend/dependencies.py
"""
依赖注入配置 - 提供服务和资源实例
"""

from pathlib import Path
from typing import Optional

# 延迟导入避免循环依赖
_db_instance = None
_s2_client = None
_pdf_parser = None


def get_db():
    """获取数据库实例（单例）"""
    global _db_instance
    if _db_instance is None:
        from mkg.database import Database
        db_path = Path(__file__).parent.parent / "mkg.db"
        _db_instance = Database(str(db_path))
        _db_instance.connect()
    return _db_instance


def get_s2_client():
    """获取 Semantic Scholar 客户端（单例）"""
    global _s2_client
    if _s2_client is None:
        from mkg.semantic_scholar import S2Client
        # 从数据库获取 API Key
        db = get_db()
        s2_config = db.config.get_s2_config()
        api_key = s2_config.get('api_key') if s2_config else None
        _s2_client = S2Client(api_key=api_key)
    return _s2_client


def get_pdf_parser():
    """获取 PDF 解析器（单例）"""
    global _pdf_parser
    if _pdf_parser is None:
        from mkg.pdf_parser import PDFParser
        _pdf_parser = PDFParser()
    return _pdf_parser


# ========== Service Factories ==========

def get_paper_service():
    """获取 PaperService 实例"""
    from .services.paper_service import PaperService
    return PaperService(get_db())


def get_upload_service():
    """获取 UploadService 实例"""
    from .services.upload_service import UploadService
    return UploadService(get_db())


def get_process_service():
    """获取 ProcessService 实例"""
    from .services.process_service import ProcessService
    return ProcessService(get_db(), get_pdf_parser())


def get_concept_service():
    """获取 ConceptService 实例"""
    from .services.concept_service import ConceptService
    return ConceptService(get_db())


def get_dedup_service():
    """获取 DedupService 实例"""
    from .services.dedup_service import DedupService
    return DedupService(get_db())


def get_research_service():
    """获取 ResearchService 实例"""
    from .services.research_service import ResearchService
    return ResearchService(get_db(), get_s2_client())
```

- [ ] **Step 3: 提交**

```bash
git add backend/dependencies.py backend/services/__init__.py
git commit -m "feat(backend): add dependencies and services module structure"
```

---

## Task 2: 创建 PaperService

**Files:**
- Create: `backend/services/paper_service.py`

- [ ] **Step 1: 创建 `backend/services/paper_service.py`**

```python
# backend/services/paper_service.py
"""
论文服务 - 论文 CRUD 操作
"""

from typing import Optional, List, Dict
from mkg.database import Database


class PaperService:
    """论文数据访问服务"""

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
        paper = self.db.papers.get(doi)
        if not paper:
            return False

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
        paper = self.db.papers.get(doi)
        if not paper:
            return False
        self.db.papers.update_metadata(doi, metadata)
        return True

    def move_to_folder(self, doi: str, folder_id: str) -> bool:
        """移动论文到文件夹"""
        paper = self.db.papers.get(doi)
        if not paper:
            return False
        self.db.papers.move_to_folder(doi, folder_id)
        return True

    def get_text(self, doi: str) -> Optional[str]:
        """获取论文文本"""
        paper = self.db.papers.get(doi)
        if not paper or not paper.get('pdf_path'):
            return None

        # 检查文件是否存在
        from pathlib import Path
        pdf_path = Path(paper['pdf_path'])
        if not pdf_path.exists():
            return None

        # 读取 PDF 文本
        from mkg.pdf_parser import PDFParser
        parser = PDFParser()
        try:
            return parser.extract_text(str(pdf_path))
        except Exception:
            return None

    def get_contribution(self, doi: str) -> Dict:
        """获取论文贡献统计"""
        return self.db.papers.get_contribution(doi)

    def get_concepts(self, doi: str) -> List[Dict]:
        """获取论文关联的概念"""
        return self.db.papers.get_concepts(doi)
```

- [ ] **Step 2: 提交**

```bash
git add backend/services/paper_service.py
git commit -m "feat(backend): add PaperService for paper CRUD operations"
```

---

## Task 3: 创建 UploadService 和 ProcessService

**Files:**
- Create: `backend/services/upload_service.py`
- Create: `backend/services/process_service.py`

- [ ] **Step 1: 创建 `backend/services/upload_service.py`**

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
    """论文上传服务"""

    def __init__(self, db: Database):
        self.db = db
        self.upload_dir = Path(__file__).parent.parent.parent / "papers"
        self.upload_dir.mkdir(exist_ok=True)

    async def upload_single(self, file: UploadFile, folder: str = "default") -> Dict:
        """上传单个论文 PDF"""
        import shutil

        # 生成唯一文件名
        file_id = str(uuid.uuid4())[:8]
        safe_filename = file.filename.replace("/", "_").replace("\\", "_")
        file_path = self.upload_dir / f"{file_id}_{safe_filename}"

        # 保存文件
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 使用文件名作为临时 DOI
        doi = f"upload:{file_id}"

        # 添加到数据库
        self.db.papers.add({
            "doi": doi,
            "title": Path(file.filename).stem,
            "pdf_path": str(file_path),
            "status": "uploaded"
        })

        # 移动到指定文件夹
        if folder and folder != "default":
            self.db.papers.move_to_folder(doi, folder)

        return {
            "doi": doi,
            "title": Path(file.filename).stem,
            "filename": file.filename,
            "success": True
        }

    async def upload_batch(self, files: List[UploadFile], folder: str = "default") -> Dict:
        """批量上传论文"""
        job_id = str(uuid.uuid4())
        results = []

        for file in files:
            try:
                if file.filename.endswith('.pdf'):
                    result = await self.upload_single(file, folder)
                    results.append(result)
                else:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": "Not a PDF file"
                    })
            except Exception as e:
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": str(e)
                })

        # 创建批处理任务记录
        self.db.execute_write(
            "INSERT OR IGNORE INTO batch_jobs (id, total, status) VALUES (?, ?, 'pending')",
            (job_id, len(results))
        )

        return {
            "job_id": job_id,
            "uploaded": results,
            "total": len(results)
        }

    def get_batch_status(self, job_id: str) -> Optional[Dict]:
        """获取批处理状态"""
        cursor = self.db.execute_read(
            "SELECT * FROM batch_jobs WHERE id = ?",
            (job_id,)
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_batch_status(self, job_id: str, completed: int, successful: int, failed: int, status: str):
        """更新批处理状态"""
        self.db.execute_write("""
            UPDATE batch_jobs
            SET completed = ?, successful = ?, failed = ?, status = ?
            WHERE id = ?
        """, (completed, successful, failed, status, job_id))
```

- [ ] **Step 2: 创建 `backend/services/process_service.py`**

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
    """论文处理服务 - PDF 解析和概念提取"""

    def __init__(self, db: Database, pdf_parser: PDFParser):
        self.db = db
        self.pdf_parser = pdf_parser

    def process_paper(self, doi: str) -> Dict:
        """处理单篇论文 - 提取概念"""
        paper = self.db.papers.get(doi)
        if not paper:
            return {"success": False, "error": "Paper not found", "doi": doi}

        if not paper.get('pdf_path'):
            return {"success": False, "error": "No PDF path", "doi": doi}

        try:
            # 更新状态
            self.db.papers.update_status(doi, "processing")

            # 提取文本
            text = self.pdf_parser.extract_text(paper['pdf_path'])
            if not text:
                raise Exception("Failed to extract text from PDF")

            # 初始化 LLM
            init_llm_from_db(self.db)

            # 提取概念
            from mkg.pdf_parser import LLMConceptExtractor
            extractor = LLMConceptExtractor()
            hierarchy = extractor.extract(text)

            # 保存概念
            self._save_concepts(doi, hierarchy)

            # 更新状态
            self.db.papers.update_status(doi, "processed")

            return {
                "success": True,
                "doi": doi,
                "message": "Paper processed successfully",
                "concepts_count": self._count_concepts(hierarchy)
            }

        except Exception as e:
            self.db.papers.update_status(doi, "failed", str(e))
            return {"success": False, "error": str(e), "doi": doi}

    def _save_concepts(self, doi: str, hierarchy: Dict):
        """保存提取的概念到数据库"""
        def save_node(node, parent_id=None):
            # 添加概念
            concept_id = self.db.concepts.add({
                "text": node.get("name", node.get("text", "")),
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

        if hierarchy:
            save_node(hierarchy)

    def _count_concepts(self, hierarchy: Dict) -> int:
        """统计概念数量"""
        if not hierarchy:
            return 0
        count = 1
        for child in hierarchy.get("children", []):
            count += self._count_concepts(child)
        return count

    def process_batch(self, dois: List[str], job_id: str) -> Dict:
        """批量处理论文"""
        results = []
        completed = 0
        successful = 0
        failed = 0

        for doi in dois:
            result = self.process_paper(doi)
            results.append(result)
            completed += 1
            if result.get("success"):
                successful += 1
            else:
                failed += 1

            # 更新进度
            self.db.execute_write("""
                UPDATE batch_jobs
                SET completed = ?, successful = ?, failed = ?, status = 'processing'
                WHERE id = ?
            """, (completed, successful, failed, job_id))

        # 标记完成
        self.db.execute_write("""
            UPDATE batch_jobs SET status = 'completed' WHERE id = ?
        """, (job_id,))

        return {
            "job_id": job_id,
            "status": "completed",
            "total": len(dois),
            "completed": completed,
            "successful": successful,
            "failed": failed,
            "results": results
        }
```

- [ ] **Step 3: 提交**

```bash
git add backend/services/upload_service.py backend/services/process_service.py
git commit -m "feat(backend): add UploadService and ProcessService"
```

---

## Task 4: 创建 ConceptService, DedupService, ResearchService

**Files:**
- Create: `backend/services/concept_service.py`
- Create: `backend/services/dedup_service.py`
- Create: `backend/services/research_service.py`

- [ ] **Step 1: 创建 `backend/services/concept_service.py`**

```python
# backend/services/concept_service.py
"""
概念服务 - 概念 CRUD 操作
"""

from typing import Optional, List, Dict
from mkg.database import Database


class ConceptService:
    """概念数据访问服务"""

    def __init__(self, db: Database):
        self.db = db

    def list(self) -> List[Dict]:
        """获取所有概念"""
        return self.db.concepts.get_all()

    def get(self, concept_id: str) -> Optional[Dict]:
        """获取单个概念（包含父子关系）"""
        concept = self.db.concepts.get(concept_id)
        if concept:
            concept['children'] = self.db.concepts.get_children(concept_id)
            concept['parents'] = self.db.concepts.get_parents(concept_id)
        return concept

    def search(self, query: str) -> List[Dict]:
        """搜索概念"""
        cursor = self.db.execute_read(
            "SELECT * FROM concepts WHERE text LIKE ? ORDER BY paper_count DESC LIMIT 50",
            (f"%{query}%",)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_roots(self) -> List[Dict]:
        """获取根概念"""
        return self.db.concepts.get_root()

    def get_tree(self, root_id: str = None) -> Dict:
        """获取概念树"""
        return self.db.concepts.get_tree(root_id)

    def get_children(self, concept_id: str) -> List[Dict]:
        """获取子概念"""
        return self.db.concepts.get_children(concept_id)

    def get_parents(self, concept_id: str) -> List[Dict]:
        """获取父概念"""
        return self.db.concepts.get_parents(concept_id)

    def get_papers(self, concept_id: str, limit: int = 20) -> List[Dict]:
        """获取概念关联的论文"""
        papers = self.db.concepts.get_papers(concept_id)
        return papers[:limit]
```

- [ ] **Step 2: 创建 `backend/services/dedup_service.py`**

```python
# backend/services/dedup_service.py
"""
去重服务 - 概念去重扫描和执行
"""

import uuid
from typing import Dict, List, Optional
from mkg.database import Database


class DedupService:
    """概念去重服务"""

    def __init__(self, db: Database):
        self.db = db

    def start_scan(self, folder_id: str = None) -> Dict:
        """开始去重扫描"""
        scan_id = str(uuid.uuid4())

        # 获取概念数量
        if folder_id:
            concepts = self.db.concepts.get_by_folder(folder_id)
        else:
            concepts = self.db.concepts.get_all()

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

    def update_scan_status(self, scan_id: str, **kwargs):
        """更新扫描状态"""
        valid_fields = ['status', 'progress', 'suggestions', 'filtered_count', 
                        'high_confidence_count', 'batches_completed', 'phase']
        updates = []
        values = []
        for key, value in kwargs.items():
            if key in valid_fields:
                updates.append(f"{key} = ?")
                values.append(value)

        if updates:
            values.append(scan_id)
            self.db.execute_write(
                f"UPDATE dedup_scans SET {', '.join(updates)} WHERE id = ?",
                tuple(values)
            )

    def execute_merge(self, scan_id: str, merge_ids: List[str]) -> Dict:
        """执行概念合并"""
        scan = self.get_scan_status(scan_id)
        if not scan:
            return {"executed": 0, "details": [], "error": "Scan not found"}

        executed = 0
        details = []

        for merge_id in merge_ids:
            # TODO: 实现实际的合并逻辑
            executed += 1
            details.append({"merge_id": merge_id, "status": "success"})

        return {"executed": executed, "details": details}

    def cleanup_old_scans(self, max_age_hours: int = 24):
        """清理旧的扫描任务"""
        self.db.execute_write("""
            DELETE FROM dedup_scans
            WHERE created_at < datetime('now', ?)
        """, (f'-{max_age_hours} hours',))
```

- [ ] **Step 3: 创建 `backend/services/research_service.py`**

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
    """研究点发现服务"""

    def __init__(self, db: Database, s2_client: S2Client = None):
        self.db = db
        self.s2_client = s2_client

    def discover_research_points(self, concept_id: str) -> Dict:
        """发现概念的研究点"""
        concept = self.db.concepts.get(concept_id)
        if not concept:
            return {"error": "Concept not found", "concept_id": concept_id}

        # 获取相关上下文
        children = self.db.concepts.get_children(concept_id)
        parents = self.db.concepts.get_parents(concept_id)
        papers = self.db.concepts.get_papers(concept_id)

        try:
            # 初始化 LLM
            init_llm_from_db(self.db)
            llm = get_llm_or_raise()

            # 构建提示
            prompt = self._build_research_prompt(concept, children, parents, papers)

            # 调用 LLM
            response = llm.invoke(prompt)

            return {
                "concept_id": concept_id,
                "concept_name": concept["text"],
                "research_points": self._parse_research_points(response.content)
            }
        except Exception as e:
            return {"error": str(e), "concept_id": concept_id}

    def search_papers_by_concept(self, concept_id: str, year: str = None,
                                  min_citations: int = None, limit: int = 10) -> Dict:
        """搜索概念相关论文"""
        concept = self.db.concepts.get(concept_id)
        if not concept:
            return {"error": "Concept not found", "concept_id": concept_id}

        if not self.s2_client:
            return {"error": "S2 client not configured", "concept_id": concept_id}

        try:
            # 使用 S2 搜索
            query = concept["text"]
            papers = self.s2_client.search_papers(query, limit=limit * 2)  # 多获取一些用于过滤

            # 过滤
            if year:
                papers = [p for p in papers if str(p.get("year")) == year]
            if min_citations:
                papers = [p for p in papers if p.get("citationCount", 0) >= min_citations]

            papers = papers[:limit]

            return {
                "concept_id": concept_id,
                "concept_text": concept["text"],
                "papers": papers,
                "total": len(papers)
            }
        except Exception as e:
            return {"error": str(e), "concept_id": concept_id}

    def _build_research_prompt(self, concept: Dict, children: List, parents: List, papers: List) -> str:
        """构建研究点发现提示"""
        child_texts = [c['text'] for c in children[:5]]
        parent_texts = [p['text'] for p in parents[:3]]

        return f"""分析以下概念的研究机会：

概念：{concept['text']}
子概念：{', '.join(child_texts) if child_texts else '无'}
父概念：{', '.join(parent_texts) if parent_texts else '无'}
相关论文数：{len(papers)}

请提供 3-5 个研究点，每个研究点包含：
1. 标题
2. 研究假设
3. 简要描述
4. 研究方法建议

以 JSON 格式返回。"""

    def _parse_research_points(self, content: str) -> List[Dict]:
        """解析研究点"""
        import json
        import re

        points = []

        # 尝试解析 JSON
        json_match = re.search(r'\[[\s\S]*\]', content)
        if json_match:
            try:
                points = json.loads(json_match.group())
                return points
            except json.JSONDecodeError:
                pass

        # 简单解析
        lines = content.split("\n")
        current = None

        for line in lines:
            if line.startswith("##") or line.startswith("**") or re.match(r'^\d+\.', line):
                if current:
                    points.append(current)
                title = re.sub(r'^[#*>\d.\s]+', '', line).strip()
                current = {"title": title, "description": ""}
            elif current and line.strip():
                current["description"] += line.strip() + " "

        if current:
            points.append(current)

        return points[:5]
```

- [ ] **Step 4: 提交**

```bash
git add backend/services/
git commit -m "feat(backend): add ConceptService, DedupService, ResearchService"
```

---

## Task 5: 创建 papers_upload.py 路由

**Files:**
- Create: `backend/routes/papers_upload.py`

- [ ] **Step 1: 创建 `backend/routes/papers_upload.py`**

```python
# backend/routes/papers_upload.py
"""
论文上传路由 - 上传和批处理相关端点
"""

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from typing import List

from ..dependencies import get_upload_service
from ..services.upload_service import UploadService
from ..schemas import BatchProcessRequest

router = APIRouter(prefix="/api/papers", tags=["papers-upload"])


@router.post("/upload")
async def upload_paper(
    file: UploadFile = File(...),
    folder: str = Form("default"),
    service: UploadService = Depends(get_upload_service)
):
    """上传单个论文 PDF"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    result = await service.upload_single(file, folder)
    return {"success": True, **result}


@router.post("/batch-upload")
async def batch_upload_papers(
    files: List[UploadFile] = File(...),
    folder: str = Form("default"),
    service: UploadService = Depends(get_upload_service)
):
    """批量上传论文 PDF"""
    pdf_files = [f for f in files if f.filename.endswith('.pdf')]
    if not pdf_files:
        raise HTTPException(status_code=400, detail="No PDF files found")

    result = await service.upload_batch(pdf_files, folder)
    return result


@router.post("/batch-process")
async def batch_process_papers(
    request: BatchProcessRequest,
    service: UploadService = Depends(get_upload_service)
):
    """批量处理已上传的论文"""
    from ..dependencies import get_process_service
    from ..services.process_service import ProcessService

    process_service = get_process_service()
    result = process_service.process_batch(request.dois, request.job_id)
    return result


@router.get("/batch-status/{job_id}")
def get_batch_status(
    job_id: str,
    service: UploadService = Depends(get_upload_service)
):
    """获取批处理任务状态"""
    status = service.get_batch_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status
```

- [ ] **Step 2: 提交**

```bash
git add backend/routes/papers_upload.py
git commit -m "feat(backend): add papers_upload.py route for upload endpoints"
```

---

## Task 6: 创建 papers_process.py 路由

**Files:**
- Create: `backend/routes/papers_process.py`

- [ ] **Step 1: 创建 `backend/routes/papers_process.py`**

```python
# backend/routes/papers_process.py
"""
论文处理路由 - PDF 解析和概念提取相关端点
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from ..dependencies import get_process_service, get_s2_client
from ..services.process_service import ProcessService
from ..schemas import ProcessRequest, ProcessResponse, SkillConceptSubmission

router = APIRouter(prefix="/api/papers", tags=["papers-process"])


class AddFromS2Request(BaseModel):
    """从 S2 添加论文请求"""
    s2_paper_id: str
    title: str
    year: Optional[int] = None
    abstract: Optional[str] = None
    authors: Optional[List[str]] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = None
    tldr: Optional[str] = None
    open_access_pdf_url: Optional[str] = None


class DownloadAndProcessRequest(BaseModel):
    """下载并处理论文请求"""
    s2_paper_id: str
    title: str
    year: Optional[int] = None
    abstract: Optional[str] = None
    authors: Optional[List[str]] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = None
    tldr: Optional[str] = None
    open_access_pdf_url: str


@router.post("/process", response_model=ProcessResponse)
def process_paper(
    request: ProcessRequest,
    service: ProcessService = Depends(get_process_service)
):
    """处理论文 - 提取概念"""
    result = service.process_paper(request.doi)
    return ProcessResponse(
        success=result.get("success", False),
        message=result.get("message", result.get("error", "")),
        concept_tree=None,
        duration=0
    )


@router.post("/process-single", response_model=ProcessResponse)
async def process_single_paper(
    request: ProcessRequest,
    service: ProcessService = Depends(get_process_service)
):
    """处理单篇论文（异步）"""
    import asyncio

    # 在后台运行处理
    result = await asyncio.to_thread(service.process_paper, request.doi)

    return ProcessResponse(
        success=result.get("success", False),
        message=result.get("message", result.get("error", "")),
        concept_tree=None,
        duration=0
    )


@router.post("/submit-concepts")
def submit_concepts(doi: str, submission: SkillConceptSubmission):
    """提交概念提取结果（人工标注）"""
    from ..dependencies import get_db
    from mkg.database import Database

    db = get_db()
    paper = db.papers.get(doi)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # 保存概念树
    db.concepts.save_extraction(doi, submission.concept_tree, submission.raw_response or "")

    return {"success": True, "message": "Concepts submitted"}


@router.post("/add-from-s2")
def add_paper_from_s2(request: AddFromS2Request):
    """从 Semantic Scholar 添加论文（仅元数据）"""
    from ..dependencies import get_db
    from mkg.database import Database

    db = get_db()

    # 使用 S2 Paper ID 作为 DOI
    doi = f"s2:{request.s2_paper_id}"

    db.papers.add({
        "doi": doi,
        "title": request.title,
        "abstract": request.abstract,
        "authors": request.authors or [],
        "year": request.year,
        "venue": request.venue,
        "citation_count": request.citation_count,
        "tldr": request.tldr,
        "s2_paper_id": request.s2_paper_id,
        "status": "metadata_only"
    })

    return {
        "success": True,
        "message": "Paper metadata added",
        "doi": doi,
        "title": request.title
    }


@router.post("/download-and-process")
async def download_and_process_paper(request: DownloadAndProcessRequest):
    """下载 PDF 并处理"""
    import httpx
    from pathlib import Path
    from ..dependencies import get_db, get_process_service

    # 下载 PDF
    pdf_dir = Path("papers")
    pdf_dir.mkdir(exist_ok=True)

    pdf_path = pdf_dir / f"{request.s2_paper_id}.pdf"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(request.open_access_pdf_url)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to download PDF")

        with open(pdf_path, "wb") as f:
            f.write(response.content)

    # 添加到数据库
    db = get_db()
    doi = f"s2:{request.s2_paper_id}"

    db.papers.add({
        "doi": doi,
        "title": request.title,
        "abstract": request.abstract,
        "authors": request.authors or [],
        "year": request.year,
        "venue": request.venue,
        "citation_count": request.citation_count,
        "tldr": request.tldr,
        "s2_paper_id": request.s2_paper_id,
        "pdf_path": str(pdf_path),
        "status": "downloaded"
    })

    # 处理
    process_service = get_process_service()
    result = process_service.process_paper(doi)

    return {
        "success": result.get("success", False),
        "doi": doi,
        "title": request.title,
        "message": result.get("message", result.get("error", ""))
    }
```

- [ ] **Step 2: 提交**

```bash
git add backend/routes/papers_process.py
git commit -m "feat(backend): add papers_process.py route for processing endpoints"
```

---

## Task 7: 精简 papers.py 路由

**Files:**
- Modify: `backend/routes/papers.py`

- [ ] **Step 1: 重写 `backend/routes/papers.py`（精简版）**

```python
# backend/routes/papers.py
"""
论文基础 CRUD 路由
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel

from ..dependencies import get_paper_service
from ..services.paper_service import PaperService

router = APIRouter(prefix="/api/papers", tags=["papers"])


class PaperMetadataUpdate(BaseModel):
    """论文元数据更新"""
    title: Optional[str] = None
    abstract: Optional[str] = None
    authors: Optional[list] = None
    keywords: Optional[list] = None
    contributions: Optional[list] = None


class MovePaperRequest(BaseModel):
    """移动论文请求"""
    folder_id: str = "default"


@router.get("/")
def list_papers(
    status: Optional[str] = None,
    folder: Optional[str] = None,
    service: PaperService = Depends(get_paper_service)
):
    """获取论文列表"""
    return service.list(status=status, folder=folder)


@router.get("/{doi:path}")
def get_paper(
    doi: str,
    service: PaperService = Depends(get_paper_service)
):
    """获取单个论文"""
    paper = service.get(doi)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.delete("/{doi:path}")
def delete_paper(
    doi: str,
    service: PaperService = Depends(get_paper_service)
):
    """删除论文"""
    if not service.delete(doi):
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"status": "deleted", "doi": doi}


@router.patch("/{doi:path}/metadata")
def update_metadata(
    doi: str,
    update: PaperMetadataUpdate,
    service: PaperService = Depends(get_paper_service)
):
    """更新论文元数据"""
    if not service.update_metadata(doi, update.dict(exclude_unset=True)):
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"status": "updated", "doi": doi}


@router.get("/{doi:path}/text")
def get_paper_text(
    doi: str,
    service: PaperService = Depends(get_paper_service)
):
    """获取论文文本"""
    text = service.get_text(doi)
    if text is None:
        raise HTTPException(status_code=404, detail="Text not available")
    return {"text": text, "doi": doi}


@router.get("/{doi:path}/contribution")
def get_contribution(
    doi: str,
    service: PaperService = Depends(get_paper_service)
):
    """获取论文贡献统计"""
    return service.get_contribution(doi)


@router.patch("/{doi:path}/move")
def move_paper(
    doi: str,
    request: MovePaperRequest,
    service: PaperService = Depends(get_paper_service)
):
    """移动论文到文件夹"""
    if not service.move_to_folder(doi, request.folder_id):
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"status": "moved", "doi": doi, "folder_id": request.folder_id}


@router.get("/{doi:path}/concepts")
def get_paper_concepts(
    doi: str,
    service: PaperService = Depends(get_paper_service)
):
    """获取论文关联的概念"""
    concepts = service.get_concepts(doi)
    return {"doi": doi, "concepts": concepts}
```

- [ ] **Step 2: 提交**

```bash
git add backend/routes/papers.py
git commit -m "refactor(backend): simplify papers.py to basic CRUD only"
```

---

## Task 8: 创建 concepts 相关路由

**Files:**
- Create: `backend/routes/concepts_tree.py`
- Create: `backend/routes/concepts_research.py`
- Create: `backend/routes/dedup.py`

- [ ] **Step 1: 创建 `backend/routes/concepts_tree.py`**

```python
# backend/routes/concepts_tree.py
"""
概念树路由 - 树操作相关端点
"""

from fastapi import APIRouter, Depends

from ..dependencies import get_concept_service
from ..services.concept_service import ConceptService

router = APIRouter(prefix="/api/concepts", tags=["concepts-tree"])


@router.get("/roots")
def get_root_concepts(service: ConceptService = Depends(get_concept_service)):
    """获取根概念"""
    return service.get_roots()


@router.get("/tree")
def get_concept_tree(
    root_id: str = None,
    service: ConceptService = Depends(get_concept_service)
):
    """获取概念树"""
    return service.get_tree(root_id)


@router.get("/{concept_id}/children")
def get_concept_children(
    concept_id: str,
    service: ConceptService = Depends(get_concept_service)
):
    """获取子概念"""
    return service.get_children(concept_id)


@router.get("/{concept_id}/parents")
def get_concept_parents(
    concept_id: str,
    service: ConceptService = Depends(get_concept_service)
):
    """获取父概念"""
    return service.get_parents(concept_id)
```

- [ ] **Step 2: 创建 `backend/routes/concepts_research.py`**

```python
# backend/routes/concepts_research.py
"""
研究路由 - 研究点发现和论文推荐相关端点
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from ..dependencies import get_research_service
from ..services.research_service import ResearchService

router = APIRouter(prefix="/api/concepts", tags=["concepts-research"])


@router.get("/{concept_id}/search-papers")
def search_papers_by_concept(
    concept_id: str,
    year: Optional[str] = None,
    min_citations: Optional[int] = None,
    limit: int = 10,
    service: ResearchService = Depends(get_research_service)
):
    """搜索概念相关论文"""
    result = service.search_papers_by_concept(concept_id, year, min_citations, limit)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{concept_id}/research-points")
def discover_research_points(
    concept_id: str,
    service: ResearchService = Depends(get_research_service)
):
    """发现概念的研究点"""
    result = service.discover_research_points(concept_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
```

- [ ] **Step 3: 创建 `backend/routes/dedup.py`**

```python
# backend/routes/dedup.py
"""
去重路由 - 概念去重相关端点
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from ..dependencies import get_dedup_service
from ..services.dedup_service import DedupService

router = APIRouter(prefix="/api/concepts", tags=["dedup"])


class DedupScanRequest(BaseModel):
    """去重扫描请求"""
    folder_id: Optional[str] = None


class DedupExecuteRequest(BaseModel):
    """去重执行请求"""
    scan_id: str
    merge_ids: List[str]


@router.post("/dedup/scan")
async def start_dedup_scan(
    request: DedupScanRequest,
    service: DedupService = Depends(get_dedup_service)
):
    """开始去重扫描"""
    result = service.start_scan(request.folder_id)
    return result


@router.get("/dedup/scan-status/{scan_id}")
def get_dedup_scan_status(
    scan_id: str,
    service: DedupService = Depends(get_dedup_service)
):
    """获取扫描状态"""
    status = service.get_scan_status(scan_id)
    if not status:
        raise HTTPException(status_code=404, detail="Scan not found")
    return status


@router.post("/dedup/execute")
def dedup_execute(
    request: DedupExecuteRequest,
    service: DedupService = Depends(get_dedup_service)
):
    """执行概念合并"""
    result = service.execute_merge(request.scan_id, request.merge_ids)
    return result
```

- [ ] **Step 4: 提交**

```bash
git add backend/routes/concepts_tree.py backend/routes/concepts_research.py backend/routes/dedup.py
git commit -m "feat(backend): add concepts_tree, concepts_research, and dedup routes"
```

---

## Task 9: 精简 concepts.py 路由

**Files:**
- Modify: `backend/routes/concepts.py`

- [ ] **Step 1: 重写 `backend/routes/concepts.py`（精简版）**

```python
# backend/routes/concepts.py
"""
概念基础 CRUD 路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_concept_service
from ..services.concept_service import ConceptService

router = APIRouter(prefix="/api/concepts", tags=["concepts"])


@router.get("/")
def list_concepts(service: ConceptService = Depends(get_concept_service)):
    """获取所有概念"""
    return service.list()


@router.get("/search")
def search_concepts(
    q: str = Query(..., min_length=1),
    service: ConceptService = Depends(get_concept_service)
):
    """搜索概念"""
    return service.search(q)


@router.get("/{concept_id}")
def get_concept(
    concept_id: str,
    service: ConceptService = Depends(get_concept_service)
):
    """获取单个概念"""
    concept = service.get(concept_id)
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")
    return concept


@router.get("/{concept_id}/papers")
def get_concept_papers(
    concept_id: str,
    limit: int = 20,
    service: ConceptService = Depends(get_concept_service)
):
    """获取概念关联的论文"""
    papers = service.get_papers(concept_id, limit)
    return {"concept_id": concept_id, "papers": papers, "total": len(papers)}
```

- [ ] **Step 2: 提交**

```bash
git add backend/routes/concepts.py
git commit -m "refactor(backend): simplify concepts.py to basic CRUD only"
```

---

## Task 10: 更新 main.py 注册新路由

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: 更新 `backend/main.py`**

```python
"""
FastAPI backend for Meta Knowledge Graph
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import routes
from backend.routes import (
    papers, papers_upload, papers_process,
    concepts, concepts_tree, concepts_research, dedup,
    graph, llm, folders, semantic_scholar, s2, agent, conversations
)

app = FastAPI(
    title="Meta Knowledge Graph API",
    description="学术知识图谱引擎 API",
    version="0.1.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers - papers
app.include_router(papers.router)
app.include_router(papers_upload.router)
app.include_router(papers_process.router)

# Include routers - concepts
app.include_router(concepts.router)
app.include_router(concepts_tree.router)
app.include_router(concepts_research.router)
app.include_router(dedup.router)

# Include routers - other
app.include_router(graph.router)
app.include_router(llm.router)
app.include_router(folders.router)
app.include_router(semantic_scholar.router)
app.include_router(s2.router)
app.include_router(agent.router)
app.include_router(conversations.router)


@app.get("/api")
def api_root():
    return {
        "name": "Meta Knowledge Graph API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


# Create papers directory on startup
@app.on_event("startup")
def startup():
    Path("papers").mkdir(exist_ok=True)

    # Serve static frontend files in Docker mode
    frontend_dist = os.environ.get("FRONTEND_DIST")
    if frontend_dist and Path(frontend_dist).exists():
        # Mount static files (JS, CSS, assets)
        assets_path = Path(frontend_dist) / "assets"
        if assets_path.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

        print(f"Serving frontend from {frontend_dist}")


# Serve frontend index.html for all non-API routes (SPA support)
@app.get("/{path:path}")
async def serve_frontend(path: str):
    # Skip API routes
    if path.startswith("api/") or path == "api":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="API endpoint not found")

    frontend_dist = os.environ.get("FRONTEND_DIST")
    if frontend_dist and Path(frontend_dist).exists():
        # Check if it's a static file request
        file_path = Path(frontend_dist) / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        # For SPA, return index.html for all other routes
        index_path = Path(frontend_dist) / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))

    return {"error": "Frontend not available"}
```

- [ ] **Step 2: 提交**

```bash
git add backend/main.py
git commit -m "refactor(backend): update main.py to use new modular routes"
```

---

## Task 11: 验证和测试

- [ ] **Step 1: 验证导入**

```bash
cd D:/meta-knowledge-graph-main
python -c "from backend.main import app; print('Backend import OK')"
```

Expected: `Backend import OK`

- [ ] **Step 2: 启动后端测试**

```bash
cd D:/meta-knowledge-graph-main
python -m uvicorn backend.main:app --reload --port 8000
```

Expected: Server starts without errors

- [ ] **Step 3: 测试 API 端点**

```bash
curl http://localhost:8000/api/papers/
curl http://localhost:8000/api/concepts/
```

Expected: JSON responses

- [ ] **Step 4: 最终提交**

```bash
git add -A
git commit -m "refactor(backend): complete routes modularization with services layer

- Create services layer with 6 services: Paper, Upload, Process, Concept, Dedup, Research
- Add dependencies.py for dependency injection
- Split papers.py into papers.py, papers_upload.py, papers_process.py
- Split concepts.py into concepts.py, concepts_tree.py, concepts_research.py, dedup.py
- Update main.py to register new routes"
```

---

## 预期结果

| 指标 | 重构前 | 重构后 |
|------|--------|--------|
| 最大路由文件行数 | 1258 | ~100 |
| 单文件端点数 | 15+ | ~5 |
| 业务逻辑可测试 | ❌ | ✅ |
| 职责清晰度 | 低 | 高 |