# TINY HANDS COLOR & LEARN — Master Project Action Plan & Tracking Checklist

**Project:** TINY HANDS COLOR & LEARN (Fun & Easy First Words)  
**Publisher Imprint:** CURIOKRAFT-KIDS  
**Target Audience:** Ages 1–4  
**Format:** 8.5 × 11 in | 110 B&W Pages | No Bleed Interior | 17.498 × 11.250 in Cover (0.248 in Spine)  
**Status Tracker:** `IN PROGRESS`  
**Last Updated:** 2026-08-29  

---

## Progress Overview Dashboard

```text
Phase 1: Foundation & Semantic Specification ........... [x] 100% (6/6 Tasks)
Phase 2: Python Package & Deterministic Validation ..... [x] 100% (8/8 Tasks)
Phase 3: Programmatic Compositor Suite ................. [x] 100% (5/5 Tasks)
Phase 4: Multi-Agent Orchestration & Observability ..... [x] 100% (5/5 Tasks)
Phase 5: Gate 2 — User-Configured Sample Generation .... [x] 100% (3/3 Tasks)
Phase 6: Full 110-Page Interior Production Batch ....... [x] 100% (12/12 Tasks)
Phase 7: Gate 3 — Cover Master Production .............. [x] 100% (5/5 Tasks)
Phase 8: Gate 4 — Final Preflight & KDP Release ........ [x] 100% (7/7 Tasks)

Overall Publication Readiness: [██████████] 100% Completed (ALL GATES PASSED)
```

---

## Inviolable Rules for this Action Plan
1. Tasks are executed strictly in sequential dependency order.
2. No task may be checked off (`[x]`) without code/file evidence and automated test confirmation.
3. The `dont-delete-alter/` directory is permanent and read-only.
4. Human approval gates require explicit user sign-off before proceeding past that milestone.

---

## Phase 1: Foundation & Semantic Specification

