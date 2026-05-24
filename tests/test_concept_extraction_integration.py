# tests/test_concept_extraction_integration.py
"""
Integration tests for Concept Extraction pipeline.

These tests mock the LLM layer and verify the full two-stage extraction pipeline
produces correctly structured output.
"""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

# Pre-inject mock mkg.llm so tests can run without langchain installed
_mock_llm_mod = MagicMock()
sys.modules["mkg.llm"] = _mock_llm_mod

from mkg.concept_extractor import LLMConceptExtractor
from mkg.pdf_models import PaperContent


@pytest.fixture
def sample_paper():
    """Create a minimal paper content fixture."""
    return PaperContent(
        title="X-Method: A Novel Approach",
        authors=["Alice Smith", "Bob Jones"],
        abstract="We propose X-Method, which improves accuracy by 15%.",
        full_text="Introduction... Related Work... Method... Experiments...",
        sections={"introduction": "...", "method": "..."},
        metadata={},
        doi="10.1234/xmethod",
    )


@pytest.fixture
def stage1_mock_response():
    """Fixed Stage 1 LLM response."""
    return '''```json
{
  "one_sentence_summary": {
    "en": "This paper proposes X-Method for image classification.",
    "zh": "本文提出了用于图像分类的X-Method。"
  },
  "research_context": {
    "field": {"en": "Computer Vision", "zh": "计算机视觉"},
    "direction": {"en": "Image Classification", "zh": "图像分类"},
    "existing_gap": {"en": "Existing methods are slow.", "zh": "现有方法很慢。"}
  },
  "core_contributions": [
    {
      "type": "new_method",
      "claim": {"en": "Proposed X-Method", "zh": "提出了X-Method"},
      "novelty": {"en": "15% faster than CNN", "zh": "比CNN快15%"}
    }
  ],
  "methodology_summary": {
    "approach": {"en": "Attention-based CNN", "zh": "基于注意力的CNN"},
    "key_components": {"en": ["attention module"], "zh": ["注意力模块"]},
    "baselines": {"en": ["ResNet"], "zh": ["ResNet"]}
  },
  "results_summary": {
    "datasets": {"en": ["ImageNet"], "zh": ["ImageNet"]},
    "metrics": {"en": ["accuracy"], "zh": ["准确率"]},
    "main_finding": {"en": "95% accuracy, 15% speedup", "zh": "95%准确率，提速15%"}
  },
  "background_concepts": {"en": ["CNN", "ImageNet"], "zh": ["CNN", "ImageNet"]},
  "novel_concepts": {"en": ["X-Method"], "zh": ["X-Method"]}
}
```'''


@pytest.fixture
def stage2_mock_response():
    """Fixed Stage 2 LLM response."""
    return '''```json
{
  "paper_summary": "Proposed X-Method for image classification with 15% speedup",
  "concept_tree": {
    "concept": "Computer Vision",
    "category": "field",
    "confidence": 0.95,
    "children": [
      {
        "concept": "Image Classification",
        "category": "direction",
        "confidence": 0.92,
        "children": [
          {
            "concept": "X-Method",
            "category": "method",
            "confidence": 0.88,
            "is_anchor": true,
            "contribution_role": "proposed",
            "children": []
          }
        ]
      }
    ]
  },
  "methodology": "Attention-based neural network architecture",
  "datasets": ["ImageNet"],
  "metrics": ["accuracy", "inference_time"]
}
```'''


class TestTwoStageExtraction:
    """Test the full two-stage extraction pipeline with mocked LLM."""

    def test_extract_produces_structured_output(self, sample_paper, stage1_mock_response, stage2_mock_response):
        """End-to-end: mock LLM and verify extract() returns LLMExtractedContent."""
        extractor = LLMConceptExtractor()

        _mock_llm_mod.generate.reset_mock()
        _mock_llm_mod.generate.side_effect = [stage1_mock_response, stage2_mock_response]

        result = extractor.extract(sample_paper, existing_concepts="")

        # Verify result structure
        assert result.title is not None
        assert result.one_sentence_summary is not None
        summary_text = result.one_sentence_summary.get("en", "")
        assert "X-Method" in summary_text or "image classification" in summary_text
        assert result.concept_tree is not None
        assert result.concept_tree.concept == "Computer Vision"
        assert len(result.concept_tree.children) == 1
        assert result.datasets.get("en") == ["ImageNet"] or result.datasets == ["ImageNet"]
        assert "accuracy" in result.metrics.get("en", []) or "accuracy" in result.metrics

    def test_extract_passes_existing_concepts_to_stage2(self, sample_paper, stage1_mock_response, stage2_mock_response):
        """Verify existing_concepts parameter is passed through to Stage 2 prompt."""
        extractor = LLMConceptExtractor()

        _mock_llm_mod.generate.reset_mock()
        _mock_llm_mod.generate.side_effect = [stage1_mock_response, stage2_mock_response]

        existing = "Existing Graph: AI -> ML -> Deep Learning"
        extractor.extract(sample_paper, existing_concepts=existing)

        # Stage 2 call should contain the existing graph context
        stage2_call = _mock_llm_mod.generate.call_args_list[1]
        stage2_prompt = stage2_call.kwargs.get("prompt") or stage2_call.args[0]
        assert "Existing Graph" in stage2_prompt or "existing_graph" in stage2_prompt

    def test_extract_handles_llm_failure_gracefully(self, sample_paper):
        """If LLM returns garbage, extract should still return a valid object."""
        extractor = LLMConceptExtractor()

        _mock_llm_mod.generate.reset_mock()
        _mock_llm_mod.generate.side_effect = ["not json", "also not json"]

        result = extractor.extract(sample_paper)

        # Should not raise; returns object with safe defaults
        assert result is not None
        # When both stages fail, concept_tree may be None (fallback behavior)
        assert result.concept_tree is None or hasattr(result.concept_tree, "concept")

    def test_stage1_prompt_contains_paper_content(self, sample_paper, stage1_mock_response, stage2_mock_response):
        """Verify Stage 1 prompt includes title, abstract, and body."""
        extractor = LLMConceptExtractor()

        _mock_llm_mod.generate.reset_mock()
        _mock_llm_mod.generate.side_effect = [stage1_mock_response, stage2_mock_response]
        extractor.extract(sample_paper)

        stage1_call = _mock_llm_mod.generate.call_args_list[0]
        prompt = stage1_call.kwargs.get("prompt") or stage1_call.args[0]
        assert sample_paper.title in prompt
        assert sample_paper.abstract in prompt

    def test_stage2_prompt_contains_stage1_summary(self, sample_paper, stage1_mock_response, stage2_mock_response):
        """Verify Stage 2 prompt includes Stage 1 summary JSON."""
        extractor = LLMConceptExtractor()

        _mock_llm_mod.generate.reset_mock()
        _mock_llm_mod.generate.side_effect = [stage1_mock_response, stage2_mock_response]
        extractor.extract(sample_paper)

        stage2_call = _mock_llm_mod.generate.call_args_list[1]
        prompt = stage2_call.kwargs.get("prompt") or stage2_call.args[0]
        assert "Computer Vision" in prompt  # From Stage 1 summary
