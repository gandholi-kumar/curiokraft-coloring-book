# CurioKraft Coloring Book Engine — Technical Changelog

All notable changes, issue investigations, root cause analyses, and solutions implemented across the **CurioKraft Coloring Book Production System** are documented in this file.

---

## [Version 1.1.0] — 2026-08-30

### 1. 🎨 Live AI Image Generation via Google Native Gemini Image Models (`gemini-3.1-flash-image`) & DALL-E 3
- **Observed Issue:**  
  Running `curiokraft-book sample generate` or `curiokraft-book generate book` generated geometric placeholder shapes (rectangles in `raw_p001_alphabet_a_to_m.png`, ellipses in `raw_p005_banana.png` and `raw_p047_dog.png`) instead of real illustrations, even when `$env:GEMINI_API_KEY` was provided. Attempting to call legacy Imagen models returned:  
  `This method is only supported in Gemini Enterprise Agent Platform mode, not in Gemini Developer API mode.`
- **Root Cause Analysis:**  
  1. Google migrated native image generation in the Gemini API away from legacy standalone Imagen models to **Native Gemini Image Models** (`gemini-3.1-flash-image` / `gemini-2.5-flash-image`) accessed via `client.interactions.create` or `POST /v1beta/interactions`.
  2. The pipeline's Step 2 needed to be wired to this modern interaction architecture.
