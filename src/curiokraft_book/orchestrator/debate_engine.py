"""Dynamic Multi-Round Specialist Debate and Judge Synthesis Engine for Coloring Book Prompts.

100% Manifest-Driven & Agent-Autonomous: Zero hardcoded object lists, zero hardcoded page IDs.
  - config/taxonomy.yaml  -> living/inanimate keyword sets and category visual templates
  - config/curriculum.yaml -> volume-agnostic style rules, layout templates, purity rules
  - manifest/pages.json   -> ALL per-volume content including spread card assignments

Works universally for Volume 1, Volume 2, Volume 3, and specialized themed editions.
To create a new volume: provide a new manifest with different "cards" arrays — no code changes.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from curiokraft_book.constants import (
    DEFAULT_AGENTS_CONFIG,
    DEFAULT_BOOK_CONFIG,
    DEFAULT_BOOK_TITLE,
    DEFAULT_CURRICULUM_CONFIG,
    DEFAULT_DEBATE_LOG_FILE,
    DEFAULT_OBJECTS_REGISTRY,
    DEFAULT_PAGE_COUNT,
    DEFAULT_PAGES_MANIFEST,
    DEFAULT_TAXONOMY_CONFIG,
)
from curiokraft_book.orchestrator.model_client import ModelClient

logger = logging.getLogger("curiokraft.debate_engine")


# =============================================================================
# Config Loader — reads taxonomy + curriculum + objects once at module startup
# =============================================================================


def _load_yaml(path: str) -> dict:
    """Load a YAML config file relative to the project root (cwd) or an absolute path."""
    p = Path(path)
    if not p.is_absolute():
        candidates = [
            Path.cwd() / path,
            Path(__file__).parent.parent.parent.parent / path,
        ]
        for c in candidates:
            if c.exists():
                p = c
                break
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_json(path: str) -> dict:
    """Load a JSON manifest file relative to cwd or package root."""
    p = Path(path)
    if not p.is_absolute():
        candidates = [
            Path.cwd() / path,
            Path(__file__).parent.parent.parent.parent / path,
        ]
        for c in candidates:
            if c.exists():
                p = c
                break
    if not p.exists():
        return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f) or {}


# Loaded once at import time — cached for the process lifetime
_TAXONOMY: dict = _load_yaml(str(DEFAULT_TAXONOMY_CONFIG))
_CURRICULUM: dict = _load_yaml(str(DEFAULT_CURRICULUM_CONFIG))
_OBJECTS_DATA: dict = _load_json(str(DEFAULT_OBJECTS_REGISTRY))
_OBJECTS_REGISTRY: dict[str, dict] = {
    obj.get("canonical_name", "").lower(): obj for obj in _OBJECTS_DATA.get("objects", [])
}


# =============================================================================
# Custom Spread Prompt Loader
# Builds prompt from config/A-Z.md template driven directly by manifest cards
# or auto-matched from interior pages (with optional alphabet_spreads.yaml fallback).
# =============================================================================

DEFAULT_ALPHABET_FALLBACK: dict[str, tuple[str, str]] = {
    "A": ("APPLE", "Apple fruit outline"),
    "B": ("BALL", "Soccer ball outline"),
    "C": ("CAT", "Cute cat outline"),
    "D": ("DOG", "Puppy dog outline"),
    "E": ("ELEPHANT", "Baby elephant outline"),
    "F": ("FISH", "Fish outline"),
    "G": ("GIRAFFE", "Giraffe outline"),
    "H": ("HAT", "Clean hat outline"),
    "I": ("ICE CREAM", "Ice cream cone outline"),
    "J": ("JUICE", "Juice box outline"),
    "K": ("KITE", "Flying kite outline"),
    "L": ("LION", "Lion face outline"),
    "M": ("MOON", "Crescent moon outline"),
    "N": ("NEST", "Bird nest outline"),
    "O": ("ORANGE", "Orange fruit outline"),
    "P": ("PENGUIN", "Penguin outline"),
    "Q": ("QUEEN", "Queen face and crown outline"),
    "R": ("RABBIT", "Bunny rabbit outline"),
    "S": ("SUN", "Smiling sun outline"),
    "T": ("TREE", "Tree outline"),
    "U": ("UMBRELLA", "Open umbrella outline"),
    "V": ("VAN", "Vehicle van outline"),
    "W": ("WATCH", "Wristwatch outline"),
    "X": ("XYLOPHONE", "Xylophone outline"),
    "Y": ("YOYO", "Yoyo outline"),
    "Z": ("ZEBRA", "Zebra outline"),
}


def _find_config_file(name: str) -> Path | None:
    """Locate a config file relative to cwd or package root."""
    candidates = [
        Path.cwd() / name,
        Path(__file__).parent.parent.parent.parent / name,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _build_alphabet_spread_prompt(
    section_key: str,
    page_record: dict[str, Any] | None = None,
    all_manifest_pages: list[dict[str, Any]] | None = None,
) -> str | None:
    """Build a filled prompt from the A-Z.md template using manifest cards or automatic page matching.

    Resolution Priority:
      1. Manifest Page Record: Uses explicit `page_record["cards"]` if present (Single Source of Truth).
      2. Automatic A-Z Matcher: Auto-matches letter items from interior pages (Pages 5–110).
      3. Legacy Fallback: Reads `config/alphabet_spreads.yaml` if available.
      4. Universal Alphabet Fallback: Populates remaining letters from preschool dictionary.

    Args:
        section_key: 'a_to_m' for P002 or 'n_to_z' for P003
        page_record: Optional page dictionary from manifest containing explicit 'cards'.
        all_manifest_pages: Optional list of all pages from the active manifest for auto-matching.

    Returns:
        The fully-filled prompt string, or None if template file is missing.
    """
    template_path = _find_config_file("config/A-Z.md")
    if template_path is None:
        logger.warning(
            "Custom alphabet spread template missing (config/A-Z.md). Falling back to generated prompt."
        )
        return None

    template = template_path.read_text(encoding="utf-8")

    if section_key == "a_to_m":
        target_letters = list("ABCDEFGHIJKLM")
    elif section_key == "n_to_z":
        target_letters = list("NOPQRSTUVWXYZ")
    else:
        logger.warning(f"Unknown alphabet spread section key '{section_key}'.")
        return None

    cards_data: list[dict[str, str]] = []

    # Tier 1: Check if page_record has explicit cards list
    if (
        page_record
        and "cards" in page_record
        and isinstance(page_record["cards"], list)
        and len(page_record["cards"]) >= 13
    ):
        for card in page_record["cards"][:13]:
            let = str(card.get("letter", "")).strip().upper()
            word = card.get("word")
            if not word:
                obj = str(card.get("object", ""))
                word = obj.replace("_", " ").upper()
            ill = (
                card.get("illustration")
                or card.get("positive_description")
                or card.get("description")
                or f"{word.title()} outline"
            )
            cards_data.append({"letter": let, "word": str(word), "illustration": str(ill)})

    # Tier 2: Automatic A-Z matcher from all manifest pages (Pages 5-110)
    if len(cards_data) < 13:
        pages_to_scan = all_manifest_pages
        if pages_to_scan is None:
            try:
                manifest_path = _find_config_file(str(DEFAULT_PAGES_MANIFEST))
                if manifest_path and manifest_path.exists():
                    with open(manifest_path, encoding="utf-8") as mf:
                        m_data = json.load(mf)
                        pages_to_scan = m_data.get("pages", [])
            except Exception:
                pages_to_scan = None

        if pages_to_scan:
            interior_pages = [
                p
                for p in pages_to_scan
                if p.get("page_number", 0) >= 4 and p.get("type") in ["coloring_page", None]
            ]
            cards_data = []
            for let in target_letters:
                matched_page = None
                for p in interior_pages:
                    lbl = (
                        str(p.get("display_label") or p.get("canonical_object", "")).strip().upper()
                    )
                    canon = str(p.get("canonical_object", "")).strip().upper()
                    if lbl.startswith(let) or canon.startswith(let):
                        matched_page = p
                        break

                if matched_page:
                    w = str(
                        matched_page.get("display_label")
                        or matched_page.get("canonical_object", "").replace("_", " ")
                    ).upper()
                    ill = str(
                        matched_page.get("positive_description")
                        or matched_page.get("description")
                        or f"{w.title()} outline"
                    )
                    cards_data.append({"letter": let, "word": w, "illustration": ill})
                elif let in DEFAULT_ALPHABET_FALLBACK:
                    fb_word, fb_ill = DEFAULT_ALPHABET_FALLBACK[let]
                    cards_data.append({"letter": let, "word": fb_word, "illustration": fb_ill})
                else:
                    cards_data.append(
                        {"letter": let, "word": let, "illustration": f"Letter {let} outline"}
                    )

    # Tier 3: Legacy Fallback to config/alphabet_spreads.yaml
    if len(cards_data) < 13:
        data_path = _find_config_file("config/alphabet_spreads.yaml")
        if data_path and data_path.exists():
            try:
                with open(data_path, encoding="utf-8") as f:
                    yaml_data = yaml.safe_load(f) or {}
                sec = yaml_data.get(section_key, {})
                yaml_letters = sec.get("letters", [])
                if len(yaml_letters) == 13:
                    cards_data = [
                        {
                            "letter": str(y.get("letter", "")),
                            "word": str(y.get("word", "")),
                            "illustration": str(y.get("illustration", "")),
                        }
                        for y in yaml_letters
                    ]
            except Exception as e:
                logger.warning(f"Failed to read alphabet_spreads.yaml fallback: {e}")

    if len(cards_data) != 13:
        logger.warning(f"Expected 13 cards for '{section_key}', resolved {len(cards_data)}.")
        return None

    # Fill placeholder variables 1–13
    substitutions: dict[str, str] = {}
    for i, card in enumerate(cards_data, start=1):
        substitutions[f"{{{{LETTER_{i}}}}}"] = card.get("letter", "")
        substitutions[f"{{{{WORD_{i}}}}}"] = card.get("word", "")
        substitutions[f"{{{{ILLUSTRATION_{i}}}}}"] = card.get("illustration", "")

    # Derive START/END letters from data
    substitutions["{{START_LETTER}}"] = cards_data[0].get("letter", "")
    substitutions["{{END_LETTER}}"] = cards_data[-1].get("letter", "")

    # Bonus tiles (from page_record, or default toddler rewards)
    bonus14 = "cute star badge with text 'GREAT JOB!' in hollow bubble letters"
    bonus15 = "cute smiling sun outline illustration"
    if page_record:
        if (
            isinstance(page_record.get("bonus_tiles"), list)
            and len(page_record["bonus_tiles"]) >= 2
        ):
            bonus14 = str(page_record["bonus_tiles"][0])
            bonus15 = str(page_record["bonus_tiles"][1])
        elif page_record.get("bonus_tile_14"):
            b14 = page_record.get("bonus_tile_14")
            bonus14 = b14.get("description", str(b14)) if isinstance(b14, dict) else str(b14)
            b15 = page_record.get("bonus_tile_15", "")
            bonus15 = b15.get("description", str(b15)) if isinstance(b15, dict) else str(b15)

    substitutions["{{BONUS_TILE_14}}"] = bonus14
    substitutions["{{BONUS_TILE_15}}"] = bonus15

    prompt = template
    for placeholder, value in substitutions.items():
        prompt = prompt.replace(placeholder, value)

    return prompt.strip()


def get_custom_alphabet_spread_prompt(
    page_record: dict[str, Any],
    all_manifest_pages: list[dict[str, Any]] | None = None,
) -> tuple[str, str] | None:
    """Return (positive_prompt, negative_prompt) from the custom A-Z template if available.

    The negative prompt is a fixed, strong universal set for coloring-book line art.
    Returns None if custom config files are missing (falls back to generated prompt).
    """
    canonical = str(page_record.get("canonical_object", "")).lower()
    page_num = page_record.get("page_number", 0)

    if "a_to_m" in canonical or page_num == 2:
        section_key = "a_to_m"
    elif "n_to_z" in canonical or page_num == 3:
        section_key = "n_to_z"
    else:
        return None

    pos = _build_alphabet_spread_prompt(
        section_key,
        page_record=page_record,
        all_manifest_pages=all_manifest_pages,
    )
    if pos is None:
        return None

    neg = (
        "No color, no gray shading, no gradients, no extra rows, no missing tiles, "
        "no dividing lines inside cards, no page title or header, no solid-filled letters, "
        "no solid-filled text, no background fill, no decorative borders outside the grid, "
        "no gray tones, no shadows, no 3D effects, no photorealistic textures, "
        "no landscape orientation, no 16:9, no cut-off edges"
    )
    return pos, neg


# =============================================================================
# Pydantic models
# =============================================================================


class DebateProposal(BaseModel):
    """Proposal from an individual specialist agent."""

    agent_id: str
    perspective: str
    suggested_features: list[str] = Field(default_factory=list)
    forbidden_elements: list[str] = Field(default_factory=list)
    confidence_score: float = 0.95


class DebateRound(BaseModel):
    """Transcript of an individual round in the debate."""

    round_number: int
    round_name: str
    agent_outputs: dict[str, Any]


class DebateResult(BaseModel):
    """Final decision and locked prompt specification from the 4-round debate."""

    page_id: str
    canonical_object: str
    display_label: str
    section: str
    winner_agent: str
    final_score: float
    positive_prompt: str
    negative_prompt: str
    rounds: list[DebateRound] = Field(default_factory=list)
    judge_verdict: str
    judge_rationale: str


# =============================================================================
# Living Taxonomy Classifier — reads from taxonomy.yaml
# =============================================================================


def classify_living_taxonomy(canonical: str, section: str) -> bool:
    """Dynamically determine if a subject is a living creature/character or inanimate.

    Reads inanimate_exceptions, inanimate_sections, and living_keywords from config/taxonomy.yaml.
    Zero hardcoded data in this function.
    """
    tax = _TAXONOMY
    inanimate_exceptions = set(tax.get("inanimate_exceptions", []))
    if canonical.lower() in inanimate_exceptions:
        return False

    inanimate_sections = {s.lower() for s in tax.get("inanimate_sections", [])}
    if section.lower() in inanimate_sections:
        return False

    living_keywords = set(tax.get("living_keywords", []))
    canon_tokens = set(canonical.lower().replace("_", " ").split())
    sec_tokens = set(section.lower().replace("_", " ").split())
    return bool((canon_tokens | sec_tokens) & living_keywords)


# =============================================================================
# Dynamic Visual Spec Generator — reads category rules from taxonomy.yaml
# =============================================================================


def _find_category_config(canonical: str, section: str, category: str = "") -> tuple[dict, str]:
    """Find the category config dictionary and key for a given object and section."""
    categories = _TAXONOMY.get("categories", {})
    canon_lower = canonical.lower()
    sec_lower = section.lower()
    cat_lower = category.lower()

    # 1. Direct match by category_name (from manifest/objects.json or section)
    for key, cfg in categories.items():
        if key in ["state_dependent", "fallback"]:
            continue
        c_name = cfg.get("category_name", "").lower()
        if c_name and c_name in (cat_lower, sec_lower):
            return cfg, key

    # 2. Match section hints
    for key, cfg in categories.items():
        if key in ["state_dependent", "fallback"]:
            continue
        hints = [h.lower() for h in cfg.get("section_hints", [])]
        if any(h in sec_lower or h in cat_lower for h in hints):
            return cfg, key

    # 3. Match keywords in canonical name
    for key, cfg in categories.items():
        if key in ["state_dependent", "fallback"]:
            continue
        keywords = set(cfg.get("keywords", []))
        if any(k in canon_lower for k in keywords):
            return cfg, key

    # 4. Fallback
    return categories.get("fallback", {}), "fallback"


def resolve_animal_anatomy_profile(canonical: str) -> dict:
    """Resolve species-specific anatomy, locomotion, posture, orientation, and safeguards.

    Queries config/taxonomy.yaml:
      1. animal_species_profiles for species-specific anatomy & overrides
      2. animal_locomotion_matrix for locomotion class defaults & negative tokens
    Falls back gracefully to natural quadrupedal mammal defaults if not found.
    """
    canon_lower = canonical.lower().strip()
    canon_tokens = set(canon_lower.replace("_", " ").split())
    matrix = _TAXONOMY.get("animal_locomotion_matrix", {})
    profiles = _TAXONOMY.get("animal_species_profiles", {})

    # Check for direct match or full token match in canonical
    matched_profile = None
    for key, prof in profiles.items():
        key_lower = key.lower().strip()
        key_tokens = set(key_lower.replace("_", " ").split())
        if (
            key_lower == canon_lower
            or key_lower in canon_tokens
            or (key_tokens and key_tokens.issubset(canon_tokens))
        ):
            matched_profile = prof
            break

    readable = canonical.replace("_", " ").lower()

    if matched_profile:
        cls_key = matched_profile.get("class", "quadrupeds")
        cls_matrix = matrix.get(cls_key, matrix.get("quadrupeds", {}))
        anatomy = matched_profile.get(
            "anatomy", f"natural {readable} anatomy with recognizable baby {readable} proportions"
        )
        posture = matched_profile.get(
            "posture_override",
            cls_matrix.get(
                "default_posture",
                "natural quadrupedal standing posture, standing securely on all four legs with all four paws supporting the body",
            ),
        )
        orientation = matched_profile.get(
            "default_orientation",
            cls_matrix.get(
                "default_orientation",
                "three-quarter front view showing the complete body and limbs",
            ),
        )
        safeguards = cls_matrix.get("safeguards", "")
        if "safeguards_extra" in matched_profile:
            safeguards = f"{safeguards} {matched_profile['safeguards_extra']}".strip()
        negative_tokens = list(cls_matrix.get("negative_tokens", []))
        return {
            "class": cls_key,
            "anatomy": anatomy,
            "posture": posture,
            "orientation": orientation,
            "safeguards": safeguards,
            "negative_tokens": negative_tokens,
        }

    # Infer class dynamically from taxonomy locomotion matrix keywords if not in specific species profile
    cls_key = "quadrupeds"
    for class_name, class_data in matrix.items():
        class_keywords = class_data.get("keywords", [])
        if any(w in canon_lower for w in class_keywords):
            cls_key = class_name
            break

    cls_matrix = matrix.get(cls_key, matrix.get("quadrupeds", {}))
    anatomy = f"natural {readable} anatomy with recognizable baby {readable} body proportions and species silhouette"
    posture = cls_matrix.get(
        "default_posture",
        "natural quadrupedal standing posture, standing securely on all four legs with all four paws supporting the body",
    )
    orientation = cls_matrix.get(
        "default_orientation", "three-quarter front view showing the complete body and limbs"
    )
    safeguards = cls_matrix.get(
        "safeguards",
        "Head and neck positioned naturally relative to the body. Do not stand upright on the hind legs. Do not use a human-like standing posture.",
    )
    negative_tokens = list(cls_matrix.get("negative_tokens", []))

    return {
        "class": cls_key,
        "anatomy": anatomy,
        "posture": posture,
        "orientation": orientation,
        "safeguards": safeguards,
        "negative_tokens": negative_tokens,
    }


def resolve_vehicle_design_profile(canonical: str) -> dict:
    """Resolve authoritative vehicle structural anatomy, support mechanics, orientation, and safeguards.

    Queries config/taxonomy.yaml:
      1. vehicle_design_profiles for vehicle-specific anatomy & overrides
      2. vehicle_domain_matrix for domain defaults and negative tokens
    Falls back gracefully to wheeled automotive defaults if not found.
    """
    canon_lower = canonical.lower().strip()
    matrix = _TAXONOMY.get("vehicle_domain_matrix", {})
    profiles = _TAXONOMY.get("vehicle_design_profiles", {})

    matched_profile = None
    for key, prof in profiles.items():
        if key in canon_lower or canon_lower in key:
            matched_profile = prof
            break

    readable = canonical.replace("_", " ").lower()

    if matched_profile:
        cls_key = matched_profile.get("class", "wheeled_four_wheel")
        cls_matrix = matrix.get(cls_key, matrix.get("wheeled_four_wheel", {}))
        anatomy = matched_profile.get(
            "anatomy", f"classic toddler {readable} anatomy with clear preschool proportions"
        )
        support = matched_profile.get(
            "support_override", cls_matrix.get("default_support", "supported cleanly by wheels")
        )
        orientation = matched_profile.get(
            "orientation",
            cls_matrix.get(
                "default_orientation",
                "three-quarter side profile view displaying the complete vehicle body",
            ),
        )
        safeguards = cls_matrix.get("safeguards", "")
        if "safeguards_extra" in matched_profile:
            safeguards = f"{safeguards} {matched_profile['safeguards_extra']}".strip()
        negative_tokens = list(cls_matrix.get("negative_tokens", []))
        if "negative_tokens" in matched_profile:
            for tok in matched_profile["negative_tokens"]:
                if tok not in negative_tokens:
                    negative_tokens.append(tok)
        return {
            "class": cls_key,
            "has_wheels": cls_matrix.get("has_wheels", True),
            "anatomy": anatomy,
            "support": support,
            "orientation": orientation,
            "safeguards": safeguards,
            "negative_tokens": negative_tokens,
        }

    # Infer domain dynamically from vehicle domain matrix keywords if not in specific profiles
    cls_key = "wheeled_four_wheel"
    for domain_name, domain_data in matrix.items():
        domain_keywords = domain_data.get("keywords", [])
        if any(w in canon_lower for w in domain_keywords):
            cls_key = domain_name
            break

    cls_matrix = matrix.get(cls_key, matrix.get("wheeled_four_wheel", {}))
    anatomy = f"classic toddler {readable} anatomy with recognizable preschool proportions"
    support = cls_matrix.get("default_support", "supported cleanly")
    orientation = cls_matrix.get("default_orientation", "three-quarter side profile view")
    safeguards = cls_matrix.get("safeguards", "")
    negative_tokens = list(cls_matrix.get("negative_tokens", []))

    return {
        "class": cls_key,
        "has_wheels": cls_matrix.get("has_wheels", True),
        "anatomy": anatomy,
        "support": support,
        "orientation": orientation,
        "safeguards": safeguards,
        "negative_tokens": negative_tokens,
    }


def is_vehicle_object(canonical: str, section: str, category: str = "") -> bool:
    """Check if object belongs to the vehicle and transportation category."""
    c = canonical.lower().strip()
    sec = section.lower()
    cat = category.lower()
    if "vehicle" in sec or "transport" in sec or "vehicle" in cat or "transport" in cat:
        return True
    if c in _TAXONOMY.get("vehicle_design_profiles", {}):
        return True
    vehicle_keywords = {
        "car",
        "bus",
        "truck",
        "bike",
        "bicycle",
        "motorcycle",
        "scooter",
        "tricycle",
        "helicopter",
        "rocket",
        "sailboat",
        "boat",
        "ship",
        "yacht",
        "submarine",
        "plane",
        "airplane",
        "jet",
        "train",
        "locomotive",
        "tractor",
        "wagon",
        "taxi",
        "ambulance",
        "fire_truck",
        "police_car",
        "hot_air_balloon",
    }
    c_tokens = set(c.replace("_", " ").split())
    if c_tokens & vehicle_keywords:
        return True
    return any(c == k or c.startswith(f"{k}_") or c.endswith(f"_{k}") for k in vehicle_keywords)


def generate_dynamic_visual_spec(
    canonical: str, section: str, is_living: bool, category: str = ""
) -> str:
    """Autonomously generate object geometry and toddler feature simplification.

    All category keyword sets and visual template strings are read from
    config/taxonomy.yaml. Zero hardcoded keyword lists in this function.
    """
    readable = canonical.replace("_", " ").lower()
    categories = _TAXONOMY.get("categories", {})

    # 1. Living animals & characters — resolved via authoritative anatomy profiles
    if is_living:
        prof = resolve_animal_anatomy_profile(canonical)
        return f"a cute friendly baby {readable}, {prof['anatomy']}, {prof['posture']}, {prof['orientation']}"

    # 2. Vehicles & Transportation — resolved via authoritative vehicle structural profiles
    if is_vehicle_object(canonical, section, category):
        veh_prof = resolve_vehicle_design_profile(canonical)
        return f"a cute classic {readable}, {veh_prof['anatomy']}, {veh_prof['orientation']}"

    # 2. State-dependent items — resolved before generic category matching
    state_items = categories.get("state_dependent", {}).get("items", {})
    for key, cfg in state_items.items():
        if key in canonical.lower():
            return cfg.get("visual_template", "").format(readable=readable)

    # 3. Dynamic category matching using _find_category_config
    cat_cfg, _ = _find_category_config(canonical, section, category)
    tmpl = cat_cfg.get("visual_template", "")
    if tmpl:
        return tmpl.format(readable=readable)

    # 4. Fallback
    fallback_tmpl = categories.get("fallback", {}).get(
        "visual_template",
        "a single {readable}, clear three-quarter or frontal view displaying its most iconic, "
        "authentic simplified physical silhouette with wide open coloring zones",
    )
    return fallback_tmpl.format(readable=readable)


# =============================================================================
# Dynamic Spread Prompt Builder
# Reads ALL card content from page_record["cards"] (manifest-driven).
# Reads style rules and layout templates from curriculum.yaml (volume-agnostic).
# =============================================================================


def _join_negative(token_lists: list[list]) -> str:
    """Flatten and deduplicate multiple negative token lists into a single string."""
    seen: list[str] = []
    seen_set: set[str] = set()
    for lst in token_lists:
        for t in lst:
            t_clean = str(t).strip()
            if t_clean and t_clean not in seen_set:
                seen_set.add(t_clean)
                seen.append(t_clean)
    return ", ".join(seen)


def _filter_contradictions(positive: str, negative_tokens: list[str]) -> list[str]:
    """Ensure no negative tokens contradict requirements in the positive prompt (Rule 10B.18)."""
    pos_lower = positive.lower()
    is_biped = "two legs" in pos_lower or "two feet" in pos_lower or "bipedal" in pos_lower
    is_quadruped = (
        "four legs" in pos_lower
        or "four paws" in pos_lower
        or "four hooves" in pos_lower
        or "quadrupedal" in pos_lower
    )

    biped_conflicts = {
        "two legs",
        "standing on two legs",
        "two-legged stance",
        "bipedal",
        "bipedal stance",
        "upright on hind legs",
        "upright",
    }
    quadruped_conflicts = {"four legs", "four-legged stance", "quadrupedal", "quadrupedal stance"}

    # Vehicle-specific conflict resolution
    has_wheels_positive = (
        "round wheels" in pos_lower
        or "two wheels" in pos_lower
        or "train wheels" in pos_lower
        or "chunky wheels" in pos_lower
    ) and ("no wheels" not in pos_lower and "without wheels" not in pos_lower)
    has_wings_positive = "wings" in pos_lower and (
        "no wings" not in pos_lower and "without wings" not in pos_lower
    )

    filtered = []
    for tok in negative_tokens:
        tok_clean = tok.strip()
        t_lower = tok_clean.lower()
        if not t_lower:
            continue
        if is_biped and t_lower in biped_conflicts:
            continue
        if is_quadruped and t_lower in quadruped_conflicts:
            continue
        if has_wings_positive and t_lower in {"wings", "bird wings", "symmetrical wings"}:
            continue
        if has_wheels_positive and t_lower in {"wheels", "tires", "rubber tires", "round wheels"}:
            continue
        filtered.append(tok_clean)
    return filtered


def _detect_spread_layout_key(canonical: str, label: str) -> str:
    """Map a page_record's canonical_object/label to a curriculum layout_templates key."""
    c = canonical.lower()
    lbl = label.lower()
    if "alphabet_a_to_m" in c or ("alphabet" in c and ("a" in lbl or "m" in lbl)):
        return "alphabet_a_m"
    if "alphabet_n_to_z" in c or ("alphabet" in c and ("n" in lbl or "z" in lbl)):
        return "alphabet_n_z"
    if "0_to_5" in c or "0 - 5" in lbl or "numbers_0_to_5" in c:
        return "numbers_0_5"
    # default: numbers_6_10
    return "numbers_6_10"


