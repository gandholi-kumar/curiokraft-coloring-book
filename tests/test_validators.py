"""Comprehensive automated unit tests for deterministic validators and rescue engine."""

import numpy as np
import pytest
from pathlib import Path
from PIL import Image, ImageDraw

from curiokraft_book.validators.dimensions import validate_dimensions
from curiokraft_book.validators.margins import validate_margins
from curiokraft_book.validators.grayscale import validate_black_and_white
from curiokraft_book.validators.duplicates import ObjectRegistryValidator
from curiokraft_book.rescue.binarizer import rescue_binarize
from curiokraft_book.rescue.margin_fitter import fit_to_safe_margins


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def perfect_bw_image(temp_dir: Path) -> Path:
    """Create a 2550x3300 px 300 DPI binary image with centered black circle."""
    img_path = temp_dir / "perfect_sample.png"
    img = Image.new("L", (2550, 3300), 255)  # Pure white
    draw = ImageDraw.Draw(img)
    # Draw centered thick circle inside safe margin (min margin 150px)
    draw.ellipse([500, 700, 2050, 2600], outline=0, width=20)
    img.save(img_path, dpi=(300, 300))
    return img_path


@pytest.fixture
def gray_shading_image(temp_dir: Path) -> Path:
    """Create an image containing intentional gray shading."""
    img_path = temp_dir / "gray_shading_sample.png"
    img = Image.new("L", (2550, 3300), 255)
    draw = ImageDraw.Draw(img)
    draw.ellipse([500, 700, 2050, 2600], outline=0, width=20)
    # Draw a 100x100 intentional gray shading cluster (intensity = 128)
    draw.rectangle([1000, 1200, 1150, 1350], fill=128)
    img.save(img_path, dpi=(300, 300))
    return img_path


@pytest.fixture
def margin_breach_image(temp_dir: Path) -> Path:
    """Create an image whose artwork breaches the 0.50in margin."""
    img_path = temp_dir / "margin_breach_sample.png"
    img = Image.new("L", (2550, 3300), 255)
    draw = ImageDraw.Draw(img)
    # Line touches the very edge (x=10 px from left)
    draw.line([10, 100, 2540, 100], fill=0, width=10)
    img.save(img_path, dpi=(300, 300))
    return img_path


# ----------------------------------------------------------------------
# 1. Dimension & DPI Validator Tests
# ----------------------------------------------------------------------

def test_validate_dimensions_success(perfect_bw_image: Path):
    result = validate_dimensions(perfect_bw_image)
    assert result.passed is True
    assert result.actual_width_px == 2550
    assert result.actual_height_px == 3300
    assert result.actual_dpi == (300, 300)
    assert len(result.violations) == 0


def test_validate_dimensions_failure(temp_dir: Path):
    bad_img_path = temp_dir / "bad_dim.png"
    img = Image.new("L", (1000, 1500), 255)
    img.save(bad_img_path, dpi=(72, 72))

    result = validate_dimensions(bad_img_path)
    assert result.passed is False
    assert any("Width mismatch" in v for v in result.violations)
    assert any("Height mismatch" in v for v in result.violations)
    assert any("DPI mismatch" in v for v in result.violations)


# ----------------------------------------------------------------------
# 2. Margin Validator Tests
# ----------------------------------------------------------------------

def test_validate_margins_success(perfect_bw_image: Path):
    result = validate_margins(perfect_bw_image)
    assert result.passed is True
    assert result.kdp_compliant is True
    assert result.project_safe_zone_compliant is True
    assert result.margins.left_margin_in >= 0.50
    assert result.margins.right_margin_in >= 0.50


def test_validate_margins_breach(margin_breach_image: Path):
    result = validate_margins(margin_breach_image)
    assert result.passed is False
    assert len(result.violations) > 0


# ----------------------------------------------------------------------
# 3. Grayscale Validator Tests
# ----------------------------------------------------------------------

def test_validate_grayscale_success(perfect_bw_image: Path):
    result = validate_black_and_white(perfect_bw_image)
    assert result.passed is True
    assert result.is_pure_black_and_white is True
    assert result.has_unauthorized_color is False
    assert result.gray_cluster_count == 0


def test_validate_grayscale_intentional_shading(gray_shading_image: Path):
    result = validate_black_and_white(gray_shading_image)
    assert result.passed is False
    assert result.gray_cluster_count > 0
    assert any("Intentional Gray Shading" in v for v in result.violations)


# ----------------------------------------------------------------------
# 4. Rescue Engine Tests
# ----------------------------------------------------------------------

def test_rescue_binarize(gray_shading_image: Path, temp_dir: Path):
    rescued_path = temp_dir / "rescued.png"
    rescue_res = rescue_binarize(gray_shading_image, rescued_path)
    assert rescue_res.success is True
    assert rescued_path.exists()

    # Now validating the rescued image should pass grayscale test
    val_res = validate_black_and_white(rescued_path)
    assert val_res.passed is True


def test_fit_to_safe_margins(margin_breach_image: Path, temp_dir: Path):
    fitted_path = temp_dir / "fitted.png"
    fit_res = fit_to_safe_margins(margin_breach_image, fitted_path)
    assert fit_res.success is True
    assert fitted_path.exists()

    # Now validating the fitted image should strictly pass margin test
    margin_res = validate_margins(fitted_path)
    assert margin_res.passed is True


# ----------------------------------------------------------------------
# 5. Semantic Object Registry Validator Tests
# ----------------------------------------------------------------------

def test_object_registry_validator():
    manifest_path = Path("manifest/objects.json")
    if not manifest_path.exists():
        pytest.skip("manifest/objects.json not found in workspace")

    val = ObjectRegistryValidator(manifest_path)

    # Authorized page request should pass
    res_auth = val.check_object("banana", requesting_page_id="category_page_005")
    assert res_auth.is_duplicate is False

    # Unauthorized request for registered object should flag duplicate
    res_dup = val.check_object("banana", requesting_page_id="category_page_099")
    assert res_dup.is_duplicate is True
    assert res_dup.match_type == "EXACT_CANONICAL"

    # Synonym match check
    res_syn = val.check_object("puppy")
    assert res_syn.is_duplicate is True
    assert res_syn.match_type == "SYNONYM"

    # Compound variant check
    res_comp = val.check_object("watermelon slice")
    assert res_comp.is_duplicate is True
    assert res_comp.match_type == "COMPOUND_VARIANT"

    # Truly unique object
    res_uniq = val.check_object("unobtainium crystal")
    assert res_uniq.is_duplicate is False
