"""Our Pokemon as a two-tone stencil for the Ruins of Alph puzzles (Arvind 2026-11-17: "the originals all have the same
dark background, so the pose must fill it up"). The game's pictures are big light shapes on a dark field (Kabuto's ring,
Aerodactyl's body, Omanyte's shell, Ho-Oh's feathers) with a few bold cut details; an engraved line drawing turns into
thin noise at 128 px. Qwen-Image-Edit redraws one of our emblems (qwen_stamp.py output) as a black and white paper-cut
in the same pose: solid black field, the creature as large solid white shapes filling the square, only bold details cut.
alph_puzzle.py STENCIL=1 reads it (white = raised stone, black = cut).
python qwen_stencil.py DESIGN OUT_PREFIX "COMPOSITION" SEED...   env FULL=1: COMPOSITION is the whole prompt"""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
DESIGN, OUT, COMP = sys.argv[1:4]; SEEDS = [int(s) for s in sys.argv[4:]] or [1, 2, 3]
PROMPT = ("Redraw <image1> as a bold two-tone stencil, like a paper-cut or a linocut print: a solid pure black background, "
          "and the creature as large solid pure white shapes that fill the whole square from edge to edge, touching the "
          "edges. Only the most important inner details are cut out of the white as solid black shapes: the eyes, the nose, "
          "the mouth, the gaps between the body parts, a few thick lines. Every black line is thick; no thin lines, no "
          "hatching, no texture, no grey, no gradients, no shading, no outline drawing. Keep the same creature, pose and "
          "composition: %s. Flat graphic black and white only. No text, no border, no frame.") % COMP
if os.environ.get('FULL') == '1': PROMPT = COMP                  # COMP is the whole prompt (e.g. to rework a stencil)
for s in SEEDS:
    p = '%s_%d.png' % (OUT, s)
    for attempt in range(8):
        if os.path.exists(p): break
        try: comfy.generate(PROMPT, p, [DESIGN], seed=s, quiet=True)
        except Exception as e:
            print('ComfyUI away (%s), waiting' % type(e).__name__, flush=True); import time; time.sleep(90)
    print(p, flush=True)
