"""Qwen-Image-Edit replaces the carved picture of one of the game's own Alph puzzles (<image1>, the 128x128 picture blown
up to 1024, 8 px per pixel, local only) with our Pokemon (<image2>, its concept art), keeping the pixel grid, the two sand
tones and the frames. Read back by alph_puzzle.py (TILE=1: each 8x8 cell to its nearest palette colour).
python qwen_tile.py STYLE DESIGN OUT_PREFIX "WHAT" SEED..."""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
STYLE, DESIGN, OUT, WHAT = sys.argv[1:5]; SEEDS = [int(s) for s in sys.argv[5:]] or [1, 2, 3]
PROMPT = ("<image1> is a pixel-art stone puzzle tablet from Pokemon HeartGold's Ruins of Alph: big square pixels on a "
          "128x128 grid, two sand tones, a carved picture. Replace only the carved picture with the creature from <image2>: %s. "
          "Draw it in exactly the same pixel art style, on the same grid of big square pixels, with the same two sand colours: "
          "the creature raised in the light sand tone with its features cut in as thick lines of the darker tone, standing on "
          "a field of the darker tone, bold simple chunky shapes like the original picture, the creature big and filling the "
          "tablet. Keep the tablet's light rim and the dark puzzle piece lines exactly where they are. No new colours, no "
          "shading, no anti-aliasing.") % WHAT
for s in SEEDS:
    p = '%s_%d.png' % (OUT, s)
    for attempt in range(6):
        if os.path.exists(p): break
        try: comfy.generate(PROMPT, p, [STYLE, DESIGN], seed=s, quiet=True)
        except comfy.ComfyError:
            print('ComfyUI away, waiting', flush=True); import time; time.sleep(90)
    print(p, flush=True)
