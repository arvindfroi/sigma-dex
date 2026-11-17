"""Qwen-Image-Edit draws our Pokemon as a Ruins of Alph stone carving: <image1> the design (concept art), <image2> one of
the game's own puzzle pictures as the style (local only, never in the repo). The answer is read in two sand tones by
alph_puzzle.py (RELIEF=1). python qwen_relief.py DESIGN STYLE OUT_PREFIX "WHAT" SEED..."""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
DESIGN, STYLE, OUT, WHAT = sys.argv[1:5]; SEEDS = [int(s) for s in sys.argv[5:]] or [1, 2, 3]
PROMPT = ("Draw the creature from <image1> as an ancient carved sandstone tablet in exactly the style of <image2>, the "
          "Ruins of Alph stone puzzle from Pokemon HeartGold: a square tablet of light sand-coloured stone that fills the "
          "whole picture, with the creature cut into it as bold, simple, flat shapes in a slightly darker sand tone, its "
          "parts separated by thin raised stone gaps, like a primitive petroglyph. The creature: %s. Only two tones of sand, "
          "no outlines, no shading, no other colours, no grid lines, no frame, no text, the creature big and centred, "
          "seen clearly, filling most of the tablet.") % WHAT
for s in SEEDS:
    p = '%s_%d.png' % (OUT, s)
    for attempt in range(6):
        if os.path.exists(p): break
        try: comfy.generate(PROMPT, p, [DESIGN, STYLE], seed=s, quiet=True)
        except comfy.ComfyError as e:
            print('ComfyUI away, waiting', flush=True); import time; time.sleep(90)
    print(p, flush=True)
