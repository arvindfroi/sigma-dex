"""v7 Sabertann: the Hunyuan3D mesh made from Arvind's drawing, painted (paint.py), rigged and animated for the intro.
Blender -b --factory-startup -P h3d/build_v7.py -- MESH.ply LABELS.npy PARTS.npy OUT.blend
Model frame like the old model: creature faces -Y, up +Z, feet at z = 0, water at WATER (he runs on the surface).
Frames 1-4: a trot toward the camera (diagonal pairs), 5-7: the leap at the camera."""
import bpy, bmesh, math, os, sys
import numpy as np
from mathutils import Vector, Matrix, Quaternion
argv = sys.argv[sys.argv.index('--') + 1:]
MESH, LABS, PARTS, OUT = argv[:4]
K = 3.3; ZMIN = -0.863; Y0 = -0.015
WATER = float(os.environ.get('SAB_WATER7', 0.16))
NFR = 7; LEAP0 = 5
def M(h):                                            # Hunyuan frame -> model frame
    x, y, z = h
    return Vector((-K * (y - Y0), K * x, K * (z - ZMIN)))

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene; col = sc.collection
bpy.ops.wm.ply_import(filepath=MESH)
src = sc.objects[0]; src.name = 'Src'
lab = np.load(LABS); part = np.load(PARTS)
me = src.data
assert len(me.vertices) == len(lab)
# ---- move into the model frame
for v in me.vertices: v.co = M(v.co)
# ---- materials (keys match pixelize.KEYS)
KEY = dict(body=(38, 38, 46), hat=(30, 30, 38), red=(142, 26, 28), gold=(224, 176, 48),
           white=(216, 220, 232), ink=(12, 12, 16), foam=(236, 244, 255))
def lin(c):
    c = c / 255; return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
MATS = {}
for k, (r, g, b) in KEY.items():
    m = bpy.data.materials.new(k); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (lin(r), lin(g), lin(b), 1)
    m['key'] = k; m['alpha'] = 0; m.use_fake_user = True; MATS[k] = m
CLASS_MAT = {0: 'body', 1: 'hat', 2: 'red', 3: 'gold', 4: 'white', 5: 'white', 6: 'ink', 7: 'ink'}
PART_NAME = {0: 'body', 1: 'hat', 2: 'hull', 3: 'sail', 4: 'mast', 5: 'eye', 6: 'tusk', 7: 'nose', 8: 'stern', 9: 'brow', 10: 'trim'}

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
RIGID = {1: 'head', 5: 'head', 6: 'head', 7: 'head', 9: 'head', 10: 'head', 2: 'spine', 4: 'mast', 3: 'mast', 8: 'stern'}
groups = {n: src.vertex_groups.new(name=n) for n in arm.bones.keys()}
V = np.array([v.co[:] for v in me.vertices])
for i, v in enumerate(me.vertices):
    p = Vector(V[i]); pt = int(part[i])
    if pt in RIGID:
        bn = RIGID[pt]
        if pt == 3 and v.co.z > K * (0.6 - ZMIN) and v.co.y > K * 0.55: bn = 'flag'
        groups[bn].add([i], 1.0, 'REPLACE'); continue
    # body: legs below the belly line, head in front of the neck, spine elsewhere; smooth blend of the 2 nearest
    ds = {n: seg_dist(p, *segs[n]) for n in BODY_BONES}
    if p.z > K * (-0.45 - ZMIN):
        for n in LEGS: ds[n + '_up'] += 0.6; ds[n + '_lo'] += 1.0
    near = sorted(ds.items(), key=lambda kv: kv[1])[:2]
    ws = {n: 1.0 / (d + 0.12) ** 4 for n, d in near}; s = sum(ws.values())
    for n, w in ws.items(): groups[n].add([i], w / s, 'REPLACE')
# ---- face materials and parts, then split into one object per part
mat_index = {}
for k in KEY: src.data.materials.append(MATS[k]); mat_index[k] = len(src.data.materials) - 1
fl = np.zeros(len(me.polygons), int); fp = np.zeros(len(me.polygons), int)
for p in me.polygons:
    vs = list(p.vertices)
    c = np.bincount(lab[vs], minlength=8); fl[p.index] = c.argmax()
    q = np.bincount(part[vs], minlength=11); fp[p.index] = q.argmax()
    p.material_index = mat_index[CLASS_MAT[int(fl[p.index])]]
    p.use_smooth = True
