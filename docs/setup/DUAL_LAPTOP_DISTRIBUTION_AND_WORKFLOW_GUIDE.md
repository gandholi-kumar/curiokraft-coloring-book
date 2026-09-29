# Dual-Laptop Distribution & Publishing Workflow Guide

This guide explains how to package the **CurioKraft Coloring Book Engine** on your primary development machine (**Laptop 1**) and install it globally as a standalone CLI tool on your secondary machine (**Laptop 2**), enabling you to produce Amazon KDP books from scratch **without downloading any source code**.

---

## 🏗️ Architecture & Roles

```
┌────────────────────────────────────────┐       Transfer Wheel       ┌────────────────────────────────────────┐
│               LAPTOP 1                 │       =============►       │               LAPTOP 2                 │
│         (Development Machine)          │   (.whl standalone file)   │          (Production Machine)          │
├────────────────────────────────────────┤                            ├────────────────────────────────────────┤
│ • Full Git repository & source code   │                            │ • NO source code required              │
│ • Package builder (`python -m build`)  │                            │ • Global CLI tool (`pipx`)             │
│ • Builds self-contained `.whl` package │                            │ • Creates new empty book workspaces    │
│   (bundles configs, manifests, fonts)  │                            │ • Runs prompts, ingestion, cover, PDF  │
└────────────────────────────────────────┘                            └────────────────────────────────────────┘
```

---

## 💻 Phase 1: On Laptop 1 (Build the Wheel Package)

On your development laptop where the repository exists, build the self-contained wheel package.

### Step 1: Open PowerShell in the Repository Root
```powershell
cd H:\Store\CurioKraft\Research_Dev\curiokraft-coloring-book
```

### Step 2: Build the Wheel
```powershell
# 1. Ensure build tool is installed
.\.venv\Scripts\python.exe -m pip install build

# 2. Build the standalone wheel
.\.venv\Scripts\python.exe -m build --wheel
```

### Step 3: Locate the Generated Wheel
The build produces a single self-contained `.whl` file in the `dist/` directory:
```
dist/curiokraft_coloring_book-1.0.0-py3-none-any.whl
```
*(Size: ~1.1 MB. Contains all required code, core configs, manifests, licensed preschool fonts, brand logos, and templates).*

### Step 4: Transfer to Laptop 2
Copy `curiokraft_coloring_book-1.0.0-py3-none-any.whl` to Laptop 2 via:
* USB Flash Drive
* Google Drive / OneDrive / Dropbox
* Local network file share

---

## 💻 Phase 2: On Laptop 2 (One-Time Global Setup)

On Laptop 2, you do **not** need Git, Git clones, or the source repository. You only need Python (>= 3.10).

### Step 1: Install `pipx` (Global Python App Manager)
`pipx` installs Python CLI tools in their own isolated environments while making their commands available globally across all terminals and folders.

Open PowerShell on Laptop 2 and run:
```powershell
# 1. Install pipx
python -m pip install --user pipx

# 2. Add pipx to your system PATH
python -m pipx ensurepath
```
> [!IMPORTANT]
> Close and re-open PowerShell after running `ensurepath` so the new system PATH takes effect.

### Step 2: Install the CurioKraft Wheel Globally
Navigate to the folder where you placed the `.whl` file and run:
```powershell
pipx install .\curiokraft_coloring_book-1.0.0-py3-none-any.whl
```

### Step 3: Verify the Global Installation
From any folder or terminal on Laptop 2, run:
```powershell
curiokraft-book --help
```
You should see the full CurioKraft CLI menu with all subcommands (`init`, `doctor`, `prompt`, `ingest`, `cover`, `assemble`, `preflight`, `kdp`, etc.).

---

## 📖 Phase 3: Creating a New Book Project on Laptop 2

Whenever you are ready to produce a new coloring book on Laptop 2, follow these steps:

### Step 1: Create a Clean Book Directory
```powershell
mkdir "C:\MyBooks\Tiny-Hands-Coloring-Book"
cd "C:\MyBooks\Tiny-Hands-Coloring-Book"
```

### Step 2: Initialize the Workspace
Run `curiokraft-book init` to unpack all configurations, manifests, fonts, and directories:

```powershell
# Option A: Standard Non-Bleed (Default, clean 0.50" white margins)
curiokraft-book init --name "Tiny Hands Color & Learn" --imprint "CurioKraft"

# Option B: Full-Bleed (Edge-to-edge environmental illustrations)
curiokraft-book init --name "Ocean Expeditions" --imprint "CurioKraft" --preset bleed
```

#### What `curiokraft-book init` automatically creates:
```text
Tiny-Hands-Coloring-Book/
├── COMMANDS.md              # 📖 Full step-by-step CLI cheatsheet
├── .env                     # 🔑 API key configuration (ready for keys)
├── .env.example             # 🔑 Template API key references
├── .gitignore               # 🛡️ Excludes big PDFs & private KDP forms
├── config/
│   ├── book_config.yaml     # ⚙️ Active book configuration
│   ├── book_config_bleed.yaml     # Full-bleed layout preset reference
│   ├── book_config_non_bleed.yaml # Non-bleed layout preset reference
│   ├── curriculum.yaml      # Layout & bubble lettering styling rules
│   ├── taxonomy.yaml        # Living vs inanimate object categories
│   ├── agents.yaml          # System prompts for the 10 specialist agents
│   └── A-Z.md               # Alphabet prompt template
├── manifest/
│   ├── pages.json           # 📋 Master 110-page manifest
│   ├── objects.json         # 📋 143-item semantic object dictionary
│   └── vocabulary.json      # 📋 Word reservation registry
├── assets/
│   ├── fonts/               # 🔤 Fredoka-Bold.ttf (licensed preschool font)
│   ├── logo/                # 🎨 curiokraft_logo.PNG
│   └── emblem/              # 🎨 curiokraft_emblem.png
├── inbox/
│   ├── raw_pages/           # 📥 Drop interior illustrations here
│   ├── kdp_forms/           # 📥 Drop saved KDP HTML forms here
│   └── special_assets/      # 📥 Drop mascot or custom scenes here
├── generated/raw_pages/     # 🖼️ Rescued & processed artwork
├── output/
│   ├── interior_masters/    # 🖼️ 110 master PNGs (300 DPI with typography)
│   ├── interior/            # 📦 Final compiled 110-page interior PDF
│   ├── cover/               # 📦 Final KDP wrap cover (PNG + CMYK PDF)
│   ├── reports/             # 🩺 18-point preflight certificates
│   └── kdp/                 # 🚀 1-click KDP HTML submission dashboard
└── logs/                    # 📝 Diagnostic pipeline traces
```

