# CurioKraft Documentation Index

All project documentation, grouped by purpose. Files are unchanged from their
original names — only the folder layout is new.

**New here?** Read **[workflows/PUBLISHING_WORKFLOWS_GUIDE.md](workflows/PUBLISHING_WORKFLOWS_GUIDE.md)**
first. It separates **Track 1** (free Google AI Studio web workflow) from **Track 2**
(automated API batch) and tells you which one applies to you.

---

## ⚙️ setup/ — environment and one-time configuration

| Document | Covers |
|---|---|
| [ONE_TIME_SETUP_AND_PREPUBLISH_CHECKLIST.md](setup/ONE_TIME_SETUP_AND_PREPUBLISH_CHECKLIST.md) | Publisher assets, environment preparation, disaster recovery, PyPI packaging, and the 15-minute pre-publish checklist. |
| [GOOGLE_AI_STUDIO_SETUP_AND_PROMPTING_GUIDE.md](setup/GOOGLE_AI_STUDIO_SETUP_AND_PROMPTING_GUIDE.md) | Exact AI Studio sidebar settings (aspect ratio `3:4`, output *Images only*, temperature `0.5`) and copy-paste System Instruction presets. |
| [GITHUB_PROJECT_MAINTENANCE_GUIDE.md](setup/GITHUB_PROJECT_MAINTENANCE_GUIDE.md) | Maintaining the repository with free GitHub tooling as a solo maintainer. |

## 🚀 workflows/ — running the pipeline and publishing

| Document | Covers |
|---|---|
| [PUBLISHING_WORKFLOWS_GUIDE.md](workflows/PUBLISHING_WORKFLOWS_GUIDE.md) | **Master guide.** Track 1 free web UI vs. Track 2 automated API batch, end to end. |
| [KDP_PUBLISHING_METADATA_GUIDE.md](workflows/KDP_PUBLISHING_METADATA_GUIDE.md) | The 4-agent KDP submission engine: A9 keyword deduplication, category trees, description copywriting, and the 1-click dashboard. |
| [PERFORMANCE.md](workflows/PERFORMANCE.md) | Profiling decorators, measured overhead, memory profiling, and py-spy flamegraphs. |

## 🏛️ architecture/ — how the system is built

| Document | Covers |
|---|---|
| [ARCHITECTURE_DIAGRAMS.md](architecture/ARCHITECTURE_DIAGRAMS.md) | Five Mermaid diagrams: high-level architecture, prompt synthesis, page lifecycle, module map, data flow. |
| [ARCHITECTURE_REVIEW_AND_ANALYSIS.md](architecture/ARCHITECTURE_REVIEW_AND_ANALYSIS.md) | Full review across architecture, security, extensibility, design patterns, and SOLID adherence. |
| [MULTI_AGENT_SYSTEM_AND_DEBATES.md](architecture/MULTI_AGENT_SYSTEM_AND_DEBATES.md) | The 10 specialist agents, their contracts, and the 4-round debate protocols. |
| [MULTI_VOLUME_ARCHITECTURE_GUIDE.md](architecture/MULTI_VOLUME_ARCHITECTURE_GUIDE.md) | Scaling to Volume 2/3 and themed editions with zero hardcoded state in application code. |
| [PARALLELISM_AND_COVER_DEBATE_FAQ.md](architecture/PARALLELISM_AND_COVER_DEBATE_FAQ.md) | Where parallelism applies in each workflow mode, and the front/back cover debate refactor. |
| [SPECIAL_PAGES_AND_MASCOT_GUIDE.md](architecture/SPECIAL_PAGES_AND_MASCOT_GUIDE.md) | Page 001 (welcome & ownership) and page 110 (completion certificate), plus the mascot system. |

## 📏 standards/ — authoritative creative standards

These are the rules the prompt-generating agents are required to follow.

| Document | Covers |
|---|---|
| [ANIMAL_ANATOMY_AND_POSTURE_STANDARD.md](standards/ANIMAL_ANATOMY_AND_POSTURE_STANDARD.md) | Animal anatomy, locomotion, posture, and the prompt hierarchy for living subjects. |
| [VEHICLE_DESIGN_AND_ANATOMY_STANDARD.md](standards/VEHICLE_DESIGN_AND_ANATOMY_STANDARD.md) | Vehicle design, structural anatomy, and propulsion domains (e.g. never injecting wheels into non-wheeled vehicles). |

## 📐 reference/ — specifications to look things up in

| Document | Covers |
|---|---|
| [KDP_PRINT_SPECIFICATIONS.md](reference/KDP_PRINT_SPECIFICATIONS.md) | Official KDP paperback geometry: cover dimensions, paper stock multipliers, spine safe areas, and barcode rules. |

## 🗄️ archive/ — superseded, kept for history

| Document | Status |
|---|---|
| [USER_GUIDE.md](archive/USER_GUIDE.md) | **Obsolete.** Superseded by [PUBLISHING_WORKFLOWS_GUIDE.md](workflows/PUBLISHING_WORKFLOWS_GUIDE.md). |
| [CHROME_DEBUG_AND_AUTOMATION_FINDINGS.md](archive/CHROME_DEBUG_AND_AUTOMATION_FINDINGS.md) | Investigation notes on Chrome remote debugging policies and AI Studio automation. |

---

## internal/ — local-only engineering bookkeeping

Four working documents live in `docs/internal/`: `TECHNICAL_DEBT_ACTION_PLAN.md`,
`TECHNICAL_DEBT_IMPLEMENTATION_PROGRESS.md`, `TECHNICAL_DEBT_ITEMS_9_10_HANDOFF.md`,
and `IMPLEMENTATION_SESSION_SUMMARY.md`.

They are excluded via `.gitignore` and are therefore **not in the repository** — they
track work-in-progress and session history rather than shipping documentation. They're
named here without links so this page stays valid for anyone who clones the project.
