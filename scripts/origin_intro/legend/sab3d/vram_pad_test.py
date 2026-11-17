"""Find the Ho-Oh film's texture VRAM budget at a given time of day (2026-11-17: v31f/v32c freeze in the morning and at
noon, work at night; Origin's 215568 bytes work at all times). Origin's own film with the pagoda members' declared TEX0
texture size (tblen) raised so the sky+pagoda pair totals TARGET bytes; nothing else changes (the extra VRAM is only
allocated and filled with whatever follows the texture data).
python vram_pad_test.py A243_ORIG TARGET OUT_NARC"""
import sys, os, struct
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, '..', '..')); sys.path.insert(0, os.path.join(H, '..'))
from narc import unpack
from lz11 import lz11_dec
from lz import lz10_enc
import nitro
def lz10_dec(src):
    n = int.from_bytes(src[1:4], 'little'); out = bytearray(); i = 4
    while len(out) < n:
        fl = src[i]; i += 1
        for b in range(8):
            if len(out) >= n: break
            if fl & (0x80 >> b):
                v = src[i] << 8 | src[i + 1]; i += 2; ln = (v >> 12) + 3; ds = (v & 0xfff) + 1
                for _ in range(ln): out.append(out[-ds])
            else: out.append(src[i]); i += 1
    return bytes(out)
dec = lambda raw: lz11_dec(raw) if raw[:1] == b'\x11' else lz10_dec(raw) if raw[:1] == b'\x10' else raw
F = unpack(open(sys.argv[1], 'rb').read()); TARGET = int(sys.argv[2])
def tex0(d): r = nitro.read_bmd(d); return [b for b in r['blocks'] if d[b:b + 4] == b'TEX0'][0]
for sky, pag in ((0, 15), (5, 19), (10, 23)):
    ds = dec(F[sky]); dp = bytearray(dec(F[pag])); bs, bp = tex0(ds), tex0(dp)
    ts = struct.unpack_from('<H', ds, bs + 12)[0] << 3; tp = struct.unpack_from('<H', dp, bp + 12)[0] << 3
    need = (TARGET - ts) // 8; assert need * 8 >= tp, (TARGET, ts, tp)
    struct.pack_into('<H', dp, bp + 12, need); F[pag] = lz10_enc(bytes(dp))
    print('pair %d+%d: %d + %d -> %d + %d = %d' % (sky, pag, ts, tp, ts, need * 8, ts + need * 8))
btaf = bytearray(b'BTAF' + b'\0' * 4 + struct.pack('<HH', len(F), 0)); gm = bytearray()
for f in F:
    s = len(gm); gm += f; btaf += struct.pack('<II', s, len(gm))
    while len(gm) % 4: gm += b'\xff'
struct.pack_into('<I', btaf, 4, len(btaf))
btnf = b'BTNF' + struct.pack('<I', 16) + struct.pack('<IHH', 4, 0, 1)
gmif = b'GMIF' + struct.pack('<I', len(gm) + 8) + gm
body = bytes(btaf) + btnf + gmif
open(sys.argv[3], 'wb').write(b'NARC' + struct.pack('<HHIHH', 0xFFFE, 0x0100, 16 + len(body), 16, 3) + body); print('ok', sys.argv[3])
