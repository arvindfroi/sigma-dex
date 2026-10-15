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


def snap(img, palette):
    """every solid colour -> the nearest palette colour (Lab)"""
    a = np.array(img.convert("RGBA")); solid = a[..., 3] > 0
    if not solid.any() or not len(palette):
        return Image.fromarray(a)
    cols, inv = np.unique(a[solid][:, :3], axis=0, return_inverse=True)
    pal = np.asarray(palette, np.uint8); d = ((lab(cols)[:, None] - lab(pal)[None]) ** 2).sum(-1)
    flat = a[solid]; flat[:, :3] = pal[d.argmin(1)][inv.ravel()]; a[solid] = flat
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


def icon_colours(icon, palettes, body_color=None, game_only=True, weight=20.0, guard=6.0):
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
    return snap(icon, palettes[best]), best
