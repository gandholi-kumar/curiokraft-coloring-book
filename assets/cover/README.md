# Cover Art Production Assets

Place the production-grade master front and back cover illustrations in this directory:

- ront_cover_master.png: Master high-resolution front cover artwork (8.5 x 11.0 in / 3:4 portrait, 300 DPI).
- ack_cover_master.png: Master high-resolution back cover artwork (8.5 x 11.0 in / 3:4 portrait, 300 DPI).

### Custom / New Edition Ingestion:
To test new cover artwork without overwriting these masters, drop your new PNG or JPG files into:
- inbox/front_cover.png (or inbox/front_cover.jpg)
- inbox/back_cover.png (or inbox/back_cover.jpg)

When you run curiokraft-book cover build, the engine automatically prioritizes inbox/ files and falls back to these master assets if inbox/ is empty.
