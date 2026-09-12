"""Centralized Constants and Configuration Management for CurioKraft Book Engine.

This module serves as the single source of truth for:
1. Publishing dimensions and KDP print geometry.
2. File system paths and pipeline artifacts.
3. Book metadata and branding defaults.
4. Algorithmic thresholds for QA and image processing.
5. Dynamic configuration loading from config/book_config.yaml.
"""

from __future__ import annotations

import functools
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("curiokraft.constants")

# ==============================================================================
# 1. Standard File System Paths
# ==============================================================================
DEFAULT_BOOK_CONFIG = Path("config/book_config.yaml")


def _read_initial_book_config() -> dict[str, Any]:
    if DEFAULT_BOOK_CONFIG.exists():
        try:
            with open(DEFAULT_BOOK_CONFIG, encoding="utf-8") as fh:
                d = yaml.safe_load(fh)
                if isinstance(d, dict):
                    return d
        except Exception:
            # Fall back to empty dictionary if configuration file is missing or unreadable
            pass
    return {}


_cfg = _read_initial_book_config()
_b_cfg = _cfg.get("book", {})
_i_cfg = _b_cfg.get("interior", {})
_aud_cfg = _b_cfg.get("target_audience", {})
_sp_cfg = _b_cfg.get("special_pages", {})
_m_cfg = _b_cfg.get("mascot", {})

DEFAULT_BOOK_VOLUME = str(_b_cfg.get("volume", "vol1")).lower()
DEFAULT_PAGES_MANIFEST = Path(str(_b_cfg.get("manifest", "manifest/pages.json")))
DEFAULT_OBJECTS_REGISTRY = Path("manifest/objects.json")
DEFAULT_CURRICULUM_CONFIG = Path("config/curriculum.yaml")
DEFAULT_TAXONOMY_CONFIG = Path("config/taxonomy.yaml")
DEFAULT_AGENTS_CONFIG = Path("config/agents.yaml")

DEFAULT_INTERIOR_MASTERS_DIR = Path("output/interior_masters")
DEFAULT_RAW_GENERATED_DIR = Path("generated/raw_pages")
DEFAULT_INBOX_DIR = Path("inbox/raw_pages")


def get_special_assets_dir(volume: str | None = None) -> Path:
    vol = (volume or DEFAULT_BOOK_VOLUME).lower()
    candidates = [
        Path(f"assets/special_assets/{vol}"),
        Path("assets/special_assets"),
        Path(f"inbox/special_assets/{vol}"),
        Path("inbox/special_assets"),
    ]
    for c in candidates:
        if c.exists():
            return c
    return Path("assets/special_assets")


DEFAULT_SPECIAL_ASSETS_DIR = get_special_assets_dir(DEFAULT_BOOK_VOLUME)
DEFAULT_FONTS_DIR = Path("assets/fonts")
DEFAULT_LOGO_PATH = Path("assets/logo/curiokraft_logo.png")
DEFAULT_EMBLEM_PATH = Path("assets/emblem/curiokraft_emblem.png")

# Milestone Bookend Pages & Mascot Defaults
DEFAULT_WELCOME_PAGE_ENABLED = (
    bool(_sp_cfg.get("welcome_page", {}).get("enabled", True))
    if isinstance(_sp_cfg, dict)
    else True
)
DEFAULT_CERTIFICATE_PAGE_ENABLED = (
    bool(_sp_cfg.get("certificate_page", {}).get("enabled", True))
    if isinstance(_sp_cfg, dict)
    else True
)
DEFAULT_MASCOT_ENABLED = bool(_m_cfg.get("enabled", True)) if isinstance(_m_cfg, dict) else False
DEFAULT_MASCOT_NAME = _m_cfg.get("name") if isinstance(_m_cfg, dict) else None
DEFAULT_MASCOT_GENERATE_PROMPT = (
    bool(_m_cfg.get("generate_prompt", False)) if isinstance(_m_cfg, dict) else False
)
DEFAULT_MASCOT_DROP_PATH = (
    Path(str(_m_cfg.get("drop_path", "inbox/special_assets/tiny_mascot.png")))
    if isinstance(_m_cfg, dict)
    else Path("inbox/special_assets/tiny_mascot.png")
)

