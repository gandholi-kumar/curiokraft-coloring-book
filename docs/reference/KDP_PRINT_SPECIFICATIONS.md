# Amazon KDP Official Paperback Specifications & Guidelines Reference

This document serves as the authoritative, mathematical reference for Amazon Kindle Direct Publishing (KDP) paperback manufacturing, cover dimensions, interior geometry, paper stock multipliers, spine safe areas, and barcode rules.

---

## 1. Official Amazon KDP Documentation Sources
- **Manuscript (Interior) Guidelines:** [https://kdp.amazon.com/en_US/help/topic/G202145060](https://kdp.amazon.com/en_US/help/topic/G202145060)
- **Cover Creation Guidelines:** [https://kdp.amazon.com/en_US/help/topic/G201953020](https://kdp.amazon.com/en_US/help/topic/G201953020)
- **Official Cover Calculator:** [https://kdp.amazon.com/en_US/cover-calculator](https://kdp.amazon.com/en_US/cover-calculator)

---

## 2. Official Cover Calculator Output (110 Pages, B&W, White Paper, 8.5 x 11.0 in)

The following table reflects the exact output from the Amazon KDP Cover Calculator:

| # | Description | Width (in) | Height (in) | Width (px @ 300 DPI) | Height (px @ 300 DPI) | Notes |
| :-: | :--- | :---: | :---: | :---: | :---: | :--- |
| **1** | **Full Cover** | **17.498 in** | **11.250 in** | **5249 px** | **3375 px** | Total canvas submitted to KDP |
| **2** | **Front / Back Cover** | 8.500 in | 11.000 in | 2550 px | 3300 px | Final trimmed visual page |
| **3** | **Safe Area** | 8.375 in | 10.750 in | 2512 px | 3225 px | 0.125 in margin inside trim line |
| **4** | **Bleed** | 0.125 in | 0.125 in | 38 px | 38 px | Required outer bleed on all 4 sides |
| **5** | **Margin** | 0.125 in | 0.125 in | 38 px | 38 px | Safe distance from mechanical trim cut |
| **6** | **Spine** | **0.248 in** | 11.000 in | **74 px** | 3300 px | 110 pages x 0.002252 in/page |
| **7** | **Spine Safe Area** | 0.123 in | 10.750 in | 37 px | 3225 px | Centered live text area on spine |
| **8** | **Spine Margin** | 0.062 in | 0.062 in | 19 px | 19 px | 0.0625 in margin on each spine edge |
| **9** | **Barcode Margin** | 0.250 in | 0.250 in | 75 px | 75 px | Clearance from spine and trim edges |

---

## 3. Paper Stock Caliper Multipliers

Amazon KDP calculates spine width dynamically based on paper stock caliper:

**Spine Width (in) = Page Count x Paper Multiplier**

| Paper & Ink Configuration | Multiplier (Inches / Page) | Multiplier (mm / Page) | Notes |
| :--- | :---: | :---: | :--- |
| **Black & White on White Paper** | **0.002252 in** | **0.0572 mm** | **CurioKraft Standard** |
| **Black & White on Cream Paper** | 0.002500 in | 0.0635 mm | Novels / Fiction standard |
| **Standard Color on White Paper** | 0.002252 in | 0.0572 mm | 50 lb / 74 gsm paper |
| **Premium Color on White Paper** | 0.002347 in | 0.0596 mm | 60 lb / 90 gsm paper |

---

## 4. Full Cover Dimensions Formula

Amazon KDP paperback covers are uploaded as a **single continuous wrap PDF**:

**Cover Width = Bleed (Left) + Back Cover Width + Spine Width + Front Cover Width + Bleed (Right)**

Cover Width = 0.125 in + 8.500 in + 0.24772 in + 8.500 in + 0.125 in = 17.49772 in ≈ **17.498 in** (5249 px @ 300 DPI)

**Cover Height = Bleed (Top) + Trim Height + Bleed (Bottom)**

Cover Height = 0.125 in + 11.000 in + 0.125 in = **11.250 in** (3375 px @ 300 DPI)

---

## 5. Critical Spine Text & Safe Area Rules

1. **Minimum Page Count for Spine Text:** KDP requires a minimum of **79 pages** to print text on the spine. With **110 pages**, our spine is 0.248 in (74 px), fully eligible for spine text.
2. **Spine Safe Margin:** All spine text and emblem graphics must maintain at least **0.0625 in (19 px)** clearance from both the left and right spine folds so ink does not bleed onto the front or back covers.
3. **Emblem Placement:** The brand emblem is placed at the base of the spine as an unadorned, crisp vector/transparent PNG scaled to fit cleanly within the 74 px width without artificial bounding circles.

---

## 6. Official Barcode Box Rules & Calibrated Master Standard (FROZEN)

> [!IMPORTANT]
> **PERMANENTLY FROZEN MASTER STANDARD (8.5 x 11 in, 110 Pages B&W Paperback):**
> The following exact dimensions and coordinates are **100% verified and frozen** against the Amazon KDP Print Previewer stamp. **DO NOT MODIFY** for 8.5 x 11 in 110-page white paper publications.
>
> 1. **Pure Clean White Box (Zero Lines, Zero Text):** Strictly NO barcode stripes (Amazon imprints automatically) and NO placeholder text.
> 2. **Exact Dimensions:** $700 \times 430\text{ px}$ ($2.333 \times 1.433\text{ in}$) @ 300 DPI.
> 3. **Exact Placement Coordinates:**
>    - **Horizontal ($X$):** `[1845, 2545] px` (Margin from spine fold $X=2587$: $42\text{ px} = 0.140\text{ in}$).
>    - **Vertical ($Y$):** `[2850, 3280] px` (Margin from bottom canvas edge $Y=3375$: $95\text{ px} = 0.317\text{ in}$).
>    - **Clearance from Red Trim Line ($Y=3337$):** $57\text{ px}$ ($0.190\text{ in}$) inside trim line $\rightarrow$ zero touching of the red cut line with balanced $30\text{ px}$ side padding and $15\text{ px}$ top padding around Amazon's barcode stamp.

---

## 7. Interior (Manuscript) Specifications (8.5 x 11.0 in, No Bleed, 110 Pages)

| Dimension / Metric | Amazon KDP Minimum | CurioKraft Master Standard |
| :--- | :--- | :--- |
| **Trim Size** | 8.500 x 11.000 in | 8.500 x 11.000 in (2550 x 3300 px at 300 DPI) |
| **Bleed Setting** | No Bleed | No Bleed |
| **Inside Gutter Margin** | >= 0.375 in (113 px) | **0.500 in ... 0.660 in (150 ... 200 px)** |
| **Outside Margins** | >= 0.250 in (75 px) | **0.500 in (150 px)** |
| **Top Margin** | >= 0.250 in (75 px) | **0.800 in (240 px)** (reserved for bubble typography) |
| **Bottom Margin** | >= 0.250 in (75 px) | **0.500 in (150 px)** |
| **Color Mode** | Pure Monochrome B&W | Binary #000000 / #FFFFFF (Zero Grayscale) |
| **File Format** | Single Flattened PDF | 110-Page Flattened PDF at 300 DPI |
