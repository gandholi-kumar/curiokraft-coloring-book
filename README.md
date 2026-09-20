# CurioKraft Coloring Book Engine

**Multi-Agent AI & Deterministic Production Engine for Amazon KDP Children's Coloring Books**

## Overview
The CurioKraft Coloring Book Engine is an enterprise-grade publication pipeline designed to generate, validate, composite, and preflight high-quality children's coloring books for Amazon KDP.

### Key Features
- **10 Specialized Agents**: Book Director, Design, KDP, Market, Education, Red-Team Critic, Judge, Prompt Engineer, Vision QA, and Book QA.
- **Centralized Database & Object Storage**: ACID-compliant relational persistence (PostgreSQL/SQLite) with S3/R2 storage, Content-Addressable Storage (CAS) SHA-256 deduplication, intelligent cross-book asset reuse, and bi-directional cloud synchronization.
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

## Quick Start CLI Manual (Sequential Execution Flow)

```powershell
# 0. Initialize Workspace & Centralized Database Foundation
curiokraft-book init
curiokraft-book db init
curiokraft-book db migrate-from-fs    # Ingest existing YAML config & pipeline_state.json
curiokraft-book doctor
curiokraft-book db status

# 1. Semantic Object Registry, Manifest Audit & Asset Indexing
curiokraft-book manifest audit
curiokraft-book manifest status --slug curiokraft-vol1
curiokraft-book db sync-assets --dir inbox/raw_pages --type raw_image

# 2. Run Automated Unit Tests on Deterministic Validators & Data Layer
curiokraft-book test validators
python -m pytest tests/test_data_layer.py

# 3. Generate 1 to 5 Configurable Sample Pages for Gate 2 Review
curiokraft-book sample generate --count 3
curiokraft-book sample generate --pages P001,P005,P047

# 4. Produce Full 110-Page Interior Production Batch (with Automatic DB Asset Reuse)
curiokraft-book generate book --slug curiokraft-vol1

# 5. Programmatically Composite KDP Paperback Cover (17.498 x 11.250 in)
curiokraft-book cover build
curiokraft-book cover validate

# 6. Assemble 110-Page Interior PDF (8.5 x 11.0 in, No Bleed, Lossless FlateDecode)
curiokraft-book assemble interior

# 7. Run Full 18-Point Deterministic KDP Preflight Diagnostic & Certificate
curiokraft-book preflight run

# 8. Generate Publishing Metadata & Synchronize Cloud Outbox (Neon + Cloudflare R2)
curiokraft-book kdp generate
curiokraft-book db sync
curiokraft-book db export-to-fs
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
│   ├── cli_db.py                            # Centralized Database & Sync CLI suite
│   ├── data/                                # 🗄️ Relational Data & Object Storage Layer
│   │   ├── base.py                          # Normalized Pydantic models & repository protocols
│   │   ├── models.py                        # Declarative SQLAlchemy ORM models (Postgres/SQLite)
│   │   ├── postgres_store.py                # SQL database manager & concrete repositories
│   │   ├── object_storage.py                # S3/Cloudflare R2 & Local Disk CAS storage
│   │   ├── hybrid_store.py                  # Dual-write coordinator & cross-book asset discovery
│   │   └── sync_engine.py                   # Bi-directional outbox sync (local <-> cloud)
│   ├── orchestrator/                        # Batch runner, 4-round debate engine, state manager, model client
│   ├── compositor/                          # KDP cover, typography, special pages, interior PDF compiler
│   ├── validators/                          # Deterministic 18-point KDP preflight, margins, grayscale, dimensions
│   └── rescue/                              # Adaptive Otsu binarization & safe-margin fitter
│
├── docker-compose.yml                       # 🐳 Local Offline Dev Stack (PostgreSQL 16 + MinIO S3)
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
│   ├── README.md                            # 🗂️ Documentation index — start here
│   ├── setup/                               # ⚙️ Environment & one-time setup
│   ├── workflows/                           # 🚀 Publishing & execution guides
│   ├── architecture/                        # 🏛️ System design, agents & debate engine
│   ├── standards/                           # 📏 Authoritative creative standards
│   ├── reference/                           # 📐 KDP print geometry specifications
│   └── archive/                             # 🗄️ Superseded documentation
│
└── logs/                                    # 📝 Observability, Diagnostics & Traces
```

---

## Documentation & Publishing Guides

* 🗂️ **[Full Documentation Index](docs/README.md)** — Every guide, grouped into setup, workflows, architecture, standards, and reference.
* 🚀 **[Master Publishing Workflows Guide](docs/workflows/PUBLISHING_WORKFLOWS_GUIDE.md)** — **Start here!** Sequential execution flow across Track 1 (Free Web UI) and Track 2 (Automated API Batch).
* 🗄️ **[Centralized Database & Object Storage Guide](docs/architecture/CENTRALIZED_DATABASE_AND_STORAGE_GUIDE.md)** — Relational schema, Neon + Cloudflare R2, offline Docker/SQLite parity, CAS deduplication, and outbox sync.
* ⚙️ **[Google AI Studio Setup & Prompt Presets](docs/setup/GOOGLE_AI_STUDIO_SETUP_AND_PROMPTING_GUIDE.md)** — Browser configuration & prompt presets.
* 📐 **[Amazon KDP Print Specifications](docs/reference/KDP_PRINT_SPECIFICATIONS.md)** — Exact geometry, spine calculations, and barcode safe zones.
* 🏛️ **[Multi-Volume Architecture Guide](docs/architecture/MULTI_VOLUME_ARCHITECTURE_GUIDE.md)** — How to create Volume 2, Volume 3, and themed editions.
* 🧠 **[Multi-Agent System & Debate Engine](docs/architecture/MULTI_AGENT_SYSTEM_AND_DEBATES.md)** — 10 specialist agents, 4-round debates, and audit logs.
* 🗺️ **[Architecture Diagrams](docs/architecture/ARCHITECTURE_DIAGRAMS.md)** — Mermaid diagrams of the pipeline, page lifecycle state machine, module map, and outbox sync.
* ⚡ **[Performance Profiling Guide](docs/workflows/PERFORMANCE.md)** — Profiling decorators, measured overhead, and how to profile a real run.
* 📥 **[Image Inbox Naming Conventions](inbox/raw_pages/README.md)** — File naming rules and fallback candidates.

