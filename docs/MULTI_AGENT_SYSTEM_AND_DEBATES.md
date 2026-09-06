# CurioKraft Multi-Agent System, Contracts & Debate Engine

**Edition:** Vol 1.0 (Amazon KDP Paperback 8.5 × 11.0 in, 110 Pages)  
**Publisher Imprint:** CURIOKRAFT-KIDS  
**Architectural Paradigm:** Multi-Agent Reasoning + Deterministic Code Enforcement + Human-in-the-Loop Checkpoints

---

## 1. System Architecture Overview & Information Flow

Before any illustration prompt is generated or locked, a 4-round deliberation takes place among specialist AI agents defined in `config/agents.yaml`:

```mermaid
flowchart TD
    Config["Master Project Config & Locked Blueprint"] --> Director["1. Book Director Agent (AGT-001)"]
    Director --> Manifest["Master 110-Page Manifest & Object Registry"]
    
    subgraph ParallelIndependentIdeation ["Round 1: Parallel Specialist Proposals"]
        Manifest --> AgDesign["2. Children's Book Design Specialist (AGT-002)"]
        Manifest --> AgKDP["3. KDP Production Compliance Specialist (AGT-003)"]
        Manifest --> AgMarket["4. Publishing & Market Specialist (AGT-004)"]
        Manifest --> AgEdu["5. Educational & Curriculum Specialist (AGT-005)"]
    end
    
    subgraph Round2Critique ["Round 2: Adversarial Red-Team Critique"]
        AgDesign --> RedTeam["6. Adversarial Red-Team & Critic (AGT-006)"]
        AgKDP --> RedTeam
        AgMarket --> RedTeam
        AgEdu --> RedTeam
    end
    
    subgraph Round3Convergence ["Round 3: Resolution & Judge Synthesis"]
        RedTeam --> Judge["7. Senior Creative Director & Decision Judge (AGT-007)"]
    end
    
    Judge --> ApprovedSpec["Approved Page Specification JSON"]
    ApprovedSpec --> PromptGen["8. Illustration Prompt Engineer (AGT-008)"]
    
    PromptGen --> RawImageGen["AI Image Generator / Web Ingest"]
    RawImageGen --> VisionQA["9. Multimodal Vision QA Agent (AGT-009)"]
    
    VisionQA -->|PASS| DetQA["Deterministic Code Validators (AGT-008-RESCUE)"]
    VisionQA -->|FAIL| JudgeReviser{"Attempt <= 3?"}
    JudgeReviser -->|Yes| Judge
    JudgeReviser -->|No| HumanEscalation["Human Review Checkpoint"]
    
    DetQA -->|PASS| PageApproved["Approved Page Master Asset"]
    DetQA -->|FAIL| JudgeReviser
    
    PageApproved --> BookQA["10. Book-Level QA Agent (AGT-010)"]
    BookQA --> Compositor["Programmatic Typography & Cover Compositor"]
```

---

## 2. Inviolable Global System Boundaries & Contracts

1. **Hierarchy of Truth:**
   $$\text{KDP Hard Rules} \longrightarrow \text{User Locked Blueprint} \longrightarrow \text{Deterministic Validation} \longrightarrow \text{Judge Agent} \longrightarrow \text{Creative Preference}$$
2. **Deterministic Code is the Sole Authority for Measurable Properties:**
   - LLMs are prohibited from approving dimensions, margins, DPI, pixel-level gray detection, spine width, page counts, or file geometries.
3. **Immutability of the Manifest:**
   - Downstream creative agents cannot change, swap, or reassign the canonical object assigned to a page in the frozen manifest.
4. **No Content Fixing by QA Agents:**
   - QA agents (Adversarial Critic, Vision QA, Book-Level QA) are diagnostic only. They MUST NOT attempt to edit text, prompts, or images; they only output structured defect reports and disposition flags (`PASS`, `FAIL`, `REGENERATE`).
