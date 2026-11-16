"""Replace Ho-Oh in one shot of the Clear Bell film with our rigged creature, the way the shot was built: our skeleton on
Ho-Oh's joints (each bone takes a Ho-Oh node that stores its matrix), our textured low-poly skinned rigidly to the bones,
and a new joint animation: the environment keeps its own tracks; Ho-Oh's joint1 keeps its flight path; our bones play a
pose cycle from the Blender rig on top of it. Writes the model and its BCA back into the NARC (LZ10).
python legend/rig3d.py NARC_IN NARC_OUT BASE BONES.json MODEL BCA [SIZE=340] [CYCLE=1,2,3,4] [STEP=5]   (env ROLL=1)"""
import math, sys, os, re, json, struct, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from narc import unpack, pack
from lz11 import lz11_dec
from lz import lz10_enc
import nitro, geom, bca_write
SRC, DST, BASE, BJ, MM, BM = sys.argv[1:7]; MM, BM = int(MM), int(BM)
SIZE = float(sys.argv[7]) if len(sys.argv) > 7 else 340.0
CYC = [int(x) for x in (sys.argv[8] if len(sys.argv) > 8 else '1,2,3,4').split(',')]; STEP = int(sys.argv[9]) if len(sys.argv) > 9 else 5
HOOH = re.compile(r'^(hou_(?!tail_[lp])|ho_head_top|ho_tail)')  # hou_tail_l/_l2 = Ho-Oh's glow disc (~600 units, joint27),
GLOWTEX = re.compile(r'^hou_tail_[lp]')                           # hou_tail_p = sparkle quads: kept, on Ho-Oh's own joints
TEST = set(os.environ.get('RIGTEST', '').split(','))              # bisect switches: noshapes, nomats, notex, rigid, nomtx
KEEP_SLOT = 30                                                   # our shapes save/restore the current matrix here (see below)
F = unpack(open(SRC, 'rb').read()); D = lambda i: lz11_dec(F[i]) if F[i][:1] == b'\x11' else F[i]
d = bytearray(D(MM)); r = nitro.read_bmd(bytes(d)); m = r['models'][0]; mats = m['mats']; up = m['info']['up']
anim = geom.read_bca(D(BM))[0]; nf = anim['nframes']; names = [n for n, _ in m['nodes']]
# hierarchy and matrix slots from the render commands
parent = {}; slot = {}
for op, p in m['rcmds']:
    if op in (6, 0x26, 0x46, 0x66):
        parent[p[0]] = p[1]
        if op in (0x26, 0x66): slot[p[0]] = p[3]
order = [p for op, p in m['rcmds'] if op in (6, 0x26, 0x46, 0x66)]
hooh = [i for i, n in enumerate(names) if re.match(r'joint\d+$', n)]
j1 = names.index('joint1')
# our rig
B = json.load(open(BJ)); rest = {k: np.array(v) for k, v in B['rest'].items()}
MERGE = {'jaw': 'head', 'flag': 'mast', 'stern': 'spine', 'root': 'spine'}             # fewer bones: matrix slots are scarce
bnames = [b for b in B['rest'] if b not in MERGE]
# smooth joints (Arvind: the run must look right): a point between two connected bones follows a HELPER bone that is the
# halfway rotation of both about their joint, so knees, elbows, shoulders, hips and the neck bend instead of tearing
POLYS_ = json.load(open(BASE + '.json'))['polys']
PAR = {b: (MERGE.get(B['parent'][b], B['parent'][b]) if B['parent'].get(b) else None) for b in B['rest']}
SMOOTH = os.environ.get('SMOOTH', '1') == '1'
def eff_bone(a, vw):
    if not SMOOTH or not vw: return a
    b2 = MERGE.get(vw[0], vw[0]); w = vw[1]
    if w < 0.25 or b2 == a or 'mast' in (a, b2): return a           # the mast is stiff: no helper there
    if PAR.get(b2) == a: return f'h:{a}:{b2}'
    if PAR.get(a) == b2: return f'h:{b2}:{a}'
    return a
HELP = sorted({eff_bone(MERGE.get(v, v), vw) for p_ in POLYS_ for v, vw in zip(p_.get('vb', []), p_.get('vw', [None] * len(p_['p'])))
               if eff_bone(MERGE.get(v, v), vw).startswith('h:')})
BASEB = list(bnames); bnames = BASEB + HELP
print('helpers', HELP)
pos = {}
for k_, (op, p) in enumerate(m['rcmds']):
    if op in (6, 0x26, 0x46, 0x66) and p[0] not in pos: pos[p[0]] = k_
# joints that carry the glow shapes keep Ho-Oh's own animation and are not taken for our bones
glowj = set(); _own = {}; _cur = None; _mat = None
for op, p in m['rcmds']:
    if op in (0x26, 0x66): _own[p[3]] = p[0]
    if op in (6, 0x26, 0x46, 0x66): _cur = p[0]
    if op == 3: _cur = _own.get(p[0])
    if op in (4, 0x24, 0x44): _mat = p[0]
    if op == 5 and GLOWTEX.search(str(mats[_mat].get('tex', ''))) and _cur is not None: glowj.add(_cur)
_anc = set()
for gj in glowj:
    while gj in parent and parent[gj] != gj: _anc.add(gj); gj = parent[gj]
glowj |= _anc
cands = sorted([i for i in hooh if i != j1 and i in slot and i not in glowj], key=lambda i: pos[i])
assert len(cands) >= len(bnames), (len(cands), len(bnames))
bnode = {b: cands[k] for k, b in enumerate(bnames)}
# model frame: Blender (fwd -Y, up +Z) -> joint1 local, as found in the film tests
Fx = np.array([[0, -1, 0], [-1, 0, 0], [0, 0, -1]], float)
for _ in range(int(os.environ.get('ROLL', 1))): Fx = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float) @ Fx
polys = json.load(open(BASE + '.json'))['polys']
tris = []
for p in polys:
    vb = [eff_bone(MERGE.get(x, x), vw) for x, vw in zip(p.get('vb', [p['b']] * len(p['p'])), p.get('vw', [None] * len(p['p'])))]
    for k in range(1, len(p['p']) - 1):
        nn = p.get('n'); nn = [nn[0], nn[k], nn[k + 1]] if nn else [None] * 3
        tris.append(([p['p'][0], p['p'][k], p['p'][k + 1]], [p['uv'][0], p['uv'][k], p['uv'][k + 1]], MERGE.get(p['b'], p['b']), p.get('g', 0), [vb[0], vb[k], vb[k + 1]], nn))
