---
name: welcome-cert-page-crafting
description: Expert system and workflow for designing, debating, and validating the Welcome page (Page 001) and Completion Certificate page (Page 110) of CurioKraft coloring books. Use whenever crafting prompts, reviewing designs, or finalizing these two special pages. Encodes the AI/Python responsibility split, zone architecture, narrative cascade, visual vocabulary, typography rules, and print geometry.
---

# Welcome & Certificate Page Crafting Skill

## Overview

This skill governs the two bookend pages of every CurioKraft coloring book:
- **Page 001 — Welcome** ("Beginning of the adventure")
- **Page 110 — Completion Certificate** ("Celebration of the adventure")

These are NOT ordinary coloring pages. They are a **matched Welcome -> Achievement system** designed to create emotional continuity across the child's entire journey through the book.

The master narrative cascade every design decision must serve:

```
WELCOME, LITTLE EXPLORER!
          |
          v
COLOR . SAY . DISCOVER . PLAY
          |
          v
   100+ LITTLE DISCOVERIES
          |
          v
       YOU DID IT!
          |
          v
     SUPER COLORIST
```

---

## Core Principle: AI as Illustrator, Python as Layout Engine

**Never ask AI to generate a complete page layout.**

| AI generates | Python generates |
|---|---|
| Mascot character | All typography / text |
| Award badge illustration | Page border / frame |
| Welcome scene (colorable) | Name fields / signature lines |
| Celebration scene | Date fields |
| Organic star clusters | Geometric star shapes |
| Sparkles / confetti | Margins / trim / bleed |
| Crayon cluster | Safe area enforcement |
| | Logo placement |
| | Footer text |
| | Page composition / zones |
| | Repeated branding ("COLOR . SAY . DISCOVER . PLAY") |

AI is an **illustrator**. Python is the **art director and typesetter**.

Reason: AI cannot reliably produce exact spelling, consistent fonts, precise margins, KDP-compliant bleed/trim/safe zones, or identical branding across two pages.

---

## The 7 Modular AI Assets

Generate these as **isolated black-and-white line-art illustrations, transparent background**. Never as a complete page.

| Asset | Filename | Rules |
|---|---|---|
| Perimeter Frame | frame.png | Full-perimeter living vignette framing a wide open 70% central area for typography, cards, and mascot. Outer 15–20% margin coverage. Crisp B/W line art. |
| Mascot | tiny_mascot.png | Cute theme-aligned character (e.g. Sammy the Sea Turtle for Ocean). B/W outline only. Solid white body. **Generate ONCE - reuse on BOTH pages.** |
| Achievement Badge | super_colorist_badge.png | Thematic award ribbon/seal. B/W outline. **STRICTLY NO TEXT, NO LETTERS, NO NUMBERS inside the badge.** |
| Welcome Scene | welcome_scene.png | Optional secondary scene if no perimeter frame is used. |
| Celebration Scene | celebration_scene.png | Festive decoration for certificate page. |
| Stars Cluster | stars.png | 3-5 outlined stars. |
| Sparkles | sparkles.png | Small sparkle/confetti elements. |
| Crayons | crayons.png | Cute crayon cluster. |

CRITICAL MASCOT RULE: Do NOT regenerate the mascot for the Certificate with a "different pose". AI cannot maintain character consistency across generations. Generate once, place on both pages.

---

## Top 10 Bestselling Genre Research Protocol & Multi-Agent Frame Deliberation

To ensure CurioKraft books compete with world-class commercial bestsellers, the Multi-Agent Debate Engine follows a strict **Genre Research Protocol** prior to synthesizing perimeter frames:

### 1. Benchmark Analysis of Top 10 Bestsellers by Genre

