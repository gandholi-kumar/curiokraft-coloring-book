"""Programmatic compositor for special publication pages (Welcome/Ownership and Completion Certificate)."""

from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont


def render_welcome_page(
    output_path: str | Path = "output/interior_masters/page_001.png",
    title: str = "TINY HANDS COLOR & LEARN",
    subtitle: str = "FUN & EASY FIRST WORDS",
    font_dir: str | Path = "assets/fonts",
    canvas_w: int = 2550,
    canvas_h: int = 3300,
    dpi: int = 300
) -> Path:
    """Render Page 1: Welcome & 'This Book Belongs To' Ownership Page.
    
    Layout (Right Page / Recto):
    - Top header: 'WELCOME TO' + Book Title
    - Central decorative 'THIS BOOK BELONGS TO:' colorable ribbon box
    - Friendly colorable mascot / book illustration
    - Cheerful bubbly stars, hearts, and bubbles border
    - Safe margins: Gutter >= 0.50 in, Outside >= 0.50 in, Top/Bottom >= 0.50 in
    """
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    f_dir = Path(font_dir)

    img = Image.new("L", (canvas_w, canvas_h), 255)
    draw = ImageDraw.Draw(img)

    f_title = ImageFont.truetype(str(f_dir / "Fredoka-Bold.ttf"), 140)
    f_sub = ImageFont.truetype(str(f_dir / "Fredoka-Bold.ttf"), 70)
    f_badge = ImageFont.truetype(str(f_dir / "Fredoka-Bold.ttf"), 95)
    f_label = ImageFont.truetype(str(f_dir / "Fredoka-Bold.ttf"), 60)
    f_brand = ImageFont.truetype(str(f_dir / "Fredoka-Bold.ttf"), 48)

    # 1. Outer Decorative Double Frame
    draw.rounded_rectangle([180, 180, canvas_w - 180, canvas_h - 180], radius=40, outline=0, width=12)
    draw.rounded_rectangle([210, 210, canvas_w - 210, canvas_h - 210], radius=30, outline=0, width=4)

    # 2. Top Title Section
    draw.text((canvas_w // 2, 380), "WELCOME TO", font=f_sub, fill=0, anchor="mm")
    
    # Book Title in large bubbly text with outline
    draw.text(
        (canvas_w // 2, 540),
        title,
        font=f_title,
        fill=255,
        stroke_width=16,
        stroke_fill=0,
        anchor="mm"
    )
    
    draw.text((canvas_w // 2, 680), subtitle, font=f_sub, fill=80, anchor="mm")
    draw.line([(500, 760), (canvas_w - 500, 760)], fill=0, width=6)

    # 3. Central "This Book Belongs To" Nameplate Box
    box_top = 920
    box_bot = 1620
    box_left = 350
    box_right = canvas_w - 350

    # Shaded shadow + white box
    draw.rounded_rectangle([box_left + 15, box_top + 15, box_right + 15, box_bot + 15], radius=35, fill=220)
    draw.rounded_rectangle([box_left, box_top, box_right, box_bot], radius=35, fill=255, outline=0, width=14)

    # Top Ribbon Badge
    draw.rounded_rectangle([box_left + 80, box_top - 50, box_right - 80, box_top + 60], radius=25, fill=255, outline=0, width=10)
    draw.text((canvas_w // 2, box_top + 5), "THIS BOOK BELONGS TO:", font=f_badge, fill=0, anchor="mm")

    # Name Lines for Child
    draw.text((box_left + 100, box_top + 220), "MY NAME IS:", font=f_label, fill=0, anchor="lm")
    draw.line([(box_left + 100, box_top + 380), (box_right - 100, box_top + 380)], fill=0, width=8)
    draw.line([(box_left + 100, box_top + 540), (box_right - 100, box_top + 540)], fill=180, width=4)

    # 4. Colorable Center Mascot Vignette (Friendly Teddy Bear + Apple + Crayons)
    # Bear head
    draw.ellipse([canvas_w // 2 - 220, 1850, canvas_w // 2 + 220, 2290], fill=255, outline=0, width=12)
    # Bear ears
    draw.ellipse([canvas_w // 2 - 260, 1820, canvas_w // 2 - 140, 1940], fill=255, outline=0, width=10)
    draw.ellipse([canvas_w // 2 + 140, 1820, canvas_w // 2 + 260, 1940], fill=255, outline=0, width=10)
    # Inner ears
    draw.ellipse([canvas_w // 2 - 235, 1845, canvas_w // 2 - 165, 1915], fill=255, outline=0, width=6)
    draw.ellipse([canvas_w // 2 + 165, 1845, canvas_w // 2 + 235, 1915], fill=255, outline=0, width=6)
    # Muzzle & Nose
    draw.ellipse([canvas_w // 2 - 100, 2020, canvas_w // 2 + 100, 2180], fill=255, outline=0, width=8)
    draw.ellipse([canvas_w // 2 - 40, 2040, canvas_w // 2 + 40, 2100], fill=0) # black nose
    draw.arc([canvas_w // 2 - 40, 2080, canvas_w // 2 + 40, 2140], start=0, end=180, fill=0, width=8) # smile
    # Happy eyes
    draw.ellipse([canvas_w // 2 - 110, 1970, canvas_w // 2 - 60, 2020], fill=0)
    draw.ellipse([canvas_w // 2 + 60, 1970, canvas_w // 2 + 110, 2020], fill=0)
    draw.ellipse([canvas_w // 2 - 95, 1975, canvas_w // 2 - 75, 1995], fill=255) # catchlight
    draw.ellipse([canvas_w // 2 + 75, 1975, canvas_w // 2 + 95, 1995], fill=255) # catchlight

    # Bear body & paws
    draw.ellipse([canvas_w // 2 - 280, 2220, canvas_w // 2 + 280, 2750], fill=255, outline=0, width=12)
    draw.ellipse([canvas_w // 2 - 340, 2400, canvas_w // 2 - 200, 2640], fill=255, outline=0, width=10) # left paw
    draw.ellipse([canvas_w // 2 + 200, 2400, canvas_w // 2 + 340, 2640], fill=255, outline=0, width=10) # right paw

    # 5. Decorative Stars and Bubbles
    star_locs = [(320, 320), (canvas_w - 320, 320), (300, 1800), (canvas_w - 300, 1800), (350, 2650), (canvas_w - 350, 2650)]
    for sx, sy in star_locs:
        draw.polygon([(sx, sy - 40), (sx + 12, sy - 12), (sx + 40, sy), (sx + 12, sy + 12), (sx, sy + 40), (sx - 12, sy + 12), (sx - 40, sy), (sx - 12, sy - 12)], fill=255, outline=0, width=6)

    # 6. Bottom Brand Inlay
    draw.text((canvas_w // 2, 2950), "CURIOKRAFT-KIDS  •  EARLY LEARNING SERIES", font=f_brand, fill=0, anchor="mm")
    draw.text((canvas_w // 2, 3020), "Ages 1 - 4  •  100+ First Words, Letters & Numbers", font=f_brand, fill=100, anchor="mm")

    img.save(out_p, dpi=(dpi, dpi))
    return out_p


def render_certificate_page(
    output_path: str | Path = "output/interior_masters/page_110.png",
    title: str = "TINY HANDS COLOR & LEARN",
    font_dir: str | Path = "assets/fonts",
    canvas_w: int = 2550,
    canvas_h: int = 3300,
    dpi: int = 300
) -> Path:
    """Render Page 110: Official Completion Certificate Page ('Super Colorist Award').
    
    Layout (Left Page / Verso):
    - Ornate decorative certificate border with ribbon corners
    - Large 3D Bubbly 'SUPER COLORIST AWARD!'
    - 'PROUDLY PRESENTED TO:' + Wide name line
    - Milestone achievement text
    - Colorable ribbon medal & starburst badge
    - Date & Parent/Teacher Signature lines
    """
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    f_dir = Path(font_dir)

    img = Image.new("L", (canvas_w, canvas_h), 255)
    draw = ImageDraw.Draw(img)

    f_huge = ImageFont.truetype(str(f_dir / "Fredoka-Bold.ttf"), 130)
    f_title = ImageFont.truetype(str(f_dir / "Fredoka-Bold.ttf"), 90)
    f_sub = ImageFont.truetype(str(f_dir / "Fredoka-Bold.ttf"), 65)
    f_name = ImageFont.truetype(str(f_dir / "Fredoka-Bold.ttf"), 75)
    f_body = ImageFont.truetype(str(f_dir / "Fredoka-Bold.ttf"), 52)
    f_small = ImageFont.truetype(str(f_dir / "Fredoka-Bold.ttf"), 44)

    # 1. Ornate Multi-Layer Certificate Frame
    draw.rectangle([140, 140, canvas_w - 140, canvas_h - 140], outline=0, width=16)
    draw.rectangle([170, 170, canvas_w - 170, canvas_h - 170], outline=0, width=4)
    draw.rectangle([210, 210, canvas_w - 210, canvas_h - 210], outline=0, width=8)

    # Corner ribbon rosettes
    corners = [(210, 210), (canvas_w - 210, 210), (210, canvas_h - 210), (canvas_w - 210, canvas_h - 210)]
    for cx, cy in corners:
        draw.ellipse([cx - 45, cy - 45, cx + 45, cy + 45], fill=255, outline=0, width=8)
        draw.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=0)

    # 2. Header Section
    draw.text((canvas_w // 2, 380), "★ OFFICIAL CERTIFICATE ★", font=f_title, fill=0, anchor="mm")
    
    # Large Bubbly Header
    draw.text(
        (canvas_w // 2, 540),
        "SUPER COLORIST AWARD!",
        font=f_huge,
        fill=255,
        stroke_width=16,
        stroke_fill=0,
        anchor="mm"
    )
    draw.line([(400, 640), (canvas_w - 400, 640)], fill=0, width=6)

    # 3. Presentation Text
    draw.text((canvas_w // 2, 780), "THIS CERTIFICATE IS PROUDLY PRESENTED TO:", font=f_sub, fill=80, anchor="mm")

    # Name Line
    draw.line([(350, 1020), (canvas_w - 350, 1020)], fill=0, width=10)
    draw.text((canvas_w // 2, 1070), "(SUPERSTAR ARTIST NAME)", font=f_small, fill=120, anchor="mm")

    # Achievement Paragraph
    draw.text(
        (canvas_w // 2, 1240),
        f"For successfully coloring and learning 100+ everyday objects, letters,",
        font=f_body,
        fill=0,
        anchor="mm"
    )
    draw.text(
        (canvas_w // 2, 1310),
        f"and numbers in '{title}'!",
        font=f_body,
        fill=0,
        anchor="mm"
    )
    draw.text(
        (canvas_w // 2, 1390),
        "You showed amazing creativity, fine motor skills, and imagination!",
        font=f_body,
        fill=0,
        anchor="mm"
    )

    # 4. Large Colorable Medal / Trophy Stamp
    badge_cx, badge_cy = canvas_w // 2, 1820
    # Starburst outer seal
    draw.ellipse([badge_cx - 240, badge_cy - 240, badge_cx + 240, badge_cy + 240], fill=255, outline=0, width=14)
    draw.ellipse([badge_cx - 200, badge_cy - 200, badge_cx + 200, badge_cy + 200], fill=255, outline=0, width=6)
    
    # Medal ribbons hanging down
    draw.polygon([(badge_cx - 100, badge_cy + 180), (badge_cx - 150, badge_cy + 420), (badge_cx - 90, badge_cy + 360), (badge_cx - 30, badge_cy + 420), (badge_cx - 40, badge_cy + 200)], fill=255, outline=0, width=8)
    draw.polygon([(badge_cx + 40, badge_cy + 200), (badge_cx + 30, badge_cy + 420), (badge_cx + 90, badge_cy + 360), (badge_cx + 150, badge_cy + 420), (badge_cx + 100, badge_cy + 180)], fill=255, outline=0, width=8)
    
    # Text inside seal
    draw.text((badge_cx, badge_cy - 70), "★ ★ ★", font=f_title, fill=0, anchor="mm")
    draw.text((badge_cx, badge_cy + 15), "#1", font=f_huge, fill=0, anchor="mm")
    draw.text((badge_cx, badge_cy + 105), "CHAMPION", font=f_sub, fill=0, anchor="mm")

    # 5. Signature and Date Section
    sig_y = 2650
    # Date Line
    draw.line([(350, sig_y), (1050, sig_y)], fill=0, width=6)
    draw.text((700, sig_y + 50), "DATE", font=f_small, fill=0, anchor="mm")

    # Teacher / Parent Signature Line
    draw.line([(canvas_w - 1050, sig_y), (canvas_w - 350, sig_y)], fill=0, width=6)
    draw.text((canvas_w - 700, sig_y + 50), "PARENT / TEACHER SIGNATURE", font=f_small, fill=0, anchor="mm")

    # 6. Bottom Brand Footer
    draw.text((canvas_w // 2, 2980), "CURIOKRAFT-KIDS PUBLICATIONS  •  OFFICIAL MASTER EDITION", font=f_small, fill=100, anchor="mm")

    img.save(out_p, dpi=(dpi, dpi))
    return out_p
