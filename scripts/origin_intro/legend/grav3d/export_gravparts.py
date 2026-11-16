"""Gravriel for Lugia's film, v6 (Arvind: "Pokémon quality"; he saw many holes in the model): the low-poly is built
from separate CLOSED parts instead of one blob (the intro mesh has the sleeves grown into the coat, so moving the arms
tore or dropped faces). Parts from the intro model's paint and the bind-pose bones: coat, beard, head, hat, left arm,
right arm (sleeve + hand), cutlass. Each part is voxel-remeshed on its own (closed) and decimated to its budget.
Skinning: every vertex has its nearest bone and the next one with a weight (`vw`), so rig_lugia.py can bend the
elbows, shoulders, neck and waist with halfway helper bones like Sabertann's.
Motion (Arvind: out of the portal like Lugia and float up; it need not be about the sword; he must be clearly
visible): Swim_Idle_Loop (floating, arms out) while he comes out, then Spell_Simple_Idle_Loop (left hand reaching
toward the camera, cutlass low in the right) like his artwork.
Blender -b title3d/grav/grav_v5.blend --python export_gravparts.py -- UAL.glb OUT_PREFIX"""
import bpy
import bmesh, sys, os, json, math
from mathutils.bvhtree import BVHTree
import numpy as np
from mathutils import Vector, Matrix, Quaternion
argv = sys.argv[sys.argv.index('--') + 1:]
UAL, OUT = argv[0], argv[1]
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
# ---------------------------------------------------------------- parts per high-poly vertex (bind pose)
NB = {b: i for i, b in enumerate(DSB)}
def seg_dist(P_, b):
    a, c = seg[b]; ab = c - a; t = np.clip(((P_ - a) @ ab) / max(ab @ ab, 1e-9), 0, 1); return np.linalg.norm(P_ - (a + t[:, None] * ab), axis=1)
DB = np.stack([seg_dist(HP, b) for b in DSB], 1)                      # distance of every vertex to every bone
ARM = {'L': [NB[b] for b in DSB if b.endswith('.L') and 'shoulder' not in b], 'R': [NB[b] for b in DSB if b.endswith('.R') and 'shoulder' not in b]}
SH_X = {s: abs(head('DEF-upper_arm.' + s)[0] - cx) for s in 'LR'}; NECK_Z = head('DEF-neck')[2]; CHEST_Z = head('DEF-spine.003')[2]
PART = np.array(['coat'] * len(HP), dtype=object)
for s in 'LR':
    side = (HP[:, 0] - cx > 0) if s == 'L' else (HP[:, 0] - cx < 0)
    near = DB[:, ARM[s]].min(1) < E('ARM_R', 0.42) * k / 3.236
    out_ = np.abs(HP[:, 0] - cx) > SH_X[s] * E('ARM_X', 0.9)
    PART[side & near & out_] = 'arm' + s
PART[(LAB == 3) & (HP[:, 0] < SWORD_X) & (HP[:, 2] < head('DEF-forearm.R')[2])] = 'sword'
PART[(LAB == 4) & (HP[:, 2] > NECK_Z)] = 'hat'
headr = E('HEAD_R', 0.55) * k / 3.236
PART[(PART == 'coat') & (np.linalg.norm(HP - np.array(head('DEF-head')), axis=1) < headr * 1.6) & (HP[:, 2] > NECK_Z - 0.1) & (LAB != 1)] = 'head'
PART[(PART == 'coat') & (LAB == 1) & (HP[:, 2] > CHEST_Z - E('BEARD_DROP', 0.9)) & (np.abs(HP[:, 0] - cx) < E('BEARD_HALF', 0.75))] = 'beard'
# v7 (Arvind on v6: "there are holes and it does not look like Gravriel"): WHOLE=1 makes everything but the cutlass ONE
# closed body. A coarse voxel (VOXW) fuses the kelp tatters into one skirt with a wavy hem, a smoothing pass rounds it and
# it is reduced as one piece, so there are no seams or gaps between parts; the look comes from the artwork painted on
# (tex_atlas.py), the way the Pokémon film models carry their detail in the texture
WHOLE = os.environ.get('WHOLE', '1') == '1'
if WHOLE: PART[PART != 'sword'] = 'body'
print('parts', {p: int((PART == p).sum()) for p in set(PART)})
BUDGET = {'coat': int(E('B_COAT', 520)), 'beard': int(E('B_BEARD', 130)), 'head': int(E('B_HEAD', 110)), 'hat': int(E('B_HAT', 70)),
          'armL': int(E('B_ARM', 110)), 'armR': int(E('B_ARM', 110)), 'sword': int(E('B_SWORD', 30))}   # polygons (mostly quads); Lugia is 1128