| Genre / Series | Top 10 Bestseller Benchmarks | Proven Design Elements | Frame Boundary Rules |
| :--- | :--- | :--- | :--- |
| **Ocean / Aquatic** | *Lost Ocean* (Johanna Basford), *Island Paradise* (Millie Marotta), *DK Eyewitness Ocean*, *Usborne Under the Sea* | Rich coral reef bottom anchor; vertical kelp fronds, sea fans, and rising bubble streams climbing outer 15% margins. | 70% center completely open. Base reef anchors bottom; bubbles cluster at top. |
| **Land / Safari** | *Wild Savannah* (Millie Marotta), *National Geographic Wild*, *World of Flowers* | Earthy textured foundation; acacia branches, sand dunes, river rocks, and tall savannah grasses framing side margins. | Grounded horizon at bottom; climbing botanical/rocky flanks; airy canopy at top. |
| **Air / Sky** | *Birds of the World* (Charley Harper), *Sibley Birds Coloring*, *DK Flight* | Airy, weightless perimeter; cumulus clouds clustering along bottom and top corners; soaring feather flourishes and wind swirls. | Lightest visual weight; clouds frame corners and top; descending raindrop/breeze trails. |
| **Origami Arts** | *Origami Tessellations* (Eric Gjerde), *Japanese Patterns* (Tuttle), *Geometric Origami* | Crisp mathematical angles, creased paper facets, interlocking polygonal folds framing a pristine center. | Modular geometric folded tabs along margins; sharp 45° and 60° beveled facets. |
| **Mandala Arts** | *Stress Relieving Mandala Designs*, *The Mandala Colouring Book* (Jim Gogarty) | Sacred radial symmetry, lotus petal scallops, intricate lace arches framing an ornamental central plaque. | Symmetrical outer quadrant arches; interlocking petal scallops framing central open zone. |

### 2. Multi-Agent Specialist Roles & Opinions for Perimeter Frames

When synthesizing perimeter frame prompts, three specialist agents must reach consensus:
1. **Art Director Agent**:
   - *Mandate*: Aesthetic composition, genre authenticity, and hierarchy.
   - *Requirement*: The perimeter frame must occupy only the outer **15% to 20%** margin perimeter. The central **70% of the canvas MUST be 100% pure empty white negative space** to house the headline, logbook card, mascot, and guide box.
2. **Technical Preflight Specialist Agent**:
   - *Mandate*: Amazon KDP print safety and zero reproduction defects.
   - *Requirement*: Strictly enforce KDP safe margin bounds (Spine Gutter $\ge 0.50$ in, Outside $\ge 0.375$ in, Top $\ge 0.40$ in, Bottom $\ge 0.375$ in). Demand pure binary black & white vector line art (0/255) with zero gray wash, zero shading, and strictly NO text, fake boxes, or measurement arrows.
3. **Target Audience Specialist Agent**:
   - *Mandate*: Developmental appropriateness and coloring engagement.
   - *Requirement*: Stroke hierarchy must be 3–5 pt primary contours and 2 pt secondary details with wide, colorable closed shapes so children or hobbyists can actively color in the perimeter frame!

---

## Master AI Prompt Templates for Perimeter Frames

### 1. Ocean / Aquatic Perimeter Frame (`aquatic_frame.png`)
```text
Ultra-clean 2D coloring book line art of an elaborate full-perimeter underwater marine life border vignette framing a wide open, completely empty white central area. Along the bottom border: lush detailed coral reef branches, sea anemones, textured sea sponges, small starfish, and scallop shells resting on ocean sand. Along the left and right vertical borders: gracefully swaying sea kelp ribbons, delicate sea fans, and ascending streams of tiny round sea bubbles climbing upward. Along the top border: gentle water surface wave ripples and floating bubble clusters. The entire center of the page (70% area) is completely empty solid white blank paper with NO illustrations and NO text. Thick clean black vector outlines, 4pt primary stroke, 2pt secondary details, completely closed shapes ready for coloring. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Strictly NO text, NO letters, NO numbers, NO rectangular border lines, NO color fills, zero shading, zero gradients, zero shadows. Pure black and white line art only.
```

