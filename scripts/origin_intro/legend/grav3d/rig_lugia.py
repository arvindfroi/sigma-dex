"""Gravriel takes Lugia's place in Lugia's 3D film (a/2/4/4, Origin's post-game Whirl Islands ritual, script 104).
Lugia is its own skinned model there (member 5 `lugia_b09`, 26 joints, 2 shapes) with its own animation (member 6, 246
frames); the cave, the fall and the water ring (members 0-4) stay. From export_gravfilm.py's JSON:
  - nodes: 'body' (node 0) is a still world root; our 14 bones go on nodes 1..14, each restoring the root's slot and
    storing its matrix in its own slot (the render commands are rewritten in place; NOPs pad to the old length).
  - geometry: per-vertex MTX_RESTORE strips (like rig3d.py) in the two shapes; group 0 (coat, weed, skin, hat) in shape 0
    with lugia_s (64x64), group 1 (mask, bone/sword, shell, eyes, sockets) in shape 1 with lugia_foot (32x32); both are
    flat colour swatches. Vertices are in their bone's bind frame / K, the bone matrices carry K (posScale is not used).
  - path (film units, Lugia's model space): hidden under the water, rises at the foot of the fall through the falling
    water at the flash, moves out in front of the fall and hovers where Lugia hovers, facing the camera (+z).
python rig_lugia.py A244_IN A244_OUT G.json      env: SIZE (his height), K, SHOW (first visible frame), LIGHTS"""
import sys, os, json, math, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', '..')); sys.path.insert(0, os.path.join(HERE, '..'))
from narc import unpack, pack
from lz11 import lz11_dec
from lz import lz10_enc
import nitro, geom, bca_write, tex0_grow
SRC, DST, GJ = sys.argv[1:4]
E = lambda k, d: float(os.environ.get(k, d))
MM, BM = 5, 6
F = unpack(open(SRC, 'rb').read()); D = lambda i: lz11_dec(F[i]) if F[i][:1] == b'\x11' else F[i]
d = bytearray(D(MM)); r = nitro.read_bmd(bytes(d)); m = r['models'][0]; mats = m['mats']; names = [n for n, _ in m['nodes']]
nf = geom.read_bca(D(BM))[0]['nframes']
J = json.load(open(GJ)); BONES = J['bones']; polys = J['polys']
# v8: the 'ghost' copy (export_gravparts.py) is drawn on its own: untextured, pale sea green, see-through, rigid on one node
GPOLYS = [p for p in polys if p.get('part') == 'ghost'] if os.environ.get('GHOST', '1') == '1' else []
polys = [p for p in polys if p.get('part') != 'ghost']
assert len(BONES) + 1 <= len(names)
# ------------------------------------------------------------------ Blender -> film coordinates
Fx = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)          # x right, z up, faces -y  ->  x right, y up, faces +z
allp = np.array([q for p in polys for q in p['p']]); zmin, zmax = allp[:, 2].min(), allp[:, 2].max()
ORG = np.array([np.median(allp[:, 0]), np.median(allp[:, 1]), zmin])  # his feet
SIZE = E('SIZE', 125); s = SIZE / (zmax - zmin); K = E('K', 16)
def orth(R):
    u, _, vt = np.linalg.svd(R); return u @ vt
def H(Mb):
    Mb = np.array(Mb); out = np.eye(4); out[:3, :3] = Fx @ orth(Mb[:3, :3]); out[:3, 3] = s * Fx @ (Mb[:3, 3] - ORG); return out
def P(v): return s * Fx @ (np.array(v) - ORG)
HB = {b: H(J['bind'][b]) for b in BONES}; HBi = {b: np.linalg.inv(M) for b, M in HB.items()}
SUPK = np.diag([K, K, K, 1.0])
# ------------------------------------------------------------------ path
# v2 (Arvind: out of the portal/fall like Lugia, slower and eerier): he waits behind the fall, glides through the
# curtain at the flash and drifts out in front of it, where Lugia hovers
# v4 (Arvind: "it looks silly that he comes out before the portal opens"; "the way he flies out is stiff"): he appears
# in the curtain when the portal opens (126) and drifts out to the hover spot, leaning into it and swaying
KEYS = [(E('K0', 126), np.array([E('AX', 8), E('AY', 36), E('AZ', -120)])), (E('K1', 168), np.array([E('BX', 4), E('BY', 58), E('BZ', -10)])),
        (E('K2', 204), np.array([E('CX', 0), E('CY', 66), E('CZ', 48)]))]
SHOW = KEYS[0][0]
def ease(t): t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)
# v6 (Arvind: "fly out of the portal like Lugia and float up"): Lugia's own body path from its animation, played at
# SLOW speed from the moment the portal opens, his middle where Lugia's body joint is
LUGIA_PATH = os.environ.get('LUGIA_PATH', '1') == '1'
if LUGIA_PATH:
    _a0 = geom.read_bca(D(BM))[0]; _order = [p for op, p in m['rcmds'] if op in (6, 0x26, 0x46, 0x66)]
    def _lugia_body(fr):
        trs = geom.node_trs(m, _a0, fr); W = {}
        for p_ in _order:
            i_, pa_ = p_[0], p_[1]; t_, rr_, sc_ = trs[i_]; T = np.eye(4); T[:3, 3] = t_; R = np.eye(4); R[:3, :3] = rr_; S = np.diag(list(sc_) + [1])
            L = (T @ np.diag([1 / x if x else 0 for x in trs[pa_][2]] + [1]) @ R @ S) if pa_ != i_ else T @ R @ S
            W[i_] = (W[pa_] if pa_ != i_ and pa_ in W else np.eye(4)) @ L
        return W[0][:3, 3]
    _LB = [_lugia_body(fr) for fr in range(nf)]
    SLOW, T0 = E('SLOW', 0.5), E('T0', 124)
    def lugia_at(t):
        t = min(nf - 1.0, max(0.0, t)); i0 = int(t); i1 = min(nf - 1, i0 + 1); w = t - i0; return _LB[i0] * (1 - w) + _LB[i1] * w
    SHOW = T0
# v7 PATH=glide (default): a slow, eased glide from where Lugia leaves the fall to where Lugia hovers, rising on the way
# and bobbing gently after (v6's half-speed copy of Lugia's path swung close to the camera and looked rushed)
PATHMODE = os.environ.get('PATH_MODE', 'rise')
# v8: Lugia stops at film frame ~160 and the picture holds until the fade (a freeze frame before the battle): he reaches
# his pose by then and freezes too (FREEZE), the glide ending there (T1)
FREEZE = E('FREEZE', 160)
T1 = E('T1', 160)
SWITCH, AURA = E('SWITCH', 147), E('AURA', 14)      # ghost -> his own colours as the scream ring reaches him; green drains
# v9 PATH_MODE=rise (Arvind: "come up out of the water instead", the portal effect from there too, a low camera at the
# water in front of him that follows his eye line): straight up out of the water below Lugia's hover spot, eased out
WATER_Y = E('WATER_Y', 10)
def rise_pos(f):
    f = min(f, FREEZE); P1 = _LB[-1] - np.array([0, SIZE * E('MID', 0.55), 0]) + np.array([E('RISE_DX', 0), 0, E('RISE_DZ', 0)])
    t_ = min(1.0, max(0.0, (f - T0) / (T1 - T0))); e_ = 1 - (1 - t_) ** E('EASE_OUT', 2.2)
    return P1 + np.array([0, -E('DEPTH', 200) * (1 - e_), 0]), e_
