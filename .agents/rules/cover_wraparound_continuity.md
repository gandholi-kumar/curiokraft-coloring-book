---
description: Mandatory rules for full-wrap cover background continuity, spine wraparound seamlessness, and anti-drift layout rules across CurioKraft covers.
globs: ["**/cover*", "**/prompts*", "**/agents.yaml", "**/debate_engine.py"]
---

# CurioKraft Full-Wrap Cover Wraparound Continuity & Anti-Drift Standard

## 1. Core Mandate
Every agent constructing, reviewing, debating, or generating prompts for book covers in CurioKraft publications MUST ensure that the Front Cover and Back Cover form a **single, continuous, visually unified wraparound artwork** when bound around the spine of the paperback. The visual styling, color palette, ground horizon, and atmospheric embellishments must be dynamically derived from the active **Cover Theme** (`ocean`, `land`, `sky`, `geometric_mandala`, `toddler`).

## 2. Inviolable Laws of Cover Wraparound Continuity

### A. Spine Fold Orientation, Seamless Continuation & Zero Crease Priming
1. **Front Cover LEFT Edge = Spine Fold**:
   - The left edge of the front cover directly abuts the book spine.
   - The entire left edge MUST be **100% clean, borderless, and horizontally flat**.
   - Strictly NO corner frames, NO scalloped vignettes, and NO vertical border bands on the left edge.
   - **Zero Spine Crease / Mockup Shadow**: Prompt and image generators must NEVER include dark vertical shading, spine crease lines, faux book fold marks, or 3D product mockup shadows along the spine margin.
2. **Back Cover RIGHT Edge = Spine Fold**:
   - The right edge of the back cover directly abuts the book spine.
   - The entire right edge MUST be **100% clean, borderless, and horizontally flat**.
   - Strictly NO corner frames, NO scalloped vignettes, and NO vertical border bands on the right edge.
3. **Full-Bleed Borderless Edge-to-Edge Artwork**:
   - Both Front Cover and Back Cover MUST be **100% full-bleed edge-to-edge illustrations** across all four borders.
   - Strictly NO corner frames, NO scalloped vignettes, NO corner flourishes, and NO vertical margin/crease lines on either cover.
4. **Anti-Measurement Dimension Elimination (Zero CAD/Ruler Priming)**:
   - POSITIVE cover prompts must NEVER contain physical dimensions, units, or measurement terminology (e.g. `"1.0 inch"`, `"300px"`, `"safe live area"`, `"ruler marks"`). Such words prime diffusion models to render literal CAD dimension lines, measurement arrows, and ruler labels.
   - ALWAYS use relative compositional percentages (e.g. `"Leave generous 20% open ocean expanse at the top third for typography, and 12% calm seabed at bottom for publisher marks"`).
   - All cover prompts must enforce negative tokens: `dimension arrows, measurement lines, ruler marks, guidelines, blueprint lines, framing lines, border margins, corner brackets, inner frames, double borders`.

### B. Synchronized Multi-Biome Canvas & Horizon Baseline
1. **Unified Background Canvas**:
   - Both Front Cover and Back Cover must share the EXACT SAME primary background color tone and lighting defined by the theme in `config/taxonomy.yaml` (e.g., soft azure and seafoam `#E6F7FF` for ocean; cheerful warm butter-cream `#FFF9E6` for toddler; sunny meadow green for land; airy sky blue for sky).
2. **Synchronized Lower Baseline / Horizon Geometry**:
   - The ground plane or horizon (e.g., lower 15–20% of canvas) must maintain the exact same horizontal height across both covers.
   - For Ocean: Gentle rolling ocean floor / coral reef bed.
   - For Land: Gentle rolling grass meadow hills.
   - For Sky: Gentle horizontal cloud fluff bank.
   - For Toddler: Gentle rolling pastel turquoise/mint wave crests.
   - Ground elements must NOT angle sharply into the spine; they must transition gently and horizontally across the spine boundary so they align seamlessly when bound.
3. **Harmonized Atmospheric Sprinkles**:
   - Both covers must share the identical distribution of theme-specific atmospheric elements:
     - Ocean: Floating translucent bubbles, tiny starfish sparkles, gentle light caustics.
     - Land: Floating dandelion puffs, golden butterfly specks, warm sun sparkles.
     - Sky: Twinkling star dust, soft cloud puffs, gentle sunbeam glints.
     - Toddler: 4-point and 5-point golden stars, pastel love hearts, confetti sparkles.

