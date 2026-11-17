"""Test ROM (local only, never shipped) for the custom sprites: our NARCs written in place into the ROM (so the lw/g7.dst
savestate still works), and walking down the bedroom stairs warps to ZONE X Z (the 1F frame script, as build_jump.py,
without touching the destination map).
python legend/custom_jump.py ROM_IN ROM_OUT ZONE X Z [ORIG_NARC=NEW_NARC ...] [+FLAG|-FLAG ...]
env A081=customs.bin puts our map figures into every overworld NARC copy (a/0/8/1, data/clothesN/a081.narc).
The savestate's stairs: from the bedroom start walk U*6, R, U, then R onto the stairs (they are at (9,3), entered moving right)."""
import sys, os, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from narc import unpack, pack
ROM_IN, ROM_OUT, ZONE, X, Z = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:6])
Y = os.path.expanduser('~/sigma-origin/legend_test/y'); orig = f'{Y}/a012_orig'
F = unpack(open(orig, 'rb').read())
code = struct.pack('<HHH', 41, 0x4000, 1)
for a in sys.argv[6:]:                                          # +FLAG sets, -FLAG clears (a figure's hide flag), before the warp
    if a[0] in '+-' and a[1:].isdigit(): code += struct.pack('<HH', 30 if a[0] == '+' else 31, int(a[1:]))
code += struct.pack('<HHHHHH', 176, ZONE, 0, X, Z, 0) + struct.pack('<H', 2)
F[842] = struct.pack('<i', 2) + struct.pack('<H', 0xFD13) + code
F[617] = bytes([1]) + struct.pack('<i', 1) + bytes([0]) + struct.pack('<HHHH', 0x4000, 0, 1, 0)
new = pack(F); old = open(orig, 'rb').read(); assert len(new) <= len(old), (len(new), len(old))
rom = bytearray(open(ROM_IN, 'rb').read())
def inplace(old, new):
    i = rom.find(old); assert i >= 0 and rom.find(old, i + 1) < 0, 'not found once'
    assert len(new) <= len(old), (len(new), len(old)); rom[i:i + len(old)] = new + bytes(len(old) - len(new)); return i
print('scripts at', hex(inplace(old, new)))
for a in [a for a in sys.argv[6:] if '=' in a]:
    o, n = a.split('='); print(os.path.basename(n), 'at', hex(inplace(open(o, 'rb').read(), open(n, 'rb').read())))
# A081=customs.bin: our map figure members into EVERY copy of the overworld NARC (a/0/8/1 and Origin's per-outfit
# data/clothesN/a081.narc: the game loads the copy that matches the player's clothes), member by member, in place
def fnt_files(rom):
    fnt_off, fnt_size, fat_off, fat_size = struct.unpack_from('<IIII', rom, 0x40)
    fat = [struct.unpack_from('<II', rom, fat_off + 8 * i) for i in range(fat_size // 8)]; out = {}
    def walk(did, path):
        sub_off, first, _ = struct.unpack_from('<IHH', rom, fnt_off + 8 * (did & 0xFFF)); p = fnt_off + sub_off; f = first
        while True:
            l = rom[p]; p += 1
            if l == 0: return
            nm = bytes(rom[p:p + (l & 0x7F)]).decode('latin1'); p += l & 0x7F
            if l & 0x80: sd = struct.unpack_from('<H', rom, p)[0]; p += 2; walk(sd, path + nm + '/')
            else: out[path + nm] = fat[f]; f += 1
    walk(0xF000, ''); return out
if os.environ.get('A081'):
    C = unpack(open(os.environ['A081'], 'rb').read()); ref = unpack(open(os.path.expanduser('~/sigma-origin/legend_test/x/files/a/0/8/1'), 'rb').read())
    MEM = [int(m) for m in os.environ.get('A081_MEMBERS', '183,186,194,210,211,228').split(',')]
    for path, (s0, e0) in fnt_files(rom).items():
        if path == 'a/0/8/1' or (path.startswith('data/clothes') and path.endswith('/a081.narc')):
            A = unpack(bytes(rom[s0:e0])); seg = bytearray(rom[s0:e0])
            for m in MEM:
                assert A[m] == ref[m], (path, m); i = seg.find(A[m]); assert i >= 0 and seg.find(A[m], i + 1) < 0
                seg[i:i + len(A[m])] = C[m]
            rom[s0:e0] = seg; print('a081 figures into', path)
open(ROM_OUT, 'wb').write(rom); print('ok', ROM_OUT)
