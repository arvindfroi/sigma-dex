"""Lapper's hop as a cut-out puppet of the approved front sprite (64x42 crop), the ow_pose recipe: parts as masks, each
moved and turned about its own pivot, stacked back to front, gaps closed. Then Qwen redraws it clean (qwen_clean_hop.py).
python hop_pose.py VARIANT OUTDIR   (variants in POSES)"""
import sys, os, json, numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lapper_small2 import load_front, to_index, rgba
from scipy import ndimage
S = 96; OX, OY = 16, 34                       # the crop sits at (OX, OY) on a 96x96 canvas (room for ears and legs)
def masks(idx):
    h, w = idx.shape; yy, xx = np.mgrid[:h, :w]; on = idx > 0
    face = on & (xx >= 14) & (xx <= 24) & (yy >= 8) & (yy <= 31) & ~((xx >= 23) & (yy <= 20))
    ear_f = on & (((yy >= 9) & (yy <= 20) & (xx <= 14)) | ((yy >= 21) & (yy <= 32) & (xx <= 17))) & ~face
    ear_b = on & (yy >= 11) & (yy <= 33) & (xx >= 23) & (xx <= 37) & ~face
    tail = on & (xx >= 54) & (yy <= 24)
    legs = {}
    for name, (x0, x1) in dict(fa=(13, 27), fb=(27, 40), ha=(40, 48), hb=(48, 61)).items():
        legs[name] = on & (yy >= 32) & (xx >= x0) & (xx < x1)
    head = on & (yy <= 10)
    body = on & ~(face | ear_f | ear_b | tail | head | legs['fa'] | legs['fb'] | legs['ha'] | legs['hb'])
    return dict(face=face, ear_f=ear_f, ear_b=ear_b, tail=tail, head=head, body=body, **legs)
def move(layer, dx=0.0, dy=0.0, rot=0.0, sx=1.0, sy=1.0, pivot=(48, 48)):
    yy, xx = np.mgrid[0:S, 0:S].astype(float); px, py = pivot
    X, Y = xx - dx - px, yy - dy - py; a = np.radians(rot); c, s = np.cos(a), np.sin(a)
    Xr, Yr = c * X + s * Y, -s * X + c * Y; ix = np.round(Xr / sx + px).astype(int); iy = np.round(Yr / sy + py).astype(int)
    ok = (ix >= 0) & (ix < S) & (iy >= 0) & (iy < S); out = np.zeros((S, S), layer.dtype); out[ok] = layer[iy[ok], ix[ok]]; return out
def close_gaps(idx, it=1):
    on = idx > 0; m = ndimage.binary_fill_holes(ndimage.binary_closing(np.pad(on, it), iterations=it)[it:-it, it:-it])
    _, (iy, ix) = ndimage.distance_transform_edt(~on, return_indices=True)
    out = idx.copy(); new = m & ~on; out[new] = idx[iy[new], ix[new]]; return out
