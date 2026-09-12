# Amazon KDP HTML Forms Drop Folder (`inbox/kdp_forms/`)

This directory is the designated drop-in landing zone for saved Amazon KDP web forms.

## How to Use:
1. When creating or editing a paperback on [Amazon KDP](https://kdp.amazon.com):
   - You can save any of the 3 web page screens directly from your browser (`Ctrl + S` -> "Webpage, HTML Only" or "Webpage, Complete"):
     - **Tab 1:** `tab1_details.html` (Paperback Details)
     - **Tab 2:** `tab2_content.html` (Paperback Content)
     - **Tab 3:** `tab3_pricing.html` (Paperback Rights & Pricing)
     *(Or any single `.html` / `.htm` file).*
2. Drop the `.html` file(s) into this directory.
3. Run:
   ```powershell
   curiokraft-book kdp generate
   ```
4. The engine will:
   - Run **AGT-KDP-004 (Form Parser & Ingestion Agent)** to map all 82 form inputs, textareas, character limits, dropdowns, and checkboxes across the 3 tabs.
   - Run **AGT-KDP-001 (SEO)**, **AGT-KDP-002 (Copywriter)**, and **AGT-KDP-003 (Compliance)** to synthesize 100% compliant publishing metadata.
   - Enforce Amazon's **Zero Emojis & Standard Characters** rule (preventing `"Emoji characters are not supported. Please use standard characters only."` submission rejection).
   - Generate and open your **Interactive 1-Click Copy-to-Clipboard Dashboard** (`output/kdp/kdp_submission_helper.html`) featuring a 4th tab with full agent deliberation logs.

> [!NOTE]
> Dropping an HTML file here is **completely optional**! If this folder is empty, the engine automatically uses its built-in Amazon KDP full schema and generates 100% of all required publishing fields for your active volume.

---

## 📚 Complete Reference:
For full publishing details, A9 keyword deduplication rules, Category Modal navigation trees, and classification checkbox guidance, see:
- [Amazon KDP Publishing & Metadata Guide](../../docs/KDP_PUBLISHING_METADATA_GUIDE.md)
