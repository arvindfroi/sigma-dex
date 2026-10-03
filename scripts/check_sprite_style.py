#!/usr/bin/env python3
"""Check the sprite renderer against a fixed test set, so a change to it shows exactly what it does.

    python scripts/check_sprite_style.py            # render, compare, check the standard
    python scripts/check_sprite_style.py --update   # accept the current sprites as the reference

tests/sprite_style/art/ holds artwork the sprite studio drew for eight very different Pokemon
(front and back, two attempts each); tests/sprite_style/expected/ holds the sprites accepted for
them. The script renders every one, says which changed and how many pixels, checks each against
the sprite standard (sprite_quality.standards), and writes a sheet with art, sprite and reference
side by side to tests/sprite_style/sheet.png (not kept in the repository). Needs opencv and Pillow.
"""
import argparse
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pixel_render
import sprite_quality
import sprites

ROOT = Path(__file__).resolve().parent.parent / "tests" / "sprite_style"
SIZE = {"waffy": 54, "torchbat": 54, "leafing": 54, "autuman": 60, "tinky": 54, "chillalit": 54, "bugmight": 63, "ampeel": 63}
AREA = {54: 955, 60: 1530, 63: 2452}          # first, middle, final stage (sprite_worker.sprite_area)


def render_pair(front_art, back_art, size):
    """Front and back exactly as the sprite worker makes them (official_sprites), through the game converter."""
    front = pixel_render.render(front_art, size=size, area=AREA.get(size))
    size = max(front.size)
    back = pixel_render.render(back_art, fit=(62, round(size * 1.4)), palette=pixel_render.palette_of(front))
    back = back.crop((0, 0, back.width, round(back.height / 1.4) + 2))
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        front.save(folder / "f.png"); back.save(folder / "b.png")
        sprites.build("test", {"front": folder / "f.png", "back": folder / "b.png"}, note="test", out=folder / "out")
        return sprites.as_rgba(folder / "out" / "front.png"), sprites.as_rgba(folder / "out" / "back.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--update", action="store_true", help="save the current sprites as the reference")
    args = parser.parse_args()
    expected = ROOT / "expected"
    expected.mkdir(exist_ok=True)
    rows, passed, changed, total = [], 0, 0, 0
    for art in sorted((ROOT / "art").glob("*_front.webp")):
        name = art.name[:-len("_front.webp")]
        sid = name.rsplit("_", 1)[0]
        front, back = render_pair(art, art.with_name(name + "_back.webp"), SIZE.get(sid, 54))
        fails = sprite_quality.standards(front, back, None)
        total += 1
        passed += not fails
        diff = []
        for view, image in (("front", front), ("back", back)):
            ref = expected / ("%s_%s.png" % (name, view))
            if args.update:
                image.save(ref)
            elif ref.exists():
                a, b = np.array(image), np.array(Image.open(ref).convert("RGBA"))
                if a.shape != b.shape or (a != b).any():
                    diff.append("%s: %s" % (view, "size %s -> %s" % (b.shape[:2], a.shape[:2]) if a.shape != b.shape else "%d pixels differ" % (a != b).any(axis=2).sum()))
            else:
                diff.append(view + ": no reference yet")
        changed += bool(diff)
        print("%-14s %-6s %s%s" % (name, "PASS" if not fails else "FAIL", "; ".join(fails), ("   changed: " + ", ".join(diff)) if diff else ""))
        rows.append((name, art, front, back, expected / ("%s_front.png" % name), fails))
    print("\n%d of %d pass the standard; %d differ from the reference%s" % (passed, total, changed, " (references updated)" if args.update else ""))
    cell = 160
    sheet = Image.new("RGB", (5 * (cell + 4), len(rows) * (cell + 16)), "white")
    draw = ImageDraw.Draw(sheet)
    for r, (name, art, front, back, ref, fails) in enumerate(rows):
        y = r * (cell + 16)
        pics = [Image.open(art).convert("RGB").resize((cell, cell))]
        for image in (front, back) + ((Image.open(ref).convert("RGBA"),) if ref.exists() else ()):
            bg = Image.new("RGBA", image.size, (200, 222, 200, 255)); bg.alpha_composite(image)
            pics.append(bg.convert("RGB").resize((cell, cell), Image.NEAREST))
        for k, pic in enumerate(pics):
            sheet.paste(pic, (k * (cell + 4), y))
        draw.text((2, y + cell + 2), "%s  %s" % (name, "PASS" if not fails else fails[0]), fill="black" if not fails else (180, 0, 0))
    sheet.save(ROOT / "sheet.png")
    print("sheet: %s (art | front | back | reference front)" % (ROOT / "sheet.png"))
    return 0 if passed >= total - 2 else 1


if __name__ == "__main__":
    sys.exit(main())