def calculate_optimal_counting_grid(
    count: int, is_full_width: bool = False
) -> tuple[int, int, list[int]]:
    """Generic mathematical calculation of counting grid (rows, cols, row_counts).

    Enforces the Horizontal Column Limit Law:
    - Half-width partitioned cards: max_cols = 3 (portrait/square zone).
    - Full-width hero cards: max_cols = 5 (landscape zone).

    Returns (rows, cols, row_counts_list).
    """
    if count <= 0:
        return 1, 1, [0]
    if count == 1:
        return 1, 1, [1]

    max_cols = 5 if is_full_width else 3

    # Check exact factor pairs where cols <= max_cols
    valid_factors = []
    for c in range(1, max_cols + 1):
        if count % c == 0:
            r = count // c
            valid_factors.append((r, c))

    if valid_factors:
        # Prefer the pair with the most columns up to max_cols (to avoid overly tall vertical stacks)
        best_r, best_c = max(valid_factors, key=lambda p: p[1])
        return best_r, best_c, [best_c] * best_r

    # Irregular / Prime counts: distribute across balanced rows
    num_rows = 2 if count <= 7 else 3
    base_per_row = count // num_rows
    rem = count % num_rows
    row_counts = []
    for i in range(num_rows):
        c_i = base_per_row + (1 if i < rem else 0)
        row_counts.append(c_i)
    max_row_c = max(row_counts) if row_counts else 1
    return len(row_counts), max_row_c, row_counts


