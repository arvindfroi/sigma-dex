"""Scene 3 style swap (Arvind 2026-11-14: "just ask Qwen to replace them, style swap"): Qwen-Image-Edit gets the original
strip (blown up 6x, local only, never in the repo) as <image1> and our deer's art as <image2>, and replaces the beast.
python deer/gen_swap.py NAME SEED..."""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
H = os.path.dirname(os.path.abspath(__file__)); S = os.path.join(H, '..', 'scratch_intro', 'src')
ASK = {
 'rockedeer': ('orig48.png', ['rock_main.png'], "the slender deep indigo-blue deer in <image2>, with its pale cream muzzle, red-orange flame markings and antlers ending in round purple orbs ringed in fire"),
 'felk': ('orig47.png', ['felk_white.png'], "the deer in <image2>, with its cream-white face, fluffy brown and cream mane, antlers covered in long green leaf-feathers and a golden halo ring"),
 'moosus': ('orig49.png', [os.path.join(H, 'faces', 'moosus2_e2.png'), 'moosus_ds_big.png'], "the moose in <image2> and <image3>, with its long brown moose snout, pale lilac body and a crown of antlers made of aurora light (green, teal, violet) shaped like dripping candle flames"),
}
name = sys.argv[1]; ref, art, who = ASK[name]
prompt = (f"Redraw <image1> exactly, but replace the creature in it with {who}. Keep everything else the same as <image1>: "
          "the same pixel-art style with big flat pixels, the same few flat colours with one darker shade, thin black outlines "
          "between the parts, the pure black background, the same close-up framing cut off by the top and bottom edges, the "
          "same dim moody palette, and the same glowing yellow eyes staring at the viewer. Only the creature changes. "
          "Remove every part of the old creature completely, including its ribbons, crest, mane, cloud and armour: nothing of it is left, "
          "only the new creature's own head, antlers and body, filling the same place.")
for seed in map(int, sys.argv[2:]):
    comfy.generate(prompt, os.path.join(H, 'swap', f'{name}_{seed}.png'),
                   refs=[os.path.join(H, 'swap_ref', ref)] + [a if os.path.isabs(a) else os.path.join(S, a) for a in art], size=(1536, 384), seed=seed)