TRIS = {'coat': int(E('T_COAT', 900)), 'beard': int(E('T_BEARD', 220)), 'head': int(E('T_HEAD', 220)), 'hat': int(E('T_HAT', 100)),
        'armL': int(E('T_ARM', 150)), 'armR': int(E('T_ARM', 150)), 'sword': int(E('T_SWORD', 40))}   # triangles before quad pairing
TRIS['body'] = int(E('T_BODY', 1300))
VOX = {'body': E('VOXW', 0.08), 'coat': E('VOX', 0.035), 'beard': 0.03, 'head': 0.025, 'hat': 0.03, 'armL': 0.03, 'armR': 0.03, 'sword': 0.012}
ALLOWED = {'body': list(DSB), 'coat': [b for b in DSB if not ('arm' in b or 'hand' in b)], 'beard': ['DEF-head', 'DEF-neck', 'DEF-spine.003'],
           'head': ['DEF-head'], 'hat': ['DEF-head'], 'sword': ['DEF-hand.R'],
           'armL': ['DEF-shoulder.L', 'DEF-upper_arm.L', 'DEF-forearm.L', 'DEF-hand.L'], 'armR': ['DEF-shoulder.R', 'DEF-upper_arm.R', 'DEF-forearm.R', 'DEF-hand.R']}
