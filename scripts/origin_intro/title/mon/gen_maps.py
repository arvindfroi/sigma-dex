"""Monarkhan clip: depth map and flame mask of the chosen picture, both drawn by Qwen 2.1 edit.
python title/mon/gen_maps.py COMP SEED -> mon/depth_{seed}.png, mon/flames_{seed}.png"""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
H = os.path.dirname(os.path.abspath(__file__)); comp, seed = sys.argv[1], int(sys.argv[2])
comfy.generate("Convert <image1> into a depth map: a smooth grayscale image where the parts nearest to the viewer are white and farther "
               "parts are darker, the background pure black. Show the 3D volumes: the head and snout, the curled neck, the mane, the "
               "wings spread behind and the flames each shaded by their distance. No lines, no outlines, no texture, no colour, no text.",
               os.path.join(H, f'depth{os.environ.get("TAGM", "")}_{seed}.png'), refs=[comp], size=(1024, 768), seed=seed)
comfy.generate("Make a mask of the fire in <image1>: paint every flame (the two flames floating above the head, and any other fire) pure "
               "white, and paint everything else - the creature's body, head, mane, wings and the background - pure black. Exactly the "
               "same picture size and the same flame shapes in the same places. No grey, no other colours, no text.",
               os.path.join(H, f'flames{os.environ.get("TAGM", "")}_{seed}.png'), refs=[comp], size=(1024, 768), seed=seed)
# fur mask (v2, Arvind 2026-11-15: "the fur should look a bit like gold"): the yellow spotted fur and mane, for their own gold tones
if os.environ.get('FUR'):
    comfy.generate("Make a mask of the fur in <image1>: paint the yellow spotted fur - the shaggy mane on the head and the fluffy fur "
                   "collar round the neck - pure white, and paint everything else - the red body, the head, the snout, the wings, the "
                   "flames and the background - pure black. Exactly the same picture size and shapes in the same places. No grey, no "
                   "other colours, no text.", os.path.join(H, f'fur{os.environ.get("TAGM", "")}_{seed}.png'), refs=[comp], size=(1024, 768), seed=seed)
