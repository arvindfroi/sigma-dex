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
import nitro, geom, bca_write
SRC, DST, GJ = sys.argv[1:4]
E = lambda k, d: float(os.environ.get(k, d))
MM, BM = 5, 6
F = unpack(open(SRC, 'rb').read()); D = lambda i: lz11_dec(F[i]) if F[i][:1] == b'\x11' else F[i]
d = bytearray(D(MM)); r = nitro.read_bmd(bytes(d)); m = r['models'][0]; mats = m['mats']; names = [n for n, _ in m['nodes']]
nf = geom.read_bca(D(BM))[0]['nframes']
J = json.load(open(GJ)); BONES = J['bones']; polys = J['polys']
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
SHOW, RISE0, RISE1, OUT1 = E('SHOW', 96), E('RISE0', 100), E('RISE1', 142), E('OUT1', 168)
A = np.array([E('AX', 0), E('AY', -150), E('AZ', -60)]); B_ = np.array([E('BX', 0), E('BY', 30), E('BZ', -45)]); C = np.array([E('CX', 0), E('CY', 58), E('CZ', 48)])
def ease(t): t = min(1.0, max(0.0, t)); return t * t * (3 - 2 * t)
def root(f):
    if f < RISE0: p = A
    elif f < RISE1: p = A + (B_ - A) * ease((f - RISE0) / (RISE1 - RISE0))
    elif f < OUT1: p = B_ + (C - B_) * ease((f - RISE1) / (OUT1 - RISE1))
    else: p = C + np.array([0, 3 * math.sin(2 * math.pi * (f - OUT1) / 70), 0])
    M = np.eye(4); M[:3, 3] = p
    if f < SHOW: M[:3, 3] += np.array([0, -900.0, 0])                     # hidden deep below until he comes up (scale stays constant: small track)
    return M
# ------------------------------------------------------------------ node worlds per frame -> local TRS (parent = still root)
NODE = {b: i + 1 for i, b in enumerate(BONES)}
PAR = {b: (J['parent'][b] if J['parent'].get(b) in NODE else None) for b in BONES}   # real hierarchy: bone offsets stay constant (small track)
T_ = [[None] * nf for _ in names]; R_ = [[None] * nf for _ in names]; S_ = [[None] * nf for _ in names]
for f in range(nf):
    Wf = J['frames'][str(min(f, len(J['frames']) - 1))]; RT = root(f)
    WW = {b: RT @ H(Wf[b]) @ SUPK for b in BONES}
    for i in range(len(names)):
        if i == 0 or i > len(BONES): T_[i][f], R_[i][f], S_[i][f] = np.zeros(3), np.eye(3), np.ones(3); continue
        b = BONES[i - 1]; Lm = (np.linalg.inv(WW[PAR[b]]) @ WW[b]) if PAR[b] else WW[b]
        sc = np.cbrt(np.linalg.det(Lm[:3, :3])); T_[i][f] = Lm[:3, 3]; R_[i][f] = orth(Lm[:3, :3] / sc); S_[i][f] = [sc, sc, sc]
anim_tpl = geom.read_bca(D(BM))[0]
bnodes = []
for i in range(len(names)):
    used = 1 <= i <= len(BONES)
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
GROUP = {'coat': 0, 'weed': 0, 'skin': 0, 'hat': 0, 'mask': 1, 'bone': 1, 'shell': 1, 'eye': 1, 'socket': 1}
COL = {n: c for n, c in zip(J['names'], J['palette'])}; COL['eye'] = [130, 255, 235]; COL['socket'] = [6, 8, 8]
TEXN = {0: 'lugia_s', 1: 'lugia_foot'}; TS = {0: 64, 1: 32}
labs = {g: [l for l in COL if GROUP[l] == g] for g in (0, 1)}
PALG = {g: [COL[l] for l in labs[g]] for g in (0, 1)}
IDX = {}; CELL = {}
for g in (0, 1):
    n_ = TS[g]; c4 = n_ // 4; ix = np.zeros((n_, n_), int)
    for k, l in enumerate(labs[g]):
        y, x = divmod(k, 4); ix[y * c4:(y + 1) * c4, x * c4:(x + 1) * c4] = k; CELL[l] = ((x + 0.5) / 4, 1 - (y + 0.5) / 4)
    IDX[g] = ix
