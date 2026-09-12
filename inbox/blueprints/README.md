# User Layout Blueprints Inbox

Drop your custom layout blueprints, wireframe mockups, or layout specs here!

## Supported Formats:
1. **Visual Images (`.png`, `.jpg`, `.jpeg`, `.webp`)**:
   - `back_cover_blueprint.png`: Wireframe sketch or visual layout for the back cover.
   - `front_cover_blueprint.png`: Wireframe sketch or visual layout for the front cover.
   - `cover_blueprint.png`: Full wraparound or general cover wireframe.
   - `page_blueprint.png`: Interior page layout blueprint.
2. **Structured Specs (`.yaml`, `.json`)**:
   - `back_cover_blueprint.yaml`
   - `cover_blueprint.yaml`

## How Agents Read Your Blueprint:
- `AGT-001-DIRECTOR`: Discovers any blueprint dropped in this folder.
- `AGT-002-DESIGN` & `AGT-009-VISIONQA`: Inspect the layout geometry (headline position, card rows/columns, callout pill grid, baseline wave height, and exclusion zones).
- `AGT-007-JUDGE`: Enforces your blueprint's layout slots during prompt synthesis, mapping active manifest content and copy into your custom design.

See `cover_blueprint_template.yaml` for an example of a structured blueprint specification.
