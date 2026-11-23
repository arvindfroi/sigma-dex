"""Each sprite in the colours of its kind, as the real ones (2026-10-15).

Arvind: "the different sprites use different colours for the same Pokemon, and so should we; the goal is to match the style
of each sprite". Measured on the real HeartGold / hg-engine sprites of 942 species (v6cfg/colour_study.py):
  - back:     the front's palette, exactly (the DS keeps one palette for both; 100 % of the back's pixels, median)
  - follower: its own palette, close to the front's (matched colours ~10 Lab apart, a little darker, the same hues)
  - icon:     ONE of six shared 16-colour icon palettes (~9 colours used; ~25-30 % less saturated than the front)
The rules were then chosen by testing them on all the real sprites (v6cfg/palette_study.py, follower_rules.py): the real
sprite drifted the way Klein's colours drift, fixed, compared with the real one (Arvind: "something more certain and
thorough; can the PokeAPI markers help?"):
  back_colours(back, front)          every colour -> the nearest front colour. Drift 7.0 -> 0.8; the exact real back in 74 %.
                                     2026-11-23: NOT needed for Origin. Its pokepic archive has a palette for the back of
                                     its own (member 3, shiny member 7; 20 of Origin's species already differ from their
                                     front's), and a test ROM showed the back drawn from it. So a back keeps all its colours.
  follower_colours(follower, front)  every colour HALFWAY towards the nearest of the front's colours and two darker shades.
                                     Snapping all the way made a nearly right follower worse (5.8 -> 9.5): real follower
                                     colours sit ~10 from the front's. Halfway: 5.8 -> 6.1 when Klein is close, 10.6 -> 8.9
                                     when it is off (the best of the five rules tried).
  icon_colours(icon, palettes, body_color)  HeartGold has 3 icon palettes (hg-engine adds 3); which one an icon uses
                                     follows PokeAPI's body colour (green -> 3 in 46 of 49, purple -> 2 in 43 of 48, blue -> 1
                                     in 68 of 86): the body colour picks the right palette for 71 % of HeartGold's icons, the
                                     front's colours only 31 %. Tuned on 80 real Klein icons of 8 held-out mons (5 steps x 2
                                     seeds): best fit alone picks the real palette 51 % of the time; among the palettes that
                                     fit within 6 of the best, the body colour's odds (weight 20) pick it 90 %. The guard
                                     keeps a clearly wrong fit out (Bronzor is "green" in PokeAPI and went pink in palette 3).
                                     Every colour -> its nearest colour in the chosen palette. Our dex has body_color.
Nearest = in Lab, decided per distinct colour (so small details keep their own colour when the palette has one near)."""

# HeartGold's own icons (#1-493): how many of each body colour use palette 1, 2, 3 (palette_study.py)
ICON_ODDS = {"black": [13, 4, 1], "blue": [68, 17, 1], "brown": [20, 41, 12], "gray": [21, 10, 7], "green": [3, 0, 46], "pink": [24, 1, 6],
             "purple": [5, 43, 0], "red": [39, 3, 2], "white": [10, 6, 7], "yellow": [17, 9, 20]}
import json
from pathlib import Path

# HeartGold's three icon palettes (the see-through colour left out), in the order of ICON_ODDS
HG_ICON_PALETTES = [[[128, 128, 112], [184, 184, 184], [248, 248, 248], [184, 160, 64], [240, 240, 40], [208, 96, 64], [240, 144, 40], [136, 120, 248],
                     [96, 72, 200], [232, 112, 152], [248, 176, 160], [160, 192, 248], [104, 168, 152], [96, 96, 88], [64, 64, 64]],
                    [[120, 120, 120], [184, 184, 176], [248, 248, 248], [112, 112, 200], [160, 168, 240], [176, 128, 88], [232, 192, 136], [192, 168, 40],
                     [240, 240, 40], [240, 96, 80], [144, 120, 200], [192, 160, 200], [184, 40, 152], [96, 96, 88], [64, 64, 64]],
                    [[112, 112, 112], [184, 184, 184], [248, 248, 248], [120, 152, 72], [152, 200, 72], [144, 240, 72], [232, 112, 152], [240, 144, 240],
                     [184, 160, 88], [240, 224, 40], [240, 240, 168], [208, 208, 104], [224, 72, 40], [96, 96, 88], [64, 64, 64]]]

import numpy as np
from PIL import Image


