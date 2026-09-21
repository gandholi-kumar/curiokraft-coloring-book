# CurioKraft — First-Time User Onboarding & End-to-End Execution Guide

Welcome to **CurioKraft**, an enterprise-grade, multi-agent AI and deterministic publishing pipeline engineered for **Amazon KDP 8.5" × 11" preschool coloring books**.

This comprehensive reference manual walks you through the entire end-to-end lifecycle as a first-time user: from cloning the repository, provisioning your database and object storage, generating theme configurations and prompts, through to ingesting illustrations, compiling print-ready interior master PDFs, and synchronizing to the cloud.

---

## 📑 Table of Contents

1. [Architectural Overview & Key Concept](#1-architectural-overview--key-concepts)
2. [Frequently Asked Question: Does Code Auto-Save Images on Drop?](#2-faq-does-the-code-auto-save-images-when-dropped-into-folders)
3. [Step 1: Cloning & Python Environment Setup](#step-1-cloning--python-environment-setup)
4. [Step 2: Environment Configuration (.env)](#step-2-environment-configuration-env)
5. [Step 3: Initializing the Database & Storage Layer](#step-3-initializing-the-database--storage-layer)
6. [Step 4: Book Configuration & Theme Manifest (Saving to DB)](#step-4-book-configuration--theme-manifest-saving-to-db)
7. [Step 5: Multi-Agent Prompt Architecture & Pre-Generation Debates](#step-5-multi-agent-prompt-architecture--pre-generation-debates)
8. [Step 6: Generating & Saving Master Prompts to Database](#step-6-generating--saving-master-prompts-to-database)
9. [Step 7: Ingesting & Saving Illustrations (Image Workflows)](#step-7-ingesting--saving-illustrations-image-workflows)
10. [Step 8: Compositing Interior Masters & Compiling Print-Ready PDF](#step-8-compositing-interior-masters--compiling-print-ready-pdf)
11. [Step 9: Full-Wrap Cover Generation & 18-Point Preflight Certification](#step-9-full-wrap-cover-generation--18-point-preflight-certification)
12. [Step 10: Publishing Metadata & Cloud Synchronization](#step-10-publishing-metadata--cloud-synchronization)
13. [CLI Command Reference Lifecycle Cheat Sheet](#cli-command-reference-lifecycle-cheat-sheet)

---

## 1. Architectural Overview & Key Concepts

CurioKraft bridges deterministic typography compositing with generative AI line art, backed by a **Dual-Write Centralized Data Architecture**:

```
                                  ┌────────────────────────────────┐
                                  │   CurioKraft CLI / Pipeline    │
                                  └───────────────┬────────────────┘
                                                  │
                                          HybridDataStore
                                                  │
                        ┌─────────────────────────┴─────────────────────────┐
                        ▼                                                   ▼
            ┌───────────────────────┐                           ┌───────────────────────┐
            │  Relational Database  │                           │   Object & Blob Store │
            │ (SQLite / PostgreSQL) │                           │   (Local / R2 / MinIO)│
            ├───────────────────────┤                           ├───────────────────────┤
            │ • books               │                           │ • raw_pages/          │
            │ • pages (110 records) │                           │ • interior_masters/   │
            │ • prompts             │                           │ • interior/*.pdf      │
            │ • media_assets (CAS)  │                           │ • cover/*.pdf         │
            │ • outbox_events       │                           │ (SHA-256 CAS Dedupe)  │
            └───────────────────────┘                           └───────────────────────┘
                        │                                                   │
                        └─────────────────────────┬─────────────────────────┘
                                                  │
                                        Offline Outbox Sync
                                                  │
                                                  ▼
                                    ┌───────────────────────────┐
                                    │    Cloud Infrastructure   │
                                    │   Neon DB + Cloudflare R2 │
                                    └───────────────────────────┘
```

- **Relational Tables (`SQLDatabaseManager`)**: Tracks metadata, 110-page progression, prompt revisions, QA scores, and outbox synchronization events.
- **Content-Addressable Storage (CAS)**: Every image and PDF is indexed by its **SHA-256 hash**. Identical files across volumes are never stored twice.
- **Dual-Write Backward Compatibility**: All changes write simultaneously to both the SQL database and legacy `output/pipeline_state.json`.

---

## 2. FAQ: Does the Code Auto-Save Images When Dropped into Folders?

> [!IMPORTANT]
> **Direct Answer:** In the current flow, **NO**, simply dropping or copying images into `inbox/raw_pages/` or `output/` does **not** instantly trigger a background filesystem hook into the database in real-time. Filesystem drops are passive operating system operations.

### How Images Get Registered & Saved into the Database:

Images are deterministically saved into the database (`media_assets` table) and storage backend via **two robust mechanisms**:

### Mechanism A: Explicit Indexing & Sync Command (Recommended after manual drops)
Whenever you download batch illustrations from Google AI Studio Web or another tool and drop them into `inbox/raw_pages/`, run:
```powershell
# Index raw illustrations into database
curiokraft-book db sync-assets --dir inbox/raw_pages --type raw_image

# Index generated composite interior masters
curiokraft-book db sync-assets --dir output/interior_masters --type composite_master

# Index final interior PDFs
curiokraft-book db sync-assets --dir output/interior --type interior_pdf

# Index final cover PDFs
curiokraft-book db sync-assets --dir output/cover --type cover_pdf
```
**What this command does:**
1. Crawls the target directory for `.png` and `.jpg` files.
2. Calculates the **SHA-256 CAS digest** for each file.
3. Inspects image dimensions (e.g. 2550 × 3300 px), DPI (300), and color mode (`L` grayscale or `RGB`).
4. Associates the asset with the corresponding `page_id` (e.g., `raw_p005_banana.png` maps to page `P005`).
5. Persists a `MediaAssetRecord` into the `media_assets` table and enqueues an `outbox_events` record for cloud sync.

### Mechanism B: Automated Pipeline Hooks (Zero manual intervention during runs)
Whenever you execute any pipeline command:
- `curiokraft-book sample generate --pages P001,P005`
- `curiokraft-book generate book`
- `curiokraft-book assemble interior`
- `curiokraft-book cover build`

The internal batch runner and compositors automatically call `store.register_media_asset(...)`:
- The raw image is read and registered into `media_assets`.
- The composite interior master (`output/interior_masters/page_xxx.png`) is saved to disk and registered into `media_assets`.
- The assembled PDF (`output/interior/...Interior_110p.pdf`) is compiled and registered into `media_assets`.

---

## Step 1: Cloning & Python Environment Setup

Clone the repository and prepare your local Python environment:

```powershell
# 1. Clone the repository
git clone https://github.com/curiokraft/curiokraft-coloring-book.git
cd curiokraft-coloring-book

# 2. Create Python virtual environment (Python 3.11 - 3.14 supported)
python -m venv .venv

# 3. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 4. Install the package in editable mode with database dependencies
pip install -e .

# 5. Verify the installation
curiokraft-book --help
```

You will see the top-level commands: `manifest`, `sample`, `generate`, `assemble`, `cover`, `preflight`, `prompt`, `debate`, `kdp`, and `db`.

---

## Step 2: Environment Configuration (.env)

Create a `.env` file in the root of `curiokraft-coloring-book/` based on your desired infrastructure:

### Option A: Embedded Zero-Dependency Local Mode (Recommended for Starters)
No setup required! CurioKraft defaults to local embedded SQLite at `output/curiokraft.db` and stores binary images on your local hard drive:
```env
# .env (Zero Setup Local Mode)
DATABASE_URL=sqlite:///output/curiokraft.db
STORAGE_BACKEND=local
LOCAL_STORAGE_ROOT=output/storage
```

### Option B: Local Docker Production-Parity Mode (PostgreSQL 16 + MinIO)

> [!NOTE]
> **Prerequisites**: [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) must be installed and running on your system.
> If Docker is not installed on your machine, use **Option A (SQLite)** which works immediately out-of-the-box with zero installation!

#### 1. Where to Execute Docker Compose:
Open PowerShell or your terminal and navigate to the project root directory where [docker-compose.yml](file:///h:/Store/CurioKraft/Research_Dev/curiokraft-coloring-book/docker-compose.yml) is located:
```powershell
cd H:\Store\CurioKraft\Research_Dev\curiokraft-coloring-book
```

#### 2. How to Start the Containers:
Run Docker Compose in detached mode (`-d`):
```powershell
docker compose up -d
```
*This spins up two containers:*
- `curiokraft-postgres`: PostgreSQL 16 on port `5432` (database: `curiokraft`, user: `postgres`, password: `postgrespassword`)
- `curiokraft-minio`: MinIO S3 API on port `9000`, Web Console on port `9001` (user: `minioadmin`, password: `minioadminpassword`)

Verify both containers are healthy:
```powershell
docker compose ps
```
*(Optional: You can view the MinIO web dashboard by opening `http://localhost:9001` in your browser).*

#### 3. Configure `.env` for Option B:
Open or create `.env` in the project root (`curiokraft-coloring-book/.env`) and add:
```env
# Database Connection (PostgreSQL 16 in Docker)
DATABASE_URL=postgresql+psycopg://postgres:postgrespassword@localhost:5432/curiokraft

# Object / Blob Storage (MinIO in Docker)
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadminpassword
S3_BUCKET_NAME=curiokraft-assets
S3_REGION=us-east-1
```

### Option C: Cloud Production Mode (Neon PostgreSQL + Cloudflare R2)
```env
# .env (Cloud Production Mode)
DATABASE_URL=postgresql+psycopg://<user>:<password>@<neon-hostname>/curiokraft_prod?sslmode=require
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://<cloudflare-account-id>.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=<r2_access_key>
S3_SECRET_ACCESS_KEY=<r2_secret_key>
S3_BUCKET_NAME=curiokraft-assets-prod
S3_REGION=auto
```

*(Optional)* If you plan to use automated AI generation rather than the free web UI, add your provider keys:
```env
GEMINI_API_KEY=your_gemini_api_key_here
ANTHROPIC_API_KEY=your_claude_api_key_here
```

---

## Step 3: Initializing the Database & Storage Layer

Now, initialize your relational database and verify system readiness:

```powershell
# 1. Initialize the SQL database schema (creates tables: books, pages, prompts, media_assets, logs, outbox)
curiokraft-book db init

# 2. Check the database connection and current asset count
curiokraft-book db status

# 3. If you have an existing workspace with manifest/pages.json or pipeline_state.json, migrate it:
curiokraft-book db migrate-from-fs

# 4. Push and index local master images into MinIO and PostgreSQL:
curiokraft-book db sync-assets --dir output/interior_masters --type composite_master
curiokraft-book db sync-assets --dir output/interior --type interior_pdf
curiokraft-book db sync-assets --dir output/cover --type cover_asset

# 5. Pull and verify assets from MinIO and PostgreSQL down to local machine:
curiokraft-book db pull-assets --dir verification_download
```

Expected output of `curiokraft-book db status`:
```text
                     CurioKraft Centralized Database Status                     
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Property                   ┃ Value                                           ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Database Engine            │ postgresql+psycopg://postgres:***@localhost:5432│
│ Storage Backend            │ S3StorageBackend (MinIO)                        │
│ Active Book                │ OCEAN EXPEDITIONS & AQUATIC BEINGS              │
│                            │ (curiokraft-aquatic_vol1)                       │
│ Total Books                │ 1                                               │
│ Total Pages in Active Book │ 110                                             │
│   Pages                    │ 110                                             │
│ Total Prompts Stored       │ 0                                               │
│ Total Media Assets Stored  │ 59                                              │
└────────────────────────────┴─────────────────────────────────────────────────┘
```

### Visualizing Database & Object Storage in Browser

| Service | Browser URL | Credentials | What You Can Inspect |
|:---|:---|:---|:---|
| **pgAdmin 4** | [http://localhost:5050](http://localhost:5050) | `admin@example.com` / `admin` | Connect to host `postgres` (port `5432`). View `books`, `pages`, `media_assets`, and `sync_outbox` tables. |
| **MinIO Console** | [http://localhost:9001](http://localhost:9001) | `minioadmin` / `minioadminpassword` | Browse bucket `curiokraft-assets`, view high-res image previews, inspect SHA-256 metadata, and create share links. |

### Pulling Assets for Verification (`db pull-assets`)
To download files stored in MinIO and verify that their local bytes match the database records without pushing:
```powershell
# Pull interior PDF to verify locally:
curiokraft-book db pull-assets --dir verify_folder --type interior_pdf

# Pull cover artwork and PDF:
curiokraft-book db pull-assets --dir verify_folder --type cover_asset

# Pull all assets for a specific volume slug:
curiokraft-book db pull-assets --slug curiokraft-aquatic_vol2 --dir vol2_verify
```
Each file is streamed from MinIO and verified against its PostgreSQL SHA-256 content hash:
```text
  [VERIFIED] page_001.png (2,305,216 bytes | SHA-256 match)
  [VERIFIED] TINY_HANDS_COLOR_AND_LEARN_Cover_300DPI.png (13,954,329 bytes | SHA-256 match)
```

---

## Step 4: Book Configuration, Manifest Mapping & Database Ingestion

Understanding how your book configuration, manifest files, and the database interconnect is essential for managing single and multi-volume publishing.

### 1. `curiokraft-book init` vs `curiokraft-book db init`
It is important to distinguish between these two initialization commands:
* **`curiokraft-book init` (Filesystem Scaffolding)**:
  Prepares all local workspace directories (`assets/`, `config/`, `manifest/`, `inbox/raw_pages/`, `output/interior_masters/`, `output/interior/`, `output/cover/`) and creates starter template configuration files if they are missing. Run this once when setting up a fresh repository workspace.
* **`curiokraft-book db init` (Database Schema Creation)**:
  Connects to your active database engine (PostgreSQL 16 in Docker or embedded SQLite) and executes DDL to create the 6 relational tables: `books`, `pages`, `prompts`, `media_assets`, `pipeline_logs`, and `sync_outbox`. Run this once after starting your database or whenever resetting the database schema.

### 2. The Configuration File: `config/book_config.yaml`
`config/book_config.yaml` is the **single source of truth** for your publication. *(Note: Any references to `curiokraft.yaml` in older notes referred to this file; always use `config/book_config.yaml`)*.

```yaml
book:
  title: "OCEAN EXPEDITIONS & AQUATIC BEINGS"
  subtitle: "Toddler & Preschool Underwater Coloring Book"
  volume: "aquatic_vol1"                          # Generates unique DB slug: curiokraft-aquatic_vol1
  manifest: "manifest/pages_aquatic_vol1.json"    # Points to active manifest for this volume
  target_audience:
    age_min: 1
    age_max: 4
  interior:
    page_count: 110
    trim_size:
      width_inches: 8.5
      height_inches: 11.0
    margins:
      inside_gutter_inches: 0.50
      outside_inches: 0.375
```

### 3. Maintaining Manifests for Different Volumes
**Do you have to maintain only a single `manifest/pages.json` file?**
**No!** You can maintain dedicated manifest files for each volume (e.g., `manifest/pages_aquatic_vol1.json`, `manifest/pages_vol2.json`, `manifest/pages_safari_vol1.json`).

* In `config/book_config.yaml`, simply point the `manifest:` key to the manifest file for the volume you are actively working on:
  ```yaml
  manifest: "manifest/pages_vol2.json"
  ```
* When you execute:
  ```powershell
  curiokraft-book db migrate-from-fs
  ```
  The ingestion engine automatically:
  1. Reads the active volume slug from `config/book_config.yaml` (e.g. `curiokraft-vol2`).
  2. Creates or selects that book record in the PostgreSQL `books` table.
  3. Loads the specified manifest JSON file (`manifest/pages_vol2.json`) and inserts its 110 pages into the `pages` table linked to that volume's `book_id`.
  4. Ingests any existing execution state from `pipeline_state.json`.

### 4. Offline Resilience Guarantee (Zero-Breakage)
**What happens if Docker, PostgreSQL, or MinIO is offline or unavailable?**
CurioKraft is built with zero-breakage offline resilience:
* If PostgreSQL is offline or `DATABASE_URL` is omitted, the engine automatically falls back to local embedded SQLite at `output/curiokraft.db` and stores binary CAS files in `output/storage/`.
* If you operate entirely without a database, the core pipeline functions (prompt export, ingestion, special pages rendering, cover building, interior assembly, and preflight) operate directly against the filesystem files (`config/book_config.yaml`, `manifest/pages.json`, and `pipeline_state.json`). You can work completely offline on a plane or train with zero dependencies.

### 5. What `manifest audit` and `manifest status` Do

#### `curiokraft-book manifest audit`
Performs an automated deterministic scan of the entire curriculum manifest to guarantee zero errors before generation begins:
* **Duplicate Detection**: Verifies that no vocabulary word or canonical object is repeated across alphabet letters, counting numbers, or coloring spreads.
* **Page Parity**: Verifies all 110 pages follow the strict odd/even alternating rule (Odd = Coloring Page, Even = Blank Bleed-Guard Backing).
* **Expected Output**:
  ```text
  [SUCCESS] Manifest curriculum audit PASSED:
    - Total Pages: 110
    - Vocabulary Collisions: 0
    - Alternating Spread Parity: 100% Compliant
  ```

#### `curiokraft-book manifest status`
Inspects the database (or filesystem state) for the active volume and displays a lifecycle summary:
```powershell
curiokraft-book manifest status
# Or inspect another volume explicitly:
curiokraft-book manifest status --slug curiokraft-aquatic_vol1
```
* **Expected Output**:
  ```text
  ============================================================
  Book: OCEAN EXPEDITIONS & AQUATIC BEINGS (curiokraft-aquatic_vol1)
  Total Pages: 110
  ------------------------------------------------------------
  DRAFT:                    0
  PROMPT_GENERATED:         0
  ILLUSTRATION_GENERATED:   0
  APPROVED:                 110
  ============================================================
  ```
To see a line-by-line breakdown of every single page (page ID, display title, current state, illustration hash), run:
```powershell
curiokraft-book manifest details
```

---

## Step 5: Multi-Agent Prompt Architecture & Pre-Generation Debates

Before sending any prompt to an image generator, CurioKraft runs an automated **4-Round Pre-Generation Multi-Agent Debate**:

1. **Child Development Specialist**: Proposes single central subject, recognizable silhouette, zero abstract visual noise.
2. **KDP Print Engineer**: Enforces minimum 3.0pt outer line weight, 1.5pt inner line weight, 0.5" gutter safety margin, pure white `#FFFFFF` background.
3. **Typography & Layout Designer**: Ensures 20% canvas headroom for preschool trace cards and display labels.
4. **The Red-Team Critic & Judge**: Identifies anti-pattern risks (grayscale shading, thin lines, complex scenes) and issues a 100-point rubric score.

### Inspecting a Prompt & Debate for a Specific Page:
```powershell
# Display optimized copy-paste prompt for Page 5 (e.g. Clownfish)
curiokraft-book prompt show --page P005

# Inspect the specialist proposals, critique, and Judge score
curiokraft-book debate show --page P005
```

---

## Step 6: Generating & Saving Master Prompts to Database

To generate the complete suite of prompts and persist them directly into the database:

```powershell
# Export all prompts to Markdown, JSON, and persist into database `prompts` table
curiokraft-book prompt export --format all --out generated/prompts_export.md --json-out generated/prompts_export.json
```

**What happens during this step:**
1. Multi-agent debate synthesizes:
   - Front Cover master illustration prompt
   - Back Cover artwork prompt
   - Volume Mascot prompt
   - Perimeter Frame prompt for milestone pages
   - All 52 core coloring illustration prompts
2. **Database Persistence**: All prompt items are immediately inserted into the SQL `prompts` table with prompt type, positive prompt, negative prompt, aspect ratio (`3:4`), and temperature (`0.9`).
3. **Artifacts Exported**:
   - `generated/prompts_export.md`: Ready for 1-click copying into web UIs.
   - `generated/prompts_export.json`: Structured manifest.
   - `logs/agent_debates_log.md`: Full debate transcript and Judge audit scores.

Verify prompts are in the DB:
```powershell
curiokraft-book db status
```
*(Total Prompts Stored will now reflect the persisted prompts!)*

---

## Step 7: Ingesting & Saving Illustrations (Image Workflows)

You can produce illustrations via either the **Free Web UI Workflow** or the **Automated API Workflow**:

### Workflow A: Free Google AI Studio Web UI (Zero API Cost)
1. Open [Google AI Studio](https://aistudio.google.com/) or Gemini.
2. Configure settings: **Aspect Ratio:** `3:4` | **Format:** Images only | **Temperature:** `0.9`.
3. Copy prompts from `generated/prompts_export.md`.
4. Download the generated illustrations and drop them into `inbox/raw_pages/` using canonical names:
   - `raw_p005_clownfish.png` (or `clownfish.png`)
   - `raw_p007_sea_turtle.png` (or `sea_turtle.png`)
5. **Index into the Database:**
   ```powershell
   curiokraft-book db sync-assets --dir inbox/raw_pages --type raw_image
   ```

### Workflow B: Automated Multi-Agent Generation (API Mode)
If you have `GEMINI_API_KEY` set, run:
```powershell
curiokraft-book generate book --slug curiokraft-aquatic_vol1
```
**Cross-Book Asset Reuse Feature**:
Before calling any external AI API, CurioKraft queries the database across all previously published volumes (`find_raw_asset_by_canonical`). If an approved illustration for `"clownfish"` already exists in Volume 1, it is automatically discovered and reused, saving API costs and maintaining style consistency! Newly generated images are auto-registered into `media_assets`.

---

## Step 8: Compositing Interior Masters & Compiling Print-Ready PDF

### 1. Visual Review Gate 2 (Generate 3 Sample Pages)
Inspect sample pages before batch running the entire book:
```powershell
curiokraft-book sample generate --pages P001,P005,P009
```
Inspect `output/samples/` to confirm:
- Gutter margin is clear (≥ 0.5").
- Line thickness is preschool-appropriate (bold 3pt+ outlines).
- Display labels and cards are correctly positioned.

### 2. Batch Generate Full 110-Page Interior Masters
```powershell
curiokraft-book generate book
```
This executes:
- Raw illustration processing and contrast rescue.
- Preschool typography compositing (`Fredoka-Bold.ttf`).
- Special page assembly:
  - Page 001: Welcome Page
  - Page 107: Alphabet Spread
  - Page 109: Official Preschool Certificate
  - Even pages: Blank verso bleed guards
- Outputs all master images to `output/interior_masters/page_001.png` through `page_110.png`.
- Automatically indexes all master images into the database (`asset_type="composite_master"`).

### 3. Compile Print-Ready Interior PDF
```powershell
curiokraft-book assemble interior
```
**Zero-Loss Compression Standards**:
- CurioKraft applies PyMuPDF FlateDecode compression (`deflate=True, garbage=4`).
- Preserves native 8-bit Grayscale raster (`mode="L"`), completely avoiding destructive 1-bit binarization that causes jagged pixelated edges.
- Reduces file size from ~46 MB down to ~2.25 MB with **100% bit-for-bit mathematical equality** (`np.array_equal` passes).
- Resulting PDF: `output/interior/TINY_HANDS_COLOR_AND_LEARN_Interior_110p.pdf`.
- Automatically registered into the database (`asset_type="interior_pdf"`).

---

## Step 9: Full-Wrap Cover Generation & 18-Point Preflight Certification

### 1. Build & Validate KDP Full-Wrap Cover
```powershell
# Build full-wrap paperback cover (Back + Spine + Front + Barcode Box)
curiokraft-book cover build

# Validate cover dimensions, 300 DPI, and barcode safe zones
curiokraft-book cover validate
```
Output: `output/cover/TINY_HANDS_COLOR_AND_LEARN_Cover_CMYK.pdf`.

### 2. Run the 18-Point Deterministic KDP Preflight Diagnostic
```powershell
curiokraft-book preflight run
```
This executes an automated 18-point verification:
1. Exact 110-page count check.
2. Trim width (8.50" ± 0.01") & trim height (11.00" ± 0.01").
3. Canvas raster DPI (300.0 DPI strictly).
4. Inside gutter margin compliance (≥ 0.50").
5. Outside margin compliance (≥ 0.375").
6. Color space verification (Grayscale 8-bit interior, CMYK cover).
7. FlateDecode compression integrity.
8. KDP barcode zone clearance (2.0" × 1.2" bottom-right safe zone).

When all 18 checks pass, an official certificate is generated at:
`output/reports/FINAL_KDP_PREFLIGHT_CERTIFICATE.txt`.

---

## Step 10: Publishing Metadata & Cloud Synchronization

### 1. Generate Amazon KDP Submission Bundle
```powershell
curiokraft-book kdp generate
```
Generates 1-click submission metadata:
- KDP Title & Subtitle.
- Optimized 7 Amazon Search Keywords & BISAC Categories.
- Formatted HTML Book Description for Amazon Author Central.

### 2. Index & Push Deliverables into Object Storage (`db sync-assets`)
Once your interior masters, cover files, and interior PDF are generated, push them into MinIO / PostgreSQL:
```powershell
# Index and upload all 110 composite master PNGs:
curiokraft-book db sync-assets --dir output/interior_masters --type composite_master

# Index and upload print interior PDF:
curiokraft-book db sync-assets --dir output/interior --type interior_pdf

# Index and upload cover PNG and CMYK PDF:
curiokraft-book db sync-assets --dir output/cover --type cover_asset
```
* **Idempotent & Deduplicated**: Every asset is indexed by its SHA-256 hash. If an asset is already in the database/MinIO, the upload is skipped. You can safely run this command as many times as you like.

### 3. Pull & Verify Remote Assets Locally (`db pull-assets`)
If you need to verify files stored in MinIO/PostgreSQL or pull assets down to another machine:
```powershell
# Pull and verify interior PDF:
curiokraft-book db pull-assets --dir output/verified_assets --type interior_pdf

# Pull and verify cover assets:
curiokraft-book db pull-assets --dir output/verified_assets --type cover_asset
```
Each downloaded file is automatically verified against its stored SHA-256 hash in PostgreSQL to guarantee 100% bit-for-bit integrity.

### 4. Synchronize Local Database & Assets to Cloud (`db sync`)
```powershell
curiokraft-book db sync
```
**How Outbox Sync Works:**
1. Scans `outbox_events` for newly created or updated books, pages, prompts, and media assets.
2. Uploads local images and PDFs to Cloudflare R2 (or S3/MinIO) using content-addressable storage keys.
3. Upserts records into the remote PostgreSQL database (Neon / Supabase).
4. Marks outbox events as `synced`.

---

## CLI Command Reference Lifecycle Cheat Sheet

| Lifecycle Stage | Command | Primary Function | Database & Storage Impact |
|:---|:---|:---|:---|
| **0. Setup** | `curiokraft-book init` | Scaffolds directory structure and templates | Verifies folder paths on disk |
| **0. Database** | `curiokraft-book db init` | Creates database tables & indexes | Creates `books`, `pages`, `prompts`, `media_assets`, `outbox` |
| **0. Database** | `curiokraft-book db status` | Displays DB connection & entity counts | Reads `books`, `pages`, `prompts`, `media_assets` |
| **0. Database** | `curiokraft-book db migrate-from-fs` | Bootstraps JSON manifest/state to DB | Populates `books` and `pages` from disk files |
| **1. Curriculum** | `curiokraft-book manifest audit` | Audits 110-page sequence & categories | Validates curriculum integrity |
| **1. Prompts** | `curiokraft-book prompt show -p P005` | Displays copy-paste prompt for a page | Reads manifest / runs single debate |
| **1. Prompts** | `curiokraft-book prompt export --format all` | Exports 110 prompts + covers + mascot | **Persists prompts into database `prompts` table** |
| **1. Indexing** | `curiokraft-book db sync-assets --dir inbox/raw_pages --type raw_image` | Indexes dropped illustrations | **Saves SHA-256 CAS records to `media_assets`** |
| **2. Review** | `curiokraft-book sample generate -p P001,P005` | Composites 3 test pages for review | Auto-registers sample masters into `media_assets` |
| **3. Production** | `curiokraft-book generate book` | Composites all 110 interior masters | **Auto-registers all 110 masters into `media_assets`** |
| **3. Assembly** | `curiokraft-book assemble interior` | Losslessly compiles 110-page PDF | **Auto-registers interior PDF into `media_assets`** |
| **3. Cover** | `curiokraft-book cover build` | Builds full-wrap paperback cover | Auto-registers cover PDF into `media_assets` |
| **4. Preflight** | `curiokraft-book preflight run` | Executes 18-point KDP diagnostic | Records preflight pass/fail audit in `pipeline_logs` |
| **5. Metadata** | `curiokraft-book kdp generate` | Generates 1-click submission dashboard | Staged for release |
| **5. Cloud Sync** | `curiokraft-book db sync` | Pushes local DB & assets to Cloud | Pushes Outbox to Neon & blobs to Cloudflare R2 |
| **5. Verification** | `curiokraft-book db pull-assets` | Pulls assets from MinIO/DB to local machine | Verifies local downloads against PostgreSQL SHA-256 hashes |
