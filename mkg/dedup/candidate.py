"""
候选对生成器 - 预筛选可能重复的概念对
"""

from difflib import SequenceMatcher
from typing import List, Dict, Generator
from dataclasses import dataclass


@dataclass
class ConceptPair:
    """概念对"""
    concept1: Dict
    concept2: Dict
    similarity: float


class CandidateGenerator:
    """候选对生成器"""

    SIMILARITY_THRESHOLD = 0.6
    CATEGORIES = ['field', 'direction', 'subdirection', 'task', 'method', 'technique']

    def __init__(self, db):
        self.db = db

    def text_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度（0-1）"""
        return SequenceMatcher(None, text1, text2).ratio()

    def generate_candidates(self, folder_id: str = None) -> List[ConceptPair]:
        """生成所有候选对，可选按文件夹过滤"""
        candidates = []
        for category in self.CATEGORIES:
            if folder_id and folder_id != 'default':
                concepts = self.db.get_concepts_by_category_and_folder(category, folder_id)
            else:
                concepts = self.db.get_concepts_by_category(category)
            candidates.extend(self._generate_pairs_in_category(concepts))
        return candidates

    def generate_candidates_batch(self, batch_size: int = 50, folder_id: str = None) -> Generator[List[ConceptPair], None, None]:
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

    def _generate_pairs_in_category(self, concepts: List[Dict]) -> List[ConceptPair]:
        """在同类概念中生成候选对"""
        pairs = []
        for i, c1 in enumerate(concepts):
            for c2 in concepts[i+1:]:
                similarity = self.text_similarity(c1['text'], c2['text'])
                if similarity >= self.SIMILARITY_THRESHOLD:
                    pairs.append(ConceptPair(concept1=c1, concept2=c2, similarity=similarity))
        return pairs