def lab(rgb):
    c = np.asarray(rgb, np.float64) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def rgb_of_lab(L):
    L = np.asarray(L, np.float64)
    fy = (L[..., 0] + 16) / 116; fx = fy + L[..., 1] / 500; fz = fy - L[..., 2] / 200
    f = np.stack([fx, fy, fz], -1); xyz = np.where(f ** 3 > 0.008856, f ** 3, (f - 16 / 116) / 7.787) * np.array([0.9505, 1.0, 1.089])
    Mi = np.linalg.inv(np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]))
    c = np.clip(xyz @ Mi.T, 0, 1); c = np.where(c > 0.0031308, 1.055 * c ** (1 / 2.4) - 0.055, 12.92 * c)
    return np.clip(np.round(c * 255), 0, 255).astype(np.uint8)


def colours(img):
    """the distinct colours of the solid pixels and the share of the sprite each covers"""
    a = np.asarray(img.convert("RGBA")).reshape(-1, 4); a = a[a[:, 3] > 0][:, :3]
    if not len(a):
        return np.zeros((0, 3), np.uint8), np.zeros(0)
    c, n = np.unique(a, axis=0, return_counts=True)
    return c, n / n.sum()


def assign(cost):
    """the cheapest way to give every row its own column (rows <= columns): the Hungarian method (Kuhn-Munkres with
    potentials, O(n^2 m)). Written out here so the drawing PC needs no scipy; scripts/site_template.html has the same."""
    cost = np.asarray(cost, np.float64); n, m = cost.shape
    INF = float("inf"); u = [0.0] * (n + 1); v = [0.0] * (m + 1); p = [0] * (m + 1); way = [0] * (m + 1)
    for i in range(1, n + 1):
        p[0] = i; j0 = 0; minv = [INF] * (m + 1); used = [False] * (m + 1)
        while True:
            used[j0] = True; i0 = p[j0]; delta = INF; j1 = 0
            row = cost[i0 - 1]
            for j in range(1, m + 1):
                if not used[j]:
                    cur = row[j - 1] - u[i0] - v[j]
                    if cur < minv[j]: minv[j] = cur; way[j] = j0
                    if minv[j] < delta: delta = minv[j]; j1 = j
            for j in range(m + 1):
                if used[j]: u[p[j]] += delta; v[j] -= delta
                else: minv[j] -= delta
            j0 = j1
            if p[j0] == 0: break
        while True:
            j1 = way[j0]; p[j0] = p[j1]; j0 = j1
            if j0 == 0: break
    out = [0] * n
    for j in range(1, m + 1):
        if p[j]: out[p[j] - 1] = j - 1
    return out


# 2026-11-23, Arvind: "slik det er nå så merges den mange farger til en ... Jeg vil at alle fargene shiftes til den relative
# nabofarge UTEN at de okkuperer samme farge". Nearest-colour snapping sent several of a sprite's colours to the same palette
# colour (two greens -> one green) and lost the details. Now every colour gets a palette colour of its OWN: the cheapest
# one-to-one assignment (Lab distance), where a big area weighs more than a small detail (so details move to a free
# neighbour, big areas keep their nearest). A colour only goes to a shade of its own family (grey to grey, a colour within
# FAMILY degrees of hue), and two colours share one only when no free shade is within MERGE (Lab) more of it.
MERGE, HUE, FAMILY = 12.0, 1.0, 40.0
NEUTRAL, PALE, OUTSIDE = 12.0, 25.0, 1000.0


def family_gate(L1, L2, family=None):
    """OUTSIDE where a target is not in the source's colour family: grey stays grey, a colour stays within `family` degrees
    of hue. Within the family the cheapest free shade wins, so shades keep their own colour and their light-to-dark order."""
    family = FAMILY if family is None else family
    C1 = np.hypot(L1[:, 1], L1[:, 2]); C2 = np.hypot(L2[:, 1], L2[:, 2])
    h1 = np.degrees(np.arctan2(L1[:, 2], L1[:, 1])); h2 = np.degrees(np.arctan2(L2[:, 2], L2[:, 1]))
    dh = np.abs((h1[:, None] - h2[None] + 180) % 360 - 180)
    n1, n2, p1 = (C1 < NEUTRAL)[:, None], (C2 < NEUTRAL)[None], (C1 < PALE)[:, None]
    # a grey goes to a grey; a pale, nearly grey colour (lavender white, ice blue) may also go to a grey
    out = (n1 & ~n2) | (~p1 & n2) | (~n1 & ~n2 & (dh > family))
    return np.where(out, OUTSIDE, 0.0)


