# CurioKraft Coloring Book — Master Publishing Workflows Guide

**Edition:** Vol 1.0 (Amazon KDP Paperback 8.5 × 11.0 in, 110 Pages)  
**Publisher Imprint:** CURIOKRAFT-KIDS  
**CLI Tool:** `curiokraft-book`

---

## 🎯 Choose Your Publishing Workflow

Select the workflow that matches your preferred generation setup:

```md
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        CHOOSE YOUR PUBLISHING WORKFLOW                          │
├───────────────────────────────────────┬─────────────────────────────────────────┤
│ 🟢 TRACK 1: FREE WEB UI WORKFLOW      | ⚡ TRACK 2: AUTOMATED CLOUD API        |
│ (Zero API Billing / Google AI Studio) │ (Fast Batch / OpenAI DALL-E or Gemini)  │
│                                       │                                         │
│ • Zero API cost                       │ • Fully hands-off 110-page generation   │
│ • Copy-paste prompts into browser     │ • Requires paid API key in environment  │
│ • Drop images into inbox/             │ • Executes in ~5–10 minutes             │
│ • Run `curiokraft-book ingest`        │ • Run `curiokraft-book generate book`   │
│                                       │                                         │
│ ➔ JUMP TO TRACK 1 BELOW              │ ➔ JUMP TO TRACK 2 BELOW                │
└───────────────────────────────────────┴─────────────────────────────────────────┘
```

---

## 🟢 Track 1: Free Google AI Studio Web Workflow (Zero API Cost)

Use this workflow to generate high-quality illustrations in the free **Google AI Studio Web UI** (or Gemini Chat / Google One) without paying for developer API tokens.

### Step 1: Export Master Prompts
Synthesize and export all 110 interior page prompts plus Front and Back Cover prompts into a single clean markdown document:
```powershell
curiokraft-book prompt export
```
* **Output generated:** `generated/prompts_export.md`
* To inspect or copy a single page prompt directly in your terminal:
  ```powershell
  curiokraft-book prompt show --page P005
  curiokraft-book cover prompt
  ```

---

