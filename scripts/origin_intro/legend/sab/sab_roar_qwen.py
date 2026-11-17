"""Sabertann's cry frame as a whole-body roar (Arvind 2026-11-17 on the open-mouth-only roar: "I didn't like that roar. It
should happen with the whole body when you roar"). Qwen-Image-Edit redraws the finished field sprite (wind_v1 frame 7, sails
full) on its own grid (scripts/ds_pixel.edit) in a roaring pose; each seed is kept so the poses can be compared.
python sab_roar_qwen.py WIND_DIR OUTDIR SEED...   -> OUTDIR/base.png, OUTDIR/<seed>.png (64x64 RGBA), OUTDIR/work_<seed>/"""
import sys, os
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import ds_pixel
WD, OD = sys.argv[1:3]; SEEDS = [int(s) for s in sys.argv[3:]] or [11, 12, 13, 14]; os.makedirs(OD, exist_ok=True)
H = os.path.dirname(os.path.abspath(__file__)); PAL = np.vstack([[0, 0, 0], np.load(os.path.join(H, 'pxd_2_pal.npy'))]).round().astype(np.uint8)
f = np.load(os.path.join(WD, 'f7_idx.npy')).astype(int)
rgba = np.zeros((64, 64, 4), np.uint8); rgba[..., :3] = PAL[f]; rgba[..., 3] = np.where(f > 0, 255, 0)
base = Image.fromarray(rgba); base.save(os.path.join(OD, 'base.png'))
WHO = ("Sabertann, a black sabre-toothed cat seen from the front, with a pirate ship's white sails, mast and small flag on its "
       "back, a dark red band over its brow, pale eyes, two long white sabre teeth and gold-tipped claws on its wide front paws")
POSE = os.environ.get('POSE', (
    "Draw %s roaring with its whole body, a big dramatic roar: it rears up so its chest and head rise higher in the picture, the "
    "head thrown up and back, the jaws opened very wide showing the red mouth and tongue between the two long sabre teeth, "
    "the eyes narrowed in fury, the shoulders hunched up, both front legs lifted and spread wide apart to the sides with the "
    "claws out, the sails billowing full behind it. The same creature, the same colours and the same pixel art style, about "
    "the same size, facing the viewer") % WHO)
for s in SEEDS:
    out = Path(OD) / ('%d.png' % s)
    if out.exists(): continue
    sp = ds_pixel.edit(base, POSE, Path(OD) / ('work_%d' % s), seeds=(s,)); sp.save(out); print(out, flush=True)
