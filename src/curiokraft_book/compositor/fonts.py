"""Font loader and manager for programmatic typography rendering with intelligent prioritization."""

from pathlib import Path
from typing import Optional
from PIL import ImageFont


# Preferred child-friendly font hierarchy for Toddler Coloring Books (Ages 1–4)
PREFERRED_FONT_ORDER = [
    "fredoka",       # #1 Best: Ultra-chunky, bubbly, warm rounded terminals
    "nunito",        # #2 Balanced, highly legible rounded sans
    "quicksand",     # #3 Geometric rounded sans
    "comic relief",  # #4 Cheerful casual font
    "comic",
    "arial rounded"
]


def get_typography_font(
    font_size_pt: int = 120,
    custom_font_path: Optional[str | Path] = None,
    preferred_font_name: Optional[str] = None,
    fonts_dir: str | Path = "assets/fonts"
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load the best available child-friendly TrueType font with intelligent preference ranking.
    
    If multiple font files exist in assets/fonts/, this loader automatically selects the optimal
    toddler font according to preschool typography benchmarks (Fredoka > Nunito > Quicksand > Comic Relief).
    
    Args:
        font_size_pt: Requested font size in points (scaled for 300 DPI canvas).
        custom_font_path: Explicit path to a .ttf/.otf font file.
        preferred_font_name: Optional font name keyword to prioritize (e.g. 'Nunito').
        fonts_dir: Directory containing project font assets.
        
    Returns:
        Loaded ImageFont instance.
    """
    # 1. Check explicit custom file path
    if custom_font_path and Path(custom_font_path).exists():
        try:
            return ImageFont.truetype(str(custom_font_path), size=font_size_pt)
        except Exception:
            pass

    # 2. Check assets/fonts/ directory
    f_dir = Path(fonts_dir)
    if f_dir.exists():
        font_files = list(f_dir.glob("*.ttf")) + list(f_dir.glob("*.otf"))
        if font_files:
            # If user explicitly requested a font family name
            if preferred_font_name:
                pref_clean = preferred_font_name.lower().strip()
                for f in font_files:
                    if pref_clean in f.stem.lower():
                        try:
                            return ImageFont.truetype(str(f), size=font_size_pt)
                        except Exception:
                            pass

            # Otherwise, sort available fonts according to PREFERRED_FONT_ORDER
            for pref in PREFERRED_FONT_ORDER:
                for f in font_files:
                    if pref in f.stem.lower():
                        try:
                            return ImageFont.truetype(str(f), size=font_size_pt)
                        except Exception:
                            pass

            # Fallback to the first font file present
            try:
                return ImageFont.truetype(str(font_files[0]), size=font_size_pt)
            except Exception:
                pass

    # 3. Check common Windows / Unix system fonts for rounded/friendly bold fonts
    system_font_candidates = [
        "C:\\Windows\\Fonts\\arialbd.ttf",      # Arial Bold
        "C:\\Windows\\Fonts\\segoeuib.ttf",     # Segoe UI Bold
        "C:\\Windows\\Fonts\\comicbd.ttf",      # Comic Sans Bold (child-friendly)
        "C:\\Windows\\Fonts\\trebucbd.ttf",     # Trebuchet Bold
        "C:\\Windows\\Fonts\\arial.ttf",        # Arial Regular
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc"
    ]

    for candidate in system_font_candidates:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size=font_size_pt)
            except Exception:
                continue

    # 4. Final fallback to PIL default font
    return ImageFont.load_default()
