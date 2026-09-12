# CurioKraft Special Publication Pages & Mascot Architecture Guide

**Covers:** Page 001 (Welcome & Ownership) and Page 110 (Completion Certificate)  
**System Imprint:** CURIOKRAFT-KIDS  
**Skill Reference:** `.agents/skills/welcome-cert-page-crafting/SKILL.md`  
**Compositor Engine:** `curiokraft_book.compositor.special_pages`  
**CLI Command:** `curiokraft-book generate special-pages`

---

## 🌟 Executive Summary

In the CurioKraft publication architecture, **Page 001 (Welcome)** and **Page 110 (Completion Certificate)** are not standard single-object coloring pages. They are **bookend milestone experiences** that establish the child's ownership on Day 1 and reward their completion on Day 110.

To maintain publishing-house grade typography, perfect KDP print geometry, and joyful toddler engagement, these special pages use a **Hybrid AI/Python Architecture**:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          HYBRID SPECIAL PAGE SPLIT                          │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ 🤖 WHAT AI GENERATES (Gemini Studio) │ 🐍 WHAT PYTHON COMPUTES (special_pages)
├──────────────────────────────────────┼──────────────────────────────────────┤
│ • Mascot (Teddy, Bunny, Puppy, etc.) │ • 100% of Typography (3 strict fonts)│
│ • Achievement Medal Badge            │ • Print Margins, Bleed & Safe Insets │
│ • Welcome Scene (Balloons, Rainbow)  │ • Drop-Shadow Name Hero Boxes        │
│ • Celebration Streamers & Confetti   │ • Dual & Triple Contour Borders      │
│ • Stars & Sparkles clusters          │ • Auto-Cropping & Centering Layout   │
│ • Crayons bundle                     │ • Smart Checkerboard/Gray Removal    │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

---

## 🎨 The 7 Modular Special Assets

All special page artwork is composed of **modular, isolated line art assets**. 

The permanent, curated production assets live in:

```text
assets/special_assets/
├── tiny_mascot.jpg            # Main volume buddy (used on BOTH Page 001 and Page 110)
├── super_colorist_badge.jpg   # Central achievement medal (Page 110)
├── welcome_scene.jpg          # Balloons, rainbow arc, crayons, stars (Page 001)
├── celebration_scene.jpg      # Confetti, streamers, star bursts (Page 110)
├── stars.jpg                  # Cluster of 5 outline stars
├── sparkles.jpg               # Sparkle and starburst accents
└── crayons.jpg                # Cluster of 3 chunky toddler crayons
```

*(Note: The engine supports `.png`, `.jpg`, and `.jpeg` automatically).*

> [!NOTE]
> **Permanent Assets vs. Transient Inbox:**
> - `assets/special_assets/` is the **permanent project library** tracked in version control alongside `assets/fonts/` and `assets/logo/`.
> - `inbox/special_assets/` is the **temporary landing zone** where raw AI Studio generations are initially downloaded by Playwright before inspection and curation.

---

## ⚠️ The Golden Rule for AI Asset Generation

> [!CAUTION]
> **NEVER specify "transparent background" in prompts for image generation (Gemini Studio / Imagen / DALL-E).**
>
> Diffusion models do not natively output alpha transparency channels; they generate RGB pixels. When prompted with `"isolated transparent background"`, the model will literally **paint an artificial gray-and-white checkerboard grid** across the background and inside the characters, ruining the coloring book page!
>
> **ALWAYS specify:**
> `Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns, pure black and white line art only.`

---

## 🐍 Python Intelligent Cleaning & Compositing Engine

Even if an asset contains subtle JPEG compression artifacts or a faux checkerboard, the Python compositor (`curiokraft_book.compositor.special_pages`) automatically performs the following:

