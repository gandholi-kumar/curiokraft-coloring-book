"""Parametric geometry engine for milestone card borders and organic containers.

Provides universal mathematical contour generators (sinusoidal, scalloped, polygonal, rounded)
and asset-based container compositing with zero hardcoded genre dependencies.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter


class ContourShapeGenerator:
    """Parametric geometry generator for themed milestone cards and decorative frames."""

    @staticmethod
    def generate_sinusoidal_box(
        bbox: tuple[int, int, int, int],
        amplitude: float = 6.0,
        frequency: float = 0.04,
        step_px: int = 4,
    ) -> list[tuple[float, float]]:
        """Generate closed undulating wave polygon perimeter matching bbox (left, top, right, bottom).

        Rounds the frequency so waves complete an exact integer number of cycles across width,
        ensuring seamless corner junctions.
        """
        x1, y1, x2, y2 = bbox
        w = max(10, x2 - x1)
        h = max(10, y2 - y1)

        # Calculate integer number of full wave cycles to ensure corner closure (sin(0)=0 and sin(2*pi*k)=0)
        cycles_x = max(1, round(w * frequency / (2 * math.pi)))
        omega_x = (2 * math.pi * cycles_x) / w

        # Subtle vertical wave on sides if height is sufficient, else clean straight sides
        cycles_y = max(1, round(h * frequency / (2 * math.pi))) if h >= 60 else 0
        omega_y = (2 * math.pi * cycles_y) / h if cycles_y > 0 else 0

        points: list[tuple[float, float]] = []

        # 1. Top Edge: left to right
        for x in range(x1, x2 + 1, step_px):
            dx = x - x1
            y = y1 - amplitude * math.sin(omega_x * dx)
            points.append((float(x), float(y)))
        if points[-1][0] != float(x2):
            points.append((float(x2), float(y1)))

        # 2. Right Edge: top to bottom
        if cycles_y > 0:
            for y in range(y1, y2 + 1, step_px):
                dy = y - y1
                px = float(x2) + (amplitude * 0.6) * math.sin(omega_y * dy)
                points.append((float(px), float(y)))
        else:
            points.append((float(x2), float(y2)))

        # 3. Bottom Edge: right to left
        for x in range(x2, x1 - 1, -step_px):
            dx = x - x1
            y = y2 + amplitude * math.sin(omega_x * dx)
            points.append((float(x), float(y)))
        if points[-1][0] != float(x1):
            points.append((float(x1), float(y2)))

        # 4. Left Edge: bottom to top
        if cycles_y > 0:
            for y in range(y2, y1 - 1, -step_px):
                dy = y - y1
                px = float(x1) - (amplitude * 0.6) * math.sin(omega_y * dy)
                points.append((float(px), float(y)))
        else:
            points.append((float(x1), float(y1)))

        return points

    @staticmethod
    def generate_scalloped_box(
        bbox: tuple[int, int, int, int],
        scallop_radius: float = 14.0,
        scallop_depth: float = 6.0,
        step_deg: int = 15,
    ) -> list[tuple[float, float]]:
        """Generate scalloped petal / cloud puff contour with symmetrical circular segments."""
        x1, y1, x2, y2 = bbox
        w = max(10, x2 - x1)
        h = max(10, y2 - y1)

        num_scallops_x = max(2, round(w / (scallop_radius * 2)))
        span_x = w / num_scallops_x

        num_scallops_y = max(2, round(h / (scallop_radius * 2)))
        span_y = h / num_scallops_y

        points: list[tuple[float, float]] = []

        # Top Edge (scallops arching upward)
        for i in range(num_scallops_x):
            cx = x1 + (i + 0.5) * span_x
            r = span_x / 2.0
            for deg in range(180, 0, -step_deg):
                rad = math.radians(deg)
                px = cx - r * math.cos(rad)
                py = y1 - scallop_depth * math.sin(rad)
                points.append((float(px), float(py)))

        # Right Edge (scallops arching rightward)
        for i in range(num_scallops_y):
            cy = y1 + (i + 0.5) * span_y
            r = span_y / 2.0
            for deg in range(180, 0, -step_deg):
                rad = math.radians(deg)
                py = cy - r * math.cos(rad)
                px = x2 + scallop_depth * math.sin(rad)
                points.append((float(px), float(py)))

        # Bottom Edge (scallops arching downward)
        for i in range(num_scallops_x - 1, -1, -1):
            cx = x1 + (i + 0.5) * span_x
            r = span_x / 2.0
            for deg in range(0, 180, step_deg):
                rad = math.radians(deg)
                px = cx - r * math.cos(rad)
                py = y2 + scallop_depth * math.sin(rad)
                points.append((float(px), float(py)))

        # Left Edge (scallops arching leftward)
        for i in range(num_scallops_y - 1, -1, -1):
            cy = y1 + (i + 0.5) * span_y
            r = span_y / 2.0
            for deg in range(0, 180, step_deg):
                rad = math.radians(deg)
                py = cy - r * math.cos(rad)
                px = x1 - scallop_depth * math.sin(rad)
                points.append((float(px), float(py)))

        return points

    @staticmethod
    def generate_polygonal_box(
        bbox: tuple[int, int, int, int],
        chamfer: float = 16.0,
    ) -> list[tuple[float, float]]:
        """Generate origami-inspired faceted geometric polygon with beveled chamfer corners."""
        x1, y1, x2, y2 = bbox
        c = min(chamfer, (x2 - x1) / 3.0, (y2 - y1) / 3.0)

        return [
            (float(x1 + c), float(y1)),
            (float(x2 - c), float(y1)),
            (float(x2), float(y1 + c)),
            (float(x2), float(y2 - c)),
            (float(x2 - c), float(y2)),
            (float(x1 + c), float(y2)),
            (float(x1), float(y2 - c)),
            (float(x1), float(y1 + c)),
        ]

    @staticmethod
    def generate_rounded_box(
        bbox: tuple[int, int, int, int],
        radius: float = 20.0,
        step_deg: int = 15,
    ) -> list[tuple[float, float]]:
        """Generate modern rounded rectangle polygon."""
        x1, y1, x2, y2 = bbox
        r = min(radius, (x2 - x1) / 2.0, (y2 - y1) / 2.0)
        points: list[tuple[float, float]] = []

        # Top-right arc (270 to 360 deg)
        cx, cy = x2 - r, y1 + r
        for deg in range(270, 361, step_deg):
            rad = math.radians(deg)
            points.append((float(cx + r * math.cos(rad)), float(cy + r * math.sin(rad))))

        # Bottom-right arc (0 to 90 deg)
        cx, cy = x2 - r, y2 - r
        for deg in range(0, 91, step_deg):
            rad = math.radians(deg)
            points.append((float(cx + r * math.cos(rad)), float(cy + r * math.sin(rad))))

        # Bottom-left arc (90 to 180 deg)
        cx, cy = x1 + r, y2 - r
        for deg in range(90, 181, step_deg):
            rad = math.radians(deg)
            points.append((float(cx + r * math.cos(rad)), float(cy + r * math.sin(rad))))

        # Top-left arc (180 to 270 deg)
        cx, cy = x1 + r, y1 + r
        for deg in range(180, 271, step_deg):
            rad = math.radians(deg)
            points.append((float(cx + r * math.cos(rad)), float(cy + r * math.sin(rad))))

        return points

    @classmethod
    def get_contour_points(
        cls,
        bbox: tuple[int, int, int, int],
        style: str = "sinusoidal",
        params: dict[str, Any] | None = None,
    ) -> list[tuple[float, float]]:
        """Resolve points using requested contour geometry style and parameters."""
        p = params or {}
        st = style.lower().strip()

        if st in ["sinusoidal", "wave", "waves", "sea", "ocean"]:
            amp = float(p.get("amplitude", 6.0))
            freq = float(p.get("frequency", 0.04))
            return cls.generate_sinusoidal_box(bbox, amplitude=amp, frequency=freq)
        elif st in ["scalloped", "mandala", "petal", "cloud", "scallop"]:
            rad = float(p.get("scallop_radius", 14.0))
            depth = float(p.get("scallop_depth", 6.0))
            return cls.generate_scalloped_box(bbox, scallop_radius=rad, scallop_depth=depth)
        elif st in ["polygonal", "origami", "faceted", "chamfer"]:
            chamfer = float(p.get("chamfer", 16.0))
            return cls.generate_polygonal_box(bbox, chamfer=chamfer)
        elif st in ["rounded", "round"]:
            radius = float(p.get("radius", 20.0))
            return cls.generate_rounded_box(bbox, radius=radius)
        else:
            # Fallback to smooth rounded box
            return cls.generate_rounded_box(bbox, radius=float(p.get("radius", 18.0)))


def draw_themed_card(
    target_img: Image.Image,
    bbox: tuple[int, int, int, int],
    style: str = "sinusoidal",
    params: dict[str, Any] | None = None,
    fill_color: tuple[int, int, int, int] = (255, 255, 255, 240),
    border_color: tuple[int, int, int, int] = (20, 24, 33, 255),
    border_width: int = 4,
    shadow: bool = True,
    shadow_offset: tuple[int, int] = (4, 5),
    shadow_color: tuple[int, int, int, int] = (0, 0, 0, 35),
    shadow_blur: int = 6,
    asset_path: str | Path | None = None,
) -> Image.Image:
    """Draw an organic themed card contour onto target_img.

    Supports both Parametric Contours (sinusoidal, scalloped, polygonal, rounded)
    and Custom Artist Asset Mode (asset_path).
    """
    # 1. Custom Artist Asset Mode
    if asset_path and Path(asset_path).is_file():
        try:
            asset_img = Image.open(asset_path).convert("RGBA")
            card_w = bbox[2] - bbox[0]
            card_h = bbox[3] - bbox[1]
            resized_asset = asset_img.resize((card_w, card_h), Image.Resampling.LANCZOS)

            # Composite asset over target
            if target_img.mode != "RGBA":
                target_img = target_img.convert("RGBA")
            target_img.alpha_composite(resized_asset, dest=(bbox[0], bbox[1]))
            return target_img
        except Exception:
            # Fall through to parametric geometry if asset load fails
            pass

    # 2. Parametric Geometry Mode
    contour = ContourShapeGenerator.get_contour_points(bbox, style=style, params=params)

    # Convert target to RGBA for alpha blending
    orig_mode = target_img.mode
    base_rgba = target_img.convert("RGBA") if orig_mode != "RGBA" else target_img

    overlay = Image.new("RGBA", base_rgba.size, (255, 255, 255, 0))

    # Optional Drop Shadow
    if shadow:
        shadow_overlay = Image.new("RGBA", base_rgba.size, (255, 255, 255, 0))
        shadow_draw = ImageDraw.Draw(shadow_overlay)
        ox, oy = shadow_offset
        shadow_contour = [(x + ox, y + oy) for x, y in contour]
        shadow_draw.polygon(shadow_contour, fill=shadow_color)
        if shadow_blur > 0:
            shadow_overlay = shadow_overlay.filter(ImageFilter.GaussianBlur(shadow_blur))
        base_rgba = Image.alpha_composite(base_rgba, shadow_overlay)

    # Card Body Fill and Outline
    draw = ImageDraw.Draw(overlay)
    draw.polygon(contour, fill=fill_color, outline=border_color, width=border_width)

    # Merge card overlay
    out_img = Image.alpha_composite(base_rgba, overlay)

    return out_img if orig_mode == "RGBA" else out_img.convert(orig_mode)