### C. Zero AI Logo / Barcode Mention (Programmatic Compositing Only)
1. **Zero-Mention Mandate in Positive Prompts**:
   - POSITIVE cover prompts must strictly **NEVER mention the words barcode, ISBN, publisher badge, or logo**. Even cautionary phrasing ("space reserved for barcode") causes diffusion models to hallucinate fake barcodes and white boxes.
   - The positive prompt must describe the footer (lower 20%) purely as a rich, unbroken, continuous theme background illustration and overlay scenery (e.g., coral reef bed, sand waves, bubbles, kelp fronds) flowing from edge to edge.
2. **Strict Negative Token Exclusion**:
   - Prompts must strictly exclude barcode and logo artifacts via the negative prompt:
     `barcode, barcode box, fake barcode, isbn, barcode placeholder, qr code, publisher logo, logo badge, white rectangle, white box, sticker, label`.
3. **Programmatic Stamping**:
   - The CurioKraft brand logo container and Amazon KDP barcode are programmatically composited by the Python compositor (`cover.py`) post-generation. The AI art must remain 100% continuous behind them.

## 3. Frozen Geometric Specifications for Programmatic Stamping

### A. Publisher Brand Badge Container (Frozen for all volumes)
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

### C. Continuous Background Artwork Flow Across Bottom Zones
Across **all current and future volumes**:
1. **Zero-Text Mandate in Logo Badge & Barcode Zones**:
   - Strictly **NO text message, words, letters, numbers, titles, blurbs, fake ISBNs, copyright notes, or technical labels** may be printed or generated in either the Publisher Brand Badge Zone or the Barcode Exclusion Zone.
2. **Required Continuous Background Flow**:
   - The underlying illustration MUST NOT leave empty white holes or cutout blanks in these positions.
   - The theme background artwork (e.g. coral reef bed, sand waves, bubbles, meadow grass, or pastel waves) **MUST flow continuously and seamlessly across the entire bottom region**.
   - The Publisher Brand Logo Badge and Barcode Box will be programmatically composited on top of this continuous background.

### D. Printing Reality Synchronization (Single-Sided vs Double-Sided)
1. **Manifest-Accurate Printing Specification**:
   - Agents and cover copy generators must inspect the active book configuration and manifest structure:
     - **Single-Sided Books (e.g. Aquatic Series with blank/bleed guard reverse pages)**: Marketing bullets, callout pills, and back cover descriptions must emphasize single-sided anti-bleed benefits:
       - *"Single-Sided Pages to Prevent Bleed-Through"*
       - *"Blank Reverse Pages for Clean Coloring"*
       - *"Safe for Crayons, Colored Pencils, Markers & Watercolors"*
     - **Double-Sided Books (e.g. Toddler Vol 1)**: Marketing bullets must emphasize double-sided volume:
       - *"100+ Full Pages of Double-Sided Coloring Fun"*
       - *"Big & Simple Toddler Shapes"*
   - Strictly **NO contradictory claims**: Single-sided books must never claim double-sided printing, and double-sided books must never claim single-sided printing.

### E. Zero Prompt Jargon in Customer-Facing Copy
1. **Prohibition of Developer Prompt Jargon**:
   - Customer-facing cover text, callout pills, and description copy must NEVER expose internal diffusion prompt-engineering directives.
   - Words and phrases such as `"thick 5pt bold outlines"`, `"5pt stroke"`, `"vector line art"`, `"binary line art"`, or `"prompt engineering"` are strictly forbidden in visible text.
   - Use engaging parent and child benefits matched to the series theme.

### F. Dynamic Manifest Section Sampling for Showcase Cards
1. **Dynamic Manifest Sampling**:
   - Back cover preview cards must NEVER be hardcoded to static object names.
   - Cards must be dynamically sampled from the actual sections present in the active manifest (`manifest/pages_aquatic_vol1.json`, `data/pages.json`, etc.).
   - Card illustrations must match the active theme and manifest objects.

### G. User Layout Blueprint Honor Protocol
1. **User-Provided Blueprint Detection**:
   - When a user drops a layout blueprint into `inbox/blueprints/`, the multi-agent system inspects the blueprint.
   - Agents map the active manifest's objects and marketing copy into the layout slots specified by the user's blueprint while strictly obeying safety margins and exclusion zone mandates.


</content>
