"""Programmatic compositor for special publication pages (Welcome/Ownership and Completion Certificate).

Design System: welcome-cert-page-crafting skill
- AI generates: mascot, badge, scenes, stars, sparkles, crayons (JPG/PNG assets in inbox/special_assets/)
- Python generates: ALL typography, borders, zones, layout, geometry, branding
- Same mascot appears on BOTH pages (generate once, reuse)
- COLOR . SAY . DISCOVER . PLAY is pixel-identical on both pages
- Narrative cascade: WELCOME, LITTLE EXPLORER -> YOU DID IT -> SUPER COLORIST
"""

import logging
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from curiokraft_book.compositor.contour_generator import draw_themed_card
from curiokraft_book.compositor.fonts import get_typography_font
from curiokraft_book.constants import (
    CANVAS_DPI,
    CANVAS_HEIGHT_PX,
    CANVAS_WIDTH_PX,
    DEFAULT_BOOK_TITLE,
    DEFAULT_BOOK_VOLUME,
    DEFAULT_FONTS_DIR,
    DEFAULT_INTERIOR_MASTERS_DIR,
    DEFAULT_MASCOT_DROP_PATH,
    DEFAULT_MASCOT_NAME,
    DEFAULT_MILESTONE_THEME,
    DEFAULT_SPECIAL_ASSETS_DIR,
    DEFAULT_WATERMARK_MIN_LUM,
    get_certificate_page_number,
)

logger = logging.getLogger("curiokraft.special_pages")

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


SPECIAL_ASSET_DIR = DEFAULT_SPECIAL_ASSETS_DIR
ASSET_NAMES = {
    "mascot": ["tiny_mascot.png", "tiny_mascot.jpg", "tiny_mascot.png.jpg"],
    "badge": ["super_colorist_badge.png", "super_colorist_badge.jpg"],
    "welcome": ["welcome_scene.png", "welcome_scene.jpg"],
    "celebration": ["celebration_scene.png", "celebration_scene.jpg"],
    "stars": ["stars.png", "stars.jpg"],
    "sparkles": ["sparkles.png", "sparkles.jpg"],
    "crayons": ["crayons.png", "crayons.jpg"],
    "watermark": ["aquatic_watermark.png", "aquatic_watermark.jpg"],
}


def archive_processed_special_assets(
    volume: str | None = None,
    dest_dir: Path | str | None = None,
    inbox_dir: Path | str | None = None,
) -> list[tuple[Path, Path]]:
    """Auto-move processed special assets from inbox drop locations into the
    corresponding volume folder in assets/special_assets/{volume}/.

    Returns a list of (source_path, destination_path) tuples for all moved assets.
    """
    import shutil

    vol = (volume or DEFAULT_BOOK_VOLUME).lower()

    target_dir = Path(dest_dir) if dest_dir else Path("assets/special_assets") / vol
    target_dir.mkdir(parents=True, exist_ok=True)

    search_dirs: list[Path] = []
    if inbox_dir:
        search_dirs.append(Path(inbox_dir))
    else:
        search_dirs.extend(
            [
                Path(f"inbox/special_assets/{vol}"),
                Path("inbox/special_assets"),
            ]
        )
        if DEFAULT_MASCOT_DROP_PATH:
            drop_p = Path(DEFAULT_MASCOT_DROP_PATH)
            if drop_p.exists() and "inbox" in drop_p.parts and drop_p.parent not in search_dirs:
                search_dirs.append(drop_p.parent)

    valid_extensions = {".png", ".jpg", ".jpeg", ".webp"}
    moved_assets: list[tuple[Path, Path]] = []
    seen_sources: set[Path] = set()

    for s_dir in search_dirs:
        if not s_dir.exists():
            continue
        for item in s_dir.iterdir():
            if not item.is_file():
                continue
            if item.name.startswith(".") or item.name.lower() in ("readme.md", ".gitkeep"):
                continue
            if item.suffix.lower() not in valid_extensions:
                continue
            if item.resolve() in seen_sources:
                continue

            dest_file = target_dir / item.name
            try:
                if dest_file.exists():
                    dest_file.unlink()
                shutil.move(str(item), str(dest_file))
                seen_sources.add(item.resolve())
                moved_assets.append((item, dest_file))
            except OSError:
                # File may be locked or permission denied; leave in place
                pass

        # Clean up empty volume subdirectory in inbox if empty
        if s_dir.name == vol and s_dir.exists():
            try:
                remaining = [f for f in s_dir.iterdir() if f.name not in (".gitkeep", "README.md")]
                if not remaining:
                    shutil.rmtree(str(s_dir), ignore_errors=True)
            except OSError:
                # Subdirectory cleanup is non-critical; leave intact if removal fails
                pass

    return moved_assets