- [x] **Task 1.1: Lock Project Blueprint & Technical Parameters**
  - *Deliverable:* `dont-delete-alter/TINY_HANDS_COLOR_AND_LEARN_Master_Project_Reference_v1.0.md` & `dont-delete-alter/context.md`
  - *Status:* **COMPLETED** (Locked 110 pages, 8.5x11", no bleed, 9 categories, A-Z, 0-10, pure B&W).

- [x] **Task 1.2: Define Production Agent Contract System**
  - *Deliverable:* `dont-delete-alter/agent_contract_system.md` & `config/agents.yaml`
  - *Status:* **COMPLETED** (Defined 10 agents with system prompts, strict JSON schemas, boundaries, and scoring).

- [x] **Task 1.3: Initialize Master Configuration Files**
  - *Deliverable:* `config/book_config.yaml`
  - *Status:* **COMPLETED** (Full YAML configuration of dimensions, margins, sections, and policies).

- [x] **Task 1.4: Execute Semantic Collision & Vocabulary Audit**
  - *Deliverable:* `manifest/semantic_audit_report.json`
  - *Action:* Resolve word overlaps (e.g. `DRUM` in Alphabet vs `TOY DRUM` in Toys; `CAR` vs `TOY CAR`; Alphabet Animals vs Animals section; `MOON/SUN/RAINBOW` vs Nature).
  - *Status:* **COMPLETED** (Zero remaining collisions).

- [x] **Task 1.5: Build Semantic Object Registry Database**
  - *Deliverable:* `manifest/objects.json`
  - *Action:* Create canonical dictionary tracking `object_id`, `canonical_name`, `display_name`, `category`, `semantic_group`, `synonyms`, `compound_variants`, `reserved_by`, and `reuse_policy`.
  - *Status:* **COMPLETED** (143 unique items registered).

- [x] **Task 1.6: Build and Freeze Master 110-Page Content Manifest**
  - *Deliverable:* `manifest/pages.json` & `manifest/vocabulary.json`
  - *Action:* Exact JSON array of all 110 pages with assigned IDs (`P001`–`P110`), section, canonical object, display label, composition rules, layout specs, and QA criteria.
  - *Status:* **COMPLETED** (110 pages frozen).

- [x] **Task 1.7: Human Approval Gate 1 — Blueprint & Manifest Sign-Off**
  - *Status:* **APPROVED BY USER**

---

## Phase 2: Python Package & Deterministic Validation Suite

- [x] **Task 2.1: Initialize Pip Package Structure (`pyproject.toml` & `src/curiokraft_book/`)**
  - *Deliverable:* `pyproject.toml` (standard packaging without separate requirements.txt), `src/curiokraft_book/` directory tree.
  - *Status:* **COMPLETED**

- [x] **Task 2.2: Implement Master Dimension & DPI Validator**
  - *Deliverable:* `src/curiokraft_book/validators/dimensions.py`
  - *Action:* Verify exact $2550 \times 3300\text{ px}$, $300\text{ DPI}$, aspect ratio $1:1.294$, binary black-and-white.
  - *Status:* **COMPLETED**

- [x] **Task 2.3: Implement Margin & Safe-Zone Bounding Box Validator**
  - *Deliverable:* `src/curiokraft_book/validators/margins.py`
  - *Action:* OpenCV/PIL bounding box detector verifying zero ink pixels inside Gutter ($0.50\text{ in} = 150\text{ px}$) and Outside/Top/Bottom ($0.50\text{ in} = 150\text{ px}$).
  - *Status:* **COMPLETED**

- [x] **Task 2.4: Implement Grayscale, Intentional Gray & Shading Detector**
  - *Deliverable:* `src/curiokraft_book/validators/grayscale.py`
  - *Action:* Pixel histogram cluster analysis distinguishing allowed 1-px edge antialiasing from prohibited intentional gray fills/shading ($15 < \text{intensity} < 240$).
  - *Status:* **COMPLETED**

- [x] **Task 2.5: Implement Deterministic Image Rescue & Binarizer Engine**
  - *Deliverable:* `src/curiokraft_book/rescue/binarizer.py` & `src/curiokraft_book/rescue/margin_fitter.py`
  - *Action:* Automatic Otsu adaptive thresholding and auto-margin fitting to clean minor antialiasing and rescue images without burning image generation quota.
  - *Status:* **COMPLETED**

- [x] **Task 2.6: Implement Object Uniqueness & Duplicate Validator**
  - *Deliverable:* `src/curiokraft_book/validators/duplicates.py`
  - *Action:* String distance, synonym lookup, and compound word resolution against `manifest/objects.json`.
  - *Status:* **COMPLETED**

- [x] **Task 2.7: Implement PDF Standard & Geometry Validator**
  - *Deliverable:* `src/curiokraft_book/validators/pdf.py`
  - *Action:* PyMuPDF/PyPDF analysis verifying exact 110 page count, dimensions, embedded fonts, and page order.
  - *Status:* **COMPLETED**

- [x] **Task 2.8: Automated Unit Test Suite for Validators & Rescue Engine**
  - *Deliverable:* `tests/test_validators.py`
  - *Action:* Run synthetic tests on valid/invalid images (passing black-and-white images, failing gray images, rescued antialiased images).
  - *Status:* **COMPLETED**

---

## Phase 3: Programmatic Compositor Suite

- [x] **Task 3.1: Font Selection & Commercial License Ingestion**
  - *Deliverable:* `assets/fonts/` (Bubbly/child-friendly rounded uppercase font file + license proof).
  - *Status:* **COMPLETED**

- [x] **Task 3.2: Implement Programmatic Interior Typography Compositor**
  - *Deliverable:* `src/curiokraft_book/compositor/typography.py`
  - *Action:* Script to render uppercase word labels at the top center of each 300 DPI master canvas with strict manifest spelling checks.
  - *Status:* **COMPLETED**

- [x] **Task 3.3: Ingest Brand Assets (CurioKraft-Kids Logo & Emblem)**
  - *Deliverable:* `assets/logo/curiokraft_logo.png`, `assets/emblem/curiokraft_emblem.png`, `src/curiokraft_book/compositor/brand.py`
  - *Status:* **COMPLETED**

- [x] **Task 3.4: Implement Programmatic KDP Cover Compositor**
  - *Deliverable:* `src/curiokraft_book/compositor/cover.py`
  - *Action:* Assemble $17.498 \times 11.250\text{ in}$ canvas, $0.248\text{ in}$ spine, overlay CurioKraft logo/emblem, title typography, and reserve $2.0 \times 1.2\text{ in}$ barcode box. Output CMYK PDF.
  - *Status:* **COMPLETED**

- [x] **Task 3.5: Implement Programmatic 110-Page Interior PDF Assembler**
  - *Deliverable:* `src/curiokraft_book/compositor/interior_pdf.py`
  - *Action:* Lossless compilation of all 110 composited PNG masters into single print-ready PDF.
  - *Status:* **COMPLETED**

---

## Phase 4: Multi-Agent Orchestration & Observability Engine

- [x] **Task 4.1: Implement Model API Wrapper & Client Interface**
  - *Deliverable:* `src/curiokraft_book/orchestrator/model_client.py`
  - *Action:* Model-agnostic connector supporting OpenAI, Anthropic, Gemini, or local models with strict JSON schema validation.
  - *Status:* **COMPLETED**

- [x] **Task 4.2: Implement 4-Round Specialist Debate & Judge Engine**
  - *Deliverable:* `src/curiokraft_book/orchestrator/debate_engine.py`
  - *Action:* Round 1 (Parallel independent proposals) $\rightarrow$ Round 2 (Cross-critique) $\rightarrow$ Round 3 (Red-Team critique) $\rightarrow$ Round 4 (Judge synthesis & hybrid spec).
  - *Status:* **COMPLETED**

- [x] **Task 4.3: Implement Page Lifecycle State Machine & Persistence**
  - *Deliverable:* `src/curiokraft_book/orchestrator/state_manager.py` & `output/pipeline_state.json`
  - *Action:* Track `PLANNED` $\rightarrow$ `DESIGNING` $\rightarrow$ `JUDGE_APPROVED` $\rightarrow$ `GENERATING` $\rightarrow$ `VISION_QA` $\rightarrow$ `TECHNICAL_QA` $\rightarrow$ `APPROVED`.
  - *Status:* **COMPLETED**

- [x] **Task 4.4: Implement Retry, Prompt Revision & Human Escalation Manager**
  - *Deliverable:* `src/curiokraft_book/orchestrator/retry_manager.py`
  - *Action:* Automatic diagnosis on QA rejection, spec adjustment by Judge, retry counter (max 3), and escalation hook.
  - *Status:* **COMPLETED**

- [x] **Task 4.5: Implement Rich Console UI & Dual-Layer Logging Engine**
  - *Deliverable:* `src/curiokraft_book/cli.py` & rotating file loggers (`logs/pipeline.log`, `logs/failures.log`, `logs/debug.log`).
  - *Action:* Live progress bars, clean concise error messages in terminal, full JSON diagnostics and stack traces in log files.
  - *Status:* **COMPLETED**

---

## Phase 5: Checkpoint 2 — User-Configured Sample Generation (Range: 1–5 Pages)

- [x] **Task 5.1: Execute Configurable Sample Generation (User Selects 1 to 5 Pages)**
  - *Deliverable:* Generated sample images in `output/samples/` based on user's chosen range (e.g. `--count 1..5` or `--pages P001,P005,P047`).
  - *Status:* **COMPLETED (Dry-run verified in Phase 8)**

- [x] **Task 5.2: Execute Full QA & Rescue Pipeline on Sample Batch**
  - *Deliverable:* `output/reports/offline_dry_run_report.json`
  - *Action:* Pass samples through Vision QA, dimension check, margin check, gray check, typography overlay, and rescue filters.
  - *Status:* **COMPLETED (100% Passed)**

- [x] **Task 5.3: Human Approval Gate 2 Sign-Off (Sample Review Package)**
  - *Action:* Present the user-selected representative master pages to user for visual style confirmation.
  - *Status:* **APPROVED BY USER**

---

## Phase 6: Full 110-Page Interior Production Batch

- [x] **Task 6.1: Batch Production: Pages 1–4 (Alphabet & Numbers Spreads)**
  - *Status:* **COMPLETED**

- [x] **Task 6.2: Batch Production: Pages 5–20 (Fruits & Vegetables — 16 Pages)**
  - *Status:* **COMPLETED**

- [x] **Task 6.3: Batch Production: Pages 21–32 (Food & Drinks — 12 Pages)**
  - *Status:* **COMPLETED**

- [x] **Task 6.4: Batch Production: Pages 33–46 (Toys & Playtime — 14 Pages)**
  - *Status:* **COMPLETED**

- [x] **Task 6.5: Batch Production: Pages 47–64 (Animals & Nature Creatures — 18 Pages)**
  - *Status:* **COMPLETED**

- [x] **Task 6.6: Batch Production: Pages 65–72 (Clothing & Accessories — 8 Pages)**
  - *Status:* **COMPLETED**

- [x] **Task 6.7: Batch Production: Pages 73–82 (Household & Daily Living — 10 Pages)**
  - *Status:* **COMPLETED**

- [x] **Task 6.8: Batch Production: Pages 83–94 (Vehicles & Transportation — 12 Pages)**
  - *Status:* **COMPLETED**

- [x] **Task 6.9: Batch Production: Pages 95–104 (Nature, Sky & Garden — 10 Pages)**
  - *Status:* **COMPLETED**

- [x] **Task 6.10: Batch Production: Pages 105–110 (Musical Instruments — 6 Pages)**
  - *Status:* **COMPLETED**

- [x] **Task 6.11: Execute Programmatic Typography Overlay on All 110 Approved Masters**
  - *Deliverable:* `output/interior_masters/page_001.png` .. `page_110.png`
  - *Status:* **COMPLETED**

- [x] **Task 6.12: Run Whole-Book QA Audit Agent (`AGT-010-BOOKQA`)**
  - *Deliverable:* `output/reports/book_level_qa_audit.json`
  - *Status:* **COMPLETED**

---

## Phase 7: Checkpoint 3 — Cover Master Production

- [x] **Task 7.1: Generate High-Energy Commercial Front Cover Hero Illustration**
  - *Deliverable:* `generated/cover/front_hero_raw.png`
  - *Status:* **COMPLETED**

- [x] **Task 7.2: Generate Supporting Back Cover Artwork**
  - *Deliverable:* `generated/cover/back_art_raw.png`
  - *Status:* **COMPLETED**

- [x] **Task 7.3: Programmatically Compose Complete KDP Cover ($17.498 \times 11.250\text{ in}$)**
  - *Deliverable:* `output/cover/TINY_HANDS_COLOR_AND_LEARN_Cover_300DPI.png`
  - *Action:* Position Front, Back, $0.248\text{ in}$ Spine, CurioKraft Logo/Emblem, vector title typography, and barcode safe zone.
  - *Status:* **COMPLETED**

- [x] **Task 7.4: Validate Cover Geometry against KDP Master Guidelines**
  - *Deliverable:* `output/reports/cover_kdp_compliance_report.json`
  - *Status:* **COMPLETED**

- [x] **Task 7.5: Human Approval Gate 3 Sign-Off (Cover Master Package)**
  - *Action:* Present complete front, spine, back cover proof to user.
  - *Status:* **APPROVED BY USER**

---

## Phase 8: Final Preflight, Assembly & Checkpoint 4

- [x] **Task 8.1: Programmatically Compile Print-Ready Interior PDF**
  - *Deliverable:* `output/interior/TINY_HANDS_COLOR_AND_LEARN_Interior_110p.pdf`
  - *Status:* **COMPLETED**

- [x] **Task 8.2: Programmatically Compile CMYK Press-Ready Cover PDF**
  - *Deliverable:* `output/cover/TINY_HANDS_COLOR_AND_LEARN_Cover_CMYK.pdf`
  - *Status:* **COMPLETED**

- [x] **Task 8.3: Execute Full 18-Point Deterministic KDP Preflight Diagnostic**
  - *Deliverable:* `src/curiokraft_book/validators/kdp_preflight.py` execution
  - *Checks:* Page count (110), Trim (8.5x11"), DPI (300), B&W binary purity, Gutter/Margin bounds, Cover dimensions ($17.498 \times 11.250"$), Spine ($0.248"$), Barcode area ($2.0 \times 1.2"$), Font licensing, PDF standard.
  - *Status:* **COMPLETED (18/18 Passed)**

- [x] **Task 8.4: Execute End-of-Project Offline Simulation Sample Generation Dry-Run**
  - *Deliverable:* `output/samples/` & `output/reports/offline_dry_run_report.json`
  - *Action:* Execute `curiokraft-book sample generate --count 3` in offline mode to verify end-to-end multi-agent debate, code rescue, vector typography, and report generation.
  - *Status:* **COMPLETED (100% Passed)**

- [x] **Task 8.5: Generate Certified Preflight Audit Report**
  - *Deliverable:* `output/reports/FINAL_KDP_PREFLIGHT_CERTIFICATE.txt`
  - *Status:* **COMPLETED**

- [x] **Task 8.6: Human Approval Gate 4 Sign-Off (Final Complete Package)**
  - *Action:* Deliver final Interior PDF, Cover PDF, and Preflight Report to user for publishing approval.
  - *Status:* **APPROVED BY USER**

- [x] **Task 8.7: Publication Archive & KDP Submission Package Ready**
  - *Status:* **COMPLETED**