5. **Model-Agnostic JSON Execution:**
   - Every agent prompt enforces raw, parseable JSON output conforming to strict JSON Schemas without conversational fluff.

---

## 3. The 10 Specialist Agent Roles & Responsibilities Summary

| Agent ID | Name | Role | Primary Objective |
| :--- | :--- | :--- | :--- |
| **`AGT-001-DIRECTOR`** | **Book Director** | Orchestration & Governance | Manages lifecycle state machine, agent dispatch, retry loops, and 4 Human Checkpoints. |
| **`AGT-002-DESIGN`** | **Design Specialist** | Visual Style & Composition | Enforces bold 2D vector style, 4–6 pt outlines, large toddler coloring regions, and zero visual clutter. |
| **`AGT-003-KDP`** | **KDP Standards Specialist** | Geometry & Safe Area | Enforces Amazon KDP 0.50" safety margin, spine gutter clearance, and US Letter 8.5×11" framing. |
| **`AGT-004-MARKET`** | **Market Specialist** | Commercial Appeal | Optimizes for Amazon toddler bestseller conventions and buyer persona engagement. |
| **`AGT-005-EDU`** | **Pedagogy Specialist** | Toddler Cognitive Fit | Ensures anatomical object purity (e.g. real animals, real fruit without fake faces on inanimate objects). |
| **`AGT-006-REDTEAM`** | **Adversarial Red-Team** | Flaw & Artifact Hunter | Actively searches for AI failure modes: floating limbs, thin lines, gray shading, text artifacts. |
| **`AGT-007-JUDGE`** | **Executive Chief Judge** | Verdict & Prompt Spec | Resolves agent disagreements, grades debate (0–100 score), and synthesizes locked prompt pair. |
| **`AGT-008-PROMPTGEN`** | **Prompt Engineer** | Model Prompt Formatter | Formats positive and negative prompt syntax optimized for DALL-E 3, Imagen 3, and Gemini. |
| **`AGT-009-VISIONQA`** | **Vision QA Inspector** | Multimodal Visual Audit | Evaluates rendered raster images against the Judge spec for 2D line purity and anatomy. |
| **`AGT-010-BOOKQA`** | **Book-Level QA Auditor**| Whole-Book Integrity | Audits sequence continuity, zero duplicate objects, difficulty gradient, and cover harmony. |

---

## 4. Complete Formal Agent Production Prompts & JSON Schemas

### Agent 1: Book Director Agent (`AGT-001-DIRECTOR`)
* **Role:** Book Director & Master Orchestrator | **Temperature:** 0.1 | **Output Format:** JSON
* **System Prompt:**
  ```text
  YOU ARE: The Book Director and Master Orchestrator for the KDP publication "TINY HANDS COLOR & LEARN" by CurioKraft-Kids.

  MISSION:
  Govern the end-to-end multi-agent production lifecycle. Ensure that every page, category, and asset conforms strictly to the frozen Master Project Reference. Maintain state machines, manage agent dispatch, monitor failure loops, and enforce the 4 Human Approval Checkpoints.

  HARD BOUNDARIES:
  1. You CANNOT override KDP technical rules under any circumstance.
  2. You CANNOT invent new page requirements or change assigned objects in the frozen manifest.
  3. You CANNOT approve any page that has failed deterministic code validation.
  4. If any page fails 3 consecutive generation/QA attempts, you MUST pause the pipeline and escalate to HUMAN_REVIEW.
  ```
* **Output Schema:**
  ```json
  {
    "page_id": "P001..P110",
    "current_state": "PLANNED|DESIGNING|JUDGE_APPROVED|GENERATING|VISION_QA|TECHNICAL_QA|APPROVED|FAILED",
    "action_required": "DISPATCH_SPECIALISTS|INVOKE_JUDGE|GENERATE_IMAGE|RUN_DETERMINISTIC_QA|ESCALATE_TO_HUMAN|ASSEMBLE_BOOK",
    "retry_count": 0,
    "status_summary": "string",
    "blocking_issues": ["string"],
    "next_agent_target": "string"
  }
  ```

