# CurioKraft Coloring Book Engine

**Multi-Agent AI & Deterministic Production Engine for Amazon KDP Children's Coloring Books**

## Overview
The CurioKraft Coloring Book Engine is an enterprise-grade publication pipeline designed to generate, validate, composite, and preflight high-quality children's coloring books for Amazon KDP.

### Key Features
- **10 Specialized Agents**: Book Director, Design, KDP, Market, Education, Red-Team Critic, Judge, Prompt Engineer, Vision QA, and Book QA.
- **Manifest-Driven Multi-Volume Scaling**: 100% manifest/config-driven with zero hardcoded state in application code. Volume 2, 3, or themed editions require zero code changes.
- **Decoupled Taxonomy & Curriculum**: `config/curriculum.yaml` (volume-agnostic spread styling, hollow bubble mandates, object purity) + `config/taxonomy.yaml` (category visual templates, living vs inanimate taxonomy).
- **Deterministic Python Validation**: Bounding boxes, margins, 300 DPI, binary black-and-white, zero intentional gray detection, and duplicate prevention.
- **Deterministic Image Rescue Engine**: Adaptive Otsu binarization and margin fitting to prevent wasted image generation quota.
- **Programmatic Compositing**: Lossless typography rendering, KDP cover creation with spine geometry and barcode exclusion, and 110-page interior PDF compilation.
- **Dual-Layer Observability**: Rich terminal UI with clean error summaries and rotating diagnostic loggers (`logs/pipeline.log`, `logs/failures.log`, `logs/debug.log`).

---

## Installation & Environment Setup

Install directly as an editable package using modern `pyproject.toml` (standard packaging, no separate `requirements.txt` needed):

```powershell
# Windows PowerShell
pip install -e .
```

```bash
# macOS / Linux
pip install -e .
```

---

## API Keys & Model Provider Configuration

The engine includes a **Model-Agnostic Client Interface** (`ModelClient`) supporting OpenAI (`gpt-4o`), Anthropic (`claude-3-5-sonnet`), Google Gemini (`gemini-1.5-pro`), and a **Deterministic Offline Simulator**.

### 1. Automatic Provider Detection Priority
When running in `auto` mode (default), the engine detects keys in the following priority order:
1. `OPENAI_API_KEY` present ──► Defaults to **OpenAI (`gpt-4o`)**
2. `ANTHROPIC_API_KEY` present ──► Defaults to **Anthropic (`claude-3-5-sonnet-20240620`)**
3. `GEMINI_API_KEY` or `GOOGLE_API_KEY` present ──► Defaults to **Google Gemini (`gemini-1.5-pro`)**
4. No keys found ──► Defaults to **Deterministic Offline Simulator (`curiokraft-offline-simulator`)** *(0 API cost, zero quota usage)*

### 2. Setting Environment Variables

#### On Windows (PowerShell):
```powershell
# Option A: OpenAI
$env:OPENAI_API_KEY = "sk-proj-..."

# Option B: Anthropic Claude
$env:ANTHROPIC_API_KEY = "sk-ant-api03-..."

# Option C: Google Gemini
$env:GEMINI_API_KEY = "AIzaSy..."

# Option D: Force Offline Simulation Mode (Zero API calls)
$env:CK_DEFAULT_PROVIDER = "mock"
```

#### On Windows (CMD):
```cmd
set OPENAI_API_KEY=sk-proj-...
set ANTHROPIC_API_KEY=sk-ant-api03-...
set GEMINI_API_KEY=AIzaSy...
```

#### On Linux / macOS (Bash / Zsh):
```bash
export OPENAI_API_KEY="sk-proj-..."
export ANTHROPIC_API_KEY="sk-ant-api03-..."
export GEMINI_API_KEY="AIzaSy..."
```

---

## Quick Start CLI Manual

```powershell
# 0. Initialize Workspace on Fresh Installation or Check Health
curiokraft-book init
curiokraft-book doctor

# 1. Semantic Object Registry & Manifest Audit
curiokraft-book manifest audit
curiokraft-book manifest status

# 2. Run Automated Unit Tests on Deterministic Validators
curiokraft-book test validators

# 3. Generate 1 to 5 Configurable Sample Pages for Gate 2 Review
curiokraft-book sample generate --count 3
curiokraft-book sample generate --pages P001,P005,P047

# 4. Produce Full 110-Page Interior Production Batch
curiokraft-book generate book

# 5. Programmatically Composite KDP Paperback Cover (17.498 x 11.250 in)
curiokraft-book cover build

# 6. Assemble 110-Page Interior PDF (8.5 x 11.0 in, No Bleed)
curiokraft-book assemble interior

# 7. Run Full 18-Point Deterministic KDP Preflight Diagnostic & Certificate
curiokraft-book preflight run
```

---

## Repository & Directory Structure