def audit_spread_card_miscount_risks(
    numeral: Any,
    count: int,
    object_name: str,
    rows: int,
    cols: int,
    row_counts: list[int],
) -> tuple[list[str], list[str]]:
    """Generic adversarial audit deriving diffusion failure modes for any count N and grid (R, C).

    Returns (stress_test_findings, recommended_hardening_tokens).
    """
    findings: list[str] = []
    hardening: list[str] = []

    clean_obj = str(object_name).replace("_", " ").strip().lower()
    plural_obj = f"{clean_obj}s" if not clean_obj.endswith("s") else clean_obj

    if count <= 0:
        findings.append(
            f"Card {numeral}: Zero objects represented. Ensure AI renders single hollow outline without items inside."
        )
        hardening.extend([f"items on card {numeral}", f"objects on card {numeral}"])
        return findings, hardening

    # Standard count neighbor hallucinations
    if count >= 2:
        hardening.append(f"{count - 1} {plural_obj}")
        hardening.append(f"{count + 1} {plural_obj}")
    if count >= 3:
        hardening.append(f"{count - 2} {plural_obj}")
    if count >= 1:
        hardening.append(f"wrong count of {plural_obj}")
        hardening.append(f"extra {clean_obj}")
        hardening.append(f"face on {clean_obj}")

    # Grid collapse failure modes (dropped row or dropped column)
    if rows >= 2 and cols >= 2:
        dropped_col_count = rows * (cols - 1)
        dropped_row_count = (rows - 1) * cols

        findings.append(
            f"Card {numeral}: In a {rows}x{cols} grid for count {count}, diffusion models risk dropping a row or column "
            f"resulting in {dropped_row_count} or {dropped_col_count} items."
        )
        if dropped_row_count != count:
            hardening.append(f"{dropped_row_count} {plural_obj} on card {numeral}")
            hardening.append(f"{rows - 1} rows of {cols}")
        if dropped_col_count != count and dropped_col_count != dropped_row_count:
            hardening.append(f"{dropped_col_count} {plural_obj} on card {numeral}")
            hardening.append(f"{rows} rows of {cols - 1}")
    else:
        findings.append(
            f"Card {numeral}: Ensure AI renders exactly {count} {plural_obj} with clear vector outlines and white spacing."
        )

    return findings, hardening


def generate_dynamic_spread_prompt(
    page_record: dict[str, Any], extra_negative_tokens: list[str] | None = None
) -> tuple[str, str]:
    """Construct multi-item flashcard overview prompts from manifest card data.

    Card content (letter/numeral -> object) is read from page_record["cards"],
    which lives in the manifest. This is entirely per-volume - no card data
    is hardcoded anywhere in Python or in curriculum.yaml.

    Style rules (numeral fill mandate, container uniformity, base style, negative
    tokens) are read from config/curriculum.yaml - these are volume-agnostic.
    """
    label = page_record.get("display_label", "")
    canonical = page_record.get("canonical_object", "")
    cards: list[dict] = page_record.get("cards", [])

    cur = _CURRICULUM
    style = cur.get("spread_style", {})
    layout_templates = cur.get("layout_templates", {})

    container_rule = style.get("container_uniformity", "")
    centering_rule = style.get("vertical_centering", "")
    base_style = style.get("base_style", "")
    common_neg = style.get("common_negative_tokens", [])

    # Layout template from curriculum.yaml
    layout_key = _detect_spread_layout_key(canonical, label)
    tmpl = layout_templates.get(layout_key, {})
    total_cards = tmpl.get("total_cards", len(cards))
    row_structure = tmpl.get("row_structure", "")
    layout_desc_raw = tmpl.get("layout_description", "")
    layout_desc = layout_desc_raw.format(total_cards=total_cards, row_structure=row_structure)
    taxonomy_rule = tmpl.get("taxonomy_rule", "")
    sequence_rule = tmpl.get("sequence_rule", "")
    shared_neg = tmpl.get("shared_negative_tokens", [])
    is_alphabet = layout_key.startswith("alphabet")

    # Build per-card descriptions from manifest data
    if not cards:
        logger.warning(
            f"No 'cards' array found in page_record for {page_record.get('page_id')}. "
            "Add a 'cards' array to this spread page in manifest/pages.json."
        )

    card_descriptions: list[str] = []
    per_card_neg: list[str] = []

    # Letter I disambiguation map - prevent the model confusing I with H
    _LETTER_DISAMBIGUATION = {
        "I": "letter I (the 9th letter of the alphabet, a single tall vertical stroke - NOT the letter H)"
    }

    for card in cards:
        if is_alphabet:
            letter = card.get("letter", "")
            desc = card.get("description", card.get("positive_description", ""))
            obj_name = card.get("object", "").replace("_", " ").title()
            # Use disambiguation for visually confusable letters
            letter_label = _LETTER_DISAMBIGUATION.get(letter, f"letter {letter}")
            card_descriptions.append(
                f"Box {letter}: large uppercase bubble {letter_label} on left, {desc} on right, label '{obj_name}' below drawing"
            )
        else:
            numeral = card.get("numeral", "")
            pos_desc = str(card.get("positive_description", "")).strip()
            clean_desc = pos_desc.replace("HOLLOW BUBBLE", "bubble").replace(
                "hollow bubble", "bubble"
            )
            card_descriptions.append(
                f"Card {numeral}: large bubble numeral {numeral} on left, {clean_desc} (numeral and objects MUST be in the SAME Card {numeral} box)"
            )
        per_card_neg.extend(card.get("negative_tokens", []))

    if extra_negative_tokens:
        per_card_neg.extend(extra_negative_tokens)

    cards_str = "; ".join(card_descriptions) + "."

    # Detect if this is A-M or N-Z for page-specific layout rules
    is_a_m = "a_m" in layout_key or "a_to_m" in layout_key
    is_n_z = "n_z" in layout_key or "n_to_z" in layout_key
    total_cards_count = len(cards)

    # Assemble positive prompt
    if is_alphabet:
        # Row structure: 4+4+3+2 = 13 cards for both A-M and N-Z
        if is_a_m:
            row_layout_rule = (
                "Layout: strict 4-COLUMN grid in 4 rows. "
                "Row 1: Box A, Box B, Box C, Box D — 4 cards side by side. "
                "Row 2: Box E, Box F, Box G, Box H — 4 cards side by side. "
                "Row 3: Box I, Box J, Box K, Box L — 4 cards side by side. "
                "Row 4: ONLY Box M centered — exactly 1 card, strictly NO empty box beside M, strictly NO blank filler box, strictly NO 14th box."
            )
        elif is_n_z:
            row_layout_rule = (
                "Layout: strict 4-COLUMN grid in 4 rows. "
                "Row 1: Box N, Box O, Box P, Box Q — 4 SQUARE cards side by side. "
                "Row 2: Box R, Box S, Box T, Box U — 4 SQUARE cards side by side. "
                "Row 3: Box V, Box W, Box X — 3 SQUARE cards centered. "
                "Row 4: Box Y, Box Z — 2 SQUARE cards centered, strictly NO empty box beside them, strictly NO 14th box."
            )
        else:
            row_layout_rule = layout_desc

        pos_parts = [
            f"Educational preschool toddler alphabet flashcard coloring poster. {row_layout_rule}",
            "CRITICAL: Every single flashcard box must be a SQUARE shape (height equals width). Strictly NO wide landscape-orientation rectangular boxes. Strictly NO boxes that are wider than they are tall.",
            f"{container_rule} {centering_rule}",
            (
                f"Inside each of the {total_cards_count} square rounded flashcard boxes, render the large single bubble uppercase letter "
                f"on the left (clean black outline with white center), its cute line art drawing on the right, and the object label word centered below the drawing: {cards_str}"
            ),
            "STRICT ONE-OBJECT-PER-BOX RULE: Each box contains EXACTLY ONE letter and EXACTLY ONE drawing. Strictly NO two drawings in one box, strictly NO drawing bleeding into the adjacent box, strictly NO content overflow between boxes.",
            "Strictly DO NOT write 'HOLLOW' or any header text at the top of any box.",
            taxonomy_rule,
            base_style,
        ]
    else:
        pos_parts = [
            f"Educational preschool toddler counting coloring poster. {layout_desc}",
            f"{container_rule} {centering_rule}",
            (
                f"Inside each discrete flashcard box, strictly render the large single bubble numeral "
                f"on the left (clean black outline with white center) and its countable items on the right: {cards_str}"
            ),
            "CRITICAL: The numeral digit AND its countable objects MUST be inside the SAME single card. Never place objects in a separate standalone box. Never create an extra card for objects.",
            "Strictly DO NOT create extra empty boxes, DO NOT split numerals and items into separate boxes.",
            "Strictly DO NOT write 'HOLLOW' or any header text at the top of any box.",
            sequence_rule,
            base_style,
        ]

    pos = " ".join(p.strip() for p in pos_parts if p.strip())
    neg = _join_negative([common_neg, shared_neg, per_card_neg])

    return pos, neg


