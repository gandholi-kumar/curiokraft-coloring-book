---
name: animal-prompt-crafting
description: Expert system and workflow for generating, debating, and validating anatomically authentic animal, aquatic, land, and aerial coloring book prompts across age tiers and dynamic environments.
---

# Animal & Living Being Prompt Crafting Skill

## Overview
This skill provides the authoritative procedures, decision tables, and validation algorithms for crafting coloring book prompts for living creatures across all CurioKraft publications.

The pipeline is **100% skill- and configuration-driven**. Python orchestration code contains **zero hardcoded biomes or static negative lists**. Instead, the orchestrator and agents adapt dynamically based on:
1. `target_audience.age_min` / `age_max`: Determines anatomical complexity (toddler simplified baby proportions for 1–4 vs authentic living species fidelity for 4–10).
2. `page_record.composition` / `visual_style.background`: Dynamically resolves against `environment_templates` in `config/taxonomy.yaml` (e.g., `aquatic`, `land`, `air`).
3. **Automatic Fallback**: If no environment is specified or if `composition: "single_centered_object"` / `background: "none"`, the engine cleanly falls back to Mode A (isolated single-object line art on pure white canvas with zero background elements, identical to Vol 1 Toddler books).

---

## Locomotion & Habitat Classification Table

| Class | Examples | Limbs / Organs | Default Posture | Default Orientation | Mandatory Negatives |
|---|---|---|---|---|---|
| **Aquatic (Marine & Freshwater)** | Fish, Dolphin, Whale, Shark, Octopus, Sea Turtle, Ray | Fins, flukes, paddle flippers, or tentacles | Natural streamlined swimming or hovering posture immersed in water | Dynamic swimming profile / 3/4 angle | `legs, feet, paws, standing on ground, walking upright, human arms, clothes, diver, boat, trash, murky water` |
| **Quadrupeds** | Lion, Tiger, Dog, Cat, Bear, Elephant, Giraffe, Horse, Cow, Sheep, Rabbit | 4 legs | Standing naturally on all 4 legs supporting the body | Three-quarter front view | `standing on two legs, upright on hind legs, bipedal stance, human-like posture, human arms, human hands, human feet, sitting like a human` |
| **Bipeds** | Chicken, Duck, Penguin, Flamingo, Ostrich | 2 legs + wings | Standing naturally on 2 feet balanced | Three-quarter view | `four legs, quadrupedal stance, human arms, human hands, human shoes` |
| **Amphibians** | Frog, Salamander, Axolotl | 4 limbs | Low-to-ground crouching or natural underwater floating | Three-quarter front view | `standing upright, human limbs, bipedal stance` |
| **Invertebrates & Crustaceans** | Crab, Lobster, Snail, Clam | Walking legs, claws, or gliding foot | Natural seafloor crawling, resting on rock, or perched | Natural perspective | `human hands, human feet, anthropomorphic face` |
| **Insects** | Butterfly, Bee | 6 legs + wings | Natural resting or flying with wings symmetrical | Natural resting/perched view | `human arms, human hands, human shoes, clothing` |
| **Arboreal & Avian** | Monkey, Koala, Owl, Eagle, Parrot | 4 grasping limbs / 2 wings | Species-appropriate branch perching or gliding | Three-quarter view | `human standing upright, bipedal stance, clothes, cages` |

---

## Prompt Construction: Mode A — Isolated Toddler Fallback (Age 1–4, `background: "none"`)

Used whenever `composition: "single_centered_object"` or `visual_style.background: "none"` (or no environment template matches):

