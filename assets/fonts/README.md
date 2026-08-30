# CurioKraft Fonts Directory & Typography Guide

Place TrueType (`.ttf`) or OpenType (`.otf`) font files in this directory for programmatic vector typography rendering on interior pages and covers.

---

## 1. Font Rankings for Ages 1–4 (Toddler Coloring Books)

| Rank | Font Family | Style / Aesthetic | Why It Works Best |
| :---: | :--- | :--- | :--- |
| 🥇 **#1** | **Fredoka / Fredoka-Bold** | **Ultra-chunky, bubbly, warm** | **Gold standard for toddlers:** Large open circular loops (`B`, `D`, `O`, `P`), soft circular terminals, and heavy bold stroke weight matching 5pt line-art. |
| 🥈 **#2** | **Nunito / Nunito-Bold** | Balanced, modern rounded sans | Clean, highly legible, modern preschool look. |
| 🥉 **#3** | **Quicksand-Bold** | Geometric rounded sans | Contemporary, minimalist, geometric clarity. |
| 🏅 **#4** | **Comic Relief** | Casual, cheerful comic-style | Playful, informal early learning activity style. |

---

## 2. Multiple Fonts Behavior & Intelligent Priority Resolution

If you drop multiple fonts into this folder (e.g. `Fredoka-Bold.ttf`, `Nunito-Bold.ttf`, `Quicksand-Bold.ttf`, and `ComicRelief.ttf`), the typography compositor automatically applies **Preschool Priority Ranking**:

```text
1. Fredoka       ──► Automatically Selected as #1 Active Font
2. Nunito        ──► Selected if Fredoka is absent
3. Quicksand     ──► Selected if 1 & 2 are absent
4. Comic Relief  ──► Selected if 1, 2, & 3 are absent
5. Other .ttf    ──► Fallback to any other custom font in folder
```

---

## 3. How to Check Which Font is Active

Run the diagnostic command in your terminal:
```powershell
curiokraft-book doctor
```

Output:
```text
Active Font: Fredoka-Bold.ttf (4 fonts installed) | FOUND | Selected via preschool priority ranking
```

---

## 4. Free & Safe Download Links (Google Fonts / SIL OFL)

All recommended fonts are open-source and free for commercial publishing:
- **Fredoka:** [Google Fonts - Fredoka](https://fonts.google.com/specimen/Fredoka)
- **Nunito:** [Google Fonts - Nunito](https://fonts.google.com/specimen/Nunito)
- **Quicksand:** [Google Fonts - Quicksand](https://fonts.google.com/specimen/Quicksand)
- **Comic Relief:** [SIL Open Font License](https://scripts.sil.org/OFL)

---

## 5. Commercial License Checklist

- Ensure any font placed in this directory carries a commercial use license (e.g., SIL Open Font License, Apache 2.0, or a commercial purchase receipt).
- The 18-point KDP Preflight diagnostic verifies that all embedded typography conforms to publishing licensing standards.
