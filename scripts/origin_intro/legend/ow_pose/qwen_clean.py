"""Qwen-Image-Edit redraws a rough cut-out puppet pose (puppet.py) as one clean field sprite in the approved sprite's design
(2026-11-17, Sabertann's and Gravriel's frames 6 and 7). Two pictures go in, both on the 64 grid blown up to 1024 on a
dark page (the white sails vanished on a white page before): <image1> the puppet pose, <image2> the approved sprite.
The answer is read back cell by cell in the approved palette (each pixel to its nearest palette colour or the page, in
Lab, then the commonest per cell). Qwen draws the figure a little smaller or lower than the puppet, so its figure is
scaled onto the puppet's bounding box first (CLAMP=1 instead keeps the puppet's exact silhouette and fills it with Qwen's
cells; that gave a mess where the two did not line up).
python qwen_clean.py PUPPET_idx.npy DESIGN_idx.npy PAL.npy OUTDIR NAME SEED...   (env POSE: the pose in words; NPAL: palette slots used)"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
PF, DF, PALF, OD, NAME = sys.argv[1:6]; SEEDS = [int(s) for s in sys.argv[6:]] or [21, 22, 23]; os.makedirs(OD, exist_ok=True)
pup = np.load(PF).astype(int); des = np.load(DF).astype(int)
NP = int(os.environ.get('NPAL', 15)); PAL = np.load(PALF).astype(float)[:NP]
PAGE = np.array([40, 44, 60.0])
def canvas(idx, path):
    P = np.vstack([PAGE, PAL]); im = Image.fromarray(P[np.clip(idx, 0, NP)].astype(np.uint8)).resize((1024, 1024), Image.NEAREST); im.save(path); return path
def lab(c):
    c = np.asarray(c, float) / 255; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]); xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116); return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
CL = lab(np.vstack([PAGE, PAL]))
def fit(a, pup):
    """Qwen's figure (everything that is not page, found by flooding the page from the border) scaled onto the puppet's
    bounding box, so the frame keeps the puppet's size and place but Qwen's own clean drawing"""
    import cv2
    page = np.sqrt(((lab(a) - CL[0]) ** 2).sum(-1)) < 9
    n, lbl = cv2.connectedComponents(page.astype(np.uint8), connectivity=4)
    border = set(np.unique(np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]]))) - {0}
    fig = ~(np.isin(lbl, list(border)) & page)
    ys, xs = np.nonzero(fig); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    py, px = np.nonzero(pup > 0); Y0, Y1, X0, X1 = py.min() * 16, (py.max() + 1) * 16, px.min() * 16, (px.max() + 1) * 16
    crop = Image.fromarray(np.where(fig[..., None], a, CL[0] * 0 + PAGE).astype(np.uint8)[y0:y1, x0:x1])
    out = np.zeros_like(a); out[...] = PAGE
    out[Y0:Y1, X0:X1] = np.asarray(crop.resize((X1 - X0, Y1 - Y0), Image.NEAREST)).astype(float)
    print('fit: figure %dx%d -> %dx%d' % (x1 - x0, y1 - y0, X1 - X0, Y1 - Y0)); return out
def read(path, pup=None):
    a = np.asarray(Image.open(path).convert('RGB').resize((1024, 1024))).astype(float)
    if pup is not None: a = fit(a, pup)
    q = ((lab(a)[..., None, :] - CL[None, None]) ** 2).sum(-1).argmin(-1)          # 0 = page, 1.. = palette
    cells = q.reshape(64, 16, 64, 16).transpose(0, 2, 1, 3).reshape(64, 64, 256)
    out = np.zeros((64, 64), int)
    for y in range(64):
        for x in range(64):
            out[y, x] = np.bincount(cells[y, x], minlength=NP + 1).argmax()
    return out
STYLE = ("an official Pokemon HeartGold and SoulSilver overworld cutscene sprite on the Nintendo DS, like Ho-Oh and Lugia when "
         "they come down to the player: pixel art on a coarse grid of big square pixels, crisp squares, no anti-aliasing, no blur, "
         "no dithering, at most 15 colors, flat color areas with one shadow tone and small highlights, a thin dark outline")
PROMPT = ("<image1> is a rough cut-and-paste pose of the creature in <image2>, made by moving pieces of its sprite; the joins "
          "are broken and some pieces are turned. Redraw <image1> as one clean finished sprite, %s, exactly in the pose, size, "
          "place and outline of <image1>, on the same grid of big pixels. Use the creature's design, colors and pixel style from "
          "<image2>. The pose: %s Mend the joins so the body is whole and natural, keep the face readable. Plain dark blue-grey "
          "background, nothing else.") % (STYLE, os.environ['POSE'])
c1 = canvas(pup, os.path.join(OD, NAME + '_puppet_1024.png')); c2 = canvas(des, os.path.join(OD, NAME + '_design_1024.png'))
for s in SEEDS:
    pic = os.path.join(OD, '%s_qwen_%d.png' % (NAME, s))
    for attempt in range(8):                                     # the Legion's sprite studio shares the GPU; ComfyUI can fall over
        if os.path.exists(pic): break
        try: comfy.generate(PROMPT, pic, [c1, c2], seed=s, quiet=True)
        except comfy.ComfyError as e:
            print('ComfyUI away, waiting (%s)' % str(e)[:60], flush=True); import time; time.sleep(90)
    if not os.path.exists(pic): continue
    inside = pup > 0
    if os.environ.get('CLAMP', '0') == '1':                     # v1: inside the puppet's silhouette, its pixels where Qwen left page
        r = read(pic); out = np.where(inside, np.where(r > 0, r, pup), 0)
    else:                                                       # default: Qwen's own figure, fitted to the puppet's box
        r = read(pic, pup); out = r
    np.save(os.path.join(OD, '%s_%d_idx.npy' % (NAME, s)), out.astype(np.uint8))
    P = np.vstack([PAGE, PAL]); Image.fromarray(P[out].astype(np.uint8)).resize((512, 512), Image.NEAREST).save(os.path.join(OD, '%s_%d_8x.png' % (NAME, s)))
    print(NAME, s, 'kept from Qwen %.0f%%' % (100 * ((r > 0) & inside).sum() / inside.sum()), flush=True)
