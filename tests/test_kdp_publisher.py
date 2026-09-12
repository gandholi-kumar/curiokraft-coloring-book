"""Unit tests for Multi-Agent Amazon KDP Publishing & Form Parsing Engine."""

import json
import re
from pathlib import Path

import pytest

from curiokraft_book.agents.kdp_parser import (
    inspect_kdp_inbox_forms,
    parse_kdp_html_file,
)
from curiokraft_book.agents.kdp_publisher import (
    KDPComplianceAgent,
    KDPCopywriterAgent,
    KDPPublisherOrchestrator,
    KDPSEOAgent,
)
from curiokraft_book.compositor.kdp_dashboard import save_kdp_submission_bundle


def test_kdp_parser_empty_directory(tmp_path: Path):
    """Verify parser handles non-existent or empty folder gracefully."""
    empty_dir = tmp_path / "empty_forms"
    empty_dir.mkdir()
    inspection = inspect_kdp_inbox_forms(empty_dir)
    assert not inspection.has_html_forms
    assert inspection.html_files_found == 0


def test_kdp_parser_with_sample_html(tmp_path: Path):
    """Verify parser correctly extracts form controls, labels, and limits."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><title>KDP Paperback Details - Amazon</title></head>
    <body>
      <h2>Paperback Details</h2>
      <form>
        <label for="book-title">Book Title</label>
        <input type="text" id="book-title" name="data[title]" maxlength="200" placeholder="Enter title" />

        <label for="book-subtitle">Subtitle</label>
        <input type="text" id="book-subtitle" name="data[subtitle]" maxlength="200" />

        <label for="kw1">Keyword 1</label>
        <input type="text" id="kw1" name="data[keywords][0]" maxlength="50" />

        <label for="desc">Description</label>
        <textarea id="desc" name="data[description]" maxlength="4000"></textarea>

        <select id="market" name="data[marketplace]">
          <option value="amazon.com">Amazon.com</option>
          <option value="amazon.co.uk">Amazon.co.uk</option>
        </select>
      </form>
    </body>
    </html>
    """
    html_file = tmp_path / "tab1_details.html"
    html_file.write_text(html_content, encoding="utf-8")

    parsed = parse_kdp_html_file(html_file)
    assert parsed.tab_detected == "details"
    assert parsed.fields_count >= 5

    # Check limits
    inspection = inspect_kdp_inbox_forms(tmp_path)
    assert inspection.has_html_forms
    assert inspection.html_files_found == 1
    assert (
        "title" in inspection.detected_limits
        or "data[title]" in inspection.detected_limits
        or "book-title" in inspection.detected_limits
    )


def test_kdp_seo_keywords_length_and_deduplication():
    """Verify that all 7 keywords are <= 50 chars and do not repeat words from Title/Subtitle."""
    title = "TINY HANDS COLOR & LEARN"
    subtitle = "FUN & EASY FIRST WORDS - Vol 2"
    volume = "vol2"

    agent = KDPSEOAgent(title, subtitle, volume, Path("manifest/pages_vol2.json"))
    keywords = agent.generate_keywords()

    assert len(keywords) == 7

    title_words = {"tiny", "hands", "color", "learn", "fun", "easy", "first", "words", "vol", "2"}

    for kw in keywords:
        assert len(kw) <= 50, f"Keyword exceeds 50 chars: '{kw}' ({len(kw)})"
        kw_tokens = set(re.findall(r"\b[a-z0-9]+\b", kw.lower()))
        overlap = kw_tokens.intersection(title_words)
        assert not overlap, f"Keyword '{kw}' overlaps with title words: {overlap}"


def test_kdp_copywriter_html_tags():
    """Verify description uses only permitted Amazon KDP HTML tags and stays under 4,000 chars."""
    agent = KDPCopywriterAgent(
        title="TINY HANDS COLOR & LEARN",
        subtitle="FUN & EASY FIRST WORDS - Vol 2",
        volume="vol2",
        mascot_name="panda",
    )
    desc = agent.generate_html_description()

    assert len(desc) <= 4000
    assert "PANDA" in desc.upper()
    assert "VOLUME 2" in desc.upper()

    # Verify permitted tags only
    tags = re.findall(r"<\/?([a-zA-Z0-9]+)[^>]*>", desc)
    allowed_tags = {"h2", "h3", "p", "b", "i", "ul", "li", "br"}
    for tag in tags:
        assert tag.lower() in allowed_tags, f"Forbidden HTML tag found in KDP description: <{tag}>"

    # Verify strictly ZERO emojis and ZERO stars in description
    assert "★" not in desc, "Forbidden star symbol '★' found in description (Amazon will reject)"
    for char in desc:
        assert ord(char) < 128 or char in "–—’‘“”", (
            f"Non-standard character '{char}' (U+{ord(char):04X}) found in description"
        )


def test_kdp_compliance_specs():
    """Verify compliance agent extracts correct KDP print geometry and AI disclosures."""
    cfg = {
        "interior": {"page_count": 110},
    }
    agent = KDPComplianceAgent(cfg)
    specs = agent.get_print_specs()
    assert specs["page_count"] == 110
    assert "8.5 x 11" in specs["trim_size"]
    assert specs["bleed_settings"] == "No Bleed"
    assert specs["cover_finish"] == "Glossy"

    ai = agent.get_ai_disclosure()
    assert "Yes" in ai["ai_generated_images"]
    assert "No" in ai["ai_generated_text"]
    assert "Gemini" in ai["ai_images_details"] or "Imagen" in ai["ai_images_details"]


