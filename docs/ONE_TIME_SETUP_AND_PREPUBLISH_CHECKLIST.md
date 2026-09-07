# CurioKraft Coloring Book — One-Time Setup & Pre-Flight Checklist

This guide provides the complete setup checklist, required publisher assets, environment preparation, disaster recovery procedures, and PyPI packaging rules for running the **CurioKraft Coloring Book Engine** in VS Code and publishing to the global Pip inventory.

---

## 1. Publisher Assets Checklist (Your Input Files)

Before running a production book generation, place your brand assets and chosen font into the designated `assets/` subdirectories:

| Asset Name | Target File Path | Recommended Specs | Purpose |
| :--- | :--- | :--- | :--- |
| **Company Logo** | `assets/logo/curiokraft_logo.png` | Transparent PNG, $\ge 600\text{ px}$ width, 300 DPI | Rendered on Front Cover & Imprint |
| **Brand Emblem** | `assets/emblem/curiokraft_emblem.png` | Transparent PNG, $\ge 300 \times 300\text{ px}$, 300 DPI | Rendered on Back Cover & Quality Stamp |
| **Child-Friendly Font** | `assets/fonts/Fredoka-Bold.ttf` (or `Nunito-Bold.ttf`) | TrueType (`.ttf`) or OpenType (`.otf`) with commercial license (OFL) | Used for all uppercase vector page headers |

> [!NOTE]
> If any asset is missing, the engine automatically uses elegant vector typographic fallbacks so tests and dry-runs will never crash.

---

## 2. One-Time VS Code & Python Setup

### Step 1: Open Folder in VS Code
Open the project root directory (`coloring-book`) in VS Code.

