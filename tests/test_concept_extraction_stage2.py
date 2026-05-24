# tests/test_concept_extraction_stage2.py
"""
Regression tests for Concept Extraction Stage 2 - Concept Tree parsing.

These tests verify that LLMConceptExtractor correctly parses concept tree responses
from Stage 2 LLM outputs.
"""

import pytest

from mkg.concept_extractor import LLMConceptExtractor


@pytest.fixture
def extractor():
    """Create an LLMConceptExtractor instance."""
    return LLMConceptExtractor()


class TestStage2Parsing:
    """Test Stage 2 response parsing with fixed LLM outputs."""

    def test_parse_concept_tree_with_markdown(self, extractor):
        """Parse concept tree wrapped in markdown code block."""
        response = '''```json
{
  "paper_summary": "Proposed X-Method for image classification",
  "concept_tree": {
    "concept": "Computer Vision",
    "category": "field",
    "confidence": 0.95,
    "children": [
      {
        "concept": "Image Classification",
        "category": "direction",
        "confidence": 0.9,
        "children": [
          {
            "concept": "X-Method",
            "category": "method",
            "confidence": 0.85,
            "children": []
          }
        ]
      }
    ]
  },
  "methodology": "Used neural networks with attention",
  "datasets": ["ImageNet", "CIFAR-10"],
  "metrics": ["accuracy", "F1"]
}
```'''
        result = extractor._parse_stage2_response(response)

        assert result["paper_summary"] == "Proposed X-Method for image classification"
        assert "concept_tree" in result
        tree = result["concept_tree"]
        assert tree["concept"] == "Computer Vision"
        assert tree["category"] == "field"
        assert len(tree["children"]) == 1
        assert tree["children"][0]["concept"] == "Image Classification"
        assert result["datasets"] == ["ImageNet", "CIFAR-10"]

    def test_parse_flat_concept_tree(self, extractor):
        """Parse a flat concept tree with no nesting."""
        response = '''{"concept_tree": {"concept": "AI", "category": "field", "children": []}, "paper_summary": "", "methodology": "", "datasets": [], "metrics": []}'''
        result = extractor._parse_stage2_response(response)

        tree = result["concept_tree"]
        assert tree["concept"] == "AI"
        assert tree["children"] == []

    def test_parse_deep_concept_tree(self, extractor):
        """Parse a deeply nested concept tree (6 levels)."""
        import json

        # Build nested tree programmatically to avoid bracket errors
        tree_data = {"concept": "L6", "category": "technique", "children": []}
        for level, category in [(5, "method"), (4, "task"), (3, "subdirection"), (2, "direction"), (1, "field")]:
            tree_data = {"concept": f"L{level}", "category": category, "children": [tree_data]}

        response = json.dumps({
            "concept_tree": tree_data,
            "paper_summary": "",
            "methodology": "",
            "datasets": [],
            "metrics": [],
        })
        result = extractor._parse_stage2_response(response)

        tree = result["concept_tree"]
        depth = 0
        node = tree
        while node.get("children"):
            depth += 1
            node = node["children"][0]
        assert depth == 5  # L1 -> L2 -> L3 -> L4 -> L5 -> L6

    def test_parse_malformed_json_fallback(self, extractor):
        """Malformed JSON should return safe fallback."""
        response = "Not valid json {{"
        result = extractor._parse_stage2_response(response)

        assert result["concept_tree"] == {}
        assert result["paper_summary"] == ""
        assert result["datasets"] == []

    def test_parse_empty_response(self, extractor):
        """Empty response should return fallback structure."""
        result = extractor._parse_stage2_response("")

        assert "concept_tree" in result
        assert "paper_summary" in result


class TestConceptTreeBuilding:
    """Test _build_concept_tree internal method."""

    def test_build_simple_tree(self, extractor):
        """Build a ConceptTree from parsed dict."""
        raw_tree = {
            "concept": "AI",
            "category": "field",
            "confidence": 0.95,
            "children": [
                {"concept": "ML", "category": "direction", "confidence": 0.9, "children": []}
            ],
        }
        concept_tree = extractor._build_concept_tree(raw_tree)

        assert concept_tree.concept == "AI"
        assert concept_tree.category == "field"
        assert len(concept_tree.children) == 1
        assert concept_tree.children[0].concept == "ML"

    def test_build_tree_with_anchor_and_role(self, extractor):
        """Build tree preserving anchor and contribution_role flags."""
        raw_tree = {
            "concept": "NovelMethod",
            "category": "method",
            "confidence": 0.88,
            "is_anchor": True,
            "contribution_role": "proposed",
            "children": [],
        }
        concept_tree = extractor._build_concept_tree(raw_tree)

        assert concept_tree.is_anchor is True
        assert concept_tree.contribution_role == "proposed"

    def test_build_empty_tree(self, extractor):
        """Build tree from empty dict returns None."""
        concept_tree = extractor._build_concept_tree({})

        assert concept_tree is None
