"""Gravriel for the Whirl Islands ritual (Lugia's slot, a/0/8/1 211), drawn the way Sabertann's field sprite was
(legend/sab/gen_front.py, which Arvind liked): Qwen draws one full-body front view, coming down toward the viewer.
<image1> = his card art (assets/concept-art/gravriel/240.webp), <image2> = his front view (title3d/grav/views/front.png,
the turnaround of Arvind's design), <image3> = Lugia's cutscene frame 1 as STYLE ONLY (local, never in the repo).
python gen_front_grav.py SEED...  -> front_{seed}.png (1024x1024)"""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
H = os.path.dirname(os.path.abspath(__file__)); A = '/Users/arvind/Sigma pokemon pc port attempt/assets'
REFS = [f'{A}/concept-art/gravriel/240.webp', '/Users/arvind/sigma-origin/title3d/grav/views/front.png', os.path.join(H, 'style_lugia1.png')]
PROMPT = os.environ.get('PROMPT') or (
    "Draw the creature from <image1> and <image2>: a ghostly sea pirate with a black tricorne pirate hat, a pale grey owl-like "
    "face mask with two big round glowing cyan eyes under heavy drooping lids and a short beige hooked beak, a long dripping "
    "green seaweed beard, a long black tattered coat studded with small pale barnacles and shells, a red-orange shell on his "
    "left shoulder, teal-green clawed hands, and a curved cutlass in his right hand. Copy his design and colours exactly from "
    "<image1> and <image2>. Pose: seen exactly from the FRONT, staring straight at the viewer, floating down toward the "
    "viewer: both arms spread wide out to the sides like wings, the cutlass held out to the side, the ragged coat flaring "
    "out wide below him like a ghost's tail. The whole creature fills the square picture, his arms and coat reaching the "
    "left and right edges. <image3> is ONLY a style reference: draw it as a clean DS pixel-art cutscene sprite exactly like "
    "<image3> - the same head-on framing, big simple shapes, flat colours with two or three tones each, thin dark outlines, "
    "bright readable colours. Do NOT draw the bird from <image3>, none of its shapes or colours. Plain white background, "
    "no text, no border.")
for seed in map(int, sys.argv[1:]):
    out = os.path.join(H, f'front_{seed}.png')
    if not os.path.exists(out):
        comfy.generate(PROMPT, out, refs=REFS, size=(1024, 1024), seed=seed); print(out, flush=True)
