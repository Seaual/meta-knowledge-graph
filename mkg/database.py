"""
SQLite 数据库管理 - 论文、概念、动态层级关系存储

新设计：
- concepts 表：存储概念（原 keywords），移除固定 level 字段
- concept_relations 表：存储父子概念关系（动态层级）
- paper_concepts 表：论文 - 概念多对多关联
"""

import sqlite3
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict


class Database:
    """SQLite 数据库管理类"""

    def __init__(self, db_path: str = "mkg.db"):
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()

    def connect(self):
        """连接到数据库"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # 启用 WAL 模式以支持并发读写
        self.conn.execute("PRAGMA journal_mode=WAL")
        # 设置繁忙超时为 30 秒
        self.conn.execute("PRAGMA busy_timeout=30000")
        # 设置外键约束
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_tables()
        self.ensure_default_folder()  # 确保默认文件夹存在

    def get_cursor(self):
        """获取数据库游标（线程安全）"""
        with self._lock:
            return self.conn.cursor()

    def execute_write(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行写操作（线程安全）"""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return cursor

    def execute_read(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行读操作（线程安全）"""
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def _init_tables(self):
        """初始化数据表"""
        cursor = self.conn.cursor()

        # 论文表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                doi TEXT PRIMARY KEY,
                arxiv_id TEXT UNIQUE,
                title TEXT NOT NULL,
                abstract TEXT,
                authors TEXT,  -- JSON array
                keywords TEXT,  -- JSON array - 关键词
                contributions TEXT,  -- JSON array - 创新点
                published_date TEXT,
                pdf_path TEXT,
                status TEXT DEFAULT 'pending',  -- pending/downloaded/processed/failed
                error_message TEXT,
                s2_paper_id TEXT,  -- Semantic Scholar 论文 ID
                venue TEXT,  -- 期刊/会议
                year INTEGER,  -- 发表年份
                citation_count INTEGER,  -- 引用数
                reference_count INTEGER,  -- 参考文献数
                influential_citation_count INTEGER,  -- 影响力引用数
                open_access_pdf TEXT,  -- 开放获取 PDF 信息 (JSON)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 概念表 - 动态层级（原 keywords 表）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concepts (
                id TEXT PRIMARY KEY,  -- slug: "reinforcement-learning"
                text TEXT NOT NULL,   -- 显示名
                category TEXT,  -- field/direction/subdirection/task/method/technique
                paper_count INTEGER DEFAULT 0,
                depth_cache INTEGER DEFAULT -1,  -- 缓存深度（从根节点到该节点的层数），-1 表示未计算
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 论文 - 概念关联表（支持多归属）
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paper_concepts (
                paper_doi TEXT,
                concept_id TEXT,
                confidence REAL DEFAULT 1.0,
                source TEXT DEFAULT 'llm',  -- llm/author/extracted
                PRIMARY KEY (paper_doi, concept_id),
                FOREIGN KEY (paper_doi) REFERENCES papers(doi),
                FOREIGN KEY (concept_id) REFERENCES concepts(id)
            )
        """)

        # 概念层级关系表 - 动态父子关系
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concept_relations (
                parent_id TEXT,
                child_id TEXT,
                relation_type TEXT DEFAULT 'is_subconcept_of',
                strength REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (parent_id, child_id),
                FOREIGN KEY (parent_id) REFERENCES concepts(id),
                FOREIGN KEY (child_id) REFERENCES concepts(id)
            )
        """)

        # 处理日志表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_doi TEXT,
                action TEXT,  -- download/extract/build_graph
                status TEXT,  -- success/failed
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (paper_doi) REFERENCES papers(doi)
            )
        """)

        # 概念提取结果表 - 存储 LLM 提取的完整概念结构
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS concept_extractions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_doi TEXT,
                concept_hierarchy TEXT,  -- JSON: 完整的概念树结构
                raw_llm_response TEXT,   -- LLM 原始响应
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (paper_doi) REFERENCES papers(doi)
            )
        """)

        # 批量任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS batch_jobs (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total INTEGER,
                completed INTEGER DEFAULT 0,
                successful INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending'
            )
        """)

        # LLM 配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT NOT NULL DEFAULT 'single',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_provider_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_id INTEGER NOT NULL,
                function_group TEXT,
                provider TEXT NOT NULL,
                api_key TEXT,
                base_url TEXT,
                model TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (config_id) REFERENCES llm_config(id)
            )
        """)

        # 文件夹表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS folders (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                paper_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 添加 folder_id 列（如果不存在）
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN folder_id TEXT DEFAULT 'default'")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # 添加 is_anchor 和 contribution_role 列到 paper_concepts 表（如果不存在）
        try:
            cursor.execute("ALTER TABLE paper_concepts ADD COLUMN is_anchor INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            cursor.execute("ALTER TABLE paper_concepts ADD COLUMN contribution_role TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # 扫描任务表 - 用于去重扫描进度跟踪
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scan_jobs (
                id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'pending',
                phase TEXT DEFAULT 'prefiltering',
                total_concepts INTEGER DEFAULT 0,
                concepts_scanned INTEGER DEFAULT 0,
                batches_total INTEGER DEFAULT 0,
                batches_completed INTEGER DEFAULT 0,
                filtered_count INTEGER DEFAULT 0,
                high_confidence_count INTEGER DEFAULT 0,
                suggestions TEXT,
                error TEXT,
                created_at REAL,
                started_at REAL,
                completed_at REAL
            )
        """)

        # Add new columns to existing scan_jobs table
        try:
            cursor.execute("ALTER TABLE scan_jobs ADD COLUMN phase TEXT DEFAULT 'prefiltering'")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE scan_jobs ADD COLUMN batches_total INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE scan_jobs ADD COLUMN batches_completed INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE scan_jobs ADD COLUMN filtered_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE scan_jobs ADD COLUMN high_confidence_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_concept_relations_parent
            ON concept_relations(parent_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_concept_relations_child
            ON concept_relations(child_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_paper_concepts
            ON paper_concepts(concept_id)
        """)

        # Semantic Scholar 配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS s2_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                api_key TEXT,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 迁移：为已存在的 papers 表添加新字段
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN s2_paper_id TEXT")
        except sqlite3.OperationalError:
            pass  # 字段已存在
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN venue TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN year INTEGER")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN citation_count INTEGER")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN reference_count INTEGER")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN influential_citation_count INTEGER")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN open_access_pdf TEXT")
        except sqlite3.OperationalError:
            pass
        # 新增：DOI 和外部 ID 字段
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN s2_doi TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN s2_arxiv_id TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN s2_external_ids TEXT")
        except sqlite3.OperationalError:
            pass

        # 新增：TLDR 和研究领域字段
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN tldr TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN s2_fields_of_study TEXT")
        except sqlite3.OperationalError:
            pass

        # 新增：S2 匹配时间
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN s2_matched_at TIMESTAMP")
        except sqlite3.OperationalError:
            pass

        # 新增：Open Access PDF URL（独立字段）
        try:
            cursor.execute("ALTER TABLE papers ADD COLUMN open_access_pdf_url TEXT")
        except sqlite3.OperationalError:
            pass

        # ============================================================
        # 新表：论文引用关系
        # ============================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paper_citations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                citing_paper_id TEXT NOT NULL,
                cited_paper_id TEXT NOT NULL,
                citing_s2_id TEXT,
                cited_s2_id TEXT,
                citing_title TEXT,
                citing_year INTEGER,
                cited_title TEXT,
                cited_year INTEGER,
                cited_citation_count INTEGER,
                is_internal BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(citing_paper_id, cited_paper_id)
            )
        """)

        # 新表：S2 推荐论文缓存
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS s2_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                recommended_s2_id TEXT NOT NULL,
                recommended_title TEXT,
                recommended_abstract TEXT,
                recommended_year INTEGER,
                recommended_citation_count INTEGER,
                recommended_tldr TEXT,
                recommended_open_access_pdf TEXT,
                score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 为 paper_citations 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_paper_citations_citing
            ON paper_citations(citing_paper_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_paper_citations_cited
            ON paper_citations(cited_paper_id)
        """)

        # 为 s2_recommendations 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_s2_recommendations_source
            ON s2_recommendations(source_type, source_id)
        """)

        # 迁移：添加 citing_title 和 citing_year 字段到 paper_citations 表
        try:
            cursor.execute("ALTER TABLE paper_citations ADD COLUMN citing_title TEXT")
        except:
            pass  # 字段已存在
        try:
            cursor.execute("ALTER TABLE paper_citations ADD COLUMN citing_year INTEGER")
        except:
            pass  # 字段已存在

        # 迁移：添加 text_en 字段到 concepts 表（英文概念名）
        try:
            cursor.execute("ALTER TABLE concepts ADD COLUMN text_en TEXT")
        except:
            pass  # 字段已存在

        self.conn.commit()

    def add_paper(self, paper_data: dict) -> str:
        """添加或更新论文"""
        cursor = self.conn.cursor()

        # 检查是否已存在（通过 DOI）
        cursor.execute("SELECT doi FROM papers WHERE doi = ?",
                      (paper_data.get('doi'),))
        existing = cursor.fetchone()

        if existing:
            # 更新
            cursor.execute("""
                UPDATE papers SET
                    title = ?, abstract = ?, authors = ?,
                    keywords = ?, contributions = ?,
                    pdf_path = ?, published_date = ?,
                    s2_paper_id = ?, venue = ?, year = ?,
                    citation_count = ?, reference_count = ?, influential_citation_count = ?,
                    open_access_pdf = ?, s2_doi = ?, s2_arxiv_id = ?, s2_external_ids = ?,
                    tldr = ?, s2_fields_of_study = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE doi = ?
            """, (
                paper_data.get('title'),
                paper_data.get('abstract'),
                json.dumps(paper_data.get('authors', [])),
                json.dumps(paper_data.get('keywords', [])),
                json.dumps(paper_data.get('contributions', [])),
                paper_data.get('pdf_path'),
                paper_data.get('published'),
                paper_data.get('s2_paper_id'),
                paper_data.get('venue'),
                paper_data.get('year'),
                paper_data.get('citation_count'),
                paper_data.get('reference_count'),
                paper_data.get('influential_citation_count'),
                paper_data.get('open_access_pdf'),
                paper_data.get('s2_doi'),
                paper_data.get('s2_arxiv_id'),
                paper_data.get('s2_external_ids'),
                paper_data.get('tldr'),
                paper_data.get('s2_fields_of_study'),
                paper_data.get('doi')
            ))
            doi = existing['doi']
        else:
            # 插入
            doi = paper_data.get('doi', paper_data.get('arxiv_id'))
            cursor.execute("""
                INSERT INTO papers (doi, arxiv_id, title, abstract, authors, keywords, contributions, pdf_path, published_date, status,
                    s2_paper_id, venue, year, citation_count, reference_count, influential_citation_count, open_access_pdf,
                    s2_doi, s2_arxiv_id, s2_external_ids, tldr, s2_fields_of_study)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doi,
                paper_data.get('arxiv_id'),
                paper_data.get('title'),
                paper_data.get('abstract'),
                json.dumps(paper_data.get('authors', [])),
                json.dumps(paper_data.get('keywords', [])),
                json.dumps(paper_data.get('contributions', [])),
                paper_data.get('pdf_path'),
                paper_data.get('published'),
                paper_data.get('s2_paper_id'),
                paper_data.get('venue'),
                paper_data.get('year'),
                paper_data.get('citation_count'),
                paper_data.get('reference_count'),
                paper_data.get('influential_citation_count'),
                paper_data.get('open_access_pdf'),
                paper_data.get('s2_doi'),
                paper_data.get('s2_arxiv_id'),
                paper_data.get('s2_external_ids'),
                paper_data.get('tldr'),
                paper_data.get('s2_fields_of_study'),
            ))

        self.conn.commit()
        return doi

    def update_paper_status(self, doi: str, status: str, error_message: str = None):
        """更新论文处理状态"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE papers SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE doi = ?
        """, (status, error_message, doi))
        self.conn.commit()

    def add_pdf_path(self, doi: str, pdf_path: str):
        """更新 PDF 路径"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE papers SET pdf_path = ?, status = 'downloaded', updated_at = CURRENT_TIMESTAMP
            WHERE doi = ?
        """, (pdf_path, doi))
        self.conn.commit()

    def get_paper(self, identifier: str) -> Optional[dict]:
        """获取论文（支持 DOI、arXiv ID 或 S2 Paper ID）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM papers WHERE doi = ? OR arxiv_id = ? OR s2_paper_id = ?
        """, (identifier, identifier, identifier))
        row = cursor.fetchone()
        if row:
            paper = dict(row)
            # Deserialize JSON fields
            if paper.get('authors') and isinstance(paper['authors'], str):
                try:
                    paper['authors'] = json.loads(paper['authors'])
                except:
                    paper['authors'] = []
            if paper.get('keywords') and isinstance(paper['keywords'], str):
                try:
                    paper['keywords'] = json.loads(paper['keywords'])
                except:
                    paper['keywords'] = []
            if paper.get('contributions') and isinstance(paper['contributions'], str):
                try:
                    paper['contributions'] = json.loads(paper['contributions'])
                except:
                    paper['contributions'] = []
            return paper
        return None

    def get_paper_by_s2_id(self, s2_paper_id: str) -> Optional[dict]:
        """通过 S2 paper ID 获取论文"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE s2_paper_id = ?", (s2_paper_id,))
        row = cursor.fetchone()
        if row:
            paper = dict(row)
            # Deserialize JSON fields
            if paper.get('authors') and isinstance(paper['authors'], str):
                try:
                    paper['authors'] = json.loads(paper['authors'])
                except:
                    paper['authors'] = []
            if paper.get('keywords') and isinstance(paper['keywords'], str):
                try:
                    paper['keywords'] = json.loads(paper['keywords'])
                except:
                    paper['keywords'] = []
            if paper.get('contributions') and isinstance(paper['contributions'], str):
                try:
                    paper['contributions'] = json.loads(paper['contributions'])
                except:
                    paper['contributions'] = []
            if paper.get('s2_fields_of_study') and isinstance(paper['s2_fields_of_study'], str):
                try:
                    paper['s2_fields_of_study'] = json.loads(paper['s2_fields_of_study'])
                except:
                    paper['s2_fields_of_study'] = []
            return paper
        return None

    def get_papers_by_status(self, status: str) -> list:
        """按状态获取论文列表"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE status = ?", (status,))
        papers = [dict(row) for row in cursor.fetchall()]
        # Deserialize JSON fields
        for paper in papers:
            if paper.get('authors') and isinstance(paper['authors'], str):
                try:
                    paper['authors'] = json.loads(paper['authors'])
                except:
                    paper['authors'] = []
            if paper.get('keywords') and isinstance(paper['keywords'], str):
                try:
                    paper['keywords'] = json.loads(paper['keywords'])
                except:
                    paper['keywords'] = []
            if paper.get('contributions') and isinstance(paper['contributions'], str):
                try:
                    paper['contributions'] = json.loads(paper['contributions'])
                except:
                    paper['contributions'] = []
            if paper.get('s2_fields_of_study') and isinstance(paper['s2_fields_of_study'], str):
                try:
                    paper['s2_fields_of_study'] = json.loads(paper['s2_fields_of_study'])
                except:
                    paper['s2_fields_of_study'] = []
        return papers

    def get_all_papers(self) -> list:
        """获取所有论文"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM papers ORDER BY created_at DESC")
        papers = [dict(row) for row in cursor.fetchall()]
        # Deserialize JSON fields
        for paper in papers:
            if paper.get('authors') and isinstance(paper['authors'], str):
                try:
                    paper['authors'] = json.loads(paper['authors'])
                except:
                    paper['authors'] = []
            if paper.get('keywords') and isinstance(paper['keywords'], str):
                try:
                    paper['keywords'] = json.loads(paper['keywords'])
                except:
                    paper['keywords'] = []
            if paper.get('contributions') and isinstance(paper['contributions'], str):
                try:
                    paper['contributions'] = json.loads(paper['contributions'])
                except:
                    paper['contributions'] = []
            if paper.get('s2_fields_of_study') and isinstance(paper['s2_fields_of_study'], str):
                try:
                    paper['s2_fields_of_study'] = json.loads(paper['s2_fields_of_study'])
                except:
                    paper['s2_fields_of_study'] = []
        return papers

    def update_paper_metadata(self, doi: str, metadata: dict):
        """更新论文元数据（作者、摘要、关键词、创新点、S2元数据等）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE papers SET
                title = COALESCE(?, title),
                abstract = COALESCE(?, abstract),
                authors = COALESCE(?, authors),
                keywords = COALESCE(?, keywords),
                contributions = COALESCE(?, contributions),
                s2_paper_id = COALESCE(?, s2_paper_id),
                s2_doi = COALESCE(?, s2_doi),
                citation_count = COALESCE(?, citation_count),
                reference_count = COALESCE(?, reference_count),
                influential_citation_count = COALESCE(?, influential_citation_count),
                venue = COALESCE(?, venue),
                year = COALESCE(?, year),
                tldr = COALESCE(?, tldr),
                s2_fields_of_study = COALESCE(?, s2_fields_of_study),
                open_access_pdf_url = COALESCE(?, open_access_pdf_url),
                s2_matched_at = COALESCE(?, s2_matched_at),
                updated_at = CURRENT_TIMESTAMP
            WHERE doi = ?
        """, (
            metadata.get('title'),
            metadata.get('abstract'),
            json.dumps(metadata['authors']) if metadata.get('authors') else None,
            json.dumps(metadata['keywords']) if metadata.get('keywords') else None,
            json.dumps(metadata['contributions']) if metadata.get('contributions') else None,
            metadata.get('s2_paper_id'),
            metadata.get('s2_doi'),
            metadata.get('citation_count'),
            metadata.get('reference_count'),
            metadata.get('influential_citation_count'),
            metadata.get('venue'),
            metadata.get('year'),
            metadata.get('tldr'),
            metadata.get('s2_fields_of_study'),
            metadata.get('open_access_pdf_url'),
            metadata.get('s2_matched_at'),
            doi
        ))
        self.conn.commit()

    # ========== 概念操作方法 ==========

    def add_concept(self, concept_data: dict) -> str:
        """添加概念（如果不存在）"""
        cursor = self.conn.cursor()
        concept_id = concept_data['id']

        # 检查概念是否已存在
        cursor.execute("SELECT id FROM concepts WHERE id = ?", (concept_id,))
        existing = cursor.fetchone()

        if existing:
            # 更新 text_en 如果提供了且当前为空
            if concept_data.get('text_en'):
                cursor.execute("""
                    UPDATE concepts SET text_en = ?
                    WHERE id = ? AND (text_en IS NULL OR text_en = '')
                """, (concept_data['text_en'], concept_id))
        else:
            # 插入新概念
            cursor.execute("""
                INSERT INTO concepts (id, text, text_en, category, paper_count, updated_at)
                VALUES (?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
            """, (
                concept_id,
                concept_data['text'],
                concept_data.get('text_en'),
                concept_data.get('category'),
            ))

        self.conn.commit()
        return concept_id

    def add_paper_concept(self, paper_doi: str, concept_id: str,
                          confidence: float = 1.0, source: str = 'llm',
                          is_anchor: bool = False, contribution_role: str = None):
        """添加论文 - 概念关联（支持多归属）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO paper_concepts (paper_doi, concept_id, confidence, source, is_anchor, contribution_role)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (paper_doi, concept_id, confidence, source, 1 if is_anchor else 0, contribution_role))

        # 更新 paper_count（基于实际关联数量）
        cursor.execute("""
            UPDATE concepts SET paper_count = (
                SELECT COUNT(DISTINCT paper_doi) FROM paper_concepts WHERE concept_id = ?
            ) WHERE id = ?
        """, (concept_id, concept_id))

        self.conn.commit()

    def add_concept_relation(self, parent_id: str, child_id: str,
                             relation_type: str = 'is_subconcept_of'):
        """添加概念层级关系（父子关系）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO concept_relations (parent_id, child_id, relation_type, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (parent_id, child_id, relation_type))
        self.conn.commit()

    def get_concept(self, concept_id: str) -> Optional[dict]:
        """获取概念"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM concepts WHERE id = ?", (concept_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_concept_by_text(self, text: str) -> Optional[dict]:
        """通过文本获取概念"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM concepts WHERE LOWER(text) = LOWER(?)", (text,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_root_concepts(self) -> list:
        """获取根概念（没有父节点的概念）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.* FROM concepts c
            LEFT JOIN concept_relations cr ON c.id = cr.child_id
            WHERE cr.parent_id IS NULL
            ORDER BY c.paper_count DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_all_concepts(self) -> list:
        """获取所有概念"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM concepts ORDER BY paper_count DESC")
        return [dict(row) for row in cursor.fetchall()]

    def get_concepts_by_category(self, category: str) -> list:
        """按类别获取概念

        Args:
            category: 概念类别 (field/direction/subdirection/task/method/technique)
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM concepts WHERE category = ? ORDER BY paper_count DESC
        """, (category,))
        return [dict(row) for row in cursor.fetchall()]

    def get_concepts_by_category_and_folder(self, category: str, folder_id: str) -> list:
        """按类别和文件夹获取概念

        Args:
            category: 概念类别 (field/direction/subdirection/task/method/technique)
            folder_id: 文件夹 ID
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT c.id, c.text, c.category, c.paper_count, c.depth_cache
            FROM concepts c
            JOIN paper_concepts pc ON c.id = pc.concept_id
            JOIN papers p ON pc.paper_doi = p.doi
            WHERE c.category = ? AND p.folder_id = ?
            ORDER BY c.paper_count DESC
        """, (category, folder_id))
        return [dict(row) for row in cursor.fetchall()]

    def get_concept_children(self, concept_id: str) -> list:
        """获取概念的子节点"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.* FROM concepts c
            JOIN concept_relations cr ON c.id = cr.child_id
            WHERE cr.parent_id = ?
            ORDER BY c.paper_count DESC
        """, (concept_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_concept_parents(self, concept_id: str) -> list:
        """获取概念的父节点"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.* FROM concepts c
            JOIN concept_relations cr ON c.id = cr.parent_id
            WHERE cr.child_id = ?
        """, (concept_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_concept_tree(self, root_id: str = None) -> dict:
        """获取概念树状结构"""
        cursor = self.conn.cursor()

        # 如果没有指定根节点，从根概念开始
        if root_id is None:
            roots = self.get_root_concepts()
            if roots:
                root_id = roots[0]['id']
            else:
                return {}

        concept = self.get_concept(root_id)
        if not concept:
            return {}

        # 递归获取子节点
        children = self.get_concept_children(root_id)
        concept['children'] = [self.get_concept_tree(child['id']) for child in children]

        # 获取关联论文
        cursor.execute("""
            SELECT p.doi, p.title FROM papers p
            JOIN paper_concepts pk ON p.doi = pk.paper_doi
            WHERE pk.concept_id = ?
        """, (root_id,))
        concept['papers'] = [{'doi': row['doi'], 'title': row['title']}
                            for row in cursor.fetchall()]

        return concept

    def get_papers_by_concept(self, concept_id: str) -> list:
        """获取概念关联的论文"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.* FROM papers p
            JOIN paper_concepts pk ON p.doi = pk.paper_doi
            WHERE pk.concept_id = ?
            ORDER BY p.published_date DESC
        """, (concept_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_concepts_by_paper(self, paper_doi: str) -> list:
        """获取论文关联的所有概念"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.* FROM concepts c
            JOIN paper_concepts pk ON c.id = pk.concept_id
            WHERE pk.paper_doi = ?
            ORDER BY pk.confidence DESC
        """, (paper_doi,))
        return [dict(row) for row in cursor.fetchall()]

    # ========== 概念提取结果存储 ==========

    def save_concept_extraction(self, paper_doi: str, hierarchy: dict, raw_response: str):
        """保存 LLM 提取的概念层级结构"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO concept_extractions (paper_doi, concept_hierarchy, raw_llm_response)
            VALUES (?, ?, ?)
        """, (paper_doi, json.dumps(hierarchy), raw_response))
        self.conn.commit()

    def get_concept_extraction(self, paper_doi: str) -> Optional[dict]:
        """获取已保存的概念提取结果"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM concept_extractions WHERE paper_doi = ?
        """, (paper_doi,))
        row = cursor.fetchone()
        if row:
            result = dict(row)
            result['concept_hierarchy'] = json.loads(result['concept_hierarchy'])
            return result
        return None

    # ========== 日志和统计 ==========

    def log_processing(self, paper_doi: str, action: str, status: str, message: str = None):
        """记录处理日志"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO processing_log (paper_doi, action, status, message)
            VALUES (?, ?, ?, ?)
        """, (paper_doi, action, status, message))
        self.conn.commit()

    def get_stats(self) -> dict:
        """获取统计信息"""
        cursor = self.conn.cursor()

        stats = {}

        # 论文统计
        cursor.execute("SELECT status, COUNT(*) as count FROM papers GROUP BY status")
        stats['papers'] = {row['status']: row['count'] for row in cursor.fetchall()}
        cursor.execute("SELECT COUNT(*) as count FROM papers")
        stats['papers']['total'] = cursor.fetchone()['count']

        # 概念统计
        cursor.execute("SELECT COUNT(*) as count FROM concepts")
        stats['concepts'] = {'total': cursor.fetchone()['count']}

        # 关系统计
        cursor.execute("SELECT COUNT(*) as count FROM concept_relations")
        stats['relations'] = cursor.fetchone()['count']

        # 根概念数量
        roots = self.get_root_concepts()
        stats['root_concepts'] = len(roots)

        return stats

    # ========== 批量操作方法 ==========

    def build_concept_tree_from_paper(self, paper_doi: str, concept_tree: dict):
        """
        从单篇论文的概念树构建/更新数据库

        Args:
            paper_doi: 论文 DOI
            concept_tree: LLM 返回的概念树结构（支持双语）
                {
                    "concept": {"en": "Artificial Intelligence", "zh": "人工智能"},
                    "category": "field",
                    "is_anchor": true,
                    "contribution_role": null,
                    "children": [...]
                }
                或旧格式：
                {
                    "concept": "人工智能",
                    "concept_en": "Artificial Intelligence",
                    ...
                }
        """
        # 递归插入概念树
        def insert_concept(node: dict, parent_id: str = None) -> str:
            # 解析概念名称（支持双语格式）
            concept_data = node.get('concept', '')
            if isinstance(concept_data, dict):
                # 新格式: {"en": "...", "zh": "..."}
                concept_text = concept_data.get('zh', concept_data.get('en', ''))
                concept_en = concept_data.get('en')
            else:
                # 旧格式
                concept_text = concept_data
                concept_en = node.get('concept_en')

            # 生成 ID（优先使用英文）
            concept_id = node.get('id', self._to_slug(concept_en or concept_text))

            # 创建或获取概念
            concept_data = {
                'id': concept_id,
                'text': concept_text,
                'text_en': concept_en,
                'category': node.get('category', 'method')
            }
            self.add_concept(concept_data)

            # 关联论文（包含 is_anchor 和 contribution_role）
            self.add_paper_concept(
                paper_doi, concept_id, node.get('confidence', 1.0),
                is_anchor=node.get('is_anchor', False),
                contribution_role=node.get('contribution_role')
            )

            # 建立父子关系
            if parent_id:
                self.add_concept_relation(parent_id, concept_id)

            # 递归处理子节点
            for child in node.get('children', []):
                insert_concept(child, concept_id)

            return concept_id

        # 从根节点开始插入
        insert_concept(concept_tree)

        # 更新论文状态
        self.update_paper_status(paper_doi, 'processed')

    def _to_slug(self, text: str) -> str:
        """将文本转换为 slug ID（支持中文）"""
        import re
        import hashlib

        # 尝试转换为拼音（如果安装了 pypinyin）
        try:
            from pypinyin import lazy_pinyin
            slug = '-'.join(lazy_pinyin(text))
            slug = slug.lower()
            slug = re.sub(r'[^a-z0-9-]', '', slug)
            slug = re.sub(r'-+', '-', slug)
            slug = slug.strip('-')
            if slug:
                return slug[:100]
        except ImportError:
            pass

        # 回退：使用文本的 hash 作为 ID
        # 对于英文，尝试正常转换
        slug = text.lower()
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        slug = slug.strip('-')

        if slug:
            return slug[:100]

        # 如果是纯中文或其他非拉丁字符，使用 hash
        return hashlib.md5(text.encode()).hexdigest()[:12]

    # ========== 合并去重操作方法 ==========

    def migrate_paper_concepts(self, source_id: str, target_id: str):
        """迁移论文关联：将 source 的论文关联迁移到 target"""
        cursor = self.conn.cursor()
        # 将 source 的论文关联迁移到 target（避免重复）
        cursor.execute("""
            INSERT OR IGNORE INTO paper_concepts (paper_doi, concept_id, confidence, source)
            SELECT paper_doi, ?, confidence, source
            FROM paper_concepts WHERE concept_id = ?
        """, (target_id, source_id))
        # 删除 source 的论文关联
        cursor.execute("""
            DELETE FROM paper_concepts WHERE concept_id = ?
        """, (source_id,))

        # 更新 target 的 paper_count
        cursor.execute("""
            UPDATE concepts SET paper_count = (
                SELECT COUNT(DISTINCT paper_doi) FROM paper_concepts WHERE concept_id = ?
            ) WHERE id = ?
        """, (target_id, target_id))

        self.conn.commit()

    def update_concept_relations(self, concept_id: str, relations: dict):
        """更新概念的父子关系

        Args:
            concept_id: 概念 ID
            relations: {"parents": [...], "children": [...]}
        """
        cursor = self.conn.cursor()

        # 删除现有的父子关系
        cursor.execute("""
            DELETE FROM concept_relations WHERE parent_id = ? OR child_id = ?
        """, (concept_id, concept_id))

        # 添加新的父关系
        for parent_id in relations.get("parents", []):
            cursor.execute("""
                INSERT OR IGNORE INTO concept_relations (parent_id, child_id)
                VALUES (?, ?)
            """, (parent_id, concept_id))

        # 添加新的子关系
        for child_id in relations.get("children", []):
            cursor.execute("""
                INSERT OR IGNORE INTO concept_relations (parent_id, child_id)
                VALUES (?, ?)
            """, (concept_id, child_id))

        self.conn.commit()

    def delete_concept(self, concept_id: str):
        """删除概念及其所有关联"""
        cursor = self.conn.cursor()

        # 删除论文关联
        cursor.execute("DELETE FROM paper_concepts WHERE concept_id = ?", (concept_id,))

        # 删除层级关系
        cursor.execute("""
            DELETE FROM concept_relations WHERE parent_id = ? OR child_id = ?
        """, (concept_id, concept_id))

        # 删除概念本身
        cursor.execute("DELETE FROM concepts WHERE id = ?", (concept_id,))

        self.conn.commit()

    def recalculate_depth_cache(self, concept_id: str = None):
        """重新计算概念的深度缓存

        使用 BFS 从根节点开始计算所有概念的深度
        """
        cursor = self.conn.cursor()

        # 重置所有 depth_cache
        cursor.execute("UPDATE concepts SET depth_cache = -1")

        # 获取根概念（没有父节点的概念）
        cursor.execute("""
            SELECT id FROM concepts c
            LEFT JOIN concept_relations cr ON c.id = cr.child_id
            WHERE cr.parent_id IS NULL
        """)
        roots = [row['id'] for row in cursor.fetchall()]

        # BFS 计算深度
        from collections import deque
        queue = deque([(root_id, 0) for root_id in roots])

        while queue:
            node_id, depth = queue.popleft()

            # 更新深度
            cursor.execute("""
                UPDATE concepts SET depth_cache = ? WHERE id = ?
            """, (depth, node_id))

            # 获取子节点
            cursor.execute("""
                SELECT child_id FROM concept_relations WHERE parent_id = ?
            """, (node_id,))
            children = [row['child_id'] for row in cursor.fetchall()]

            for child_id in children:
                queue.append((child_id, depth + 1))

        self.conn.commit()

    # ========== 批量任务操作方法 ==========

    def create_batch_job(self, job_id: str, total: int):
        """创建批量任务"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO batch_jobs (id, total, status)
            VALUES (?, ?, 'pending')
        """, (job_id, total))
        self.conn.commit()

    def get_batch_job(self, job_id: str) -> Optional[dict]:
        """获取批量任务状态"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM batch_jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_batch_job(self, job_id: str, completed: int, successful: int, failed: int, status: str):
        """更新批量任务状态"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE batch_jobs
            SET completed = ?, successful = ?, failed = ?, status = ?
            WHERE id = ?
        """, (completed, successful, failed, status, job_id))
        self.conn.commit()

    # ========== 扫描任务操作方法 ==========

    def create_scan_job(self, scan_id: str, total_concepts: int):
        """创建扫描任务"""
        import time
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO scan_jobs (id, total_concepts, status, created_at)
            VALUES (?, ?, 'pending', ?)
        """, (scan_id, total_concepts, time.time()))
        self.conn.commit()

    def get_scan_job(self, scan_id: str) -> Optional[dict]:
        """获取扫描任务状态"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM scan_jobs WHERE id = ?", (scan_id,))
        row = cursor.fetchone()
        if not row:
            return None
        result = dict(row)
        # Parse suggestions JSON if present
        if result.get('suggestions') and isinstance(result['suggestions'], str):
            try:
                import json
                result['suggestions'] = json.loads(result['suggestions'])
            except:
                result['suggestions'] = None
        return result

    def update_scan_job(self, scan_id: str, **kwargs):
        """更新扫描任务状态"""
        import time
        cursor = self.conn.cursor()

        # Build dynamic update query
        set_parts = []
        values = []
        for key, value in kwargs.items():
            if key == 'suggestions' and isinstance(value, (list, dict)):
                import json
                value = json.dumps(value)
            set_parts.append(f"{key} = ?")
            values.append(value)

        if not set_parts:
            return

        values.append(scan_id)
        cursor.execute(f"""
            UPDATE scan_jobs SET {', '.join(set_parts)}
            WHERE id = ?
        """, values)
        self.conn.commit()

    def cleanup_old_scan_jobs(self, max_age_hours: int = 24):
        """清理过期的扫描任务"""
        import time
        cursor = self.conn.cursor()
        cutoff = time.time() - (max_age_hours * 3600)
        cursor.execute(
            "DELETE FROM scan_jobs WHERE completed_at < ? OR (status IN ('completed', 'failed') AND created_at < ?)",
            (cutoff, cutoff)
        )
        self.conn.commit()

    def get_concept_count(self, folder_id: str = None) -> int:
        """获取概念总数，可选按文件夹过滤"""
        cursor = self.conn.cursor()
        if folder_id and folder_id != 'default':
            # 获取该文件夹中论文关联的概念数
            cursor.execute("""
                SELECT COUNT(DISTINCT c.id) as count
                FROM concepts c
                JOIN paper_concepts pc ON c.id = pc.concept_id
                JOIN papers p ON pc.paper_doi = p.doi
                WHERE p.folder_id = ?
            """, (folder_id,))
        else:
            cursor.execute("SELECT COUNT(*) as count FROM concepts")
        return cursor.fetchone()['count']

    # ========== LLM Configuration ==========

    def get_llm_config(self) -> Optional[Dict]:
        """Get current LLM configuration"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM llm_config ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            return None

        config = dict(row)
        config_id = config['id']

        # Get provider configs
        cursor.execute("SELECT * FROM llm_provider_config WHERE config_id = ?", (config_id,))
        providers = [dict(r) for r in cursor.fetchall()]
        config['providers'] = providers

        return config

    def save_llm_config(self, mode: str, providers: List[Dict]) -> Dict:
        """Save LLM configuration"""
        cursor = self.conn.cursor()

        # Clear existing config
        cursor.execute("DELETE FROM llm_provider_config")
        cursor.execute("DELETE FROM llm_config")

        # Insert new config
        cursor.execute(
            "INSERT INTO llm_config (mode) VALUES (?)",
            (mode,)
        )
        config_id = cursor.lastrowid

        # Insert provider configs
        for p in providers:
            cursor.execute("""
                INSERT INTO llm_provider_config
                (config_id, function_group, provider, api_key, base_url, model, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                config_id,
                p.get('function_group'),
                p['provider'],
                p.get('api_key'),
                p.get('base_url'),
                p.get('model'),
                p.get('is_active', True)
            ))

        self.conn.commit()
        return self.get_llm_config()

    def get_llm_provider_for_function(self, function_group: str) -> Optional[Dict]:
        """Get provider config for a specific function"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.* FROM llm_provider_config p
            JOIN llm_config c ON p.config_id = c.id
            WHERE c.mode = 'per_function' AND p.function_group = ? AND p.is_active = 1
        """, (function_group,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_active_llm_provider(self) -> Optional[Dict]:
        """Get the active provider (for single mode)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT p.* FROM llm_provider_config p
            JOIN llm_config c ON p.config_id = c.id
            WHERE c.mode = 'single' AND p.is_active = 1
            LIMIT 1
        """)
        row = cursor.fetchone()
        return dict(row) if row else None

    # ========== 文件夹操作方法 ==========

    def get_all_folders(self) -> list:
        """获取所有文件夹"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM folders ORDER BY created_at")
        return [dict(row) for row in cursor.fetchall()]

    def get_folder(self, folder_id: str) -> Optional[dict]:
        """获取单个文件夹"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM folders WHERE id = ?", (folder_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def create_folder(self, folder_data: dict) -> str:
        """创建文件夹"""
        cursor = self.conn.cursor()
        folder_id = self._to_slug(folder_data['name'])
        cursor.execute("""
            INSERT OR IGNORE INTO folders (id, name, description)
            VALUES (?, ?, ?)
        """, (folder_id, folder_data['name'], folder_data.get('description')))
        self.conn.commit()
        return folder_id

    def update_folder(self, folder_id: str, data: dict):
        """更新文件夹"""
        cursor = self.conn.cursor()
        if 'name' in data:
            cursor.execute("UPDATE folders SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                          (data['name'], folder_id))
        if 'description' in data:
            cursor.execute("UPDATE folders SET description = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                          (data['description'], folder_id))
        self.conn.commit()

    def delete_folder(self, folder_id: str, delete_contents: bool = True) -> bool:
        """删除文件夹

        Args:
            folder_id: 文件夹ID
            delete_contents: 如果为 True，删除文件夹中的论文和孤立概念；
                            如果为 False，将论文移动到默认文件夹

        Returns:
            是否删除成功
        """
        if folder_id == 'default':
            return False  # 不能删除默认文件夹

        cursor = self.conn.cursor()
        # 检查文件夹是否存在
        cursor.execute("SELECT id FROM folders WHERE id = ?", (folder_id,))
        if not cursor.fetchone():
            return False  # 文件夹不存在

        if delete_contents:
            # 获取该文件夹中的所有论文
            cursor.execute("SELECT doi FROM papers WHERE folder_id = ?", (folder_id,))
            papers = [row['doi'] for row in cursor.fetchall()]

            # 删除每篇论文及其关联的概念（会自动清理孤立概念）
            for doi in papers:
                self.delete_paper_cascade(doi)
        else:
            # 将论文移到 default
            cursor.execute("UPDATE papers SET folder_id = 'default' WHERE folder_id = ?", (folder_id,))

        # 删除文件夹
        cursor.execute("DELETE FROM folders WHERE id = ?", (folder_id,))
        self.conn.commit()
        return True

    def ensure_default_folder(self):
        """确保默认文件夹存在"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM folders WHERE id = 'default'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO folders (id, name, description)
                VALUES ('default', '默认', '默认文件夹')
            """)
            self.conn.commit()

    def get_papers_by_folder(self, folder_id: str) -> list:
        """按文件夹获取论文"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE folder_id = ? ORDER BY created_at DESC", (folder_id,))
        papers = [dict(row) for row in cursor.fetchall()]
        for paper in papers:
            if paper.get('authors') and isinstance(paper['authors'], str):
                try:
                    paper['authors'] = json.loads(paper['authors'])
                except:
                    paper['authors'] = []
            if paper.get('keywords') and isinstance(paper['keywords'], str):
                try:
                    paper['keywords'] = json.loads(paper['keywords'])
                except:
                    paper['keywords'] = []
            if paper.get('contributions') and isinstance(paper['contributions'], str):
                try:
                    paper['contributions'] = json.loads(paper['contributions'])
                except:
                    paper['contributions'] = []
            if paper.get('s2_fields_of_study') and isinstance(paper['s2_fields_of_study'], str):
                try:
                    paper['s2_fields_of_study'] = json.loads(paper['s2_fields_of_study'])
                except:
                    paper['s2_fields_of_study'] = []
        return papers

    def move_paper_to_folder(self, doi: str, folder_id: str):
        """移动论文到文件夹"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE papers SET folder_id = ? WHERE doi = ?", (folder_id, doi))
        self.conn.commit()

    def get_concepts_by_folder(self, folder_id: str) -> list:
        """获取指定文件夹中的论文关联的所有概念"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT c.id, c.text, c.category, c.paper_count, c.depth_cache
            FROM concepts c
            JOIN paper_concepts pc ON c.id = pc.concept_id
            JOIN papers p ON pc.paper_doi = p.doi
            WHERE p.folder_id = ?
        """, (folder_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_concept_relations_by_folder(self, folder_id: str) -> list:
        """获取指定文件夹中的概念关系（确保两端节点都在文件夹中）"""
        cursor = self.conn.cursor()
        # 先获取该文件夹中所有概念的 ID 集合
        cursor.execute("""
            SELECT DISTINCT c.id
            FROM concepts c
            JOIN paper_concepts pc ON c.id = pc.concept_id
            JOIN papers p ON pc.paper_doi = p.doi
            WHERE p.folder_id = ?
        """, (folder_id,))
        concept_ids = set(row['id'] for row in cursor.fetchall())

        # 获取所有关系，然后过滤
        cursor.execute("""
            SELECT DISTINCT cr.parent_id, cr.child_id
            FROM concept_relations cr
            JOIN paper_concepts pc1 ON cr.parent_id = pc1.concept_id
            JOIN papers p1 ON pc1.paper_doi = p1.doi
            WHERE p1.folder_id = ?
        """, (folder_id,))

        # 只返回两端节点都在文件夹中的关系
        relations = []
        for row in cursor.fetchall():
            if row['parent_id'] in concept_ids and row['child_id'] in concept_ids:
                relations.append(dict(row))
        return relations

    def get_paper_contribution(self, doi: str) -> dict:
        """获取论文贡献的概念节点数和根概念"""
        cursor = self.conn.cursor()

        # 获取该论文关联的概念数
        cursor.execute("""
            SELECT COUNT(*) as count FROM paper_concepts WHERE paper_doi = ?
        """, (doi,))
        node_count = cursor.fetchone()['count']

        # 获取根概念（该论文的概念树的根）
        cursor.execute("""
            SELECT c.text FROM concepts c
            JOIN paper_concepts pc ON c.id = pc.concept_id
            LEFT JOIN concept_relations cr ON c.id = cr.child_id
            WHERE pc.paper_doi = ? AND cr.parent_id IS NULL
            LIMIT 1
        """, (doi,))
        row = cursor.fetchone()
        root_concept = row['text'] if row else None

        return {"node_count": node_count, "root_concept": root_concept}

    def delete_paper_cascade(self, doi: str):
        """
        删除论文及其孤立的概念节点

        工作流程：
        1. 获取该论文关联的所有概念
        2. 删除 paper_concepts 关联
        3. 对每个概念，检查是否有其他论文引用
        4. 如果没有，删除该概念并递归检查子概念
        5. 清理 concept_relations 记录
        """
        cursor = self.conn.cursor()

        # 获取该论文关联的概念
        cursor.execute("""
            SELECT concept_id FROM paper_concepts WHERE paper_doi = ?
        """, (doi,))
        concepts = [row['concept_id'] for row in cursor.fetchall()]

        # 删除 paper_concepts 关联
        cursor.execute("DELETE FROM paper_concepts WHERE paper_doi = ?", (doi,))

        # 删除 concept_extractions
        cursor.execute("DELETE FROM concept_extractions WHERE paper_doi = ?", (doi,))

        # 删除 processing_log
        cursor.execute("DELETE FROM processing_log WHERE paper_doi = ?", (doi,))

        # 检查并删除孤立概念
        for concept_id in concepts:
            self._delete_orphaned_concept(concept_id)

        # 删除论文
        cursor.execute("DELETE FROM papers WHERE doi = ?", (doi,))

        self.conn.commit()

    def _delete_orphaned_concept(self, concept_id: str):
        """递归删除孤立概念（没有论文引用的概念）"""
        cursor = self.conn.cursor()

        # 检查是否有其他论文引用此概念
        cursor.execute("""
            SELECT COUNT(*) as count FROM paper_concepts WHERE concept_id = ?
        """, (concept_id,))

        if cursor.fetchone()['count'] > 0:
            return  # 还有论文引用，不删除

        # 获取子概念
        cursor.execute("""
            SELECT child_id FROM concept_relations WHERE parent_id = ?
        """, (concept_id,))
        children = [row['child_id'] for row in cursor.fetchall()]

        # 删除与父概念的关系以及作为父节点的关系
        cursor.execute("DELETE FROM concept_relations WHERE child_id = ? OR parent_id = ?", (concept_id, concept_id))

        # 删除概念本身
        cursor.execute("DELETE FROM concepts WHERE id = ?", (concept_id,))

        # 递归检查子概念
        for child_id in children:
            self._delete_orphaned_concept(child_id)

    # ==================== Semantic Scholar Config ====================

    def get_s2_config(self) -> Optional[Dict]:
        """获取 Semantic Scholar 配置"""
        cursor = self.execute_read("SELECT * FROM s2_config WHERE id = 1")
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def save_s2_config(self, api_key: str, enabled: bool = True) -> Dict:
        """保存 Semantic Scholar 配置"""
        cursor = self.execute_write("""
            INSERT INTO s2_config (id, api_key, enabled, updated_at)
            VALUES (1, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                api_key = excluded.api_key,
                enabled = excluded.enabled,
                updated_at = CURRENT_TIMESTAMP
        """, (api_key, enabled))
        return self.get_s2_config()

    # ==================== Paper Citations ====================

    def add_paper_citation(self, data: Dict):
        """
        添加论文引用关系

        Args:
            data: {
                citing_paper_id, cited_paper_id,
                citing_s2_id, cited_s2_id,
                citing_title, citing_year,
                cited_title, cited_year, cited_citation_count,
                is_internal
            }
        """
        self.execute_write("""
            INSERT INTO paper_citations (
                citing_paper_id, cited_paper_id,
                citing_s2_id, cited_s2_id,
                citing_title, citing_year,
                cited_title, cited_year, cited_citation_count,
                is_internal
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(citing_paper_id, cited_paper_id) DO UPDATE SET
                citing_title = excluded.citing_title,
                citing_year = excluded.citing_year,
                cited_title = excluded.cited_title,
                cited_year = excluded.cited_year,
                cited_citation_count = excluded.cited_citation_count,
                is_internal = excluded.is_internal
        """, (
            data['citing_paper_id'],
            data['cited_paper_id'],
            data.get('citing_s2_id'),
            data.get('cited_s2_id'),
            data.get('citing_title'),
            data.get('citing_year'),
            data.get('cited_title'),
            data.get('cited_year'),
            data.get('cited_citation_count'),
            data.get('is_internal', False)
        ))

    def get_paper_citations(self, paper_id: str) -> List[Dict]:
        """获取论文引用的所有论文（这篇论文引用了谁）"""
        cursor = self.execute_read("""
            SELECT * FROM paper_citations
            WHERE citing_paper_id = ?
            ORDER BY cited_citation_count DESC
        """, (paper_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_paper_cited_by(self, paper_id: str) -> List[Dict]:
        """获取引用了这篇论文的所有论文（谁引用了这篇论文）

        同时检查 DOI 和 S2 ID 匹配
        """
        # 先获取论文的 S2 paper ID
        paper = self.get_paper(paper_id)
        s2_id = paper.get('s2_paper_id') if paper else None

        if s2_id:
            # 同时匹配 DOI 和 S2 ID
            cursor = self.execute_read("""
                SELECT * FROM paper_citations
                WHERE cited_paper_id = ? OR cited_s2_id = ?
                ORDER BY cited_citation_count DESC
            """, (paper_id, s2_id))
        else:
            cursor = self.execute_read("""
                SELECT * FROM paper_citations
                WHERE cited_paper_id = ?
                ORDER BY cited_citation_count DESC
            """, (paper_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_internal_citation_edges(self) -> List[Dict]:
        """获取所有内部引用边（两端都在图谱中）

        通过 S2 ID 匹配来判断是否为内部引用
        """
        cursor = self.execute_read("""
            SELECT
                pc.citing_paper_id as source,
                pc.cited_paper_id as target,
                p1.title as source_title,
                COALESCE(p2.title, pc.cited_title) as target_title
            FROM paper_citations pc
            JOIN papers p1 ON pc.citing_paper_id = p1.doi
            LEFT JOIN papers p2 ON pc.cited_s2_id = p2.s2_paper_id
            WHERE p2.doi IS NOT NULL OR pc.is_internal = 1
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_papers_with_s2_id(self) -> List[Dict]:
        """获取所有有 S2 paper ID 的论文"""
        cursor = self.execute_read("""
            SELECT doi, title, s2_paper_id, citation_count, year, venue
            FROM papers
            WHERE s2_paper_id IS NOT NULL
            ORDER BY citation_count DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_all_papers_basic(self) -> List[Dict]:
        """获取所有论文的基本信息（用于引用图谱）"""
        cursor = self.execute_read("""
            SELECT doi, title, s2_paper_id, citation_count, year, venue
            FROM papers
            ORDER BY citation_count DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

    def get_all_citations(self) -> List[Dict]:
        """获取所有引用数据"""
        cursor = self.execute_read("SELECT * FROM paper_citations")
        return [dict(row) for row in cursor.fetchall()]

    def get_citation_by_s2_id(self, s2_id: str) -> Dict:
        """根据 S2 ID 获取引用信息"""
        cursor = self.execute_read("""
            SELECT cited_title, cited_year, cited_citation_count
            FROM paper_citations
            WHERE cited_s2_id = ?
            LIMIT 1
        """, (s2_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_citation_edges(self) -> List[Dict]:
        """获取所有引用边（用于引用图谱可视化）"""
        cursor = self.execute_read("""
            SELECT
                citing_paper_id as source,
                cited_s2_id as target,
                citing_title as source_title,
                cited_title as target_title,
                cited_year as target_year,
                cited_citation_count as target_citation_count
            FROM paper_citations
        """)
        return [dict(row) for row in cursor.fetchall()]

    def clear_paper_citations(self, paper_id: str = None):
        """清除论文引用关系（可选指定论文）"""
        if paper_id:
            self.execute_write(
                "DELETE FROM paper_citations WHERE citing_paper_id = ? OR cited_paper_id = ?",
                (paper_id, paper_id)
            )
        else:
            self.execute_write("DELETE FROM paper_citations")

    # ==================== S2 Recommendations ====================

    def add_s2_recommendation(self, data: Dict):
        """添加推荐论文"""
        self.execute_write("""
            INSERT INTO s2_recommendations (
                source_type, source_id,
                recommended_s2_id, recommended_title,
                recommended_abstract, recommended_year,
                recommended_citation_count, recommended_tldr,
                recommended_open_access_pdf, score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['source_type'],
            data['source_id'],
            data['recommended_s2_id'],
            data.get('recommended_title'),
            data.get('recommended_abstract'),
            data.get('recommended_year'),
            data.get('recommended_citation_count'),
            data.get('recommended_tldr'),
            data.get('recommended_open_access_pdf'),
            data.get('score')
        ))

    def get_s2_recommendations(self, source_type: str, source_id: str) -> List[Dict]:
        """获取推荐论文"""
        cursor = self.execute_read("""
            SELECT * FROM s2_recommendations
            WHERE source_type = ? AND source_id = ?
            ORDER BY score DESC, recommended_citation_count DESC
        """, (source_type, source_id))
        return [dict(row) for row in cursor.fetchall()]

    def clear_s2_recommendations(self, source_type: str = None, source_id: str = None):
        """清除推荐论文缓存"""
        if source_type and source_id:
            self.execute_write(
                "DELETE FROM s2_recommendations WHERE source_type = ? AND source_id = ?",
                (source_type, source_id)
            )
        elif source_type:
            self.execute_write(
                "DELETE FROM s2_recommendations WHERE source_type = ?",
                (source_type,)
            )
        else:
            self.execute_write("DELETE FROM s2_recommendations")

    # ==================== S2 Metadata Update ====================

    def update_paper_s2_metadata(self, doi: str, metadata: Dict):
        """
        更新论文的 S2 元数据

        Args:
            doi: 论文 DOI
            metadata: S2 元数据字典
        """
        self.execute_write("""
            UPDATE papers SET
                s2_paper_id = ?,
                s2_doi = ?,
                citation_count = ?,
                reference_count = ?,
                influential_citation_count = ?,
                venue = ?,
                year = ?,
                tldr = ?,
                s2_fields_of_study = ?,
                open_access_pdf_url = ?,
                s2_matched_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE doi = ?
        """, (
            metadata.get('s2_paper_id'),
            metadata.get('doi'),
            metadata.get('citation_count', 0),
            metadata.get('reference_count', 0),
            metadata.get('influential_citation_count', 0),
            metadata.get('venue'),
            metadata.get('year'),
            metadata.get('tldr'),
            metadata.get('s2_fields_of_study'),
            metadata.get('open_access_pdf_url'),
            metadata.get('s2_matched_at'),
            doi
        ))

    # ========== 上下文管理器 ==========

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
