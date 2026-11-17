"""Cut-out puppet on a 64x64 indexed sprite: parts are masks of the approved sprite, each moved, turned and scaled about its
own pivot and stacked back to front (2026-11-17, frames 6 and 7 of Sabertann's and Gravriel's field sprites: the poses
must change as much as Lugia's and Ho-Oh's, so the parts move far; Qwen then redraws the rough puppet as clean pixel art).
part(idx, mask) -> layer; move(layer, dx=0, dy=0, rot=0, sx=1, sy=1, pivot=(x, y)) -> layer; stack([layers]) -> idx
Rotation in degrees, positive turns clockwise on screen (y down). Backward nearest sampling, so nothing tears."""
import numpy as np
def part(idx, mask):
    return np.where(mask, idx, 0)
def box(y0, y1, x0, x1):
    m = np.zeros((64, 64), bool); m[max(0, y0):y1, max(0, x0):x1] = True; return m
def move(layer, dx=0.0, dy=0.0, rot=0.0, sx=1.0, sy=1.0, pivot=(31.5, 31.5), size=64):
    yy, xx = np.mgrid[0:size, 0:size].astype(float); px, py = pivot
    X, Y = xx - dx - px, yy - dy - py                          # undo the move, then the turn, then the scale
    a = np.radians(rot); c, s = np.cos(a), np.sin(a)
    Xr, Yr = c * X + s * Y, -s * X + c * Y
    sxp, syp = Xr / sx + px, Yr / sy + py
    ix, iy = np.round(sxp).astype(int), np.round(syp).astype(int)
    ok = (ix >= 0) & (ix < layer.shape[1]) & (iy >= 0) & (iy < layer.shape[0])
    out = np.zeros((size, size), layer.dtype); out[ok] = layer[iy[ok], ix[ok]]; return out
def stack(layers):
    out = np.zeros_like(layers[0])
    for l in layers: out = np.where(l > 0, l, out)
    return out
def close_gaps(idx, it=2):
    """fill the gaps the moved parts left inside the figure: close the silhouette, fill its holes, give each new pixel the
    colour of the nearest old one"""
    from scipy import ndimage
    on = idx > 0; m = ndimage.binary_fill_holes(ndimage.binary_closing(np.pad(on, it), iterations=it)[it:-it, it:-it])
    _, (iy, ix) = ndimage.distance_transform_edt(~on, return_indices=True)
    out = idx.copy(); new = m & ~on; out[new] = idx[iy[new], ix[new]]; return out
def rgba(idx, pal):
    """pal: (n, 3) for indices 1..n"""
    P = np.vstack([[0, 0, 0], np.asarray(pal)[:15]]).round().astype(np.uint8)
    a = np.zeros(idx.shape + (4,), np.uint8); a[..., :3] = P[idx]; a[..., 3] = np.where(idx > 0, 255, 0); return a
