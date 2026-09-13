"""Text-generation client (Interface Segregation).

Owns exactly one responsibility: turning a system+user prompt pair into a
:class:`~curiokraft_book.orchestrator.providers.ModelResponse` via a chat LLM.
Image analysis lives in :mod:`vision_client`; image creation lives in
:mod:`image_generator`.
"""

import json
import logging
import os
from typing import Any

from pydantic import BaseModel

from curiokraft_book.orchestrator.providers import (
    ModelResponse,
    load_env_file,
    resolve_provider_and_model,
)

logger = logging.getLogger("curiokraft.llm_client")


class LLMClient:
    """Executes agent prompts against a text LLM provider.

    Supported providers: ``openai``, ``anthropic``, ``gemini``, ``mock``
    (deterministic offline simulator) and ``auto``.
    """

    def __init__(self, provider: str = "auto", model_name: str | None = None):
        """
        Args:
            provider: 'openai' | 'anthropic' | 'gemini' | 'mock' | 'auto'.
            model_name: Specific model ID; provider default when omitted.
        """
        load_env_file()
        self.provider, self.model_name = resolve_provider_and_model(provider, model_name)
        logger.info(f"Initialized LLMClient with provider: {self.provider} ({self.model_name})")

    def call_agent(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[BaseModel] | None = None,
        temperature: float = 0.2,
    ) -> ModelResponse:
        """Execute an agent prompt and return structured response.

        Args:
            system_prompt: The agent's authoritative system prompt.
            user_prompt: The specific task/context payload.
            response_schema: Optional Pydantic model for JSON validation.
            temperature: Sampling temperature (default: 0.2 for deterministic output).

        Returns:
            ModelResponse containing raw text and parsed JSON.
        """
        if self.provider == "mock":
            return self._mock_call(system_prompt, user_prompt, response_schema)
        elif self.provider == "openai":
            return self._call_openai(system_prompt, user_prompt, response_schema, temperature)
        elif self.provider == "anthropic":
            return self._call_anthropic(system_prompt, user_prompt, response_schema, temperature)
        elif self.provider == "gemini":
            return self._call_gemini(system_prompt, user_prompt, response_schema, temperature)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _mock_call(
        self, system_prompt: str, user_prompt: str, response_schema: type[BaseModel] | None
    ) -> ModelResponse:
        """Deterministic offline mock simulator for pipeline testing without API credits."""
        # Detect agent role from system prompt
        if "AGT-007" in system_prompt or "Judge" in system_prompt:
            mock_payload = {
                "decision": "APPROVED",
                "final_score": 96.5,
                "winner_agent": "AGT-002-DESIGN",
                "hybrid_specification": {
                    "canonical_object": "apple",
                    "composition": "single_centered_large",
                    "line_art_style": "bold_clean_2d_vector",
                    "stroke_weight_pt": 6.0,
                    "prohibited_elements": ["shading", "gradients", "color", "background"],
                },
                "judge_notes": "Synthesized optimal bold outline with conservative 0.50in margin clearance.",
            }
        elif "AGT-008" in system_prompt or "Prompt Engineer" in system_prompt:
            mock_payload = {
                "page_id": "P005",
                "positive_prompt": (
                    "Ultra clean bold 2D coloring book page for toddlers aged 1-4, a single cute simple BANANA, "
                    "centered in frame, stark pure black outline, thick 5pt stroke, pure stark white background #FFFFFF, "
                    "zero shading, zero gradients, zero grayscale, zero texture, wide open coloring areas, coloring book style."
                ),
                "negative_prompt": (
                    "shading, gradients, gray, grayscale, color, textures, 3d, realistic, complex details, multiple objects, "
                    "background scenery, text, letters, watermarks, frames, borders, thin lines, cross-hatching"
                ),
                "aspect_ratio": "8.5:11",
                "safety_tokens": [
                    "pure black and white",
                    "no shading",
                    "single object",
                    "toddler coloring book",
                ],
            }
        elif "AGT-009" in system_prompt or "Vision QA" in system_prompt:
            mock_payload = {
                "verdict": "PASS",
                "overall_score": 98.0,
                "scores": {
                    "visual_simplicity": 100,
                    "line_weight_consistency": 95,
                    "zero_shading_compliance": 100,
                    "single_object_focus": 100,
                    "toddler_suitability": 95,
                },
                "anomalies_detected": [],
                "recommendation": "APPROVED_FOR_MASTER_COMPOSITING",
            }
        elif "AGT-010" in system_prompt or "Book QA" in system_prompt:
            mock_payload = {
                "audit_verdict": "PASSED",
                "overall_book_readiness_score": 99.5,
                "duplicate_count": 0,
                "style_cohesion_score": 98,
                "kdp_compliance_score": 100,
                "ready_for_press": True,
                "summary": "110 pages audited with 0 duplicates, pristine line weight cohesion, and 100% KDP compliance.",
            }
        else:
            mock_payload = {
                "agent_id": "SPECIALIST",
                "status": "PROPOSAL_READY",
                "confidence_score": 95.0,
                "recommendation": "Follow master blueprint parameters.",
            }

        return ModelResponse(
            content=json.dumps(mock_payload, indent=2),
            parsed_json=mock_payload,
            model_name="curiokraft-offline-simulator",
            prompt_tokens=150,
            completion_tokens=80,
        )

    def _call_openai(
        self, system_prompt: str, user_prompt: str, response_schema: Any, temp: float
    ) -> ModelResponse:
        import openai

        client = openai.OpenAI()
        messages: list[Any] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        call_kwargs: dict[str, Any] = {
            "model": self.model_name or "gpt-4o",
            "messages": messages,
            "temperature": temp,
        }
        if response_schema:
            call_kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**call_kwargs)
        content = resp.choices[0].message.content or ""
        parsed = None
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            # Response is plain text or invalid JSON; keep parsed as None
            pass
        return ModelResponse(
            content=content,
            parsed_json=parsed,
            model_name=str(self.model_name or "gpt-4o"),
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
        )

    def _call_anthropic(
        self, system_prompt: str, user_prompt: str, response_schema: Any, temp: float
    ) -> ModelResponse:
        import anthropic

        client = anthropic.Anthropic()
        call_kwargs: dict[str, Any] = {
            "model": self.model_name or "claude-3-5-sonnet-20240620",
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": temp,
        }
        resp = client.messages.create(**call_kwargs)
        first_content = resp.content[0] if resp.content else None
        content = getattr(first_content, "text", "") if first_content else ""
        parsed = None
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            # Response is plain text or invalid JSON; keep parsed as None
            pass
        return ModelResponse(
            content=content,
            parsed_json=parsed,
            model_name=str(self.model_name or "claude-3-5-sonnet-20240620"),
            prompt_tokens=resp.usage.input_tokens if resp.usage else 0,
            completion_tokens=resp.usage.output_tokens if resp.usage else 0,
        )

    def _call_gemini(
        self, system_prompt: str, user_prompt: str, response_schema: Any, temp: float
    ) -> ModelResponse:
        import google.generativeai as genai

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=self.model_name or "gemini-1.5-pro", system_instruction=system_prompt
        )
        resp = model.generate_content(
            user_prompt,
            generation_config={"temperature": temp, "response_mime_type": "application/json"},
        )
        content = resp.text or ""
        parsed = None
        try:
            parsed = json.loads(content)
        except Exception:
            # Response is plain text or invalid JSON; keep parsed as None
            pass
        return ModelResponse(
            content=content, parsed_json=parsed, model_name=self.model_name or "gemini-1.5-pro"
        )
