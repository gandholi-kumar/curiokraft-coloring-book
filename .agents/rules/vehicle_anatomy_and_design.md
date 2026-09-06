---
description: Mandatory rules and priority hierarchy for vehicle anatomy, structural design, propulsion domains, and prompt construction across all CurioKraft publications.
globs: ["**/*vehicle*", "**/prompts*", "**/taxonomy.yaml", "**/agents.yaml", "**/debate_engine.py"]
---

# CurioKraft Vehicle Anatomy & Structural Design Rules

## 1. Core Mandate
Every agent constructing, reviewing, debating, or generating prompts for vehicles and transportation in CurioKraft publications MUST follow the authoritative standard in `docs/VEHICLE_DESIGN_AND_ANATOMY_STANDARD.md` and the `vehicle-prompt-crafting` skill.

## 2. Inviolable Laws of Vehicle Design

1. **Propulsion & Structural Support Governs Anatomy**:
   Preschool styling, bold 5pt vector outlines, and cute rounded aesthetics can **NEVER** alter a vehicle's fundamental propulsion or structural support mechanism.
   - **Rockets** do not have wheels; they have aerodynamic cylindrical bodies, nose cones, base stabilizer fins, and exhaust nozzles.
   - **Helicopters** do not have wheels; they have rounded cockpit bubbles, overhead main rotors, tail rotors, and twin horizontal landing skids (runner rails).
   - **Sailboats and Boats** do not have wheels; they have buoyant curved hulls, decks, and sails/cabins resting on a clean water baseline.
   - **Bicycles and Motorcycles** have exactly **two wheels** connected by a tubular frame (never four wheels).
   - **Cars, Trucks, and Buses** have four chunky round wheels supporting an automotive chassis.

2. **The Universal Wheel Ban for Non-Wheeled Vehicles**:
   Image diffusion models must **NEVER** be allowed to infer wheels on non-wheeled vehicles.
   - When generating **Rockets**, **Helicopters**, **Sailboats**, **Boats**, **Submarines**, or **Hot Air Balloons**:
     - The positive prompt MUST explicitly define the vehicle's authentic support structure (e.g. `twin horizontal parallel landing skids`, `flared base stabilizing fins`, `curved boat hull`).
     - The positive prompt MUST explicitly state `strictly NO wheels`.
     - The negative prompt MUST include `wheels, tires, car wheels, bicycle wheels, landing gear wheels, road`.

3. **Explicit Wheel Count for Wheeled Vehicles**:
   - For single-track/two-wheeled vehicles (`bicycle`, `motorcycle`, `scooter`): explicitly mandate `two clearly separated circular wheels`. Add `four wheels, car body` to the negative prompt.
   - For automobiles (`car`, `taxi`, `ambulance`, `fire_truck`, `police_car`, `bus`, `truck`): explicitly mandate `large chunky round wheels with clean hubcaps`.

4. **Zero Mechanical Clutter & Toddler Purity**:
   - Vehicles must have large, open, colorable panels.
   - Ban complex exposed engines, dangling wires, intricate sprockets, chain links, exhaust smoke clouds, and human drivers/passengers.
   - Keep all windows large, clean, and empty with pure white fill for toddler coloring.

## 3. Mandatory 11-Block Prompt Order for Vehicles
1. `[SUBJECT]` - 2D toddler coloring book line art of classic/cute [vehicle]
2. `[DOMAIN & ANATOMY]` - Authentic domain anatomy (e.g. rotary aircraft, spacecraft, watercraft, automobile)
3. `[SUPPORT / PROPULSION]` - Defining support structure (e.g. twin landing skids, 4 chunky wheels, hull)
4. `[ORIENTATION]` - Natural viewing angle (e.g. 3/4 side profile, side profile for cycles, upright for rockets)
5. `[SAFEGUARDS]` - Strict exclusion of incorrect components (e.g. strictly NO wheels for helicopters/rockets)
6. `[SIMPLIFICATION]` - Simplified preschool proportions, clean chunky panels, big colorable windows
7. `[LINE ART]` - Bold clean black vector outline, 5pt stroke, wide open coloring areas
8. `[COMPOSITION]` - Full vehicle silhouette, vertical 3:4 portrait, 25% white margin clearance
9. `[BACKGROUND]` - Pure white (#FFFFFF), zero ground/road lines, zero exhaust smoke, zero scenery
10. `[STRICT RESTRICTIONS]` - Strictly NO text, NO letters, NO words, NO color, NO human driver
11. `[NEGATIVE PROMPT]` - Domain-specific negatives + standard coloring negatives
