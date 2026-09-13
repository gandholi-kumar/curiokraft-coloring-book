# CURIOKRAFT CHILDREN'S COLORING BOOK SYSTEM
## Authoritative Vehicle Design, Structural Anatomy, Propulsion Domains & Prompt Hierarchy Standard

---

### Executive Purpose
This document serves as the **single source of truth** for vehicle structural design, propulsion domains, support mechanics, viewing orientations, and prompt construction across all CurioKraft publication volumes (Volume 1, Volume 2, and future themed editions).

All internal debate agents (`AGT-001` through `AGT-008`), prompt engineering modules, and QA inspectors MUST strictly enforce this standard.

---

### 1. The Core Golden Rules of Vehicle Design

1. **Structure Governs Style**:
   Artistic styling, preschool simplification, and "cute" modifiers can **never** alter a vehicle's authentic propulsion or structural support mechanics. A rocket cannot have wheels simply because it is drawn in a preschool style.

2. **The Non-Wheeled Vehicle Rule**:
   Never allow an image diffusion model to infer wheels on vehicles that naturally operate in air, space, or water:
   - **Rockets / Spacecraft**: Stabilizer fins and propulsion nozzles; **strictly ZERO wheels**.
   - **Helicopters / Rotorcraft**: Overhead main rotor, tail rotor boom, and twin horizontal landing skids (runner rails); **strictly ZERO wheels**.
   - **Sailboats / Boats / Ships**: Watertight buoyant hull and sails/cabin; **strictly ZERO wheels**.
   - **Submarines**: Cylindrical submersible hull with conning tower and propeller; **strictly ZERO wheels**.
   - **Hot Air Balloons**: Buoyant teardrop envelope with suspended passenger basket; **strictly ZERO wheels**.

3. **Wheel Count Precision**:
   - For cycles (`bicycle`, `motorcycle`, `scooter`): always enforce **exactly two wheels** connected by a clean tubular frame.
   - For automobiles (`car`, `bus`, `truck`, `taxi`, `ambulance`, `fire_truck`, `police_car`): enforce **large chunky round wheels** with simple hubcaps.

4. **Zero Human Operators & Zero Environmental Clutter**:
   - All vehicles must be depicted standalone as clean physical objects with pure white (#FFFFFF) background.
   - Strictly **NO human drivers, pilots, riders, or passengers**.
   - Strictly **NO road lines, pavement, street scenery, clouds, or exhaust smoke plumes**.

---

### 2. Vehicle Structural Domain Matrix

| Domain Class | Canonical Objects | Defining Structural Elements | Support Mechanism | Anti-Hallucination Safeguards | Mandatory Negative Tokens |
|---|---|---|---|---|---|
| **Wheeled 4-Wheel (Automobiles & Heavy)** | `car`, `bus`, `truck`, `taxi`, `ambulance`, `fire_truck`, `police_car`, `tractor`, `wagon` | Aerodynamic or boxy cabin, windshield, large colorable windows, headlights, bumpers | Four chunky round rubber tires / wheels with clean circular hubcaps | Clear window panes, no tiny door handles or screws | `complex engine parts, tiny mechanical chains, exhaust smoke, road, street, human driver` |
| **Wheeled 2-Wheel (Cycles & Light)** | `bicycle`, `motorcycle`, `scooter`, `tricycle` | Sturdy tubular frame, front handlebars, seat, pedals/footrests | Exactly two clearly separated circular wheels (three for tricycle) | Keep frame clean and simple; no complex gear teeth or loose chains | `four wheels, car body, complex sprockets, tiny gear teeth, road, human rider` |
| **Rail Vehicles** | `train`, `locomotive`, `subway`, `tram` | Engine boiler or cabin, front cowcatcher, smokestack or roof pantograph, side windows | Multiple round steel train wheels aligned along straight baseline | Avoid dark exhaust soot or complicated drive rods | `rubber car tires, steering wheel, complex pistons, heavy dark smoke, road` |
| **Rotorcraft** | `helicopter` | Rounded cockpit bubble, large clear windshield, top main rotor with flat blades, tail boom with vertical rotor | Two horizontal parallel landing skids (runner rails) | Enforce twin runner skids; strictly prohibit wheels or airplane wings | `wheels, tires, car wheels, bicycle wheels, landing gear wheels, road, airplane wings, jet engines` |
| **Fixed-Wing Aircraft** | `airplane`, `plane`, `jet`, `biplane` | Streamlined cylindrical fuselage, two symmetric wide horizontal wings, vertical tail fin, cockpit windshield | Aerodynamic flight profile or clean minimal landing gear | Wings smoothly attached to fuselage; clear windows | `car wheels, bicycle wheels, road, complex mechanical engines, military weapons, passengers` |
| **Spacecraft** | `rocket`, `spaceship`, `space_shuttle` | Sleek cylindrical fuselage tapering upward to a smooth conical nose cone, circular observation porthole | 3 to 4 bold symmetrical stabilizing fins flared at bottom base + exhaust nozzle | Enforce base fins and nozzle; strictly prohibit wheels or landing gear | `wheels, tires, car wheels, bicycle wheels, road wheels, landing gear, road, tracks, ground, wings with propellers` |
| **Watercraft** | `sailboat`, `boat`, `tugboat`, `ship`, `yacht` | Buoyant curved boat hull, flat deck, central mast with triangular sails or steering cabin | Floating curved hull resting on clean waterline | Watertight hull; strictly prohibit wheels or road parts | `wheels, tires, car wheels, bicycle wheels, landing gear, road, pavement, tracks, legs` |
| **Submersibles** | `submarine` | Elongated cylindrical hull, top conning tower with periscope, circular portholes | Underwater diving planes and rear propulsion propeller | Streamlined hull; strictly prohibit wheels or landing tracks | `wheels, tires, car wheels, landing gear, legs, road` |
| **Lighter-than-Air** | `hot_air_balloon`, `blimp` | Teardrop-shaped fabric envelope with vertical stripe sections, suspension burner ropes | Woven passenger basket suspended neatly underneath | Symmetrical envelope; strictly prohibit wheels, wings, or engines | `wheels, tires, wings, propellers, road` |

---

### 3. Absolute Priority Hierarchy for Vehicle Prompts

```text
LEVEL 1: Vehicle Domain & Fundamental Structure (Automobile, Cycle, Rotorcraft, Spacecraft, Watercraft)
   ↓
LEVEL 2: Authentic Support / Propulsion Mechanics (Skids, fins/nozzles, hull, 2 wheels, 4 wheels)
   ↓
LEVEL 3: Defining Structural Elements (Rotors, sails, handlebars, cowcatcher, windows)
   ↓
LEVEL 4: Component Exclusion Safeguards (Strictly NO wheels for rockets/helicopters/boats)
   ↓
LEVEL 5: Perspective & Viewing Orientation (Three-quarter profile, side profile for cycles)
   ↓
LEVEL 6: Preschool Proportions & Clean Panels (Chunky body, big open colorable zones, clean windows)
   ↓
LEVEL 7: Line Art Physics (Bold clean 5pt black vector stroke, pure white #FFFFFF background)
   ↓
LEVEL 8: Composition & Margins (Centered subject, vertical 3:4 portrait, 25% empty white margins)
   ↓
LEVEL 9: Strict Prohibitions & Negatives (Zero text, zero shading, domain-specific negatives)
```
