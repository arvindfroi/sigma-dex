"""v4 (Arvind 2026-11-15: "remove the ball from the hand but keep the effect; mind the fingers in front of the ball"):
Qwen 2.1 edit removes the orb from comp2_5, same pose and place.  python title/war/gen_noorb.py SEED... -> noorb_{seed}.png"""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
H = os.path.dirname(os.path.abspath(__file__))
for seed in map(int, sys.argv[1:]):
    comfy.generate("Remove the glowing water orb from the creature's raised hand in <image1>. The clawed hand stays raised in exactly the "
                   "same place, size and pose, its fingers and claws curled open as if holding something that is not there; draw the "
                   "palm and the parts of the fingers that the orb hid. Keep everything else exactly identical: the same creature, "
                   "pose, framing, colours, line art and the pure black background. No orb, no ball, no glow.",
                   os.path.join(H, f'noorb_{seed}.png'), refs=[os.path.join(H, 'comp2_5.png')], size=(1024, 768), seed=seed)
