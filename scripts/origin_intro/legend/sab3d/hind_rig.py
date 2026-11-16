"""Re-rig Sabertann's hind legs (Arvind: "bakbeina er ikke så bra"). The high-poly armature's thigh bone covers the whole
round haunch (1.7 units front to back), and the low-poly leg is a thick stump. Its shin and the big flat paw are one rigid
part. Swinging that thigh dragged the flank into a stretched slab, and the paw could only paddle.
Same two bones per hind leg (the matrix slots are all used), new joints:
  haunch (z >= 1.0)            -> the body (spine); its lower edge blends into the leg through the hip helper
  leg column (0.3 < z < 1.0)   -> B?_up, pivot at the top of the leg column (where the leg leaves the haunch)
  paw (z <= 0.3, claws)        -> B?_lo, pivot at the ankle, so the paw can roll flat, push off and flick back
python hind_rig.py pt16 bones_rest14.json pt17 bones_rest17.json"""
import sys, json, os, shutil, numpy as np
from collections import Counter
SRC, BJ, DST, BJO = sys.argv[1:5]
D = json.load(open(SRC + '.json')); B = json.load(open(BJ)); rest = {k: np.array(v) for k, v in B['rest'].items()}
import os as _o
HIP_Z, ANK_Z = float(_o.environ.get('HIP_Z', '1.0')), float(_o.environ.get('ANK_Z', '0.3'))
LEG = {'L': ('BL_up', 'BL_lo'), 'R': ('BR_up', 'BR_lo')}
col = {s: [] for s in LEG}
for p in D['polys']:
    for q, vb in zip(p['p'], p['vb']):
        for s, (u, l) in LEG.items():
            if (p['part'] == 'BodyLeg' and (q[0] > 0) == (s == 'L') or vb in (u, l)) and ANK_Z < q[2] < HIP_Z: col[s].append(q)
piv = {}
for s, (u, l) in LEG.items():
    c = np.mean(col[s], 0); piv[u] = np.array([c[0], c[1], HIP_Z]); piv[l] = np.array([c[0], c[1] + 0.05, ANK_Z])
    print(s, 'leg column centre', np.round(c, 2), 'hip pivot', np.round(piv[u], 2), 'ankle pivot', np.round(piv[l], 2))
SPLIT_LEGS = any(p['part'] == 'BodyLeg' for p in D['polys'])     # export_parts7: the hind legs are their own part
def reassign_part(q, vb, vw, part):
    s = 'L' if q[0] > 0 else 'R'; u, l = LEG[s]; z = q[2]
    if part == 'Claw': return (l, [l, 0.0]) if vb in (u, l) else (vb, vw)   # hind claws ride on the paw
    if part != 'BodyLeg':
        return ('spine', ['spine', 0.0]) if vb in (u, l) else (vb, vw)   # the haunch stays with the body
    if z > ANK_Z: return u, (['spine', 0.35] if z > HIP_Z - 0.15 else ([l, 0.3] if z < ANK_Z + 0.15 else [u, 0.0]))
    return l, ([u, 0.35] if z > ANK_Z - 0.15 else [l, 0.0])
def reassign(q, vb, vw):
    for s, (u, l) in LEG.items():
        if vb not in (u, l): continue
        z = q[2]
        if z >= HIP_Z: return 'spine', ([u, 0.3] if z < HIP_Z + 0.2 else ['spine', 0.0])
        if z > ANK_Z:
            if z > 0.62: return u, ['spine', 0.3]
            if z < 0.45: return u, [l, 0.3]
            return u, [u, 0.0]
        return l, ([u, 0.35] if z > 0.15 else [l, 0.0])
    return vb, vw
moved = Counter()
for p in D['polys']:
    nv = []; nw = []
    for q, vb, vw in zip(p['p'], p['vb'], p.get('vw', [None] * len(p['p']))):
        b2, w2 = reassign_part(q, vb, vw, p['part']) if SPLIT_LEGS else reassign(q, vb, vw); nv.append(b2); nw.append(w2)
        if b2 != vb: moved[(vb, b2)] += 1
    p['vb'] = nv; p['vw'] = nw
    if any(b in ('BL_up', 'BL_lo', 'BR_up', 'BR_lo') for b in nv) or p['b'] in ('BL_up', 'BL_lo', 'BR_up', 'BR_lo'):
        p['b'] = Counter(nv).most_common(1)[0][0]
print('moved', dict(moved))
json.dump(D, open(DST + '.json', 'w'))
for f in os.listdir(os.path.dirname(os.path.abspath(SRC)) or '.'):
    base = os.path.basename(SRC)
    if f.startswith(base + '_') and not f.endswith('.json'):
        shutil.copy(os.path.join(os.path.dirname(os.path.abspath(SRC)), f), os.path.join(os.path.dirname(os.path.abspath(DST)), f.replace(base + '_', os.path.basename(DST) + '_', 1)))
for b, t in piv.items():
    M = rest[b].copy(); M[:3, 3] = t; B['rest'][b] = M.tolist()
json.dump(B, open(BJO, 'w')); print('ok')
