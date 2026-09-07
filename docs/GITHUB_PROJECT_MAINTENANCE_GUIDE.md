# GitHub Tools & Solo Project Maintenance Guide for CurioKraft

This guide provides practical instructions for maintaining the **CurioKraft Publishing Engine** using 100% free GitHub tools designed for independent creators and solo maintainers.

---

## 1. Free GitHub Projects (v2) Setup

GitHub Projects v2 provides dynamic spreadsheet and Kanban views with custom fields, automated status transitions, and roadmap views at zero cost.

### Recommended Board Configuration
Create a project board named **"CurioKraft Publication Engine & Multi-Volume Roadmap"**:

#### Recommended Custom Fields:
1. **Volume** (Single Select):
   - `Vol 1: Tiny Hands Color & Learn`
   - `Vol 2: Tiny Explorers (Dinosaurs)`
   - `Vol 3: Farm Animals`
   - `Vol 4: Vehicles & Machines`
   - `Engine Core`
2. **Production Stage** (Single Select / Columns):
   - 📋 **Backlog / Concept** (Manifest ideation & curriculum planning)
   - 🤖 **Debate & Prompts** (Multi-agent debate engine & prompt export)
   - 🎨 **Image Generation** (Batch generation via API or web UI)
   - 📥 **Ingest & Rescue** (Binarization & safe margin refitting)
   - 📑 **PDF Compositing** (110-page master assembly & full-wrap cover)
   - 🩺 **Preflight Certified** (18-point deterministic certification passed)
   - 🚀 **Published on KDP** (Live on Amazon)
3. **Target Date** (Date field)
4. **KDP Status** (Single Select: `Draft`, `In Review`, `Live`)

---

## 2. GitHub Milestones & Semantic Versioning

Group issues and pull requests into versioned release milestones to track progress:

| Milestone | Scope | Target Deliverable |
| :--- | :--- | :--- |
| **v1.0.0** | Core Engine Release | 110-page interior assembly, cover compositor, 18-point preflight, and CLI. |
| **v1.1.0** | Multi-Volume Architecture | Dynamic theme profiles, taxonomy inheritance, and vehicle anatomy rules. |
| **v1.2.0** | Autonomous Cloud Pipeline | Automated KDP upload preflight validation in GitHub Actions CI. |

---

## 3. GitHub Discussions Setup

Turn on GitHub Discussions in repository **Settings** ➔ **Features** ➔ Check **Discussions**.

### Recommended Discussion Categories:
* 💡 **Ideas & Theme Proposals:** Solicit community feedback on upcoming coloring book themes.
* 💬 **Q&A / Help:** Assist users with API setup, Playwright CDP automation, or Python venv installation.
* 📢 **Announcements:** Post newly published Amazon KDP paperback releases with ASIN links.
* 🗳️ **Polls:** Run voting polls for which volume to publish next.

---

## 4. GitHub Releases & Distribution

Automate release distribution using GitHub Releases:
* Whenever a new milestone is achieved, tag the commit (e.g. `git tag -a v1.0.0 -m "Release v1.0.0"`).
* Create a GitHub Release referencing the tag:
  - Attach the built wheel (`dist/curiokraft_coloring_book-1.0.0-py3-none-any.whl`).
  - Attach proof PDF samples (e.g. `output/samples/proof_sample_P001_P005.pdf`).
  - Attach the preflight diagnostic certificate (`FINAL_KDP_PREFLIGHT_CERTIFICATE.txt`).

---

## 5. Free Security Features Checklist

In your GitHub repository **Settings** ➔ **Code security and analysis**:
- [x] **Dependabot alerts:** Turn ON (alerts when dependencies have known CVEs).
- [x] **Dependabot security updates:** Turn ON (auto-creates pull requests to patch vulnerabilities).
- [x] **Secret scanning:** Turn ON (detects leaked keys).
- [x] **Push protection:** Turn ON (blocks `git push` if an API key or password is detected in commits).
- [x] **CodeQL analysis:** Enabled via `.github/workflows/codeql.yml`.