def hue_distance(L1, L2, hue=None):
    """Lab distance with the hue part weighted (LCh): with hue > 1 a shade goes to another shade of its own colour before
    it goes to a neighbouring colour"""
    hue = HUE if hue is None else hue
    C1 = np.hypot(L1[:, 1], L1[:, 2])[:, None]; C2 = np.hypot(L2[:, 1], L2[:, 2])[None]
    dL = L1[:, 0][:, None] - L2[:, 0][None]; dC = C1 - C2
    dab2 = (L1[:, 1][:, None] - L2[:, 1][None]) ** 2 + (L1[:, 2][:, None] - L2[:, 2][None]) ** 2
    dH2 = np.maximum(dab2 - dC ** 2, 0)
    return np.sqrt(dL ** 2 + dC ** 2 + hue * hue * dH2)


def distinct_map(cols, shares, palette, merge=None, hue=None, family=None):
    """for each source colour (rows of cols, RGB) the index of its palette colour"""
    merge = MERGE if merge is None else merge
    cols = np.asarray(cols, np.uint8); pal = np.asarray(palette, np.uint8); n, m = len(cols), len(pal)
    if not n or not m:
        return np.zeros(n, int)
    L1, L2 = lab(cols), lab(pal)
    d = hue_distance(L1, L2, hue) + family_gate(L1, L2, family)
    shares = np.asarray(shares, np.float64); w = 0.3 + 0.7 * np.sqrt(shares / max(shares.max(), 1e-9))
    slots = n                                                # no cap: every further taker of one colour just costs more
    # column s*m + k = colour k for its s-th taker; moving AND sharing are weighed by the area, so a big area keeps its
    # nearest colour and a small detail moves to a free neighbour rather than share
    cost = np.concatenate([(d + s * merge) * w[:, None] for s in range(slots)], 1)
    return np.array(assign(cost)) % m          # the optimum keeps shades in their light-to-dark order by itself


def snap(img, palette, distinct=False):
    """every solid colour -> the nearest palette colour (Lab), or with distinct=True its own one (distinct_map)"""
    a = np.array(img.convert("RGBA")); solid = a[..., 3] > 0
    if not solid.any() or not len(palette):
        return Image.fromarray(a)
    cols, inv, counts = np.unique(a[solid][:, :3], axis=0, return_inverse=True, return_counts=True)
    pal = np.asarray(palette, np.uint8)
    if distinct:
        pick = distinct_map(cols, counts / counts.sum(), pal)
    else:
        pick = ((lab(cols)[:, None] - lab(pal)[None]) ** 2).sum(-1).argmin(1)
    flat = a[solid]; flat[:, :3] = pal[pick][inv.ravel()]; a[solid] = flat
    return Image.fromarray(a)


def distance(img, palette, weights=None):
    """how far the sprite's colours are from a palette: the mean nearest Lab distance, weighted by area"""
    cols, w = colours(img)
    if not len(cols) or not len(palette):
        return float("inf")
    d = np.sqrt(((lab(cols)[:, None] - lab(np.asarray(palette, np.uint8))[None]) ** 2).sum(-1)).min(1)
    return float((d * w).sum())


def back_colours(back, front):
    return snap(back, colours(front)[0])


def pull(img, palette, amount=0.5):
    """every solid colour `amount` of the way towards the nearest palette colour (Lab)"""
    a = np.array(img.convert("RGBA")); solid = a[..., 3] > 0
    if not solid.any() or not len(palette):
        return Image.fromarray(a)
    cols, inv = np.unique(a[solid][:, :3], axis=0, return_inverse=True); L1, L2 = lab(cols), lab(np.asarray(palette, np.uint8))
    near = L2[((L1[:, None] - L2[None]) ** 2).sum(-1).argmin(1)]
    flat = a[solid]; flat[:, :3] = rgb_of_lab(L1 + amount * (near - L1))[inv.ravel()]; a[solid] = flat
    return Image.fromarray(a)


def follower_colours(follower, front, darker=(8.0, 16.0), amount=0.5):
    """halfway towards the nearest of the front's colours and two darker shades of each"""
    fc = colours(front)[0]
    if not len(fc):
        return follower
    L = lab(fc); shades = [fc]
    for d in darker:
        x = L.copy(); x[:, 0] = np.maximum(x[:, 0] - d, 0); shades.append(rgb_of_lab(x))
    return pull(follower, np.unique(np.concatenate(shades), axis=0), amount)


def load_icon_palettes(path, least_uses=10):
    """the shared icon palettes (colour 0 is the see-through one), the ones real icons use"""
    return [np.array(p["rgb"][1:], np.uint8) for p in json.loads(Path(path).read_text()) if p["uses"] >= least_uses]


