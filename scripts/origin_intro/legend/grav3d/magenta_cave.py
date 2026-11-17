"""Hole test (Arvind 2026-11-16: "test it by giving the model a magenta background"): every palette colour of the cave
model in Lugia's film (member 0) becomes magenta, so anything you can see through Gravriel shows magenta.
python magenta_cave.py A244_IN A244_OUT"""
import sys, os, struct
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', '..')); sys.path.insert(0, os.path.join(HERE, '..'))
from narc import unpack, pack
from lz11 import lz11_dec
from lz import lz10_enc
import nitro
def lz10_dec(d):
    n = d[1] | d[2] << 8 | d[3] << 16; p = 4; out = bytearray()
    while len(out) < n:
        fl = d[p]; p += 1
        for b in range(8):
            if len(out) >= n: break
            if not fl & (0x80 >> b): out.append(d[p]); p += 1; continue
            l = (d[p] >> 4) + 3; disp = ((d[p] & 0xF) << 8 | d[p + 1]) + 1; p += 2
            for _ in range(l): out.append(out[-disp])
    return bytes(out)
F = unpack(open(sys.argv[1], 'rb').read()); raw = F[0]
d = bytearray(lz11_dec(raw) if raw[:1] == b'\x11' else lz10_dec(raw) if raw[:1] == b'\x10' else raw)
bo = [b for b in nitro.read_bmd(bytes(d))['blocks'] if d[b:b + 4] == b'TEX0'][0]; f = nitro.read_tex(bytes(d), bo)['raw_hdr']
pbo, plen = f[17], f[14] << 3
for i in range(0, plen, 2): struct.pack_into('<H', d, bo + pbo + i, 0x7C1F)
F[0] = lz10_enc(bytes(d)) if raw[:1] in (b'\x10', b'\x11') else bytes(d); open(sys.argv[2], 'wb').write(pack(F)); print('cave palettes magenta', plen // 2, 'colours')
