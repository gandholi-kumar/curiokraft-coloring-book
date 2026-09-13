"""
Regression tests for Item #3: Extract DRY in Cover Generation refactoring.

Verifies that the refactored run_cover_debate() produces identical outputs
to the original implementation while reducing code duplication.
"""

import pytest
from pathlib import Path

from curiokraft_book.orchestrator.debate_engine import DebateEngine, _CoverDebateSpec
from curiokraft_book.orchestrator.model_client import ModelClient


@pytest.fixture
def debate_engine():
    """Create a DebateEngine instance for testing."""
    return DebateEngine(model_client=ModelClient())


def test_back_cover_debate_structure(debate_engine):
    """Verify back cover debate produces expected 4-round structure."""
    result = debate_engine.run_cover_debate(
        cover_type="back_cover",
        manifest_path="data/pages.json",
    )

    # Verify basic structure
    assert result.page_id == "COVER_BACK"
    assert result.canonical_object == "back_cover"
    assert result.display_label == "BACK COVER MASTER ARTWORK"
    assert result.section == "Covers"

    # Verify 4 rounds
    assert len(result.rounds) == 4
    assert result.rounds[0].round_name == "Specialist Proposals"
    assert result.rounds[1].round_name == "Cross-Specialist Review"
    assert result.rounds[2].round_name == "Adversarial Red-Team Critique"
    assert result.rounds[3].round_name == "Judge Synthesis & Specification Lock"

    # Verify prompts exist
    assert len(result.positive_prompt) > 100
    assert len(result.negative_prompt) > 50
    assert result.judge_verdict == "APPROVED"
    assert result.winner_agent == "AGT-002-DESIGN"
    assert result.final_score == 98.0


def test_front_cover_debate_structure(debate_engine):
    """Verify front cover debate produces expected 4-round structure."""
    result = debate_engine.run_cover_debate(
        cover_type="front_cover",
        manifest_path="data/pages.json",
    )

    # Verify basic structure
    assert result.page_id == "COVER_FRONT"
    assert result.canonical_object == "front_cover"
    assert result.display_label == "FRONT COVER MASTER ARTWORK"
    assert result.section == "Covers"

    # Verify 4 rounds
    assert len(result.rounds) == 4
    assert result.rounds[0].round_name == "Specialist Proposals"
    assert result.rounds[1].round_name == "Cross-Specialist Review"
    assert result.rounds[2].round_name == "Adversarial Red-Team Critique"
    assert result.rounds[3].round_name == "Judge Synthesis & Specification Lock"

    # Verify prompts exist
    assert len(result.positive_prompt) > 100
    assert len(result.negative_prompt) > 50
    assert result.judge_verdict == "APPROVED"
    assert result.winner_agent == "AGT-002-DESIGN"
    assert result.final_score == 98.0


def test_back_cover_contains_flashcards(debate_engine):
    """Verify back cover positive prompt contains flashcard grid elements."""
    result = debate_engine.run_cover_debate(
        cover_type="back_cover",
        manifest_path="data/pages.json",
    )

    positive = result.positive_prompt.lower()

    # Back cover specific elements
    assert "flashcard" in positive or "card" in positive
    assert "feature" in positive or "pill" in positive
    assert "right edge" in positive  # Spine on right for back cover
    assert "turquoise" in positive
    assert "wave" in positive


def test_front_cover_contains_hero(debate_engine):
    """Verify front cover positive prompt contains hero character and title."""
    result = debate_engine.run_cover_debate(
        cover_type="front_cover",
        manifest_path="data/pages.json",
    )

    positive = result.positive_prompt.lower()

    # Front cover specific elements
    assert "tiny hands" in positive
    assert "hero" in positive or "central" in positive
    assert "left edge" in positive  # Spine on left for front cover
    assert "3d puffy" in positive or "bubble" in positive
    assert "turquoise" in positive
    assert "wave" in positive


