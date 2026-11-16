"""FK retarget of a quadruped gallop onto Sabertann (replaces the paw-path IK of retarget_walk.py for the run).
The source's leg ANGLES are carried over: the upper leg's swing and the knee's bend in the body's side plane, relative to
the source's rest pose. So the gallop keeps its reach whatever our leg length is, and left and right stay symmetric.
The IK version gave the left front leg +-48 deg and the right one +-4 deg, and the body never rocked, because the
Quaternius horse run has no body pitch at all. Here the body gets a rocking-horse pitch: the nose is highest while the
hind legs push. It also gets the source's bob (about the cycle mean), and the head partly holds against the rocking.
Output is resampled to N keys (periodic spline), so one key = 2 film frames at a 2N-frame cadence.
env: AMP_F AMP_H (front/hind swing), AMP_K (knee), OFF_F OFF_H (swing centre, deg forward), ROCK (deg), ROCK_PH (source
frame of the highest nose), BOB (x source bob scaled to our legs), NOD, N
python retarget_fk.py SRC.json OUR_bones.json OUT.json [PITCH=-8]        (SRC: Quaternius CC0 horse Run, extract_anim.py)"""
import sys, json, math, os, numpy as np
from scipy.interpolate import CubicSpline
SRC, BJ, OUT = sys.argv[1:4]; PITCH = float(sys.argv[4]) if len(sys.argv) > 4 else -8.0
S = json.load(open(SRC)); B = json.load(open(BJ)); rest = {k: np.array(v) for k, v in B['rest'].items()}; par = B['parent']
E = lambda k, d: float(os.environ.get(k, d))
AMP_F, AMP_H, AMP_K = E('AMP_F', 0.8), E('AMP_H', 0.75), E('AMP_K', 0.9)
OFF_F, OFF_H = E('OFF_F', 0), E('OFF_H', 8)
ROCK, ROCK_PH, BOBA, NOD, N = E('ROCK', 7), E('ROCK_PH', 11), E('BOB', 1.0), E('NOD', 0.6), int(E('N', 18))
LEGS = {'FL': ('FrontUpLeg.L', 'FrontLowLeg.L'), 'FR': ('FrontUpLeg.R', 'FrontLowLeg.R'),
        'BL': ('BackUpLeg.L', 'BackLowLeg.L'), 'BR': ('BackUpLeg.R', 'BackLowLeg.R')}
P_ = lambda fr, b, k: np.array(fr[b][k])
def body(fr):                                                   # source body frame: hips -> shoulders, up = world Z
    a = P_(fr, 'Hips', 'head'); b = P_(fr, 'Shoulders', 'head'); f = (b - a) / np.linalg.norm(b - a)
    u = np.array([0, 0, 1.0]); u = u - f * (f @ u); u /= np.linalg.norm(u); return f, u, (P_(fr, 'Hips', 'head') + P_(fr, 'Torso', 'tail')) / 2
def ang(v, f, u): return math.degrees(math.atan2(v @ f, -(v @ u)))   # 0 = straight down, + = forward
def leg_angles(fr, f, u, up_, lo_):
    v = P_(fr, up_, 'tail') - P_(fr, up_, 'head'); w = P_(fr, lo_, 'tail') - P_(fr, lo_, 'head'); a = ang(v, f, u); return a, ang(w, f, u) - a
f0, u0, _ = body(S['rest']); NS = len(S['frames'])
REST = {k: leg_angles(S['rest'], f0, u0, *LEGS[k]) for k in LEGS}
dU = {k: [] for k in LEGS}; dL = {k: [] for k in LEGS}; bob = []; nod = []
hb = 'Head'; hd0 = np.array([P_(S['rest'], hb, 'tail') - P_(S['rest'], hb, 'head')]); hd0 = math.atan2(hd0[0] @ u0, hd0[0] @ f0)
for fr in S['frames']:
    f, u, c = body(fr)
    for k in LEGS:
        a, b = leg_angles(fr, f, u, *LEGS[k]); dU[k].append(a - REST[k][0]); dL[k].append(b - REST[k][1])
    bob.append(c[2]); hd = P_(fr, hb, 'tail') - P_(fr, hb, 'head'); nod.append(math.degrees(math.atan2(hd @ u, hd @ f) - hd0))
