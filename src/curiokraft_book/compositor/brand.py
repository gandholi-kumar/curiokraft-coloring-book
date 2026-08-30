"""Protected brand asset manager for CurioKraft-Kids logo and emblem overlays."""

from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw
import numpy as np

from curiokraft_book.compositor.fonts import get_typography_font


def make_background_transparent(img: Image.Image, threshold: int = 245) -> Image.Image:
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
    r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]
    white_mask = (r >= threshold) & (g >= threshold) & (b >= threshold)
    
    # Set alpha to 0 for background pixels
    data[:, :, 3][white_mask] = 0
    
    return Image.fromarray(data)


def get_brand_logo(
    logo_path: str | Path = "assets/logo/curiokraft_logo.png",
    target_width_px: int = 600,
    auto_remove_white_bg: bool = True,
    brand_text_fallback: str = "CURIOKRAFT-KIDS"
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
    path = Path(logo_path)
    if path.exists():
        try:
            with Image.open(path) as img:
                orig_w, orig_h = img.size
                scale = target_width_px / orig_w
                new_h = max(1, int(round(orig_h * scale)))
                resized = img.convert("RGBA").resize((target_width_px, new_h), Image.Resampling.LANCZOS)
                
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
    draw.text(((badge_w - tw) // 2, (badge_h - th) // 2), brand_text_fallback, fill=(255, 255, 255, 255), font=font)
    
    return badge


def get_brand_emblem(
    emblem_path: str | Path = "assets/emblem/curiokraft_emblem.png",
    target_size_px: int = 200,
    auto_remove_white_bg: bool = True
) -> Image.Image:
    """Load the protected CurioKraft brand emblem or generate an exact vector fallback.
    
    Args:
        emblem_path: Path to the emblem asset.
        target_size_px: Desired bounding size in pixels.
        auto_remove_white_bg: Automatically make pure white backgrounds transparent.
        
    Returns:
        PIL Image with RGBA transparency.
    """
    path = Path(emblem_path)
    if path.exists():
        try:
            with Image.open(path) as img:
                resized = img.convert("RGBA").resize((target_size_px, target_size_px), Image.Resampling.LANCZOS)
                if auto_remove_white_bg:
                    resized = make_background_transparent(resized)
                return resized
        except Exception:
            pass

    # Circular fallback emblem
    emblem = Image.new("RGBA", (target_size_px, target_size_px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(emblem)
    draw.ellipse([5, 5, target_size_px - 5, target_size_px - 5], fill=(230, 126, 34, 255), outline=(255, 255, 255, 255), width=6)
    
    font = get_typography_font(font_size_pt=60)
    draw.text((target_size_px // 2 - 25, target_size_px // 2 - 38), "CK", fill=(255, 255, 255, 255), font=font)
    return emblem