### 2. Land / Safari Perimeter Frame (`land_frame.png`)
```text
Ultra-clean 2D coloring book line art of an elaborate full-perimeter terrestrial safari landscape border vignette framing a wide open, completely empty white central area. Along the bottom border: textured sand dunes, smooth river pebbles and stones, small fallen leaves, and lush tufts of wild savannah grasses. Along the left and right vertical borders: climbing botanical vines, wild acacia branches, and tall bamboo stalks. Along the top border: arched canopy tree leaves and hanging jungle foliage. The entire center of the page (70% area) is completely empty solid white blank paper with NO illustrations and NO text. Thick clean black vector outlines, 4pt primary stroke, 2pt secondary details, completely closed shapes ready for coloring. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Strictly NO text, NO letters, NO numbers, NO rectangular boxes, zero shading, zero gradients. Pure black and white line art only.
```

### 3. Air / Sky Perimeter Frame (`air_frame.png`)
```text
Ultra-clean 2D coloring book line art of an elaborate full-perimeter open sky and cloud border vignette framing a wide open, completely empty white central area. Along the bottom border: billowing cumulus cloud banks and soft stylized mountain peak silhouettes. Along the left and right vertical borders: swirling wind ribbons, gentle diagonal rain drop streams, and soaring feather flourishes. Along the top border: puffy cloud clusters and gentle sunburst outline rays. The entire center of the page (70% area) is completely empty solid white blank paper with NO illustrations and NO text. Thick clean black vector outlines, 4pt primary stroke, 2pt secondary details, completely closed shapes ready for coloring. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Strictly NO text, NO letters, NO numbers, NO rectangular boxes, zero shading, zero gradients. Pure black and white line art only.
```

### 4. Origami Arts Perimeter Frame (`origami_frame.png`)
```text
Ultra-clean 2D coloring book line art of an elaborate full-perimeter Japanese origami folded paper border vignette framing a wide open, completely empty white central area. Along all outer borders: interlocking geometric folded paper facets, modular origami paper crane silhouettes, beveled 45-degree and 60-degree paper fold creases, and decorative paper tessellations. The entire center of the page (70% area) is completely empty solid white blank paper with NO illustrations and NO text. Sharp clean black vector outlines, 3.5pt primary stroke, 2pt fold crease details, closed coloring facets. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Strictly NO text, NO letters, NO numbers, zero shading, zero gradients. Pure black and white line art only.
```

### 5. Mandala Arts Perimeter Frame (`mandala_frame.png`)
```text
Ultra-clean 2D coloring book line art of an elaborate full-perimeter sacred mandala and lotus petal border vignette framing a wide open, completely empty white central area. Along all outer borders: ornate symmetrical lace arches, sacred geometric circular filigree, radiating lotus petal scallops, and decorative corner quadrant mandalas. The entire center of the page (70% area) is completely empty solid white blank paper with NO illustrations and NO text. Crisp clean black vector outlines, 3.5pt stroke, bold open coloring segments. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Strictly NO text, NO letters, NO numbers, zero shading, zero gradients. Pure black and white line art only.
```

---

## Universal Dual-Mode Container Architecture (Cards & Frames)

To prevent hardcoded style restrictions across diverse series, all milestone page containers operate on a **Dual-Mode System**:
1. **Mode 1: Artist Asset Container (`mode: "asset"`)**:
   - An artist or volume designer can drop a custom-drawn `card_frame.png` or `frame.png` into `assets/special_assets/{volume}/`.
   - The engine automatically loads, scales, and composites the asset, rendering dynamic typography directly inside its designated safe zone.
2. **Mode 2: Parametric Geometry Engine (`mode: "parametric"`)**:
   - When procedurally generating cards, the geometry is configured in `book_config.yaml` using pure mathematical primitives:
     - `geometry: "sinusoidal"`: Fluid ocean waves, sand dunes, gentle swells.
     - `geometry: "scalloped"`: Mandala petal arches, cloud puffs, floral scallops.
     - `geometry: "polygonal"`: Origami creased facets, crystalline chamfers, beveled tabs.
     - `geometry: "rounded"`: Classic modern rounded rectangle fallback.

---

## AI Prompt Templates (Per Asset)

> [!IMPORTANT]
> **Background Generation Rule:** NEVER specify "transparent background" in prompts for image generation (Gemini Studio/Imagen). Diffusion models do not generate alpha channels; they generate RGB pixels and will paint an artificial gray/white checkered pattern (fake Photoshop transparency grid) across the canvas and inside the characters!
> **Always specify:** `Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns, pure black and white line art only`.
> The Python compositor automatically handles background cleaning, cropping, and thresholding.

