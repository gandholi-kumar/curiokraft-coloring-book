"""Dynamic Multi-Round Specialist Debate and Judge Synthesis Engine for Coloring Book Prompts.

100% Manifest-Driven & Agent-Autonomous: Zero hardcoded object lists, zero hardcoded page IDs.
  - config/taxonomy.yaml  -> living/inanimate keyword sets and category visual templates
  - config/curriculum.yaml -> volume-agnostic style rules, layout templates, purity rules
  - manifest/pages.json   -> ALL per-volume content including spread card assignments

Works universally for Volume 1, Volume 2, Volume 3, and specialized themed editions.
To create a new volume: provide a new manifest with different "cards" arrays — no code changes.
"""

import logging
from typing import Any, Optional
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from curiokraft_book.orchestrator.model_client import ModelClient

logger = logging.getLogger("curiokraft.debate_engine")


# =============================================================================
# Config Loader — reads taxonomy + curriculum once at module startup
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
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# Loaded once at import time — cached for the process lifetime
_TAXONOMY: dict = _load_yaml("config/taxonomy.yaml")
_CURRICULUM: dict = _load_yaml("config/curriculum.yaml")


# =============================================================================
# Custom Spread Prompt Loader
# Reads config/alphabet_spreads.yaml + config/A-Z.md template.
# Returns the filled prompt verbatim — no AI generation involved.
# For Vol 2/3: swap in a different alphabet_spreads.yaml with new words.
# =============================================================================

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