DEFAULT_INTERIOR_PDF = Path("output/interior/TINY_HANDS_COLOR_AND_LEARN_Interior_110p.pdf")
DEFAULT_COVER_OUTPUT_PNG = Path("output/cover/TINY_HANDS_COLOR_AND_LEARN_Cover_300DPI.png")
DEFAULT_COVER_OUTPUT_PDF = Path("output/cover/TINY_HANDS_COLOR_AND_LEARN_Cover_CMYK.pdf")
DEFAULT_BOOK_QA_REPORT = Path("output/reports/book_level_qa_audit.json")
DEFAULT_COVER_COMPLIANCE_REPORT = Path("output/reports/cover_kdp_compliance_report.json")
DEFAULT_PIPELINE_STATE_FILE = Path("output/pipeline_state.json")
DEFAULT_DEBATE_LOG_FILE = Path("logs/agent_debates_log.md")

# KDP Publishing & Forms Defaults
DEFAULT_KDP_FORMS_INBOX_DIR = Path("inbox/kdp_forms")
DEFAULT_KDP_OUTPUT_DIR = Path("output/kdp")
DEFAULT_KDP_SUBMISSION_HTML = Path("output/kdp/kdp_submission_helper.html")
DEFAULT_KDP_METADATA_JSON = Path("output/kdp/kdp_metadata.json")
DEFAULT_KDP_FIELDS_MD = Path("output/kdp/kdp_fields.md")
DEFAULT_KDP_LIST_PRICE = 6.99
DEFAULT_KDP_ROYALTY_RATE = 0.60
KDP_KEYWORD_MAX_CHARS = 50
KDP_DESCRIPTION_MAX_CHARS = 4000

# ==============================================================================
# 2. Publishing Dimensions & KDP Print Geometry
# ==============================================================================
CANVAS_WIDTH_PX = 2550
CANVAS_HEIGHT_PX = 3300
CANVAS_DPI = 300

DEFAULT_TRIM_WIDTH_IN = 8.5
DEFAULT_TRIM_HEIGHT_IN = 11.0
DEFAULT_PAGE_WIDTH_PT = 612.0
DEFAULT_PAGE_HEIGHT_PT = 792.0
DEFAULT_BLEED_IN = 0.125
DEFAULT_PAGE_COUNT = int(_i_cfg.get("page_count", 110))

# KDP spine thickness multipliers (inches per page)
KDP_PAPER_MULTIPLIERS = {
    "white": 0.002252,
    "cream": 0.0025,
    "color": 0.002347,
    "standard_color": 0.002252,
}

# Standard 110-page paperback wrap cover dimensions (inches @ 300 DPI)
DEFAULT_COVER_WIDTH_IN = 17.498
DEFAULT_COVER_HEIGHT_IN = 11.250
DEFAULT_SPINE_WIDTH_IN = 0.248

# Safety Margins (inches)
SAFE_MARGIN_IN = 0.50
KDP_MIN_GUTTER_IN = 0.375
KDP_MIN_OUTSIDE_IN = 0.250
HEADER_RESERVATION_IN = 1.2
TARGET_COVERAGE_RATIO = 0.72

# Back Cover Fixed Exclusion Zones (pixels @ 300 DPI)
BARCODE_BOX_X1 = 1845
BARCODE_BOX_X2 = 2545
BARCODE_BOX_Y1 = 2850
BARCODE_BOX_Y2 = 3280

PUBLISHER_BADGE_X1 = 180
PUBLISHER_BADGE_Y1 = 2860
PUBLISHER_BADGE_X2 = 820
PUBLISHER_BADGE_Y2 = 3280
PUBLISHER_BADGE_WIDTH = 640
PUBLISHER_BADGE_HEIGHT = 420

# ==============================================================================
# 3. Branding & Book Metadata Defaults
# ==============================================================================
DEFAULT_BOOK_TITLE = str(_b_cfg.get("title", "TINY HANDS COLOR & LEARN"))
DEFAULT_BOOK_SUBTITLE = str(_b_cfg.get("subtitle", "FUN & EASY FIRST WORDS"))
DEFAULT_BOOK_VOLUME = str(_b_cfg.get("volume", "vol1")).lower()
DEFAULT_IMPRINT = str(_b_cfg.get("brand", "CURIOKRAFT-KIDS"))
DEFAULT_AUTHOR = str(_b_cfg.get("author", "CurioKraft Publications"))
DEFAULT_AGE_MIN = int(_aud_cfg.get("age_min", 1))
DEFAULT_AGE_MAX = int(_aud_cfg.get("age_max", 4))