### Mascot
```
Ultra-clean 2D preschool toddler coloring book line art illustration of a cute friendly baby [CHOOSE ONE: teddy bear / bunny / puppy / smiling sun character] for ages 1-4. Simple rounded body, sweet gentle expression, big friendly eyes, simple happy face. Thick clean black vector outline, 5pt stroke, wide open coloring areas. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Vertical portrait framing with generous empty margin space. Strictly NO text, NO letters, NO numbers, NO color fills, zero shading, zero gradients, zero shadows. Pure black and white line art only.
```

### Achievement Badge
```
Ultra-clean 2D preschool toddler coloring book line art achievement badge illustration for ages 1-4. A cheerful smiling sun face inside a decorative award ribbon with flowing tails, five-point outline stars arranged around it. Thick smooth black vector outlines, simple large coloring areas, bold clean shapes. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Strictly NO text, NO letters, NO numbers, NO words anywhere in the image. Zero shading, zero gradients, zero shadows, zero color fills. Pure B/W line art only.
```

### Welcome Scene
```
Ultra-clean 2D preschool toddler coloring book line art illustration - a joyful colorable welcome scene for ages 1-4. Shows: outline star shapes, simple balloon outlines, a small outlined rainbow arc, cute outlined crayon shapes. All elements have bold thick outlines and large open areas for coloring. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Arranged as a friendly decorative composition. Strictly NO text, NO letters, NO numbers. Zero shading, zero gradients, zero color fills. Pure B/W line art only.
```

### Celebration Scene
```
Ultra-clean 2D preschool toddler coloring book line art celebration decoration for ages 1-4. Festive confetti pieces, sparkle stars, small outlined star bursts, celebration streamers - all as simple bold outlines. Denser arrangement than a simple scene, feeling like a big party. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Strictly NO text, NO letters, NO numbers. Zero shading, zero gradients, zero color fills. Pure B/W line art only.
```

### Stars Cluster
```
Ultra-clean 2D preschool toddler coloring book line art of 3 to 5 five-point outlined stars arranged in a small cluster. Bold clean black vector outlines, simple interiors with no fills. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Strictly NO text. Zero shading, zero gradients.
```

---

## Zone-by-Zone Page Architecture

Agents must evaluate each page by **zone**, not holistically. A design cannot be approved unless every zone is addressed.

### Welcome Page (Page 001) - Zones top to bottom

| Zone | Required Content | Notes |
|---|---|---|
| Top | WELCOME, LITTLE EXPLORER! | Hero headline. ALL CAPS. Largest type on page. |
| Brand | TINY HANDS COLOR & LEARN | Brand display font. |
| Subheading | COLOR . SAY . DISCOVER . PLAY | Must match Certificate exactly - Python renders this. |
| Ownership | THIS BOOK BELONGS TO: / MY NAME IS: / write line | Creates child ownership. Box/frame around this block. |
| Interaction | Large colorable illustration (mascot + welcome scene assets) | Must be colorable by child. Thick outlines. Wide open areas. This is an activity, not decoration. |
| Parent connection | Grown-Up Tip: "Color together, say the words aloud, and celebrate every little discovery!" | Positions the book as parent+child activity. Small but present. |
| Footer | AGES 1-4 . 100+ FIRST WORDS, LETTERS & NUMBERS | Small. Not tiny. |

### Certificate Page (Page 110) - Zones top to bottom

| Zone | Required Content | Notes |
|---|---|---|
| Top | YOU DID IT, LITTLE EXPLORER! | Hero headline. ALL CAPS. Largest type on page. Mirrors Welcome Top zone. |
| Main award | SUPER COLORIST | Second tier headline. |
| Recipient | "This special certificate celebrates" + large name line | Name line must be a **visual hero** - large outlined area, not just a thin underline. |
| Achievement | "for completing the Tiny Hands Color & Learn adventure! You explored, colored, discovered, and played with 100+ first words, letters, numbers, and everyday objects." | Sentence case. Warm, not academic. |
| Emotional message | "Every page was a little adventure. Every color was your own. Every discovery was something to celebrate!" | Three lines. Emotional payoff moment. |
| Hero badge | super_colorist_badge.png asset (large, centered) | This is the MEDAL. Make it large. Not a small clip-art icon. |
| Bottom | Date: ___ / My Grown-Up's Signature: ___ | Use "My Grown-Up's Signature" NOT "Parent/Teacher Signature". |

