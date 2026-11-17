"""v9 Sabertann (Arvind's v8 notes: snout like a dog's, black paws with claws, a deck instead of a red barrel, the stern
skull like Den sorte dame's, a steady hand on the paint, the pounce, Ho-Oh's pixel style and eyes).
Blender -b --factory-startup -P h3d/build_v9.py -- MESH.ply CLEAN_PREFIX EXTRA.json OUT.blend   (env SAB_TEX = emblem dir)
MESH from v9_mesh.py (longer muzzle, deck painted), CLEAN_PREFIX from clean_labels.py (per-face colours and parts).
Paint: every vertex carries smoothed colour weights; the material picks the strongest per pixel, so colour borders are
smooth curves instead of the mesh's ragged triangle edges. Deck planks and the hat emblem are drawn per pixel too.
Model frame: creature faces -Y, up +Z, feet at z = 0, water at WATER. Frames 1-4 trot, 5-7 the pounce."""
import bpy, bmesh, math, os, sys, json
import numpy as np
from mathutils import Vector, Matrix, Quaternion
argv = sys.argv[sys.argv.index('--') + 1:]
MESH, CPRE, EXTRA, OUT = argv[:4]
K = 3.3; ZMIN = -0.863; Y0 = -0.015; YC = -0.045
WATER = float(os.environ.get('SAB_WATER7', 0.16))
NFR = 7; LEAP0 = 5
def M(h):                                            # Hunyuan frame -> model frame
    x, y, z = h
    return Vector((-K * (y - Y0), K * x, K * (z - ZMIN)))
def MN(n):                                           # a direction, Hunyuan -> model
    return Vector((-n[1], n[0], n[2]))
ex = json.load(open(EXTRA))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; col = sc.collection
bpy.ops.wm.ply_import(filepath=MESH)
src = sc.objects[0]; src.name = 'Src'
me = src.data
fl = np.load(CPRE + '_flab.npy'); fpart = np.load(CPRE + '_fpart.npy')
assert len(me.polygons) == len(fl), (len(me.polygons), len(fl))
VH = np.array([v.co[:] for v in me.vertices])        # Hunyuan frame, kept as the 'rest' attribute for the paint
FF = np.array([p.vertices[:] for p in me.polygons])
for v in me.vertices: v.co = M(v.co)
# ---- colour keys (match pixelize.KEYS)
KEY = dict(body=(38, 38, 46), hat=(30, 30, 38), red=(142, 26, 28), gold=(224, 176, 48), white=(216, 220, 232),
           ink=(12, 12, 16), wood=(118, 76, 40), seam=(64, 40, 22), foam=(236, 244, 255), glow=(250, 200, 90))
def lin(c):
    c = c / 255; return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
def lrgb(k): r, g, b = KEY[k]; return (lin(r), lin(g), lin(b), 1)
MATS = {}
def flat_mat(k, keyname=None):
    m = bpy.data.materials.new(k); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = lrgb(k)
    m.diffuse_color = lrgb(k)
    m['key'] = keyname or k; m['alpha'] = 0; m.use_fake_user = True; MATS[k] = m; return m
for k in KEY: flat_mat(k, 'gold' if k == 'glow' else None)
MATS['glow'].node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = lrgb('glow')
MATS['glow'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 2.0

# ---- smoothed colour weights per vertex (classes: body hat red gold white ink wood)
CLS = ['body', 'hat', 'red', 'gold', 'white', 'ink', 'wood']
CLS_OF_LAB = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 4, 6: 5, 7: 5, 8: 6, 9: 6}
cf = np.array([CLS_OF_LAB.get(int(l), 0) for l in fl])
area = 0.5 * np.linalg.norm(np.cross(VH[FF[:, 1]] - VH[FF[:, 0]], VH[FF[:, 2]] - VH[FF[:, 0]]), axis=1) + 1e-12
nv = len(VH)
W = np.zeros((nv, len(CLS)))
area[fpart == 12] = 0                                # the dropped old teeth do not colour their neighbours
for k in range(3): np.add.at(W, (FF[:, k], cf), area)
W /= W.sum(1, keepdims=True) + 1e-12
from collections import defaultdict
E_ = np.concatenate([FF[:, [0, 1]], FF[:, [1, 2]], FF[:, [2, 0]]]); E_.sort(1); E_ = np.unique(E_, axis=0)
deg = np.bincount(E_.ravel(), minlength=nv).astype(float)
for it in range(int(os.environ.get('SAB_BLUR', 2))):
    acc = np.zeros_like(W); np.add.at(acc, E_[:, 0], W[E_[:, 1]]); np.add.at(acc, E_[:, 1], W[E_[:, 0]])
    W = 0.5 * W + 0.5 * acc / np.maximum(deg, 1)[:, None]
