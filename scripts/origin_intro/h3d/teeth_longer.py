"""Make the sabre teeth as long as in the drawing (they reach well below the chin there).
python h3d/teeth_longer.py GRAFT.npz PARTS.npy OUT.npz [extra]
Tooth vertices (part 6) slide down along their own length: the root stays, the tip moves by `extra` (default 0.11)
straight down and a little forward, so the tips stay in front of the chest. Vertex order is kept, so the labels fit."""
import sys, numpy as np
gp, pp, out = sys.argv[1:4]; extra = float(sys.argv[4]) if len(sys.argv) > 4 else 0.11
d = dict(np.load(gp)); part = np.load(pp); V = d['V'].astype(float)
t_ = part == 6
z = V[:, 2]; top = z[t_].max(); bot = z[t_].min()
t = np.clip((top - z) / (top - bot), 0, 1)                 # 0 at the root, 1 at the tip
V[t_] += (t[t_] ** 1.3)[:, None] * np.array([-0.012, 0.0, -extra])
d['V'] = V.astype(np.float32); np.savez_compressed(out, **d)
F = d['F']; N = d['N']
with open(out.replace('.npz', '.ply'), 'wb') as f:
    f.write(('ply\nformat binary_little_endian 1.0\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\n'
             'property float nx\nproperty float ny\nproperty float nz\nelement face %d\nproperty list uchar int vertex_indices\n'
             'end_header\n' % (len(V), len(F))).encode())
    f.write(np.concatenate([V, N], 1).astype('<f4').tobytes())
    fa = np.zeros(len(F), dtype=[('n', 'u1'), ('a', '<i4'), ('b', '<i4'), ('c', '<i4')])
    fa['n'] = 3; fa['a'], fa['b'], fa['c'] = F[:, 0], F[:, 1], F[:, 2]
    f.write(fa.tobytes())
print('teeth verts', int(t_.sum()), 'root z %.3f tip z %.3f -> %.3f' % (top, bot, bot - extra))
