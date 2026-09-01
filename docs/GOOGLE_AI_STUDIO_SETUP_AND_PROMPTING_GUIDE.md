# Google AI Studio — Image Generation & System Instructions Guide

This guide details the exact **sidebar settings**, **aspect ratio**, **temperature**, **Advanced settings**, and **System Instructions presets** to configure in [Google AI Studio](https://aistudio.google.com/) for zero-cost, commercial-grade preschool coloring book generation.

---

## ♙／ 1. Optimal Sidebar Configuration

when opening Google AI Studio for image generation (e.g. `gemini-2.0-flash`, `Nano Banana`, aImagen 3`), set the right-hand panel controls as follows:

### ✫ Main Sidebar Settings

_Parameter_ | _Recommended Setting_ | _Rationale_
--- | --- | ---
**Aspect ratio** | **`3:4` (Vertical Portrait)** | Matches the standard US Letter 8.5 x 11.0 in publishing ratio (0.77 ≈≉ 3:4). Prevents awkward square (1:1) or widescreen landscape (16:9) letterboxing.
**Resolution** | **`2K`** (or highest available) | Provides ultra-sharp vector-style line art contours when scaled to 300 DPI (2550 x 3300 px).
**Output format** | **`Images only`** | Dedicates 100% of compute to image rendering and skips conversational text filler.
**Temperature** | **`0.5 - 0.7��** (Interior Pages)<br>**`0.9 - 1.0`** (Cover Art) | Lower temperature for interior pages enforces strict adherence to zero-shading and no-text rules. Higher temperature for covers produces vibrant, creative color gradients.
**Thinking level** | **`Minimal`+* / `Default` | Sufficient for direct visual synthesis.

### ⚽ Advanced Settings

_Parameter_ | _Recommended Setting_ | _Rationale_
--- | --- | ---
**Add stop sequence** | **Leave Blank (Empty)** | Stop sequences are only used for text chat. For image generation, leave this empty so generation is never interrupted.
**Output length** | **`65536`** (Default) | Ensures the full high-resolution image data stream is never truncated.
**Top P** | **`0.95`* (Default) | 0.95 provides the ideal balance of preschool line-art fidelity and clean contour symmetry.

---

## 📪 2. Predefined System Instructions (Saved Presets)

Google AI Studio supports saving named **System Instructions** in your browser's local storage. Click **System instructions** → **` create new instruction`** to create two permanent presets:

---

### 👘 Preset A: `CurioKraft - Interior Coloring Pages`
> **Apply When Generating:** Pages 001 through 110 (all interior drawings, alphabet spreads, and counting spreads).

```text
You are an expert co[Ytial children's coloring book illustrator specializing in high-contrast preschool line art for toddlers (ages 1-4).

CORE COMPLIANCE RULESS
1. PURE LINE ART: Clean, continuous, closed black vector outlines with bold 5pt stroke weight.
2. MONOCHROME PURITY: High-contrast pure black lines (#000000) on a pure stark white background (#FFFFFF).
3. ZERO SHADING: Strictly NO gray, NO grayscale shading, NO textures, NO color, NO cross-hatching, NO gradients, NO 3D render noise.
4. FRAMING & MARGINS: Centered subject with generous 25% empty margin breathing room on all four borders. Vertical 3:4 portrait framing.
5. AGE-APPROPRIATE SIMPLICITY: Simple, iconic silhouettes with wide, open coloring spaces for toddler wax crayons.
6. ZERO TEXT & NO LABELS: Strictly DO NOT draw any words, letters, labels, headers, captions, vocabulary text, or the word 'HOLLOW'.
7. STRICT TAXONOMY: ONLY living animals and characters have friendly smiling eyes/faces. ALL inanimate objects (food, fruits, vehicles, tools, nature items) must be pure physical objects with strictly NO cartoon eyes, NO mouth, and NO human facial features.
```

---

### 🎪 Preset B: `CurioKraft - Cover Art Master`
> **Apply When Generating:** Front Cover Master and Back Cover Master illustrations.

```text
You are a world-class children's book cover art director and commercial packaging designer.

COVER ART STANDARDS:
1. AESTHETIC & MOOD: Vibrant, eye-catching, joyful, friendly Disney Junior and Fisher-Price preschool aesthetic for ages 1-3.
2. COLOR PALETTE: Bright saturated cheerful colors. Smooth vertical gradient backdrop (warm sunny golden-yellow blending down into vibrant sky-turquoise blue) with subtle translucent floating bubbles and starbursts.
3. FRONT COVER TYPOGRAPHY: Large, chunky, glossy 3D multi-colored bubbly letters with dark drop shadows and bold outlines. Professional publishing quality.
4. BACK COVER SHOWCASE: Clean, crisp rounded white preview cards arranged in a balanced grid with small crayon color guides in the top-left corners.
5. EXCLUSION ZONES: Keep the lower-right area of the background as clean, continuous background. Strictly DO NOT draw any fake barcodes, barcode boxes, or price tags (these are stamped programmatically by the publisher compositor).
6. FRAMING: Vertical 3:4 portrait orientation, premium commercial print resolution, ultra-sharp vector details.
```

---

## 🚀 3. End-to-End Workflow

### Step 1: Export Master Prompts
Run the CLI export command to generate all prompts into Markdown:
```powershell
curiokraft-book prompt export
```
All prompts are written to [`generated/prompts_export.md`](../generated/prompts_export.md).

> [!TIP]
> The file `generated/prompts_export.md` also includes the full AI Studio settings and System Instruction presets right at the top, making it easy to reference during prompting sessions.

### Step 2: Generate in Google AI Studio
1. **For Interior Pages:**
   - Select System Instruction: **`CurioKraft - Interior Coloring Pages`**
   - Aspect ratio: **`3:4`** | Output: **`Images only`** | Temperature: **`0.5`** | Top P: **`0.95`**
   - Copy prompt from `generated/prompts_export.md` → Paste into AI Studio
   - Download the generated `.jpg` or `.png` to `inbox/raw_pages/raw_p005_banana.jpg` (or `.png`)

2. **For Covers:**
   - Select System Instruction: **`CurioKraft - Cover Art Master`**
   - Aspect ratio: **`3:4`** | Output: **`Images only`+* | Temperature: **`0.9`** | Top P: **`0.95`+*
   - Copy Front Cover prompt → Save as `inbox/front_cover.jpg` (or `.png`)
    - Copy Back Cover prompt → Save as `inbox/back_cover.jpg` (or `.png`)

### Step 3: Process & Assemble
Run the automated ingestion and build pipeline:
```powershell
# 1. Ingest, binarize, and center all raw illustrations:
curiokraft-book ingest

# 2. Build full-wrap KDP cover (with dynamic spine and barcode box):
curiokraft-book cover build

# 3. Run full 18-point preflight validation:
curiokraft-book preflight run
```