allp = np.array([t[0] for t in tris]).reshape(-1, 3); cen = (allp.max(0) + allp.min(0)) / 2
s = SIZE / ((allp @ Fx.T).max(0) - (allp @ Fx.T).min(0)).max()
def H(Mb):                                                    # Blender bone world -> transform under joint1 (no scale)
    out = np.eye(4); out[:3, :3] = Fx @ Mb[:3, :3]; out[:3, 3] = s * Fx @ (Mb[:3, 3] - cen); return out
def orth(Rm):
    u, _, vt = np.linalg.svd(Rm); return u @ vt
# pose at film frame f: interpolate between cycle poses (rotation by slerp through quaternions)
from scipy.spatial.transform import Rotation as Rot, Slerp
pose = {}
for b in BASEB:
    Ms = [np.array(B['frames'][str(c)][b]) for c in CYC] + [np.array(B['frames'][str(CYC[0])][b])]
    rots = Rot.from_matrix([orth(M[:3, :3]) for M in Ms]); sl = Slerp(np.arange(len(Ms)), rots); tr = np.array([M[:3, 3] for M in Ms])
    pose[b] = (sl, tr)
PH = None                                                   # walk phase per film frame (set from the distance travelled)
def bone_pose(b, x):
    x = x % len(CYC); sl, tr = pose[b]; i = int(x); w = x - i
    M = np.eye(4); M[:3, :3] = sl([x]).as_matrix()[0]; M[:3, 3] = tr[i] * (1 - w) + tr[i + 1] * w; return M
SNAP = os.environ.get('PHASE_SNAP', '1') == '1'                  # step through the cycle's own keys: poses repeat, the animation stays small
def bone_world(b, f): return bone_pose(b, (math.floor(PH[f] + 1e-6) if SNAP else PH[f]) if PH is not None else f / STEP)
# evaluate the original worlds (environment parents and joint1's path)
def worlds(f):
    trs = geom.node_trs(m, anim, f); W = {}; ssc = m['info']['scaling'] == 1
    for p in order:
        i, pa = p[0], p[1]; t, rr, sc = trs[i]; T = np.eye(4); T[:3, 3] = t; R = np.eye(4); R[:3, :3] = rr; S = np.diag(list(sc) + [1])
        L = T @ R @ S
        if ssc and pa != i: L = T @ np.diag([1 / x if x else 0 for x in trs[pa][2]] + [1]) @ R @ S
        W[i] = (W[pa] if pa != i and pa in W else np.eye(4)) @ L
    return W, trs
# our own root along Ho-Oh's path: facing where it goes (sideways part of the motion), upright to the scene's up (+Y),
# no banking; Ho-Oh's scale on joint1 is kept so sizes match
P1 = []; WJ = []
for f in range(nf):
    Wf, _ = worlds(f); WJ.append(Wf[j1]); P1.append(Wf[j1][:3, 3])
P1 = np.array(P1); sig = np.cbrt(np.linalg.det(WJ[0][:3, :3]))
# Arvind: the walk must be correct -> the cycle advances with the distance travelled, so a paw in stance stays put in the
# world (no gliding) and he stands still when Ho-Oh hovers. Stride and stance share are measured from the cycle itself.
if os.environ.get('WALKDIST', '1') == '1':
    FEET_ = ('FL_lo', 'FR_lo', 'BL_lo', 'BR_lo'); _pv = {}
    for b in FEET_:
        vs = [np.array(v) for t in tris for v, vb in zip(t[0], t[4]) if vb == b]
        v = min(vs, key=lambda q: q[2]); _pv[b] = (np.linalg.inv(H(rest[b])) @ np.append(s * Fx @ (v - cen), 1))[:3]
    xs = np.linspace(0, len(CYC), 193)[:-1]; strides = []; duties = []; STANCE = {}
    for b in FEET_:
        Q = np.array([(H(bone_pose(b, x)) @ np.append(_pv[b], 1))[:3] for x in xs])   # joint1-local: x forward, y up
        back = np.diff(np.r_[Q[:, 0], Q[0, 0]]) < 0                                   # stance: the paw moves backwards
        STANCE[b] = back; strides.append(-np.sum(np.minimum(np.diff(np.r_[Q[:, 0], Q[0, 0]]), 0)) * sig); duties.append(back.mean())
    STRIDE = float(np.mean(strides)); DUTY = float(np.mean(duties)); per_cycle = STRIDE / max(DUTY, 1e-3)
    sp = np.r_[0, np.linalg.norm(np.diff(P1, axis=0), axis=1)]
    MINF = float(os.environ.get('MIN_CYCLE_FRAMES', '20'))      # never faster than one cycle per MINF frames (sky shot swoops)
    PH = np.cumsum(np.minimum(sp / per_cycle * len(CYC), len(CYC) / MINF))
    if os.environ.get('CADENCE'):                                # Arvind: a steady, heavier gallop like Ho-Oh's steady wingbeat
        PH = np.arange(nf) * len(CYC) / float(os.environ['CADENCE'])
    print('walk: stride %.2f duty %.2f -> %.2f world units per cycle, %.1f cycles in the shot' % (STRIDE, DUTY, per_cycle, PH[-1] / len(CYC)))
def in_stance(b, f):
    if PH is None: return False
    k = int((PH[f] % len(CYC)) / len(CYC) * len(STANCE[b])) % len(STANCE[b]); return bool(STANCE[b][k])
UPB = {'FL_lo': 'FL_up', 'FR_lo': 'FR_up', 'BL_lo': 'BL_up', 'BR_lo': 'BR_up'}
def _rot_between(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b); v = np.cross(a, b); c = float(a @ b)
    if np.linalg.norm(v) < 1e-9: return np.eye(3)
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]); return np.eye(3) + K + K @ K * (1 / (1 + c))
def _about(R, piv):
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = piv - R @ piv; return M
_lock = {}
def plant_targets():
    # world plant point per foot per frame (None when the paw is free); 4-frame ease back after the stance
    out = {}
    for b in UPB:
        tg = [None] * nf; cur = None; ease = 0; last = None
        for f in range(nf):
            free = (root_frame(f) @ H(bone_world(b, f)) @ np.append(_pv[b], 1))[:3]
            if in_stance(b, f):
                if cur is None: cur = free
                tg[f] = ('lock', cur); last = cur
            else:
                if cur is not None: ease = 4; cur = None
                if ease and last is not None: tg[f] = ('ease', last, ease / 5.0); ease -= 1
        out[b] = tg
    return out
