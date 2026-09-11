"""HTML Form Parser for Amazon KDP Web Publishing Screens.

Parses saved Amazon KDP HTML pages from inbox/kdp_forms/ to extract input
fields, textareas, selects, radios, character limits, and section tabs.
Uses Python's standard library html.parser (zero external dependencies).
"""

from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from curiokraft_book.constants import DEFAULT_KDP_FORMS_INBOX_DIR

logger = logging.getLogger("curiokraft.kdp_parser")


class KDPFormField(BaseModel):
    """Extracted form field control with attributes and context."""

    tag: str  # input, textarea, select
    field_type: str = "text"  # text, radio, checkbox, hidden, etc.
    name: str = ""
    field_id: str = ""
    label: str = ""
    placeholder: str = ""
    maxlength: int | None = None
    value: str = ""
    options: list[str] = Field(default_factory=list)
    aria_label: str = ""
    tab_guess: str = "unknown"  # details, content, pricing, unknown
    canonical_key: str = ""


class KDPParsedFile(BaseModel):
    """Result of parsing a single HTML file."""

    file_path: str
    file_name: str
    tab_detected: str = "unknown"  # details, content, pricing, general
    page_title: str = ""
    fields_count: int = 0
    fields: list[KDPFormField] = Field(default_factory=list)


class KDPFormInspection(BaseModel):
    """Aggregated inspection of all HTML forms in inbox/kdp_forms/."""

    source_dir: str
    html_files_found: int = 0
    parsed_files: list[KDPParsedFile] = Field(default_factory=list)
    fields_by_tab: dict[str, list[KDPFormField]] = Field(default_factory=dict)
    detected_limits: dict[str, int] = Field(default_factory=dict)
    has_html_forms: bool = False


class _KDPRawHTMLParser(HTMLParser):
    """Internal HTML parser extracting inputs, labels, textareas, and selects."""

    def __init__(self) -> None:
        super().__init__()
        self.fields: list[dict[str, Any]] = []
        self.labels: dict[str, str] = {}  # id -> label_text
        self.current_label_for: str | None = None
        self.current_label_text: list[str] = []
        self.current_tag: str | None = None
        self.current_textarea: dict[str, Any] | None = None
        self.current_select: dict[str, Any] | None = None
        self.page_title_parts: list[str] = []
        self.in_title: bool = False
        self.in_heading: bool = False
        self.headings: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k.lower(): (v or "") for k, v in attrs}
        self.current_tag = tag

        if tag == "title":
            self.in_title = True
        elif tag in ("h1", "h2", "h3"):
            self.in_heading = True
        elif tag == "label":
            self.current_label_for = attr_dict.get("for")
            self.current_label_text = []
        elif tag == "input":
            f_type = attr_dict.get("type", "text").lower()
            if f_type in ("text", "radio", "checkbox", "number", "search", "url", "file"):
                max_l = None
                if "maxlength" in attr_dict:
                    try:
                        max_l = int(attr_dict["maxlength"])
                    except ValueError:
                        pass
                self.fields.append(
                    {
                        "tag": "input",
                        "field_type": f_type,
                        "name": attr_dict.get("name", ""),
                        "field_id": attr_dict.get("id", ""),
                        "placeholder": attr_dict.get("placeholder", ""),
                        "maxlength": max_l,
                        "value": attr_dict.get("value", ""),
                        "aria_label": attr_dict.get("aria-label", ""),
                    }
                )
        elif tag == "textarea":
            max_l = None
            if "maxlength" in attr_dict:
                try:
                    max_l = int(attr_dict["maxlength"])
                except ValueError:
                    pass
            self.current_textarea = {
                "tag": "textarea",
                "field_type": "textarea",
                "name": attr_dict.get("name", ""),
                "field_id": attr_dict.get("id", ""),
                "placeholder": attr_dict.get("placeholder", ""),
                "maxlength": max_l,
                "value": "",
                "aria_label": attr_dict.get("aria-label", ""),
            }
        elif tag == "select":
            self.current_select = {
                "tag": "select",
                "field_type": "select",
                "name": attr_dict.get("name", ""),
                "field_id": attr_dict.get("id", ""),
                "placeholder": "",
                "maxlength": None,
                "value": "",
                "options": [],
                "aria_label": attr_dict.get("aria-label", ""),
            }
        elif tag == "option" and self.current_select is not None:
            val = attr_dict.get("value", "")
            if val:
                self.current_select["options"].append(val)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        elif tag in ("h1", "h2", "h3"):
            self.in_heading = False
        elif tag == "label":
            if self.current_label_for:
                text = " ".join(self.current_label_text).strip()
                if text:
                    self.labels[self.current_label_for] = text
            self.current_label_for = None
            self.current_label_text = []
        elif tag == "textarea" and self.current_textarea is not None:
            self.fields.append(self.current_textarea)
            self.current_textarea = None
        elif tag == "select" and self.current_select is not None:
            self.fields.append(self.current_select)
            self.current_select = None
        self.current_tag = None

    def handle_data(self, data: str) -> None:
        clean_text = data.strip()
        if not clean_text:
            return

        if self.in_title:
            self.page_title_parts.append(clean_text)
        elif self.current_tag == "label":
            self.current_label_text.append(clean_text)
        elif self.current_textarea is not None:
            self.current_textarea["value"] += clean_text
        elif self.in_heading:
            self.headings.append(clean_text)


