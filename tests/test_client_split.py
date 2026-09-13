"""Tests for the ModelClient -> focused-clients split (Item #6, ISP)."""

import warnings

import pytest

from curiokraft_book.orchestrator.image_generator import ImageGenerator
from curiokraft_book.orchestrator.llm_client import LLMClient
from curiokraft_book.orchestrator.providers import (
    DEFAULT_TEXT_MODELS,
    OFFLINE_MODEL_NAME,
    resolve_provider_and_model,
)
from curiokraft_book.orchestrator.vision_client import VisionClient

# --- Interface segregation ---------------------------------------------------


def test_llm_client_exposes_only_text_generation():
    client = LLMClient(provider="mock")
    assert hasattr(client, "call_agent")
    assert not hasattr(client, "call_vision")
    assert not hasattr(client, "generate")
    assert not hasattr(client, "generate_illustration")


def test_vision_client_exposes_only_image_analysis():
    client = VisionClient()
    assert hasattr(client, "call_vision")
    assert not hasattr(client, "call_agent")
    assert not hasattr(client, "generate")
    assert not hasattr(client, "generate_illustration")


def test_image_generator_exposes_only_image_creation():
    gen = ImageGenerator()
    assert hasattr(gen, "generate")
    assert not hasattr(gen, "call_agent")
    assert not hasattr(gen, "call_vision")


# --- Functional behaviour on the offline path -------------------------------


def test_llm_client_mock_returns_structured_response():
    client = LLMClient(provider="mock")
    resp = client.call_agent("AGT-007 Judge", "decide")
    assert resp.model_name == OFFLINE_MODEL_NAME
    assert resp.parsed_json is not None
    assert resp.parsed_json["decision"] == "APPROVED"


def test_vision_client_falls_back_to_spatial_analyzer(tmp_path, monkeypatch):
    from PIL import Image

    img_path = tmp_path / "back_cover_blueprint.png"
    Image.new("L", (2550, 3300), 255).save(img_path)

    # Construct first: VisionClient.__init__ calls load_env_file(), which would
    # otherwise re-populate the key we clear below.
    client = VisionClient()

    # Force the offline path regardless of ambient API keys.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    resp = client.call_vision("system", "analyze this layout", img_path)
    assert resp.model_name == "curiokraft-spatial-analyzer"
    assert resp.parsed_json["blueprint_type"] == "back_cover"


def test_vision_client_missing_file_raises():
    client = VisionClient()
    with pytest.raises(FileNotFoundError):
        client.call_vision("sys", "user", "does/not/exist.png")


def test_image_generator_mock_renders_page():
    gen = ImageGenerator(provider="mock")
    img = gen.generate("cute apple", canonical_label="apple", section="Fruits", source_mode="mock")
    assert img.size == (2550, 3300)
    assert img.mode == "L"


def test_image_generator_illustration_alias_still_works():
    gen = ImageGenerator(provider="mock")
    img = gen.generate_illustration("cute pear", canonical_label="pear", source_mode="mock")
    assert img.size == (2550, 3300)


# --- Provider resolution -----------------------------------------------------


def test_resolve_provider_explicit():
    assert resolve_provider_and_model("openai") == ("openai", "gpt-4o")
    assert resolve_provider_and_model("gemini", "gemini-2.0") == ("gemini", "gemini-2.0")


def test_resolve_provider_auto_falls_back_to_mock(monkeypatch):
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.delenv("CK_DEFAULT_PROVIDER", raising=False)

    provider, model = resolve_provider_and_model("auto")
    assert provider == "mock"
    assert model == OFFLINE_MODEL_NAME


def test_resolve_provider_auto_prefers_gemini(monkeypatch):
    monkeypatch.delenv("CK_DEFAULT_PROVIDER", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "AIza-fake")
    assert resolve_provider_and_model("auto")[0] == "gemini"


def test_default_text_model_map_covers_known_providers():
    assert set(DEFAULT_TEXT_MODELS) == {"openai", "anthropic", "gemini"}


# --- Backward-compatibility facade -------------------------------------------


def test_model_client_facade_warns_and_delegates():
    from curiokraft_book.orchestrator.model_client import ModelClient

    with pytest.warns(DeprecationWarning, match="Use LLMClient"):
        client = ModelClient(provider="mock")

    assert hasattr(client, "call_agent")
    assert hasattr(client, "call_vision")
    assert hasattr(client, "generate_illustration")
    # Attribute contract preserved for existing callers
    assert client.provider == "mock"
    assert client.model_name == OFFLINE_MODEL_NAME


def test_model_client_facade_delegates_to_focused_clients():
    from curiokraft_book.orchestrator.model_client import ModelClient

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        client = ModelClient(provider="mock")

    assert isinstance(client.llm, LLMClient)
    assert isinstance(client.vision, VisionClient)
    assert isinstance(client.image_gen, ImageGenerator)

    img = client.generate_illustration("cute cat", canonical_label="cat", source_mode="mock")
    assert img.size == (2550, 3300)


def test_model_client_module_reexports_shared_types():
    """Legacy import paths must keep resolving."""
    from curiokraft_book.orchestrator.model_client import (  # noqa: F401
        BaseImageProvider,
        DiskInboxProvider,
        GeminiImageProvider,
        MockImageProvider,
        ModelResponse,
        OpenAIImageProvider,
        load_env_file,
    )

    assert issubclass(GeminiImageProvider, BaseImageProvider)
    assert issubclass(MockImageProvider, BaseImageProvider)
    assert callable(load_env_file)
    assert ModelResponse.__name__ == "ModelResponse"
    assert DiskInboxProvider.provider_name.fget is not None
