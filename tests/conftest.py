import types

import pytest


@pytest.fixture(autouse=True)
def _no_live_image_api(monkeypatch):
    """Fail if any test reaches a live image provider.

    Records hits and asserts AFTER the test: auto mode swallows the provider
    exception and falls back to the mock, so raising here would be swallowed too.
    """
    hits: list[str] = []

    def _record(name):
        def _generate(*args, **kwargs):
            hits.append(name)
            raise RuntimeError(f"{name} called")

        return lambda: types.SimpleNamespace(generate=_generate)

    monkeypatch.setattr(
        "curiokraft_book.orchestrator.image_generator.GeminiImageProvider", _record("Gemini")
    )
    monkeypatch.setattr(
        "curiokraft_book.orchestrator.image_generator.OpenAIImageProvider", _record("OpenAI")
    )
    yield
    assert not hits, f"test reached a live image API: {hits}; pass source_mode='mock'"


@pytest.fixture(autouse=True)
def _isolate_database_and_storage(monkeypatch, tmp_path):
    """Ensure tests are strictly isolated from production DB and cloud S3."""
    db_file = tmp_path / "test_suite_isolated.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.delenv("REMOTE_DATABASE_URL", raising=False)
    monkeypatch.delenv("S3_ENDPOINT_URL", raising=False)
    import contextlib

    with contextlib.suppress(Exception):
        from curiokraft_book.data.hybrid_store import reset_global_data_store

        reset_global_data_store()
    yield
    with contextlib.suppress(Exception):
        from curiokraft_book.data.hybrid_store import reset_global_data_store

        reset_global_data_store()


@pytest.fixture
def sandbox_cwd(tmp_path, monkeypatch):
    """Run a test with the process cwd redirected to a temp directory.

    Every default path in ``curiokraft_book.constants`` is relative to the cwd
    (``output/pipeline_state.json``, ``manifest/pages.json``, ...), so pipeline
    integration tests must chdir or they will write into the repository.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path
