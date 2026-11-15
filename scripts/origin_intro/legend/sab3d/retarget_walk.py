"""Retarget an existing quadruped walk (Quaternius CC0 Animal Pack Vol.2, extracted with extract_anim.py) onto Sabertann's
rig. What is carried over is the motion itself, not the skeleton: each paw's path relative to its shoulder/hip (scaled by
leg length), the body's bob and pitch, the head's nod. Our legs follow with a two-bone IK in their own bend plane.
python retarget_walk.py SRC_walk.json OUR_bones.json OUR_MODEL(.json) OUT.json [PITCH=-12] [SWAYS=1]
Source axes (Quaternius, Blender after FBX import): forward +X, left +Y, up +Z. Ours: forward -Y, left +X, up +Z."""
import sys, json, math, numpy as np
SRC, BJ, MODEL, OUT = sys.argv[1:5]; PITCH = float(sys.argv[5]) if len(sys.argv) > 5 else -12.0
S = json.load(open(SRC)); B = json.load(open(BJ)); rest = {k: np.array(v) for k, v in B['rest'].items()}; par = B['parent']
P = json.load(open(MODEL))['polys']
LEGS = {'FR': ('Bone.014', 'Bone.016'), 'FL': ('Bone.017', 'Bone.019'), 'BL': ('Bone.008', 'Bone.010'), 'BR': ('Bone.011', 'Bone.013')}
def s2o(v):                                                   # source (f=x, l=y, u=z) -> ours (f=-y, l=x, u=z)
    return np.array([v[1], -v[0], v[2]])
H = lambda fr, b, k: np.array(S['frames'][fr][b][k]) if isinstance(fr, int) else np.array(S['rest'][b][k])
# source body frame per frame: pelvis head -> chest tail gives forward/pitch; up = world Z re-orthogonalised
def body(fr):
    a = H(fr, 'Bone', 'head'); b_ = H(fr, 'Bone.001', 'tail'); fwd = (b_ - a) / np.linalg.norm(b_ - a)
    up = np.array([0, 0, 1.0]); up = up - fwd * (fwd @ up); up /= np.linalg.norm(up); left = np.cross(up, fwd)
    return (a + b_) / 2, np.column_stack([fwd, left, up])
c0, R0 = body('rest')
def pitch_of(R): return math.degrees(math.atan2(R[2, 0], math.hypot(R[0, 0], R[1, 0])))
p0 = pitch_of(R0)
LSRC = {k: np.linalg.norm(H('rest', u, 'head') - H('rest', f, 'head')) for k, (u, f) in LEGS.items()}
# our paws: the lowest model point that follows each lower-leg bone
paw = {}
for k in LEGS:
    lo = k + '_lo'; vs = [np.array(q) for p in P for q, vb in zip(p['p'], p['vb']) if vb == lo]; paw[k] = min(vs, key=lambda q: q[2])
LOUR = {k: np.linalg.norm(rest[k + '_up'][:3, 3] - paw[k]) for k in LEGS}
LAT = np.array([1.0, 0, 0])
def rot(axis, deg):
    a = math.radians(deg); axis = axis / np.linalg.norm(axis); K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    R = np.eye(4); R[:3, :3] = np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K; return R
def about(M, piv):
    T = np.eye(4); T[:3, 3] = piv; Ti = np.eye(4); Ti[:3, 3] = -piv; return T @ M @ Ti
def rot_between(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b); v = np.cross(a, b); c = float(a @ b)
    if np.linalg.norm(v) < 1e-9: return np.eye(3)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]); return np.eye(3) + K + K @ K * (1 / (1 + c))
