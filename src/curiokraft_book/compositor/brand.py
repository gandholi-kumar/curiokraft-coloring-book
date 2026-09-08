"""Protected brand asset manager for CurioKraft-Kids logo and emblem overlays."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from curiokraft_book.compositor.fonts import get_typography_font
from curiokraft_book.constants import (
    BACKGROUND_TRANSPARENCY_THRESHOLD,
    DEFAULT_EMBLEM_PATH,
    DEFAULT_IMPRINT,
    DEFAULT_LOGO_PATH,
    PUBLISHER_BADGE_HEIGHT,
    PUBLISHER_BADGE_WIDTH,
)


def make_background_transparent(
    img: Image.Image, threshold: int = BACKGROUND_TRANSPARENCY_THRESHOLD
) -> Image.Image:
    """Intelligently converts solid white/off-white background pixels to transparent alpha.

    Ensures that logos and emblems blend seamlessly over colored cover backgrounds.

    Args:
        img: Input PIL image.
        threshold: Brightness threshold above which pixels become transparent (0-255).

    Returns:
        RGBA Image with transparent background.
    """
    rgba = img.convert("RGBA")
    data = np.array(rgba)

    # Calculate mask of near-white background pixels (R > threshold, G > threshold, B > threshold)
    r, g, b = data[:, :, 0], data[:, :, 1], data[:, :, 2]
    white_mask = (r >= threshold) & (g >= threshold) & (b >= threshold)

    # Set alpha to 0 for background pixels
    data[:, :, 3][white_mask] = 0

    return Image.fromarray(data)


def get_brand_logo(
    logo_path: str | Path = DEFAULT_LOGO_PATH,
    target_width_px: int = 600,
    auto_remove_white_bg: bool = True,
    brand_text_fallback: str = DEFAULT_IMPRINT,
) -> Image.Image:
    """Load the protected CurioKraft company logo or generate an exact vector fallback.

    Guarantees that AI models never hallucinate or redraw the company branding.

    Args:
        logo_path: Path to the original logo file.
        target_width_px: Desired width in pixels for compositing.
        auto_remove_white_bg: Automatically make pure white backgrounds transparent.
        brand_text_fallback: Text to render if original image asset is not yet placed.

    Returns:
        PIL Image with RGBA transparency.
    """
    candidates = [
        Path(logo_path),
        Path("assets/logo/curiokraft_logo.PNG"),
        Path("assets/logo/curiokraft_logo.png"),
        Path("assets/logo/logo.png"),
        Path("assets/logo/logo.PNG"),
    ]
    path = None
    for c in candidates:
        if c.exists() and c.is_file():
            path = c
            break

    if path is not None:
        try:
            with Image.open(path) as img:
                img = img.convert("RGBA")
                # Crop to visible ink to eliminate empty padding
                bbox = img.getbbox()
                if bbox:
                    img = img.crop(bbox)
                orig_w, orig_h = img.size
                scale = target_width_px / orig_w
                new_h = max(1, int(round(orig_h * scale)))
                resized = img.resize((target_width_px, new_h), Image.Resampling.LANCZOS)

                # If image has a solid white background, make it transparent
                if auto_remove_white_bg:
                    resized = make_background_transparent(resized)

                return resized
        except Exception:
            pass

    # Clean typographic fallback badge
    font = get_typography_font(font_size_pt=48)
    badge_w = target_width_px
    badge_h = 100
    badge = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)

    # Draw rounded rectangle container
    draw.rounded_rectangle([0, 0, badge_w, badge_h], radius=15, fill=(30, 30, 30, 255))

    # Draw centered text
    bbox = draw.textbbox((0, 0), brand_text_fallback, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((badge_w - tw) // 2, (badge_h - th) // 2),
        brand_text_fallback,
        fill=(255, 255, 255, 255),
        font=font,
    )

    return badge


def create_publisher_badge(
    card_w: int = PUBLISHER_BADGE_WIDTH,
    card_h: int = PUBLISHER_BADGE_HEIGHT,
    radius: int = 28,
    offset_x: int = 16,
    offset_y: int = 20,
    blur_radius: int = 20,
    shadow_alpha: int = 95,
    logo_padding_h: int = 60,
    logo_padding_v: int = 50,
) -> tuple[Image.Image, int]:
    """Creates an authentic publisher badge card with a soft bottom/right drop shadow and CurioKraft logo.

    Guarantees:
    - Dedicated pure white rounded background (#FFFFFF) to eliminate color spill from cover background.
    - Soft, realistic multi-pass box shadow offset to bottom and right side.
    - CurioKraft brand logo scaled prominently while strictly preserving its original aspect ratio.

    Args:
        card_w: Width of the white card in pixels (default: 640 px for Option H5).
        card_h: Height of the white card in pixels (default: 420 px).
        radius: Corner radius of the rounded card.
        offset_x: Horizontal shadow offset (positive = right side).
        offset_y: Vertical shadow offset (positive = bottom side).
        blur_radius: Gaussian blur radius for shadow softness.
        shadow_alpha: Opacity of the shadow mask (0-255).
        logo_padding_h: Horizontal breathing margin inside card for logo.
        logo_padding_v: Vertical breathing margin inside card for logo.

    Returns:
        tuple[Image.Image, int]: (badge_patch_rgba, pad_px)
        To place the card at (x, y), paste badge_patch_rgba at (x - pad_px, y - pad_px).
    """
    from PIL import ImageFilter

    pad = max(offset_x, offset_y) + blur_radius * 2
    patch_w = card_w + pad * 2
    patch_h = card_h + pad * 2

    # 1. Generate bottom/right drop shadow
    shadow_mask = Image.new("L", (patch_w, patch_h), 0)
    s_draw = ImageDraw.Draw(shadow_mask)
    s_draw.rounded_rectangle(
        [pad + offset_x, pad + offset_y, pad + offset_x + card_w, pad + offset_y + card_h],
        radius=radius,
        fill=shadow_alpha,
    )
    blurred_shadow = shadow_mask.filter(ImageFilter.GaussianBlur(blur_radius))
    shadow_layer = Image.new("RGBA", (patch_w, patch_h), (0, 0, 0, 0))
    shadow_layer.putalpha(blurred_shadow)

    # 2. Generate pure white card with subtle protective border
    card_layer = Image.new("RGBA", (patch_w, patch_h), (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(card_layer)
    c_draw.rounded_rectangle(
        [pad, pad, pad + card_w, pad + card_h],
        radius=radius,
        fill=(255, 255, 255, 255),
        outline=(230, 233, 238, 255),
        width=2,
    )

    # 3. Load & tightly crop authentic CurioKraft brand logo
    max_logo_w = max(10, card_w - logo_padding_h)

    candidates = [
        Path("assets/logo/curiokraft_logo.PNG"),
        Path("assets/logo/curiokraft_logo.png"),
        Path("assets/logo/logo.png"),
        Path("assets/logo/logo.PNG"),
    ]
    logo_file = None
    for c in candidates:
        if c.exists() and c.is_file():
            logo_file = c
            break

    if logo_file is not None:
        try:
            with Image.open(logo_file) as l_img:
                l_img = l_img.convert("RGBA")
                bbox = l_img.getbbox()
                if bbox:
                    l_img = l_img.crop(bbox)

                cw, ch = l_img.size
                # Option H5 Lockup (Wide Card 640 x 420 px with 1.85x Uniform Subtitle):
                # - Bird & Book: natural aspect ratio (310 x 212 px)
                # - "CURIOKRAFT": prominent bold brand name (480 px wide)
                # - Line: 540 px wide divider line
                # - Subtitle: full 1.85x uniform scale on single line (540 x 22 px) with authentic Option 3 letter proportions
                bird = l_img.crop((0, 0, cw, 514))
                brand_text = l_img.crop((0, 546, cw, 625))
                line = l_img.crop((0, 643, cw, 649))
                subtitle = l_img.crop((0, 665, cw, 692))
                sub_ink = subtitle.crop(subtitle.getbbox())

                b_img = bird.resize((310, int(round(310 * 514 / cw))), Image.Resampling.LANCZOS)
                brand_img = brand_text.resize(
                    (480, int(round(480 * 79 / cw))), Image.Resampling.LANCZOS
                )
                line_img = line.resize((540, 4), Image.Resampling.LANCZOS)
                sub_img = sub_ink.resize((540, 22), Image.Resampling.LANCZOS)

                tot_h = (
                    b_img.height + 10 + brand_img.height + 6 + line_img.height + 8 + sub_img.height
                )
                cur_y = pad + (card_h - tot_h) // 2

                card_layer.paste(b_img, (pad + (card_w - b_img.width) // 2, cur_y), b_img)
                cur_y += b_img.height + 10
                card_layer.paste(
                    brand_img, (pad + (card_w - brand_img.width) // 2, cur_y), brand_img
                )
                cur_y += brand_img.height + 6
                card_layer.paste(line_img, (pad + (card_w - line_img.width) // 2, cur_y), line_img)
                cur_y += line_img.height + 8
                card_layer.paste(sub_img, (pad + (card_w - sub_img.width) // 2, cur_y), sub_img)
        except Exception:
            pass
    else:
        fallback = get_brand_logo(target_width_px=max_logo_w)
        lx = pad + (card_w - fallback.width) // 2
        ly = pad + (card_h - fallback.height) // 2
        card_layer.paste(fallback, (lx, ly), fallback)

    badge_patch = Image.alpha_composite(shadow_layer, card_layer)
    return badge_patch, pad


def get_brand_emblem(
    emblem_path: str | Path = DEFAULT_EMBLEM_PATH,
    target_size_px: int = 200,
    auto_remove_white_bg: bool = True,
) -> Image.Image:
    """Load the protected CurioKraft brand emblem or generate an exact vector fallback.

    Args:
        emblem_path: Path to the emblem asset.
        target_size_px: Desired bounding size in pixels.
        auto_remove_white_bg: Automatically make pure white backgrounds transparent.

    Returns:
        PIL Image with RGBA transparency.
    """
    candidates = [
        Path(emblem_path),
        Path("assets/emblem/curiokraft_emblem.png"),
        Path("assets/emblem/curiokraft_emblem.PNG"),
        Path("assets/emblem/emblem.png"),
    ]
    path = None
    for c in candidates:
        if c.exists() and c.is_file():
            path = c
            break

    if path is not None:
        try:
            with Image.open(path) as img:
                resized = img.convert("RGBA").resize(
                    (target_size_px, target_size_px), Image.Resampling.LANCZOS
                )
                if auto_remove_white_bg:
                    resized = make_background_transparent(resized)
                return resized
        except Exception:
            pass

    # Circular fallback emblem
    emblem = Image.new("RGBA", (target_size_px, target_size_px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(emblem)
    draw.ellipse(
        [5, 5, target_size_px - 5, target_size_px - 5],
        fill=(230, 126, 34, 255),
        outline=(255, 255, 255, 255),
        width=6,
    )

    font = get_typography_font(font_size_pt=60)
    draw.text(
        (target_size_px // 2 - 25, target_size_px // 2 - 38),
        "CK",
        fill=(255, 255, 255, 255),
        font=font,
    )
    return emblem
