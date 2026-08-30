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