PART_ID = {}
objs = []
for pid, pname in PART_NAME.items():
    if pid == 8: continue                                     # the old stern ornament goes; the skull replaces it
    keep = set(np.where(fp == pid)[0].tolist())
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

# ---- the gold skull at the stern (Den sorte dame): facing aft, red-rimmed eye windows, nose hole, grinning teeth
def ellipsoid(name, c, r, seg=20):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2 + 2, radius=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * r[0], v.co.y * r[1], v.co.z * r[2])) + Vector(c)
    me_ = bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free()
    o = bpy.data.objects.new(name, me_); col.objects.link(o); return o
def tube(name, pts, rad, seg=6):
    bm = bmesh.new(); rings = []
    for i, p in enumerate(pts):
        p = Vector(p); t = (Vector(pts[min(i + 1, len(pts) - 1)]) - Vector(pts[max(i - 1, 0)])).normalized()
        a = t.orthogonal().normalized(); b = t.cross(a)
        rings.append([bm.verts.new(p + (a * math.cos(2 * math.pi * k / seg) + b * math.sin(2 * math.pi * k / seg)) * rad) for k in range(seg)])
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(seg): bm.faces.new((r0[k], r0[(k + 1) % seg], r1[(k + 1) % seg], r1[k]))
    me_ = bpy.data.meshes.new(name); bm.to_mesh(me_); bm.free()
    o = bpy.data.objects.new(name, me_); col.objects.link(o); return o
SKS = float(os.environ.get('SAB_SKULL', 1.25))
SK = M((0.80, Y0, -0.16))
def sk(ox, oy, oz): return SK + Vector((ox, oy, oz)) * SKS
def finish(o, mat, pname, bn='stern'):
    o.data.materials.append(MATS[mat])
    for p in o.data.polygons: p.use_smooth = True
    if pname not in PART_ID: PART_ID[pname] = len(PART_ID) + 1
    o.pass_index = PART_ID[pname]; o['part'] = pname
    vg = o.vertex_groups.new(name=bn); vg.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
    m = o.modifiers.new('rig', 'ARMATURE'); m.object = rig; o.parent = rig
    objs.append(o); return o
finish(ellipsoid('SkullDome', sk(0, -0.02, 0.1), (0.46 * SKS, 0.42 * SKS, 0.44 * SKS)), 'gold', 'skull')
finish(ellipsoid('SkullFace', sk(0, 0.2, -0.16), (0.38 * SKS, 0.28 * SKS, 0.3 * SKS)), 'gold', 'skull')
finish(ellipsoid('SkullJaw', sk(0, 0.16, -0.46), (0.3 * SKS, 0.24 * SKS, 0.15 * SKS)), 'gold', 'skull')
for sx in (1, -1):
    finish(ellipsoid(f'SkullCheek{sx}', sk(0.37 * sx, 0.16, -0.14), (0.15 * SKS, 0.2 * SKS, 0.14 * SKS)), 'gold', 'skull')
    ring = [tuple(sk(0.2 * sx + 0.16 * math.cos(a), 0.4, 0.03 + 0.16 * math.sin(a))) for a in [2 * math.pi * k / 16 for k in range(17)]]
    finish(tube(f'SocketRim{sx}', ring, 0.05 * SKS), 'red', 'socket')
    finish(ellipsoid(f'Socket{sx}', sk(0.2 * sx, 0.37, 0.03), (0.14 * SKS, 0.06 * SKS, 0.14 * SKS)), 'ink', 'socket')
finish(ellipsoid('SkullNose', sk(0, 0.48, -0.17), (0.06 * SKS, 0.05 * SKS, 0.09 * SKS)), 'ink', 'socket')
finish(ellipsoid('SkullMouth', sk(0, 0.36, -0.38), (0.24 * SKS, 0.06 * SKS, 0.08 * SKS)), 'ink', 'socket')
for row, zz in ((0, -0.31), (1, -0.45)):
    for k in range(7):
        xx = (k - 3) * 0.068
        finish(ellipsoid(f'Tooth{row}{k}', sk(xx, 0.4 - 0.02 * abs(k - 3), zz), (0.03 * SKS, 0.04 * SKS, 0.05 * SKS), seg=10), 'white', 'skullteeth')

# ---- foam material for render_passes
fm = bpy.data.materials.new('foam'); fm.use_nodes = True
r, g, b = KEY['foam']; fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (lin(r), lin(g), lin(b), 1)
fm['key'] = 'foam'; fm['alpha'] = 0; fm.use_fake_user = True

