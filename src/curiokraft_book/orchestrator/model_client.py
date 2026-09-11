"""Model-agnostic client interface supporting OpenAI, Anthropic, Gemini, and offline simulation."""

import json
import logging
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger("curiokraft.model_client")


def load_env_file(env_filename: str = ".env") -> None:
    """Auto-load environment variables from .env file if present."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass

    # Built-in fallback parser for zero-dependency .env support
    search_dirs = [Path.cwd(), Path(__file__).resolve().parents[3], Path(__file__).resolve().parent]
    for d in search_dirs:
        env_file = d / env_filename
        if env_file.is_file():
            try:
                for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k and k not in os.environ:
                        os.environ[k] = v
                break
            except Exception:
                pass


# Auto-load on import
load_env_file()


class ModelResponse(BaseModel):
    """Standardized response from an LLM model call."""

    content: str
    parsed_json: dict[str, Any] | None = None
    model_name: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


# ----------------------------------------------------------------------
# Pluggable Image Provider Strategy Architecture
# ----------------------------------------------------------------------


class BaseImageProvider:
    """Abstract Base Class for all illustration generation providers."""

    @property
    def provider_name(self) -> str:
        raise NotImplementedError

    def generate(
        self,
        positive_prompt: str,
        negative_prompt: str = "",
        canonical_label: str = "",
        section: str = "General",
        page_id: str | None = None,
        page_number: int | None = None,
        **kwargs,
    ) -> Any:
        raise NotImplementedError


class GeminiImageProvider(BaseImageProvider):
    """Google Gemini Native Image Generation Provider (gemini-3.1-flash-image)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = (
            api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        )

    @property
    def provider_name(self) -> str:
        return "gemini"

    def generate(
        self,
        positive_prompt: str,
        negative_prompt: str = "",
        canonical_label: str = "",
        section: str = "General",
        **kwargs,
    ) -> Any:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment.")

        import base64
        from io import BytesIO

        from PIL import Image

        imagen_prompt = (
            f"{positive_prompt}, clean 2D vector line art coloring book page for toddlers, "
            f"thick black outlines, pure white background #FFFFFF, no shading, zero grayscale, no colors"
        )

        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)
            for model_id in ["gemini-3.1-flash-image", "gemini-2.5-flash-image"]:
                try:
                    logger.info(f"Calling Google Gemini Image Generation with {model_id}...")
                    interaction = client.interactions.create(model=model_id, input=imagen_prompt)
                    if interaction.output_image and interaction.output_image.data:
                        img_bytes = base64.b64decode(interaction.output_image.data)
                        pil_img = Image.open(BytesIO(img_bytes)).convert("L")
                        logger.info(f"Successfully generated illustration via {model_id}.")
                        return pil_img
                except Exception as m_err:
                    logger.debug(f"Model {model_id} attempt failed: {m_err}")
                    if "limit: 0" in str(m_err) or "429" in str(m_err):
                        raise
        except Exception as sdk_err:
            if (
                "limit: 0" in str(sdk_err)
                or "429" in str(sdk_err)
                or "too_many_requests" in str(sdk_err)
            ):
                raise RuntimeError(
                    "Google AI Studio requires a linked Pay-As-You-Go billing account for image generation models (gemini-3.1-flash-image). "
                    "Free tier image quota is 0 RPM."
                ) from sdk_err
            logger.debug(f"google-genai SDK invocation failed: {sdk_err}")

        # REST fallback
        try:
            import requests

            url = "https://generativelanguage.googleapis.com/v1beta/interactions"
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            }
            payload = {
                "model": "gemini-3.1-flash-image",
                "input": [{"type": "text", "text": imagen_prompt}],
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                out_img = data.get("output_image", {})
                if out_img and "data" in out_img:
                    img_bytes = base64.b64decode(out_img["data"])
                    pil_img = Image.open(BytesIO(img_bytes)).convert("L")
                    logger.info("Successfully generated illustration via REST interactions.")
                    return pil_img
            else:
                raise RuntimeError(f"Google Gemini Image API HTTP {resp.status_code}: {resp.text}")
        except Exception as rest_err:
            raise RuntimeError(f"Google Gemini REST generation error: {rest_err}") from rest_err


class OpenAIImageProvider(BaseImageProvider):
    """OpenAI DALL-E 3 Image Generation Provider."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

    @property
    def provider_name(self) -> str:
        return "openai"

    def generate(
        self,
        positive_prompt: str,
        negative_prompt: str = "",
        canonical_label: str = "",
        section: str = "General",
        **kwargs,
    ) -> Any:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment.")

        from io import BytesIO

        import openai
        import requests
        from PIL import Image

        client = openai.OpenAI(api_key=self.api_key)
        logger.info("Calling OpenAI DALL-E 3...")
        resp = client.images.generate(
            model="dall-e-3",
            prompt=f"{positive_prompt}. Clean preschool coloring book line art, thick black outlines, stark pure white background, no shading.",
            size="1024x1024",
            quality="standard",
            n=1,
        )
        img_url = resp.data[0].url
        raw_bytes = requests.get(img_url, timeout=30).content
        pil_img = Image.open(BytesIO(raw_bytes)).convert("L")
        logger.info("Successfully received generated image from OpenAI DALL-E 3.")
        return pil_img


class DiskInboxProvider(BaseImageProvider):
    """Ingests fresh user-dropped illustrations from inbox/raw_pages/."""

    def __init__(
        self, inbox_dir: str | Path = "inbox/raw_pages", raw_dir: str | Path = "generated/raw_pages"
    ):
        self.inbox_dir = Path(inbox_dir)
        self.raw_dir = Path(raw_dir)
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    @property
    def provider_name(self) -> str:
        return "inbox"

    def find_image(
        self, page_id: str | None = None, page_number: int | None = None, canonical_label: str = ""
    ) -> Path | None:
        if not self.inbox_dir.exists():
            return None

        canon = canonical_label.lower().strip().replace(" ", "_")
        valid_extensions = {".png", ".jpg", ".jpeg", ".webp"}

        inbox_files = [
            f for f in self.inbox_dir.iterdir() if f.is_file() and f.stat().st_size > 500
        ]

        def get_clean_stem_and_ext(file_path: Path) -> tuple[str, str]:
            name = file_path.name.lower()
            for ext in [".png.jpg", ".jpg.png", ".jpeg.jpg", ".jpeg.png", ".png.jpeg", ".jpg.jpeg"]:
                if name.endswith(ext):
                    clean_stem = name[: -len(ext)]
                    return clean_stem, ext
            return file_path.stem.lower(), file_path.suffix.lower()

        candidates_p1 = []
        candidates_p2 = []
        candidates_p3 = []

        import re

        target_prefixes = []
        if page_number is not None:
            target_prefixes.extend(
                [
                    f"raw_p{page_number:03d}",
                    f"p{page_number:03d}",
                    f"raw_p{page_number}",
                    f"p{page_number}",
                ]
            )
        if page_id:
            pid = page_id.lower().strip()
            target_prefixes.extend([f"raw_{pid}", pid])

        for f in inbox_files:
            clean_stem, ext = get_clean_stem_and_ext(f)
            is_valid_img = any(ext.endswith(ve) for ve in valid_extensions)
            if not is_valid_img:
                continue

            # Strict page-number ownership check: if file explicitly starts with a page number (e.g. raw_p110),
            # it must NEVER be matched by any other page (e.g. Page 49).
            p_match = re.match(r"^(?:raw_)?p(\d+)(?:[_-].*)?$", clean_stem)
            if p_match:
                file_page_num = int(p_match.group(1))
                if page_number is not None and file_page_num != page_number:
                    continue  # Strictly belongs to a different page

            matches_page = any(
                clean_stem == pfx
                or clean_stem.startswith(f"{pfx}_")
                or clean_stem.startswith(f"{pfx}-")
                for pfx in target_prefixes
            )

            # Whole-token canonical matching (prevents 'cat' matching 'certificate' or 'car' matching 'carrot')
            stem_tokens = "_".join(re.split(r"[-_\s]+", clean_stem))
            canon_tokens = "_".join(re.split(r"[-_\s]+", canon))
            stem_delim = f"_{stem_tokens}_"
            canon_delim = f"_{canon_tokens}_"
            matches_canon = bool(canon and (clean_stem == canon or canon_delim in stem_delim))

            if matches_page and matches_canon:
                candidates_p1.append(f)
            elif matches_page:
                candidates_p2.append(f)
            elif matches_canon:
                candidates_p3.append(f)

        if candidates_p1:
            return candidates_p1[0]
        if candidates_p2:
            return candidates_p2[0]
        if candidates_p3:
            return candidates_p3[0]

        return None

    def generate(
        self,
        positive_prompt: str,
        negative_prompt: str = "",
        canonical_label: str = "",
        section: str = "General",
        page_id: str | None = None,
        page_number: int | None = None,
        **kwargs,
    ) -> Any:
        from PIL import Image

        found = self.find_image(
            page_id=page_id, page_number=page_number, canonical_label=canonical_label
        )
        if not found:
            raise FileNotFoundError(
                f"No image found in {self.inbox_dir}/ for page {page_id} ({canonical_label})."
            )
        logger.info(f"Ingesting user image from {found}")
        return Image.open(found).convert("L")


class MockImageProvider(BaseImageProvider):
    """Deterministic offline generator rendering smooth cubic Bézier vector templates."""

    @property
    def provider_name(self) -> str:
        return "mock"

    def _cubic_bezier(self, p0, p1, p2, p3, n=80):
        pts = []
        for i in range(n + 1):
            t = i / float(n)
            x = (
                (1 - t) ** 3 * p0[0]
                + 3 * (1 - t) ** 2 * t * p1[0]
                + 3 * (1 - t) * t**2 * p2[0]
                + t**3 * p3[0]
            )
            y = (
                (1 - t) ** 3 * p0[1]
                + 3 * (1 - t) ** 2 * t * p1[1]
                + 3 * (1 - t) * t**2 * p2[1]
                + t**3 * p3[1]
            )
            pts.append((int(x), int(y)))
        return pts

    def generate(
        self,
        positive_prompt: str,
        negative_prompt: str = "",
        canonical_label: str = "",
        section: str = "General",
        **kwargs,
    ) -> Any:
        from PIL import Image, ImageDraw

        canvas = Image.new("L", (2550, 3300), 255)
        draw = ImageDraw.Draw(canvas)
        # Dynamic generic vector drawing based on category
        sec_lower = section.lower()
        if "spread" in sec_lower or "alphabet" in sec_lower or "numbers" in sec_lower:
            # Multi-card overview grid
            draw.rectangle([400, 500, 2150, 2900], outline=0, width=18)
            draw.line([(400, 1700), (2150, 1700)], fill=0, width=14)
            draw.line([(1275, 500), (1275, 2900)], fill=0, width=14)
        elif "animal" in sec_lower or "pet" in sec_lower or "creature" in sec_lower:
            # Cute animal vector contour with friendly eyes
            draw.ellipse([800, 950, 1750, 1950], outline=0, width=22)
            draw.ellipse([550, 950, 900, 1650], outline=0, width=22)
            draw.ellipse([1650, 950, 2000, 1650], outline=0, width=22)
            draw.ellipse([1100, 1450, 1450, 1750], outline=0, width=18)
            draw.ellipse([1020, 1250, 1120, 1350], fill=0)
            draw.ellipse([1430, 1250, 1530, 1350], fill=0)
            draw.arc([1210, 1580, 1340, 1680], start=20, end=160, fill=0, width=16)
        elif "vehicle" in sec_lower or "transport" in sec_lower:
            # Vehicle silhouette with chunky wheels
            draw.rounded_rectangle([600, 1200, 1950, 2100], radius=80, outline=0, width=22)
            draw.rounded_rectangle([850, 800, 1650, 1200], radius=50, outline=0, width=20)
            draw.ellipse([750, 1900, 1050, 2200], outline=0, fill=255, width=22)
            draw.ellipse([1500, 1900, 1800, 2200], outline=0, fill=255, width=22)
        else:
            # Iconic centered physical object with bold 22px outline
            draw.ellipse([650, 850, 1900, 2450], outline=0, width=22)
            draw.arc([850, 1150, 1700, 2150], start=30, end=150, fill=0, width=16)

        return canvas


class ModelClient:
    """Unified interface for executing agent prompts across different LLM providers."""

    def __init__(self, provider: str = "auto", model_name: str | None = None):
        """Initialize model client.

        Args:
            provider: 'openai' | 'anthropic' | 'gemini' | 'mock' | 'auto'.
            model_name: Specific model ID (e.g. 'gpt-4o', 'claude-3-5-sonnet', 'gemini-1.5-pro').
        """
        load_env_file()
        env_provider = os.environ.get("CK_DEFAULT_PROVIDER")
        if env_provider:
            self.provider = env_provider.lower()
        else:
            self.provider = provider.lower()

        self.model_name = model_name

        if self.provider == "auto":
            if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
                self.provider = "gemini"
                self.model_name = model_name or "gemini-1.5-pro"
            elif os.environ.get("OPENAI_API_KEY"):
                self.provider = "openai"
                self.model_name = model_name or "gpt-4o"
            elif os.environ.get("ANTHROPIC_API_KEY"):
                self.provider = "anthropic"
                self.model_name = model_name or "claude-3-5-sonnet-20240620"
            else:
                self.provider = "mock"
                self.model_name = "curiokraft-offline-simulator"

        logger.info(f"Initialized ModelClient with provider: {self.provider} ({self.model_name})")

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
        resp = client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"} if response_schema else None,
            temperature=temp,
        )
        content = resp.choices[0].message.content or ""
        parsed = None
        try:
            parsed = json.loads(content)
        except Exception:
            pass
        return ModelResponse(
            content=content,
            parsed_json=parsed,
            model_name=self.model_name,
            prompt_tokens=resp.usage.prompt_tokens if resp.usage else 0,
            completion_tokens=resp.usage.completion_tokens if resp.usage else 0,
        )

    def _call_anthropic(
        self, system_prompt: str, user_prompt: str, response_schema: Any, temp: float
    ) -> ModelResponse:
        import anthropic

        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=self.model_name,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=temp,
        )
        content = resp.content[0].text if resp.content else ""
        parsed = None
        try:
            parsed = json.loads(content)
        except Exception:
            pass
        return ModelResponse(
            content=content,
            parsed_json=parsed,
            model_name=self.model_name,
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
            pass
        return ModelResponse(
            content=content, parsed_json=parsed, model_name=self.model_name or "gemini-1.5-pro"
        )

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
                        "response_mime_type": "application/json" if response_schema else "text/plain",
                    },
                )
                content = resp.text or ""
                parsed = None
                try:
                    parsed = json.loads(content)
                except Exception:
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

    def generate_illustration(
        self,
        positive_prompt: str,
        negative_prompt: str = "",
        canonical_label: str = "",
        section: str = "General",
        source_mode: str = "auto",
        page_id: str | None = None,
        page_number: int | None = None,
        force_fresh: bool = False,
    ) -> Any:
        """Generate or ingest raw illustration using the pluggable provider strategy."""
        mode = source_mode.lower().strip()
        inbox_provider = DiskInboxProvider()

        # 1. Explicit 'inbox' or 'disk' mode
        if mode in ["inbox", "disk"]:
            return inbox_provider.generate(
                positive_prompt,
                negative_prompt,
                canonical_label,
                section,
                page_id=page_id,
                page_number=page_number,
            )

        # 2. Check inbox if in 'auto' mode and not forced fresh
        if mode == "auto" and not force_fresh:
            found = inbox_provider.find_image(
                page_id=page_id, page_number=page_number, canonical_label=canonical_label
            )
            if found:
                logger.info(f"Auto-detected fresh user drop in inbox: {found}")
                from PIL import Image

                return Image.open(found).convert("L")

        # 3. Live API Generation (OpenAI / Gemini)
        if mode in ["api", "openai", "gemini", "auto"]:
            if self.provider == "openai" or (os.environ.get("OPENAI_API_KEY") and mode != "mock"):
                try:
                    return OpenAIImageProvider().generate(
                        positive_prompt, negative_prompt, canonical_label, section
                    )
                except Exception as e:
                    logger.warning(f"OpenAI provider error: {e}")
                    if mode in ["api", "openai"]:
                        raise

            elif self.provider == "gemini" or (os.environ.get("GEMINI_API_KEY") and mode != "mock"):
                try:
                    return GeminiImageProvider().generate(
                        positive_prompt, negative_prompt, canonical_label, section
                    )
                except Exception as e:
                    logger.warning(f"Gemini provider error: {e}")
                    if mode in ["api", "gemini"]:
                        raise

        # 4. Fallback to Deterministic Offline Simulator
        return MockImageProvider().generate(
            positive_prompt, negative_prompt, canonical_label, section
        )
