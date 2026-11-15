"""Monarkhan v5 (Arvind 2026-11-15: "very very close; make the wings - the limb the wings come out of - match the colour and
thickness in the art; make the flames by the ears bigger"). Qwen 2.1 edit of comp3_4 with his design as the reference.
python title/mon/gen_edit.py SEED... -> mon/comp5_{seed}.png"""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
H = os.path.dirname(os.path.abspath(__file__))
P = ("Edit <image1>, keep everything else exactly as it is (the creature, its pose, the framing, the mane, the fur collar, the spots, "
     "the line art, the colours and the black background). Two changes only: 1) The arm that each wing grows out of - the bone along "
     "the top edge of the wing up to its tip - must be a THICK dark crimson-red limb, the same red as the creature's neck and body and "
     "about as thick as its arm, like the red wing arm with a pale claw at its tip in <image2>; the yellow spotted wing membrane hangs "
     "from that red arm. 2) Make the two flames floating above its head twice as big and taller, still floating free above the head "
     "without touching it.")
for seed in map(int, sys.argv[1:]):
    comfy.generate(P, os.path.join(H, f'comp5_{seed}.png'), refs=[os.path.join(H, 'comp3_4.png'), os.path.join(H, 'monarkhan_design.png')],
                   size=(1024, 768), seed=seed)
