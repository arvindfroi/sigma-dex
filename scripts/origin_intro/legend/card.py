"""Put a flat picture of our creature into the Ho-Oh cinematic models (a/2/4/3): hide Ho-Oh's shapes, reuse the shape and
texture of ho_head_top (128x128, 16 colours) for a quad bound to joint1 (Ho-Oh's root, which carries the flight path),
colour 0 transparent, both faces drawn. Local test tool.
python legend/card.py NARC_IN NARC_OUT SPRITE.png MEMBER[,MEMBER] [HALF=0.7] [PLANE=xy] [FLIPX=0] [FLIPY=0]"""
import sys, os, re, struct, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from narc import unpack, pack
from lz11 import lz11_dec
from lz import lz10_enc
from PIL import Image
import nitro
SRC, DST, SPR, MEMS = sys.argv[1], sys.argv[2], sys.argv[3], [int(x) for x in sys.argv[4].split(',')]
HALF = float(sys.argv[5]) if len(sys.argv) > 5 else 0.7; PLANE = sys.argv[6] if len(sys.argv) > 6 else 'xy'
FX = int(sys.argv[7]) if len(sys.argv) > 7 else 0; FY = int(sys.argv[8]) if len(sys.argv) > 8 else 0
HOOH = re.compile(r'^(hou_|ho_head_top|ho_tail)')
# the picture: fit into 128x128, 15 colours + clear
im = Image.open(SPR).convert('RGBA'); im = im.crop(im.getbbox()); s = 124 / max(im.size)
im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.NEAREST)
can = Image.new('RGBA', (128, 128)); can.alpha_composite(im, ((128 - im.width) // 2, (128 - im.height) // 2))
a = np.array(can); vis = a[..., 3] > 127
cols, inv = np.unique(a[vis][:, :3], axis=0, return_inverse=True)
if len(cols) > 15:
    q = can.convert('RGB').quantize(15, dither=0); pal = np.array(q.getpalette()[:45]).reshape(15, 3); idx = np.array(q) + 1
else:
    pal = cols; idx = np.zeros((128, 128), int); idx[vis] = inv.reshape(-1) + 1
idx[~vis] = 0
def bgr(c): r, g, b = (int(round(v / 255 * 31)) for v in c); return r | g << 5 | b << 10
F = unpack(open(SRC, 'rb').read())
for mi in MEMS:
    raw = F[mi]; d = bytearray(lz11_dec(raw) if raw[:1] == b'\x11' else raw)
    b = nitro.read_bmd(bytes(d)); m = b['models'][0]; mats = m['mats']; names = [x['name'] for x in mats]
    mo = m['off']; size, rc, mat, shp, invo = struct.unpack_from('<5I', d, mo)
    ents, _ = nitro.dict_read(bytes(d), mo + shp, 4); shapes = []
    for e, sn, _ in ents:
        o = mo + shp + nitro.u32(e, 0); dummy, ssz, flag, co, cl = struct.unpack_from('<HHIII', d, o); shapes.append((o + co, cl))
    root_slot = None; cur = None; hide = set(); card = None; card_mat = None
    for op, p in m['rcmds']:
        if op in (0x26, 0x66) and m['nodes'][p[0]][0] == 'joint1': root_slot = p[3]
        if op in (4, 0x24, 0x44): cur = p[0]
        elif op == 5 and cur is not None and HOOH.search(str(mats[cur].get('tex', ''))):
            if mats[cur].get('tex') == 'ho_head_top' and card is None: card = p[0]; card_mat = cur
            else: hide.add(p[0])
    for sh in hide:
        o, cl = shapes[sh]; d[o:o + cl] = bytes(cl)
    # quad display list on the card shape
    h = int(HALF * 4096)
    def v16(x, y, z): return [((y & 0xffff) << 16) | (x & 0xffff), z & 0xffff]
    corners = [(-1, 1, 0, 0), (1, 1, 128, 0), (1, -1, 128, 128), (-1, -1, 0, 128)]
    up = int(round(m['info']['up'] * 4096))                 # vertices are in posScale units: SCALE after the restore
    cmds = [(0x14, [root_slot]), (0x1b, [up, up, up]), (0x20, [0x7fff]), (0x40, [1])]
    for pl in PLANE.split(','):
        for cx, cy, s_, t_ in corners:
            if FX: s_ = 128 - s_
            if FY: t_ = 128 - t_
            X, Y = cx * h, cy * h
            xyz = {'xy': (X, Y, 0), 'xz': (X, 0, Y), 'yz': (0, Y, X), 'zy': (0, X, Y)}[pl]
            cmds += [(0x22, [((t_ * 16) & 0xffff) << 16 | ((s_ * 16) & 0xffff)]), (0x23, v16(*xyz))]
    cmds += [(0x41, [])]
    out = bytearray()
    for k in range(0, len(cmds), 4):
        grp = cmds[k:k + 4] + [(0, [])] * (4 - len(cmds[k:k + 4]))
        out += bytes(op for op, _ in grp)
        for _, ps in grp:
            for v in ps: out += struct.pack('<I', v & 0xffffffff)
    o, cl = shapes[card]; assert len(out) <= cl; d[o:o + cl] = bytes(out) + bytes(cl - len(out))
    # material: both faces
    mo_ = mats[card_mat]['off']; pa = struct.unpack_from('<I', d, mo_ + 12)[0]; struct.pack_into('<I', d, mo_ + 12, (pa & ~(31 << 16)) | 0xC0 | (31 << 16))
    # texture + palette (colour 0 clear)
    for bo in b['blocks']:
        if d[bo:bo + 4] != b'TEX0': continue
        t = nitro.read_tex(bytes(d), bo); f = t['raw_hdr']; tbo, pbo = f[6], f[17]
        ents2, _ = nitro.dict_read(bytes(d), bo + f[4], 8)
        for (e2, nm2, eo), x in zip(ents2, t['texs']):
            if x['name'] != 'ho_head_top': continue
            struct.pack_into('<I', d, eo, x['param'] | (1 << 29))
            off = (x['param'] & 0xffff) << 3; fl = idx.astype(np.uint8).reshape(-1)
            d[bo + tbo + off: bo + tbo + off + 8192] = bytes(fl[0::2] | (fl[1::2] << 4))
        for pl in t['pals']:
            if pl['name'].startswith('ho_head_top'):
                for i in range(16): struct.pack_into('<H', d, bo + pbo + pl['off'] + 2 * i, bgr(pal[i - 1]) if 1 <= i <= len(pal) else 0)
    new = lz10_enc(bytes(d)); print('member', mi, m['name'], 'root slot', root_slot, 'card shape', card, 'hid', len(hide), 'size', len(new), '/', len(raw))
    F[mi] = new
open(DST, 'wb').write(pack(F))
