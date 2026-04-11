"""Metadata for the canonical E2E test fixture.

Everything in this file is keyed to `tests/fixtures/e2e_sample.pdf`. If that
file is replaced, update the constants below — nothing else in the E2E suite
references the specific paper.
"""

from pathlib import Path

FIXTURE_PDF_PATH = Path(__file__).parent.parent / "fixtures" / "e2e_sample.pdf"
FIXTURE_PDF_NAME = "e2e_sample.pdf"
FIXTURE_EXPECTED_DOI = "e2e_sample"  # Database.add_paper uses pdf_path.stem

# Loose keyword set for "did the LLM return something topically relevant"
# assertions. Matched case-insensitively via `any(kw in text.lower() ...)`.
# Initial values target 2305.11738v4 (CRITIC: LLMs Self-Correct with
# Tool-Interactive Critiquing). If false positives occur, GROW this set —
# never loosen the count thresholds in test_pipeline.py.
FIXTURE_TOPIC_KEYWORDS: frozenset[str] = frozenset({
    "llm",
    "language model",
    "critic",
    "correct",
    "tool",
    "feedback",
    "reason",
    "reasoning",
    "evaluation",
    "大语言模型",
    "自我修正",
    "工具",
})
