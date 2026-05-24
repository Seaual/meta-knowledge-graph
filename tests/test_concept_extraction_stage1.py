# tests/test_concept_extraction_stage1.py
"""
Regression tests for Concept Extraction Stage 1 - Paper Summary parsing.

These tests verify that LLMConceptExtractor correctly parses various LLM response formats
without requiring actual LLM calls.
"""

import pytest

from mkg.concept_extractor import LLMConceptExtractor
from mkg.pdf_models import PaperContent


@pytest.fixture
def extractor():
    """Create an LLMConceptExtractor instance."""
    return LLMConceptExtractor()


class TestStage1Parsing:
    """Test Stage 1 response parsing with fixed LLM outputs."""

    def test_parse_valid_json_with_markdown_code_block(self, extractor):
        """Parse JSON wrapped in markdown code block."""
        response = '''```json
{
  "one_sentence_summary": {
    "en": "This paper proposes a novel method for X.",
    "zh": "本文提出了一种新的X方法。"
  },
  "research_context": {
    "field": {"en": "Computer Science", "zh": "计算机科学"},
    "direction": {"en": "Machine Learning", "zh": "机器学习"},
    "existing_gap": {"en": "Previous methods were slow.", "zh": "之前的方法很慢。"}
  },
  "core_contributions": [
    {
      "type": "new_method",
      "claim": {"en": "Proposed X", "zh": "提出了X"},
      "novelty": {"en": "Faster than Y", "zh": "比Y更快"}
    }
  ],
  "methodology_summary": {
    "approach": {"en": "Neural network", "zh": "神经网络"},
    "key_components": {"en": ["attention"], "zh": ["注意力"]},
    "baselines": {"en": ["CNN"], "zh": ["CNN"]}
  },
  "results_summary": {
    "datasets": {"en": ["ImageNet"], "zh": ["ImageNet"]},
    "metrics": {"en": ["accuracy"], "zh": ["准确率"]},
    "main_finding": {"en": "95% accuracy", "zh": "95%准确率"}
  },
  "background_concepts": {"en": ["Deep Learning"], "zh": ["深度学习"]},
  "novel_concepts": {"en": ["X-Method"], "zh": ["X方法"]}
}
```'''
        result = extractor._parse_stage1_response(response)

        assert result["one_sentence_summary"]["en"] == "This paper proposes a novel method for X."
        assert result["research_context"]["field"]["en"] == "Computer Science"
        assert len(result["core_contributions"]) == 1
        assert result["core_contributions"][0]["type"] == "new_method"
        assert result["background_concepts"]["en"] == ["Deep Learning"]
        assert result["novel_concepts"]["en"] == ["X-Method"]

    def test_parse_plain_json_without_markdown(self, extractor):
        """Parse plain JSON without markdown wrapper."""
        response = '{"one_sentence_summary": {"en": "Plain JSON test", "zh": "纯JSON测试"}, "research_context": {}, "core_contributions": [], "methodology_summary": {}, "results_summary": {}, "background_concepts": {"en": [], "zh": []}, "novel_concepts": {"en": [], "zh": []}}'
        result = extractor._parse_stage1_response(response)

        assert result["one_sentence_summary"]["en"] == "Plain JSON test"

    def test_parse_malformed_json_fallback(self, extractor):
        """Malformed JSON should return a safe fallback structure."""
        response = "This is not JSON at all { broken"
        result = extractor._parse_stage1_response(response)

        # Should return fallback with all expected keys
        assert "one_sentence_summary" in result
        assert "research_context" in result
        assert "core_contributions" in result
        assert result["core_contributions"] == []

    def test_parse_empty_response(self, extractor):
        """Empty response should return fallback structure."""
        result = extractor._parse_stage1_response("")

        assert "one_sentence_summary" in result
        assert "concept_tree" not in result  # Stage 1 doesn't produce concept_tree


class TestStage1StructureValidation:
    """Validate that parsed results conform to expected schema."""

    def test_all_required_keys_present(self, extractor):
        """Every Stage 1 result must contain the required top-level keys."""
        response = '''```json
{
  "one_sentence_summary": {"en": "E", "zh": "Z"},
  "research_context": {"field": {"en": "F", "zh": "F"}, "direction": {"en": "D", "zh": "D"}, "existing_gap": {"en": "G", "zh": "G"}},
  "core_contributions": [],
  "methodology_summary": {"approach": {"en": "A", "zh": "A"}, "key_components": {"en": [], "zh": []}, "baselines": {"en": [], "zh": []}},
  "results_summary": {"datasets": {"en": [], "zh": []}, "metrics": {"en": [], "zh": []}, "main_finding": {"en": "M", "zh": "M"}},
  "background_concepts": {"en": [], "zh": []},
  "novel_concepts": {"en": [], "zh": []}
}
```'''
        result = extractor._parse_stage1_response(response)
        required_keys = [
            "one_sentence_summary",
            "research_context",
            "core_contributions",
            "methodology_summary",
            "results_summary",
            "background_concepts",
            "novel_concepts",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"
