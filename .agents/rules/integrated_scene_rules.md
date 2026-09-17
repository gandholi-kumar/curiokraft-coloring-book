---
description: Universal rules and hierarchy for integrated habitat scenes versus isolated single-object coloring pages across all CurioKraft publications.
globs: ["**/*prompt*", "**/taxonomy.yaml", "**/agents.yaml", "**/debate_engine.py"]
---

# Universal Integrated Scene & Environment Rules

## 1. Core Principle
CurioKraft publications support two distinct scene archetypes:
1. **Dynamic Integrated Habitat Scenes** (`composition: "integrated_<env>_scene"` or `visual_style.background: "<env>_environment"`):
   - Used for older developmental tiers (Ages 4–10) where creatures are contextualized in their natural living habitats (e.g. aquatic, land, air, prehistoric).
2. **Isolated Single-Object Fallback** (`composition: "single_centered_object"` or `visual_style.background: "none"`):
   - Used for toddler early-learning publications (Ages 1–4, Vol 1 style) where distraction-free isolation is pedagogically required.

## 2. Inviolable Laws for Integrated Habitat Scenes

1. **Vector Art Style Cohesion**:
   The primary living subject and all environmental background elements MUST share the exact same clean 2D vector line art coloring book style. Zero mixing of sketchy backgrounds with flat subjects.
2. **Stroke Weight Hierarchy**:
   - **4pt Black Vector Outline**: Outer perimeter contour of the primary living creature.
   - **2.5pt Internal Contours**: Anatomical division lines (scales, muscle ridges, fins, paws, feathers).
   - **2pt Vector Outline**: Background habitat elements (kelp, coral, waves, trees, grass, clouds, branches).
3. **Boundary Separation Whitespace**:
   Background habitat lines must maintain an uninterrupted 4–8px white buffer before touching the primary creature's silhouette contour to prevent visual collision and ensure effortless coloring fill.
4. **Top 20% Margin Reservation for Typography**:
   AI generation MUST leave the top 20% of the canvas completely blank (#FFFFFF). The educational species name is rendered programmatically by the Python compositor in a hollow, colorable uppercase font.
5. **Zero Text Mandate**:
   Prompts must strictly forbid text, letters, words, and labels (`strictly NO text, NO letters, NO words`) so the AI never hallucinates illegible characters.
6. **Binary Line Art Purity**:
   Pure black (#000000) outlines on pure white (#FFFFFF) canvas. Strictly zero grayscale, zero airbrush shading, zero textures, zero gradients, zero shadows.

## 3. Dynamic Environment Resolution Law
Python code (`debate_engine.py`) MUST NOT contain hardcoded biomes or `if is_<biome>:` conditionals. All habitat definitions, actions, elements, and negative exclusions MUST be resolved dynamically from `environment_templates` in `config/taxonomy.yaml`. If no environment matches, the system MUST cleanly fall back to the Isolated Single-Object archetype.
