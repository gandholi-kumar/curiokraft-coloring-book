"""Layout Blueprint Ingestion Engine for CurioKraft Multi-Agent Publishing System.

Enables users to drop layout wireframes, mockups, or blueprint specs into `inbox/blueprints/`
(or `inbox/`). Specialist agents (Director, Design Specialist, Vision QA, Red-Team)
read the layout geometry and dynamically structure the content, card slots, pill grids,
and baseline waves to match the user's design.
"""

import json
import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from curiokraft_book.orchestrator.model_client import ModelClient

logger = logging.getLogger("curiokraft.blueprint_reader")

DEFAULT_BLUEPRINTS_DIR = Path("inbox/blueprints")
DEFAULT_INBOX_DIR = Path("inbox")


class BlueprintCardGridSpec(BaseModel):
    """Layout specification for flashcard preview or object containers."""

    rows: int = 1
    columns: int = 3
    card_shape: str = "rounded_rectangle"
    border_style: str = "thin dark charcoal border"
    content_type: str = "2D coloring book line art"
    notes: str = "equal-sized containers in neat horizontal row"


class BlueprintFeatureCalloutSpec(BaseModel):
    """Layout specification for parent feature callouts / benefit pills."""

    layout: str = "2x2_grid"  # "2x2_grid", "1x4_row", "vertical_list", "pill_banner"
    count: int = 4
    shape: str = "rounded_pill"
    bullet_style: str = "star"
    placement: str = "directly below flashcards and above bottom rolling wave"


class BlueprintWaveSpec(BaseModel):
    """Layout specification for ground curve or baseline wave."""

    height_percentage: int = 20
    style: str = "smooth rolling wave in pastel turquoise and mint"
    spine_continuity: str = "horizontally flat at spine fold, borderless"


class BlueprintLayoutSpec(BaseModel):
    """Comprehensive parsed blueprint layout specification."""

    source_path: str
    target_type: str = "back_cover"  # "back_cover", "front_cover", "interior_page", "spread"
    headline_style: str = "bold uppercase headline centered at top"
    description_style: str = "friendly parent description in clean dark navy typography"
    card_grid: BlueprintCardGridSpec = Field(default_factory=BlueprintCardGridSpec)
    feature_callouts: BlueprintFeatureCalloutSpec = Field(
        default_factory=BlueprintFeatureCalloutSpec
    )
    baseline_wave: BlueprintWaveSpec = Field(default_factory=BlueprintWaveSpec)
    exclusion_zones_respected: bool = True
    custom_directives: list[str] = Field(default_factory=list)

    def to_prompt_composition(self) -> str:
        """Render layout specification into an explicit diffusion prompt composition block."""
        cards_layout_desc = (
            f"exactly {self.card_grid.columns * self.card_grid.rows} clean, upright white rounded flashcard preview boxes "
            f"arranged in a neat {self.card_grid.rows} row by {self.card_grid.columns} columns grid, "
            f"each with a {self.card_grid.border_style}. {self.card_grid.notes}."
        )
        pills_layout_desc = (
            f"Middle-lower zone ({self.feature_callouts.placement}): "
            f"features {self.feature_callouts.count} neat, colorful pastel rounded feature note pills "
            f"arranged in a balanced {self.feature_callouts.layout.replace('_', ' ')} with playful {self.feature_callouts.bullet_style} bullets."
        )
        wave_layout_desc = (
            f"Bottom baseline features the exact same {self.baseline_wave.style} across the lower "
            f"{self.baseline_wave.height_percentage}% of the canvas. {self.baseline_wave.spine_continuity}."
        )
        return f"{cards_layout_desc} {pills_layout_desc} {wave_layout_desc}"