fverts = [list(p.vertices) for p in me.polygons]
LP = {}
for part in (['body', 'sword'] if WHOLE else list(BUDGET)):
    keep = [f for f in fverts if sum(PART[i] == part for i in f) * 2 > len(f)]
    if not keep: continue
    used = sorted({i for f in keep for i in f}); rem = {i: j for j, i in enumerate(used)}
    m_ = bpy.data.meshes.new('P_' + part); m_.from_pydata([tuple(HP[i]) for i in used], [], [[rem[i] for i in f] for f in keep]); m_.update()
    o = bpy.data.objects.new('P_' + part, m_); bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    # closed by a fine voxel remesh, decimated to 2 x budget triangles, then paired into quads like the Pokémon models
    # (a quad is one DS polygon). Coarse voxels straight to the budget broke the thin parts into fragments (v6a).
    if os.environ.get('KEEP_STAGES') == '1':
        k_ = o.copy(); k_.data = o.data.copy(); k_.name = 'K_' + part; bpy.context.collection.objects.link(k_); k_.hide_render = True
    # v6 (Arvind 2026-11-16: "lots of holes", "same quality as Pokémon"): each part is made a closed solid first. The cut
    # loops are capped, the surface gets a thin solidify (the sculpt has open sheets and folds that made the voxel
    # remesher leak into 82 crumbs), then a voxel remesh, cavities inside the solid are dropped, the surface is cleaned to a
    # proper manifold, decimated to its triangle budget (keeps the tatters and beard strands) and flat pairs become quads.
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    bm.to_mesh(o.data); bm.free()
    sm = o.modifiers.new('sol', 'SOLIDIFY'); sm.thickness = VOX[part] * E('SOLID', 1.5); sm.offset = 0; bpy.ops.object.modifier_apply(modifier=sm.name)
    rm = o.modifiers.new('vox', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = VOX[part]; bpy.ops.object.modifier_apply(modifier=rm.name)
    nf = len(o.data.polygons); vs = VOX[part]
    def island_list(bm_):
        seen = set(); out_ = []
        for f in bm_.faces:
            if f.index in seen: continue
            st = [f]; comp = []; seen.add(f.index)
            while st:
                g = st.pop(); comp.append(g)
                for e in g.edges:
                    for h in e.link_faces:
                        if h.index not in seen: seen.add(h.index); st.append(h)
            out_.append(comp)
        return sorted(out_, key=len, reverse=True)
    bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table()
    tree = BVHTree.FromBMesh(bm); drop = []
    for comp in island_list(bm)[1:]:                         # an island inside the solid (ray parity) is a cavity
        f0 = comp[0]; p0 = f0.calc_center_median() + f0.normal * 1e-3; ins = 0
        for d in (Vector((0.31, 0.17, 0.93)), Vector((-0.7, 0.4, -0.2)), Vector((0.1, -0.95, 0.3))):
            d = d.normalized(); n_ = 0; q = p0.copy()
            while n_ <= 50:
                hit = tree.ray_cast(q, d, 100)
                if hit[0] is None: break
                n_ += 1; q = hit[0] + d * 1e-4
            ins += n_ % 2
        if ins >= 2: drop += comp
    if drop: bmesh.ops.delete(bm, geom=drop, context='FACES')
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=E('MERGE', 3e-4))
    bmesh.ops.dissolve_degenerate(bm, dist=E('MERGE', 3e-4), edges=bm.edges[:])
    for _ in range(4):
        bad = [e for e in bm.edges if len(e.link_faces) > 2 or len(e.link_faces) == 0]
        badv = [v for v in bm.verts if not v.is_manifold and not v.is_boundary]
        if not bad and not badv: break
        fs = list({f for e in bad for f in e.link_faces} | {f for v in badv for f in v.link_faces})
        bmesh.ops.delete(bm, geom=fs, context='FACES')
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    crumbs = [f for c in island_list(bm) if len(c) < E('CRUMB', 40) for f in c]
    if crumbs: bmesh.ops.delete(bm, geom=crumbs, context='FACES')
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(o.data); bm.free(); o.data.update()
    if os.environ.get('KEEP_STAGES') == '1':
        v_ = o.copy(); v_.data = o.data.copy(); v_.name = 'V_' + part; bpy.context.collection.objects.link(v_); v_.hide_render = True
    if part == 'body':                                       # round the voxel steps before reducing
        sm2 = o.modifiers.new('sm', 'SMOOTH'); sm2.factor = 0.5; sm2.iterations = int(E('SMI', 4)); bpy.ops.object.modifier_apply(modifier=sm2.name)
    dm = o.modifiers.new('dec', 'DECIMATE'); dm.decimate_type = 'COLLAPSE'; dm.ratio = min(1.0, TRIS[part] / max(1, len(o.data.polygons))); dm.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=dm.name)
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.join_triangles(bm, faces=bm.faces[:], cmp_seam=False, cmp_sharp=False, cmp_uvs=False, cmp_vcols=False, cmp_materials=False,
                             angle_face_threshold=math.radians(E('QUAD_FACE', 30)), angle_shape_threshold=math.radians(E('QUAD_SHAPE', 80)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(o.data); bm.free(); o.data.update()
    LP[part] = o; print('part', part, 'faces', len(keep), '-> voxel %.3f' % vs, '->', len(o.data.polygons), 'polygons', sum(len(p_.vertices) == 4 for p_ in o.data.polygons), 'quads')
# ---------------------------------------------------------------- faces: points, bones (two per point), colour label
from mathutils.kdtree import KDTree
kd = KDTree(len(HP))
for i, v in enumerate(HP): kd.insert(Vector(v), i)
kd.balance()
def two_bones(p, allowed):
    ds = sorted((float(seg_dist(np.array([p]), b)[0]), b) for b in allowed)
    if len(ds) < 2: return ds[0][1], None
    (d1, b1), (d2, b2) = ds[0], ds[1]; w = max(0.0, 0.5 - (d2 - d1) / E('BLEND_W', 0.35) * 0.5)
    return b1, ([b2, round(w, 3)] if w > 0.05 else None)
polys = []
for part, o in LP.items():
    for poly in o.data.polygons:
        P = [np.array(o.matrix_world @ o.data.vertices[i].co) for i in poly.vertices]
        c = sum((Vector(p) for p in P), Vector()) / len(P)
        votes = np.zeros(7)
        for p in P + [np.array(c)]:
            for (co, idx, dist) in kd.find_n(Vector(p), 8):
                if PART[idx] == part or part in ('head', 'hat'): votes[LAB[idx]] += 1
        lab = NAMES[int(votes.argmax())]
        if part == 'sword': lab = 'blade'
        if lab == 'coat':                                       # kelp strands: vertical bands with a little noise
            cc = np.array(c); band = math.sin(cc[0] * 5.1 + cc[1] * 3.7 + 0.6 * math.sin(cc[2] * 2.3)) + 0.35 * math.sin(cc[0] * 13.0 + cc[2] * 1.1)
            lab = 'coat' if band < -0.35 else ('kelp2' if band < 0.55 else 'kelp3')
        al = ALLOWED[part]
        if part == 'coat':
            al = ['DEF-hips'] if c[2] < HIP_Z - E('COAT_FREE', 0.3) else al     # the long coat hangs from the hips (a ghost: no legs)
        if part == 'body' and c[2] < HIP_Z - E('COAT_FREE', 0.3):            # below the waist: the hips, or the hands beside it
            al = ['DEF-hips', 'DEF-forearm.L', 'DEF-hand.L', 'DEF-forearm.R', 'DEF-hand.R']
        bw = [two_bones(p, al) for p in P]
        polys.append(dict(p=[list(map(float, p)) for p in P], vb=[b for b, _ in bw], vw=[w for _, w in bw], lab=lab, part=part))
print('polys', len(polys), 'by part', {p: sum(1 for q in polys if q['part'] == p) for p in LP})
# ---------------------------------------------------------------- motion
FPS = 2.0                                                # film frames per library frame (60 vs 30 fps)
# v6b (in game the Spell idle turned him side-on to the camera): he settles into the standing idle, arms down with the
# cutlass in his right hand, like the artwork
SEQ = [('Swim_Idle_Loop', E('T_RISE', 100), 0.5), (os.environ.get('ACT2', 'Idle_Loop'), E('T_REACH', 178), float(os.environ.get('ACT2_SPEED', 0.6)))]
# v7: only part of each library motion, on top of the artwork pose (the bind pose), so the one-piece body is not torn and
# the movement stays calm: a slow float with the arms lifting a little, then a quiet idle
AMP = [E('AMP1', 0.35), E('AMP2', 0.6)]
def scaled(ps, amp):
    out = {}
    for nm, (q, t) in ps.items():
        b0 = BIND_POSE[nm]; out[nm] = (b0.to_quaternion().slerp(q, amp), b0.to_translation().lerp(t, amp))
    return out
BLEND = E('BLEND', 12)
def basis_at(action, t):
    rig.animation_data.action = bpy.data.actions[action]
    a = bpy.data.actions[action]; n = a.frame_range[1] - a.frame_range[0]
    tt = a.frame_range[0] + (t % n if 'Loop' in action else min(t, n))
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
        poses.append((max(w, 1e-3), scaled(basis_at(act, max(0.0, f - start) / FPS * speed), AMP[min(k_, len(AMP) - 1)])))
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
# the cutlass hangs ~2 units below the right wrist: the library's wrist turns would swing it off his hand, so the right
# hand is rigid with the forearm (also lock_wrist.py for older exports)
if os.environ.get('WRIST_LOCK', '1') == '1':
    _rel = np.linalg.inv(np.array(BIND['DEF-forearm.R'])) @ np.array(BIND['DEF-hand.R'])
    for _m in frames.values(): _m['DEF-hand.R'] = (np.array(_m['DEF-forearm.R']) @ _rel).tolist()
parent = {b: (rig.pose.bones[b].parent.name if rig.pose.bones[b].parent else None) for b in DSB}
json.dump(dict(polys=polys, palette=PAL, names=NAMES, bones=DSB, parent=parent, bind=BIND, frames=frames,
               seq=SEQ, rig_scale=k), open(OUT + '.json', 'w'))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '.blend')
print('ok', OUT)