- **Fix Provided:**  
  - Updated [`src/curiokraft_book/orchestrator/model_client.py`](file:///h:/Store/CurioKraft/Publications/coloring-book/src/curiokraft_book/orchestrator/model_client.py):
    - Implemented Google's official `client.interactions.create(model="gemini-3.1-flash-image", input=...)` pattern with automatic fallback to `gemini-2.5-flash-image` and REST endpoint (`/v1beta/interactions`).
    - Base64 payload decoding (`interaction.output_image.data`) and automatic proportional scaling to the $2550 \times 3300\text{ px}$ 300 DPI master canvas.
    - Integrated OpenAI DALL-E 3 (`dall-e-3`) for users with `$env:OPENAI_API_KEY`.
  - Wired `model_client.generate_illustration()` directly into [`src/curiokraft_book/orchestrator/batch_runner.py`](file:///h:/Store/CurioKraft/Publications/coloring-book/src/curiokraft_book/orchestrator/batch_runner.py) and [`src/curiokraft_book/cli.py`](file:///h:/Store/CurioKraft/Publications/coloring-book/src/curiokraft_book/cli.py).

---

### 2. 🖍️ Toddler Hollow Bubble Typography, Tracking & Sizing Matrix
- **Observed Issue:**  
  Text headers were rendered with solid black fill (`fill=0`), font size was small (`135 pt`), words were tightly kerned without spacing, and text was positioned too close to the top trim.
- **Root Cause Analysis:**  
  Preschool coloring books require discrete, hollow bubble uppercase letterforms with bold black outlines and generous letter spacing (tracking) so toddlers can color each character individually with crayons without outline collisions.
- **Fix Provided:**  
  - Updated [`src/curiokraft_book/compositor/typography.py`](file:///h:/Store/CurioKraft/Publications/coloring-book/src/curiokraft_book/compositor/typography.py):
    - Upgraded base font size from `135 pt` to **`245 pt`** (and up to **`265 pt` / $360\text{ px}$ tall** for short words).
    - Shifted top placement down to `240 px` ($0.80\text{ in}$) for comfortable breathing room.
    - Implemented **Character-by-Character Tracking / Letter Spacing** ($20\text{--}46\text{ px}$ / $0.07\text{--}0.15\text{ in}$) so letters never touch or merge.
    - Configured bold outline bubble style: `fill=255` (white interior) and `stroke_width=15 px, stroke_fill=0` (black outline).
    - Added point binarization to snap FreeType antialiasing to pure binary $0\text{ or }255$.

---

### 3. 🔍 Whole-Book QA Audit Failure Diagnosis
- **Observed Issue:**  
  Running `curiokraft-book generate book` displayed `[FAIL] 110-Page Interior Production Batch Encountered an Issue , Reason: Whole-Book QA failed with 106 flagged pages.`
- **Root Cause Analysis:**  
  `AGT-010-BOOKQA` scans `output/interior_masters/` for all 110 pages. Because only a partial run had executed, pages 3, 4, 6–110 were missing from disk. The auditor accurately reported 106 missing files.
- **Fix Provided:**  
  - Verified that running the complete batch populates all 110 pages, resolving the missing file audit flags.
  - Added clear diagnostic logging in `book_level_qa_audit.json`.

---

### 4. 🪟 Windows PowerShell Encoding & Unicode Crash Fix
- **Observed Issue:**  
  Running CLI commands on Windows command prompt threw:  
  `UnicodeEncodeError: 'charmap' codec can't encode character '\u2714' in position 0: character maps to <undefined>`.
- **Root Cause Analysis:**  
  Default Windows console encoding (`cp1252`) cannot encode Unicode glyphs (`✔`, `✖`) when output is streamed without explicit UTF-8 encoding.
- **Fix Provided:**  
  - Updated `src/curiokraft_book/cli.py`:
    - Added `sys.stdout.reconfigure(encoding='utf-8', errors='replace')` and `sys.stderr.reconfigure(encoding='utf-8', errors='replace')`.
    - Configured Rich `Console(force_terminal=True, legacy_windows=False)`.
    - Replaced raw Unicode characters with universally compatible styled tags (`[PASS]`, `[FAIL]`, `[OK]`).

---

### 5. 🔇 PyMuPDF Deprecation Warning Silenced
- **Observed Issue:**  
  Console displayed `warning: The fitz API is deprecated and will be removed in future. Use import pymupdf instead.`
- **Root Cause Analysis:**  
  Legacy PyMuPDF import syntax (`import fitz`) was used across PDF validator and compiler scripts.
- **Fix Provided:**  
  - Updated `src/curiokraft_book/validators/pdf.py` and `src/curiokraft_book/compositor/interior_pdf.py` to use `import pymupdf as fitz`.

---

### 6. 🧪 Unit Test Precision & Flakiness Fixes (100% Pass Rate)
- **Observed Issue:**  
  1. `test_composite_typography`: Failed with `assert (299.9994, 299.9994) == (300, 300)`.
  2. `test_book_qa_audit`: Failed due to synthetic line antialiasing triggering the gray shading validator.
- **Root Cause Analysis:**  
  1. Windows PNG metadata converts metric DPI to pixels-per-meter, resulting in minor floating-point rounding.
  2. Synthetic PIL vector arcs produced antialiased transition pixels.
- **Fix Provided:**  
  - Updated `tests/test_compositor.py` to assert `int(round(dpi[0])) == 300`.
  - Added binary threshold snapping in `batch_runner.py` and `typography.py`.
  - **Result:** **16/16 Unit Tests pass green in ~28 seconds.**

---

### 7. 📖 Gutter & Safe Live Area Visual Documentation
- **Observed Issue:**  
  Need for clear documentation explaining how the spine binding (gutter) affects odd vs. even pages and guaranteeing Amazon KDP print compliance.
- **Fix Provided:**  
  - Added Section 4 to `docs/USER_GUIDE.md` and Section 7 to `docs/ONE_TIME_SETUP_AND_PREPUBLISH_CHECKLIST.md`.
  - Included a 2-page open book spread ASCII diagram detailing gutter clearance ($0.50\text{ in} \dots 0.66\text{ in}$ vs. Amazon's $0.375\text{ in}$ requirement) and single-sided coloring architecture.

---

### 8. 🔌 Pluggable Decoupled Provider Architecture & Stale Cache-Free Inbox Ingestion
- **Observed Issue:**  
  1. Google AI Studio free tier enforces `limit: 0` quota on developer image generation APIs (`gemini-3.1-flash-image`), while text models (`gemini-1.5-pro`) remain free.
  2. Tight coupling to a single API provider or naive disk reading created the risk of **stale cache bugs** (silently re-validating old placeholder artwork or skipping API calls).
- **Root Cause Analysis:**  
  A professional production publishing engine must be completely provider-agnostic. It should seamlessly decouple the *source of raw illustrations* (Live OpenAI API, Live Gemini API, manual Web UI downloads, or offline vector mocks) from the downstream compositor, binarizer, and KDP preflight pipeline.
- **Fix Provided:**  
  - Implemented **Pluggable Provider Strategy** in [`src/curiokraft_book/orchestrator/model_client.py`](file:///h:/Store/CurioKraft/Publications/coloring-book/src/curiokraft_book/orchestrator/model_client.py):
    - `BaseImageProvider` (abstract base strategy).
    - `GeminiImageProvider` (Google Gemini Native Image Generation).
    - `OpenAIImageProvider` (OpenAI DALL-E 3).
    - `DiskInboxProvider` (isolated fresh drop inbox scanner).
    - `MockImageProvider` (offline cubic Bézier curve procedural vector generator).
  - Created isolated input directory **`inbox/raw_pages/`** (scaffolded via `curiokraft-book init`).
  - Added **`curiokraft-book ingest`** (`process-raw`) command:
    - Scans `inbox/raw_pages/` for user-dropped artwork.
    - Deterministically binarizes, rescales to 300 DPI, fits into KDP safe margins, overlays preschool bubble typography, and runs QA validation.
    - **Automatically archives processed images from `inbox/raw_pages/` to `generated/raw_pages/`**, eliminating accidental stale re-ingestion.
  - Added **`curiokraft-book prompt show -p <ID>`** and **`curiokraft-book prompt export`** commands to generate 1-click copy-paste prompts for free Web UI image generation.
  - Added CLI control flags to `sample generate` and `generate book`:
    - `--source [auto | api | inbox | disk | mock | openai | gemini]`.
    - `--force` (bypasses existing caches for clean fresh generation).
  - Expanded test suite: **19/19 Unit Tests pass green (100%)**.

---

### 9. 🧠 Multi-Agent Pre-Generation Debate Engine & Transparent Debate Audit Log (`logs/agent_debates_log.md`)
- **Observed Issue:**  
  1. Overview Spread for Page 1 (`A - M FIRST WORDS`) generated as a flat 16-cell grid with 3 dead blank boxes, missing alphabet letters A–M, and faceless animal silhouettes (cat, dog, elephant).
  2. Need for granular transparency into what each individual specialist agent proposed, criticized, and voted on for every page BEFORE image generation.
- **Root Cause Analysis:**  
  1. The blanket `"strictly NO text"` rule (which is mandatory for single pages where typography is added programmatically) was inadvertently applied to the Alphabet Spread (where letter-to-sound pairing is essential).
  2. Specialist agents needed dynamic, object-tailored proposals and an automated audit logging mechanism to record all 4 rounds of debate on disk for inspection.
- **Fix Provided:**  
  - Updated [`src/curiokraft_book/orchestrator/debate_engine.py`](file:///h:/Store/CurioKraft/Publications/coloring-book/src/curiokraft_book/orchestrator/debate_engine.py):
    - **Dynamic Object-Tailored Proposals:** Implemented bespoke proposals for each specialist agent (`AGT-002-DESIGN`, `AGT-003-KDP`, `AGT-004-MARKET`, `AGT-005-EDU`, `AGT-006-REDTEAM`, `AGT-007-JUDGE`, `AGT-008-PROMPTGEN`) for every single page (1 to 110).
    - **Fixed Educational Spreads (P001–P004):** Enforced uppercase bubble letter-illustration pairings (A for Apple, B for Ball...), smiling animal faces with big round eyes, and balanced layouts with zero empty boxes.
    - **Added `export_full_debate_log()`:** Automatically records the entire 4-round debate for all 110 pages into **`logs/agent_debates_log.md`**.
  - Added CLI commands in `src/curiokraft_book/cli.py`:
    - `curiokraft-book debate show --page <ID>`: Interactive live terminal inspection of any page's 4-round debate and scoring.
    - `curiokraft-book debate export --out logs/agent_debates_log.md`: Exports the full 3,600+ line transparent audit report.
  - Automated test suite: **19/19 Unit Tests Passing (100% Green)**.

---

### 10. 🏛️ Manifest-Driven Architecture & Zero-Hardcoded State (Universal Volume Scaling)
- **Observed Issue:**  
  Spread card assignments (e.g. A=Apple, Card 8=Plain Wooden Cubes), category keyword dictionaries, and visual templates were hardcoded inside Python code (`debate_engine.py`) and static agent prompts. This prevented easy reuse for Volume 2, Volume 3, or themed editions.
- **Root Cause Analysis:**  
  Volume-specific content was intertwined with volume-agnostic layout and taxonomy rules.
- **Fix Provided:**  
  - Implemented clean 3-tier decoupled architecture:
    1. **`manifest/pages.json` (Volume-Specific):** Master source of truth for all page definitions and spread `cards` arrays (A=Apple, 8=Plain Wooden Cubes, descriptions, negative tokens).
    2. **`config/curriculum.yaml` (Volume-Agnostic):** Layout structures (`alphabet_a_m`, `numbers_0_5`), hollow bubble numeral fill mandate, container uniformity rules, and object purity filters.
    3. **`config/taxonomy.yaml` (Volume-Agnostic):** Semantic categorization database (living creature keywords, category visual templates, inanimate exceptions).
  - Updated [`debate_engine.py`](file:///h:/Store/CurioKraft/Publications/coloring-book/src/curiokraft_book/orchestrator/debate_engine.py) to read all card assignments dynamically from `page_record["cards"]`. Zero hardcoded keyword sets or card object lists remain in code.
  - Updated [`config/agents.yaml`](file:///h:/Store/CurioKraft/Publications/coloring-book/config/agents.yaml) so all 10 specialist agents reference configuration files dynamically.
  - **Volume 2 Scaling:** New volumes require only a new manifest file (e.g. `manifest/pages_vol2.json`) with **zero Python code changes**.

---

### 11. 🎨 Amazon KDP Full-Wrap Cover Compositor Overhaul & Anti-Drift Immutable Anchors
- **Observed Issue:**  
  1. Cover had flat dark navy 2D typography, lack of visual atmosphere, and generic plain text bullets.
  2. Barcode box contained printed text `"[ KDP Barcode Zone ]"` which causes automated Amazon KDP preflight rejection.
  3. Spine text was small (24pt) and hard to read; brand logo and emblem lacked aspect-ratio protection and safe margin buffering.
- **Root Cause Analysis:**  
  1. Amazon KDP automatically imprints the official barcode and ISBN upon publication; the uploaded PDF barcode area must be a clean, blank white box ($2.000 \times 1.200\text{ in}$) with zero barcode lines and zero text.
  2. The cover needed a hybrid AI + Programmatic Compositor architecture with 3-layer immutable prompt anchors to prevent LLM drift.
- **Fix Provided:**  
  - Overhauled [`src/curiokraft_book/compositor/cover.py`](file:///h:/Store/CurioKraft/Publications/coloring-book/src/curiokraft_book/compositor/cover.py):
    - **Atmospheric Background:** Sunny golden-yellow (`#FFE066`) to vibrant sky cyan (`#22D3EE`) vertical gradient with procedural translucent floating bubbles, sparkling stars, and watermark doodles.
    - **3D Multi-Color Bubbly Typography:** `TINY HANDS` rendered with alternating preschool palette colors, dark 3D contour stroke, and extruded shadow; `COLOR & LEARN` in white bubbly font with 3D drop shadow; top pill badge `FUN & EASY FIRST WORDS`; bottom banner `100+ EVERYDAY OBJECTS` with `AGES 1-3 YEARS` roundel.
    - **Back Cover 6-Card Preview Showcase:** 2x3 grid of discrete rounded white cards with line art icons, labels, and mini wax-crayon color guide badges dynamically pulled from `manifest/pages.json`.
    - **Barcode Box Compliance:** 100% clean white rectangle ($2.0 \times 1.2\text{ in} = 600 \times 360\text{ px}$ @ 300 DPI) with $\ge 0.25\text{ in}$ margin clearance, strictly **zero barcode lines and zero text**.
    - **Dynamic Aspect Ratio Lock:** Brand logo and spine emblem dynamically scaled with strict aspect ratio preservation and rendered as-is (no artificial surrounding circles or boxes).
  - Implemented **`curiokraft-book cover prompt`** in [`src/curiokraft_book/cli.py`](file:///h:/Store/CurioKraft/Publications/coloring-book/src/curiokraft_book/cli.py) with 3-layer immutable prompt anchors (alpha transparency, zero-text, stroke physics).
  - Updated [`config/agents.yaml`](file:///h:/Store/CurioKraft/Publications/coloring-book/config/agents.yaml) with cover design, anti-drift, and barcode safety protocols.
  - Updated [`docs/KDP_PRINT_SPECIFICATIONS.md`](file:///h:/Store/CurioKraft/Publications/coloring-book/docs/KDP_PRINT_SPECIFICATIONS.md) with official Amazon KDP Cover Calculator output and guidelines.
  - Automated tests: **19/19 Unit Tests Passing (100% Green)** and **18/18 Preflight Certified Pass**.

---

### 12. 🔒 Permanent Freeze: 8.5 x 11.0 in B&W Paperback 110-Page Master Dimension Standard
- **Context:**  
  The user uploaded live Amazon KDP Print Previewer validation screenshots (`media_1788102271365.png`, `media_1788103257909.png`, `media_1788104574081.png`) testing the physical fit of the full-wrap cover against Amazon's automated manufacturing stamp.
- **Verification & Exact Calibration:**  
  1. **Full Cover Canvas:** $17.498 \times 11.250\text{ in}$ ($5249 \times 3375\text{ px}$ @ 300 DPI) with $0.125\text{ in}$ ($38\text{ px}$) outer bleed on all 4 sides.
  2. **Spine Width:** $0.248\text{ in}$ ($74\text{ px}$) calculated dynamically from $110\text{ pages} \times 0.002252\text{ in/page}$ (B&W on White Paper). Spine safe live text zone $= 0.123\text{ in}$ ($37\text{ px}$) with $\ge 0.0625\text{ in}$ ($19\text{ px}$) margin from both spine folds.
  3. **Barcode Exclusion Box:** Calibrated to $700 \times 430\text{ px}$ ($2.333 \times 1.433\text{ in}$) @ 300 DPI.
     - **Horizontal Placement:** $X \in [1845, 2545]\text{ px}$ (`margin_from_spine_px: 42`), leaving $42\text{ px}$ ($0.140\text{ in}$) clearance from spine fold.
     - **Vertical Placement:** $Y \in [2850, 3280]\text{ px}$ (`margin_from_bottom_px: 95`), maintaining $57\text{ px}$ ($0.190\text{ in}$) clearance inside the red trim line ($Y=3337\text{ px}$).
- **Standard Status:** **PERMANENTLY FROZEN MASTER SPECIFICATION**. These parameters are locked into `config/curriculum.yaml`, `config/book_config.yaml`, and `docs/KDP_PRINT_SPECIFICATIONS.md` and will serve as the immutable benchmark for all 8.5 × 11 in 110-page B&W paperback coloring books in this publication line.
