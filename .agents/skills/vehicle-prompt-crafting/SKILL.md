---
name: vehicle-prompt-crafting
description: Expert system and workflow for generating, debating, and validating structurally authentic vehicle and transportation coloring book prompts. Use whenever crafting vehicle prompts or reviewing vehicle image generation results.
---

# Vehicle Prompt Crafting Skill

## Overview
This skill provides authoritative procedures, domain classification tables, structural specifications, and validation algorithms for crafting toddler-friendly coloring book prompts for vehicles and transportation across all CurioKraft publications.

The primary mandate is **Structural Propulsion Authenticity**: A vehicle's structural support and propulsion mechanics dictate its anatomy. Wheels must **never** be universally applied to non-wheeled vehicles such as rockets, helicopters, boats, or submarines.

---

## Vehicle Domain Classification Table

| Domain Class | Canonical Examples | Support / Propulsion Mechanism | Defining Structural Anatomy | Default Orientation | Mandatory Positive Specifications | Mandatory Negatives |
|---|---|---|---|---|---|---|
| **Wheeled 4-Wheel (Automobiles & Heavy)** | Car, Bus, Truck, Van, Taxi, Ambulance, Fire Truck, Police Car, Tractor, Wagon | 4 rubber tires / wheels supporting chassis | Chassis, cabin, large chunky round wheels with clean hubcaps, windshield, side windows, headlights, bumpers | Three-quarter side-front profile view | `large chunky round wheels, clean round hubcaps, clear colorable windshield and windows` | `complex engine parts, tiny mechanical chains, exhaust smoke, road, street, human driver` |
| **Wheeled 2-Wheel (Cycles & Light)** | Bicycle, Motorcycle, Scooter, Tricycle (3-wheel) | 2 inline wheels (or 3 for tricycle), frame | 2 clearly separated circular wheels, tubular frame, handlebars, seat, pedals/footrests | Side profile view displaying both wheels | `two clearly separated round wheels, sturdy tubular frame, front handlebars, seat` | `four wheels, car body, complex sprockets, tiny gear teeth, road, human rider` |
| **Rail Vehicles** | Train, Steam Locomotive, Subway, Tram, Trolley | Steel rail wheels along track baseline | Long locomotive boiler/cabin, smokestack/pantograph, cowcatcher grill, multiple round steel train wheels | Three-quarter side profile view | `multiple round train wheels aligned along bottom baseline, cozy engineer cab, front cowcatcher` | `rubber car tires, steering wheel, complex pistons, heavy dark smoke, road` |
| **Rotorcraft** | Helicopter | Twin horizontal landing skids (runner rails) + overhead main rotor | Rounded cockpit cabin, large clear windshield, top main rotor mast with flat blades, tail boom with vertical tail rotor, twin parallel landing skids | Three-quarter side profile view displaying cockpit, rotors, and skids | `twin horizontal parallel landing skids, wide top main rotor blades, slender tail boom with tail rotor, strictly NO wheels` | `wheels, tires, car wheels, bicycle wheels, landing gear wheels, road, airplane wings, jet engines` |
| **Fixed-Wing Aircraft** | Airplane, Jet, Biplane, Passenger Plane | Aerodynamic wings generating lift, minimal simple landing gear | Streamlined cylindrical fuselage, two wide symmetric horizontal wings, vertical tail fin with horizontal stabilizers, cockpit windshield, passenger windows | Three-quarter front-side view displaying full wingspan | `two wide symmetrical horizontal wings, streamlined fuselage, vertical tail fin, smooth cockpit windshield` | `car wheels, bicycle wheels, road, complex mechanical engines, military weapons, passengers` |
| **Spacecraft** | Rocket, Spaceship, Space Shuttle | Reaction thrusters / base stabilizer fins | Sleek cylindrical fuselage tapering upward to a smooth conical nose cone, round circular astronaut observation porthole, 3 to 4 bold flared stabilizing fins at base, clean rocket nozzle | Upright vertical or dynamic slight upward angle displaying complete body | `sleek aerodynamic rocket fuselage, pointed nose cone, circular porthole window, 3 to 4 flared base stabilizer fins, exhaust nozzle, strictly NO wheels` | `wheels, tires, car wheels, bicycle wheels, road wheels, landing gear, road, tracks, ground, wings with propellers` |
| **Watercraft** | Sailboat, Motorboat, Tugboat, Ship, Yacht, Canoe | Buoyant watertight hull resting on water baseline | Curved buoyant boat hull, flat deck, central mast with triangular sails (sailboat) or steering cabin (motorboat/tugboat) | Three-quarter side profile view displaying hull and upper deck | `smooth curved buoyant boat hull, sturdy central mast, crisp triangular sails, strictly NO wheels` | `wheels, tires, car wheels, bicycle wheels, landing gear, road, pavement, tracks, legs` |
| **Submersibles** | Submarine | Watertight cylindrical hull, diving fins, rear propeller | Elongated rounded cylindrical hull, top conning tower with periscope, round portholes, rear propulsion propeller and dive planes | Side profile view | `rounded elongated submarine hull, top conning tower with periscope, circular porthole windows, rear propeller, strictly NO wheels` | `wheels, tires, car wheels, landing gear, legs, road` |
| **Lighter-than-Air** | Hot Air Balloon, Blimp | Buoyant gas envelope + suspended passenger basket | Large rounded teardrop fabric balloon envelope with vertical stripe segments, suspension burner ropes, woven square/rounded basket suspended below | Upright frontal / three-quarter view | `large rounded teardrop balloon envelope with bold vertical stripe segments, sturdy suspension ropes, neat woven basket, strictly NO wheels` | `wheels, tires, wings, propellers, road` |

