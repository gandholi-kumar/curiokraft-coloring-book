---
name: cover-prompt-crafting
description: Authoritative skill and procedural guide for synthesizing, debating, and validating Amazon KDP Front Cover and Back Cover prompts across all CurioKraft book series. Enforces full-bleed borderless composition, zero-dimension measurement rules, 3D sculpted typography, value-driven parent marketing copy, and seamless continuous background scenery.
---

# CurioKraft Cover Prompt Crafting Skill

## 1. Overview & Architectural Principles

The CurioKraft cover pipeline is **100% configuration- and theme-driven**. Application code contains **zero hardcoded series names, color codes, or static copy**. Instead:
1. All cover themes (`ocean`, `land`, `sky`, `toddler`, `geometric_mandala`) are defined in [`config/taxonomy.yaml`](file:///h:/Store/CurioKraft/Publications/coloring-book/config/taxonomy.yaml).
2. Layout continuity and geometric print boundaries are governed by [`.agents/rules/cover_wraparound_continuity.md`](file:///h:/Store/CurioKraft/Publications/coloring-book/.agents/rules/cover_wraparound_continuity.md).
3. Any agent generating or reviewing cover prompts must strictly adhere to the rules below to guarantee **first-pass generation success** with zero need for image re-renders or redos.

---

## 2. Inviolable Laws for Front Covers

### A. The Anti-Measurement Dimension Mandate
* **STRICTLY FORBIDDEN**: Never write physical dimensions, units, or CAD phrasing into the positive prompt:
  - ❌ `"safe live area (1.0 inch / 300px from all outer edges)"`
  - ❌ `"1.0 inch safe zone"`
  - ❌ `"300px margin lines"`
  - ❌ `"cut lines"` or `"ruler marks"`
* **Why**: Diffusion models (Google Imagen 3, Stable Diffusion) are trained on millions of blueprint schematics, design templates, and KDP print-margin guides. Writing `"1.0 inch / 300px"` causes the text encoder to activate the architectural/blueprint concept cluster, literally painting **dimension arrows, measurement tick marks, and ruler labels** onto the cover art!
* **REQUIRED ALTERNATIVE**: Always use relative, compositional percentages:
  - ✅ `"Leave generous 20% open ocean expanse at the top third of the canvas for the title lettering, and 12% calm seabed at the bottom for publisher marks."`
  - ✅ `"The central 68% of the canvas is occupied by a lively ensemble of 4 distinct iconic sea creatures..."`

### B. 100% Full-Bleed Borderless Canvas
* **STRICTLY FORBIDDEN**: Never request borders, vignettes, or simulated book folds:
  - ❌ `"scalloped corner frames"`
  - ❌ `"inner frame border"`
  - ❌ `"vertical spine crease"` or `"book fold shading"`
* **REQUIRED SPECIFICATION**: The positive prompt must mandate edge-to-edge illustration:
  - ✅ `"100% full-bleed borderless edge-to-edge ocean scene with water extending completely to all four outer canvas edges, strictly zero white borders, zero frame borders, zero margin crease lines."`

### C. Ensemble Variety & Deduplication
* The front cover must feature an ensemble of **4 distinct, recognizable creatures/objects** matching the volume's theme.
* **Deduplication Law**: The ensemble selection algorithm must strictly exclude blank verso, bleed guard, or non-content pages, ensuring that no creature (e.g. sea turtle or clownfish) appears twice.

### D. High-Contrast 3D Sculpted Typography
* Title display lettering must be rendered in high-relief 3D sculpted typography using the theme's display color palette from `taxonomy.yaml` (e.g., golden-amber/sunlit yellow `#FFD13B` with dark oceanic navy blue `#002244` outline drop-shadow for ocean series).
* **Isolation Law**: Keep the headline/title strictly in quotes (`"{title}"`). Never prepend style descriptions into the quote (e.g., avoid `'Sculpted 3D text: Title'`), which causes the model to render the word "Sculpted" as part of the book title.
* **Pill Banner Deduplication**: Bottom callout pills on the front cover must display age tiers and benefits (e.g. `"AGES 4-8 • 50 OCEAN CREATURES"`), never duplicating the book title or subtitle.

---

## 3. Inviolable Laws for Back Covers

### A. Value-Driven Parent Marketing Copy
* **STRICTLY FORBIDDEN**: Dry, repetitive technical summaries (e.g., repeating *"Thick Lines, 50 Images"* across the headline, body, and pills).
* **REQUIRED COPY STRUCTURE**:
  1. **Artistic Headline**: Sculpted 3D nautical headline in quotes:
     `"UNLOCK THE WONDERS OF THE DEEP BLUE OCEAN!"`
  2. **Child Developmental Benefit Copy**: An engaging 3-sentence blurb highlighting:
     - **Marine Biology / Nature Curiosity**: Inspiring young explorers with diverse species.
     - **Fine Motor Development**: Building pencil grip and hand-eye coordination with bold lines.
     - **Screen-Free Mindfulness & Creative Confidence**: Calming, focused creative play.
  3. **Clean Preview Showcase Cards**: 3 preview cards displaying only species names (`BLUE TANG`, `BLUE WHALE`, `SEA OTTER`), strictly omitting section prefixes like `"Fish:"` or `"Mammal:"`.
  4. **4 Distinct Benefit Pills**: 4 balanced, unique highlights with zero repetition:
     - `50 Unique Ocean Habitats`
     - `Single-Sided Bleed Prevention`
     - `Bold Outlines for Easy Coloring`
     - `Rich Educational Marine Life`

### B. Zero AI Barcode & Logo Mention (Continuous Scenery Only)
* **STRICTLY FORBIDDEN**: Never mention the words `barcode`, `ISBN`, `publisher logo`, or `badge` in the positive prompt. Even cautionary phrasing (*"leave blank box for barcode"*) primes diffusion models to paint blurry fake barcodes and distorted white boxes.
* **REQUIRED FOOTER SPECIFICATION**: The footer (lower 20%) must be described purely as rich, unbroken, continuous marine floor / seabed scenery (coral reef bed, sand ripples, gentle water currents, bubbles) flowing seamlessly across the bottom.
* **Programmatic Stamping**: The Python compositor stamps the actual Amazon KDP barcode and CurioKraft publisher badge on top of this scenery post-generation.

---

## 4. Master Prompt Templates

### Front Cover Prompt Template
```text
Clean 2D educational children's coloring book front cover art for [THEME_DISPLAY_NAME], ages [AGE_MIN]-[AGE_MAX].
Title at top in bold, vibrant [DISPLAY_PALETTE] sculpted 3D children's display lettering: "[BOOK_TITLE]".
Subtitle beneath in clean, readable rounded sans-serif font: "[BOOK_SUBTITLE]".
100% full-bleed borderless edge-to-edge [THEME_NAME] scene with water extending completely to all four outer canvas edges, strictly zero white borders, zero frame borders, zero margin crease lines.
Leave generous 20% open [THEME_MEDIUM] expanse at the top third of the canvas for the title lettering, and 12% calm seabed at the bottom for publisher marks.
The central 68% of the canvas is occupied by a lively ensemble of 4 distinct iconic [THEME_SUBJECTS]: [ENSEMBLE_DESCRIPTION], swimming in natural biological postures with joyful, curious, child-friendly expressions.
Rich vibrant oceanic color palette: [COLOR_PALETTE].
At the bottom, a stylish floating pill banner reading: "[PILL_BANNER_TEXT]".
Clean vector art style with smooth gradients, crisp outlines, zero photorealistic textures, zero airbrush noise.
```

### Back Cover Prompt Template
```text
Educational children's coloring book back cover for [THEME_DISPLAY_NAME], ages [AGE_MIN]-[AGE_MAX].
100% full-bleed borderless edge-to-edge [THEME_NAME] scene with water extending completely to all four outer canvas edges, strictly zero white borders, zero frame borders, zero margin crease lines.
Leave generous 15% open ocean expanse at top and 20% continuous [THEME_FOOTER_SCENERY] at bottom, perfectly aligned horizontally with the front cover.
Headline at top in clean, stylish sculpted 3D lettering: "[BACK_HEADLINE]".
Beneath the headline, a clean, inviting paragraph in readable, rounded typography: "[PARENT_DEVELOPMENTAL_COPY]".
Middle section features 3 charming circular or rounded-square preview cards showcasing line art from inside the book: "[CARD_1]", "[CARD_2]", and "[CARD_3]".
Beneath the preview cards, 4 distinct floating benefit pills in two neat rows: "[PILL_1]", "[PILL_2]", "[PILL_3]", and "[PILL_4]".
The bottom 20% is a rich, continuous [THEME_FOOTER_SCENERY] flowing seamlessly from edge to edge.
Clean vector illustration style matching the front cover.
```

---

## 5. Mandatory Negative Prompt Tokens

Every front and back cover prompt MUST include the following negative tokens to prevent CAD, crease, and barcode artifacts:

```text
dimension arrows, measurement lines, ruler marks, guidelines, blueprint lines, framing lines, border margins, corner brackets, inner frames, double borders, dark vertical crease line, dark margin line, spine shade line, scalloped corners, scalloped borders, vignette frame, barcode, barcode box, fake barcode, isbn, barcode placeholder, qr code, publisher logo, logo badge, white rectangle, white box, sticker, label, photorealistic, 3d render, dark scary creatures, scary expression, sharp teeth, text errors, typos, misspelled words, blurry text, watermark, signature
```

---

## 6. Pre-Generation Verification Checklist

Before locking or sending any cover prompt to the generation engine, verify:

| # | Check | Requirement |
| :--- | :--- | :--- |
| 1 | **Anti-Measurement** | Zero occurrences of `"1.0 inch"`, `"300px"`, `"safe live area"`, or `"ruler"` in the positive prompt. |
| 2 | **Full-Bleed Mandate** | Full-bleed borderless edge-to-edge specified; scalloped frames and inner borders strictly forbidden. |
| 3 | **Negative Tokens** | All measurement, crease, and barcode negative tokens are present in the negative prompt. |
| 4 | **Ensemble Uniqueness** | Exactly 4 distinct creatures specified; zero duplicates from bleed-guards or blank pages. |
| 5 | **Typography Contrast** | High-contrast palette defined from `taxonomy.yaml` (e.g. golden-amber `#FFD13B` on deep ocean blue). |
| 6 | **Developmental Copy** | Back cover focuses on child benefits (curiosity, fine motor, screen-free), not repetitive page specs. |
| 7 | **Zero AI Barcode** | Footer described purely as continuous scenery; zero mention of barcode/logo in positive prompt. |