# the film camera never moves (measured with marker cubes: film_camera.json, 0.1 px); a new camera is made by moving the
# whole world the other way: everything (cave root, his root, the mist) gets M = V_orig^-1 V_new
_CJ = json.load(open(os.path.join(HERE, 'film_camera.json'))); _Ro = np.array(_CJ['R']); _Co = np.array(_CJ['C'])
_Vo = np.eye(4); _Vo[:3, :3] = _Ro; _Vo[:3, 3] = -_Ro @ _Co; _Voi = np.linalg.inv(_Vo)
VCAM = os.environ.get('VCAM', '1' if os.environ.get('PATH_MODE', 'rise') == 'rise' else '0') == '1'
def _look(C, Tt):
    z = Tt - C; z = z / np.linalg.norm(z); dn = np.array([0, -1.0, 0]); y = dn - (dn @ z) * z; y = y / np.linalg.norm(y); x = np.cross(y, z)
    V = np.eye(4); V[:3, :3] = np.array([x, y, z]); V[:3, 3] = -V[:3, :3] @ C; return V
def cam_C(f):                                       # the new camera's position (film world, before M is applied)
    f = min(f, FREEZE); rp, e_ = rise_pos(f); a = math.radians(E('CAM_ANG', 40)); Dd = E('CAM_D', 320)   # v12: back to v9's 40 degrees to his side (Arvind: v9's angle was better); v10/v11 had 0, straight in front
    return np.array([rp[0] + Dd * math.sin(a), E('CAM_Y0', 18) + (E('CAM_Y1', 40) - E('CAM_Y0', 18)) * e_, rp[2] + Dd * math.cos(a)])
def VM(f):
    if not VCAM: return np.eye(4)
    f = min(f, FREEZE); rp, e_ = rise_pos(f); C = cam_C(f)
    aim = WATER_Y + E('CAM_AIM0', 80) if f < T0 else max(WATER_Y + E('CAM_AIM0', 80), rp[1] + E('AIM', 0.55) * SIZE)   # looking up a little: the water line sits at the bottom edge
    return _Voi @ _look(C, np.array([rp[0], aim, rp[2]]))
def root(f):
    if PATHMODE in ('glide', 'rise'): f = min(f, FREEZE)
    if LUGIA_PATH and PATHMODE == 'rise':
        p = rise_pos(f)[0]
    elif LUGIA_PATH and PATHMODE == 'glide':
        # start behind the falling water in the middle of the fall (Lugia's own start at frame 124 is off to the side near
        # the camera: he popped in at the bottom right), end where Lugia hovers
        mid = np.array([0, SIZE * E('MID', 0.55), 0]); P0 = np.array([float(v) for v in os.environ.get('G0', '8,40,-90').split(',')]); P1 = _LB[-1] - mid
        # ease-out: he breaks through the falling water quickly (behind the water he smeared into a ghost for ~40 frames
        # in v7c) and slows into the hover
        # v8: the glide starts after the portal flash (G_START) so the flight out shows, eased in and out, ending at the freeze
        GS = E('G_START', 132); t_ = min(1.0, max(0.0, (f - GS) / (T1 - GS))); e_ = 1 - (1 - t_) ** E('EASE_OUT', 3) if os.environ.get('EASE', 'inout') == 'out' else ease(t_)
        p = P0 + (P1 - P0) * e_ + np.array([0, E('ARC', 12) * math.sin(math.pi * e_), 0])
        p = p + np.array([0, E('BOB', 1.5) * math.sin(2 * math.pi * f / 90) * min(1.0, max(0.0, (f - T0) / 30)), 0])
    elif LUGIA_PATH:
        p = lugia_at(T0 + max(0.0, f - T0) * SLOW) - np.array([0, SIZE * E('MID', 0.55), 0]) + np.array([0, 3 * math.sin(2 * math.pi * f / 80), 0])
    elif f <= KEYS[0][0]: p = KEYS[0][1].copy()
    elif f >= KEYS[-1][0]: p = KEYS[-1][1] + np.array([0, 3 * math.sin(2 * math.pi * (f - KEYS[-1][0]) / 80), 0])
    else:
        for (f0, p0), (f1, p1) in zip(KEYS, KEYS[1:]):
            if f0 <= f <= f1: p = p0 + (p1 - p0) * ease((f - f0) / (f1 - f0)); break
    # sway: lean forward while gliding (eases upright at the hover), slow roll and yaw, all small
    gl = 0.0 if PATHMODE == 'rise' else (1 - ease((f - T0) / (T1 - T0)) if f >= T0 else 1.0) if (LUGIA_PATH and PATHMODE == 'glide') else (1 - ease((f - KEYS[0][0]) / (KEYS[-1][0] - KEYS[0][0])) if f >= KEYS[0][0] else 1.0)
    pitch = math.radians(E('LEAN', 16)) * gl; roll = math.radians(E('ROLL_SW', 2 if PATHMODE == 'glide' else 6)) * math.sin(2 * math.pi * f / 95)
    yaw = math.radians(E('YAW_SW', 3 if PATHMODE == 'glide' else 9)) * math.sin(2 * math.pi * f / 140 + 0.7)
    # v6b: the film camera looks along +x (Lugia's body node turns its +z to -x for the whole film); facing +z showed him
    # side-on (and -90 showed his back: the shell on the wrong side), so he is turned to face +x, the camera
    yaw += math.radians(E('BASE_YAW', (-4 if PATHMODE in ('glide', 'rise') else 90) if LUGIA_PATH else 0))   # v12: back to v9, Lugia's heading (v11 had 0 for rise, facing the front camera)   # v7b: Lugia's own heading at the end (head/jaw toward +z, -4 deg); 60 faced the camera
    cx_, sx_ = math.cos(pitch), math.sin(pitch); cz_, sz_ = math.cos(roll), math.sin(roll); cy_, sy_ = math.cos(yaw), math.sin(yaw)
    Rx = np.array([[1, 0, 0], [0, cx_, -sx_], [0, sx_, cx_]]); Rz = np.array([[cz_, -sz_, 0], [sz_, cz_, 0], [0, 0, 1]]); Ry = np.array([[cy_, 0, sy_], [0, 1, 0], [-sy_, 0, cy_]])
    M = np.eye(4); M[:3, :3] = Ry @ Rz @ Rx; M[:3, 3] = p
    if f < SHOW: M[:3, 3] += np.array([0, -900.0, 0])                     # hidden until the portal opens
    return M
