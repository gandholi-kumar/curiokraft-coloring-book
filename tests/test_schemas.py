"""Unit tests for the ``schemas`` package (prompt-manifest Pydantic models).

Pure data models: no I/O, no mocking. These tests pin the required-vs-defaulted
field split and the ``Literal`` constraints, since downstream exporters rely on
a serialised manifest being unambiguous.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from curiokraft_book import schemas

CurioKraftPromptManifest = schemas.CurioKraftPromptManifest
PromptDefaults = schemas.PromptDefaults
PromptItem = schemas.PromptItem


def _item(**overrides) -> PromptItem:
    """A minimal valid ``PromptItem``; override any field per test."""
    base = {
        "id": "P001",
        "label": "Apple",
        "type": "interior_page",
        "drop_target": "inbox/raw_pages/raw_p001_apple.png",
        "preset_name": "CurioKraft - Interior Coloring Pages",
        "temperature": 0.5,
        "positive_prompt": "a simple apple line drawing",
        "negative_prompt": "shading, gray, color",
    }
    base.update(overrides)
    return PromptItem(**base)


def _manifest(**overrides) -> CurioKraftPromptManifest:
    base = {"book_title": "Test Book", "book_id": "test-vol1", "total_prompts": 1}
    base.update(overrides)
    return CurioKraftPromptManifest(**base)


# ----------------------------------------------------------------------
# PromptDefaults
# ----------------------------------------------------------------------


def test_prompt_defaults_are_filled_in():
    defaults = PromptDefaults()
    assert defaults.aspect_ratio == "3:4"
    assert defaults.output_format == "Images only"
    assert defaults.top_p == 0.95


def test_prompt_defaults_accept_overrides():
    defaults = PromptDefaults(aspect_ratio="1:1", top_p=0.5)
    assert defaults.aspect_ratio == "1:1"
    assert defaults.top_p == 0.5


# ----------------------------------------------------------------------
# PromptItem
# ----------------------------------------------------------------------


def test_prompt_item_defaults():
    item = _item()
    assert item.page_number is None
    assert item.section == "General"
    assert item.aspect_ratio == "3:4"
    assert item.output_format == "Images only"
    assert item.top_p == 0.95
    assert item.chat_id is None
    assert item.status == "pending"
    assert item.error is None


@pytest.mark.parametrize(
    "asset_type",
    ["front_cover", "back_cover", "interior_page", "special_asset"],
)
def test_prompt_item_accepts_each_asset_type(asset_type: str):
    assert _item(type=asset_type).type == asset_type


@pytest.mark.parametrize(
    "asset_type",
    ["cover", "interior", "INTERIOR_PAGE", ""],
)
def test_prompt_item_rejects_unknown_asset_type(asset_type: str):
    with pytest.raises(ValidationError):
        _item(type=asset_type)


@pytest.mark.parametrize(
    "status",
    ["pending", "in_progress", "completed", "failed", "skipped"],
)
def test_prompt_item_accepts_each_status(status: str):
    assert _item(status=status).status == status


def test_prompt_item_rejects_unknown_status():
    with pytest.raises(ValidationError):
        _item(status="done")


@pytest.mark.parametrize(
    "preset",
    ["CurioKraft - Interior Coloring Pages", "CurioKraft - Cover Art Master"],
)
def test_prompt_item_accepts_each_known_preset(preset: str):
    assert _item(preset_name=preset).preset_name == preset


def test_prompt_item_rejects_unknown_preset():
    with pytest.raises(ValidationError):
        _item(preset_name="Some Other Preset")


@pytest.mark.parametrize(
    "missing",
    [
        "id",
        "label",
        "type",
        "drop_target",
        "preset_name",
        "temperature",
        "positive_prompt",
        "negative_prompt",
    ],
)
def test_prompt_item_requires_core_fields(missing: str):
    fields = {
        "id": "P001",
        "label": "Apple",
        "type": "interior_page",
        "drop_target": "inbox/raw_pages/raw_p001_apple.png",
        "preset_name": "CurioKraft - Interior Coloring Pages",
        "temperature": 0.5,
        "positive_prompt": "positive",
        "negative_prompt": "negative",
    }
    del fields[missing]
    with pytest.raises(ValidationError):
        PromptItem(**fields)


def test_prompt_item_round_trips_through_dump_and_validate():
    original = _item(id="COVER_FRONT", type="front_cover", temperature=0.9, status="completed")
    restored = PromptItem.model_validate(original.model_dump())
    assert restored == original


# ----------------------------------------------------------------------
# CurioKraftPromptManifest
# ----------------------------------------------------------------------


def test_manifest_defaults():
    manifest = _manifest()
    assert manifest.manifest_version == "1.0.0"
    assert manifest.volume == "vol1"
    assert manifest.prompts == []
    assert isinstance(manifest.defaults, PromptDefaults)


@pytest.mark.parametrize("missing", ["book_title", "book_id", "total_prompts"])
def test_manifest_requires_core_fields(missing: str):
    fields = {"book_title": "T", "book_id": "b", "total_prompts": 0}
    del fields[missing]
    with pytest.raises(ValidationError):
        CurioKraftPromptManifest(**fields)


def test_manifest_generated_at_is_utc_iso8601():
    manifest = _manifest()
    parsed = datetime.fromisoformat(manifest.generated_at)
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_manifest_generated_at_is_not_shared_between_instances():
    """``default_factory`` must produce a fresh timestamp, not a shared default."""
    first = _manifest().generated_at
    second = _manifest().generated_at
    assert isinstance(first, str) and isinstance(second, str)
    # Both parse; they are independent values rather than one frozen default.
    datetime.fromisoformat(first)
    datetime.fromisoformat(second)


def test_manifest_holds_prompt_items_and_round_trips():
    manifest = _manifest(
        total_prompts=2,
        prompts=[_item(id="P001"), _item(id="P002", label="Banana")],
    )
    assert [p.id for p in manifest.prompts] == ["P001", "P002"]

    restored = CurioKraftPromptManifest.model_validate(manifest.model_dump())
    assert restored == manifest
    assert restored.prompts[1].label == "Banana"


def test_manifest_rejects_malformed_prompt_entry():
    with pytest.raises(ValidationError):
        _manifest(total_prompts=1, prompts=[{"id": "P001"}])  # missing required fields


# ----------------------------------------------------------------------
# Package re-exports
# ----------------------------------------------------------------------


def test_package_reexports_model_classes():
    assert schemas.PromptItem is PromptItem
    assert schemas.PromptDefaults is PromptDefaults
    assert schemas.CurioKraftPromptManifest is CurioKraftPromptManifest
    assert set(schemas.__all__) == {
        "CurioKraftPromptManifest",
        "PromptItem",
        "PromptDefaults",
    }
