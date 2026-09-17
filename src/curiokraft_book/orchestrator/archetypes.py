"""CurioKraft Universal Page Archetype & Cover Theme Strategy Engine.

Implements the Strategy Pattern and Central Registry Pattern for publishing series.
Decouples prompt synthesis from monolithic conditionals, enabling zero-code expansion
for future publications:
  - Integrated Habitat Wildlife (Ocean, Savanna, Jungle, Sky, Prehistoric)
  - Geometric Design Patterns (Waves, Concentric Circles, Mandalas, Tessellations)
  - Activity Books (Connect-the-Dots, Mazes, Puzzle Shapes)
  - Handwriting & Tracing (Dotted Guidelines, Cursive Letterforms, Stroke Guides)
  - Educational Multi-Card Spreads (A-Z Alphabets, 0-10 Counting)
  - Single Centered Subjects (Isolated First Words, Classic Objects)
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("curiokraft.archetypes")

# Cached taxonomy and curriculum loaders
_TAXONOMY_CACHE: dict | None = None
_CURRICULUM_CACHE: dict | None = None


def _load_yaml_file(relative_path: str) -> dict:
    """Helper to safely locate and parse a YAML file."""
    candidates = [
        Path.cwd() / relative_path,
        Path(__file__).parent.parent.parent.parent / relative_path,
    ]
    for c in candidates:
        if c.exists():
            try:
                with open(c, encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Failed loading {c}: {e}")
    return {}


def get_taxonomy() -> dict:
    global _TAXONOMY_CACHE
    if _TAXONOMY_CACHE is None:
        _TAXONOMY_CACHE = _load_yaml_file("config/taxonomy.yaml")
    return _TAXONOMY_CACHE


def get_curriculum() -> dict:
    global _CURRICULUM_CACHE
    if _CURRICULUM_CACHE is None:
        _CURRICULUM_CACHE = _load_yaml_file("config/curriculum.yaml")
    return _CURRICULUM_CACHE


def join_negative_tokens(token_lists: list[list[str] | None]) -> str:
    """Flatten and deduplicate negative tokens preserving clean order."""
    seen: set[str] = set()
    result: list[str] = []
    for lst in token_lists:
        if not lst:
            continue
        for token in lst:
            t = str(token).strip()
            if t and t.lower() not in seen:
                seen.add(t.lower())
                result.append(t)
    return ", ".join(result)


# =============================================================================
# Abstract Strategy: Page Archetype
# =============================================================================


class PageArchetypeStrategy(ABC):
    """Abstract Strategy defining prompt synthesis for a specific publication archetype."""

    archetype_id: str

    @abstractmethod
    def build_prompt(
        self,
        page_record: dict[str, Any],
        book_config: dict[str, Any],
    ) -> tuple[str, str]:
        """Synthesize positive and negative prompts for this page archetype.

        Returns (positive_prompt, negative_prompt).
        """
        pass


# =============================================================================
# Concrete Strategy 1: Integrated Habitat Scene (Wildlife, Ocean, Land, Sky)
# =============================================================================


class IntegratedHabitatStrategy(PageArchetypeStrategy):
    """Archetype for living biological organisms seamlessly embedded in their natural ecosystem."""

    archetype_id = "integrated_habitat"

    def build_prompt(
        self,
        page_record: dict[str, Any],
        book_config: dict[str, Any],
    ) -> tuple[str, str]:
        taxonomy = get_taxonomy()
        standards = taxonomy.get("prompt_standards", {})
        common_neg = list(standards.get("common_coloring_negatives", []))

        canonical = page_record.get("canonical_object", "creature")
        label = page_record.get("display_label") or canonical.replace("_", " ").title()
        composition = page_record.get("composition", "integrated_aquatic_scene")
        bg_style = book_config.get("visual_style", {}).get("background", "none")

        # Resolve environment template from taxonomy
        env_templates = taxonomy.get("environment_templates", {})
        active_template = None

        # Check composition patterns
        for _key, tmpl in env_templates.items():
            comp_patterns = [p.lower() for p in tmpl.get("composition_patterns", [])]
            bg_patterns = [p.lower() for p in tmpl.get("background_patterns", [])]
            if any(p in composition.lower() for p in comp_patterns) or any(
                p in bg_style.lower() for p in bg_patterns
            ):
                active_template = tmpl
                break

        if not active_template:
            # Fallback to aquatic template if none matched
            active_template = env_templates.get("aquatic", {})

        habitat_name = active_template.get("habitat_name", "natural habitat")
        habitat_elements = active_template.get("habitat_elements", "natural environmental elements")
        subject_action = active_template.get("subject_action", "living naturally in its habitat")
        line_weight = active_template.get(
            "line_weight",
            "Bold 4pt black vector outline on subject silhouette; lighter 2pt outlines for background elements with distinct outline separation for effortless coloring.",
        )
        stroke_hierarchy = active_template.get(
            "stroke_hierarchy",
            f"Clear stroke hierarchy: bold 4pt black vector contour defining the {label} silhouette with wide open interior coloring zones, and lighter 2pt outlines for background elements.",
        ).format(readable_name=label)
        margin_reserve = active_template.get(
            "margin_reserve",
            "Leave generous 20% empty white margin space at the top of the canvas for typography.",
        )

        pos = (
            f"Pure 2D coloring book line art of an authentic living {label}, {subject_action}. "
            f"Adheres strictly to the anatomical structure of a real {label} with authentic living eyes, mouth, and natural locomotion. "
            f"Surrounded naturally by {habitat_elements}, illustrating the {label} inside its {habitat_name}. "
            f"Stroke hierarchy: {stroke_hierarchy} "
            f"{line_weight} "
            f"{margin_reserve} "
            f"Vertical 3:4 portrait orientation, perfectly centered, pure white background (#FFFFFF), "
            f"clean continuous unbroken lines, strictly NO text, NO letters, NO words, NO title labels on the drawing, "
            f"strictly zero color fills, zero shading, zero grayscale, zero pencil textures."
        )

        env_negatives = list(active_template.get("negative_tokens", []))
        neg = join_negative_tokens([common_neg, env_negatives])
        return pos, neg


# =============================================================================
# Concrete Strategy 2: Single Centered Subject (Toddler Vol 1, Isolated Items)
# =============================================================================


class SingleCenteredStrategy(PageArchetypeStrategy):
    """Archetype for single, isolated objects or preschool characters on pure white canvas."""

    archetype_id = "single_centered_subject"

    def build_prompt(
        self,
        page_record: dict[str, Any],
        book_config: dict[str, Any],
    ) -> tuple[str, str]:
        taxonomy = get_taxonomy()
        standards = taxonomy.get("prompt_standards", {})
        common_neg = list(standards.get("common_coloring_negatives", []))
        isolated_neg = list(standards.get("isolated_object_negatives", []))

        canonical = page_record.get("canonical_object", "object")
        label = page_record.get("display_label") or canonical.replace("_", " ").title()
        section = page_record.get("section", "General")

        # Determine entity type (living character vs nonliving object)
        is_living = False
        inanimate_sections = {s.lower() for s in taxonomy.get("inanimate_sections", [])}
        if section.lower() not in inanimate_sections:
            living_kw = set(taxonomy.get("living_keywords", []))
            canon_tokens = set(canonical.lower().replace("_", " ").split())
            if canon_tokens & living_kw:
                is_living = True

        if is_living:
            subject_desc = (
                f"a cute friendly baby {label} with sweet smiling round eyes and rosy cheeks"
            )
        else:
            subject_desc = (
                f"an authentic simplified physical {label} with clean silhouette, "
                f"pure inanimate object, strictly NO eyes, NO mouth, NO face, NO facial features"
            )

        pos = (
            f"Ultra-clean 2D preschool toddler coloring book line art illustration of {subject_desc}. "
            f"Thick bold black vector outlines, 5pt stroke, wide open coloring areas, perfectly centered on canvas. "
            f"Solid pure white background (#FFFFFF), completely isolated with zero background elements, zero floor lines. "
            f"Strictly NO text, NO letters, NO words, NO color, zero shading, zero grayscale, zero drop shadows."
        )

        neg_extra = []
        if not is_living:
            neg_extra = [
                "face",
                "eyes",
                "mouth",
                "smile",
                "facial features",
                "anthropomorphic",
                "cartoon eyes",
            ]

        neg = join_negative_tokens([common_neg, isolated_neg, neg_extra])
        return pos, neg


# =============================================================================
# Concrete Strategy 3: Geometric Pattern (Waves, Circles, Mandalas, Shapes)
# =============================================================================


class GeometricPatternStrategy(PageArchetypeStrategy):
    """Archetype for geometric coloring books: hypnotic waves, concentric circles, mandalas, tessellations."""

    archetype_id = "geometric_pattern"

    def build_prompt(
        self,
        page_record: dict[str, Any],
        book_config: dict[str, Any],
    ) -> tuple[str, str]:
        taxonomy = get_taxonomy()
        standards = taxonomy.get("prompt_standards", {})
        common_neg = list(standards.get("common_coloring_negatives", []))

        pattern_name = page_record.get(
            "canonical_object", page_record.get("display_label", "geometric_mandala")
        )
        label = pattern_name.replace("_", " ").title()

        pos = (
            f"Mesmerizing pure 2D black-and-white geometric coloring book line art featuring {label}. "
            f"Composed of rhythmic concentric circles, flowing harmonious wave bands, and symmetrical kaleidoscope tessellations. "
            f"Crisp uniform 3pt black vector linework defining wide, open, beautifully balanced coloring zones. "
            f"Pure radial and bilateral geometric harmony centered on vertical 3:4 portrait canvas. "
            f"Solid pure white background (#FFFFFF), zero color fills, zero shading, zero gradients, zero grayscale. "
            f"Strictly pure abstract vector line art with strictly ZERO faces, ZERO characters, ZERO text, ZERO numbers, and ZERO words."
        )

        pattern_negatives = [
            "faces",
            "eyes",
            "mouth",
            "head",
            "body",
            "animals",
            "characters",
            "people",
            "human",
            "text",
            "letters",
            "numbers",
            "words",
            "typography",
            "shading",
            "gradients",
            "gray",
            "grayscale",
            "color",
            "colors",
            "smudge",
            "pencil texture",
        ]

        neg = join_negative_tokens([common_neg, pattern_negatives])
        return pos, neg


# =============================================================================
# Concrete Strategy 4: Connect-The-Dots Activity Puzzle
# =============================================================================


class ConnectTheDotsStrategy(PageArchetypeStrategy):
    """Archetype for connect-the-dots activity pages: numbered guide dots forming hidden shapes."""

    archetype_id = "connect_the_dots"

    def build_prompt(
        self,
        page_record: dict[str, Any],
        book_config: dict[str, Any],
    ) -> tuple[str, str]:
        taxonomy = get_taxonomy()
        standards = taxonomy.get("prompt_standards", {})
        common_neg = list(standards.get("common_coloring_negatives", []))

        subject = page_record.get("canonical_object", "mystery_animal")
        label = subject.replace("_", " ").title()
        dot_count = page_record.get("dot_count", 30)

        pos = (
            f"Print-ready 2D children's connect-the-dots activity coloring page revealing a {label}. "
            f"Features an arranged sequence of exactly {dot_count} discrete, solid black circular guide dots "
            f"numbered in clear, legible ascending sequence from 1 to {dot_count}. "
            f"Faint, ultra-light dotted dashed guideline cues connect the dots outlining the recognizable contour of {label}. "
            f"Wide spacing between numbered dots ensuring effortless pencil path tracing for kids. "
            f"Vertical 3:4 portrait orientation, centered on pure stark white background (#FFFFFF). "
            f"Strictly NO solid dark black outlines pre-drawn, strictly NO shading, zero color fills."
        )

        dots_negatives = [
            "solid pre-drawn outlines",
            "heavy black contours",
            "complete dark outline",
            "pre-colored drawing",
            "shading",
            "gradients",
            "unclear numbers",
            "scrambled numbers",
            "overlapping dots",
            "text paragraphs",
            "captions",
        ]

        neg = join_negative_tokens([common_neg, dots_negatives])
        return pos, neg


# =============================================================================
# Concrete Strategy 5: Tracing & Handwriting Practice
# =============================================================================


class TracingHandwritingStrategy(PageArchetypeStrategy):
    """Archetype for letter tracing and cursive practice pages: guidelines with directional tracing paths."""

    archetype_id = "tracing_handwriting"

    def build_prompt(
        self,
        page_record: dict[str, Any],
        book_config: dict[str, Any],
    ) -> tuple[str, str]:
        taxonomy = get_taxonomy()
        standards = taxonomy.get("prompt_standards", {})
        common_neg = list(standards.get("common_coloring_negatives", []))

        letter = page_record.get("canonical_object", "letter_a").upper().replace("LETTER_", "")
        script_style = page_record.get("script_style", "cursive")

        pos = (
            f"Children's educational {script_style} handwriting and letter tracing practice worksheet for Letter '{letter}'. "
            f"Clean, horizontal primary 3-line ruling guidelines (solid top headline, dashed midline, solid baseline). "
            f"Large hollow outline {script_style} letterforms featuring a clear, centered dashed/dotted tracing path inside "
            f"with tiny directional arrow indicators showing correct stroke order. "
            f"Evenly spaced across uniform rows, vertical 3:4 portrait canvas, pure white background (#FFFFFF). "
            f"Pure vector line art only, strictly NO solid black filled letters, zero grayscale, zero shading."
        )

        tracing_negatives = [
            "solid filled black letters",
            "dark black typography",
            "unruled paper",
            "blank void",
            "shading",
            "grayscale",
            "gradients",
            "distorted letter shapes",
            "spelling mistakes",
        ]

        neg = join_negative_tokens([common_neg, tracing_negatives])
        return pos, neg


# =============================================================================
# Concrete Strategy 6: Educational Multi-Card Spread (A-Z, 0-10 Counting)
# =============================================================================


class MultiCardSpreadStrategy(PageArchetypeStrategy):
    """Archetype for educational flashcard spreads (A-Z alphabet worksheets, 0-10 counting grids)."""

    archetype_id = "multi_card_spread"
    _prompt_builder: Any = None

    @classmethod
    def set_prompt_builder(cls, builder: Any) -> None:
        cls._prompt_builder = staticmethod(builder) if builder is not None else None

    def build_prompt(
        self,
        page_record: dict[str, Any],
        book_config: dict[str, Any],
    ) -> tuple[str, str]:
        # Delegate to curriculum spread builder if injected
        builder = MultiCardSpreadStrategy._prompt_builder
        if builder is not None:
            return builder(page_record)
        try:
            import importlib

            de = importlib.import_module("curiokraft_book.orchestrator.debate_engine")
            return de.generate_dynamic_spread_prompt(page_record)
        except Exception:
            return (f"Educational flashcard spread for {page_record.get('display_label', '')}", "")


# =============================================================================
# Archetype Central Registry
# =============================================================================


class ArchetypeRegistry:
    """Central registry resolving page records to their corresponding archetype strategy."""

    _STRATEGIES: dict[str, PageArchetypeStrategy] = {
        "integrated_habitat": IntegratedHabitatStrategy(),
        "single_centered_subject": SingleCenteredStrategy(),
        "geometric_pattern": GeometricPatternStrategy(),
        "connect_the_dots": ConnectTheDotsStrategy(),
        "tracing_handwriting": TracingHandwritingStrategy(),
        "multi_card_spread": MultiCardSpreadStrategy(),
    }

    @classmethod
    def register(cls, archetype_id: str, strategy: PageArchetypeStrategy) -> None:
        """Register a new custom archetype strategy at runtime."""
        cls._STRATEGIES[archetype_id] = strategy

    @classmethod
    def resolve(
        cls,
        page_record: dict[str, Any],
        book_config: dict[str, Any],
    ) -> PageArchetypeStrategy:
        """Determine and return the appropriate Archetype strategy for a page record."""
        # 1. Explicit archetype field in manifest
        arch_id = page_record.get("archetype")
        if arch_id and arch_id in cls._STRATEGIES:
            return cls._STRATEGIES[arch_id]

        # 2. Page type checks
        p_type = str(page_record.get("type", "")).lower()
        if p_type in ["alphabet_spread", "counting_spread", "educational_spread"]:
            return cls._STRATEGIES["multi_card_spread"]

        # 3. Composition matching
        composition = str(page_record.get("composition", "")).lower()
        if composition.startswith("integrated_") or composition in [
            "aquatic",
            "marine",
            "habitat",
            "land_scene",
            "air_scene",
        ]:
            return cls._STRATEGIES["integrated_habitat"]
        if composition in ["flashcard_grid", "cards_grid"]:
            return cls._STRATEGIES["multi_card_spread"]
        if composition in ["geometric", "pattern", "mandala", "tessellation"]:
            return cls._STRATEGIES["geometric_pattern"]
        if composition in ["connect_the_dots", "dots", "dot_to_dot"]:
            return cls._STRATEGIES["connect_the_dots"]
        if composition in ["tracing", "handwriting", "cursive"]:
            return cls._STRATEGIES["tracing_handwriting"]

        # 4. Check book_config visual style background
        bg_style = book_config.get("visual_style", {}).get("background", "none")
        if bg_style != "none" and bg_style in [
            "aquatic_environment",
            "land_environment",
            "air_environment",
            "savanna_environment",
            "forest_environment",
        ]:
            return cls._STRATEGIES["integrated_habitat"]

        # 5. Default fallback
        return cls._STRATEGIES["single_centered_subject"]


# =============================================================================
# Cover Theme Strategy & Central Registry
# =============================================================================


class CoverThemeRegistry:
    """Central registry resolving book publication configurations to their Cover Theme."""

    @classmethod
    def resolve(
        cls,
        book_config: dict[str, Any],
        manifest_path: str = "",
    ) -> dict[str, Any]:
        """Resolve the active Cover Theme dictionary from config/taxonomy.yaml.

        Supports ocean, land, sky, geometric_mandala, and toddler.
        """
        taxonomy = get_taxonomy()
        themes = taxonomy.get("cover_themes", {})
        if not themes:
            logger.warning("No cover_themes found in taxonomy.yaml, using defaults.")
            return {}

        b_cfg = book_config.get("book", book_config)
        cfg_manifest = str(b_cfg.get("manifest", "")).lower().replace("\\", "/")
        norm_manifest_path = str(manifest_path).lower().replace("\\", "/")

        # Direct toddler manifest check for full backward compatibility
        if (
            norm_manifest_path
            in ["data/pages.json", "manifest/pages.json", "manifest/pages_vol2.json"]
            or "pages.json" in norm_manifest_path
        ) and "aquatic" not in norm_manifest_path:
            return themes.get("toddler", {})

        # If caller passed a standalone/test manifest that does not match the config's manifest,
        # don't contaminate the theme search context with book_config's volume/title
        if (
            cfg_manifest
            and norm_manifest_path
            and norm_manifest_path not in cfg_manifest
            and cfg_manifest not in norm_manifest_path
        ):
            search_context = norm_manifest_path
        else:
            bg_style = str(b_cfg.get("visual_style", {}).get("background", "")).lower()
            volume = str(b_cfg.get("volume", "")).lower()
            title = str(b_cfg.get("title", "")).lower()
            search_context = f"{bg_style} {volume} {title} {norm_manifest_path}"

        # 1. Match theme pattern_matchers
        for _theme_key, theme_data in themes.items():
            matchers = [m.lower() for m in theme_data.get("pattern_matchers", [])]
            if any(m in search_context for m in matchers):
                return theme_data

        # 2. Fallback to toddler for backward compatibility
        return themes.get("toddler", next(iter(themes.values()), {}))