# ---- animation
sc.frame_start = 1; sc.frame_end = NFR; sc.render.fps = 30
rig.animation_data_create(); act = bpy.data.actions.new('run_leap'); rig.animation_data.action = act
pb = rig.pose.bones
for p in pb: p.rotation_mode = 'QUATERNION'
X = Vector((1, 0, 0)); Zw = Vector((0, 0, 1)); Yw = Vector((0, 1, 0))
def rot(n, axis, deg):
    """rotate a pose bone about a world-frame axis (taken in its rest orientation)"""
    b = arm.bones[n]
    la = (b.matrix_local.to_3x3().inverted() @ axis).normalized()
    pb[n].rotation_quaternion = Quaternion(la, math.radians(deg)) @ pb[n].rotation_quaternion
def key(f):
    for p in pb:
        p.keyframe_insert('location', frame=f); p.keyframe_insert('rotation_quaternion', frame=f)
# signs: +deg about +X swings a hanging leg backward (+Y); the nose (at -Y) goes up for -deg about +X
SWING = float(os.environ.get('SAB_SWING', 28)); LIFT = float(os.environ.get('SAB_LIFT', 55))
LEAP = {5: dict(up=0.35, fwd=0.35, pitch=6, reach=40, hind=-20, head=8),
        6: dict(up=0.95, fwd=0.9, pitch=11, reach=65, hind=-30, head=14),
        7: dict(up=1.25, fwd=1.4, pitch=14, reach=78, hind=-38, head=18)}     # head > pitch: he glares down at us
PH = {'FL': 0.0, 'BR': 0.0, 'FR': math.pi, 'BL': math.pi}
for f in range(1, NFR + 1):
    for p in pb: p.location = (0, 0, 0); p.rotation_quaternion = (1, 0, 0, 0)
    if f < LEAP0:
        ph = 2 * math.pi * (f - 1) / (LEAP0 - 1)
        for n, sh in PH.items():
            a = ph + sh
            fwd = math.sin(a)                     # +1: leg reaching forward
            lift = max(0.0, math.cos(a))          # swing phase: the paw is up
            front = n[0] == 'F'
            rot(n + '_up', X, -SWING * fwd - (18 * lift if front else 8 * lift))
            rot(n + '_lo', X, (LIFT if front else 30) * lift)
        bob = 0.07 * math.cos(2 * ph)
        pb['root'].location = (0, 0, 0)
        rot('root', Yw, 3 * math.sin(ph))
        pb['root'].location = Vector((0, 0, bob))   # pose space of root ~ world (root is horizontal)
        rot('head', X, -3 * math.sin(2 * ph + 0.6))
        rot('mast', Yw, 2.5 * math.sin(ph + 0.5))
        rot('flag', Zw, 14 * math.sin(ph))
    else:
        L = LEAP[f]
        rot('root', X, -L['pitch'])
        for n in LEGS:
            if n[0] == 'F':
                rot(n + '_up', X, -L['reach']); rot(n + '_lo', X, 25)
            else:
                rot(n + '_up', X, -L['hind']); rot(n + '_lo', X, 10)
        rot('head', X, L['head'])
        rot('flag', Zw, -18)
        pb['root'].location = Vector((0, 0, 0))
    key(f)
    if f >= LEAP0:
        # root translation in world terms: up and toward the camera (-Y). Root bone points along +X (model x).
        L = LEAP[f]
        bm_ = arm.bones['root'].matrix_local.to_3x3().inverted()
        pb['root'].location = bm_ @ Vector((0, -L['fwd'], L['up']))
        pb['root'].keyframe_insert('location', frame=f)
    else:
        bm_ = arm.bones['root'].matrix_local.to_3x3().inverted()
        pb['root'].location = bm_ @ Vector((0, 0, 0.07 * math.cos(4 * math.pi * (f - 1) / (LEAP0 - 1))))
        pb['root'].keyframe_insert('location', frame=f)
for fc in getattr(act, 'fcurves', []):
    for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
try:
    for layer in act.layers:
        for strip in layer.strips:
            for cb in strip.channelbags:
                for fc in cb.fcurves:
                    for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
except Exception:
    pass
sc['water'] = WATER; sc['leap0'] = LEAP0; sc['part_ids'] = str(PART_ID)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('saved', OUT, 'objects', len(objs), PART_ID)