### Step 3: Run the Health Audit
```powershell
curiokraft-book doctor
```
All checks (Brand Logo, Emblem, Active Font, Page Manifest, Object Registry, Book Config, and KDP Form Privacy) will report `[VALID]` or `[FOUND]`.

---

## 🎨 Phase 4: Day-to-Day Production Workflow (Manual Web Drops)

### Step 1: Export AI Generation Prompts
```powershell
curiokraft-book prompt export
```
* Opens or inspects `generated/prompts_export.md`.
* Copy each prompt into your preferred generator (Google AI Studio, Midjourney, DALL-E, etc.).

### Step 2: Drop Images into Inbox Targets
Save your downloaded images directly into your book project folders:

| Destination Drop Path | Expected Filenames | What it is for |
| :--- | :--- | :--- |
| `inbox/raw_pages/` | `raw_p005_apple.png`<br>`p005.png`<br>`apple.png` | Interior coloring pages (Pages 1 to 110) |
| `inbox/front_cover.png` | `front_cover.png` | Front cover hero artwork |
| `inbox/back_cover.png` | `back_cover.png` | Back cover background artwork |
| `inbox/special_assets/` | `tiny_mascot.png` | Mascot illustration (if mascot enabled) |

### Step 3: Ingest & Process Raw Pages
```powershell
curiokraft-book ingest
```
* Automatically performs Otsu binarization, fits to safe margins, and overlays lossless preschool vector typography.
* Outputs ready-to-print master PNGs to `output/interior_masters/page_XXX.png`.

### Step 4: Build & Validate the KDP Cover
```powershell
# 1. Composite the 17.498 x 11.250 in cover
curiokraft-book cover build

# 2. Validate KDP specifications (margins, barcode exclusion, dimensions)
curiokraft-book cover validate
```
* **Outputs:**
  * `output/cover/TINY_HANDS_COLOR_AND_LEARN_Cover_300DPI.png`
  * `output/cover/TINY_HANDS_COLOR_AND_LEARN_Cover_CMYK.pdf`

### Step 5: Assemble the 110-Page Interior PDF
```powershell
curiokraft-book assemble interior
```
* Compiles all 110 pages into a lossless, print-ready PDF at 8.5 × 11.0 in (300 DPI).
* **Output:** `output/interior/TINY_HANDS_COLOR_AND_LEARN_Interior_110p.pdf`

### Step 6: Run 18-Point Preflight Diagnostic
```powershell
curiokraft-book preflight run
```
* Validates trim dimensions, DPI, page count, margin compliance, and generates the official certificate:
  `output/reports/FINAL_KDP_PREFLIGHT_CERTIFICATE.txt`

### Step 7: Generate KDP Publishing Metadata
```powershell
curiokraft-book kdp generate
```
* Automatically opens `output/kdp/kdp_submission_helper.html` in your browser.
* Provides 1-click copy buttons for Title, Subtitle, 7 Amazon Keywords, BISAC Categories, and formatted HTML Description.

---

## 🔄 Updating to a Newer Engine Version on Laptop 2

Whenever you make improvements or bug fixes on Laptop 1:

1. **On Laptop 1:**
   Rebuild the wheel:
   ```powershell
   .\.venv\Scripts\python.exe -m build --wheel
   ```
2. **Transfer** the new `.whl` to Laptop 2.
3. **On Laptop 2:**
   Force-reinstall the global package:
   ```powershell
   pipx install --force path\to\curiokraft_coloring_book-1.0.0-py3-none-any.whl
   ```
Your existing project folders remain untouched, and all future `curiokraft-book init` and CLI commands immediately benefit from the updated engine logic!

---

## ❓ Frequently Asked Questions & Troubleshooting

### Q1: How do I switch between Bleed and Non-Bleed layouts?
Both presets are saved in your `config/` directory. Simply copy the desired preset over `config/book_config.yaml`:
```powershell
# Switch to Full-Bleed:
Copy-Item config/book_config_bleed.yaml config/book_config.yaml -Force

# Switch back to Non-Bleed:
Copy-Item config/book_config_non_bleed.yaml config/book_config.yaml -Force
```

### Q2: What if `curiokraft-book doctor` reports missing files?
Run `curiokraft-book doctor` to see which specific file is missing. In any fresh directory, `curiokraft-book init` will restore all required assets and manifests automatically.

### Q3: Do I need an internet connection on Laptop 2?
No! Once installed via `pipx`, all deterministic validation, Otsu binarization, cover compositing, interior PDF assembly, and preflight certification run **100% offline locally**. An internet connection is only needed if you configure an API key for automated cloud generation.
