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
| Mascot | tiny_mascot.png | Cute bear/bunny/sun/puppy character. B/W outline only. Transparent BG. **Generate ONCE - reuse on BOTH pages.** |
| Achievement Badge | super_colorist_badge.png | Sun + ribbon + stars composition. B/W outline. Transparent BG. **STRICTLY NO TEXT, NO LETTERS, NO NUMBERS inside the badge.** Python will write "SUPER COLORIST". |
| Welcome Scene | welcome_scene.png | Friendly colorable scene: balloons, stars, crayons, rainbow. B/W thick outlines. Transparent BG. Must be colorable by a child. |
| Celebration Scene | celebration_scene.png | Festive: confetti, sparkles, stars. Denser and more celebratory than welcome scene. B/W outline. Transparent BG. |
| Stars Cluster | stars.png | 3-5 outlined stars. Transparent BG. |
| Sparkles | sparkles.png | Small sparkle/confetti elements. Transparent BG. |
| Crayons | crayons.png | Cute crayon cluster. B/W outline. Transparent BG. For Welcome page footer area. |

CRITICAL MASCOT RULE: Do NOT regenerate the mascot for the Certificate with a "different pose". AI cannot maintain character consistency across generations. Generate once, place on both pages.

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
