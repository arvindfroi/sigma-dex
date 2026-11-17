"""Dahrugula passed out drunk in Snorlax's place (a/0/8/1 194 KABIGON, one 64x64 frame; Arvind 2026-11-17: "the sleeping
Snorlax becomes a full Dahrugula: that line is written so the Pokemon is not asleep but very drunk and blacked out").
Qwen-Image-Edit draws it on the 64 grid in the style and size of Origin's sleeping Snorlax (<image1>, local only) from
Dahrugula's DS front sprite (<image2>); scripts/ds_pixel.snap reads it back. python gen_drunk.py OUT_PREFIX SEED..."""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy, ds_pixel
OUT = sys.argv[1]; SEEDS = [int(s) for s in sys.argv[2:]] or [1, 2, 3]
H = os.path.dirname(os.path.abspath(__file__))
PROMPT = ("<image1> is a Pokemon HeartGold overworld map sprite on the Nintendo DS: pixel art on a 64x64 grid of big square "
          "pixels, a big Pokemon lying on its back on a small patch of grass, blocking the road. Redraw it with the creature "
          "from <image2> instead, in exactly the same pixel art style, size, grid and place: Dahrugula, a round green koala-like "
          "Pokemon with big round ears, a cream face and belly and a red sash, lying flat on its back passed out drunk, its eyes "
          "two little x marks, red flushed cheeks, its tongue lolling out, one arm still hugging a small wooden barrel, the other "
          "wooden barrel tipped over on its side beside it with a puddle of spilled amber brew on the grass, a few little bubbles "
          "above its head. A thin dark outline, at most 15 colours, crisp square pixels, no anti-aliasing. Plain white background.")
for s in SEEDS:
    pic = '%s_qwen_%d.png' % (OUT, s)
    for attempt in range(6):
        if os.path.exists(pic): break
        try: comfy.generate(PROMPT, pic, [os.path.join(H, 'style_kabigon_local_1024.png'), os.path.join(H, 'design_front_1024.png')], seed=s, quiet=True)
        except comfy.ComfyError:
            print('ComfyUI away, waiting', flush=True); import time; time.sleep(90)
    sp = ds_pixel.snap(pic, colours=15, grid=64, crop=False); sp.save('%s_px_%d.png' % (OUT, s)); print('%s_px_%d.png' % (OUT, s), flush=True)