def put_attr(name, arr, typ):
    a = me.attributes.new(name, typ, 'POINT')
    a.data.foreach_set('color' if typ == 'FLOAT_COLOR' else 'vector', arr.astype(np.float32).ravel())
wa = W[:, 0:4]; wb = np.concatenate([W[:, 4:7], np.zeros((nv, 1))], 1)
put_attr('wa', wa, 'FLOAT_COLOR'); put_attr('wb', wb, 'FLOAT_COLOR')
fn = np.cross(VH[FF[:, 1]] - VH[FF[:, 0]], VH[FF[:, 2]] - VH[FF[:, 0]])
VN = np.zeros_like(VH)
for k in range(3): np.add.at(VN, FF[:, k], fn)
VN /= np.linalg.norm(VN, axis=1, keepdims=True) + 1e-12
put_attr('rest', VH, 'FLOAT_VECTOR'); put_attr('restn', VN, 'FLOAT_VECTOR')

TEX = os.environ.get('SAB_TEX', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tex'))
PLANK = float(os.environ.get('SAB_PLANK', 0.07))
EW = 0.245; EZ0 = 0.041                                # hat emblem: image width in Hunyuan units, bottom height
def paint_mat():
    m = bpy.data.materials.new('paint'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links
    bsdf = N['Principled BSDF']
    def nd(t, **kw):
        n = N.new(t)
        for k, v in kw.items(): setattr(n, k, v)
        return n
    def math_(op, a, b=None, c=None):
        n = nd('ShaderNodeMath', operation=op)
        for i, s in enumerate((a, b, c)):
            if s is None: continue
            if isinstance(s, (int, float)): n.inputs[i].default_value = s
            else: L.new(s, n.inputs[i])
        return n.outputs[0]
    def attr(name):
        n = nd('ShaderNodeAttribute', attribute_name=name, attribute_type='GEOMETRY'); return n
    A = attr('wa'); B = attr('wb')
    sa = nd('ShaderNodeSeparateColor'); L.new(A.outputs['Color'], sa.inputs[0])
    sb = nd('ShaderNodeSeparateColor'); L.new(B.outputs['Color'], sb.inputs[0])
    ws = [sa.outputs[0], sa.outputs[1], sa.outputs[2], A.outputs['Alpha'], sb.outputs[0], sb.outputs[1], sb.outputs[2]]
    mx = ws[0]
    for w in ws[1:]: mx = math_('MAXIMUM', mx, w)
    thr = math_('SUBTRACT', mx, 1e-4)
    steps = [None] + [math_('GREATER_THAN', w, thr) for w in ws[1:]]
    def rgb(k):
        n = nd('ShaderNodeRGB'); n.outputs[0].default_value = lrgb(k); return n.outputs[0]
    colr = rgb('body')
    for k in range(1, len(CLS)):
        mix = nd('ShaderNodeMix', data_type='RGBA'); L.new(steps[k], mix.inputs['Factor'])
        L.new(colr, mix.inputs[6]); L.new(rgb(CLS[k]), mix.inputs[7]); colr = mix.outputs[2]
    R = attr('rest'); xyz = nd('ShaderNodeSeparateXYZ'); L.new(R.outputs['Vector'], xyz.inputs[0])
    RN = attr('restn'); nxyz = nd('ShaderNodeSeparateXYZ'); L.new(RN.outputs['Vector'], nxyz.inputs[0])
    # deck seams: planks run fore and aft, a dark seam every PLANK across
    fr = math_('FRACT', math_('DIVIDE', math_('SUBTRACT', xyz.outputs[1], Y0), PLANK))
    seam = math_('GREATER_THAN', math_('ABSOLUTE', math_('SUBTRACT', fr, 0.5)), 0.41)
    sf = math_('MULTIPLY', seam, steps[6])
    mix = nd('ShaderNodeMix', data_type='RGBA'); L.new(sf, mix.inputs['Factor']); L.new(colr, mix.inputs[6]); L.new(rgb('seam'), mix.inputs[7]); colr = mix.outputs[2]
    # hat emblem: a clean picture projected onto the crown's front
    u = math_('ADD', math_('DIVIDE', math_('SUBTRACT', xyz.outputs[1], YC), EW), 0.5)
    v = math_('DIVIDE', math_('SUBTRACT', xyz.outputs[2], EZ0), EW)
    cmb = nd('ShaderNodeCombineXYZ'); L.new(u, cmb.inputs[0]); L.new(v, cmb.inputs[1])
    tx = nd('ShaderNodeTexImage'); tx.image = bpy.data.images.load(os.path.join(TEX, 'hat.png')); tx.interpolation = 'Closest'; tx.extension = 'CLIP'
    L.new(cmb.outputs[0], tx.inputs[0])
    front = math_('MULTIPLY', math_('LESS_THAN', nxyz.outputs[0], -0.3), math_('LESS_THAN', xyz.outputs[0], -0.6))
    ef = math_('MULTIPLY', math_('MULTIPLY', tx.outputs['Alpha'], front), steps[1])
    mix = nd('ShaderNodeMix', data_type='RGBA'); L.new(ef, mix.inputs['Factor']); L.new(colr, mix.inputs[6]); L.new(rgb('gold'), mix.inputs[7]); colr = mix.outputs[2]
    alb = nd('ShaderNodeMix', data_type='RGBA'); alb.name = 'ALB'; alb.label = 'ALB'
    alb.inputs['Factor'].default_value = 0.0; L.new(colr, alb.inputs[6]); L.new(colr, alb.inputs[7])
    L.new(alb.outputs[2], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.6
    m['key'] = 'paint'; m['alpha'] = 0; m.use_fake_user = True; m.diffuse_color = lrgb('body')
    return m
PAINT = paint_mat()

# ---- armature (positions given in the Hunyuan frame)
arm = bpy.data.armatures.new('Rig'); rig = bpy.data.objects.new('Rig', arm); col.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
def bone(n, h, t, parent=None):
    b = arm.edit_bones.new(n); b.head = M(h); b.tail = M(t)
    if parent: b.parent = arm.edit_bones[parent]
    return b
bone('root', (0.0, Y0, -0.3), (-0.3, Y0, -0.3))
bone('spine', (0.55, Y0, -0.3), (-0.45, Y0, -0.25), 'root')
bone('head', (-0.5, Y0, -0.12), (-0.92, Y0, -0.08), 'spine')
bone('mast', (0.45, Y0, 0.0), (0.45, Y0, 0.5), 'spine')
bone('flag', (0.62, Y0, 0.62), (0.75, Y0, 0.75), 'mast')
bone('stern', (0.75, Y0, -0.2), (0.95, Y0, -0.2), 'spine')
LEGS = {}
for side, sy in (('L', 1), ('R', -1)):
    LEGS['F' + side] = [(-0.6, Y0 + 0.30 * sy, -0.36), (-0.70, Y0 + 0.43 * sy, -0.62), (-0.78, Y0 + 0.47 * sy, -0.84)]
    LEGS['B' + side] = [(0.36, Y0 + 0.20 * sy, -0.34), (0.40, Y0 + 0.25 * sy, -0.62), (0.47, Y0 + 0.28 * sy, -0.84)]
for n, (a, b_, c) in LEGS.items():
    bone(n + '_up', a, b_, 'spine'); bone(n + '_lo', b_, c, n + '_up')
bpy.ops.object.mode_set(mode='OBJECT')
BODY_BONES = ['spine', 'head'] + [n + s for n in LEGS for s in ('_up', '_lo')]
segs = {n: (arm.bones[n].head_local.copy(), arm.bones[n].tail_local.copy()) for n in arm.bones.keys()}
def seg_dist(p, a, b):
    ab = b - a; t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (a + ab * t - p).length
# vertex part = majority of its faces' parts
vpart = np.zeros(nv, int)
cnt = np.zeros((nv, 13), int)
for k in range(3): np.add.at(cnt, (FF[:, k], fpart), 1)
vpart = cnt.argmax(1)
RIGID = {1: 'head', 5: 'head', 6: 'head', 7: 'head', 9: 'head', 10: 'head', 2: 'spine', 11: 'spine', 4: 'mast', 3: 'mast', 8: 'stern'}
groups = {n: src.vertex_groups.new(name=n) for n in arm.bones.keys()}
for i, v in enumerate(me.vertices):
    p = v.co; pt = int(vpart[i])
    if pt == 10 and VH[i, 0] > -0.45: pt = 2                     # gold rail line on the hull: rides with the spine
    if pt in RIGID:
        bn = RIGID[pt]
        if pt == 3 and v.co.z > K * (0.6 - ZMIN) and v.co.y > K * 0.55: bn = 'flag'
        groups[bn].add([i], 1.0, 'REPLACE'); continue
    ds = {n: seg_dist(p, *segs[n]) for n in BODY_BONES}
    if p.z > K * (-0.45 - ZMIN):
        for n in LEGS: ds[n + '_up'] += 0.6; ds[n + '_lo'] += 1.0
    near = sorted(ds.items(), key=lambda kv: kv[1])[:2]
    ws = {n: 1.0 / (d + 0.12) ** 4 for n, d in near}; s = sum(ws.values())
    for n, w in ws.items(): groups[n].add([i], w / s, 'REPLACE')
# ---- split into one object per part; painted parts use the paint material
PART_NAME = {0: 'body', 1: 'hat', 2: 'hull', 3: 'sail', 4: 'mast', 7: 'nose', 10: 'trim', 11: 'deck'}
src.data.materials.append(PAINT)
for p in me.polygons: p.material_index = 0; p.use_smooth = True
PART_ID = {}; objs = []
fpart2 = fpart.copy(); fpart2[np.isin(fpart2, [5, 6, 9])] = 0       # stray eye/tooth faces: body
for pid, pname in PART_NAME.items():
    keep = set(np.where(fpart2 == pid)[0].tolist())
    if not keep: continue
    o = src.copy(); o.data = src.data.copy(); col.objects.link(o)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.index not in keep], context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bm.to_mesh(o.data); bm.free()
    nm = {'body': 'Body'}.get(pname, pname.capitalize())
    o.name = nm; o.data.name = nm
    if pname not in PART_ID: PART_ID[pname] = len(PART_ID) + 1
    o.pass_index = PART_ID[pname]; o['part'] = pname
    m = o.modifiers.new('rig', 'ARMATURE'); m.object = rig; o.parent = rig
    objs.append(o)
bpy.data.objects.remove(src)
body_o = bpy.data.objects.get('Body')
if body_o:
    bm = bmesh.new(); bm.from_mesh(body_o.data)
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=int(os.environ.get('SAB_HOLE', 60)))
    bm.to_mesh(body_o.data); bm.free()

# ---- sails and flag: smooth the relief away, planar UVs, clean emblem textures
def tex_mat(name, img):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(TEX, img))
    t.interpolation = 'Closest'; t.extension = 'EXTEND'; t.image.colorspace_settings.name = 'sRGB'
    nt.links.new(t.outputs['Color'], nt.nodes['Principled BSDF'].inputs['Base Color'])
    m['key'] = 'white'; m['alpha'] = 0; m.use_fake_user = True; m.diffuse_color = lrgb('white'); return m
