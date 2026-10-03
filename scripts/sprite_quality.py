"""Automatic quality check for a 64x64 sprite: a sieve for technical faults, not a judge of design.

score(image) gives a number (higher is better) and its parts: lone pixels (mud), busy colour
changes (noisy texture), how much of the silhouette has a dark outline, and whether there is a
dark pixel next to a glint in the upper part (an eye). Tested on 2026-10-03: the two sprites the
group liked ranked in the top four of 19, the muddy ones at the bottom; it cannot tell a wrong
design from a right one, so people still choose. Used by the sprite worker to drop the worst half.
"""
import numpy as np, cv2
from PIL import Image

def parts(img, view="front"):
    a = np.array(img.convert("RGBA")); op = a[..., 3] >= 128
    if not op.any(): return {"empty": 1}
    rgb = a[..., :3].astype(int); lum = rgb @ [0.299, 0.587, 0.114]
    key = rgb[..., 0] * 65536 + rgb[..., 1] * 256 + rgb[..., 2]
    ys, xs = np.nonzero(op); top, bottom, left, right = ys.min(), ys.max(), xs.min(), xs.max()
    h, w = bottom - top + 1, right - left + 1
    # noise: opaque pixels whose colour matches none of their 4 neighbours (inside the drawing)
    pad = np.pad(key, 1, constant_values=-1); padop = np.pad(op, 1)
    same = sum((pad[1 + dy:pad.shape[0] - 1 + dy, 1 + dx:pad.shape[1] - 1 + dx] == key) for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)))
    inside = op & padop[:-2, 1:-1] & padop[2:, 1:-1] & padop[1:-1, :-2] & padop[1:-1, 2:]
    noise = (inside & (same == 0)).sum() / max(1, inside.sum())
    # outline: silhouette edge pixels that are dark
    edge = op & ~inside
    outline = (lum[edge] < 90).mean() if edge.any() else 0
    # eyes: a dark pixel touching a very light pixel, in the upper 60% of the drawing (pupil + glint)
    dark = op & (lum < 60); light = op & (lum > 215)
    near_light = cv2.dilate(light.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    region = np.zeros_like(op); region[top:top + int(h * 0.6) + 1] = True
    eyes = (dark & near_light & region).sum()
    # flatness: number of distinct colours and colour changes per pixel (busy shading)
    colours = len(np.unique(key[op]))
    changes = ((key[:, 1:] != key[:, :-1]) & op[:, 1:] & op[:, :-1]).sum() / max(1, op.sum())
    return {"noise": float(noise), "outline": float(outline), "eyes": int(eyes), "colours": colours, "busy": float(changes), "height": int(h), "width": int(w)}

def score(img, view="front", target=None):
    p = parts(img, view)
    if "empty" in p: return -99, p
    s = 0.0
    s -= 40 * p["noise"]                       # lone pixels look like mud
    s -= 6 * max(0, p["busy"] - 0.35)          # too many colour changes = noisy texture
    s += 3 * p["outline"]                      # a clear outline
    if view == "front": s += 2 if p["eyes"] >= 2 else (1 if p["eyes"] >= 1 else -2)
    if target: s -= 0.08 * abs(max(p["height"], p["width"]) - target)
    return round(s, 2), p
