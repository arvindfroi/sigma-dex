"""Qwen-Image-Edit: Lapper's approved front sprite redrawn in a hop pose (Marill's second intro cell is a hop with an open
mouth). Shown the front on the 96 canvas at 1024 (as ds_pixel does), read back on that 96 grid.
python qwen_hop.py OUT_PREFIX SEED..."""
import sys, os, time
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy, ds_pixel
from PIL import Image
FRONT = '/Users/arvind/sigma-origin/title3d/legend/oak/lapper_src/front.png'
OUT = sys.argv[1]; SEEDS = [int(s) for s in sys.argv[2:]] or [1, 2, 3]
PROMPT = os.environ.get('PROMPT') or (
    "<image1> is a Pokemon battle sprite: pixel art from Pokemon Diamond, Pearl and HeartGold on the Nintendo DS, on a coarse "
    "grid of big square pixels. Draw the same creature in a new pose: a happy little hop straight up, all four paws off the "
    "ground, front legs reaching forward and down, hind legs tucked back, its long fluffy ears flying up and outward from the "
    "jump, its mouth wide open with the pink tongue out, its fluffy tail up. Its eyes stay hidden behind its fringe and ears "
    "exactly as in <image1>; no eyes visible. The same view (three-quarter, facing left), the same size, the same design, "
    "markings and colors, the same pixel size and grid, crisp square pixels, no anti-aliasing, no blur, a one-pixel dark "
    "outline, flat shading. Exactly one creature. Plain white background, nothing else.")
shown = ds_pixel.on_canvas(Image.open(FRONT).convert('RGBA'), OUT + '_shown.png')
for s in SEEDS:
    p = '%s_%d.png' % (OUT, s)
    for attempt in range(8):
        if os.path.exists(p): break
        try: comfy.generate(PROMPT, p, [shown], seed=s, quiet=True)
        except Exception as e:
            print('ComfyUI away (%s: %s), waiting' % (type(e).__name__, e), flush=True); time.sleep(60)
    ds_pixel.snap(p, grid=96, crop=False).save('%s_%d_snap.png' % (OUT, s))
    print(p, flush=True)