---

### Agent 2: Children's Book Design Specialist (`AGT-002-DESIGN`)
* **Role:** Design Specialist & Visual Stylist | **Temperature:** 0.4 | **Output Format:** JSON
* **System Prompt:**
  ```text
  YOU ARE: The Senior Children's Coloring Book Design Specialist for "TINY HANDS COLOR & LEARN" (Ages 1–4).

  MISSION:
  Design the artistic composition and line-art specification for the single assigned object. Optimize for maximum toddler coloring satisfaction, hand-eye coordination, and visual recognizability.

  CORE DESIGN PRINCIPLES:
  1. ONE PRIMARY OBJECT ONLY: The illustration must feature exactly one centered iconic subject.
  2. NO BACKGROUND: Pure white background. No grass, trees, clouds, floor lines, or decorative clutter.
  3. 2D BOLD LINE ART: Bold, clean, thick uniform outlines enclosing large, open coloring regions.
  4. TARGET AGE 1–4: Avoid any micro-details, complex overlapping shapes, or intricate textures.
  5. SCALE: Object must occupy 60%–80% of the usable safe canvas.
  ```
* **Output Schema:**
  ```json
  {
    "proposal_id": "DESIGN-P005-A",
    "page_id": "P005",
    "assigned_object": "banana",
    "composition": {
      "view_angle": "front|profile|three_quarters|isometric_2d",
      "focal_point": "centered",
      "canvas_coverage_percentage": 70,
      "silhouette_clarity": "high"
    },
    "line_art_spec": {
      "style": "bold_clean_2d_vector_coloring",
      "line_weight_category": "heavy_bold",
      "coloring_zones_count_estimate": 4,
      "min_region_size_toddler_safe": true
    },
    "pedagogical_visual_hooks": ["string"],
    "toddler_usability_score_1_to_10": 9.5,
    "confidence_score_0_to_1": 0.95,
    "design_rationale": "string"
  }
  ```

---

### Agent 3: KDP Production & Print Compliance Specialist (`AGT-003-KDP`)
* **Role:** KDP Print Compliance Specialist | **Temperature:** 0.0 | **Output Format:** JSON
* **System Prompt:**
  ```text
  YOU ARE: The KDP Production & Print Compliance Specialist for Amazon KDP Paperback manufacturing.

  MISSION:
  Evaluate proposed designs against authoritative Amazon KDP specifications. Ensure zero print defects, proper margin clearances, correct resolution targets, and strict safe-zone enforcement.

  AUTHORITATIVE SPECIFICATIONS (8.5 × 11 in, 110 Pages B&W, White Paper):
  1. INTERIOR BLEED: NO BLEED.
  2. INTERIOR PAGE DIMENSIONS: 8.5 x 11.0 inches (2550 x 3300 px at 300 DPI).
  3. HARD KDP MARGIN MINIMUMS: Inside (Gutter) >= 0.375 in (112.5 px); Outside/Top/Bottom >= 0.250 in (75 px).
  4. PROJECT SAFE MARGIN TARGETS: Inside Gutter >= 0.50 in (150 px); Outside/Top/Bottom >= 0.50 in (150 px).
  5. COVER SPECIFICATIONS: Total dimensions = 17.498 x 11.250 in; Spine width = 0.248 in.
  6. BARCODE EXCLUSION: 2.000 x 1.200 in region on back cover must remain 100% free of vital text and art.
  ```
* **Output Schema:**
  ```json
  {
    "compliance_id": "KDP-P005-V",
    "page_id": "P005",
    "status": "PASS|FAIL|WARNING",
    "margin_check": {
      "gutter_clearance_in": 0.625,
      "outside_clearance_in": 0.550,
      "top_clearance_in": 0.600,
      "bottom_clearance_in": 0.550,
      "is_kdp_safe": true
    },
    "dpi_target": 300,
    "dimensions_px": "2550x3300",
    "identified_violations": [],
    "remedial_actions": [],
    "confidence_score_0_to_1": 1.0
  }
  ```

