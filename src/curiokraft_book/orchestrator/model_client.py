"""Backward-compatibility facade for the former monolithic ``ModelClient``.

.. deprecated::
    ``ModelClient`` bundled three responsibilities (text generation, image
    analysis, image creation), which made it impossible to depend on -- or mock
    -- just one of them (Interface Segregation violation).

    Use the focused clients instead:

    ==========================  ==========================================
    Old (``ModelClient``)       New
    ==========================  ==========================================
    ``call_agent``              :meth:`LLMClient.call_agent`
    ``call_vision``             :meth:`VisionClient.call_vision`
    ``generate_illustration``   :meth:`ImageGenerator.generate`
    ==========================  ==========================================

    ``ModelClient`` is retained so existing imports keep working and will be
    removed in v2.0. New code should import the specific client it needs.

The shared primitives (``ModelResponse``, the image-provider strategy classes,
``load_env_file``) now live in :mod:`curiokraft_book.orchestrator.providers`
and are re-exported here unchanged for compatibility.
"""

import logging
import warnings

from curiokraft_book.orchestrator.image_generator import ImageGenerator
from curiokraft_book.orchestrator.llm_client import LLMClient
from curiokraft_book.orchestrator.providers import (  # noqa: F401  (re-exported API)
    BaseImageProvider,
    DiskInboxProvider,
    GeminiImageProvider,
    MockImageProvider,
    ModelResponse,
    OpenAIImageProvider,
    load_env_file,
)
from curiokraft_book.orchestrator.vision_client import VisionClient

logger = logging.getLogger("curiokraft.model_client")

__all__ = [
    "BaseImageProvider",
    "DiskInboxProvider",
    "GeminiImageProvider",
    "ImageGenerator",
    "LLMClient",
    "MockImageProvider",
    "ModelClient",
    "ModelResponse",
    "OpenAIImageProvider",
    "VisionClient",
    "load_env_file",
]


class ModelClient:
    """DEPRECATED: use ``LLMClient``, ``VisionClient`` or ``ImageGenerator``.

    Thin delegating facade. Each method forwards to the focused client so the
    three responsibilities stay independently testable and mockable.
    """

    def __init__(self, provider: str = "auto", model_name: str | None = None):
        warnings.warn(
            "ModelClient is deprecated and will be removed in v2.0. "
            "Use LLMClient, VisionClient, or ImageGenerator instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.llm = LLMClient(provider, model_name)
        self.vision = VisionClient(provider, model_name)
        self.image_gen = ImageGenerator(provider, model_name)

        # Preserve the attributes callers historically read off ModelClient.
        self.provider = self.llm.provider
        self.model_name = self.llm.model_name
        logger.info(f"Initialized deprecated ModelClient facade (provider: {self.provider})")

    def call_agent(self, *args, **kwargs):
        """DEPRECATED: use :meth:`LLMClient.call_agent`."""
        return self.llm.call_agent(*args, **kwargs)

    def call_vision(self, *args, **kwargs):
        """DEPRECATED: use :meth:`VisionClient.call_vision`."""
        return self.vision.call_vision(*args, **kwargs)

    def generate_illustration(self, *args, **kwargs):
        """DEPRECATED: use :meth:`ImageGenerator.generate`."""
        return self.image_gen.generate(*args, **kwargs)
