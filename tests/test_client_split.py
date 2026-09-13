"""Tests for the ModelClient -> focused-clients split (Item #6, ISP)."""

import warnings
from unittest import mock

import pytest
from PIL import Image

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


# --- ImageGenerator coverage extensions ---------------------------------------


def test_image_generator_inbox_mode():
    gen = ImageGenerator()
    dummy_img = Image.new("L", (2550, 3300), 255)
    with mock.patch(
        "curiokraft_book.orchestrator.image_generator.DiskInboxProvider.generate",
        return_value=dummy_img,
    ):
        res = gen.generate("cute dog", source_mode="inbox", page_id="P001")
        assert res.size == (2550, 3300)


def test_image_generator_auto_finds_inbox_image(tmp_path):
    gen = ImageGenerator()
    img_file = tmp_path / "raw_page.png"
    Image.new("L", (2550, 3300), 255).save(img_file)
    with mock.patch(
        "curiokraft_book.orchestrator.image_generator.DiskInboxProvider.find_image",
        return_value=img_file,
    ):
        res = gen.generate("cute dog", source_mode="auto", page_id="P001", force_fresh=False)
        assert res.size == (2550, 3300)


def test_image_generator_openai_mode_mocked(monkeypatch):
    gen = ImageGenerator(provider="openai")
    dummy_img = Image.new("L", (2550, 3300), 255)
    mock_prov = mock.MagicMock()
    mock_prov.generate.return_value = dummy_img
    monkeypatch.setattr(
        "curiokraft_book.orchestrator.image_generator.OpenAIImageProvider",
        lambda: mock_prov,
    )
    monkeypatch.setattr(
        "curiokraft_book.orchestrator.image_generator.GeminiImageProvider",
        lambda: mock_prov,
    )
    res = gen.generate("cute dog", source_mode="openai")
    assert res.size == (2550, 3300)


def test_image_generator_openai_error_raises_in_openai_mode(monkeypatch):
    gen = ImageGenerator(provider="openai")
    mock_prov = mock.MagicMock()
    mock_prov.generate.side_effect = RuntimeError("quota")
    monkeypatch.setattr(
        "curiokraft_book.orchestrator.image_generator.OpenAIImageProvider",
        lambda: mock_prov,
    )
    monkeypatch.setattr(
        "curiokraft_book.orchestrator.image_generator.GeminiImageProvider",
        lambda: mock_prov,
    )
    with pytest.raises(RuntimeError, match="quota"):
        gen.generate("cute dog", source_mode="openai")


def test_image_generator_gemini_mode_mocked(monkeypatch):
    gen = ImageGenerator(provider="gemini")
    dummy_img = Image.new("L", (2550, 3300), 255)
    mock_prov = mock.MagicMock()
    mock_prov.generate.return_value = dummy_img
    monkeypatch.setattr(
        "curiokraft_book.orchestrator.image_generator.OpenAIImageProvider",
        lambda: mock_prov,
    )
    monkeypatch.setattr(
        "curiokraft_book.orchestrator.image_generator.GeminiImageProvider",
        lambda: mock_prov,
    )
    res = gen.generate("cute dog", source_mode="gemini")
    assert res.size == (2550, 3300)


def test_image_generator_gemini_error_raises_in_gemini_mode(monkeypatch):
    gen = ImageGenerator(provider="gemini")
    mock_prov = mock.MagicMock()
    mock_prov.generate.side_effect = RuntimeError("gemini down")
    monkeypatch.setattr(
        "curiokraft_book.orchestrator.image_generator.OpenAIImageProvider",
        lambda: mock_prov,
    )
    monkeypatch.setattr(
        "curiokraft_book.orchestrator.image_generator.GeminiImageProvider",
        lambda: mock_prov,
    )
    with pytest.raises(RuntimeError, match="gemini down"):
        gen.generate("cute dog", source_mode="gemini")


def test_image_generator_auto_with_env_keys_fallback(monkeypatch):
    gen = ImageGenerator()
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    mock_prov = mock.MagicMock()
    mock_prov.generate.side_effect = Exception("api err")
    monkeypatch.setattr(
        "curiokraft_book.orchestrator.image_generator.OpenAIImageProvider",
        lambda: mock_prov,
    )
    monkeypatch.setattr(
        "curiokraft_book.orchestrator.image_generator.GeminiImageProvider",
        lambda: mock_prov,
    )
    res = gen.generate("cute dog", source_mode="auto")
    assert res.size == (2550, 3300)


# --- VisionClient coverage extensions ----------------------------------------


def test_vision_client_gemini_success_json(tmp_path, monkeypatch):
    img_path = tmp_path / "test_wireframe.png"
    Image.new("L", (2550, 3300), 255).save(img_path)

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    mock_model = mock.MagicMock()
    mock_resp = mock.MagicMock()
    mock_resp.text = '{"quality": "high", "objects": ["cat"]}'
    mock_model.generate_content.return_value = mock_resp

    with (
        mock.patch("google.generativeai.GenerativeModel", return_value=mock_model),
        mock.patch("google.generativeai.configure"),
    ):
        client = VisionClient()
        resp = client.call_vision("sys", "analyze", img_path, response_schema=dict)
        assert resp.parsed_json == {"quality": "high", "objects": ["cat"]}
        assert resp.model_name == "gemini-1.5-flash"