def leg_L(f):
    # bone matrices (joint1-local) of the four legs with the paws locked: analytic two-bone IK in the leg's own bend plane
    res = {}
    if PH is None or os.environ.get('FOOTLOCK', '1') != '1': return res
    RFi = np.linalg.inv(root_frame(f))
    for lo, upb in UPB.items():
        Mu = H(bone_world(upb, f)); Ml = H(bone_world(lo, f))
        A = Mu[:3, 3]; B_ = Ml[:3, 3]; C = (Ml @ np.append(_pv[lo], 1))[:3]
        t = PLANT[lo][f]
        if t is None: continue
        T = (RFi @ np.append(t[1], 1))[:3]
        if t[0] == 'ease': T = T * t[2] + C * (1 - t[2])
        l1 = np.linalg.norm(B_ - A); l2 = np.linalg.norm(C - B_); d = np.linalg.norm(T - A)
        d = min(max(d, abs(l1 - l2) + 1e-4), l1 + l2 - 1e-4); T = A + (T - A) / (np.linalg.norm(T - A) + 1e-9) * d
        ax = (T - A) / d; pole = B_ - A - ax * ((B_ - A) @ ax); pole /= np.linalg.norm(pole) + 1e-9
        a_ = (l1 * l1 - l2 * l2 + d * d) / (2 * d); h_ = np.sqrt(max(l1 * l1 - a_ * a_, 0)); Bn = A + ax * a_ + pole * h_
        R1 = _about(_rot_between(B_ - A, Bn - A), A); Mu2 = R1 @ Mu; Ml1 = R1 @ Ml; C1 = (Ml1 @ np.append(_pv[lo], 1))[:3]
        R2 = _about(_rot_between(C1 - Bn, T - Bn), Bn); res[upb] = Mu2; res[lo] = R2 @ Ml1
    return res
# heading = the way Ho-Oh itself faces (its +X, flattened), smoothed: steady while it hovers, no banking or pitch.
# (the travel direction flips at random when Ho-Oh hovers in place, which made him turn suddenly)
YAW = []
for f in range(nf):
    v = WJ[f][:3, :3] @ np.array([1.0, 0, 0]); YAW.append(np.arctan2(v[2], v[0]))
YAW = np.unwrap(np.array(YAW)); K = 6
YAW = np.array([YAW[max(0, f - K):f + K + 1].mean() for f in range(nf)])
def root_frame(f):
    fwd = np.array([np.cos(YAW[f]), 0, np.sin(YAW[f])]); upv = np.array([0, 1.0, 0]); side = np.cross(fwd, upv)
    M = np.eye(4); M[:3, :3] = sig * np.column_stack([fwd, upv, side]); M[:3, 3] = P1[f]; return M
