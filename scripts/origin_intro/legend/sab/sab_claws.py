"""Sabertann's raised paw in the cry frame: the claws white like his other claws, not gold (Arvind 2026-11-17: "the only
thing is that Sabertann does not have gold claws"). Qwen's paw edit (ow_pose/paw_edit.py seed 31) drew gold claw tips; the
gold band at the wrist (rows 51-52) stays, as on his standing legs. In the claw box the gold and orange go to the claws'
white and beige-grey (the standing paws' claws are white 15 shaded with beige-grey 6).
python sab_claws.py IN_DIR OUT_DIR  (frames 1-6 copied, frame 7 fixed)   env BOX 'y0,y1,x0,x1' (38,47,7,28)"""
import sys, os, shutil
import numpy as np
from PIL import Image
ID, OD = sys.argv[1:3]; os.makedirs(OD, exist_ok=True)
for k in range(1, 7): shutil.copy(os.path.join(ID, f'f{k}_idx.npy'), OD)
f = np.load(os.path.join(ID, 'f7_idx.npy')).astype(int)
y0, y1, x0, x1 = (int(v) for v in os.environ.get('BOX', '38,47,7,28').split(','))
MAP = {14: 15, 13: 15, 12: 15, 10: 6, 8: 6}                    # yellow, gold, cream -> white; orange, brown -> beige-grey
b = f[y0:y1, x0:x1]; n = 0
for a, c in MAP.items(): n += int((b == a).sum()); b[b == a] = c
np.save(os.path.join(OD, 'f7_idx.npy'), f.astype(np.uint8)); print('recoloured', n, 'claw pixels')
H = os.path.dirname(os.path.abspath(__file__)); P = np.vstack([[0, 0, 0], np.load(os.path.join(H, 'pxd_2_pal.npy'))]); BG = np.array([40, 44, 60])
old = np.load(os.path.join(ID, 'f7_idx.npy'))
row = np.concatenate([np.pad(np.where(x[..., None] > 0, P[x], BG), ((2, 2), (2, 2), (0, 0)), constant_values=255) for x in (old, f)], 1).astype(np.uint8)
Image.fromarray(row).resize((row.shape[1] * 8, row.shape[0] * 8), Image.NEAREST).save(os.path.join(OD, 'claws.png'))
