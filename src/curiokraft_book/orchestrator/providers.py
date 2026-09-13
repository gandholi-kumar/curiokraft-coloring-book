"""Shared provider primitives.

Houses the pieces that the specialised clients
(:mod:`llm_client`, :mod:`vision_client`, :mod:`image_generator`) build on:

- ``load_env_file`` / provider auto-detection helpers
- ``ModelResponse`` -- the normalized response envelope
- The pluggable image-provider strategy (:class:`BaseImageProvider` and friends)

Responsibility-based split of the former monolithic ``model_client`` module.
"""

import logging
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger("curiokraft.providers")


def load_env_file(env_filename: str = ".env") -> None:
    """Auto-load environment variables from .env file if present."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        # python-dotenv is optional; continue with built-in env parser fallback
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
                # Failed reading candidate env file; try next search directory
                pass


# Auto-load on import
load_env_file()


# Per-provider default text model IDs, used when the caller does not pin one.
DEFAULT_TEXT_MODELS: dict[str, str] = {
    "openai": "gpt-4o",
    "anthropic": "claude-3-5-sonnet-20240620",
    "gemini": "gemini-1.5-pro",
}
OFFLINE_MODEL_NAME = "curiokraft-offline-simulator"


def resolve_provider_and_model(
    provider: str = "auto", model_name: str | None = None
) -> tuple[str, str]:
    """Resolve the effective provider and model name.

    Precedence: ``CK_DEFAULT_PROVIDER`` env override, then the ``auto``
    detection order (Gemini -> OpenAI -> Anthropic -> offline mock), then the
    caller-supplied provider. ``model_name`` is filled with the provider default
    when omitted.

    Returns:
        ``(provider, model_name)`` with both values concrete (never ``"auto"``).
    """
    env_provider = os.environ.get("CK_DEFAULT_PROVIDER")
    resolved = (env_provider or provider).lower()

    if resolved == "auto":
        if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            resolved = "gemini"
        elif os.environ.get("OPENAI_API_KEY"):
            resolved = "openai"
        elif os.environ.get("ANTHROPIC_API_KEY"):
            resolved = "anthropic"
        else:
            resolved = "mock"

    if not model_name:
        model_name = DEFAULT_TEXT_MODELS.get(resolved, OFFLINE_MODEL_NAME)
    return resolved, model_name


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
        page_id: str | None = None,
        page_number: int | None = None,
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
                    out_img_obj = getattr(interaction, "output_image", None)
                    if out_img_obj and getattr(out_img_obj, "data", None):
                        img_bytes = base64.b64decode(out_img_obj.data)
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
            payload: dict[str, Any] = {
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
            logger.debug(f"REST interaction fallback failed: {rest_err}")

        raise RuntimeError("Failed to generate image via Gemini API.")


class OpenAIImageProvider(BaseImageProvider):
    """OpenAI DALL-E 3 Provider."""

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
        page_id: str | None = None,
        page_number: int | None = None,
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
        if not resp.data or not resp.data[0].url:
            raise ValueError("No image URL returned from OpenAI")
        img_url = resp.data[0].url
        raw_bytes = requests.get(str(img_url), timeout=30).content
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
        page_id: str | None = None,
        page_number: int | None = None,
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
