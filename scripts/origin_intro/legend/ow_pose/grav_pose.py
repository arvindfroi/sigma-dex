"""Gravriel's frames 6 (anticipation) and 7 (the cry) as cut-out puppets of the approved field sprite (frames_v2 base), posed
far enough to match Lugia's folded and spread wings (Arvind 2026-11-17).
  6, the wind-up: he wraps himself in his coat like Lugia folding its wings: both arms swing down and cross in front of
     his chest (the cutlass hangs down across him), the coat draws in narrow, the head bows so the hat tips down
  7, the cry: everything thrown open: both arms swing up and out (the cutlass raised high), the coat flares wide, the
     head lifts; the green ghost flash (as frame 7 of v5) is added after Qwen's redraw
The arms are only moved in these two frames (the float loop 1-5 keeps them still: "he should not flap his arms").
python grav_pose.py BASE_idx.npy PAL.npy OUTDIR  -> anticip_idx.npy, roar_idx.npy, *.png"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from puppet import part, box, move, stack, rgba, close_gaps
BF, PF, OD = sys.argv[1:4]; os.makedirs(OD, exist_ok=True)
base = np.load(BF).astype(int); PAL = np.load(PF); on = base > 0
E = lambda k, d: float(os.environ.get(k, d))
armL = box(20, 37, 0, 22) & on; armR = box(20, 37, 46, 64) & on
head = box(0, 17, 0, 64) & on
hem = box(44, 64, 0, 64) & on
body = on & ~armL & ~armR & ~head & ~hem
L, R, H, M, B = (part(base, m) for m in (armL, armR, head, hem, body))
SL, SR = (22, 24), (45, 24)                                     # the shoulders
# 6: wrap
a6 = close_gaps(stack([move(M, sx=E('HEM6', 0.8), dy=-2, pivot=(31.5, 44)), move(B, sx=0.92, pivot=(31.5, 30)),
                       move(H, dy=E('BOW', 2)),
                       move(L, dx=E('LX6', 7), dy=E('LY6', 2), rot=-E('ARM6', 70), pivot=SL),
                       move(R, dx=-E('LX6', 7), dy=E('LY6', 2), rot=E('ARM6', 70), pivot=SR)]))
# 7: thrown open
a7 = close_gaps(stack([move(M, sx=E('HEM7', 1.15), pivot=(31.5, 44)), B, move(H, dy=-1),
                       move(L, dx=-1, dy=-1, rot=E('ARM7', 40), pivot=SL),
                       move(R, dx=1, dy=-1, rot=-E('ARM7', 40), pivot=SR)]))
for name, a in (('anticip', a6), ('roar', a7), ('rest', base)):
    np.save(os.path.join(OD, name + '_idx.npy'), a.astype(np.uint8))
    im = Image.fromarray(rgba(a, PAL)); im.save(os.path.join(OD, name + '.png'))
    bg = Image.new('RGBA', im.size, (40, 44, 60, 255)); bg.alpha_composite(im); bg.convert('RGB').resize((512, 512), Image.NEAREST).save(os.path.join(OD, name + '_8x.png'))
print('ok', OD)
