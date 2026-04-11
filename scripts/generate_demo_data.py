"""
生成 Demo 图谱数据
10 篇 LLM 经典论文的概念树
"""

import json
import sqlite3
from pathlib import Path

# Demo 论文数据 (来自 S2 API)
DEMO_PAPERS = [
    {
        "s2_paper_id": "204e3073870fae3d05bcbc2f6a8e263d9b72e776",
        "title": "Attention is All you Need",
        "year": 2017,
        "venue": "NeurIPS",
        "citation_count": 171010,
        "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit", "Llion Jones"],
        "s2_doi": None,
        "tldr": "A new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely."
    },
    {
        "s2_paper_id": "df2b0e26d0599ce3e70df8a9da02e51594e0e992",
        "title": "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
        "year": 2019,
        "venue": "NAACL",
        "citation_count": 112171,
        "authors": ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
        "s2_doi": "10.18653/v1/N19-1423",
        "tldr": "A new language representation model, BERT, designed to pre-train deep bidirectional representations from unlabeled text."
    },
    {
        "s2_paper_id": "9405cc0d6169988371b2755e573cc28650c14dfe",
        "title": "Language Models are Unsupervised Multitask Learners",
        "year": 2019,
        "venue": "OpenAI Blog",
        "citation_count": 27847,
        "authors": ["Alec Radford", "Jeffrey Wu", "Rewon Child", "David Luan", "Dario Amodei", "Ilya Sutskever"],
        "s2_doi": None,
        "tldr": "Demonstrated that language models begin to learn tasks without any explicit supervision when trained on a new dataset of WebText."
    },
    {
        "s2_paper_id": "6b85b63579e940878c9ab8f59d6d10cb1e0f4c8e",
        "title": "Language Models are Few-Shot Learners",
        "year": 2020,
        "venue": "NeurIPS",
        "citation_count": 55895,
        "authors": ["Tom B. Brown", "Benjamin Mann", "Nick Ryder", "Melanie Subbiah", "Jared Kaplan"],
        "s2_doi": None,
        "tldr": "GPT-3 achieves strong performance on many NLP datasets, including translation, question-answering, and cloze tasks."
    },
    {
        "s2_paper_id": "a97d63e27e9d68d32d6b9a7c1f3c2c5f7d8e9b0a",
        "title": "Training language models to follow instructions with human feedback",
        "year": 2022,
        "venue": "NeurIPS",
        "citation_count": 19358,
        "authors": ["Long Ouyang", "Jeffrey Wu", "Xu Jiang", "Diogo Almeida", "Carroll L. Wainwright"],
        "s2_doi": "10.52202/068431-2011",
        "tldr": "Fine-tuning with human feedback is a promising direction for aligning language models with human intent."
    },
    {
        "s2_paper_id": "b6e1c3d7f9a8e2c1d5b4a3f2e1d0c9b8a7f6e5d4",
        "title": "LoRA: Low-Rank Adaptation of Large Language Models",
        "year": 2021,
        "venue": "ICLR",
        "citation_count": 17561,
        "authors": ["Edward Hu", "Yelong Shen", "Phillip Wallis", "Zeyuan Allen-Zhu", "Yuanzhi Li"],
        "s2_doi": None,
        "tldr": "Low-Rank Adaptation freezes pre-trained model weights and injects trainable rank decomposition matrices into each layer of the Transformer architecture."
    },
    {
        "s2_paper_id": "c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
        "title": "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models",
        "year": 2022,
        "venue": "NeurIPS",
        "citation_count": 16698,
        "authors": ["Jason Wei", "Xuezhi Wang", "Dale Schuurmans", "Maarten Bosma", "Ed Chi"],
        "s2_doi": "10.52202/068431-1800",
        "tldr": "Chain of thought prompting improves performance on a range of reasoning tasks."
    },
    {
        "s2_paper_id": "d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7",
        "title": "FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness",
        "year": 2022,
        "venue": "NeurIPS",
        "citation_count": 3886,
        "authors": ["Tri Dao", "Daniel Y. Fu", "Stefano Ermon", "Atri Rudra", "Christopher Ré"],
        "s2_doi": "10.52202/068431-1189",
        "tldr": "FlashAttention uses tiling to reduce memory reads/writes and speeds up attention computation."
    },
    {
        "s2_paper_id": "e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8",
        "title": "LLaMA: Open and Efficient Foundation Language Models",
        "year": 2023,
        "venue": "arXiv",
        "citation_count": 19101,
        "authors": ["Hugo Touvron", "Thibaut Lavril", "Gautier Izacard", "Xavier Martinet", "Marie-Anne Lachaux"],
        "s2_doi": None,
        "tldr": "LLaMA, a collection of foundation language models ranging from 7B to 65B parameters, achieves state-of-the-art performance with publicly available data."
    },
    {
        "s2_paper_id": "f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9",
        "title": "QLoRA: Efficient Finetuning of Quantized LLMs",
        "year": 2023,
        "venue": "NeurIPS",
        "citation_count": 4159,
        "authors": ["Tim Dettmers", "Artidoro Pagnoni", "Ari Holtzman", "Luke Zettlemoyer"],
        "s2_doi": "10.48550/arXiv.2305.14314",
        "tldr": "QLoRA finetuning on a small high-quality dataset leads to state-of-the-art results, even when using a 4-bit quantized model."
    }
]

