"""Write rendered title clips into a/2/6/4: clip c = members 14+50c .. 63+50c (8bpp 256x192 NCGR, tiled, not compressed).
Palette 13 is left as it is (the clips reuse their own entries).
python title/build_title.py IN OUT CLIP=CLIPDIR [CLIP=CLIPDIR ...]   e.g. 0=title/war/clip"""
import sys, os, struct, numpy as np
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, '..'))
from g2d import sections
from narc import unpack, pack
SRC, DST = sys.argv[1:3]
F = unpack(open(SRC, 'rb').read())
for arg in sys.argv[3:]:
    c, d = arg.split('=', 1); c = int(c); frames = np.load(os.path.join(d, 'idx.npy'))
    for t in range(50):
        m = 14 + 50 * c + t; b = bytearray(F[m]); _, _, s = sections(bytes(b)); o, sc = s[b'RAHC']
        off = o + 8 + struct.unpack_from('<I', sc, 28)[0]; sz = struct.unpack_from('<I', sc, 24)[0]
        raw = frames[t].reshape(24, 8, 32, 8).swapaxes(1, 2).reshape(-1).astype(np.uint8).tobytes()
        assert len(raw) == sz; b[off:off + sz] = raw; F[m] = bytes(b)
    print('clip', c, 'written from', d)
open(DST, 'wb').write(pack(F))