PATHFRAME = os.environ.get('PATHFRAME', '1') == '1'
SUP = np.diag([up, up, up, 1.0])
PLANT = plant_targets() if PH is not None else None   # needs root_frame
# Arvind: no glow around him; Ho-Oh's glow disc (joint27) becomes a ripple in the air under each paw that touches down
RIPPLE = os.environ.get('RIPPLE', '1') == '1' and 'joint27' in names
if RIPPLE:
    j27 = names.index('joint27'); FEET = ('FL_lo', 'FR_lo', 'BL_lo', 'BR_lo'); RMAX = float(os.environ.get('RIPPLE_R', '12')); RLOC = 0.255
    # Ho-Oh's disc (shape polygon13) is a fan of radius 0.254 in the joint's YZ plane, at x = -0.187: it sits 0.73 x its
    # radius below the joint. joint27 hangs under joint1, whose 0.1 scale it inherits (measured in the game: the drawn ring
    # is sig x rad), so the drop is sig x 0.73 x rad; lifted back here. The bright line of the texture is at 0.72 of the radius.
    DISC_X, VIS = -0.187, 0.72
    PSC = [sig]                                            # the disc joint's parent scale: joint1's 0.1, or 1 on the world root
    def ring_matrix(pos, rad, f, disc=0):
        # drawn ring radius = sig x rad whatever the parent (the size approved in v25..v29); the disc drop lifted back
        RF_ = root_frame(f); upw = np.array([0, 1.0, 0]); fwd = RF_[:3, 0] / np.linalg.norm(RF_[:3, 0]); fwd = fwd - upw * (fwd @ upw); fwd /= np.linalg.norm(fwd)
        sc_ = sig * rad / (RLOC * up * PSC[0]); M = np.eye(4); M[:3, :3] = np.column_stack([upw, fwd, np.cross(upw, fwd)]) * sc_
        M[:3, 3] = pos - upw * (PSC[0] * sc_ * up * DISC_X)
        if disc == 1: M[:3, :3] *= up        # disc 2 is restored after the POSSCALE command (0x0b) of disc 1: posScale folded in
        return M
    pvf = {}
    for b in FEET:                                          # the paw: the lowest model point that follows this bone
        vs = [np.array(v) for t in tris for v, vb in zip(t[0], t[4]) if vb == b]
        v = min(vs, key=lambda q: q[2]); pvf[b] = (np.linalg.inv(H(rest[b])) @ np.append(s * Fx @ (v - cen), 1))[:3]
    def foot_world(b, f):
        LG = leg_L(f); M_ = LG[b] if b in LG else H(bone_world(b, f)); return (root_frame(f) @ M_ @ np.append(pvf[b], 1))[:3]
    def foot_h(b, f): return (np.linalg.inv(root_frame(f)) @ np.append(foot_world(b, f), 1))[1]
    # Arvind (v29): "it should look like a ripple comes where he steps from: every time he pushes off to run/jump forward"
    # and "why not on every paw when they land on the air". So every paw makes its own ring at its push-off: the last frame
    # it is down (its contact = the lowest quarter of its own height range; not the most forward point, the front paw is
    # furthest forward high in its reach), at the spot it pushes from, on its lowest level. The ring stays where it was
    # made (a ripple in the air) and grows. Two discs (Ho-Oh's glow disc on joint27, and the same disc drawn again on
    # joint16, Ho-Oh's tail joint, see RIPPLE2 below) take turns between the four paws; each ring lives until its disc is
    # needed again (at most RIPPLE_L frames). Checked in the game with DEBUG_RING=<paw> (a small ring locked to that paw).
    events = []; n_ = len(CYC); HMIN = {}; BAND = {}
    for b in FEET:
        h = np.array([(H(bone_pose(b, x)) @ np.append(pvf[b], 1))[1] for x in range(n_)]); HMIN[b] = h.min()
        BAND[b] = h <= h.min() + 0.25 * (h.max() - h.min())
    key_ = lambda f: int(math.floor(PH[f] + 1e-6)) % n_ if PH is not None else 0
    if PH is not None:
        for b in FEET:
            for f in range(nf - 1):
                if BAND[b][key_(f)] and not BAND[b][key_(f + 1)]: events.append((f, b))
    events.sort()
    J16 = names.index('joint16') if os.environ.get('RIPPLE2', '1') == '1' and 'joint16' in names else None
    DISCS = [j27] + ([J16] if J16 is not None else []); L_ = int(os.environ.get('RIPPLE_L', '18'))
    if J16 is not None:                                   # both discs hang on the world root (see RIPPLE2 at the render commands)
        WR_ = next(p_[0] for op_, p_ in m['rcmds'] if op_ in (0x26, 0x66) and p_[0] == p_[1]); parent[J16] = WR_; parent[j27] = WR_
        PSC[0] = float(np.cbrt(np.linalg.det(worlds(0)[0][WR_][:3, :3])))
    ASSIGNED = []; last_ = [-10 ** 9] * len(DISCS)
    for fe, b in events:
        k = int(np.argmin(last_)); ASSIGNED.append((fe, b, k)); last_[k] = fe
    LIFE = {}
    for i, (fe, b, k) in enumerate(ASSIGNED):
        nxt = [f2 for f2, _, k2 in ASSIGNED[i + 1:] if k2 == k]; LIFE[(fe, b)] = min(L_, nxt[0] - fe) if nxt else L_
    def under_paw(a, f):
        RF_ = root_frame(f); q = (np.linalg.inv(RF_) @ np.append(foot_world(a, f), 1))[:3]
        q[1] = min(q[1], HMIN[a]); return (RF_ @ np.append(q, 1))[:3]
    POS = {(fe, b): under_paw(b, fe) for fe, b, _ in ASSIGNED}; R0 = 0.25 * RMAX
    print('ripples', len(events), 'on', len(DISCS), 'discs; push-offs', [(fe, b[:2]) for fe, b in events[:8]], 'lives', [LIFE[e] for e in events[:8]])
    if os.environ.get('DIAG_RIPPLE'):                       # check: does each ring start at its paw, and does the paw then leave it?
        for fe, b, k in ASSIGNED[:8]:
            row = []
            for a_ in (-4, -2, 0, 2, 4, 8):
                f_ = min(max(fe + a_, 0), nf - 1); RFi = np.linalg.inv(root_frame(f_)); q = (RFi @ np.append(foot_world(b, f_), 1))[:3]; c = (RFi @ np.append(POS[(fe, b)], 1))[:3]
                row.append('%+.0f/%.0f' % ((q[1] - c[1]) * sig, np.linalg.norm(np.delete(q - c, 1)) * sig))
            print('   f%3d %s disc %d life %2d  paw height over ring / paw distance from ring centre at ages -4 -2 0 2 4 8: %s' % (fe, b[:2], k, LIFE[(fe, b)], ' '.join(row)))
        sys.exit(0)
    def ripple_world(f, disc=0):
        if os.environ.get('DEBUG_RING2') and disc == 1: return ring_matrix(foot_world(os.environ['DEBUG_RING2'], f), R0, f, 1)   # test: disc 2 on a paw
        if os.environ.get('DEBUG_RING') and disc == 0:        # test: a small ring on one paw (or the hind midpoint) every frame
            dr = os.environ['DEBUG_RING']; pos = foot_world(dr, f) if dr != 'MID' else (foot_world('BL_lo', f) + foot_world('BR_lo', f)) / 2
            return ring_matrix(pos, R0, f)
        mine = [(fe, b) for fe, b, k in ASSIGNED if k == disc]
        cur = [e for e in mine if e[0] <= f]; nxt = [e for e in mine if e[0] > f]
        if cur and f - cur[-1][0] < LIFE[cur[-1]]:
            fe, b = cur[-1]; return ring_matrix(POS[(fe, b)], R0 + (RMAX - R0) * (f - fe) / max(LIFE[(fe, b)] - 1, 1), fe, disc)
        e = nxt[0] if nxt else (cur[-1] if cur else None)      # hidden: tiny, waiting where the next ring comes (the track stands still)
        return ring_matrix(POS[e], 1e-3 * RMAX, e[0], disc) if e is not None else None
nodes_T = [[None] * nf for _ in names]; nodes_R = [[None] * nf for _ in names]; nodes_S = [[None] * nf for _ in names]
for f in range(nf):
    W, trs = worlds(f); want = dict(W)
    RF = root_frame(f) if PATHFRAME else W[j1]
    LG = leg_L(f)
    for b in BASEB: want[bnode[b]] = RF @ (LG[b] if b in LG else H(bone_world(b, f))) @ SUP     # posScale folded into the bone matrices; legs: paws locked
    for h_ in HELP:                                                    # helpers: halfway between the two bones, about their joint
        _, A_, Bc_ = h_.split(':')
        WA = LG[A_] if A_ in LG else H(bone_world(A_, f)); WB = LG[Bc_] if Bc_ in LG else H(bone_world(Bc_, f))
        KA = WA @ np.linalg.inv(H(rest[A_])); KB = WB @ np.linalg.inv(H(rest[Bc_])); pB = H(rest[Bc_])[:3, 3]
        Rt = Slerp([0, 1], Rot.from_matrix([orth(KA[:3, :3]), orth(KB[:3, :3])]))([0.5]).as_matrix()[0]
        pt = ((KA @ np.append(pB, 1))[:3] + (KB @ np.append(pB, 1))[:3]) / 2
        Kh = np.eye(4); Kh[:3, :3] = Rt; Kh[:3, 3] = pt - Rt @ pB
        want[bnode[h_]] = RF @ Kh @ H(rest[A_]) @ SUP
    if f >= nf - int(os.environ.get('HIDE_TAIL', '0')):   # the sky shot ends with the camera flying through him: hide him there
        for bb in bnames: want[bnode[bb]] = RF @ np.diag([1e-3, 1e-3, 1e-3, 1.0])
    for i in hooh:
        if i != j1 and i not in bnode.values(): want[i] = W[i] if i in glowj else W[j1]   # glow joints: Ho-Oh's own; the rest on the root
    if RIPPLE:
        for k_d, jd in enumerate(DISCS):
            rw = ripple_world(f, k_d)
            want[jd] = rw if rw is not None else (W[j1] @ np.diag([1e-3, 1e-3, 1e-3, 1]))      # between ripples: hidden (tiny)
    for i in range(len(names)):
        if i in hooh and i != j1:
            # Maya segment scale compensation (model scaling == 1): world_i = world_pa . T_i . S_pa^-1 . R_i . S_i, so with
            # uniform scales: R_i = R_pa^T R_i(world), S_i = scale_i(world), T_i = R_pa^T (p_i - p_pa) / scale_pa
            pa = parent[i]; Mp, Mi = want[pa], want[i]
            sp = np.cbrt(np.linalg.det(Mp[:3, :3])); si = np.cbrt(np.linalg.det(Mi[:3, :3]))
            Rp = orth(Mp[:3, :3] / sp); Ri = orth(Mi[:3, :3] / si)
            nodes_T[i][f] = Rp.T @ (Mi[:3, 3] - Mp[:3, 3]) / sp; nodes_R[i][f] = Rp.T @ Ri; nodes_S[i][f] = [si, si, si]
        else:
            nodes_T[i][f], nodes_R[i][f], nodes_S[i][f] = trs[i]