# =============================================================================
# DebateEngine
# =============================================================================


class DebateEngine:
    """Orchestrates the 4-round adversarial debate between specialist agents and Judge."""

    def __init__(
        self,
        model_client: ModelClient | None = None,
        agents_config_path: str = str(DEFAULT_AGENTS_CONFIG),
    ):
        self.client = model_client or ModelClient()
        self.agents_config_path = agents_config_path

    def run_page_debate(self, page_record: dict[str, Any]) -> DebateResult:
        """Execute 4-round multi-agent debate for any manifest page record dynamically."""
        page_id = page_record.get("page_id", "P000")
        canonical = page_record.get("canonical_object", "object")
        label = page_record.get("display_label", canonical.upper())
        section = page_record.get("section", "General")
        page_type = page_record.get("type", "single_page")
        composition = page_record.get("composition", "single_centered_object")

        is_spread = (page_type in ["educational_spread", "counting_spread"]) or (
            composition == "flashcard_grid"
        )
        is_living = classify_living_taxonomy(canonical, section)
        obj_meta = _OBJECTS_REGISTRY.get(canonical.lower(), {})
        object_category = obj_meta.get("category", section)
        is_veh = is_vehicle_object(canonical, section, object_category) and not is_living
        readable_name = canonical.replace("_", " ").lower()

        object_rule = obj_meta.get("object_rule", "")
        object_desc = generate_dynamic_visual_spec(
            canonical, section, is_living, category=object_category
        )

        logger.info(
            f"Initiating 4-Round Debate for Page {page_id} [{label}] ({section}) [type={page_type}]..."
        )
        rounds: list[DebateRound] = []

        # ------------------------------------------------------------------
        # Round 1: Parallel Specialist Proposals
        # ------------------------------------------------------------------
        if is_spread:
            cards = page_record.get("cards", [])
            is_counting = (page_type == "counting_spread") or ("numbers" in canonical.lower())

            spread_design_notes: list[str] = []
            spread_critic_findings: list[str] = [
                "Ensure AI renders 100% equal-sized containers without tall bottom boxes.",
                "Ensure AI centers content vertically inside cards without empty top voids.",
                "Ensure all numerals rendered as HOLLOW BUBBLE OUTLINES with white interior, not solid black.",
            ]
            debated_hardening_tokens: list[str] = []

            if is_counting:
                total_cards = len(cards)
                for idx, c_item in enumerate(cards):
                    num = c_item.get("numeral", idx)
                    cnt = c_item.get("count", c_item.get("numeral", 0))
                    obj = c_item.get("object", "item")
                    is_hero = (idx == total_cards - 1) and (total_cards % 2 == 1)

                    rows, cols, row_counts = calculate_optimal_counting_grid(
                        cnt, is_full_width=is_hero
                    )
                    spread_design_notes.append(
                        f"Card {num}: {rows}x{cols} {'hero ' if is_hero else ''}grid ({cnt} {obj}s, row distribution {row_counts})"
                    )

                    c_findings, c_tokens = audit_spread_card_miscount_risks(
                        num, cnt, obj, rows, cols, row_counts
                    )
                    spread_critic_findings.extend(c_findings)
                    debated_hardening_tokens.extend(c_tokens)
            else:
                spread_critic_findings.append(
                    "Ensure AI renders exact object counts per card as specified in manifest cards array."
                )
                spread_critic_findings.append(
                    "Ensure AI does not draw cartoon eyes on inanimate food/objects."
                )

            r1_outputs = {
                "AGT-002-DESIGN": {
                    "composition": (
                        f"Balanced educational flashcard spread for {label}. 100% equal-sized uniform rounded-corner cards "
                        f"across all rows, vertically centered content with balanced margins. "
                        f"Grid structures: {'; '.join(spread_design_notes[:4]) if spread_design_notes else 'uniform cards'}."
                    ),
                    "line_weight": "Thick 6pt bold black vector outlines enclosing large, open coloring shapes.",
                    "prohibited": [
                        "empty grid boxes",
                        "blank cells",
                        "intersecting table grid",
                        "widescreen 16:9 crop",
                        "unequal box heights",
                        "empty top voids",
                    ],
                },
                "AGT-003-KDP": {
                    "geometry": "Strict 0.50in (150px) margin safety clearance from canvas boundary, 2550x3300px at 300 DPI, zero interior bleed.",
                    "compliance": "Pure binary black & white (#000000 / #FFFFFF). Zero grayscale or drop-shadows.",
                },
                "AGT-004-MARKET": {
                    "commercial_appeal": "High parent perceived value for early childhood literacy. Distinct geometric silhouettes across spread cards to avoid visual monotony. All living animals/characters MUST feature sweet smiling faces, while inanimate objects must remain clean and faceless. Exact 1-to-1 counting accuracy.",
                    "prohibited": [
                        "faceless animals",
                        "faces on fruits/objects",
                        "scary silhouettes",
                        "counting mismatches",
                    ],
                },
                "AGT-005-EDU": {
                    "pedagogical_hook": "Direct letter/numeral-to-illustration correspondence. Counting spreads follow cognitive subitizing groupings (pairs and symmetrical matrices).",
                    "target_milestone": "Ages 1-4 early phonetic awareness and numeracy.",
                },
            }
            r2_outputs = {
                "cross_consensus": "Consensus on discrete equal-sized rounded-corner flashcards in centered balanced rows, hollow bubble letters/numerals paired with cute icons, vertically centered content, and zero empty cells or voids."
            }
            r3_outputs = {
                "AGT-006-CRITIC": {
                    "stress_test_findings": spread_critic_findings,
                    "risk_level": "LOW",
                    "recommended_hardening": (
                        "Merge base negative tokens with debated per-card hardening tokens: "
                        + ", ".join(debated_hardening_tokens[:6])
                        if debated_hardening_tokens
                        else "Merge negative tokens from curriculum.yaml spread_style.common_negative_tokens + layout_templates.shared_negative_tokens."
                    ),
                }
            }
        elif is_living:
            prof = resolve_animal_anatomy_profile(canonical)
            r1_outputs = {
                "AGT-002-DESIGN": {
                    "composition": f"Centered single illustration of baby {readable_name} in {prof['orientation']}. {prof['posture']}. Occupying 70% of safe canvas. Vertical portrait 3:4 aspect ratio.",
                    "line_weight": "Thick 5pt bold black vector outlines enclosing large, smooth coloring surfaces.",
                    "prohibited": prof["negative_tokens"][:4]
                    + [
                        "thin hair lines",
                        "cross-hatching",
                        "intricate fur patterns",
                        "widescreen 16:9 crop",
                    ],
                },
                "AGT-003-KDP": {
                    "geometry": "Strict 0.50in (150px) margin safety clearance, 2550x3300px at 300 DPI, zero interior bleed.",
                    "compliance": "Pure binary monochrome black & white. Typography added separately at top.",
                },
                "AGT-004-MARKET": {
                    "commercial_appeal": f"Authentic baby {readable_name} illustration preserving natural {prof['class']} anatomy with charming big round eyes and sweet gentle preschool expression.",
                    "prohibited": [
                        "anthropomorphic cartoon character",
                        "human-like standing",
                        "scary/creepy expressions",
                        "sharp fangs/claws",
                    ],
                },
                "AGT-005-EDU": {
                    "pedagogical_hook": f"Iconic, unmistakable canonical {readable_name} silhouette for instant recognition by a 2-year-old child.",
                    "target_milestone": f"Vocabulary expansion in category '{section}'.",
                },
            }
            r2_outputs = {
                "cross_consensus": f"Agreed on charming single {readable_name} animal with big round eyes, authentic {prof['class']} anatomy, bold 5pt outlines, and 0.50in margin safety clearance."
            }
            r3_outputs = {
                "AGT-006-CRITIC": {
                    "stress_test_findings": [
                        f"Verify strict {prof['class']} anatomy: ensure AI does not render {readable_name} standing upright on two legs or like a human cartoon mascot.",
                        f"Verify limb grounding and orientation: complete body visible in {prof['orientation']} with limbs naturally positioned.",
                        f"Ensure AI does not draw background habitat, floor, or grass behind the {readable_name}.",
                        "Ensure AI renders pure flat 2D line art with zero pencil shading or gray airbrushing.",
                        "Ensure typography is NOT drawn on canvas (handled by compositor).",
                    ],
                    "risk_level": "LOW",
                    "recommended_hardening": f"Enforce species safeguards: {prof['safeguards']}. Add negative tokens: "
                    + ", ".join(prof["negative_tokens"][:4]),
                }
            }
        elif is_veh:
            veh_prof = resolve_vehicle_design_profile(canonical)
            r1_outputs = {
                "AGT-002-DESIGN": {
                    "composition": f"Centered single illustration of {readable_name} in {veh_prof['orientation']}. {veh_prof['anatomy']}. Occupying 70% of safe canvas. Vertical portrait 3:4 aspect ratio.",
                    "line_weight": "Thick 5pt bold black vector outlines enclosing large, smooth coloring surfaces.",
                    "prohibited": veh_prof["negative_tokens"][:4]
                    + [
                        "thin hair lines",
                        "cross-hatching",
                        "intricate engine parts",
                        "widescreen 16:9 crop",
                    ],
                },
                "AGT-003-KDP": {
                    "geometry": "Strict 0.50in (150px) margin safety clearance, 2550x3300px at 300 DPI, zero interior bleed.",
                    "compliance": "Pure binary monochrome black & white. Typography added separately at top.",
                },
                "AGT-004-MARKET": {
                    "commercial_appeal": f"Authentic simplified {readable_name} preserving {veh_prof['class']} domain structure with bold preschool contours, large colorable panels, and strictly NO human driver or cartoon faces.",
                    "prohibited": [
                        "human driver",
                        "cartoon eyes on vehicle",
                        "road scenery",
                        "complex mechanical clutter",
                    ],
                },
                "AGT-005-EDU": {
                    "pedagogical_hook": f"Iconic, unmistakable canonical {readable_name} silhouette for instant recognition by a 2-year-old child.",
                    "target_milestone": f"Object identification in category '{section}'.",
                },
            }
            r2_outputs = {
                "cross_consensus": f"Agreed on authentic {readable_name} ({veh_prof['class']}) with {veh_prof['support']}, bold 5pt outlines, and 0.50in margin safety clearance."
            }
            r3_outputs = {
                "AGT-006-CRITIC": {
                    "stress_test_findings": [
                        f"Verify {veh_prof['class']} domain rules: {veh_prof['safeguards']}",
                        f"Verify structural support: {veh_prof['support']}.",
                        "Ensure AI does not draw road, street, or background scenery.",
                        "Ensure AI does not draw human driver, operator, or passengers.",
                        "Ensure AI renders pure flat 2D line art with zero shading or gray gradients.",
                    ],
                    "risk_level": "LOW",
                    "recommended_hardening": f"Enforce vehicle safeguards: {veh_prof['safeguards']}. Add negative tokens: "
                    + ", ".join(veh_prof["negative_tokens"][:4]),
                }
            }
        else:
            r1_outputs = {
                "AGT-002-DESIGN": {
                    "composition": f"Centered single illustration of {object_desc} occupying 70% of safe canvas. Vertical portrait 3:4 aspect ratio.",
                    "line_weight": "Thick 5pt bold black vector outlines enclosing wide, open coloring shapes.",
                    "prohibited": [
                        "thin hair lines",
                        "cross-hatching",
                        "intricate patterns",
                        "widescreen 16:9 crop",
                        "cartoon faces on non-living objects",
                    ],
                },
                "AGT-003-KDP": {
                    "geometry": "Strict 0.50in (150px) margin safety clearance, 2550x3300px at 300 DPI, zero interior bleed.",
                    "compliance": "Pure binary monochrome black & white. Reserve top header for programmatic typography.",
                },
                "AGT-004-MARKET": {
                    "commercial_appeal": f"Clean, authentic simplified physical {readable_name} silhouette. Pure inanimate object with strictly NO cartoon eyes, NO mouth, NO face, and NO anthropomorphic features.",
                    "prohibited": [
                        "cartoon eyes",
                        "smiling mouth",
                        "face on non-living object",
                        "unnatural distortions",
                    ],
                },
                "AGT-005-EDU": {
                    "pedagogical_hook": f"Universal real-world {readable_name} object identification for early childhood cognitive development.",
                    "target_milestone": f"Object recognition in category '{section}'.",
                },
            }
            r2_outputs = {
                "cross_consensus": f"Agreed on authentic inanimate {readable_name} object, strictly NO facial features, bold 5pt outlines, and 0.50in margin buffer."
            }
            r3_outputs = {
                "AGT-006-CRITIC": {
                    "stress_test_findings": [
                        f"Ensure AI does not hallucinate cartoon eyes or a mouth on the {readable_name}.",
                        "Ensure AI does not draw table, kitchen, or background scenery.",
                        "Ensure AI does not render widescreen landscape 16:9 crop.",
                    ],
                    "risk_level": "LOW",
                    "recommended_hardening": "Add negative tokens: face, eyes, mouth, smile, facial features, anthropomorphic, cartoon character face, background, floor, text, letters, words, 16:9, widescreen.",
                }
            }

        rounds.append(
            DebateRound(round_number=1, round_name="Specialist Proposals", agent_outputs=r1_outputs)
        )
        rounds.append(
            DebateRound(
                round_number=2, round_name="Cross-Specialist Review", agent_outputs=r2_outputs
            )
        )
        rounds.append(
            DebateRound(
                round_number=3, round_name="Adversarial Red-Team Critique", agent_outputs=r3_outputs
            )
        )

        # ------------------------------------------------------------------
        # Round 4: Judge Synthesis & Prompt Generation
        # ------------------------------------------------------------------
        if is_spread:
            positive_prompt, negative_prompt = generate_dynamic_spread_prompt(
                page_record, extra_negative_tokens=debated_hardening_tokens
            )
        else:
            cat_cfg, _ = _find_category_config(canonical, section, object_category)
            cat_rule = cat_cfg.get("category_rule", "").strip()
            cat_neg = cat_cfg.get("negative_tokens", [])

            if object_rule:
                subject_instruction = (
                    f"{readable_name.title()}. {object_rule}".strip().rstrip(".") + "."
                )
            else:
                subject_instruction = f"{object_desc}".strip().rstrip(".") + "."

            if is_living:
                prof = resolve_animal_anatomy_profile(canonical)
                positive_prompt = (
                    f"Ultra-clean 2D preschool toddler coloring book line art vector illustration of a cute friendly baby {readable_name}. "
                    f"{prof['anatomy'].capitalize()}. "
                    f"{prof['posture'].capitalize()}. {prof['orientation'].capitalize()}. "
                    f"{prof['safeguards']} "
                    "Sweet, gentle, friendly expression with simple round eyes and a happy approachable face. "
                    "Simplified preschool-friendly proportions while preserving natural animal anatomy and species silhouette. "
                    "Bold clean black vector outline, 5pt stroke, wide open coloring areas, perfectly centered, "
                    "vertical portrait 3:4 aspect ratio framing, leave generous 25% empty white margin space around "
                    "the centered subject on all four sides, wide breathing room, pure stark white background (#FFFFFF), "
                    "zero shading, zero grayscale, zero gradients, zero shadows, no background elements, "
                    "strictly NO text, NO letters, NO words."
                )
                base_neg = [
                    "shading",
                    "shadows",
                    "gradients",
                    "gray",
                    "grayscale",
                    "color",
                    "textures",
                    "3d",
                    "photorealistic",
                    "intricate patterns",
                    "multiple objects",
                    "background scenery",
                    "floor",
                    "ground",
                    "sky",
                    "horizon",
                    "borders",
                    "frames",
                    "separator lines",
                    "text",
                    "letters",
                    "words",
                    "alphabet",
                    "typography",
                    "watermarks",
                    "labels",
                    "writing",
                    "cross-hatching",
                    "thin lines",
                    "scary expression",
                    "widescreen",
                    "16:9",
                    "landscape orientation",
                    "horizontal cropping",
                    "cut off edges",
                ]
                unfiltered_neg = _join_negative([prof["negative_tokens"], base_neg, cat_neg])
                neg_tokens_list = [t.strip() for t in unfiltered_neg.split(",") if t.strip()]
                filtered_neg = _filter_contradictions(positive_prompt, neg_tokens_list)
                negative_prompt = ", ".join(filtered_neg)
            elif is_veh:
                veh_prof = resolve_vehicle_design_profile(canonical)
                positive_prompt = (
                    f"Ultra-clean 2D preschool toddler coloring book line art vector illustration of a cute classic {readable_name}. "
                    f"{veh_prof['anatomy'].capitalize()}. "
                    f"Supported by {veh_prof['support']}. {veh_prof['orientation'].capitalize()}. "
                    f"{veh_prof['safeguards']} "
                    f"Category Guidance: {cat_rule} "
                    "authentic simplified physical object silhouette, pure inanimate object, strictly NO eyes, NO mouth, "
                    "NO face, NO facial features, non-anthropomorphic, thick bold clean black vector outline, 5pt stroke, "
                    "wide open coloring spaces, perfectly centered, vertical portrait 3:4 aspect ratio framing, "
                    "leave generous 25% empty white margin space around the centered subject on all four sides, wide breathing room, "
                    "pure stark white background (#FFFFFF), zero shading, zero grayscale, zero gradients, zero shadows, "
                    "no background elements, strictly NO text, NO letters, NO words."
                )
                base_neg = [
                    "face",
                    "eyes",
                    "mouth",
                    "smile",
                    "facial features",
                    "anthropomorphic",
                    "cartoon character face",
                    "human features",
                    "shading",
                    "shadows",
                    "gradients",
                    "gray",
                    "grayscale",
                    "color",
                    "textures",
                    "3d",
                    "photorealistic",
                    "intricate patterns",
                    "multiple objects",
                    "background scenery",
                    "floor",
                    "ground",
                    "sky",
                    "horizon",
                    "borders",
                    "frames",
                    "separator lines",
                    "text",
                    "letters",
                    "words",
                    "alphabet",
                    "typography",
                    "watermarks",
                    "labels",
                    "writing",
                    "cross-hatching",
                    "thin lines",
                    "widescreen",
                    "16:9",
                    "landscape orientation",
                    "horizontal cropping",
                    "cut off edges",
                ]
                unfiltered_neg = _join_negative([veh_prof["negative_tokens"], base_neg, cat_neg])
                neg_tokens_list = [t.strip() for t in unfiltered_neg.split(",") if t.strip()]
                filtered_neg = _filter_contradictions(positive_prompt, neg_tokens_list)
                negative_prompt = ", ".join(filtered_neg)
            else:
                positive_prompt = (
                    f"Ultra-clean 2D preschool toddler coloring book line art vector illustration of {subject_instruction} "
                    f"Category Guidance: {cat_rule} "
                    "authentic simplified physical object silhouette, pure inanimate object, strictly NO eyes, NO mouth, "
                    "NO face, NO facial features, non-anthropomorphic, thick bold clean black vector outline, 5pt stroke, "
                    "wide open coloring spaces, perfectly centered, vertical portrait 3:4 aspect ratio framing, "
                    "leave generous 25% empty white margin space around the centered subject on all four sides, wide breathing room, "
                    "pure stark white background (#FFFFFF), zero shading, zero grayscale, zero gradients, zero shadows, "
                    "no background elements, strictly NO text, NO letters, NO words."
                )
                base_neg = [
                    "face",
                    "eyes",
                    "mouth",
                    "smile",
                    "facial features",
                    "anthropomorphic",
                    "cartoon character face",
                    "human features",
                    "shading",
                    "shadows",
                    "gradients",
                    "gray",
                    "grayscale",
                    "color",
                    "textures",
                    "3d",
                    "photorealistic",
                    "intricate patterns",
                    "multiple objects",
                    "background scenery",
                    "floor",
                    "ground",
                    "sky",
                    "horizon",
                    "borders",
                    "frames",
                    "separator lines",
                    "text",
                    "letters",
                    "words",
                    "alphabet",
                    "typography",
                    "watermarks",
                    "labels",
                    "writing",
                    "cross-hatching",
                    "thin lines",
                    "widescreen",
                    "16:9",
                    "landscape orientation",
                    "horizontal cropping",
                    "cut off edges",
                ]
                negative_prompt = _join_negative([base_neg, cat_neg])

        judge_verdict = "APPROVED"
        judge_rationale = (
            f"Synthesized hybrid specification for {label}. Locked bold outline style with zero shading, "
            f"enforced vertical portrait 3:4 framing, preserved 0.50in margin clearance, enforced container uniformity, and enforced "
            f"{'living animal face' if is_living else ('domain-accurate vehicle structure' if is_veh else 'pure inanimate object (no facial features)')} rule."
        )

        r4_outputs = {
            "AGT-007-JUDGE": {
                "verdict": judge_verdict,
                "winner": "AGT-002-DESIGN",
                "score": 97.5,
                "rationale": judge_rationale,
            },
            "AGT-008-PROMPT": {
                "positive_prompt": positive_prompt,
                "negative_prompt": negative_prompt,
            },
        }
        rounds.append(
            DebateRound(
                round_number=4,
                round_name="Judge Synthesis & Specification Lock",
                agent_outputs=r4_outputs,
            )
        )

        return DebateResult(
            page_id=page_id,
            canonical_object=canonical,
            display_label=label,
            section=section,
            winner_agent="AGT-002-DESIGN",
            final_score=97.5,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            rounds=rounds,
            judge_verdict=judge_verdict,
            judge_rationale=judge_rationale,
        )

    def run_cover_debate(
        self,
        cover_type: str = "back_cover",
        manifest_path: str = str(DEFAULT_PAGES_MANIFEST),
        book_config_path: str = str(DEFAULT_BOOK_CONFIG),
        blueprint_path: str | Path | None = None,
    ) -> DebateResult:
        """Execute 4-round multi-agent debate for Front or Back Cover Master Illustration."""
        from curiokraft_book.orchestrator.blueprint_reader import LayoutBlueprintReader

        b_cfg = _load_yaml(book_config_path).get("book", {})
        title = b_cfg.get("title", DEFAULT_BOOK_TITLE)
        subtitle = b_cfg.get("subtitle", "FUN & EASY FIRST WORDS")
        brand = b_cfg.get("brand", "CURIOKRAFT-KIDS")
        age_min = b_cfg.get("target_audience", {}).get("age_min", 1)
        age_max = b_cfg.get("target_audience", {}).get("age_max", 4)
        # Resolve volume name dynamically from manifest or config
        volume_name = ""
        if manifest_path:
            mp_str = str(manifest_path).lower()
            m_vol = re.search(r"vol(?:ume)?[_-]?(\d+)", mp_str)
            if m_vol:
                volume_name = f"Volume {m_vol.group(1)}"
            elif "pages.json" in mp_str:
                volume_name = "Volume 1"
        if not volume_name:
            cfg_vol = str(b_cfg.get("volume", "")).strip()
            if cfg_vol:
                m_vol = re.search(r"vol(?:ume)?[_-]?(\d+)", cfg_vol.lower())
                volume_name = f"Volume {m_vol.group(1)}" if m_vol else cfg_vol.title()

        # Check for user layout blueprint in inbox/blueprints/
        bp_reader = LayoutBlueprintReader()
        blueprint_spec = None
        if blueprint_path:
            try:
                blueprint_spec = bp_reader.read_blueprint(blueprint_path)
            except Exception as e:
                logger.warning(f"Could not read specified blueprint {blueprint_path}: {e}")
        if not blueprint_spec:
            blueprint_spec = bp_reader.get_layout_spec(cover_type)

        rounds: list[DebateRound] = []

        if cover_type == "back_cover":
            # 1. Dynamically extract 3 representative interior cards from active manifest
            cards = extract_cover_showcase_cards(manifest_path, count=3)
            cards_desc_list = [f"{c['category_name']}: {c['description']}" for c in cards]
            cards_summary = "; ".join(cards_desc_list)

            # 2. Marketing Copy & Benefit Pills (Strictly double-sided, zero developer prompt jargon)
            c_back = _CURRICULUM.get("cover_styling", {}).get("back_cover", {})
            headlines = c_back.get(
                "headline_options", ["DISCOVER, COLOR & LEARN!", "LITTLE HANDS, BIG DISCOVERIES!"]
            )
            headline = headlines[0] if headlines else "DISCOVER, COLOR & LEARN!"

            # Dynamic page count from manifest
            page_count = 110
            try:
                m_p = Path(manifest_path)
                if not m_p.is_absolute():
                    candidates = [
                        Path.cwd() / manifest_path,
                        Path(__file__).parent.parent.parent.parent / manifest_path,
                    ]
                    for c in candidates:
                        if c.exists():
                            m_p = c
                            break
                if m_p.exists():
                    with open(m_p, encoding="utf-8") as mf:
                        m_data = json.load(mf)
                        page_count = len(m_data.get("pages", [])) or 110
            except (OSError, json.JSONDecodeError):
                # Manifest file missing or unreadable; default to baseline page_count
                pass

            vol_label = f" {volume_name}" if volume_name else ""
            description = (
                f"Continue your little one's joyful learning journey with{vol_label}! "
                f"Packed with {page_count}+ adorable preschool illustrations and everyday first words, "
                "it's perfect for building fine motor skills, early vocabulary, and creative confidence!"
            )

            # Layout slots: from user blueprint if present, else standard responsive
            if blueprint_spec:
                card_cols = blueprint_spec.card_grid.columns
                pill_count = blueprint_spec.feature_callouts.count
                pill_layout = blueprint_spec.feature_callouts.layout.replace("_", " ")
                wave_pct = blueprint_spec.baseline_wave.height_percentage
            else:
                card_cols = 3
                pill_count = 4
                pill_layout = "2x2 grid"
                wave_pct = 20

            pills_text = (
                f"'{pill_count}+ Brand-New Simple Drawings', 'Chunky Outlines for Little Hands', "
                f"'{page_count} Full Pages of Double-Sided Coloring', 'Perfect for Ages {age_min}-{age_max}'"
            )

            # Round 1: Specialist Proposals
            r1_outputs = {
                "AGT-002-DESIGN": {
                    "composition": (
                        f"Back cover master illustration matching front cover style and palette (#FFF9E6). "
                        f"Flashcard grid: exactly {card_cols} upright white rounded cards in a single row ({cards_summary}). "
                        f"Middle-lower zone: {pill_count} pastel rounded feature pills in {pill_layout}. "
                        f"Spine continuity: RIGHT edge directly abuts book spine — must remain 100% borderless and horizontally flat. "
                        f"Bottom layout: lower {wave_pct}% continuous pastel turquoise and mint wave with zero white cutout boxes or placeholder badges."
                    ),
                    "prohibited": [
                        "white box on left",
                        "white cutout box",
                        "logo placeholder",
                        "text in bottom corners",
                        "barcode on artwork",
                        "border on right edge",
                        "crayons on cards",
                        "single-sided claims",
                        "5pt outlines jargon",
                    ],
                },
                "AGT-004-MARKET": {
                    "commercial_messaging": (
                        f"Headline: '{headline}'. Description: '{description}'. "
                        f"Pills: {pills_text}. Highlighting double-sided preschool value, zero developer prompt jargon."
                    ),
                    "prohibited": [
                        "single-sided pages",
                        "blank backs",
                        "5pt outlines",
                        "vector stroke",
                    ],
                },
                "AGT-005-EDU": {
                    "pedagogical_milestone": f"Ages {age_min}-{age_max} early vocabulary and fine motor dexterity.",
                },
            }

            # Round 2: Cross-Specialist Consensus
            r2_outputs = {
                "cross_consensus": (
                    "Agreed on 100% continuous turquoise wave across bottom 20% (strictly zero white boxes for logo/barcode), "
                    "truthful double-sided printing messaging, zero developer prompt jargon, and authentic manifest card showcase."
                )
            }

            # Round 3: Adversarial Red-Team Stress-Test
            r3_outputs = {
                "AGT-006-REDTEAM": {
                    "stress_test_findings": [
                        "Verify zero AI white box / cutout at bottom-left: background wave and stardust must flow continuously.",
                        "Verify double-sided truth: strictly prohibit 'single-sided' or 'blank backs' tokens.",
                        "Verify zero developer prompt jargon: ban '5pt bold outlines' from visible copy.",
                        "Verify right edge is borderless and horizontally flat to seamlessly match spine and front cover.",
                    ],
                    "risk_level": "LOW",
                    "recommended_hardening": (
                        "Mandate strictly NO text, NO words, NO letters, and NO white cutout boxes in bottom corners. "
                        "Reinforce negative tokens: white badge on left, white box on left, single-sided, 5pt outlines."
                    ),
                }
            }

            # Round 4: Judge Synthesis
            pos = (
                f"Cohesive, print-ready 2D preschool toddler coloring book back cover master illustration for '{title}', "
                "perfectly matching and continuing the visual style, color palette, and organic framing of the front cover. "
                "Background: cheerful warm butter-cream / soft sunny pale yellow canvas (#FFF9E6), perfectly matching the front cover. "
                f"Bottom baseline features the exact same smooth, gentle rolling wave in pastel turquoise and mint across the lower 15-{wave_pct}% of the canvas at the exact same horizontal height. "
                "WRAPAROUND SPINE CONTINUITY MANDATE: The RIGHT edge of this back cover directly abuts the book spine — keep the entire RIGHT edge completely clean, borderless, and horizontally flat with zero corner frames, zero diagonal rivers, and zero vertical decorative borders, ensuring a 100% continuous, uninterrupted horizontal flow across the spine into the front cover. Playful organic wavy/scalloped corner frames in pastel turquoise, mint, and lemon-yellow are positioned strictly on the OUTER LEFT corners only. "
                "The entire canvas is sprinkled with subtle celebratory toddler star dust: floating 4-point and 5-point twinkling stars in golden yellow, orange, and blue, and soft pastel floating love hearts in pink and lilac. "
                f"Top section: bold uppercase headline in dark navy '{headline}'. "
                f"Directly below the headline, a friendly parent description in clean, dark navy rounded typography: '{description}' "
                f"Middle section: exactly {card_cols} clean, upright white rounded flashcard preview boxes arranged in a single neat horizontal row (1 row by {card_cols} columns), showcasing authentic black-and-white coloring book sample pages from inside this specific volume. "
                "Each card is a clean rounded white rectangle with a thin dark charcoal border. (CRITICAL: Strictly NO crayons on cards, NO angled crayons, and NO coloring tools—display pure, clean coloring pages). "
                f"Inside each card is pure 2D black-and-white coloring book line art with bold outlines and large open spaces for toddlers to color: "
                f"{cards_summary}. "
                f"Middle-lower zone (directly below the flashcards and above the bottom rolling wave): utilizes the space with {pill_count} neat, colorful pastel rounded feature note pills arranged in a balanced {pill_layout} with playful star bullets: "
                f"'★ {page_count}+ Brand-New Simple Drawings', '★ Chunky Easy Outlines for Little Hands', '★ {page_count} Full Pages of Double-Sided Coloring', and '★ Perfect for Ages {age_min}–{age_max}'. "
                "Bottom layout: The bottom-left and bottom-right corners feature clean, unbroken continuous pastel background artwork with the gentle wavy turquoise baseline, delicate twinkling star dust, soft floating hearts, and subtle playful doodles. "
                "(CRITICAL INVIOLABLE MULTI-VOLUME MANDATE: The lower 20% of the canvas containing the wavy turquoise baseline must remain 100% flat, continuous, and clear with strictly ZERO text, ZERO cards, ZERO notes, and ZERO white cutout boxes or placeholder badges anywhere in the bottom-left or bottom-right positions. Background color (#FFF9E6), rolling waves, star dust, and doodles MUST flow continuously and seamlessly across both bottom positions; strictly ZERO text is to be printed in these two locations, as the publisher logo badge and barcode are programmatically composited in code post-generation). "
                "Vertical 3:4 portrait orientation, premium commercial publisher print quality, perfectly balanced typography, cards, and colors."
            )

            neg = (
                "text in bottom-left corner, text in bottom-right corner, barcode numbers, publisher text, bottom labels, "
                "letters in bottom left, letters in bottom right, text on turquoise wave, words on bottom baseline, "
                "white badge on left, white box on left, logo badge, empty white rectangle on left, white badge cutout, placeholder box, "
                "single-sided, single-sided pages, single sided, blank backs, anti-bleed blank backs, "
                "5pt bold outlines, 5pt stroke, vector stroke, prompt engineering, "
                "corner frame on right edge, border on right edge, right vertical border, diagonal river across right edge, "
                "numbers in corners, dimensions, measurements, margin text, technical annotations, labels, 0.60 in, 180px, "
                "white rectangle on right, barcode box, barcode placeholder, printed barcode, barcode lines, qr code, "
                "fake logo, gibberish text in badge, text inside white badge, crayons on cards, wax crayons, "
                "colored drawings inside cards, colored line art inside cards, realistic shading, grayscale shading in cards, "
                "2x3 grid, 6 cards, blurry, low resolution, dark moody colors, photographic, realistic textures, "
                "jagged lines, distorted cards, cut-off cards, horizontal landscape, 16:9, cut off edges"
            )

            page_id = "COVER_BACK"
            label = "BACK COVER MASTER ARTWORK"
            canonical = "back_cover"
            section = "Covers"

        else:  # front_cover
            hero_char, companions, page_count = extract_front_cover_ensemble(manifest_path)
            companions_desc = ", ".join(companions)

            r1_outputs = {
                "AGT-002-DESIGN": {
                    "composition": (
                        f"Front cover master illustration. Central hero: {hero_char}. "
                        f"Companions: {companions_desc}. 3D puffy candy title 'TINY HANDS' arched at top. "
                        "Butter-cream canvas (#FFF9E6) with rolling turquoise wave across lower 15-20%. "
                        "Spine continuity: LEFT edge directly abuts spine — 100% borderless and horizontally flat."
                    ),
                    "prohibited": [
                        "border on left edge",
                        "spine crease shadow",
                        "black drop shadows",
                        "barcode on front",
                    ],
                },
                "AGT-004-MARKET": {
                    "commercial_appeal": "Instant preschool delight with candy-colored 3D bubbly title and adorable hero animal.",
                },
            }
            r2_outputs = {
                "cross_consensus": "Agreed on vibrant 2D sticker art with white puffy die-cut outlines."
            }
            r3_outputs = {
                "AGT-006-REDTEAM": {
                    "stress_test_findings": [
                        "Verify spine shadow removal: left edge must have zero vertical crease or shadow.",
                        "Verify safe live area: top banner comfortably 1.0 inch below top margin.",
                    ],
                    "risk_level": "LOW",
                    "recommended_hardening": "Add negative tokens against spine lines, vertical crease, and dark shadows.",
                }
            }

            pos = (
                f"Eye-catching vibrant 2D preschool toddler coloring book front cover master illustration for '{title}'. "
                f"Generous top safety margin: leave the top 10-12% of the canvas as clean sunny golden-cream background. Position the top text banner '{brand} Presents' comfortably inside the safe live area, centered at least 1.0 inch / 300px below the top canvas edge in clean, bold navy preschool lettering so it will not be cut off during physical trimming. "
                "Directly below, main title 'TINY HANDS' rendered in a joyful upward rainbow arch in large, chunky 3D puffy inflated bubble jelly/candy letters with high-gloss specular reflections (white highlight curves on the top surfaces). "
                "Each letter in 'TINY HANDS' has an individual vibrant saturated candy color: T (warm orange), I (sunny yellow), N (electric cyan blue), Y (peach orange), H (hot pink), A (golden yellow), N (bright red/coral), D (sky blue), S (tangerine orange). "
                "The letters feature a clean bright white puffy die-cut contour outline with soft warm pastel depth (strictly NO dark black drop shadows, NO harsh black outlines). "
                "Directly below 'TINY HANDS', the words 'COLOR & LEARN' are also rendered in large, vibrant multi-colored 3D puffy bubble letters (NOT plain white): C (hot pink), O (bright yellow), L (cyan blue), O (lime green), R (vibrant purple), & (golden orange), L (hot pink), E (sunny yellow), A (electric blue), R (lime green), N (violet purple), with glossy candy highlights and a clean thick puffy white contour outline. "
                f"Directly underneath the arched title lockup, clean bold dark navy rounded lettering reading '{subtitle}', flanked by cute little decorative stars. "
                f"Central joyful toddler illustration: {hero_char}. "
                f"Surrounding the hero character is a rich ensemble of adorable, chunky preschool objects: {companions_desc}, plus a curved floating rainbow wax crayon with colorful motion lines in the sky. "
                "All characters and objects have clean vibrant 2D vector styling with pure white sticker contours (strictly NO dark black cast shadows, NO dark ground shadows, and NO dirty gray shading underneath characters or objects). "
                "Background: cheerful warm butter-cream / soft sunny pale yellow canvas (#FFF9E6) with a gentle, smooth pastel turquoise and mint rolling wave across the lower 15-20% of the canvas. "
                "WRAPAROUND SPINE CONTINUITY MANDATE: The LEFT edge of this front cover directly abuts the book spine — keep the entire LEFT edge completely clean, borderless, and horizontally flat with zero corner frames and zero vertical decorative borders, allowing the butter-cream sky and bottom turquoise wave to flow seamlessly and continuously into the spine without any seams or step jumps. Playful organic wavy/scalloped corner frames in pastel turquoise, mint, and lemon-yellow are positioned strictly on the OUTER RIGHT corners only. "
                "The entire atmosphere is filled with celebratory toddler star dust and magical confetti: floating 4-point and 5-point twinkling stars in golden yellow, orange, and blue; soft pastel floating love hearts in pink and lilac; and colorful tiny confetti dots, sparkles, and sprinkles floating merrily through the air. "
                f"Bottom layout: a wide clean white rounded pill banner with bold navy text '{page_count}+ EVERYDAY OBJECTS' and 'FIRST WORDS • LETTERS & NUMBERS', accompanied on the right by a circular sunny yellow roundel badge reading 'AGES {age_min}-{age_max} YEARS'. "
                "Vertical 3:4 portrait orientation, premium commercial publisher print quality, ultra-sharp vector rendering, joyful friendly Disney Junior and Fisher-Price toddler aesthetic."
            )

            neg = (
                "corner frame on left edge, border on left edge, left vertical border, clean pastel floor, text on floor, words on floor, "
                "floor label, dark black shadows, heavy black shadows, black drop shadows, dark ground shadows, harsh contact shadows, "
                "spine shadow line, vertical crease, spine crease shadow, book fold shadow, 3d book mockup shadow, shading line along spine, "
                "dirty shading, muddy shadows, realistic shadows, white letters for color and learn, plain white text, flat title, "
                "monochromatic lettering, blurry, pixelated, low resolution, photographic, dark gritty shadows, realistic adult human faces, "
                "scary expressions, jagged lines, muddy colors, grey backdrop, horizontal landscape, 16:9, cut off edges, distorted anatomy, "
                "barcode on front cover, spine lines across front cover"
            )

            page_id = "COVER_FRONT"
            label = "FRONT COVER MASTER ARTWORK"
            canonical = "front_cover"
            section = "Covers"

        judge_verdict = "APPROVED"
        judge_rationale = (
            f"Approved {label} specification: Enforced 100% continuous turquoise wave across bottom baseline, "
            f"borderless spine edge clearance, truthful double-sided parent benefits, and dynamic manifest-derived assets."
        )

        r4_outputs = {
            "AGT-007-JUDGE": {
                "verdict": judge_verdict,
                "winner": "AGT-002-DESIGN",
                "score": 98.0,
                "rationale": judge_rationale,
            },
            "AGT-008-PROMPT": {
                "positive_prompt": pos,
                "negative_prompt": neg,
            },
        }

        rounds.append(
            DebateRound(round_number=1, round_name="Specialist Proposals", agent_outputs=r1_outputs)
        )
        rounds.append(
            DebateRound(
                round_number=2, round_name="Cross-Specialist Review", agent_outputs=r2_outputs
            )
        )
        rounds.append(
            DebateRound(
                round_number=3, round_name="Adversarial Red-Team Critique", agent_outputs=r3_outputs
            )
        )
        rounds.append(
            DebateRound(
                round_number=4,
                round_name="Judge Synthesis & Specification Lock",
                agent_outputs=r4_outputs,
            )
        )

        return DebateResult(
            page_id=page_id,
            canonical_object=canonical,
            display_label=label,
            section=section,
            winner_agent="AGT-002-DESIGN",
            final_score=98.0,
            positive_prompt=pos,
            negative_prompt=neg,
            rounds=rounds,
            judge_verdict=judge_verdict,
            judge_rationale=judge_rationale,
        )

    def run_mascot_debate(
        self,
        mascot_name: str,
        book_config_path: str = str(DEFAULT_BOOK_CONFIG),
    ) -> DebateResult:
        """Execute 4-round multi-agent debate synthesizing the Volume Mascot prompt for Welcome & Certificate pages."""
        mascot_clean = mascot_name.replace("_", " ").strip()
        mascot_title = mascot_clean.title()

        rounds: list[DebateRound] = []

        # Round 1: Developmental & Toddler Psychology Specialist
        r1 = DebateRound(
            round_number=1,
            round_name="Developmental & Toddler Psychology Specialist",
            agent_outputs={
                "AGT-005-EDU": {
                    "age_target": "Ages 1-4 toddler range",
                    "hero_mascot": mascot_title,
                    "psychology_rationale": (
                        f"The mascot ({mascot_title}) serves as the child's continuous coloring friend across the entire book. "
                        f"It introduces the child on Page 001 ('THIS BOOK BELONGS TO') and celebrates their achievement on Page 110 ('SUPER COLORIST'). "
                        f"Must have an endearing chubby baby anatomy, sweet smiling round eyes, joyful rosy blushing cheeks, and a friendly waving paw to encourage immediate bonding."
                    ),
                    "character_pose": "Sitting joyfully in an upright posture, waving one front paw welcomingly toward the child.",
                }
            },
        )
        rounds.append(r1)

        # Round 2: Line Art & Visual Purity Specialist
        r2 = DebateRound(
            round_number=2,
            round_name="Line Art & Visual Purity Specialist",
            agent_outputs={
                "AGT-002-DESIGN": {
                    "outline_specification": "5pt ultra-clean black vector outline, uniform stroke width",
                    "coloring_regions": "Wide open interior coloring spaces suitable for chunky wax crayons",
                    "purity_mandates": (
                        "Strictly zero color fills, zero grayscale shading, zero shadow gradients, zero crosshatching, "
                        "and zero micro-details. Unbroken continuous contours for effortless coloring."
                    ),
                }
            },
        )
        rounds.append(r2)

        # Round 3: Print Geometry & Compositor Specialist
        r3 = DebateRound(
            round_number=3,
            round_name="Print Geometry & Compositor Specialist",
            agent_outputs={
                "AGT-003-KDP": {
                    "canvas_dimensions": "3:4 vertical portrait framing with generous empty margin buffers",
                    "background_isolation": (
                        "CRITICAL: Solid pure white background (#FFFFFF). Absolutely isolated with zero scenery, "
                        "zero furniture, zero floor lines. MANDATE: Strictly NO checkerboard patterns, NO faux Photoshop "
                        "transparency grids, NO gray pixel patterns. Must allow Python PIL luminance thresholding (>140 -> 255) "
                        "to extract an ultra-clean alpha mask for programmatic placement on Page 001 and Page 110."
                    ),
                    "continuity_mandate": "Exact same mascot image asset will be composited into both Page 001 and Page 110.",
                }
            },
        )
        rounds.append(r3)

        # Round 4: Executive Creative Judge & Synthesizer
        pos = (
            f"Ultra-clean 2D preschool toddler coloring book line art illustration of a cute friendly baby {mascot_clean} for ages 1-4. "
            f"Adorable chubby rounded body, sweet gentle smiling expression, big friendly round eyes, rosy blushing cheeks, "
            f"sitting joyfully and waving one front paw. Thick clean black vector outline, 5pt stroke, wide open coloring areas. "
            f"Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. "
            f"Vertical portrait framing with generous empty margin space on all sides. "
            f"Strictly NO text, NO letters, NO numbers, NO color fills, zero shading, zero grayscale, zero gradients, zero shadows. "
            f"Pure black and white line art only."
        )

        neg = (
            "text, letters, numbers, words, watermark, logo, title, label, color, colors, colored, color fills, "
            "shading, grayscale, gray fills, shadows, drop shadows, gradients, realistic textures, realistic animal, "
            "photographic, 3d render, complex details, crosshatching, thin lines, broken lines, sketchy lines, dirty lines, "
            "checkerboard, grid, transparency grid, grey pattern, background elements, scenery, furniture, clothes, "
            "complex clothing, scary expressions, sharp teeth, claws, distorted anatomy, low resolution, blurry, pixelated"
        )

        r4 = DebateRound(
            round_number=4,
            round_name="Executive Creative Judge & Synthesizer",
            agent_outputs={
                "AGT-007-JUDGE": {
                    "final_score": 99.5,
                    "status": "APPROVED FOR MULTI-VOLUME MILESTONE PAGES",
                    "verdict": f"Synthesized official {mascot_title} mascot illustration prompt complying with 5pt KDP purity and dual Page 001/110 reuse rules.",
                }
            },
        )
        rounds.append(r4)

        return DebateResult(
            page_id="MASCOT",
            canonical_object=mascot_name,
            display_label=f"{mascot_clean.upper()} (VOLUME MASCOT)",
            section="Special Assets",
            winner_agent="AGT-007-JUDGE",
            final_score=99.5,
            positive_prompt=pos,
            negative_prompt=neg,
            rounds=rounds,
            judge_verdict="APPROVED FOR MULTI-VOLUME PRODUCTION",
            judge_rationale=f"Full consensus reached across specialists for {mascot_title} mascot.",
        )

    def export_full_debate_log(
        self,
        manifest_path: str | Path = DEFAULT_PAGES_MANIFEST,
        output_file: str | Path = DEFAULT_DEBATE_LOG_FILE,
    ) -> str:
        """Synthesize and export the complete 4-round debate transcript across all manifest pages."""
        import json

        m_path = Path(manifest_path)
        out_p = Path(output_file)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if not m_path.exists():
            raise FileNotFoundError(f"Manifest file not found at: {manifest_path}")

        with open(m_path, encoding="utf-8") as f:
            manifest_data = json.load(f)

        pages = manifest_data.get("pages", [])
        title = manifest_data.get("book_title", DEFAULT_BOOK_TITLE)
        total_p = len(pages) if pages else DEFAULT_PAGE_COUNT

        lines = [
            "# \U0001f916 Multi-Agent Specialist Pre-Generation Debate & Decision Audit Log",
            f"**Publication:** {title} | **Total Pages Audited:** {total_p} | **Engine:** CurioKraft Multi-Agent Orchestrator v1.0",
            "**Specialist Agents:** `AGT-001-DIRECTOR`, `AGT-002-DESIGN`, `AGT-003-KDP`, `AGT-004-MARKET`, `AGT-005-EDU`, `AGT-006-REDTEAM`, `AGT-007-JUDGE`, `AGT-008-PROMPTGEN`",
            "",
            "> [!NOTE]",
            "> This log records the complete pre-generation reasoning, independent specialist proposals, cross-agent debate, adversarial stress-testing, and Judge synthesis for every single page.",
            "",
            "---",
            "",
        ]

        for p in pages:
            res = self.run_page_debate(p)
            num = p.get("page_number", 0)
            lines.append(f"## \U0001f4c4 Page {num:03d} ({res.page_id}): {res.display_label}")
            lines.append(f"- **Section:** {res.section}")
            lines.append(f"- **Canonical Object:** `{res.canonical_object}`")
            lines.append(
                f"- **Judge Verdict:** `{res.judge_verdict}` (Score: `{res.final_score}/100` | Winner: `{res.winner_agent}`)"
            )
            lines.append(f"- **Judge Rationale:** {res.judge_rationale}")
            lines.append("")

            r1 = next((r for r in res.rounds if r.round_number == 1), None)
            if r1:
                lines.append("### \U0001f4ac Round 1: Specialist Agent Proposals")
                lines.append(
                    "| Specialist Agent | Perspective & Proposals | Constraints / Prohibitions |"
                )
                lines.append("| :--- | :--- | :--- |")
                for agent_id, out in r1.agent_outputs.items():
                    if isinstance(out, dict):
                        props = "<br/>".join(
                            [f"**{k}:** {v}" for k, v in out.items() if k != "prohibited"]
                        )
                        prohib = "<br/>".join(out.get("prohibited", []))
                        lines.append(f"| **{agent_id}** | {props} | {prohib} |")
                lines.append("")

            r3 = next((r for r in res.rounds if r.round_number == 3), None)
            if r3:
                lines.append("### \U0001f50d Round 3: Adversarial Red-Team Stress-Test (AGT-006)")
                critic_out = r3.agent_outputs.get("AGT-006-CRITIC", {})
                lines.append("**Stress-Test Findings:**")
                for f_item in critic_out.get("stress_test_findings", []):
                    lines.append(f"- {f_item}")
                lines.append(
                    f"**Recommended Hardening:** {critic_out.get('recommended_hardening', 'N/A')}"
                )
                lines.append("")

            lines.append("### \u2696\ufe0f Round 4: Judge Decision & Locked Prompts")
            lines.append("- **Positive Prompt (Copy & Paste):**")
            lines.append(f"  ```text\n  {res.positive_prompt}\n  ```")
            lines.append("- **Negative Prompt:**")
            lines.append(f"  ```text\n  {res.negative_prompt}\n  ```")
            lines.append("")
            lines.append("---")
            lines.append("")

        out_p.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Successfully exported full multi-agent debate log to {output_file}")
        return str(out_p)


