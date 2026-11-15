"""Repack a NARC where some members share another member's bytes (FATB entries pointing at the same data).
python legend/pack_shared.py IN_NARC OUT_NARC ALIAS=SRC [ALIAS=SRC ...]"""
import sys, os, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from narc import unpack
F = unpack(open(sys.argv[1], 'rb').read()); alias = {int(a): int(b) for a, b in (x.split('=') for x in sys.argv[3:])}
btaf = bytearray(b'BTAF' + b'\0' * 4 + struct.pack('<HH', len(F), 0)); gm = bytearray(); where = {}
for i, f in enumerate(F):
    if i in alias: continue
    where[i] = (len(gm), len(gm) + len(f)); gm += f
    while len(gm) % 4: gm += b'\xff'
for i in range(len(F)):
    s, e = where[alias[i]] if i in alias else where[i]; btaf += struct.pack('<II', s, e)
struct.pack_into('<I', btaf, 4, len(btaf))
btnf = b'BTNF' + struct.pack('<I', 16) + struct.pack('<IHH', 4, 0, 1)
gmif = b'GMIF' + struct.pack('<I', len(gm) + 8) + gm
body = bytes(btaf) + btnf + gmif
out = b'NARC' + struct.pack('<HHIHH', 0xFFFE, 0x0100, 16 + len(body), 16, 3) + body
open(sys.argv[2], 'wb').write(out); print('size', len(out))
