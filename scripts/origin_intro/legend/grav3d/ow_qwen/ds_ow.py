"""Gravriel's overworld sprite as real DS pixel art, the way the dex's DS battle sprites are made (scripts/ds_pixel.py):
Qwen-Image-Edit draws the creature as pixel art laid out on the sprite's own grid, shown as a grey silhouette blown up
to 1024 (one sprite pixel = 16 px on the 64 canvas); its picture is read back cell by cell (15 colours, the commonest
colour per cell), so nothing is shrunk afterwards (shrinking Qwen's detailed front view gave noise, Arvind preferred
Sabertann's clean sprite).  python ds_ow.py DESIGN.png DRAFT_idx.npy OUT_PREFIX SEED...
DESIGN = Qwen's front view (front_3.png), DRAFT = its 64x64 pixelized index image (size/place only)"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy, ds_pixel
DESIGN, DRAFT, OUT = sys.argv[1:4]; SEEDS = [int(s) for s in sys.argv[4:]]
STYLE = ("an official Pokemon HeartGold and SoulSilver overworld cutscene sprite on the Nintendo DS, like the legendary birds "
         "Ho-Oh and Lugia when they come down to the player: pixel art on a coarse grid of big square pixels, each pixel a crisp "
         "square, no anti-aliasing, no blur, no dithering, a limited palette of at most 15 colors, bright readable colors, big "
         "simple shapes, flat color areas with one shadow tone and small highlights, a thin dark outline.")
PROMPT = os.environ.get('PROMPT') or (
    "Convert <image1> (the design) into %s It must be laid out like <image2>, the sprite's grey silhouette at the right size, "
    "place and pixel grid: the same size, place and outline, the same pixel size, drawn well inside it. Big clean shapes, no "
    "noise, no single-pixel speckles. Keep the creature exactly as in <image1>: a ghostly sea pirate floating toward the "
    "viewer, black tricorne hat, a pale grey owl face mask with two big round glowing cyan eyes and a short beige beak, a long "
    "green seaweed beard, a black tattered coat with a few pale barnacles, a red-orange shell on his left shoulder, teal clawed "
    "hands, one curved cutlass in his right hand, the ragged coat flaring out below like a ghost's tail. The face drawn big "
    "and clear: the two glowing cyan eyes must read. Plain white background, nothing else.") % STYLE
a = np.load(DRAFT); rgba = np.zeros((64, 64, 4), np.uint8); rgba[a > 0] = (128, 128, 128, 255)
guide = ds_pixel.on_canvas(ds_pixel.silhouette(Image.fromarray(rgba)), OUT + '_guide.png', grid=64)
for s in SEEDS:
    pic = OUT + '_qwen_%d.png' % s
    if not os.path.exists(pic): comfy.generate(PROMPT, pic, [DESIGN, str(guide)], seed=s, quiet=True)
    sp = ds_pixel.snap(pic, colours=15, grid=64, crop=False); sp.save(OUT + '_px_%d.png' % s); print(OUT + '_px_%d.png' % s, flush=True)