def test_kdp_dashboard_generation(tmp_path: Path):
    """Verify complete bundle generation produces HTML dashboard, Markdown cheatsheet, and JSON."""
    orchestrator = KDPPublisherOrchestrator(
        config_path=Path("config/book_config.yaml"),
        inbox_forms_dir=tmp_path,
    )
    package = orchestrator.synthesize()
    assert package.volume_id == "vol2"
    assert package.title == "TINY HANDS COLOR & LEARN"
    assert len(package.details.category_items) == 3
    assert len(package.agent_deliberations) >= 3

    saved = save_kdp_submission_bundle(package, output_dir=tmp_path / "kdp_out")
    assert saved["html"].exists()
    assert saved["markdown"].exists()
    assert saved["json"].exists()

    # Validate JSON
    data = json.loads(saved["json"].read_text(encoding="utf-8"))
    assert data["details"]["book_title"] == "TINY HANDS COLOR & LEARN"
    assert len(data["details"]["keywords"]) == 7
    assert data["details"]["language"] == "English"
    assert data["details"]["combined_title_length"] == 54

    # Validate HTML dashboard has copy functions and tab titles
    html_content = saved["html"].read_text(encoding="utf-8")
    assert "copyField" in html_content
    assert "1. Paperback Details" in html_content
    assert "2. Paperback Content" in html_content
    assert "3. Rights &amp; Pricing" in html_content
    assert "Agent Deliberations &amp; Audit" in html_content
    assert "📋" not in html_content, "Emoji '📋' should not be used in copy buttons"


def test_kdp_parser_classify_fields():
    """Verify field classification across all supported KDP attributes."""
    from curiokraft_book.agents.kdp_parser import _canonicalize_field_key

    def check(txt: str):
        return _canonicalize_field_key(txt, "", "")

    assert check("series title") == ("details", "series_title")
    assert check("series number volume 2") == ("details", "series_number")
    assert check("edition number") == ("details", "edition_number")
    assert check("primary-author first_name") == ("details", "author_first")
    assert check("primary-author middle_name") == ("details", "author_middle")
    assert check("primary-author last_name") == ("details", "author_last")
    assert check("primary-author prefix") == ("details", "author_prefix")
    assert check("primary-author suffix") == ("details", "author_suffix")
    assert check("primary-author") == ("details", "author_name")
    assert check("contributor role") == ("details", "contributor_role")
    assert check("contributor name") == ("details", "contributors")
    assert check("public_domain rights") == ("details", "publishing_rights")
    assert check("adult_content flag") == ("details", "adult_content")
    assert check("reading_age min") == ("details", "reading_age_min")
    assert check("reading_age max") == ("details", "reading_age_max")
    assert check("low-content book") == ("details", "low_content_book")
    assert check("large-print book") == ("details", "large_print_book")
    assert check("publication_date") == ("details", "publication_date")
    assert check("release_date") == ("details", "release_date")

    # Content tab
    assert check("isbn input") == ("content", "isbn")
    assert check("interior black and white paper") == ("content", "interior_paper")
    assert check("trim size 8.5") == ("content", "trim_size")
    assert check("bleed settings") == ("content", "bleed_settings")
    assert check("matte finish") == ("content", "cover_finish")
    assert check("left to right direction") == ("content", "page_direction")
    assert check("manuscript upload") == ("content", "manuscript_file")
    assert check("cover file upload") == ("content", "cover_file")
    assert check("ai_disclosure artificial intelligence") == ("content", "ai_disclosure")

    # Pricing tab
    assert check("worldwide territories") == ("pricing", "territories")
    assert check("price_usd") == ("pricing", "list_price_usd")
    assert check("royalty pricing list price") == ("pricing", "list_price")
    assert check("expanded distribution") == ("pricing", "expanded_distribution")
    assert check("unrecognized text") == ("unknown", "unmapped")


def test_parse_kdp_html_file_not_found(tmp_path: Path):
    """Verify FileNotFoundError when target HTML does not exist."""
    with pytest.raises(FileNotFoundError):
        parse_kdp_html_file(tmp_path / "non_existent_tab.html")


def test_inspect_kdp_inbox_forms_multiple_tabs(tmp_path: Path):
    """Verify inspection discovers multiple tabs and classifies them."""
    forms_dir = tmp_path / "inbox_forms"
    forms_dir.mkdir()

    (forms_dir / "tab1_details.html").write_text(
        '<form><input id="title" name="data[title]" maxlength="200" /></form>',
        encoding="utf-8",
    )
    (forms_dir / "tab2_content.html").write_text(
        '<form><input id="isbn" name="data[isbn]" /></form>',
        encoding="utf-8",
    )
    (forms_dir / "tab3_pricing.html").write_text(
        '<form><input id="price" name="data[price_usd]" /></form>',
        encoding="utf-8",
    )

    inspection = inspect_kdp_inbox_forms(forms_dir)
    assert inspection.has_html_forms is True
    assert inspection.html_files_found == 3
    assert len(inspection.parsed_files) == 3