def _find_asset(key: str, asset_dir: Path | str = SPECIAL_ASSET_DIR) -> Path | None:
    vol = DEFAULT_BOOK_VOLUME

    # Check for mascot: first check archived volume folder, then inbox drop path
    if key == "mascot" and DEFAULT_MASCOT_DROP_PATH:
        vol_mascot = Path(f"assets/special_assets/{vol}") / Path(DEFAULT_MASCOT_DROP_PATH).name
        if vol_mascot.exists():
            return vol_mascot
        if Path(DEFAULT_MASCOT_DROP_PATH).exists():
            return Path(DEFAULT_MASCOT_DROP_PATH)

    dirs_to_check = [
        Path(asset_dir),
        Path(f"assets/special_assets/{vol}"),
        Path("assets/special_assets/shared"),
        Path("assets/special_assets"),
        Path(f"inbox/special_assets/{vol}"),
        Path("inbox/special_assets"),
        DEFAULT_SPECIAL_ASSETS_DIR,
        Path(__file__).resolve().parent.parent.parent.parent / f"assets/special_assets/{vol}",
        Path(__file__).resolve().parent.parent.parent.parent / "assets/special_assets",
        Path(__file__).resolve().parent.parent.parent.parent / "inbox/special_assets",
    ]

    candidate_names = list(ASSET_NAMES.get(key, []))
    if key == "mascot":
        if DEFAULT_MASCOT_DROP_PATH:
            p_name = Path(DEFAULT_MASCOT_DROP_PATH).name
            if p_name not in candidate_names:
                candidate_names.insert(0, p_name)
        if DEFAULT_MASCOT_NAME:
            clean_m = DEFAULT_MASCOT_NAME.lower().replace(" ", "_")
            for ext in [".png", ".jpg", ".jpeg"]:
                m_fname = f"{clean_m}_mascot{ext}"
                if m_fname not in candidate_names:
                    candidate_names.append(m_fname)
                m_plain = f"{clean_m}{ext}"
                if m_plain not in candidate_names:
                    candidate_names.append(m_plain)

    for d in dirs_to_check:
        if not d.exists():
            continue
        for name in candidate_names:
            p = d / name
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


def _load_watermark_asset(asset_dir: Path | str = SPECIAL_ASSET_DIR) -> Image.Image | None:
    p = _find_asset("watermark", asset_dir)
    if not p or not p.exists():
        return None
    try:
        return Image.open(p).convert("L")
    except Exception as e:
        logger.warning(f"Could not load watermark from {p}: {e}")
        return None


