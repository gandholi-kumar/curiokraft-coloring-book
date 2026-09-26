# CurioKraft Book Engine — CLI Workflow & Commands Guide

Welcome to your CurioKraft coloring book project! This workspace contains all configurations, manifests, fonts, and drop folders needed to produce an Amazon KDP print-ready coloring book.

---

## 🚀 Sequential Publishing Workflow

Follow these steps sequentially to generate and publish your coloring book:

### Step 1: Health Check & System Audit
Verify that all fonts, manifests, configurations, and privacy protections are ready:
```powershell
curiokraft-book doctor
```

---

### Step 2: Export AI Generation Prompts
Generate optimized image generation prompts for all pages:
```powershell
# Export all 110 page prompts to generated/prompts_export.md
curiokraft-book prompt export

# Or view a specific page prompt in terminal (e.g. Page 5)
curiokraft-book prompt show P005
```
* **Output:** [generated/prompts_export.md](file:///generated/prompts_export.md)
* Copy the prompts from this file and paste them into your image generation tool (e.g. Google AI Studio, Midjourney, etc.).

---

### Step 3: Drop Your Generated Images
Save and drop your downloaded PNG illustrations into their designated drop targets:

| File Type | Drop Location | File Naming Example |
| :--- | :--- | :--- |
| **Interior Coloring Pages** | `inbox/raw_pages/` | `raw_p005_apple.png` or `p005.png` or `apple.png` |
| **Front Cover Art** | `inbox/front_cover.png` | `front_cover.png` *(or front_cover.jpg)* |
| **Back Cover Art** | `inbox/back_cover.png` | `back_cover.png` *(or back_cover.jpg)* |
| **Mascot Art (Optional)** | `inbox/special_assets/` | `tiny_mascot.png` |

---

### Step 4: Ingest & Process Raw Pages
Process raw dropped images (automatic Otsu binarization, margin fitting, and vector typography):
```powershell
# Ingest and process all images from inbox/raw_pages/
curiokraft-book ingest

# Or generate / test a single sample page (e.g. Page 5)
curiokraft-book sample generate --pages P005
```
* **Output:** Processed 300 DPI master PNGs saved in `output/interior_masters/page_XXX.png`.

---

### Step 5: Build & Validate the Full-Wrap KDP Cover
Composite the exact 17.498 × 11.250 in (300 DPI) paperback wrap cover:
```powershell
# 1. (Optional) Export cover generation prompts for front/back artwork
curiokraft-book cover prompt

# 2. Build cover (uses dropped artwork or procedural gradient fallback)
curiokraft-book cover build

# 3. Validate dimensions, spine, barcode exclusion zone, and safe margins
curiokraft-book cover validate
```
* **Output:**
  * `output/cover/TINY_HANDS_COLOR_AND_LEARN_Cover_300DPI.png`
  * `output/cover/TINY_HANDS_COLOR_AND_LEARN_Cover_CMYK.pdf`

---

### Step 6: Assemble the 110-Page Interior Print PDF
Compile all page masters into the final lossless 8.5 × 11.0 in PDF:
```powershell
curiokraft-book assemble interior
```
* **Output:** `output/interior/TINY_HANDS_COLOR_AND_LEARN_Interior_110p.pdf`

---

### Step 7: Run 18-Point Deterministic KDP Preflight
Run the official diagnostic certification suite before publishing:
```powershell
curiokraft-book preflight run
```
* **Output:** `output/reports/FINAL_KDP_PREFLIGHT_CERTIFICATE.txt`

---

### Step 8: Generate Amazon KDP Submission Bundle
Synthesize optimized KDP title, subtitle, 7 search keywords, categories, and description:
```powershell
curiokraft-book kdp generate
```
* **Output:** Automatically opens `output/kdp/kdp_submission_helper.html` in your browser with 1-click copy buttons for the KDP publishing portal!

---

## 🎨 Layout Presets: Bleed vs. Non-Bleed

Your `config/` directory includes presets for both publishing styles:

* **Non-Bleed (Default):** `config/book_config_non_bleed.yaml`
  * Isolated, centered line-art with clean white margins (`0.50 in` on all sides).
  * Ideal for toddler and preschool first-words coloring books.
* **Bleed:** `config/book_config_bleed.yaml`
  * Full-bleed, edge-to-edge environmental illustrations (`bleed: true`, `target_coverage_ratio: 1.0`).
  * Ideal for older kids, scenery, and complex themed books.

### How to switch layout presets:
```powershell
# Switch active config to Full-Bleed:
Copy-Item config/book_config_bleed.yaml config/book_config.yaml -Force

# Switch active config back to Non-Bleed:
Copy-Item config/book_config_non_bleed.yaml config/book_config.yaml -Force
```

---

## 📚 Quick Command Reference

| Command | Description |
| :--- | :--- |
| `curiokraft-book init` | Initialize workspace (supports `--preset bleed` or `--preset non-bleed`) |
| `curiokraft-book doctor` | Run health diagnostics and asset audit |
| `curiokraft-book prompt export` | Export all page generation prompts to markdown |
| `curiokraft-book prompt show <PAGE_ID>` | Show single page prompt (e.g. `P005`) |
| `curiokraft-book ingest` | Ingest and process raw PNGs from `inbox/raw_pages/` |
| `curiokraft-book sample generate` | Generate sample pages for visual review (`--count 3` or `--pages P005`) |
| `curiokraft-book cover build` | Composite full-wrap KDP paperback cover (PNG + CMYK PDF) |
| `curiokraft-book cover validate` | Validate cover dimensions, barcode zone, and margins |
| `curiokraft-book assemble interior` | Assemble 110-page interior PDF |
| `curiokraft-book preflight run` | Run official 18-point KDP Preflight diagnostic |
| `curiokraft-book kdp generate` | Generate KDP metadata and 1-click HTML submission dashboard |
| `curiokraft-book test validators` | Run automated unit tests on validators and rescue algorithms |
| `curiokraft-book web start` | Launch local web studio interface (`http://127.0.0.1:8000`) |
