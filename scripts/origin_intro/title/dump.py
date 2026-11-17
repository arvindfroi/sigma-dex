"""Title screen bottom art (a/2/6/4, Origin rc8): dump the 150 frames (members 14-163, 8bpp 256x192, tiled) with palette 13.
python title/dump.py -> title/frames/fNNN.png (palette images) + title/idx.npy (150x192x256 indices) + title/pal13.npy"""
import sys, os, struct, numpy as np
from PIL import Image
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, '..'))
from g2d import lz10_dec, sections
from narc import unpack
F = unpack(open(os.path.expanduser('~/sigma-origin/rc8/x_rc8/files/a/2/6/4'), 'rb').read())
dec = lambda i: lz10_dec(F[i]) if F[i][:1] == b'\x10' else F[i]
p = dec(13); _, _, s = sections(p); o, sc = s[b'TTLP']; pb = o + 8 + struct.unpack_from('<I', sc, 20)[0]
c = np.array(struct.unpack_from('<256H', p, pb))
pal = np.stack([(c & 31) * 255 // 31, ((c >> 5) & 31) * 255 // 31, ((c >> 10) & 31) * 255 // 31], 1).astype(np.uint8)
np.save(os.path.join(H, 'pal13.npy'), pal)
os.makedirs(os.path.join(H, 'frames'), exist_ok=True)
allidx = []
for k, m in enumerate(range(14, 164)):
    d = dec(m); _, _, s = sections(d); o, sc = s[b'RAHC']
    th, tw, bpp, _, mapping = struct.unpack_from('<HHIII', sc, 8); sz = struct.unpack_from('<I', sc, 24)[0]
    raw = np.frombuffer(d[o + 8 + struct.unpack_from('<I', sc, 28)[0]:][:sz], np.uint8)
    if k == 0: print('tiles', th, tw, 'bpp field', bpp, 'mapping', mapping, 'flag', struct.unpack_from('<I', sc, 20)[0])
    idx = raw.reshape(24, 32, 8, 8).swapaxes(1, 2).reshape(192, 256)
    allidx.append(idx)
    im = Image.fromarray(idx, 'P'); im.putpalette(pal.ravel().tolist()); im.save(os.path.join(H, 'frames', f'f{k:03d}.png'))
np.save(os.path.join(H, 'idx.npy'), np.array(allidx))
print('done', len(allidx))
