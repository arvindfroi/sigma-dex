"""Seed 3 has the better body, sails and hull; seed 1 has the better head (a real snout with a nose, eyes, mouth and
teeth that show under the hat). Both are Hunyuan meshes of the same drawing, aligned by align_head.py.
python h3d/graft.py BODY.npz HEAD_ALIGNED.npz OUT.npz
The head (an ellipsoid around it, plus its hat) comes from seed 1; seed 3 loses a slightly smaller ellipsoid and its own
hat, so the two surfaces overlap a little at the seam (under the chin and behind the head) instead of leaving a gap.
Writes OUT.npz (V, N, F, thick, src: 0 body seed, 1 head seed) and OUT.ply."""
import sys, os, numpy as np
bp, hp, out = sys.argv[1:4]
Y0 = float(os.environ.get('Y0', -0.015))
C = np.array([float(v) for v in os.environ.get('HEAD_C', '-0.78,-0.17').split(',')])
R = np.array([float(v) for v in os.environ.get('HEAD_R', '0.30,0.42,0.30').split(',')])
SHRINK = float(os.environ.get('SHRINK', 0.025))
b = np.load(bp); h = np.load(hp)
def region(V, r, hatz):
    x, y, z = V[:, 0], V[:, 1] - Y0, V[:, 2]; ay = np.abs(y)
    e = ((x - C[0]) / r[0]) ** 2 + (y / r[1]) ** 2 + ((z - C[1]) / r[2]) ** 2 < 1
    hat = (x < -0.3) & ((z > hatz) | ((z > -0.12) & (ay > 0.33)))
    return e | hat, x, z, ay
keep1, *_ = region(h['V'], R, 0.0)
rm3, x3, z3, ay3 = region(b['V'], R - SHRINK, -0.01)
rm3 |= (x3 < -0.78) & (z3 > -0.48) & (z3 < -0.18) & (ay3 > 0.04) & (ay3 < 0.32)      # seed 3's own teeth
keep3 = ~rm3
def sub(d, keep):
    F = d['F']; fk = keep[F].all(1)
    idx = -np.ones(len(keep), int); idx[keep] = np.arange(keep.sum())
    T = d['thick'] if 'thick' in d else np.full(len(keep), 9.0, np.float32)
    return d['V'][keep], d['N'][keep], idx[F[fk]], T[keep]
V3, N3, F3, T3 = sub(b, keep3); V1, N1, F1, T1 = sub(h, keep1)
V = np.concatenate([V3, V1]); N = np.concatenate([N3, N1]); F = np.concatenate([F3, F1 + len(V3)])
T = np.concatenate([T3, T1]); src = np.concatenate([np.zeros(len(V3), np.uint8), np.ones(len(V1), np.uint8)])
used = np.zeros(len(V), bool); used[F.ravel()] = True                  # drop vertices no face uses
idx = -np.ones(len(V), int); idx[used] = np.arange(used.sum())
V, N, T, src = V[used], N[used], T[used], src[used]; F = idx[F]
np.savez_compressed(out, V=V.astype(np.float32), N=N.astype(np.float32), F=F.astype(np.int32), thick=T.astype(np.float32),
                    vis=np.zeros(len(V), bool), src=src)
with open(out.replace('.npz', '.ply'), 'wb') as f:
    f.write(('ply\nformat binary_little_endian 1.0\nelement vertex %d\nproperty float x\nproperty float y\nproperty float z\n'
             'property float nx\nproperty float ny\nproperty float nz\nelement face %d\nproperty list uchar int vertex_indices\n'
             'end_header\n' % (len(V), len(F))).encode())
    f.write(np.concatenate([V, N], 1).astype('<f4').tobytes())
    fa = np.zeros(len(F), dtype=[('n', 'u1'), ('a', '<i4'), ('b', '<i4'), ('c', '<i4')])
    fa['n'] = 3; fa['a'], fa['b'], fa['c'] = F[:, 0], F[:, 1], F[:, 2]
    f.write(fa.tobytes())
print('body verts', len(V3), 'head verts', len(V1), 'total', len(V), 'faces', len(F))
