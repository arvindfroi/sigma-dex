"""Scene 3 deer strips, style pass (Arvind 2026-11-15: "work on the image model to swap the style; we have many LoRAs").
Takes the three faces in use (v5) and redraws only their style toward the originals' flat anime cel look:
  ken55 / ken75  Illustrious + sugimori_ken_il LoRA, image to image, canny ControlNet 0.6, denoise 0.55 / 0.75
  fake65         Illustrious + fakemon_sugimori_il LoRA, denoise 0.65
  qart           Qwen 2.1 edit + pkmn_art_style_v1 LoRA 0.8, our face as the only reference
  qorig          Qwen 2.1 edit, no LoRA, <image1> = the original strip in the same slot (STYLE ONLY), <image2> = our face
python deer/style_test.py [VARIANT...]   -> deer/style/{name}_{variant}.png (1536x384)"""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H, 'style'); os.makedirs(OUT, exist_ok=True)
FACES = {   # name: (face in use, original strip in the same slot (local only), what it is)
 'rockedeer': ('faces/rock4_e2.png', 'swap_ref/orig48.png',
               'a slender deep indigo-blue deer, head turned to the left, pale cream muzzle, red-orange flame markings, antlers ending in round purple orbs ringed in fire'),
 'moosus': ('faces/moos4_e4.png', 'swap_ref/orig47.png',
            'a moose face seen head-on, long broad brown snout, big nose, small ears, a crown of aurora antlers shaped like dripping candle flames, green and teal fading to violet'),
 'felk': ('faces/felk5_e8.png', 'swap_ref/orig49.png',
          'a deer with a cream-white face turned to the right, small black nose, fluffy brown and cream mane, branching antlers covered in green leaf-feathers, a thin golden halo ring'),
}
SD_STYLE = ("anime screencap, 2d anime keyframe, cel shading, flat colors, two tones per color, very thick black outlines around every shape, "
            "simple large shapes, clean lineart, no texture, dark night, deep shadow, glowing yellow eyes, black background, close-up, ")
NEG = ("lowres, text, watermark, logo, signature, frame, border, photo, 3d, realistic, blurry, painterly, brush strokes, fur texture, "
       "detailed fur, noise, gradient, sketch, human, girl")
Q_STYLE = ("Clean 2D anime cel style exactly like a Pokemon anime opening keyframe: large simple shapes, completely flat colours with only two "
           "or three tones per colour and hard edges between them, very thick solid black outlines around every shape and between the parts, "
           "no texture, no fur strands, no brush strokes, no gradients, no noise. Dark moonlit night, the creature mostly in deep blue-grey shadow, "
           "its eyes glowing bright golden yellow. Pure black background. Keep the creature, its pose, its framing and its colours exactly as they are.")
# round 2: the Sugimori LoRA at 0.65 / 0.75 kept the originals' flat look best; weighted words for the parts it dropped
WHAT2 = {'rockedeer': '(glowing yellow eyes:1.4), (purple orbs on antler tips:1.2), (orange flames:1.1), dark blue deer, pale grey muzzle, red markings, head turned left, ',
         'moosus': '(glowing yellow eyes:1.4), moose, head-on, brown snout, (green aurora antler crown:1.2), lilac body, ',
         'felk': '(glowing yellow eyes:1.4), (cream white face:1.3), deer, head turned right, brown fluffy mane, green leaf antlers, golden halo, '}
VARS = sys.argv[1:] or ['ken55', 'ken75', 'fake65', 'qart', 'qorig']
if VARS == ['r2']:
    for name, (face, orig, what) in FACES.items():
        for dn in (65, 75):
            for seed in (21, 22, 23):
                out = os.path.join(OUT, f'{name}_r2k{dn}_{seed}.png')
                if os.path.exists(out): continue
                comfy.restyle(os.path.join(H, face), WHAT2[name] + SD_STYLE + what, out, denoise=dn / 100, control=0.6, seed=seed,
                              lora_name='sugimori_ken_il.safetensors', trigger='sugimori ken, pokemon (creature), no humans, solo, ', negative=NEG, cfg=5.5)
    sys.exit()