def hun(co): return (co.y / K, -co.x / K + Y0, co.z / K + ZMIN)
SAILS = [('sailtex', 'sail.png', lambda x, y, z: z < 0.68 and x < 0.74, (-0.38, 0.37), (0.10, 0.56)),
         ('flagtex', 'flag.png', lambda x, y, z: z >= 0.68, (-0.12, 0.25), (0.69, 0.88)),
         ('sail2tex', 'sail2.png', lambda x, y, z: z < 0.68 and x >= 0.74, (-0.33, 0.02), (0.13, 0.36))]
sail = bpy.data.objects.get('Sail')
if sail:
    me_ = sail.data; me_.materials.clear()
    for nm, img, *_ in SAILS: me_.materials.append(tex_mat(nm, img))
    uvl = me_.uv_layers.new(name='UVMap')
    for p in me_.polygons:
        c = hun(p.center); k = next(i for i, s in enumerate(SAILS) if s[2](*c)); p.material_index = k
        _, _, _, (y0_, y1_), (z0_, z1_) = SAILS[k]
        for li in p.loop_indices:
            h = hun(me_.vertices[me_.loops[li].vertex_index].co)
            uvl.data[li].uv = ((h[1] - y0_) / (y1_ - y0_), (h[2] - z0_) / (z1_ - z0_))
    sm = sail.modifiers.new('smooth', 'LAPLACIANSMOOTH'); sm.lambda_factor = 1.0; sm.iterations = 12
    sm.use_volume_preserve = True; sm.use_normalized = True; sail.modifiers.move(len(sail.modifiers) - 1, 0)