# mist (v2, Arvind: more fog, scarier, the whole room): two drifting layers of see-through sheets, on spare nodes
MIST = int(E('MIST', 1)); MS = E('MS', 64.0)
MIST_NODES = ([len(BONES) + 1] if GPOLYS else [len(BONES) + 1, len(BONES) + 2]) if MIST else []   # v8: one mist node frees one for the ghost
MBASE = {n_: np.array([100.0, 0, 0]) for n_ in MIST_NODES}
MDRIFT = {n_: np.array([E('DRIFT1', 0.22), 0, 0.04]) * (1 if k_ == 0 else -0.7) for k_, n_ in enumerate(MIST_NODES)}
GHOST_NODE = len(BONES) + 1 + len(MIST_NODES) if GPOLYS else None
GMID = np.array([0, SIZE * E('MID', 0.55), 0])
# ------------------------------------------------------------------ node worlds per frame -> local TRS (parent = still root)
NODE = {b: i + 1 for i, b in enumerate(BONES)}
PAR = {b: (J['parent'][b] if J['parent'].get(b) in NODE else None) for b in BONES}   # real hierarchy: bone offsets stay constant (small track)
# v6 smooth joints (Pokémon quality, no tearing): a vertex whose second bone is its parent/child with weight >= HELP_W
# follows a HELPER = the halfway rotation of the two about their joint. The helper's frame has its origin AT the joint
# and the parent's bind orientation, so in its parent node its offset is constant and only a rotation is animated.
from collections import Counter
from scipy.spatial.transform import Rotation as Rot, Slerp
HELP_W = E('HELP_W', 0.22)
def helper_of(b1, vw):
    if not vw or vw[1] < HELP_W: return None
    b2 = vw[0]
    if PAR.get(b2) == b1: return (b1, b2)
    if PAR.get(b1) == b2: return (b2, b1)
    return None
_cnt = Counter(h for p in polys for b1, vw in zip(p['vb'], p.get('vw', [None] * len(p['vb']))) for h in [helper_of(b1, vw)] if h)
FIRST_H = len(BONES) + 1 + len(MIST_NODES) + (1 if GPOLYS else 0); NH = max(0, min(int(E('HMAX', 9)), len(names) - FIRST_H))
HELPERS = [h for h, _ in _cnt.most_common(NH)]
for k_, h in enumerate(HELPERS): NODE[h] = FIRST_H + k_
for h in HELPERS:
    A_, B_ = h; Mh = np.eye(4); Mh[:3, :3] = HB[A_][:3, :3]; Mh[:3, 3] = HB[B_][:3, 3]; HB[h] = Mh; HBi[h] = np.linalg.inv(Mh)
def eff_bone(b1, vw):
    h = helper_of(b1, vw); return h if h in HB else b1
print('helpers', [a[4:] + '/' + b[4:] for a, b in HELPERS])
HELPER_NODES = {NODE[h]: h for h in HELPERS}
T_ = [[None] * nf for _ in names]; R_ = [[None] * nf for _ in names]; S_ = [[None] * nf for _ in names]
for f in range(nf):
    fz = min(f, FREEZE) if PATHMODE in ('glide', 'rise') else f
    Wf = J['frames'][str(min(int(fz), len(J['frames']) - 1))]; RT = root(f); Mv = VM(f); RTG = Mv @ RT
    if GPOLYS and f < SWITCH: RT = RT.copy(); RT[:3, 3] += np.array([0, -900.0, 0])     # his own body appears at the switch
    RT = Mv @ RT
    W0 = {b: RT @ H(Wf[b]) for b in BONES}; WW = {b: W0[b] @ SUPK for b in BONES}
    if GPOLYS:
        # the ghost: rigid in the artwork pose; at the switch it swells a little around him and shrinks into him (green drains)
        a_ = (f - SWITCH) / AURA; gs = 1.0 if a_ < 0 else (E('AURA_S0', 1.06) + (E('AURA_S1', 0.86) - E('AURA_S0', 1.06)) * min(1.0, a_))
        Mg = RTG @ np.array([[1, 0, 0, GMID[0]], [0, 1, 0, GMID[1]], [0, 0, 1, GMID[2]], [0, 0, 0, 1.0]]) @ np.diag([K * gs, K * gs, K * gs, 1])
        if f >= SWITCH + AURA: Mg = Mv @ np.linalg.inv(Mv) @ Mg; Mg[:3, 3] += Mv[:3, :3] @ np.array([0, -900.0, 0])
        WW['__ghost'] = Mg
    for h in HELPERS:
        A_, B_ = h; KA = W0[A_] @ HBi[A_]; KB = W0[B_] @ HBi[B_]
        Rt = Slerp([0, 1], Rot.from_matrix([orth(KA[:3, :3]), orth(KB[:3, :3])]))([0.5]).as_matrix()[0]
        Wh = np.eye(4); Wh[:3, :3] = Rt @ HB[h][:3, :3]; Wh[:3, 3] = (KB @ np.append(HB[h][:3, 3], 1))[:3]; WW[h] = Wh @ SUPK
    for i in range(len(names)):
        if i in MIST_NODES: T_[i][f], R_[i][f], S_[i][f] = Mv[:3, :3] @ (MBASE[i] + MDRIFT[i] * f) + Mv[:3, 3], orth(Mv[:3, :3]), [MS, MS, MS]; continue
        if i == GHOST_NODE:
            Lm = WW['__ghost']; sc = np.cbrt(np.linalg.det(Lm[:3, :3])); T_[i][f] = Lm[:3, 3]; R_[i][f] = orth(Lm[:3, :3] / sc); S_[i][f] = [sc, sc, sc]; continue
        if i in HELPER_NODES:
            h = HELPER_NODES[i]; Lm = np.linalg.inv(WW[h[0]]) @ WW[h]
            sc = np.cbrt(np.linalg.det(Lm[:3, :3])); T_[i][f] = Lm[:3, 3]; R_[i][f] = orth(Lm[:3, :3] / sc); S_[i][f] = [sc, sc, sc]; continue
        if i == 0 or i > len(BONES): T_[i][f], R_[i][f], S_[i][f] = np.zeros(3), np.eye(3), np.ones(3); continue
        b = BONES[i - 1]; Lm = (np.linalg.inv(WW[PAR[b]]) @ WW[b]) if PAR[b] else WW[b]
        sc = np.cbrt(np.linalg.det(Lm[:3, :3])); T_[i][f] = Lm[:3, 3]; R_[i][f] = orth(Lm[:3, :3] / sc); S_[i][f] = [sc, sc, sc]
anim_tpl = geom.read_bca(D(BM))[0]
bnodes = []
for i in range(len(names)):
    used = 1 <= i <= len(BONES) or i in MIST_NODES or i in HELPER_NODES or i == GHOST_NODE
    bnodes.append(dict(flags_keep=None if used else 1, T=T_[i], R=R_[i], S=S_[i], idx=i, rate=int(E('HALFRATE', 1)) if used else 0))
bnodes[0]['flags_keep'] = None; bnodes[0]['rate'] = 0
new_bca = bca_write.build(nf, bnodes, template=D(BM))
# ------------------------------------------------------------------ render commands: our node list, then the two draws
mo = m['off']; size, rc, mat_o, shp, invo = struct.unpack_from('<5I', d, mo)
o = mo + rc; ops = []
while True:
    op = d[o]; n = 2 + 3 * d[o + 2] if op == 9 else nitro.RCMD_LEN[op]; ops.append((op, list(d[o + 1:o + 1 + n]))); o += 1 + n
    if op == 1: break
