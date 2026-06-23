# mkg/database/schema.py
"""Database schema - table definitions"""

import sqlite3


class SchemaMixin:
    """Schema management mixin"""


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

        # 对话历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,  -- UUID
                device_id TEXT NOT NULL,  -- 设备标识
                title TEXT,  -- AI 生成的标题
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 对话消息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_messages (
                id TEXT PRIMARY KEY,  -- UUID
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,  -- 'user' | 'assistant'
                content TEXT NOT NULL,
                agent TEXT,  -- optional, for assistant messages
                attachments TEXT,  -- JSON format
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)

        # 创建索引加速查询
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_device
            ON conversations(device_id, updated_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
            ON conversation_messages(conversation_id, created_at)
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
        except sqlite3.OperationalError:
            pass  # 字段已存在
        try:
            cursor.execute("ALTER TABLE paper_citations ADD COLUMN citing_year INTEGER")
        except sqlite3.OperationalError:
            pass  # 字段已存在

        # 迁移：添加 text_en 字段到 concepts 表（英文概念名）
        try:
            cursor.execute("ALTER TABLE concepts ADD COLUMN text_en TEXT")
        except sqlite3.OperationalError:
            pass  # 字段已存在

        # 迁移：添加 text_zh 字段到 concepts 表（中文概念名）
        try:
            cursor.execute("ALTER TABLE concepts ADD COLUMN text_zh TEXT")
        except sqlite3.OperationalError:
            pass  # 字段已存在

        # Research sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_sessions (
                id TEXT PRIMARY KEY,
                user_query TEXT NOT NULL,
                target_type TEXT,
                target_id TEXT,
                status TEXT DEFAULT 'running',
                dimensions TEXT,
                progress INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                report_path TEXT
            )
        """)

        # Research findings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                dimension TEXT,
                finding TEXT,
                sources TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES research_sessions(id)
            )
        """)

        # Agent context table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                context_json TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 迁移：为 research_sessions 添加缺失字段
        try:
            cursor.execute("ALTER TABLE research_sessions ADD COLUMN target_name TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE research_sessions ADD COLUMN query TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE research_sessions ADD COLUMN completed_dimensions TEXT DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE research_sessions ADD COLUMN report TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE research_sessions ADD COLUMN updated_at TIMESTAMP")
        except sqlite3.OperationalError:
            pass

        # 迁移：为 research_findings 添加缺失字段
        try:
            cursor.execute("ALTER TABLE research_findings ADD COLUMN finding_type TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE research_findings ADD COLUMN content TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE research_findings ADD COLUMN confidence REAL")
        except sqlite3.OperationalError:
            pass

        # 用户偏好表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 对话上下文表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_context (
                id TEXT PRIMARY KEY,
                conv_id TEXT NOT NULL,
                summary TEXT,
                key_concepts TEXT,
                research_interests TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conv_id) REFERENCES conversations(id)
            )
        """)

        # 研究记忆表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS research_memories (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT,
                memory_type TEXT NOT NULL,
                tags TEXT,
                concept_ids TEXT,
                paper_doi TEXT,
                source_section TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON research_memories(memory_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_paper_doi ON research_memories(paper_doi)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_concept_ids ON research_memories(concept_ids)")

        self.conn.commit()
