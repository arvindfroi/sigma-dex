"""DS sprites (Origin HeartGold, 80x80) drawn by Qwen-Image-Edit as pixel art, not built by our renderer.

Found on 2026-10-05 after the renderer's sprites stayed messy at the DS size (faces, hands and
textures turned to specks) and the Pokemon sprite LoRAs either lost the design or the outlines:
Qwen-Image-Edit, asked to turn the creature's official-style artwork into a DS battle sprite, draws
real pixel art that keeps the design. What it needs is the size and the pixel grid, so it is shown
a rough draft of the sprite next to the artwork: our renderer's sprite (scripts/pixel_render.py),
blown up from a 96x96 canvas to 1024 (one sprite pixel = 10.7 pixels). Its picture is then read back
on that same grid, so nothing is redrawn or resized afterwards:

1. draft   our renderer's front and back (sprite_worker.ds_sprites) on the 96 canvas, shown to Qwen
           only as a grey silhouette: size, place and grid (shown the draft itself, Qwen copied its mess).
2. front   Qwen draws the front from the artwork, laid out like the draft; a few seeds.
3. snap    the picture read as 96x96 cells: 15 colours fitted over the creature (Lab k-means), each
           cell takes the colour most of it has, the white page goes; feet on the frame's bottom row.
4. pick    the front closest to its stage's size, with readable eyes, little single-pixel noise and
           the artwork's colours (sprite_quality).
5. back    Qwen draws the back from the chosen pixel front (the same creature in the same style),
           laid out like the back draft (big, cut off by the bottom edge), with the back artwork for the
           markings on its back (Chillalit's swirl); snapped the same way, cut
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
FRONT = ("Convert <image1> (the design) into %s It must be laid out like <image2>, the sprite's grey silhouette at the right "
         "size, place and pixel grid: the same size, place and outline, the same pixel size, drawn well inside it. Big "
         "clean shapes, no noise, no single-pixel speckles. Keep the "
         "creature exactly as in <image1>: its design, colors, markings, pose and face. The face exactly as designed: the same eye "
         "shape and eye color, the same mouth and expression, drawn big and clear; do not add pupils, glints, teeth or details the "
         "design does not have. Hands, claws and small parts stay readable. Plain white background, nothing else.") % STYLE
ICON_ART = ("Redraw the creature from <image1> as its tiny party menu icon from Pokemon HeartGold, as a clean illustration: "
            "a chibi version of it, the head about half of its height and drawn big, the body squashed and compact, short limbs, "
            "the whole creature facing left (turned toward the left side of the picture, three-quarter view), standing. Keep its "
            "design, colors and signature features, exaggerated and simplified so they read at 32 pixels: the face, the eyes, "
            "the most recognisable parts; small details dropped. Bold dark outlines, flat colors, one shadow tone. It fills most "
            "of the picture. Exactly one creature, plain white background, no text.")
BACK = ("<image1> is an official Pokemon battle sprite from Pokemon Diamond, Pearl and HeartGold on the Nintendo DS. Draw the "
        "same creature's back sprite: the player's own Pokemon in a DS battle, seen from behind and a little from its left, "
        "looking over its shoulder toward the upper right, so we see its back, the back of its head and its tail, at most the "
        "side of its face. Seen fairly close, its upper body and head in view, cut off flat by the bottom edge, laid out like "
        "<image2> (its grey silhouette at the right size, place and pixel grid). Big clean shapes, no noise. The same pixel art style as <image1>: the same pixel size, the same colors, a "
        "one-pixel dark outline, flat shading, no anti-aliasing. <image3> shows how its back looks: draw the markings and colors "
        "on its back as there. Plain white background, nothing else.")


def silhouette(sprite):
    """Only the draft's shape: light grey with a one-pixel dark edge. Shown the draft itself, Qwen
    copied its messy inside (2026-10-05); the shape gives size, place and grid and nothing else."""
    a = np.array(sprite.convert("RGBA"))
    solid = a[..., 3] > 0
    pad = np.pad(solid, 1)
    edge = solid & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    out = np.zeros_like(a)
    out[solid] = (214, 214, 214, 255)
    out[edge] = (90, 90, 90, 255)
    return Image.fromarray(out)


def on_canvas(sprite, path):
    """An 80x80 sprite on the 96 canvas, blown up to 1024 (what Qwen is shown)."""
    canvas = Image.new("RGB", (GRID, GRID), "white")
    canvas.paste(sprite, ((GRID - FRAME) // 2, (GRID - FRAME) // 2), sprite)
    canvas.resize((1024, 1024), Image.NEAREST).save(path)
    return path


def snap(path, colours=15, grid=GRID):
    """Qwen's picture read on the draft's grid (grid x grid cells; GRID, or coarser for an icon): colours fitted first, then each
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
    edges = np.round(np.arange(grid + 1) * 1024 / grid).astype(int)
    cells = np.full((grid, grid), colours, np.int32)
    for i in range(grid):
        for j in range(grid):
            block = index[edges[i]:edges[i + 1], edges[j]:edges[j + 1]].ravel()
            counts = np.bincount(block, minlength=colours + 1)
            cells[i, j] = colours if counts[colours] > 0.55 * block.size else int(np.argmax(counts[:colours]))
    rgb = cv2.cvtColor(centres.clip(0, 255).astype(np.uint8).reshape(-1, 1, 3), cv2.COLOR_LAB2RGB).reshape(-1, 3)
    out = np.zeros((grid, grid, 4), np.uint8)
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
    """Higher is better: covers about the stage's back area, is cut off flat at the bottom, and is
    really seen from behind - a back that shows a face (two eyes, as Erobi's first back did) is
    the front drawn again."""
    a = np.array(back)[..., 3] > 0
    if not a.any():
        return -99.0
    rows = np.nonzero(a.any(axis=1))[0]
    flat = a[rows.max()].sum() / max(1, a.any(axis=0).sum())
    eyes = sprite_quality.parts(back)["eyes"]
    return round(2 * flat - abs(a.sum() - 2100) / 1000 - (4 if eyes >= 2 else 0), 2)


