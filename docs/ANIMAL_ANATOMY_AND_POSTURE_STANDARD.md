# CURIOKRAFT CHILDREN'S COLORING BOOK SYSTEM
## Authoritative Animal Anatomy, Locomotion, Posture & Prompt Hierarchy Standard

---

### Executive Purpose
This document is the **single source of truth** for animal anatomy, posture, locomotion, body orientation, and prompt construction across all CurioKraft publication volumes (Volume 1, Volume 2, and future series).

All internal debate agents (`AGT-001` through `AGT-008`), programmatic prompt builders, and AI assistants MUST strictly enforce this standard.

---

### 1. The Core Golden Rules

1. **Anatomy Governs Style (Rule 10B.2 & Rule 39)**:
   Artistic styling, preschool simplification, and "cute" modifiers can **never** alter an animal's species-specific anatomy, limb count, skeletal structure, or natural locomotion.

2. **The Golden Posture Rule (Rule 10A.15 & Rule 47)**:
   > **Never allow the image generator to decide an animal's fundamental posture implicitly.**
   > Make the animal cute through facial expression (smiling round eyes, chubby cheeks), simplified outlines, and preschool proportions — **never** by giving it humanoid posture, human arms, or human clothing.

3. **Ambiguity Ban (Rule 26 & Rule 10B.11)**:
   Never use the bare word `"standing"`. Always resolve it explicitly to `"natural quadrupedal standing on all four legs"` or `"natural bipedal standing on two feet"` according to the animal's natural locomotion.

4. **"Lively Posing" and "Character" Ban (Rule 13, 14 & Rule 10A.13)**:
   Do NOT use `"joyful lively posing"` or `"animal character"`. Diffusion models interpret these as license to generate bipedal, dancing, or humanoid cartoon mascots. Convert all behavior into species-appropriate actions while maintaining quadrupedal/natural posture.

---

### 2. Absolute Priority Hierarchy (Rule 10B.2)

When constructing or evaluating prompts, instructions must be resolved in this exact priority sequence:

```text
LEVEL 1: Species Identity & Fundamental Anatomy  (Limb count, head, tail, joint structure)
   ↓
LEVEL 2: Species-Specific Locomotion              (Walking, hopping, swimming, flying, slithering)
   ↓
LEVEL 3: Valid User Action/Posture                (Action must be anatomically valid for species)
   ↓
LEVEL 4: Species-Appropriate Posture              (Standing on 4 legs, perched, horizontal swimming)
   ↓
LEVEL 5: Natural Body Orientation                 (Three-quarter front view to clearly reveal limbs)
   ↓
LEVEL 6: Anatomical Integrity & Limb Placement    (Limbs grounded, neck attached, no floating paws)
   ↓
LEVEL 7: Full-Body Composition                    (Full body, vertical 3:4 portrait, 25% margin)
   ↓
LEVEL 8: Facial Expression                        (Friendly, gentle, simple round smiling eyes)
   ↓
LEVEL 9: Preschool Line Art Style                 (Bold 5pt black outline, pure white #FFFFFF)
   ↓
LEVEL 10: Strict Prohibitions                     (Zero shading, zero text, animal-specific negatives)
```

> **Higher-level rules constrain lower-level rules. Lower-level rules may never modify higher-level anatomy.**

---

### 3. Locomotion Categories & Decision Matrix (Section 10A)

#### Class A: Quadrupedal Mammals
* **Species**: Lion, Tiger, Leopard, Cheetah, Dog, Puppy, Cat, Kitten, Rabbit, Fox, Wolf, Bear, Elephant, Giraffe, Zebra, Horse, Cow, Goat, Sheep, Deer, Pig, Camel, Donkey.
* **High-Risk Subgroup**: Puppy, Dog, Rabbit, Bear, Fox, Cat (most vulnerable to humanoid standing).
* **Anatomical Structure**: Exactly 4 legs, 4 paws/hooves attached to a horizontal torso, species tail, and anatomically connected neck.
* **Default Posture**: `Natural quadrupedal standing posture, standing securely on all four legs with all four paws/hooves supporting the body.`
* **Default Orientation**: `Three-quarter front view showing the complete body and limbs.`
* **Mandatory Safeguards**: `Do not stand upright on hind legs. Do not use a human-like standing posture. Do not anthropomorphize the body.`
* **Mandatory Negatives**: `standing on two legs, upright on hind legs, bipedal stance, human-like posture, human arms, human hands, human feet, sitting like a human, anthropomorphic body`.

#### Class B: Naturally Bipedal Animals (Birds & Fowl)
* **Species**: Chicken, Chick, Duck, Hen, Rooster, Penguin, Flamingo, Ostrich, Emu.
* **Anatomical Structure**: Exactly 2 legs/feet + 2 wings, beak/bill, feathers.
* **Default Posture**: `Natural bird standing posture on two legs, standing balanced on both feet.`
* **Default Orientation**: `Three-quarter view showing both feet supporting the body.`
* **Critical Invariant**: **Never apply quadrupedal 4-leg rules to birds.**
* **Mandatory Negatives**: `four legs, quadrupedal stance, human arms, human hands, human shoes`.

#### Class C: Aquatic / Marine Creatures
* **Species**: Fish, Dolphin, Whale, Shark, Octopus.
* **Anatomical Structure**: Streamlined body, dorsal/pectoral fins, tail fluke (or 8 symmetrical arms for octopus). Zero legs.
* **Default Posture**: `Natural horizontal streamlined swimming posture.`
* **Critical Invariant**: **Never use "standing" or terrestrial ground.**
* **Mandatory Negatives**: `legs, feet, paws, standing on ground, terrestrial walking, walking upright`.

