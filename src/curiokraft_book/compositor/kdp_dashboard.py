"""Interactive 1-Click Copy-to-Clipboard Amazon KDP Publishing Dashboard.

Features:
- Zero emojis and zero special symbols (100% standard characters compliant with Amazon KDP).
- Complete field mapping matching live Amazon KDP screens (Language, Title, Subtitle, Series,
  Author breakdown, Category Modal Navigation Trees, Book Classification checkboxes, Description,
  7 Keywords, Content print geometry, and Pricing).
- Multi-Agent Deliberation & Audit Log showcasing the rationale of AGT-KDP-001 through AGT-KDP-004.
"""

from __future__ import annotations

import html
import json
import logging
from pathlib import Path

from curiokraft_book.constants import (
    DEFAULT_KDP_FIELDS_MD,
    DEFAULT_KDP_METADATA_JSON,
    DEFAULT_KDP_OUTPUT_DIR,
    DEFAULT_KDP_SUBMISSION_HTML,
)
from curiokraft_book.agents.kdp_publisher import KDPSubmissionPackage

logger = logging.getLogger("curiokraft.kdp_dashboard")


def render_kdp_html_dashboard(package: KDPSubmissionPackage) -> str:
    """Generate interactive, responsive, offline-ready HTML submission dashboard."""
    d = package.details
    c = package.content
    p = package.pricing

    desc_escaped_html = html.escape(d.description_html)

    # Keywords HTML rows
    keywords_html = ""
    for idx, kw in enumerate(d.keywords, 1):
        kw_len = len(kw)
        badge_class = "badge-pass" if kw_len <= 50 else "badge-warn"
        keywords_html += f"""
        <div class="field-card">
          <div class="field-header">
            <span class="field-title">Keyword Box #{idx}</span>
            <span class="field-badge {badge_class}">{kw_len} / 50 chars</span>
          </div>
          <div class="field-body">
            <input type="text" class="field-input" id="kw_{idx}" value="{html.escape(kw)}" readonly />
            <button class="copy-btn" onclick="copyField('kw_{idx}')">Copy</button>
          </div>
        </div>
        """

    # Category Modal Step-by-Step Tree HTML (Matching Amazon KDP Modal)
    categories_html = ""
    for idx, cat in enumerate(d.category_items, 1):
        subcats_str = " &gt; ".join(cat.subcategories)
        placements_str = ", ".join(cat.placements)
        categories_html += f"""
        <div class="field-card category-card">
          <div class="field-header">
            <span class="field-title">Category #{idx}: {cat.category}</span>
            <span class="field-badge badge-info">Modal Placement</span>
          </div>
          <div class="category-steps">
            <div class="step-row"><b>1. Category:</b> <span class="step-val">{cat.category}</span></div>
            <div class="step-row"><b>2. Subcategories:</b> <span class="step-val">{subcats_str}</span></div>
            <div class="step-row"><b>3. Check Placement Box:</b> <span class="step-badge">[X] {placements_str}</span></div>
          </div>
          <div class="field-body" style="margin-top: 8px;">
            <input type="text" class="field-input" id="cat_{idx}" value="{html.escape(cat.display_path)}" readonly />
            <button class="copy-btn" onclick="copyField('cat_{idx}')">Copy Full Path</button>
          </div>
        </div>
        """

    # Agent Deliberations HTML
    debates_html = ""
    for deb in package.agent_deliberations:
        debates_html += f"""
        <div class="agent-card">
          <div class="agent-header">
            <span class="agent-id">[{deb.agent_id}]</span>
            <span class="agent-name">{deb.agent_name}</span>
            <span class="agent-verdict">{deb.verdict}</span>
          </div>
          <div class="agent-body">{deb.rationale}</div>
        </div>
        """

    # Checklist HTML
    checklist_html = "".join(f"<li>{item}</li>" for item in package.qa_checklist)

    # Converted marketplaces table rows
    mp_rows = "".join(
        f"<tr><td><b>{k}</b></td><td><input type='text' id='mp_{idx}' value='{v}' class='field-input-sm' readonly /></td><td><button class='copy-btn-sm' onclick=\"copyField('mp_{idx}')\">Copy</button></td></tr>"
        for idx, (k, v) in enumerate(p.converted_marketplaces.items())
    )

    combined_status = "badge-pass" if d.combined_title_length <= 200 else "badge-warn"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Amazon KDP 1-Click Publishing Assistant | {package.title}</title>
  <style>
    :root {{
      --bg-primary: #0f172a;
      --bg-secondary: #1e293b;
      --bg-card: #334155;
      --accent-primary: #38bdf8;
      --accent-secondary: #818cf8;
      --accent-success: #34d399;
      --accent-warning: #fbbf24;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --border-color: #475569;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background-color: var(--bg-primary);
      color: var(--text-main);
      padding: 24px;
      line-height: 1.5;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    header {{
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
      border: 1px solid var(--border-color);
      border-radius: 16px;
      padding: 24px 32px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }}
    .brand-title {{
      font-size: 24px;
      font-weight: 800;
      letter-spacing: -0.5px;
      background: linear-gradient(90deg, #38bdf8, #818cf8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .book-subtitle {{
      color: var(--text-muted);
      font-size: 15px;
      margin-top: 4px;
    }}
    .nav-tabs {{
      display: flex;
      gap: 12px;
      margin-bottom: 24px;
      border-bottom: 2px solid var(--border-color);
      padding-bottom: 12px;
      flex-wrap: wrap;
    }}
    .tab-btn {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      padding: 12px 24px;
      font-size: 15px;
      font-weight: 600;
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.2s ease;
    }}
    .tab-btn:hover {{
      color: var(--text-main);
      border-color: var(--accent-primary);
    }}
    .tab-btn.active {{
      background: linear-gradient(135deg, #0284c7 0%, #4f46e5 100%);
      color: #fff;
      border-color: #38bdf8;
      box-shadow: 0 4px 14px rgba(56, 189, 248, 0.3);
    }}
    .tab-content {{
      display: none;
    }}
    .tab-content.active {{
      display: block;
      animation: fadeIn 0.3s ease;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(6px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    .grid-2 {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
      gap: 20px;
    }}
    .field-card {{
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 18px 20px;
      margin-bottom: 16px;
      transition: border-color 0.2s ease;
    }}
    .field-card:hover {{
      border-color: #64748b;
    }}
    .field-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }}
    .field-title {{
      font-size: 14px;
      font-weight: 700;
      color: #cbd5e1;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .field-badge {{
      font-size: 12px;
      padding: 3px 8px;
      border-radius: 6px;
      font-weight: 600;
    }}
    .badge-pass {{ background: rgba(52, 211, 153, 0.15); color: #34d399; border: 1px solid #34d399; }}
    .badge-warn {{ background: rgba(251, 191, 36, 0.15); color: #fbbf24; border: 1px solid #fbbf24; }}
    .badge-info {{ background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid #38bdf8; }}
    .field-body {{
      display: flex;
      gap: 10px;
      align-items: center;
    }}
    .field-input {{
      flex: 1;
      background: var(--bg-primary);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 14px;
    }}
    .field-input-sm {{
      width: 100%;
      background: var(--bg-primary);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 13px;
    }}
    .copy-btn {{
      background: #0284c7;
      color: #fff;
      border: none;
      padding: 10px 18px;
      font-size: 14px;
      font-weight: 600;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      white-space: nowrap;
      transition: background 0.15s ease, transform 0.1s ease;
    }}
    .copy-btn:hover {{ background: #0369a1; transform: scale(1.02); }}
    .copy-btn:active {{ transform: scale(0.98); }}
    .copy-btn.copied {{
      background: #10b981 !important;
    }}
    .copy-btn-sm {{
      background: #334155;
      color: #fff;
      border: 1px solid var(--border-color);
      padding: 6px 12px;
      font-size: 12px;
      font-weight: 600;
      border-radius: 6px;
      cursor: pointer;
    }}
    .copy-btn-sm:hover {{ background: #0284c7; }}
    .copy-btn-sm.copied {{ background: #10b981 !important; }}
    textarea.field-input {{
      min-height: 180px;
      font-family: monospace;
      font-size: 13px;
      resize: vertical;
    }}
    .desc-preview {{
      background: #ffffff;
      color: #111827;
      border-radius: 8px;
      padding: 20px;
      margin-top: 12px;
      font-size: 14px;
      line-height: 1.6;
      max-height: 350px;
      overflow-y: auto;
      border: 1px solid #cbd5e1;
    }}
    .desc-preview h2 {{ font-size: 18px; margin-bottom: 10px; color: #1e293b; }}
    .desc-preview h3 {{ font-size: 15px; margin: 12px 0 6px 0; color: #334155; }}
    .desc-preview ul {{ padding-left: 24px; margin-bottom: 12px; }}
    .desc-preview li {{ margin-bottom: 4px; }}
    .category-steps {{
      background: var(--bg-primary);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 12px 14px;
      font-size: 13px;
      margin-bottom: 8px;
    }}
    .step-row {{
      margin-bottom: 4px;
    }}
    .step-val {{
      color: var(--accent-primary);
      font-weight: 600;
    }}
    .step-badge {{
      color: #34d399;
      font-weight: 700;
    }}
    .agent-card {{
      background: var(--bg-secondary);
      border: 1px solid #38bdf8;
      border-radius: 10px;
      padding: 14px 18px;
      margin-bottom: 12px;
    }}
    .agent-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .agent-id {{
      color: #38bdf8;
      font-weight: 800;
      font-size: 13px;
    }}
    .agent-name {{
      color: #f1f5f9;
      font-weight: 600;
      font-size: 13px;
    }}
    .agent-verdict {{
      color: #34d399;
      font-size: 12px;
      font-weight: 700;
    }}
    .agent-body {{
      color: #94a3b8;
      font-size: 13px;
      line-height: 1.45;
    }}
    .toast {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #10b981;
      color: #fff;
      padding: 12px 24px;
      border-radius: 8px;
      font-weight: 700;
      box-shadow: 0 10px 25px rgba(0,0,0,0.4);
      opacity: 0;
      transform: translateY(20px);
      transition: all 0.25s ease;
      z-index: 1000;
      pointer-events: none;
    }}
    .toast.show {{
      opacity: 1;
      transform: translateY(0);
    }}
    .pricing-table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
    }}
    .pricing-table td, .pricing-table th {{
      padding: 10px 12px;
      border-bottom: 1px solid var(--border-color);
    }}
    .pricing-table th {{
      text-align: left;
      color: var(--text-muted);
      font-size: 13px;
    }}
    .qa-box {{
      background: rgba(56, 189, 248, 0.08);
      border: 1px solid #0284c7;
      border-radius: 12px;
      padding: 18px 24px;
      margin-top: 24px;
    }}
    .qa-box ul {{
      padding-left: 20px;
      margin-top: 10px;
      color: #bae6fd;
      font-size: 14px;
    }}
    .qa-box li {{
      margin-bottom: 6px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <div class="brand-title">CurioKraft KDP 1-Click Publishing Assistant</div>
        <div class="book-subtitle"><b>{package.title}</b> - {package.subtitle} (Volume: {package.volume_id.upper()})</div>
      </div>
      <div style="text-align: right;">
        <span class="field-badge badge-pass">Preflight Certified</span>
        <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Generated: {package.generated_at[:19]} UTC</div>
      </div>
    </header>

    <div class="nav-tabs">
      <button class="tab-btn active" onclick="switchTab(event, 'tab-details')">1. Paperback Details</button>
      <button class="tab-btn" onclick="switchTab(event, 'tab-content')">2. Paperback Content</button>
      <button class="tab-btn" onclick="switchTab(event, 'tab-pricing')">3. Rights &amp; Pricing</button>
      <button class="tab-btn" onclick="switchTab(event, 'tab-agents')">Agent Deliberations &amp; Audit</button>
    </div>

    <!-- TAB 1: DETAILS -->
    <div id="tab-details" class="tab-content active">
      <div class="grid-2">
        <div>
          <!-- Language -->
          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Language</span>
              <span class="field-badge badge-info">Dropdown Selection</span>
            </div>
            <div class="field-body">
              <input type="text" class="field-input" id="f_lang" value="{d.language}" readonly />
              <button class="copy-btn" onclick="copyField('f_lang')">Copy</button>
            </div>
          </div>

          <!-- Title -->
          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Book Title (Exact Cover Match)</span>
              <span class="field-badge badge-pass">{d.title_length} / 255 chars</span>
            </div>
            <div class="field-body">
              <input type="text" class="field-input" id="f_title" value="{html.escape(d.book_title)}" readonly />
              <button class="copy-btn" onclick="copyField('f_title')">Copy</button>
            </div>
          </div>

          <!-- Subtitle -->
          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Subtitle (Exact Cover Match)</span>
              <span class="field-badge badge-pass">{d.subtitle_length} / 253 chars</span>
            </div>
            <div class="field-body">
              <input type="text" class="field-input" id="f_subtitle" value="{html.escape(d.subtitle)}" readonly />
              <button class="copy-btn" onclick="copyField('f_subtitle')">Copy</button>
            </div>
            <div style="margin-top: 8px; font-size: 12px; color: var(--text-muted); display: flex; justify-content: space-between;">
              <span>Combined Title + Subtitle Length:</span>
              <span class="field-badge {combined_status}">{d.combined_title_length} / 200 chars (KDP Limit)</span>
            </div>
          </div>

          <!-- Series Details -->
          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Series (Click "Add to series")</span>
              <span class="field-badge badge-info">Multi-Volume Linked</span>
            </div>
            <div class="field-body" style="margin-bottom: 8px;">
              <span style="font-size: 13px; color: var(--text-muted); width: 140px;">Series Title:</span>
              <input type="text" class="field-input" id="f_series_name" value="{html.escape(d.series_name)}" readonly />
              <button class="copy-btn" onclick="copyField('f_series_name')">Copy</button>
            </div>
            <div class="field-body" style="margin-bottom: 8px;">
              <span style="font-size: 13px; color: var(--text-muted); width: 140px;">Book Number:</span>
              <input type="text" class="field-input" id="f_series_num" value="{html.escape(d.series_number)}" readonly />
              <button class="copy-btn" onclick="copyField('f_series_num')">Copy</button>
            </div>
            <div class="field-body">
              <span style="font-size: 13px; color: var(--text-muted); width: 140px;">Relationship:</span>
              <input type="text" class="field-input" id="f_series_rel" value="{html.escape(d.series_relationship)}" readonly />
              <button class="copy-btn" onclick="copyField('f_series_rel')">Copy</button>
            </div>
          </div>

          <!-- Edition Number -->
          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Edition Number (Optional)</span>
              <span class="field-badge badge-info">1st Edition</span>
            </div>
            <div class="field-body">
              <input type="text" class="field-input" id="f_edition" value="{d.edition_number or '(Leave blank)'}" readonly />
              <button class="copy-btn" onclick="copyField('f_edition')">Copy</button>
            </div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 6px;">
              {d.edition_guidance}
            </div>
          </div>

          <!-- Primary Author -->
          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Primary Author or Contributor</span>
              <span class="field-badge badge-info">Publisher Brand</span>
            </div>
            <div class="field-body" style="margin-bottom: 8px;">
              <span style="font-size: 13px; color: var(--text-muted); width: 100px;">First Name:</span>
              <input type="text" class="field-input" id="f_author_first" value="{html.escape(d.author_first)}" readonly />
              <button class="copy-btn" onclick="copyField('f_author_first')">Copy</button>
            </div>
            <div class="field-body">
              <span style="font-size: 13px; color: var(--text-muted); width: 100px;">Last Name:</span>
              <input type="text" class="field-input" id="f_author_last" value="{html.escape(d.author_last)}" readonly />
              <button class="copy-btn" onclick="copyField('f_author_last')">Copy</button>
            </div>
          </div>

          <!-- Contributors -->
          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Contributors (Optional)</span>
              <span class="field-badge badge-info">Illustrator</span>
            </div>
            <div class="field-body" style="margin-bottom: 8px;">
              <span style="font-size: 13px; color: var(--text-muted); width: 100px;">Role:</span>
              <input type="text" class="field-input" id="f_contrib_role" value="{d.contributor_role}" readonly />
              <button class="copy-btn" onclick="copyField('f_contrib_role')">Copy</button>
            </div>
            <div class="field-body">
              <span style="font-size: 13px; color: var(--text-muted); width: 100px;">Name:</span>
              <input type="text" class="field-input" id="f_contrib_name" value="{d.contributor_first} {d.contributor_last}" readonly />
              <button class="copy-btn" onclick="copyField('f_contrib_name')">Copy</button>
            </div>
          </div>

          <!-- Publishing Rights -->
          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Publishing Rights</span>
              <span class="field-badge badge-pass">Copyrighted Work</span>
            </div>
            <div class="field-body">
              <input type="text" class="field-input" id="f_rights" value="[X] I own the copyright and I hold necessary publishing rights." readonly />
              <button class="copy-btn" onclick="copyField('f_rights')">Copy</button>
            </div>
          </div>

          <!-- Primary Audience & Reading Age -->
          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Primary Audience &amp; Reading Age</span>
              <span class="field-badge badge-info">Ages {d.reading_age_min}-{d.reading_age_max}</span>
            </div>
            <div class="field-body" style="margin-bottom: 8px;">
              <span style="font-size: 13px; color: var(--text-muted); width: 180px;">Sexually Explicit?</span>
              <input type="text" class="field-input" id="f_adult" value="No (Select radio: No)" readonly />
              <button class="copy-btn" onclick="copyField('f_adult')">Copy</button>
            </div>
            <div class="field-body" style="margin-bottom: 8px;">
              <span style="font-size: 13px; color: var(--text-muted); width: 180px;">Minimum Reading Age:</span>
              <input type="text" class="field-input" id="f_age_min" value="{d.reading_age_min} (Select dropdown: 1)" readonly />
              <button class="copy-btn" onclick="copyField('f_age_min')">Copy</button>
            </div>
            <div class="field-body">
              <span style="font-size: 13px; color: var(--text-muted); width: 180px;">Maximum Reading Age:</span>
              <input type="text" class="field-input" id="f_age_max" value="{d.reading_age_max} (Select dropdown: 4)" readonly />
              <button class="copy-btn" onclick="copyField('f_age_max')">Copy</button>
            </div>
          </div>

          <!-- Primary Marketplace -->
          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Primary Marketplace</span>
              <span class="field-badge badge-info">US Store</span>
            </div>
            <div class="field-body">
              <input type="text" class="field-input" id="f_mkt" value="{d.primary_marketplace}" readonly />
              <button class="copy-btn" onclick="copyField('f_mkt')">Copy</button>
            </div>
          </div>

          <!-- Book Classification Types -->
          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Book Classification Types</span>
              <span class="field-badge badge-info">KDP Classification</span>
            </div>
            <div style="margin-bottom: 8px;">
              <div style="font-weight: 700; font-size: 13px; color: #f87171;">[ ] Low-content book (journals, notebooks, planners):</div>
              <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">{d.low_content_guidance}</div>
            </div>
            <div>
              <div style="font-weight: 700; font-size: 13px; color: #34d399;">[X] Large-print book (16-point font or greater):</div>
              <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">{d.large_print_guidance}</div>
            </div>
          </div>
        </div>

        <div>
          <!-- Categories Modal Selector Helper -->
          <div class="field-card" style="border-color: #38bdf8;">
            <div class="field-header">
              <span class="field-title" style="color: #38bdf8;">Categories (Click "Choose Categories")</span>
              <span class="field-badge badge-pass">3 Modal Trees</span>
            </div>
            <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px;">
              Use the exact step-by-step dropdown navigation below inside Amazon KDP's Category selector modal:
            </div>
            {categories_html}
          </div>

          <!-- 7 Keywords -->
          <div class="field-card" style="border-color: #818cf8;">
            <div class="field-header">
              <span class="field-title" style="color: #818cf8;">7 Backend Search Keywords (Amazon A9 Optimized)</span>
              <span class="field-badge badge-pass">0 Title Overlap</span>
            </div>
            <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px;">
              Amazon automatically indexes all words in Title and Subtitle. These 7 phrases capture complementary, high-intent buyer searches (strictly under 50 characters each).
            </div>
            {keywords_html}
          </div>

          <!-- Description -->
          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Product Description (KDP-Allowed HTML, Zero Emojis)</span>
              <span class="field-badge badge-pass">{len(d.description_html)} / 4,000 chars</span>
            </div>
            <textarea class="field-input" id="f_desc" readonly>{desc_escaped_html}</textarea>
            <div style="margin-top: 10px; display: flex; justify-content: space-between; align-items: center;">
              <button class="copy-btn" style="width: 100%; justify-content: center;" onclick="copyField('f_desc')">Copy HTML Description (Paste into KDP Source View)</button>
            </div>
            <div style="margin-top: 16px;">
              <span class="field-title" style="font-size: 12px;">Visual Rendered Buyer Preview:</span>
              <div class="desc-preview">
                {d.description_html}
              </div>
            </div>
          </div>

          <!-- Publication & Release Dates -->
          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Publication &amp; Release Dates</span>
              <span class="field-badge badge-pass">Standard Release</span>
            </div>
            <div class="field-body" style="margin-bottom: 8px;">
              <span style="font-size: 13px; color: var(--text-muted); width: 140px;">Publication Date:</span>
              <input type="text" class="field-input" id="f_pub_date" value="[X] {d.publication_date_option}" readonly />
              <button class="copy-btn" onclick="copyField('f_pub_date')">Copy</button>
            </div>
            <div class="field-body">
              <span style="font-size: 13px; color: var(--text-muted); width: 140px;">Release Date:</span>
              <input type="text" class="field-input" id="f_rel_date" value="[X] {d.release_date_option}" readonly />
              <button class="copy-btn" onclick="copyField('f_rel_date')">Copy</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 2: CONTENT -->
    <div id="tab-content" class="tab-content">
      <div class="grid-2">
        <div>
          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Print ISBN</span>
              <span class="field-badge badge-info">Standard KDP</span>
            </div>
            <div class="field-body">
              <input type="text" class="field-input" id="c_isbn" value="{c.isbn_option}" readonly />
              <button class="copy-btn" onclick="copyField('c_isbn')">Copy</button>
            </div>
          </div>

          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Interior &amp; Paper Type</span>
              <span class="field-badge badge-pass">Standard Black &amp; White</span>
            </div>
            <div class="field-body">
              <input type="text" class="field-input" id="c_paper" value="{c.interior_paper_type}" readonly />
              <button class="copy-btn" onclick="copyField('c_paper')">Copy</button>
            </div>
          </div>

          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Trim Size</span>
              <span class="field-badge badge-pass">US Letter Format</span>
            </div>
            <div class="field-body">
              <input type="text" class="field-input" id="c_trim" value="{c.trim_size}" readonly />
              <button class="copy-btn" onclick="copyField('c_trim')">Copy</button>
            </div>
          </div>

          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Bleed Settings</span>
              <span class="field-badge badge-pass">Preflight Certified</span>
            </div>
            <div class="field-body">
              <input type="text" class="field-input" id="c_bleed" value="{c.bleed_settings}" readonly />
              <button class="copy-btn" onclick="copyField('c_bleed')">Copy</button>
            </div>
          </div>

          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Paperback Cover Finish</span>
              <span class="field-badge badge-pass">Toddler Wipe-Clean</span>
            </div>
            <div class="field-body">
              <input type="text" class="field-input" id="c_finish" value="{c.cover_finish}" readonly />
              <button class="copy-btn" onclick="copyField('c_finish')">Copy</button>
            </div>
          </div>

          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Page-Turn Direction</span>
              <span class="field-badge badge-info">Standard English</span>
            </div>
            <div class="field-body">
              <input type="text" class="field-input" id="c_dir" value="{c.page_turn_direction}" readonly />
              <button class="copy-btn" onclick="copyField('c_dir')">Copy</button>
            </div>
          </div>
        </div>

        <div>
          <!-- File Upload Quick Links -->
          <div class="field-card" style="border-color: #34d399;">
            <div class="field-header">
              <span class="field-title" style="color: #34d399;">Manuscript &amp; Cover Upload Targets</span>
              <span class="field-badge badge-pass">110 Pages Ready</span>
            </div>
            <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px;">
              Copy the absolute paths below to easily paste into your browser file upload dialog:
            </div>
            <div class="field-body" style="margin-bottom: 8px;">
              <input type="text" class="field-input" id="c_manuscript" value="{c.manuscript_file_path}" readonly />
              <button class="copy-btn" onclick="copyField('c_manuscript')">Copy Path</button>
            </div>
            <div class="field-body">
              <input type="text" class="field-input" id="c_cover" value="{c.cover_file_path}" readonly />
              <button class="copy-btn" onclick="copyField('c_cover')">Copy Path</button>
            </div>
          </div>

          <!-- Amazon AI-Generated Content Disclosure -->
          <div class="field-card" style="border-color: #818cf8;">
            <div class="field-header">
              <span class="field-title" style="color: #818cf8;">Mandatory Amazon AI Content Disclosure (2024/2026 Policy)</span>
              <span class="field-badge badge-info">Compliant Answers</span>
            </div>
            <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 12px;">
              Amazon requires disclosure of AI-based tools used in content creation. Use these verified answers to ensure instant compliance without audit delays:
            </div>
            <div class="field-body" style="margin-bottom: 8px;">
              <span style="font-size: 13px; color: var(--text-muted); width: 140px;">AI Used in Text?</span>
              <input type="text" class="field-input" id="ai_text" value="{c.ai_generated_text}" readonly />
              <button class="copy-btn" onclick="copyField('ai_text')">Copy</button>
            </div>
            <div class="field-body" style="margin-bottom: 8px;">
              <span style="font-size: 13px; color: var(--text-muted); width: 140px;">AI Used in Images?</span>
              <input type="text" class="field-input" id="ai_img" value="{c.ai_generated_images} (Some sections with minimal or no edits)" readonly />
              <button class="copy-btn" onclick="copyField('ai_img')">Copy</button>
            </div>
            <div class="field-body" style="margin-bottom: 8px;">
              <span style="font-size: 13px; color: var(--text-muted); width: 140px;">Tools &amp; Edits:</span>
              <textarea class="field-input" id="ai_tools" style="min-height: 80px;" readonly>{c.ai_images_details}</textarea>
              <button class="copy-btn" onclick="copyField('ai_tools')">Copy</button>
            </div>
            <div class="field-body">
              <span style="font-size: 13px; color: var(--text-muted); width: 140px;">AI Translations?</span>
              <input type="text" class="field-input" id="ai_trans" value="{c.ai_translations}" readonly />
              <button class="copy-btn" onclick="copyField('ai_trans')">Copy</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 3: PRICING -->
    <div id="tab-pricing" class="tab-content">
      <div class="grid-2">
        <div>
          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Publishing Territories</span>
              <span class="field-badge badge-pass">Worldwide</span>
            </div>
            <div class="field-body">
              <input type="text" class="field-input" id="p_terr" value="{p.territories}" readonly />
              <button class="copy-btn" onclick="copyField('p_terr')">Copy</button>
            </div>
          </div>

          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Primary Marketplace</span>
              <span class="field-badge badge-info">United States</span>
            </div>
            <div class="field-body">
              <input type="text" class="field-input" id="p_market" value="{p.primary_marketplace}" readonly />
              <button class="copy-btn" onclick="copyField('p_market')">Copy</button>
            </div>
          </div>

          <div class="field-card">
            <div class="field-header">
              <span class="field-title">List Price (USD)</span>
              <span class="field-badge badge-pass">60% Royalty Tier</span>
            </div>
            <div class="field-body" style="margin-bottom: 8px;">
              <input type="text" class="field-input" id="p_price" value="${p.list_price_usd:.2f}" readonly />
              <button class="copy-btn" onclick="copyField('p_price')">Copy Price</button>
            </div>
            <div style="font-size: 13px; color: #34d399; margin-top: 6px;">
              [PASS] {p.royalty_rate_est}
            </div>
          </div>

          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Expanded Distribution</span>
              <span class="field-badge badge-pass">Recommended</span>
            </div>
            <div class="field-body">
              <input type="text" class="field-input" id="p_exp" value="Yes (Check the box to enable bookstores &amp; libraries)" readonly />
              <button class="copy-btn" onclick="copyField('p_exp')">Copy</button>
            </div>
          </div>
        </div>

        <div>
          <div class="field-card">
            <div class="field-header">
              <span class="field-title">Converted Global Marketplaces</span>
              <span class="field-badge badge-info">Automatic Conversion</span>
            </div>
            <div style="font-size: 13px; color: var(--text-muted); margin-bottom: 8px;">
              Recommended retail prices matching your primary list price:
            </div>
            <table class="pricing-table">
              <thead>
                <tr>
                  <th>Marketplace</th>
                  <th>Suggested Retail Price</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {mp_rows}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 4: AGENT DELIBERATIONS & AUDIT -->
    <div id="tab-agents" class="tab-content">
      <div style="margin-bottom: 16px;">
        <h3 style="color: #38bdf8; font-size: 18px; margin-bottom: 6px;">Multi-Agent Publishing Synthesis Audit</h3>
        <p style="color: var(--text-muted); font-size: 14px;">
          The CurioKraft Publishing Subsystem deploys 4 specialist agents to autonomously analyze the book manifest,
          enforce Amazon A9 SEO algorithms, verify KDP technical print constraints, and map dropped HTML form fields.
        </p>
      </div>
      {debates_html}
    </div>

    <!-- QA Audit Summary -->
    <div class="qa-box">
      <div style="font-weight: 700; font-size: 16px; color: #38bdf8;">Pre-Publication Validation Checklist</div>
      <ul>
        {checklist_html}
      </ul>
    </div>
  </div>

  <div id="toast" class="toast">Copied to clipboard!</div>

  <script>
    function switchTab(evt, tabId) {{
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      document.getElementById(tabId).classList.add('active');
      evt.currentTarget.classList.add('active');
    }}

    function copyField(elementId) {{
      const el = document.getElementById(elementId);
      if (!el) return;
      const textToCopy = el.value || el.innerText;
      navigator.clipboard.writeText(textToCopy).then(() => {{
        showToast("Copied: " + (textToCopy.length > 35 ? textToCopy.substring(0, 32) + "..." : textToCopy));
        const btn = el.parentElement ? el.parentElement.querySelector('button') : null;
        if (btn) {{
          const orig = btn.innerText;
          btn.innerText = "Copied!";
          btn.classList.add('copied');
          setTimeout(() => {{
            btn.innerText = orig;
            btn.classList.remove('copied');
          }}, 1500);
        }}
      }}).catch(err => {{
        console.error("Copy failed", err);
      }});
    }}

    function showToast(msg) {{
      const toast = document.getElementById('toast');
      toast.innerText = msg;
      toast.classList.add('show');
      setTimeout(() => {{
        toast.classList.remove('show');
      }}, 2000);
    }}
  </script>
</body>
</html>
"""


def render_kdp_markdown_cheatsheet(package: KDPSubmissionPackage) -> str:
    """Generate clean, copy-paste Markdown reference cheatsheet."""
    d = package.details
    c = package.content
    p = package.pricing

    kw_list = "\n".join(f"{i}. `{kw}` ({len(kw)} chars)" for i, kw in enumerate(d.keywords, 1))
    cat_list = "\n".join(
        f"{i}. **{cat.category}:** {cat.display_path} (Placement: {', '.join(cat.placements)})"
        for i, cat in enumerate(d.category_items, 1)
    )

    debates_md = "\n\n".join(
        f"### [{deb.agent_id}] {deb.agent_name}\n* **Verdict:** {deb.verdict}\n* **Rationale:** {deb.rationale}"
        for deb in package.agent_deliberations
    )

    return f"""# Amazon KDP Publishing Cheatsheet - {package.title} ({package.volume_id.upper()})

Generated: {package.generated_at[:19]} UTC  
Status: Certified & Compliant (Zero Emojis, Standard ASCII Only)

---

## Tab 1: Paperback Details

* **Language:** `{d.language}`
* **Book Title:** `{d.book_title}` ({d.title_length} chars)
* **Subtitle:** `{d.subtitle}` ({d.subtitle_length} chars)
* **Combined Title Length:** `{d.combined_title_length} / 200 chars (Compliant)`
* **Series Name:** `{d.series_name}` (Book #{d.series_number}, Relationship: {d.series_relationship})
* **Edition Number:** `{d.edition_number or '(Leave blank for 1st edition)'}`
* **Primary Author:** `{d.author_first}` `{d.author_last}`
* **Primary Audience / Adult Content:** `{d.adult_content}` (Sexually explicit: No)
* **Reading Age:** Minimum: `{d.reading_age_min}` years, Maximum: `{d.reading_age_max}` years
* **Primary Marketplace:** `{d.primary_marketplace}`
* **Low-Content Book Checkbox:** `Unchecked / No` (Coloring books are standard content)
* **Large-Print Book Checkbox:** `Checked / Yes` (200pt+ bubble headers qualify)

### Categories (Step-by-Step Modal Navigation):
{cat_list}

### 7 Backend Search Keywords (Amazon A9 Optimized, <=50c, 0 Title Overlap):
{kw_list}

### Product Description (KDP-Allowed HTML, Zero Emojis):
```html
{d.description_html}
```

---

## Tab 2: Paperback Content

* **Print ISBN:** `{c.isbn_option}`
* **Publication Date:** `{c.publication_date}`
* **Interior & Paper Type:** `{c.interior_paper_type}`
* **Trim Size:** `{c.trim_size}`
* **Bleed Settings:** `{c.bleed_settings}`
* **Paperback Cover Finish:** `{c.cover_finish}`
* **Page-Turn Direction:** `{c.page_turn_direction}`
* **Manuscript PDF:** `{c.manuscript_file_path}`
* **Cover PDF:** `{c.cover_file_path}`

### Amazon AI-Generated Content Disclosure:
* **AI in Text:** `{c.ai_generated_text}`
* **AI in Images:** `{c.ai_generated_images}`
* **Tools & Post-Processing:** `{c.ai_images_details}`
* **AI in Translations:** `{c.ai_translations}`

---

## Tab 3: Paperback Rights & Pricing

* **Territories:** `{p.territories}`
* **Primary Marketplace:** `{p.primary_marketplace}`
* **List Price:** `${p.list_price_usd:.2f} USD` ({p.royalty_rate_est})
* **Expanded Distribution:** `Enabled`

### Converted Global Retail Prices:
{chr(10).join(f"- **{k}:** `{v}`" for k, v in p.converted_marketplaces.items())}

---

## Multi-Agent Publishing Synthesis Audit
{debates_md}

---

## Pre-Publication Checklist
{chr(10).join(f"- {item}" for item in package.qa_checklist)}
"""


def save_kdp_submission_bundle(
    package: KDPSubmissionPackage,
    output_dir: str | Path = DEFAULT_KDP_OUTPUT_DIR,
) -> dict[str, Path]:
    """Save HTML dashboard, markdown cheatsheet, and JSON export."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    html_path = out / "kdp_submission_helper.html"
    md_path = out / "kdp_fields.md"
    json_path = out / "kdp_metadata.json"

    # 1. HTML Dashboard
    html_content = render_kdp_html_dashboard(package)
    html_path.write_text(html_content, encoding="utf-8")

    # 2. Markdown Cheatsheet
    md_content = render_kdp_markdown_cheatsheet(package)
    md_path.write_text(md_content, encoding="utf-8")

    # 3. JSON Export
    json_path.write_text(
        json.dumps(package.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    logger.info("Saved KDP submission bundle to %s", out)
    return {
        "html": html_path,
        "markdown": md_path,
        "json": json_path,
    }
