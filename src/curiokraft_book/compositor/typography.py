"""Programmatic vector typography compositor with dynamic preschool font autoscaling and letter spacing."""

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw
from pydantic import BaseModel

from curiokraft_book.compositor.fonts import get_typography_font
from curiokraft_book.constants import (
    TYPOGRAPHY_BASE_FONT_SIZE_PT,
    TYPOGRAPHY_LETTER_SPACING_PX,
    TYPOGRAPHY_STROKE_WIDTH_PX,
    TYPOGRAPHY_TOP_OFFSET_PX,
)


class TypographyCompositorResult(BaseModel):
    """Result of programmatic typography compositing."""

    success: bool
    output_path: str
    display_label: str
    text_bbox: tuple[int, int, int, int]
    font_size_pt: int
    horizontal_center_px: int
    vertical_top_px: int
    is_hollow_bubble: bool = True
    letter_spacing_px: int = 35


def measure_spaced_text(
    draw: ImageDraw.ImageDraw, text: str, font: Any, stroke_width: int, letter_spacing_px: int
) -> tuple[int, int]:
    """Calculate total bounding width and height of text with inter-character spacing."""
    total_w = 0
    max_h = 0
    chars = list(text)
    for i, char in enumerate(chars):
        if char == " ":
            total_w += int(letter_spacing_px * 2.5)
            continue
        c_bbox = draw.textbbox((0, 0), char, font=font, stroke_width=stroke_width)
        c_w = c_bbox[2] - c_bbox[0]
        c_h = c_bbox[3] - c_bbox[1]
        max_h = max(max_h, c_h)
        total_w += c_w
        if i < len(chars) - 1:
            total_w += letter_spacing_px
    return total_w, max_h


def composite_typography(
    image_input: str | Path | Image.Image,
    display_label: str,
    output_path: str | Path | None = None,
    base_font_size_pt: int = TYPOGRAPHY_BASE_FONT_SIZE_PT,
    top_offset_px: int = TYPOGRAPHY_TOP_OFFSET_PX,
    hollow_bubble_style: bool = True,
    stroke_width_px: int = TYPOGRAPHY_STROKE_WIDTH_PX,
    letter_spacing_px: int = TYPOGRAPHY_LETTER_SPACING_PX,
    custom_font_path: str | Path | None = None,
) -> TypographyCompositorResult:
    """Render uppercase bubbly vector typography onto the top of the master canvas.

    Features generous inter-character letter spacing (tracking) and dynamic autoscaling
    so each letter is distinct and easy for toddlers to color with crayons.

    Args:
        image_input: Path to the 300 DPI master image or an existing PIL Image.
        display_label: The exact uppercase word to render (e.g. "BANANA", "ELEPHANT").
        output_path: Destination path for the composite 300 DPI PNG master.
        base_font_size_pt: Base font size in points for standard words (default: 245 pt for 300 DPI).
        top_offset_px: Distance in pixels from top edge to text top (default: 240 px = 0.80 in).
        hollow_bubble_style: If True, draws hollow colorable letters with thick black stroke.
        stroke_width_px: Thickness of the black outline around hollow letters (default: 15 px).
        letter_spacing_px: Spacing between adjacent letterforms to prevent outline overlap (default: 40 px).
        custom_font_path: Optional explicit path to a TrueType font file.

    Returns:
        TypographyCompositorResult with positioning coordinates.
    """
    clean_label = display_label.upper().strip()

    # Load base canvas image
    if isinstance(image_input, (str, Path)):
        in_p = Path(image_input)
        if not in_p.exists():
            raise FileNotFoundError(f"Source image not found: {in_p}")
        img = Image.open(in_p).convert("L")
    elif isinstance(image_input, Image.Image):
        img = image_input.convert("L")
        in_p = Path("in_memory_image.png")
    else:
        raise TypeError("image_input must be a file path or PIL Image object.")

    canvas_width, canvas_height = img.size
    max_text_width = canvas_width - 350  # Enforce 0.58 in (175 px) left/right safety margins

    # 1. Intelligent Font Autoscaling based on word length
    char_len = len(clean_label)
    if char_len <= 5:
        target_font_size = int(base_font_size_pt * 1.08)  # ~265 pt (tall prominent bubble letters)
        spacing = int(letter_spacing_px * 1.15)  # ~46 px
    elif char_len <= 8:
        target_font_size = base_font_size_pt  # ~245 pt
        spacing = letter_spacing_px  # ~40 px
    elif char_len <= 11:
        target_font_size = int(base_font_size_pt * 0.82)  # ~200 pt
        spacing = int(letter_spacing_px * 0.75)  # ~30 px
    elif char_len <= 15:
        target_font_size = int(base_font_size_pt * 0.68)  # ~166 pt
        spacing = int(letter_spacing_px * 0.60)  # ~24 px
    else:
        target_font_size = int(base_font_size_pt * 0.55)  # ~135 pt
        spacing = int(letter_spacing_px * 0.50)  # ~20 px

    font = get_typography_font(font_size_pt=target_font_size, custom_font_path=custom_font_path)
    draw = ImageDraw.Draw(img)
    stroke = stroke_width_px if hollow_bubble_style else 0

    # 2. Measure spaced text width and downscale iteratively if needed
    text_width, text_height = measure_spaced_text(draw, clean_label, font, stroke, spacing)

    while text_width > max_text_width and target_font_size > 50:
        target_font_size -= 8
        spacing = max(10, int(spacing * 0.90))
        font = get_typography_font(font_size_pt=target_font_size, custom_font_path=custom_font_path)
        text_width, text_height = measure_spaced_text(draw, clean_label, font, stroke, spacing)

    # 3. Calculate horizontal center position
    pos_x = (canvas_width - text_width) // 2
    pos_y = top_offset_px

    # 4. Render Spaced Typography Character-by-Character
    curr_x = pos_x
    chars = list(clean_label)
    for i, char in enumerate(chars):
        if char == " ":
            curr_x += int(spacing * 2.5)
            continue

        c_bbox = draw.textbbox((0, 0), char, font=font, stroke_width=stroke)
        c_w = c_bbox[2] - c_bbox[0]

        if hollow_bubble_style:
            # Draw individual hollow bubble letter
            draw.text(
                (curr_x, pos_y),
                char,
                font=font,
                fill=255,  # White interior for toddler coloring
                stroke_width=stroke,
                stroke_fill=0,  # Bold Black outline
            )
        else:
            draw.text((curr_x, pos_y), char, fill=0, font=font)

        curr_x += c_w
        if i < len(chars) - 1:
            curr_x += spacing

    # 5. Snap antialiasing to pure binary black (0) and white (255)
    img = img.point(lambda p: 0 if p < 160 else 255, mode="L")

    # Determine output path
    if output_path:
        out_p = Path(output_path)
    elif isinstance(image_input, (str, Path)):
        out_p = Path(image_input).parent / f"{Path(image_input).stem}_titled.png"
    else:
        out_p = Path("output/composite_page.png")

    out_p.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_p, dpi=(300, 300), format="PNG")

    final_bbox = (pos_x, pos_y, pos_x + text_width, pos_y + text_height)

    return TypographyCompositorResult(
        success=True,
        output_path=str(out_p),
        display_label=clean_label,
        text_bbox=final_bbox,
        font_size_pt=target_font_size,
        horizontal_center_px=canvas_width // 2,
        vertical_top_px=pos_y,
        is_hollow_bubble=hollow_bubble_style,
        letter_spacing_px=spacing,
    )