def _canonicalize_field_key(name: str, field_id: str, label: str) -> tuple[str, str]:
    """Map raw HTML field identifiers to canonical KDP fields and tabs."""
    text = f"{name} {field_id} {label}".lower()

    # Tab 1: Details
    if "language" in text:
        return "details", "language"
    if any(k in text for k in ("subtitle", "sub-title")):
        return "details", "subtitle"
    if any(k in text for k in ("book title", "print_book][title]", "print-book-title")):
        return "details", "title"
    if "series" in text:
        if any(k in text for k in ("number", "order", "vol")):
            return "details", "series_number"
        return "details", "series_title"
    if "edition" in text:
        return "details", "edition_number"

    # Author & Contributor components
    if "primary_author" in text or "primary-author" in text:
        if "prefix" in text:
            return "details", "author_prefix"
        if any(k in text for k in ("first_name", "first-name", "first")):
            return "details", "author_first"
        if any(k in text for k in ("middle_name", "middle-name", "middle")):
            return "details", "author_middle"
        if any(k in text for k in ("last_name", "last-name", "last")):
            return "details", "author_last"
        if "suffix" in text:
            return "details", "author_suffix"
        return "details", "author_name"

    if "contributor" in text:
        if "role" in text:
            return "details", "contributor_role"
        return "details", "contributors"

    if any(k in text for k in ("description", "synopsis", "summary")):
        return "details", "description"

    # Publishing Rights (Public domain vs copyright)
    if any(k in text for k in ("public_domain", "public-domain", "is_public_domain", "publishing rights", "copyright")):
        return "details", "publishing_rights"

    # Adult content
    if any(k in text for k in ("adult_content", "is_adult_content", "sexually explicit")):
        return "details", "adult_content"

    # Reading age ranges
    if any(k in text for k in ("reading_interest_age", "reading-interest-age", "reading age", "reading_age")):
        if any(k in text for k in ("min", "start")):
            return "details", "reading_age_min"
        if any(k in text for k in ("max", "end")):
            return "details", "reading_age_max"

    # Classification types
    if any(k in text for k in ("is_lcb", "low-content", "low_content", "low content", "lcb")):
        return "details", "low_content_book"
    if any(k in text for k in ("large_print", "large-print", "large print")):
        return "details", "large_print_book"

    # Marketplace & Categories
    if any(k in text for k in ("home_marketplace", "primary market", "marketplace")):
        return "details", "primary_marketplace"
    if any(k in text for k in ("browse_nodes", "category", "categories", "bisac")):
        return "details", "categories"

    # Keywords (boxes 0 to 6)
    if "keyword" in text:
        m = re.search(r"keywords?\]?\[?_?-?([0-6])", text)
        if m:
            return "details", f"keyword_{int(m.group(1)) + 1}"
        return "details", "keywords"

    # Publication & Release Date
    if any(k in text for k in ("publication_date", "publication-date", "previously_published")):
        return "details", "publication_date"
    if any(k in text for k in ("release_date", "release-date", "release_event", "future_release")):
        return "details", "release_date"

    # Tab 2: Content
    if "isbn" in text:
        return "content", "isbn"
    if any(k in text for k in ("interior", "paper type", "black and white", "color")):
        return "content", "interior_paper"
    if any(k in text for k in ("trim", "trim size", "8.5")):
        return "content", "trim_size"
    if "bleed" in text:
        return "content", "bleed_settings"
    if any(k in text for k in ("finish", "glossy", "matte")):
        return "content", "cover_finish"
    if any(k in text for k in ("direction", "page turn", "left to right", "right to left")):
        return "content", "page_direction"
    if any(k in text for k in ("manuscript", "interior file", "upload interior")):
        return "content", "manuscript_file"
    if any(k in text for k in ("cover file", "upload cover")):
        return "content", "cover_file"
    if re.search(r"\bai\b|artificial intelligence|ai-generated|ai_disclosure", text):
        return "content", "ai_disclosure"

    # Tab 3: Pricing
    if any(k in text for k in ("territory", "territories", "worldwide")):
        return "pricing", "territories"
    if "price-input-usd" in text or "price_usd" in text:
        return "pricing", "list_price_usd"
    if any(k in text for k in ("price-input", "list price", "royalty", "pricing")):
        return "pricing", "list_price"
    if any(k in text for k in ("expanded", "distribution")):
        return "pricing", "expanded_distribution"

    return "unknown", "unmapped"


