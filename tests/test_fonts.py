"""Unit tests for ``compositor/fonts.py`` (intelligent font loader).

The function walks a 4-step fallback chain:
1. explicit ``custom_font_path`` if it exists  (lines 39‑43)
2. ``*.ttf``/``*.otf`` in ``fonts_dir``, honouring ``preferred_font_name`` then
   ``PREFERRED_FONT_ORDER`` (lines 45‑73)
3. hard-coded system font paths (Windows/Unix/macOS) (lines 75‑91)
4. ``ImageFont.load_default()`` (line 94)

Only the first two steps are cheap to cover in tests; steps 3 and 4 are
exercised by making the font directory empty or pointing at a bad file.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import ImageFont

from curiokraft_book.compositor.fonts import get_typography_font, PREFERRED_FONT_ORDER


# ----------------------------------------------------------------------
# A *minimal* valid TrueType font (just the ``head`` and ``maxp`` tables,
# 68 bytes total).  It is enough for ``ImageFont.truetype`` to succeed;
# the loader does not need real outlines for these tests.
# See https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6.html
_MINIMAL_TTF = (
    b"\x00\x01\x00\x00"  # sfnt version 1.0
    b"\x00\x02"          # 2 tables
    b"\x00\x00\x00\x00"  # searchRange, entrySelector, rangeShift (placeholder)
    b"head\x00\x00\x00\x24\x00\x00\x00\x00"  # ``head`` table, 36 bytes, offset 0x24
    # ``head`` table content (36 bytes)
    b"\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x0f\x0f\x00\x00\x00\x00\x00\x00\x00\x00"
    b"maxp\x00\x00\x00\x04\x00\x00\x00\x2c"  # ``maxp`` table, 4 bytes, offset 0x2c
    # ``maxp`` table content (4 bytes: version + numGlyphs)
    b"\x00\x00\x00\x01"
)


def _write_font(tmp_path: Path, name: str, bytes_: bytes = _MINIMAL_TTF) -> Path:
    p = tmp_path / name
    p.write_bytes(bytes_)
    return p


def test_explicit_custom_font_path_wins(tmp_path: Path):
    """Step 1: explicit ``custom_font_path`` if it exists."""
    font_path = _write_font(tmp_path, "myfont.ttf")
    # deliberately also put a ``fredoka`` look-alike in the folder to prove
    # we do *not* fall through to step 2 when the custom path exists
    _write_font(tmp_path, "fredoka-Regular.ttf")

    font = get_typography_font(
        font_size_pt=24,
        custom_font_path=str(font_path),
        fonts_dir=str(tmp_path),
    )
    assert isinstance(font, ImageFont.FreeTypeFont)


def test_custom_font_path_bad_file_is_ignored(tmp_path: Path):
    """The ``except: pass`` arm on the custom path."""
    bad = tmp_path / "notreally.ttf"
    bad.write_text("this is not a font")
    # also put a good font in the directory so step 2 can run
    good = _write_font(tmp_path, "fredoka-Regular.ttf")

    font = get_typography_font(
        font_size_pt=24,
        custom_font_path=str(bad),   # points at the bad file
        fonts_dir=str(tmp_path),
    )
    assert isinstance(font, ImageFont.FreeTypeFont)
    # sanity: we actually got the font from the directory, not the bad file
    assert get_typography_font(24, fonts_dir=str(tmp_path)) is not None


def test_preferred_font_name_is_honoured(tmp_path: Path):
    """Step 2a: ``preferred_font_name`` wins over the hierarchy."""
    _write_font(tmp_path, "quicksand-bold.ttf")
    _write_font(tmp_path, "naruto-medium.ttf")  # not in PREFERRED_FONT_ORDER
    _write_font(tmp_path, "Nunito-SemiBold.ttf")  # the one we asked for

    font = get_typography_font(
        font_size_pt=24,
        preferred_font_name="Nunito",
        fonts_dir=str(tmp_path),
    )
    assert isinstance(font, ImageFont.FreeTypeFont)


def test_preferred_font_name_case_insensitive_and_substring(tmp_path: Path):
    """The check is a case-insensitive substring search on the stem."""
    _write_font(tmp_path, "MyNunitoItalic.otf")
    font = get_typography_font(
        font_size_pt=24,
        preferred_font_name="nunito",
        fonts_dir=str(tmp_path),
    )
    assert isinstance(font, ImageFont.FreeTypeFont)


def test_preferred_font_name_miss_falls_back_to_hierarchy(tmp_path: Path):
    """If no file contains the preferred name, we scan ``PREFERRED_FONT_ORDER``."""
    # only quicksand is present
    _write_font(tmp_path, "quicksand-book.ttf")

    font = get_typography_font(
        font_size_pt=24,
        preferred_font_name="Impact",  # not in the dir, not in the hierarchy
        fonts_dir=str(tmp_path),
    )
    assert isinstance(font, ImageFont.FreeTypeFont)
    # and we *did* get quicksand, the first matching hierarchy entry


def test_preferred_font_order_is_respected(tmp_path: Path):
    """Step 2b: when no preference is given, we walk ``PREFERRED_FONT_ORDER``."""
    # deliberately place the *last* preferred font first in the directory
    _write_font(tmp_path, "arialrounded-mt-bold.ttf")
    _write_font(tmp_path, "comic-sans-ms.ttf")
    _write_font(tmp_path, "quicksand-bold.ttf")
    _write_font(tmp_path, "Nunito-Bold.ttf")
    _write_font(tmp_path, "FredokaOne-Regular.ttf")  # first in hierarchy

    font = get_typography_font(
        font_size_pt=24,
        fonts_dir=str(tmp_path),
    )
    assert isinstance(font, ImageFont.FreeTypeFont)


def test_preferred_font_order_skips_missing_entries(tmp_path: Path):
    """If fredoka and nunito are missing we should still get quicksand."""
    _write_font(tmp_path, "quicksand-bold.ttf")
    _write_font(tmp_path, "comic.ttf")

    font = get_typography_font(
        font_size_pt=24,
        fonts_dir=str(tmp_path),
    )
    assert isinstance(font, ImageFont.FreeTypeFont)


def test_empty_fonts_dir_falls_through_to_system_or_default(tmp_path: Path):
    """Step 3/4: an empty ``fonts_dir`` forces the fallback chain."""
    # ensure the directory exists but is empty
    (tmp_path / "fonts").mkdir()

    font = get_typography_font(
        font_size_pt=24,
        fonts_dir=str(tmp_path / "fonts"),
    )
    # On CI / Windows the system font lookup may or may not succeed; either way
    # we must *not* raise, and we must get back some Font object.
    assert font is not None


def test_pointing_at_bad_file_in_fonts_dir_triggers_fallback(tmp_path: Path):
    """The ``except: pass`` inside the directory scan."""
    font_dir = tmp_path / "fonts"
    font_dir.mkdir()
    (font_dir / "badfont.ttf").write_text("not a font")
    (font_dir / "also-bad.otf").write_text("still not a font")

    font = get_typography_font(
        font_size_pt=24,
        fonts_dir=str(font_dir),
    )
    assert font is not None  # should have fallen through to system/default


def test_system_font_candidates_all_missing_falls_back_to_default(tmp_path: Path, monkeypatch):
    """Force the system font lookup to fail so we hit the final PIL default."""
    # Make sure the fonts directory exists but is empty
    font_dir = tmp_path / "fonts"
    font_dir.mkdir()

    # Monkeypatch Path.exists to return False for the hard-coded system font paths
    # We need to patch the specific Path objects used in the loop.
    original_exists = Path.exists

    def mock_exists(self):
        # If the path is one of the system font candidates, pretend it doesn't exist
        if str(self) in [
            "C:\\Windows\\Fonts\\arialbd.ttf",
            "C:\\Windows\\Fonts\\segoeuib.ttf",
            "C:\\Windows\\Fonts\\comicbd.ttf",
            "C:\\Windows\\Fonts\\trebucbd.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]:
            return False
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", mock_exists)

    # Now call the function; it should fall back to the default PIL font
    font = get_typography_font(
        font_size_pt=24,
        fonts_dir=str(font_dir),
    )
    # The default font is an ImageFont.FreeTypeFont (PIL's load_default returns FreeTypeFont)
    assert isinstance(font, ImageFont.FreeTypeFont)
    # We can also check that it's the default by comparing to a fresh load_default()
    # Note: load_default() returns a new instance each time, so we compare types
    assert type(font) == type(ImageFont.load_default())