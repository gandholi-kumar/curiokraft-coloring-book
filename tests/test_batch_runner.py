"""Unit tests for InteriorBatchRunner and Whole-Book QA Auditor."""

import json
from pathlib import Path

import pytest

from curiokraft_book.agents.book_qa import run_book_qa_audit
from curiokraft_book.orchestrator.batch_runner import InteriorBatchRunner


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def sample_mini_manifest(temp_dir: Path) -> Path:
    manifest_p = temp_dir / "mini_manifest.json"
    data = {
        "manifest_version": "1.0",
        "book_title": "TEST MINI BOOK",
        "total_pages": 4,
        "pages": [
            {
                "page_id": "P001",
                "page_number": 1,
                "section": "Alphabet",
                "canonical_object": "alphabet_a_m",
                "display_label": "A - M FIRST WORDS",
            },
            {
                "page_id": "P002",
                "page_number": 2,
                "section": "Alphabet",
                "canonical_object": "alphabet_n_z",
                "display_label": "N - Z FIRST WORDS",
            },
            {
                "page_id": "P005",
                "page_number": 3,
                "section": "Fruits",
                "canonical_object": "banana",
                "display_label": "BANANA",
            },
            {
                "page_id": "P047",
                "page_number": 4,
                "section": "Animals",
                "canonical_object": "dog",
                "display_label": "DOG",
            },
        ],
    }
    with open(manifest_p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return manifest_p


def test_batch_runner_single_page(sample_mini_manifest: Path, temp_dir: Path):
    masters_dir = temp_dir / "masters"
    raw_dir = temp_dir / "raw"

    runner = InteriorBatchRunner(
        manifest_path=sample_mini_manifest,
        output_masters_dir=masters_dir,
        raw_generated_dir=raw_dir,
    )

    page_data = {
        "page_id": "P005",
        "page_number": 3,
        "canonical_object": "banana",
        "display_label": "BANANA",
        "section": "Fruits",
    }
    master_path = runner.generate_single_page(page_data)

    assert master_path.exists()
    assert master_path.name == "page_003.png"


def test_batch_runner_mini_batch(sample_mini_manifest: Path, temp_dir: Path):
    masters_dir = temp_dir / "masters"
    raw_dir = temp_dir / "raw"

    runner = InteriorBatchRunner(
        manifest_path=sample_mini_manifest,
        output_masters_dir=masters_dir,
        raw_generated_dir=raw_dir,
    )

    report = runner.run_full_book_batch()
    assert report.total_pages == 4
    assert report.successful_pages == 4
    assert report.failed_pages == 0


def test_book_qa_audit(sample_mini_manifest: Path, temp_dir: Path):
    masters_dir = temp_dir / "masters"
    raw_dir = temp_dir / "raw"
    qa_report_path = temp_dir / "qa_report.json"

    # First generate mini batch
    runner = InteriorBatchRunner(
        manifest_path=sample_mini_manifest,
        output_masters_dir=masters_dir,
        raw_generated_dir=raw_dir,
    )
    runner.run_full_book_batch()

    # Now audit
    qa_res = run_book_qa_audit(
        masters_dir=masters_dir,
        manifest_path=sample_mini_manifest,
        objects_registry_path="manifest/objects.json",
        report_output_path=qa_report_path,
    )

    assert qa_res.audit_verdict == "PASSED"
    assert qa_res.passed_pages_count == 4
    assert qa_res.duplicate_objects_found == 0
    assert qa_report_path.exists()


def test_mock_image_provider():
    from curiokraft_book.orchestrator.model_client import MockImageProvider

    provider = MockImageProvider()
    img = provider.generate("cute banana", canonical_label="banana", section="Fruits")
    assert img.size == (2550, 3300)
    assert img.mode == "L"


def test_inbox_image_provider(temp_dir: Path):
    from PIL import Image, ImageDraw

    from curiokraft_book.orchestrator.model_client import DiskInboxProvider

    inbox = temp_dir / "test_inbox"
    inbox.mkdir(parents=True, exist_ok=True)

    # Place a test image in inbox
    test_img = Image.new("L", (1000, 1000), 255)
    draw = ImageDraw.Draw(test_img)
    draw.rectangle([200, 200, 800, 800], outline=0, width=10)
    test_img.save(inbox / "raw_p005_banana.png")

    prov = DiskInboxProvider(inbox_dir=inbox)
    found_p = prov.find_image(page_number=5, canonical_label="banana")
    assert found_p is not None
    assert found_p.name == "raw_p005_banana.png"

    loaded_img = prov.generate("banana", canonical_label="banana", page_number=5)
    assert loaded_img is not None
    assert loaded_img.size == (1000, 1000)

    # Test double extension support (.png.jpg)
    double_ext_file = inbox / "raw_p022_pizza.png.jpg"
    test_img.save(double_ext_file)
    found_double = prov.find_image(page_number=22, canonical_label="pizza")
    assert found_double is not None
    assert found_double.name == "raw_p022_pizza.png.jpg"

    # Test case-insensitive and prefix matching (P033.PNG)
    upper_file = inbox / "P033.PNG"
    test_img.save(upper_file)
    found_upper = prov.find_image(page_id="P033", page_number=33, canonical_label="cup")
    assert found_upper is not None
    assert found_upper.name == "P033.PNG"


def test_spread_formatting_bypasses_typography(temp_dir: Path):
    from curiokraft_book.orchestrator.batch_runner import InteriorBatchRunner
    from curiokraft_book.validators.margins import validate_margins

    runner = InteriorBatchRunner()
    runner.output_masters_dir = temp_dir / "masters"
    runner.output_masters_dir.mkdir(parents=True, exist_ok=True)
    runner.raw_generated_dir = temp_dir / "raw"
    runner.raw_generated_dir.mkdir(parents=True, exist_ok=True)

    spread_page_data = {
        "page_id": "P002",
        "page_number": 2,
        "section": "A-Z Alphabet",
        "canonical_object": "alphabet_a_to_m",
        "display_label": "A - M FIRST WORDS",
        "type": "educational_spread",
        "composition": "flashcard_grid",
        "cards": [],
    }

    master_p = runner.generate_single_page(spread_page_data, source_mode="mock", force_fresh=True)
    assert master_p.exists()

    m_res = validate_margins(master_p)
    assert m_res.passed
    assert m_res.margins.left_margin_in >= 0.50
    assert m_res.margins.right_margin_in >= 0.50
    assert m_res.margins.top_margin_in >= 0.50
    assert m_res.margins.bottom_margin_in >= 0.50


def test_prompt_taxonomy_and_export_compliance():
    from curiokraft_book.orchestrator.debate_engine import DebateEngine, classify_living_taxonomy

    manifest_p = Path("manifest/pages.json")
    with open(manifest_p, encoding="utf-8") as f:
        manifest = json.load(f)

    engine = DebateEngine()
    pages = manifest.get("pages", [])
    assert len(pages) == 110

    inanimate_count = 0
    living_count = 0
    spread_count = 0

    for p in pages:
        sec = p.get("section", "")
        canon = p.get("canonical_object", "")
        page_type = p.get("type", "single_page")
        is_spread = (page_type in ["educational_spread", "counting_spread"]) or (
            p.get("composition") == "flashcard_grid"
        )
        res = engine.run_page_debate(p)
        pos = res.positive_prompt
        neg = res.negative_prompt

        # 1. Orientation Checks across all 110 pages
        assert "vertical portrait 3:4" in pos.lower()
        assert "16:9" in neg.lower()
        assert "widescreen" in neg.lower()

        # 2. Taxonomy & Text Checks
        is_living = classify_living_taxonomy(canon, sec)
        if is_spread:
            spread_count += 1
            assert "educational" in pos.lower()
            assert "empty boxes" in neg.lower()
        elif is_living:
            living_count += 1
            assert "cute friendly" in pos.lower()
            assert "round eyes" in pos.lower()
            assert "no text" in pos.lower()
            assert "text" in neg.lower()
        else:
            inanimate_count += 1
            assert "pure inanimate object" in pos.lower()
            assert "strictly no eyes" in pos.lower()
            assert "no mouth" in pos.lower()
            assert "no face" in pos.lower()
            assert "no text" in pos.lower()
            assert "face" in neg.lower()
            assert "eyes" in neg.lower()
            assert "text" in neg.lower()

    assert spread_count == 4
    assert living_count == 20  # Animals + Teddy Bear + Doll
    assert inanimate_count == 86  # Inanimate objects (Fruits, Veg, Food, Vehicles, Household, etc.)
    assert spread_count + living_count + inanimate_count == len(pages)


def test_vehicle_design_profile_resolution():
    from curiokraft_book.orchestrator.debate_engine import resolve_vehicle_design_profile

    # 1. Rocket (Spacecraft)
    rocket = resolve_vehicle_design_profile("rocket")
    assert rocket["class"] == "spacecraft"
    assert rocket["has_wheels"] is False
    assert "stabilizing fins" in rocket["anatomy"].lower()
    assert "strictly no wheels" in rocket["support"].lower()
    assert "wheels" in rocket["negative_tokens"]
    assert "tires" in rocket["negative_tokens"]

    # 2. Helicopter (Rotorcraft)
    heli = resolve_vehicle_design_profile("helicopter")
    assert heli["class"] == "rotorcraft"
    assert heli["has_wheels"] is False
    assert "main rotor" in heli["anatomy"].lower()
    assert "landing skids" in heli["support"].lower()
    assert "strictly no wheels" in heli["support"].lower()
    assert "wheels" in heli["negative_tokens"]
    assert "airplane wings" in heli["negative_tokens"]

    # 3. Sailboat (Watercraft)
    boat = resolve_vehicle_design_profile("sailboat")
    assert boat["class"] == "watercraft"
    assert boat["has_wheels"] is False
    assert "boat hull" in boat["anatomy"].lower()
    assert "strictly no wheels" in boat["support"].lower()
    assert "wheels" in boat["negative_tokens"]

    # 4. Bicycle (Wheeled Two-Wheel)
    bike = resolve_vehicle_design_profile("bicycle")
    assert bike["class"] == "wheeled_two_wheel"
    assert bike["has_wheels"] is True
    assert "two clearly separated circular wheels" in bike["anatomy"].lower()
    assert "four wheels" in bike["negative_tokens"]

    # 5. Car (Wheeled Four-Wheel)
    car = resolve_vehicle_design_profile("car")
    assert car["class"] == "wheeled_four_wheel"
    assert car["has_wheels"] is True
    assert "large chunky round wheels" in car["anatomy"].lower()


def test_vehicle_prompts_export_compliance():
    import json

    from typer.testing import CliRunner

    from curiokraft_book.cli import app

    export_path = Path("generated/prompts_export.json")
    if not export_path.exists():
        runner = CliRunner()
        runner.invoke(app, ["prompt", "export", "--format", "json"])

    assert export_path.exists()
    data = json.loads(export_path.read_text(encoding="utf-8"))
    prompts_list = data.get("prompts", data)

    # Check if Vol 1 or Vol 2 manifest is active in export
    items_by_label = {item.get("label", "").upper(): item for item in prompts_list}

    if "HELICOPTER" in items_by_label:
        heli = items_by_label["HELICOPTER"]
        pos_heli = heli["positive_prompt"].lower()
        neg_heli = heli["negative_prompt"].lower()
        assert "landing skids" in pos_heli
        assert "strictly no wheels" in pos_heli
        assert "chunky round wheels" not in pos_heli
        assert "wheels" in neg_heli
        assert "airplane wings" in neg_heli

    if "SAILBOAT" in items_by_label:
        boat = items_by_label["SAILBOAT"]
        pos_boat = boat["positive_prompt"].lower()
        neg_boat = boat["negative_prompt"].lower()
        assert "boat hull" in pos_boat
        assert "strictly no wheels" in pos_boat
        assert "chunky round wheels" not in pos_boat
        assert "wheels" in neg_boat

    if "ROCKET" in items_by_label:
        rocket = items_by_label["ROCKET"]
        pos_rocket = rocket["positive_prompt"].lower()
        neg_rocket = rocket["negative_prompt"].lower()
        assert "stabilizing fins" in pos_rocket
        assert "strictly no wheels" in pos_rocket
        assert "chunky round wheels" not in pos_rocket
        assert "wheels" in neg_rocket

    if "CANOE" in items_by_label:
        canoe = items_by_label["CANOE"]
        pos_canoe = canoe["positive_prompt"].lower()
        neg_canoe = canoe["negative_prompt"].lower()
        assert "canoe" in pos_canoe
        assert "wheels" in neg_canoe

    if "SUBMARINE" in items_by_label:
        sub = items_by_label["SUBMARINE"]
        pos_sub = sub["positive_prompt"].lower()
        neg_sub = sub["negative_prompt"].lower()
        assert "submarine" in pos_sub
        assert "wheels" in neg_sub

    if "COMB" in items_by_label:
        comb = items_by_label["COMB"]
        pos_comb = comb["positive_prompt"].lower()
        assert "sturdy legs" not in pos_comb


def test_welcome_page_preserves_raw_and_mascot(temp_dir: Path):
    """Verify that when a user drops an illustration for welcome_page, it is preserved in raw_dir and composited."""
    from PIL import Image

    masters_dir = temp_dir / "masters"
    raw_dir = temp_dir / "raw"
    inbox_dir = temp_dir / "inbox"
    masters_dir.mkdir(parents=True)
    raw_dir.mkdir(parents=True)
    inbox_dir.mkdir(parents=True)

    # Place mock user illustration in inbox
    user_img = Image.new("L", (800, 600), 255)
    inbox_file = inbox_dir / "raw_p001_welcome_belongs_to.png"
    user_img.save(inbox_file)

    manifest_p = temp_dir / "mini_manifest.json"
    manifest_data = {
        "manifest_version": "1.0",
        "book_title": "TEST MINI BOOK",
        "total_pages": 1,
        "pages": [
            {
                "page_id": "P001",
                "page_number": 1,
                "section": "Front Matter",
                "canonical_object": "welcome_belongs_to",
                "display_label": "THIS BOOK BELONGS TO",
                "type": "welcome_page",
            }
        ],
    }
    manifest_p.write_text(json.dumps(manifest_data), encoding="utf-8")

    runner = InteriorBatchRunner(
        manifest_path=manifest_p, output_masters_dir=masters_dir, raw_generated_dir=raw_dir
    )
    # Point runner's inbox provider to test inbox
    runner.inbox_provider.inbox_dir = inbox_dir

    page_data = manifest_data["pages"][0]
    out_master = runner.generate_single_page(page_data, source_mode="inbox")

    assert out_master.exists()
    assert out_master.name == "page_001.png"
    # Verify canonical raw page is preserved in raw_dir
    expected_raw = raw_dir / "raw_p001_welcome_belongs_to.png"
    assert expected_raw.exists()
    assert expected_raw.stat().st_size > 500
