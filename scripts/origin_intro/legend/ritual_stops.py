"""The yellow speckled block over Lugia (and over Gravriel's overworld sprite) in the post-game Whirl Islands ritual.
Cause (found 2026-11-17): zone 230 (map 244's events) has five SPRITE_STOP (349) objects round Lugia's spot (objects 6-10
at x 15-17, z 16-17, flag 579 like Lugia). STOP objects are invisible blockers elsewhere, but this cutscene draws them,
with a texture that is not loaded (blanking the 'stop' graphic, a/0/8/1 243, did not help; hiding the five objects did).
They only exist with the bird (flag 579) during the scripted ritual, which goes straight into the battle, so nothing
needs them. They are moved to a corner out of the scene (default x 0, z 0); the file keeps its size (written in place).
python legend/ritual_stops.py A032_IN A032_OUT [X Z]"""
import sys, os, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from narc import unpack, pack
SRC, DST = sys.argv[1:3]; X = int(sys.argv[3]) if len(sys.argv) > 3 else 0; Z = int(sys.argv[4]) if len(sys.argv) > 4 else 0
F = unpack(open(SRC, 'rb').read()); d = bytearray(F[230]); o = 0
nb = struct.unpack_from('<I', d, o)[0]; o += 4 + nb * 20; no = struct.unpack_from('<I', d, o)[0]; o += 4; moved = 0
for i in range(no):
    f = struct.unpack_from('<HHHHHHHHHHHHHHII', d, o)
    if f[1] == 349 and f[4] == 579:
        struct.pack_into('<HH', d, o + 24, X, Z); moved += 1; print('obj', i, 'stop at', (f[12], f[13]), '->', (X, Z))
    o += 32
assert moved == 5, moved
F[230] = bytes(d); open(DST, 'wb').write(pack(F)); print('moved', moved, 'stop objects out of the ritual scene')
