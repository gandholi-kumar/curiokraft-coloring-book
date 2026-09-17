from pathlib import Path

from PIL import Image

from curiokraft_book.compositor.contour_generator import (
    ContourShapeGenerator,
    draw_themed_card,
)


def test_generate_sinusoidal_box():
    bbox = (50, 50, 450, 350)
    pts = ContourShapeGenerator.generate_sinusoidal_box(
        bbox, amplitude=8.0, frequency=0.05, step_px=5
    )
    assert len(pts) > 20
    # First point should be around top-left
    assert pts[0][0] == 50.0
    # Last point should be around left edge returning to start
    assert pts[-1][0] == 50.0 or pts[-1][1] == 50.0


def test_generate_sinusoidal_box_small_height():
    bbox = (20, 20, 200, 50)  # height < 60
    pts = ContourShapeGenerator.generate_sinusoidal_box(bbox, amplitude=4.0, frequency=0.02)
    assert len(pts) > 10


def test_generate_scalloped_box():
    bbox = (100, 100, 500, 400)
    pts = ContourShapeGenerator.generate_scalloped_box(bbox, scallop_radius=20.0, scallop_depth=8.0)
    assert len(pts) > 30
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    # Check boundaries
    assert min(xs) < 100.0 or min(ys) < 100.0
    assert max(xs) > 500.0 or max(ys) > 400.0


def test_generate_polygonal_box():
    bbox = (0, 0, 300, 200)
    pts = ContourShapeGenerator.generate_polygonal_box(bbox, chamfer=25.0)
    # Polygonal octagon with 8 vertices
    assert len(pts) == 8
    assert pts[0] == (25.0, 0.0)
    assert pts[1] == (275.0, 0.0)
    assert pts[2] == (300.0, 25.0)


def test_generate_rounded_box():
    bbox = (10, 10, 210, 110)
    pts = ContourShapeGenerator.generate_rounded_box(bbox, radius=15.0, step_deg=30)
    assert len(pts) > 10


def test_get_contour_points_aliases():
    bbox = (0, 0, 200, 200)
    # sinusoidal variants
    for style in ["sinusoidal", "wave", "waves", "sea", "ocean"]:
        pts = ContourShapeGenerator.get_contour_points(bbox, style=style, params={"amplitude": 5})
        assert len(pts) > 0

    # scalloped variants
    for style in ["scalloped", "mandala", "petal", "cloud", "scallop"]:
        pts = ContourShapeGenerator.get_contour_points(
            bbox, style=style, params={"scallop_radius": 15}
        )
        assert len(pts) > 0

    # polygonal variants
    for style in ["polygonal", "origami", "faceted", "chamfer"]:
        pts = ContourShapeGenerator.get_contour_points(bbox, style=style, params={"chamfer": 10})
        assert len(pts) == 8

    # rounded variants
    for style in ["rounded", "round"]:
        pts = ContourShapeGenerator.get_contour_points(bbox, style=style, params={"radius": 12})
        assert len(pts) > 0

    # fallback
    pts = ContourShapeGenerator.get_contour_points(bbox, style="unknown_style_fallback")
    assert len(pts) > 0


def test_draw_themed_card_rgb():
    img = Image.new("RGB", (600, 600), (240, 240, 240))
    res = draw_themed_card(
        img,
        bbox=(50, 50, 550, 550),
        style="sinusoidal",
        params={"amplitude": 6.0},
        fill_color=(255, 255, 255, 240),
        border_color=(10, 20, 30, 255),
        border_width=3,
        shadow=True,
    )
    assert res.size == (600, 600)
    assert res.mode == "RGB"


def test_draw_themed_card_rgba_no_shadow():
    img = Image.new("RGBA", (400, 400), (255, 255, 255, 255))
    res = draw_themed_card(
        img,
        bbox=(40, 40, 360, 360),
        style="polygonal",
        params={"chamfer": 20},
        shadow=False,
    )
    assert res.size == (400, 400)
    assert res.mode == "RGBA"


def test_draw_themed_card_asset_mode(tmp_path: Path):
    asset_file = tmp_path / "card_asset.png"
    asset_img = Image.new("RGBA", (100, 100), (200, 100, 50, 255))
    asset_img.save(asset_file)

    base = Image.new("RGB", (500, 500), (255, 255, 255))
    res = draw_themed_card(
        base,
        bbox=(50, 50, 350, 250),
        style="asset",
        asset_path=asset_file,
    )
    assert res.size == (500, 500)


def test_draw_themed_card_missing_asset_fallback():
    base = Image.new("RGB", (400, 400), (255, 255, 255))
    res = draw_themed_card(
        base,
        bbox=(50, 50, 350, 350),
        style="asset",
        asset_path="non_existent_asset_file.png",
    )
    assert res.size == (400, 400)