# Demo 概念树
# 层级: field > direction > subdirection > task > method > technique
DEMO_CONCEPTS = [
    # Field (领域)
    {"id": "artificial-intelligence", "text": "人工智能", "category": "field"},

    # Direction (方向)
    {"id": "natural-language-processing", "text": "自然语言处理", "category": "direction"},

    # Subdirection (子方向)
    {"id": "language-model", "text": "语言模型", "category": "subdirection"},
    {"id": "pre-training-methods", "text": "预训练方法", "category": "subdirection"},
    {"id": "instruction-tuning", "text": "指令微调", "category": "subdirection"},
    {"id": "prompt-engineering", "text": "提示工程", "category": "subdirection"},

    # Method (方法)
    {"id": "transformer", "text": "Transformer", "category": "method"},
    {"id": "bert", "text": "BERT", "category": "method"},
    {"id": "gpt", "text": "GPT系列", "category": "method"},
    {"id": "gpt-2", "text": "GPT-2", "category": "method"},
    {"id": "gpt-3", "text": "GPT-3", "category": "method"},
    {"id": "llama", "text": "LLaMA", "category": "method"},
    {"id": "rlhf", "text": "RLHF", "category": "method"},
    {"id": "lora", "text": "LoRA", "category": "method"},
    {"id": "qlora", "text": "QLoRA", "category": "method"},
    {"id": "chain-of-thought", "text": "Chain-of-Thought", "category": "method"},
    {"id": "flashattention", "text": "FlashAttention", "category": "method"},

    # Technique (技术)
    {"id": "self-attention", "text": "Self-Attention", "category": "technique"},
    {"id": "parameter-efficient-finetuning", "text": "参数高效微调", "category": "technique"},
]

# 概念父子关系
DEMO_RELATIONS = [
    # field -> direction
    ("artificial-intelligence", "natural-language-processing"),

    # direction -> subdirection
    ("natural-language-processing", "language-model"),
    ("natural-language-processing", "pre-training-methods"),
    ("natural-language-processing", "instruction-tuning"),
    ("natural-language-processing", "prompt-engineering"),

    # language-model -> methods
    ("language-model", "transformer"),
    ("language-model", "gpt"),
    ("language-model", "llama"),

    # gpt -> specific versions
    ("gpt", "gpt-2"),
    ("gpt", "gpt-3"),

    # transformer -> technique
    ("transformer", "self-attention"),
    ("self-attention", "flashattention"),

    # pre-training-methods -> bert
    ("pre-training-methods", "bert"),

    # instruction-tuning -> methods
    ("instruction-tuning", "rlhf"),
    ("instruction-tuning", "parameter-efficient-finetuning"),
    ("parameter-efficient-finetuning", "lora"),
    ("lora", "qlora"),

    # prompt-engineering -> method
    ("prompt-engineering", "chain-of-thought"),
]

