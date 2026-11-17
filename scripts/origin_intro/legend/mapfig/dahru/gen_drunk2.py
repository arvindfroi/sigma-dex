"""Drunk Dahrugula drawn straight on the 64 grid (the dex's DS sprite recipe, scripts/ds_pixel.py): Qwen-Image-Edit fills
the grey silhouette of Origin's sleeping Snorlax (a/0/8/1 194, local only) blown up to 1024 (one pixel = 16 px), so the
figure takes Snorlax's exact size and place; read back cell by cell with 15 colours.
python gen_drunk2.py OUT_PREFIX SEED..."""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import numpy as np
from PIL import Image
import comfy, ds_pixel
OUT = sys.argv[1]; SEEDS = [int(s) for s in sys.argv[2:]] or [1, 2, 3]
H = os.path.dirname(os.path.abspath(__file__))
k = np.asarray(Image.open(os.path.join(H, 'kabigon_local.png')).convert('RGBA')); rgba = np.zeros((64, 64, 4), np.uint8); rgba[k[..., 3] > 0] = (128, 128, 128, 255)
guide = ds_pixel.on_canvas(ds_pixel.silhouette(Image.fromarray(rgba)), OUT + '_guide.png', grid=64)
PROMPT = ("<image1> is the grey silhouette of a Pokemon HeartGold overworld sprite on the Nintendo DS, laid out on a 64x64 "
          "grid of big square pixels. Fill exactly that silhouette, at that size and place on the same pixel grid, with "
          "Dahrugula from <image2> passed out drunk on a small patch of grass: a round green koala-like Pokemon with big "
          "round ears, a cream face and belly and a red sash, lying flat on its back, its head on the right, its eyes two "
          "dark X marks, pink flushed cheeks, its red tongue lolling out, one wooden barrel tipped over beside it with a "
          "puddle of spilled amber brew. Strong contrast: a thick dark outline round the creature, the grass patch a darker "
          "green than the creature. Pixel art like an official HeartGold sprite: crisp square pixels, at most 15 colours, "
          "no anti-aliasing, flat colours with one shadow tone. Plain white background outside the silhouette.")
for s in SEEDS:
    pic = '%s_qwen_%d.png' % (OUT, s)
    for attempt in range(6):
        if os.path.exists(pic): break
        try: comfy.generate(PROMPT, pic, [str(guide), os.path.join(H, 'design_front_1024.png')], seed=s, quiet=True)
        except comfy.ComfyError:
            print('ComfyUI away, waiting', flush=True); import time; time.sleep(90)
    sp = ds_pixel.snap(pic, colours=15, grid=64, crop=False); sp.save('%s_px_%d.png' % (OUT, s)); print('%s_px_%d.png' % (OUT, s), flush=True)