RC_LEN = o - (mo + rc)
draws = []; cm = None
for op, p in ops:
    if op in (4, 0x24, 0x44): cm = p[0]
    if op == 5: draws.append((cm, p[0]))
KEEP = 30
cmd = bytearray([0x26, 0, 0, 0, 0])                                    # root: own parent, stored in slot 0
for b in BONES: pn = NODE[PAR[b]] if PAR[b] else 0; cmd += bytes([0x66, NODE[b], pn, 0, NODE[b], pn])   # restore the parent's slot, store in slot = node
for mn in MIST_NODES + ([GHOST_NODE] if GPOLYS else []): cmd += bytes([0x66, mn, 0, 0, mn, 0])
for hn, h in HELPER_NODES.items(): cmd += bytes([0x66, hn, NODE[h[0]], 0, hn, NODE[h[0]]])   # helpers under their parent bone
cmd += bytes([0x02, 0, 1])                                            # node 0 visible (the draws check it)
for mt, sh in draws: cmd += bytes([0x03, 0, 0x0b, 0x04, mt, 0x05, sh])
assert len(cmd) + 1 <= RC_LEN, (len(cmd), RC_LEN)
d[mo + rc:mo + rc + RC_LEN] = cmd + bytes(RC_LEN - 1 - len(cmd)) + bytes([1])
SHAPE_OF = {mats[mt]['tex']: sh for mt, sh in draws}; MAT_OF = {mats[mt]['tex']: mt for mt, sh in draws}
print('draws', [(mats[mt]['name'], mats[mt]['tex'], sh) for mt, sh in draws], 'render cmds', len(cmd), '/', RC_LEN)
ents, _ = nitro.dict_read(bytes(d), mo + shp, 4); shapes = []; shapehdr = []
for e, sn, _ in ents:
    oo = mo + shp + nitro.u32(e, 0); dummy, ssz, flag, co, cl = struct.unpack_from('<HHIII', d, oo); shapes.append((oo + co, cl)); shapehdr.append(oo)
# ------------------------------------------------------------------ swatch textures
GROUP = {'coat': 0, 'weed': 0, 'skin': 0, 'hat': 0, 'kelp2': 0, 'kelp3': 0, 'mask': 1, 'bone': 1, 'shell': 1, 'eye': 1, 'socket': 1, 'blade': 1, 'mist': 1}
COL = {n: c for n, c in zip(J['names'], J['palette'])}; COL['eye'] = [170, 255, 245]; COL['socket'] = [4, 6, 6]; COL['mist'] = [int(x) for x in os.environ.get('MISTC', '176,214,190').split(',')]
TEXN = {0: 'lugia_s', 1: 'lugia_foot'}; TS = {0: 64, 1: 32}
TSZ = {0: (64, 64), 1: (32, 32)}; TFMT = {0: 3, 1: 3}; ORIG_SZ = dict(TSZ)
if 'tex' in J and all(len(J['tex'][str(g)]) >= 6 for g in (0, 1)):     # v7 atlases (tex_atlas.py): own size and format
    for g in (0, 1): TSZ[g] = tuple(J['tex'][str(g)][3:5]); TFMT[g] = J['tex'][str(g)][5]
if 'tex' in J:                                                  # the artwork's scheme: near-black coat, bright kelp strands, sea-green skin
    # v6b: the film's light made the old kelp greens lime; the artwork is a near-black coat with dark green kelp, olive
    # beard strands and sea-teal hands and feet (env SCHEME=old for the v5 colours)
    if os.environ.get('SCHEME', 'v6') == 'old':
        COL.update({'coat': [24, 34, 28], 'kelp2': [62, 102, 46], 'kelp3': [100, 146, 62], 'weed': [116, 156, 66], 'skin': [70, 136, 132], 'hat': [26, 30, 28]})
    else:
        COL.update({'coat': [16, 22, 19], 'kelp2': [28, 48, 30], 'kelp3': [52, 84, 40], 'weed': [70, 104, 46], 'skin': [44, 104, 112], 'hat': [18, 21, 19]})
labs = {g: [l for l in COL if GROUP.get(l, 0) == g] for g in (0, 1)}
PALG = {g: [COL[l] for l in labs[g]] for g in (0, 1)}
IDX = {}; CELL = {}
TEXMODE = 'tex' in J and all('uv' in p for p in polys)
HYB = 'tex' in J and not TEXMODE
if HYB: GROUP.update({k: 0 for k in GROUP}); labs = {0: [l for l in COL if l not in ('eye', 'socket', 'mist')], 1: []}; PALG = {0: [COL[l] for l in labs[0]], 1: []}
for g in ([] if TEXMODE else ((0,) if HYB else (0, 1))):
    n_ = TS[g]; c4 = n_ // 4; ix = np.zeros((n_, n_), int)
    for k, l in enumerate(labs[g]):
        y, x = divmod(k, 4); ix[y * c4:(y + 1) * c4, x * c4:(x + 1) * c4] = k; CELL[l] = ((x + 0.5) / 4, 1 - (y + 0.5) / 4)
    IDX[g] = ix
if TEXMODE or HYB:                                             # painted textures from the turnaround (tex_project.py)
    for g in ((0, 1) if TEXMODE else (1,)):
        png, npy, pal_ = J['tex'][str(g)][:3]; IDX[g] = np.load(os.path.join(os.path.dirname(GJ), os.path.basename(npy))); PALG[g] = [list(c) for c in pal_]
    CELL['mist'] = tuple(J['mist_uv']) if 'mist_uv' in J else (30.5 / 32, 1 - 30.5 / 32)
# ------------------------------------------------------------------ strips
up = 1.0
def v10(q):
    q = [int(round(v / K * 64)) for v in q]; assert all(-512 <= x < 512 for x in q), q
    return (q[0] & 1023) | (q[1] & 1023) << 10 | (q[2] & 1023) << 20
def n10(q):
    a = [max(-512, min(511, int(round(v * 512)))) & 1023 for v in q]; return a[0] | a[1] << 10 | a[2] << 20
def tc(uv, g):
    w_, h_ = TSZ[g]; a_ = int(round(uv[0] * w_ * 16)); b_ = int(round((1 - uv[1]) * h_ * 16)); return (b_ & 0xffff) << 16 | (a_ & 0xffff)
def pack_cmds(cmds):
    out = bytearray()
    for k in range(0, len(cmds), 4):
        grp = cmds[k:k + 4] + [(0, [])] * (4 - len(cmds[k:k + 4])); out += bytes(op for op, _ in grp)
        for _, ps in grp:
            for v in ps: out += struct.pack('<I', v & 0xffffffff)
    return out
# smooth normals per position (film frame, bind pose)
from collections import defaultdict
nacc = defaultdict(lambda: np.zeros(3))
FP = [[P(q) + (np.array([0, 0, E('EYE_DZ', 2.0)]) if p['lab'] == 'eye' else 0) for q in p['p']] for p in polys]   # the glow in front of the dark socket
for pp in FP:
    n = np.cross(pp[1] - pp[0], pp[2] - pp[0])
    for q in pp: nacc[tuple(np.round(q, 2))] += n