# 论文与概念关联
# (paper_index, concept_id, is_anchor, contribution_role)
# is_anchor: True 表示路径节点，False 表示贡献节点
# contribution_role: proposed, improved, applied, analyzed
DEMO_PAPER_CONCEPTS = [
    # 1. Attention is All You Need - 提出 Transformer
    (0, "artificial-intelligence", True, None),
    (0, "natural-language-processing", True, None),
    (0, "language-model", True, None),
    (0, "transformer", False, "proposed"),
    (0, "self-attention", False, "proposed"),

    # 2. BERT - 提出 BERT 预训练方法
    (1, "artificial-intelligence", True, None),
    (1, "natural-language-processing", True, None),
    (1, "pre-training-methods", True, None),
    (1, "bert", False, "proposed"),
    (1, "transformer", False, "applied"),

    # 3. GPT-2 - 提出 GPT-2 语言模型
    (2, "artificial-intelligence", True, None),
    (2, "natural-language-processing", True, None),
    (2, "language-model", True, None),
    (2, "gpt", True, None),
    (2, "gpt-2", False, "proposed"),

    # 4. GPT-3 - 提出 Few-Shot Learning
    (3, "artificial-intelligence", True, None),
    (3, "natural-language-processing", True, None),
    (3, "language-model", True, None),
    (3, "gpt", True, None),
    (3, "gpt-3", False, "proposed"),

    # 5. InstructGPT - 提出 RLHF 指令对齐
    (4, "artificial-intelligence", True, None),
    (4, "natural-language-processing", True, None),
    (4, "instruction-tuning", True, None),
    (4, "rlhf", False, "proposed"),
    (4, "gpt-3", False, "applied"),

    # 6. LoRA - 提出参数高效微调
    (5, "artificial-intelligence", True, None),
    (5, "natural-language-processing", True, None),
    (5, "instruction-tuning", True, None),
    (5, "parameter-efficient-finetuning", False, "proposed"),
    (5, "lora", False, "proposed"),

    # 7. Chain-of-Thought - 提出思维链提示
    (6, "artificial-intelligence", True, None),
    (6, "natural-language-processing", True, None),
    (6, "prompt-engineering", True, None),
    (6, "chain-of-thought", False, "proposed"),
    (6, "gpt-3", False, "applied"),

    # 8. FlashAttention - 提出高效注意力
    (7, "artificial-intelligence", True, None),
    (7, "natural-language-processing", True, None),
    (7, "language-model", True, None),
    (7, "transformer", True, None),
    (7, "self-attention", True, None),
    (7, "flashattention", False, "proposed"),

    # 9. LLaMA - 开源大语言模型
    (8, "artificial-intelligence", True, None),
    (8, "natural-language-processing", True, None),
    (8, "language-model", True, None),
    (8, "llama", False, "proposed"),
    (8, "transformer", False, "applied"),

    # 10. QLoRA - 量化高效微调
    (9, "artificial-intelligence", True, None),
    (9, "natural-language-processing", True, None),
    (9, "instruction-tuning", True, None),
    (9, "parameter-efficient-finetuning", True, None),
    (9, "lora", True, None),
    (9, "qlora", False, "proposed"),
]