1. **Luminance Thresholding:** Any background pixel with luminance $> 140$ is automatically forced to pure white (`255`). The jet-black outlines ($< 100$) are preserved with zero degradation.
2. **Dynamic Bounding-Box Cropping:** The engine scans the line art contour, detects the tight bounds, and crops away empty margins so that graphics scale accurately to their designated layout slot.
3. **Dynamic Welcome Scene Split:** The welcome scene (balloons and rainbow) is dynamically split along its central empty vertical channel:
   - **Left Flank:** Floating Heart Balloon and Star Balloon with outline stars.
   - **Right Flank:** Floating Oval Balloon, crayons, rainbow arc, and outline stars.
4. **Hero Centering:** The Mascot is scaled to hero proportions (~$980 \times 1260$ px) and centered horizontally (`x = (2550 - 980) // 2`), creating a completely balanced, symmetrical, and inviting coloring playground.

---

## 📐 Page Structure & Zone Breakdown

### Page 001 — Welcome & Ownership

- **Border:** Double rounded contour with hand-drawn 5-point star corner ornaments.

- **Hero Headline:** `WELCOME, LITTLE EXPLORER!` (Font 135 pt).
- **Brand Display:** `TINY HANDS COLOR & LEARN` with thin accent divider rule.
- **Brand Mantra:** `COLOR • SAY • DISCOVER • PLAY` (identical to Page 110).
- **Ownership Zone:** `THIS BOOK BELONGS TO:` with a large framed Name Hero Box ($340 \times 170$ px) featuring a subtle drop shadow.
- **Interaction Zone (Centered):**
  - **Center:** Hero Mascot waving happily.
  - **Left Flank:** Balloons and stars floating upward.
  - **Right Flank:** Balloons, crayons, and rainbow arc.
  - **Accents:** Floating starburst sparkles above the mascot's ears.
- **Parent Connection:** Framed `★ Grown-Up Tip` card.
- **Footer:** `AGES 1–4 • 100+ FIRST WORDS, LETTERS & NUMBERS` placed safely above the inner border.

### Page 110 — Completion Certificate (Super Colorist Award)

- **Border:** Festive triple-contour celebratory border with dense corner and midpoint stars.

- **Hero Headline:** Flanked by sparkles, `YOU DID IT, LITTLE EXPLORER!` (Font 135 pt).
- **Award Title:** Star-flanked `★ SUPER COLORIST ★` with double accent line.
- **Recipient Zone:** `This special certificate celebrates` + Name Hero Box.
- **Achievement & Emotional Payoff:** Warm milestone text celebrating 100+ first words and everyday objects.
- **Central Hero Medal Assembly:**
  - **Center:** Giant **Super Colorist Medal** (~$860 \times 860$ px).
  - **Left Flank:** Festive celebration confetti and streamers.
  - **Right Flank:** The same Mascot cheering proudly.
  - **Accent:** Star cluster above the signature block.
- **Brand Mantra:** `COLOR • SAY • DISCOVER • PLAY`.
- **Signature Zone:** Generous lines for `Date` and `My Grown-Up's Signature`.
- **Footer:** `★ KEEP COLORING • KEEP EXPLORING • KEEP LEARNING! ★`.

---

## ⚙️ Configuration in `book_config.yaml`

The special pages and mascot system is 100% configurable in [`config/book_config.yaml`](../config/book_config.yaml) without code changes:

```yaml
book:
  title: "TINY HANDS COLOR & LEARN"
  subtitle: "FUN & EASY FIRST WORDS - Vol 2"
  volume: "vol2"
  brand: "CURIOKRAFT-KIDS"
  manifest: "manifest/pages_vol2.json"

  # ============================================================================
  # Milestone Bookend Pages Configuration (Include / Exclude)
  # ============================================================================
  special_pages:
    welcome_page:
      enabled: true          # true = render Page 001 Welcome; false = standard coloring page
      page_number: 1
    certificate_page:
      enabled: true          # true = render Page 110 Certificate; false = standard coloring page
      page_number: 110

  # ============================================================================
  # Volume Mascot Configuration (Theme-Aligned)
  # ============================================================================
  mascot:
    enabled: true            # true = volume uses a mascot; false = exclude mascot
    name: "panda"            # Optional: e.g. "panda", "dolphin", "tugboat". If omitted, auto-picks from active theme
    generate_prompt: true    # Boolean: true = synthesize prompt for AI Studio; false = exclude prompt
    drop_path: "inbox/special_assets/tiny_mascot.png" # Destination drop path
```