def vnorm(q):
    n = nacc[tuple(np.round(q, 2))]; return n / (np.linalg.norm(n) + 1e-9)
LIGHTS = int(E('LIGHTS', 1))
work = {0: [], 1: []}
for g in (0, 1):
    tris = []; quads = []
    for p, pp in zip(polys, FP):
        pg = p['g'] if (TEXMODE or HYB) else GROUP[p['lab']]
        if pg != g: continue
        vws = p.get('vw', [None] * len(p['vb']))
        vv = [(pp[k], eff_bone(p['vb'][k], vws[k]), tuple(p['uv'][k]) if 'uv' in p else p['lab']) for k in range(len(pp))]
        (quads if len(vv) == 4 else tris).append(vv)
    # quads (v6, like the Pokémon models: one DS polygon each) go out as quad lists, 24 per block
    for k0 in range(0, len(quads), 24):
        cmds = [(0x40, [1])]; curb = None; lastt = None
        for qd in quads[k0:k0 + 24]:
            for q, b, l in qd:
                loc = (HBi[b] @ np.append(q, 1))[:3]
                if b != curb: cmds.append((0x14, [NODE[b]])); curb = b
                t_ = tc(l if isinstance(l, tuple) else CELL[l], g)
                if t_ != lastt: cmds.append((0x22, [t_])); lastt = t_
                if LIGHTS: cmds.append((0x21, [n10(HBi[b][:3, :3] @ vnorm(q))]))
                cmds.append((0x24, [v10(loc)]))
        work[g].append(cmds + [(0x41, [])])
    # greedy strips over shared (position, bone, label) vertices
    keyof = {}; verts = []
    def vid(q, b, l):
        kk = tuple(np.round(q, 2)) + (b, l)
        if kk not in keyof: keyof[kk] = len(verts); verts.append((q, b, l))
        return keyof[kk]
    T = [tuple(vid(*v) for v in t) for t in tris]; edge = {}
    for ti, t in enumerate(T):
        for a_, b_ in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])): edge.setdefault(frozenset((a_, b_)), []).append(ti)
    used = [False] * len(T)
    # v7b: a strip draws triangle k as (s[k], s[k+1], s[k+2]) for even k and (s[k+1], s[k], s[k+2]) for odd k; a triangle
    # is only added when that order is its own winding. v6's builder ignored it, which did not show while both sides were
    # drawn but left holes once back faces were culled (the magenta test)
    def cyc(a, b, c, t): return (a, b, c) in ((t[0], t[1], t[2]), (t[1], t[2], t[0]), (t[2], t[0], t[1]))
    FIXW = os.environ.get('STRIP_FIX', '1') == '1'
    def grow(st):
        while len(st) < 40:
            k = len(st) - 2; a, b = st[-2], st[-1]
            cand = [t for t in edge.get(frozenset((a, b)), []) if not used[t]]
            ok = None
            for t in cand:
                x = [v for v in T[t] if v not in (a, b)][0]
                if not FIXW or (cyc(a, b, x, T[t]) if k % 2 == 0 else cyc(b, a, x, T[t])): ok = (t, x); break
            if ok is None: return st
            used[ok[0]] = True; st.append(ok[1])
        return st
    for s0 in range(len(T)):
        if used[s0]: continue
        used[s0] = True; st = grow(list(T[s0]))
        if not FIXW: st = grow(list(reversed(st)))
        cmds = [(0x40, [2])]; curb = None; lastt = None
        for vi in st:
            q, b, l = verts[vi]; loc = (HBi[b] @ np.append(q, 1))[:3]
            if b != curb: cmds.append((0x14, [NODE[b]])); curb = b
            t_ = tc(l if isinstance(l, tuple) else CELL[l], g)
            if t_ != lastt: cmds.append((0x22, [t_])); lastt = t_
            if LIGHTS: cmds.append((0x21, [n10(HBi[b][:3, :3] @ vnorm(q))]))
            cmds.append((0x24, [v10(loc)]))
        work[g].append(cmds + [(0x41, [])])
if MIST:
    rng = np.random.default_rng(int(E('MSEED', 5)))
    def quad_h(cx, cy, cz, w, dz):               # a flat sheet over the water
        return [np.array([cx - w, cy, cz - dz]), np.array([cx + w, cy, cz - dz]), np.array([cx + w, cy, cz + dz]), np.array([cx - w, cy, cz + dz])]
    def quad_v(cx, cy, cz, w, h):                # a veil facing the camera
        return [np.array([cx - w, cy - h, cz]), np.array([cx + w, cy - h, cz]), np.array([cx + w, cy + h, cz]), np.array([cx - w, cy + h, cz])]
    LAYERS = []
    for li, (y, alpha) in enumerate(((14, int(E('MA1', 13))), (22, int(E('MA2', 11))), (32, int(E('MA3', 9))), (46, int(E('MA4', 7))))):
        qs = [quad_h(rng.uniform(-150, 380), y + rng.uniform(-3, 3), rng.uniform(-130, 150), rng.uniform(50, 110), rng.uniform(30, 70)) for _ in range(9)]
        LAYERS.append((MIST_NODES[0], alpha, 33 + li, qs))
    for li, (z, alpha) in enumerate((((-15, int(E('MV1', 7))), (30, int(E('MV2', 6))), (80, int(E('MV3', 5))))[:int(E('VEILS', 1))])):
        qs = [quad_v(rng.uniform(-120, 330), rng.uniform(35, 75), z + rng.uniform(-8, 8), rng.uniform(60, 110), rng.uniform(25, 45)) for _ in range(6)]
        LAYERS.append((MIST_NODES[-1], alpha, 40 + li, qs))
    for node, alpha, pid, qs in LAYERS:
        attr = (0 << 0) | (0 << 4) | (3 << 6) | (1 << 15) | (alpha << 16) | (pid << 24)      # unlit, modulate, both faces, fog, see-through
        cmds = [(0x29, [attr]), (0x14, [node]), (0x20, [0x7fff]), (0x22, [tc(CELL['mist'], 1)]), (0x40, [1])]
        for q in qs:
            for v in q: cmds.append((0x24, [v10((v - MBASE[node]) / MS * K)]))
        work[1].append(cmds + [(0x41, [])])
    print('mist layers', len(LAYERS))
MARKERS = os.environ.get('MARKERS', '')
if MARKERS and MIST:
    # camera calibration (v9): opaque coloured cubes at known film-space points, on the still mist node
    mn = MIST_NODES[0]; cmk = [(0x29, [0xC0 | (31 << 16) | (60 << 24)]), (0x2A, [0]), (0x14, [mn])]
    for mk in MARKERS.split(';'):
        x, y, z, rr, gg, bb = [float(v) for v in mk.split(',')]; c = np.array([x, y, z]); hs = E('MK_SIZE', 3.0)
        cmk.append((0x20, [int(rr) >> 3 | (int(gg) >> 3) << 5 | (int(bb) >> 3) << 10])); cmk.append((0x40, [1]))
        for ax in range(3):
            for sg in (-1, 1):
                u_, w_ = [a for a in range(3) if a != ax]
                for du, dw in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    v = c.copy(); v[ax] += sg * hs; v[u_] += du * hs; v[w_] += dw * hs
                    cmk.append((0x24, [v10((v - MBASE[mn]) / MS * K)]))
        cmk.append((0x41, []))
    work[1].append(cmk); print('markers', len(MARKERS.split(';')))