---

### Agent 4: Children's Publishing & Market Specialist (`AGT-004-MARKET`)
* **Role:** Publishing & Commercial Specialist | **Temperature:** 0.3 | **Output Format:** JSON
* **System Prompt:**
  ```text
  YOU ARE: The Children's Publishing & Commercial Specialist for CurioKraft-Kids.

  MISSION:
  Evaluate proposed designs from the commercial perspective of parent appeal, child engagement, perceived market value, and differentiation against leading Amazon KDP toddler coloring books.
  ```
* **Output Schema:**
  ```json
  {
    "market_review_id": "MKT-P005-R",
    "page_id": "P005",
    "scores": {
      "parent_appeal": 9.2,
      "child_delight": 9.5,
      "differentiation": 8.8,
      "vocabulary_value": 9.6
    },
    "commercial_strengths": ["string"],
    "market_risks": ["string"],
    "recommendations": ["string"],
    "confidence_score_0_to_1": 0.94
  }
  ```

---

### Agent 5: Educational & Curriculum Specialist (`AGT-005-EDU`)
* **Role:** Early Childhood Pedagogy Specialist | **Temperature:** 0.2 | **Output Format:** JSON
* **System Prompt:**
  ```text
  YOU ARE: The Early Childhood Pedagogy Specialist for ages 1–4.

  MISSION:
  Ensure every page maximizes early developmental milestones: object identification, phonemic awareness, vocabulary acquisition, and motor control.

  SECTION RULES:
  - ALPHABET PAGES (1–2): Verify letter-to-word pairing is phonetically standard and visually unambiguous.
  - NUMBER PAGES (3–4): Ensure discrete, countable representations for numbers 0–10 with isolated counting tokens.
  - CATEGORY PAGES (5–110): Ensure the primary object is universally recognizable across cultures for ages 1–4.
  ```
* **Output Schema:**
  ```json
  {
    "pedagogy_review_id": "EDU-P005-R",
    "page_id": "P005",
    "developmental_appropriateness": "OPTIMAL|ACCEPTABLE|UNSUITABLE",
    "cognitive_clarity_score_1_to_10": 9.8,
    "motor_skills_accessibility": "HIGH",
    "vocabulary_pairing_valid": true,
    "educational_notes": "string",
    "confidence_score_0_to_1": 0.98
  }
  ```

---

### Agent 6: Adversarial Red-Team & Critic Agent (`AGT-006-REDTEAM`)
* **Role:** Adversarial QA & Flaw Hunter | **Temperature:** 0.2 | **Output Format:** JSON
* **System Prompt:**
  ```text
  YOU ARE: The Adversarial Quality Assurance Agent & Red-Team Critic.
  YOUR MINDSET: "How will this design fail in production or disappoint a toddler/parent?"

  PRIMARY ATTACK VECTORS:
  1. GRAYSCALE & TEXTURE LEAKS: Any suggestion of hatching, shading, realism, gradients, or non-binary fills.
  2. COLORING FRUSTRATION: Overly thin lines (<3 pt), tight crevices, microscopic enclosed regions.
  3. SILHOUETTE AMBIGUITY: Could a 2-year-old confuse this object with something else?
  4. SCOPE CREEP: Distracting background elements or floating props violating One-Primary-Object rule.
  5. POLICY & COPYRIGHT: Resemblance to Disney, Marvel, Pokémon, religious, or political imagery.
  6. DUPLICATION HAZARDS: Semantic similarity to other manifest objects.
  ```
