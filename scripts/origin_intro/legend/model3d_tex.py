"""Put a textured low-poly model (sab3d/export_textured.py JSON + shade_tex.py texture) into the Ho-Oh cinematic models
(a/2/4/3), the way the game's own Ho-Oh is built: unlit textured polygons whose shading lives in the texture.
Ho-Oh's shapes are emptied and refilled with triangle strips (TEXCOORD + VTX_10) bound to joint1; every refilled shape is
drawn with the ho_head_top material, whose 128x128 16-colour texture becomes ours. Local test tool.
python legend/model3d_tex.py NARC_IN NARC_OUT BASE MEMBER[,..] [SIZE=340]   (env ROLL, MAXT)"""
import sys, os, re, json, struct, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from narc import unpack, pack
from lz11 import lz11_dec
from lz import lz10_enc
import nitro
SRC, DST, BASE, MEMS = sys.argv[1], sys.argv[2], sys.argv[3], [int(x) for x in sys.argv[4].split(',')]
SIZE = float(sys.argv[5]) if len(sys.argv) > 5 else 340.0
HOOH = re.compile(r'^(hou_|ho_head_top|ho_tail)')
polys = json.load(open(BASE + '.json'))['polys']
tris = []
for p in polys:
    for k in range(1, len(p['p']) - 1): tris.append(([p['p'][0], p['p'][k], p['p'][k + 1]], [p['uv'][0], p['uv'][k], p['uv'][k + 1]]))
R = np.array([[0, -1, 0], [-1, 0, 0], [0, 0, -1]], float)
for _ in range(int(os.environ.get('ROLL', 1))): R = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float) @ R
P = np.array([t[0] for t in tris]) @ R.T; U = np.array([t[1] for t in tris])
cen = (P.reshape(-1, 3).max(0) + P.reshape(-1, 3).min(0)) / 2; P -= cen; P *= SIZE / (P.reshape(-1, 3).max(0) - P.reshape(-1, 3).min(0)).max()
idx = np.load(BASE + '_tex_idx.npy'); pal = np.load(BASE + '_tex_pal.npy'); TS = idx.shape[0]
# vertices shared by position + uv; greedy strips
keyof = {}; verts = []
def vid(p, uv):
    k = (round(p[0], 1), round(p[1], 1), round(p[2], 1), round(uv[0], 4), round(uv[1], 4))
    if k not in keyof: keyof[k] = len(verts); verts.append((p, uv))
    return keyof[k]
T = [tuple(vid(P[i][j], U[i][j]) for j in range(3)) for i in range(len(tris))]
edge = {}
for ti, t in enumerate(T):
    for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])): edge.setdefault(frozenset((a, b)), []).append(ti)
used = [False] * len(T); strips = []
def third(t, a, b): return [v for v in t if v not in (a, b)][0]
def grow(strip):                                          # both faces are drawn, so winding does not matter
    while True:
        e = frozenset((strip[-2], strip[-1])); cand = [t for t in edge.get(e, []) if not used[t]]
        if not cand: return strip
        t = cand[0]; used[t] = True; strip.append(third(T[t], strip[-2], strip[-1]))
for s0 in range(len(T)):
    if used[s0]: continue
    used[s0] = True; best = None
    for rot in range(3):                                  # try the three starting edges, keep the longest
        a, b, c = T[s0][rot:] + T[s0][:rot]
        saved = used[:]; st = grow([a, b, c]); 
        if best is None or len(st) > len(best[0]): best = (st, used[:])
        used[:] = saved
    strip, used = best
    rev = grow(list(reversed(strip)))                     # and extend backwards too
    strips.append(rev)
def c555(c): r, g, b = (int(round(v / 255 * 31)) for v in c); return r | g << 5 | b << 10
def v10(p, up):
    q = [int(round(v / up * 64)) for v in p]; assert all(-512 <= x < 512 for x in q), q
    return (q[0] & 1023) | (q[1] & 1023) << 10 | (q[2] & 1023) << 20
def tc(uv):
    s = min(2047, max(-2048, int(round(uv[0] * TS * 16)))); t = min(2047, max(-2048, int(round((1 - uv[1]) * TS * 16))))
    return (t & 0xffff) << 16 | (s & 0xffff)
