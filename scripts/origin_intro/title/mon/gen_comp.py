"""Title screen clip 2 (Arvind 2026-11-15): Monarkhan takes Charizard's clip. Its design: monarkhan_design.png (Arvind's).
Qwen 2.1: <image1> our design, <image2> an original frame (local only) as style/framing reference.
python title/mon/gen_comp.py SEED... -> title/mon/comp_{seed}.png (1024x768)"""
import sys, os
sys.path.insert(0, '/Users/arvind/Sigma pokemon pc port attempt/scripts')
import comfy
H = os.path.dirname(os.path.abspath(__file__))
P = ("Draw the creature from <image1> as a dramatic anime title-screen close-up: Monarkhan, a dark crimson-red dragon-like creature with "
     "a long curved neck, a blunt pig-like snout with a big pink nose and two small fangs, a spiky yellow mane with brown spots on its "
     "head, huge yellow leathery wings with brown leopard spots and pointed edges, two separate flames floating above its head like "
     "fiery horns, and a long flame for a tail. Copy its design and colours exactly from <image1>. It faces the viewer head-on and glares "
     "straight into the camera with two glowing pure white eyes. Its head is large on the left half of the picture, its spotted wings "
     "spread out behind it filling the right side, the tail flame curling up at the edge. <image2> is ONLY a style and framing "
     "reference: a tight heroic close-up filling the frame and cut off by the frame edges, thick solid black outlines and black inner "
     "lines, flat cel shading with hard light and shadow shapes, strong clear volumes, on a pure black background. Do NOT draw anything "
     "from <image2>: no trainer, no cap, no ball, no orange dragon. Full colour. No text, no border.")
# v2 (Arvind 2026-11-15: "it did not quite look like Monarkhan; the flames are not attached to his body; you can't see his eyes,
# his spotted hair / monobrow covers them; he is a bit thicker than Charizard")
P2 = ("Draw the creature from <image1> as a dramatic anime title-screen close-up. Copy its design, proportions and colours exactly "
      "from <image1>: Monarkhan, a big chunky heavy-set crimson-red beast, much thicker and rounder than a slim dragon - a thick "
      "short curved neck, broad heavy shoulders, a round heavy head with a huge blunt pig snout, a big pink nose with two nostrils and "
      "two small white fangs. A shaggy spiky yellow mane with brown leopard spots sits on top of its head and hangs down over its eyes "
      "like a thick monobrow, so its eyes are completely hidden under the yellow hair - no eyes are visible at all. Two separate "
      "flames float in the air above its head, clearly NOT touching the head or the mane, with dark empty space between the flames and "
      "the head. Huge yellow wings with brown leopard spots and zigzag edges spread behind it, short thick red arms with pale claws. "
      "Its head faces the viewer head-on, large on the left half of the picture, the spotted wings fill the right side. <image2> is "
      "ONLY a style and framing reference: a tight heroic close-up filling the frame and cut off by the frame edges, thick solid black "
      "outlines and black inner lines, flat cel shading with hard light and shadow shapes, strong clear volumes, on a pure black "
      "background. Do NOT draw anything from <image2>: no trainer, no cap, no ball, no orange dragon. Full colour. No text, no border.")
# v3: v2 lost the neck and became a pig; his drawing has a thick long neck that arches up in a C before the head
P3 = ("Draw the creature from <image1> as a dramatic anime title-screen close-up. Copy its design, proportions and colours exactly "
      "from <image1>: Monarkhan, a dark crimson-red dragon-like beast that is heavier and thicker than a normal slim dragon. It has a "
      "THICK LONG NECK that arches up and over in a big C-shaped curve, exactly like in <image1>, ending in a heavy head with a big blunt "
      "pig snout, a big pink nose and two small white fangs. A shaggy spiky yellow mane with brown leopard spots sits on top of its head "
      "and hangs down over its eyes like a thick monobrow, so its eyes are completely hidden - no eyes are visible. Two separate flames "
      "float in the air above its head, NOT touching the head or the mane, with dark empty space below them. A thick fluffy yellow "
      "spotted fur collar round the base of its neck, huge yellow wings with brown leopard spots and zigzag edges spread behind it, "
      "thick red arms with pale claws. The head faces the viewer, the arched neck on the left, the wings fill the right side. <image2> "
      "is ONLY a style and framing reference: a tight heroic close-up filling the frame and cut off by the frame edges, thick solid "
      "black outlines and black inner lines, flat cel shading with hard light and shadow shapes, strong clear volumes, on a pure black "
      "background. Do NOT draw anything from <image2>: no trainer, no cap, no ball, no orange dragon. Full colour. No text, no border.")
V3 = len(sys.argv) > 1 and sys.argv[1] == 'v3'
if V3: sys.argv.pop(1); P = P3
V2 = len(sys.argv) > 1 and sys.argv[1] == 'v2'
if V2: sys.argv.pop(1); P = P2
TAG = 'comp3' if V3 else ('comp2' if V2 else 'comp')
for seed in map(int, sys.argv[1:]):
    comfy.generate(P, os.path.join(H, f'{TAG}_{seed}.png'), refs=[os.path.join(H, 'monarkhan_design.png'), os.path.join(H, 'style_ref.png')],
                   size=(1024, 768), seed=seed)
