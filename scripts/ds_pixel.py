"""DS sprites (Origin HeartGold, 80x80) drawn by Qwen-Image-Edit as pixel art, not built by our renderer.

Found on 2026-10-05 after the renderer's sprites stayed messy at the DS size (faces, hands and
textures turned to specks) and the Pokemon sprite LoRAs either lost the design or the outlines:
Qwen-Image-Edit, asked to turn the creature's official-style artwork into a DS battle sprite, draws
real pixel art that keeps the design. What it needs is the size and the pixel grid, so it is shown
a rough draft of the sprite next to the artwork: our renderer's sprite (scripts/pixel_render.py),
blown up from a 96x96 canvas to 1024 (one sprite pixel = 10.7 pixels). Its picture is then read back
on that same grid, so nothing is redrawn or resized afterwards:

1. draft   our renderer's front and back (sprite_worker.ds_sprites) on the 96 canvas: size and place.
2. front   Qwen draws the front from the artwork, laid out like the draft; a few seeds.
3. snap    the picture read as 96x96 cells: 15 colours fitted over the creature (Lab k-means), each
           cell takes the colour most of it has, the white page goes; feet on the frame's bottom row.
4. pick    the front closest to its stage's size, with readable eyes, little single-pixel noise and
           the artwork's colours (sprite_quality).
5. back    Qwen draws the back from the chosen pixel front (the same creature in the same style),
           laid out like the back draft (big, cut off by the bottom edge); snapped the same way, cut
           to the frame on the tail side, and given the front's colours.

All pictures are made from our own concept art; no game sprites are shown to the model.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comfy
import pixel_render
import sprite_quality
import sprite_worker

GRID = 96                    # the draft's canvas (the 80 frame with 8 pixels around it)
FRAME = 80
STYLE = ("an official Pokemon battle sprite from Pokemon Diamond, Pearl, Platinum and HeartGold on the Nintendo DS: pixel art "
         "on a coarse grid of big square pixels, each pixel a crisp square, no anti-aliasing, no blur, no dithering, a limited "
         "palette of at most 15 colors. A one-pixel dark outline around the creature, darker on the lower right; flat color "
         "areas with one shadow tone and small highlights, light from the upper left.")
FRONT = ("Convert <image1> (the design) into %s It must be laid out like <image2>, a rough draft of the sprite at the right "
         "size, place and pixel grid: the same size and place, the same pixel size, but cleaned up and drawn well. Keep the "
         "creature exactly as in <image1>: its design, colors, pose, face and expression. Eyes are clear: a dark pupil with a "
         "one-pixel white glint. Hands, claws and small parts stay readable. Plain white background, nothing else.") % STYLE
BACK = ("<image1> is an official Pokemon battle sprite from Pokemon Diamond, Pearl and HeartGold on the Nintendo DS. Draw the "
        "same creature's back sprite: the player's own Pokemon in a DS battle, seen from behind and a little from its left, "
        "looking over its shoulder toward the upper right, so we see its back, the back of its head and its tail, at most the "
        "side of its face. Big and close, cut off flat by the bottom edge, laid out like <image2> (a rough draft of the back at "
        "the right size, place and pixel grid). The same pixel art style as <image1>: the same pixel size, the same colors, a "
        "one-pixel dark outline, flat shading, no anti-aliasing. Plain white background, nothing else.")


def on_canvas(sprite, path):
    """An 80x80 sprite on the 96 canvas, blown up to 1024 (what Qwen is shown)."""
    canvas = Image.new("RGB", (GRID, GRID), "white")
    canvas.paste(sprite, ((GRID - FRAME) // 2, (GRID - FRAME) // 2), sprite)
    canvas.resize((1024, 1024), Image.NEAREST).save(path)
    return path


def snap(path, colours=15):
    """Qwen's picture read on the draft's grid (GRID x GRID cells): colours fitted first, then each
    cell takes its commonest colour; a cell is see-through when most of it is the white page
    connected to the border. Returns the creature cropped to its own size (RGBA)."""
    a = np.array(Image.open(path).convert("RGB").resize((1024, 1024)))
    L = pixel_render.lab(a.astype(np.float32))
    page = a.min(axis=2) > 232
    n, lbl = cv2.connectedComponents(page.astype(np.uint8), connectivity=4)
    border = set(np.unique(np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]]))) - {0}
    outside = np.isin(lbl, list(border)) & page
    cv2.setRNGSeed(1)
    _, _, centres = cv2.kmeans(L[~outside][::7].astype(np.float32), colours, None,
                               (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.2), 4, cv2.KMEANS_PP_CENTERS)
    index = ((L[..., None, :] - centres[None, None]) ** 2).sum(axis=3).argmin(axis=2)
    index[outside] = colours
    edges = np.round(np.arange(GRID + 1) * 1024 / GRID).astype(int)
    cells = np.full((GRID, GRID), colours, np.int32)
    for i in range(GRID):
        for j in range(GRID):
            block = index[edges[i]:edges[i + 1], edges[j]:edges[j + 1]].ravel()
            counts = np.bincount(block, minlength=colours + 1)
            cells[i, j] = colours if counts[colours] > 0.55 * block.size else int(np.argmax(counts[:colours]))
    rgb = cv2.cvtColor(centres.clip(0, 255).astype(np.uint8).reshape(-1, 1, 3), cv2.COLOR_LAB2RGB).reshape(-1, 3)
    out = np.zeros((GRID, GRID, 4), np.uint8)
    solid = cells < colours
    out[solid, :3] = rgb[cells[solid]]
    out[solid, 3] = 255
    image = pixel_render.drop_specks(Image.fromarray(out))
    box = image.getbbox()
    return image.crop(box) if box else image


def front_frame(sprite):
    """The front on the 80 frame, centred, feet on the bottom row (cut to the frame if bigger)."""
    if sprite.width > FRAME:
        left = (sprite.width - FRAME) // 2
        sprite = sprite.crop((left, 0, left + FRAME, sprite.height))
    if sprite.height > FRAME:
        sprite = sprite.crop((0, sprite.height - FRAME, sprite.width, sprite.height))
    return sprite_worker.on_frame(sprite, FRAME)


def back_frame(sprite):
    """The back on the 80 frame: cut off flat by the bottom edge; if wider, the side away from the head is cut."""
    alpha = np.array(sprite)[..., 3] > 0
    if sprite.height > FRAME:
        sprite, alpha = sprite.crop((0, 0, sprite.width, FRAME)), alpha[:FRAME]
    if sprite.width > FRAME:
        rows = np.nonzero(alpha.any(axis=1))[0]
        cols = np.nonzero(alpha[rows[0]:rows[0] + max(1, len(rows) // 3)].any(axis=0))[0]
        left = cols.max() + 2 - FRAME if cols.mean() > sprite.width / 2 else cols.min() - 2
        left = int(np.clip(left, 0, sprite.width - FRAME))
        sprite = sprite.crop((left, 0, left + FRAME, sprite.height))
    return sprite_worker.on_frame(sprite, FRAME)


def to_palette(sprite, palette):
    """Every colour of `sprite` replaced by the nearest of `palette` (the back takes the front's)."""
    a = np.array(sprite.convert("RGBA"))
    solid = a[..., 3] > 0
    if not solid.any():
        return sprite
    P = np.array(palette, np.float32)
    PL = pixel_render.lab(P.reshape(1, -1, 3).astype(np.uint8)).reshape(-1, 3)
    X = pixel_render.lab(a[..., :3].astype(np.uint8))[solid]
    a[solid, :3] = P[((X[:, None] - PL[None]) ** 2).sum(axis=2).argmin(axis=1)].astype(np.uint8)
    return Image.fromarray(a)


def front_score(sprite, art, target):
    """Higher is better: the stage's size, readable eyes, little noise, the artwork's colours kept."""
    p = sprite_quality.parts(sprite)
    if "empty" in p:
        return -99.0
    side = max(p["height"], p["width"])
    eyes = 2 if p["eyes"] >= 2 else 0 if p["eyes"] else -3
    return round(-0.15 * abs(side - target) - 40 * p["noise"] + eyes + 10 * sprite_quality.fidelity(str(art), sprite), 2)


def back_score(back, front):
    """Higher is better: covers about the stage's back area and is cut off flat at the bottom."""
    a = np.array(back)[..., 3] > 0
    if not a.any():
        return -99.0
    rows = np.nonzero(a.any(axis=1))[0]
    flat = a[rows.max()].sum() / max(1, a.any(axis=0).sum())
    return round(2 * flat - abs(a.sum() - 2600) / 1000, 2)


def make(raw, species_id, folder, seeds=(5, 6, 7), back_seeds=(5, 6)):
    """Front and back for one attempt's artwork (raw: {"front": art, "back": art}). Writes
    front.png, back.png and icon.png in `folder` and returns ({view: path}, front score)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    k = sprite_worker.stage(species_id)
    target = sprite_worker.GAMES[4]["sizes"][k]
    drafts = sprite_worker.ds_sprites(raw, species_id, folder / "draft_")
    guide_front = on_canvas(Image.open(drafts["front"]).convert("RGBA"), folder / "guide_front.png")
    guide_back = on_canvas(Image.open(drafts["back"]).convert("RGBA"), folder / "guide_back.png")
    fronts = []
    for seed in seeds:
        picture = folder / ("qwen_front_%d.png" % seed)
        if not picture.exists():
            comfy.generate(FRONT, picture, [raw["front"], guide_front], seed=seed, quiet=True)
        sprite = front_frame(snap(picture))
        fronts.append((front_score(sprite, raw["front"], target), seed, sprite))
    score, seed, front = max(fronts, key=lambda f: f[0])
    shown = on_canvas(front, folder / "front_shown.png")
    palette = pixel_render.palette_of(front)
    backs = []
    for bseed in back_seeds:
        picture = folder / ("qwen_back_%d.png" % bseed)
        if not picture.exists():
            comfy.generate(BACK, picture, [shown, guide_back], seed=bseed, quiet=True)
        back = to_palette(back_frame(snap(picture)), palette)
        backs.append((back_score(back, front), bseed, back))
    back = max(backs, key=lambda b: b[0])[2]
    files = {"front": folder / "front.png", "back": folder / "back.png", "icon": folder / "icon.png"}
    front.save(files["front"])
    back.save(files["back"])
    pixel_render.render(str(raw["front"]), size=28).save(files["icon"])          # the icon is still the renderer's
    (folder / "picks.txt").write_text("front seeds %s -> %d; back seeds %s\n" % ([(f[1], f[0]) for f in fronts], seed, [(b[1], b[0]) for b in backs]))
    return files, score
