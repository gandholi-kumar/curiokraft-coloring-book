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

All special page artwork is generated as **modular, isolated line art assets** stored in:

```text
inbox/special_assets/
├── tiny_mascot.png            # Main volume buddy (used on BOTH pages)
├── super_colorist_badge.png   # Central achievement medal (Page 110)
├── welcome_scene.png          # Balloons, rainbow arc, crayons, stars (Page 001)
├── celebration_scene.png      # Confetti, streamers, star bursts (Page 110)
├── stars.png                  # Cluster of 5 outline stars
├── sparkles.png               # Sparkle and starburst accents
└── crayons.png                # Cluster of 3 chunky toddler crayons
```

*(Note: The engine supports `.png`, `.jpg`, and `.jpeg` automatically).*

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
* **Border:** Double rounded contour with hand-drawn 5-point star corner ornaments.
* **Hero Headline:** `WELCOME, LITTLE EXPLORER!` (Font 135 pt).
* **Brand Display:** `TINY HANDS COLOR & LEARN` with thin accent divider rule.
* **Brand Mantra:** `COLOR • SAY • DISCOVER • PLAY` (identical to Page 110).
* **Ownership Zone:** `THIS BOOK BELONGS TO:` with a large framed Name Hero Box ($340 \times 170$ px) featuring a subtle drop shadow.
* **Interaction Zone (Centered):**
  - **Center:** Hero Mascot waving happily.
  - **Left Flank:** Balloons and stars floating upward.
  - **Right Flank:** Balloons, crayons, and rainbow arc.
  - **Accents:** Floating starburst sparkles above the mascot's ears.
* **Parent Connection:** Framed `★ Grown-Up Tip` card.
* **Footer:** `AGES 1–4 • 100+ FIRST WORDS, LETTERS & NUMBERS` placed safely above the inner border.

### Page 110 — Completion Certificate (Super Colorist Award)
* **Border:** Festive triple-contour celebratory border with dense corner and midpoint stars.
* **Hero Headline:** Flanked by sparkles, `YOU DID IT, LITTLE EXPLORER!` (Font 135 pt).
* **Award Title:** Star-flanked `★ SUPER COLORIST ★` with double accent line.
* **Recipient Zone:** `This special certificate celebrates` + Name Hero Box.
* **Achievement & Emotional Payoff:** Warm milestone text celebrating 100+ first words and everyday objects.
* **Central Hero Medal Assembly:**
  - **Center:** Giant **Super Colorist Medal** (~$860 \times 860$ px).
  - **Left Flank:** Festive celebration confetti and streamers.
  - **Right Flank:** The same Mascot cheering proudly.
  - **Accent:** Star cluster above the signature block.
* **Brand Mantra:** `COLOR • SAY • DISCOVER • PLAY`.
* **Signature Zone:** Generous lines for `Date` and `My Grown-Up's Signature`.
* **Footer:** `★ KEEP COLORING • KEEP EXPLORING • KEEP LEARNING! ★`.

---

## 🏛️ Multi-Volume Mascot Extensibility (Vol 2, Vol 3, etc.)

The mascot is **never hardcoded to a Teddy Bear**. You can switch to any mascot character for subsequent volumes with **zero code changes**:

### Option 1: Direct Drop-in (Single Volume Active)
Simply generate a new mascot (e.g., Baby Bunny) and place it as `inbox/special_assets/tiny_mascot.png`. When you run `curiokraft-book generate special-pages`, both Page 001 and Page 110 will automatically inherit the new mascot!

### Option 2: Volume Asset Folders (Recommended for Series)
Keep assets for multiple volumes side-by-side:
```text
inbox/
├── special_assets_vol1/       # Volume 1: Teddy Bear mascot & assets
├── special_assets_vol2/       # Volume 2: Bunny Rabbit mascot & assets
└── special_assets_vol3/       # Volume 3: Playful Puppy mascot & assets
```

Run the generator specifying the asset directory:
```powershell
# Generate Volume 2 Special Pages:
curiokraft-book generate special-pages --assets inbox/special_assets_vol2 --output output/vol2/interior_masters

# Generate Volume 3 Special Pages:
curiokraft-book generate special-pages --assets inbox/special_assets_vol3 --output output/vol3/interior_masters
```

---

## 📋 Copy-Paste Prompts for Future Volume Mascots

To ensure all mascots match the **5pt stroke weight and toddler line art style** across the entire CurioKraft series, use these verified templates:

### Baby Bunny (Recommended for Volume 2)
```text
Ultra-clean 2D preschool toddler coloring book line art illustration of a cute friendly baby bunny rabbit for ages 1-4. Long floppy ears, sweet gentle expression, big friendly eyes, cute nose and whiskers, simple happy smiling face, waving one front paw. Simple rounded chubby body. Thick clean black vector outline, 5pt stroke, wide open coloring areas. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Vertical portrait framing with generous empty margin space on all sides. Strictly NO text, NO letters, NO numbers, NO color fills, zero shading, zero grayscale, zero gradients, zero shadows. Pure black and white line art only.
```

### Playful Puppy (Recommended for Volume 3)
```text
Ultra-clean 2D preschool toddler coloring book line art illustration of a cute friendly baby puppy dog for ages 1-4. Floppy puppy ears, sweet gentle expression, big round friendly eyes, happy smiling face, sitting and waving one front paw. Simple rounded chubby body. Thick clean black vector outline, 5pt stroke, wide open coloring areas. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Vertical portrait framing with generous empty margin space on all sides. Strictly NO text, NO letters, NO numbers, NO color fills, zero shading, zero grayscale, zero gradients, zero shadows. Pure black and white line art only.
```

### Smiling Sun Character
```text
Ultra-clean 2D preschool toddler coloring book line art illustration of a cheerful smiling baby sun character for ages 1-4. Cute round face, sweet gentle expression, big friendly eyes, happy smiling mouth, simple chunky sun rays radiating outward with rounded tips, waving two cute cartoon hands. Thick clean black vector outline, 5pt stroke, wide open coloring areas. Solid pure white background, completely isolated on clean empty white background, NO checkerboard, NO grid, NO grey patterns. Vertical portrait framing with generous empty margin space on all sides. Strictly NO text, NO letters, NO numbers, NO color fills, zero shading, zero grayscale, zero gradients, zero shadows. Pure black and white line art only.
```

---

## 💻 CLI Commands Reference

```powershell
# 1. Render both special pages at 300 DPI:
curiokraft-book generate special-pages

# 2. Render with print-safety guide overlays (red=bleed, blue=trim, green=safe):
curiokraft-book generate special-pages --guides

# 3. Custom assets directory and custom output directory:
curiokraft-book generate special-pages --assets inbox/special_assets_vol2 --output output/interior_masters
```

---

## 🔒 Bookend Continuity Rule

> [!IMPORTANT]
> Whichever mascot character is chosen for a specific volume, **the exact same mascot image must be used on both Page 001 and Page 110**.
>
> This creates a closed emotional loop for the child:
> - **Page 001:** "Welcome! My name is ____, and this is my coloring friend."
> - **Page 110:** "You did it! Your coloring friend is here to celebrate your achievement!"
