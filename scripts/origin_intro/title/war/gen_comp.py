"""Title screen clip 1 (Arvind 2026-11-15): Warrallier takes Blastoise's clip. Step 1: the still picture the light sweeps over.
Qwen 2.1: <image1> our design (concept art 454), <image2> an original frame (local only) as STYLE and framing reference.
No trainer (ours does not exist yet) and no effect layer (Arvind: Warrallier has no obvious water part, drop it).
python title/war/gen_comp.py SEED... -> title/war/comp_{seed}.png (1024x768)"""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
H = os.path.dirname(os.path.abspath(__file__))
P1 = ("Draw the creature from <image1> as a dramatic anime title-screen close-up: Warrallier, a fierce bipedal platypus warrior with "
     "a long flat dark bill, a narrow glaring yellow eye, a crest of sharp spikes running back from its head, a dark blue-black body "
     "with a black chest, strong arms with sharp claws, one clawed fist raised near its face, a big flat beaver tail. Copy its design "
     "exactly from <image1>. <image2> is ONLY a style and framing reference: copy how it is drawn - a tight heroic close-up of the head "
     "and upper body filling the frame and cut off by the frame edges, the head large on the right half looking at the viewer, the "
     "fist in the foreground on the left, thick solid black outlines and black inner lines, flat cel shading with hard light and shadow "
     "shapes, strong clear volumes, on a pure black background. Do NOT draw anything from <image2>: no trainer, no cap, no cannon, no "
     "shell, no ball. Full colour. No text, no border.")
# v2 (Arvind 2026-11-15): facing the camera like all the originals, white eyes, the raised hand holds a ball (like the
# glowing orb at the tip of Blastoise's cannon)
P2 = ("Draw the creature from <image1> as a dramatic anime title-screen close-up: Warrallier, a fierce bipedal platypus warrior with a "
      "long flat dark bill, a crest of sharp spikes running back from its head, a dark blue-black body with a black chest, strong arms "
      "with sharp claws and a big flat beaver tail. Copy its design exactly from <image1>. It faces the viewer head-on and glares "
      "straight into the camera with two glowing pure white eyes without pupils. Its right hand is raised in the foreground on the left "
      "side of the picture, its claws holding a glowing round orb of water, as big as its head, bright and smooth. <image2> is ONLY a "
      "style and framing reference: a tight heroic close-up of the head and upper body filling the frame and cut off by the frame edges, "
      "thick solid black outlines and black inner lines, flat cel shading with hard light and shadow shapes, strong clear volumes, on a "
      "pure black background. Do NOT draw anything from <image2>: no trainer, no cap, no cannon, no shell, no ball with a button. "
      "Full colour. No text, no border.")
V2 = len(sys.argv) > 1 and sys.argv[1] == 'v2'
if V2: sys.argv.pop(1)
P = P2 if V2 else P1; TAG = 'comp2' if V2 else 'comp'
for seed in map(int, sys.argv[1:]):
    comfy.generate(P, os.path.join(H, f'{TAG}_{seed}.png'), refs=[os.path.join(H, '..', 'art', 'warrallier_454.jpg'), os.path.join(H, 'style_ref.png')],
                   size=(1024, 768), seed=seed)
    print(seed, flush=True)
