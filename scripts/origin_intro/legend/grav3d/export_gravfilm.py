"""Gravriel for Lugia's 3D film (a/2/4/4): a game low-poly from the intro model, rigged on Quaternius' CC0 humanoid rig
(Universal Animation Library, standard), and his film motion from that library's actions (Arvind 2026-11-16: "he is
humanoid, there is much more to use for rigging and animation; remember he has a sword").
Blender -b title3d/grav/grav_v5.blend --python export_gravfilm.py -- UAL.glb OUT_PREFIX [TRIS=1100]
Writes OUT.json: polys (3 points each in Blender coordinates, bone per point, palette label), the palette, the DS bones'
bind matrices (the rig posed into the mesh) and their world matrices for every film frame (246).
How it is built:
  - colours: the intro paint is an argmax of 7 weights (attributes wa.rgba, wb.rgb) over 7 palette colours, read here
    per vertex; each low-poly face takes the majority label of its nearest high-poly vertices.
  - rig: the UAL rig (T-pose rest) is scaled to his shoulder height and its arms are aimed at his hands = the bind pose.
    Vertices follow one bone each (DS skinning is per vertex): below the hips the coat follows the hips (a floating ghost:
    no legs), the sword follows the right hand, the rest the nearest bone segment.
  - motion (film frames, 60 fps; the library is 30 fps): rise with arms out (Swim_Idle_Loop), the overhead slash
    (Sword_Attack) when the water ring spins, then the sword stance (Sword_Idle); 6-frame blends between them."""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector, Matrix, Quaternion
argv = sys.argv[sys.argv.index('--') + 1:]
UAL, OUT = argv[0], argv[1]; TRIS = int(argv[2]) if len(argv) > 2 else 1100
E = lambda k, d: float(os.environ.get(k, d))
NF = 246
# ---------------------------------------------------------------- palette labels per high-poly vertex
body = bpy.data.objects['Body']
dg = bpy.context.evaluated_depsgraph_get(); eb = body.evaluated_get(dg)
me = bpy.data.meshes.new_from_object(eb, preserve_all_data_layers=True, depsgraph=dg)   # as posed by the intro rig
wa = np.array([c.color[:] for c in me.attributes['wa'].data]); wb = np.array([c.color[:] for c in me.attributes['wb'].data])
W7 = np.column_stack([wa[:, 0], wa[:, 1], wa[:, 2], wa[:, 3], wb[:, 0], wb[:, 1], wb[:, 2]])
LAB = W7.argmax(1)
PAL_LIN = [(0.009, 0.014, 0.012), (0.065, 0.102, 0.034), (0.03, 0.102, 0.107), (0.479, 0.402, 0.254),
           (0.048, 0.061, 0.051), (0.456, 0.089, 0.042), (0.515, 0.539, 0.539)]