bob = np.array(bob) - np.mean(bob)
# our leg length / the source's (front) scales the source bob
LS = np.linalg.norm(P_(S['rest'], 'FrontUpLeg.L', 'head') - P_(S['rest'], 'FrontLowLeg.L', 'tail'))
LO = np.linalg.norm(rest['FL_up'][:3, 3] - rest['FL_lo'][:3, 3]) * 1.9
def per(vals):                                                  # periodic spline over the source cycle, sampled at N keys
    x = np.arange(NS + 1); y = np.r_[vals, vals[0]]; cs = CubicSpline(x, y, bc_type='periodic'); return cs(np.arange(N) * NS / N)
dU = {k: per(np.array(v)) for k, v in dU.items()}; dL = {k: per(np.array(v)) for k, v in dL.items()}; bob = per(bob) * LO / LS * BOBA; nod = per(np.array(nod))
LAT = np.array([1.0, 0, 0])
def rot(axis, deg):
    a = math.radians(deg); axis = axis / np.linalg.norm(axis); K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    R = np.eye(4); R[:3, :3] = np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K; return R
def about(M, piv):
    T = np.eye(4); T[:3, 3] = piv; Ti = np.eye(4); Ti[:3, 3] = -piv; return T @ M @ Ti
order = ['root', 'spine', 'head', 'jaw', 'mast', 'flag', 'stern', 'FL_up', 'FL_lo', 'BL_up', 'BL_lo', 'FR_up', 'FR_lo', 'BR_up', 'BR_lo']
piv = rest['root'][:3, 3]; frames = {}; rocks = []
for i in range(N):
    t = i / N; rock = ROCK * math.cos(2 * math.pi * (t - ROCK_PH / NS)); rocks.append(rock)     # + = nose up
    G = np.eye(4); G[2, 3] = bob[i]; G = G @ about(rot(LAT, PITCH - rock), piv)
    W = {}
    for b in order:
        if b not in rest: continue
        p = par[b]
        if p is None: W[b] = G @ rest[b]; continue
        Wb = W[p] @ np.linalg.inv(rest[p]) @ rest[b]
        if b == 'head': Wb = about(rot(LAT, -NOD * nod[i] + 0.6 * rock - 0.35 * PITCH), Wb[:3, 3]) @ Wb
        if b == 'mast': Wb = about(rot(LAT, 0.5 * ROCK * math.sin(2 * math.pi * (t - ROCK_PH / NS))), Wb[:3, 3]) @ about(rot(np.array([0, 1.0, 0]), 4 * math.sin(2 * math.pi * t + 1.0)), Wb[:3, 3]) @ Wb
        if b == 'flag': Wb = about(rot(np.array([0, 1.0, 0]), 14 * math.sin(2 * math.pi * t + 2.2)), Wb[:3, 3]) @ Wb
        if b == 'jaw': Wb = about(rot(LAT, 3 + 3 * math.sin(2 * math.pi * (t - ROCK_PH / NS))), Wb[:3, 3]) @ Wb
        if b.endswith('_up') or b.endswith('_lo'):
            k = b[:2]; front = k[0] == 'F'; latw = (W['spine'] @ np.linalg.inv(rest['spine']))[:3, :3] @ LAT
            if b.endswith('_up'): sw = (AMP_F if front else AMP_H) * dU[k][i] + (OFF_F if front else OFF_H)
            else: sw = AMP_K * dL[k][i]
            Wb = about(rot(latw, -sw), Wb[:3, 3]) @ Wb                   # rot(lat, -x) moves the paw forward by x
        W[b] = Wb
    frames[str(i + 1)] = {b: W[b].tolist() for b in W}
json.dump(dict(rest=B['rest'], parent=par, frames=frames), open(OUT, 'w'))
print('keys', N, 'front swing %.0f..%.0f' % (AMP_F * min(dU['FL'].min(), dU['FR'].min()) + OFF_F, AMP_F * max(dU['FL'].max(), dU['FR'].max()) + OFF_F),
      'hind swing %.0f..%.0f' % (AMP_H * min(dU['BL'].min(), dU['BR'].min()) + OFF_H, AMP_H * max(dU['BL'].max(), dU['BR'].max()) + OFF_H),
      'rock %.0f..%.0f' % (min(rocks), max(rocks)), 'bob %.2f..%.2f' % (bob.min(), bob.max()))
