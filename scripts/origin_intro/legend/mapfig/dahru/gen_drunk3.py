"""Dahrugula drawn over Origin's sleeping Snorlax itself (a/0/8/1 194; Arvind 2026-11-17 on the lying-sideways try: "it
breaks the original's perspective, and it does not look enough like Dahrugula"). Qwen-Image-Edit gets the Snorlax sprite
(<image1>, on its own 64 grid, local only) as the picture to change and Dahrugula's DS front sprite (<image2>) as the
design; everything about the pose, size, angle and grass patch stays Snorlax's. Read back with ds_pixel.snap.
python gen_drunk3.py OUT_PREFIX SEED..."""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import numpy as np
from PIL import Image
import comfy, ds_pixel
OUT = sys.argv[1]; SEEDS = [int(s) for s in sys.argv[2:]] or [1, 2, 3]
H = os.path.dirname(os.path.abspath(__file__))
k = Image.open(os.path.join(H, 'kabigon_local.png')).convert('RGBA')
shown = ds_pixel.on_canvas(k, OUT + '_shown.png', grid=64)
PROMPT = ("<image1> is a Pokemon HeartGold overworld sprite on the Nintendo DS: pixel art on a 64x64 grid of big square pixels, "
          "a big Pokemon lying on its back on a small patch of grass, seen from this exact angle. Change only who it is: turn "
          "it into Dahrugula from <image2>, passed out drunk, in exactly the same pose, size, angle, outline and place, on the "
          "same grass patch and the same pixel grid. Dahrugula: a green koala-like Pokemon, green all over in its own greens "
          "(the belly green too), two big round ears with peach-coloured insides on its head, a brown nose, its eyes two dark "
          "X marks, a red sash round its belly, hugging one of its small orange-brown wooden barrels with dark hoops on its "
          "belly, its mouth open with a red tongue. Crisp square pixels, a dark outline, at most 15 colours, no anti-aliasing. "
          "Plain white background.")
for s in SEEDS:
    pic = '%s_qwen_%d.png' % (OUT, s)
    for attempt in range(6):
        if os.path.exists(pic): break
        try: comfy.generate(PROMPT, pic, [str(shown), os.path.join(H, 'design_front_1024.png')], seed=s, quiet=True)
        except comfy.ComfyError:
            print('ComfyUI away, waiting', flush=True); import time; time.sleep(90)
    sp = ds_pixel.snap(pic, colours=15, grid=64, crop=False); sp.save('%s_px_%d.png' % (OUT, s)); print('%s_px_%d.png' % (OUT, s), flush=True)