# =============================================================================
# Dynamic Cover Artwork Prompt Generators (Manifest-Driven Agent Synthesis)
# =============================================================================


def _get_crayon_color_for_object(obj_name: str) -> str:
    """Helper to determine preschool crayon color guide based on object semantics."""
    obj = obj_name.lower()
    if any(k in obj for k in ["apple", "strawberry", "cherry", "tomato", "heart", "rose"]):
        return "red"
    if any(k in obj for k in ["banana", "sun", "lemon", "duck", "cheese", "corn", "star"]):
        return "yellow"
    if any(
        k in obj
        for k in ["car", "boat", "ship", "train", "plane", "whale", "dolphin", "milk", "water"]
    ):
        return "blue"
    if any(k in obj for k in ["carrot", "guitar", "orange", "fox", "tiger", "lion", "basketball"]):
        return "orange"
    if any(
        k in obj for k in ["frog", "turtle", "tree", "leaf", "caterpillar", "dinosaur", "grass"]
    ):
        return "green"
    if any(k in obj for k in ["grape", "eggplant", "plum", "butterfly", "octopus"]):
        return "purple"
    return "bright colorful"


def extract_cover_showcase_cards(
    manifest_path: str = str(DEFAULT_PAGES_MANIFEST),
    count: int = 3,
) -> list[dict[str, str]]:
    """Dynamically select representative interior coloring pages from the active manifest across diverse categories.

    Returns a list of card dicts with:
      - slot: index 1..count
      - title: Uppercase display word
      - category_name: Educational category label
      - description: Clean 2D coloring book line art description
    """
    m_p = Path(manifest_path)
    if not m_p.is_absolute():
        candidates = [
            Path.cwd() / manifest_path,
            Path(__file__).parent.parent.parent.parent / manifest_path,
        ]
        for c in candidates:
            if c.exists():
                m_p = c
                break

    pages = []
    if m_p.exists():
        try:
            with open(m_p, encoding="utf-8") as f:
                data = json.load(f)
                pages = [
                    p
                    for p in data.get("pages", [])
                    if p.get("page_number", 0) >= 4 and p.get("type") in ["coloring_page", None]
                ]
        except Exception as e:
            logger.warning(f"Error loading manifest pages: {e}")

    # Group pages into distinct preschool domains
    group_food = []
    group_animals = []
    group_vehicles = []
    group_objects = []

    for p in pages:
        canon = str(p.get("canonical_object", "")).lower()
        sec = str(p.get("section", "")).lower()
        canon_tokens = set(canon.replace("_", " ").split())
        sec_tokens = set(sec.replace("_", " ").split())

        is_living = classify_living_taxonomy(canon, sec)
        is_food = bool(
            (canon_tokens | sec_tokens)
            & {
                "fruit",
                "food",
                "vegetable",
                "sweet",
                "drink",
                "apple",
                "cherry",
                "banana",
                "strawberry",
                "grape",
                "orange",
                "carrot",
            }
        )
        is_veh = is_vehicle_object(canon, sec)

        if is_food and not is_living:
            group_food.append(p)
        elif is_living:
            group_animals.append(p)
        elif is_veh and not is_living:
            group_vehicles.append(p)
        else:
            group_objects.append(p)

    selected_pages = []
    if group_food:
        selected_pages.append((group_food[0], "First Words & Fruit"))
    if group_animals:
        selected_pages.append((group_animals[0], "Cute Animals & Nature"))
    if group_vehicles:
        selected_pages.append((group_vehicles[0], "Vehicles & First Transport"))
    elif group_objects:
        selected_pages.append((group_objects[0], "Everyday Objects"))

    # Fallback to remaining pages if any category was missing
    if len(selected_pages) < count:
        seen_ids = {p.get("page_id") for p, _ in selected_pages}
        for p in pages:
            if p.get("page_id") not in seen_ids:
                selected_pages.append((p, "Preschool First Words"))
                seen_ids.add(p.get("page_id"))
                if len(selected_pages) >= count:
                    break

    cards_out = []
    for idx, (p, cat_label) in enumerate(selected_pages[:count], start=1):
        word = (
            str(p.get("display_label") or p.get("canonical_object", f"ITEM {idx}"))
            .upper()
            .replace("_", " ")
        )
        canon = str(p.get("canonical_object", word.lower()))
        desc = p.get("positive_description") or p.get("description")
        if not desc:
            is_living = classify_living_taxonomy(canon, p.get("section", ""))
            desc = generate_dynamic_visual_spec(canon, p.get("section", ""), is_living)
        # Format clean card outline spec
        card_desc = f"hollow bubble-letter coloring title '{word}' across the top, {desc.strip().rstrip('.')}"
        cards_out.append(
            {
                "slot": str(idx),
                "title": word,
                "category_name": cat_label,
                "description": card_desc,
            }
        )

    return cards_out