if GPOLYS:
    # colour per vertex like the intro's ghost: the painted texture's brightness at the vertex turned into pale sea green
    # (build_grav4.py: (0.35l+10, 1.05l+60, 0.8l+44)), the eyes' glow kept bright
    def tex_rgb(g, uv):
        ix = IDX[g]; h_, w_ = ix.shape; x = int(min(w_ - 1, max(0, uv[0] * w_))); y = int(min(h_ - 1, max(0, (1 - uv[1]) * h_)))
        blk = ix[max(0, y - 1):y + 2, max(0, x - 1):x + 2].ravel(); return np.mean([PALG[g][int(c)] for c in blk], 0)
    def ghost_col(c):
        if c[2] > 200 and c[1] > 200 and c[0] < 200: return (200, 255, 230)
        l = 0.3 * c[0] + 0.55 * c[1] + 0.15 * c[2]; gb = E('GHOST_GAIN', 1.0); q_ = E('GHOST_Q', 24); l = round(l / q_) * q_   # steps: fewer COLOR commands
        return tuple(min(248, v) for v in ((0.35 * l + 10) * gb, (1.05 * l + 60) * gb, (0.8 * l + 44) * gb))
    def c555(c): rr, gg, bb = (int(round(v / 255 * 31)) for v in c); return rr | gg << 5 | bb << 10
    GA = int(E('GHOST_ALPHA', 14)); gattr = 0x80 | (GA << 16) | (int(E('GHOST_ID', 50)) << 24)
    head_ = [(0x29, [gattr]), (0x2A, [0]), (0x14, [GHOST_NODE])]
    gv = {}; gverts = []
    def gvid(q, col):
        kk = tuple(np.round(q, 2)) + tuple(int(v) for v in col)
        if kk not in gv: gv[kk] = len(gverts); gverts.append((q, col))
        return gv[kk]
    gtris = []; gquads = []
    for p in GPOLYS:
        vs = [gvid(P(q) - GMID, ghost_col(tex_rgb(p['g'], uv))) for q, uv in zip(p['p'], p['uv'])]
        (gquads if len(vs) == 4 else gtris).append(tuple(vs))
    def emit(seq, prim):
        cmds = [(0x40, [prim])]; lastc = None
        for vi in seq:
            q, col = gverts[vi]; c_ = c555(col)
            if c_ != lastc: cmds.append((0x20, [c_])); lastc = c_
            cmds.append((0x24, [v10(q)]))
        return cmds + [(0x41, [])]
    first = True
    for k0 in range(0, len(gquads), 24):
        work[1].append((head_ if first else []) + emit([v for qd in gquads[k0:k0 + 24] for v in qd], 1)); first = False
    gedge = {}
    for ti, t in enumerate(gtris):
        for a_, b_ in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])): gedge.setdefault(frozenset((a_, b_)), []).append(ti)
    gused = [False] * len(gtris)
    def gcyc(a, b, c, t): return (a, b, c) in ((t[0], t[1], t[2]), (t[1], t[2], t[0]), (t[2], t[0], t[1]))
    for s0 in range(len(gtris)):
        if gused[s0]: continue
        gused[s0] = True; st = list(gtris[s0])
        while len(st) < 40:
            k = len(st) - 2; a, b = st[-2], st[-1]; ok = None
            for t in gedge.get(frozenset((a, b)), []):
                if gused[t]: continue
                x = [v for v in gtris[t] if v not in (a, b)][0]
                if gcyc(a, b, x, gtris[t]) if k % 2 == 0 else gcyc(b, a, x, gtris[t]): ok = (t, x); break
            if ok is None: break
            gused[ok[0]] = True; st.append(ok[1])
        work[1].append((head_ if first else []) + emit(st, 2)); first = False
    print('ghost', len(GPOLYS), 'polys on node', GHOST_NODE, 'switch', SWITCH, 'aura', AURA, 'alpha', GA)
# v6: the two shapes' display lists lie back to back (shape 0 then shape 1, then the inverse bind matrices), so the
# boundary between them moves to where the body needs it; only the two shape headers' offset/length fields change
blobs = {}
for g in (0, 1):
    cmds = [(0x13, [KEEP]), (0x20, [0x7fff])]
    for w in work[g]: cmds += w
    blobs[g] = pack_cmds(cmds + [(0x14, [KEEP])])
lay = sorted(((shapes[SHAPE_OF[TEXN[g]]][0], g) for g in (0, 1)))
start0 = lay[0][0]; end1 = lay[1][0] + shapes[SHAPE_OF[TEXN[lay[1][1]]]][1]
assert lay[0][0] + shapes[SHAPE_OF[TEXN[lay[0][1]]]][1] == lay[1][0], 'shape display lists are not back to back'
need = sum(len(b) for b in blobs.values()); room = end1 - start0
print('display lists', {g: len(b) for g, b in blobs.items()}, 'need', need, 'room', room)
assert need <= room, 'strips do not fit'
pos = start0
for k_, (_, g) in enumerate(lay):
    sh = SHAPE_OF[TEXN[g]]; b = blobs[g]
    ln = len(b) if k_ == 0 else end1 - pos                                   # the last list keeps the slack (zero padded)
    d[pos:pos + ln] = b + bytes(ln - len(b))
    struct.pack_into('<II', d, shapehdr[sh] + 8, pos - shapehdr[sh], ln)    # offset from the shape header, length
    struct.pack_into('<I', d, shapehdr[sh] + 4, struct.unpack_from('<I', d, shapehdr[sh] + 4)[0] | 0x2 | 0x8)
    print('group', g, TEXN[g], 'strips', len(work[g]), 'bytes', len(b), 'slot', ln); pos += ln
# ------------------------------------------------------------------ materials (lit like Lugia, white diffuse), textures, palettes
def c555(c): rr, gg, bb = (int(round(v / 255 * 31)) for v in c); return rr | gg << 5 | bb << 10
for g in (0, 1):
    mt = MAT_OF[TEXN[g]]; mo_ = mats[mt]['off']; pa = struct.unpack_from('<I', d, mo_ + 12)[0]
    print('material', mats[mt]['name'], 'polygon attr %08x' % pa)
    # v6g: the parts are closed and their normals agree, so back faces are culled (front only, 0x80). Drawing both sides
    # showed the brim's underside and the solidify inner sheets as a black band over the face; it also halves the
    # polygons the DS has to draw (env BOTH=1 for the old 0xC0)
    sides = 0xC0 if os.environ.get('BOTH') == '1' else 0x80
    struct.pack_into('<I', d, mo_ + 12, (pa & ~0xF & ~(31 << 16) & ~0xC0) | sides | (31 << 16) | (pa & 0xF if LIGHTS else 0))
    if not LIGHTS:                                  # unlit: white vertex colour, the painted texture as it is
        struct.pack_into('<II', d, mo_ + 4, 31 | 31 << 5 | 31 << 10 | 0x8000, 0)
    if LIGHTS:
        struct.pack_into('<I', d, mo_ + 4, 31 | 31 << 5 | 31 << 10 | 0x8000 | (int(E('AMB', 26)) * 0x421) << 16)
        # v6d: the face (shape 1: painted head front + the unlit mist) glows a little more than the body, so the pale beak
        # and the blue eyes read in the film's light now that he faces the camera
        EM = int(E('EMI1', 13)) if g == 1 else int(E('EMI', 7)); struct.pack_into('<I', d, mo_ + 8, (EM | EM << 5 | EM << 10) << 16)
