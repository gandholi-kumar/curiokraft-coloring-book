---
description: Mandatory rules and priority hierarchy for animal anatomy, posture, locomotion, and prompt construction across all CurioKraft publications.
globs: ["**/*animal*", "**/prompts*", "**/taxonomy.yaml", "**/agents.yaml", "**/debate_engine.py"]
---

# CurioKraft Animal Anatomy & Posture Rules

## 1. Core Mandate
Every agent constructing, reviewing, debating, or generating prompts for animals in CurioKraft publications MUST follow the authoritative standard in `docs/ANIMAL_ANATOMY_AND_POSTURE_STANDARD.md`.

## 2. Inviolable Laws
1. **Species Anatomy > Artistic Style**:
   Preschool styling, cute round eyes, chubby cheeks, and bold 5pt vector lines are strictly visual expressions and can NEVER alter an animal's species anatomy, limb count, skeletal structure, or natural locomotion.
2. **The Golden Posture Rule**:
   Never allow an image diffusion model to infer an animal's posture implicitly. Explicitly define:
   - What animal it is
   - How many limbs it has
   - How it naturally moves
   - Exactly how it is positioned
   - Which direction it faces (three-quarter front view preferred)
3. **Banned Ambiguities & Keywords**:
   - Never use the bare word `"standing"`. Always resolve to `"natural quadrupedal standing posture on all four legs"` or `"natural bipedal bird standing on two legs"`.
   - Never use `"joyful lively posing"` (causes anthropomorphic jumping/dancing poses).
   - Never use `"animal character"` (triggers cartoon humanoid mascots). Use `"baby [animal] illustration"`.
4. **Mandatory Negative Enforcements**:
   - For all quadrupedal animals: ALWAYS add `standing on two legs, upright on hind legs, bipedal stance, human-like posture, human arms, human hands, human feet, sitting like a human`.
   - For all birds: NEVER include quadrupedal tokens (`four legs`).
   - For all aquatic creatures: NEVER include terrestrial standing or ground tokens.

## 3. Mandatory 11-Block Prompt Order
1. `[SUBJECT]` - 2D toddler coloring book line art of cute baby [animal]
2. `[ANATOMY]` - Species anatomy, exact limb count, tail, ears, muzzle
3. `[POSTURE & ORIENTATION]` - Explicit posture (e.g. on all 4 legs) + 3/4 front view
4. `[SAFEGUARDS]` - Head/neck alignment, strict ban on upright standing/anthropomorphism
5. `[EXPRESSION]` - Sweet, gentle, friendly expression with simple rounded eyes
6. `[STYLE]` - Simplified preschool proportions preserving natural anatomy
7. `[LINE ART]` - Bold clean black vector outline, 5pt stroke, wide open coloring areas
8. `[COMPOSITION]` - Full body, 3:4 portrait, 25% white margin clearance
9. `[BACKGROUND]` - Pure white (#FFFFFF), zero shading, zero ground, zero elements
10. `[STRICT RESTRICTIONS]` - Strictly NO text, NO letters, NO words, NO color
11. `[NEGATIVE PROMPT]` - Species-specific negatives + standard coloring negatives
