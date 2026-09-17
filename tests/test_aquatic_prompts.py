from curiokraft_book.orchestrator.debate_engine import (
    DebateEngine,
    generate_certificate_page_prompt,
    generate_dynamic_spread_prompt,
    generate_perimeter_frame_prompt,
    generate_welcome_page_prompt,
)


def test_generate_welcome_page_prompts():
    pos_ocean, neg_ocean = generate_welcome_page_prompt(habitat="OCEAN")
    assert "WELCOME, OCEAN EXPLORER!" in pos_ocean
    assert "LOGBOOK" in pos_ocean
    assert len(neg_ocean) > 0

    pos_sky, _ = generate_welcome_page_prompt(habitat="SKY")
    assert "WELCOME, SKY EXPLORER!" in pos_sky

    pos_wild, _ = generate_welcome_page_prompt(habitat="WILDLIFE")
    assert "WELCOME, WILDLIFE EXPLORER!" in pos_wild

    # Default habitat resolution
    pos_def, _ = generate_welcome_page_prompt()
    assert "WELCOME," in pos_def


def test_generate_certificate_page_prompts():
    pos_ocean, neg_ocean = generate_certificate_page_prompt(habitat="OCEAN")
    assert "COMPLETION CERTIFICATE" in pos_ocean.upper()
    assert "MASTER OCEAN COLORIST" in pos_ocean
    assert len(neg_ocean) > 0

    pos_sky, _ = generate_certificate_page_prompt(habitat="SKY")
    assert "MASTER SKY COLORIST" in pos_sky

    pos_wild, _ = generate_certificate_page_prompt(habitat="WILDLIFE")
    assert "MASTER WILDLIFE COLORIST" in pos_wild

    pos_def, _ = generate_certificate_page_prompt()
    assert "COLORIST" in pos_def


def test_generate_perimeter_frame_prompt():
    pos_ocean, neg_ocean = generate_perimeter_frame_prompt(theme_name="ocean")
    assert len(pos_ocean) > 0
    assert len(neg_ocean) > 0

    pos_wild, _ = generate_perimeter_frame_prompt(theme_name="wildlife")
    assert len(pos_wild) > 0

    pos_def, _ = generate_perimeter_frame_prompt()
    assert len(pos_def) > 0


def test_dynamic_spread_prompt():
    page_record = {
        "page_id": "P010",
        "display_label": "A-D Overview",
        "canonical_object": "alphabet_spread_a_d",
        "cards": [
            {"letter": "A", "object": "Apple", "cavity": "large"},
            {"letter": "B", "object": "Ball", "cavity": "large"},
            {"letter": "C", "object": "Cat", "cavity": "large"},
            {"letter": "D", "object": "Dog", "cavity": "large"},
        ],
    }
    pos, neg = generate_dynamic_spread_prompt(page_record)
    assert "Apple" in pos
    assert "Ball" in pos
    assert len(neg) > 0


def test_debate_engine_cover_spec():
    engine = DebateEngine()
    spec_front = engine._build_cover_debate_spec(
        cover_type="front",
        manifest_path="manifest/pages_aquatic_vol1.json",
        book_config_path="config/book_config_bleed.yaml",
        blueprint_spec=None,
        title="OCEAN EXPEDITIONS",
        subtitle="COLORING BOOK",
        brand="CURIOKRAFT",
        age_min=4,
        age_max=8,
    )
    assert spec_front.page_id == "COVER_FRONT"
    assert spec_front.canonical_object == "front_cover"
    assert spec_front.display_label == "FRONT COVER MASTER ARTWORK"

    spec_back = engine._build_cover_debate_spec(
        cover_type="back",
        manifest_path="manifest/pages_aquatic_vol1.json",
        book_config_path="config/book_config_bleed.yaml",
        blueprint_spec=None,
        title="OCEAN EXPEDITIONS",
        subtitle="COLORING BOOK",
        brand="CURIOKRAFT",
        age_min=4,
        age_max=8,
    )
    assert spec_back.page_id == "COVER_BACK"
    assert spec_back.canonical_object == "back_cover"
    assert spec_back.display_label == "BACK COVER MASTER ARTWORK"
