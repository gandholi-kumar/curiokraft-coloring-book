"""Unit tests for pure prompt synthesis function in debate_engine.py.

Validates that prompts can be synthesized purely in-process without spawning
subprocesses, parsing CLI arguments, or calling external network APIs.
"""

from curiokraft_book.orchestrator.debate_engine import PromptItem, synthesize_prompts


def test_synthesize_prompts_returns_typed_items():
    """Verify synthesize_prompts returns a list of PromptItem models."""
    prompts = synthesize_prompts(count=3)
    assert len(prompts) >= 3
    assert all(isinstance(p, PromptItem) for p in prompts)


def test_prompt_item_required_fields():
    """Verify every prompt item contains valid, non-empty fields."""
    prompts = synthesize_prompts(count=3)
    for p in prompts:
        assert p.id, "Prompt ID must not be empty"
        assert p.label, "Prompt label must not be empty"
        assert len(p.positive_prompt) > 20, (
            "Positive prompt must contain descriptive line art instructions"
        )
        assert len(p.negative_prompt) > 10, "Negative prompt must contain quality constraints"
        assert p.aspect_ratio in ["3:4", "8.5:11"], "Aspect ratio must be portrait"
        assert 0.0 <= p.temperature <= 1.0, "Temperature must be between 0.0 and 1.0"


def test_covers_included_in_synthesis():
    """Verify that Front Cover and Back Cover are automatically synthesized."""
    prompts = synthesize_prompts(count=2)
    prompt_ids = {p.id for p in prompts}
    assert "COVER_FRONT" in prompt_ids
    assert "COVER_BACK" in prompt_ids


def test_selected_pages_filtering():
    """Verify selected_pages parameter filters interior pages correctly."""
    prompts = synthesize_prompts(selected_pages=["P005"])
    interior_ids = [p.id for p in prompts if p.type == "interior_page"]
    assert "P005" in interior_ids
    assert "P006" not in interior_ids
