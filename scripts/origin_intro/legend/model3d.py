"""Put a real 3D low-poly model (legend/sab3d/export_lowpoly.py JSON) into the Ho-Oh cinematic models (a/2/4/3): Ho-Oh's
shapes are emptied and refilled with our triangles (flat colour per triangle with baked light, VTX_10), bound to joint1
(the root that carries the flight path), drawn with Ho-Oh's materials whose textures are made plain white so the colour
is ours. Local test tool. python legend/model3d.py NARC_IN NARC_OUT MODEL.json MEMBER[,..] [SIZE=260] [YAW_FLIP=0]"""
import sys, os, re, json, struct, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from narc import unpack, pack
from lz11 import lz11_dec
from lz import lz10_enc
import nitro
SRC, DST, MJ, MEMS = sys.argv[1], sys.argv[2], sys.argv[3], [int(x) for x in sys.argv[4].split(',')]
SIZE = float(sys.argv[5]) if len(sys.argv) > 5 else 260.0; FLIP = int(sys.argv[6]) if len(sys.argv) > 6 else 0
HOOH = re.compile(r'^(hou_|ho_head_top|ho_tail)')
T = json.load(open(MJ))['tris']
MAXT = int(os.environ.get('MAXT', 0))
if MAXT and len(T) > MAXT:                              # drop the smallest triangles
    ar = [np.linalg.norm(np.cross(np.subtract(t['p'][1], t['p'][0]), np.subtract(t['p'][2], t['p'][0]))) for t in T]
    keep = sorted(np.argsort(ar)[::-1][:MAXT]); T = [T[i] for i in keep]
P = np.array([t['p'] for t in T], float); Cl = np.array([t['c'] for t in T], float)
# Blender (fwd -Y, up +Z, left +X) -> joint1 frame (fwd +X, up -Z, a proper rotation)
R = np.array([[0, -1, 0], [-1, 0, 0], [0, 0, -1]], float)
if FLIP: R = np.array([[0, 1, 0], [1, 0, 0], [0, 0, -1]], float)
ROLL = int(os.environ.get('ROLL', 0)); YAW = int(os.environ.get('YAW', 0))
for _ in range(ROLL): R = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float) @ R      # 90 deg about the flight axis
for _ in range(YAW): R = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], float) @ R       # 90 deg about Z
Q = P @ R.T; cen = (Q.reshape(-1, 3).max(0) + Q.reshape(-1, 3).min(0)) / 2; Q -= cen
Q *= SIZE / (Q.reshape(-1, 3).max(0) - Q.reshape(-1, 3).min(0)).max()
n = np.cross(Q[:, 1] - Q[:, 0], Q[:, 2] - Q[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
L = np.array([0.35, 0.25, -1.0]); L /= np.linalg.norm(L)
shade = 0.5 + 0.5 * np.abs(n @ L)
srgb = lambda c: np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(np.clip(c, 0, 1), 1 / 2.4) - 0.055)
rgb = np.clip(srgb(np.clip(Cl, 0, 1)) * shade[:, None], 0, 1)
def c555(c): r, g, b = (int(round(v * 31)) for v in c); return r | g << 5 | b << 10
def v10(p, up):
    q = [int(round(v / up * 64)) for v in p]
    assert all(-512 <= x < 512 for x in q), q
    return (q[0] & 1023) | (q[1] & 1023) << 10 | (q[2] & 1023) << 20
F = unpack(open(SRC, 'rb').read())
for mi in MEMS:
    raw = F[mi]; d = bytearray(lz11_dec(raw) if raw[:1] == b'\x11' else raw)
    b = nitro.read_bmd(bytes(d)); m = b['models'][0]; mats = m['mats']
    mo = m['off']; size, rc, mat, shp, invo = struct.unpack_from('<5I', d, mo); up = m['info']['up']
    ents, _ = nitro.dict_read(bytes(d), mo + shp, 4); shapes = []
    for e, sn, _ in ents:
        o = mo + shp + nitro.u32(e, 0); dummy, ssz, flag, co, cl = struct.unpack_from('<HHIII', d, o); shapes.append((o + co, cl))
    root = None; cur = None; use = []; usemats = set()
    for op, p in m['rcmds']:
        if op in (0x26, 0x66) and m['nodes'][p[0]][0] == 'joint1': root = p[3]
        if op in (4, 0x24, 0x44): cur = p[0]
        elif op == 5 and cur is not None and HOOH.search(str(mats[cur].get('tex', ''))) and p[0] not in use:
            use.append(p[0]); usemats.add(cur)
    for s in use: o, cl = shapes[s]; d[o:o + cl] = bytes(cl)
    # fill the emptied shapes in turn
    head = [(0x14, [root]), (0x1b, [int(up * 4096)] * 3), (0x40, [0])]
    def pack_cmds(cmds):
        out = bytearray()
        for k in range(0, len(cmds), 4):
            grp = cmds[k:k + 4] + [(0, [])] * (4 - len(cmds[k:k + 4]))
            out += bytes(op for op, _ in grp)
            for _, ps in grp:
                for v in ps: out += struct.pack('<I', v & 0xffffffff)
        return out
    ti = 0; si = 0; placed = 0
    for s in sorted(use, key=lambda s: -shapes[s][1]):
        o, cl = shapes[s]; cmds = list(head)
        while ti < len(T):
            nxt = cmds + [(0x20, [c555(rgb[ti])])] + [(0x24, [v10(Q[ti][k], up)]) for k in range(3)]
            if len(pack_cmds(nxt + [(0x41, [])])) > cl: break
            cmds = nxt; ti += 1
        if len(cmds) > 3:
            blob = pack_cmds(cmds + [(0x41, [])]); d[o:o + cl] = blob + bytes(cl - len(blob)); placed += 1
    # Ho-Oh's materials: both faces, opaque, no lights; their textures plain white
    for mt in usemats:
        o = mats[mt]['off']; pa = struct.unpack_from('<I', d, o + 12)[0]
        struct.pack_into('<I', d, o + 12, (pa & ~0xF & ~(31 << 16)) | 0xC0 | (31 << 16))
    texnames = {mats[mt].get('tex') for mt in usemats}; palnames = {mats[mt].get('pal') for mt in usemats}
    for bo in b['blocks']:
        if d[bo:bo + 4] != b'TEX0': continue
        t = nitro.read_tex(bytes(d), bo); f = t['raw_hdr']; tbo, pbo = f[6], f[17]
        ents2, _ = nitro.dict_read(bytes(d), bo + f[4], 8)
        for (e2, nm2, eo), x in zip(ents2, t['texs']):
            if x['name'] not in texnames or x['fmt'] not in (2, 3, 4): continue
            struct.pack_into('<I', d, eo, x['param'] & ~(1 << 29))
            off = (x['param'] & 0xffff) << 3; nbytes = x['w'] * x['h'] * {2: 2, 3: 4, 4: 8}[x['fmt']] // 8
            fill = {2: 0x55, 3: 0x11, 4: 0x01}[x['fmt']]; d[bo + tbo + off: bo + tbo + off + nbytes] = bytes([fill]) * nbytes
        for pl in t['pals']:
            if pl['name'] in palnames:
                for i in range(16): struct.pack_into('<H', d, bo + pbo + pl['off'] + 2 * i, 0x7FFF)
    new = lz10_enc(bytes(d)); print('member', mi, m['name'], 'triangles', ti, 'of', len(T), 'in', placed, 'shapes; size', len(new), '/', len(raw))
    F[mi] = new
open(DST, 'wb').write(pack(F))
