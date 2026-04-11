"""
候选对生成器 - 预筛选可能重复的概念对
"""

from collections.abc import Generator
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class ConceptPair:
    """概念对"""
    concept1: dict
    concept2: dict
    similarity: float


class CandidateGenerator:
    """候选对生成器"""

    SIMILARITY_THRESHOLD = 0.6
    CATEGORIES = ['field', 'direction', 'subdirection', 'task', 'method', 'technique', 'dataset', 'finding']
    HIGH_SIMILARITY_THRESHOLD = 0.9  # Above this, auto-merge without LLM

    @staticmethod
    def check_text_containment(text1: str, text2: str) -> tuple[bool, str]:
        """Check if one text contains another (absorption merge).

        Returns (should_auto_merge, target_text_to_keep)
        """
        t1, t2 = text1.lower().strip(), text2.lower().strip()

        # Complete containment - keep shorter text
        if t1 in t2 and len(t1) < len(t2):
            return True, text1
        if t2 in t1 and len(t2) < len(t1):
            return True, text2

        # Common suffix patterns (Chinese and English)
        suffixes = ['方法', '方法 ', ' method', ' methods', '技术', '技术 ', ' technique', ' techniques']
        for suffix in suffixes:
            if t1 + suffix == t2:
                return True, text1
            if t2 + suffix == t1:
                return True, text2

        return False, ""

    def __init__(self, db):
        self.db = db

    def text_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度（0-1）"""
        return SequenceMatcher(None, text1, text2).ratio()

    def generate_candidates(self, folder_id: str = None) -> list[ConceptPair]:
        """生成所有候选对，可选按文件夹过滤"""
        candidates = []
        for category in self.CATEGORIES:
            if folder_id and folder_id != 'default':
                concepts = self.db.get_concepts_by_category_and_folder(category, folder_id)
            else:
                concepts = self.db.get_concepts_by_category(category)
            candidates.extend(self._generate_pairs_in_category(concepts))
        return candidates

    def generate_candidates_with_prefilter(self, folder_id: str = None) -> dict:
        """Generate candidates with pre-filtering rules applied.

        Returns:
            {
                "candidates": [...],      # Need LLM analysis
                "high_confidence": [...], # Auto-merge suggestions (no LLM needed)
                "filtered": [...],        # Filtered out by rules
                "stats": {...}
            }
        """
        raw_candidates = self.generate_candidates(folder_id=folder_id)

        candidates = []
        high_confidence = []
        filtered = []
        stats = {"total_pairs": len(raw_candidates), "high_similarity": 0, "text_containment": 0}

        for pair in raw_candidates:
            # Rule 1: High similarity auto-merge
            if pair.similarity >= self.HIGH_SIMILARITY_THRESHOLD:
                # Keep the one with higher paper_count
                if pair.concept1.get('paper_count', 0) >= pair.concept2.get('paper_count', 0):
                    target, source = pair.concept1, pair.concept2
                else:
                    target, source = pair.concept2, pair.concept1

                high_confidence.append({
                    "source_id": source['id'],
                    "target_id": target['id'],
                    "confidence": 0.95,
                    "rationale": f"文本高度相似 (相似度: {pair.similarity:.2f})",
                    "merge_type": "synonym"
                })
                stats["high_similarity"] += 1
                continue

            # Rule 2: Text containment (absorption)
            should_merge, target_text = self.check_text_containment(
                pair.concept1['text'], pair.concept2['text']
            )
            if should_merge:
                # The shorter text is the target (returned by check_text_containment)
                if pair.concept1['text'] == target_text:
                    target, source = pair.concept1, pair.concept2
                else:
                    target, source = pair.concept2, pair.concept1

                high_confidence.append({
                    "source_id": source['id'],
                    "target_id": target['id'],
                    "confidence": 0.90,
                    "rationale": f"文本包含关系: '{target['text']}' 是 '{source['text']}' 的简洁形式",
                    "merge_type": "absorption"
                })
                stats["text_containment"] += 1
                continue

            # Needs LLM analysis
            candidates.append(pair)

        stats["llm_needed"] = len(candidates)
        stats["auto_merged"] = len(high_confidence)

        return {
            "candidates": candidates,
            "high_confidence": high_confidence,
            "filtered": filtered,
            "stats": stats
        }

    def generate_candidates_batch(self, batch_size: int = 50, folder_id: str = None) -> Generator[list[ConceptPair], None, None]:
        """分批生成候选对（用于大库），可选按文件夹过滤"""
        batch = []
        for category in self.CATEGORIES:
            if folder_id and folder_id != 'default':
                concepts = self.db.get_concepts_by_category_and_folder(category, folder_id)
            else:
                concepts = self.db.get_concepts_by_category(category)
            for i, c1 in enumerate(concepts):
                for c2 in concepts[i+1:]:
                    similarity = self.text_similarity(c1['text'], c2['text'])
                    if similarity >= self.SIMILARITY_THRESHOLD:
                        batch.append(ConceptPair(concept1=c1, concept2=c2, similarity=similarity))
                        if len(batch) >= batch_size:
                            yield batch
                            batch = []
        if batch:
            yield batch

    def _generate_pairs_in_category(self, concepts: list[dict]) -> list[ConceptPair]:
        """在同类概念中生成候选对"""
        pairs = []
        for i, c1 in enumerate(concepts):
            for c2 in concepts[i+1:]:
                similarity = self.text_similarity(c1['text'], c2['text'])
                if similarity >= self.SIMILARITY_THRESHOLD:
                    pairs.append(ConceptPair(concept1=c1, concept2=c2, similarity=similarity))
        return pairs