mast = bpy.data.objects.get('Mast')
if mast:                                               # masts and spars: plain dark wood, no paint patches
    mast.data.materials.clear(); mast.data.materials.append(MATS['seam'])
SMOOTH_BODY = int(os.environ.get('SAB_SMOOTHBODY', 6))
for nm in ('Body', 'Hull', 'Hat', 'Deck', 'Trim'):
    o = bpy.data.objects.get(nm)
    if not o or not SMOOTH_BODY: continue
    sm = o.modifiers.new('smooth', 'LAPLACIANSMOOTH'); sm.lambda_factor = 0.6; sm.iterations = SMOOTH_BODY
    sm.use_volume_preserve = True; sm.use_normalized = True; o.modifiers.move(len(o.modifiers) - 1, 0)

# ---- helpers for the modelled pieces
def new_obj(name, bm):
    me_ = bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free()
    o = bpy.data.objects.new(name, me_); col.objects.link(o); return o
def ellipsoid(name, c, r, rotm=None, seg=20):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2 + 2, radius=1.0)
    R = rotm or Matrix.Identity(3)
    for v in bm.verts: v.co = R @ Vector((v.co.x * r[0], v.co.y * r[1], v.co.z * r[2])) + Vector(c)
    return new_obj(name, bm)
def sweep(name, pts, radii, seg=8, flat=1.0, side=None, closed=False, cap=True):
    """tube along pts; radii per point; flat < 1 squashes the section along `side` (a blade)"""
    bm = bmesh.new(); rings = []
    n = len(pts)
    for i, p in enumerate(pts):
        p = Vector(p)
        if closed: t = (Vector(pts[(i + 1) % n]) - Vector(pts[i - 1])).normalized()
        else: t = (Vector(pts[min(i + 1, n - 1)]) - Vector(pts[max(i - 1, 0)])).normalized()
        a = (Vector(side) - t * Vector(side).dot(t)).normalized() if side else t.orthogonal().normalized()
        b = t.cross(a)
        rr = radii[i]
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / seg) * flat + b * math.sin(2 * math.pi * k / seg)) * rr) for k in range(seg)])
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for r0, r1 in pairs:
        for k in range(seg): bm.faces.new((r0[k], r0[(k + 1) % seg], r1[(k + 1) % seg], r1[k]))
    if cap and not closed:
        for r in (rings[0], rings[-1]):
            c = bm.verts.new(sum((v.co for v in r), Vector()) / len(r))
            for k in range(seg): bm.faces.new((r[k], r[(k + 1) % seg], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_obj(name, bm)
def finish(o, mat, pname, bn, smooth=True):
    o.data.materials.append(MATS[mat])
    for p in o.data.polygons: p.use_smooth = smooth
    if pname not in PART_ID: PART_ID[pname] = len(PART_ID) + 1
    o.pass_index = PART_ID[pname]; o['part'] = pname
    vg = o.vertex_groups.new(name=bn); vg.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
    m = o.modifiers.new('rig', 'ARMATURE'); m.object = rig; o.parent = rig
    objs.append(o); return o
def frame_from(n, fwd):
    """rotation whose x = fwd (in the tangent plane), z = n"""
    n = n.normalized(); f = (fwd - n * fwd.dot(n)).normalized(); u = n.cross(f)
    return Matrix((f, u, n)).transposed()

# ---- eyes: white almonds set into the carved slits, angry tilt (front end lower), dark pupil toward the nose
ey = ex['eyes']
exm = np.mean([e['c'][0] for e in ey]); ezm = np.mean([e['c'][2] for e in ey])
nref = next((e['n'] for e in ey if e['c'][1] < YC), ey[0]['n'])
for e in ey:
    sgn = 1 if e['c'][1] > YC else -1
    c = Vector((exm, e['c'][1], ezm)); n = Vector((nref[0], abs(nref[1]) * sgn, nref[2])).normalized()
    cm = M(c); nm_ = MN(n)
    R = frame_from(nm_, Vector((0, -1, 0)))
    tilt = Matrix.Rotation(math.radians(-16 * sgn), 3, nm_) if True else Matrix.Identity(3)
    R2 = tilt @ R
    ES = float(os.environ.get('SAB_EYE', 1.0))
    finish(ellipsoid(f'Eye{sgn}', cm + nm_ * 0.012, (0.20 * ES, 0.085 * ES, 0.05), R2), 'white', 'eye', 'head')
    pc = cm + nm_ * 0.035 + (R2 @ Vector((0.075 * ES, -0.01, 0)))
    finish(ellipsoid(f'Pupil{sgn}', pc, (0.05 * ES, 0.055 * ES, 0.03), R2, seg=12), 'ink', 'pupil', 'head')
    R3 = Matrix.Rotation(math.radians(-30 * sgn), 3, nm_) @ R
    lid = cm + nm_ * 0.04 + (R3 @ Vector((0.0, 0.07 * ES, 0)))
    finish(ellipsoid(f'Brow{sgn}', lid, (0.27 * ES, 0.05, 0.06), R3, seg=12), 'body', 'brow', 'head')

# ---- sabres: long blades from under the upper lip down past the chin, bowed a little forward
sab = ex['sabres']
dy = np.mean([abs(s['root'][1] - YC) for s in sab]); rx = np.mean([s['root'][0] for s in sab]); rz = np.mean([s['root'][2] for s in sab])
tdy = np.mean([abs(s['tip'][1] - YC) for s in sab]); tx_ = np.mean([s['tip'][0] for s in sab]); tz = float(os.environ.get('SAB_TOOTHZ', -0.50))
for sgn in (1, -1):
    RX = float(os.environ.get('SAB_TOOTHX', -0.995))
    r0 = np.array([RX, YC + sgn * dy, rz + 0.03]); r1 = np.array([RX + 0.05, YC + sgn * (dy + 0.03), tz])
    pts = []; rad = []
    for i in range(13):
        t = i / 12
        p = r0 + (r1 - r0) * t + np.array([-0.035, 0, 0]) * math.sin(math.pi * t)
        pts.append(M(p)); rad.append(K * (0.026 * (1 - t) ** 0.75 + 0.002))
    finish(sweep(f'Sabre{sgn}', pts, rad, seg=10, flat=1.0, side=Vector((sgn * 1.0, 0, 0))), 'white', 'tusk', 'head')
# flatten the blades sideways: squash x about each sabre's own axis (model x is athwart)
for o in [o for o in objs if o.name.startswith('Sabre')]:
    cx = sum(v.co.x for v in o.data.vertices) / len(o.data.vertices)
    for v in o.data.vertices: v.co.x = cx + (v.co.x - cx) * 0.6

# ---- claws: three per paw from the toe tips, curving down (front claws bigger, as in the drawing)
for n, tips in ex['toes'].items():
    front = n[0] == 'F'; Lc = 0.08 if front else 0.06; rc = 0.017 if front else 0.013
    for j, t in enumerate(tips):
        p = np.array(t['p']); d = np.array(t['dir']); d /= np.linalg.norm(d)
        p0 = p - d * 0.02 + np.array([0, 0, 0.01])
        pts = [M(p0 + d * Lc * s + np.array([0, 0, -0.035 * s * s])) for s in np.linspace(0, 1, 7)]
        rad = [K * (rc * (1 - s) + 0.002) for s in np.linspace(0, 1, 7)]
        finish(sweep(f'Claw{n}{j}', pts, rad, seg=8), 'white', 'claw', n + '_lo')

# ---- deck: a gold balustrade around the deck's edge (rail on posts), as on Den sorte dame
dk = ex['deck']
RH = float(os.environ.get('SAB_RAILH', 0.05))
rp = [M((x, y, z + RH)) for x, y, z in dk]
finish(sweep('Rail', rp, [K * 0.009] * len(rp), seg=6, closed=True), 'gold', 'rail', 'spine')
step = max(1, len(dk) // 26)
for i in range(0, len(dk), step):
    x, y, z = dk[i]
    finish(sweep(f'Post{i}', [M((x, y, z - 0.01)), M((x, y, z + RH))], [K * 0.007] * 2, seg=6), 'gold', 'rail', 'spine')

# ---- the stern ornament (Arvind's turnaround + Den sorte dame): a gold skull facing aft, red-rimmed dark eye windows,
# an open grin with two rows of teeth, crowned by gold spikes like a flame
SKS = float(os.environ.get('SAB_SKULL', 0.85))
SK = M((0.80, -0.025, -0.22))
def sk(ox, oy, oz): return SK + Vector((ox, oy, oz)) * SKS
def sr(*r): return tuple(v * SKS for v in r)
finish(ellipsoid('SkullHead', sk(0, -0.08, 0.12), sr(0.66, 0.42, 0.55)), 'gold', 'skull', 'stern')
for sx in (1, -1):
    finish(ellipsoid(f'SkullCheek{sx}', sk(0.48 * sx, 0.16, -0.12), sr(0.22, 0.24, 0.19)), 'gold', 'skull', 'stern')
    tilt = Matrix.Rotation(math.radians(9 * sx), 3, Vector((0, 1, 0)))
    ec = sk(0.30 * sx, 0.30, 0.20)
    ring = [ec + tilt @ Vector((0.24 * math.cos(a), 0.0, 0.17 * math.sin(a))) * SKS for a in [2 * math.pi * k / 24 for k in range(24)]]
    finish(sweep(f'EyeRim{sx}', ring, [0.05 * SKS] * 24, seg=8, closed=True), 'red', 'socket', 'stern')
    finish(ellipsoid(f'EyeHole{sx}', ec + Vector((0, 0.02, 0)) * SKS, sr(0.22, 0.05, 0.155), tilt), 'ink', 'socket', 'stern')
    finish(ellipsoid(f'Nose{sx}', sk(0.045 * sx, 0.40, -0.07), sr(0.05, 0.04, 0.08), Matrix.Rotation(math.radians(-20 * sx), 3, Vector((0, 1, 0))), seg=12), 'ink', 'socket', 'stern')
finish(ellipsoid('SkullMaxilla', sk(0, 0.22, -0.22), sr(0.48, 0.26, 0.12)), 'gold', 'skull', 'stern')
finish(ellipsoid('SkullMouth', sk(0, 0.16, -0.46), sr(0.44, 0.24, 0.17)), 'ink', 'mouth', 'stern')
finish(ellipsoid('SkullJaw', sk(0, 0.18, -0.70), sr(0.48, 0.28, 0.10)), 'gold', 'skull', 'stern')
for row, zz, hh in ((0, -0.33, 0.075), (1, -0.61, 0.06)):
    for k in range(7):
        xx = (k - 3) * 0.11
        yy = 0.36 - 0.32 * (xx / 0.5) ** 2
        finish(ellipsoid(f'Tooth{row}{k}', sk(xx, yy, zz), sr(0.048, 0.045, hh), seg=10), 'white', 'skullteeth', 'stern')
# the crown of gold spikes: flat blades fanning up and back from the top of the skull
for j, (ang, ln) in enumerate(((0, 0.95), (32, 0.75), (-32, 0.75), (60, 0.5), (-60, 0.5))):
    a_ = math.radians(ang)
    base = sk(0.30 * math.sin(a_), -0.05, 0.50 * math.cos(a_) * 0.9)
    tipd = Vector((math.sin(a_), 0.45, math.cos(a_))).normalized()
    pts = [base + tipd * ln * SKS * t for t in np.linspace(0, 1, 6)]
    rad = [0.17 * SKS * (1 - t) + 0.01 for t in np.linspace(0, 1, 6)]
    finish(sweep(f'Fin{j}', pts, rad, seg=8, flat=0.35, side=Vector((0, 1, 0))), 'gold', 'skull', 'stern')

# ---- the shell's spikes (turnaround: black cones with a gold foot, three on each side, leaning up and back)
for j, sp in enumerate(ex.get('spikes', [])):
    p = np.array(sp['p']); n = np.array(sp['n'])
    ax = n + np.array([0.35, 0, 0.75]); ax /= np.linalg.norm(ax)
    H_ = float(os.environ.get('SAB_SPIKEH', 0.10)); R_ = 0.04
    P0 = p - n * 0.01
    gold_pts = [M(P0 + ax * H_ * t) for t in (0.0, 0.3)]
    finish(sweep(f'SpikeFoot{j}', gold_pts, [K * R_, K * R_ * 0.78], seg=10), 'gold', 'spikefoot', 'spine')
    blk = [M(P0 + ax * H_ * t) for t in np.linspace(0.28, 1.0, 5)]
    finish(sweep(f'Spike{j}', blk, [K * R_ * 0.8 * (1 - (t - 0.28) / 0.72) + 0.006 for t in np.linspace(0.28, 1.0, 5)], seg=10), 'body', 'spike', 'spine')

# ---- a short tail under the stern, black with a gold tip (turnaround: side view)
tp = [np.array([0.58, Y0, -0.56]) + np.array([0.33, 0, -0.10]) * t + np.array([0, 0, -0.04]) * t * t for t in np.linspace(0, 1, 9)]
tr_ = [0.055 * (1 - t) ** 0.8 + 0.004 for t in np.linspace(0, 1, 9)]
finish(sweep('Tail', [M(p) for p in tp[:7]], [K * r for r in tr_[:7]], seg=10), 'body', 'tail', 'spine')
finish(sweep('TailTip', [M(p) for p in tp[6:]], [K * r for r in tr_[6:]], seg=10), 'gold', 'tail', 'spine')

# ---- foam material for render_passes

# ---- animation
sc.frame_start = 1; sc.frame_end = NFR; sc.render.fps = 30
rig.animation_data_create(); act = bpy.data.actions.new('run_leap'); rig.animation_data.action = act
pb = rig.pose.bones
for p in pb: p.rotation_mode = 'QUATERNION'
X = Vector((1, 0, 0)); Zw = Vector((0, 0, 1)); Yw = Vector((0, 1, 0))
def rot(n, axis, deg):
    b = arm.bones[n]
    la = (b.matrix_local.to_3x3().inverted() @ axis).normalized()
    pb[n].rotation_quaternion = Quaternion(la, math.radians(deg)) @ pb[n].rotation_quaternion
def key(f):
    for p in pb:
        p.keyframe_insert('location', frame=f); p.keyframe_insert('rotation_quaternion', frame=f)
SWING = float(os.environ.get('SAB_SWING', 28)); LIFT = float(os.environ.get('SAB_LIFT', 55))
# the pounce of a cat at the viewer: front legs reach forward and up, nearly parallel, paws bent down so the pads and
# claws face the camera; hind legs stretch back from the push-off; body pitched up, head down to glare
LEAP = {5: dict(up=0.25, fwd=0.30, pitch=8, reach=45, spread=4, curl=20, hind=-25, head=5),
        6: dict(up=0.75, fwd=0.90, pitch=14, reach=80, spread=8, curl=34, hind=-45, head=10),
        7: dict(up=1.05, fwd=1.40, pitch=16, reach=96, spread=12, curl=42, hind=-55, head=14)}
PH = {'FL': 0.0, 'BR': 0.0, 'FR': math.pi, 'BL': math.pi}
for f in range(1, NFR + 1):
    for p in pb: p.location = (0, 0, 0); p.rotation_quaternion = (1, 0, 0, 0)
    if f < LEAP0:
        ph = 2 * math.pi * (f - 1) / (LEAP0 - 1)
        for n, sh in PH.items():
            a = ph + sh; fwd = math.sin(a); lift = max(0.0, math.cos(a)); front = n[0] == 'F'
            rot(n + '_up', X, -SWING * fwd - (18 * lift if front else 8 * lift))
            rot(n + '_lo', X, (LIFT if front else 30) * lift)
        rot('root', Yw, 3 * math.sin(ph))
        rot('head', X, -3 * math.sin(2 * ph + 0.6))
        rot('mast', Yw, 2.5 * math.sin(ph + 0.5))
        rot('flag', Zw, 14 * math.sin(ph))
    else:
        L = LEAP[f]
        rot('root', X, -L['pitch'])
        for n in LEGS:
            if n[0] == 'F':
                side = 1 if n[1] == 'L' else -1
                rot(n + '_up', X, -L['reach']); rot(n + '_up', Zw, -side * L['spread']); rot(n + '_lo', X, L['curl'])
            else:
                rot(n + '_up', X, -L['hind']); rot(n + '_lo', X, 12)
        rot('head', X, L['head'])
        rot('flag', Zw, -18)
    key(f)
    bm_ = arm.bones['root'].matrix_local.to_3x3().inverted()
    if f >= LEAP0:
        L = LEAP[f]; pb['root'].location = bm_ @ Vector((0, -L['fwd'], L['up']))
    else:
        pb['root'].location = bm_ @ Vector((0, 0, 0.07 * math.cos(4 * math.pi * (f - 1) / (LEAP0 - 1))))
    pb['root'].keyframe_insert('location', frame=f)
def const(fc):
    for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
for fc in getattr(act, 'fcurves', []): const(fc)
try:
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                for fc in cb.fcurves: const(fc)
except Exception:
    pass
sc['water'] = WATER; sc['leap0'] = LEAP0; sc['part_ids'] = str(PART_ID)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('saved', OUT, 'objects', len(objs), PART_ID)