for name, (face, orig, what) in FACES.items():
    src = os.path.join(H, face)
    for v in VARS:
        out = os.path.join(OUT, f'{name}_{v}.png')
        if os.path.exists(out): continue
        if v in ('ken55', 'ken75'):
            comfy.restyle(src, SD_STYLE + what, out, denoise=int(v[3:]) / 100, control=0.6, seed=11, lora_name='sugimori_ken_il.safetensors',
                          trigger='sugimori ken, pokemon (creature), no humans, solo, ', negative=NEG, cfg=5.5)
        elif v == 'fake65':
            comfy.restyle(src, SD_STYLE + what, out, denoise=0.65, control=0.6, seed=11, lora_name='fakemon_sugimori_il.safetensors',
                          trigger='Fakemon, Sugimori, pokemon (creature), no humans, solo, ', negative=NEG, cfg=5.5)
        elif v == 'qart':
            comfy.generate("Redraw <image1> in a new art style. " + Q_STYLE, out, refs=[src], size=(1536, 384), seed=11,
                           lora='pkmn_art_style_v1.safetensors', lora_strength=0.8)
        elif v == 'qorig':
            comfy.generate("<image1> shows ONLY the art style to copy; do not copy its creature, its shapes or its colours. Redraw the creature "
                           "in <image2> in exactly the drawing style of <image1>: the same line thickness, the same flat cel shading, the same "
                           "number of tones, the same darkness. " + Q_STYLE, out, refs=[os.path.join(H, orig), src], size=(1536, 384), seed=11)
        print(name, v, flush=True)
# round D2 (Arvind 2026-11-15: "v5 and D liked best, none good enough"): stay with D (Qwen 2.1 + pkmn_art_style_v1 on the v5
# face); vary the LoRA strength / the art LoRA, and ask for what the originals have and D lacked: a moonlit blue-grey body
# lighter than the background, thin black inner lines, the aurora crown still green, eyes glowing gold.
Q2 = ("Clean 2D anime cel style like a Pokemon anime opening keyframe: flat colours, two or three tones per colour with hard edges, "
      "a solid black outline around the whole creature and thin black lines between all its parts (eyes, snout, ears, mane, antlers, markings). "
      "No texture, no fur strands, no brush strokes, no noise. Cold moonlit night: every colour is tinted toward cool blue-grey and a little "
      "darker, but the creature's body stays clearly lighter than the pure black background so its shape reads at a glance. "
      "Its eyes glow bright golden yellow, the brightest thing in the picture. Keep the creature, its design, its pose and framing exactly as they are.")
EXTRA = {'rockedeer': ' Keep the purple orbs and orange flames on its antler tips.', 'moosus': ' Keep the antler crown green and teal fading to violet, glowing softly; both eyes glow.',
         'felk': ' Keep its face pale cream, its leaf antlers green and the golden halo.'}
if VARS == ['d2']:
    for name, (face, orig, what) in FACES.items():
        for tag, lora, st in (('s06', 'pkmn_art_style_v1.safetensors', 0.6), ('s08', 'pkmn_art_style_v1.safetensors', 0.8),
                              ('s10', 'pkmn_art_style_v1.safetensors', 1.0), ('a08', 'pkmn_art_v1.safetensors', 0.8)):
            for seed in (31, 32):
                out = os.path.join(OUT, f'{name}_d2{tag}_{seed}.png')
                if os.path.exists(out): continue
                comfy.generate("Redraw <image1> in a new art style. " + Q2 + EXTRA[name], out, refs=[os.path.join(H, face)], size=(1536, 384),
                               seed=seed, lora=lora, lora_strength=st, quiet=True)
                print(name, tag, seed, flush=True)
