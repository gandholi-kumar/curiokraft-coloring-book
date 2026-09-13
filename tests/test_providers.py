"""Unit tests for ``curiokraft_book.orchestrator.providers``."""

import os
import sys
from io import BytesIO
from pathlib import Path
from unittest import mock

import pytest

from curiokraft_book.orchestrator.providers import (
    load_env_file,
    resolve_provider_and_model,
    BaseImageProvider,
    GeminiImageProvider,
    ModelResponse,
    DEFAULT_TEXT_MODELS,
    OFFLINE_MODEL_NAME,
)


def test_load_env_file_does_not_crash_when_dotenv_missing(tmp_path, monkeypatch):
    """If python-dotenv is not installed, the built‑in parser should still run."""
    # Simulate missing dotenv by raising ImportError inside the try block
    monkeypatch.setattr("curiokraft_book.orchestrator.providers.dotenv", None, raising=False)
    # Create a temporary .env file
    env_file = tmp_path / ".env"
    env_file.write_text("TEST_KEY=test_value\n")
    # Point cwd to temp dir
    monkeypatch.setattr("curiokraft_book.orchestrator.providers.Path.cwd", lambda: tmp_path)
    # Call the function – it should not raise
    load_env_file(str(env_file))
    # The variable should have been injected into os.environ
    assert os.environ.get("TEST_KEY") == "test_value"
    # Clean up
    os.environ.pop("TEST_KEY", None)


def test_load_env_file_ignores_bad_lines(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n"
        "# comment\n"
        "KEY1=value1\n"
        "KEY2=value2 with spaces\n"
        "KEY3=\"quoted\"\n"
        "KEY4='single-quoted'\n"
        "BADLINE\n"
        "KEY5=\n"
        "= novalue\n"
    )
    monkeypatch.setattr("curiokraft_book.orchestrator.providers.Path.cwd", lambda: tmp_path)
    load_env_file(str(env_file))
    assert os.environ.get("KEY1") == "value1"
    assert os.environ.get("KEY2") == "value2 with spaces"
    assert os.environ.get("KEY3") == "quoted"
    assert os.environ.get("KEY4") == "single-quoted"
    # BADLINE (no =) should be ignored
    assert os.environ.get("BADLINE") is None
    # KEY5 with empty value should be set to empty string
    assert os.environ.get("KEY5") == ""
    # Cleanup
    for k in ["KEY1", "KEY2", "KEY3", "KEY4", "KEY5"]:
        os.environ.pop(k, None)


def test_resolve_provider_and_model_prefers_env_override():
    """CK_DEFAULT_PROVIDER should win over the auto detection order."""
    with mock.patch.dict(os.environ, {"CK_DEFAULT_PROVIDER": "openai"}):
        prov, model = resolve_provider_and_model("auto")
        assert prov == "openai"
        assert model == DEFAULT_TEXT_MODELS["openai"]


def test_resolve_provider_and_model_auto_detects_gemini():
    with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
        prov, model = resolve_provider_and_model("auto")
        assert prov == "gemini"
        assert model == DEFAULT_TEXT_MODELS["gemini"]


def test_resolve_provider_and_model_auto_detects_openai():
    with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
        prov, model = resolve_provider_and_model("auto")
        assert prov == "openai"
        assert model == DEFAULT_TEXT_MODELS["openai"]


def test_resolve_provider_and_model_auto_detects_anthropic():
    with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=True):
        prov, model = resolve_provider_and_model("auto")
        assert prov == "anthropic"
        assert model == DEFAULT_TEXT_MODELS["anthropic"]


def test_resolve_provider_and_model_falls_back_to_mock():
    with mock.patch.dict(os.environ, {}, clear=True):
        prov, model = resolve_provider_and_model("auto")
        assert prov == "mock"
        assert model == OFFLINE_MODEL_NAME


def test_resolve_provider_and_model_respects_explicit_provider():
    # Even if env says gemini, explicit provider should win
    with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
        prov, model = resolve_provider_and_model("openai")
        assert prov == "openai"
        assert model == DEFAULT_TEXT_MODELS["openai"]


def test_base_image_provider_methods_raise_not_implemented():
    """BaseImageProvider is a plain class whose methods raise NotImplementedError."""
    base = BaseImageProvider()
    with pytest.raises(NotImplementedError):
        _ = base.provider_name
    with pytest.raises(NotImplementedError):
        base.generate("prompt")


def test_gemini_image_provider_raises_without_api_key():
    # Ensure no Gemini key in environment
    with mock.patch.dict(os.environ, {}, clear=True):
        provider = GeminiImageProvider()
        with pytest.raises(ValueError, match="GEMINI_API_KEY is not set"):
            provider.generate("prompt")


def test_gemini_image_provider_generate_mocks_success(monkeypatch):
    """Monkeypatch the google-genai SDK to return a fake image."""
    import base64

    from PIL import Image

    # Build real PNG bytes for a small grayscale image
    buf = BytesIO()
    Image.new("L", (10, 10), color=255).save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")

    class _OutputImage:
        data = encoded

    class _Interaction:
        output_image = _OutputImage()

    class _Client:
        def __init__(self, api_key=None):
            pass

        class interactions:  # noqa: N801 - mirrors SDK shape
            @staticmethod
            def create(model, input):  # noqa: A002 - mirrors SDK kwarg
                return _Interaction()

    fake_genai = mock.MagicMock()
    fake_genai.Client = _Client

    fake_google = mock.MagicMock()
    fake_google.genai = fake_genai

    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)

    with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
        provider = GeminiImageProvider()
        result = provider.generate("test prompt")
        assert result.mode == "L"
        assert result.size == (10, 10)


def test_model_response_defaults():
    resp = ModelResponse(content="hello", model_name="test-model")
    assert resp.content == "hello"
    assert resp.model_name == "test-model"
    assert resp.parsed_json is None
    assert resp.prompt_tokens == 0
    assert resp.completion_tokens == 0


def test_model_response_accepts_extra_fields():
    resp = ModelResponse(
        content="hello",
        model_name="test-model",
        parsed_json={"key": "value"},
        prompt_tokens=7,
        completion_tokens=3,
    )
    assert resp.parsed_json == {"key": "value"}
    assert resp.prompt_tokens == 7
    assert resp.completion_tokens == 3