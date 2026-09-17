from curiokraft_book.orchestrator.archetypes import (
    ArchetypeRegistry,
    ConnectTheDotsStrategy,
    CoverThemeRegistry,
    GeometricPatternStrategy,
    IntegratedHabitatStrategy,
    MultiCardSpreadStrategy,
    SingleCenteredStrategy,
    TracingHandwritingStrategy,
    _load_yaml_file,
    get_curriculum,
    get_taxonomy,
    join_negative_tokens,
)


def test_join_negative_tokens():
    tokens = [
        ["blurry", "low quality", "color"],
        ["color", "shading", "blurry"],
        None,
        ["grainy"],
    ]
    res = join_negative_tokens(tokens)
    assert "blurry" in res
    assert "color" in res
    assert "grainy" in res
    assert "shading" in res
    # Ensure deduplicated
    parts = [p.strip() for p in res.split(",")]
    assert len(parts) == len(set(parts))


def test_yaml_loaders():
    tax = get_taxonomy()
    assert isinstance(tax, dict)
    cur = get_curriculum()
    assert isinstance(cur, dict)
    # Non-existent file loader fallback
    missing = _load_yaml_file("non_existent_path.yaml")
    assert missing == {}


def test_integrated_habitat_strategy():
    strategy = IntegratedHabitatStrategy()
    assert strategy.archetype_id == "integrated_habitat"

    page_record = {
        "canonical_object": "clownfish",
        "display_label": "Clownfish & Coral",
        "composition": "integrated_aquatic_scene",
    }
    book_config = {
        "visual_style": {"background": "aquatic_environment"},
        "age_min": 4,
        "age_max": 8,
    }
    pos, neg = strategy.build_prompt(page_record, book_config)
    assert "Clownfish" in pos
    assert len(neg) > 0


def test_single_centered_strategy():
    strategy = SingleCenteredStrategy()
    assert strategy.archetype_id == "single_centered_subject"

    page_record = {"canonical_object": "apple", "display_label": "Apple"}
    book_config = {"age_min": 2, "age_max": 4}
    pos, neg = strategy.build_prompt(page_record, book_config)
    assert "Apple" in pos
    assert "single" in pos.lower() or "centered" in pos.lower()


def test_geometric_pattern_strategy():
    strategy = GeometricPatternStrategy()
    assert strategy.archetype_id == "geometric_pattern"

    page_record = {"canonical_object": "mandala", "display_label": "Ocean Mandala"}
    book_config = {}
    pos, neg = strategy.build_prompt(page_record, book_config)
    assert "mandala" in pos.lower() or "geometric" in pos.lower()


def test_connect_the_dots_strategy():
    strategy = ConnectTheDotsStrategy()
    assert strategy.archetype_id == "connect_the_dots"

    page_record = {"canonical_object": "starfish", "display_label": "Starfish"}
    book_config = {}
    pos, neg = strategy.build_prompt(page_record, book_config)
    assert "dots" in pos.lower() or "connect" in pos.lower()


def test_tracing_handwriting_strategy():
    strategy = TracingHandwritingStrategy()
    assert strategy.archetype_id == "tracing_handwriting"

    page_record = {"canonical_object": "letter_a", "display_label": "Letter A"}
    book_config = {}
    pos, neg = strategy.build_prompt(page_record, book_config)
    assert "tracing" in pos.lower() or "guideline" in pos.lower()


def test_multi_card_spread_strategy():
    strategy = MultiCardSpreadStrategy()
    assert strategy.archetype_id == "multi_card_spread"

    # Injected builder
    strategy.set_prompt_builder(lambda rec: (f"Custom spread for {rec['display_label']}", "no bad"))
    pos, neg = strategy.build_prompt({"display_label": "A-D Overview"}, {})
    assert "Custom spread for A-D Overview" in pos
    assert neg == "no bad"

    # Reset builder to test fallback/dynamic import
    strategy.set_prompt_builder(None)
    pos2, _ = strategy.build_prompt({"display_label": "Numbers 1-10"}, {})
    assert len(pos2) > 0


def test_archetype_registry_resolve():
    # 1. Explicit archetype
    arch = ArchetypeRegistry.resolve({"archetype": "geometric_pattern"}, {})
    assert isinstance(arch, GeometricPatternStrategy)

    # 2. Type based
    arch = ArchetypeRegistry.resolve({"type": "alphabet_spread"}, {})
    assert isinstance(arch, MultiCardSpreadStrategy)

    # 3. Composition based
    arch = ArchetypeRegistry.resolve({"composition": "aquatic"}, {})
    assert isinstance(arch, IntegratedHabitatStrategy)

    arch = ArchetypeRegistry.resolve({"composition": "dots"}, {})
    assert isinstance(arch, ConnectTheDotsStrategy)

    arch = ArchetypeRegistry.resolve({"composition": "tracing"}, {})
    assert isinstance(arch, TracingHandwritingStrategy)

    arch = ArchetypeRegistry.resolve({"composition": "flashcard_grid"}, {})
    assert isinstance(arch, MultiCardSpreadStrategy)

    # 4. Background style based
    arch = ArchetypeRegistry.resolve({}, {"visual_style": {"background": "aquatic_environment"}})
    assert isinstance(arch, IntegratedHabitatStrategy)

    # 5. Default fallback
    arch = ArchetypeRegistry.resolve({}, {})
    assert isinstance(arch, SingleCenteredStrategy)


def test_cover_theme_registry_resolve():
    # Toddler resolution
    theme = CoverThemeRegistry.resolve(
        {"book": {"volume": "vol1", "visual_style": {"background": "none"}}},
        manifest_path="manifest/pages.json",
    )
    assert isinstance(theme, dict)

    # Aquatic resolution
    theme_aquatic = CoverThemeRegistry.resolve(
        {"book": {"volume": "aquatic_vol1", "visual_style": {"background": "aquatic_environment"}}},
        manifest_path="manifest/pages_aquatic_vol1.json",
    )
    assert isinstance(theme_aquatic, dict)
