"""Programmatic compositor for special publication pages (Welcome/Ownership and Completion Certificate).

Design System: welcome-cert-page-crafting skill
- AI generates: mascot, badge, scenes, stars, sparkles, crayons (JPG/PNG assets in inbox/special_assets/)
- Python generates: ALL typography, borders, zones, layout, geometry, branding
- Same mascot appears on BOTH pages (generate once, reuse)
- COLOR . SAY . DISCOVER . PLAY is pixel-identical on both pages
- Narrative cascade: WELCOME, LITTLE EXPLORER -> YOU DID IT -> SUPER COLORIST
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from curiokraft_book.compositor.fonts import get_typography_font
from curiokraft_book.constants import (
    CANVAS_DPI,
    CANVAS_HEIGHT_PX,
    CANVAS_WIDTH_PX,
    DEFAULT_BOOK_TITLE,
    DEFAULT_FONTS_DIR,
    DEFAULT_INTERIOR_MASTERS_DIR,
    DEFAULT_SPECIAL_ASSETS_DIR,
)

# ---------------------------------------------------------------------------
# BOOK THEME -- single source of truth for both pages
# ---------------------------------------------------------------------------
BOOK_THEME = {
    "canvas_w": CANVAS_WIDTH_PX,
    "canvas_h": CANVAS_HEIGHT_PX,
    "dpi": CANVAS_DPI,
    "safe_margin": 113,
    "bleed": 38,
    "border_outer_inset": 140,
    "border_inner_inset": 170,
    "border_outer_width": 12,
    "border_inner_width": 5,
    "border_radius": 30,
    "size_hero": 135,
    "size_award": 110,
    "size_brand": 78,
    "size_tagline": 56,
    "size_heading": 64,
    "size_body": 44,
    "size_small": 40,
    "black": 0,
    "dark_gray": 50,
    "mid_gray": 120,
    "light_gray": 215,
    "white": 255,
}


SPECIAL_ASSET_DIR = Path("inbox/special_assets")
ASSET_NAMES = {
    "mascot": ["tiny_mascot.png", "tiny_mascot.jpg", "tiny_mascot.png.jpg"],
    "badge": ["super_colorist_badge.png", "super_colorist_badge.jpg"],
    "welcome": ["welcome_scene.png", "welcome_scene.jpg"],
    "celebration": ["celebration_scene.png", "celebration_scene.jpg"],
    "stars": ["stars.png", "stars.jpg"],
    "sparkles": ["sparkles.png", "sparkles.jpg"],
    "crayons": ["crayons.png", "crayons.jpg"],
}


def _find_asset(key: str, asset_dir: Path = SPECIAL_ASSET_DIR) -> Path | None:
    for name in ASSET_NAMES.get(key, []):
        p = asset_dir / name
        if p.exists():
            return p
    return None


def _load_asset_grayscale(
    key: str, asset_dir: Path = SPECIAL_ASSET_DIR, crop: bool = True
) -> Image.Image | None:
    p = _find_asset(key, asset_dir)
    if p is None:
        return None
    try:
        with Image.open(p) as raw:
            rgba = raw.convert("RGBA")
            data = np.array(rgba)
            r, g, b, a = data[..., 0], data[..., 1], data[..., 2], data[..., 3]
            lum = (0.299 * r + 0.587 * g + 0.114 * b).astype(np.uint8)
            lum[a < 128] = 255
            # Checkerboard / background thresholding
            lum[lum > 140] = 255
            if crop:
                mask = lum < 140
                rows = np.any(mask, axis=1)
                cols = np.any(mask, axis=0)
                if np.any(rows) and np.any(cols):
                    rmin, rmax = np.where(rows)[0][[0, -1]]
                    cmin, cmax = np.where(cols)[0][[0, -1]]
                    pad = 12
                    rmin = max(0, rmin - pad)
                    rmax = min(lum.shape[0], rmax + pad)
                    cmin = max(0, cmin - pad)
                    cmax = min(lum.shape[1], cmax + pad)
                    lum = lum[rmin:rmax, cmin:cmax]
            return Image.fromarray(lum, mode="L")
    except Exception:
        return None


def _load_welcome_scene_halves(
    asset_dir: Path = SPECIAL_ASSET_DIR,
) -> tuple[Image.Image | None, Image.Image | None]:
    """Dynamically split welcome_scene into left and right clusters to surround the central mascot."""
    p = _find_asset("welcome", asset_dir)
    if p is None:
        return None, None
    try:
        with Image.open(p) as raw:
            rgba = raw.convert("RGBA")
            data = np.array(rgba)
            r, g, b, a = data[..., 0], data[..., 1], data[..., 2], data[..., 3]
            lum = (0.299 * r + 0.587 * g + 0.114 * b).astype(np.uint8)
            lum[a < 128] = 255
            lum[lum > 140] = 255

            w = lum.shape[1]
            mid_start = int(w * 0.30)
            mid_end = int(w * 0.70)
            col_dark_counts = (lum[:, mid_start:mid_end] < 140).sum(axis=0)
            best_split = mid_start + int(np.argmin(col_dark_counts))

            left_arr = lum[:, :best_split]
            right_arr = lum[:, best_split:]

            def crop_sub(arr):
                mask = arr < 140
                rows = np.any(mask, axis=1)
                cols = np.any(mask, axis=0)
                if np.any(rows) and np.any(cols):
                    rmin, rmax = np.where(rows)[0][[0, -1]]
                    cmin, cmax = np.where(cols)[0][[0, -1]]
                    pad = 12
                    rmin = max(0, rmin - pad)
                    rmax = min(arr.shape[0], rmax + pad)
                    cmin = max(0, cmin - pad)
                    cmax = min(arr.shape[1], cmax + pad)
                    return Image.fromarray(arr[rmin:rmax, cmin:cmax], mode="L")
                return None

            return crop_sub(left_arr), crop_sub(right_arr)
    except Exception:
        return None, None


def _paste_asset(
    canvas: Image.Image, asset_img: Image.Image, x: int, y: int, max_w: int, max_h: int
) -> tuple:
    scale = min(max_w / asset_img.width, max_h / asset_img.height, 1.0)
    new_w = max(1, int(asset_img.width * scale))
    new_h = max(1, int(asset_img.height * scale))
    resized = asset_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    px = x + (max_w - new_w) // 2
    py = y + (max_h - new_h) // 2
    canvas_crop = canvas.crop((px, py, px + new_w, py + new_h))
    blended = Image.fromarray(np.minimum(np.array(canvas_crop), np.array(resized)), mode="L")
    canvas.paste(blended, (px, py))
    return new_w, new_h


def _font(size: int):
    return get_typography_font(font_size_pt=size)


def _centered_text(
    draw,
    y: int,
    text: str,
    font,
    fill: int = 0,
    canvas_w: int = 2550,
    stroke_width: int = 0,
    stroke_fill: int = 255,
):
    draw.text(
        (canvas_w // 2, y),
        text,
        font=font,
        fill=fill,
        anchor="mm",
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )


def _draw_star(draw, cx: int, cy: int, r: int, fill: int = 0):
    ri = int(r * 0.42)
    pts = [
        (cx, cy - r),
        (cx + int(ri * 0.59), cy - int(ri * 0.81)),
        (cx + int(r * 0.95), cy - int(r * 0.31)),
        (cx + int(ri * 0.95), cy + int(ri * 0.31)),
        (cx + int(r * 0.59), cy + int(r * 0.81)),
        (cx, cy + ri),
        (cx - int(r * 0.59), cy + int(r * 0.81)),
        (cx - int(ri * 0.95), cy + int(ri * 0.31)),
        (cx - int(r * 0.95), cy - int(r * 0.31)),
        (cx - int(ri * 0.59), cy - int(ri * 0.81)),
    ]
    draw.polygon(pts, fill=fill)


def _draw_border_welcome(draw, t: dict):
    cw, ch = t["canvas_w"], t["canvas_h"]
    oi, ii = t["border_outer_inset"], t["border_inner_inset"]
    r = t["border_radius"]
    draw.rounded_rectangle(
        [oi, oi, cw - oi, ch - oi], radius=r + 10, outline=0, width=t["border_outer_width"]
    )
    draw.rounded_rectangle(
        [ii, ii, cw - ii, ch - ii], radius=r, outline=0, width=t["border_inner_width"]
    )
    _draw_star(draw, oi + 40, oi + 40, 26, fill=0)
    _draw_star(draw, cw - oi - 40, oi + 40, 26, fill=0)
    _draw_star(draw, oi + 40, ch - oi - 40, 26, fill=0)
    _draw_star(draw, cw - oi - 40, ch - oi - 40, 26, fill=0)


def _draw_border_certificate(draw, t: dict):
    cw, ch = t["canvas_w"], t["canvas_h"]
    oi, ii = t["border_outer_inset"], t["border_inner_inset"]
    r = t["border_radius"]
    draw.rounded_rectangle(
        [oi, oi, cw - oi, ch - oi], radius=r + 10, outline=0, width=t["border_outer_width"] + 4
    )
    draw.rounded_rectangle(
        [ii, ii, cw - ii, ch - ii], radius=r, outline=0, width=t["border_inner_width"]
    )
    draw.rounded_rectangle(
        [ii + 20, ii + 20, cw - ii - 20, ch - ii - 20], radius=r - 8, outline=0, width=3
    )
    for cx, cy in [
        (oi + 55, oi + 55),
        (cw - oi - 55, oi + 55),
        (oi + 55, ch - oi - 55),
        (cw - oi - 55, ch - oi - 55),
    ]:
        _draw_star(draw, cx, cy, 36, fill=0)
    _draw_star(draw, cw // 2, oi + 30, 20, fill=0)
    _draw_star(draw, cw // 2, ch - oi - 30, 20, fill=0)


def _draw_name_hero_box(draw, t: dict, top_y: int, box_h: int = 180, helper_text: str = "") -> int:
    cw = t["canvas_w"]
    box_l, box_r = 340, cw - 340
    box_t, box_b = top_y, top_y + box_h
    draw.rounded_rectangle(
        [box_l + 10, box_t + 10, box_r + 10, box_b + 10], radius=22, fill=t["light_gray"]
    )
    draw.rounded_rectangle(
        [box_l, box_t, box_r, box_b], radius=22, fill=t["white"], outline=0, width=8
    )
    if helper_text:
        f_help = _font(34)
        draw.text(
            (cw // 2, box_t + box_h // 2),
            helper_text,
            font=f_help,
            fill=t["light_gray"],
            anchor="mm",
        )
    return box_b


def _draw_debug_guides(draw, t: dict):
    cw, ch = t["canvas_w"], t["canvas_h"]
    b = t["bleed"]
    s = t["safe_margin"]
    draw.rectangle([b, b, cw - b, ch - b], outline=80, width=6)
    draw.rectangle([s, s, cw - s, ch - s], outline=140, width=4)


def render_welcome_page(
    output_path: str | Path = DEFAULT_INTERIOR_MASTERS_DIR / "page_001.png",
    title: str = DEFAULT_BOOK_TITLE,
    font_dir: str | Path = DEFAULT_FONTS_DIR,
    asset_dir: str | Path = DEFAULT_SPECIAL_ASSETS_DIR,
    canvas_w: int = CANVAS_WIDTH_PX,
    canvas_h: int = CANVAS_HEIGHT_PX,
    dpi: int = CANVAS_DPI,
    show_guides: bool = False,
    mascot_image_path: str | Path | None = None,
    award_image_path: str | Path | None = None,
) -> Path:
    t = {**BOOK_THEME, "canvas_w": canvas_w, "canvas_h": canvas_h, "dpi": dpi}
    a_dir = Path(asset_dir)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("L", (canvas_w, canvas_h), t["white"])
    draw = ImageDraw.Draw(img)

    _draw_border_welcome(draw, t)

    # 1. Top Zone - Hero Headline
    f_hero = _font(135)
    _centered_text(draw, 310, "WELCOME,", f_hero, fill=0, canvas_w=canvas_w)
    _centered_text(draw, 450, "LITTLE EXPLORER!", f_hero, fill=0, canvas_w=canvas_w)

    # 2. Brand Zone
    f_brand = _font(t["size_brand"])
    _centered_text(draw, 570, title, f_brand, fill=t["dark_gray"], canvas_w=canvas_w)
    draw.line([(520, 620), (canvas_w - 520, 620)], fill=t["mid_gray"], width=4)

    # 3. Subheading (Identical Mantra to Certificate)
    f_tag = _font(t["size_tagline"])
    _centered_text(
        draw,
        680,
        "COLOR  •  SAY  •  DISCOVER  •  PLAY",
        f_tag,
        fill=t["dark_gray"],
        canvas_w=canvas_w,
    )

    # 4. Ownership Zone
    f_own = _font(t["size_heading"])
    _centered_text(draw, 775, "THIS BOOK BELONGS TO:", f_own, fill=0, canvas_w=canvas_w)
    name_box_bottom = _draw_name_hero_box(draw, t, top_y=825, box_h=170)

    # 5. Interaction Zone - Centered Hero Mascot surrounded by balanced artifacts
    interaction_top = name_box_bottom + 45
    mascot = _load_asset_grayscale("mascot", a_dir)
    left_wel, right_wel = _load_welcome_scene_halves(a_dir)
    sparkles = _load_asset_grayscale("sparkles", a_dir)

    # Left Column: Balloons & Stars from welcome scene
    if left_wel:
        _paste_asset(img, left_wel, x=220, y=interaction_top + 10, max_w=560, max_h=1480)

    # Center: Hero Teddy Bear Mascot (heroic centered presence)
    if mascot:
        _paste_asset(
            img, mascot, x=(canvas_w - 980) // 2, y=interaction_top + 120, max_w=980, max_h=1260
        )

    # Right Column: Balloon, crayons, rainbow & stars from welcome scene
    if right_wel:
        _paste_asset(
            img, right_wel, x=canvas_w - 220 - 560, y=interaction_top + 10, max_w=560, max_h=1480
        )

    # Floating sparkle accents around Mascot's ears and waving paw
    if sparkles:
        _paste_asset(img, sparkles, x=740, y=interaction_top + 40, max_w=220, max_h=180)
        _paste_asset(img, sparkles, x=1600, y=interaction_top + 40, max_w=220, max_h=180)

    # 6. Parent Connection Zone - Framed Tip Card (enlarged for parent readability)
    tip_top = 2580
    tip_l, tip_r = 340, canvas_w - 340
    tip_h = 220
    tip_b = tip_top + tip_h
    draw.rounded_rectangle([tip_l, tip_top, tip_r, tip_b], radius=24, outline=0, width=4)
    draw.rounded_rectangle(
        [tip_l + 10, tip_top + 10, tip_r - 10, tip_b - 10],
        radius=18,
        outline=t["light_gray"],
        width=2,
    )

    f_tip_lbl = _font(54)
    _centered_text(draw, tip_top + 68, "GROWN-UP TIP", f_tip_lbl, fill=0, canvas_w=canvas_w)
    _draw_star(draw, canvas_w // 2 - 250, tip_top + 68, 18, fill=0)
    _draw_star(draw, canvas_w // 2 + 250, tip_top + 68, 18, fill=0)

    f_tip_body = _font(48)
    _centered_text(
        draw,
        tip_top + 150,
        "Color together, say the words aloud, and celebrate every little discovery!",
        f_tip_body,
        fill=t["dark_gray"],
        canvas_w=canvas_w,
    )

    # 7. Footer Zone (safe distance above inner border at 3130)
    f_foot = _font(40)
    _centered_text(
        draw,
        2980,
        "AGES 1–4   •   100+ FIRST WORDS, LETTERS & NUMBERS",
        f_foot,
        fill=t["dark_gray"],
        canvas_w=canvas_w,
    )
    _centered_text(
        draw,
        3038,
        "CURIOKRAFT-KIDS   •   EARLY LEARNING SERIES",
        _font(34),
        fill=t["mid_gray"],
        canvas_w=canvas_w,
    )

    if show_guides:
        _draw_debug_guides(draw, t)

    assert img.width == canvas_w, f"Width mismatch: {img.width} != {canvas_w}"
    assert img.height == canvas_h, f"Height mismatch: {img.height} != {canvas_h}"
    assert dpi >= 300, f"DPI {dpi} < 300 -- KDP minimum not met"

    img.save(out_p, dpi=(dpi, dpi))
    return out_p


def render_certificate_page(
    output_path: str | Path = DEFAULT_INTERIOR_MASTERS_DIR / "page_110.png",
    title: str = DEFAULT_BOOK_TITLE,
    font_dir: str | Path = DEFAULT_FONTS_DIR,
    asset_dir: str | Path = DEFAULT_SPECIAL_ASSETS_DIR,
    canvas_w: int = CANVAS_WIDTH_PX,
    canvas_h: int = CANVAS_HEIGHT_PX,
    dpi: int = CANVAS_DPI,
    show_guides: bool = False,
    award_image_path: str | Path | None = None,
) -> Path:
    t = {**BOOK_THEME, "canvas_w": canvas_w, "canvas_h": canvas_h, "dpi": dpi}
    a_dir = Path(asset_dir)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("L", (canvas_w, canvas_h), t["white"])
    draw = ImageDraw.Draw(img)

    _draw_border_certificate(draw, t)

    # 1. Top Zone - Hero Headline with flanking sparkles
    sparkles = _load_asset_grayscale("sparkles", a_dir)
    if sparkles:
        _paste_asset(img, sparkles, x=220, y=240, max_w=250, max_h=220)
        _paste_asset(img, sparkles, x=canvas_w - 470, y=240, max_w=250, max_h=220)

    f_hero = _font(135)
    _centered_text(draw, 305, "YOU DID IT,", f_hero, fill=0, canvas_w=canvas_w)
    _centered_text(draw, 445, "LITTLE EXPLORER!", f_hero, fill=0, canvas_w=canvas_w)

    # 2. Main Award Banner flanked by stars
    f_award = _font(105)
    _draw_star(draw, 380, 565, 24, fill=0)
    _draw_star(draw, canvas_w - 380, 565, 24, fill=0)
    _centered_text(draw, 565, "SUPER COLORIST", f_award, fill=0, canvas_w=canvas_w)
    draw.line([(420, 625), (canvas_w - 420, 625)], fill=0, width=6)

    # 3. Recipient Zone
    f_body = _font(46)
    _centered_text(
        draw,
        685,
        "This special certificate celebrates",
        f_body,
        fill=t["dark_gray"],
        canvas_w=canvas_w,
    )
    name_box_bottom = _draw_name_hero_box(draw, t, top_y=730, box_h=170)

    # 4. Achievement & Emotional Payoff Zone
    ach_y = name_box_bottom + 50
    _centered_text(
        draw, ach_y, f"for completing the {title} adventure!", _font(48), fill=0, canvas_w=canvas_w
    )
    _centered_text(
        draw,
        ach_y + 65,
        "You explored, colored, discovered, and played with",
        f_body,
        fill=t["dark_gray"],
        canvas_w=canvas_w,
    )
    _centered_text(
        draw,
        ach_y + 125,
        "100+ first words, letters, numbers, and everyday objects.",
        f_body,
        fill=t["dark_gray"],
        canvas_w=canvas_w,
    )

    emo_y = ach_y + 205
    f_emo = _font(42)
    _centered_text(
        draw,
        emo_y,
        "Every page was a little adventure.  •  Every color was your own.",
        f_emo,
        fill=t["dark_gray"],
        canvas_w=canvas_w,
    )
    _centered_text(
        draw,
        emo_y + 58,
        "Every discovery was something to celebrate!",
        f_emo,
        fill=0,
        canvas_w=canvas_w,
    )

    # 5. Central Hero Medal & Celebratory Assembly Zone (y=1400 to 2350)
    badge_y = emo_y + 140
    badge = _load_asset_grayscale("badge", a_dir)
    mascot = _load_asset_grayscale("mascot", a_dir)
    celebration = _load_asset_grayscale("celebration", a_dir)
    stars = _load_asset_grayscale("stars", a_dir)

    # Left: Celebration confetti & streamers
    if celebration:
        _paste_asset(img, celebration, x=220, y=badge_y + 20, max_w=500, max_h=760)

    # Center: SUPER COLORIST MEDAL (Dominant hero badge, ~860x860)
    if badge:
        _paste_asset(img, badge, x=(canvas_w - 860) // 2, y=badge_y - 30, max_w=860, max_h=860)

    # Right: Teddy Bear mascot cheering proudly
    if mascot:
        _paste_asset(img, mascot, x=canvas_w - 740, y=badge_y + 50, max_w=520, max_h=680)

    # 6. Subheading (Identical Mantra) with decorative stars
    tag_y = badge_y + 850
    f_tag = _font(t["size_tagline"])
    _draw_star(draw, 440, tag_y, 16, fill=t["mid_gray"])
    _draw_star(draw, canvas_w - 440, tag_y, 16, fill=t["mid_gray"])
    _centered_text(
        draw,
        tag_y,
        "COLOR  •  SAY  •  DISCOVER  •  PLAY",
        f_tag,
        fill=t["dark_gray"],
        canvas_w=canvas_w,
    )

    # Stars cluster accent above signatures
    if stars:
        _paste_asset(img, stars, x=(canvas_w - 380) // 2, y=tag_y + 45, max_w=380, max_h=160)

    # 7. Signature Zone (comfortably proportioned)
    sig_y = 2670
    f_sig = _font(38)
    draw.line([(340, sig_y), (1060, sig_y)], fill=0, width=5)
    draw.text((700, sig_y + 36), "Date", font=f_sig, fill=t["mid_gray"], anchor="mm")
    draw.line([(canvas_w - 1060, sig_y), (canvas_w - 340, sig_y)], fill=0, width=5)
    draw.text(
        (canvas_w - 700, sig_y + 36),
        "My Grown-Up's Signature",
        font=f_sig,
        fill=t["mid_gray"],
        anchor="mm",
    )

    # 8. Footer Zone (safe distance above inner border at 3130)
    f_foot = _font(40)
    _draw_star(draw, 340, 2980, 18, fill=t["dark_gray"])
    _draw_star(draw, canvas_w - 340, 2980, 18, fill=t["dark_gray"])
    _centered_text(
        draw,
        2980,
        "KEEP COLORING  •  KEEP EXPLORING  •  KEEP LEARNING!",
        f_foot,
        fill=t["dark_gray"],
        canvas_w=canvas_w,
    )
    _centered_text(
        draw,
        3038,
        "CURIOKRAFT-KIDS   •   EARLY LEARNING SERIES",
        _font(34),
        fill=t["mid_gray"],
        canvas_w=canvas_w,
    )

    if show_guides:
        _draw_debug_guides(draw, t)

    assert img.width == canvas_w, f"Width mismatch: {img.width} != {canvas_w}"
    assert img.height == canvas_h, f"Height mismatch: {img.height} != {canvas_h}"
    assert dpi >= 300, f"DPI {dpi} < 300 -- KDP minimum not met"

    img.save(out_p, dpi=(dpi, dpi))
    return out_p
