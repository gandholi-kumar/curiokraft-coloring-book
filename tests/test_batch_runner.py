"""Unit tests for InteriorBatchRunner and Whole-Book QA Auditor."""

import json
import pytest
from pathlib import Path

from curiokraft_book.orchestrator.batch_runner import InteriorBatchRunner
from curiokraft_book.agents.book_qa import run_book_qa_audit


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
            {"page_id": "P001", "page_number": 1, "section": "Alphabet", "canonical_object": "alphabet_a_m", "display_label": "A - M FIRST WORDS"},
            {"page_id": "P002", "page_number": 2, "section": "Alphabet", "canonical_object": "alphabet_n_z", "display_label": "N - Z FIRST WORDS"},
            {"page_id": "P005", "page_number": 3, "section": "Fruits", "canonical_object": "banana", "display_label": "BANANA"},
            {"page_id": "P047", "page_number": 4, "section": "Animals", "canonical_object": "dog", "display_label": "DOG"}
        ]
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
        raw_generated_dir=raw_dir
    )

    page_data = {"page_id": "P005", "page_number": 3, "canonical_object": "banana", "display_label": "BANANA", "section": "Fruits"}
    master_path = runner.generate_single_page(page_data)

    assert master_path.exists()
    assert master_path.name == "page_003.png"


def test_batch_runner_mini_batch(sample_mini_manifest: Path, temp_dir: Path):
    masters_dir = temp_dir / "masters"
    raw_dir = temp_dir / "raw"

    runner = InteriorBatchRunner(
        manifest_path=sample_mini_manifest,
        output_masters_dir=masters_dir,
        raw_generated_dir=raw_dir
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
        raw_generated_dir=raw_dir
    )
    runner.run_full_book_batch()

    # Now audit
    qa_res = run_book_qa_audit(
        masters_dir=masters_dir,
        manifest_path=sample_mini_manifest,
        objects_registry_path="manifest/objects.json",
        report_output_path=qa_report_path
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


def test_prompt_taxonomy_and_export_compliance():
    from curiokraft_book.orchestrator.debate_engine import DebateEngine, classify_living_taxonomy

    manifest_p = Path("manifest/pages.json")
    with open(manifest_p, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    engine = DebateEngine()
    pages = manifest.get("pages", [])
    assert len(pages) == 110

    inanimate_count = 0
    living_count = 0
    spread_count = 0

    for p in pages:
        pid = p["page_id"]
        sec = p.get("section", "")
        canon = p.get("canonical_object", "")
        page_type = p.get("type", "single_page")
        is_spread = (page_type in ["educational_spread", "counting_spread"]) or (p.get("composition") == "flashcard_grid")
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
