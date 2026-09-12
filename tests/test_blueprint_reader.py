"""Unit tests for Layout Blueprint Ingestion Engine."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from curiokraft_book.orchestrator.blueprint_reader import (
    BlueprintCardGridSpec,
    BlueprintFeatureCalloutSpec,
    BlueprintLayoutSpec,
    BlueprintWaveSpec,
    LayoutBlueprintReader,
)
from curiokraft_book.orchestrator.model_client import ModelResponse


def test_blueprint_models_defaults_and_composition():
    """Verify default values and prompt composition string formatting."""
    grid = BlueprintCardGridSpec(rows=2, columns=4)
    assert grid.rows == 2
    assert grid.columns == 4

    pills = BlueprintFeatureCalloutSpec(count=6, layout="pill_banner")
    assert pills.count == 6

    wave = BlueprintWaveSpec(height_percentage=18)
    assert wave.height_percentage == 18

    spec = BlueprintLayoutSpec(
        source_path="mock_path.yaml",
        card_grid=grid,
        feature_callouts=pills,
        baseline_wave=wave,
    )
    assert spec.target_type == "back_cover"
    assert spec.card_grid.columns == 4
    assert spec.card_grid.rows == 2
    assert spec.feature_callouts.count == 6
    assert spec.baseline_wave.height_percentage == 18

    comp = spec.to_prompt_composition()
    assert "8 clean, upright white rounded flashcard preview boxes" in comp
    assert "features 6 neat, colorful pastel rounded feature note pills" in comp
    assert "lower 18% of the canvas" in comp


def test_find_blueprint_yaml(tmp_path: Path):
    """Verify discovery of layout blueprint YAML files."""
    bp_dir = tmp_path / "blueprints"
    bp_dir.mkdir()
    inbox_dir = tmp_path / "inbox"
    inbox_dir.mkdir()

    # Create dummy cover blueprint
    yaml_file = bp_dir / "cover_blueprint.yaml"
    yaml_file.write_text("target_type: cover\n", encoding="utf-8")

    reader = LayoutBlueprintReader(blueprints_dir=bp_dir, inbox_dir=inbox_dir)
    found = reader.find_blueprint(target_type="cover")
    assert found == yaml_file

    # Search for something that does not exist
    not_found = reader.find_blueprint(target_type="interior_spread")
    assert not_found is None


def test_find_blueprint_inbox_fallback(tmp_path: Path):
    """Verify discovery when blueprint is placed in inbox fallback directory."""
    bp_dir = tmp_path / "empty_bp"
    inbox_dir = tmp_path / "inbox"
    inbox_dir.mkdir()

    img_file = inbox_dir / "back_cover_wireframe.png"
    img_file.write_bytes(b"fake image bytes")

    reader = LayoutBlueprintReader(blueprints_dir=bp_dir, inbox_dir=inbox_dir)
    found = reader.find_blueprint(target_type="back_cover")
    assert found == img_file


def test_read_blueprint_yaml(tmp_path: Path):
    """Verify parsing of valid structured YAML layout blueprint."""
    yaml_data = {
        "target_type": "back_cover",
        "headline_style": "custom bold headline",
        "description_style": "custom parent description",
        "card_grid": {
            "rows": 2,
            "columns": 3,
            "card_shape": "hexagon",
            "border_style": "thick border",
            "notes": "two rows of cards",
        },
        "feature_callouts": {
            "layout": "1x4_row",
            "count": 4,
            "shape": "circle",
            "bullet_style": "check",
            "placement": "under cards",
        },
        "baseline_wave": {
            "height_percentage": 25,
            "style": "gentle pastel waves",
            "spine_continuity": "seamless wrap",
        },
        "custom_directives": ["keep colors vivid"],
    }
    file_path = tmp_path / "custom_blueprint.yaml"
    file_path.write_text(yaml.dump(yaml_data), encoding="utf-8")

    reader = LayoutBlueprintReader()
    spec = reader.read_blueprint(file_path)

    assert spec.target_type == "back_cover"
    assert spec.headline_style == "custom bold headline"
    assert spec.card_grid.rows == 2
    assert spec.card_grid.card_shape == "hexagon"
    assert spec.feature_callouts.layout == "1x4_row"
    assert spec.baseline_wave.height_percentage == 25
    assert "keep colors vivid" in spec.custom_directives


def test_read_blueprint_json(tmp_path: Path):
    """Verify parsing of valid JSON layout blueprint."""
    json_data = {
        "target_type": "front_cover",
        "cards": {"rows": 1, "cols": 4},
        "pills": {"layout": "pill_banner", "count": 2},
        "wave": {"height_percentage": 15},
    }
    file_path = tmp_path / "front_cover.json"
    file_path.write_text(json.dumps(json_data), encoding="utf-8")

    reader = LayoutBlueprintReader()
    spec = reader.read_blueprint(file_path)

    assert spec.target_type == "front_cover"
    assert spec.card_grid.columns == 4
    assert spec.feature_callouts.count == 2
    assert spec.baseline_wave.height_percentage == 15


def test_read_blueprint_image_vision(tmp_path: Path):
    """Verify multimodal vision parsing of blueprint image."""
    img_path = tmp_path / "back_cover_blueprint.png"
    img_path.write_bytes(b"\x89PNG\r\n\x1a\nfake")

    mock_client = MagicMock()
    mock_client.call_vision.return_value = ModelResponse(
        content='{"target_type": "back_cover"}',
        parsed_json={
            "target_type": "back_cover",
            "card_grid": {"rows": 1, "columns": 3},
            "feature_callouts": {"layout": "2x2_grid", "count": 4},
            "baseline_wave": {"height_percentage": 22},
        },
        model_name="mock-vision-model",
    )

    reader = LayoutBlueprintReader(model_client=mock_client)
    spec = reader.read_blueprint(img_path)

    assert spec.target_type == "back_cover"
    assert spec.card_grid.columns == 3
    assert spec.baseline_wave.height_percentage == 22
    mock_client.call_vision.assert_called_once()


def test_read_blueprint_errors(tmp_path: Path):
    """Verify error handling for missing files and unsupported formats."""
    reader = LayoutBlueprintReader()

    # Missing file
    with pytest.raises(FileNotFoundError):
        reader.read_blueprint(tmp_path / "non_existent.yaml")

    # Unsupported format
    txt_file = tmp_path / "blueprint.txt"
    txt_file.write_text("unsupported format", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported blueprint format"):
        reader.read_blueprint(txt_file)


def test_get_layout_spec_convenience(tmp_path: Path):
    """Verify get_layout_spec finds and reads blueprint or handles failures."""
    bp_dir = tmp_path / "blueprints"
    bp_dir.mkdir()
    yaml_file = bp_dir / "back_cover_blueprint.yaml"
    yaml_file.write_text("target_type: back_cover\n", encoding="utf-8")

    reader = LayoutBlueprintReader(blueprints_dir=bp_dir, inbox_dir=tmp_path / "inbox")

    # 1. Successfully found & parsed
    spec = reader.get_layout_spec(target_type="back_cover")
    assert spec is not None
    assert spec.target_type == "back_cover"

    # 2. Not found
    missing = reader.get_layout_spec(target_type="front_cover")
    assert missing is None

    # 3. Corrupted file error recovery
    corrupt_file = bp_dir / "front_cover_blueprint.yaml"
    corrupt_file.write_text(":\t\aINVALID YAML--__", encoding="utf-8")
    corrupt_res = reader.get_layout_spec(target_type="front_cover")
    assert corrupt_res is None
