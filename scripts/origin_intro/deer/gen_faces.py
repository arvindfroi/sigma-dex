"""Scene 3 deer strips, step 1: Qwen draws a wide close-up of each deer's face from its concept art.
python deer/gen_faces.py NAME SEED..."""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
S = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scratch_intro', 'src')
STYLE = ("Cinematic widescreen close-up for an anime opening, 4:1 letterbox. Pure black background. Clean anime cel shading "
         "with flat colours, bold black outlines around every shape and between the parts, two or three tones per colour, like a 2D Pokemon anime keyframe. "
         "Moonlit night: cool dim light from the upper left, the creature's own colours kept but a little darker. "
         "The face is mostly in deep shadow, dark and menacing, and the eyes GLOW bright golden yellow, like lanterns in the dark: the glowing eyes are the brightest thing in the picture and stare straight at the viewer. No text, no border, nothing else in the picture.")
ASK = {
 'felk5': (['felk_white.png'],
   "The creature is the deer in <image1>. Copy its design exactly: a CREAM-WHITE face and muzzle with a small black nose, a big "
   "fluffy mane of BROWN and cream fur round its neck, slim branching pale antlers covered in long bright GREEN leaf-feathers, and a "
   "thin GOLDEN HALO ring floating around the antlers. Tight close-up like a movie title card: its head is large, right of centre, in "
   "three-quarter view turned to the RIGHT and glaring at the viewer; the leaf antlers and mane stream out behind it to the left. "
   "The halo and antler tips are cut off by the top edge, the mane by the bottom edge. Its cream face stays pale and clearly lit "
   "by the moon even though the rest is dark."),
 'felk6': (['felk_arvind6.png'],
   "The creature is the deer in <image1>, Arvind's design: copy it exactly. A CREAM-WHITE face, muzzle and throat with a small black nose, "
   "a fluffy BROWN mane with cream tufts round its neck and shoulders, slim pale cream branching antlers covered in long bright LIME-GREEN "
   "leaf-feathers, and several thin GOLDEN HALO rings floating around the antlers. Tight close-up like a movie title card: its head is large, "
   "right of centre, in three-quarter view turned to the RIGHT and glaring at the viewer; the leaf antlers and halos fill the top, the mane "
   "streams out behind it to the left. The halos and antler tips are cut off by the top edge, the mane by the bottom edge. Its cream face "
   "stays pale and clearly lit by the moon even though the rest is dark."),
 'rock4': (['rock_main.png', 'rock_front.png'],
   "The creature is the deer in <image1> and <image2>: a slender deep indigo-blue deer with a pale cream muzzle, red-orange flame "
   "markings and antlers ending in round purple orbs ringed in fire. Tight close-up like a movie title card: its head is on the "
   "left half of the frame in three-quarter view, turned to the LEFT and glaring at the viewer, its neck and back running off to "
   "the right edge, the orb antlers cut off by the top edge, the jaw cut off by the bottom edge."),
 'moos4': (['moosus_ds_big.png', 'moosus_sketch.png'],
   "The creature is the moose in <image1> and <image2>. Tight head-on close-up of its face staring straight at the viewer, centred: "
   "a long broad brown moose snout with a big soft nose, small ears, a pale lilac body behind, and on top a wide crown of antlers "
   "made of aurora light shaped like dripping candle flames, green and teal fading to violet at the tips. The crown is cut off by "
   "the top edge and the snout by the bottom edge."),
 'felk4': (['felk_white.png'],
   "The creature is the deer in <image1>: a cream-white deer face with a fluffy brown and cream mane, branching antlers covered in "
   "long green leaf-feathers and a golden halo ring. Tight close-up like a movie title card: its head is right of centre in "
   "three-quarter view, turned to the RIGHT and glaring at the viewer, its big mane and leaf antlers streaming out behind it to the "
   "left, the antlers cut off by the top edge, the jaw cut off by the bottom edge."),
 'moosus2': (['moosus_ds_big.png', 'moosus_sketch.png'],
   "The creature is the moose in <image1> and <image2>. Head-on close-up of its face looking straight at the viewer: a long "
   "broad moose snout with a big soft nose, brown fur, small ears, and on top of its head a large wide crown of antlers made of "
   "glowing aurora light, shaped like dripping candle flames, bright green and teal fading to violet at the tips, softly lighting "
   "its brow from above. Behind the head the shoulders of a pale lilac body. The face fills the frame height, crown at the top edge, chin at the bottom edge, centred."),
 'moosus': (['moosus_ds_big.png', 'moosus_sketch.png'],
   "The creature is the moose in <image1> and <image2>: a brown moose head with a long drooping snout, a calm green-teal eye, "
   "and a glowing aurora-coloured (green, teal, violet) crown of antlers shaped like dripping candle flames; a pale lilac body. "
   "Show only its head and the antler crown, facing the viewer almost head-on, filling the frame height, cut off at the top of the antlers and under the jaw, placed in the centre."),
 'felk': (['felk_white.png'],
   "The creature is the deer in <image1>: a cream-white deer face with a fluffy brown and cream mane, a bright blue eye, "
   "branching antlers covered in long green leaf-feathers, and golden halo rings floating around the antlers. "
   "Show only its head, mane and antlers, three-quarter view, head turned toward the viewer, filling the frame height, the antlers running off the top edge, placed right of centre."),
 'rockedeer': (['rock_main.png', 'rock_front.png'],
   "The creature is the deer in <image1> and <image2>: a slender deep indigo-blue deer with a pale cream muzzle and throat, "
   "red-orange flame markings, narrow focused eyes, and antlers ending in round purple psychic orbs ringed in fire. "
   "Show only its head, neck and antlers, three-quarter view turned toward the viewer with a fierce look, filling the frame height, the orbs blazing, placed left of centre."),
}
# felk7 (2026-11-15): felk6's ask, but the colours kept true (the cel pass adds the night shadow itself); felk6 came out grey-blue
STYLE_TRUE = ("Cinematic widescreen close-up for an anime opening, 4:1 letterbox. Pure black background. Clean anime cel shading with flat "
              "colours, bold black outlines around every shape, one lit tone and one shadow tone per colour. Moonlight from the upper left. "
              "Keep its true colours clearly visible: the face and muzzle CREAM WHITE, the mane WARM BROWN with cream tufts, the leaves "
              "BRIGHT LIME GREEN, the halos GOLD. The eyes glow bright golden yellow. No text, no border, nothing else in the picture.")
ASK['felk7'] = ASK['felk6']
name = sys.argv[1]; refs, look = ASK[name]
if name == 'felk7': STYLE = STYLE_TRUE
for seed in map(int, sys.argv[2:]):
    comfy.generate(look + ' ' + STYLE, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'faces', f'{name}_e{seed}.png'),
                   refs=[os.path.join(S, r) for r in refs], size=(1536, 384), seed=seed)