NEEDED = set()                                                    # our bones, the glow joints and all their parents
if RIPPLE and J16 is not None: NEEDED.add(J16)                     # the second ripple disc
for i in list(bnode.values()) + list(glowj):
    while True:
        NEEDED.add(i)
        if i not in parent or parent[i] == i: break
        i = parent[i]
bnodes = []
for i, o in enumerate(anim['objs']):
    keep = None if (i in hooh and i != j1) else (o['flags'] & (1 | 6 | 0xC0 | 0x600))
    if i in hooh and i != j1 and i not in NEEDED: keep = 1              # unused Ho-Oh joint, no geometry, not a parent: not animated
    bnodes.append(dict(flags_keep=keep, T=nodes_T[i], R=nodes_R[i], S=nodes_S[i], idx=i, rate=(int(os.environ.get('HALFRATE', '0')) if keep is None and not (RIPPLE and i in DISCS) else 0)))   # ripple discs: every frame (a ring jumps to its next spot)
new_bca = bca_write.build(nf, bnodes, template=D(BM))
# geometry: Ho-Oh's shapes emptied; per bone strips in the bone's rest frame
mo = m['off']; size, rc, mat, shp, invo = struct.unpack_from('<5I', d, mo)
ents, _ = nitro.dict_read(bytes(d), mo + shp, 4); shapes = []; shapehdr = []
for e, sn, _ in ents:
    o = mo + shp + nitro.u32(e, 0); dummy, ssz, flag, co, cl = struct.unpack_from('<HHIII', d, o); shapes.append((o + co, cl)); shapehdr.append(o)
headmat = [i for i, x in enumerate(mats) if x.get('tex') == 'ho_head_top'][0]
# walk the raw render commands: move our bones' matrix stores to free slots (17..), follow the restores, note when each
# Ho-Oh shape is drawn (a bone can only be drawn after its matrix is made)
matpos = {}
OURS = set(bnode.values())
SUPPRESS = {i for i in hooh if i != j1 and i not in NEEDED and i not in OURS}
forbid = {KEEP_SLOT, 0}
for op, p in m['rcmds']:
    if op in (0x26, 0x66) and p[0] not in OURS and p[0] not in SUPPRESS: forbid.add(p[3])
    if op == 9: forbid.add(p[0])
FREE = [s_ for s_ in range(1, 30) if s_ not in forbid]
assert len(FREE) >= len(bnames), ('not enough matrix slots', len(FREE), len(bnames))
newslot = {bnode[b]: FREE[k] for k, b in enumerate(bnames)}
print('slots', len(FREE), 'free for', len(bnames), 'bones; suppressed stores', len(SUPPRESS))
if RIPPLE and J16 is not None:
    # RIPPLE2, the second ripple disc. joint16 (Ho-Oh's tail joint, no matrix slot) now restores the world root, applies its
    # own track and stores the result in a free slot; right after the first disc is drawn, that slot is restored and the
    # same disc shape is drawn again. joint27 (the first disc) also hangs on the world root now: a ring stays where it was
    # made, so both tracks stand still between rings and pack small. The bytes come from repeated material commands in front
    # of Ho-Oh's sparkle quads (same material set again) and world-root visibility checks; NOPs pad to the old length.
    ops = []; o = mo + rc
    while True:
        op = d[o]; n = 2 + 3 * d[o + 2] if op == 9 else nitro.RCMD_LEN[op]; ops.append([op, list(d[o + 1:o + 1 + n])]); o += 1 + n
        if op == 1: break
    RC_LEN = o - (mo + rc)
    WR = next(p_[0] for op_, p_ in ops if op_ in (0x26, 0x66) and p_[0] == p_[1])          # the world root: its own parent
    WRS = next(p_[3] for op_, p_ in ops if op_ in (0x26, 0x66) and p_[0] == WR)
    S16 = FREE[len(bnames)]; assert S16 not in newslot.values()
    ring_ms = None; cm = None
    for op_, p_ in ops:
        if op_ in (4, 0x24, 0x44): cm = p_[0]
        if op_ == 5 and cm is not None and str(mats[cm].get('tex', '')).startswith('hou_tail_l'): ring_ms = (cm, p_[0]); break
    assert ring_ms, 'ring disc not found'
    out = []; cm = None; need = 5
    for op_, p_ in ops:
        if op_ in (6, 0x26, 0x46, 0x66) and p_[0] == J16: out.append([0x66, [J16, WR, 0, S16, WRS]]); continue   # flag 0: no scale compensation (the world root keeps no parent scale)
        if op_ == 0x66 and p_[0] == j27: out.append([0x66, [j27, WR, p_[2], p_[3], WRS]]); continue
        if op_ in (4, 0x24, 0x44) and p_[0] == cm and GLOWTEX.search(str(mats[cm].get('tex', ''))): continue      # same material again
        if op_ == 2 and p_[0] == WR and need > 0: need -= 3; continue                            # world root: always visible
        if op_ in (4, 0x24, 0x44): cm = p_[0]
        out.append([op_, p_])
        if op_ == 5 and (cm, p_[0]) == ring_ms: out += [[3, [S16]], [5, [ring_ms[1]]]]
    blob = bytearray()
    for op_, p_ in out[:-1]: blob += bytes([op_] + p_)
    assert len(blob) + 1 <= RC_LEN, ('render commands grew', len(blob) + 1, RC_LEN)
    blob += bytes(RC_LEN - 1 - len(blob)) + bytes([1]); d[mo + rc:mo + rc + RC_LEN] = blob
    parent[J16] = WR; parent[j27] = WR
    print('ripple disc 2: joint16 -> slot', S16, '; disc', ring_ms, 'drawn twice;', RC_LEN - 1 - len(blob.rstrip(bytes([1])).rstrip(bytes(1))), 'NOP bytes left')
