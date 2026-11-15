"""Hide parts of a scene model in the legendary cinematic (a/2/4/3 Ho-Oh, a/2/4/4 Lugia; LZ11 members): every shape drawn
with a chosen material gets its display list replaced by NOPs (same size). Re-compressed with LZ10 (the loader reads the
header). Local test tool. python legend/hide_parts.py NARC_IN NARC_OUT MEMBER[,MEMBER...] REGEX_ON_TEXTURE_OR_MATERIAL"""
import sys, os, re, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from narc import unpack, pack
from lz11 import lz11_dec
from lz import lz10_enc
import nitro
SRC, DST, MEMS, RX = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(',')], re.compile(sys.argv[4])
F = unpack(open(SRC, 'rb').read())
for mi in MEMS:
    raw = F[mi]; d = bytearray(lz11_dec(raw) if raw[:1] == b'\x11' else raw)
    b = nitro.read_bmd(bytes(d)); m = b['models'][0]
    tex_of = {}
    for mt in m['mats']: tex_of[mt['name']] = mt.get('tex', '')
    names = [mt['name'] for mt in m['mats']]
    # shape offsets
    mo = m['off']; size, rc, mat, shp, inv = struct.unpack_from('<5I', d, mo)
    ents, _ = nitro.dict_read(bytes(d), mo + shp, 4)
    shapes = []
    for e, sn, _ in ents:
        o = mo + shp + nitro.u32(e, 0); dummy, ssz, flag, co, cl = struct.unpack_from('<HHIII', d, o); shapes.append((o + co, cl))
    cur = None; hidden = set()
    for op, p in m['rcmds']:
        if op in (4, 0x24, 0x44): cur = p[0]
        elif op == 5 and cur is not None and (RX.search(names[cur]) or RX.search(str(tex_of.get(names[cur], '')))): hidden.add(p[0])
    for s in hidden:
        o, cl = shapes[s]; d[o:o + cl] = bytes(cl)
    new = lz10_enc(bytes(d))
    print('member', mi, m['name'], 'hid', len(hidden), 'of', len(shapes), 'shapes; size', len(new), 'old', len(raw))
    F[mi] = new
open(DST, 'wb').write(pack(F))
