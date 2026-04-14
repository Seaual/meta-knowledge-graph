# backend/services/localization.py
"""概念本地化工具 — 根据用户语言返回对应的概念名"""


def localize_concept(concept: dict, lang: str) -> dict:
    """根据语言返回对应的概念名"""
    if not concept:
        return concept
    if lang == "en" and concept.get("text_en"):
        return {**concept, "text": concept["text_en"]}
    return concept


def localize_concept_list(concepts: list[dict], lang: str) -> list[dict]:
    """批量本地化概念列表"""
    return [localize_concept(c, lang) for c in concepts]
