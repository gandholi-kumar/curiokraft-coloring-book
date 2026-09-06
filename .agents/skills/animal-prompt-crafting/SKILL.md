---
name: animal-prompt-crafting
description: Expert system and workflow for generating, debating, and validating anatomically authentic animal coloring book prompts. Use whenever crafting animal prompts or reviewing animal image generation results.
---

# Animal Prompt Crafting Skill

## Overview
This skill provides the authoritative procedures, decision tables, and validation algorithms for crafting toddler-friendly coloring book prompts for the animal kingdom across all CurioKraft publications.

## Locomotion Classification Table

| Class | Examples | Limbs | Default Posture | Default Orientation | Mandatory Negatives |
|---|---|---|---|---|---|
| **Quadrupeds** | Lion, Tiger, Dog, Cat, Bear, Elephant, Giraffe, Horse, Cow, Sheep, Rabbit | 4 legs | Standing naturally on all 4 legs supporting the body | Three-quarter front view | `standing on two legs, upright on hind legs, bipedal stance, human-like posture, human arms, human hands, human feet, sitting like a human` |
| **Bipeds** | Chicken, Duck, Penguin, Flamingo, Ostrich | 2 legs + wings | Standing naturally on 2 feet balanced | Three-quarter view | `four legs, quadrupedal stance, human arms, human hands, human shoes` |
| **Aquatic** | Fish, Dolphin, Whale, Shark, Octopus | Fins/flukes (or 8 arms) | Horizontal streamlined swimming posture | Swimming profile / 3/4 angle | `legs, feet, paws, standing on ground, walking upright` |
| **Amphibians** | Frog | 4 limbs | Low-to-ground crouching with folded hind legs | Three-quarter front view | `standing upright, human limbs, bipedal stance` |
| **Invertebrates** | Snail | 0 legs (gliding foot) | Gliding low along surface with shell upright | Side profile showing antennae | `legs, paws, feet, human limbs` |
| **Insects** | Butterfly, Bee | 6 legs + wings | Natural resting or flying with wings symmetrical | Natural resting/perched view | `human arms, human hands, human shoes, clothing` |
| **Arboreal** | Monkey, Chimpanzee, Koala | 4 grasping limbs | Species-appropriate 4-limbed branch stance or crouch | Three-quarter view | `human standing upright, bipedal stance, clothes` |

## Prompt Construction Template
```text
Ultra-clean 2D preschool toddler coloring book line art vector illustration of a cute friendly baby [SPECIES]. Natural [species] anatomy with a recognizable baby-[species] body, [anatomical features]. [Default posture from table]. [Default orientation from table]. Head and neck positioned naturally relative to the torso. Do not stand upright on the hind legs. Do not use a human-like posture. Do not anthropomorphize the body. Sweet, gentle, friendly expression with simple rounded eyes and a happy approachable face. Simplified preschool-friendly proportions while preserving natural animal anatomy and species silhouette. Bold clean black vector outline, 5pt stroke, wide open coloring areas, perfectly centered, vertical portrait 3:4 aspect ratio framing, generous 25% empty white margin space around the centered subject on all four sides, wide breathing room, pure stark white background (#FFFFFF), zero shading, zero grayscale, zero gradients, zero shadows, no background elements, strictly NO text, NO letters, NO words.
```

## Validation Checklist (Run Before Approval)
1. Has species locomotion been determined?
2. Are all legs explicitly grounded?
3. Is bare "standing" avoided?
4. Is "joyful lively posing" absent?
5. Is "animal character" replaced with baby animal illustration?
6. Are anti-anthropomorphic negatives present in the negative prompt?
7. Did the positive and negative prompts pass the contradiction check?
