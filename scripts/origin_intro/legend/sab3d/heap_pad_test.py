"""Heap side of the daytime freeze (2026-11-17): Origin's film with each model/animation member padded to the size of
the matching member in another film (decompressed size, and about its compressed size: random bytes then zeros, after
the data, so the game's buffers grow while the content stays Origin's). Optional TARGET raises the declared texture
size like vram_pad_test.py.
python heap_pad_test.py A243_ORIG A243_LIKE OUT_NARC [TARGET]"""
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
F = unpack(open(sys.argv[1], 'rb').read()); G = unpack(open(sys.argv[2], 'rb').read()); TARGET = int(sys.argv[4]) if len(sys.argv) > 4 else 0
rnd = os.urandom
for i in range(len(F)):
    a, b = dec(F[i]), dec(G[i]); extra = len(b) - len(a)
    if extra <= 0: continue
    r = max(0, min(extra, int((len(G[i]) - len(F[i])) / 1.125))); d = bytearray(a) + rnd(r) + bytes(extra - r)
    if TARGET and i in (15, 19, 23):
        sky = dec(F[{15: 0, 19: 5, 23: 10}[i]]); bs = [x for x in nitro.read_bmd(sky)['blocks'] if sky[x:x + 4] == b'TEX0'][0]
        bp = [x for x in nitro.read_bmd(bytes(a))['blocks'] if a[x:x + 4] == b'TEX0'][0]
        struct.pack_into('<H', d, bp + 12, (TARGET - (struct.unpack_from('<H', sky, bs + 12)[0] << 3)) // 8)
    F[i] = lz10_enc(bytes(d)); print(i, 'dec', len(a), '->', len(d), 'raw ->', len(F[i]), 'like', len(G[i]))
btaf = bytearray(b'BTAF' + b'\0' * 4 + struct.pack('<HH', len(F), 0)); gm = bytearray()
for f in F:
    s = len(gm); gm += f; btaf += struct.pack('<II', s, len(gm))
    while len(gm) % 4: gm += b'\xff'
struct.pack_into('<I', btaf, 4, len(btaf))
btnf = b'BTNF' + struct.pack('<I', 16) + struct.pack('<IHH', 4, 0, 1)
gmif = b'GMIF' + struct.pack('<I', len(gm) + 8) + gm
body = bytes(btaf) + btnf + gmif
open(sys.argv[3], 'wb').write(b'NARC' + struct.pack('<HHIHH', 0xFFFE, 0x0100, 16 + len(body), 16, 3) + body); print('ok', sys.argv[3], 16 + len(body))