---

## Prompt Construction Template (11-Block Sequence)

```text
Ultra-clean 2D preschool toddler coloring book line art vector illustration of a cute classic [VEHICLE]. Authentic [domain_class] vehicle anatomy with a [defining structural anatomy]. Supported by [support_structure]. [Default orientation from table]. [Safeguards: e.g. strictly NO wheels for rotorcraft/spacecraft/watercraft; exactly two wheels for cycles]. Clear, recognizable preschool proportions with simplified mechanical details. Bold clean black vector outline, 5pt stroke, wide open coloring areas, perfectly centered, vertical portrait 3:4 aspect ratio framing, generous 25% empty white margin space around the centered subject on all four sides, wide breathing room, pure stark white background (#FFFFFF), zero shading, zero grayscale, zero gradients, zero shadows, no background elements, strictly NO text, NO letters, NO words.
```

---

## Validation Checklist (Run Before Approval)

1. **Domain Verification**: Has the vehicle's propulsion/support domain been correctly identified?
2. **Wheel Audit (CRITICAL)**:
   - If the vehicle is a **Rotorcraft** (Helicopter), **Spacecraft** (Rocket), or **Watercraft** (Sailboat, Boat, Submarine): Are wheels **100% ABSENT** from the positive prompt?
   - Are anti-wheel negative tokens (`wheels, tires, car wheels, landing gear wheels, road`) explicitly present in the negative prompt?
3. **Wheel Count Accuracy**:
   - For **Cycles** (Bicycle, Motorcycle, Scooter): Are exactly **two wheels** specified (never four)?
   - For **Automobiles / Trucks / Buses**: Are large chunky round wheels specified?
4. **Support Structure**:
   - Helicopters have **twin parallel landing skids**.
   - Rockets have **flared base stabilizer fins & rocket nozzle**.
   - Sailboats/Boats have a **buoyant curved hull**.
5. **Perspective & Orientation**: Is the orientation appropriate (e.g. three-quarter profile showing structure, upright for rockets)?
6. **Contradiction Audit**: Do the positive and negative prompts pass the contradiction check (e.g., ensuring negative tokens do not filter out necessary elements)?