class LayoutBlueprintReader:
    """Discovers, parses, and converts user layout blueprints into agent-consumable specs."""

    def __init__(
        self,
        blueprints_dir: Path | str = DEFAULT_BLUEPRINTS_DIR,
        inbox_dir: Path | str = DEFAULT_INBOX_DIR,
        model_client: ModelClient | None = None,
    ):
        self.blueprints_dir = Path(blueprints_dir)
        self.inbox_dir = Path(inbox_dir)
        self.client = model_client or ModelClient()

    def find_blueprint(self, target_type: str = "back_cover") -> Path | None:
        """Locate user-dropped blueprint matching the target_type."""
        clean_target = target_type.lower().strip()
        search_dirs = [self.blueprints_dir, self.inbox_dir]

        # Prioritize matching file stems
        stem_candidates = [
            f"{clean_target}_blueprint",
            f"blueprint_{clean_target}",
            f"{clean_target}_wireframe",
            f"{clean_target}_layout",
            "cover_blueprint" if "cover" in clean_target else None,
            "blueprint",
        ]
        stem_candidates = [s for s in stem_candidates if s]

        valid_extensions = [".png", ".jpg", ".jpeg", ".webp", ".yaml", ".yml", ".json"]

        for d in search_dirs:
            if not d.exists():
                continue
            for f in d.iterdir():
                if not f.is_file():
                    continue
                f_stem = f.stem.lower()
                f_ext = f.suffix.lower()
                if f_ext in valid_extensions:
                    for cand in stem_candidates:
                        if f_stem == cand or cand in f_stem:
                            logger.info(f"Found layout blueprint: {f}")
                            return f

        return None

    def read_blueprint(self, blueprint_path: Path | str) -> BlueprintLayoutSpec:
        """Parse blueprint file (visual image or YAML/JSON spec) into BlueprintLayoutSpec."""
        p = Path(blueprint_path)
        if not p.exists():
            raise FileNotFoundError(f"Blueprint file does not exist: {blueprint_path}")

        ext = p.suffix.lower()
        if ext in [".yaml", ".yml"]:
            return self._parse_yaml_blueprint(p)
        elif ext == ".json":
            return self._parse_json_blueprint(p)
        elif ext in [".png", ".jpg", ".jpeg", ".webp"]:
            return self._parse_image_blueprint(p)
        else:
            raise ValueError(f"Unsupported blueprint format: {ext}")

    def _parse_yaml_blueprint(self, path: Path) -> BlueprintLayoutSpec:
        """Parse structured YAML blueprint."""
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return self._build_spec_from_dict(data, source_path=str(path))

    def _parse_json_blueprint(self, path: Path) -> BlueprintLayoutSpec:
        """Parse structured JSON blueprint."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f) or {}
        return self._build_spec_from_dict(data, source_path=str(path))

    def _parse_image_blueprint(self, path: Path) -> BlueprintLayoutSpec:
        """Analyze visual layout wireframe/mockup image via multimodal vision."""
        system_prompt = (
            "YOU ARE: The Children's Book Design Specialist (AGT-002) and Vision QA Inspector (AGT-009). "
            "Analyze this user-dropped coloring book layout blueprint/wireframe image. "
            "Extract the exact spatial layout zones: headline zone, parent copy zone, flashcard grid (rows, columns, shapes), "
            "feature callout notes (pill count, grid structure), and bottom baseline wave height. "
            "Output strictly valid JSON with keys: target_type, card_grid (rows, columns, card_shape, border_style), "
            "feature_callouts (layout, count, shape, bullet_style), baseline_wave (height_percentage, style), custom_directives."
        )
        user_prompt = (
            f"Extract the exact layout geometry and structure from this blueprint image ({path.name}) "
            "so our specialist agents can structure the illustration prompt to match this user's design."
        )

        resp = self.client.call_vision(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            image_path=path,
            response_schema=dict,
        )

        parsed = resp.parsed_json or {}
        return self._build_spec_from_dict(parsed, source_path=str(path))

    def _build_spec_from_dict(self, data: dict, source_path: str) -> BlueprintLayoutSpec:
        """Construct BlueprintLayoutSpec from dictionary payload."""
        cards_raw = data.get("card_grid", data.get("cards", {}))
        card_grid = BlueprintCardGridSpec(
            rows=cards_raw.get("rows", 1),
            columns=cards_raw.get("columns", cards_raw.get("cols", 3)),
            card_shape=cards_raw.get("card_shape", "rounded_rectangle"),
            border_style=cards_raw.get("border_style", "thin dark charcoal border"),
            notes=cards_raw.get("notes", "equal-sized containers in neat horizontal row"),
        )

        pills_raw = data.get("feature_callouts", data.get("features", data.get("pills", {})))
        feature_callouts = BlueprintFeatureCalloutSpec(
            layout=pills_raw.get("layout", "2x2_grid"),
            count=pills_raw.get("count", 4),
            shape=pills_raw.get("shape", "rounded_pill"),
            bullet_style=pills_raw.get("bullet_style", "star"),
            placement=pills_raw.get(
                "placement", "directly below flashcards and above bottom rolling wave"
            ),
        )

        wave_raw = data.get("baseline_wave", data.get("wave", {}))
        baseline_wave = BlueprintWaveSpec(
            height_percentage=wave_raw.get("height_percentage", 20),
            style=wave_raw.get("style", "smooth rolling wave in pastel turquoise and mint"),
            spine_continuity=wave_raw.get(
                "spine_continuity", "horizontally flat at spine fold, borderless"
            ),
        )

        return BlueprintLayoutSpec(
            source_path=source_path,
            target_type=data.get("target_type", "back_cover"),
            headline_style=data.get("headline_style", "bold uppercase headline centered at top"),
            description_style=data.get(
                "description_style", "friendly parent description in clean dark navy typography"
            ),
            card_grid=card_grid,
            feature_callouts=feature_callouts,
            baseline_wave=baseline_wave,
            custom_directives=data.get("custom_directives", []),
        )

    def get_layout_spec(self, target_type: str = "back_cover") -> BlueprintLayoutSpec | None:
        """Convenience method: find and read blueprint for target_type, or return None if absent."""
        found = self.find_blueprint(target_type=target_type)
        if not found:
            return None
        try:
            return self.read_blueprint(found)
        except Exception as e:
            logger.warning(f"Failed to read blueprint from {found}: {e}")
            return None