```text
Ultra-clean 2D preschool toddler coloring book line art vector illustration of a cute friendly baby [SPECIES]. Natural [species] anatomy with a recognizable baby-[species] body, [anatomical features]. [Default posture from table]. [Default orientation from table]. Head and neck positioned naturally relative to the torso. Do not stand upright on the hind legs. Do not use a human-like posture. Do not anthropomorphize the body. Sweet, gentle, friendly expression with simple rounded eyes and a happy approachable face. Simplified preschool-friendly proportions while preserving natural animal anatomy and species silhouette. Bold clean black vector outline, 5pt stroke, wide open coloring areas, perfectly centered, vertical portrait 3:4 aspect ratio framing, generous 25% empty white margin space around the centered subject on all four sides, wide breathing room, pure stark white background (#FFFFFF), zero shading, zero grayscale, zero gradients, zero shadows, no background elements, strictly NO text, NO letters, NO words.
```

---

## Prompt Construction: Mode B — Dynamic Integrated Habitat Scenes (Age 4–10)

Triggered whenever `composition: "integrated_<env>_scene"` (e.g. `integrated_aquatic_scene`, `integrated_land_scene`, `integrated_air_scene`) or `visual_style.background: "<env>_environment"`.

### 1. Unified Design System Across All Biomes
- **Single Integrated Scene**: Render the creature naturally immersed inside its authentic habitat (water currents & coral for aquatic; savanna grass & trees for land; clouds & canopy branches for air). The creature is not a floating cutout.
- **Shared Art Style**: The subject and background environment must share the **exact same crisp 2D vector coloring book line art style**.
- **Top Margin Typography Reservation**: Maintain generous empty white space at the top 20% of the canvas to allow programmatic typesetting of the creature's name by the Python compositor.
- **Stroke Weight Hierarchy & Boundary Separation**:
  - **Primary Subject**: Bold 4pt black vector outline on the outer silhouette of the creature, with 2.5pt internal anatomical detail lines.
  - **Environmental Background**: Lighter 2pt clean vector outlines for habitat elements.
  - **Boundary Separation**: Background lines maintain a clean 4–8px whitespace buffer before contacting the creature's perimeter contour, ensuring children can clearly identify and color the animal without color bleeding into the background.

### 2. Biome Habitat Resolutions (from `config/taxonomy.yaml`)

- **Aquatic (`integrated_aquatic_scene` / `aquatic_environment`)**:
  - *Action*: `swimming in its natural ocean habitat`
  - *Elements*: `rising air bubbles, fluid gentle water currents, swaying kelp fronds, and colorable coral reef formations on the sea bed`
  - *Exclusions*: `murky water, diver, boat, trash, human, clothes`

- **Land (`integrated_land_scene` / `land_environment`)**:
  - *Action*: `standing or resting naturally in its natural land habitat`
  - *Elements*: `swaying grasses, wildflowers, gentle rolling ground contours, distant stylized trees, and foliage`
  - *Exclusions*: `cars, pavement, buildings, trash, cages, zoo bars, fences, human, clothes`

- **Air (`integrated_air_scene` / `air_environment`)**:
  - *Action*: `gliding or perching naturally in its natural open sky canopy habitat`
  - *Elements*: `soft stylized puffy clouds, open sky currents, gentle sun rays, and leafy treetop branch perches`
  - *Exclusions*: `cages, airplanes, smoke, smog, power lines, indoor ceiling, human, clothes`