# ---------- neighbour contrast (2026-11-23) ----------
# Arvind: "det må jo være en bedre måte ... på ikon så kan det egentlig også bli bedre". Tested with ground truth: HeartGold's
# own icons, their colours drifted the way Klein's drift, then mapped back (private benchmark in ~/sigma-origin/colourbench):
# the old way (palette by fit + body colour, every colour to its nearest) gave back 84 % of the pixels and picked the right
# palette 80 % of the time; this gives 90 % and 97 %. A colour map is chosen for the whole picture: every colour stays near
# its own (weighed by its area) AND neighbouring pixels keep their difference (direction and size), so shading and outlines
# survive without new hard edges; two shades that never touch may share a colour. The palette is the one where the picture
# survives best, plus the body colour's odds.
CONTRAST = 8.0


def picture_parts(img):
    """the distinct colours, their pixel counts, the colour index of every pixel (-1 = clear) and how often two colours
    touch (4-neighbours)"""
    a = np.array(img.convert("RGBA")); solid = a[..., 3] > 0
    cols, inv, counts = np.unique(a[solid][:, :3], axis=0, return_inverse=True, return_counts=True)
    idx = -np.ones(a.shape[:2], int); idx[solid] = inv.ravel(); n = len(cols); A = np.zeros((n, n))
    for x, y in ((idx[:, :-1], idx[:, 1:]), (idx[:-1, :], idx[1:, :])):
        m = (x >= 0) & (y >= 0) & (x != y)
        np.add.at(A, (x[m], y[m]), 1)
    return a, solid, cols, inv.ravel(), counts.astype(float), A + A.T


def contrast_map(cols, counts, A, palette, lam=None, sweeps=20):
    """(palette index per colour, energy per pixel): the colour map that keeps both the colours and the neighbour
    differences, by coordinate descent from the nearest map"""
    lam = CONTRAST if lam is None else lam
    cols = np.asarray(cols, np.uint8); X, P = lab(cols), lab(np.asarray(palette, np.uint8))
    U = counts[:, None] * np.sqrt(((X[:, None] - P[None]) ** 2).sum(-1))
    f = np.sqrt(((X[:, None] - P[None]) ** 2).sum(-1)).argmin(1)
    for _ in range(sweeps):
        changed = False
        for i in np.lexsort((cols[:, 2], cols[:, 1], cols[:, 0], -counts)):   # biggest first, ties by RGB (as on the website)
            D = (X[i] - X)[None] - (P[:, None] - P[f][None])
            c = U[i] + lam * (A[i][None] * np.sqrt((D ** 2).sum(-1))).sum(1)
            j = int(c.argmin())
            if j != f[i]: f[i] = j; changed = True
        if not changed: break
    D = (X[:, None] - X[None]) - (P[f][:, None] - P[f][None])
    e = U[np.arange(len(f)), f].sum() + lam * 0.5 * (A * np.sqrt((D ** 2).sum(-1))).sum()
    return f, float(e / max(counts.sum(), 1))


def contrast_snap(img, palette, lam=None):
    """every colour onto the palette with contrast_map (returns the picture and its energy per pixel)"""
    a, solid, cols, inv, counts, A = picture_parts(img)
    if not len(cols) or not len(palette):
        return Image.fromarray(a), 0.0
    pal = np.asarray(palette, np.uint8); f, e = contrast_map(cols, counts, A, pal, lam)
    flat = a[solid]; flat[:, :3] = pal[f][inv]; a[solid] = flat
    return Image.fromarray(a), e


def icon_colours(icon, palettes, body_color=None, prior=10.0):
    """the icon in the one of HeartGold's 3 icon palettes (ICON_ODDS order) where it survives best (contrast_map's energy)
    plus the body colour's odds; returns (icon, palette index)"""
    odds = ICON_ODDS.get(body_color); best = None
    for i in range(3):
        out, e = contrast_snap(icon, palettes[i])
        score = e - (prior * np.log((odds[i] + 1) / (sum(odds) + 3)) if odds else 0.0)
        if best is None or score < best[0]: best = (score, out, i)
    return best[1], best[2]


def icon_colours_old(icon, palettes, body_color=None, game_only=True, weight=20.0, guard=6.0):
    """among the icon palettes that fit within `guard` of the best (HeartGold's 3 only, unless game_only is False), the one
    with the best fit plus the body colour's odds; every colour -> its nearest colour in it. Returns (icon, palette index)."""
    k = 3 if game_only else len(palettes)
    fits = [distance(icon, palettes[i]) for i in range(k)]
    odds = ICON_ODDS.get(body_color)
    def score(i):
        prior = 0.0
        if odds is not None and i < 3:
            prior = -weight * np.log((odds[i] + 1) / (sum(odds) + 3))
        elif odds is not None:
            prior = -weight * np.log(1 / (sum(odds) + 3))
        return fits[i] + prior
    best = min((i for i in range(k) if fits[i] <= min(fits) + guard), key=score)
    return snap(icon, palettes[best], False), best
