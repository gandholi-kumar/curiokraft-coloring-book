"""Integration test: the Typer CLI surface driven in-process.

``cli.py`` is excluded from coverage, so these tests exist for behavioural
protection — they assert the commands wired to the pipeline actually run.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from curiokraft_book.cli import app

pytestmark = pytest.mark.integration

runner = CliRunner()


def _manifest(tmp_path: Path) -> Path:
    p = tmp_path / "cli_manifest.json"
    p.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "book_title": "CLI MINI",
                "total_pages": 1,
                "pages": [
                    {
                        "page_id": "P005",
                        "page_number": 5,
                        "section": "Fruits",
                        "canonical_object": "banana",
                        "display_label": "BANANA",
                        "type": "coloring_page",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return p


def test_root_help_lists_the_production_stages():
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ["init", "doctor", "ingest", "process-raw"]:
        assert command in result.output
    for group in ["generate", "cover", "preflight", "kdp"]:
        assert group in result.output


def test_init_scaffolds_the_workspace(sandbox_cwd: Path):
    result = runner.invoke(app, ["init", "--name", "MY TEST BOOK", "--imprint", "TEST IMPRINT"])

    assert result.exit_code == 0
    assert "MY TEST BOOK" in result.output

    for directory in [
        "config",
        "manifest",
        "output/interior_masters",
        "output/reports",
        "inbox/raw_pages",
        "generated/raw_pages",
        "assets/fonts",
    ]:
        assert (sandbox_cwd / directory).is_dir(), f"missing {directory}"

    # Drop-in instructions are scaffolded for the human-supplied assets
    assert (sandbox_cwd / "inbox/raw_pages/README.md").exists()
    assert (sandbox_cwd / "assets/fonts/README.md").exists()


def test_init_is_idempotent(sandbox_cwd: Path):
    """Re-running init must not clobber a user's inbox notes."""
    note = sandbox_cwd / "inbox/raw_pages/README.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("my own notes", encoding="utf-8")

    assert runner.invoke(app, ["init"]).exit_code == 0
    assert note.read_text(encoding="utf-8") == "my own notes"


def test_doctor_reports_workspace_health(sandbox_cwd: Path):
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "Workspace Health Check" in result.output
    # The brand logo is absent in a fresh workspace, so the fallback path is taken
    assert "FALLBACK" in result.output


def test_manifest_status_reports_the_lifecycle_table(sandbox_cwd: Path):
    result = runner.invoke(app, ["manifest", "status"])

    assert result.exit_code == 0
    assert "110-Page Pipeline Lifecycle Status" in result.output


def test_prompt_show_prints_a_copy_ready_prompt(tmp_path: Path):
    manifest = _manifest(tmp_path)

    result = runner.invoke(app, ["prompt", "show", "--page", "P005", "--manifest", str(manifest)])

    assert result.exit_code == 0
    assert "BANANA" in result.output
    assert "Negative Prompt" in result.output
    assert "raw_p005_banana.png" in result.output


def test_prompt_show_rejects_a_missing_manifest(tmp_path: Path):
    result = runner.invoke(app, ["prompt", "show", "--manifest", str(tmp_path / "absent.json")])

    assert result.exit_code == 1
    assert "Manifest not found" in result.output


def test_prompt_show_rejects_an_unknown_page(tmp_path: Path):
    manifest = _manifest(tmp_path)

    result = runner.invoke(app, ["prompt", "show", "--page", "P999", "--manifest", str(manifest)])

    assert result.exit_code == 1
    assert "not found in manifest" in result.output


def test_manifest_audit_verifies_the_shipped_registry():
    """Runs against the repository's real ``manifest/objects.json``."""
    objects_registry = Path(__file__).resolve().parents[1] / "manifest" / "objects.json"
    assert objects_registry.exists(), f"missing production registry: {objects_registry}"

    cwd = Path.cwd()
    result = runner.invoke(app, ["manifest", "audit"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "Semantic Object Registry Status" in result.output
    assert "VERIFIED ZERO DUPLICATES" in result.output
    assert Path.cwd() == cwd  # the command must not relocate the process