def test_vision_client_gemini_plain_text_response(tmp_path, monkeypatch):
    img_path = tmp_path / "test_wireframe.png"
    Image.new("L", (2550, 3300), 255).save(img_path)

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    mock_model = mock.MagicMock()
    mock_resp = mock.MagicMock()
    mock_resp.text = "Just plain text description"
    mock_model.generate_content.return_value = mock_resp

    with (
        mock.patch("google.generativeai.GenerativeModel", return_value=mock_model),
        mock.patch("google.generativeai.configure"),
    ):
        client = VisionClient()
        resp = client.call_vision("sys", "analyze", img_path)
        assert resp.parsed_json is None
        assert resp.content == "Just plain text description"


def test_vision_client_gemini_error_falls_back_to_spatial(tmp_path, monkeypatch):
    img_path = tmp_path / "test_wireframe.png"
    Image.new("L", (2550, 3300), 255).save(img_path)

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    mock_model = mock.MagicMock()
    mock_model.generate_content.side_effect = RuntimeError("network err")

    with (
        mock.patch("google.generativeai.GenerativeModel", return_value=mock_model),
        mock.patch("google.generativeai.configure"),
    ):
        client = VisionClient()
        resp = client.call_vision("sys", "analyze", img_path)
        assert resp.model_name == "curiokraft-spatial-analyzer"


def test_vision_client_simulate_front_cover_and_corrupt(tmp_path):
    client = VisionClient()
    front_path = tmp_path / "front_cover.png"
    Image.new("L", (2550, 3300), 255).save(front_path)
    resp_front = client._simulate_vision_analysis(front_path, "prompt")
    assert resp_front.parsed_json["blueprint_type"] == "cover"

    corrupt_path = tmp_path / "corrupt.png"
    corrupt_path.write_bytes(b"not an image")
    resp_corrupt = client._simulate_vision_analysis(corrupt_path, "prompt")
    assert resp_corrupt.parsed_json["canvas_dimensions"] == {
        "width": 2550,
        "height": 3300,
        "aspect_ratio": 0.772,
    }


# --- LLMClient coverage extensions -------------------------------------------


def test_llm_client_mock_agent_roles():
    client = LLMClient(provider="mock")
    resp_prompt = client.call_agent("AGT-008 Prompt Engineer", "prompt")
    assert "positive_prompt" in resp_prompt.parsed_json

    resp_vqa = client.call_agent("AGT-009 Vision QA", "qa")
    assert resp_vqa.parsed_json["verdict"] == "PASS"

    resp_bqa = client.call_agent("AGT-010 Book QA", "audit")
    assert resp_bqa.parsed_json["audit_verdict"] == "PASSED"

    resp_spec = client.call_agent("AGT-001 Research Specialist", "research")
    assert resp_spec.parsed_json["agent_id"] == "SPECIALIST"


def test_llm_client_unsupported_provider():
    client = LLMClient(provider="mock")
    client.provider = "unsupported_provider"
    with pytest.raises(ValueError, match="Unsupported provider"):
        client.call_agent("sys", "user")


def test_llm_client_openai_call_mocked():
    mock_openai_client = mock.MagicMock()
    mock_completion = mock.MagicMock()
    mock_choice = mock.MagicMock()
    mock_choice.message.content = '{"decision": "APPROVED"}'
    mock_completion.choices = [mock_choice]
    mock_completion.usage.prompt_tokens = 10
    mock_completion.usage.completion_tokens = 20
    mock_openai_client.chat.completions.create.return_value = mock_completion

    with mock.patch("openai.OpenAI", return_value=mock_openai_client):
        client = LLMClient(provider="openai")
        resp = client.call_agent("sys", "user")
        assert resp.parsed_json == {"decision": "APPROVED"}
        assert resp.prompt_tokens == 10
        assert resp.completion_tokens == 20


def test_llm_client_anthropic_call_mocked():
    mock_anthropic_client = mock.MagicMock()
    mock_msg = mock.MagicMock()
    mock_block = mock.MagicMock()
    mock_block.text = '{"decision": "APPROVED"}'
    mock_msg.content = [mock_block]
    mock_msg.usage.input_tokens = 12
    mock_msg.usage.output_tokens = 22
    mock_anthropic_client.messages.create.return_value = mock_msg

    with mock.patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        client = LLMClient(provider="anthropic")
        resp = client.call_agent("sys", "user")
        assert resp.parsed_json == {"decision": "APPROVED"}
        assert resp.prompt_tokens == 12
        assert resp.completion_tokens == 22


def test_llm_client_gemini_call_mocked(monkeypatch):
    mock_model = mock.MagicMock()
    mock_resp = mock.MagicMock()
    mock_resp.text = '{"gemini": "reply"}'
    mock_model.generate_content.return_value = mock_resp

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with (
        mock.patch("google.generativeai.GenerativeModel", return_value=mock_model),
        mock.patch("google.generativeai.configure"),
    ):
        client = LLMClient(provider="gemini")
        resp = client.call_agent("sys", "user")
        assert resp.parsed_json == {"gemini": "reply"}