# ==============================================================================
# 4. Quality, Validation & Algorithmic Thresholds
# ==============================================================================
BLACK_THRESHOLD = 20
WHITE_THRESHOLD = 235
INK_THRESHOLD = 240
COLOR_TOLERANCE = 6
MAX_GRAY_CLUSTER_SIZE_PX = 60
BINARIZE_THRESHOLD_VALUE = 200
BACKGROUND_TRANSPARENCY_THRESHOLD = 245
SIMILARITY_SCORE_THRESHOLD = 0.85
MAX_RETRY_ATTEMPTS = 3

# Typography defaults
TYPOGRAPHY_BASE_FONT_SIZE_PT = 245
TYPOGRAPHY_TOP_OFFSET_PX = 240
TYPOGRAPHY_STROKE_WIDTH_PX = 15
TYPOGRAPHY_LETTER_SPACING_PX = 40

# ==============================================================================
# 5. Pipeline State Enum Constants
# ==============================================================================
STATE_PLANNED = "PLANNED"
STATE_DEBATED = "DEBATED"
STATE_PROMPT_LOCKED = "PROMPT_LOCKED"
STATE_GENERATING = "GENERATING"
STATE_GENERATED = "GENERATED"
STATE_VISION_QA_PASSED = "VISION_QA_PASSED"
STATE_TECHNICAL_QA_PASSED = "TECHNICAL_QA_PASSED"
STATE_RESCUED = "RESCUED"
STATE_COMPOSITED = "COMPOSITED"
STATE_APPROVED = "APPROVED"
STATE_FAILED = "FAILED"
STATE_ESCALATED = "ESCALATED"

ALL_PIPELINE_STATES = (
    STATE_PLANNED,
    STATE_DEBATED,
    STATE_PROMPT_LOCKED,
    STATE_GENERATING,
    STATE_GENERATED,
    STATE_VISION_QA_PASSED,
    STATE_TECHNICAL_QA_PASSED,
    STATE_RESCUED,
    STATE_COMPOSITED,
    STATE_APPROVED,
    STATE_FAILED,
    STATE_ESCALATED,
)

# ==============================================================================
# 6. Dynamic Configuration Loader
# ==============================================================================


@functools.lru_cache(maxsize=8)
def load_book_config(config_path: Path | str = DEFAULT_BOOK_CONFIG) -> dict[str, Any]:
    """Load book configuration with caching and graceful fallbacks.

    Returns the loaded YAML dictionary, or a minimal structured fallback
    matching the standard constants if the file cannot be loaded.
    """
    path = Path(config_path)

    if not path.exists():
        logger.debug(f"Book configuration not found at {path}, using standard defaults.")
        return _build_fallback_config()

    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if isinstance(data, dict):
            return data
        return _build_fallback_config()
    except Exception as exc:
        logger.warning(f"Error loading {path}: {exc}. Using standard defaults.")
        return _build_fallback_config()


def _build_fallback_config() -> dict[str, Any]:
    """Return a baseline configuration dictionary derived from standard constants."""
    return {
        "book": {
            "title": DEFAULT_BOOK_TITLE,
            "subtitle": DEFAULT_BOOK_SUBTITLE,
            "brand": DEFAULT_IMPRINT,
            "manifest": str(DEFAULT_PAGES_MANIFEST),
            "target_audience": {"age_min": DEFAULT_AGE_MIN, "age_max": DEFAULT_AGE_MAX},
            "interior": {
                "page_count": DEFAULT_PAGE_COUNT,
                "target_dpi": CANVAS_DPI,
                "trim_size": {
                    "width_in": DEFAULT_TRIM_WIDTH_IN,
                    "height_in": DEFAULT_TRIM_HEIGHT_IN,
                },
                "master_canvas_px": {
                    "width": CANVAS_WIDTH_PX,
                    "height": CANVAS_HEIGHT_PX,
                },
                "safe_margins_in": {
                    "inside_gutter": SAFE_MARGIN_IN,
                    "outside": SAFE_MARGIN_IN,
                    "top": SAFE_MARGIN_IN,
                    "bottom": SAFE_MARGIN_IN,
                },
            },
            "cover": {
                "overall_dimensions_in": {
                    "width": DEFAULT_COVER_WIDTH_IN,
                    "height": DEFAULT_COVER_HEIGHT_IN,
                },
                "spine_width_in": DEFAULT_SPINE_WIDTH_IN,
            },
        }
    }
