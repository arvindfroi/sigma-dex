"""A Klein follower sheet -> the game's follower sprite (2026-10-14).

Klein draws the whole HGSS follower sheet in one picture: 4 columns (up, down, left, right) x 2 rows (step 1, step 2) of
32x32 frames at 4x (512 x 256) on flat magenta. This turns it into what the game uses:
  - the 4x4 pixel grid read back to 128 x 64 (the grid's phase found by the least spread inside the cells; the median
    colour per cell, so JPEG noise and soft edges go away),
  - magenta -> see-through (plus the magenta fringe the model leaves at the edges),
  - specks smaller than 3 pixels removed,
  - right = the left column mirrored (as in 87 % of the real sheets; the left one is the one the model gets right most),
  - at most 15 colours over the whole sheet (one 16-colour palette with the see-through one, as the DS keeps it): the two
    MOST ALIKE colours are merged first (Lab), so near-copies of one shade go and small distinct colours stay (eyes, the
    X on Metagross, a tongue). ds_pixel.limit_colours merges the rarest first, which took exactly those.
Also a walking GIF (each direction twice, step 1 / step 2) to see it move, and a preview on grass.
Usage: klein_follower.py <sheet.png|jpg> <out folder> [name]"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ds_pixel  # noqa: E402

COLS = ("up", "down", "left", "right")


def read_grid(img, scale=4):
    """The scale x scale cells read back to single pixels at the grid phase with the least spread inside the cells."""
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    best = None
    for py in range(scale):
        for px in range(scale):
            h, w = (a.shape[0] - py) // scale, (a.shape[1] - px) // scale
            blk = a[py:py + h * scale, px:px + w * scale].reshape(h, scale, w, scale, 3)
            spread = float(blk.std(axis=(1, 3)).mean())
            if best is None or spread < best[0]:
                best = (spread, py, px)
    _, py, px = best
    h, w = (a.shape[0] - py) // scale, (a.shape[1] - px) // scale
    blk = a[py:py + h * scale, px:px + w * scale].reshape(h, scale, w, scale, 3)
    inner = blk[:, 1:scale - 1, :, 1:scale - 1] if scale >= 4 else blk          # the cell's middle: no bleeding from neighbours
    out = np.median(inner.reshape(h, inner.shape[1], w, inner.shape[3], 3).transpose(0, 2, 1, 3, 4).reshape(h, w, -1, 3), axis=2)
    H, W = a.shape[0] // scale, a.shape[1] // scale
    if h != H or w != W:                                                         # phase > 0 loses a row / column: pad back
        full = np.zeros((H, W, 3), np.float32); full[..., :] = (255, 0, 255)
        full[:min(h, H), :min(w, W)] = out[:H, :W]; out = full
    return out.astype(np.uint8)


def magenta_to_clear(rgb):
    r, g, b = (rgb[..., i].astype(int) for i in range(3))
    bg = (r > 150) & (b > 150) & (g < 110) & (np.abs(r - b) < 90)               # magenta and its pinkish fringe
    a = np.dstack([rgb, np.where(bg, 0, 255).astype(np.uint8)])
    return a


def clean_fringe(a):
    """Edge pixels the model blended with the magenta (dark pinkish purple next to the background) take the colour of
    their darkest solid neighbour, i.e. the outline; a magenta body colour inside the figure is left alone."""
    r, g, b = (a[..., i].astype(int) for i in range(3))
    pink = (a[..., 3] > 0) & (r - g > 70) & (b - g > 70) & (np.abs(r - b) < 80)
    clear = a[..., 3] == 0
    near = np.zeros_like(clear)
    near[1:] |= clear[:-1]; near[:-1] |= clear[1:]; near[:, 1:] |= clear[:, :-1]; near[:, :-1] |= clear[:, 1:]
    out = a.copy()
    for y, x in zip(*np.nonzero(pink & near)):
        best = None
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ny, nx = y + dy, x + dx
                if 0 <= ny < a.shape[0] and 0 <= nx < a.shape[1] and a[ny, nx, 3] > 0 and not pink[ny, nx]:
                    v = int(a[ny, nx, :3].astype(int).sum())
                    if best is None or v < best[0]: best = (v, a[ny, nx, :3])
        if best is None: out[y, x, 3] = 0
        else: out[y, x, :3] = best[1]
    return out


def drop_specks(a, least=3):
    from collections import deque
    solid = a[..., 3] > 0
    seen = np.zeros_like(solid)
    for y, x in zip(*np.nonzero(solid)):
        if seen[y, x]:
            continue
        comp, q = [], deque([(y, x)]); seen[y, x] = True
        while q:
            cy, cx = q.popleft(); comp.append((cy, cx))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < a.shape[0] and 0 <= nx < a.shape[1] and solid[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; q.append((ny, nx))
        if len(comp) < least:
            for cy, cx in comp:
                a[cy, cx, 3] = 0
    return a


def merge_alike(sheet, most=15):
    """At most `most` colours, keeping the shading (2026-10-18; Arvind: "the backs still come out very flat ... the way we
    handle colours is not good enough"). The old way merged each colour into the more used of a close pair, so whole runs
    of shades collapsed into one flat colour (Sabertann's hull, Limulk's body). Now: a quick greedy pass down to 64,
    then Ward merging (the pair that costs least, size-weighted, into their weighted mean) down to `most`, then k-means
    over every original colour (Lab, weighted by pixels): each final colour is the mean of its shades, so light, mid and
    dark tones survive as separate colours."""
    import pixel_render
    a = np.array(sheet.convert("RGBA")); solid = a[..., 3] > 0
    if not solid.any():
        return Image.fromarray(a)
    cols, inv, counts = np.unique(a[solid][:, :3], axis=0, return_inverse=True, return_counts=True)
    if len(cols) <= most:
        return Image.fromarray(a)
    lab = pixel_render.lab(cols.reshape(1, -1, 3).astype(np.uint8)).reshape(-1, 3).astype(np.float64)
    w = counts.astype(np.float64)
    pre = np.array(merge_alike_greedy(sheet, min(64, len(cols))).convert("RGBA"))[solid][:, :3]
    groups, ginv = np.unique(pre, axis=0, return_inverse=True)
    ginv = ginv.ravel()
    g_of = np.zeros(len(cols), np.int64); g_of[inv.ravel()] = ginv          # each original colour -> its group
    k = len(groups); glab = np.zeros((k, 3)); gn = np.zeros(k)
    np.add.at(glab, g_of, lab * w[:, None]); np.add.at(gn, g_of, w); glab /= gn[:, None]
    alive = list(range(k))
    while len(alive) > most:
        L, N = glab[alive], gn[alive]
        d = ((L[:, None] - L[None]) ** 2).sum(-1) * (N[:, None] * N[None]) / (N[:, None] + N[None]); np.fill_diagonal(d, np.inf)
        i, j = np.unravel_index(np.argmin(d), d.shape); i, j = alive[i], alive[j]
        t = gn[i] + gn[j]; glab[i] = (glab[i] * gn[i] + glab[j] * gn[j]) / t; gn[i] = t; alive.remove(j)
    centres = glab[alive]
    for _ in range(25):
        label = ((lab[:, None] - centres[None]) ** 2).sum(-1).argmin(1)
        for c in range(len(centres)):
            m = label == c
            if m.any(): centres[c] = (lab[m] * w[m, None]).sum(0) / w[m].sum()
    rgb = np.zeros((len(centres), 3))
    for c in range(len(centres)):
        m = label == c
        if m.any(): rgb[c] = (cols[m] * w[m, None]).sum(0) / w[m].sum()
    flat = a[solid]; flat[:, :3] = np.clip(np.round(rgb[label[inv.ravel()]]), 0, 255).astype(np.uint8); a[solid] = flat
    return Image.fromarray(a)


def merge_alike_greedy(sheet, most=15):
    """At most `most` colours: repeatedly merge the two closest colours (Lab), the less used into the more used (the
    first pass of merge_alike; on its own it flattens shading)."""
    import pixel_render
    a = np.array(sheet.convert("RGBA")); solid = a[..., 3] > 0
    cols, inv, counts = np.unique(a[solid][:, :3], axis=0, return_inverse=True, return_counts=True)
    cols = cols.astype(np.int32); counts = counts.astype(np.int64); alive = np.ones(len(cols), bool); target = np.arange(len(cols))
    lab = pixel_render.lab(cols.reshape(1, -1, 3).astype(np.uint8)).reshape(-1, 3).astype(np.float64)
    d = ((lab[:, None] - lab[None]) ** 2).sum(-1); np.fill_diagonal(d, np.inf)
    while alive.sum() > most:
        i, j = np.unravel_index(np.argmin(d), d.shape)
        keep, drop = (i, j) if counts[i] >= counts[j] else (j, i)
        target[target == drop] = keep; counts[keep] += counts[drop]; alive[drop] = False
        d[drop, :] = np.inf; d[:, drop] = np.inf
    flat = a[solid]; flat[:, :3] = cols[target[inv.ravel()]]; a[solid] = flat
    return Image.fromarray(a)


def frame(sheet, d, k):
    c = COLS.index(d)
    return sheet.crop((c * 32, k * 32, c * 32 + 32, k * 32 + 32))


def to_game(src, mirror_right=True):
    rgb = read_grid(Image.open(src))
    a = drop_specks(clean_fringe(magenta_to_clear(rgb)))
    a[..., :3][a[..., 3] == 0] = 0
    sheet = Image.fromarray(a)
    if mirror_right:
        for k in (0, 1):
            sheet.paste(frame(sheet, "left", k).transpose(Image.FLIP_LEFT_RIGHT), (96, k * 32))
    return merge_alike(sheet, 15)


def to_icon(src):
    """Klein's icon picture (the two 32x32 frames side by side at 8x, 512 x 256) -> the game's icon: 32x64, frame 1 over
    frame 2, see-through, at most 15 colours."""
    a = drop_specks(clean_fringe(magenta_to_clear(read_grid(Image.open(src), scale=8))))
    a[..., :3][a[..., 3] == 0] = 0
    side = merge_alike(Image.fromarray(a), 15)
    icon = Image.new("RGBA", (32, 64), (0, 0, 0, 0)); icon.paste(side.crop((0, 0, 32, 32)), (0, 0)); icon.paste(side.crop((32, 0, 64, 32)), (0, 32))
    return icon


def to_back(src):
    """Klein's back picture (the 80x80 frame at 4x, 320 x 320, on magenta) -> the game's 80x80 back, see-through, 15 colours."""
    a = drop_specks(clean_fringe(magenta_to_clear(read_grid(Image.open(src), scale=4))))
    a[..., :3][a[..., 3] == 0] = 0
    return merge_alike(Image.fromarray(a), 15)


def walking_gif(sheet, out, zoom=4, ground=(120, 184, 104)):
    frames = []
    for d in ("down", "left", "up", "right"):
        for _ in range(3):
            for k in (0, 1):
                f = Image.new("RGBA", (32, 32), ground + (255,)); f.alpha_composite(frame(sheet, d, k))
                frames.append(f.convert("RGB").resize((32 * zoom, 32 * zoom), Image.NEAREST))
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=220, loop=0)


def preview(src, sheet, out, name=""):
    """The model's picture, the game sheet, and the 8 frames on grass at 4x."""
    from PIL import ImageDraw
    big = Image.open(src).convert("RGB").resize((512, 256))
    g = Image.new("RGBA", (128, 64), (120, 184, 104, 255)); g.alpha_composite(sheet)
    g = g.convert("RGB").resize((512, 256), Image.NEAREST)
    pv = Image.new("RGB", (1048, 300), "white"); d = ImageDraw.Draw(pv)
    d.text((8, 6), f"{name}  modellens bilde", fill="black"); d.text((532, 6), "som i spillet: 32x32, gjennomsiktig, 15 farger, høyre = speilet venstre", fill="black")
    pv.paste(big, (8, 26)); pv.paste(g, (528, 26)); pv.save(out)


if __name__ == "__main__":
    src, out = Path(sys.argv[1]), Path(sys.argv[2]); name = sys.argv[3] if len(sys.argv) > 3 else src.stem
    out.mkdir(parents=True, exist_ok=True)
    s = to_game(src)
    s.save(out / f"{name}_follower.png")
    walking_gif(s, out / f"{name}_walk.gif")
    preview(src, s, out / f"{name}_preview.png", name)
    print(out / f"{name}_follower.png", len(np.unique(np.asarray(s)[np.asarray(s)[..., 3] > 0][:, :3], axis=0)), "colours")
