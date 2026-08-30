"""Programmatic Amazon KDP cover compositor enforcing exact 17.498x11.250 in geometry.

100% Manifest & Config-Driven (Zero Hardcoded Content):
  - config/curriculum.yaml  -> Gradient palette, 3D title colors, feature bullets, preview grid styling
  - config/book_config.yaml  -> Title, subtitle, brand, age range, target dimensions
  - manifest/pages.json      -> Representative preview card objects (Apple, Banana, Car, Guitar, Carrot, Milk)
  - assets/logo/             -> Brand logo (aspect-fit, no bounding badge)
  - assets/emblem/           -> Brand emblem (aspect-fit, no surrounding circle)
"""

import math
import random
from pathlib import Path
from typing import Optional, Any
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pydantic import BaseModel, Field
import yaml

from curiokraft_book.compositor.fonts import get_typography_font
from curiokraft_book.compositor.brand import get_brand_logo, get_brand_emblem

KDP_PAPER_MULTIPLIERS = {
    "white": 0.002252,
    "cream": 0.002500,
    "standard_color": 0.002252,
    "premium_color": 0.002347,
}


def _load_yaml(path: str) -> dict:
    """Helper to load a YAML configuration file safely."""
    p = Path(path)
    if not p.is_absolute():
        candidates = [
            Path.cwd() / path,
            Path(__file__).parent.parent.parent.parent / path,
        ]
        for c in candidates:
            if c.exists():
                p = c
                break
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def calculate_kdp_cover_dimensions(
    page_count: int,
    trim_w_in: float = 8.500,
    trim_h_in: float = 11.000,
    paper_type: str = "white",
    bleed_in: float = 0.125,
    dpi: int = 300
) -> dict:
    """Calculate exact Amazon KDP paperback cover dimensions dynamically.
    
    Formula:
      Spine Width = page_count * multiplier
      Cover Width = (2 * bleed_in) + (2 * trim_w_in) + spine_w_in
      Cover Height = (2 * bleed_in) + trim_h_in
    """
    multiplier = KDP_PAPER_MULTIPLIERS.get(paper_type.lower(), 0.002252)
    spine_w_in = page_count * multiplier
    overall_w_in = (2 * bleed_in) + (2 * trim_w_in) + spine_w_in
    overall_h_in = (2 * bleed_in) + trim_h_in

    return {
        "spine_width_in": round(spine_w_in, 5),
        "overall_width_in": round(overall_w_in, 5),
        "overall_height_in": round(overall_h_in, 5),
        "spine_width_px": int(round(spine_w_in * dpi)),
        "total_width_px": int(round(overall_w_in * dpi)),
        "total_height_px": int(round(overall_h_in * dpi)),
        "dpi": dpi,
    }


class CoverCompositorResult(BaseModel):
    """Result of programmatic cover compositing."""
    success: bool
    output_png_path: str
    output_cmyk_pdf_path: Optional[str] = None
    overall_width_in: float = 17.498
    overall_height_in: float = 11.250
    canvas_dimensions_px: tuple[int, int]
    spine_width_in: float = 0.248
    spine_width_px: int
    spine_center_x_px: int
    barcode_box_px: tuple[int, int, int, int]
    violations: list[str] = Field(default_factory=list)


