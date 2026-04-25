# backend/services/concept_translation.py
"""概念翻译服务 — 当概念缺少 text_en 时自动翻译补全"""

import logging

from mkg.database import Database
from mkg.llm import extract_text_content, get_llm_or_raise
from mkg.resilience import RetryableExternalError, call_with_retries

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
        
        def _invoke():
            try:
                return llm.invoke(prompt)
            except Exception as exc:
                error_text = str(exc).lower()
                if any(token in error_text for token in ("timeout", "timed out", "rate limit", "429", "503")):
                    raise RetryableExternalError(str(exc)) from exc
                raise

        response = call_with_retries(
            "concept_translation.invoke",
            _invoke,
            logger=logger,
            retries=2,
            retry_delay=1.0,
        )
        content = extract_text_content(response.content if hasattr(response, "content") else response)
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