owner = {}; use = []; cur = None; curpos = None; o = mo + rc; k_ = 0; shape_k = {}; made = {}
while True:
    op = d[o]; n = 2 + 3 * d[o + 2] if op == 9 else nitro.RCMD_LEN[op]; p = list(d[o + 1:o + 1 + n])
    if op == 0x46 and owner.get(p[3]) in newslot: d[o + 1 + 3] = newslot[owner[p[3]]]
    if op == 0x66 and owner.get(p[4]) in newslot: d[o + 1 + 4] = newslot[owner[p[4]]]
    if op == 3 and owner.get(p[0]) in newslot: d[o + 1] = newslot[owner[p[0]]]
    if op in (0x26, 0x66) and p[0] in SUPPRESS:                       # unused Ho-Oh joint: no store (same length: NOP after)
        if op == 0x26: d[o:o + 5] = bytes([0x06, p[0], p[1], p[2], 0x00])
        else: d[o:o + 6] = bytes([0x46, p[0], p[1], p[2], d[o + 5], 0x00])
    elif op in (0x26, 0x66):
        if p[0] in newslot: d[o + 1 + 3] = newslot[p[0]]; made[p[0]] = k_; owner[p[3]] = p[0]   # later restores of the old slot follow it
        else: owner[p[3]] = p[0]
        if p[0] in newslot: pass
        else: owner[p[3]] = p[0]
    if op == 9: owner[p[0]] = None
    if op in (4, 0x24, 0x44): cur = p[0]; curpos = o + 1
    elif op == 5 and cur is not None and HOOH.search(str(mats[cur].get('tex', ''))) and p[0] not in use:
        use.append(p[0]); shape_k[p[0]] = k_; matpos[p[0]] = curpos
    o += 1 + n; k_ += 1
    if op == 1: break
if 'noshapes' in TEST: use = []
for sh in use: so, cl = shapes[sh]; d[so:so + cl] = bytes(cl)
TEXN = {0: 'ho_head_top', 1: 'hou_eye', 2: 'hou_mouth01'}
import os as _os
MULTI = _os.path.exists(BASE + '_tex0_idx.npy')
HASN = any('n' in p for p in polys); LIGHTS = int(os.environ.get('LIGHTS', '3'))   # with normals: lit like Ho-Oh (lights 0+1)
PALG = None
if MULTI and _os.path.exists(BASE + '_tex0_pal.npy'):     # v31 (tex_views.py): Arvind's turnaround painted on, 8 bpp, a palette per texture
    IDX = {g: np.load(f'{BASE}_tex{g}_idx.npy') for g in (0, 1, 2)}; PALG = {g: np.load(f'{BASE}_tex{g}_pal.npy') for g in (0, 1, 2)}; pal = PALG[0]
elif MULTI:
    IDX = {g: np.load(f'{BASE}_tex{g}_idx.npy') for g in (0, 1, 2)}; pal = np.load(BASE + '_tex_pal.npy')
else:
    IDX = {0: np.load(BASE + '_tex_idx.npy')}; pal = np.load(BASE + '_tex_pal.npy')
GMAT = {g: [i for i, x in enumerate(mats) if x.get('tex') == TEXN[g]][0] for g in IDX}
def v10(q):
    q = [int(round(v / up * 64)) for v in q]; assert all(-512 <= x < 512 for x in q), q
    return (q[0] & 1023) | (q[1] & 1023) << 10 | (q[2] & 1023) << 20
def n10(q):                                                 # NORMAL: three signed 1.9 fixed values
    a = [max(-512, min(511, int(round(v * 512)))) & 1023 for v in q]; return a[0] | a[1] << 10 | a[2] << 20
def tc(uv, g=0):
    th, tw = IDX[g].shape
    a_ = min(tw * 16 - 1, max(-2048, int(round(uv[0] * tw * 16)))); b_ = min(th * 16 - 1, max(-2048, int(round((1 - uv[1]) * th * 16)))); return (b_ & 0xffff) << 16 | (a_ & 0xffff)
def pack_cmds(cmds):
    out = bytearray()
    for k in range(0, len(cmds), 4):
        grp = cmds[k:k + 4] + [(0, [])] * (4 - len(cmds[k:k + 4])); out += bytes(op for op, _ in grp)
        for _, ps in grp:
            for v in ps: out += struct.pack('<I', v & 0xffffffff)
    return out
def strips_of(tris_l):                                     # greedy strips; both faces are drawn so winding is free
    keyof = {}; verts = []
    def vid(pv, uv):
        u_ = uv[0] if isinstance(uv[1], str) else uv
        kk = tuple(np.round(pv, 2)) + (round(u_[0], 4), round(u_[1], 4)) + ((uv[1],) if isinstance(uv[1], str) else ()) + (tuple(uv[2]) if len(uv) > 2 and uv[2] is not None else ())
        if kk not in keyof: keyof[kk] = len(verts); verts.append((pv, uv))
        return keyof[kk]
    T = [tuple(vid(pv, uv) for pv, uv in t) for t in tris_l]; edge = {}
    for ti, t in enumerate(T):
        for a_, b_ in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])): edge.setdefault(frozenset((a_, b_)), []).append(ti)
    used = [False] * len(T); out = []
    MAXS = int(os.environ.get('MAXSTRIP', '30'))                   # long strips are split so they fit the leftover room in shapes
    def grow(st):
        while len(st) < MAXS:
            cand = [t for t in edge.get(frozenset((st[-2], st[-1])), []) if not used[t]]
            if not cand: return st
            t = cand[0]; used[t] = True; st.append([v for v in T[t] if v not in (st[-2], st[-1])][0])
        return st
    for s0 in range(len(T)):
        if used[s0]: continue
        used[s0] = True; st = grow(list(T[s0])); st = grow(list(reversed(st))); out.append([verts[v] for v in st])
    return out