NAMES = ['coat', 'weed', 'skin', 'bone', 'hat', 'shell', 'mask']
s2 = lambda c: [int(round(255 * (12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055))) for x in c]
PAL = [s2(c) for c in PAL_LIN]
# v2 (Arvind: much of him came out grey, he is mostly kelp and seaweed): the coat is kelp in three greens (strands by
# position), the weed a lighter olive, the skin a paler sea-green, the blade steel so it shows against the white fall
PAL[0] = [34, 58, 34]; PAL[1] = [104, 136, 58]; PAL[2] = [78, 128, 120]; PAL[4] = [28, 34, 30]
NAMES += ['kelp2', 'kelp3', 'blade']; PAL += [[52, 86, 40], [76, 110, 46], [150, 164, 170]]
HP = np.array([tuple(body.matrix_world @ v.co) for v in me.vertices], float)
print('labels', {NAMES[k]: int((LAB == k).sum()) for k in range(7)})
# ---------------------------------------------------------------- low poly
lp = bpy.data.objects.new('LP', me.copy()); lp.matrix_world = body.matrix_world.copy(); bpy.context.collection.objects.link(lp)
bpy.ops.object.select_all(action='DESELECT'); lp.select_set(True); bpy.context.view_layer.objects.active = lp
rm = lp.modifiers.new('vox', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = E('VOX', 0.035); bpy.ops.object.modifier_apply(modifier=rm.name)   # clean manifold
print('voxel mesh', len(lp.data.polygons))
d = lp.modifiers.new('dec', 'DECIMATE'); d.decimate_type = 'COLLAPSE'; d.ratio = TRIS / max(1, len(me.polygons)); d.use_collapse_triangulate = True
bpy.ops.object.modifier_apply(modifier=d.name)
bm = bmesh.new(); bm.from_mesh(lp.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(lp.data); bm.free()
print('low poly tris', len(lp.data.polygons))
# extra parts: glowing eye slits and dark sockets (head)
EXTRA = []
for nm, lab in (('Socket0', 'socket'), ('Socket1', 'socket'), ('Slit0', 'eye'), ('Slit1', 'eye')):
    o = bpy.data.objects.get(nm)
    if o is None: continue
    eo = o.evaluated_get(dg); c = bpy.data.objects.new(nm + '_lp', bpy.data.meshes.new_from_object(eo, depsgraph=dg)); c.matrix_world = o.matrix_world.copy(); bpy.context.collection.objects.link(c)
    bpy.ops.object.select_all(action='DESELECT'); c.select_set(True); bpy.context.view_layer.objects.active = c
    dd = c.modifiers.new('dec', 'DECIMATE'); dd.ratio = 16 / max(1, len(c.data.polygons)); bpy.ops.object.modifier_apply(modifier=dd.name)
    bm = bmesh.new(); bm.from_mesh(c.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(c.data); bm.free()
    k_ = E('EYE_SCALE', 1.6) if lab == 'eye' else E('SOCKET_SCALE', 1.0)
    cen_ = sum((v.co for v in c.data.vertices), Vector()) / len(c.data.vertices)
    for v in c.data.vertices: v.co = cen_ + (v.co - cen_) * k_ + (Vector((0, -E('EYE_FWD', 0.04), 0)) if lab == 'eye' else Vector())   # glow in front of the socket
    EXTRA.append((c, lab))
# ---------------------------------------------------------------- rig: UAL, fitted and posed into the mesh
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=UAL)
new = [o for o in bpy.data.objects if o not in before]
rig = next(o for o in new if o.type == 'ARMATURE' and 'DEF-hips' in o.data.bones)
for o in new:
    if o.type == 'MESH': bpy.data.objects.remove(o)
rig.animation_data_create(); rig.animation_data.action = None
for pb in rig.pose.bones: pb.matrix_basis = Matrix()
bpy.context.view_layer.update()
def head(b): return rig.matrix_world @ rig.pose.bones[b].head
def tail(b): return rig.matrix_world @ rig.pose.bones[b].tail
zmin = float(HP[:, 2].min()); cx = float(np.median(HP[:, 0])); cy = float(np.median(HP[:, 1]))
SH_Z, HAND_R, HAND_L = E('SH_Z', 1.62), Vector((E('HRX', -1.87), cy, E('HRZ', -0.93))), Vector((E('HLX', 2.25), cy, E('HLZ', -0.48)))
foot = min(tail('DEF-toe.L')[2], head('DEF-foot.L')[2]); sh = head('DEF-upper_arm.L')[2]
k = float((SH_Z - zmin) / (sh - foot)); rig.scale = rig.scale * k; bpy.context.view_layer.update()
foot = min(tail('DEF-toe.L')[2], head('DEF-foot.L')[2]); hp_ = head('DEF-hips')
rig.location += Vector((cx - hp_[0], cy - hp_[1], zmin - foot)); bpy.context.view_layer.update()
print('rig scale %.3f' % k, 'hips', tuple(round(x, 2) for x in head('DEF-hips')), 'shoulder z %.2f' % head('DEF-upper_arm.L')[2])
def aim(bone, target_world, end_bone):
    pb = rig.pose.bones[bone]; a = head(bone); e = tail(end_bone)
    q = (e - a).rotation_difference(target_world - a)
    Mw = rig.matrix_world @ pb.matrix; R = q.to_matrix().to_4x4()
    T = Matrix.Translation(a) @ R @ Matrix.Translation(-a)
    pb.matrix = rig.matrix_world.inverted() @ T @ Mw; bpy.context.view_layer.update()
aim('DEF-upper_arm.R', HAND_R, 'DEF-forearm.R'); aim('DEF-upper_arm.L', HAND_L, 'DEF-forearm.L')
DSB = ['DEF-hips', 'DEF-spine.001', 'DEF-spine.002', 'DEF-spine.003', 'DEF-neck', 'DEF-head',
       'DEF-shoulder.L', 'DEF-upper_arm.L', 'DEF-forearm.L', 'DEF-hand.L', 'DEF-shoulder.R', 'DEF-upper_arm.R', 'DEF-forearm.R', 'DEF-hand.R']
def bone_mats():
    return {b: [list(r) for r in (rig.matrix_world @ rig.pose.bones[b].matrix)] for b in DSB}
BIND = bone_mats(); BIND_POSE = {pb.name: pb.matrix_basis.copy() for pb in rig.pose.bones}
seg = {b: (np.array(head(b)), np.array(tail(b))) for b in DSB}
HIP_Z = head('DEF-spine.001')[2]
def nearest_bone(p, allowed):
    best, bd = None, 1e9
    for b in allowed:
        a, c = seg[b]; ab = c - a; t = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-9), 0, 1); dd = np.linalg.norm(p - (a + t * ab))
        if dd < bd: best, bd = b, dd
    return best