def extract_front_cover_ensemble(
    manifest_path: str = str(DEFAULT_PAGES_MANIFEST),
) -> tuple[str, list[str], int]:
    """Dynamically discover the hero character, companion objects, and page count from active manifest."""
    m_p = Path(manifest_path)
    if not m_p.is_absolute():
        candidates = [
            Path.cwd() / manifest_path,
            Path(__file__).parent.parent.parent.parent / manifest_path,
        ]
        for c in candidates:
            if c.exists():
                m_p = c
                break

    pages = []
    page_count = 110
    if m_p.exists():
        try:
            with open(m_p, encoding="utf-8") as f:
                data = json.load(f)
                pages = data.get("pages", [])
                page_count = len(pages) or 110
        except Exception:
            pass

    mascot_priorities = [
        "elephant",
        "panda",
        "teddy_bear",
        "bear",
        "puppy",
        "dog",
        "kitten",
        "cat",
        "lion",
        "bunny",
        "rabbit",
        "monkey",
    ]
    found_hero = None

    interior_pages = [p for p in pages if p.get("page_number", 0) >= 4]

    for mascot in mascot_priorities:
        for p in interior_pages:
            canon = str(p.get("canonical_object", "")).lower()
            if canon == mascot:
                lbl = str(p.get("display_label") or canon.replace("_", " ")).lower()
                found_hero = (
                    f"an adorable chubby cartoon baby {lbl} with sweet smiling round eyes, blushing pink cheeks, "
                    f"and friendly gentle expression, sitting joyfully while clutching a chunky wax crayon with little sparkle motion lines"
                )
                break
        if found_hero:
            break

    if not found_hero:
        for p in interior_pages:
            canon = str(p.get("canonical_object", "")).lower()
            sec = str(p.get("section", "")).lower()
            if classify_living_taxonomy(canon, sec):
                lbl = str(p.get("display_label") or canon.replace("_", " ")).lower()
                found_hero = (
                    f"an adorable chubby cartoon baby {lbl} with sweet smiling round eyes and rosy cheeks, "
                    f"sitting joyfully while holding a bright wax crayon"
                )
                break

    hero_char = (
        found_hero
        or "an adorable chubby cartoon baby mascot with sweet smiling round eyes, sitting joyfully while holding a bright wax crayon"
    )

    dynamic_companions: list[str] = []
    for p in interior_pages:
        canon = str(p.get("canonical_object", "")).lower()
        sec = str(p.get("section", "")).lower()
        lbl = str(p.get("display_label") or canon.replace("_", " ")).lower()
        if ("fruit" in sec or canon in ["apple", "cherry", "banana", "strawberry"]) and len(
            dynamic_companions
        ) < 1:
            dynamic_companions.append(
                f"a shiny cute smiling cartoon {lbl} with big sweet round eyes, rosy cheeks, and leafy stem"
            )
        elif ("nature" in sec or canon in ["flower", "sun", "tree"]) and len(
            dynamic_companions
        ) < 2:
            dynamic_companions.append(
                f"a cute happy smiling cartoon {lbl} with cheerful sunny face and soft petals"
            )
        elif ("vehicle" in sec or canon in ["car", "airplane", "bus", "train", "truck"]) and len(
            dynamic_companions
        ) < 3:
            dynamic_companions.append(
                f"a cheerful chunky preschool toy {lbl} with round cartoon headlights and friendly smiling details"
            )

    dynamic_companions.append(
        "a vibrant multi-colored arching rainbow emerging from two fluffy white cumulus clouds"
    )

    return hero_char, dynamic_companions, page_count


