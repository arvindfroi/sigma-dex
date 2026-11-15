"""Take one shot of the Ho-Oh film (a/2/4/3: model member + its BCA) apart for Blender: per-frame world matrices of every
node (Ho-Oh's joint1 = the path), the environment (everything not Ho-Oh) as OBJ + textures at frame 0, and Ho-Oh itself
at frame 0 for scale. python legend/scene_io.py NARC MODEL_MEMBER BCA_MEMBER OUTDIR"""
import sys, os, json, re, numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from narc import unpack
from lz11 import lz11_dec
import nitro, geom
NARC, MM, BM, OUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]; os.makedirs(OUT, exist_ok=True)
F = unpack(open(NARC, 'rb').read()); D = lambda i: lz11_dec(F[i]) if F[i][:1] == b'\x11' else F[i]
d = D(MM); r = nitro.read_bmd(d); m = r['models'][0]; anim = geom.read_bca(D(BM))[0]
names = [n for n, _ in m['nodes']]; nf = anim['nframes']
HOOH = re.compile(r'^(hou_|ho_head_top|ho_tail)')
def node_worlds(f):
    trs = geom.node_trs(m, anim, f); ssc = m['info']['scaling'] == 1
    def local(i, parent):
        t, rr, s = trs[i]; T = np.eye(4); T[:3, 3] = t; R = np.eye(4); R[:3, :3] = rr; S = np.diag(list(s) + [1])
        if ssc and parent != i: ps = trs[parent][2]; return T @ np.diag([1 / x for x in ps] + [1]) @ R @ S
        return T @ R @ S
    stack = [np.eye(4)] * 32; cur = np.eye(4); W = {}
    for op, p in m['rcmds']:
        if op in (6, 0x26, 0x46, 0x66):
            if op == 0x46: cur = stack[p[3]]
            if op == 0x66: cur = stack[p[4]]
            cur = cur @ local(p[0], p[1]); W[names[p[0]]] = cur.copy()
            if op in (0x26, 0x66): stack = list(stack); stack[p[3]] = cur
        elif op == 3: cur = stack[p[0]]
    return W
frames = [{k: v.tolist() for k, v in node_worlds(f).items()} for f in range(nf)]
json.dump(dict(nframes=nf, up=m['info']['up'], nodes=names, frames=frames), open(f'{OUT}/nodes.json', 'w'))
# environment and Ho-Oh at frame 0 as OBJ (geom.export_frame_obj writes every draw; split by material afterwards)
tmp = f'{OUT}/_model.nsbmd'; open(tmp, 'wb').write(d)
geom.export_frame_obj(tmp, OUT, anim, 0, 'frame0')
p0 = np.array([frames[f]['joint1'] for f in range(nf)])[:, :3, 3]
print('frames', nf, 'joint1 path from', p0[0].round(1), 'to', p0[-1].round(1), 'min', p0.min(0).round(0), 'max', p0.max(0).round(0))