UPPER = [b for b in DSB if b != 'DEF-hips']
def chain(b):
    return 'L' if b.endswith('.L') else ('R' if b.endswith('.R') else 'T')
def parent_of(b):
    p_ = rig.pose.bones[b].parent
    while p_ is not None and p_.name not in DSB: p_ = p_.parent
    return p_.name if p_ is not None else None
SWORD_X = E('SWORD_X', -1.25)
def assign(p, lab):
    if lab == 'bone' and p[0] < SWORD_X and p[2] < head('DEF-forearm.R')[2]: return 'DEF-hand.R'      # the cutlass
    if p[2] < HIP_Z and abs(p[0] - cx) < E('COAT_HALF', 1.35): return 'DEF-hips'                   # the coat below the waist
    return nearest_bone(p, UPPER if p[2] >= HIP_Z else DSB)
# ---------------------------------------------------------------- faces: points, bone per point, colour label
from mathutils.kdtree import KDTree
kd = KDTree(len(HP))
for i, v in enumerate(HP): kd.insert(Vector(v), i)
kd.balance()
polys = []
lpm = lp.matrix_world
for poly in lp.data.polygons:
    P = [np.array(lpm @ lp.data.vertices[i].co) for i in poly.vertices]
    c = sum((Vector(p) for p in P), Vector()) / 3
    votes = np.zeros(7)
    for p in P + [np.array(c)]:
        for (co, idx, dist) in kd.find_n(Vector(p), 6): votes[LAB[idx]] += 1
    lab = NAMES[int(votes.argmax())]
    if lab == 'coat':                                       # kelp strands: vertical bands with a little noise
        cc = np.array(c); band = math.sin(cc[0] * 5.1 + cc[1] * 3.7 + 0.6 * math.sin(cc[2] * 2.3)) + 0.35 * math.sin(cc[0] * 13.0 + cc[2] * 1.1)
        lab = 'coat' if band < -0.35 else ('kelp2' if band < 0.55 else 'kelp3')
    vb = [assign(p, lab) for p in P]
    if len(set(vb)) > 1 and not all(x == y or parent_of(x) == y or parent_of(y) == x for x in vb for y in vb):
        if len({chain(x) for x in vb}) > 1: continue   # sleeve tatter to coat (arm and body): dropped (v1 made it a loose shard)
        vb = [assign(np.array(c), lab)] * 3            # within the body (waist band, hips to chest): one bone, no gap
    if lab == 'bone' and all(b == 'DEF-hand.R' for b in vb) and c[0] < SWORD_X: lab = 'blade'
    polys.append(dict(p=[list(map(float, p)) for p in P], vb=vb, lab=lab))
