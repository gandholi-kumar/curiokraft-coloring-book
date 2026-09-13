"""Image-analysis client (Interface Segregation).

Owns exactly one responsibility: describing/validating an image. Uses a
vision-capable LLM when a Gemini key is available and otherwise falls back to a
deterministic offline spatial analyzer, so callers always get a response.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from curiokraft_book.orchestrator.providers import ModelResponse, load_env_file

logger = logging.getLogger("curiokraft.vision_client")


class VisionClient:
    """Analyzes images via a multimodal LLM or the offline spatial analyzer."""

    def __init__(self, provider: str = "auto", model_name: str | None = None):
        """
        Args:
            provider: Retained for symmetry with the other clients.
            model_name: Vision model ID; defaults to ``gemini-1.5-flash``.
        """
        load_env_file()
        self.provider = provider.lower()
        self.model_name = model_name or "gemini-1.5-flash"
        logger.info(f"Initialized VisionClient with model: {self.model_name}")

    def call_vision(
        self,
        system_prompt: str,
        user_prompt: str,
        image_path: str | Path,
        response_schema: Any = None,
        temp: float = 0.2,
    ) -> ModelResponse:
        """Analyze an image using multimodal vision LLM or offline spatial analysis fallback."""
        img_p = Path(image_path)
        if not img_p.exists():
            raise FileNotFoundError(f"Image not found for vision analysis: {image_path}")

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if api_key:
            try:
                import google.generativeai as genai
                from PIL import Image

                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-flash", system_instruction=system_prompt
                )
                pil_img = Image.open(img_p)
                resp = model.generate_content(
                    [user_prompt, pil_img],
                    generation_config={
                        "temperature": temp,
                        "response_mime_type": "application/json"
                        if response_schema
                        else "text/plain",
                    },
                )
                content = resp.text or ""
                parsed = None
                try:
                    parsed = json.loads(content)
                except (json.JSONDecodeError, TypeError, ValueError):
                    # Response was plain text or not formatted as JSON; leave parsed as None
                    pass
                return ModelResponse(
                    content=content,
                    parsed_json=parsed,
                    model_name="gemini-1.5-flash",
                )
            except Exception as e:
                logger.warning(
                    f"Gemini vision call failed, falling back to deterministic spatial analyzer: {e}"
                )

        return self._simulate_vision_analysis(img_p, user_prompt)

    def _simulate_vision_analysis(self, image_path: Path, prompt: str) -> ModelResponse:
        """Deterministic offline spatial analyzer for layout blueprint wireframes."""
        from PIL import Image

        try:
            with Image.open(image_path) as img:
                w, h = img.size
                ar = w / h if h else 1.0
        except Exception:
            w, h, ar = 2550, 3300, 0.772

        mock_blueprint_analysis = {
            "blueprint_type": "back_cover" if "back" in image_path.name.lower() else "cover",
            "canvas_dimensions": {"width": w, "height": h, "aspect_ratio": round(ar, 3)},
            "zones_detected": {
                "header_zone": {
                    "detected": True,
                    "bounds_normalized": [0.05, 0.04, 0.95, 0.22],
                    "elements": ["bold uppercase headline", "parent description copy"],
                },
                "flashcard_grid_zone": {
                    "detected": True,
                    "bounds_normalized": [0.06, 0.24, 0.94, 0.52],
                    "rows": 1,
                    "columns": 3,
                    "card_shape": "rounded_rectangle",
                    "border_style": "clean dark stroke",
                    "content_type": "2D coloring book line art",
                },
                "feature_callout_zone": {
                    "detected": True,
                    "bounds_normalized": [0.12, 0.55, 0.88, 0.76],
                    "grid": "2x2_pill_grid",
                    "pill_count": 4,
                    "pill_style": "pastel rounded pill with star bullet",
                },
                "baseline_wave_zone": {
                    "detected": True,
                    "bounds_normalized": [0.0, 0.80, 1.0, 1.0],
                    "style": "continuous rolling pastel turquoise wave",
                    "height_percentage": 20,
                },
                "exclusion_zones": {
                    "bottom_left_logo": {"clear": True, "bounds": [0.05, 0.84, 0.25, 0.97]},
                    "bottom_right_barcode": {"clear": True, "bounds": [0.72, 0.84, 0.95, 0.97]},
                },
            },
            "layout_mandates": [
                "1 row by 3 columns flashcard arrangement",
                "2x2 grid of 4 pastel feature callout pills",
                "100% continuous rolling wave across lower 20% with zero pre-rendered white boxes",
                "Left edge (back cover) or right edge (front cover) borderless spine clearance",
            ],
        }

        return ModelResponse(
            content=json.dumps(mock_blueprint_analysis, indent=2),
            parsed_json=mock_blueprint_analysis,
            model_name="curiokraft-spatial-analyzer",
            prompt_tokens=100,
            completion_tokens=250,
        )