def _load_volume_perimeter_frame(
    frame_path: str | Path | None = None,
    asset_dir: Path | str = SPECIAL_ASSET_DIR,
    canvas_size: tuple[int, int] = (CANVAS_WIDTH_PX, CANVAS_HEIGHT_PX),
) -> Image.Image | None:
    """Load and prepare thematic living perimeter frame asset for milestone pages."""
    vol = DEFAULT_BOOK_VOLUME.lower()
    p_candidates: list[Path] = []
    if frame_path and Path(frame_path).exists():
        p_candidates.append(Path(frame_path))

    cfg_frame_path = DEFAULT_MILESTONE_THEME.get("frame", {}).get("asset_path")
    if cfg_frame_path:
        p_candidates.append(Path(cfg_frame_path))

    p_candidates.extend(
        [
            Path(f"assets/special_assets/{vol}/{vol}_frame.png"),
            Path(f"assets/special_assets/{vol}/perimeter_frame.png"),
            Path(f"assets/special_assets/{vol}/aquatic_frame.png"),
            Path(f"inbox/special_assets/{vol}/{vol}_frame.png"),
            Path(f"inbox/special_assets/{vol}/aquatic_frame.png"),
            Path("assets/special_assets/perimeter_frame.png"),
            Path(asset_dir) / f"{vol}_frame.png",
            Path(asset_dir) / "aquatic_frame.png",
            Path(asset_dir) / "perimeter_frame.png",
        ]
    )

    resolved_path: Path | None = None
    for cand in p_candidates:
        if cand.is_file():
            resolved_path = cand
            break

    if not resolved_path:
        return None

    try:
        with Image.open(resolved_path) as raw:
            l_img = raw.convert("L")
            cw, ch = canvas_size
            if l_img.size != (cw, ch):
                l_img = l_img.resize((cw, ch), Image.Resampling.LANCZOS)
            arr = np.array(l_img)
            # Ensure pure white negative space in the interior (>235 -> 255)
            arr[arr > 235] = 255
            return Image.fromarray(arr, mode="L")
    except Exception as e:
        logger.warning(f"Failed to load perimeter frame from {resolved_path}: {e}")
        return None


def _load_contoured_mascot(mascot_path: Path | str) -> tuple[Image.Image, Image.Image] | None:
    p = Path(mascot_path)
    if not p.exists():
        return None
    try:
        import cv2

        bgr = cv2.imread(str(p))
        if bgr is None:
            return None
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mask = np.zeros_like(gray)
        cv2.drawContours(mask, contours, -1, 255, thickness=cv2.FILLED)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.dilate(mask, kernel, iterations=1)

        y_indices, x_indices = np.where(mask > 0)
        if len(y_indices) == 0:
            return None
        min_x, max_x = int(np.min(x_indices)), int(np.max(x_indices))
        min_y, max_y = int(np.min(y_indices)), int(np.max(y_indices))

        gray_cropped = gray[min_y : max_y + 1, min_x : max_x + 1]
        mask_cropped = mask[min_y : max_y + 1, min_x : max_x + 1]
        gray_clean = np.where(gray_cropped < 160, 0, 255).astype(np.uint8)

        return Image.fromarray(gray_clean, mode="L"), Image.fromarray(mask_cropped, mode="L")
    except Exception as e:
        logger.warning(f"Failed to contour mascot: {e}")
        return None


def _draw_border_welcome(draw, t: dict, is_aquatic: bool = False):
    cw, ch = t["canvas_w"], t["canvas_h"]
    oi, ii = t["border_outer_inset"], t["border_inner_inset"]
    r = t["border_radius"]
    draw.rounded_rectangle(
        [oi, oi, cw - oi, ch - oi], radius=r + 10, outline=0, width=t["border_outer_width"]
    )
    draw.rounded_rectangle(
        [ii, ii, cw - ii, ch - ii], radius=r, outline=0, width=t["border_inner_width"]
    )
    if not is_aquatic:
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


