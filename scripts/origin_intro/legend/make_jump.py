"""Test ROM only (never shipped): patch a map so entering it runs a jump script that sets the story var, shows/hides the
right objects and warps to a cutscene map tile. Used to record Origin's own Ho-Oh/Lugia scenes.
python legend/make_jump.py SCR_NARC HDR_MEMBER SCR_MEMBER ZONE X Z [VAR=VAL ...] [+FLAG ...] [-FLAG ...]"""
import sys, struct; sys.path.insert(0, '.')
from narc import unpack, pack
NARC, HDR, SCR, ZONE, X, Z = sys.argv[1], *map(int, sys.argv[2:7])
code = b''
for a in sys.argv[7:]:
    if '=' in a: v, val = a.split('='); code += struct.pack('<HHH', 41, int(v, 0), int(val, 0))
    elif a[0] == '+': code += struct.pack('<HH', 30, int(a[1:], 0))
    elif a[0] == '-': code += struct.pack('<HH', 31, int(a[1:], 0))
code += (struct.pack('<HHHHHH', 176, ZONE, 0, X, Z, 0) if ZONE >= 0 else b'') + struct.pack('<H', 2)
F = unpack(open(NARC, 'rb').read())
n = 0
while struct.unpack_from('<H', F[SCR], 4 * n)[0] != 0xFD13: n += 1
head = b''.join(struct.pack('<i', (4 * n + 2) - (4 * i + 4)) for i in range(n)) + struct.pack('<H', 0xFD13)
F[SCR] = head + code
# header: frame table -> script 1 when temp var 0x4000 == 0
F[HDR] = bytes([1]) + struct.pack('<i', 1) + bytes([0]) + struct.pack('<HHHH', 0x4000, 0, 1, 0) + b'\0\0'
open(NARC, 'wb').write(pack(F)); print('scripts', n, 'code', code.hex())