### Universal Series Adaptability

| Series / Theme | Recommended Mascot | `special_pages` Configuration | Result |
|---|---|---|---|
| **Toddler First Words (Vol 1, Vol 2)** | Panda / Teddy Bear | Both `enabled: true` | P001 Welcome + P110 Super Colorist Certificate with cheerful waving mascot |
| **Sea Animals Series** | Baby Dolphin / Sea Turtle | Both `enabled: true` | Ocean-themed welcome and certificate featuring the sea animal mascot |
| **Vehicles & Transportation** | Little Tugboat / Steam Train | Both `enabled: true` | Transportation-themed milestones celebrating little builders |
| **Story Book / Narrative Series** | Story Hero Protagonist | Both `enabled: true` or `welcome_page.enabled: true` | Story hero anchors the introduction and achievement |
| **Pure Coloring Book (No Milestones)** | N/A (`mascot.enabled: false`) | Both `enabled: false` | 100% coloring pages from Page 1 to the end; zero milestone templates |

---

## 🏛️ Multi-Volume Mascot Storage & Resolution Architecture

The compositor automatically resolves assets using a clean volume-aware cascade based on the active `volume:` in `book_config.yaml`:

```text
coloring-book/
├── assets/
│   └── special_assets/
│       ├── vol1/                          # Volume 1 curated mascot (Teddy Bear)
│       │   └── tiny_mascot.jpg
│       ├── vol2/                          # Volume 2 curated mascot (Baby Panda)
│       │   └── tiny_mascot.jpg
│       └── shared/ (or root fallback)     # Common decorative assets shared across all volumes
│           ├── crayons.jpg
│           ├── stars.jpg
│           ├── sparkles.jpg
│           ├── welcome_scene.jpg
│           └── celebration_scene.jpg
└── inbox/
    └── special_assets/                    # Transient drop zone where AI Studio downloads fresh assets
```

### Resolution Cascade (Zero Manual Flags Needed):
When `curiokraft-book generate special-pages` (or `curiokraft-book ingest`) runs:
1. It checks `assets/special_assets/{volume}/` for volume-specific assets (e.g. `tiny_mascot.jpg`).
2. If an asset is not found in the volume folder (or for universal items like `crayons` and `stars`), it falls back to `assets/special_assets/shared/` or `assets/special_assets/`.
3. If still not found, it checks `inbox/special_assets/{volume}/` or `inbox/special_assets/` for fresh AI generation drops.
4. An explicit `--assets <path>` CLI option can override the cascade at any time.

---

## 🤖 Multi-Agent Mascot Prompt Synthesis Workflow

When `curiokraft-book prompt export` is executed with `mascot.generate_prompt: true`:
1. The engine checks `mascot.name` in `book_config.yaml`. If omitted, `auto_pick_volume_mascot()` scans the active manifest's theme and picks the flagship identity (e.g. `panda` for Vol 2).
2. Four specialized agents (`AGT-005-EDU`, `AGT-002-DESIGN`, `AGT-003-KDP`, and `AGT-007-JUDGE`) debate and synthesize the prompt:
   - **5pt thick outline** with wide open coloring zones.
   - **Chubby joyful baby anatomy** sitting and waving one front paw.
   - **Solid pure white background** (strictly avoiding faux Photoshop checkerboards).
   - **Zero text, zero shading, zero color fills**.
3. The prompt is exported as item `MASCOT` in `generated/prompts_export.json` and `prompts_export.md` with drop target pointing to `mascot.drop_path` (default: `inbox/special_assets/tiny_mascot.png`).
4. Playwright generates and downloads the mascot directly into `inbox/special_assets/tiny_mascot.png`.
5. **Automated Post-Processing Archival:** When `curiokraft-book generate special-pages` or `curiokraft-book ingest` runs, it composites the milestone pages (Page 001 and Page 110) and then **automatically moves** all newly dropped assets from `inbox/special_assets/` into `assets/special_assets/{volume}/` (e.g. `assets/special_assets/vol2/`), keeping the inbox clean and preserving the assets permanently in the volume folder.