def icon_frames(icon):
    """The menu icon's two animation frames, 32x64: the second is the first one pixel higher (the hop
    the party screen plays)."""
    sheet = Image.new("RGBA", (32, 64), (0, 0, 0, 0))
    sheet.alpha_composite(icon, (0, 0))
    up = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    up.alpha_composite(icon.crop((0, 1, 32, 32)), (0, 0))
    sheet.alpha_composite(up, (0, 32))
    return sheet


def make_icon(art, folder, seeds=(5, 6)):
    """The menu icon (32x32), its own drawing: menu icons all face left and are squashed, the head
    big, so it is not the battle sprite made smaller. Qwen draws a chibi icon illustration from the
    artwork (ICON_ART); our renderer makes the 28-pixel icon from it (on such a small, flat drawing
    it is clean; Qwen asked for the pixel icon itself drew it far too small or kept the guide's grey,
    2026-10-05). The one closest to 28 pixels with a readable eye and little noise wins."""
    best = None
    for seed in seeds:
        drawing = folder / ("icon_art_%d.png" % seed)
        if not drawing.exists():
            comfy.generate(ICON_ART, drawing, [art], seed=seed, quiet=True)
        with pixel_render.styled(**pixel_render.DS):
            icon = pixel_render.render(str(drawing), size=28)
        canvas = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        canvas.alpha_composite(icon, ((32 - icon.width) // 2, 32 - 1 - icon.height))
        p = sprite_quality.parts(canvas)
        if "empty" in p:
            continue
        score = -abs(max(p["height"], p["width"]) - 28) + (2 if p["eyes"] else 0) - 20 * p["noise"]
        if best is None or score > best[0]:
            best = (score, canvas)
    return best[1]


def make(raw, species_id, folder, seeds=(5, 6, 7), back_seeds=(5, 6, 7)):
    """Front and back for one attempt's artwork (raw: {"front": art, "back": art}). Writes
    front.png, back.png and icon.png in `folder` and returns ({view: path}, front score)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    k = sprite_worker.stage(species_id)
    target = sprite_worker.GAMES[4]["sizes"][k]
    # the backs are drawn at about HeartGold's median size (more of the upper body seen): the bigger
    # ones (68/77/80, 1.15x) were mostly one colour, a tail or a cape
    saved = sprite_worker.GAMES[4]
    sprite_worker.GAMES[4] = dict(saved, back_sizes=(56, 64, 70), back_areas=(1700, 2200, 2600))
    try:
        drafts = sprite_worker.ds_sprites(raw, species_id, folder / "draft_")
    finally:
        sprite_worker.GAMES[4] = saved
    guide_front = on_canvas(silhouette(Image.open(drafts["front"])), folder / "guide_front.png")
    guide_back = on_canvas(silhouette(Image.open(drafts["back"])), folder / "guide_back.png")
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
            comfy.generate(BACK, picture, [shown, guide_back, raw["back"]], seed=bseed, quiet=True)
        back = to_palette(back_frame(snap(picture)), palette)
        backs.append((back_score(back, front), bseed, back))
    back = max(backs, key=lambda b: b[0])[2]
    files = {"front": folder / "front.png", "back": folder / "back.png", "icon": folder / "icon.png"}
    front.save(files["front"])
    back.save(files["back"])
    icon = make_icon(raw["front"], folder)
    icon.save(files["icon"])
    icon_frames(icon).save(folder / "icon_frames.png")
    (folder / "picks.txt").write_text("front seeds %s -> %d; back seeds %s\n" % ([(f[1], f[0]) for f in fronts], seed, [(b[1], b[0]) for b in backs]))
    return files, score