def parse_kdp_html_file(file_path: str | Path) -> KDPParsedFile:
    """Parse a single HTML file from Amazon KDP."""
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(f"HTML file not found: {p}")

    content = p.read_text(encoding="utf-8", errors="replace")
    parser = _KDPRawHTMLParser()
    try:
        parser.feed(content)
    except Exception as err:
        logger.warning("Error parsing HTML %s: %s", p.name, err)

    fields: list[KDPFormField] = []
    for raw in parser.fields:
        f_id = raw.get("field_id", "")
        f_name = raw.get("name", "")
        label_text = parser.labels.get(f_id, "")
        if not label_text and f_name in parser.labels:
            label_text = parser.labels[f_name]

        tab_guess, canonical_key = _canonicalize_field_key(f_name, f_id, label_text)

        fields.append(
            KDPFormField(
                tag=raw["tag"],
                field_type=raw.get("field_type", "text"),
                name=f_name,
                field_id=f_id,
                label=label_text,
                placeholder=raw.get("placeholder", ""),
                maxlength=raw.get("maxlength"),
                value=raw.get("value", ""),
                options=raw.get("options", []),
                aria_label=raw.get("aria_label", ""),
                tab_guess=tab_guess,
                canonical_key=canonical_key,
            )
        )

    title_text = " ".join(parser.page_title_parts).strip()
    headings_joined = " ".join(parser.headings).lower()
    lowered_all = f"{title_text} {headings_joined} {p.name}".lower()

    if any(k in headings_joined for k in ("rights & pricing", "royalties", "territories")) or any(k in lowered_all for k in ("pricing", "rights", "tab3")):
        tab_detected = "pricing"
    elif any(k in lowered_all for k in ("detail", "details", "tab1", "step1")):
        tab_detected = "details"
    elif any(k in lowered_all for k in ("content", "manuscript", "tab2", "step2")):
        tab_detected = "content"
    else:
        tab_detected = "general"

    return KDPParsedFile(
        file_path=str(p),
        file_name=p.name,
        tab_detected=tab_detected,
        page_title=title_text,
        fields_count=len(fields),
        fields=fields,
    )


def inspect_kdp_inbox_forms(
    inbox_dir: str | Path = DEFAULT_KDP_FORMS_INBOX_DIR,
) -> KDPFormInspection:
    """Inspect all HTML files in inbox/kdp_forms/ and build field mapping."""
    target_p = Path(inbox_dir)
    if not target_p.exists():
        return KDPFormInspection(source_dir=str(target_p), has_html_forms=False)

    html_files = sorted(list(target_p.glob("*.html")) + list(target_p.glob("*.htm")))
    if not html_files:
        return KDPFormInspection(source_dir=str(target_p), has_html_forms=False)

    parsed_files: list[KDPParsedFile] = []
    fields_by_tab: dict[str, list[KDPFormField]] = {
        "details": [],
        "content": [],
        "pricing": [],
        "unknown": [],
    }
    detected_limits: dict[str, int] = {}

    for f in html_files:
        pf = parse_kdp_html_file(f)
        parsed_files.append(pf)
        for field in pf.fields:
            fields_by_tab.setdefault(field.tab_guess, []).append(field)
            if field.maxlength:
                detected_limits[field.canonical_key or field.name or field.field_id] = field.maxlength

    return KDPFormInspection(
        source_dir=str(target_p),
        html_files_found=len(html_files),
        parsed_files=parsed_files,
        fields_by_tab=fields_by_tab,
        detected_limits=detected_limits,
        has_html_forms=True,
    )
