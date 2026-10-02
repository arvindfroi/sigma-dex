#!/usr/bin/env python3
"""Turn pictures into sprites in the exact format the game needs.

    python scripts/sprites.py make <pokemon> --front PIC [--front2 PIC] [--back PIC]
                                             [--shiny PIC] [--icon PIC] [--footprint PIC] [--size 64]
    python scripts/sprites.py auto     # build from pictures uploaded on the website as sprite pictures
    python scripts/sprites.py check    # check every sprite folder against the game's rules

Any picture works as input: a drawing, AI art, or a finished pixel sprite. The background is
removed, the picture is shrunk to fit 64x64, and its colors are reduced to the 15 the game
allows (front and back share them). A picture that already is a 64x64 sprite passes through
unchanged apart from the color check. What comes out is in assets/sprites/<pokemon>/, see
docs/SPRITES.md.
"""
import argparse
import hashlib
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

import dexlib
from dexlib import ROOT, section

SPRITES = ROOT / "assets" / "sprites"
ICON_PALETTES = ROOT / "data" / "engine" / "icon_palettes.yaml"
FRAME, ICON, FOOT, COLORS = 64, 32, 16, 15
BACKDROPS = [(152, 208, 160), (255, 0, 255), (0, 255, 255), (0, 255, 0)]   # color 0, the see-through one
KINDS = ("front", "front2", "back", "shiny", "icon", "footprint")
TOOL_VERSION = 1


class SpriteError(Exception):
    pass


# ---------- reading a picture ----------