HINV = {b: np.linalg.inv(H(rest[b.split(':')[1] if b.startswith('h:') else b])) for b in bnames}   # a helper lives in its parent's rest frame
work = []                                                   # (group, bones used, strip commands); each vertex follows its own bone
for g in IDX:
    mine = [t for t in tris if (t[3] if MULTI else 0) == g]
    def nloc(n_, vb):                                       # the normal in the bone's frame (rotation only), for the DS light
        if n_ is None: return None
        q = HINV[vb][:3, :3] @ (Fx @ np.array(n_)); return tuple(np.round(q / (np.linalg.norm(q) + 1e-9), 3))
    LB = np.array([-0.35, -0.55, 0.75]); LB /= np.linalg.norm(LB)
    def nshade(n_, vb):                                     # unlit shots (Ho-Oh is unlit in the sky shot): light baked into COLOR
        if n_ is None or PALG is not None: return None          # v31: the painting carries its own light (white vertex colour)
        return ('c', int(round(31 * min(1.0, 0.55 + 0.5 * max(0.0, float(np.array(n_) @ LB))))))
    lit = LIGHTS != 0
    loc = [[((HINV[vb] @ np.append(s * Fx @ (np.array(v) - cen), 1))[:3], (uvv, vb, (nloc(n_, vb) if lit else nshade(n_, vb)))) for v, uvv, vb, n_ in zip(t[0], t[1], t[4], t[5])] for t in mine]
    for st in strips_of([[(pv, x) for pv, x in tri] for tri in loc]):
        bones_ = {x[1] for _, x in st}; cmds_ = [(0x40, [2])]; curb_ = None
        if 'rigid' in TEST: cmds_ = [(0x14, [newslot[bnode[st[0][1][1]]]]), (0x40, [2])]; curb_ = st[0][1][1]
        last_t = None; last_c = None
        for pv, (uv, vb, nl) in st:
            if 'nomtx' in TEST: curb_ = vb
            if vb != curb_ and 'rigid' not in TEST: cmds_ += [(0x14, [newslot[bnode[vb]]])]; curb_ = vb      # no SCALE: it is in the bone matrix
            t_ = tc(uv, g)
            if nl is not None and nl[0] == 'c':
                cc = nl[1] | nl[1] << 5 | nl[1] << 10; nc = [] if cc == last_c else [(0x20, [cc])]; last_c = cc; nn_ = []
            else: nc = []; nn_ = [(0x21, [n10(nl)])] if nl is not None else []
            cmds_ += ([(0x22, [t_])] if t_ != last_t else []) + nc + nn_ + [(0x24, [v10(pv)])]; last_t = t_   # swatches: same UV, sent once
        work.append((g, bones_, cmds_ + [(0x41, [])]))
done = [False] * len(work); placed = 0
ready = lambda w, k: all(made.get(bnode[b], 1e9) < k for b in w[1])
# which texture group each Ho-Oh shape carries (one material per shape): searched, not greedy — the greedy choice gave the
# big shapes to the body texture and left the head/sail strips without room
_order = [] if 'noplace' in TEST else sorted(use, key=lambda x: shape_k[x])
_wlen = [len(pack_cmds(w[2])) for w in work]
def _simulate(assign):
    dn = [False] * len(work); n = 0
    for sh in _order:
        g = assign.get(sh)
        if g is None: continue
        room = shapes[sh][1] - 16
        for wi, w in enumerate(work):
            if dn[wi] or w[0] != g or not ready(w, shape_k[sh]) or _wlen[wi] > room: continue
            room -= _wlen[wi]; dn[wi] = True; n += 1
    return n
_need = {g: sum(_wlen[wi] for wi, w in enumerate(work) if w[0] == g) for g in IDX}
_rng = np.random.default_rng(int(os.environ.get("ASSIGN_SEED", "7"))); best = None
for _t in range(int(os.environ.get("ASSIGN_TRIES", "4000"))):
    asg = {}
    if _t == 0:                                                        # the old greedy as a candidate
        left = dict(_need)
        for sh in _order: g = max(left, key=left.get); asg[sh] = g; left[g] -= shapes[sh][1]
    else:
        p_ = np.array([_need[g] for g in IDX], float); p_ /= p_.sum(); gs = list(IDX)
        for sh in _order: asg[sh] = gs[_rng.choice(len(gs), p=p_)]
    sc_ = _simulate(asg)
    if best is None or sc_ > best[0]: best = (sc_, asg)
    if best[0] == len(work): break
ASSIGN = best[1]
if best[0] < len(work):                                                # leftovers: strips on a late helper fall back to its parent bone
    def _placed(assign):
        dn = [False] * len(work)
        for sh in _order:
            g = assign.get(sh)
            if g is None: continue
            room = shapes[sh][1] - 16
            for wi, w in enumerate(work):
                if dn[wi] or w[0] != g or not ready(w, shape_k[sh]) or _wlen[wi] > room: continue
                room -= _wlen[wi]; dn[wi] = True
        return dn
    for wi, ok_ in enumerate(_placed(ASSIGN)):
        if ok_: continue
        w = work[wi]; hs = [b for b in w[1] if b.startswith('h:')]
        if not hs: continue
        rp = {newslot[bnode[h]]: newslot[bnode[h.split(':')[1]]] for h in hs}
        work[wi] = (w[0], {(b.split(':')[1] if b.startswith('h:') else b) for b in w[1]}, [((op, [rp.get(ps[0], ps[0])]) if op == 0x14 else (op, ps)) for op, ps in w[2]])
    _wlen = [len(pack_cmds(w[2])) for w in work]
    print('fallback: strips on late helpers moved to the parent bone;', _simulate(ASSIGN), 'of', len(work), 'now fit')
for sh in ([] if 'noplace' in TEST else sorted(use, key=lambda x: shape_k[x])):             # shapes in draw order; only bones already made; one group per shape
    so, cl = shapes[sh]
    g_ = ASSIGN.get(sh)
    if g_ is None: continue
    # NNS remembers the last restored matrix slot and skips a restore of the same slot; our strips change the hardware
    # matrix behind its back, so the next shape (the sky shot's glow) would be drawn with our bone. Save and give it back.
    cmds = [(0x13, [KEEP_SLOT]), (0x20, [0x7fff])]; tail = [(0x14, [KEEP_SLOT])]
    if 'nomtx' in TEST: cmds = [(0x20, [0x7fff])]; tail = []
    if 'minimal' in TEST: cmds = [(0x0, []), (0x0, [])]; tail = []
    for wi, w in enumerate(work):
        if done[wi] or w[0] != g_ or not ready(w, shape_k[sh]): continue
        if len(pack_cmds(cmds + w[2] + tail)) > cl: continue
        cmds += w[2]; done[wi] = True
    if len(cmds) > (1 if 'nomtx' in TEST else 2):
        blob = pack_cmds(cmds + tail); d[so:so + cl] = blob + bytes(cl - len(blob)); placed += 1; d[matpos[sh]] = GMAT[g_]
        # shape flags: 2 = sends COLOR, 8 = restores matrices (NNS then stops trusting its current-matrix cache: without it the
        # next restore of the same slot is skipped and the sky shot's glow is drawn with our bone matrix)
        if 'noflag' not in TEST: struct.pack_into('<I', d, shapehdr[sh] + 4, struct.unpack_from('<I', d, shapehdr[sh] + 4)[0] | 0x2 | 0x8)
