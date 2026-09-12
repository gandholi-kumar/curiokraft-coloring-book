"""Unit tests for Multi-Agent Amazon KDP Publishing & Form Parsing Engine."""

import json
import re
from pathlib import Path

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