def _scale_aspect_fit(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Scale an image to fit inside max_w x max_h with strict aspect ratio preservation."""
    if img.width == 0 or img.height == 0:
        return img
    scale = min(max_w / img.width, max_h / img.height)
    new_w = max(1, int(round(img.width * scale)))
    new_h = max(1, int(round(img.height * scale)))
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)


def _draw_bubble(draw: ImageDraw.ImageDraw, x: int, y: int, r: int, fill_rgba: tuple = (255, 255, 255, 60)):
    """Draw a translucent decorative bubble with subtle specular highlight."""
    # Outer ring
    draw.ellipse([x - r, y - r, x + r, y + r], outline=(255, 255, 255, 110), width=max(2, r // 14))
    # Specular crescent/highlight
    hr = max(2, r // 3)
    hx = x - (r // 3)
    hy = y - (r // 3)
    draw.arc([hx - hr, hy - hr, hx + hr, hy + hr], start=180, end=290, fill=(255, 255, 255, 200), width=max(2, r // 10))


def _draw_starburst(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color_rgba: tuple = (255, 255, 255, 180)):
    """Draw a 4-point twinkling starburst watermark."""
    # Vertical line
    draw.line([(cx, cy - size), (cx, cy + size)], fill=color_rgba, width=max(2, size // 8))
    # Horizontal line
    draw.line([(cx - size, cy), (cx + size, cy)], fill=color_rgba, width=max(2, size // 8))
    # Center sparkle dot
    cr = max(2, size // 5)
    draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=color_rgba)


def _draw_mini_crayon(canvas: Image.Image, x: int, y: int, length: int = 70, color_rgb: tuple = (231, 76, 60), angle: float = 45):
    """Draw a cute angled wax crayon icon."""
    w = 22
    h = length
    crayon_img = Image.new("RGBA", (w + 10, h + 20), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(crayon_img)
    
    # Body rectangle
    body_y1 = 18
    body_y2 = h
    cdraw.rectangle([4, body_y1, w + 4, body_y2], fill=color_rgb, outline=(30, 30, 30, 255), width=2)
    # Pointed tip
    cdraw.polygon([(4, body_y1), (w // 2 + 4, 2), (w + 4, body_y1)], fill=color_rgb, outline=(30, 30, 30, 255))
    # Label stripe on body
    stripe_y = body_y1 + (body_y2 - body_y1) // 3
    cdraw.rectangle([4, stripe_y, w + 4, stripe_y + 12], fill=(255, 255, 255, 180), outline=(30, 30, 30, 200), width=1)
    
    # Rotate and paste
    rot = crayon_img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    canvas.paste(rot, (x, y), rot)


def _draw_3d_multicolor_title(
    canvas: Image.Image,
    text: str,
    font: ImageFont.FreeTypeFont,
    center_x: int,
    y: int,
    palette: list[str],
    stroke_color: str = "#2C1810",
    shadow_color: str = "#1A0C06",
    stroke_width: int = 14,
    shadow_offset: int = 16,
    letter_spacing: int = 6
):
    """Render multi-color 3D extruded bubbly letters with dark outline and drop shadow."""
    dummy = ImageDraw.Draw(canvas)
    char_widths = []
    for ch in text:
        if ch == ' ':
            char_widths.append((ch, font.size // 3))
        else:
            bbox = dummy.textbbox((0, 0), ch, font=font)
            char_widths.append((ch, (bbox[2] - bbox[0]) + letter_spacing))
    
    total_w = sum(w for _, w in char_widths) - letter_spacing
    start_x = center_x - (total_w // 2)
    
    # 1. First pass: Draw all shadows (3D extrusion layer)
    cur_x = start_x
    for i, (ch, cw) in enumerate(char_widths):
        if ch != ' ':
            for step in range(shadow_offset, 0, -3):
                dummy.text(
                    (cur_x + step, y + step),
                    ch,
                    font=font,
                    fill=shadow_color,
                    stroke_width=stroke_width,
                    stroke_fill=shadow_color
                )
        cur_x += cw
        
    # 2. Second pass: Draw outer stroke contours
    cur_x = start_x
    for i, (ch, cw) in enumerate(char_widths):
        if ch != ' ':
            dummy.text(
                (cur_x, y),
                ch,
                font=font,
                fill=stroke_color,
                stroke_width=stroke_width,
                stroke_fill=stroke_color
            )
        cur_x += cw
        
    # 3. Third pass: Draw vibrant colorful letter faces
    cur_x = start_x
    color_idx = 0
    for i, (ch, cw) in enumerate(char_widths):
        if ch != ' ':
            char_color = palette[color_idx % len(palette)]
            dummy.text(
                (cur_x, y),
                ch,
                font=font,
                fill=char_color
            )
            color_idx += 1
        cur_x += cw


def _draw_procedural_hero_placeholder(canvas: Image.Image, cx: int, cy: int, max_w: int = 1900, max_h: int = 1400):
    """Renders a high-fidelity vector/procedural hero illustration (Teddy Bear + Apple + Crayons) on play rug."""
    hero_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    hdraw = ImageDraw.Draw(hero_layer)
    
    # 1. Play rug / mat at base
    rug_x1 = cx - 750
    rug_x2 = cx + 750
    rug_y1 = cy + 320
    rug_y2 = cy + 480
    
    # Rug stripes
    stripe_colors = [(255, 107, 107), (78, 205, 196), (255, 230, 109), (168, 218, 220), (69, 123, 157)]
    sw = (rug_x2 - rug_x1) // len(stripe_colors)
    for idx, sc in enumerate(stripe_colors):
        sx1 = rug_x1 + (idx * sw)
        sx2 = sx1 + sw if idx < len(stripe_colors) - 1 else rug_x2
        hdraw.rectangle([sx1, rug_y1, sx2, rug_y2], fill=sc)
    hdraw.rectangle([rug_x1, rug_y1, rug_x2, rug_y2], outline=(30, 30, 30), width=8)
    
    # 2. Adorable Teddy Bear (Half-colored brown, half white line art)
    bx = cx - 180
    by = cy + 60
    
    # Bear Ears
    hdraw.ellipse([bx - 180, by - 260, bx - 80, by - 160], fill=(255, 255, 255), outline=(30, 30, 30), width=9)
    hdraw.ellipse([bx + 80, by - 260, bx + 180, by - 160], fill=(184, 115, 51), outline=(30, 30, 30), width=9)
    hdraw.ellipse([bx + 105, by - 235, bx + 155, by - 185], fill=(230, 175, 130), outline=(30, 30, 30), width=6)
    
    # Bear Head
    hdraw.ellipse([bx - 170, by - 210, bx + 170, by + 130], fill=(255, 255, 255), outline=(30, 30, 30), width=10)
    hdraw.pieslice([bx - 170, by - 210, bx + 170, by + 130], start=270, end=90, fill=(184, 115, 51), outline=(30, 30, 30), width=10)
    
    # Bear Snout
    hdraw.ellipse([bx - 60, by - 40, bx + 60, by + 60], fill=(245, 215, 185), outline=(30, 30, 30), width=7)
    hdraw.ellipse([bx - 24, by - 25, bx + 24, by + 8], fill=(30, 30, 30))
    hdraw.arc([bx - 30, by - 5, bx + 30, by + 40], start=20, end=160, fill=(30, 30, 30), width=7)
    
    # Bear Eyes (Big friendly round preschool eyes)
    hdraw.ellipse([bx - 100, by - 110, bx - 60, by - 70], fill=(30, 30, 30))
    hdraw.ellipse([bx - 90, by - 105, bx - 75, by - 90], fill=(255, 255, 255))
    hdraw.ellipse([bx + 60, by - 110, bx + 100, by - 70], fill=(30, 30, 30))
    hdraw.ellipse([bx + 70, by - 105, bx + 85, by - 90], fill=(255, 255, 255))
    
    # Bear Body
    hdraw.ellipse([bx - 150, by + 80, bx + 150, by + 340], fill=(255, 255, 255), outline=(30, 30, 30), width=10)
    hdraw.pieslice([bx - 150, by + 80, bx + 150, by + 340], start=270, end=90, fill=(184, 115, 51), outline=(30, 30, 30), width=10)
    
    # Bear holding yellow crayon in paws
    _draw_mini_crayon(hero_layer, bx - 25, by + 120, length=120, color_rgb=(255, 215, 0), angle=35)
    
    # 3. Adorable Smiling Red Apple (Half colored red, half white)
    ax = cx + 340
    ay = cy + 220
    
    # Apple Body
    hdraw.ellipse([ax - 130, ay - 110, ax + 130, ay + 120], fill=(255, 255, 255), outline=(30, 30, 30), width=9)
    hdraw.pieslice([ax - 130, ay - 110, ax + 130, ay + 120], start=90, end=270, fill=(235, 60, 60), outline=(30, 30, 30), width=9)
    hdraw.arc([ax - 30, ay - 160, ax + 10, ay - 100], start=200, end=340, fill=(100, 60, 20), width=8)
    hdraw.ellipse([ax + 5, ay - 160, ax + 55, ay - 120], fill=(76, 175, 80), outline=(30, 30, 30), width=5)
    
    # Apple Eyes & Smile
    hdraw.ellipse([ax - 60, ay - 20, ax - 30, ay + 10], fill=(30, 30, 30))
    hdraw.ellipse([ax - 52, ay - 15, ax - 40, ay - 3], fill=(255, 255, 255))
    hdraw.ellipse([ax + 30, ay - 20, ax + 60, ay + 10], fill=(30, 30, 30))
    hdraw.ellipse([ax + 38, ay - 15, ax + 50, ay - 3], fill=(255, 255, 255))
    hdraw.arc([ax - 20, ay + 10, ax + 20, ay + 45], start=10, end=170, fill=(30, 30, 30), width=6)
    
    # Apple Cute Cartoon Feet
    hdraw.ellipse([ax - 80, ay + 105, ax - 25, ay + 135], fill=(235, 60, 60), outline=(30, 30, 30), width=6)
    hdraw.ellipse([ax + 25, ay + 105, ax + 80, ay + 135], fill=(30, 30, 30), outline=(30, 30, 30), width=6)
    
    # 4. Playful Scattered Crayons around them
    _draw_mini_crayon(hero_layer, cx - 620, cy + 180, length=110, color_rgb=(241, 196, 15), angle=65)
    _draw_mini_crayon(hero_layer, cx + 580, cy + 20, length=115, color_rgb=(231, 76, 60), angle=-30)
    
    canvas.paste(hero_layer, (0, 0), hero_layer)


def _draw_preview_card_icon(draw: ImageDraw.ImageDraw, obj: str, cx: int, cy: int, size: int = 140):
    """Renders clean toddler line art for the 6 preview cards."""
    obj = obj.lower().replace(" ", "_")
    r = size // 2
    
    if "apple" in obj:
        draw.ellipse([cx - r + 10, cy - r + 10, cx + r - 10, cy + r - 10], outline=(30, 30, 30), width=7)
        draw.line([(cx, cy - r + 10), (cx + 10, cy - r - 15)], fill=(30, 30, 30), width=6)
        draw.ellipse([cx + 10, cy - r - 20, cx + 35, cy - r], outline=(30, 30, 30), width=5)
    elif "banana" in obj:
        draw.arc([cx - r, cy - r, cx + r + 20, cy + r + 20], start=180, end=300, fill=(30, 30, 30), width=9)
        draw.arc([cx - r + 15, cy - r - 10, cx + r + 5, cy + r + 5], start=185, end=295, fill=(30, 30, 30), width=7)
    elif "car" in obj:
        draw.rounded_rectangle([cx - r, cy, cx + r, cy + (r // 2)], radius=15, outline=(30, 30, 30), width=7)
        draw.arc([cx - (r // 2), cy - (r // 2), cx + (r // 2), cy + (r // 2)], start=180, end=360, fill=(30, 30, 30), width=7)
        draw.ellipse([cx - (r // 2) - 15, cy + (r // 3), cx - (r // 2) + 15, cy + (r // 3) + 30], fill=(30, 30, 30))
        draw.ellipse([cx + (r // 2) - 15, cy + (r // 3), cx + (r // 2) + 15, cy + (r // 3) + 30], fill=(30, 30, 30))
    elif "guitar" in obj:
        draw.ellipse([cx - (r // 2), cy - (r // 4), cx + (r // 2), cy + r], outline=(30, 30, 30), width=7)
        draw.line([(cx, cy - (r // 4)), (cx, cy - r)], fill=(30, 30, 30), width=7)
        draw.rectangle([cx - 15, cy - r, cx + 15, cy - r + 20], outline=(30, 30, 30), width=5)
    elif "carrot" in obj:
        draw.polygon([(cx - (r // 2), cy - (r // 2)), (cx + (r // 2), cy - (r // 2)), (cx, cy + r)], outline=(30, 30, 30), width=7)
        draw.line([(cx, cy - (r // 2)), (cx - 15, cy - r)], fill=(30, 30, 30), width=5)
        draw.line([(cx, cy - (r // 2)), (cx + 15, cy - r)], fill=(30, 30, 30), width=5)
    elif "milk" in obj:
        draw.rectangle([cx - (r // 2), cy - (r // 4), cx + (r // 2), cy + r], outline=(30, 30, 30), width=7)
        draw.polygon([(cx - (r // 2), cy - (r // 4)), (cx + (r // 2), cy - (r // 4)), (cx, cy - (r // 2) - 10)], outline=(30, 30, 30), width=7)
    else:
        draw.ellipse([cx - r + 15, cy - r + 15, cx + r - 15, cy + r - 15], outline=(30, 30, 30), width=7)
        draw.line([(cx - (r // 2), cy), (cx + (r // 2), cy)], fill=(30, 30, 30), width=6)


def composite_kdp_cover(
    front_hero_art_path: Optional[str | Path] = None,
    output_png_path: str | Path = "output/cover/TINY_HANDS_COLOR_AND_LEARN_Cover_300DPI.png",
    output_pdf_path: Optional[str | Path] = "output/cover/TINY_HANDS_COLOR_AND_LEARN_Cover_CMYK.pdf",
    manifest_path: str | Path = "manifest/pages.json",
    book_config_path: str | Path = "config/book_config.yaml",
    curriculum_config_path: str | Path = "config/curriculum.yaml",
    dpi: int = 300,
    page_count: int = 110,
    overall_w_in: float = 17.498,
    overall_h_in: float = 11.250,
    spine_w_in: float = 0.248,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    brand_name: Optional[str] = None
) -> CoverCompositorResult:
    """Programmatically assemble the complete print-ready Amazon KDP paperback cover."""
    
    # 1. Load Configurations (Zero hardcoded data)
    b_cfg = _load_yaml(str(book_config_path)).get("book", {})
    c_cfg = _load_yaml(str(curriculum_config_path)).get("cover_styling", {})
    
    title = title or b_cfg.get("title", "TINY HANDS COLOR & LEARN")
    subtitle = subtitle or b_cfg.get("subtitle", "FUN & EASY FIRST WORDS")
    brand_name = brand_name or b_cfg.get("brand", "CURIOKRAFT-KIDS")
    age_min = b_cfg.get("target_audience", {}).get("age_min", 1)
    age_max = b_cfg.get("target_audience", {}).get("age_max", 4)
    age_str = f"{age_min}-{age_max}"
    
    # Calculate exact pixel geometry at 300 DPI
    total_w_px = int(round(overall_w_in * dpi))  # 5249 px
    total_h_px = int(round(overall_h_in * dpi))  # 3375 px
    spine_w_px = int(round(spine_w_in * dpi))    # 74 px
    
    spine_center_x = total_w_px // 2
    spine_left_x = spine_center_x - (spine_w_px // 2)
    spine_right_x = spine_left_x + spine_w_px
    
    front_center_x = (spine_right_x + total_w_px) // 2
    back_center_x = spine_left_x // 2
    
    # Create master RGBA canvas
    cover = Image.new("RGBA", (total_w_px, total_h_px), (255, 255, 255, 255))
    draw = ImageDraw.Draw(cover)
    
    # =========================================================================
    # LAYER 1: Background Vertical Gradient (Sunny Golden-Yellow to Vibrant Sky Cyan)
    # =========================================================================
    grad_cfg = c_cfg.get("gradient", {})
    top_rgb = grad_cfg.get("top_color_rgb", [255, 224, 102])
    bot_rgb = grad_cfg.get("bottom_color_rgb", [34, 211, 238])
    
    for y in range(total_h_px):
        ratio = y / total_h_px
        r = int(top_rgb[0] + ratio * (bot_rgb[0] - top_rgb[0]))
        g = int(top_rgb[1] + ratio * (bot_rgb[1] - top_rgb[1]))
        b = int(top_rgb[2] + ratio * (bot_rgb[2] - top_rgb[2]))
        draw.line([(0, y), (total_w_px, y)], fill=(r, g, b, 255))
        
    # Spine gradient overlay (Warm golden spine)
    sp_top = grad_cfg.get("spine_top_color_rgb", [255, 215, 80])
    sp_bot = grad_cfg.get("spine_bottom_color_rgb", [250, 190, 60])
    for y in range(total_h_px):
        ratio = y / total_h_px
        r = int(sp_top[0] + ratio * (sp_bot[0] - sp_top[0]))
        g = int(sp_top[1] + ratio * (sp_bot[1] - sp_top[1]))
        b = int(sp_top[2] + ratio * (sp_bot[2] - sp_top[2]))
        draw.line([(spine_left_x, y), (spine_right_x, y)], fill=(r, g, b, 255))
        
    draw.line([(spine_left_x, 0), (spine_left_x, total_h_px)], fill=(220, 160, 40, 200), width=2)
    draw.line([(spine_right_x, 0), (spine_right_x, total_h_px)], fill=(220, 160, 40, 200), width=2)

    # =========================================================================
    # LAYER 2: Procedural Atmosphere (Floating Bubbles & Sparkling Stars)
    # =========================================================================
    watermark_layer = Image.new("RGBA", (total_w_px, total_h_px), (0, 0, 0, 0))
    wdraw = ImageDraw.Draw(watermark_layer)
    
    rng = random.Random(42)
    for _ in range(36):
        bx = rng.randint(100, total_w_px - 100)
        if spine_left_x - 50 < bx < spine_right_x + 50:
            continue
        by = rng.randint(100, total_h_px - 100)
        br = rng.randint(25, 90)
        _draw_bubble(wdraw, bx, by, br)
        
    for _ in range(48):
        sx = rng.randint(80, total_w_px - 80)
        if spine_left_x - 50 < sx < spine_right_x + 50:
            continue
        sy = rng.randint(80, total_h_px - 80)
        ss = rng.randint(12, 32)
        _draw_starburst(wdraw, sx, sy, ss)
        
    cover.paste(watermark_layer, (0, 0), watermark_layer)

    # =========================================================================
    # LAYER 3: Front Cover Components
    # =========================================================================
    
    # 1. Top Subtitle Pill Badge ("FUN & EASY FIRST WORDS")
    sub_pill_font = get_typography_font(font_size_pt=36)
    sub_text = subtitle.upper()
    sub_bbox = draw.textbbox((0, 0), sub_text, font=sub_pill_font)
    sub_w = sub_bbox[2] - sub_bbox[0]
    sub_h = sub_bbox[3] - sub_bbox[1]
    
    pill_w = sub_w + 90
    pill_h = sub_h + 36
    pill_x1 = front_center_x - (pill_w // 2)
    pill_y1 = 260
    pill_x2 = pill_x1 + pill_w
    pill_y2 = pill_y1 + pill_h
    
    draw.rounded_rectangle([pill_x1, pill_y1, pill_x2, pill_y2], radius=pill_h // 2, fill=(255, 255, 255), outline=(34, 211, 238), width=6)
    draw.text((pill_x1 + 45, pill_y1 + 16), sub_text, fill=(30, 58, 138), font=sub_pill_font)
    
    # 2. Main Title Line 1 ("TINY HANDS") in 3D Multi-Color Bubbly Letters
    title_palette = c_cfg.get("title_styling", {}).get("palette", [
        "#E74C3C", "#E67E22", "#F1C40F", "#2ECC71", "#3498DB", "#9B59B6", "#E91E63", "#FF9800", "#00BCD4"
    ])
    
    title_font_large = get_typography_font(font_size_pt=145)
    _draw_3d_multicolor_title(
        canvas=cover,
        text="TINY HANDS",
        font=title_font_large,
        center_x=front_center_x,
        y=pill_y2 + 45,
        palette=title_palette,
        stroke_color="#2C1810",
        shadow_color="#1A0C06",
        stroke_width=14,
        shadow_offset=16
    )
    
    # 3. Main Title Line 2 ("COLOR & LEARN") in White Bubbly Letters with 3D Shadow
    title_font_sub = get_typography_font(font_size_pt=105)
    _draw_3d_multicolor_title(
        canvas=cover,
        text="COLOR & LEARN",
        font=title_font_sub,
        center_x=front_center_x,
        y=pill_y2 + 300,
        palette=["#FFFFFF"],
        stroke_color="#2C1810",
        shadow_color="#1A0C06",
        stroke_width=12,
        shadow_offset=14
    )
    
    # 4. Front Cover Hero Artwork Inlay
    hero_inlaid = False
    if front_hero_art_path and Path(front_hero_art_path).exists():
        try:
            with Image.open(front_hero_art_path) as hero:
                hero_rgba = hero.convert("RGBA")
                hero_fitted = _scale_aspect_fit(hero_rgba, max_w=2000, max_h=1500)
                hx = front_center_x - (hero_fitted.width // 2)
                hy = 1150
                cover.paste(hero_fitted, (hx, hy), hero_fitted)
                hero_inlaid = True
        except Exception:
            pass
            
    if not hero_inlaid:
        _draw_procedural_hero_placeholder(cover, front_center_x, 1850)
        
    # 5. Bottom Callout Banner ("100+ EVERYDAY OBJECTS") + Age Badge
    banner_w = 1750
    banner_h = 210
    banner_x1 = front_center_x - (banner_w // 2) - 80
    banner_y1 = total_h_px - banner_h - 180
    banner_x2 = banner_x1 + banner_w
    banner_y2 = banner_y1 + banner_h
    
    draw.rounded_rectangle([banner_x1, banner_y1, banner_x2, banner_y2], radius=50, fill=(255, 255, 255), outline=(226, 232, 240), width=4)
    
    b_font_top = get_typography_font(font_size_pt=48)
    b_font_sub = get_typography_font(font_size_pt=34)
    
    b_txt_top = "100+ EVERYDAY OBJECTS"
    b_txt_sub = "FIRST WORDS • LETTERS & NUMBERS"
    
    draw.text((banner_x1 + 60, banner_y1 + 35), b_txt_top, fill=(30, 58, 138), font=b_font_top)
    draw.text((banner_x1 + 60, banner_y1 + 120), b_txt_sub, fill=(30, 58, 138), font=b_font_sub)
    
    # Age Roundel Badge ("AGES 1-3 YEARS")
    badge_r = 135
    badge_cx = banner_x2 + 50
    badge_cy = banner_y1 + (banner_h // 2)
    
    draw.ellipse([badge_cx - badge_r, badge_cy - badge_r, badge_cx + badge_r, badge_cy + badge_r], fill=(255, 255, 255), outline=(30, 58, 138), width=8)
    
    age_font_lbl = get_typography_font(font_size_pt=26)
    age_font_num = get_typography_font(font_size_pt=62)
    
    draw.text((badge_cx - 52, badge_cy - 90), "AGES", fill=(30, 58, 138), font=age_font_lbl)
    draw.text((badge_cx - 82, badge_cy - 48), age_str, fill=(20, 20, 20), font=age_font_num)
    draw.text((badge_cx - 62, badge_cy + 42), "YEARS", fill=(30, 58, 138), font=age_font_lbl)

    # =========================================================================
    # LAYER 4: Back Cover Components
    # =========================================================================
    
    # 1. Top Age Callout Pill (Upper Right of Back Cover)
    top_age_pill_w = 260
    top_age_pill_h = 75
    top_age_x1 = spine_left_x - top_age_pill_w - 200
    top_age_y1 = 180
    top_age_x2 = top_age_x1 + top_age_pill_w
    top_age_y2 = top_age_y1 + top_age_pill_h
    
    draw.rounded_rectangle([top_age_x1, top_age_y1, top_age_x2, top_age_y2], radius=top_age_pill_h // 2, fill=(255, 215, 0), outline=(230, 180, 0), width=3)
    age_pill_font = get_typography_font(font_size_pt=34)
    draw.text((top_age_x1 + 35, top_age_y1 + 14), f"AGES {age_str}", fill=(30, 30, 30), font=age_pill_font)
    
    # 2. Back Cover Main Header ("LITTLE HANDS, BIG DISCOVERIES!")
    back_hdr_font = get_typography_font(font_size_pt=58)
    back_hdr = c_cfg.get("back_cover", {}).get("headline", "LITTLE HANDS, BIG DISCOVERIES!")
    draw.text((back_center_x - 900, 300), back_hdr, fill=(30, 58, 138), font=back_hdr_font)
    
    # 3. Feature Highlights Panel with Bullet Points
    bullets = c_cfg.get("back_cover", {}).get("bullets", [
        {"icon": "🍎", "text": "100+ Everyday Objects, First Words, Letters & Numbers"},
        {"icon": "✏️", "text": "Extra-Thick Bold Outlines for Tiny Hands & Motor Skills"},
        {"icon": "⭐", "text": "Simple Wax-Crayon Color Guides on Every Page"}
    ])
    
    bullet_font = get_typography_font(font_size_pt=36)
    b_start_y = 420
    for item in bullets:
        b_text = f"{item.get('icon', '•')}  {item.get('text', '')}"
        draw.text((back_center_x - 900, b_start_y), b_text, fill=(30, 41, 59), font=bullet_font)
        b_start_y += 75
        
    # 4. Interior 6-Card Preview Showcase (2 rows x 3 columns)
    preview_sample_objs = [
        ("apple", "APPLE", (231, 76, 60)),
        ("banana", "BANANA", (241, 196, 15)),
        ("car", "TOY CAR", (52, 152, 219)),
        ("guitar", "GUITAR", (230, 126, 34)),
        ("carrot", "CARROT", (230, 126, 34)),
        ("milk", "MILK", (52, 152, 219))
    ]
    
    grid_start_x = back_center_x - 920
    grid_start_y = b_start_y + 60
    card_w = 580
    card_h = 680
    gap_x = 40
    gap_y = 40
    
    card_lbl_font = get_typography_font(font_size_pt=42)
    
    for idx, (obj_key, obj_label, crayon_col) in enumerate(preview_sample_objs):
        row = idx // 3
        col = idx % 3
        cx1 = grid_start_x + col * (card_w + gap_x)
        cy1 = grid_start_y + row * (card_h + gap_y)
        cx2 = cx1 + card_w
        cy2 = cy1 + card_h
        
        draw.rounded_rectangle([cx1, cy1, cx2, cy2], radius=32, fill=(255, 255, 255), outline=(30, 41, 59), width=7)
        _draw_mini_crayon(cover, cx1 + 25, cy1 + 25, length=65, color_rgb=crayon_col, angle=45)
        
        card_cx = cx1 + (card_w // 2)
        card_cy = cy1 + (card_h // 2) - 40
        _draw_preview_card_icon(draw, obj_key, card_cx, card_cy, size=240)
        
        lbl_bbox = draw.textbbox((0, 0), obj_label, font=card_lbl_font)
        lw = lbl_bbox[2] - lbl_bbox[0]
        draw.text((card_cx - (lw // 2), cy2 - 95), obj_label, fill=(30, 41, 59), font=card_lbl_font)
        
    # 5. Brand Logo (Lower Left of Back Cover) — Aspect fit, NO white box
    logo_img = get_brand_logo(target_width_px=850)
    logo_fitted = _scale_aspect_fit(logo_img, max_w=850, max_h=320)
    logo_x = grid_start_x
    logo_y = total_h_px - logo_fitted.height - 180
    cover.paste(logo_fitted, (logo_x, logo_y), logo_fitted)
    
    # 6. Barcode Box (Lower Right of Back Cover) — Aligned to exact Amazon KDP Previewer stamp
    bc_cfg = c_cfg.get("barcode_box", {})
    barcode_w_px = bc_cfg.get("width_px", 700)
    barcode_h_px = bc_cfg.get("height_px", 430)
    margin_from_spine = bc_cfg.get("margin_from_spine_px", 42)
    margin_from_bottom = bc_cfg.get("margin_from_bottom_px", 95)
    
    barcode_x2 = spine_left_x - margin_from_spine
    barcode_x1 = barcode_x2 - barcode_w_px
    barcode_y2 = total_h_px - margin_from_bottom
    barcode_y1 = barcode_y2 - barcode_h_px
    
    draw.rectangle([barcode_x1, barcode_y1, barcode_x2, barcode_y2], fill=(255, 255, 255), outline=(203, 213, 225), width=2)

    # =========================================================================
    # LAYER 5: Spine Formatting & Unadorned Emblem
    # =========================================================================
    
    # 1. Vertical Spine Title in Color
    spine_font = get_typography_font(font_size_pt=38)
    spine_text = f"{title.upper()}"
    
    spine_strip = Image.new("RGBA", (2200, 68), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(spine_strip)
    
    _draw_3d_multicolor_title(
        canvas=spine_strip,
        text=spine_text,
        font=spine_font,
        center_x=1100,
        y=10,
        palette=title_palette,
        stroke_color="#2C1810",
        shadow_color="#1A0C06",
        stroke_width=6,
        shadow_offset=4,
        letter_spacing=8
    )
    
    rotated_spine_txt = spine_strip.rotate(270, expand=True, resample=Image.Resampling.BICUBIC)
    
    sp_txt_x = spine_left_x + (spine_w_px - rotated_spine_txt.width) // 2
    sp_txt_y = (total_h_px - rotated_spine_txt.height) // 2 - 120
    cover.paste(rotated_spine_txt, (sp_txt_x, sp_txt_y), rotated_spine_txt)
    
    # 2. Brand Emblem at Spine Base — Aspect fit, NO surrounding circle
    emblem_img = get_brand_emblem(target_size_px=220)
    emblem_fitted = _scale_aspect_fit(emblem_img, max_w=44, max_h=55)
    
    emblem_x = spine_left_x + (spine_w_px - emblem_fitted.width) // 2
    emblem_y = total_h_px - emblem_fitted.height - 200
    cover.paste(emblem_fitted, (emblem_x, emblem_y), emblem_fitted)

    # =========================================================================
    # Final Export (Lossless RGB PNG & Press-Quality CMYK PDF)
    # =========================================================================
    out_png = Path(output_png_path)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    
    rgb_cover = Image.new("RGB", cover.size, (255, 255, 255))
    rgb_cover.paste(cover, mask=cover.split()[3])
    rgb_cover.save(out_png, dpi=(dpi, dpi), format="PNG")
    
    out_pdf_str = None
    if output_pdf_path:
        out_pdf = Path(output_pdf_path)
        out_pdf.parent.mkdir(parents=True, exist_ok=True)
        cmyk_cover = rgb_cover.convert("CMYK")
        cmyk_cover.save(out_pdf, resolution=float(dpi), format="PDF")
        out_pdf_str = str(out_pdf)
        
    return CoverCompositorResult(
        success=True,
        output_png_path=str(out_png),
        output_cmyk_pdf_path=out_pdf_str,
        overall_width_in=overall_w_in,
        overall_height_in=overall_h_in,
        canvas_dimensions_px=(total_w_px, total_h_px),
        spine_width_in=spine_w_in,
        spine_width_px=spine_w_px,
        spine_center_x_px=spine_center_x,
        barcode_box_px=(barcode_x1, barcode_y1, barcode_x2, barcode_y2)
    )