---

## Visual Vocabulary (Mandatory Recurring Elements)

Do NOT randomly decorate. Use exactly these 6 elements consistently across both pages:

| Element | Role |
|---|---|
| Star | Primary decoration |
| Happy sun (in badge) | Secondary / achievement |
| Ribbon/badge | Achievement symbol |
| Sparkles | Journey indicator |
| Tiny Hands logo | Brand identity |
| Mascot | Character / friend (same character, both pages) |

The sun+ribbon+stars badge is used at three scales across the book:
- Welcome page: Small (Little Explorer Badge feel)
- Throughout book: Occasional micro-use (Great Job!)
- Certificate: Large hero element (Super Colorist medal)

---

## Typography Rules

Enforce **exactly 3 fonts** on both pages. No exceptions.

| Font Role | Used For | Case Rule |
|---|---|---|
| Font 1 - Brand display | TINY HANDS COLOR & LEARN | ALL CAPS |
| Font 2 - Friendly heading | Hero headlines and named subheadings | ALL CAPS for hero; Title Case for subheadings |
| Font 3 - Highly readable body | Body copy, Grown-Up Tip, achievement text | Sentence case |

### Case Hierarchy (Mandatory)

| Case | Used For | Example |
|---|---|---|
| ALL CAPS | Hero headlines ONLY | "YOU DID IT!" |
| Title Case | Named headings | "Welcome, Little Explorer!" |
| Sentence case | Body / emotional copy | "Your coloring adventure starts here." |

Never make everything uppercase. When all text is caps, hierarchy collapses - everything looks equally important.

---

## Border Rules

| Welcome Border | Certificate Border |
|---|---|
| Small outlined stars | More stars (denser) |
| Simple clean line art | Award badge element |
| Open / anticipatory feeling | Confetti / celebration elements |
| | Mascot present |

Python draws the border programmatically (not AI). The border uses the same visual language on both pages but the Certificate version is more celebratory: anticipation -> celebration.

---

## The Journey Correlation (Bookend Mirror Check)

Before approving either page, verify this mirror is intact:

| Welcome (Page 001) | Certificate (Page 110) |
|---|---|
| WELCOME, LITTLE EXPLORER! | YOU DID IT, LITTLE EXPLORER! |
| Your adventure starts here | Your adventure is complete |
| This book belongs to | This achievement belongs to |
| COLOR . SAY . DISCOVER . PLAY | COLOR . SAY . DISCOVER . PLAY (identical) |
| Little Explorer | Super Colorist |
| Stars (small) | Stars (large + more) |
| Mascot (same character) | Mascot (same character) |
| Badge (small) | Award (large hero) |
| Tiny Hands brand | Tiny Hands brand |
| 100+ learning activities | 100+ learning experiences |

---

## Print Geometry (Python Must Enforce)

| Dimension | Value |
|---|---|
| Trim size | 8.5 x 11 inches |
| Resolution | 300 DPI minimum |
| Canvas (no bleed) | 2550 x 3300 px |
| Canvas (full bleed) | approx 2588 x 3375 px |
| Bleed | 0.125 inch on top, bottom, outside edge |
| Safe area inside margin | 0.375 inch minimum (KDP 24-150 page books) |
| Safe area outside margin | 0.375 inch with bleed |

Three zones Python must enforce:

| Zone | Rule |
|---|---|
| Bleed (0.125 inch beyond trim) | Background art may extend here. NO text. |
| Trim (8.5 x 11 inch) | Final cut boundary. |
| Safe area (0.375 inch inside trim) | ALL text, name fields, signatures, logos MUST stay here. |