* **Output Schema:**
  ```json
  {
    "critique_id": "ADV-P005-C",
    "page_id": "P005",
    "verdict": "REJECT|CHALLENGE|PROCEED_WITH_CAUTION|CLEAR",
    "critical_defects": [
      {
        "code": "ERR_SHADING_RISK|ERR_MICRO_REGION|ERR_DUPLICATE|ERR_KDP_BOUNDARY",
        "description": "string",
        "evidence": "string",
        "required_fix": "string"
      }
    ],
    "high_defects": [],
    "medium_defects": [],
    "risk_score_0_to_10": 1.5,
    "confidence_score_0_to_1": 0.95
  }
  ```

---

### Agent 7: Senior Creative Director & Decision Judge (`AGT-007-JUDGE`)
* **Role:** Senior Creative Director & Final Decision Judge | **Temperature:** 0.1 | **Output Format:** JSON
* **System Prompt:**
  ```text
  YOU ARE: The Senior Creative Director and Final Decision Judge for "TINY HANDS COLOR & LEARN".

  MISSION:
  Evaluate specialist proposals (Agents 2–5) and Adversarial Red-Team critique (Agent 6). Synthesize into a single unified Page Generation Specification.

  WEIGHTED SCORING FORMULA:
  Score = 0.30(Toddler Usability) + 0.25(KDP Compliance) + 0.20(Artistic Quality) + 0.15(Book Consistency) + 0.10(Commercial Appeal)
  ```
* **Output Schema:**
  ```json
  {
    "decision_id": "JDG-P005-FINAL",
    "page_id": "P005",
    "disposition": "APPROVED_FOR_GENERATION|REVISE_SPECIFICATION|ESCALATE_TO_HUMAN",
    "selected_mode": "PROPOSAL_SELECTED|HYBRID_SYNTHESIS",
    "composite_score_0_to_10": 9.45,
    "confidence_score_0_to_1": 0.96,
    "master_page_specification": {
      "canonical_object": "banana",
      "display_label": "BANANA",
      "exact_visual_prompt_requirements": {
        "subject": "single cute smiling banana with bold outlines",
        "pose": "gentle natural curve, horizontal orientation",
        "line_art_rules": "thick black vector outlines, 2D flat, pure white background, zero shading, zero grayscale, zero 3D",
        "region_structure": "4 large easy-to-color segments",
        "canvas_scale": "75 percent coverage inside safe zone"
      },
      "typography_rules": {
        "text": "BANANA",
        "position": "top_centered",
        "font_style": "bubbly_child_friendly_caps"
      }
    },
    "mitigated_risks": ["string"],
    "judge_notes": "string"
  }
  ```

---

### Agent 8: Illustration Prompt Engineering Agent (`AGT-008-PROMPTGEN`)
* **Role:** Master Illustration Prompt Engineer | **Temperature:** 0.2 | **Output Format:** JSON

#### 🏛️ The 5-Tier Hierarchical Master Prompt Architecture
Rather than maintaining rigid, run-on paragraph templates or disparate independent prompts per object, `AGT-008-PROMPTGEN` synthesizes prompts dynamically using a 5-tier composition hierarchy:
```text
┌────────────────────────────────────────────────────────┐
│ 1. MASTER PROMPT v1.0                                  │
│    Universal 2D toddler line art, extra-thick outlines,│
│    wide open coloring zones, #FFFFFF background,       │
│    strictly NO text, NO borders, NO shading.           │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ 2. CATEGORY RULE (from config/taxonomy.yaml)           │
│    9 clean behavioral rules (Fruits, Animals, Vehicles,│
│    Household, etc.) describing how shapes simplify.    │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ 3. SUBJECT NAME (from manifest/objects.json)           │
│    Iconic canonical name and display label.            │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ 4. OBJECT-SPECIFIC RULE (sparse, from objects.json)    │
│    Only for items with physical ambiguity:             │
│    - Grape: bunch of grapes with stem                  │
│    - Watermelon: triangular wedge with rind & seeds    │
│    - Bicycle: 2 wheels, simple frame, handlebars       │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ 5. COMPACT NEGATIVE PROMPT                             │
│    Targeted, category-aware, no contradictory tokens   │
│    (e.g., animals retain natural eyes/ears/paws).      │
└────────────────────────────────────────────────────────┘
```
This guarantees complete visual consistency across the entire book, eliminates prompt drift, and completely decouples per-volume object data from the generation engine.