order = ['root', 'spine', 'head', 'jaw', 'mast', 'flag', 'stern', 'FL_up', 'FL_lo', 'BL_up', 'BL_lo', 'FR_up', 'FR_lo', 'BR_up', 'BR_lo']
scale_body = LOUR['FL'] / LSRC['FL']
frames = {}; N = len(S['frames'])
for i in range(N):
    t = i / N; c, R = body(i)
    bob = (c - c0)[2] * scale_body; dpitch = pitch_of(R) - p0
    sp = rest['spine'][:3, 3]
    G = np.eye(4); G[2, 3] = bob; G = G @ about(rot(LAT, PITCH - dpitch), sp)        # climb + the source's pitch change
    # head nod: source head bone direction relative to the body, pitch only
    hd0 = R0.T @ (H('rest', 'Bone.003', 'tail') - H('rest', 'Bone.003', 'head')); hd = R.T @ (H(i, 'Bone.003', 'tail') - H(i, 'Bone.003', 'head'))
    nod = math.degrees(math.atan2(hd[2], hd[0]) - math.atan2(hd0[2], hd0[0]))
    W = {}
    for b in order:
        if b not in rest: continue
        p = par[b]
        if p is None: W[b] = G @ rest[b]; continue
        Wb = W[p] @ np.linalg.inv(rest[p]) @ rest[b]
        if b == 'head': Wb = about(rot(LAT, -nod - 0.35 * PITCH), Wb[:3, 3]) @ Wb
        if b == 'mast': Wb = about(rot(np.array([0, 1.0, 0]), 6 * math.sin(2 * math.pi * t + 1.0)), Wb[:3, 3]) @ Wb
        if b == 'flag': Wb = about(rot(np.array([0, 1.0, 0]), 16 * math.sin(2 * math.pi * t + 2.2)), Wb[:3, 3]) @ Wb
        if b == 'jaw': Wb = about(rot(LAT, 4 + 4 * math.sin(2 * math.pi * t)), Wb[:3, 3]) @ Wb
        W[b] = Wb
    # legs: paw target = our shoulder/hip + the source paw offset (in the source body frame) scaled to our leg length
    for k, (su, sf) in LEGS.items():
        up_, lo_ = k + '_up', k + '_lo'
        off = R.T @ (H(i, sf, 'head') - H(i, su, 'head')) / LSRC[k]                    # source body frame, unit leg
        off0 = R0.T @ (H('rest', sf, 'head') - H('rest', su, 'head')) / LSRC[k]
        Gb = W['spine'] @ np.linalg.inv(rest['spine'])                                  # our body motion
        A = W[up_][:3, 3]; restpaw_w = (Gb @ np.append(paw[k], 1))[:3]
        # rest-relative: our rest paw offset + (source offset - source rest offset), all in our body frame
        T = restpaw_w + Gb[:3, :3] @ (s2o(off - off0) * LOUR[k])
        Mu = W[up_]; Ml = W[lo_]; B_ = Ml[:3, 3]; C = (Ml @ np.linalg.inv(rest[lo_]) @ np.append(paw[k], 1))[:3]
        l1 = np.linalg.norm(B_ - A); l2 = np.linalg.norm(C - B_); d = np.linalg.norm(T - A)
        d = min(max(d, abs(l1 - l2) + 1e-4), l1 + l2 - 1e-4); T = A + (T - A) / (np.linalg.norm(T - A) + 1e-9) * d
        ax = (T - A) / d; pole = B_ - A - ax * ((B_ - A) @ ax); pole /= np.linalg.norm(pole) + 1e-9
        a_ = (l1 * l1 - l2 * l2 + d * d) / (2 * d); h_ = math.sqrt(max(l1 * l1 - a_ * a_, 0)); Bn = A + ax * a_ + pole * h_
        R1 = np.eye(4); R1[:3, :3] = rot_between(B_ - A, Bn - A); R1 = about(R1, A)
        Mu2 = R1 @ Mu; Ml1 = R1 @ Ml; C1 = (Ml1 @ np.linalg.inv(rest[lo_]) @ np.append(paw[k], 1))[:3]
        R2 = np.eye(4); R2[:3, :3] = rot_between(C1 - Bn, T - Bn); R2 = about(R2, Bn)
        W[up_] = Mu2; W[lo_] = R2 @ Ml1
    frames[str(i + 1)] = {b: W[b].tolist() for b in W}
json.dump(dict(rest=B['rest'], parent=par, frames=frames), open(OUT, 'w')); print('frames', N, 'leg scale', {k: round(LOUR[k] / LSRC[k], 2) for k in LEGS})
