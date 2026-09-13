"""Integration test: pipeline state persistence and crash recovery."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from curiokraft_book.orchestrator.state_manager import PageStatus, PipelineStateManager

pytestmark = pytest.mark.integration

_MANIFEST_PAGES = [
    ("P005", 5, "Fruits", "banana", "BANANA"),
    ("P006", 6, "Fruits", "cherry", "CHERRY"),
    ("P007", 7, "Nature", "flower", "FLOWER"),
]


def _manifest(tmp_path: Path) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "book_title": "STATE MINI",
                "total_pages": len(_MANIFEST_PAGES),
                "pages": [
                    {
                        "page_id": pid,
                        "page_number": num,
                        "section": section,
                        "canonical_object": canonical,
                        "display_label": label,
                        "type": "coloring_page",
                    }
                    for pid, num, section, canonical, label in _MANIFEST_PAGES
                ],
            }
        ),
        encoding="utf-8",
    )
    return p


def test_fresh_init_registers_every_manifest_page(tmp_path: Path):
    state_file = tmp_path / "state" / "pipeline_state.json"
    mgr = PipelineStateManager(state_file_path=state_file, manifest_path=_manifest(tmp_path))

    assert sorted(mgr.pages) == ["P005", "P006", "P007"]
    assert mgr.get_page("P005").canonical_object == "banana"
    assert mgr.get_page("P005").display_label == "BANANA"
    assert mgr.get_page("P005").section == "Fruits"
    assert mgr.get_page("P005").status == PageStatus.PLANNED

    summary = mgr.get_summary()
    assert summary[PageStatus.PLANNED.value] == 3
    assert summary[PageStatus.APPROVED.value] == 0

    assert state_file.exists()
    on_disk = json.loads(state_file.read_text(encoding="utf-8"))
    assert on_disk["total_pages"] == 3


def test_state_survives_a_process_restart(tmp_path: Path):
    """A new manager over the same state file sees the persisted lifecycle."""
    state_file = tmp_path / "pipeline_state.json"
    manifest = _manifest(tmp_path)

    first = PipelineStateManager(state_file_path=state_file, manifest_path=manifest)
    first.update_page("P005", status=PageStatus.APPROVED, qa_passed=True, qa_score=100.0)
    first.update_page("P006", status=PageStatus.RESCUED, rescued_image_path="temp_rescued_006.png")
    first.update_page("P007", status=PageStatus.FAILED, violations=["Margin Violation"])

    # Simulate a crash + restart: a brand new manager, no shared memory
    recovered = PipelineStateManager(state_file_path=state_file, manifest_path=manifest)

    assert recovered.get_page("P005").status == PageStatus.APPROVED
    assert recovered.get_page("P005").qa_passed is True
    assert recovered.get_page("P005").qa_score == 100.0
    assert recovered.get_page("P006").status == PageStatus.RESCUED
    assert recovered.get_page("P006").rescued_image_path == "temp_rescued_006.png"
    assert recovered.get_page("P007").status == PageStatus.FAILED
    assert recovered.get_page("P007").violations == ["Margin Violation"]

    assert [p.page_id for p in recovered.get_pages_by_status(PageStatus.APPROVED)] == ["P005"]
    assert recovered.get_summary()[PageStatus.PLANNED.value] == 0
    assert recovered.get_summary()[PageStatus.FAILED.value] == 1


def test_partial_state_file_is_merged_with_the_manifest(tmp_path: Path):
    """Pages missing from the persisted state are re-registered as PLANNED."""
    state_file = tmp_path / "pipeline_state.json"
    manifest = _manifest(tmp_path)

    seeded = PipelineStateManager(state_file_path=state_file, manifest_path=manifest)
    seeded.update_page("P006", status=PageStatus.APPROVED)

    # Drop every page except P006 from the persisted file
    on_disk = json.loads(state_file.read_text(encoding="utf-8"))
    on_disk["pages"] = {"P006": on_disk["pages"]["P006"]}
    state_file.write_text(json.dumps(on_disk), encoding="utf-8")

    recovered = PipelineStateManager(state_file_path=state_file, manifest_path=manifest)

    assert recovered.get_page("P006").status == PageStatus.APPROVED  # preserved
    assert recovered.get_page("P005").status == PageStatus.PLANNED  # rebuilt
    assert recovered.get_page("P007").status == PageStatus.PLANNED


def test_corrupt_state_file_falls_back_to_the_manifest(tmp_path: Path):
    """A truncated JSON state file does not abort the run — it is rebuilt."""
    state_file = tmp_path / "pipeline_state.json"
    state_file.write_text('{"pages": {"P005": ', encoding="utf-8")

    mgr = PipelineStateManager(state_file_path=state_file, manifest_path=_manifest(tmp_path))

    assert sorted(mgr.pages) == ["P005", "P006", "P007"]
    assert all(p.status == PageStatus.PLANNED for p in mgr.pages.values())
    # and the file is repaired on the write that follows
    assert json.loads(state_file.read_text(encoding="utf-8"))["total_pages"] == 3


def test_update_page_rejects_unknown_page_ids(tmp_path: Path):
    mgr = PipelineStateManager(
        state_file_path=tmp_path / "state.json", manifest_path=_manifest(tmp_path)
    )

    with pytest.raises(KeyError, match="P999"):
        mgr.update_page("P999", status=PageStatus.APPROVED)


def test_manager_without_a_manifest_starts_empty(tmp_path: Path):
    mgr = PipelineStateManager(
        state_file_path=tmp_path / "state.json", manifest_path=tmp_path / "no_manifest.json"
    )

    assert mgr.pages == {}
    assert mgr.get_page("P005") is None
    assert mgr.get_pages_by_status(PageStatus.PLANNED) == []