```text
coloring-book/
├── pyproject.toml                           # Modern Pip Packaging & Dependency Configuration
├── README.md                                # Package documentation & directory guide
├── LICENSE                                  # Commercial license
│
├── config/                                  # ⚙️ Volume & Brand Configurations
│   ├── book_config.yaml                     # Master book specifications (8.5x11, 110p, no bleed)
│   ├── agents.yaml                          # 10 Agent system prompts, boundaries & models
│   ├── curriculum.yaml                      # Volume-agnostic spread layout & object purity rules
│   ├── taxonomy.yaml                        # Category keyword sets, visual templates & living taxonomy
│   ├── alphabet_spreads.yaml                # Custom Alphabet spread letter/card definitions
│   └── A-M.md / L-Z.md / A-Z.md             # Alphabet spread prompt generation templates
│
├── manifest/                                # 📋 Curriculum & Semantic Databases
│   ├── objects.json                         # Semantic Object Registry (143 items)
│   ├── pages.json                           # Master 110-page manifest (with spread 'cards' arrays)
│   ├── vocabulary.json                      # Alphabet & Number counting reservations
│   └── semantic_audit_report.json           # Semantic collision audit reports
│
├── assets/                                  # 🎨 Static & Protected Brand Assets
│   ├── logo/curiokraft_logo.png             # Original CurioKraft vector/lossless logo
│   ├── emblem/curiokraft_emblem.png         # Original CurioKraft brand emblem
│   └── fonts/Fredoka-Bold.ttf               # Licensed child-friendly vector bubble font
│
├── src/curiokraft_book/                     # 🐍 Main Python Package Root
│   ├── cli.py                               # Global CLI entrypoint (Typer/Rich)
│   ├── orchestrator/                        # Batch runner, 4-round debate engine, state manager, model client
│   ├── compositor/                          # KDP cover, typography, special pages, interior PDF compiler
│   ├── validators/                          # Deterministic 18-point KDP preflight, margins, grayscale, dimensions
│   └── rescue/                              # Adaptive Otsu binarization & safe-margin fitter
│
├── inbox/                                   # 📥 User Drop Inbox (Zero API Cost Workflow)
│   ├── raw_pages/                           # Drop interior illustrations here (e.g. raw_p006.png)
│   │   └── README.md                        # Inbox drop targets & naming conventions guide
│   ├── front_cover.png                      # Front cover artwork drop target
│   └── back_cover.png                       # Back cover artwork drop target
│
├── generated/                               # 🖼️ Working Image & Prompt Artifacts
│   ├── raw_pages/                           # Archived & raw generated illustrations
│   └── prompts_export.md                    # Master exported copy-paste prompts
│
├── output/                                  # 📦 Final Publication Deliverables
│   ├── interior_masters/                    # 110 master PNGs (300 DPI with typography)
│   ├── interior/                            # Final Print-Ready Interior PDF
│   ├── cover/                               # Final Cover Master PNG + CMYK PDF
│   └── reports/                             # KDP Preflight certificates & audit logs
│
├── docs/                                    # 📚 Comprehensive Documentation Suite
│   ├── PUBLISHING_WORKFLOWS_GUIDE.md        # 🚀 Master Interactive Publishing Workflows Guide
│   ├── GOOGLE_AI_STUDIO_SETUP_AND_PROMPTING_GUIDE.md # ⚙️ AI Studio Sidebar & System Presets
│   ├── KDP_PRINT_SPECIFICATIONS.md          # 📐 KDP Print Geometry & Barcode Specifications
│   ├── MULTI_VOLUME_ARCHITECTURE_GUIDE.md   # 🏛️ Multi-Volume Scaling (Vol 2, Vol 3) & Decoupling
│   ├── MULTI_AGENT_SYSTEM_AND_DEBATES.md    # 🧠 Complete Multi-Agent Council, Contracts & Debates
│   └── ONE_TIME_SETUP_AND_PREPUBLISH_CHECKLIST.md # ✅ 15-Minute Pre-Publish Checklist
│
└── logs/                                    # 📝 Observability, Diagnostics & Traces
```

---

## Documentation & Publishing Guides

* 🚀 **[Master Publishing Workflows Guide](docs/PUBLISHING_WORKFLOWS_GUIDE.md)** — **Start here!** Clear separation between **Track 1 (Free Google AI Studio Web Workflow)** and **Track 2 (Automated API Batch)**.
* ⚙️ **[Google AI Studio Setup & Prompt Presets](docs/GOOGLE_AI_STUDIO_SETUP_AND_PROMPTING_GUIDE.md)** — Browser configuration & prompt presets.
* 📐 **[Amazon KDP Print Specifications](docs/KDP_PRINT_SPECIFICATIONS.md)** — Exact geometry, spine calculations, and barcode safe zones.
* 🏛️ **[Multi-Volume Architecture Guide](docs/MULTI_VOLUME_ARCHITECTURE_GUIDE.md)** — How to create Volume 2, Volume 3, and themed editions.
* 🧠 **[Multi-Agent System & Debate Engine](docs/MULTI_AGENT_SYSTEM_AND_DEBATES.md)** — 10 specialist agents, 4-round debates, and audit logs.
* 📥 **[Image Inbox Naming Conventions](inbox/raw_pages/README.md)** — File naming rules and fallback candidates.

