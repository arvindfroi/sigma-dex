"""Index-space downscale of Lapper's front sprite: each target pixel takes the colour covering most of its area
(dark outline colours win only with a clear share), then despeckle and a closed 1-px outline."""
import numpy as np
from PIL import Image, ImageDraw
from collections import Counter
S = '/Users/arvind/sigma-origin/title3d/legend/oak/lapper_src/'
def load_front():
    a = np.array(Image.open(S + 'front.png').convert('RGBA'))
    ys, xs = np.nonzero(a[..., 3] > 0); return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
def to_index(a):
    cols = sorted({tuple(int(v) for v in p[:3]) for p in a[a[..., 3] > 0]}, key=lambda c: sum(c))
    lut = {c: i + 1 for i, c in enumerate(cols)}
    idx = np.zeros(a.shape[:2], np.int16)
    for y, x in zip(*np.nonzero(a[..., 3] > 0)): idx[y, x] = lut[tuple(int(v) for v in a[y, x, :3])]
    return idx, [(0, 0, 0)] + cols
def down(idx, W, H, dark=(1, 2), dark_share=0.42, alpha_share=0.5, phase=(0.0, 0.0)):
    h, w = idx.shape; sx, sy = w / W, h / H; n = idx.max() + 1
    out = np.zeros((H, W), np.int16)
    for Y in range(H):
        for X in range(W):
            x0, x1 = X * sx + phase[0], (X + 1) * sx + phase[0]; y0, y1 = Y * sy + phase[1], (Y + 1) * sy + phase[1]
            wts = np.zeros(n)
            for yy in range(int(np.floor(y0)), int(np.ceil(y1))):
                if yy < 0 or yy >= h: continue
                fy = min(y1, yy + 1) - max(y0, yy)
                for xx in range(int(np.floor(x0)), int(np.ceil(x1))):
                    if xx < 0 or xx >= w: continue
                    fx = min(x1, xx + 1) - max(x0, xx); wts[idx[yy, xx]] += fx * fy
            tot = wts.sum()
            if tot == 0 or wts[0] / tot > alpha_share: continue
            wts[0] = 0
            d = sum(wts[k] for k in dark if k < n); 
            if d / wts.sum() >= dark_share: out[Y, X] = max(dark, key=lambda k: wts[k] if k < n else -1); continue
            for k in dark:
                if k < n: wts[k] = 0
            out[Y, X] = wts.argmax() if wts.sum() > 0 else dark[0]
    return out
def despeckle(o, keep=()):
    o = o.copy(); H, W = o.shape
    for _ in range(2):
        for y in range(1, H - 1):
            for x in range(1, W - 1):
                v = o[y, x]
                if v == 0 or v in keep: continue
                nb = [o[y - 1, x], o[y + 1, x], o[y, x - 1], o[y, x + 1]]
                if all(n != v for n in nb) and all(n != 0 for n in nb):
                    c = Counter(nb).most_common(1)[0]
                    if c[1] >= 3: o[y, x] = c[0]
    return o
def outline(o, col=1):
    m = o > 0; e = np.zeros_like(m)
    e[1:] |= ~m[:-1]; e[:-1] |= ~m[1:]; e[:, 1:] |= ~m[:, :-1]; e[:, :-1] |= ~m[:, 1:]
    e[0] = True; e[-1] = True; e[:, 0] = True; e[:, -1] = True
    o = o.copy(); o[m & e] = col; return o
def rgba(o, pal):
    a = np.zeros(o.shape + (4,), np.uint8)
    for k, c in enumerate(pal):
        if k: a[o == k, :3] = c; a[o == k, 3] = 255
    return a
if __name__ == '__main__':
    fb = load_front(); idx, pal = to_index(fb)
    print('palette', pal)
    outs = []
    for W in (46, 47, 48):
        H = round(fb.shape[0] * W / fb.shape[1])
        for ph in ((0, 0), (0.35, 0.35)):
            o = down(idx, W, H, phase=ph); o2 = outline(despeckle(o))
            outs.append(('W%d ph%.2f' % (W, ph[0]), rgba(o2, pal)))
    sc = 6; pad = 8
    Wt = sum(o.shape[1] * sc + pad for _, o in outs); Ht = max(o.shape[0] for _, o in outs) * sc + 20
    sheet = Image.new('RGBA', (Wt, Ht), (247, 214, 140, 255)); d = ImageDraw.Draw(sheet); x = 0
    for name, o in outs:
        im = Image.fromarray(o).resize((o.shape[1] * sc, o.shape[0] * sc), Image.NEAREST); sheet.alpha_composite(im, (x, 0)); d.text((x, Ht - 14), name, fill='black'); x += im.width + pad
        Image.fromarray(o).save('tries/idx_' + name.replace(' ', '_') + '.png')
    sheet.save('tries/sheet_v1.png'); print(sheet.size)