---

## 📋 Copy-Paste Prompts for Future Volume Mascots

To ensure all mascots match the **5pt stroke weight and toddler line art style** across the entire CurioKraft series, use these verified templates:

### Baby Panda (Volume 2 Official Mascot)

```text
Ultra-clean 2D preschool toddler coloring book line art illustration of a cute friendly baby panda for ages 1-4. Adorable chubby rounded body, sweet gentle smiling expression, big friendly round eyes, rosy blushing cheeks, sitting joyfully and waving one front paw. Thick clean black vector outline, 5pt stroke, wide open coloring areas. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Vertical portrait framing with generous empty margin space on all sides. Strictly NO text, NO letters, NO numbers, NO color fills, zero shading, zero grayscale, zero gradients, zero shadows. Pure black and white line art only.
```

### Baby Bunny (Alternative Mascot)

```text
Ultra-clean 2D preschool toddler coloring book line art illustration of a cute friendly baby bunny rabbit for ages 1-4. Long floppy ears, sweet gentle expression, big friendly eyes, cute nose and whiskers, simple happy smiling face, waving one front paw. Simple rounded chubby body. Thick clean black vector outline, 5pt stroke, wide open coloring areas. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Vertical portrait framing with generous empty margin space on all sides. Strictly NO text, NO letters, NO numbers, NO color fills, zero shading, zero grayscale, zero gradients, zero shadows. Pure black and white line art only.
```

### Playful Puppy (Recommended for Volume 3)

```text
Ultra-clean 2D preschool toddler coloring book line art illustration of a cute friendly baby puppy dog for ages 1-4. Floppy puppy ears, sweet gentle expression, big round friendly eyes, happy smiling face, sitting and waving one front paw. Simple rounded chubby body. Thick clean black vector outline, 5pt stroke, wide open coloring areas. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Vertical portrait framing with generous empty margin space on all sides. Strictly NO text, NO letters, NO numbers, NO color fills, zero shading, zero grayscale, zero gradients, zero shadows. Pure black and white line art only.
```

### Baby Dolphin (Sea Animals Series Mascot)

```text
Ultra-clean 2D preschool toddler coloring book line art illustration of a cute friendly baby dolphin for ages 1-4. Sweet smiling snout, gentle joyful expression, big friendly round eyes, chubby baby dolphin body, playfully upright with one front flipper waving happily. Thick clean black vector outline, 5pt stroke, wide open coloring areas. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Vertical portrait framing with generous empty margin space on all sides. Strictly NO text, NO letters, NO numbers, NO color fills, zero shading, zero grayscale, zero gradients, zero shadows. Pure black and white line art only.
```

---

## 💻 CLI Commands Reference

```powershell
# 1. Export prompts (includes MASCOT prompt when mascot.generate_prompt: true):
curiokraft-book prompt export

# 2. Render both special pages at 300 DPI (auto-resolves active volume):
curiokraft-book generate special-pages

# 3. Render with print-safety guide overlays (red=bleed, blue=trim, green=safe):
curiokraft-book generate special-pages --guides

# 4. Custom assets directory and custom output directory override:
curiokraft-book generate special-pages --assets assets/special_assets/vol2 --output output/interior_masters
```

---

## 🔒 Bookend Continuity Rule

> [!IMPORTANT]
> Whichever mascot character is chosen for a specific volume, **the exact same mascot image must be used on both Page 001 and Page 110**.
>
> This creates a closed emotional loop for the child:
> - **Page 001:** "Welcome! My name is ____, and this is my coloring friend."
> - **Page 110:** "You did it! Your coloring friend is here to celebrate your achievement!"
>
> This creates a closed emotional loop for the child:
>
> - **Page 001:** "Welcome! My name is ____, and this is my coloring friend."
> - **Page 110:** "You did it! Your coloring friend is here to celebrate your achievement!"
