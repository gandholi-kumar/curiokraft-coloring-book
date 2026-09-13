"""Illustration-generation client (Interface Segregation).

Owns exactly one responsibility: producing the raw raster for a page. Selects
among the pluggable image-provider strategies (inbox drop, OpenAI, Gemini,
offline mock) according to ``source_mode``.
"""

import logging
import os
from typing import Any

from curiokraft_book.orchestrator.providers import (
    DiskInboxProvider,
    GeminiImageProvider,
    MockImageProvider,
    OpenAIImageProvider,
    load_env_file,
    resolve_provider_and_model,
)

logger = logging.getLogger("curiokraft.image_generator")


class ImageGenerator:
    """Selects and runs the appropriate image provider for a page."""

    def __init__(self, provider: str = "auto", model_name: str | None = None):
        """
        Args:
            provider: 'openai' | 'gemini' | 'mock' | 'auto'.
            model_name: Retained for symmetry with the other clients.
        """
        load_env_file()
        self.provider, self.model_name = resolve_provider_and_model(provider, model_name)
        logger.info(f"Initialized ImageGenerator with provider: {self.provider}")

    def generate(
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

    def generate_illustration(self, *args, **kwargs) -> Any:
        """Deprecated alias for :meth:`generate`; kept for existing callers."""
        return self.generate(*args, **kwargs)
