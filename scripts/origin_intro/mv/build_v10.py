"""v10 Sabertann: the multi-view mesh (Hunyuan3D-2mv from Arvind's turnaround, no tail), coloured from his views
(mv/paint_mv.py), cleaned (h3d/clean_labels.py), painted per pixel, rigged; the deck gets a gold rail.
Blender -b --factory-startup -P mv/build_v10.py -- MESH.ply CLEAN_PREFIX EXTRA.json OUT.blend
mv frame: faces -Y, +X = its left, Z up. Model frame = K * mv, feet at z = 0.
--- notes kept from v9:
v9 Sabertann (Arvind's v8 notes: snout like a dog's, black paws with claws, a deck instead of a red barrel, the stern
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
K = float(os.environ.get('SAB_K', 3.3)); ZMIN = float(os.environ.get('SAB_ZMIN', -0.70)); Y0 = 0.0; YC = 0.0
WATER = float(os.environ.get('SAB_WATER7', 0.16))
NFR = int(os.environ.get('SAB_NFR10', 9)); LEAP0 = 5
def M(h):                                            # mv frame -> model frame (same axes, scaled, feet at 0)
    x, y, z = h
    return Vector((K * x, K * y, K * (z - ZMIN)))
def MN(n): return Vector(n)
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
KEY = dict(eyeglow=(255, 240, 190), grey=(84, 84, 94), body=(38, 38, 46), hat=(30, 30, 38), red=(142, 26, 28), gold=(224, 176, 48), white=(216, 220, 232),
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
eg = flat_mat('eyeglow', 'white')                      # the eyes glow (Ho-Oh, Lugia): pale light, emissive
eg.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (1.0, 0.93, 0.62, 1)
eg.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (1.0, 0.93, 0.62, 1)
eg.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 3.0

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
EW = float(os.environ.get('SAB_EW', 0.26)); EZ0 = float(os.environ.get('SAB_EZ0', 0.136))                                # hat emblem: image width in Hunyuan units, bottom height
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
    fr = math_('FRACT', math_('DIVIDE', xyz.outputs[0], PLANK))
    seam = math_('GREATER_THAN', math_('ABSOLUTE', math_('SUBTRACT', fr, 0.5)), 0.41)
    sf = math_('MULTIPLY', seam, steps[6])
    mix = nd('ShaderNodeMix', data_type='RGBA'); L.new(sf, mix.inputs['Factor']); L.new(colr, mix.inputs[6]); L.new(rgb('seam'), mix.inputs[7]); colr = mix.outputs[2]
    # hat emblem: a clean picture projected onto the crown's front
    u = math_('ADD', math_('DIVIDE', xyz.outputs[0], EW), 0.5)
    v = math_('DIVIDE', math_('SUBTRACT', xyz.outputs[2], EZ0), EW)
    cmb = nd('ShaderNodeCombineXYZ'); L.new(u, cmb.inputs[0]); L.new(v, cmb.inputs[1])
    tx = nd('ShaderNodeTexImage'); tx.image = bpy.data.images.load(os.path.join(TEX, 'hat.png')); tx.interpolation = 'Closest'; tx.extension = 'CLIP'
    L.new(cmb.outputs[0], tx.inputs[0])
    front = math_('MULTIPLY', math_('LESS_THAN', nxyz.outputs[1], -0.3), math_('LESS_THAN', xyz.outputs[1], -0.6))
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
J = json.loads(os.environ['SAB_JOINTS']) if os.environ.get('SAB_JOINTS') else {}
def jp(n, dflt): return tuple(J.get(n, dflt))
bone('root', (0.0, 0.0, -0.25), (0.0, -0.3, -0.25))
bone('spine', (0.0, 0.55, -0.25), (0.0, -0.45, -0.2), 'root')
bone('head', jp('head0', (0.0, -0.5, -0.05)), jp('head1', (0.0, -0.95, 0.0)), 'spine')
bone('jaw', (0.0, -0.70, -0.045), (0.0, -0.95, -0.10), 'head')       # v15: the lower jaw, hinged at the mouth corners
bone('mast', jp('mast0', (0.0, 0.2, 0.05)), jp('mast1', (0.0, 0.2, 0.6)), 'spine')
bone('flag', jp('flag0', (0.0, 0.2, 0.6)), jp('flag1', (0.0, 0.3, 0.75)), 'mast')
bone('stern', (0.0, 0.5, -0.2), (0.0, 0.8, -0.2), 'spine')
LEGS = {}
FA = jp('front', (0.24, -0.52, -0.22, 0.33, -0.60, -0.50, 0.36, -0.66, -0.70))
HA = jp('hind', (0.20, 0.33, -0.25, 0.30, 0.40, -0.50, 0.32, 0.42, -0.70))
for side, sx in (('L', 1), ('R', -1)):
    LEGS['F' + side] = [(FA[0] * sx, FA[1], FA[2]), (FA[3] * sx, FA[4], FA[5]), (FA[6] * sx, FA[7], FA[8])]
    LEGS['B' + side] = [(HA[0] * sx, HA[1], HA[2]), (HA[3] * sx, HA[4], HA[5]), (HA[6] * sx, HA[7], HA[8])]
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
cnt = np.zeros((nv, 15), int)
for k in range(3): np.add.at(cnt, (FF[:, k], fpart), 1)
vpart = cnt.argmax(1)
RIGID = {1: 'head', 5: 'head', 6: 'head', 7: 'head', 9: 'head', 10: 'head', 2: 'spine', 11: 'spine', 4: 'mast', 3: 'mast', 8: 'stern', 14: 'flag'}
LEGZ = float(os.environ.get('SAB_LEGZ', -0.32))
groups = {n: src.vertex_groups.new(name=n) for n in arm.bones.keys()}
for i, v in enumerate(me.vertices):
    p = v.co; pt = int(vpart[i])
    if pt in RIGID:
        bn = RIGID[pt]
        if pt in (3, 4) and VH[i, 2] > float(os.environ.get('SAB_FLAGZ', 0.62)): bn = 'flag'
        groups[bn].add([i], 1.0, 'REPLACE'); continue
    ds = {n: seg_dist(p, *segs[n]) for n in BODY_BONES}
    if VH[i, 2] > LEGZ:
        for n in LEGS: ds[n + '_up'] += 0.6; ds[n + '_lo'] += 1.0
    near = sorted(ds.items(), key=lambda kv: kv[1])[:2]
    ws = {n: 1.0 / (d + 0.12) ** 4 for n, d in near}; s = sum(ws.values())
    for n, w in ws.items(): groups[n].add([i], w / s, 'REPLACE')
# ---- the lower jaw (v15): from the lip line (z -0.03) down to the chin, in front of the mouth corners; smooth edges
def sstep(a, b, v): t = min(1.0, max(0.0, (v - a) / (b - a))); return t * t * (3 - 2 * t)
gj = groups['jaw']
wj = np.zeros(nv)
for i in range(nv):
    xh, yh, zh = VH[i]
    if abs(xh) > 0.3 or yh > -0.62 or zh > -0.005 or zh < -0.26 or int(vpart[i]) in (1, 6, 10): continue
    lip = 1.0 if zh < -0.03 else 0.0                      # a clean cut at the lip line: the lips part
    w = lip * sstep(-0.64, -0.76, yh) * sstep(-0.26, -0.19, zh) * sstep(0.3, 0.2, abs(xh))
    if w <= 0: continue
    wj[i] = w
    v = me.vertices[i]
    for g in v.groups: g.weight *= (1 - w)
    gj.add([i], w, 'REPLACE')
# faces across the lip line (one corner on the jaw, one on the upper lip) go, so the mouth can open
fc = VH[FF].mean(1); fw = wj[FF]
cut = (fw.max(1) > 0.6) & (fw.min(1) < 0.2) & (fc[:, 2] > -0.08) & (fc[:, 2] < 0.02) & (fc[:, 1] < -0.70)
fpart = fpart.copy(); fpart[cut] = 12
# ---- split into one object per part; painted parts use the paint material
PART_NAME = {0: 'body', 1: 'hat', 2: 'hull', 3: 'sail', 4: 'mast', 5: 'eye', 6: 'tusk', 7: 'nose', 8: 'stern', 9: 'pupil', 10: 'trim', 11: 'deck', 13: 'claw', 14: 'flag'}
src.data.materials.append(PAINT)
for p in me.polygons: p.material_index = 0; p.use_smooth = True
PART_ID = {}; objs = []
fpart2 = fpart.copy()
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
if sail and os.environ.get('SAB_SAILTEX') == '1':
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
if mast and False:
    mast.data.materials.clear(); mast.data.materials.append(MATS['seam'])
SMOOTH_BODY = int(os.environ.get('SAB_SMOOTHBODY', 6))
for nm in ('Body', 'Hull', 'Hat', 'Deck', 'Trim', 'Stern', 'Sail'):
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

# ---- eyes (Arvind's front view): narrow white eyes on the face under the hat brim, inner ends lower (angry), a dark
# pupil at the inner end, and a heavy brow ridge over each one
for e in ex.get('eyes', []):
    cm = M(e['c']); nm_ = MN(e['n']).normalized()
    out_ = Vector((1.0 if e['c'][0] > 0 else -1.0, 0, 0))
    f = (out_ - nm_ * out_.dot(nm_)).normalized(); u = nm_.cross(f)
    if u.z < 0: u = -u; f = u.cross(nm_)                  # keep (f, u, n) right-handed with u pointing up
    R = Matrix((f, u, nm_)).transposed()
    ES = float(os.environ.get('SAB_EYE', 1.4)); TILT = float(os.environ.get('SAB_EYETILT', 18))
    sg = 1 if f.x > 0 else -1                              # rotating toward u lifts the outer end when f points outward
    R2 = Matrix.Rotation(math.radians(TILT), 3, nm_) @ R if f.dot(out_) > 0 else Matrix.Rotation(math.radians(-TILT), 3, nm_) @ R
    finish(ellipsoid(f'Eye{sg}', cm + nm_ * 0.015, (0.17 * ES, 0.065 * ES, 0.045), R2), 'eyeglow', 'eye', 'head')
    if os.environ.get('SAB_PUPIL', '0') == '1':          # v12: glowing eyes without pupils, like Ho-Oh's
        pc = cm + nm_ * 0.045 + (R2 @ Vector((-0.06 * ES, -0.005, 0)))
        finish(ellipsoid(f'Pupil{sg}', pc, (0.045 * ES, 0.045 * ES, 0.03), R2, seg=12), 'ink', 'pupil', 'head')
    R3 = Matrix.Rotation(math.radians(TILT + 10), 3, nm_) @ R if f.dot(out_) > 0 else Matrix.Rotation(math.radians(-TILT - 10), 3, nm_) @ R
    lid = cm + nm_ * 0.06 + (R3 @ Vector((0.0, 0.075 * ES + float(os.environ.get('SAB_BROWUP', 0.03)), 0)))
    finish(ellipsoid(f'Brow{sg}', lid, (0.26 * ES, 0.06, 0.08), R3, seg=14), 'grey', 'brow', 'head')

# ---- inside the mouth (seen when the jaw opens): dark red, with a row of small lower teeth on the jaw
finish(ellipsoid('MouthIn', M((0.0, -0.80, -0.06)), (K * 0.12, K * 0.09, K * 0.03)), 'red', 'mouth', 'head')
finish(ellipsoid('Palate', M((0.0, -0.84, -0.04)), (K * 0.12, K * 0.08, K * 0.02)), 'red', 'mouth', 'head')
finish(ellipsoid('Tongue', M((0.0, -0.84, -0.085)), (K * 0.07, K * 0.08, K * 0.02)), 'red', 'mouth', 'jaw')
for j, xt in enumerate((-0.10, -0.045, 0.045, 0.10)):
    tb = np.array([xt, -0.93 + 0.02 * abs(xt) / 0.1, -0.06])
    finish(sweep(f'LowTooth{j}', [M(tb), M(tb + np.array([0, -0.004, 0.035]))], [K * 0.012, K * 0.002], seg=6), 'white', 'tusk', 'jaw')

# ---- claws: white, from the toe tips, curving down (four on the front paws, three behind, as on the turnaround)
for n, tips in ex.get('toes', {}).items():
    front = n[0] == 'F'; Lc = 0.075 if front else 0.06; rc = 0.017 if front else 0.014
    for j, t in enumerate(tips):
        p_ = np.array(t['p']); d_ = np.array(t['dir']); d_ /= np.linalg.norm(d_)
        p0 = p_ - d_ * 0.025 + np.array([0, 0, 0.012])
        pts = [M(p0 + d_ * Lc * s_ + np.array([0, 0, -0.035 * s_ * s_])) for s_ in np.linspace(0, 1, 7)]
        rad = [K * (rc * (1 - s_) + 0.002) for s_ in np.linspace(0, 1, 7)]
        finish(sweep(f'Claw{n}{j}', pts, rad, seg=8), 'white', 'claw', n + '_lo')

# ---- the hat's gold edge: a clean band along the brim's outline
he = ex.get('hat_edge', [])
if len(he) > 8:
    finish(sweep('HatEdge', [M(p_) for p_ in he], [K * float(os.environ.get('SAB_HATEDGE', 0.012))] * len(he), seg=6, closed=True), 'gold', 'trim', 'head')

# ---- the gold skull on the back (Den sorte dame), at the aft end of the gold stern ornament, facing aft
SKS = float(os.environ.get('SAB_SKULL', 0.8))
SK = M([float(t) for t in os.environ.get('SAB_SKULLAT', '0,0.90,-0.33').split(',')])
def sk(ox, oy, oz): return SK + Vector((ox, oy, oz)) * SKS
def sr(*r): return tuple(v * SKS for v in r)
finish(ellipsoid('SkullHead', sk(0, -0.08, 0.12), sr(0.66, 0.42, 0.55)), 'gold', 'skull', 'stern')
for sx in (1, -1):
    finish(ellipsoid(f'SkullCheek{sx}', sk(0.48 * sx, 0.16, -0.12), sr(0.22, 0.24, 0.19)), 'gold', 'skull', 'stern')
    tilt = Matrix.Rotation(math.radians(9 * sx), 3, Vector((0, 1, 0)))
    ec = sk(0.30 * sx, 0.30, 0.20)
    ring = [ec + tilt @ Vector((0.24 * math.cos(a_), 0.0, 0.17 * math.sin(a_))) * SKS for a_ in [2 * math.pi * k / 24 for k in range(24)]]
    finish(sweep(f'EyeRim{sx}', ring, [0.05 * SKS] * 24, seg=8, closed=True), 'red', 'socket', 'stern')
    finish(ellipsoid(f'EyeHole{sx}', ec + Vector((0, 0.02, 0)) * SKS, sr(0.22, 0.05, 0.155), tilt), 'ink', 'socket', 'stern')
    finish(ellipsoid(f'SkNose{sx}', sk(0.045 * sx, 0.40, -0.07), sr(0.05, 0.04, 0.08), Matrix.Rotation(math.radians(-20 * sx), 3, Vector((0, 1, 0))), seg=12), 'ink', 'socket', 'stern')
finish(ellipsoid('SkullMaxilla', sk(0, 0.22, -0.22), sr(0.48, 0.26, 0.12)), 'gold', 'skull', 'stern')
finish(ellipsoid('SkullMouth', sk(0, 0.16, -0.46), sr(0.44, 0.24, 0.17)), 'ink', 'mouth', 'stern')
finish(ellipsoid('SkullJaw', sk(0, 0.18, -0.70), sr(0.48, 0.28, 0.10)), 'gold', 'skull', 'stern')
for row, zz, hh in ((0, -0.33, 0.075), (1, -0.61, 0.06)):
    for k in range(7):
        xx = (k - 3) * 0.11; yy = 0.36 - 0.32 * (xx / 0.5) ** 2
        finish(ellipsoid(f'Tooth{row}{k}', sk(xx, yy, zz), sr(0.048, 0.045, hh), seg=10), 'white', 'skullteeth', 'stern')

# ---- the flag: white cloth with a gold skull, projected from the front
flag = bpy.data.objects.get('Flag')
if flag:
    me_ = flag.data
    xs_ = [v.co.x for v in me_.vertices]; zs_ = [v.co.z for v in me_.vertices]
    x0, x1, z0, z1 = min(xs_), max(xs_), min(zs_), max(zs_)
    me_.materials.append(tex_mat('flagtex', 'flag.png')); ti = len(me_.materials) - 1
    uvl = me_.uv_layers.new(name='UVMap')
    for p in me_.polygons:
        p.material_index = ti
        for li in p.loop_indices:
            co = me_.vertices[me_.loops[li].vertex_index].co
            uvl.data[li].uv = ((co.x - x0) / max(x1 - x0, 1e-6), (co.z - z0) / max(z1 - z0, 1e-6))

# ---- the square sails: a clean skull and crossbones on their front, projected from the front (the flag stays painted)
sail = bpy.data.objects.get('Sail')
if sail and os.environ.get('SAB_SAILEMB', '1') == '1':
    me_ = sail.data
    FZ = K * (float(os.environ.get('SAB_FLAGZ', 0.62)) - ZMIN)
    vs = [v.co for v in me_.vertices if v.co.z < FZ]
    x0, x1 = min(v.x for v in vs), max(v.x for v in vs); z0, z1 = min(v.z for v in vs), max(v.z for v in vs)
    me_.materials.append(tex_mat('sailtex', 'sail.png')); ti = len(me_.materials) - 1
    uvl = me_.uv_layers.new(name='UVMap')
    for p in me_.polygons:
        if p.center.z >= FZ: continue
        p.material_index = ti
        for li in p.loop_indices:
            co = me_.vertices[me_.loops[li].vertex_index].co
            uvl.data[li].uv = ((co.x - x0) / (x1 - x0), (co.z - z0) / (z1 - z0))

# ---- deck: a gold balustrade around the deck's edge (rail on posts), as on Den sorte dame
dk = ex['deck']
RH = float(os.environ.get('SAB_RAILH', 0.05))
rp = [M((x, y, z + RH)) for x, y, z in dk]
finish(sweep('Rail', rp, [K * 0.009] * len(rp), seg=6, closed=True), 'gold', 'rail', 'spine')
step = max(1, len(dk) // 26)
for i in range(0, len(dk), step):
    x, y, z = dk[i]
    finish(sweep(f'Post{i}', [M((x, y, z - 0.01)), M((x, y, z + RH))], [K * 0.007] * 2, seg=6), 'gold', 'rail', 'spine')

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
LEAP = {5: dict(up=0.25, fwd=0.30, pitch=8, reach=38, spread=16, curl=22, hind=-25, head=3),
        6: dict(up=0.75, fwd=0.90, pitch=14, reach=60, spread=30, curl=26, hind=-48, head=4),
        7: dict(up=1.15, fwd=1.40, pitch=20, reach=70, spread=32, curl=26, hind=-56, head=8, jaw=14),
        # v14: the attack. He lunges straight at the viewer, body stretched out level, forelegs thrust at the camera
        # with the claws open, hind legs flung back, head low and forward
        8: dict(up=1.35, fwd=2.2, pitch=8, reach=92, spread=22, curl=6, hind=-70, head=-8, jaw=45),
        9: dict(up=1.45, fwd=3.0, pitch=4, reach=100, spread=26, curl=0, hind=-78, head=-12, jaw=58)}
PH = {'FL': 0.0, 'BR': 0.0, 'FR': math.pi, 'BL': math.pi}
for f in range(1, NFR + 1):
    for p in pb: p.location = (0, 0, 0); p.rotation_quaternion = (1, 0, 0, 0)
    if f < LEAP0:
        # v13 run: a cat's bound, front pair and hind pair together, the body rocking and rising, the head steadier
        # than the body, the mast swaying a beat behind. Key poses (deg; negative swings a leg forward):
        RUN = [dict(fu=24, fl=8, hu=-30, hl=24, pitch=-3, bob=-0.11, head=3, roll=-2),    # gather: legs under the body
               dict(fu=-12, fl=55, hu=12, hl=8, pitch=6, bob=0.03, head=-4, roll=1),       # push: hind drive back, front lift
               dict(fu=-40, fl=22, hu=32, hl=4, pitch=1, bob=0.14, head=-1, roll=2),       # stretch: front reach, hind back
               dict(fu=-10, fl=0, hu=4, hl=48, pitch=-7, bob=-0.02, head=5, roll=-1)]      # land: front planted, hind tuck
        i = (f - 1) % 4; R0 = RUN[i]; R1 = RUN[(i + 1) % 4]; Rp = RUN[(i - 1) % 4]
        for n in LEGS:
            lead = 0.0 if n[1] == 'L' else 0.3                # the right pair runs a little behind: not robotic
            g = {k: (1 - lead) * R0[k] + lead * Rp[k] for k in R0}
            if n[0] == 'F': rot(n + '_up', X, g['fu']); rot(n + '_lo', X, g['fl'])
            else: rot(n + '_up', X, g['hu']); rot(n + '_lo', X, g['hl'])
        rot('root', X, -R0['pitch'])
        rot('root', Yw, R0['roll'])
        rot('head', X, R0['head'] + 0.5 * R0['pitch'])
        rot('mast', X, 0.6 * Rp['pitch'] - 0.6 * R0['pitch'])   # the rig lags the body
        rot('mast', Yw, 2.5 * math.sin(2 * math.pi * i / 4 + 0.5))
        rot('flag', Zw, 14 * math.sin(2 * math.pi * i / 4))
    else:
        L = LEAP[f]
        rot('root', X, -L['pitch'])
        for n in LEGS:
            if n[0] == 'F':
                side = -1 if n[1] == 'L' else 1                # v10 frame: L is +X (v9 had it on -X); +spread swings the paw outward
                rot(n + '_up', X, -L['reach']); rot(n + '_up', Zw, -side * L['spread']); rot(n + '_lo', X, L['curl'])
            else:
                rot(n + '_up', X, -L['hind']); rot(n + '_lo', X, 12)
        rot('head', X, L['head'])
        rot('jaw', X, L.get('jaw', 0))
        rot('flag', Zw, -18)
    key(f)
    bm_ = arm.bones['root'].matrix_local.to_3x3().inverted()
    if f >= LEAP0:
        L = LEAP[f]; pb['root'].location = bm_ @ Vector((0, -L['fwd'], L['up']))
    else:
        pb['root'].location = bm_ @ Vector((0, 0, [-0.11, 0.03, 0.14, -0.02][(f - 1) % 4]))
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