### 3. Master Integrated Scene Prompt Template
```text
Clean 2D educational coloring book line art vector illustration of an authentic living [SPECIES] [SUBJECT_ACTION] for ages [AGE_MIN]-[AGE_MAX].
[SPECIES_ANATOMY]. [POSTURE]. [ORIENTATION]. [SAFEGUARDS].
The [SPECIES] is naturally immersed in a cohesive [HABITAT_NAME] with [HABITAT_ELEMENTS], all rendered in the same clean vector line art style.
[STROKE_HIERARCHY]
[MARGIN_RESERVE]
Pure stark white background (#FFFFFF), strictly NO color fills, zero shading, zero grayscale, zero gradients, zero shadows, zero photorealistic textures, zero airbrushing.
### 4. Anti-Measurement Dimension & Zero-Color-Priming Rules

#### Rule A: Zero Engineering Measurements in Positive Prompts
- **Strictly Prohibited**: Words and phrases specifying physical dimensions, such as `"1.0 inch"`, `"300px"`, `"safe live area"`, `"margin line"`, `"cut line"`, or `"ruler"`.
- **Why**: Text-to-image diffusion models (e.g. Imagen 3, Stable Diffusion) are trained on millions of design templates, architectural blueprints, and KDP margin guides. Mentioning physical dimensions primes the text encoder to synthesize literal CAD dimension arrows, measurement lines, and ruler tick marks directly on the artwork!
- **Required Alternative**: Use relative compositional phrasing:
  - *Toddler Mode*: `"vertical portrait 3:4 aspect ratio framing, generous 25% empty white margin space around the centered subject on all four sides, wide breathing room"`
  - *Integrated Mode*: `"Leave generous 20% empty white margin space at the top of the canvas for typography, with the subject positioned naturally in the lower 80%."`
- **Mandatory Negative Tokens**: All prompt configurations must enforce:
  `dimension arrows, measurement lines, ruler marks, guidelines, blueprint lines, borders, frames, separator lines`

#### Rule B: Zero Color Priming in Positive Prompts
- **Strictly Prohibited**: Mentioning specific forbidden color words in the positive prompt (e.g., do NOT write `"zero red"`, `"zero pink"`, `"no blue"` in the positive prompt).
- **Why**: Text encoders (CLIP / T5) attend to the tokens `"red"`, `"pink"`, and `"blue"`. Even with negation words like "zero" or "no", positive token attention activates the color concept cluster, causing diffusion models to generate colored fills (e.g., red oarfish crests, blue whale skin).
- **Required Positive Pattern**: Use purely structural line art directives:
  `"Strictly uncolored hollow black vector outlines with empty white interior body for coloring, strictly zero color fills, zero shading, zero grayscale, zero gradients, zero shadows, zero photorealistic textures, zero airbrushing."`
- **Required Negative Pattern**: Place all specific color names strictly into the **Negative Prompt**:
  `red, red crest, red fins, pink, pink crest, pink fins, blue, blue skin, blue body, blue fill, blue color, orange, color fills, colored body, colored creature, colored in, tinted, color wash`

---

## Validation Checklist (Run Before Approval)

1. **Locomotion & Anatomy Check**:
   - Is species locomotion determined according to the table?
   - For ages 4–10, are biological traits (fin counts, gills, scutes, paws, claws) species-authentic rather than baby-distorted?
2. **Environment & Habitat Consistency**:
   - If `env_template is None` (or `background: "none"`): Is background strictly empty pure white (#FFFFFF) with zero elements?
   - If `env_template` is active: Are habitat elements rendered in the matching clean vector line art style?
3. **Stroke Weight & Coloring Separability**:
   - Is there a clear 4pt / 2pt stroke hierarchy between foreground creature and background habitat?
   - Can the creature's outline be clearly separated for filling with crayons/markers?
4. **Anti-Measurement Dimension Check**:
   - Are physical measurements (`1.0 inch`, `300px`, `safe live area`) completely absent from the positive prompt?
   - Are `dimension arrows, measurement lines, ruler marks, guidelines, blueprint lines` present in the negative prompt?
5. **Zero Color Priming Check**:
   - Are forbidden color names (`red`, `blue`, etc.) completely absent from the positive prompt and strictly routed to the negative prompt?
   - Is the creature specified with hollow black vector outlines and empty white interior coloring zones?
6. **Line Art Purity**:
   - Binary black lines only (`#000000` on `#FFFFFF`)?
   - Zero gray pixels, zero airbrush gradients, zero stippling, zero crosshatching?
7. **Zero Text Mandate**:
   - Is all text, letters, and numbers strictly forbidden in the AI prompt to reserve the top margin for programmatic Python typography?
