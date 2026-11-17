"""Sabertann for the Bell Tower scene (Ho-Oh's slot, a/0/8/1 210): Qwen draws one full-body front view, flying down
from the sky with its sails full of wind. <image1>/<image2> = our design (DS front sprite + concept), <image3> = Ho-Oh's
cutscene frame 1 as STYLE ONLY (local, never in the repo).
python legend/sab/gen_front.py SEED...  -> legend/sab/front_{seed}.png (1024x1024)"""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
H = os.path.dirname(os.path.abspath(__file__)); A = '/Users/arvind/Sigma pokemon pc port attempt/assets'
REFS = [f'{A}/concept-art/sabertann/624.webp', f'{A}/sprites-ds/sabertann/front.png', os.path.join(H, 'style_hooh1.png')]
PROMPT = ("Draw the creature from <image1> and <image2>: a big black sabre-toothed cat with long ivory sabre fangs, a gold-trimmed "
          "black pirate captain hat with a gold skull, gold paws, and a red pirate-ship hull with gold spikes on its back carrying "
          "a mast with white sails painted with a gold skull and crossbones and a small flag on top. Copy its design and colours "
          "exactly from <image1> and <image2>. Pose: seen exactly from the FRONT, perfectly symmetric, staring straight at the "
          "viewer, coming down from the sky toward the viewer: front legs spread wide to both sides with the gold paws open, "
          "the sails puffed up full of wind and spread wide behind and above its head like wings, the hull visible behind its "
          "shoulders. The whole creature fills the square picture, its sails touching the left and right edges. "
          "<image3> is ONLY a style reference: draw it as a clean DS pixel-art cutscene sprite exactly like <image3> - the same "
          "head-on symmetric framing, big simple shapes, flat colours with two or three tones each, thin dark outlines, bright "
          "readable colours in daylight. Do NOT draw the bird from <image3>, none of its shapes or colours. Plain white background, "
          "no text, no border.")
for seed in map(int, sys.argv[1:]):
    out = os.path.join(H, f'front_{seed}.png')
    if not os.path.exists(out):
        comfy.generate(PROMPT, out, refs=REFS, size=(1024, 1024), seed=seed); print(out, flush=True)