BIGTEX = any(TFMT[g] != 3 or TSZ[g] != ORIG_SZ[g] for g in TEXN)
if BIGTEX:                                          # v7: the TEX0 block is rebuilt for the bigger 8-bpp textures
    _bo = [b for b in r['blocks'] if d[b:b + 4] == b'TEX0'][0]; _tp = nitro.read_tex(bytes(d), _bo)['pals']; texd = {}; pald = {}
    for g, tn_ in TEXN.items():
        ix = IDX[g]; h_, w_ = ix.shape; assert (w_, h_) == TSZ[g], (tn_, ix.shape, TSZ[g]); fl = ix.astype(np.uint8).reshape(-1)
        texd[tn_] = (TFMT[g], w_, h_, bytes(fl) if TFMT[g] == 4 else bytes(fl[0::2] | (fl[1::2] << 4)))
        pn = [p_['name'] for p_ in _tp if p_['name'].startswith(tn_)][0]
        pald[pn] = b''.join(struct.pack('<H', c555(PALG[g][i]) if i < len(PALG[g]) else 0) for i in range(256 if TFMT[g] == 4 else 16))
    d = bytearray(tex0_grow.grow(d, texd, pald))
    for g, tn_ in TEXN.items():
        struct.pack_into('<HH', d, mats[MAT_OF[tn_]]['off'] + 32, *TSZ[g])
    print('textures rebuilt', {tn_: TSZ[g] for g, tn_ in TEXN.items()}, 'model', len(d))