#### Class D: Amphibians & Crawlers
* **Frog**: 4 limbs with folded hind legs. Default posture is `natural low-to-ground crouching posture with hind legs folded under the body and front paws grounded`.
* **Turtle**: Low quadrupedal stance, 4 stubby flippers/legs supporting protective shell.
* **Snail**: Legless soft body, spiral shell on back, gliding along surface, eye stalks.
* **Snake**: Elongated legless body in a gentle natural curved/slithering position. Zero limbs.

#### Class E: Flying Insects
* **Species**: Butterfly, Bee.
* **Anatomical Structure**: 6 delicate legs (simplified for preschool), 2 or 4 wings, antennae.
* **Default Posture**: `Natural resting or flying posture with wings positioned symmetrically and naturally.`
* **Mandatory Negatives**: `human arms, human hands, human shoes, cartoon mascot clothing`.

#### Class F: Arboreal / Primates
* **Species**: Monkey, Chimpanzee, Gorilla, Sloth, Koala, Squirrel.
* **Anatomical Structure**: 4 grasping limbs / prehensile tail.
* **Default Posture**: `Natural species-appropriate quadrupedal stance or natural seated monkey posture.`
* **Mandatory Safeguards**: **Never allow human bipedal standing.**

---

### 4. Orientation & Limb Visibility Invariants (Rule 18 & 10B.14)

1. **Three-Quarter Front View Preference**:
   * A pure frontal view hides hind legs behind front legs.
   * A pure side profile often merges bilateral legs into single overlapping outlines.
   * A **three-quarter front view** provides optimal depth, ensuring all 4 legs are distinguishable without distortion while displaying the friendly facial features.
2. **Natural Placement > Forced Visibility**:
   * Do NOT force unnatural leg splaying, twisted torsos, or floating paws to expose every limb.
   * Mandate: `"All four legs anatomically present and clearly distinguishable in natural perspective."`

---

### 5. Standardized 11-Block Animal Prompt Architecture

Every animal illustration prompt must be constructed using this exact 11-block order:

```text
[1. SUBJECT]
Ultra-clean 2D preschool toddler coloring book line art vector illustration of a cute friendly baby [ANIMAL].

[2. ANATOMY & BODY]
Natural [species] anatomy with a recognizable baby-[animal] body, [limb count, paws/hooves, ears, tail, muzzle].

[3. POSTURE & ORIENTATION]
[Default natural posture, e.g., Natural quadrupedal standing posture, standing securely on all four legs with all four paws supporting the body]. [Default orientation, e.g., Three-quarter front view with the complete body visible].

[4. ANATOMICAL SAFEGUARDS]
Head and neck positioned naturally relative to the body. Do not stand upright on the hind legs. Do not use a human-like standing posture. Do not anthropomorphize the body.

[5. EXPRESSION]
Sweet, gentle, friendly expression with simple rounded eyes and a happy, approachable face.

[6. ART STYLE]
Simplified preschool-friendly proportions while preserving natural animal anatomy and species silhouette.

[7. LINE ART]
Bold, clean black vector outline, approximately 5pt stroke, wide open coloring areas.

[8. COMPOSITION]
Full-body centered subject, vertical portrait 3:4 aspect ratio framing, generous 25% empty white margin space around the subject on all four sides, complete animal visible without cropping.

[9. BACKGROUND]
Pure stark white background (#FFFFFF), zero shading, zero grayscale, zero gradients, zero shadows, no background elements, no scenery, no ground.

[10. STRICT RESTRICTIONS]
Strictly NO text, NO letters, NO words, NO color, NO photorealism, NO 3D rendering.

[11. NEGATIVE PROMPT]
[Species-specific negatives: standing on two legs, upright on hind legs, bipedal stance, human-like posture, human arms, human hands, human feet, sitting like a human, human clothes, human shoes], shading, shadows, gradients, gray, grayscale, color, textures, 3d, photorealistic, intricate patterns, background scenery, floor, ground, sky, borders, frames, text, letters, words, labels.
```

---

### 6. Contradiction Validation Algorithm (Rule 10B.18)

Before finalizing any animal prompt, the system MUST verify that no negative term contradicts a positive requirement:
* If positive specifies `"two legs"` (e.g. bird), negative must NOT include `"two legs"`.
* If positive specifies `"hopping"` (e.g. rabbit), negative must NOT include `"hopping"`.
* If positive specifies `"four legs"` (e.g. quadruped), negative must NOT include `"four legs"`.

---

### 7. Checklist for Multi-Agent Verification Gate (Rule 10B.27)

Every animal prompt MUST pass all 10 gates before receiving an `APPROVED` verdict:
- [ ] 1. Species correctly identified and mapped to its locomotion class?
- [ ] 2. Limb count and limb type explicitly stated?
- [ ] 3. Natural locomotion explicitly defined?
- [ ] 4. Posture explicitly defined (no bare "standing")?
- [ ] 5. For quadrupeds: "standing on all four legs" explicitly mandated?
- [ ] 6. For birds: bipedal standing mandated without quadrupedal rules?
- [ ] 7. Body orientation explicitly stated (3/4 front view preferred)?
- [ ] 8. Anti-anthropomorphic safeguards included in positive prompt?
- [ ] 9. Species-specific negatives added (anti-bipedal for quadrupeds)?
- [ ] 10. Zero contradictions between positive and negative prompts?
