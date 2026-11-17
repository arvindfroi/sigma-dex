"""Gravriel's overworld frames with real poses (Arvind on v2: "the animation is a bit lazy" next to Lugia, Ho-Oh and even
Sabertann). Lugia's 7 frames: 1-5 a full wing beat (wings high, mid, level, low, back up), 6 wings folded (landed),
7 the cry. Gravriel has no wings, so his arms and his ragged coat do the beat: Qwen-Image-Edit redraws the finished
pixel sprite (v2 frame, on its own grid; scripts/ds_pixel.edit) in each pose, keeping the creature, colours and grid.
python anim_edit.py BASE.png OUTDIR [SEED...]   -> OUTDIR/<pose>.png (64x64 RGBA) for every pose
env: POSES (comma list of pose names to make)"""
import sys, os
from pathlib import Path
from PIL import Image
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import ds_pixel
BASE, OUT = sys.argv[1:3]; SEEDS = tuple(int(s) for s in sys.argv[3:]) or (11, 12)
WHO = ("the ghost pirate (black tricorne hat, pale owl face mask with glowing cyan eyes and a beige beak, green seaweed beard, "
       "black tattered coat, teal clawed hands, a cutlass in his right hand on the left side of the picture)")
POSES = {
    'up':      "the pose of %s: both arms raised high above his shoulders and spread wide like wings at the top of a wing beat, "
               "the cutlass pointing up; the ragged coat hangs straight down, narrower; the body a little lower" % WHO,
    'halfup':  "the pose of %s: both arms raised to shoulder height and spread wide like wings half way up a wing beat, the "
               "cutlass held out to the side and up; the ragged coat hangs down" % WHO,
    'down':    "the pose of %s: both arms swept down and out below his waist like wings at the bottom of a wing beat, the "
               "cutlass pointing down and out; the ragged coat flares out wide to both sides as if pushed by the stroke; the body "
               "a little higher" % WHO,
    'halfdown':"the pose of %s: both arms spread out sideways a little below shoulder height like wings coming back up, the "
               "ragged coat still flared out wide" % WHO,
    'landed':  "the pose of %s: he has stopped and hangs still in the air: both arms down at his sides close to the body, the "
               "cutlass hanging straight down in his right hand, the ragged coat hanging straight and still" % WHO,
    'cry':     "the pose of %s: he roars: his head tilted a little up, his beak wide open, both arms thrown up and out wide, the "
               "cutlass raised high above his head, the coat flaring out" % WHO,
}
# v3b: the body must not move or change size between frames (Lugia's body stays put while its wings beat); only the arms
# and the coat's hem change
KEEP = (" Only his arms (and the cutlass in his hand) and the ragged bottom of his coat change. His head, hat, face, eyes, beak, "
        "beard and body keep exactly the same size and the same place in the picture as in <image1>, pixel for pixel.")
if os.environ.get('KEEP_BODY', '1') == '1':
    for k in ('up', 'halfup', 'down', 'halfdown', 'landed'): POSES[k] = POSES[k].replace('; the body a little lower', '').replace('; the body a little higher', '') + KEEP
want = [p for p in os.environ.get('POSES', ','.join(POSES)).split(',') if p]
base = Image.open(BASE).convert('RGBA'); os.makedirs(OUT, exist_ok=True)
for name in want:
    out = Path(OUT) / (name + '.png')
    if out.exists(): continue
    sp = ds_pixel.edit(base, "Draw " + POSES[name], Path(OUT) / ('work_' + name), seeds=SEEDS)
    sp.save(out); print(out, flush=True)