### Step 2: Generate Illustrations in Google AI Studio
1. Open [Google AI Studio](https://aistudio.google.com).
2. Configure the recommended settings in the right sidebar:
   * **Model:** `gemini-2.5-flash` (or latest Gemini Image model)
   * **Aspect Ratio:** `3:4` (Vertical Portrait)
   * **Output Format:** `Images only`
   * **Temperature:** `0.5` (Interior) / `0.9` (Covers)
   * *(See [docs/GOOGLE_AI_STUDIO_SETUP_AND_PROMPTING_GUIDE.md](GOOGLE_AI_STUDIO_SETUP_AND_PROMPTING_GUIDE.md) for full preset details)*
3. Copy the **Positive Prompt** and **Negative Prompt** from `generated/prompts_export.md` into the prompt box and click **Run**.

---

### Step 3: Save Downloaded Images into Inbox Folders
Download the generated images and save them using standard naming:

* **Interior Illustrations:** Save into `inbox/raw_pages/`
  * Example: `inbox/raw_pages/raw_p002_alphabet_a_to_m.png` *(Page 2)*
  * Example: `inbox/raw_pages/raw_p004_numbers_0_to_5.png` *(Page 4)*
  * Example: `inbox/raw_pages/raw_p006_banana.png` (or simply `raw_p006.png` / `P006.png`)
* **Cover Artwork:** Save directly into `inbox/`
  * Front Cover: `inbox/front_cover.png` (or `.jpg`)
  * Back Cover: `inbox/back_cover.png` (or `.jpg`)

*(For complete file naming rules and multi-volume resolution, see [inbox/raw_pages/README.md](../inbox/raw_pages/README.md))*

---

### Step 4: Ingest & Programmatically Process Images
Run the ingestion engine to binarize (Otsu thresholding), scale to safe printable margins, and overlay toddler vector bubble typography:
```powershell
curiokraft-book ingest
```
* Automatically moves processed files from `inbox/raw_pages/` to `generated/raw_pages/` to keep your inbox clean.
* Outputs certified 300 DPI master canvases into `output/interior_masters/page_001.png` through `page_110.png`.

---

### Step 5: Render Special Pages (Page 001 Welcome & Page 110 Certificate)
Page 001 and Page 110 are bookend milestone pages that use modular assets (`tiny_mascot`, `super_colorist_badge`, `welcome_scene`, `celebration_scene`, `crayons`, `stars`, `sparkles`) located in `inbox/special_assets/`.

To render both pages with automated centering, white-background cleaning, and strict KDP 300 DPI typography:
```powershell
curiokraft-book generate special-pages
```
* **Output generated:** `output/interior_masters/page_001.png` & `output/interior_masters/page_110.png`
* **Guide & Multi-Volume Customization:** See [docs/SPECIAL_PAGES_AND_MASCOT_GUIDE.md](SPECIAL_PAGES_AND_MASCOT_GUIDE.md)

---

### Step 6: (Optional) Verify Visual Samples
To inspect sample pages before assembling the final book:
```powershell
curiokraft-book sample generate --pages P002,P004,P006 --source inbox
```
Inspect the output in `output/samples/`.

---

### Step 7: Build Cover & Assemble Interior PDF
Once all pages are ingested and special pages are rendered:
```powershell
# 1. Composite KDP Full-Wrap Cover (17.498 x 11.250 in with spine and barcode safe box)
curiokraft-book cover build

# 2. Compile 110 master PNGs into print-ready interior PDF
curiokraft-book assemble interior
```
* **Cover Output:** `output/cover/TINY_HANDS_COLOR_AND_LEARN_Cover_300DPI.png` & `output/cover/TINY_HANDS_COLOR_AND_LEARN_Cover_CMYK.pdf`
* **Interior Output:** `output/interior/TINY_HANDS_COLOR_AND_LEARN_Interior_110p.pdf`

---

### Step 8: Run Preflight Certification & Publish
```powershell
curiokraft-book preflight run
```
* Runs the full 18-point KDP diagnostic check (margins, bleed, resolution, page count, barcode clearance).
* Generates official certificate: `output/reports/FINAL_KDP_PREFLIGHT_CERTIFICATE.txt`.
* **Upload both files to Amazon KDP!**


---

## ⚡ Track 2: Automated Cloud API Workflow (Paid API Keys)

Use this workflow if you have an **OpenAI** or **Google Cloud (Gemini)** API key and want fully hands-off batch generation.

### Step 1: Set API Key in Environment
Open PowerShell in your project folder and set your active key:

```powershell
# For OpenAI DALL-E 3:
$env:OPENAI_API_KEY = "sk-proj-your-openai-api-key-here"

# OR for Google Gemini Developer API (requires paid billing enabled):
$env:GEMINI_API_KEY = "AIzaSy-your-gemini-api-key-here"
```

---

### Step 2: Generate Visual Samples (Gate 2 Visual Approval)
Generate 3 sample pages to verify style and prompt synthesis before running the full book:
```powershell
# Using OpenAI:
curiokraft-book sample generate --count 3 --source openai

# OR using Gemini:
curiokraft-book sample generate --count 3 --source gemini
```
* Review sample master PNGs in `output/samples/`.

---

### Step 3: Run Full 110-Page Production Batch
Execute the automated multi-agent debate, generation, code rescue, and vector typography pipeline across all 110 pages:
```powershell
# Using OpenAI:
curiokraft-book generate book --source openai

# OR using Gemini:
curiokraft-book generate book --source gemini
```
* **Output:** `output/interior_masters/page_001.png` through `page_110.png`.
* Check progress in the terminal progress bar or inspect `logs/pipeline.log`.

---

### Step 4: Build Cover & Assemble Interior PDF
```powershell
# 1. Composite full-wrap KDP cover (front, back, spine, logo, barcode box)
curiokraft-book cover build

# 2. Assemble all 110 interior masters into a print-ready PDF
curiokraft-book assemble interior
```

---

### Step 5: Run Preflight Certification & Publish
```powershell
curiokraft-book preflight run
```
* Executes the 18-point diagnostic.
* **Upload to Amazon KDP!**

---

## 🧪 Track 3: Offline Developer / Test Mode (Zero Cost Bézier Mock)

For local development, testing scripts, and CI/CD without calling any AI APIs:
```powershell
# Generate 3 mock vector pages:
curiokraft-book sample generate --count 3 --source mock

# Generate complete 110-page mock book:
curiokraft-book generate book --source mock
curiokraft-book cover build
curiokraft-book assemble interior
curiokraft-book preflight run
```

---

## 📋 CLI Command Cheat Sheet

| Command | Purpose | When to Use |
| :--- | :--- | :--- |
| `curiokraft-book doctor` | Check assets, fonts, and API environment | Initial workspace setup |
| `curiokraft-book manifest audit` | Verify 0 duplicate vocabulary collisions in manifest | Before generation |
| `curiokraft-book prompt export` | Export all 110 prompts + Cover prompts to markdown | **Track 1 (Free Web UI)** |
| `curiokraft-book prompt show -p P005` | Display single page prompt in terminal | Track 1 quick copy |
| `curiokraft-book cover prompt` | Display Front and Back cover artwork prompts | Track 1 cover creation |
| `curiokraft-book ingest` | Process user images from `inbox/raw_pages/` | **Track 1 (Free Web UI)** |
| `curiokraft-book sample generate` | Generate 1–5 sample master pages for review | Gate 2 visual check |
| `curiokraft-book generate book` | Run full automated 110-page generation batch | **Track 2 (Automated API)** |
| `curiokraft-book cover build` | Composite 17.498×11.250" cover PNG & PDF | After interior masters ready |
| `curiokraft-book cover validate` | Validate KDP cover dimensions, spine, and barcode zone | Cover compliance verification |
| `curiokraft-book assemble interior` | Compile 110 master PNGs into print interior PDF | After interior masters ready |
| `curiokraft-book preflight run` | Run official 18-point KDP diagnostic preflight | Final step before upload |
| `curiokraft-book debate show -p P005` | Inspect 4-round agent debate log for a page | Debugging / Quality Audit |

---

## 📚 Deep-Dive Documentation Index

For detailed mathematical specifications, prompt presets, multi-volume scaling, and multi-agent system internals, consult these focused documents:

* **[Google AI Studio Setup & Prompt Presets](GOOGLE_AI_STUDIO_SETUP_AND_PROMPTING_GUIDE.md)** — Aspect ratio, temperature, and copy-paste system instruction presets for web generation.
* **[Amazon KDP Print Specifications & Barcode Rules](KDP_PRINT_SPECIFICATIONS.md)** — Official geometry tables, cover calculation formulas, spine thickness, safe margins, and barcode box positioning.
* **[Amazon KDP Global Pricing & Royalty Strategy Guide](KDP_PRICING_AND_ROYALTY_GUIDE.md)** — Comprehensive analysis of the 60% vs. 50% royalty tier threshold, 14 regional marketplaces, European Fixed Price laws, and Expanded Distribution.
* **[Multi-Volume Architecture & Scaling Guide (Vol 2, Vol 3)](MULTI_VOLUME_ARCHITECTURE_GUIDE.md)** — How to create Volume 2, edit manifests, custom curriculum templates, and decouple data from code.
* **[Upcoming Volumes Concept & Series Roadmap](UPCOMING_VOLUMES.md)** — Top 6 evaluated volume concepts (Ocean, Vehicles, Baby Animals, Dinos, Farm, Bedtime), mascot profiles, 110-page structures, and launch blueprint.
* **[Multi-Agent System & Debate Engine](MULTI_AGENT_SYSTEM_AND_DEBATES.md)** — Details on the 10 specialist agents, 4-round debate protocols, red-teaming, and debate log inspection.
* **[Pre-Publish Checklist](ONE_TIME_SETUP_AND_PREPUBLISH_CHECKLIST.md)** — Step-by-step 15-minute verification checklist before publishing to Amazon.
* **[Image Inbox Naming Conventions](../inbox/raw_pages/README.md)** — Drop targets and naming fallback rules (`raw_p002_alphabet_a_to_m.png`, `raw_p006.png`, etc.).