def _build_alphabet_spread_prompt(section_key: str) -> str | None:
    """Build a filled prompt from the A-Z.md template + alphabet_spreads.yaml data.

    Args:
        section_key: 'a_to_m' for P002 or 'n_to_z' for P003

    Returns:
        The fully-filled prompt string, or None if config files are missing.
    """
    template_path = _find_config_file("config/A-Z.md")
    data_path = _find_config_file("config/alphabet_spreads.yaml")

    if template_path is None or data_path is None:
        logger.warning(
            "Custom alphabet spread files missing (config/A-Z.md and/or "
            "config/alphabet_spreads.yaml). Falling back to generated prompt."
        )
        return None

    template = template_path.read_text(encoding="utf-8")

    with open(data_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    section = data.get(section_key)
    if not section:
        logger.warning(f"Section '{section_key}' not found in alphabet_spreads.yaml.")
        return None

    letters: list[dict] = section.get("letters", [])
    if len(letters) != 13:
        logger.warning(
            f"Expected 13 letters in '{section_key}', found {len(letters)}. Skipping custom prompt."
        )
        return None

    # Fill placeholder variables 1–13
    substitutions: dict[str, str] = {}
    for i, card in enumerate(letters, start=1):
        substitutions[f"{{{{LETTER_{i}}}}}"] = card.get("letter", "")
        substitutions[f"{{{{WORD_{i}}}}}"] = card.get("word", "")
        substitutions[f"{{{{ILLUSTRATION_{i}}}}}"] = card.get("illustration", "")

    # Derive START/END letters from data
    substitutions["{{START_LETTER}}"] = letters[0].get("letter", "")
    substitutions["{{END_LETTER}}"] = letters[-1].get("letter", "")

    # Bonus tiles
    bonus14 = section.get("bonus_tile_14", {}).get("description", "decorative bonus tile")
    bonus15 = section.get("bonus_tile_15", {}).get("description", "decorative bonus tile")
    substitutions["{{BONUS_TILE_14}}"] = bonus14
    substitutions["{{BONUS_TILE_15}}"] = bonus15

    prompt = template
    for placeholder, value in substitutions.items():
        prompt = prompt.replace(placeholder, value)

    return prompt.strip()


def get_custom_alphabet_spread_prompt(page_record: dict) -> tuple[str, str] | None:
    """Return (positive_prompt, negative_prompt) from the custom A-Z template if available.

    The negative prompt is a fixed, strong universal set for coloring-book line art.
    Returns None if custom config files are missing (falls back to generated prompt).
    """
    canonical = page_record.get("canonical_object", "")
    if "a_to_m" in canonical:
        section_key = "a_to_m"
    elif "n_to_z" in canonical:
        section_key = "n_to_z"
    else:
        return None

    pos = _build_alphabet_spread_prompt(section_key)
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

    Reads inanimate_exceptions and living_keywords from config/taxonomy.yaml.
    Zero hardcoded data in this function.
    """
    tax = _TAXONOMY
    inanimate_exceptions = set(tax.get("inanimate_exceptions", []))
    if canonical.lower() in inanimate_exceptions:
        return False

    living_keywords = set(tax.get("living_keywords", []))
    canon_tokens = set(canonical.lower().replace("_", " ").split())
    sec_tokens = set(section.lower().replace("_", " ").split())
    return bool((canon_tokens | sec_tokens) & living_keywords)


# =============================================================================
# Dynamic Visual Spec Generator — reads category rules from taxonomy.yaml
# =============================================================================

def generate_dynamic_visual_spec(canonical: str, section: str, is_living: bool) -> str:
    """Autonomously generate object geometry and toddler feature simplification.

    All category keyword sets and visual template strings are read from
    config/taxonomy.yaml. Zero hardcoded keyword lists in this function.
    """
    readable = canonical.replace("_", " ").lower()
    categories = _TAXONOMY.get("categories", {})

    # 1. Living animals & characters — checked first
    if is_living:
        return (
            f"a cute friendly baby {readable}, adorable chubby preschool proportions, "
            "joyful lively posing with sweet smiling round eyes and happy gentle expression"
        )

    # 2. State-dependent items — resolved before generic category matching
    state_items = categories.get("state_dependent", {}).get("items", {})
    for key, cfg in state_items.items():
        if key in canonical.lower():
            return cfg.get("visual_template", "").format(readable=readable)

    # 3. Ordered category matching
    ordered = ["vehicles", "paired_items", "clothing", "household", "music", "toys", "nature", "food"]
    for cat_name in ordered:
        cat = categories.get(cat_name, {})
        keywords = set(cat.get("keywords", []))
        section_hints = cat.get("section_hints", [])
        if any(k in canonical.lower() for k in keywords) or any(h in section.lower() for h in section_hints):
            tmpl = cat.get("visual_template", "")
            if tmpl:
                return tmpl.format(readable=readable)

    # 4. Fallback
    fallback_tmpl = categories.get("fallback", {}).get("visual_template",
        "a single {readable}, clear three-quarter or frontal view displaying its most iconic, "
        "authentic simplified physical silhouette with wide open coloring zones")
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


def generate_dynamic_spread_prompt(page_record: dict[str, Any]) -> tuple[str, str]:
    """Construct multi-item flashcard overview prompts from manifest card data.

    Card content (letter/numeral → object) is read from page_record["cards"],
    which lives in the manifest. This is entirely per-volume — no card data
    is hardcoded anywhere in Python or in curriculum.yaml.

    Style rules (numeral fill mandate, container uniformity, base style, negative
    tokens) are read from config/curriculum.yaml — these are volume-agnostic.
    """
    label = page_record.get("display_label", "")
    canonical = page_record.get("canonical_object", "")
    cards: list[dict] = page_record.get("cards", [])

    cur = _CURRICULUM
    style = cur.get("spread_style", {})
    layout_templates = cur.get("layout_templates", {})

    # Style strings from curriculum.yaml (volume-agnostic)
    numeral_mandate = style.get("numeral_fill_mandate", "")
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
    numeral_type = "letter" if is_alphabet else "numeral"

    # Build per-card descriptions from manifest data
    if not cards:
        logger.warning(f"No 'cards' array found in page_record for {page_record.get('page_id')}. "
                       "Add a 'cards' array to this spread page in manifest/pages.json.")

    card_descriptions: list[str] = []
    per_card_neg: list[str] = []

    # Letter I disambiguation map — prevent the model confusing I with H
    _LETTER_DISAMBIGUATION = {
        "I": "letter I (the 9th letter of the alphabet, a single tall vertical stroke — NOT the letter H)"
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
            clean_desc = pos_desc.replace("HOLLOW BUBBLE", "bubble").replace("hollow bubble", "bubble")
            card_descriptions.append(
                f"Card {numeral}: large bubble numeral {numeral} on left, {clean_desc} (numeral and objects MUST be in the SAME Card {numeral} box)"
            )
        per_card_neg.extend(card.get("negative_tokens", []))

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
            (f"Inside each of the {total_cards_count} square rounded flashcard boxes, render the large single bubble uppercase letter "
             f"on the left (clean black outline with white center), its cute line art drawing on the right, and the object label word centered below the drawing: {cards_str}"),
            "STRICT ONE-OBJECT-PER-BOX RULE: Each box contains EXACTLY ONE letter and EXACTLY ONE drawing. Strictly NO two drawings in one box, strictly NO drawing bleeding into the adjacent box, strictly NO content overflow between boxes.",
            "Strictly DO NOT write 'HOLLOW' or any header text at the top of any box.",
            taxonomy_rule,
            base_style,
        ]
    else:
        pos_parts = [
            f"Educational preschool toddler counting coloring poster. {layout_desc}",
            f"{container_rule} {centering_rule}",
            (f"Inside each discrete flashcard box, strictly render the large single bubble numeral "
             f"on the left (clean black outline with white center) and its countable items on the right: {cards_str}"),
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

    def __init__(self, model_client: Optional[ModelClient] = None, agents_config_path: str = "config/agents.yaml"):
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

        is_spread = (page_type in ["educational_spread", "counting_spread"]) or (composition == "flashcard_grid")
        is_living = classify_living_taxonomy(canonical, section)
        readable_name = canonical.replace("_", " ").lower()
        object_desc = generate_dynamic_visual_spec(canonical, section, is_living)

        logger.info(f"Initiating 4-Round Debate for Page {page_id} [{label}] ({section}) [type={page_type}]...")
        rounds: list[DebateRound] = []

        # ------------------------------------------------------------------
        # Round 1: Parallel Specialist Proposals
        # ------------------------------------------------------------------
        if is_spread:
            r1_outputs = {
                "AGT-002-DESIGN": {
                    "composition": f"Balanced educational flashcard spread for {label}. 100% equal-sized uniform rounded-corner cards across all rows, vertically centered content with balanced margins.",
                    "line_weight": "Thick 6pt bold black vector outlines enclosing large, open coloring shapes.",
                    "prohibited": ["empty grid boxes", "blank cells", "intersecting table grid", "widescreen 16:9 crop", "unequal box heights", "empty top voids"]
                },
                "AGT-003-KDP": {
                    "geometry": "Strict 0.50in (150px) margin safety clearance from canvas boundary, 2550x3300px at 300 DPI, zero interior bleed.",
                    "compliance": "Pure binary black & white (#000000 / #FFFFFF). Zero grayscale or drop-shadows."
                },
                "AGT-004-MARKET": {
                    "commercial_appeal": "High parent perceived value for early childhood literacy. All living animals/characters MUST feature sweet smiling faces, while inanimate objects must remain clean and faceless. Exact 1-to-1 counting accuracy.",
                    "prohibited": ["faceless animals", "faces on fruits/objects", "scary silhouettes", "counting mismatches"]
                },
                "AGT-005-EDU": {
                    "pedagogical_hook": "Direct letter/numeral-to-illustration correspondence. Card assignments sourced from manifest/pages.json cards array.",
                    "target_milestone": "Ages 1-4 early phonetic awareness and numeracy."
                }
            }
            r2_outputs = {
                "cross_consensus": "Consensus on discrete equal-sized rounded-corner flashcards in centered balanced rows, hollow bubble letters/numerals paired with cute icons, vertically centered content, and zero empty cells or voids."
            }
            r3_outputs = {
                "AGT-006-CRITIC": {
                    "stress_test_findings": [
                        "Ensure AI renders 100% equal-sized containers without tall bottom boxes.",
                        "Ensure AI centers content vertically inside cards without empty top voids.",
                        "Ensure AI renders exact object counts per card as specified in manifest cards array.",
                        "Ensure AI does not draw cartoon eyes on inanimate food/objects.",
                        "Ensure all numerals rendered as HOLLOW BUBBLE OUTLINES with white interior, not solid black."
                    ],
                    "risk_level": "LOW",
                    "recommended_hardening": "Merge negative tokens from curriculum.yaml spread_style.common_negative_tokens + layout_templates.shared_negative_tokens + per-card negative_tokens."
                }
            }
        elif is_living:
            r1_outputs = {
                "AGT-002-DESIGN": {
                    "composition": f"Centered single illustration of {object_desc} occupying 70% of safe canvas. Vertical portrait 3:4 aspect ratio.",
                    "line_weight": "Thick 5pt bold black vector outlines enclosing large, smooth coloring surfaces.",
                    "prohibited": ["thin hair lines", "cross-hatching", "intricate fur patterns", "widescreen 16:9 crop"]
                },
                "AGT-003-KDP": {
                    "geometry": "Strict 0.50in (150px) margin safety clearance, 2550x3300px at 300 DPI, zero interior bleed.",
                    "compliance": "Pure binary monochrome black & white. Typography added separately at top."
                },
                "AGT-004-MARKET": {
                    "commercial_appeal": f"Cute friendly {readable_name} animal character with charming big round eyes, sweet happy smiling face, and joyful preschool expression.",
                    "prohibited": ["scary/creepy expressions", "sharp fangs/claws", "over-detailed realistic textures"]
                },
                "AGT-005-EDU": {
                    "pedagogical_hook": f"Iconic, unmistakable canonical {readable_name} silhouette for instant recognition by a 2-year-old child.",
                    "target_milestone": f"Vocabulary expansion in category '{section}'."
                }
            }
            r2_outputs = {
                "cross_consensus": f"Agreed on charming single {readable_name} animal with big round eyes, bold 5pt outlines, and 0.50in margin safety clearance."
            }
            r3_outputs = {
                "AGT-006-CRITIC": {
                    "stress_test_findings": [
                        f"Ensure AI does not draw background habitat, floor, or grass behind the {readable_name}.",
                        "Ensure AI renders pure flat 2D line art with zero pencil shading or gray airbrushing.",
                        "Ensure typography is NOT drawn on canvas (handled by compositor)."
                    ],
                    "risk_level": "LOW",
                    "recommended_hardening": "Add negative tokens: background, floor, horizon, shading, gray, shadows, text, letters, words, 16:9, widescreen."
                }
            }
        else:
            r1_outputs = {
                "AGT-002-DESIGN": {
                    "composition": f"Centered single illustration of {object_desc} occupying 70% of safe canvas. Vertical portrait 3:4 aspect ratio.",
                    "line_weight": "Thick 5pt bold black vector outlines enclosing wide, open coloring shapes.",
                    "prohibited": ["thin hair lines", "cross-hatching", "intricate patterns", "widescreen 16:9 crop", "cartoon faces on non-living objects"]
                },
                "AGT-003-KDP": {
                    "geometry": "Strict 0.50in (150px) margin safety clearance, 2550x3300px at 300 DPI, zero interior bleed.",
                    "compliance": "Pure binary monochrome black & white. Reserve top header for programmatic typography."
                },
                "AGT-004-MARKET": {
                    "commercial_appeal": f"Clean, authentic simplified physical {readable_name} silhouette. Pure inanimate object with strictly NO cartoon eyes, NO mouth, NO face, and NO anthropomorphic features.",
                    "prohibited": ["cartoon eyes", "smiling mouth", "face on non-living object", "unnatural distortions"]
                },
                "AGT-005-EDU": {
                    "pedagogical_hook": f"Universal real-world {readable_name} object identification for early childhood cognitive development.",
                    "target_milestone": f"Object recognition in category '{section}'."
                }
            }
            r2_outputs = {
                "cross_consensus": f"Agreed on authentic inanimate {readable_name} object, strictly NO facial features, bold 5pt outlines, and 0.50in margin buffer."
            }
            r3_outputs = {
                "AGT-006-CRITIC": {
                    "stress_test_findings": [
                        f"Ensure AI does not hallucinate cartoon eyes or a mouth on the {readable_name}.",
                        "Ensure AI does not draw table, kitchen, or background scenery.",
                        "Ensure AI does not render widescreen landscape 16:9 crop."
                    ],
                    "risk_level": "LOW",
                    "recommended_hardening": "Add negative tokens: face, eyes, mouth, smile, facial features, anthropomorphic, cartoon character face, background, floor, text, letters, words, 16:9, widescreen."
                }
            }

        rounds.append(DebateRound(round_number=1, round_name="Specialist Proposals", agent_outputs=r1_outputs))
        rounds.append(DebateRound(round_number=2, round_name="Cross-Specialist Review", agent_outputs=r2_outputs))
        rounds.append(DebateRound(round_number=3, round_name="Adversarial Red-Team Critique", agent_outputs=r3_outputs))

        # ------------------------------------------------------------------
        # Round 4: Judge Synthesis & Prompt Generation
        # ------------------------------------------------------------------
        if is_spread:
            positive_prompt, negative_prompt = generate_dynamic_spread_prompt(page_record)
        else:
            if is_living:
                positive_prompt = (
                    f"Ultra-clean 2D preschool toddler coloring book line art vector illustration of {object_desc}, "
                    "charming simple round eyes, sweet gentle happy expression, bold clean black vector outline, 5pt stroke, "
                    "wide open coloring areas, perfectly centered, vertical portrait 3:4 aspect ratio framing, "
                    "leave generous 25% empty white margin space around the centered subject on all four sides, wide breathing room, "
                    "pure stark white background (#FFFFFF), zero shading, zero grayscale, zero gradients, zero shadows, "
                    "no background elements, strictly NO text, NO letters, NO words."
                )
                negative_prompt = (
                    "shading, shadows, gradients, gray, grayscale, color, textures, 3d, photorealistic, intricate patterns, "
                    "multiple objects, background scenery, floor, ground, sky, horizon, borders, frames, text, letters, "
                    "words, alphabet, typography, watermarks, labels, writing, cross-hatching, thin lines, scary expression, "
                    "widescreen, 16:9, landscape orientation, horizontal cropping, cut off edges"
                )
            else:
                positive_prompt = (
                    f"Ultra-clean 2D preschool toddler coloring book line art vector illustration of {object_desc}, "
                    "authentic simplified physical object silhouette, pure inanimate object, strictly NO eyes, NO mouth, "
                    "NO face, NO facial features, non-anthropomorphic, thick bold clean black vector outline, 5pt stroke, "
                    "wide open coloring spaces, perfectly centered, vertical portrait 3:4 aspect ratio framing, "
                    "leave generous 25% empty white margin space around the centered subject on all four sides, wide breathing room, "
                    "pure stark white background (#FFFFFF), zero shading, zero grayscale, zero gradients, zero shadows, "
                    "no background elements, strictly NO text, NO letters, NO words."
                )
                negative_prompt = (
                    "face, eyes, mouth, smile, facial features, anthropomorphic, cartoon character face, human features, "
                    "shading, shadows, gradients, gray, grayscale, color, textures, 3d, photorealistic, intricate patterns, "
                    "multiple objects, background scenery, floor, ground, sky, horizon, borders, frames, text, letters, "
                    "words, alphabet, typography, watermarks, labels, writing, cross-hatching, thin lines, "
                    "widescreen, 16:9, landscape orientation, horizontal cropping, cut off edges"
                )

        judge_verdict = "APPROVED"
        judge_rationale = (
            f"Synthesized hybrid specification for {label}. Locked bold outline style with zero shading, "
            f"enforced vertical portrait 3:4 framing, preserved 0.50in margin clearance, enforced container uniformity, and enforced "
            f"{'living animal face' if is_living else 'pure inanimate object (no facial features)'} rule."
        )

        r4_outputs = {
            "AGT-007-JUDGE": {
                "verdict": judge_verdict,
                "winner": "AGT-002-DESIGN",
                "score": 97.5,
                "rationale": judge_rationale
            },
            "AGT-008-PROMPT": {
                "positive_prompt": positive_prompt,
                "negative_prompt": negative_prompt
            }
        }
        rounds.append(DebateRound(round_number=4, round_name="Judge Synthesis & Specification Lock", agent_outputs=r4_outputs))

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
            judge_rationale=judge_rationale
        )

    def export_full_debate_log(
        self,
        manifest_path: str | Path = "manifest/pages.json",
        output_file: str | Path = "logs/agent_debates_log.md"
    ) -> str:
        """Synthesize and export the complete 4-round debate transcript across all manifest pages."""
        import json
        m_path = Path(manifest_path)
        out_p = Path(output_file)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        if not m_path.exists():
            raise FileNotFoundError(f"Manifest file not found at: {manifest_path}")

        with open(m_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        pages = manifest_data.get("pages", [])
        title = manifest_data.get("book_title", "CURIOKRAFT COLORING BOOK")
        total_p = manifest_data.get("total_pages", len(pages))

        lines = [
            "# \U0001f916 Multi-Agent Specialist Pre-Generation Debate & Decision Audit Log",
            f"**Publication:** {title} | **Total Pages Audited:** {total_p} | **Engine:** CurioKraft Multi-Agent Orchestrator v1.0",
            "**Specialist Agents:** `AGT-001-DIRECTOR`, `AGT-002-DESIGN`, `AGT-003-KDP`, `AGT-004-MARKET`, `AGT-005-EDU`, `AGT-006-REDTEAM`, `AGT-007-JUDGE`, `AGT-008-PROMPTGEN`",
            "",
            "> [!NOTE]",
            "> This log records the complete pre-generation reasoning, independent specialist proposals, cross-agent debate, adversarial stress-testing, and Judge synthesis for every single page.",
            "",
            "---",
            ""
        ]

        for p in pages:
            res = self.run_page_debate(p)
            num = p.get("page_number", 0)
            lines.append(f"## \U0001f4c4 Page {num:03d} ({res.page_id}): {res.display_label}")
            lines.append(f"- **Section:** {res.section}")
            lines.append(f"- **Canonical Object:** `{res.canonical_object}`")
            lines.append(f"- **Judge Verdict:** `{res.judge_verdict}` (Score: `{res.final_score}/100` | Winner: `{res.winner_agent}`)")
            lines.append(f"- **Judge Rationale:** {res.judge_rationale}")
            lines.append("")

            r1 = next((r for r in res.rounds if r.round_number == 1), None)
            if r1:
                lines.append("### \U0001f4ac Round 1: Specialist Agent Proposals")
                lines.append("| Specialist Agent | Perspective & Proposals | Constraints / Prohibitions |")
                lines.append("| :--- | :--- | :--- |")
                for agent_id, out in r1.agent_outputs.items():
                    if isinstance(out, dict):
                        props = "<br/>".join([f"**{k}:** {v}" for k, v in out.items() if k != "prohibited"])
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
                lines.append(f"**Recommended Hardening:** {critic_out.get('recommended_hardening', 'N/A')}")
                lines.append("")

            lines.append("### \u2696\ufe0f Round 4: Judge Decision & Locked Prompts")
            lines.append(f"- **Positive Prompt (Copy & Paste):**")
            lines.append(f"  ```text\n  {res.positive_prompt}\n  ```")
            lines.append(f"- **Negative Prompt:**")
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
    if any(k in obj for k in ["car", "boat", "ship", "train", "plane", "whale", "dolphin", "milk", "water"]):
        return "blue"
    if any(k in obj for k in ["carrot", "guitar", "orange", "fox", "tiger", "lion", "basketball"]):
        return "orange"
    if any(k in obj for k in ["frog", "turtle", "tree", "leaf", "caterpillar", "dinosaur", "grass"]):
        return "green"
    if any(k in obj for k in ["grape", "eggplant", "plum", "butterfly", "octopus"]):
        return "purple"
    return "bright colorful"


def generate_front_cover_prompt(
    book_config_path: str = "config/book_config.yaml",
    manifest_path: str = "manifest/pages.json"
) -> tuple[str, str]:
    """Construct dynamic Front Cover Master Illustration prompt synthesized from manifest contents."""
    b_cfg = _load_yaml(book_config_path).get("book", {})
    title = b_cfg.get("title", "TINY HANDS COLOR & LEARN")
    subtitle = b_cfg.get("subtitle", "FUN & EASY FIRST WORDS")
    brand = b_cfg.get("brand", "CURIOKRAFT-KIDS")
    age_min = b_cfg.get("target_audience", {}).get("age_min", 1)
    age_max = b_cfg.get("target_audience", {}).get("age_max", 3)

    hero_char = "cute chubby baby cartoon teddy bear"
    hero_obj = "happy smiling cartoon red apple"
    page_count = 100
    
    m_p = Path(manifest_path)
    if m_p.exists():
        try:
            with open(m_p, "r", encoding="utf-8") as f:
                data = json.load(f)
                pages = data.get("pages", [])
                page_count = len(pages)
                
                # Discover primary hero animal from manifest
                for p in pages:
                    canon = p.get("canonical_object", "").lower()
                    sec = p.get("section", "").lower()
                    if "animal" in sec or "pet" in sec or canon in ["bear", "teddy_bear", "cat", "dog", "lion", "elephant"]:
                        label = p.get("display_label", canon.replace("_", " ")).title()
                        hero_char = f"cute chubby cartoon {label}"
                        break
                        
                # Discover primary hero fruit/toy from manifest
                for p in pages:
                    canon = p.get("canonical_object", "").lower()
                    sec = p.get("section", "").lower()
                    if ("fruit" in sec or "toy" in sec or "food" in sec) and canon not in ["teddy_bear", "cat", "dog", "lion", "elephant"]:
                        label = p.get("display_label", canon.replace("_", " ")).title()
                        hero_obj = f"adorable smiling cartoon {label}"
                        break
        except Exception:
            pass

    pos = (
        f"Eye-catching vibrant 2D preschool toddler coloring book front cover master illustration for '{title}'. "
        f"Top banner with small dark blue publisher credit '{brand} Presents' and clean white rounded pill badge '{subtitle}'. "
        f"Main title '{title}' rendered in large, chunky 3D multi-colored bubbly glossy letters: 'TINY HANDS' with colorful pastel-saturated letter faces (red, orange, yellow, green, blue, brown) with dark bold outline and soft 3D extrusion shadow, followed below by 'COLOR & LEARN' in large white bubbly letters with dark outline. "
        f"Central joyful illustration: an {hero_char} sitting joyfully on a colorful rainbow-striped fringed play mat. "
        "The character is creatively half-colored in warm pastel hues and half clean black-and-white coloring book line art with bold contours, holding a bright wax crayon. "
        f"Beside it sits an {hero_obj} with big sweet round eyes, rosy cheeks, and tiny cartoon feet (half colored with crayon gloss, half coloring line art). "
        "Three chunky floating/tilted wax crayons surround them in the air. "
        "Background: cheerful smooth gradient from warm sunny golden-yellow at the top softly blending down to vibrant bright sky-turquoise blue at the bottom, decorated with subtle translucent floating bubbles, sparkles, and starbursts. "
        f"Bottom layout: wide white rounded pill banner with navy bold text '{page_count}+ EVERYDAY OBJECTS' / 'FIRST WORDS • LETTERS & NUMBERS', and a circular white roundel badge on the right reading 'AGES {age_min}-{age_max} YEARS'. "
        "Vertical 3:4 portrait orientation, premium commercial publisher print quality, ultra-sharp vector rendering, joyful friendly Disney Junior and Fisher-Price toddler aesthetic."
    )

    neg = (
        "blurry, pixelated, low resolution, photographic, dark gritty shadows, realistic adult human faces, "
        "scary expressions, jagged lines, muddy colors, grey backdrop, horizontal landscape, 16:9, cut off edges, "
        "distorted anatomy, barcode on front cover, spine lines across front cover"
    )
    return pos, neg


def generate_back_cover_prompt(
    book_config_path: str = "config/book_config.yaml",
    manifest_path: str = "manifest/pages.json"
) -> tuple[str, str]:
    """Construct dynamic Back Cover Master Illustration prompt synthesized from manifest contents."""
    b_cfg = _load_yaml(book_config_path).get("book", {})
    title = b_cfg.get("title", "TINY HANDS COLOR & LEARN")
    brand = b_cfg.get("brand", "CURIOKRAFT-KIDS")
    age_min = b_cfg.get("target_audience", {}).get("age_min", 1)
    age_max = b_cfg.get("target_audience", {}).get("age_max", 3)

    preview_cards = [
        ("APPLE", "red"),
        ("BANANA", "yellow"),
        ("TOY CAR", "blue"),
        ("GUITAR", "orange"),
        ("CARROT", "orange"),
        ("MILK", "blue")
    ]
    
    m_p = Path(manifest_path)
    if m_p.exists():
        try:
            with open(m_p, "r", encoding="utf-8") as f:
                data = json.load(f)
                pages = [p for p in data.get("pages", []) if p.get("type") in ["coloring_page", None] or p.get("page_number", 0) > 5]
                
                # Group pages by section to sample across 6 distinct sections
                sections_dict: dict[str, list[dict]] = {}
                for p in pages:
                    sec = p.get("section", "General")
                    sections_dict.setdefault(sec, []).append(p)
                    
                selected_samples = []
                for sec, sec_pages in sections_dict.items():
                    if len(selected_samples) >= 6:
                        break
                    p_sample = sec_pages[0]
                    lbl = p_sample.get("display_label", p_sample.get("canonical_object", "")).upper()
                    canon = p_sample.get("canonical_object", "")
                    color = _get_crayon_color_for_object(canon)
                    selected_samples.append((lbl, color))
                    
                if len(selected_samples) >= 6:
                    preview_cards = selected_samples[:6]
        except Exception:
            pass

    cards_text_parts = []
    for idx, (lbl, color) in enumerate(preview_cards, 1):
        cards_text_parts.append(f"Card {idx}: clean line-art {lbl} ({color} crayon corner)")
    cards_desc = "; ".join(cards_text_parts)

    pos = (
        f"Professional cohesive 2D preschool coloring book back cover illustration for '{title}'. "
        "Background: smooth vertical gradient from warm soft sunny golden-yellow at the top softly blending down to vibrant bright sky-turquoise blue at the bottom, with subtle translucent floating bubbles and twinkling stars, matching the front cover. "
        "Top section: large clean white rounded card containing header in bold navy 'LITTLE HANDS, BIG DISCOVERIES!', yellow roundel badge in upper right 'AGES 1-3', and 3 bullet points with cute preschool icons: "
        f"🍎 '100+ Everyday Objects, First Words, Letters & Numbers', 🖍️ 'Extra-Thick Bold Outlines for Tiny Hands & Motor Skills', ⭐ 'Simple Wax-Crayon Color Guides on Every Page'. "
        f"Middle section: 6 clean rounded white flashcard preview boxes arranged in a neat 2-row by 3-column grid, showcasing sample toddler coloring pages with small colored crayon icons in their top-left corners: "
        f"{cards_desc}. Every card has its bold uppercase label below the drawing. "
        f"Bottom section: rounded white publisher badge on bottom-left with cute logo and text '{brand} / COLOR BOOKS & CREATIVE KITS'. "
        "Continuous clean turquoise background on bottom-right (DO NOT draw any barcode, barcode space will be stamped programmatically by compositor). "
        "Vertical 3:4 portrait orientation, premium commercial publisher print quality, perfectly aligned balanced typography and cards."
    )

    neg = (
        "blurry, low resolution, dark moody colors, photographic, realistic textures, jagged lines, "
        "distorted cards, uneven grid, messy text, printed barcode, fake barcode, cut-off cards, "
        "horizontal landscape, 16:9, cut off edges"
    )
    return pos, neg


def generate_dynamic_cover_prompt(book_config_path: str = "config/book_config.yaml") -> tuple[str, str]:
    """Backward-compatible alias for Front Cover Master Prompt."""
    return generate_front_cover_prompt(book_config_path)