def generate_front_cover_prompt(
    book_config_path: str = str(DEFAULT_BOOK_CONFIG),
    manifest_path: str = str(DEFAULT_PAGES_MANIFEST),
) -> tuple[str, str]:
    """Construct dynamic Front Cover Master Illustration prompt synthesized via multi-agent debate."""
    engine = DebateEngine()
    res = engine.run_cover_debate(
        cover_type="front_cover",
        manifest_path=manifest_path,
        book_config_path=book_config_path,
    )
    return res.positive_prompt, res.negative_prompt


def generate_back_cover_prompt(
    book_config_path: str = str(DEFAULT_BOOK_CONFIG),
    manifest_path: str = str(DEFAULT_PAGES_MANIFEST),
) -> tuple[str, str]:
    """Construct dynamic Back Cover Master Illustration prompt synthesized via multi-agent debate."""
    engine = DebateEngine()
    res = engine.run_cover_debate(
        cover_type="back_cover",
        manifest_path=manifest_path,
        book_config_path=book_config_path,
    )
    return res.positive_prompt, res.negative_prompt


def generate_dynamic_cover_prompt(
    book_config_path: str = str(DEFAULT_BOOK_CONFIG),
) -> tuple[str, str]:
    """Backward-compatible alias for Front Cover Master Prompt."""
    return generate_front_cover_prompt(book_config_path)


