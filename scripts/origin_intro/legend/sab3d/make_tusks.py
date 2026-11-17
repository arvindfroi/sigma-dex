"""New sabre tusks for the film model (2026-11-17, Arvind: "the teeth are the most important to get right"). The export
left each tusk as a 4-triangle wedge. Rebuilt as tapered, bowed tubes measured on Arvind's turnaround (mv/views,
fitted scale/offset from tex_views.py):
  front view: root centre x -0.374 at z 2.39 (under the lip), bowing out to -0.38 halfway, tip x -0.297 at z 1.43
  (tips turn in), root 0.19 wide; side view: root y -2.77, tip y -2.69 (a little back), 0.15 thick, front edge convex
Each tusk: K sides x rings from the root (embedded in the lip) to a closed point; bone 'head' like the old tusks.
Each vertex carries 'tu' = (u around: 0.5 + 0.5 sin(angle), inner side = 1; v along the tusk 0..1) for the tusk
texture region tex_views.py cuts from the drawing's own tusk.
python make_tusks.py IN_BASE OUT_BASE      (copies IN_BASE_tex*.png / _albedo*.png to OUT_BASE_*)"""
import sys, os, json, math, shutil, glob
import numpy as np
IB, OB = sys.argv[1:3]
E = lambda k, d: float(os.environ.get(k, d))
J = json.load(open(IB + '.json')); P = J['polys']
old = [p for p in P if p.get('part') == 'Tusk']; keep = [p for p in P if p.get('part') != 'Tusk']
proto = dict(old[0]) if old else dict(P[0])
K = int(E('TUSK_SIDES', 6)); TS = [float(x) for x in os.environ.get('TUSK_RINGS', '0,0.25,0.5,0.75,0.92').split(',')]
Z0, Z1 = E('TUSK_Z0', 2.42), E('TUSK_Z1', 1.42); RX, RY = E('TUSK_RX', 0.095), E('TUSK_RY', 0.075); TAPER = E('TUSK_TAPER', 0.7)
def centre(t):                                                  # the tusk at x < 0; the other is its mirror
    x = -0.374 - 0.101 * t + 0.178 * t * t                      # front view: bows out, tip turns in
    y = -2.77 - 0.16 * t + 0.24 * t * t                         # side view: front edge convex, tip a little back
    return np.array([x, y, Z0 + (Z1 - Z0) * t])
new = []
for sgn in (-1, 1):                                             # -1: the tusk at x < 0, +1: its mirror at x > 0
    def C(t): c = centre(t); c[0] = abs(c[0]) * sgn; return c
    rings = []
    for t in TS:
        r = (1 - t) ** TAPER; c = C(t); ring = []
        for k in range(K):
            th = 2 * math.pi * k / K                            # 0 = facing front (-y), +90 deg = toward +x
            off = np.array([RX * r * math.sin(th), -RY * r * math.cos(th), 0.0])
            inner = -sgn * math.sin(th)                         # +1 on the side toward the face's centre
            ring.append((c + off, off / max(np.linalg.norm(off), 1e-9), (0.5 + 0.5 * inner, t)))
        rings.append(ring)
    tip = (C(1.0), np.array([0, 0, -1.0]), (0.5, 1.0))
    def tri(a, b, c):
        q = dict(proto); q['p'] = [list(map(float, v[0])) for v in (a, b, c)]; q['n'] = [list(map(float, v[1])) for v in (a, b, c)]
        q['tu'] = [list(v[2]) for v in (a, b, c)]; q['uv'] = [[0.5, 0.5]] * 3; q['part'] = 'Tusk'; q['b'] = 'head'; q['vb'] = ['head'] * 3
        q['vw'] = [['head', 1.0]] * 3; new.append(q)
    for i in range(len(rings) - 1):
        for k in range(K):
            a, b = rings[i][k], rings[i][(k + 1) % K]; c, d = rings[i + 1][k], rings[i + 1][(k + 1) % K]
            tri(a, c, b); tri(b, c, d)
    for k in range(K): tri(rings[-1][k], tip, rings[-1][(k + 1) % K])
J['polys'] = keep + new
json.dump(J, open(OB + '.json', 'w'))
for f in glob.glob(IB + '_tex*.png') + glob.glob(IB + '_albedo*.png'): shutil.copy(f, OB + f[len(IB):])
print('tusks: old', len(old), 'new', len(new), 'polys', len(J['polys']))
