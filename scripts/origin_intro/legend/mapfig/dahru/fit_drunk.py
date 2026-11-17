"""Qwen's drunk Dahrugula fitted into Snorlax's place: the figure (everything not white page) cropped, scaled to the box the
sleeping Snorlax takes in its 64x64 frame (same bottom line and centre), cut to 14 colours (k-means in RGB on DS 5-bit
steps), lone pixels removed and a one-pixel dark outline round the silhouette, as Snorlax has.
python fit_drunk.py QWEN.png KABIGON.png OUT_idx.npy OUT_pal.npy PREVIEW.png   env SCALE (1.0 of Snorlax's width), FIXED=1 (Dahrugula's palette)"""
import sys, os
import numpy as np
from PIL import Image
from scipy import ndimage
from sklearn.cluster import KMeans
Q, K, OI, OP, PREV = sys.argv[1:6]
q = np.asarray(Image.open(Q).convert('RGB')).astype(float)
page = q.min(-1) > 238
lbl, n = ndimage.label(page); border = set(np.unique(np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]]))) - {0}
fig = ~np.isin(lbl, list(border)); fig = ndimage.binary_opening(fig, iterations=2)
lb, nn = ndimage.label(fig); sz = ndimage.sum(fig, lb, range(1, nn + 1)); fig = np.isin(lb, [i + 1 for i, s in enumerate(sz) if s > 0.01 * sz.max()])
ys, xs = np.nonzero(fig); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
k = np.asarray(Image.open(K).convert('RGBA')); km_ = k[..., 3] > 0; ky, kx = np.nonzero(km_)
KW, KH = kx.max() - kx.min() + 1, ky.max() - ky.min() + 1; kcx, kbot = (kx.min() + kx.max()) / 2, ky.max()
s = float(os.environ.get('SCALE', 1.0)) * (KW + 4) / (x1 - x0)
w, h = int(round((x1 - x0) * s)), int(round((y1 - y0) * s))
crop = np.dstack([q[y0:y1, x0:x1], fig[y0:y1, x0:x1] * 255]).astype(np.uint8)
small = np.asarray(Image.fromarray(crop, 'RGBA').resize((w, h), Image.BOX)).astype(float)
on = small[..., 3] > 110
cols = small[on][:, :3]
if os.environ.get('FIXED'):                                     # Dahrugula's own colours + grass + barrel, not k-means
    cen = np.array([[8, 48, 32], [0, 96, 56], [8, 128, 64], [56, 176, 88], [248, 224, 192], [248, 168, 112],
                    [240, 72, 48], [96, 64, 48], [200, 120, 64], [168, 80, 32], [72, 112, 64], [104, 144, 80], [40, 72, 40], [24, 16, 16]], float)
    def lab(c):
        c = np.asarray(c, float) / 255; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
        M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]); xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
        f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116); return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
    lab_ = ((lab(cols)[:, None] - lab(cen)[None]) ** 2).sum(-1).argmin(1)
else:
    km = KMeans(14, n_init=8, random_state=0).fit(cols); cen = (np.round(km.cluster_centers_ / 8) * 8).clip(0, 248); lab_ = km.labels_
idx = np.zeros((h, w), int); idx[on] = lab_ + 2                            # 1 = outline, 2.. = colours
for _ in range(2):
    new = idx.copy()
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if idx[y, x] < 2: continue
            nb = np.delete(idx[y - 1:y + 2, x - 1:x + 2].ravel(), 4); nb = nb[nb >= 2]
            if len(nb) >= 6 and (nb == idx[y, x]).sum() == 0: new[y, x] = np.bincount(nb).argmax()
    idx = new
out = np.zeros((64, 64), int)
oy, ox = int(kbot - h + 1), int(round(kcx - w / 2))
oy = max(1, min(oy, 63 - h)); ox = max(1, min(ox, 63 - w))
out[oy:oy + h, ox:ox + w] = idx
sil = out > 0; edge = ndimage.binary_dilation(sil) & ~sil; out[edge] = 1
pal = np.vstack([[16, 24, 16], cen])                                        # 1: Snorlax's near-black outline
np.save(OI, out.astype(np.uint8)); np.save(OP, pal.astype(int))
P = np.vstack([[0, 0, 0], pal]); BG = np.array([40, 44, 60])
kk = np.where(k[..., 3:4] > 0, k[..., :3], BG)
z = np.hstack([kk, np.full((64, 4, 3), 255), np.where(out[..., None] > 0, P[out], BG)]).astype(np.uint8)
Image.fromarray(z).resize((z.shape[1] * 6, 384), Image.NEAREST).save(PREV); print('ok', w, h, 'at', ox, oy)
