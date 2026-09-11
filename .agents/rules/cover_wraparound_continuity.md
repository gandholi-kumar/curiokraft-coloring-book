---
description: Mandatory rules for full-wrap cover background continuity, spine wraparound seamlessness, and anti-drift layout rules across CurioKraft covers.
globs: ["**/cover*", "**/prompts*", "**/agents.yaml", "**/debate_engine.py"]
---

# CurioKraft Full-Wrap Cover Wraparound Continuity & Anti-Drift Standard

## 1. Core Mandate
Every agent constructing, reviewing, debating, or generating prompts for book covers in CurioKraft publications MUST ensure that the Front Cover and Back Cover form a **single, continuous, visually unified wraparound artwork** when bound around the spine of the paperback.

## 2. Inviolable Laws of Cover Wraparound Continuity

### A. Spine Fold Orientation & Seamless Continuation
1. **Front Cover LEFT Edge = Spine Fold**:
   - The left edge of the front cover directly abuts the book spine.
   - The entire left edge MUST be **100% clean, borderless, and horizontally flat**.
   - Strictly NO corner frames, NO scalloped vignettes, and NO vertical border bands on the left edge.
2. **Back Cover RIGHT Edge = Spine Fold**:
   - The right edge of the back cover directly abuts the book spine.
   - The entire right edge MUST be **100% clean, borderless, and horizontally flat**.
   - Strictly NO corner frames, NO scalloped vignettes, and NO vertical border bands on the right edge.
3. **Outer Perimeter Only Framing**:
   - Decorative corner frames (scalloped waves in pastel turquoise/mint/yellow) are permitted **strictly on the outer perimeter**:
     - Back Cover: Top-left and bottom-left outer corners only.
     - Front Cover: Top-right and bottom-right outer corners only.

### B. Synchronized Canvas & Horizon Baseline
1. **Unified Background Canvas**:
   - Both Front Cover and Back Cover must share the EXACT SAME primary background: cheerful warm butter-cream / soft sunny pale yellow canvas (`#FFF9E6`).
2. **Synchronized Lower Baseline / Rolling Waves**:
   - Any ground wave, rolling hill, or pastel turquoise curve in the lower canvas must maintain the exact same horizontal height (lower 15–20% of canvas) across both covers.
   - Wavy elements must NOT angle sharply into the spine as diagonal rivers; they must transition gently and horizontally across the spine boundary so they align seamlessly when bound.
3. **Harmonized Atmospheric Sprinkles**:
   - Both covers must share the identical distribution of floating celebratory star dust: 4-point and 5-point twinkling stars in golden yellow, orange, and blue; soft pastel floating love hearts in pink and lilac; and tiny confetti sparkles.

### C. Zero AI Logo Placeholder Boxes (Programmatic Compositing Only)
1. **No AI White Badges or Cutouts**:
   - Back cover prompts MUST NOT instruct the AI generator to draw any white card, white rectangle, badge, cutout, or placeholder for the brand logo or barcode.
   - The AI image generator must produce an **unbroken, continuous pastel background** across the entire bottom-left and bottom-right.
2. **Programmatic White Brand Badge with Box Shadow**:
   - The CurioKraft brand logo container is rendered programmatically by the compositor (`cover.py`).
   - The container is an elevated, prominent white rounded card (`640 x 420 px @ 300 DPI`) with a soft drop shadow on the bottom and right sides.
   - The authentic brand logo (`curiokraft_logo.PNG`) is stamped inside, preserving authentic proportions, scaled large for maximum clarity.
   - The white background guarantees that dark/colored background cover inks will NEVER spill or bleed into the brand logo during commercial Amazon KDP printing.
3. **Programmatic Barcode Box**:
   - The 700 x 430 px barcode box in the bottom-right is also rendered programmatically by code. Prompts must enforce strict negative tokens against AI-generated fake barcodes or white boxes.

## 3. Frozen Geometric Specifications for Programmatic Stamping

### A. Publisher Brand Badge Container (Frozen for all future volumes)
* **Location**: Back cover, bottom-left safe region.
* **Canvas Coordinates (@ 300 DPI, 5249 x 3375 px canvas)**:
  - `x1`: `180 px` (`0.60 in` from canvas left margin)
  - `y1`: `2860 px` (`9.533 in` from canvas top margin)
  - `x2`: `820 px` (`2.733 in` from canvas left margin)
  - `y2`: `3280 px` (`10.933 in` from canvas top margin)
  - **Card Width**: `640 px` (`2.133 in`)
  - **Card Height**: `420 px` (`1.40 in`)
  - **Corner Radius**: `28 px`
* **Vertical Symmetry**: The card baseline (`y2 = 3280 px`) matches the Amazon Barcode box baseline (`y2 = 3280 px`) across the bottom edge.
* **Box Shadow**:
  - Offset X: `+16 px` (right)
  - Offset Y: `+20 px` (bottom)
  - Blur Radius: `20 px` Gaussian blur
  - Mask Alpha: `95 / 255`
