"""Our Pokemon as a Ruins of Alph puzzle picture in the puzzles' own style (Arvind 2026-11-17: "you must not just put the
drawings on the puzzle: it must match the style and fill the frames"). The game's pictures are bold symbolic glyphs in two
flat sand tones that fill the whole tablet edge to edge (Kabuto's ring, Omanyte's spiral, Ho-Oh's fan of feathers), so
every piece holds a clear part of it. Qwen-Image-Edit draws such a glyph: <image1> the matching original puzzle picture
as the style (local only), <image2> our concept art as the design. alph_puzzle.py RELIEF=1 reads it in two tones.
python qwen_stamp.py STYLE DESIGN OUT_PREFIX "COMPOSITION" SEED..."""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
STYLE, DESIGN, OUT, COMP = sys.argv[1:5]; SEEDS = [int(s) for s in sys.argv[5:]] or [1, 2, 3, 4]
PROMPT = ("A square stone tablet carving in exactly the style of <image1>, the Ruins of Alph puzzle picture from Pokemon "
          "HeartGold: a bold, simplified, symbolic glyph of the creature from <image2>, drawn with only two flat tones of "
          "sand (light raised stone and a slightly darker carved stone), big chunky shapes and thick strokes as wide as in "
          "<image1>, no thin lines, no small details, no shading, no outlines, no gradients. The design fills the whole square "
          "from edge to edge like <image1>, with no empty margins, composed as a strong emblem: %s. Flat and graphic like a "
          "linocut stamp or an ancient petroglyph. No grid lines, no frame, no text.") % COMP
for s in SEEDS:
    p = '%s_%d.png' % (OUT, s)
    for attempt in range(6):
        if os.path.exists(p): break
        try: comfy.generate(PROMPT, p, [STYLE, DESIGN], seed=s, quiet=True)
        except comfy.ComfyError:
            print('ComfyUI away, waiting', flush=True); import time; time.sleep(90)
    print(p, flush=True)
