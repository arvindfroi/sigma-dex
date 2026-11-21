r"""Post-processing for the trainer studio's pictures (2026-11-21; Arvind: "etterbehandling mangler"). The same steps as
title3d/legend/trainers/trainer_post2.py (battle, T 40) and npc_post.py (map, T 25), in the repository so the drawing PC's
worker has them. Measured against the real HGSS trainers: lone pixels median 12 %, 14-15 colours, a dark outline on most of
the edge, feet 1 px above the bottom; real map NPCs have ~4 % lone pixels.

battle(img)    80x80 after klein_follower.to_back -> <= 15 colours, lone pixels cleaned (T 40), a closed 'sel-out' outline
               (light pixels on the outside edge take a darker shade of themselves from the sprite's own palette), feet 1 px up.
overworld(img) a 512x32 sheet (16 frames) -> one shared palette of <= 15 colours, lone pixels cleaned per frame (T 25).
               No outline pass: the NPC LoRA already draws ~90 % dark edges.
to16(sheet)    the NPC LoRA's 2x4 layout (columns up, down, left, right; rows step 1, step 2) -> the game's 16 NPC frames, the
               way a real NPC sheet uses them (measured once on NPC 009 by npc_gen.py; frame k = (column, row, mirrored)).

python scripts/trainer_post.py battle|overworld IN.png OUT.png [T]
"""
import sys

import cv2
import numpy as np
from PIL import Image

import klein_follower as KF

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))
FRAMES16 = [(0, 0, False), (2, 0, False), (3, 0, True), (2, 1, False), (3, 0, False), (2, 0, True), (3, 0, False), (2, 1, True),
            (0, 1, False), (0, 0, False), (0, 1, False), (1, 0, False), (1, 1, False), (1, 0, False), (1, 1, False), (3, 0, True)]


def _lab(rgb):
    return cv2.cvtColor(np.array([[rgb]], np.uint8), cv2.COLOR_RGB2LAB)[0, 0].astype(float)


def _luma(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


def lone(a):
    """share of solid pixels whose colour none of its 4 solid neighbours has"""
    sol = a[..., 3] > 0
    iso = n = 0
    for y in range(1, a.shape[0] - 1):
        for x in range(1, a.shape[1] - 1):
            if not sol[y, x]:
                continue
            n += 1
            nb = [tuple(a[y + dy, x + dx, :3]) for dy, dx in N4 if sol[y + dy, x + dx]]
            if nb and tuple(a[y, x, :3]) not in nb:
                iso += 1
    return iso / max(n, 1)


def clean(a, T=30.0):
    """lone pixels take the closest colour among their 8 neighbours when it is within Lab dE T, repeated until nothing changes;
    the darkest colour and very bright highlights (eye glints) are left alone"""
    a = a.copy()
    H, W = a.shape[:2]
    sol = a[..., 3] > 0
    if not sol.any():
        return a
    cols = np.unique(a[sol][:, :3], axis=0)
    darkest = tuple(cols[np.argmin([_luma(c) for c in cols])])
    lab = {tuple(c): _lab(c) for c in cols}
    for _ in range(6):
        changed = 0
        new = a.copy()
        for y in range(1, H - 1):
            for x in range(1, W - 1):
                if not sol[y, x]:
                    continue
                c = tuple(a[y, x, :3])
                if c == darkest or _luma(c) > 235:
                    continue
                n4 = [tuple(a[y + dy, x + dx, :3]) for dy, dx in N4 if sol[y + dy, x + dx]]
                if not n4 or c in n4:
                    continue
                n8 = [tuple(a[y + dy, x + dx, :3]) for dy, dx in N8 if sol[y + dy, x + dx]]
                best = min(n8, key=lambda q: ((lab[q] - lab[c]) ** 2).sum())
                if np.sqrt(((lab[best] - lab[c]) ** 2).sum()) < T:
                    new[y, x, :3] = best
                    changed += 1
        a = new
        if not changed:
            break
    return a


def outline(a):
    a = a.copy()
    sol = a[..., 3] > 0
    if not sol.any():
        return a
    pad = np.pad(sol, 1)
    edge = sol & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    cols = np.unique(a[sol][:, :3], axis=0).astype(float)
    labs = np.array([_lab(c) for c in cols])
    for y, x in zip(*np.nonzero(edge)):
        c = a[y, x, :3].astype(float)
        if _luma(c) <= 110:
            continue
        t = _lab(np.clip(c * 0.5, 0, 255))
        a[y, x, :3] = cols[int(np.argmin(((labs - t) ** 2).sum(1)))]
    return a


def place(a):
    """the figure stands 1 px above the bottom edge (row 78 of 80)"""
    sol = a[..., 3] > 0
    if not sol.any():
        return a
    dy = a.shape[0] - 2 - np.nonzero(sol)[0].max()
    out = np.zeros_like(a)
    if dy > 0:
        out[dy:] = a[:-dy]
    elif dy < 0:
        out[:dy] = a[-dy:]
    else:
        out = a.copy()
    return out


def battle(img, T=40.0):
    a = np.array(KF.merge_alike(img.convert("RGBA"), 15).convert("RGBA"))
    a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
    return Image.fromarray(place(outline(clean(a, T))))


def overworld(img, T=25.0):
    a = np.array(KF.merge_alike(img.convert("RGBA"), 15).convert("RGBA"))
    a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
    out = np.zeros_like(a)
    for i in range(a.shape[1] // 32):                       # per frame, so nothing bleeds between neighbouring frames
        f = np.pad(a[:, 32 * i:32 * i + 32], ((1, 1), (1, 1), (0, 0)))
        out[:, 32 * i:32 * i + 32] = clean(f, T)[1:-1, 1:-1]
    return Image.fromarray(out)


def to16(sheet):
    sw, sh = sheet.width // 4, sheet.height // 2
    cells = [[sheet.crop((c * sw, r * sh, c * sw + sw, r * sh + sh)) for r in range(2)] for c in range(4)]
    out = Image.new("RGBA", (512, 32), (0, 0, 0, 0))
    for i, (c, r, flip) in enumerate(FRAMES16):
        f = cells[c][r]
        out.paste(f.transpose(Image.FLIP_LEFT_RIGHT) if flip else f, (32 * i, 0))
    return out


if __name__ == "__main__":
    kind, src, dst = sys.argv[1], sys.argv[2], sys.argv[3]
    t = float(sys.argv[4]) if len(sys.argv) > 4 else (40.0 if kind == "battle" else 25.0)
    im = Image.open(src)
    out = (battle if kind == "battle" else overworld)(im, t)
    out.save(dst)
    print("lone", round(lone(np.array(im.convert("RGBA"))), 3), "->", round(lone(np.array(out)), 3))