def pack_cmds(cmds):
    out = bytearray()
    for k in range(0, len(cmds), 4):
        grp = cmds[k:k + 4] + [(0, [])] * (4 - len(cmds[k:k + 4]))
        out += bytes(op for op, _ in grp)
        for _, ps in grp:
            for v in ps: out += struct.pack('<I', v & 0xffffffff)
    return out
print('triangles', len(T), 'strips', len(strips), 'vertices in strips', sum(len(s) for s in strips))
F = unpack(open(SRC, 'rb').read())
for mi in MEMS:
    raw = F[mi]; d = bytearray(lz11_dec(raw) if raw[:1] == b'\x11' else raw)
    b = nitro.read_bmd(bytes(d)); m = b['models'][0]; mats = m['mats']; up = m['info']['up']
    mo = m['off']; size, rc, mat, shp, invo = struct.unpack_from('<5I', d, mo)
    ents, _ = nitro.dict_read(bytes(d), mo + shp, 4); shapes = []
    for e, sn, _ in ents:
        o = mo + shp + nitro.u32(e, 0); dummy, ssz, flag, co, cl = struct.unpack_from('<HHIII', d, o); shapes.append((o + co, cl))
    headmat = [i for i, x in enumerate(mats) if x.get('tex') == 'ho_head_top'][0]
    root = None; cur = None; curpos = None; use = []; matpos = {}
    # walk the raw render commands to know the byte position of each MAT op
    o = mo + rc
    while True:
        op = d[o]; n = 2 + 3 * d[o + 2] if op == 9 else nitro.RCMD_LEN[op]; p = list(d[o + 1:o + 1 + n])
        if op in (0x26, 0x66) and m['nodes'][p[0]][0] == 'joint1': root = p[3]
        if op in (4, 0x24, 0x44): cur = p[0]; curpos = o + 1
        elif op == 5 and cur is not None and HOOH.search(str(mats[cur].get('tex', ''))) and p[0] not in use:
            use.append(p[0]); d[curpos] = headmat               # draw it with the textured head material
        o += 1 + n
        if op == 1: break
    for s in use: so, cl = shapes[s]; d[so:so + cl] = bytes(cl)
    head = [(0x14, [root]), (0x1b, [int(up * 4096)] * 3), (0x20, [0x7fff])]
    si = 0; placed = 0; ntri = 0
    for s in sorted(use, key=lambda s: -shapes[s][1]):
        so, cl = shapes[s]; cmds = list(head)
        while si < len(strips):
            st = strips[si]; add = [(0x40, [2])]
            for v in st: add += [(0x22, [tc(verts[v][1])]), (0x24, [v10(verts[v][0], up)])]
            add += [(0x41, [])]
            if len(pack_cmds(cmds + add)) > cl: break
            cmds += add; si += 1; ntri += len(st) - 2
        if len(cmds) > 3:
            blob = pack_cmds(cmds); d[so:so + cl] = blob + bytes(cl - len(blob)); placed += 1
    mo_ = mats[headmat]['off']; pa = struct.unpack_from('<I', d, mo_ + 12)[0]
    struct.pack_into('<I', d, mo_ + 12, (pa & ~0xF & ~(31 << 16)) | 0xC0 | (31 << 16))
    for bo in b['blocks']:
        if d[bo:bo + 4] != b'TEX0': continue
        t = nitro.read_tex(bytes(d), bo); f = t['raw_hdr']; tbo, pbo = f[6], f[17]
        ents2, _ = nitro.dict_read(bytes(d), bo + f[4], 8)
        for (e2, nm2, eo), x in zip(ents2, t['texs']):
            if x['name'] != 'ho_head_top': continue
            struct.pack_into('<I', d, eo, x['param'] & ~(1 << 29))
            off = (x['param'] & 0xffff) << 3; fl = idx.astype(np.uint8).reshape(-1)
            d[bo + tbo + off: bo + tbo + off + TS * TS // 2] = bytes(fl[0::2] | (fl[1::2] << 4))
        for pl in t['pals']:
            if pl['name'].startswith('ho_head_top'):
                for i in range(16): struct.pack_into('<H', d, bo + pbo + pl['off'] + 2 * i, c555(pal[i - 1]) if 1 <= i <= len(pal) else 0)
    new = lz10_enc(bytes(d))
    print('member', mi, m['name'], 'triangles', ntri, 'strips', si, '/', len(strips), 'shapes', placed, 'size', len(new), '/', len(raw))
    F[mi] = new
open(DST, 'wb').write(pack(F))