def cutout(image):
    """RGBA copy of the picture with its background made see-through."""
    image = image.convert("RGBA")
    pixels = np.array(image)
    if (pixels[..., 3] < 128).mean() > 0.01:
        return image                                    # it already has a transparent background
    work = image
    if max(image.size) > 512:                           # flood-filling a huge picture is slow and gains nothing
        scale = 512 / max(image.size)
        work = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.BOX)
    rgb = np.array(work)[..., :3].astype(int)
    height, width = rgb.shape[:2]
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    colors, counts = np.unique(border // 8, axis=0, return_counts=True)
    background = colors[counts.argmax()] * 8 + 4
    close = (np.abs(rgb - background).sum(axis=2) < 60)  # pixels that look like the background
    outside = np.zeros((height, width), bool)
    queue = deque()
    for x in range(width):
        queue.extend(((0, x), (height - 1, x)))
    for y in range(height):
        queue.extend(((y, 0), (y, width - 1)))
    while queue:                                        # only background that touches the edge is removed
        y, x = queue.popleft()
        if y < 0 or x < 0 or y >= height or x >= width or outside[y, x] or not close[y, x]:
            continue
        outside[y, x] = True
        queue.extend(((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)))
    mask = Image.fromarray((~outside * 255).astype(np.uint8)).resize(image.size, Image.NEAREST)
    image.putalpha(mask)
    image.info["background"] = tuple(int(v) for v in background)
    return image


def block_size(image):
    """If the picture is pixel art that was blown up (every pixel a block of NxN), return N."""
    pixels = np.array(image)
    for n in range(32, 1, -1):
        if image.width % n or image.height % n:
            continue
        small = pixels[n // 2::n, n // 2::n]
        if np.array_equal(np.repeat(np.repeat(small, n, axis=0), n, axis=1), pixels):
            return n
    return 1


def snap(image, grid):
    """Pixel art drawn by an AI on a grid x grid canvas: give every cell its most common color.

    Averaging would blur the edges between the big "pixels"; taking the commonest color keeps them crisp.
    """
    side = grid * 8
    pixels = np.array(image.resize((side, side), Image.BOX)).astype(int)
    coarse = pixels[..., :3] // 16                         # similar shades count as the same color
    keys = (coarse[..., 0] << 8 | coarse[..., 1] << 4 | coarse[..., 2]).reshape(grid, 8, grid, 8).swapaxes(1, 2).reshape(grid, grid, 64)
    cells = pixels.reshape(grid, 8, grid, 8, 4).swapaxes(1, 2).reshape(grid, grid, 64, 4)
    out = np.zeros((grid, grid, 4), np.uint8)
    for y in range(grid):
        for x in range(grid):
            solid = cells[y, x, :, 3] >= 128
            if solid.sum() < 32:
                continue                                   # mostly see-through: leave the cell empty
            values, counts = np.unique(keys[y, x][solid], return_counts=True)
            chosen = solid & (keys[y, x] == values[counts.argmax()])
            out[y, x, :3] = cells[y, x][chosen][:, :3].mean(axis=0)
            out[y, x, 3] = 255
    return Image.fromarray(out)


def snap_detail(image, grid, thickness=2):
    """Like snap(), but keeps thin outlines and small features (eyes, claws) alive.

    Uses the PixelOE method (github.com/KohakuBlueleaf/PixelOE): contrasting lines are thickened
    before the picture is shrunk, and every cell takes its most contrasting value instead of
    its commonest. Needs the `pixeloe` package (Python 3.10 or newer).
    """
    import cv2
    from pixeloe.legacy.pixelize import pixelize
    side = grid * 8
    big = image.resize((side, side), Image.LANCZOS)
    flat = Image.new("RGBA", big.size, "white")
    flat.alpha_composite(big)
    bgr = cv2.cvtColor(np.array(flat.convert("RGB")), cv2.COLOR_RGB2BGR)
    small = cv2.cvtColor(pixelize(bgr, mode="contrast", target_size=grid, patch_size=8, thickness=thickness, no_upscale=True), cv2.COLOR_BGR2RGB)
    alpha = np.array(big.getchannel("A")).reshape(grid, 8, grid, 8).swapaxes(1, 2).reshape(grid, grid, 64)
    solid = ((alpha >= 128).sum(axis=2) >= 32).astype(np.uint8) * 255
    return Image.fromarray(np.dstack([small[:grid, :grid], solid]))


def defringe(image, background):
    """Remove the pale rim that is left where a drawing's edge blended into its background."""
    pixels = np.array(image)
    for _ in range(2):
        opaque = pixels[..., 3] >= 128
        padded = np.pad(opaque, 1)
        inside = padded[:-2, 1:-1] & padded[2:, 1:-1] & padded[1:-1, :-2] & padded[1:-1, 2:]
        like_background = np.abs(pixels[..., :3].astype(int) - np.array(background)).sum(axis=2) < 150
        pixels[opaque & ~inside & like_background, 3] = 0
    return Image.fromarray(pixels)


def despeckle(indexes, opaque, palette):
    """Replace lone pixels (noise) with the color around them. The lightest and darkest colors stay: eye glints and pupils."""
    brightness = [sum(color) for color in palette]
    keep = {brightness.index(min(brightness)), brightness.index(max(brightness))}
    out = indexes.copy()
    height, width = indexes.shape
    for y in range(height):
        for x in range(width):
            if not opaque[y, x] or indexes[y, x] in keep:
                continue
            around = [indexes[j, i] for j in range(max(0, y - 1), min(height, y + 2)) for i in range(max(0, x - 1), min(width, x + 2))
                      if (j, i) != (y, x) and opaque[j, i]]
            if around and indexes[y, x] not in around:
                out[y, x] = max(set(around), key=around.count)
    return out


def tidy(opaque):
    """Remove single stray pixels that stick out of or float around the drawing."""
    padded = np.pad(opaque, 1)
    neighbours = sum(np.roll(np.roll(padded, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx)[1:-1, 1:-1]
    return opaque & (neighbours >= 2)


def shrink(image, limit, grid=None, detail=False):
    """Crop to the drawing and make it fit in limit x limit. Returns (rgb, opaque) arrays."""
    image = cutout(image)
    if grid:
        background = image.info.get("background")
        image = snap_detail(image, grid) if detail else snap(image, grid)
        if background:
            image = defringe(image, background)
    n = block_size(image)
    if n > 1:
        image = image.resize((image.width // n, image.height // n), Image.NEAREST)
    box = image.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox()
    if not box:
        raise SpriteError("the picture is empty after removing the background")
    image = image.crop(box)
    if max(image.size) > limit:
        scale = limit / max(image.size)
        size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
        pixels = np.array(image).astype(float)
        pixels[..., :3] *= pixels[..., 3:] / 255          # so the background does not bleed into the edges
        small = np.array(Image.fromarray(pixels.astype(np.uint8)).resize(size, Image.BOX)).astype(float)
        alpha = small[..., 3:]
        rgb = np.where(alpha > 0, small[..., :3] * 255 / np.maximum(alpha, 1), 0)
        return np.clip(rgb, 0, 255).astype(np.uint8), small[..., 3] >= 128
    pixels = np.array(image)
    opaque = pixels[..., 3] >= 128
    if grid:
        opaque = tidy(opaque)
        return outline(pixels[..., :3], opaque), opaque
    return pixels[..., :3], opaque


def gba(colors):
    """The GBA stores 5 bits per channel; round colors to what it can show."""
    return (np.asarray(colors).astype(int) // 8) * 8


def pick_palette(frames):
    """Up to 15 colors that suit all the frames together.

    Small but important colors (the white of an eye, a dark outline) must survive, so every
    distinct color counts by the square root of how often it is used, not by its full area.
    """
    pixels = np.concatenate([gba(rgb[opaque]) for rgb, opaque in frames])
    unique, counts = np.unique(pixels, axis=0, return_counts=True)
    if len(unique) <= COLORS:
        return [tuple(int(v) for v in c) for c in unique]
    weights = np.maximum(1, np.sqrt(counts)).astype(int)
    strip = Image.fromarray(np.repeat(unique, weights, axis=0).astype(np.uint8).reshape(1, -1, 3))
    reduced = strip.quantize(COLORS - 2, method=Image.Quantize.MEDIANCUT, kmeans=3, dither=Image.Dither.NONE)
    raw = reduced.getpalette()
    palette = []
    brightness = unique.sum(axis=1)
    for color in ([unique[brightness.argmin()], unique[brightness.argmax()]]            # always keep the darkest and the lightest
                  + [raw[i * 3:i * 3 + 3] for i in sorted(set(reduced.getdata()))]):
        color = tuple(int(v) for v in gba(color))
        if color not in palette:
            palette.append(color)
    return palette


def outline(rgb, opaque):
    """Darken the pixels on the edge of the drawing, the way hand-made sprites have a dark colored outline."""
    padded = np.pad(opaque, 1)
    inside = padded[:-2, 1:-1] & padded[2:, 1:-1] & padded[1:-1, :-2] & padded[1:-1, 2:]
    edge = opaque & ~inside
    out = rgb.astype(float)
    out[edge] *= 0.45
    return out.astype(np.uint8)


def nearest(rgb, palette):
    """Index of the closest palette color for every pixel."""
    table = np.array(palette, int)
    difference = rgb.astype(int)[:, :, None, :] - table[None, None, :, :]
    return (difference ** 2 * np.array([3, 4, 2])).sum(axis=3).argmin(axis=2)   # eyes notice green most


def place(indexes, opaque, size, bottom=False):
    """Put the drawing on an empty size x size frame. Index 0 is see-through."""
    height, width = opaque.shape
    frame = np.zeros((size, size), np.uint8)
    top = size - height if bottom else (size - height) // 2
    left = (size - width) // 2
    frame[top:top + height, left:left + width] = np.where(opaque, indexes + 1, 0)
    return frame


def backdrop(palette):
    return next(color for color in BACKDROPS if color not in palette)


def save_indexed(frame, colors, path, bits=4):
    image = Image.fromarray(frame).convert("L")
    image = Image.frombytes("P", image.size, image.tobytes())
    flat = [channel for color in colors for channel in color]
    image.putpalette(flat + [0] * (3 * (2 ** bits) - len(flat)))
    image.save(path, bits=bits, optimize=False)


def save_pal(colors, path):
    colors = list(colors) + [(0, 0, 0)] * (16 - len(colors))
    path.write_bytes(("JASC-PAL\r\n0100\r\n16\r\n" + "".join("%d %d %d\r\n" % tuple(c) for c in colors)).encode())


def measure(frame):
    """Width and height of the drawing (rounded up to 8, as the game wants) and the empty rows below it."""
    rows, columns = np.where(frame.any(axis=1))[0], np.where(frame.any(axis=0))[0]
    up8 = lambda value: min(FRAME, -(-int(value) // 8) * 8)
    return {"width": up8(columns[-1] - columns[0] + 1), "height": up8(rows[-1] - rows[0] + 1),
            "y_offset": int(frame.shape[0] - 1 - rows[-1])}


def icon_palettes():
    return [[tuple(color) for color in palette] for palette in yaml.safe_load(ICON_PALETTES.read_text(encoding="utf-8"))["palettes"]]


def make_icon(rgb, opaque):
    """32x64 icon (two frames) in whichever of the game's shared icon palettes fits best."""
    best = None
    for number, palette in enumerate(icon_palettes()):
        indexes = nearest(rgb, palette[1:])
        error = ((np.array(palette[1:], int)[indexes] - rgb.astype(int)) ** 2).sum(axis=2)[opaque].sum()
        if best is None or error < best[0]:
            best = (error, number, indexes, palette)
    _, number, indexes, palette = best
    still = place(indexes, opaque, ICON)
    bob = np.roll(still, -1, axis=0) if not still[0].any() else still       # second frame: one pixel up
    return np.vstack([still, bob]), palette, number


# ---------- building one Pokemon's sprites ----------

def build(sid, sources, size=FRAME, note=None, grid=None, out=None, detail=False):
    """sources: {kind: path}. Writes assets/sprites/<sid>/ (or `out`) and returns the facts about it."""
    if "front" not in sources:
        raise SpriteError("a front picture is needed")
    if not 8 <= size <= FRAME:
        raise SpriteError("--size must be between 8 and 64")
    opened = {kind: Image.open(path) for kind, path in sources.items()}
    for kind, image in opened.items():
        image.load()
    drawn = {kind: shrink(opened[kind], size, grid, detail) for kind in ("front", "front2", "back") if kind in opened}
    palette = pick_palette(list(drawn.values()))
    colors = [backdrop(palette)] + palette
    clean = (lambda indexes, opaque: despeckle(indexes, opaque, palette)) if grid else (lambda indexes, opaque: indexes)
    frames = {kind: place(clean(nearest(rgb, palette), opaque), opaque, FRAME) for kind, (rgb, opaque) in drawn.items()}

    out = Path(out) if out else SPRITES / sid
    out.mkdir(parents=True, exist_ok=True)
    for stale in out.iterdir():
        stale.unlink()
    front = frames["front"]
    second = frames.get("front2", front)
    save_indexed(front, colors, out / "front.png")
    save_indexed(np.vstack([front, second]), colors, out / "anim_front.png")
    save_pal(colors, out / "normal.pal")
    facts = {"tool_version": TOOL_VERSION, "colors": len(palette), "animated": "front2" in frames,
             "front": measure(front), "drafts": [], "sources": {k: digest(p) for k, p in sorted(sources.items())}}
    if note:
        facts["note"] = note
    if "back" in frames:
        save_indexed(frames["back"], colors, out / "back.png")
        facts["back"] = measure(frames["back"])

    shiny = None
    if "shiny" in opened:                                # the same drawing in the shiny colors
        rgb, opaque = shrink(opened["shiny"], size, grid, detail)
        if opaque.shape != drawn["front"][1].shape:
            raise SpriteError("the shiny picture must be the front picture recolored (same size and outline)")
        indexes = nearest(drawn["front"][0], palette)
        both = opaque & drawn["front"][1]
        shiny = [colors[0]] + [tuple(int(v) for v in gba(rgb[both & (indexes == i)].mean(axis=0))) if (both & (indexes == i)).any() else color
                               for i, color in enumerate(palette)]
    else:
        facts["drafts"].append("shiny.pal (same colors as normal until a shiny picture is given)")
    save_pal(shiny or colors, out / "shiny.pal")

    if "icon" in opened:
        icon_rgb, icon_opaque = shrink(opened["icon"], ICON)
    else:
        icon_rgb, icon_opaque = shrink(opened["front"], ICON - 4)
        facts["drafts"].append("icon.png (the front picture shrunk; a hand-made icon looks better)")
    icon, icon_colors, facts["icon_palette"] = make_icon(icon_rgb, icon_opaque)
    save_indexed(icon, icon_colors, out / "icon.png")

    if "footprint" in opened:
        _, mark = shrink(opened["footprint"], FOOT)
        save_indexed(place(np.zeros(mark.shape, int), mark, FOOT), [(255, 255, 255), (0, 0, 0)], out / "footprint.png", bits=1)

    preview(out, colors, shiny or colors, [front] + ([second] if "front2" in frames else []) + ([frames["back"]] if "back" in frames else []),
            icon[:ICON], icon_colors)
    (out / "sprite.json").write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")
    problems = check_folder(out)
    if problems:
        raise SpriteError("the result does not pass the checks: " + "; ".join(problems))
    return facts


def preview(out, colors, shiny, frames, icon, icon_colors, zoom=4):
    """One picture showing everything enlarged, for people to judge the result."""
    def paint(frame, palette):
        rgb = np.array(palette, np.uint8)[frame]
        board = ((np.indices(frame.shape).sum(axis=0) // 4) % 2 * 16 + 224).astype(np.uint8)   # checkerboard = see-through
        return np.where((frame > 0)[..., None], rgb, board[..., None].repeat(3, axis=2))
    tiles = [paint(frame, colors) for frame in frames]
    if shiny != colors:
        tiles.append(paint(frames[0], shiny))
    small = np.full((FRAME, FRAME, 3), 224, np.uint8)
    small[16:48, 16:48] = paint(icon, icon_colors)
    tiles.append(small)
    strip = np.concatenate(tiles, axis=1)
    Image.fromarray(strip).resize((strip.shape[1] * zoom, strip.shape[0] * zoom), Image.NEAREST).save(out / "preview.png")


def as_rgba(path):
    """An indexed sprite as a normal picture with a see-through background (color 0)."""
    image = Image.open(path)
    alpha = np.where(np.array(image) > 0, 255, 0).astype(np.uint8)
    rgba = image.convert("RGBA")
    rgba.putalpha(Image.fromarray(alpha))
    return rgba


def digest(path):
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()[:16]


def record(sid, facts):
    """Point the species file at the new sprites."""
    species, _ = dexlib.load_species()
    path, data = next((p, d) for s, p, d in species if s == sid)
    folder = SPRITES / sid
    assets = dict(section(data, "assets"))
    relative = lambda name: str((folder / name).relative_to(ROOT)) if (folder / name).exists() else None
    assets.update(front_sprite=relative("front.png"), front_anim=relative("anim_front.png"), back_sprite=relative("back.png"),
                  icon=relative("icon.png"), footprint=relative("footprint.png"),
                  shiny_palette=relative("shiny.pal") if not any(d.startswith("shiny") for d in facts["drafts"]) else None)
    engine = dict(section(data, "engine"))
    engine.update(front_y_offset=facts["front"]["y_offset"], icon_palette=facts["icon_palette"])
    if "back" in facts:
        engine["back_y_offset"] = facts["back"]["y_offset"]
    data["assets"], data["engine"] = assets, engine
    dexlib.write_species(path, data)


# ---------- checking ----------

def check_folder(folder):
    """What is wrong with a sprite folder, as a list of sentences (empty = fine)."""
    problems = []
    rules = {"front.png": (FRAME, FRAME, 16), "anim_front.png": (FRAME, FRAME * 2, 16), "back.png": (FRAME, FRAME, 16),
             "icon.png": (ICON, ICON * 2, 16), "footprint.png": (FOOT, FOOT, 2)}
    palettes = {}
    for name, (width, height, limit) in rules.items():
        path = folder / name
        if not path.exists():
            if name in ("front.png", "anim_front.png", "icon.png"):
                problems.append("%s is missing" % name)
            continue
        image = Image.open(path)
        if image.size != (width, height):
            problems.append("%s is %dx%d, must be %dx%d" % (name, image.width, image.height, width, height))
        if image.mode != "P":
            problems.append("%s is not an indexed-color PNG" % name)
            continue
        used = max(image.getdata()) + 1
        if used > limit:
            problems.append("%s uses %d colors, the limit is %d" % (name, used, limit))
        palettes[name] = image.getpalette()[:48]
    for name in ("anim_front.png", "back.png"):
        if name in palettes and "front.png" in palettes and palettes[name] != palettes["front.png"]:
            problems.append("%s does not have the same palette as front.png" % name)
    if "icon.png" in palettes and ICON_PALETTES.exists():
        flat = [[channel for color in palette for channel in color] for palette in icon_palettes()]
        if palettes["icon.png"] not in flat:
            problems.append("icon.png does not use one of the game's 6 icon palettes")
    for name in ("normal.pal", "shiny.pal"):
        path = folder / name
        if not path.exists():
            problems.append("%s is missing" % name)
        elif len([line for line in path.read_text().split("\n")[3:] if line.strip()]) != 16:
            problems.append("%s must list exactly 16 colors" % name)
    return problems


def check_all():
    """(folder name, problem) for every sprite folder. Used by validate.py too."""
    found = []
    for folder in sorted(SPRITES.glob("*")) if SPRITES.exists() else []:
        if folder.is_dir():
            found += [(folder.name, problem) for problem in check_folder(folder)]
    return found


# ---------- pictures uploaded on the website ----------

def tagged(caption):
    """'[front] my drawing' -> 'front'. Pictures without such a tag are concept art."""
    caption = (caption or "").strip().lower()
    return next((kind for kind in KINDS if caption.startswith("[%s]" % kind)), None)


def auto():
    manifest_path = ROOT / "data" / "images.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []
    wanted = {}
    for entry in manifest:                              # later uploads replace earlier ones of the same kind
        kind = tagged(entry.get("caption"))
        if kind and (ROOT / entry["file"]).exists():
            wanted.setdefault(entry["species"], {})[kind] = ROOT / entry["file"]
    built = 0
    for sid, sources in sorted(wanted.items()):
        facts_path = SPRITES / sid / "sprite.json"
        old = json.loads(facts_path.read_text(encoding="utf-8")) if facts_path.exists() else {}
        if old.get("note") == "made by hand":
            continue                                    # never overwrite sprites someone made with `make`
        if old.get("sources") == {k: digest(p) for k, p in sorted(sources.items())} and old.get("tool_version") == TOOL_VERSION:
            continue
        try:
            drawn_by_ai = any((entry.get("caption") or "").startswith("[front] AI draft") for entry in manifest if entry["species"] == sid)
            record(sid, build(sid, sources, note="AI draft" if drawn_by_ai else "from the website"))
            built += 1
        except (SpriteError, OSError) as error:
            print("WARNING: sprites for %s could not be made: %s" % (sid, error))
    print("Sprites: %d Pokemon rebuilt from website pictures" % built)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("make")
    make.add_argument("pokemon")
    for kind in KINDS:
        make.add_argument("--" + kind, required=kind == "front")
    make.add_argument("--size", type=int, default=FRAME, help="longest side of the drawing in pixels (smaller Pokemon look right at 40-56)")
    make.add_argument("--detail", action="store_true", help="with --grid: keep thin outlines and small features when shrinking (needs the pixeloe package)")
    make.add_argument("--grid", type=int, help="the picture is AI pixel art drawn on a GRID x GRID canvas (usually 64): keep its pixels crisp")
    commands.add_parser("auto")
    commands.add_parser("check")
    args = parser.parse_args()

    if args.command == "auto":
        return auto()
    if args.command == "check":
        problems = check_all()
        for name, problem in problems:
            print("%s: %s" % (name, problem))
        print("%d sprite folders checked, %d problems" % (len(list(SPRITES.glob("*/sprite.json"))) if SPRITES.exists() else 0, len(problems)))
        return 1 if problems else 0
    species, _ = dexlib.load_species()
    sid = dexlib.slugify(args.pokemon)
    if sid not in {s for s, _, _ in species}:
        sys.exit("There is no Pokemon '%s' in data/species/." % sid)
    sources = {kind: getattr(args, kind) for kind in KINDS if getattr(args, kind)}
    try:
        facts = build(sid, sources, args.size, note="made by hand", grid=args.grid, detail=args.detail)
    except (SpriteError, OSError) as error:
        sys.exit("Could not make the sprites: %s" % error)
    record(sid, facts)
    print("Wrote assets/sprites/%s/ (%d colors, front %dx%d). Look at preview.png." % (sid, facts["colors"], facts["front"]["width"], facts["front"]["height"]))
    for draft in facts["drafts"]:
        print("  draft: " + draft)
    return 0


if __name__ == "__main__":
    sys.exit(main())