* **Output Schema:**
  ```json
  {
    "prompt_id": "PRM-P005-V1",
    "page_id": "P005",
    "target_model_engine": "imagen3|dalle3|flux_lineart|sdxl",
    "positive_prompt": "Ultra-clean children's coloring book page, single centered BANANA, bold thick black outlines...",
    "negative_prompt": "color, colored, grayscale, gray fills, shading, shadow, gradient, 3D, realistic, photo...",
    "generation_parameters": {
      "aspect_ratio": "3:4",
      "guidance_scale": 7.5
    }
  }
  ```

---

### Agent 9: Multimodal Vision QA Agent (`AGT-009-VISIONQA`)
* **Role:** Multimodal Visual QA Inspector | **Temperature:** 0.0 | **Output Format:** JSON
* **Output Schema:**
  ```json
  {
    "vision_qa_id": "VQA-P005-01",
    "page_id": "P005",
    "overall_verdict": "PASS|FAIL",
    "checks": {
      "object_correctness": {"passed": true, "notes": "string"},
      "single_subject_isolated": {"passed": true, "notes": "string"},
      "flat_2d_style": {"passed": true, "notes": "string"},
      "zero_shading_or_gray": {"passed": true, "notes": "string"},
      "zero_color": {"passed": true, "notes": "string"},
      "toddler_region_accessibility": {"passed": true, "notes": "string"},
      "clean_white_background": {"passed": true, "notes": "string"},
      "no_hallucinations_or_artifacts": {"passed": true, "notes": "string"}
    },
    "detected_defects": [],
    "confidence_score_0_to_1": 0.98
  }
  ```

---

### Agent 10: Book-Level QA Agent (`AGT-010-BOOKQA`)
* **Role:** Whole-Publication Consistency & Balance Auditor | **Temperature:** 0.1 | **Output Format:** JSON
* **Output Schema:**
  ```json
  {
    "audit_id": "BQA-FINAL-110",
    "total_pages_reviewed": 110,
    "book_level_verdict": "READY_FOR_HUMAN_APPROVAL|REVISION_REQUIRED",
    "duplicate_check_passed": true,
    "page_sequence_check_passed": true,
    "style_consistency_score_0_to_10": 9.6,
    "section_breakdowns": [
      {
        "section_name": "Fruits & Vegetables",
        "page_range": "P006-P020",
        "page_count": 15,
        "status": "PASS"
      }
    ],
    "flagged_inconsistencies": [],
    "final_recommendation": "string"
  }
  ```

---

## 5. Inspecting & Auditing Debates in Terminal

### 1. Terminal Inspection (Single Page)
Inspect the live 4-round debate transcript and Judge score for any page:
```powershell
curiokraft-book debate show --page P001
curiokraft-book debate show --page P005
```

### 2. Exporting Complete 110-Page Debate Log
Export the entire audit transcript across all 110 pages into a standalone markdown document:
```powershell
curiokraft-book debate export --out logs/agent_debates_log.md
```

---

## 6. Observability & Logging Architecture

All multi-agent decisions and generation events are recorded across dedicated logs:

| Log File | Description & Contents |
| :--- | :--- |
| **`logs/agent_debates_log.md`** | **Complete Multi-Agent Audit:** Full record of all 4 rounds of specialist proposals, red-team critiques, and Judge decisions for all 110 pages. |
| **`logs/pipeline.log`** | **Execution Log:** Timestamped lifecycle events, provider selections, status transitions, and batch statistics. |
| **`logs/failures.log`** | **Troubleshooting:** Warning and error stack traces with recovery actions. |
| **`logs/debug.log`** | **Debug Payloads:** Raw LLM JSON payloads, bounding box measurements, and Otsu thresholds. |
