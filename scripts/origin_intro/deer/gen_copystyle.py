"""Scene 3, v10 idea (Arvind 2026-11-15: "add a picture of Felk and the one of Raikou and ask it to copy the style"):
Qwen 2.1 gets OUR design first (<image1>, what to draw) and the original strip in the same slot second (<image2>, local only,
6x nearest from the ROM: only how to draw it). v3/qorig failed because our picture came second and the old beast leaked in.
python deer/gen_copystyle.py NAME SEED...   -> deer/copy/{name}_{seed}.png (1536x384)"""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
H = os.path.dirname(os.path.abspath(__file__)); S = os.path.join(H, '..', 'scratch_intro', 'src'); OUT = os.path.join(H, 'copy'); os.makedirs(OUT, exist_ok=True)
JOB = {
 'felk': ('felk_arvind6.png', 'orig49.png', 'Raikou',
          "a deer with a cream-white face and muzzle, a small black nose, a fluffy brown mane with cream tufts, pale branching antlers "
          "covered in long lime-green leaf-feathers and several thin golden halo rings around the antlers. Its head is right of centre, "
          "turned to the RIGHT, glaring at the viewer, the leaf antlers and mane streaming out behind it to the left"),
 'rockedeer': ('rock_main.png', 'orig48.png', 'Entei',
               "a slender deep indigo-blue deer with a pale cream muzzle, red-orange flame markings and antlers ending in round purple "
               "orbs ringed in fire. Its head is left of centre, turned to the LEFT, glaring at the viewer, its neck and back running off to the right"),
 'moosus': ('moosus_ds_big.png', 'orig47.png', 'Suicune',
            "a moose seen head-on, centred, staring at the viewer: a long broad brown snout with a big soft nose, small ears, a pale lilac "
            "body behind, and a wide crown of antlers made of aurora light shaped like dripping candle flames, green and teal fading to violet"),
}
name = sys.argv[1]; ours, orig, old, what = JOB[name]
PROMPT = (f"Draw the creature from <image1> as a new picture: {what}. Copy its design, its parts and its colours from <image1> exactly. "
          f"<image2> is ONLY a style reference: draw the new picture in exactly the same art style as <image2> - the same tight cinematic "
          f"close-up crop of the head that fills the frame height and is cut off by the top and bottom edges, the same flat cel shading "
          f"with one base colour and one darker shadow colour per part, the same solid black outlines and black inner lines, the same dark "
          f"moonlit colours on a pure black background, the same glowing golden eyes. Do NOT draw the {old} from <image2>: none of its "
          f"shapes, mane, crest or colours; only its drawing style. No text, no border.")
for seed in map(int, sys.argv[2:]):
    comfy.generate(PROMPT, os.path.join(OUT, f'{name}_{seed}.png'), refs=[os.path.join(S, ours), os.path.join(H, 'swap_ref', orig)],
                   size=(1536, 384), seed=seed)
