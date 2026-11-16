"""Gravriel's 7 overworld frames (LUG_OBJ01, a/0/8/1 211) from grav2d.py's pixel art at overworld size (2026-11-17).
grav2d draws the intro's Gravriel from his front view (the design exactly) with per-pixel eyes and the edge rule Arvind
asked for in the intro (no ink outline: edge pixels are the inner colour a shade darker, like Lugia's and Ho-Oh's).
Run it at overworld size in the design's own colours first:
  G2_SCALE=0.0711 G2_POSES=5 G2_SWAY=3 G2_GRADE=none G2_HARMONIZE=0 python grav/grav2d.py DIR
Lugia's frames: 1-5 the wing beat while it comes down, 6 wings folded (landed), 7 the cry (the beak open). Gravriel's:
1-5 his float cycle (the coat, beard and arms sway, the whole figure bobs a pixel or two), 6 still, 7 the cry (the eyes
flare, grav2d's 'glow' state). Frames share one framing: the figures' union, centred, feet on the bottom row.
python ow_frames.py G2DIR OUTDIR [LUGIA_SHEET.png]  -> OUTDIR/f{1..7}_idx.npy, pal.npy, sheet.png (x4)
env: SPEC ('0:stare:0,1:stare:1,2:stare:2,3:stare:1,4:stare:0,0:stare:0,2:glow:0' = pose:eyes:bob per frame)"""
import sys, os, json
import numpy as np
from PIL import Image
GD, OD = sys.argv[1:3]; LS = sys.argv[3] if len(sys.argv) > 3 else None; os.makedirs(OD, exist_ok=True)
META = json.load(open(os.path.join(GD, 'pal.json'))); PAL = np.array(META['palette'])
SPEC = [x.split(':') for x in os.environ.get('SPEC', '0:stare:0,1:stare:1,2:stare:2,3:stare:1,4:stare:0,0:stare:0,2:glow:0').split(',')]
ims = [np.asarray(Image.open(os.path.join(GD, f'p{p}_{e}.png'))).astype(np.uint8).copy() for p, e, _ in SPEC]
# the face at overworld size, drawn per pixel (grav2d's eyes need ~14 px; here an eye is 3): a heavy dark lid, white
# outside and glowing cyan toward the beak, the pale owl mask under the eyes; the cry flares the eyes. The head never
# moves in grav2d's pictures, so one template fits every frame.
I = META['index']; SC = META['scale']
if os.environ.get('FACE', '1') == '1':
    ey = int(round(213 * SC)); exl = int(round(512.5 * SC)); exr = int(round(603.5 * SC)); D, W_, C, ML, MD = 1, I['eyeW'], I['iris'], I['maskL'], I['maskD']
    for k, ((p, e, _), im) in enumerate(zip(SPEC, ims)):
        glow = e == 'glow'
        for cx, inner in ((exl, 1), (exr, -1)):
            xs3 = [cx - 1, cx, cx + 1] if inner == 1 else [cx + 1, cx, cx - 1]      # outer -> inner
            for j, x in enumerate(xs3):
                im[ey - 1, x] = C if glow else D                                    # the lid (lifted in the cry)
                im[ey, x] = W_ if (glow or j == 0) else C                           # white outer, cyan inner
                im[ey + 1, x] = ML                                                  # pale mask under the eye
        for x in range(exl - 1, exr + 2):                                           # cheeks: pale mask, not the beak
            if im[ey + 2, x] not in (I['beakL'], I['beakD']) and im[ey + 2, x] != 0: im[ey + 2, x] = MD
U = np.zeros_like(ims[0], bool)
for im in ims: U |= im > 0
ys, xs = np.nonzero(U); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
w, h = x1 - x0, y1 - y0; assert w <= 64 and h <= 62, (w, h)   # 2 rows left for the bob
ox = (64 - w) // 2; out = []
for (p, e, bob), im in zip(SPEC, ims):
    f = np.zeros((64, 64), np.uint8); oy = 64 - h - int(bob)              # feet on the bottom row; bob lifts him
    f[oy:oy + h, ox:ox + w] = im[y0:y1, x0:x1]; out.append(f)
# readability on the dark cave water: the darkest colours are lifted a little (hue kept), and the silhouette's edge takes
# the ghost green of his film outline (Arvind chose it for the film: the same green as his see-through form). It uses
# grav2d's unused 'rim' slot.
PAL = PAL.astype(float)
LIFT = float(os.environ.get('LIFT', 52))
for i in range(1, len(PAL)):
    l_ = PAL[i] @ np.array([0.3, 0.55, 0.15])
    if 0 < l_ < LIFT: PAL[i] = PAL[i] * (LIFT / l_) ** 0.6
EDGE = os.environ.get('EDGE', '96,176,140')
if EDGE:
    PAL[I['rim']] = [float(v) for v in EDGE.split(',')]
    for f in out:
        s_ = f > 0; pd = np.pad(s_, 1); edge = s_ & ~(pd[:-2, 1:-1] & pd[2:, 1:-1] & pd[1:-1, :-2] & pd[1:-1, 2:]); f[edge] = I['rim']
PAL = (np.round(PAL / 8) * 8).clip(0, 248).astype(int)
for k, f in enumerate(out): np.save(os.path.join(OD, f'f{k + 1}_idx.npy'), f)
np.save(os.path.join(OD, 'pal.npy'), PAL[1:16])
BG = np.array([40, 44, 60]); row = np.full((64, 7 * 68, 3), 255)
for k, f in enumerate(out): row[:, k * 68:k * 68 + 64] = np.where(f[..., None] > 0, PAL[f], BG)
sh = Image.fromarray(row.astype(np.uint8)).resize((row.shape[1] * 4, 256), Image.NEAREST)
if LS:
    l = Image.open(LS).convert('RGB'); z = Image.new('RGB', (max(l.width, sh.width), l.height + sh.height + 8), 'white'); z.paste(l, (0, 0)); z.paste(sh, (0, l.height + 8)); sh = z
sh.save(os.path.join(OD, 'sheet.png')); print('ok', OD, 'figure', w, 'x', h, 'colours', len(np.unique(np.concatenate([f.ravel() for f in out]))) - 1)
