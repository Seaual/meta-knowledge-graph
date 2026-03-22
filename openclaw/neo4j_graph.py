"""
Neo4j 知识图谱操作模块

使用 Neo4j 存储论文和关键词的层级关系
支持混合存储模式 (SQLite + Neo4j)
"""

import os
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class KeywordNode:
    """关键词节点"""
    id: str
    text: str
    level: int
    category: str
    paper_count: int = 0


@dataclass
class PaperNode:
    """论文节点"""
    doi: str
    arxiv_id: str = ""
    title: str = ""
    abstract: str = ""
    authors: List[str] = None
    published_date: str = ""
    pdf_path: str = ""
    status: str = "pending"

    def __post_init__(self):
        if self.authors is None:
            self.authors = []


class Neo4jGraph:
    """Neo4j 知识图谱操作类"""

    def __init__(self, uri: str = None, user: str = None, password: str = None):
        """
        初始化 Neo4j 连接

        Args:
            uri: Neo4j URI (如：bolt://localhost:7687)
            user: 用户名
            password: 密码

        如果未提供参数，会从环境变量读取:
        - NEO4J_URI
        - NEO4J_USER
        - NEO4J_PASSWORD
        """
        self.driver = None
        self.connected = False

        # 从环境变量读取配置
        if uri is None:
            uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        if user is None:
            user = os.getenv("NEO4J_USER", "neo4j")
        if password is None:
            password = os.getenv("NEO4J_PASSWORD", "password")

        try:
            from neo4j import GraphDatabase, exceptions

            self.driver = GraphDatabase.driver(uri, auth=(user, password))

            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")

            self.connected = True
            self._init_schema()
            print("[OK] Neo4j 连接成功")
        except ImportError:
            print("[WARN] neo4j 库未安装，请运行：pip install neo4j")
        except Exception as e:
            print(f"[WARN] Neo4j 连接失败：{e}")
            print("       请确保 Neo4j 已启动或使用 SQLite 版本")

    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            self.connected = False

    def _init_schema(self):
        """初始化图谱 schema（创建索引和约束）"""
        with self.driver.session() as session:
            # 创建关键词 ID 索引
            session.run("CREATE INDEX IF NOT EXISTS FOR (k:Keyword) ON (k.id)")
            # 创建论文 DOI 索引
            session.run("CREATE INDEX IF NOT EXISTS FOR (p:Paper) ON (p.doi)")
            # 创建 arXiv ID 索引
            session.run("CREATE INDEX IF NOT EXISTS FOR (p:Paper) ON (p.arxiv_id)")
            # 创建关键词层级索引
            session.run("CREATE INDEX IF NOT EXISTS FOR (k:Keyword) ON (k.level)")
            # 创建关键词文本索引
            session.run("CREATE INDEX IF NOT EXISTS FOR (k:Keyword) ON (k.text)")

            # 创建唯一约束
            try:
                session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (k:Keyword) REQUIRE k.id IS UNIQUE")
            except Exception:
                pass  # 约束可能已存在

            try:
                session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Paper) REQUIRE p.doi IS UNIQUE")
            except Exception:
                pass

    # ==================== 论文操作 ====================

    def add_paper(self, paper: PaperNode) -> bool:
        """添加论文节点"""
        with self.driver.session() as session:
            session.run("""
                MERGE (p:Paper {doi: $doi})
                SET p.arxiv_id = $arxiv_id,
                    p.title = $title,
                    p.abstract = $abstract,
                    p.authors = $authors,
                    p.published_date = $published_date,
                    p.pdf_path = $pdf_path,
                    p.status = $status,
                    p.updated_at = datetime()
            """, {
                'doi': paper.doi,
                'arxiv_id': paper.arxiv_id,
                'title': paper.title,
                'abstract': paper.abstract,
                'authors': json.dumps(paper.authors),
                'published_date': paper.published_date,
                'pdf_path': paper.pdf_path,
                'status': paper.status
            })
        return True

    def get_paper(self, doi: str) -> Optional[Dict]:
        """获取论文"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Paper {doi: $doi})
                RETURN p
            """, {'doi': doi})
            record = result.single()
            if record:
                data = dict(record['p'])
                # 解析 JSON 字段
                if 'authors' in data and data['authors']:
                    try:
                        data['authors'] = json.loads(data['authors'])
                    except:
                        pass
                return data
            return None

    def get_paper_by_arxiv_id(self, arxiv_id: str) -> Optional[Dict]:
        """通过 arXiv ID 获取论文"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Paper {arxiv_id: $arxiv_id})
                RETURN p
            """, {'arxiv_id': arxiv_id})
            record = result.single()
            if record:
                data = dict(record['p'])
                if 'authors' in data and data['authors']:
                    try:
                        data['authors'] = json.loads(data['authors'])
                    except:
                        pass
                return data
            return None

    def update_paper_status(self, doi: str, status: str, error_message: str = None):
        """更新论文处理状态"""
        with self.driver.session() as session:
            session.run("""
                MATCH (p:Paper {doi: $doi})
                SET p.status = $status,
                    p.error_message = $error_message,
                    p.updated_at = datetime()
            """, {'doi': doi, 'status': status, 'error_message': error_message})

    def get_papers_by_status(self, status: str) -> List[Dict]:
        """按状态获取论文列表"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Paper {status: $status})
                RETURN p ORDER BY p.updated_at DESC
            """, {'status': status})
            papers = []
            for record in result:
                data = dict(record['p'])
                if 'authors' in data and data['authors']:
                    try:
                        data['authors'] = json.loads(data['authors'])
                    except:
                        pass
                papers.append(data)
            return papers

    def get_all_papers(self, limit: int = 100) -> List[Dict]:
        """获取所有论文"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Paper)
                RETURN p ORDER BY p.updated_at DESC LIMIT $limit
            """, {'limit': limit})
            papers = []
            for record in result:
                data = dict(record['p'])
                if 'authors' in data and data['authors']:
                    try:
                        data['authors'] = json.loads(data['authors'])
                    except:
                        pass
                papers.append(data)
            return papers

    # ==================== 关键词操作 ====================

    def add_keyword(self, keyword: KeywordNode) -> bool:
        """添加关键词节点"""
        with self.driver.session() as session:
            session.run("""
                MERGE (k:Keyword {id: $id})
                SET k.text = $text,
                    k.level = $level,
                    k.category = $category,
                    k.paper_count = COALESCE(k.paper_count, 0) + 1,
                    k.updated_at = datetime()
            """, {
                'id': keyword.id,
                'text': keyword.text,
                'level': keyword.level,
                'category': keyword.category
            })
        return True

    def get_keyword(self, keyword_id: str) -> Optional[Dict]:
        """获取关键词"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (k:Keyword {id: $id})
                RETURN k
            """, {'id': keyword_id})
            record = result.single()
            if record:
                return dict(record['k'])
            return None

    def get_keywords_by_level(self, level: int) -> List[Dict]:
        """按层级获取关键词"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (k:Keyword {level: $level})
                OPTIONAL MATCH (p:Paper)-[:HAS_KEYWORD]->(k)
                WITH k, count(p) as paper_count
                RETURN k ORDER BY paper_count DESC
            """, {'level': level})
            return [dict(record['k']) for record in result]

    def get_all_keywords(self) -> List[Dict]:
        """获取所有关键词"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (k:Keyword)
                RETURN k ORDER BY k.level, k.paper_count DESC
            """)
            return [dict(record['k']) for record in result]

    # ==================== 关系操作 ====================

    def add_paper_keyword(self, doi: str, keyword_id: str, confidence: float = 1.0, source: str = 'author'):
        """添加论文 - 关键词关系"""
        with self.driver.session() as session:
            session.run("""
                MATCH (p:Paper {doi: $doi})
                MATCH (k:Keyword {id: $keyword_id})
                MERGE (p)-[r:HAS_KEYWORD]->(k)
                SET r.confidence = $confidence,
                    r.source = $source
            """, {'doi': doi, 'keyword_id': keyword_id, 'confidence': confidence, 'source': source})

    def add_keyword_relation(self, parent_id: str, child_id: str, relation_type: str = 'HAS_SUBKEYWORD'):
        """添加关键词层级关系"""
        with self.driver.session() as session:
            session.run("""
                MATCH (parent:Keyword {id: $parent_id})
                MATCH (child:Keyword {id: $child_id})
                MERGE (parent)-[r:HAS_SUBKEYWORD]->(child)
            """, {'parent_id': parent_id, 'child_id': child_id})

    def get_keyword_children(self, keyword_id: str) -> List[Dict]:
        """获取关键词的子节点"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (parent:Keyword {id: $id})-[:HAS_SUBKEYWORD]->(child:Keyword)
                RETURN child ORDER BY child.paper_count DESC
            """, {'id': keyword_id})
            return [dict(record['child']) for record in result]

    def get_keyword_parents(self, keyword_id: str) -> List[Dict]:
        """获取关键词的父节点"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (child:Keyword {id: $id})<-[:HAS_SUBKEYWORD]-(parent:Keyword)
                RETURN parent
            """, {'id': keyword_id})
            return [dict(record['parent']) for record in result]

    def get_papers_by_keyword(self, keyword_id: str, limit: int = 50) -> List[Dict]:
        """获取关键词关联的论文"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Paper)-[:HAS_KEYWORD]->(k:Keyword {id: $id})
                RETURN p ORDER BY p.published_date DESC LIMIT $limit
            """, {'id': keyword_id, 'limit': limit})
            papers = []
            for record in result:
                data = dict(record['p'])
                if 'authors' in data and data['authors']:
                    try:
                        data['authors'] = json.loads(data['authors'])
                    except:
                        pass
                papers.append(data)
            return papers

    # ==================== 图谱查询 ====================

    def get_tree(self, root_id: str = None, max_depth: int = 5) -> Dict:
        """获取树状结构"""
        with self.driver.session() as session:
            # 如果没有指定根节点，从 L0 开始
            if root_id is None:
                result = session.run("""
                    MATCH (k:Keyword)
                    WHERE k.level = 0
                    RETURN k ORDER BY k.paper_count DESC LIMIT 1
                """)
                record = result.single()
                if record:
                    root_id = dict(record['k'])['id']
                else:
                    return {}

            return self._build_tree(session, root_id, 0, max_depth)

    def _build_tree(self, session, keyword_id: str, depth: int, max_depth: int) -> Dict:
        """递归构建树"""
        if depth > max_depth:
            return {'id': keyword_id, 'more': True}

        # 获取当前节点
        result = session.run("""
            MATCH (k:Keyword {id: $id})
            RETURN k
        """, {'id': keyword_id})
        record = result.single()
        if not record:
            return {}

        node = dict(record['k'])

        # 获取子节点
        children_result = session.run("""
            MATCH (parent:Keyword {id: $id})-[:HAS_SUBKEYWORD]->(child:Keyword)
            RETURN child.id, child.text, child.level, child.paper_count
            ORDER BY child.paper_count DESC
        """, {'id': keyword_id})

        node['children'] = []
        for child in children_result:
            child_dict = dict(child)
            child_node = self._build_tree(session, child_dict['child.id'], depth + 1, max_depth)
            node['children'].append(child_node)

        # 获取关联论文
        papers_result = session.run("""
            MATCH (p:Paper)-[:HAS_KEYWORD]->(k:Keyword {id: $id})
            RETURN p.doi, p.title LIMIT 10
        """, {'id': keyword_id})

        node['papers'] = [{'doi': r['p.doi'], 'title': r['p.title']} for r in papers_result]

        return node

    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self.driver.session() as session:
            # 关键词统计
            result = session.run("""
                MATCH (k:Keyword)
                RETURN k.level AS level, count(*) AS count
                ORDER BY level
            """)
            keywords_by_level = {r['level']: r['count'] for r in result}

            result = session.run("MATCH (k:Keyword) RETURN count(*) AS count")
            total_keywords = result.single()['count']

            # 论文统计
            result = session.run("MATCH (p:Paper) RETURN count(*) AS count")
            total_papers = result.single()['count']

            # 关系统计
            result = session.run("MATCH ()-[r:HAS_SUBKEYWORD]->() RETURN count(r) AS count")
            total_relations = result.single()['count']

            return {
                'papers': {'total': total_papers},
                'keywords': {'total': total_keywords},
                'keywords_by_level': keywords_by_level,
                'relations': total_relations
            }

    def find_gaps(self) -> List[Dict]:
        """找出研究空白（子节点少的方向）"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (k:Keyword)
                WHERE k.level <= 2
                OPTIONAL MATCH (k)-[:HAS_SUBKEYWORD]->(child:Keyword)
                WITH k, count(child) AS child_count
                WHERE child_count <= 1
                RETURN k.id, k.text, k.level, k.paper_count, child_count
                ORDER BY k.paper_count DESC
                LIMIT 20
            """)
            return [dict(r) for r in result]

    def find_connections(self) -> List[Dict]:
        """找出潜在关联（共现关键词对）"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Paper)-[:HAS_KEYWORD]->(k1:Keyword)
                MATCH (p)-[:HAS_KEYWORD]->(k2:Keyword)
                WHERE k1.id < k2.id
                WITH k1, k2, count(p) AS cooccurrence
                WHERE cooccurrence >= 2
                RETURN k1.text AS keyword1, k2.text AS keyword2, cooccurrence
                ORDER BY cooccurrence DESC
                LIMIT 20
            """)
            return [dict(r) for r in result]

    def search_keywords(self, query: str, limit: int = 20) -> List[Dict]:
        """搜索关键词"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (k:Keyword)
                WHERE k.text CONTAINS $query OR toLower(k.text) CONTAINS toLower($query)
                RETURN k ORDER BY k.paper_count DESC LIMIT $limit
            """, {'query': query, 'limit': limit})
            return [dict(record['k']) for record in result]

    def search_papers(self, query: str, limit: int = 20) -> List[Dict]:
        """搜索论文"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p:Paper)
                WHERE p.title CONTAINS $query OR p.abstract CONTAINS $query
                RETURN p ORDER BY p.published_date DESC LIMIT $limit
            """, {'query': query, 'limit': limit})
            papers = []
            for record in result:
                data = dict(record['p'])
                if 'authors' in data and data['authors']:
                    try:
                        data['authors'] = json.loads(data['authors'])
                    except:
                        pass
                papers.append(data)
            return papers

    def clear_all(self):
        """清空图谱（慎用）"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connected and self.driver is not None
