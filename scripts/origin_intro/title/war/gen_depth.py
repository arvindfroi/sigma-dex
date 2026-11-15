"""Step 2: a depth map of the still picture, for the light plane. Qwen 2.1 edit draws it (no new model download).
python title/war/gen_depth.py COMP.png OUT.png SEED"""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
comp, out, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
comfy.generate("Convert <image1> into a depth map: a smooth grayscale image where the parts nearest to the viewer are white and "
               "farther parts are darker, the background pure black. Show the 3D volumes: the rounded head and bill, the fist, the "
               "chest, the arm and the tail each shaded by their distance. No lines, no outlines, no texture, no colour, no text.",
               out, refs=[comp], size=(1024, 768), seed=seed)
