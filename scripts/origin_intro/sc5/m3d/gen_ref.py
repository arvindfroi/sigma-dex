"""Scene 5 v4 (Arvind 2026-11-15: "none of these look good, try a new way that will work"): Moosus as a 3D model.
Step 1: a clean full-body picture for Hunyuan3D 2.1: Qwen redraws Moosus from its DS front sprite (<image1>, design)
and Arvind's drawing (<image2>), all four legs visible, smooth cel artwork on white.
python sc5/m3d/gen_ref.py SEED... -> sc5/m3d/ref_{seed}.png (1024x1024)"""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
H = os.path.dirname(os.path.abspath(__file__)); S = os.path.join(H, '..', '..', 'scratch_intro', 'src')
P = ("Draw the creature from <image1> as clean official character artwork for a 3D modeller: Moosus, a moose with a big round "
     "pale lilac-and-white body, a brown moose head with a long drooping brown snout and a big soft nose, a small brown "
     "neck tuft, a crown of short aurora antlers (green and teal with violet tips) on top of its head, four thin pale blue-white "
     "legs with small dark hooves, and a short brown tail. Copy its design, proportions and colours exactly from <image1>; "
     "<image2> is the same creature drawn by its designer. Standing on all four legs, seen in a three-quarter view from the front "
     "left so all four legs are visible and separate, the head turned to the left. Smooth clean cel shading, crisp outlines, no "
     "pixels. The whole creature centred and filling most of the picture, on a pure white background, no ground, no shadow, "
     "no rings, no text.")
for seed in map(int, sys.argv[1:]):
    comfy.generate(P, os.path.join(H, f'ref_{seed}.png'), refs=[os.path.join(S, 'moosus_ds_big.png'), os.path.join(S, 'moosus_686.png')],
                   size=(1024, 1024), seed=seed)
    print(seed, flush=True)
