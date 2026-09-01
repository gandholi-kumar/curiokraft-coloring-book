# CurioKraft Raw Image Inbox — Quick Reference & Naming Guide

Drop your downloaded raw illustrations (`.png`, `.jpg`, `.jpeg`) into this folder (`inbox/raw_pages/`), or covers into `inbox/`.
Then run:
```powershell
curiokraft-book ingest
```
or
```powershell
curiokraft-book sample generate --pages P002,P004,P006 --source inbox
```

---

## 1. Naming Conventions for Special Spreads & Pages

The ingestion engine resolves images case-insensitively and supports `.png`, `.jpg`, and `.jpeg`.

| Page # | Page ID | Section / Purpose | Canonical Name | Recommended Filename | Supported Alternatives |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Page 1** | `P001` | **Front Matter** (Intro / "This Book Belongs To") | `welcome_belongs_to` | `raw_p001_welcome_belongs_to.png` | `raw_p001.png`, `p001.png`, `P001.png`, `welcome_belongs_to.png` |
| **Page 2** | `P002` | **A–M Educational Spread** (15-Tile Grid) | `alphabet_a_to_m` | `raw_p002_alphabet_a_to_m.png` | `raw_p002.png`, `p002.png`, `P002.png`, `alphabet_a_to_m.png` |
| **Page 3** | `P003` | **N–Z Educational Spread** (15-Tile Grid) | `alphabet_n_to_z` | `raw_p003_alphabet_n_to_z.png` | `raw_p003.png`, `p003.png`, `P003.png`, `alphabet_n_to_z.png` |
| **Page 4** | `P004` | **Numbers 0–5 Spread** (6-Tile Counting) | `numbers_0_to_5` | `raw_p004_numbers_0_to_5.png` | `raw_p004.png`, `p004.png`, `P004.png`, `numbers_0_to_5.png` |
| **Page 5** | `P005` | **Numbers 6–10 Spread** (6-Tile Counting) | `numbers_6_to_10` | `raw_p005_numbers_6_to_10.png` | `raw_p005.png`, `p005.png`, `P005.png`, `numbers_6_to_10.png` |
| **Pages 6–109** | `P006`–`P109` | **Single-Object Coloring Pages** | *(e.g. `banana`)* | `raw_p006_banana.png` | `raw_p006.png`, `p006.png`, `P006.png`, `banana.png` |
| **Page 110** | `P110` | **Back Matter** (Super Colorist Award) | `completion_certificate` | `raw_p110_completion_certificate.png` | `raw_p110.png`, `p110.png`, `P110.png`, `completion_certificate.png` |
| **Covers** | — | **Full-Wrap Paperback Cover** | `front_cover` / `back_cover` | `inbox/front_cover.png`<br>`inbox/back_cover.png` | `cover_front.png`, `cover_back.png` (or `.jpg`) |

> **Note on Pages 1 & 110:**
> Pages 1 and 110 are **rendered programmatically by default** with vector borders, text lines, badges, and mascot art. You only need to drop files for them if you want to override the default templates with custom illustrations.

---

## 2. Multi-Volume Production (e.g. Vol 2, Vol 3)

### Do you need to mention the object name (e.g. `banana.png`)?
**No, the object name in the filename is optional if you use the page number.**

The ingestion engine checks candidate filenames in this priority order:
1. `raw_p{NNN}_{object}.png` (e.g. `raw_p006_mango.png`)
2. `p{NNN}_{object}.png`
3. `raw_p{NNN}.png` (e.g. `raw_p006.png`) — **Object-name independent**
4. `p{NNN}.png` (e.g. `p006.png`) — **Object-name independent**
5. `P{NNN}.png` (e.g. `P006.png`) — **Object-name independent**
6. `{object}.png` (e.g. `mango.png` or `banana.png`)

### Why Page-Numbered Naming (`raw_p006.png` or `P006.png`) is Recommended for Future Volumes:
- **Decoupled from words:** In Vol 2, Page 6 might be `MANGO` or `ASTRONAUT`. Naming your file `raw_p006.png` automatically maps to Page 6 in the active `manifest/pages.json`.
- **Automatic Typography:** The compositor reads `display_label` from the manifest and overlays the correct hollow bubble typography at the top of the canvas.
- **Zero Typo Risk:** Eliminates accidental mismatches due to spelling mistakes in filenames.

### When Object Names ARE Required:
- If you use **bare filenames without page numbers** (e.g. `mango.png`), the file must match the `canonical_object` field in `manifest/pages.json` so the engine knows which page it belongs to.
