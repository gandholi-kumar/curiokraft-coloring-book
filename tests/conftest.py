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


@pytest.fixture
def sandbox_cwd(tmp_path, monkeypatch):
    """Run a test with the process cwd redirected to a temp directory.

    Every default path in ``curiokraft_book.constants`` is relative to the cwd
    (``output/pipeline_state.json``, ``manifest/pages.json``, ...), so pipeline
    integration tests must chdir or they will write into the repository.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path