for o, lab in EXTRA:
    for poly in o.data.polygons:
        P = [np.array(o.matrix_world @ o.data.vertices[i].co) for i in poly.vertices]
        polys.append(dict(p=[list(map(float, p)) for p in P], vb=['DEF-head'] * 3, lab=lab))
print('polys', len(polys), 'by bone', {b: sum(1 for p in polys if p['vb'][0] == b) for b in DSB})
# ---------------------------------------------------------------- motion
FPS = 2.0                                                # film frames per library frame (60 vs 30 fps)
S_SL = E('S_SLASH', 1.0)
SEQ = [('Swim_Idle_Loop', E('T_RISE', 100), 0.6), ('Sword_Attack', E('T_SLASH', 150), S_SL), ('Sword_Idle', E('T_STANCE', 150 + 36 * FPS / S_SL), 0.8)]
BLEND = E('BLEND', 6)
def basis_at(action, t):
    rig.animation_data.action = bpy.data.actions[action]
    a = bpy.data.actions[action]; n = a.frame_range[1] - a.frame_range[0]
    tt = a.frame_range[0] + (t % n if 'Loop' in action or action == 'Sword_Idle' else min(t, n))
    bpy.context.scene.frame_set(int(math.floor(tt)), subframe=tt - math.floor(tt))
    return {pb.name: (pb.matrix_basis.to_quaternion(), pb.matrix_basis.to_translation()) for pb in rig.pose.bones}
frames = {}
for f in range(NF):
    poses = []
    for k_, (act, start, speed) in enumerate(SEQ):
        end = SEQ[k_ + 1][1] if k_ + 1 < len(SEQ) else 1e9
        if f < start - BLEND and k_ > 0: continue
        if f >= end + BLEND: continue
        w = 1.0
        if k_ > 0 and f < start + BLEND: w = min(w, (f - (start - BLEND)) / (2 * BLEND))
        if k_ + 1 < len(SEQ) and f > end - BLEND: w = min(w, 1 - (f - (end - BLEND)) / (2 * BLEND))
        if w <= 0: continue
        poses.append((max(w, 1e-3), basis_at(act, max(0.0, f - start) / FPS * speed)))
    tot = sum(w for w, _ in poses); acc = None
    for w, ps in poses:
        if acc is None: acc = {k2: (q, t * (w / tot)) for k2, (q, t) in ps.items()}; aw = w / tot; continue
        nw = w / tot; aw2 = aw + nw
        acc = {k2: (acc[k2][0].slerp(ps[k2][0], nw / aw2), acc[k2][1] + ps[k2][1] * nw) for k2 in acc}; aw = aw2
    rig.animation_data.action = None
    for pb in rig.pose.bones:
        q, t = acc[pb.name]; pb.matrix_basis = Matrix.Translation(t) @ q.to_matrix().to_4x4()
    bpy.context.view_layer.update()
    frames[str(f)] = bone_mats()
parent = {b: (rig.pose.bones[b].parent.name if rig.pose.bones[b].parent else None) for b in DSB}
json.dump(dict(polys=polys, palette=PAL, names=NAMES, bones=DSB, parent=parent, bind=BIND, frames=frames,
               seq=SEQ, rig_scale=k), open(OUT + '.json', 'w'))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '.blend')
print('ok', OUT)