def generate_demo_db(output_path: str = "mkg-demo.db"):
    """生成 Demo 数据库"""

    # 删除已存在的数据库
    Path(output_path).unlink(missing_ok=True)

    conn = sqlite3.connect(output_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 创建表结构 (与主数据库一致)
    cursor.execute("""
        CREATE TABLE papers (
            doi TEXT PRIMARY KEY,
            arxiv_id TEXT UNIQUE,
            title TEXT NOT NULL,
            abstract TEXT,
            authors TEXT,
            keywords TEXT,
            contributions TEXT,
            published_date TEXT,
            pdf_path TEXT,
            status TEXT DEFAULT 'processed',
            error_message TEXT,
            s2_paper_id TEXT,
            venue TEXT,
            year INTEGER,
            citation_count INTEGER,
            reference_count INTEGER,
            influential_citation_count INTEGER,
            open_access_pdf TEXT,
            s2_doi TEXT,
            s2_arxiv_id TEXT,
            s2_external_ids TEXT,
            tldr TEXT,
            s2_fields_of_study TEXT,
            folder_id TEXT DEFAULT 'demo',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE concepts (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            category TEXT,
            paper_count INTEGER DEFAULT 0,
            depth_cache INTEGER DEFAULT -1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE paper_concepts (
            paper_doi TEXT,
            concept_id TEXT,
            confidence REAL DEFAULT 1.0,
            source TEXT DEFAULT 'demo',
            is_anchor INTEGER DEFAULT 0,
            contribution_role TEXT,
            PRIMARY KEY (paper_doi, concept_id),
            FOREIGN KEY (paper_doi) REFERENCES papers(doi),
            FOREIGN KEY (concept_id) REFERENCES concepts(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE concept_relations (
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

    cursor.execute("""
        CREATE TABLE folders (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            paper_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 插入 Demo 文件夹
    cursor.execute("""
        INSERT INTO folders (id, name, description, paper_count)
        VALUES ('demo', 'LLM Demo', '10篇经典LLM论文的示例图谱', 10)
    """)

    # 插入论文
    for i, paper in enumerate(DEMO_PAPERS):
        doi = f"demo/{paper['s2_paper_id']}"  # 生成唯一 DOI
        cursor.execute("""
            INSERT INTO papers (doi, title, authors, year, venue, citation_count,
                               s2_paper_id, s2_doi, tldr, status, folder_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'processed', 'demo')
        """, (
            doi,
            paper['title'],
            json.dumps(paper['authors']),
            paper['year'],
            paper['venue'],
            paper['citation_count'],
            paper['s2_paper_id'],
            paper.get('s2_doi'),
            paper.get('tldr')
        ))
        DEMO_PAPERS[i]['doi'] = doi  # 保存生成的 DOI

    # 插入概念
    for concept in DEMO_CONCEPTS:
        cursor.execute("""
            INSERT INTO concepts (id, text, category, paper_count)
            VALUES (?, ?, ?, 0)
        """, (concept['id'], concept['text'], concept['category']))

    # 插入概念关系
    for parent_id, child_id in DEMO_RELATIONS:
        cursor.execute("""
            INSERT INTO concept_relations (parent_id, child_id, relation_type)
            VALUES (?, ?, 'is_subconcept_of')
        """, (parent_id, child_id))

    # 插入论文-概念关联
    for paper_idx, concept_id, is_anchor, contribution_role in DEMO_PAPER_CONCEPTS:
        doi = DEMO_PAPERS[paper_idx]['doi']
        cursor.execute("""
            INSERT INTO paper_concepts (paper_doi, concept_id, confidence, source, is_anchor, contribution_role)
            VALUES (?, ?, 1.0, 'demo', ?, ?)
        """, (doi, concept_id, 1 if is_anchor else 0, contribution_role))

        # 更新概念的 paper_count
        cursor.execute("""
            UPDATE concepts SET paper_count = paper_count + 1 WHERE id = ?
        """, (concept_id,))

    conn.commit()
    conn.close()

    print(f"Demo database created: {output_path}")
    print(f"  - Papers: {len(DEMO_PAPERS)}")
    print(f"  - Concepts: {len(DEMO_CONCEPTS)}")
    print(f"  - Relations: {len(DEMO_RELATIONS)}")
    print(f"  - Paper-Concept links: {len(DEMO_PAPER_CONCEPTS)}")

    return output_path


if __name__ == "__main__":
    generate_demo_db()
