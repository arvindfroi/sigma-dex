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
ICON_ART = ("Redraw the creature from <image1> as the picture for its tiny party menu icon in Pokemon HeartGold, as a clean "
            "illustration. It must be unmistakably the same creature: <image2> is its original concept art and <image3> its battle "
            "sprite; copy its design exactly from them: the same body shape and proportions (a long neck stays long, a dragon stays "
            "a dragon, a round body stays round), the same colors, every marking, pattern and part, the face with its exact eyes "
            "and mouth; nothing added or dropped, no extra arms or legs, not chibi, not cuter. Keep its own natural pose from "
            "<image3>, only simplified and drawn compact: limbs, wings and tail close to the body so the whole creature fits in a "
            "small square frame, the way Charizard or Beedrill fit in theirs, without changing its shape. Seen from slightly above "
            "in a three-quarter view, facing left toward the lower left. Bold simple shapes, flat colors, one shadow tone, the face "
            "and signature features clear. It fills the picture. Exactly one creature, plain white background, no text, no shadow.")
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


def on_canvas(sprite, path, grid=GRID):
    """An 80x80 sprite on the 96 canvas, blown up to 1024 (what Qwen is shown)."""
    canvas = Image.new("RGB", (grid, grid), "white")
    canvas.paste(sprite, ((grid - sprite.width) // 2, (grid - sprite.height) // 2), sprite)
    canvas.resize((1024, 1024), Image.NEAREST).save(path)
    return path


def snap(path, colours=15, grid=GRID, crop=True):
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
    if not crop:
        return image
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


ICON_OUTLINE = (64, 64, 64)       # HeartGold's menu icons have one dark grey outline colour (measured on its 493 icons)


def icon_palettes(rom_files=Path.home() / "sigma-origin" / "x_spike_backup" / "files"):
    """The DS's three shared icon palettes (16 colours each), read from the user's own ROM files when
    they are on this computer (never stored in the repo); None elsewhere."""
    path = Path(rom_files) / "data" / "pokeicon.narc"
    if not path.exists():
        return None
    import struct
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 24)[0]
    start, end = struct.unpack_from("<II", data, 28)
    base = 16 + struct.unpack_from("<I", data, 20)[0]
    base += struct.unpack_from("<I", data, base + 4)[0] + 8
    nclr = data[base + start:base + end]
    return [[((v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3) for v in struct.unpack_from("<16H", nclr, 40 + 32 * k)] for k in range(3)]


def in_icon_palette(a, palettes):
    """The icon in the nearest of the three shared palettes (the game can show no other colours);
    returns (pixels, palette number)."""
    solid = a[..., 3] > 0
    X = pixel_render.lab(a[..., :3].astype(np.uint8))[solid]
    best = None
    for k, P in enumerate(palettes):
        choices = np.array(P[1:14], np.float32)                  # 0 is see-through, 14 and 15 the greys of the outlines
        d = ((X[:, None] - pixel_render.lab(choices.astype(np.uint8).reshape(1, -1, 3)).reshape(-1, 3)[None]) ** 2).sum(axis=2)
        if best is None or d.min(axis=1).sum() < best[0]:
            best = (d.min(axis=1).sum(), k, choices[d.argmin(axis=1)])
    a = a.copy()
    a[solid, :3] = best[2].astype(np.uint8)
    return a, best[1]


ICON_SIDE = 26                    # every icon about this big, whatever its stage: party icons sit side by side (Arvind, 2026-10-05)


def halve(image):
    """2x2 cells to one pixel, each the colour most of its cell has (see-through if 3 of 4 are)."""
    a = np.array(image.convert("RGBA"))
    h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
    a = a[:h, :w]
    key = a[..., 0].astype(int) * 65536 + a[..., 1].astype(int) * 256 + a[..., 2]
    key[a[..., 3] == 0] = -1
    out = np.zeros((h // 2, w // 2, 4), np.uint8)
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            block = key[y:y + 2, x:x + 2].ravel()
            if (block == -1).sum() >= 3:
                continue
            values, counts = np.unique(block[block != -1], return_counts=True)
            i = list(block).index(values[np.argmax(counts)])
            out[y // 2, x // 2] = a[y + i // 2, x + i % 2]
    return Image.fromarray(out)


def make_icon(art, folder, seeds=(5, 6, 7), side=ICON_SIDE, palettes=None, concept=None, front=None):
    """The menu icon (32x32), its own drawing. HeartGold's icons (measured locally on its 493:
    about 22x21 pixels, bottom on row 29, about 9 colours, a one-colour dark grey outline, about a
    fifth of the inside single detail pixels, all in one of three shared palettes) are not the
    battle sprite made smaller: the pose is rearranged into a compact, roughly square shape, seen
    from slightly above (almost isometric), facing left. Qwen draws that icon pose as an
    illustration (ICON_ART: its own body shape and natural pose kept, only compact and seen from
    slightly above; asked for a "roughly square" rearranged pose, Qwen made balls and broken limbs);
    it is read on a grid where the creature is `side` cells and its edge pixels become the games'
    one-pixel grey outline. Chibi drawings, our renderer at this size, despeckling (it took the detail pixels
    the games keep) and outlines tinted by the colour next to them were all rejected (2026-10-05).
    Returns the icon; its palette number is in icon.info["palette"] (None: its own colours).

    By default the icon keeps its own 15 colours: forced into the three shared palettes, Bugmight's
    navy turned khaki and Waffy purple (2026-10-05). Origin's icon palette file has room for 16
    palettes and uses 3, so the export can give our mons palettes of their own (to be checked in
    the game); palettes="rom" maps to the nearest of the three instead."""
    palettes = icon_palettes() if palettes == "rom" else palettes
    best = None
    for seed in seeds:
        drawing = folder / ("icon_art_%d.png" % seed)
        if not drawing.exists():
            comfy.generate(ICON_ART, drawing, [art] + [r for r in (concept, front) if r], seed=seed, quiet=True)
        # flattened first (the drawing's soft shading made noise), read at twice the size, then halved by majority
        flat = folder / ("icon_flat_%d.png" % seed)
        if not flat.exists():
            Image.fromarray(cv2.pyrMeanShiftFiltering(np.array(Image.open(drawing).convert("RGB")), 14, 40)).save(flat)
        rgb = pixel_render.load(str(flat))
        x0, y0, x1, y1 = pixel_render.box_of(str(flat))
        grid = max(24, round(side * max(rgb.shape[:2]) / max(x1 - x0, y1 - y0)))
        icon = halve(snap(flat, colours=12, grid=2 * grid))
        icon.thumbnail((30, 30), Image.NEAREST)
        canvas = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        canvas.alpha_composite(icon, ((32 - icon.width) // 2, 30 - icon.height))
        a = np.array(canvas)
        number = None
        if palettes:
            a, number = in_icon_palette(a, palettes)
        # the outline is the silhouette's own edge pixels, one pixel, in the games' dark grey (an extra
        # ring outside, on top of the drawing's own dark edge, made it two pixels thick)
        solid = a[..., 3] > 0
        pad = np.pad(solid, 1)
        edge = solid & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
        a[edge, :3] = palettes[number][15] if palettes else ICON_OUTLINE
        # a dark line just inside it is the drawing's own outline, now doubled: it takes the colour inside it
        inner = solid & ~edge
        lum = a[..., :3].astype(int) @ [299, 587, 114] // 1000
        pin = np.pad(inner, 1)
        next_to_edge = inner & ~(np.pad(~edge, 1)[:-2, 1:-1] & np.pad(~edge, 1)[2:, 1:-1] & np.pad(~edge, 1)[1:-1, :-2] & np.pad(~edge, 1)[1:-1, 2:])
        h, w = solid.shape
        for y, x in zip(*np.nonzero(next_to_edge & (lum < 70))):
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                yy, xx = y + 2 * dy, x + 2 * dx
                if 0 <= yy < h and 0 <= xx < w and inner[yy, xx] and lum[yy, xx] >= 70 and not edge[y + dy, x + dx]:
                    a[y, x, :3] = a[yy, xx, :3]
                    break
        canvas = Image.fromarray(a)
        canvas.info["palette"] = number
        p = sprite_quality.parts(canvas)
        if "empty" in p:
            continue
        # like the battle sprite: its colours kept (fidelity against the front's artwork), the right size, an eye
        score = -abs(max(p["height"], p["width"]) - (side + 2)) + (2 if p["eyes"] else 0) + 10 * sprite_quality.fidelity(str(art), canvas)
        if best is None or score > best[0]:
            best = (score, canvas)
    return best[1]


EDIT = ("<image1> is a Pokemon battle sprite: pixel art from Pokemon Diamond, Pearl and HeartGold on the Nintendo DS, on a coarse "
        "grid of big square pixels. Change it: %s %sKeep everything else exactly as it is: the same creature, pose, size, place and "
        "outline, the same colors, the same pixel size and grid, crisp square pixels, no anti-aliasing, no blur, a one-pixel dark "
        "outline, flat shading. Plain white background, nothing else.")
EDIT_AREA = ("<image2> shows the same sprite with a red frame around the part to change: change only what is inside the red "
             "frame; everything outside it stays exactly the same. Do not draw the red frame. ")


def limit_colours(sprite, most=15, keep=None):
    """At most `most` colours: the least used colour is merged into its nearest (Lab) until it fits
    (an edit can bring new colours; the frequent ones stay as they are). Colours in `keep` (the old
    sprite's) are merged away last."""
    keep = {tuple(int(v) for v in c) for c in (keep if keep is not None else [])}
    a = np.array(sprite.convert("RGBA"))
    solid = a[..., 3] > 0
    while True:
        colours, counts = np.unique(a[solid][:, :3], axis=0, return_counts=True)
        if len(colours) <= most:
            return Image.fromarray(a)
        L = pixel_render.lab(colours.reshape(1, -1, 3).astype(np.uint8)).reshape(-1, 3)
        weight = counts.astype(float) + np.array([1e9 if tuple(int(v) for v in c) in keep else 0 for c in colours])
        rare = int(np.argmin(weight))
        d = ((L - L[rare]) ** 2).sum(axis=1)
        d[rare] = np.inf
        into = colours[int(np.argmin(d))]
        same = solid & (a[..., :3] == colours[rare]).all(axis=2)
        a[same, :3] = into


def area_cells(area, frame):
    """The marked area (fractions x0, y0, x1, y1 of the frame) as a frame-sized mask."""
    mask = np.zeros((frame, frame), bool)
    x0, x1 = sorted((float(area["x0"]), float(area["x1"])))
    y0, y1 = sorted((float(area["y0"]), float(area["y1"])))
    c0, c1 = int(np.floor(np.clip(x0, 0, 1) * frame)), int(np.ceil(np.clip(x1, 0, 1) * frame))
    r0, r1 = int(np.floor(np.clip(y0, 0, 1) * frame)), int(np.ceil(np.clip(y1, 0, 1) * frame))
    mask[r0:max(r1, r0 + 1), c0:max(c1, c0 + 1)] = True
    return mask


def edit(sprite, change, folder, area=None, seeds=(11, 12), progress=None):
    """A finished sprite changed as asked, by Qwen-Image-Edit working on the pixel art itself (not on the
    artwork, so everything that was not asked for stays). With `area`, only the cells inside it are
    taken from Qwen's picture; everything outside is the old sprite, pixel for pixel. The picture is
    read back on the sprite's own grid. Returns the new sprite (same size as the old one)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    sprite = sprite.convert("RGBA")
    frame = sprite.width
    grid = frame + max(4, frame // 5)                     # 80 -> 96 as for drawing; a little white page around it
    pad = (grid - frame) // 2
    shown = on_canvas(sprite, folder / "edit_shown.png", grid)
    refs = [shown]
    mask = None
    if area:
        mask = area_cells(area, frame)
        marked = Image.open(shown).convert("RGB")
        rows, cols = np.nonzero(mask)
        cell = 1024 / grid
        box = [(cols.min() + pad - 0.5) * cell, (rows.min() + pad - 0.5) * cell, (cols.max() + pad + 1.5) * cell, (rows.max() + pad + 1.5) * cell]
        from PIL import ImageDraw
        ImageDraw.Draw(marked).rectangle(box, outline=(230, 20, 20), width=max(3, round(cell / 3)))
        marked.save(folder / "edit_marked.png")
        refs.append(folder / "edit_marked.png")
    change = " ".join(str(change).split()).rstrip(".") + "."
    prompt = EDIT % (change, EDIT_AREA if area else "")
    old = np.array(sprite)
    tries = []
    for n, seed in enumerate(seeds):
        if progress:
            progress("changing the sprite (%d of %d)" % (n + 1, len(seeds)))
        picture = folder / ("edit_%d.png" % seed)
        if not picture.exists():
            comfy.generate(prompt, picture, refs, seed=seed, quiet=True)
        new = np.array(snap(picture, grid=grid, crop=False))[pad:pad + frame, pad:pad + frame]
        if mask is not None:
            out = old.copy()
            out[mask] = new[mask]
            changed = (np.abs(out.astype(int) - old.astype(int)).sum(axis=2) > 30)[mask].mean()
        else:
            out = new
            changed = 1.0
        result = limit_colours(Image.fromarray(out), keep=np.unique(old[old[..., 3] > 0][:, :3], axis=0) if mask is not None else None)
        p = sprite_quality.parts(result)
        noise = p.get("noise", 1.0) if "empty" not in p else 1.0
        # an edit that changed nothing in the marked area missed the point; otherwise the cleaner one wins
        tries.append((-40 * noise - (5 if changed < 0.02 else 0), seed, result))
    return max(tries, key=lambda t: t[0])[2]


def make(raw, species_id, folder, seeds=(5, 6, 7), back_seeds=(5, 6, 7), progress=None):
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
    for n, seed in enumerate(seeds):
        if progress:
            progress("front sprite %d of %d" % (n + 1, len(seeds)))
        picture = folder / ("qwen_front_%d.png" % seed)
        if not picture.exists():
            comfy.generate(FRONT, picture, [raw["front"], guide_front], seed=seed, quiet=True)
        sprite = front_frame(snap(picture))
        fronts.append((front_score(sprite, raw["front"], target), seed, sprite))
    score, seed, front = max(fronts, key=lambda f: f[0])
    shown = on_canvas(front, folder / "front_shown.png")
    palette = pixel_render.palette_of(front)
    backs = []
    for n, bseed in enumerate(back_seeds):
        if progress:
            progress("back sprite %d of %d" % (n + 1, len(back_seeds)))
        picture = folder / ("qwen_back_%d.png" % bseed)
        if not picture.exists():
            comfy.generate(BACK, picture, [shown, guide_back, raw["back"]], seed=bseed, quiet=True)
        back = to_palette(back_frame(snap(picture)), palette)
        backs.append((back_score(back, front), bseed, back))
    back = max(backs, key=lambda b: b[0])[2]
    files = {"front": folder / "front.png", "back": folder / "back.png", "icon": folder / "icon.png"}
    front.save(files["front"])
    back.save(files["back"])
    if progress:
        progress("menu icon")
    icon = make_icon(raw["front"], folder, side=ICON_SIDE, concept=raw.get("concept"), front=shown)
    icon.save(files["icon"])
    icon_frames(icon).save(folder / "icon_frames.png")
    (folder / "picks.txt").write_text("front seeds %s -> %d; back seeds %s\n" % ([(f[1], f[0]) for f in fronts], seed, [(b[1], b[0]) for b in backs]))
    return files, score
