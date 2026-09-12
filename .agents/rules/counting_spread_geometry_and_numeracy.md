---
description: Mandatory rules and spatial geometry standards for educational counting spreads, column limits, isotropic object selection, and adversarial numeracy audits across all CurioKraft publications.
globs: ["**/*counting*", "**/prompts*", "**/curriculum.yaml", "**/agents.yaml", "**/debate_engine.py", "**/pages*.json"]
---

# CurioKraft Counting Spread Geometry & Numeracy Rules

## 1. Core Mandate
Every agent constructing, reviewing, debating, or generating prompts for educational counting spreads (such as Numbers 0–5, Numbers 6–10, and multi-item flashcard grids) MUST obey the mathematical spatial limits and object selection criteria defined in this standard.

---

## 2. Spatial Geometry & Column Limit Laws

1. **Partitioned Container Aspect Ratio**:
   - In standard 2-column spread layouts (e.g. 2 flashcards per row on an 8.5x11 / 3:4 portrait canvas), each flashcard is a half-width container.
   - The large bubble numeral occupies ~35–40% of the box width on the left.
   - The remaining drawing area on the right has an aspect ratio of $\approx 0.8:1$ to $1.1:1$ (portrait-oriented or square).

2. **The Horizontal Column Limit Law ($C_{\text{max}} \le 3$)**:
   - In a portrait or square drawing zone ($W/H \le 1.1$), NEVER attempt to pack 4 or more columns horizontally ($C > 3$).
   - Diffusion image generators require sufficient margin clearance between distinct vector line art objects. Forcing 4 columns into a half-width card results in horizontal compression and causes the diffusion model to drop a column to fit the space (e.g. $4 \times 2$ or $2 \times 4$ collapsing into a $3 \times 2$ grid of 6 items).
   - In full-width hero flashcards (spanning the entire page width, $W/H \ge 1.8$), horizontal column limit expands to $C_{\text{max}} \le 6$.

3. **Mathematical Grid Factorization**:
   - Every count $N$ must be factorized into $(R \text{ rows} \times C \text{ columns})$ such that $C \le C_{\text{max}}$.
   - **For Count 8**: $2 \text{ rows} \times 4 \text{ columns}$ is STRICTLY PROHIBITED. Count 8 MUST be structured as **$4 \text{ rows} \times 2 \text{ columns}$** ($4 \times 2$ vertical array, 4 rows of 2 items). This naturally matches the tall height of the numeral and guarantees generous horizontal breathing room.
   - **For Count 6**: $3 \text{ rows} \times 2 \text{ columns}$ (or $2 \text{ rows} \times 3 \text{ columns}$).
   - **For Count 9**: $3 \text{ rows} \times 3 \text{ columns}$ square matrix.
   - **For Count 4**: $2 \text{ rows} \times 2 \text{ columns}$ square matrix.
   - **For Count 2**: $2 \text{ rows} \times 1 \text{ column}$ (vertical stack).

4. **Explicit Coordinate Prompts**:
   - Prompts must define explicit row-by-row coordinates rather than vague clusters:
     `Row 1: {c} items; Row 2: {c} items; ...; left column has {R} items, right column has {R} items`.

---

## 3. High-Count Object Selection Criteria ($N \ge 6$)

For cards with counts $N \ge 6$, agents must evaluate candidate objects against the following physical and developmental rubric:

1. **$1:1$ Isotropic Aspect Ratio**:
   - Candidate objects must have a compact, roughly balanced aspect ratio ($0.8 \le W/H \le 1.25$).
   - Horizontally wide objects ($W \gg H$, such as ribbon bows, airplanes, glasses, cars, butterflies) are strictly rejected for counts $\ge 6$ because their wide wings/tails cause adjacent items to collide.

2. **Single Closed Vector Contour**:
   - Objects must feature a single, continuous, bold outline enclosing a wide, open coloring interior.
   - Micro-textures, loose trailing tails, knots, complex multi-part segments, and thin crevices are prohibited. Toddlers using jumbo crayons must be able to color each item cleanly.

3. **Inanimate & 100% Faceless Taxonomy**:
   - High-count items (6–10) must be pure inanimate objects.
   - Strictly NO cartoon eyes, smiles, or faces on high-count items. Rendering 6–10 faces in a single card results in muddy facial artifacts and visual clutter.

4. **Spread Silhouette Contrast**:
   - Across a multi-card spread, each card's object must present a visually distinct geometric silhouette (e.g. circle vs slender vertical vs star vs ring vs heart). Agents must prevent duplicate basic shapes on the same spread.

---

## 4. Adversarial Red-Team & Judge Protocol

1. **Round 3 Critic Miscount Audit**:
   - `AGT-006-REDTEAM` must mathematically audit every card count $N$ and layout $(R, C)$.
   - The Critic identifies collapse modes (e.g. dropping a row or column to $(R-1) \times C$ or $R \times (C-1)$) and count neighbors ($N-1, N+1$).
   - The Critic actively outputs the recommended negative hardening tokens during Round 3 debate.

2. **Round 4 Judge Synthesis**:
   - `AGT-007-JUDGE` incorporates the Critic's debated negative hardening tokens into the final negative prompt.
   - No silent Python auto-injections; all hardening tokens must be visible in the debate log.
