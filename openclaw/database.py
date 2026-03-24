"""
SQLite 数据库管理 - 论文、概念、动态层级关系存储

新设计：
- concepts 表：存储概念（原 keywords），移除固定 level 字段
- concept_relations 表：存储父子概念关系（动态层级）
- paper_concepts 表：论文 - 概念多对多关联
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict


class Database:
    """SQLite 数据库管理类"""

    def __init__(self, db_path: str = "openclaw.db"):
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """连接到数据库"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

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
                    pdf_path = ?, published_date = ?, updated_at = CURRENT_TIMESTAMP
                WHERE doi = ?
            """, (
                paper_data.get('title'),
                paper_data.get('abstract'),
                json.dumps(paper_data.get('authors', [])),
                json.dumps(paper_data.get('keywords', [])),
                json.dumps(paper_data.get('contributions', [])),
                paper_data.get('pdf_path'),
                paper_data.get('published'),
                paper_data.get('doi')
            ))
            doi = existing['doi']
        else:
            # 插入
            doi = paper_data.get('doi', paper_data.get('arxiv_id'))
            cursor.execute("""
                INSERT INTO papers (doi, arxiv_id, title, abstract, authors, keywords, contributions, pdf_path, published_date, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (
                doi,
                paper_data.get('arxiv_id'),
                paper_data.get('title'),
                paper_data.get('abstract'),
                json.dumps(paper_data.get('authors', [])),
                json.dumps(paper_data.get('keywords', [])),
                json.dumps(paper_data.get('contributions', [])),
                paper_data.get('pdf_path'),
                paper_data.get('published')
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
        """获取论文（支持 DOI 或 arXiv ID）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM papers WHERE doi = ? OR arxiv_id = ?
        """, (identifier, identifier))
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
        return papers

    def update_paper_metadata(self, doi: str, metadata: dict):
        """更新论文元数据（作者、摘要、关键词、创新点等）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE papers SET
                title = COALESCE(?, title),
                abstract = COALESCE(?, abstract),
                authors = COALESCE(?, authors),
                keywords = COALESCE(?, keywords),
                contributions = COALESCE(?, contributions),
                updated_at = CURRENT_TIMESTAMP
            WHERE doi = ?
        """, (
            metadata.get('title'),
            metadata.get('abstract'),
            json.dumps(metadata['authors']) if metadata.get('authors') else None,
            json.dumps(metadata['keywords']) if metadata.get('keywords') else None,
            json.dumps(metadata['contributions']) if metadata.get('contributions') else None,
            doi
        ))
        self.conn.commit()

    # ========== 概念操作方法 ==========

    def add_concept(self, concept_data: dict) -> str:
        """添加概念（如果不存在）"""
        cursor = self.conn.cursor()
        concept_id = concept_data['id']

        # 只在概念不存在时插入，不更新 paper_count
        cursor.execute("""
            INSERT OR IGNORE INTO concepts (id, text, category, paper_count, updated_at)
            VALUES (?, ?, ?, 0, CURRENT_TIMESTAMP)
        """, (
            concept_id,
            concept_data['text'],
            concept_data.get('category'),
        ))

        self.conn.commit()
        return concept_id

    def add_paper_concept(self, paper_doi: str, concept_id: str,
                          confidence: float = 1.0, source: str = 'llm'):
        """添加论文 - 概念关联（支持多归属）"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO paper_concepts (paper_doi, concept_id, confidence, source)
            VALUES (?, ?, ?, ?)
        """, (paper_doi, concept_id, confidence, source))

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
            concept_tree: LLM 返回的概念树结构
                {
                    "concept": "人工智能",
                    "category": "field",
                    "children": [
                        {
                            "concept": "机器学习",
                            "category": "field",
                            "children": [...]
                        }
                    ]
                }
        """
        # 递归插入概念树
        def insert_concept(node: dict, parent_id: str = None) -> str:
            # 创建或获取概念
            concept_id = node.get('id', self._to_slug(node['concept']))

            concept_data = {
                'id': concept_id,
                'text': node['concept'],
                'category': node.get('category', 'method')
            }
            self.add_concept(concept_data)

            # 关联论文
            self.add_paper_concept(paper_doi, concept_id, node.get('confidence', 1.0))

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

    # ========== 上下文管理器 ==========

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