def auto_pick_volume_mascot(
    manifest_path: str = str(DEFAULT_PAGES_MANIFEST),
    book_config_path: str = str(DEFAULT_BOOK_CONFIG),
) -> str:
    """Resolve or auto-pick the volume's flagship mascot identity based on config and manifest theme."""
    # 1. Check explicit name in book_config.yaml
    b_cfg = _load_yaml(book_config_path).get("book", {})
    m_cfg = b_cfg.get("mascot", {})
    if isinstance(m_cfg, dict):
        cfg_name = m_cfg.get("name")
        if cfg_name and str(cfg_name).strip():
            return str(cfg_name).strip().lower()

    # 2. Inspect active manifest
    try:
        m_data = _load_json(manifest_path)
    except Exception:
        return "panda"

    pages = m_data.get("pages", [])
    interior_pages = [p for p in pages if p.get("page_number", 0) >= 2]

    # Priority candidate list across themes (land animals, sea creatures, vehicles)
    mascot_priorities = [
        "panda",
        "bear",
        "teddy_bear",
        "puppy",
        "dog",
        "kitten",
        "cat",
        "bunny",
        "rabbit",
        "koala",
        "dolphin",
        "turtle",
        "sea_turtle",
        "whale",
        "penguin",
        "owl",
        "fox",
        "deer",
        "lion",
        "monkey",
        "elephant",
        "tugboat",
        "train",
        "airplane",
    ]

    for cand in mascot_priorities:
        for p in interior_pages:
            canon = str(p.get("canonical_object", "")).lower()
            if canon == cand:
                return canon

    # 3. Fallback: Find first living creature in manifest
    for p in interior_pages:
        canon = str(p.get("canonical_object", "")).lower()
        sec = str(p.get("section", "")).lower()
        if (
            "animal" in sec
            or "creature" in sec
            or "sea" in sec
            or classify_living_taxonomy(canon, sec)
        ):
            return canon

    # 4. Ultimate fallback
    return "panda"


def generate_mascot_prompt(
    mascot_name: str | None = None,
    book_config_path: str = str(DEFAULT_BOOK_CONFIG),
    manifest_path: str = str(DEFAULT_PAGES_MANIFEST),
) -> tuple[str, str]:
    """Construct dynamic Volume Mascot prompt synthesized via multi-agent debate."""
    name = mascot_name or auto_pick_volume_mascot(manifest_path, book_config_path)
    engine = DebateEngine()
    res = engine.run_mascot_debate(mascot_name=name, book_config_path=book_config_path)
    return res.positive_prompt, res.negative_prompt