Debug mode: Python must support render_page(show_guides=True) which overlays RED=bleed, BLUE=trim, GREEN=safe area, YELLOW=text boxes. Production uses render_page(show_guides=False).

---

## Python QA Assertions (Run Before Every PDF)

```python
assert page.width == expected_width
assert page.height == expected_height
assert dpi >= 300
assert title_inside_safe_area
assert name_field_inside_safe_area
assert signature_inside_safe_area
assert no_text_in_bleed_area
assert all_fonts_embedded
```

Build output must include: welcome.png, certificate.png, welcome_debug.png, certificate_debug.png, qa_report.json, book.pdf

---

## Python Module Architecture (Target Structure)

```
book_config.py          <- Design constants, theme tokens
design_system.py        <- BOOK_THEME dict (fonts, sizes, strokes, colors)
layout_engine.py        <- Semantic page DSL
assets/
    mascot/             <- tiny_mascot.png
    badges/             <- super_colorist_badge.png
    illustrations/      <- welcome_scene.png, celebration_scene.png
pages/
    welcome.py          <- Welcome page using layout_engine
    certificate.py      <- Certificate page using layout_engine
validators/
    print_qa.py         <- All QA assertions
build/                  <- Final outputs
```

Welcome and Certificate must share one design_system.py. No independent theme variables. All geometry is deterministic in Python. Use semantic DSL - never raw pixel coordinates.

---

## Anti-Patterns (Validation Failures - Reject These)

- AI asked to generate a complete page layout
- Text / letters / numbers inside the badge AI asset
- Gray shading on any illustration (kills colorability - toddlers must be able to color it)
- Interior animal/vehicle illustrations reused as mascot or decorations (wrong composition type)
- Mascot regenerated separately for Certificate (character will differ)
- "Official Certificate" language (too institutional for toddlers)
- "Successfully learned / mastered 100+" (developmental overclaim - use "explored")
- "Parent / Teacher Signature" (must be "My Grown-Up's Signature")
- Everything in ALL CAPS (hierarchy collapses)
- More than 3 fonts on one page
- Any important element outside the safe area
- "COLOR . SAY . DISCOVER . PLAY" rendered differently on the two pages
- Certificate name field as a thin underline only (must be a large outlined visual hero area)
- Sun/ribbon badge asset used at small size on the Certificate (it must be the large HERO element)
- Treating the PNG output as the final print-ready product (must produce a proper KDP PDF)

---

## Validation Checklist (Run Before Approving Any Design)

### Asset Prompts
1. Is every AI asset requested as isolated B/W line art with transparent background?
2. Is the badge prompt explicit that NO text/letters/numbers appear inside it?
3. Is the mascot the same asset on both pages (not regenerated)?

### Welcome Page
4. Does the Top zone use "WELCOME, LITTLE EXPLORER!" (not "Welcome to Tiny Hands...")?
5. Is the Interaction zone a genuinely colorable illustration (thick outlines, open areas)?
6. Is the Grown-Up Tip present in the Parent connection zone?
7. Does "THIS BOOK BELONGS TO" feel like ownership, and is the name field boxed/framed?

### Certificate Page
8. Does the Top zone use "YOU DID IT, LITTLE EXPLORER!" (not "Official Certificate")?
9. Is "My Grown-Up's Signature" used (not "Parent/Teacher Signature")?
10. Is the achievement text warm and participatory (not academic/mastery claims)?
11. Is the child's name field a large visual hero area (not just a thin line)?
12. Is the Hero badge large and central (medal-sized, not icon-sized)?

### Both Pages
13. Does "COLOR . SAY . DISCOVER . PLAY" appear identically on both pages?
14. Are all 6 visual vocabulary elements (star, sun, ribbon, sparkle, logo, mascot) present?
15. Is typography limited to 3 fonts with correct case hierarchy?
16. Does the border evolve from anticipatory (Welcome) to celebratory (Certificate)?
17. Is all text within the safe area (0.375 inch inside trim)?
18. Does the narrative cascade hold: Welcome Little Explorer -> YOU DID IT -> SUPER COLORIST?
