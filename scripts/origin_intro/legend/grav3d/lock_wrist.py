"""Gravriel's cutlass hangs ~2 units below the right wrist, so the motion library's wrist turns swing it off his hand
(v6 preview, Spell_Simple). The right hand is made rigid with the forearm in every frame.
python lock_wrist.py G.json [HAND=DEF-hand.R] [FORE=DEF-forearm.R]   (in place)"""
import sys, json
import numpy as np
G = sys.argv[1]; H = sys.argv[2] if len(sys.argv) > 2 else 'DEF-hand.R'; F = sys.argv[3] if len(sys.argv) > 3 else 'DEF-forearm.R'
J = json.load(open(G)); B = J['bind']; rel = np.linalg.inv(np.array(B[F])) @ np.array(B[H])
for f, m in J['frames'].items(): m[H] = (np.array(m[F]) @ rel).tolist()
json.dump(J, open(G, 'w')); print('wrist locked', H, 'to', F, 'in', len(J['frames']), 'frames')
