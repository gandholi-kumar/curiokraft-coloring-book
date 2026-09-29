"""Tests for curiokraft-book db CLI commands."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from curiokraft_book.cli_db import db_app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolate_cli_db_env(monkeypatch):
    """Ensure all CLI tests run strictly in-memory or on local isolated paths."""
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.delenv("S3_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("S3_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("REMOTE_DATABASE_URL", raising=False)
    monkeypatch.delenv("CLOUD_DATABASE_URL", raising=False)
    monkeypatch.delenv("CLOUD_S3_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("CLOUD_S3_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("CLOUD_S3_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("CLOUD_S3_BUCKET_NAME", raising=False)


def test_cli_db_init_and_status(tmp_path: Path, monkeypatch):
    """Test 'curiokraft-book db init' and 'curiokraft-book db status' with isolated DB."""
    db_file = tmp_path / "cli_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("STORAGE_BACKEND", "local")

    # 1. db init
    result_init = runner.invoke(db_app, ["init"])
    assert result_init.exit_code == 0
    assert (
        "initialized successfully" in result_init.stdout or "Schema verified" in result_init.stdout
    )

    # 2. db status
    result_status = runner.invoke(db_app, ["status"])
    assert result_status.exit_code == 0
    assert "Database Status" in result_status.stdout


def test_cli_db_migrate_and_export(tmp_path: Path, monkeypatch):
    """Test 'migrate-from-fs' and 'export-to-fs' CLI commands."""
    db_file = tmp_path / "cli_migrate_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")

    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(
        json.dumps(
            {
                "manifest_version": "1.0",
                "pages": [
                    {
                        "page_id": "P001",
                        "page_number": 1,
                        "canonical_object": "starfish",
                        "display_label": "STARFISH",
                        "section": "Tidal Pools",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    state_file = tmp_path / "state.json"
    state_file.write_text(
        json.dumps(
            {
                "total_pages": 1,
                "pages": {
                    "P001": {
                        "page_id": "P001",
                        "page_number": 1,
                        "canonical_object": "starfish",
                        "display_label": "STARFISH",
                        "section": "Tidal Pools",
                        "status": "APPROVED",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    export_file = tmp_path / "exported_state.json"

    # Migrate from filesystem
    result_migrate = runner.invoke(
        db_app,
        ["migrate-from-fs", "--manifest", str(manifest_file), "--state", str(state_file)],
    )
    assert result_migrate.exit_code == 0
    assert "Migration Complete" in result_migrate.stdout

    # Export to filesystem
    result_export = runner.invoke(
        db_app,
        ["export-to-fs", "--output", str(export_file)],
    )
    assert result_export.exit_code == 0
    assert "Exported" in result_export.stdout
    assert export_file.exists()


def test_cli_db_sync_command(tmp_path: Path, monkeypatch):
    """Test 'db sync' when remote URL is not configured."""
    db_file = tmp_path / "cli_sync_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.delenv("REMOTE_DATABASE_URL", raising=False)

    result_sync = runner.invoke(db_app, ["sync"])
    assert result_sync.exit_code == 1
    assert (
        "Sync encountered errors" in result_sync.stdout
        or "Remote database URL not configured" in result_sync.stdout
    )


def test_cli_db_cloud_status_unconfigured():
    """Test 'curiokraft-book db cloud-status' when cloud DB is not configured."""
    result = runner.invoke(db_app, ["cloud-status"])
    assert result.exit_code == 1
    assert (
        "Cloud target (Neon) not configured" in result.stdout or "not configured" in result.stdout
    )


def test_cli_db_push_to_cloud_unconfigured():
    """Test 'curiokraft-book db push-to-cloud' when cloud is not configured."""
    result = runner.invoke(db_app, ["push-to-cloud"])
    assert result.exit_code == 1
    assert "Cloud configuration missing or unreachable" in result.stdout


def test_cli_db_cloud_status_and_push_configured(tmp_path: Path, monkeypatch):
    """Test 'cloud-status' and 'push-to-cloud' with isolated local and cloud DBs."""
    from curiokraft_book.data.postgres_store import SQLDatabaseManager

    local_db = tmp_path / "cli_local.db"
    cloud_db = tmp_path / "cli_cloud.db"

    # Initialize both databases
    SQLDatabaseManager(f"sqlite:///{local_db}").init_db()
    SQLDatabaseManager(f"sqlite:///{cloud_db}").init_db()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{local_db}")
    monkeypatch.setenv("CLOUD_DATABASE_URL", f"sqlite:///{cloud_db}")
    monkeypatch.setenv("CLOUD_S3_ENDPOINT_URL", "https://s3.us-east-005.backblazeb2.com")
    monkeypatch.setenv("CLOUD_S3_ACCESS_KEY_ID", "test_key_id")
    monkeypatch.setenv("CLOUD_S3_SECRET_ACCESS_KEY", "test_secret")
    monkeypatch.setenv("CLOUD_S3_BUCKET_NAME", "curiokraft-assets")

    # 1. Test cloud-status
    res_status = runner.invoke(db_app, ["cloud-status"])
    assert res_status.exit_code == 0
    assert "Local vs Cloud Catalog Status" in res_status.stdout

    # 2. Test push-to-cloud dry run with active volume
    res_push = runner.invoke(db_app, ["push-to-cloud", "--dry-run"])
    assert res_push.exit_code == 0
    assert "Promotion Succeeded" in res_push.stdout or "DRY-RUN" in res_push.stdout

    # 3. Test push-to-cloud --all
    res_push_all = runner.invoke(db_app, ["push-to-cloud", "--all", "--dry-run"])
    assert res_push_all.exit_code == 0

    # 4. Test push-to-cloud with unknown slug
    res_push_unknown = runner.invoke(db_app, ["push-to-cloud", "--slug", "non-existent-book"])
    assert res_push_unknown.exit_code == 1
    assert "Promotion Failed" in res_push_unknown.stdout