P = lambda x, y: (x + OX, y + OY)              # crop coords -> canvas
POSES = {
    # ears flare out like a bell (concept art 445, "winds up its ears"): turned out at the root and widened, still hanging
    # G: mild: ears out, nose a little up, front paws folded forward, hind paws hang back
    'G': dict(body=dict(rot=6), ear_f=dict(rot=16, sx=1.12, pivot=(12, 10)), ear_b=dict(rot=-12, sx=1.1, pivot=(30, 10)),
              fa=dict(rot=28, sy=0.85, pivot=(21, 31)), fb=dict(rot=22, sy=0.85, pivot=(32, 31)), ha=dict(rot=-15, pivot=(44, 31)),
              hb=dict(rot=-20, pivot=(53, 31)), tail=dict(rot=-25, pivot=(55, 21))),
    # H: bigger: ears well out, nose up, front legs tucked high, hind legs kicked back
    'H': dict(body=dict(rot=10), ear_f=dict(rot=26, sx=1.2, pivot=(12, 10)), ear_b=dict(rot=-20, sx=1.15, pivot=(30, 10)),
              fa=dict(rot=42, sy=0.75, pivot=(21, 31)), fb=dict(rot=34, sy=0.75, pivot=(32, 31)), ha=dict(rot=-28, pivot=(44, 31)),
              hb=dict(rot=-34, pivot=(53, 31)), tail=dict(rot=-32, pivot=(55, 21))),
    # I: stretch: body a little taller, legs hang straight and long with the paws pointing down, ears out
    # J: spring: the front well up (a diagonal from hind paws to head), front legs tucked, hind legs stretched back
    'J': dict(body=dict(rot=16), ear_f=dict(rot=24, sx=1.15, pivot=(12, 10)), ear_b=dict(rot=-20, sx=1.12, pivot=(30, 10)),
              fa=dict(rot=48, sy=0.75, pivot=(21, 31)), fb=dict(rot=40, sy=0.75, pivot=(32, 31)), ha=dict(rot=-35, sy=1.1, pivot=(44, 31)),
              hb=dict(rot=-42, sy=1.1, pivot=(53, 31)), tail=dict(rot=-30, pivot=(55, 21))),
    'I': dict(body=dict(rot=4), stretch=1.06, ear_f=dict(rot=20, sx=1.12, pivot=(12, 10)), ear_b=dict(rot=-15, sx=1.1, pivot=(30, 10)),
              fa=dict(sy=1.15, rot=8, pivot=(21, 31)), fb=dict(sy=1.15, rot=4, pivot=(32, 31)), ha=dict(sy=1.15, rot=-6, pivot=(44, 31)),
              hb=dict(sy=1.15, rot=-10, pivot=(53, 31)), tail=dict(rot=-30, pivot=(55, 21))),
}
def pose(name):
    fb = load_front(); idx, pal = to_index(fb); M = masks(idx)
    can = np.zeros((S, S), idx.dtype); can[OY:OY + idx.shape[0], OX:OX + idx.shape[1]] = idx
    def layer(m): z = np.zeros((S, S), bool); z[OY:OY + idx.shape[0], OX:OX + idx.shape[1]] = m; return np.where(z, can, 0)
    cfg = POSES[name]; bodyrot = cfg['body'].get('rot', 0); bpiv = P(34, 22)
    def place(part, extra):
        e = dict(extra); piv = P(*e.pop('pivot')) if 'pivot' in e else bpiv
        l = move(layer(M[part]), pivot=piv, **e)
        return move(l, rot=bodyrot, pivot=bpiv)          # every part rides on the body's tilt
    order = ['ear_b', 'hb', 'ha', 'tail', 'body', 'fb', 'fa', 'head', 'face', 'ear_f']
    layers = []
    for p in order:
        if p in ('body', 'head', 'face'): layers.append(move(layer(M[p]), rot=bodyrot, pivot=bpiv))
        else: layers.append(place(p, cfg.get(p, {})))
    out = np.zeros((S, S), idx.dtype)
    for l in layers: out = np.where(l > 0, l, out)
    if cfg.get('stretch'): out = move(out, sy=cfg['stretch'], pivot=P(34, 40))
    out = close_gaps(out)
    ys, xs = np.nonzero(out > 0)
    # where the nose (crop 16, 11) went: the body tilt about bpiv (forward of move's backward mapping), then the crop
    a = np.radians(bodyrot); c, s_ = np.cos(a), np.sin(a); nx, ny = P(16, 11); X, Y = nx - bpiv[0], ny - bpiv[1]
    nose = (c * X - s_ * Y + bpiv[0], s_ * X + c * Y + bpiv[1])
    if cfg.get('stretch'): nose = (nose[0], (nose[1] - P(34, 40)[1]) * cfg['stretch'] + P(34, 40)[1])
    pose.nose = (nose[0] - xs.min(), nose[1] - ys.min()); pose.pivot = (bpiv[0] - xs.min(), bpiv[1] - ys.min())
    return out[ys.min():ys.max() + 1, xs.min():xs.max() + 1], pal, M
if __name__ == '__main__':
    name, od = sys.argv[1], sys.argv[2]; os.makedirs(od, exist_ok=True)
    o, pal, M = pose(name)
    np.save(f'{od}/puppet_{name}.npy', o); Image.fromarray(rgba(o, pal)).save(f'{od}/puppet_{name}.png')
    print(name, o.shape)
