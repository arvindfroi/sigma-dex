"""Print a zone's events (a/0/3/2 member): objects, warps, coord triggers.  python legend/zev.py NARC ZONE..."""
import sys, struct; sys.path.insert(0, '.')
from narc import unpack
F = unpack(open(sys.argv[1], 'rb').read())
for z in map(int, sys.argv[2:]):
    d = F[z]; o = 0
    nb = struct.unpack_from('<I', d, o)[0]; o += 4 + nb * 20
    no = struct.unpack_from('<I', d, o)[0]; o += 4
    print(f'zone {z}: bg {nb}, objects {no}')
    for i in range(no):
        f = struct.unpack_from('<HHHHHHHHHHHHHHII', d, o); o += 32
        print(f'  obj {f[0]} sprite {f[1]} move {f[2]} type {f[3]} flag {f[4]} script {f[5]} x {f[12]} z {f[13]}')
    nw = struct.unpack_from('<I', d, o)[0]; o += 4
    for i in range(nw):
        f = struct.unpack_from('<HHHHI', d, o); o += 12; print(f'  warp x {f[0]} z {f[1]} to zone {f[2]} anchor {f[3]}')
    nc = struct.unpack_from('<I', d, o)[0]; o += 4
    for i in range(nc):
        f = struct.unpack_from('<HHHHHHHH', d, o); o += 16; print(f'  coord script {f[0]} x {f[1]} z {f[2]} w {f[3]} h {f[4]} val {f[6]} var {f[7]:#x}')
