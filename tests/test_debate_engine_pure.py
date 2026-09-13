"""Unit tests for the pure/pure-ish helpers in ``orchestrator/debate_engine.py``.

These target the module-level functions that do not require a live LLM: taxonomy
classification, anatomy/vehicle profile resolution, spread-grid maths, cover-card
extraction and mascot auto-picking. They add coverage without touching the
network (and are safe under the conftest tripwire).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from curiokraft_book.constants import DEFAULT_PAGES_MANIFEST
from curiokraft_book.orchestrator.debate_engine import (
    _build_alphabet_spread_prompt,
    _detect_spread_layout_key,
    _filter_contradictions,
    _find_config_file,
    _get_crayon_color_for_object,
    _join_negative,
    _load_json,
    _load_yaml,
    audit_spread_card_miscount_risks,
    auto_pick_volume_mascot,
    calculate_optimal_counting_grid,
    classify_living_taxonomy,
    extract_cover_showcase_cards,
    extract_front_cover_ensemble,
    generate_dynamic_spread_prompt,
    generate_dynamic_visual_spec,
    get_custom_alphabet_spread_prompt,
    is_vehicle_object,
    resolve_animal_anatomy_profile,
)

# ----------------------------------------------------------------------
# Config loaders
# ----------------------------------------------------------------------


def test_load_json_missing_file_returns_empty_dict(tmp_path: Path):
    assert _load_json(str(tmp_path / "nope.json")) == {}


def test_load_yaml_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        _load_yaml(str(tmp_path / "nope.yaml"))


def test_find_config_file_present_and_absent(tmp_path: Path):
    target = tmp_path / "thing.yaml"
    target.write_text("key: value\n", encoding="utf-8")
    assert _find_config_file(str(target)) == target
    assert _find_config_file(str(tmp_path / "absent.yaml")) is None


# ----------------------------------------------------------------------
# Taxonomy classification
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "canonical,section,expected",
    [
        ("dog", "Animals", True),
        ("teddy_bear", "Toys", True),
        ("apple", "Fruits & Vegetables", False),
        ("banana", "Fruits", False),
    ],
)
def test_classify_living_taxonomy(canonical: str, section: str, expected: bool):
    assert classify_living_taxonomy(canonical, section) is expected


# ----------------------------------------------------------------------
# Anatomy / vehicle profiles
# ----------------------------------------------------------------------


def test_resolve_animal_anatomy_profile_returns_all_keys():
    prof = resolve_animal_anatomy_profile("dog")
    assert set(prof) == {
        "class",
        "anatomy",
        "posture",
        "orientation",
        "safeguards",
        "negative_tokens",
    }
    assert prof["class"] == "quadrupeds"
    assert isinstance(prof["negative_tokens"], list)


def test_resolve_animal_anatomy_profile_unknown_falls_back():
    prof = resolve_animal_anatomy_profile("zzz_unknown_creature")
    assert prof["class"] == "quadrupeds"
    assert "zzz unknown creature" in prof["anatomy"]


@pytest.mark.parametrize(
    "canonical,section,expected",
    [
        ("rocket", "Vehicles", True),
        ("sailboat", "Sea", True),
        ("apple", "Fruits", False),
        ("dog", "Animals", False),
        ("fire_truck", "Transportation", True),
    ],
)
def test_is_vehicle_object(canonical: str, section: str, expected: bool):
    assert is_vehicle_object(canonical, section) is expected


def test_generate_dynamic_visual_spec_living():
    spec = generate_dynamic_visual_spec("dog", "Animals", True)
    assert spec.startswith("a cute friendly baby dog")


def test_generate_dynamic_visual_spec_vehicle():
    spec = generate_dynamic_visual_spec("rocket", "Vehicles", False)
    assert "rocket" in spec


def test_generate_dynamic_visual_spec_fallback():
    spec = generate_dynamic_visual_spec("apple", "Fruits", False)
    assert "apple" in spec


# ----------------------------------------------------------------------
# Negative-token helpers
# ----------------------------------------------------------------------


def test_join_negative_flattens_and_dedupes():
    result = _join_negative([["a", "b"], ["b", "c"], [], [" a "]])
    assert result == "a, b, c"


def test_join_negative_empty():
    assert _join_negative([]) == ""


def test_filter_contradictions_removes_biped_tokens():
    filtered = _filter_contradictions("a figure standing on two legs", ["two legs", "extra"])
    assert "two legs" not in filtered
    assert "extra" in filtered


def test_filter_contradictions_removes_quadruped_tokens():
    filtered = _filter_contradictions("a dog on four legs", ["four legs", "horns"])
    assert "four legs" not in filtered
    assert "horns" in filtered


def test_filter_contradictions_removes_wheel_tokens_when_wheels_required():
    filtered = _filter_contradictions("a car with chunky wheels", ["wheels", "tires", "wings"])
    assert "wheels" not in filtered
    assert "tires" not in filtered
    assert "wings" in filtered


def test_filter_contradictions_keeps_empty_out():
    assert _filter_contradictions("plain", ["", "   ", "keep"]) == ["keep"]


# ----------------------------------------------------------------------
# Spread layout detection & grid maths
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "canonical,label,expected",
    [
        ("alphabet_a_to_m", "A - M", "alphabet_a_m"),
        ("alphabet_n_to_z", "N - Z", "alphabet_n_z"),
        ("numbers_0_to_5", "0 - 5", "numbers_0_5"),
        ("something_else", "Numbers", "numbers_6_10"),
    ],
)
def test_detect_spread_layout_key(canonical: str, label: str, expected: str):
    assert _detect_spread_layout_key(canonical, label) == expected


@pytest.mark.parametrize(
    "count,is_full_width,expected",
    [
        (0, False, (1, 1, [0])),
        (1, False, (1, 1, [1])),
        (6, False, (2, 3, [3, 3])),
        (5, True, (1, 5, [5])),
    ],
)
def test_calculate_optimal_counting_grid(count, is_full_width, expected):
    assert calculate_optimal_counting_grid(count, is_full_width) == expected


def test_calculate_optimal_counting_grid_prime_count():
    rows, cols, row_counts = calculate_optimal_counting_grid(7)
    assert rows == 7
    assert cols == 1
    assert sum(row_counts) == 7


def test_audit_spread_card_miscount_risks_zero_count():
    findings, hardening = audit_spread_card_miscount_risks("0", 0, "apple", 1, 1, [0])
    assert any("Zero objects" in f for f in findings)
    assert hardening == ["items on card 0", "objects on card 0"]


def test_audit_spread_card_miscount_risks_grid():
    findings, hardening = audit_spread_card_miscount_risks("6", 6, "apple", 2, 3, [3, 3])
    assert any("2x3 grid" in f for f in findings)
    assert "5 apples" in hardening
    assert "7 apples" in hardening
    assert "wrong count of apples" in hardening


def test_audit_spread_card_miscount_risks_single_row():
    findings, hardening = audit_spread_card_miscount_risks("1", 1, "ball", 1, 1, [1])
    assert any("exactly 1 ball" in f for f in findings)


# ----------------------------------------------------------------------
# Crayon colours
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "obj,expected",
    [
        ("apple", "red"),
        ("banana", "yellow"),
        ("car", "blue"),
        ("guitar", "orange"),
        ("frog", "green"),
        ("grape", "purple"),
        ("zzz_unknown", "bright colorful"),
    ],
)
def test_get_crayon_color_for_object(obj: str, expected: str):
    assert _get_crayon_color_for_object(obj) == expected


def test_get_crayon_color_carrot_matches_blue_because_of_substring():
    """Pin the quirk: 'carrot' hits the car/boat/... blue branch first."""
    assert _get_crayon_color_for_object("carrot") == "blue"


# ----------------------------------------------------------------------
# Manifest-driven extractors
# ----------------------------------------------------------------------


def _write_manifest(tmp_path: Path, pages: list[dict]) -> Path:
    p = tmp_path / "pages.json"
    p.write_text(json.dumps({"pages": pages}), encoding="utf-8")
    return p


def test_extract_cover_showcase_cards_from_manifest(tmp_path: Path):
    manifest = _write_manifest(
        tmp_path,
        [
            {"page_id": "P001", "page_number": 1, "canonical_object": "welcome"},
            {
                "page_id": "P005",
                "page_number": 5,
                "canonical_object": "apple",
                "display_label": "APPLE",
                "section": "Fruits",
                "type": "coloring_page",
            },
            {
                "page_id": "P047",
                "page_number": 47,
                "canonical_object": "dog",
                "display_label": "DOG",
                "section": "Animals",
                "type": "coloring_page",
            },
            {
                "page_id": "P060",
                "page_number": 60,
                "canonical_object": "car",
                "display_label": "CAR",
                "section": "Vehicles",
                "type": "coloring_page",
            },
        ],
    )
    cards = extract_cover_showcase_cards(str(manifest), count=3)
    assert len(cards) == 3
    assert all(set(c) == {"slot", "title", "category_name", "description"} for c in cards)
    assert cards[0]["slot"] == "1"


def test_extract_cover_showcase_cards_missing_manifest(tmp_path: Path):
    cards = extract_cover_showcase_cards(str(tmp_path / "absent.json"), count=3)
    assert cards == []


def test_extract_front_cover_ensemble(tmp_path: Path):
    manifest = _write_manifest(
        tmp_path,
        [
            {
                "page_id": "P010",
                "page_number": 10,
                "canonical_object": "elephant",
                "display_label": "ELEPHANT",
                "section": "Animals",
            },
            {
                "page_id": "P020",
                "page_number": 20,
                "canonical_object": "apple",
                "display_label": "APPLE",
                "section": "Fruits",
            },
        ],
    )
    hero, companions, page_count = extract_front_cover_ensemble(str(manifest))
    assert "elephant" in hero.lower()
    assert page_count == 2
    assert companions  # at least the rainbow is always appended
    assert any("rainbow" in c for c in companions)


def test_auto_pick_volume_mascot_from_config(tmp_path: Path):
    cfg = tmp_path / "book.yaml"
    cfg.write_text("book:\n  mascot:\n    name: Panda\n", encoding="utf-8")
    assert auto_pick_volume_mascot(str(tmp_path / "absent.json"), str(cfg)) == "panda"


def test_auto_pick_volume_mascot_from_manifest(tmp_path: Path):
    cfg = tmp_path / "no_mascot.yaml"
    cfg.write_text("book:\n  title: Test\n", encoding="utf-8")
    manifest = _write_manifest(
        tmp_path,
        [
            {
                "page_id": "P030",
                "page_number": 30,
                "canonical_object": "panda",
                "section": "Animals",
            }
        ],
    )
    assert auto_pick_volume_mascot(str(manifest), str(cfg)) == "panda"


def test_auto_pick_volume_mascot_ultimate_fallback(tmp_path: Path):
    cfg = tmp_path / "no_mascot.yaml"
    cfg.write_text("book:\n  title: Test\n", encoding="utf-8")
    manifest = _write_manifest(
        tmp_path,
        [
            {
                "page_id": "P040",
                "page_number": 40,
                "canonical_object": "spoon",
                "section": "Household",
            }
        ],
    )
    assert auto_pick_volume_mascot(str(manifest), str(cfg)) == "panda"


# ----------------------------------------------------------------------
# Alphabet spread prompt building
# ----------------------------------------------------------------------


def _thirteen_cards() -> list[dict]:
    return [
        {
            "letter": chr(ord("A") + i),
            "word": f"WORD{i}",
            "illustration": f"Word {i} outline",
        }
        for i in range(13)
    ]


def test_build_alphabet_spread_prompt_with_explicit_cards():
    prompt = _build_alphabet_spread_prompt("a_to_m", page_record={"cards": _thirteen_cards()})
    assert prompt is not None
    assert "WORD0" in prompt
    assert "{{WORD_1}}" not in prompt


def test_build_alphabet_spread_prompt_unknown_section_returns_none():
    assert _build_alphabet_spread_prompt("zzz", page_record={"cards": _thirteen_cards()}) is None


def test_build_alphabet_spread_prompt_uses_object_when_word_missing():
    cards = [{"letter": chr(ord("A") + i), "object": f"thing_{i}"} for i in range(13)]
    prompt = _build_alphabet_spread_prompt("a_to_m", page_record={"cards": cards})
    assert prompt is not None
    assert "THING 0" in prompt


def test_build_alphabet_spread_prompt_with_bonus_tiles():
    cards = _thirteen_cards()
    prompt = _build_alphabet_spread_prompt(
        "a_to_m",
        page_record={"cards": cards, "bonus_tiles": ["BONUS A", "BONUS B"]},
    )
    assert prompt is not None
    assert "BONUS A" in prompt
    assert "BONUS B" in prompt


def test_get_custom_alphabet_spread_prompt_returns_pair_for_page_two():
    result = get_custom_alphabet_spread_prompt(
        {"canonical_object": "alphabet_a_to_m", "page_number": 2}
    )
    assert result is not None
    pos, neg = result
    assert "no gray shading" in neg
    assert pos


def test_get_custom_alphabet_spread_prompt_n_to_z_by_page_number():
    result = get_custom_alphabet_spread_prompt(
        {"canonical_object": "something_else", "page_number": 3}
    )
    assert result is not None


def test_get_custom_alphabet_spread_prompt_unrelated_returns_none():
    assert (
        get_custom_alphabet_spread_prompt({"canonical_object": "banana", "page_number": 5}) is None
    )


# ----------------------------------------------------------------------
# Dynamic spread prompt (uses the real manifest + curriculum)
# ----------------------------------------------------------------------


def _real_manifest_page(canonical: str) -> dict:
    data = json.loads(Path(str(DEFAULT_PAGES_MANIFEST)).read_text(encoding="utf-8"))
    for p in data["pages"]:
        if p.get("canonical_object") == canonical:
            return p
    raise AssertionError(f"page {canonical} not found in manifest")


def test_generate_dynamic_spread_prompt_alphabet():
    page = _real_manifest_page("alphabet_a_to_m")
    pos, neg = generate_dynamic_spread_prompt(page)
    assert "A" in pos
    assert neg
    assert "gray" in neg.lower() or "shading" in neg.lower()


def test_generate_dynamic_spread_prompt_counting():
    page = _real_manifest_page("numbers_6_to_10")
    pos, neg = generate_dynamic_spread_prompt(page)
    assert pos
    assert neg


def test_generate_dynamic_spread_prompt_extra_negative_tokens():
    page = _real_manifest_page("alphabet_a_to_m")
    _, neg_with = generate_dynamic_spread_prompt(page, extra_negative_tokens=["UNIQUE_MARKER"])
    assert "UNIQUE_MARKER" in neg_with


# ----------------------------------------------------------------------
# Additional branch coverage
# ----------------------------------------------------------------------


def test_generate_dynamic_visual_spec_fallback_template():
    spec = generate_dynamic_visual_spec("gizmo", "Unknown Section", False)
    assert "a single gizmo" in spec


def test_filter_contradictions_removes_wing_tokens_when_wings_required():
    filtered = _filter_contradictions("a bird with spread wings", ["wings", "extra"])
    assert "wings" not in filtered
    assert "extra" in filtered


def test_build_alphabet_spread_prompt_missing_template(monkeypatch):
    monkeypatch.setattr(
        "curiokraft_book.orchestrator.debate_engine._find_config_file",
        lambda _name: None,
    )
    assert _build_alphabet_spread_prompt("a_to_m", page_record={"cards": _thirteen_cards()}) is None


def test_build_alphabet_spread_prompt_auto_matches_manifest_pages():
    pages = [
        {
            "page_id": "P005",
            "page_number": 5,
            "canonical_object": "apple",
            "display_label": "APPLE",
            "type": "coloring_page",
        },
        {
            "page_id": "P006",
            "page_number": 6,
            "canonical_object": "ball",
            "display_label": "BALL",
            "type": "coloring_page",
        },
    ]
    prompt = _build_alphabet_spread_prompt(
        "a_to_m",
        page_record=None,
        all_manifest_pages=pages
        + [
            {
                "page_id": "P007",
                "page_number": 7,
                "canonical_object": "cat",
                "display_label": "CAT",
                "type": "coloring_page",
            },
        ],
    )
    assert prompt is not None
    assert "APPLE" in prompt


def test_build_alphabet_spread_prompt_bonus_tile_14_dict():
    prompt = _build_alphabet_spread_prompt(
        "a_to_m",
        page_record={
            "cards": _thirteen_cards(),
            "bonus_tile_14": {"description": "CUSTOM BONUS"},
            "bonus_tile_15": {"description": "SECOND BONUS"},
        },
    )
    assert prompt is not None
    assert "CUSTOM BONUS" in prompt
    assert "SECOND BONUS" in prompt


def test_get_custom_alphabet_spread_prompt_none_when_builder_returns_none(monkeypatch):
    monkeypatch.setattr(
        "curiokraft_book.orchestrator.debate_engine._build_alphabet_spread_prompt",
        lambda *a, **k: None,
    )
    assert (
        get_custom_alphabet_spread_prompt({"canonical_object": "alphabet_a_to_m", "page_number": 2})
        is None
    )


def test_extract_cover_showcase_cards_corrupt_manifest(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    assert extract_cover_showcase_cards(str(bad), count=3) == []


def test_extract_cover_showcase_cards_objects_only_group(tmp_path: Path):
    manifest = _write_manifest(
        tmp_path,
        [
            {
                "page_id": "P004",
                "page_number": 4,
                "canonical_object": "spoon",
                "section": "Household",
                "type": "coloring_page",
            },
            {
                "page_id": "P005",
                "page_number": 5,
                "canonical_object": "cup",
                "section": "Household",
                "type": "coloring_page",
            },
            {
                "page_id": "P006",
                "page_number": 6,
                "canonical_object": "ball",
                "section": "Toys",
                "type": "coloring_page",
            },
        ],
    )
    cards = extract_cover_showcase_cards(str(manifest), count=3)
    assert len(cards) == 3
    assert cards[0]["category_name"] == "Everyday Objects"


def test_extract_front_cover_ensemble_living_fallback(tmp_path: Path):
    manifest = _write_manifest(
        tmp_path,
        [
            {
                "page_id": "P010",
                "page_number": 10,
                "canonical_object": "zebra",
                "display_label": "ZEBRA",
                "section": "Animals",
            }
        ],
    )
    hero, companions, page_count = extract_front_cover_ensemble(str(manifest))
    assert "zebra" in hero.lower()
    assert page_count == 1


def test_extract_front_cover_ensemble_corrupt_manifest(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json", encoding="utf-8")
    hero, companions, page_count = extract_front_cover_ensemble(str(bad))
    assert hero  # falls back to the generic mascot description
    assert page_count == 110


def test_auto_pick_volume_mascot_corrupt_manifest(tmp_path: Path):
    cfg = tmp_path / "no_mascot.yaml"
    cfg.write_text("book:\n  title: Test\n", encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json", encoding="utf-8")
    assert auto_pick_volume_mascot(str(bad), str(cfg)) == "panda"


# ----------------------------------------------------------------------
# Cover debate spec assembly (offline — no LLM call is made)
# ----------------------------------------------------------------------


def test_build_cover_debate_spec_back_and_front():
    from curiokraft_book.constants import DEFAULT_BOOK_CONFIG
    from curiokraft_book.orchestrator.debate_engine import DebateEngine

    engine = DebateEngine()
    back = engine._build_cover_debate_spec(
        "back_cover",
        str(DEFAULT_PAGES_MANIFEST),
        str(DEFAULT_BOOK_CONFIG),
        None,
        "A TITLE",
        "A SUBTITLE",
        "BRAND",
        3,
        6,
    )
    assert back is not None

    front = engine._build_cover_debate_spec(
        "front_cover",
        str(DEFAULT_PAGES_MANIFEST),
        str(DEFAULT_BOOK_CONFIG),
        None,
        "A TITLE",
        "A SUBTITLE",
        "BRAND",
        3,
        6,
    )
    assert front is not None


def test_assemble_cover_debate_from_spec():
    from curiokraft_book.constants import DEFAULT_BOOK_CONFIG
    from curiokraft_book.orchestrator.debate_engine import DebateEngine

    engine = DebateEngine()
    spec = engine._build_cover_debate_spec(
        "front_cover",
        str(DEFAULT_PAGES_MANIFEST),
        str(DEFAULT_BOOK_CONFIG),
        None,
        "A TITLE",
        "A SUBTITLE",
        "BRAND",
        3,
        6,
    )
    result = engine._assemble_cover_debate(spec)
    assert result.positive_prompt
    assert result.negative_prompt


def test_run_mascot_debate_offline():
    from curiokraft_book.constants import DEFAULT_BOOK_CONFIG
    from curiokraft_book.orchestrator.debate_engine import DebateEngine

    engine = DebateEngine()
    result = engine.run_mascot_debate(
        mascot_name="panda", book_config_path=str(DEFAULT_BOOK_CONFIG)
    )
    assert result.positive_prompt
    assert result.negative_prompt


def test_export_full_debate_log(tmp_path: Path):
    from curiokraft_book.orchestrator.debate_engine import DebateEngine

    manifest = _write_manifest(
        tmp_path,
        [
            {
                "page_id": "P005",
                "page_number": 5,
                "canonical_object": "banana",
                "display_label": "BANANA",
                "section": "Fruits",
                "type": "coloring_page",
            }
        ],
    )
    engine = DebateEngine()
    out = engine.export_full_debate_log(str(manifest), str(tmp_path / "debate_log.md"))
    assert Path(out).exists()
    text = Path(out).read_text(encoding="utf-8")
    assert "Round 4" in text
    assert "BANANA" in text


def test_export_full_debate_log_missing_manifest_raises(tmp_path: Path):
    from curiokraft_book.orchestrator.debate_engine import DebateEngine

    engine = DebateEngine()
    with pytest.raises(FileNotFoundError):
        engine.export_full_debate_log(str(tmp_path / "absent.json"), str(tmp_path / "out.md"))