qi = sum(sum(len(c[1]) for c in [w]) for w, ok in zip(work, done) if ok); queue = work
if os.environ.get('DIAG_STRIPS'):
    from collections import Counter as _C
    print('UNPLACED by group/bones', _C((w[0], tuple(sorted(w[1]))) for w, ok in zip(work, done) if not ok).most_common(8))
    print('shape free bytes', [(sh, shapes[sh][1]) for sh in sorted(use, key=lambda x: shape_k[x])])
print('glow joints', sorted(names[i] for i in glowj)); print('strips placed', sum(done), 'of', len(work), 'in', placed, 'shapes; bones', {b: names[i] for b, i in bnode.items()})
for g, mi_ in ({} if 'nomats' in TEST else GMAT).items():
    mo_ = mats[mi_]['off']; pa = struct.unpack_from('<I', d, mo_ + 12)[0]; struct.pack_into('<I', d, mo_ + 12, (pa & ~0xF & ~(31 << 16)) | 0xC0 | (31 << 16) | (LIGHTS if HASN else 0))
    if HASN:
        EM = int(os.environ.get('EMI', '9')); struct.pack_into('<I', d, mo_ + 4, 31 | 31 << 5 | 31 << 10 | 0x8000 | (24 | 24 << 5 | 24 << 10) << 16)
        struct.pack_into('<I', d, mo_ + 8, (EM | EM << 5 | (EM + 2) << 10) << 16)
def c555(c): rr, gg, bb = (int(round(v / 255 * 31)) for v in c); return rr | gg << 5 | bb << 10
BIGTEX = PALG is not None
if BIGTEX and 'notex' not in TEST:                          # v31: Ho-Oh's three texture slots rebuilt as 8-bpp textures with their own palettes
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grav3d')); import tex0_grow
    _bo = [b for b in r['blocks'] if d[b:b + 4] == b'TEX0'][0]; _tt = nitro.read_tex(bytes(d), _bo); texd = {}; pald = {}
    for g, tn_ in TEXN.items():
        ix = IDX[g]; h_, w_ = ix.shape; texd[tn_] = (4, w_, h_, bytes(ix.astype(np.uint8).reshape(-1)))
        pn = mats[GMAT[g]]['pal']                               # the material's own palette (a prefix match took hou_eye01_pl for hou_eye)
        pald[pn] = b''.join(struct.pack('<H', c555(PALG[g][i]) if i < len(PALG[g]) else 0) for i in range(256))
    if RIPPLE:                                              # the glow disc's texture redrawn as a ring (A3I5), as below
        for x in _tt['texs']:
            if x['name'].startswith('hou_tail_l') and x['fmt'] == 1 and x['w'] == 16:
                RING_ = [0, 1, 3, 5, 7, 7, 6, 4, 2, 1, 0, 0, 0, 0, 0, 0]; raw_ = bytearray(x['data'])
                for yy in range(16):
                    for xx in range(16): raw_[yy * 16 + xx] = (RING_[xx] << 5) | (raw_[yy * 16 + xx] & 31)
                texd[x['name']] = (1, 16, 16, bytes(raw_))
    # Ho-Oh's other textures (his emptied shapes only) shrink to 8x8, 4 colours: texture VRAM and RAM are tight here
    if os.environ.get('SHRINK_HOOH', '1') == '1':
        for x in _tt['texs']:
            if HOOH.search(x['name']) and x['name'] not in TEXN.values() and x['name'] not in texd and not GLOWTEX.search(x['name']):
                texd[x['name']] = (2, 8, 8, bytes(16))
    d = bytearray(tex0_grow.grow(d, texd, pald))
    for mt in mats:
        for g, tn_ in TEXN.items():
            if mt.get('tex') == tn_: h_, w_ = IDX[g].shape; struct.pack_into('<HH', d, mt['off'] + 32, w_, h_)
    print('textures rebuilt', {tn_: IDX[g].shape[::-1] for g, tn_ in TEXN.items()}, 'model', len(d))
for bo in ([] if ('notex' in TEST or BIGTEX) else r['blocks']):
    if d[bo:bo + 4] != b'TEX0': continue
    t = nitro.read_tex(bytes(d), bo); fh = t['raw_hdr']; tbo, pbo = fh[6], fh[17]
    ents2, _ = nitro.dict_read(bytes(d), bo + fh[4], 8)
    for (e2, nm2, eo), x in zip(ents2, t['texs']):
        if RIPPLE and x['name'].startswith('hou_tail_l') and x['fmt'] == 1 and x['w'] == 16:   # the glow disc becomes a ring (A3I5)
            off = (x['param'] & 0xffff) << 3; RING = [0, 1, 3, 5, 7, 7, 6, 4, 2, 1, 0, 0, 0, 0, 0, 0]
            for yy in range(16):
                for xx in range(16):
                    k = bo + tbo + off + yy * 16 + xx; d[k] = (RING[xx] << 5) | (d[k] & 31)
        for g, tn_ in TEXN.items():
            if g not in IDX or x['name'] != tn_: continue
            ix = IDX[g]; assert ix.shape == (x['h'], x['w']) and x['fmt'] == 3, (tn_, ix.shape, x['w'], x['h'], x['fmt'])
            struct.pack_into('<I', d, eo, x['param'] & ~(1 << 29)); off = (x['param'] & 0xffff) << 3; fl = ix.astype(np.uint8).reshape(-1)
            d[bo + tbo + off: bo + tbo + off + x['w'] * x['h'] // 2] = bytes(fl[0::2] | (fl[1::2] << 4))
    for pl in t['pals']:
        if any(g in IDX and pl['name'].startswith(TEXN[g]) for g in TEXN):
            for i in range(16): struct.pack_into('<H', d, bo + pbo + pl['off'] + 2 * i, c555(pal[i - 1]) if 1 <= i <= len(pal) else 0)
F[MM] = lz10_enc(bytes(d)); F[BM] = lz10_enc(new_bca)
open(DST, 'wb').write(pack(F)); print('model', len(F[MM]), 'anim', len(F[BM]))