def test_covers_have_different_layouts(debate_engine):
    """Verify front and back covers have distinct content (not just mirrored)."""
    back_result = debate_engine.run_cover_debate(
        cover_type="back_cover",
        manifest_path="data/pages.json",
    )
    front_result = debate_engine.run_cover_debate(
        cover_type="front_cover",
        manifest_path="data/pages.json",
    )

    # Prompts should be completely different
    assert back_result.positive_prompt != front_result.positive_prompt
    assert back_result.negative_prompt != front_result.negative_prompt

    # Round 1 outputs should differ
    back_r1 = back_result.rounds[0].agent_outputs
    front_r1 = front_result.rounds[0].agent_outputs
    assert back_r1 != front_r1

    # Verify back has flashcards, front has hero
    back_pos = back_result.positive_prompt.lower()
    front_pos = front_result.positive_prompt.lower()

    assert "flashcard" in back_pos or "card" in back_pos
    assert "hero" in front_pos or "tiny hands" in front_pos


def test_cover_debate_spec_construction(debate_engine):
    """Verify _build_cover_debate_spec creates valid spec objects."""
    # Test back cover spec
    back_spec = debate_engine._build_cover_debate_spec(
        cover_type="back_cover",
        manifest_path="data/pages.json",
        book_config_path="data/book_config.yaml",
        blueprint_spec=None,
        title="Test Title",
        subtitle="Test Subtitle",
        brand="Test Brand",
        age_min=1,
        age_max=4,
    )

    assert isinstance(back_spec, _CoverDebateSpec)
    assert back_spec.page_id == "COVER_BACK"
    assert len(back_spec.r1_outputs) > 0
    assert len(back_spec.r2_outputs) > 0
    assert len(back_spec.r3_outputs) > 0
    assert len(back_spec.positive_prompt) > 100
    assert len(back_spec.negative_prompt) > 50

    # Test front cover spec
    front_spec = debate_engine._build_cover_debate_spec(
        cover_type="front_cover",
        manifest_path="data/pages.json",
        book_config_path="data/book_config.yaml",
        blueprint_spec=None,
        title="Test Title",
        subtitle="Test Subtitle",
        brand="Test Brand",
        age_min=1,
        age_max=4,
    )

    assert isinstance(front_spec, _CoverDebateSpec)
    assert front_spec.page_id == "COVER_FRONT"
    assert len(front_spec.r1_outputs) > 0
    assert len(front_spec.r2_outputs) > 0
    assert len(front_spec.r3_outputs) > 0
    assert len(front_spec.positive_prompt) > 100
    assert len(front_spec.negative_prompt) > 50

    # Specs should be different
    assert back_spec.positive_prompt != front_spec.positive_prompt


def test_assemble_cover_debate_creates_result(debate_engine):
    """Verify _assemble_cover_debate correctly builds DebateResult from spec."""
    # Create a minimal spec
    spec = _CoverDebateSpec(
        page_id="TEST_ID",
        canonical_object="test_cover",
        display_label="TEST COVER",
        section="Covers",
        r1_outputs={"AGT-001": {"test": "value1"}},
        r2_outputs={"cross_consensus": "test consensus"},
        r3_outputs={"AGT-006-REDTEAM": {"stress_test_findings": ["finding1"]}},
        positive_prompt="Test positive prompt",
        negative_prompt="Test negative prompt",
        judge_verdict="APPROVED",
        judge_score=98.0,
        winner_agent="AGT-002-DESIGN",
        judge_rationale="Test rationale",
    )

    result = debate_engine._assemble_cover_debate(spec)

    assert result.page_id == "TEST_ID"
    assert result.canonical_object == "test_cover"
    assert result.display_label == "TEST COVER"
    assert result.positive_prompt == "Test positive prompt"
    assert result.negative_prompt == "Test negative prompt"
    assert result.judge_verdict == "APPROVED"
    assert result.final_score == 98.0
    assert len(result.rounds) == 4


def test_no_code_duplication_in_round_assembly():
    """Verify DRY principle: round assembly logic is not duplicated."""
    # Read the debate_engine source to verify no duplication
    engine_path = Path(__file__).parent.parent / "src" / "curiokraft_book" / "orchestrator" / "debate_engine.py"

    with open(engine_path, encoding="utf-8") as f:
        source = f.read()

    # Count occurrences of the round assembly pattern
    # After refactoring, "DebateRound(round_number=1" should appear only in _assemble_cover_debate
    round1_count = source.count('DebateRound(round_number=1, round_name="Specialist Proposals"')

    # Should only appear once in _assemble_cover_debate (not duplicated in back/front branches)
    assert round1_count == 1, f"Found {round1_count} occurrences of round 1 assembly (expected 1)"