### Step 2: Ensure Python 3.10+ is Installed
If Python is not recognized in your terminal, download and install Python 3.10 or higher from [python.org](https://www.python.org/downloads/) (ensure you check **"Add Python to PATH"** during installation).

### Step 3: Create & Activate a Virtual Environment
In your VS Code PowerShell terminal:
```powershell
# Create a local virtual environment (.venv)
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
or 
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; .\.venv\Scripts\Activate.ps1
```

### Step 4: Install the Package in Editable Mode
```powershell
pip install -e .
```
*(This automatically installs all dependencies: Typer, Rich, Pillow, OpenCV, NumPy, PyMuPDF, ReportLab, Pydantic, etc.)*

### Step 5: Configure Your API Key (or Use Mock Mode)

You can set your API keys either in a local **`.env`** file (recommended for persistence) or directly in your PowerShell terminal:

#### Method 1: Create a `.env` file in the project root (Recommended)
Create a file named `.env` in the root folder with your preferred provider's key:
```env
# Google Gemini (Default recommended)
GEMINI_API_KEY=AIzaSy...

# Or OpenAI
# OPENAI_API_KEY=sk-proj-...

# Or Anthropic Claude
# ANTHROPIC_API_KEY=sk-ant-api03-...

# Or Force Offline Simulation Mode (Zero API cost)
# CK_DEFAULT_PROVIDER=mock
```

#### Method 2: Set in PowerShell Session
```powershell
# Option A: Google Gemini
$env:GEMINI_API_KEY = "AIzaSy..."

# Option B: OpenAI
$env:OPENAI_API_KEY = "sk-proj-..."

# Option C: Anthropic Claude
$env:ANTHROPIC_API_KEY = "sk-ant-api03-..."

# Option D: Offline Simulation Mode (Zero API cost, zero quota usage)
#### Method 3: Free Web UI Workflow (Zero API Cost)
If you prefer not to use paid API keys or want to generate illustrations using Google's free web interface with saved presets:
- See the dedicated setup guide: [docs/GOOGLE_AI_STUDIO_SETUP_AND_PROMPTING_GUIDE.md](GOOGLE_AI_STUDIO_SETUP_AND_PROMPTING_GUIDE.md) for the exact **3:4 Aspect Ratio**, **Images only** output mode, and copy-paste **System Instruction presets**.
- Run `curiokraft-book prompt export` to export prompts into Markdown.
- Drop generated `.jpg` or `.png` illustrations into `inbox/raw_pages/` and run `curiokraft-book ingest`.

### Step 6: Verify Workspace Health or Scaffold New Laptop
If you ever clone the project to a **new laptop**, or if any local folders were accidentally deleted, run:
```powershell
# Auto-creates all missing directories and template READMEs
curiokraft-book init

# Runs a complete diagnostic check of your assets, manifests, and API keys
curiokraft-book doctor
```

---

## 3. Directory Layout: What to Push to Pip vs What to Keep Local

When packaging and publishing to the global Pip inventory (PyPI), here is the exact breakdown of what gets distributed versus what stays in your private publishing repository:

```text
coloring-book/
│
├── 📦 DISTRIBUTED VIA PIP PACKAGE (PyPI)
│   ├── pyproject.toml              <-- Master build configuration & dependencies
│   ├── README.md                   <-- Package description on PyPI
│   ├── LICENSE                     <-- License terms
│   └── src/curiokraft_book/        <-- ALL Python package source code
│       ├── agents/                 <-- Agent contracts & QA logic
│       ├── compositor/             <-- Typography, Cover & PDF engines
│       ├── orchestrator/           <-- Debate, state machine, batch runner
│       ├── rescue/                 <-- Adaptive Otsu binarizer & margin fitter
│       ├── validators/             <-- Dimensions, margins, grayscale, duplicates
│       ├── cli.py                  <-- Global CLI commands (curiokraft-book)
│       └── __init__.py
│
├── 🔒 LOCAL REPOSITORY ONLY (Do NOT upload to PyPI / Add to .gitignore)
│   ├── dont-delete-alter/          <-- Permanent reference blueprint & contracts
│   ├── manifest/                   <-- Book content database (objects.json, pages.json)
│   ├── assets/                     <-- Your company logos, emblem, fonts
│   ├── config/                     <-- book_config.yaml, agents.yaml
│   ├── inbox/                      <-- Drop-in zone for fresh web-downloaded illustrations (inbox/raw_pages/)
│   ├── generated/                  <-- Archived & raw raster illustrations
│   ├── output/                     <-- Final PDFs, covers, master PNGs, certificates
│   ├── logs/                       <-- Debug, pipeline, and failure logs
│   ├── tests/                      <-- Automated unit tests
│   └── .venv/                      <-- Local virtual environment
```

---

## 4. Disaster Recovery & Moving to a New Laptop

If you ever accidentally delete local files or set up a brand-new computer:

### 1. Re-Scaffolding the Directory Tree
Run:
```powershell
curiokraft-book init
```
This automatically recreates all required folders (`assets/logo/`, `assets/emblem/`, `assets/fonts/`, `config/`, `manifest/`, `output/`, `logs/`, `generated/`) and places drop-in instruction files.

### 2. Checking Workspace Health
Run:
```powershell
curiokraft-book doctor
```
This audits your workspace and prints a table showing:
- Whether custom company logos are detected or using fallback badges.
- Whether TrueType fonts are active.
- Whether the 110-page manifest and object registry are intact.
- Which AI provider (OpenAI, Claude, Gemini, Mock) is currently active.

---

## 5. How to Update Branding / Logos in Future Editions

1. **Replace the image files:**
   - Drop new logo: `assets/logo/curiokraft_logo.png`
   - Drop new emblem: `assets/emblem/curiokraft_emblem.png`
2. **Verify detection:**
   ```powershell
   curiokraft-book doctor
   ```
3. **Re-composite the KDP cover:**
   ```powershell
   curiokraft-book cover build
   ```

---

## 6. How to Build & Publish to Global Pip (PyPI)

Whenever you want to build and release the package to PyPI or your private package registry:

```powershell
# 1. Install standard build tools
pip install build twine

# 2. Build the wheel (.whl) and source tarball (.tar.gz)
python -m build

# (This creates a dist/ folder containing the clean installable package)

# 3. Upload to PyPI (Global Pip Inventory)
twine upload dist/*
```

Once uploaded, anyone (or any server) can simply run:
```bash
pip install curiokraft-coloring-book
curiokraft-book --help
```

---

## 7. Amazon KDP Gutter & Safe Area Margin Specifications

```text
=============================================================================================================
                                     OPEN 2-PAGE SPREAD (17.0 x 11.0 in)
=============================================================================================================
 ◄─────── LEFT-HAND PAGE (Even / Verso) ─────────► ║ ◄──────── RIGHT-HAND PAGE (Odd / Recto) ────────►
 ┌───────────────────────────────────────────────┬─║─┬───────────────────────────────────────────────┐
 │ 0.50" Top Safe Margin                         │ ║ │ 0.50" Top Safe Margin                         │
 │ ┌───────────────────────────────────────────┐ │ ║ │ ┌───────────────────────────────────────────┐ │
 │ │                                           │ │ ║ │ │ [Zone 1: BUBBLE WORD HEADER]              │ │
 │ │                                           │ │ ║ │ │ Y = 240 px (0.80") | 230pt Colorable Font │ │
 │ │                                           │ │ ║ │ │              E L E P H A N T              │ │
 │ │                                           │ │ ║ │ ├───────────────────────────────────────────┤ │
 │ │                                           │ │ ║ │ │                                           │ │
 │ │           LEFT PAGE / BLEED GUARD         │ │ ║ │ │ [Zone 2: MAIN ILLUSTRATION AREA]          │ │
 │ │        (Blank or Light Patterned)         │ │ ║ │ │ Y = 600 px to 3100 px (Centered)          │ │
 │ │                                           │ │ ║ │ │                                           │ │
 │ │                                           │ │ ║ │ │            [ CUTE CHUNKY ]                │ │
 │ │                                           │ │ ║ │ │            [ TODDLER ART ]                │ │
 │ │                                           │ │ ║ │ │                                           │ │
 │ │                                           │ │ ║ │ │                                           │ │
 │ └───────────────────────────────────────────┘ │ ║ │ └───────────────────────────────────────────┘ │
 │ 0.50" Bottom Safe Margin                      │ ║ │ 0.50" Bottom Safe Margin                      │
 └───────────────────────────────────────────────┴─║─┴───────────────────────────────────────────────┘
 ◄─────── 0.50" ──────►◄──────── 0.50" ────────►   ║   ◄──────── 0.50" ────────►◄─────── 0.50" ──────►
   Outside Trim Edge       GUTTER (SPINE)          ║       GUTTER (SPINE)          Outside Trim Edge
  (Mechanical Blade)   (Inside Binding Glue)       ║   (Inside Binding Glue)      (Mechanical Blade)
                                                   ║
                                           CENTER SPINE FOLD
```

For standard $8.5 \times 11\text{ in}$ No-Bleed 110-page printing:
- **Inside Gutter Margin:** $0.500\text{ in} \dots 0.660\text{ in}$ ($150 \dots 200\text{ px}$) — provides $+33\%$ extra buffer beyond Amazon's $0.375\text{ in}$ requirement so ink never curves into the spine.
- **Outer, Top & Bottom Margins:** $0.500\text{ in}$ ($150\text{ px}$) — double Amazon's $0.250\text{ in}$ minimum against mechanical trimming shift.
- **Typography Header Zone:** Positioned at $Y = 240\text{ px}$ ($0.80\text{ in}$ from top) with colorable bubble letters.
- **Toddler Recto Layout:** All main coloring drawings sit on odd (right-hand) pages, ensuring flat, easy coloring.

### 7.1 Preschool Typography Sizing & Letter Spacing Specifications

| Category / Word Length | Example Words | Font Size (Points) | Letter Height (Pixels / Inches) | Inter-Letter Spacing (Tracking) | Outline Stroke Width |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Short Words** ($\le 5$ chars) | `CAT`, `DOG`, `COW`, `CAR`, `BOAT` | **`265 pt`** | **$360\text{ px}$** ($1.20\text{ in}$) | **`46 px`** ($0.15\text{ in}$) | `15 px` ($0.05\text{ in}$) |
| **Medium Words** ($6\text{--}8$ chars) | `BANANA`, `ELEPHANT`, `MONKEY` | **`245 pt`** | **$330\text{ px}$** ($1.10\text{ in}$) | **`40 px`** ($0.13\text{ in}$) | `15 px` ($0.05\text{ in}$) |
| **Long Words** ($9\text{--}11$ chars) | `STRAWBERRY`, `WATERMELON` | **`200 pt`** | **$270\text{ px}$** ($0.90\text{ in}$) | **`30 px`** ($0.10\text{ in}$) | `15 px` ($0.05\text{ in}$) |
| **Very Long Words** ($12\text{--}15$ chars) | `TRACTOR TRAILER`, `HELICOPTER` | **`166 pt`** | **$225\text{ px}$** ($0.75\text{ in}$) | **`24 px`** ($0.08\text{ in}$) | `15 px` ($0.05\text{ in}$) |
| **Spread Titles** ($16+$ chars) | `A - M FIRST WORDS`, `NUMBERS 0 - 5` | **`135 pt`** | **$180\text{ px}$** ($0.60\text{ in}$) | **`20 px`** ($0.07\text{ in}$) | `15 px` ($0.05\text{ in}$) |

---

## 8. Pre-Publication Execution Checklist

Use this checklist every time you run a production book edition:

- [ ] **1. Assets Placed:** `assets/logo/curiokraft_logo.png`, `assets/emblem/curiokraft_emblem.png`, and `assets/fonts/` present.
- [ ] **2. Workspace Health Checked:** Run `curiokraft-book doctor`.
- [ ] **3. Manifest Audited:** Run `curiokraft-book manifest audit` (verifies 0 collisions across 143 items).
- [ ] **4. Unit Tests Passed:** Run `curiokraft-book test validators`.
- [ ] **5. Sample Review Passed:** Run `curiokraft-book sample generate --count 3` and inspect `output/samples/`.
- [ ] **6. Full Batch Produced:** Run `curiokraft-book generate book` (generates all 110 pages in `output/interior_masters/`).
- [ ] **7. Cover Assembled:** Run `curiokraft-book cover build` (creates 17.498x11.250" cover PNG and CMYK PDF).
- [ ] **8. Interior PDF Compiled:** Run `curiokraft-book assemble interior` (creates 110p interior PDF).
- [ ] **9. 18-Point Preflight Certified:** Run `curiokraft-book preflight run` (inspect `output/reports/FINAL_KDP_PREFLIGHT_CERTIFICATE.txt`).
