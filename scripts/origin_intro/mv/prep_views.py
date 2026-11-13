"""Cut Arvind's turnaround sheet into the views Hunyuan3D-2mv takes (front, left, back, right) on white.
python mv/prep_views.py SHEET.png OUTDIR
The sheet: FRONT | SIDE (facing left) | BACK | 3/4 on paper. The paper (and the soft floor shadow) goes by a flood
fill from the panel edges that stops at the black ink lines; enclosed paper-coloured pockets go too. All views share
one scale and one vertical placement (they are views of one object); each is centred on its own width.
The right view is the side view mirrored (the design is symmetric left/right)."""
import sys, os, numpy as np, cv2
from PIL import Image
from scipy import ndimage
src, out = sys.argv[1:3]; os.makedirs(out, exist_ok=True)
a = np.array(Image.open(src).convert('RGB'))
H, W, _ = a.shape
PANELS = dict(front=(0, 392), side=(405, 975), back=(1025, 1345), q34=(1345, 1834))
Y0, Y1 = 112, H                                         # below the titles
S = int(os.environ.get('SIZE', 640)); YC = int(os.environ.get('YC', 345))
paper = np.median(a[60:100, 5:60].reshape(-1, 3), 0)
def cut(x0, x1):
    p = a[Y0:Y1, x0:x1].copy()
    h, w, _ = p.shape
    blur = cv2.GaussianBlur(p, (3, 3), 0)
    mask = np.zeros((h + 2, w + 2), np.uint8)
    flags = 4 | cv2.FLOODFILL_MASK_ONLY | (255 << 8)
    d = int(os.environ.get('DIFF', 5))
    seeds = [(x, 0) for x in range(0, w, 3)] + [(x, h - 1) for x in range(0, w, 3)] + \
            [(0, y) for y in range(0, h, 3)] + [(w - 1, y) for y in range(0, h, 3)]
    for sx, sy in seeds:
        if mask[sy + 1, sx + 1]: continue
        if np.abs(blur[sy, sx].astype(int) - paper).sum() > 90: continue
        cv2.floodFill(blur, mask, (sx, sy), 0, (d, d, d), (d, d, d), flags)
    bg = mask[1:-1, 1:-1] > 0
    # enclosed pockets of paper colour (between the mast and the sails, under the belly)
    near_paper = np.abs(p.astype(int) - paper).sum(-1) < 40
    lab, n = ndimage.label(near_paper & ~bg)
    sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
    for k, sz in enumerate(sizes, 1):
        if sz > 30: bg |= lab == k
    fg = ~bg
    # the soft floor shadow (warm grey) under the feet
    ys = np.where(fg.any(1))[0]; low = np.zeros_like(fg); low[int(ys.min() + 0.7 * (ys.max() - ys.min())):] = True
    sh = np.abs(p.astype(int) - np.array([140, 129, 115])).sum(-1) < int(os.environ.get('SHADOW', 70))
    fg &= ~(sh & low)
    fg = ndimage.binary_opening(fg, np.ones((3, 3)))
    lab, n = ndimage.label(fg)
    if n:
        sizes = ndimage.sum(fg, lab, range(1, n + 1)); keep = np.isin(lab, 1 + np.where(sizes > 0.01 * sizes.max())[0])
    else: keep = fg
    rgb = np.where(keep[..., None], p, 255).astype(np.uint8)
    xs = np.where(keep.any(0))[0]
    return rgb, keep, (xs.min() + xs.max()) / 2
res = {}
for name, (x0, x1) in PANELS.items():
    rgb, keep, cx = cut(x0, x1)
    canvas = np.full((S, S, 3), 255, np.uint8)
    ox = int(round(S / 2 - cx)); oy = int(round(S / 2 - (YC - Y0)))
    h, w, _ = rgb.shape
    ys0, xs0 = max(0, -oy), max(0, -ox); ys1, xs1 = min(h, S - oy), min(w, S - ox)
    sub = rgb[ys0:ys1, xs0:xs1]; km = keep[ys0:ys1, xs0:xs1]
    reg = canvas[oy + ys0:oy + ys1, ox + xs0:ox + xs1]; reg[km] = sub[km]
    res[name] = canvas
    Image.fromarray(canvas).resize((1024, 1024), Image.LANCZOS).save(os.path.join(out, f'{name}.png'))
Image.fromarray(res['side'][:, ::-1]).resize((1024, 1024), Image.LANCZOS).save(os.path.join(out, 'side_mirror.png'))
sheet = np.concatenate([res['front'], res['side'], res['back'], res['side'][:, ::-1], res['q34']], 1)
Image.fromarray(sheet).resize((sheet.shape[1] // 2, sheet.shape[0] // 2), Image.LANCZOS).save(os.path.join(out, 'views.png'))
print('views written', list(res))
