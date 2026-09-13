"""Unit tests for ``orchestrator/retry_manager.py``.

The handoff notes the uncovered sections are:
- 59, 73: early-failure branches in ``attempt_programmatic_rescue``
- 84–87: the success branch after validation
- 104–135: the ``formulate_revised_prompt`` logic (both the escalation path
  and the per-violation fortification).

Only a small amount of mocking is needed; the rescue functions themselves
are already tested in ``test_validators.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from curiokraft_book.orchestrator.retry_manager import RetryManager


def test_attempt_programmatic_rescue_binarize_fails(tmp_path: Path):
    """Line 59: binarize step returns failure."""
    raw = tmp_path / "raw.png"
    raw.write_bytes(b"not an image")
    out = tmp_path / "out.png"

    mgr = RetryManager()
    ok, msg, violations = mgr.attempt_programmatic_rescue(raw, out)

    assert ok is False
    assert msg == "Failed to apply adaptive binarization."
    assert violations == ["RESCUE_BINARIZE_FAILED"]


def test_attempt_programmatic_rescue_margin_fit_fails(tmp_path: Path, monkeypatch):
    """Line 73: margin fitting step returns failure."""
    # Give binarize a fake-success so we reach the margin fitter
    raw = tmp_path / "raw.png"
    raw.write_bytes(b"89 50 4e 47 0d 0a 1a 0a")  # PNG header so it opens
    out = tmp_path / "out.png"

    # Mock binarize to succeed so we reach the margin fitter
    def mock_binarize_success(*_a, **_k):
        from curiokraft_book.rescue.binarizer import RescueBinarizeResult

        return RescueBinarizeResult(
            success=True,
            input_path=str(raw),
            output_path=str(out),
            original_non_binary_pixels=100,
            cleaned_pixels_count=50,
            method_applied="MOCK",
        )

    monkeypatch.setattr(
        "curiokraft_book.orchestrator.retry_manager.rescue_binarize", mock_binarize_success
    )

    def fail_fit(*_a, **_k):
        from curiokraft_book.rescue.margin_fitter import MarginFitResult

        # Return a failure result with dummy values for required fields
        return MarginFitResult(
            success=False,
            input_path=str(raw),
            output_path=str(out),
            original_bbox=(0, 0, 0, 0),
            new_bbox=(0, 0, 0, 0),
            scale_factor=1.0,
            target_canvas_size=(2550, 3300),
            top_margin_px=0,
            bottom_margin_px=0,
            left_margin_px=0,
            right_margin_px=0,
        )

    monkeypatch.setattr("curiokraft_book.orchestrator.retry_manager.fit_to_safe_margins", fail_fit)

    mgr = RetryManager()
    ok, msg, violations = mgr.attempt_programmatic_rescue(raw, out)

    assert ok is False
    assert msg == "Failed to fit artwork to safe margins."
    assert violations == ["RESCUE_MARGIN_FIT_FAILED"]


def test_attempt_programmatic_rescue_success_path(tmp_path: Path, monkeypatch):
    """Lines 84–87: all three validators pass, so we return the success tuple."""
    raw = tmp_path / "raw.png"
    raw.write_bytes(b"89 50 4e 47 0d 0a 1a 0a")
    out = tmp_path / "out.png"

    # Mock binarize to succeed so we reach the margin fitter
    def mock_binarize_success(*_a, **_k):
        from curiokraft_book.rescue.binarizer import RescueBinarizeResult

        return RescueBinarizeResult(
            success=True,
            input_path=str(raw),
            output_path=str(out),
            original_non_binary_pixels=100,
            cleaned_pixels_count=50,
            method_applied="MOCK",
        )

    monkeypatch.setattr(
        "curiokraft_book.orchestrator.retry_manager.rescue_binarize", mock_binarize_success
    )

    # Mock margin fitter to succeed so we reach the validators
    def mock_fit_success(*_a, **_k):
        from curiokraft_book.rescue.margin_fitter import MarginFitResult

        return MarginFitResult(
            success=True,
            input_path=str(raw),
            output_path=str(out),
            original_bbox=(0, 0, 100, 100),
            new_bbox=(0, 0, 100, 100),
            scale_factor=1.0,
            target_canvas_size=(2550, 3300),
            top_margin_px=0,
            bottom_margin_px=0,
            left_margin_px=0,
            right_margin_px=0,
        )

    monkeypatch.setattr(
        "curiokraft_book.orchestrator.retry_manager.fit_to_safe_margins", mock_fit_success
    )

    # Patch the three validators to return passing results
    class Passing:
        def __init__(self):
            self.passed = True
            self.violations = []

    monkeypatch.setattr(
        "curiokraft_book.orchestrator.retry_manager.validate_dimensions",
        lambda *_a, **_k: Passing(),
    )
    monkeypatch.setattr(
        "curiokraft_book.orchestrator.retry_manager.validate_margins",
        lambda *_a, **_k: Passing(),
    )
    monkeypatch.setattr(
        "curiokraft_book.orchestrator.retry_manager.validate_black_and_white",
        lambda *_a, **_k: Passing(),
    )

    mgr = RetryManager()
    ok, msg, violations = mgr.attempt_programmatic_rescue(raw, out)

    assert ok is True
    assert msg == "Deterministic rescue completely resolved all violations."
    assert violations == []


# ----------------------------------------------------------------------
# formulate_revised_prompt
# ----------------------------------------------------------------------


def test_formulate_revised_prompt_escalates_after_max_retries():
    """Line 104–109: when attempt_number >= max_retries we escalate."""
    mgr = RetryManager(max_retries=2)
    action = mgr.formulate_revised_prompt(
        current_positive="pos",
        current_negative="neg",
        violations=["some violation"],
        attempt_number=2,  # == max_retries
    )

    assert action.action_type == "ESCALATE_HUMAN"
    assert action.success is False
    assert "Exceeded maximum retry attempts" in action.details
    assert action.revised_positive_prompt is None
    assert action.revised_negative_prompt is None


@pytest.mark.parametrize(
    "violation,pos_chunk,neg_chunk",
    [
        ("Gray", "stark pure binary black and white line art only", "gray tones"),
        ("Shading", "stark pure binary black and white line art only", "shading"),
        ("Color", "stark pure binary black and white line art only", "grayscale"),
    ],
)
def test_formulate_revised_prompt_fortifies_against_shading(
    violation: str, pos_chunk: str, neg_chunk: str
):
    """Lines 115–122: Gray/Shading/Color violations add the expected tokens."""
    mgr = RetryManager(max_retries=5)
    action = mgr.formulate_revised_prompt(
        current_positive="base positive",
        current_negative="base negative",
        violations=[violation],
        attempt_number=0,
    )

    assert action.action_type == "REVISE_PROMPT"
    assert action.success is True
    assert pos_chunk in action.revised_positive_prompt
    assert neg_chunk in action.revised_negative_prompt
    # Also check that we kept the original text
    assert "base positive" in action.revised_positive_prompt
    assert "base negative" in action.revised_negative_prompt


def test_formulate_revised_prompt_idempotent_on_shading():
    """Calling twice with the same violation does not double-append."""
    mgr = RetryManager(max_retries=5)
    first = mgr.formulate_revised_prompt("pos", "neg", ["Gray violation"], attempt_number=0)
    second = mgr.formulate_revised_prompt(
        first.revised_positive_prompt,
        first.revised_negative_prompt,
        ["Gray violation"],
        attempt_number=1,
    )
    # Should only contain one instance of the fortification
    assert (
        first.revised_positive_prompt.count("stark pure binary black and white line art only") == 1
    )
    assert (
        second.revised_positive_prompt.count("stark pure binary black and white line art only") == 1
    )


@pytest.mark.parametrize(
    "violation,pos_chunk,neg_chunk",
    [
        ("Margin", "centered strictly in middle", "touching edges"),
        ("Gutter", "centered strictly in middle", "border elements"),
    ],
)
def test_formulate_revised_prompt_fortifies_against_margins(
    violation: str, pos_chunk: str, neg_chunk: str
):
    """Lines 124–129: Margin/Gutter violations add centering tokens."""
    mgr = RetryManager(max_retries=5)
    action = mgr.formulate_revised_prompt(
        current_positive="base positive",
        current_negative="base negative",
        violations=[violation],
        attempt_number=0,
    )

    assert action.action_type == "REVISE_PROMPT"
    assert pos_chunk in action.revised_positive_prompt
    assert neg_chunk in action.revised_negative_prompt


def test_formulate_revised_prompt_fortifies_against_complexity():
    """Lines 131–133: Multiple/Complexity violations add isolated-object tokens."""
    mgr = RetryManager(max_retries=5)
    action = mgr.formulate_revised_prompt(
        current_positive="base positive",
        current_negative="base negative",
        violations=["Multiple objects found"],
        attempt_number=0,
    )

    assert action.action_type == "REVISE_PROMPT"
    assert "isolated single lone object" in action.revised_positive_prompt
    assert "multiple objects, scenery, landscape" in action.revised_negative_prompt


def test_formulate_revised_prompt_accumulates_multiple_violations(tmp_path: Path):
    """When several violation types are present, all fortifications are added."""
    mgr = RetryManager(max_retries=5)
    action = mgr.formulate_revised_prompt(
        current_positive="base pos",
        current_negative="base neg",
        violations=[
            "Gray shading detected",
            "Margin too narrow",
            "Multiple objects on page",
        ],
        attempt_number=0,
    )

    assert action.action_type == "REVISE_PROMPT"
    assert "stark pure binary black and white line art only" in action.revised_positive_prompt
    assert "centered strictly in middle" in action.revised_positive_prompt
    assert "isolated single lone object" in action.revised_positive_prompt

    assert "gray tones" in action.revised_negative_prompt
    assert "touching edges" in action.revised_negative_prompt
    assert "multiple objects, scenery, landscape" in action.revised_negative_prompt


def test_formulate_revised_prompt_ignores_known_but_inactive_violations():
    """Violations that don't match any if/leave the prompts unchanged."""
    mgr = RetryManager(max_retries=5)
    action = mgr.formulate_revised_prompt(
        current_positive="base pos",
        current_negative="base neg",
        violations=["Some unrelated error"],
        attempt_number=0,
    )

    assert action.action_type == "REVISE_PROMPT"
    assert action.revised_positive_prompt == "base pos"
    assert action.revised_negative_prompt == "base neg"