def _ingest_raw_full_page(
    raw_path: str | Path,
    canvas_w: int = CANVAS_WIDTH_PX,
    canvas_h: int = CANVAS_HEIGHT_PX,
    dpi: int = CANVAS_DPI,
) -> Image.Image:
    """Ingest a full-page illustration, fit to canvas preserving aspect ratio, and center on white."""
    raw_p = Path(raw_path)
    with Image.open(raw_p) as src:
        src_gray = src.convert("L")
        src_w, src_h = src_gray.size
        scale = min(canvas_w / src_w, canvas_h / src_h)
        new_w = int(round(src_w * scale))
        new_h = int(round(src_h * scale))
        resample_filter = getattr(Image, "Resampling", Image).LANCZOS
        resized = src_gray.resize((new_w, new_h), resample=resample_filter)

        canvas = Image.new("L", (canvas_w, canvas_h), 255)
        offset_x = (canvas_w - new_w) // 2
        offset_y = (canvas_h - new_h) // 2
        canvas.paste(resized, (offset_x, offset_y))
        return canvas


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
    watermark_image_path: str | Path | None = None,
    watermark_min_lum: float = DEFAULT_WATERMARK_MIN_LUM,
    frame_image_path: str | Path | None = None,
    contour_style: str | None = None,
    contour_params: dict | None = None,
    auto_archive: bool = False,
) -> Path:
    t = {**BOOK_THEME, "canvas_w": canvas_w, "canvas_h": canvas_h, "dpi": dpi}
    a_dir = Path(asset_dir)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    # Check for direct full-page Welcome artwork in inbox/raw_pages
    raw_candidates = [
        Path("inbox/raw_pages/raw_welcome.png"),
        Path("inbox/raw_pages/raw_p001.png"),
    ]
    inbox_raw = Path("inbox/raw_pages")
    if inbox_raw.exists():
        for p in inbox_raw.glob("raw_welcome*.png"):
            if p not in raw_candidates:
                raw_candidates.append(p)
        for p in inbox_raw.glob("raw_p001*.png"):
            if p not in raw_candidates:
                raw_candidates.append(p)

    raw_full = None
    for cand in raw_candidates:
        if cand.exists() and cand.is_file():
            raw_full = cand
            break

    if raw_full is not None:
        logger.info(f"Directly ingesting full-page Welcome illustration from {raw_full}")
        img = _ingest_raw_full_page(raw_full, canvas_w=canvas_w, canvas_h=canvas_h, dpi=dpi)
        img.save(out_p, dpi=(dpi, dpi))
        if auto_archive:
            archive_processed_special_assets()
        return out_p

    img = Image.new("L", (canvas_w, canvas_h), t["white"])
    draw = ImageDraw.Draw(img)

    vol = DEFAULT_BOOK_VOLUME.lower()
    is_aquatic = "aquatic" in vol or "ocean" in vol or "aquatic" in str(title).lower()

    m_theme = DEFAULT_MILESTONE_THEME or {}
    frame_cfg = m_theme.get("frame", {})
    cards_cfg = m_theme.get("cards", {})

    frame_enabled = bool(frame_cfg.get("enabled", True))
    card_style = contour_style or cards_cfg.get(
        "contour_style", "sinusoidal" if is_aquatic else "rounded"
    )
    card_params = contour_params or cards_cfg.get("contour_params", {})
    card_fill = tuple(cards_cfg.get("fill_color", [255, 255, 255, 245]))
    card_border = tuple(cards_cfg.get("border_color", [20, 24, 33, 255]))
    card_border_w = int(cards_cfg.get("border_width", 4))
    card_shadow = bool(cards_cfg.get("shadow", True))
    card_shadow_offset = tuple(cards_cfg.get("shadow_offset", [4, 5]))
    card_shadow_color = tuple(cards_cfg.get("shadow_color", [0, 0, 0, 35]))
    card_shadow_blur = int(cards_cfg.get("shadow_blur", 6))

    frame_img = None
    if frame_enabled:
        frame_img = _load_volume_perimeter_frame(
            frame_image_path, asset_dir=a_dir, canvas_size=(canvas_w, canvas_h)
        )

    if is_aquatic:
        if frame_img:
            # Composite living perimeter frame directly
            canvas_arr = np.array(img)
            canvas_arr = np.minimum(canvas_arr, np.array(frame_img))
            img = Image.fromarray(canvas_arr, mode="L")
            draw = ImageDraw.Draw(img)
        elif frame_cfg.get("fallback_to_border", True):
            # Fallback to double border only if requested
            _draw_border_welcome(draw, t, is_aquatic=True)

        # 1. Top Zone - Hero Headline
        f_hero = _font(120)
        _centered_text(draw, 280, "WELCOME,", f_hero, fill=0, canvas_w=canvas_w)
        _centered_text(draw, 415, "OCEAN EXPLORER!", f_hero, fill=0, canvas_w=canvas_w)

        # 2. Brand Zone
        f_brand = _font(t["size_brand"])
        _centered_text(draw, 535, title, f_brand, fill=t["dark_gray"], canvas_w=canvas_w)
        draw.line([(520, 595), (canvas_w - 520, 595)], fill=t["mid_gray"], width=3)

        # 3. Subheading Tagline
        f_tag = _font(t["size_tagline"])
        _centered_text(
            draw,
            620,
            "DISCOVER  •  COLOR  •  LEARN  •  PROTECT",
            f_tag,
            fill=t["dark_gray"],
            canvas_w=canvas_w,
        )

        # 4. Ownership Zone - Explorer Logbook Contoured Card
        f_own = _font(t["size_heading"])
        _centered_text(draw, 715, "THIS LOGBOOK BELONGS TO:", f_own, fill=0, canvas_w=canvas_w)
        box_l, box_r = 340, canvas_w - 340
        box_t, box_b = 765, 945

        img_rgb = img.convert("RGB")
        img_rgb = draw_themed_card(
            img_rgb,
            bbox=(box_l, box_t, box_r, box_b),
            style=card_style,
            params=card_params,
            fill_color=card_fill,
            border_color=card_border,
            border_width=card_border_w,
            shadow=card_shadow,
            shadow_offset=card_shadow_offset,
            shadow_color=card_shadow_color,
            shadow_blur=card_shadow_blur,
        )
        img = img_rgb.convert("L")
        draw = ImageDraw.Draw(img)

        f_field = _font(42)
        f_sub = _font(32)
        draw.text((box_l + 65, box_t + 40), "EXPLORER:", font=f_field, fill=0)
        draw.line([(box_l + 300, box_t + 75), (box_r - 65, box_t + 75)], fill=40, width=3)

        draw.text((box_l + 65, box_t + 110), "EXPEDITION DATE:", font=f_sub, fill=60)
        draw.line([(box_l + 360, box_t + 135), (box_r - 65, box_t + 135)], fill=120, width=2)

        # 5. Center Mascot - Sammy the Sea Turtle
        resolved_mascot = mascot_image_path or _find_asset("mascot", a_dir)
        if resolved_mascot:
            contoured = _load_contoured_mascot(resolved_mascot)
            if contoured:
                m_img, m_mask = contoured
                target_mh = 1350
                target_mw = int(m_img.width * (target_mh / m_img.height))
                m_resized = m_img.resize((target_mw, target_mh), Image.Resampling.LANCZOS)
                mask_resized = m_mask.resize((target_mw, target_mh), Image.Resampling.LANCZOS)
                mx = (canvas_w - target_mw) // 2
                my = 1010
                img.paste(m_resized, (mx, my), mask=mask_resized)

        # 6. Explorer Guide Tip Contoured Card
        # 6. Explorer Guide Tip Contoured Card
        tip_top = 2390
        tip_h = 320
        tip_l, tip_r = 340, canvas_w - 340

        img_rgb = img.convert("RGB")
        img_rgb = draw_themed_card(
            img_rgb,
            bbox=(tip_l, tip_top, tip_r, tip_top + tip_h),
            style=card_style,
            params=card_params,
            fill_color=card_fill,
            border_color=card_border,
            border_width=card_border_w,
            shadow=card_shadow,
            shadow_offset=card_shadow_offset,
            shadow_color=card_shadow_color,
            shadow_blur=card_shadow_blur,
        )
        img = img_rgb.convert("L")
        draw = ImageDraw.Draw(img)

        f_tip_h = _font(46)
        _centered_text(
            draw, tip_top + 45, "OCEAN EXPLORER GUIDE", f_tip_h, fill=0, canvas_w=canvas_w
        )
        _draw_star(draw, canvas_w // 2 - 320, tip_top + 45, 18, fill=0)
        _draw_star(draw, canvas_w // 2 + 320, tip_top + 45, 18, fill=0)

        f_tip_b = _font(35)
        _centered_text(
            draw,
            tip_top + 105,
            "• Explore 50 majestic ocean animals from shallow reefs to abyssal depths.",
            f_tip_b,
            fill=t["dark_gray"],
            canvas_w=canvas_w,
        )
        _centered_text(
            draw,
            tip_top + 152,
            "• Use crayons, colored pencils, or markers. Thick line art prevents bleed!",
            f_tip_b,
            fill=t["dark_gray"],
            canvas_w=canvas_w,
        )
        _centered_text(
            draw,
            tip_top + 199,
            "• Personalize each marine species with your own vibrant colors and patterns.",
            f_tip_b,
            fill=t["dark_gray"],
            canvas_w=canvas_w,
        )

        draw.line(
            [(tip_l + 60, tip_top + 245), (tip_r - 60, tip_top + 245)],
            fill=t["light_gray"],
            width=2,
        )
        _centered_text(
            draw,
            tip_top + 280,
            "AGES 4–10   •   CURIOKRAFT WILDLIFE DISCOVERY SERIES   •   VOLUME 1",
            _font(32),
            fill=t["mid_gray"],
            canvas_w=canvas_w,
        )
    else:
        # Original toddler welcome page
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
                img,
                right_wel,
                x=canvas_w - 220 - 560,
                y=interaction_top + 10,
                max_w=560,
                max_h=1480,
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
    if auto_archive:
        archive_processed_special_assets()
    return out_p


def render_certificate_page(
    output_path: str | Path | None = None,
    title: str = DEFAULT_BOOK_TITLE,
    font_dir: str | Path = DEFAULT_FONTS_DIR,
    asset_dir: str | Path = DEFAULT_SPECIAL_ASSETS_DIR,
    canvas_w: int = CANVAS_WIDTH_PX,
    canvas_h: int = CANVAS_HEIGHT_PX,
    dpi: int = CANVAS_DPI,
    show_guides: bool = False,
    award_image_path: str | Path | None = None,
    frame_image_path: str | Path | None = None,
    mascot_image_path: str | Path | None = None,
    contour_style: str | None = None,
    contour_params: dict | None = None,
    auto_archive: bool = False,
) -> Path:
    cert_num = get_certificate_page_number()
    t = {**BOOK_THEME, "canvas_w": canvas_w, "canvas_h": canvas_h, "dpi": dpi}
    a_dir = Path(asset_dir)
    out_p = (
        Path(output_path)
        if output_path is not None
        else DEFAULT_INTERIOR_MASTERS_DIR / f"page_{cert_num:03d}.png"
    )
    out_p.parent.mkdir(parents=True, exist_ok=True)

    # Check for direct full-page Certificate artwork in inbox/raw_pages
    raw_candidates = [
        Path("inbox/raw_pages/raw_certificate.png"),
        Path(f"inbox/raw_pages/raw_p{cert_num:03d}.png"),
    ]
    inbox_raw = Path("inbox/raw_pages")
    if inbox_raw.exists():
        for p in inbox_raw.glob("raw_certificate*.png"):
            if p not in raw_candidates:
                raw_candidates.append(p)
        for p in inbox_raw.glob(f"raw_p{cert_num:03d}*.png"):
            if p not in raw_candidates:
                raw_candidates.append(p)

    raw_full = None
    for cand in raw_candidates:
        if cand.exists() and cand.is_file():
            raw_full = cand
            break

    if raw_full is not None:
        logger.info(f"Directly ingesting full-page Certificate illustration from {raw_full}")
        img = _ingest_raw_full_page(raw_full, canvas_w=canvas_w, canvas_h=canvas_h, dpi=dpi)
        img.save(out_p, dpi=(dpi, dpi))

        # Single-sided mode: ensure page 110 is generated as blank bleed guard
        if cert_num == 109:
            blank_110 = out_p.parent / "page_110.png"
            blank_canvas = Image.new("L", (canvas_w, canvas_h), 255)
            blank_canvas.save(blank_110, dpi=(dpi, dpi))
            logger.info(f"Generated single-sided protective bleed guard at {blank_110}")

        if auto_archive:
            archive_processed_special_assets()
        return out_p

    img = Image.new("L", (canvas_w, canvas_h), t["white"])
    draw = ImageDraw.Draw(img)

    vol = DEFAULT_BOOK_VOLUME.lower()
    is_aquatic = "aquatic" in vol or "ocean" in vol or "aquatic" in str(title).lower()

    m_theme = DEFAULT_MILESTONE_THEME or {}
    frame_cfg = m_theme.get("frame", {})
    cards_cfg = m_theme.get("cards", {})

    frame_enabled = bool(frame_cfg.get("enabled", True))
    card_style = contour_style or cards_cfg.get(
        "contour_style", "sinusoidal" if is_aquatic else "rounded"
    )
    card_params = contour_params or cards_cfg.get("contour_params", {})
    card_fill = tuple(cards_cfg.get("fill_color", [255, 255, 255, 245]))
    card_border = tuple(cards_cfg.get("border_color", [20, 24, 33, 255]))
    card_border_w = int(cards_cfg.get("border_width", 4))
    card_shadow = bool(cards_cfg.get("shadow", True))
    card_shadow_offset = tuple(cards_cfg.get("shadow_offset", [4, 5]))
    card_shadow_color = tuple(cards_cfg.get("shadow_color", [0, 0, 0, 35]))
    card_shadow_blur = int(cards_cfg.get("shadow_blur", 6))

    frame_img = None
    if frame_enabled:
        frame_img = _load_volume_perimeter_frame(
            frame_image_path, asset_dir=a_dir, canvas_size=(canvas_w, canvas_h)
        )

    if is_aquatic:
        if frame_img:
            # Composite living perimeter frame directly
            canvas_arr = np.array(img)
            canvas_arr = np.minimum(canvas_arr, np.array(frame_img))
            img = Image.fromarray(canvas_arr, mode="L")
            draw = ImageDraw.Draw(img)
        elif frame_cfg.get("fallback_to_border", True):
            _draw_border_certificate(draw, t)

        # 1. Top Zone - Hero Headline
        f_hero = _font(115)
        _centered_text(draw, 270, "CONGRATULATIONS,", f_hero, fill=0, canvas_w=canvas_w)
        _centered_text(draw, 395, "OCEAN EXPLORER!", f_hero, fill=0, canvas_w=canvas_w)

        # 2. Main Award Banner
        f_award = _font(95)
        _centered_text(draw, 515, "MASTER OCEAN COLORIST", f_award, fill=0, canvas_w=canvas_w)
        _draw_star(draw, canvas_w // 2 - 430, 515, 20, fill=0)
        _draw_star(draw, canvas_w // 2 + 430, 515, 20, fill=0)

        f_cit = _font(36)
        _centered_text(
            draw,
            575,
            "OFFICIAL RECOGNITION OF UNDERWATER DISCOVERY & ARTISTIC MASTERY",
            f_cit,
            fill=t["dark_gray"],
            canvas_w=canvas_w,
        )
        draw.line([(480, 615), (canvas_w - 480, 615)], fill=t["mid_gray"], width=3)

        # 3. Recipient Contoured Wave Card
        box_l, box_r = 340, canvas_w - 340
        box_t, box_b = 665, 855

        img_rgb = img.convert("RGB")
        img_rgb = draw_themed_card(
            img_rgb,
            bbox=(box_l, box_t, box_r, box_b),
            style=card_style,
            params=card_params,
            fill_color=card_fill,
            border_color=card_border,
            border_width=card_border_w,
            shadow=card_shadow,
            shadow_offset=card_shadow_offset,
            shadow_color=card_shadow_color,
            shadow_blur=card_shadow_blur,
        )
        img = img_rgb.convert("L")
        draw = ImageDraw.Draw(img)

        f_field = _font(42)
        f_sub = _font(32)
        draw.text((box_l + 65, box_t + 40), "AWARDED TO:", font=f_field, fill=0)
        draw.line([(box_l + 340, box_t + 75), (box_r - 65, box_t + 75)], fill=40, width=3)

        draw.text((box_l + 65, box_t + 110), "EXPEDITION DATE:", font=f_sub, fill=60)
        draw.line([(box_l + 380, box_t + 135), (box_r - 65, box_t + 135)], fill=120, width=2)

        # 4. Center Mascot - Sammy the Sea Turtle
        resolved_mascot = mascot_image_path or _find_asset("mascot", a_dir)
        if resolved_mascot:
            contoured = _load_contoured_mascot(resolved_mascot)
            if contoured:
                m_img, m_mask = contoured
                target_mh = 1200
                target_mw = int(m_img.width * (target_mh / m_img.height))
                m_resized = m_img.resize((target_mw, target_mh), Image.Resampling.LANCZOS)
                mask_resized = m_mask.resize((target_mw, target_mh), Image.Resampling.LANCZOS)
                mx = (canvas_w - target_mw) // 2
                my = 920
                img.paste(m_resized, (mx, my), mask=mask_resized)

        # 5. Attestation & Signature Plaque Contoured Wave Card
        att_top = 2170
        att_h = 430
        att_l, att_r = 340, canvas_w - 340

        img_rgb = img.convert("RGB")
        img_rgb = draw_themed_card(
            img_rgb,
            bbox=(att_l, att_top, att_r, att_top + att_h),
            style=card_style,
            params=card_params,
            fill_color=card_fill,
            border_color=card_border,
            border_width=card_border_w,
            shadow=card_shadow,
            shadow_offset=card_shadow_offset,
            shadow_color=card_shadow_color,
            shadow_blur=card_shadow_blur,
        )
        img = img_rgb.convert("L")
        draw = ImageDraw.Draw(img)

        f_att_title = _font(44)
        _centered_text(
            draw,
            att_top + 45,
            "UNDERWATER EXPEDITION COMPLETED",
            f_att_title,
            fill=0,
            canvas_w=canvas_w,
        )
        _draw_star(draw, canvas_w // 2 - 380, att_top + 45, 18, fill=0)
        _draw_star(draw, canvas_w // 2 + 380, att_top + 45, 18, fill=0)

        _centered_text(
            draw,
            att_top + 100,
            "Having successfully explored, discovered, and brought to life",
            _font(36),
            fill=t["dark_gray"],
            canvas_w=canvas_w,
        )
        _centered_text(
            draw,
            att_top + 145,
            "50 magnificent ocean creatures from shallow sunlit reefs to the deep abyss!",
            _font(36),
            fill=0,
            canvas_w=canvas_w,
        )

        draw.line(
            [(att_l + 60, att_top + 195), (att_r - 60, att_top + 195)],
            fill=t["light_gray"],
            width=2,
        )

        # Integrated Signatures
        sig_y = att_top + 295
        f_sig = _font(36)
        draw.line([(att_l + 60, sig_y), (att_l + 700, sig_y)], fill=0, width=4)
        draw.text(
            (att_l + 380, sig_y + 36),
            "Expedition Naturalist",
            font=f_sig,
            fill=t["dark_gray"],
            anchor="mm",
        )
        draw.line([(att_r - 700, sig_y), (att_r - 60, sig_y)], fill=0, width=4)
        draw.text(
            (att_r - 380, sig_y + 36),
            "Master Colorist Signature",
            font=f_sig,
            fill=t["dark_gray"],
            anchor="mm",
        )

        draw.line(
            [(att_l + 60, att_top + 360), (att_r - 60, att_top + 360)],
            fill=t["light_gray"],
            width=2,
        )
        _centered_text(
            draw,
            att_top + 395,
            "CURIOKRAFT WILDLIFE DISCOVERY SERIES   •   OCEAN EXPEDITIONS VOL 1",
            _font(32),
            fill=t["mid_gray"],
            canvas_w=canvas_w,
        )
    else:
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
            draw,
            ach_y,
            f"for completing the {title} adventure!",
            _font(48),
            fill=0,
            canvas_w=canvas_w,
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

    # Single-sided mode: ensure page 110 is generated as blank bleed guard
    if cert_num == 109:
        blank_110 = out_p.parent / "page_110.png"
        blank_canvas = Image.new("L", (canvas_w, canvas_h), 255)
        blank_canvas.save(blank_110, dpi=(dpi, dpi))
        logger.info(f"Generated single-sided protective bleed guard at {blank_110}")

    if auto_archive:
        archive_processed_special_assets()
    return out_p
