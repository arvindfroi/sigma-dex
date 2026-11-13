"""Overlay the model render (fit_view.py) on Arvind's drawing: both cropped to their silhouettes and scaled to the
same height, side by side, plus the model's outline drawn on the drawing in red.
python overlay.py VIEWDIR OUT.png"""
import sys, numpy as np, cv2
from PIL import Image
V, OUT = sys.argv[1], sys.argv[2]
D = np.asarray(Image.open('/Users/arvind/Sigma pokemon pc port attempt/assets/concept-art/sabertann/624.webp').convert('RGB'))
keep = np.load('/Users/arvind/sigma-origin/title3d/art/keep.npy')
ys, xs = np.where(keep); dbox = (xs.min(), ys.min(), xs.max(), ys.max())
M = np.asarray(Image.open(f'{V}/shade.png').convert('RGBA'))
ma = M[..., 3] > 0
ys2, xs2 = np.where(ma); mbox = (xs2.min(), ys2.min(), xs2.max(), ys2.max())
H = 700
def crop_scale(img, box, h):
    c = img[box[1]:box[3] + 1, box[0]:box[2] + 1]
    s = h / c.shape[0]
    return cv2.resize(c, (int(c.shape[1] * s), h), interpolation=cv2.INTER_AREA), s
dc, sd = crop_scale(D, dbox, H)
mc, sm = crop_scale(M, mbox, H)
mrgb = mc[..., :3].copy(); mrgb[mc[..., 3] < 128] = 255
# outline of the model silhouette on the drawing (aligned by the left/top of the boxes, same height)
ov = dc.copy()
msk = (mc[..., 3] > 128).astype(np.uint8)
cnt, _ = cv2.findContours(msk, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cv2.drawContours(ov, cnt, -1, (230, 0, 0), 2)
W = dc.shape[1] + mrgb.shape[1] + ov.shape[1] + 40
out = np.full((H, W, 3), 255, np.uint8)
x = 0
for im in (dc, mrgb, ov):
    out[:, x:x + im.shape[1]] = im[:, :, :3]; x += im.shape[1] + 20
Image.fromarray(out).save(OUT); print('drawing box', dbox, 'model box', mbox, 'aspect d/m', round((dbox[2]-dbox[0])/(dbox[3]-dbox[1]),3), round((mbox[2]-mbox[0])/(mbox[3]-mbox[1]),3))