* **Card Surface**: Solid pure white (`#FFFFFF`) with subtle border `rgb(230, 233, 238)` to eliminate color spill from cover art during physical printing.

### B. Barcode Exclusion Zone (Frozen Amazon KDP Standard)
* **Location**: Back cover, bottom-right safe region.
* **Canvas Coordinates (@ 300 DPI)**:
  - `x1`: `1845 px`
  - `y1`: `2850 px`
  - `x2`: `2545 px`
  - `y2`: `3280 px`
  - **Width**: `700 px`
  - **Height**: `430 px`
* **Surface**: Solid pure white (`#FFFFFF`).

### C. Inviolable Multi-Volume Zero-Text Mandate & Permitted Continuous Assets
Across **all current and future volumes** (Vol 1, Vol 2, Vol 3+):
1. **Zero-Text Mandate in Logo Badge & Barcode Zones**:
   - Strictly **NO text message, words, letters, numbers, titles, blurbs, fake ISBNs, copyright notes, or technical labels** may be printed or generated in either the Publisher Brand Badge Zone (`x1: 180, y1: 2860, x2: 820, y2: 3280`) or the Barcode Exclusion Zone (`x1: 1845, y1: 2850, x2: 2545, y2: 3280`).
   - Neither the AI diffusion generator nor the programmatic compositor may place arbitrary typography into these two bottom zones.
2. **Permitted & Required Continuous Background Assets**:
   - The underlying illustration MUST NOT leave empty white holes or cutout blanks in these positions.
   - Background assets — specifically the warm butter-cream canvas (`#FFF9E6`), the gentle rolling pastel turquoise/mint waves, golden/blue star dust, soft floating hearts, and playful toddler doodles — **ARE explicitly permitted and MUST flow continuously and seamlessly across the entire bottom region**.
   - The Publisher Brand Logo Badge (with its white card surface and soft drop shadow) and the Barcode Box (clean white solid fill) will be programmatically stamped on top of this rich, continuous background art during final compositing.

### D. Double-Sided Printing Reality Mandate
1. **Double-Sided Book Manufacturing**:
   - CurioKraft publications are printed **double-sided** on white paper (all 110 pages are front-and-back toddler coloring pages, comprising 55 physical leaves).
   - Strictly **NO agent, prompt, or cover copy** may claim the book contains "single-sided pages", "single sided anti-bleed pages", "blank backs", or similar misstatements.
   - Parent-facing marketing bullets, callout pills, and descriptions must truthfully emphasize double-sided coloring value (e.g. *"110 Full Pages of Double-Sided Coloring Fun"*, *"100+ Big Preschool Drawings"*, *"Builds Early Vocabulary & Fine Motor Skills"*).

### E. Zero Prompt Jargon in Customer-Facing Copy
1. **Prohibition of Developer Prompt Jargon**:
   - Customer-facing cover text, callout note pills, and description copy must NEVER expose internal diffusion prompt-engineering directives.
   - Words and phrases such as `"thick 5pt bold outlines"`, `"5pt stroke"`, `"vector line art"`, `"binary line art"`, or `"prompt engineering"` are strictly forbidden in visible text.
   - Use toddler-friendly parent benefits: *"Chunky Easy Outlines for Little Hands"*, *"Big & Simple Toddler Shapes"*, *"Develops Pencil Grip & Fine Motor Skills"*, *"Ages 1 to 4"*.

### F. Dynamic Manifest Card Sampling & Distinct Volume Layouts
1. **Dynamic Manifest Sampling**:
   - Back cover preview cards must NEVER be hardcoded in Python code.
   - For every volume, cards must be dynamically extracted from the active manifest (`manifest/pages.json`, `manifest/pages_vol2.json`, etc.), selecting 3 diverse objects representing distinct categories:
     - 1 Food or Fruit item
     - 1 Living Animal or Character item
     - 1 Vehicle, Tool, or Everyday Living item
2. **Distinct Layout Placements Across Volumes**:
   - To avoid visual monotony, different volumes should feature distinct placements and arrangements of notes, cards, and decorative banners.

### G. User Layout Blueprint Honor Protocol
1. **User-Provided Blueprint Detection**:
   - When a user drops a layout blueprint (image wireframe/mockup or YAML spec) into `inbox/blueprints/`, the multi-agent system must inspect the blueprint via multimodal vision or schema parsing.
2. **Layout Geometry Preservation**:
   - Agents must map the active manifest's objects and marketing copy into the layout slots specified by the user's blueprint (header style, card rows/columns, callout pill grid, wave baseline height).
   - The user's blueprint overrides default layout heuristics while strictly obeying safety margins, double-sided printing reality, and exclusion zone mandates.

</content>