for bo in ([] if BIGTEX else r['blocks']):
    if d[bo:bo + 4] != b'TEX0': continue
    t = nitro.read_tex(bytes(d), bo); fh = t['raw_hdr']; tbo, pbo = fh[6], fh[17]
    ents2, _ = nitro.dict_read(bytes(d), bo + fh[4], 8)
    for (e2, nm2, eo), x in zip(ents2, t['texs']):
        for g, tn_ in TEXN.items():
            if x['name'] != tn_: continue
            ix = IDX[g]; assert ix.shape == (x['h'], x['w']) and x['fmt'] == 3, (tn_, x['w'], x['h'], x['fmt'])
            struct.pack_into('<I', d, eo, x['param'] & ~(1 << 29)); off = (x['param'] & 0xffff) << 3; fl = ix.astype(np.uint8).reshape(-1)
            d[bo + tbo + off: bo + tbo + off + x['w'] * x['h'] // 2] = bytes(fl[0::2] | (fl[1::2] << 4))
    for pl in t['pals']:
        for g, tn_ in TEXN.items():
            if pl['name'].startswith(tn_):
                for i in range(16): struct.pack_into('<H', d, bo + pbo + pl['off'] + 2 * i, c555(PALG[g][i]) if i < len(PALG[g]) else 0)
                print('palette', pl['name'], len(PALG[g]), 'colours')
# v7b (Arvind: the ring around Lugia when it screams lay in front of Gravriel, who arrives later): the cave's three ring
# nodes (polySurface758/759/760, the wave2/3/6 discs that grow from film frame ~150) follow him, keeping their offset to
# Lugia's body at the hover. All cave tracks are re-encoded from their decoded values; only the rings' translation changes.
if os.environ.get('RING_FOLLOW', '1') == '1':
    mc = nitro.read_bmd(D(0))['models'][0]; ac = geom.read_bca(D(1))[0]; nfc = ac['nframes']; corder = [p_ for op, p_ in mc['rcmds'] if op in (6, 0x26, 0x46, 0x66)]
    def cworld(trs):
        Wd = {}
        for p_ in corder:
            i_, pa_ = p_[0], p_[1]; t_, rr_, sc_ = trs[i_]; Tm = np.eye(4); Tm[:3, 3] = t_; Rm = np.eye(4); Rm[:3, :3] = rr_; Sm = np.diag(list(sc_) + [1])
            Lm_ = (Tm @ np.diag([1 / x if x else 0 for x in trs[pa_][2]] + [1]) @ Rm @ Sm) if pa_ != i_ else Tm @ Rm @ Sm
            Wd[i_] = (Wd[pa_] if pa_ != i_ and pa_ in Wd else np.eye(4)) @ Lm_
        return Wd
    BURST = int(E('BURST_NODE', 1))
    RING_MODE = os.environ.get('RING_MODE', 'halo')   # v13 'halo' (facing the camera behind his head); 'hoop' = v10-v12
    HALO_N = {3: np.array([0, 0, 1.0]), 4: np.array([0.148, 0.928, 0.342])}   # front face normal (by winding) of the disc shapes 27/28
    HALO_C = {3: np.array([0, 0, 0.0]), 4: np.array([7.97, -6.405, 9.685])}   # disc centre (fan hub) in the shape's units
    def _rot_between(a_, b_):                       # the smallest rotation taking direction a_ to b_
        a_ = a_ / np.linalg.norm(a_); b_ = b_ / np.linalg.norm(b_); v_ = np.cross(a_, b_); c_ = float(a_ @ b_)
        if c_ < -0.9999: return -np.eye(3) + 2 * np.outer(np.array([1.0, 0, 0]), np.array([1.0, 0, 0]))
        K_ = np.array([[0, -v_[2], v_[1]], [v_[2], 0, -v_[0]], [-v_[1], v_[0], 0]]); return np.eye(3) + K_ + K_ @ K_ / (1 + c_)
    RINGS = [int(x) for x in os.environ.get('RING_NODES', '3,4,5' if PATHMODE == 'rise' else '1,3,4,5').split(',')]   # 3/4 = the band rings (de_ap_e4), 5 = sparkles
    W160 = cworld(geom.node_trs(mc, ac, 160)); off = {k: W160[k][:3, 3] - _LB[-1] for k in RINGS}
    mid_ = np.array([0, SIZE * E('MID', 0.55), 0])
    CT = {i: [] for i in range(len(mc['nodes']))}; CR = {i: [] for i in CT}; CS = {i: [] for i in CT}
    for f in range(nfc):
        trs = geom.node_trs(mc, ac, f); Wd = cworld(trs); body = root(min(f, nf - 1))[:3, 3] + mid_
        Mv = VM(f); rpw = rise_pos(f)[0]
        for i in CT:
            t_, rr_, sc_ = trs[i]; t_ = np.array(t_, float)
            if i == 0 and VCAM:                          # the whole cave moves the other way of the new camera
                W0n = Mv @ Wd[0]; sc0 = np.array(sc_, float); t_ = W0n[:3, 3]; rr_ = orth(W0n[:3, :3] @ np.diag(1 / np.where(sc0 == 0, 1, sc0)))
            if i == BURST and PATHMODE == 'rise':      # the portal burst (pCylinder1, de_ap_e1) comes up from the water where he rises
                par = [p_[1] for p_ in corder if p_[0] == i][0]; Wp = Wd[par] if par != i else np.eye(4)
                t_ = (np.linalg.inv(Wp) @ np.append([rpw[0], E('BURST_Y', 9), rpw[2]], 1))[:3]
                # v10: the burst stretches along its own z (out of the fall toward the camera); turned so z points up, it
                # shoots straight up out of the water where he rises (Arvind: "the portal must be vertical now")
                if os.environ.get('BURST_UP', '1') == '1': rr_ = np.array([[1, 0, 0], [0, 0, 1.0], [0, -1.0, 0]]) @ np.array(rr_, float)
                if os.environ.get('BURST_UP', '1') == '1' and os.environ.get('BURST_TRACK', '1') == '1':
                    # v14 (Arvind on v13: the portal seemed off, not placed or timed with his arrival): the cylinder (8-gon,
                    # radius 90, 25 deep) has its axis 90 units off its own origin (local y), so stood up it rose beside
                    # him, and the original collapse (y scale 1 -> -0.37) flattened it sideways into two strips. Its own
                    # track now, on his rise axis and timed with him (his head breaks the water at ~126.5, his feet leave
                    # it at ~141): a short ring of light opens on the water (BO0-BO1), shoots up as his head comes through
                    # (BO1-BU1) and narrows into him (BC0-BC1), so he comes out of it
                    def _ss(a0, a1, x): tq = min(1.0, max(0.0, (x - a0) / (a1 - a0))); return tq * tq * (3 - 2 * tq)
                    BO0, BO1, BU1, BC0, BC1 = E('BO0', 120), E('BO1', 124), E('BU1', 128), E('BC0', 129), E('BC1', 137)
                    rad = E('BR', 0.8) * _ss(BO0, BO1, f) * (1 - _ss(BC0, BC1, f)); hz = E('BZ0', 0.8) + (E('BZ', 12) - E('BZ0', 0.8)) * _ss(BO1, BU1, f)
                    if f < BO0 or f >= BC1: rad, hz = 0.0, 0.0
                    sc_ = [rad, rad, hz]; Rw = np.array([[1, 0, 0], [0, 0, 1.0], [0, -1.0, 0]])
                    org = np.array([rpw[0], E('BURST_Y', 9), rpw[2]]) - Rw @ np.array([0, 90.0 * rad, 0])   # the axis (local y 90) on his rise axis
                    rr_ = orth(Wp[:3, :3]).T @ Rw; t_ = (np.linalg.inv(Wp) @ np.append(org, 1))[:3]
            elif i in RINGS and PATHMODE == 'rise' and i in (3, 4) and RING_MODE == 'halo':
                # v13 (Arvind on v12: the ring/halo should come out from behind Gravriel, so it looks like it comes from his
                # head, facing the camera): both band discs (12-gon fans: node 3 rim 143, node 4 rim 202 in their own
                # units) turn so their front faces the camera, centred on his head and HALO_BACK behind it along the view
                # line; they grow as in the original (frames 152-160), so two concentric rings widen out from behind him
                par = [p_[1] for p_ in corder if p_[0] == i][0]; Wp = Wd[par] if par != i else np.eye(4)
                Cc = cam_C(f); head = body + np.array([0, E('HALO_DY', 32), 0]); dv = Cc - head; dv = dv / np.linalg.norm(dv)
                ctr = head - E('HALO_BACK', 32) * dv
                Rw = _rot_between(HALO_N[i], dv); rr_ = orth(Wp[:3, :3]).T @ Rw
                sc_ = [v * E('HALO_SCALE', 0.30) for v in sc_]
                t_ = (np.linalg.inv(Wp) @ np.append(ctr - Rw @ (HALO_C[i] * sc_[0]), 1))[:3]   # the disc's centre (not the node origin) on ctr
            elif i in RINGS and PATHMODE == 'rise' and i in (3, 4):
                # v10: seen from straight in front the band rings were a circle far bigger than the screen; they become a hoop
                # around him: laid flat (node 3's disc faced the old camera) and scaled down (RING_SCALE)
                par = [p_[1] for p_ in corder if p_[0] == i][0]; Wp = Wd[par] if par != i else np.eye(4)
                # node 3 (a flat disc, normal = its z): a halo facing the camera, centred on his chest, slightly behind him;
                # node 4 (a tilted ring): a hoop round his middle, tipped 30 degrees toward the camera so it reads as an ellipse
                if os.environ.get('RING_ORIENT', '0') != '1':   # v10: the own orientation; turning the discs showed their culled back
                    t_ = (np.linalg.inv(Wp) @ np.append(body + (np.array([0, E('HOOP_DY', 20), 0]) if i == 4 else off[i]), 1))[:3]   # the hoop centred on him
                    if i == 4:                                  # the ring stood edge-on to the low front camera: tipped back so it opens
                        tl = math.radians(E('HOOP_TILT', 25)); rr_ = np.array([[1, 0, 0], [0, math.cos(tl), -math.sin(tl)], [0, math.sin(tl), math.cos(tl)]]) @ np.array(rr_, float)
                elif i == 3:
                    t_ = (np.linalg.inv(Wp) @ np.append(body + np.array([0, E('HALO_DY', 12), -E('HALO_BACK', 14)]), 1))[:3]; rr_ = np.eye(3)
                else:
                    t_ = (np.linalg.inv(Wp) @ np.append(body, 1))[:3]
                    from scipy.spatial.transform import Rotation as _R
                    tl = math.radians(E('HOOP_TILT', 30)); dn_ = np.array([0, math.cos(tl), math.sin(tl)])
                    rr_ = _R.align_vectors([dn_], [np.array([-0.15, -0.93, -0.34]) / np.linalg.norm([-0.15, -0.93, -0.34])])[0].as_matrix()
                sc_ = [v * E('RING_SCALE', 0.33) for v in sc_]
            elif i in RINGS:
                par = [p_[1] for p_ in corder if p_[0] == i][0]; Wp = Wd[par] if par != i else np.eye(4)
                t_ = (np.linalg.inv(Wp) @ np.append(body + off[i], 1))[:3]
            CT[i].append(t_); CR[i].append(np.array(rr_, float)); CS[i].append(list(sc_))
    cnodes = [dict(flags_keep=None, T=CT[i], R=CR[i], S=CS[i], idx=i, rate=0) for i in CT]
    F[1] = lz10_enc(bca_write.build(nfc, cnodes, template=D(1))); print('ring nodes follow him', RINGS, 'cave anim', len(F[1]))
F[MM] = lz10_enc(bytes(d)); F[BM] = lz10_enc(new_bca)
open(DST, 'wb').write(pack(F)); print('model', len(F[MM]), 'anim', len(F[BM]), 'file', len(pack(F)))
