"""A walk-on-air cycle for Sabertann's rig, computed from the rest pose (bones.json from export_bones.py): a lateral-sequence
walk (left hind, left fore, right hind, right fore a quarter apart), each leg swinging about the body's sideways axis with
the lower leg folding while it swings forward; the body pitched nose-up to climb, bobbing twice a cycle; the head
countering the bob; mast and flag swaying. Writes the same JSON layout with frames 1..N.
python walkcycle.py bones.json OUT.json [N=12] [PITCH=14] [SWING=30] [FOLD=40]"""
import sys, json, math, numpy as np
B = json.load(open(sys.argv[1])); OUT = sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 12; PITCH = float(sys.argv[4]) if len(sys.argv) > 4 else 14
SWING = float(sys.argv[5]) if len(sys.argv) > 5 else 30; FOLD = float(sys.argv[6]) if len(sys.argv) > 6 else 40
rest = {k: np.array(v) for k, v in B['rest'].items()}; par = B['parent']
LAT = np.array([1.0, 0, 0])                                     # Blender: the model faces -Y, so X is sideways
def rot(axis, deg):
    a = math.radians(deg); axis = axis / np.linalg.norm(axis); K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    R = np.eye(4); R[:3, :3] = np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K; return R
def about(M_world_rot, pivot):
    T = np.eye(4); T[:3, 3] = pivot; Ti = np.eye(4); Ti[:3, 3] = -pivot; return T @ M_world_rot @ Ti
PHASE = {'BL': 0.0, 'FL': 0.25, 'BR': 0.5, 'FR': 0.75}
order = ['root', 'spine', 'head', 'jaw', 'mast', 'flag', 'stern', 'FL_up', 'FL_lo', 'BL_up', 'BL_lo', 'FR_up', 'FR_lo', 'BR_up', 'BR_lo']
frames = {}
for k in range(N):
    t = k / N; W = {}
    # body: climb pitch about the spine origin, bob, a little roll with the gait
    sp = rest['spine'][:3, 3]
    body = about(rot(LAT, PITCH + 2.5 * math.sin(4 * math.pi * t)), sp) @ about(rot(np.array([0, 1.0, 0]), 3 * math.sin(2 * math.pi * t)), sp)
    lift = np.eye(4); lift[2, 3] = 0.06 * math.sin(4 * math.pi * t)
    G = lift @ body                                               # world motion applied to the whole rig
    extra = {}
    extra['head'] = -0.6 * (2.5 * math.sin(4 * math.pi * t))      # counter the bob
    extra['mast'] = 4 * math.sin(2 * math.pi * t + 1.0)
    extra['flag'] = 10 * math.sin(2 * math.pi * t + 2.0)
    extra['jaw'] = 4 + 4 * math.sin(2 * math.pi * t)
    for leg, ph in PHASE.items():
        u = (t + ph) % 1.0                                         # 0..0.6 stance (paw pushes back), 0.6..1 swing (forward)
        if u < 0.6: sw = SWING * (0.5 - u / 0.6); fold = 0
        else: v = (u - 0.6) / 0.4; sw = SWING * (-0.5 + v); fold = FOLD * math.sin(math.pi * v)
        hind = leg[0] == 'B'
        extra[leg + '_up'] = sw * (-1 if hind else 1)
        extra[leg + '_lo'] = fold * (1 if hind else -1)
    for b in order:
        if b not in rest: continue
        p = par[b]
        if p is None: W[b] = G @ rest[b]; continue
        local = np.linalg.inv(rest[p]) @ rest[b]
        Wb = W[p] @ local
        if b in extra:
            Wb = about(rot(LAT if b not in ('mast', 'flag') else np.array([0, 1.0, 0]), extra[b]), Wb[:3, 3]) @ Wb
        W[b] = Wb
    frames[str(k + 1)] = {b: W[b].tolist() for b in W}
json.dump(dict(rest=B['rest'], parent=par, frames=frames), open(OUT, 'w')); print('frames', N)