# ------------------------------------------------------------------ strips
up = 1.0
def v10(q):
    q = [int(round(v / K * 64)) for v in q]; assert all(-512 <= x < 512 for x in q), q
    return (q[0] & 1023) | (q[1] & 1023) << 10 | (q[2] & 1023) << 20
def n10(q):
    a = [max(-512, min(511, int(round(v * 512)))) & 1023 for v in q]; return a[0] | a[1] << 10 | a[2] << 20
def tc(uv, g):
    n_ = TS[g]; a_ = int(round(uv[0] * n_ * 16)); b_ = int(round((1 - uv[1]) * n_ * 16)); return (b_ & 0xffff) << 16 | (a_ & 0xffff)
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
FP = [[P(q) for q in p['p']] for p in polys]
for pp in FP:
    n = np.cross(pp[1] - pp[0], pp[2] - pp[0])
    for q in pp: nacc[tuple(np.round(q, 2))] += n
def vnorm(q):
    n = nacc[tuple(np.round(q, 2))]; return n / (np.linalg.norm(n) + 1e-9)
LIGHTS = int(E('LIGHTS', 1))
work = {0: [], 1: []}
for g in (0, 1):
    tris = []
    for p, pp in zip(polys, FP):
        if GROUP[p['lab']] != g: continue
        tris.append([(pp[k], p['vb'][k], p['lab']) for k in range(3)])
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
    def grow(st):
        while len(st) < 40:
            cand = [t for t in edge.get(frozenset((st[-2], st[-1])), []) if not used[t]]
            if not cand: return st
            t = cand[0]; used[t] = True; st.append([v for v in T[t] if v not in (st[-2], st[-1])][0])
        return st
    for s0 in range(len(T)):
        if used[s0]: continue
        used[s0] = True; st = grow(list(T[s0])); st = grow(list(reversed(st)))
        cmds = [(0x40, [2])]; curb = None; lastt = None
        for vi in st:
            q, b, l = verts[vi]; loc = (HBi[b] @ np.append(q, 1))[:3]
            if b != curb: cmds.append((0x14, [NODE[b]])); curb = b
            t_ = tc(CELL[l], g)
            if t_ != lastt: cmds.append((0x22, [t_])); lastt = t_
            if LIGHTS: cmds.append((0x21, [n10(HBi[b][:3, :3] @ vnorm(q))]))
            cmds.append((0x24, [v10(loc)]))
        work[g].append(cmds + [(0x41, [])])
for g in (0, 1):
    sh = SHAPE_OF[TEXN[g]]; so, cl = shapes[sh]
    cmds = [(0x13, [KEEP]), (0x20, [0x7fff])]; n_ok = 0
    for w in work[g]:
        if len(pack_cmds(cmds + w + [(0x14, [KEEP])])) > cl: continue
        cmds += w; n_ok += 1
    blob = pack_cmds(cmds + [(0x14, [KEEP])]); d[so:so + cl] = blob + bytes(cl - len(blob))
    struct.pack_into('<I', d, shapehdr[sh] + 4, struct.unpack_from('<I', d, shapehdr[sh] + 4)[0] | 0x2 | 0x8)
    print('group', g, TEXN[g], 'strips', n_ok, 'of', len(work[g]), 'bytes', len(blob), '/', cl)
    assert n_ok == len(work[g]), 'strips do not fit'
# ------------------------------------------------------------------ materials (lit like Lugia, white diffuse), textures, palettes
def c555(c): rr, gg, bb = (int(round(v / 255 * 31)) for v in c); return rr | gg << 5 | bb << 10
for g in (0, 1):
    mt = MAT_OF[TEXN[g]]; mo_ = mats[mt]['off']; pa = struct.unpack_from('<I', d, mo_ + 12)[0]
    print('material', mats[mt]['name'], 'polygon attr %08x' % pa)
    struct.pack_into('<I', d, mo_ + 12, (pa & ~0xF & ~(31 << 16)) | 0xC0 | (31 << 16) | (pa & 0xF if LIGHTS else 0))
    if LIGHTS:
        struct.pack_into('<I', d, mo_ + 4, 31 | 31 << 5 | 31 << 10 | 0x8000 | (int(E('AMB', 20)) * 0x421) << 16)
for bo in r['blocks']:
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
F[MM] = lz10_enc(bytes(d)); F[BM] = lz10_enc(new_bca)
open(DST, 'wb').write(pack(F)); print('model', len(F[MM]), 'anim', len(F[BM]), 'file', len(pack(F)))
