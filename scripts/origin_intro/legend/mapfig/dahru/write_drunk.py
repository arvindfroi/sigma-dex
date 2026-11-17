"""Write drunk Dahrugula into Snorlax's place (a/0/8/1 194 KABIGON, one 64x64 4-bpp texture + one palette, in place).
The chosen grid drawing (gen_drunk2.py, seed 4) lost its X eyes in the read-back, so two dark X marks are drawn back in
on the face (each 3x3: corners and centre), where Qwen's picture has them.
python write_drunk.py IDX.npy PAL.npy A081_IN A081_OUT PREVIEW.png"""
import sys, os
sys.path.insert(0, os.path.expanduser('~/sigma-origin/title3d')); sys.path.insert(0, os.path.expanduser('~/sigma-origin/lw'))
import numpy as np
from PIL import Image
from narc import unpack
import btx
IDX, PALF, IN, OUT, PREV = sys.argv[1:6]
idx = np.load(IDX).astype(int); pal = np.load(PALF).astype(int)
DARK = int(np.argmin(pal @ np.array([0.3, 0.55, 0.15]))) + 1
for cx, cy in ((43, 44), (47, 46)):
    for dx, dy in ((-1, -1), (1, -1), (0, 0), (-1, 1), (1, 1)): idx[cy + dy, cx + dx] = DARK
raw = open(IN, 'rb').read(); F = unpack(raw); d = F[194]
t, to, ts, po, ps = btx.parts(d); assert ts == 2048, ts
P16 = [(0, 0, 0)] + [tuple(int(v) for v in c) for c in pal] + [(0, 0, 0)] * (15 - len(pal))
new = btx.encode(d, idx.astype(np.uint8), P16); assert len(new) == len(d)
ro = raw.find(d); assert raw.count(d) == 1
open(OUT, 'wb').write(raw[:ro] + new + raw[ro + len(new):])
P = np.vstack([[40, 44, 60], pal]).astype(np.uint8)
Image.fromarray(P[idx]).resize((384, 384), Image.NEAREST).save(PREV); print('ok', OUT)
