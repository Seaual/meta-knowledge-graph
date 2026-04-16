# backend/services/concept_translation.py
"""概念翻译服务 — 当概念缺少 text_en 时自动翻译补全"""

import logging

from mkg.database import Database
from mkg.llm import get_llm_or_raise

logger = logging.getLogger(__name__)


def translate_concept_if_needed(concept: dict, db: Database) -> str:
    """如果概念缺少英文名，自动翻译为适合学术搜索的英文关键词并保存"""
    if concept.get("text_en"):
        return concept["text_en"]

    try:
        llm = get_llm_or_raise()
        prompt = (
            f"Translate this Chinese academic concept to English search keywords for Semantic Scholar.\n"
            f"Return only the English keywords, nothing else.\n\n"
            f"Concept: {concept['text']}"
        )
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict):
                    # Only extract text content, ignore thinking/thinking blocks
                    if item.get('type') == 'text':
                        parts.append(item.get('text', ''))
                    elif 'text' in item:
                        parts.append(item['text'])
                else:
                    parts.append(str(item))
            content = '\n'.join(parts)
        en_name = content.strip()

        # 保存到数据库
        cursor = db.conn.cursor()
        cursor.execute(
            "UPDATE concepts SET text_en = ? WHERE id = ?",
            (en_name, concept["id"])
        )
        db.conn.commit()

        return en_name
    except Exception as e:
        logger.warning(f"Failed to translate concept '{concept.get('text', '')}': {e}")
        return concept.get("text", "")
