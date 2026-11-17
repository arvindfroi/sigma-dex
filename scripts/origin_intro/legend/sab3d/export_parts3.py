"""Blender (headless): a game-ready low-poly Sabertann built part by part, like a hand-made DS model: big parts are
remeshed and decimated to their own budget; sails and the flag become small grids shrink-wrapped onto the cloth;
claws, tusks and the mast get a handful of triangles; small details (teeth, mouth, the hat's skull, gold trims, eyes)
are not geometry but are baked into the texture. One UV set packed by area, albedo + object normal baked from every
high-poly part. blender -b sab_v15.blend --python export_parts3.py -- OUT [TEXSIZE=128] [SOLID=900] [STERN_SHIFT=0.8]
v3 (Arvind 2026-11-15): the stern skull moved in against the hull (like the stern of Den sorte dame), claws as real little cones,
eyes as their own quads with a drawn eye (like Ho-Oh's hou_eye), per-vertex bones for stretching joints."""
import bpy, bmesh, sys, json, math, mathutils
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]; OUT = argv[0]; TS = int(argv[1]) if len(argv) > 1 else 128
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 4
rig = bpy.data.objects['Rig']; rig.data.pose_position = 'REST'
BUDGET = {'Body': 420, 'Hull': 180, 'Hat': 90, 'Stern': 60, 'Deck': 50, 'Mast': 24, 'Tusk': 24}
GRID = {'Sail': (3, 3), 'Flag': (2, 2)}                       # verts per side of each island's grid
CLAW = 6
src = [o for o in bpy.data.objects if o.type == 'MESH' and o.visible_get()]
dg = bpy.context.evaluated_depsgraph_get()
def posed_copy(o, suffix):
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    c = bpy.data.objects.new(o.name + suffix, me); c.matrix_world = o.matrix_world.copy(); sc.collection.objects.link(c)
    for g in o.vertex_groups: c.vertex_groups.new(name=g.name)
    for v in o.data.vertices:
        for ge in v.groups: c.vertex_groups[o.vertex_groups[ge.group].name].add([v.index], ge.weight, 'REPLACE')
    return c
def activate(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
def apply_tf(o): activate(o); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
def decimate_to(o, target):
    activate(o)
    for it in range(16):
        n = len(o.data.polygons)
        if n <= target * 1.05: break
        mod = o.modifiers.new('dec', 'DECIMATE'); mod.ratio = max(0.2, target / n); mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier='dec')
def transfer_weights(dst, srco):
    for g in srco.vertex_groups:
        if g.name not in dst.vertex_groups: dst.vertex_groups.new(name=g.name)
    activate(dst); dt = dst.modifiers.new('dt', 'DATA_TRANSFER'); dt.object = srco; dt.use_vert_data = True
    dt.data_types_verts = {'VGROUP_WEIGHTS'}; dt.vert_mapping = 'POLYINTERP_NEAREST'; dt.layers_vgroup_select_src = 'ALL'; dt.layers_vgroup_select_dst = 'NAME'
    bpy.ops.object.modifier_apply(modifier='dt')
def remesh_part(hp, target, div=140, octree=0):
    lp = hp.copy(); lp.data = hp.data.copy(); sc.collection.objects.link(lp); lp.name = hp.name + '_lp'
    for g in list(lp.vertex_groups): lp.vertex_groups.remove(g)
    activate(lp); rm = lp.modifiers.new('rm', 'REMESH')
    if octree:                                              # octree remesh closes the mesh (voxel alone falls apart on it), then a voxel
        rm.mode = 'SMOOTH'; rm.octree_depth = octree; rm.scale = 0.9; rm.use_remove_disconnected = True; rm.threshold = 0.3
        bpy.ops.object.modifier_apply(modifier='rm')             # pass makes it manifold so it decimates; small loose bits dropped
        rm = lp.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = max(hp.dimensions) / div
        bpy.ops.object.modifier_apply(modifier='rm')
        bm = bmesh.new(); bm.from_mesh(lp.data); bm.verts.ensure_lookup_table(); seen = set(); kill = []
        for v in bm.verts:
            if v.index in seen: continue
            st = [v]; comp = []; seen.add(v.index)
            while st:
                x = st.pop(); comp.append(x)
                for e in x.link_edges:
                    y = e.other_vert(x)
                    if y.index not in seen: seen.add(y.index); st.append(y)
            if len(comp) < 0.03 * len(bm.verts): kill += comp
        bmesh.ops.delete(bm, geom=kill, context='VERTS'); bm.to_mesh(lp.data); bm.free()
        decimate_to(lp, target); transfer_weights(lp, hp); return lp
    else: rm.mode = 'VOXEL'; rm.voxel_size = max(hp.dimensions) / div
    bpy.ops.object.modifier_apply(modifier='rm'); decimate_to(lp, target); transfer_weights(lp, hp); return lp
def grids(hp, nu, nv):
    """a small grid per loose island, in the island's best-fit plane, shrink-wrapped onto it"""
    bm = bmesh.new(); bm.from_mesh(hp.data); bm.verts.ensure_lookup_table(); seen = set(); islands = []
    for v in bm.verts:
        if v.index in seen: continue
        st = [v]; isl = []; seen.add(v.index)
        while st:
            x = st.pop(); isl.append(x.co.copy())
            for e in x.link_edges:
                y = e.other_vert(x)
                if y.index not in seen: seen.add(y.index); st.append(y)
        if len(isl) > 20: islands.append(isl)
    bm.free(); out = bmesh.new()
    import numpy as np
    for isl in islands:
        P = np.array([tuple(p) for p in isl]); c = P.mean(0); u, s, vt = np.linalg.svd(P - c)
        a, b = vt[0], vt[1]; pa = (P - c) @ a; pb = (P - c) @ b
        vs = [[out.verts.new(Vector(c + a * (pa.min() + (pa.max() - pa.min()) * i / (nu - 1)) + b * (pb.min() + (pb.max() - pb.min()) * j / (nv - 1))))
               for j in range(nv)] for i in range(nu)]
        for i in range(nu - 1):
            for j in range(nv - 1): out.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
    me = bpy.data.meshes.new(hp.name + '_grid'); out.to_mesh(me); out.free()
    lp = bpy.data.objects.new(hp.name + '_lp', me); sc.collection.objects.link(lp)
    activate(lp); sw = lp.modifiers.new('sw', 'SHRINKWRAP'); sw.target = hp; sw.wrap_method = 'NEAREST_SURFACEPOINT'
    bpy.ops.object.modifier_apply(modifier='sw'); transfer_weights(lp, hp); return lp
HP = []; LP = []; SOLID = []
SOLIDS = ('Body', 'Hull', 'Deck', 'Hat', 'Stern', 'Tusk', 'HatEdge', 'Rail')
SHIFT = float(argv[3]) if len(argv) > 3 else 0.8; LIFT = float(argv[4]) if len(argv) > 4 else 0.7; CLAWS = []; EYES = []
for o in src:
    hp = posed_copy(o, '_hp'); apply_tf(hp)
    vg = [g.name for g in o.vertex_groups]
    if vg == ['stern'] or o.name.split('.')[0] in ('Stern', 'SkullHead', 'SkullMouth', 'SkullMaxilla', 'SkullJaw', 'SkullCheek1', 'SkullCheek-1') or (vg and vg[0] == 'stern'):
        for v in hp.data.vertices: v.co.y -= SHIFT; v.co.z += LIFT   # the stern skull in against the hull and up by its top edge (concept)
    if o.name.startswith('Claw'): CLAWS.append(hp)
    if o.name.startswith('Eye1'): EYES.append(hp)
    HP.append(hp)
    base = o.name.split('.')[0]
    SOLID.append(hp)                   # every part goes into the voxel mesh (without the sails the remesh falls apart)
    if base in GRID:
        g = grids(hp, *GRID[base]); a = g.data.attributes.new('grp', 'INT', 'FACE')
        for i in range(len(g.data.polygons)): a.data[i].value = 2
        LP.append(g)
# the solid parts only close up together (the body is open where the hull sits): one voxel mesh, one budget
bpy.ops.object.select_all(action='DESELECT')
cps = []
for h in SOLID:
    c = h.copy(); c.data = h.data.copy(); sc.collection.objects.link(c); c.select_set(True); cps.append(c)
bpy.context.view_layer.objects.active = cps[0]; bpy.ops.object.join(); U = bpy.context.view_layer.objects.active; U.name = 'SolidSrc'
solid = remesh_part(U, int(argv[2]) if len(argv) > 2 else 900, 140, octree=7)
# drop the voxel faces that belong to the cloth (sails, flag): the grids replace them
from mathutils.bvhtree import BVHTree
cloth = [h for h in HP if h.name.split('.')[0].replace('_hp', '') in GRID]
other = [h for h in HP if h not in cloth]
def tree(objs):
    bm = bmesh.new()
    for o in objs:
        t = bmesh.new(); t.from_mesh(o.data); t.transform(o.matrix_world); tmp = bpy.data.meshes.new('t'); t.to_mesh(tmp); t.free(); bm.from_mesh(tmp)
    return BVHTree.FromBMesh(bm)
tc, to = tree(cloth), tree(other)
bm = bmesh.new(); bm.from_mesh(solid.data); kill = []
for f in bm.faces:
    c = solid.matrix_world @ f.calc_center_median()
    a = tc.find_nearest(c); b = to.find_nearest(c)
    if a[0] is not None and (b[0] is None or a[3] < b[3] * 0.8): kill.append(f)
bmesh.ops.delete(bm, geom=kill, context='FACES'); bm.to_mesh(solid.data); bm.free(); print('CLOTH faces removed', len(kill))
LP.append(solid); U.hide_render = True
import numpy as np
def tagged(name, verts, faces, grpv, uvs, bone, role):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    a = me.attributes.new('grp', 'INT', 'FACE'); r = me.attributes.new('role', 'INT', 'FACE')
    for i in range(len(faces)): a.data[i].value = grpv; r.data[i].value = role
    if uvs is not None:
        ca = me.attributes.new('euv', 'FLOAT2', 'CORNER')
        for p in me.polygons:
            for li, vi in zip(p.loop_indices, p.vertices): ca.data[li].vector = uvs[vi]
    vg = ob.vertex_groups.new(name=bone); vg.add(list(range(len(verts))), 1.0, 'REPLACE'); return ob
for c in CLAWS:                                             # a 4-sided cone from the claw's root to its tip
    P = np.array([v.co[:] for v in c.data.vertices]); cen = P.mean(0); u, sv, vt = np.linalg.svd(P - cen); ax = vt[0]
    pr = (P - cen) @ ax; tip = P[pr.argmax()] if abs(pr.max()) > abs(pr.min()) else P[pr.argmin()]
    root = cen - (tip - cen) * 0.6; d = tip - root; d /= np.linalg.norm(d)
    s1 = np.cross(d, [0, 0, 1.0]); s1 = s1 / (np.linalg.norm(s1) + 1e-9) if np.linalg.norm(s1) > 1e-6 else np.array([1.0, 0, 0]); s2 = np.cross(d, s1)
    rad = sv[1] / np.sqrt(len(P)) * 1.6
    base = [root + rad * (np.cos(k * np.pi / 2) * s1 + np.sin(k * np.pi / 2) * s2) for k in range(4)]
    bone = c.vertex_groups[0].name if c.vertex_groups else 'spine'
    LP.append(tagged(c.name + '_cone', base + [tip], [(k, (k + 1) % 4, 4) for k in range(4)], 0, [(0.2, 0.2)] * 4 + [(0.8, 0.8)], bone, 1))
EQ = {}
for e in EYES:                                              # a quad in front of each eye, facing forward and a little out
    P = np.array([v.co[:] for v in e.data.vertices]); mn, mx = P.min(0), P.max(0); c = (mn + mx) / 2
    side = 1.0 if c[0] > 0 else -1.0; n = np.array([0.35 * side, -1.0, -0.15]); n /= np.linalg.norm(n)
    t1 = np.cross([0, 0, 1.0], n); t1 /= np.linalg.norm(t1); t2 = np.cross(n, t1)
    w, h = (mx[0] - mn[0]) * 0.9, (mx[2] - mn[2]) * 0.7; ctr = np.array([c[0], mn[1] - 0.04, c[2] - 0.02])
    # sit just outside the low-poly face: cast from in front back toward the eye, keep the first hit
    from mathutils import Vector as _V
    sbm = bmesh.new(); sbm.from_mesh(solid.data); sbm.transform(solid.matrix_world); stree = BVHTree.FromBMesh(sbm); sbm.free()
    hit = stree.ray_cast(_V(tuple(c + n * 1.5)), _V(tuple(-n)), 3.0)
    if hit[0] is not None: ctr = np.array(hit[0][:]) + n * 0.10 - np.array([0, 0, 0.05])
    quad = [ctr - w * t1 - h * t2, ctr + w * t1 - h * t2, ctr + w * t1 + h * t2, ctr - w * t1 + h * t2]
    EQ[2 if side > 0 else 3] = (quad[0], quad[1] - quad[0], quad[3] - quad[0])
    LP.append(tagged(e.name + '_quad', quad, [(0, 1, 2), (0, 2, 3)], 1, [(0, 0), (1, 0), (1, 1), (0, 1)], 'head', 2 if side > 0 else 3))
for o in src: o.hide_render = True; o.hide_set(True)
for l in LP: print('LP', l.name, len(l.data.polygons))
# join the low-poly, triangulate, UV by area, bake from all high-poly parts
bpy.ops.object.select_all(action='DESELECT')
for l in LP: l.select_set(True)
bpy.context.view_layer.objects.active = LP[0]; bpy.ops.object.join(); L = bpy.context.view_layer.objects.active; L.name = 'LP'
bm = bmesh.new(); bm.from_mesh(L.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(L.data); bm.free()
# texture groups, like Ho-Oh's several textures: 0 body/hull/legs (A, 128x128), 1 head + hat (B, 64x64), 2 sails + flag (C, 32x64)
SIZES = {0: (TS, TS), 1: (64, 64), 2: (32, 64)}
me = L.data; names = [g.name for g in L.vertex_groups]
ga = me.attributes.get('grp') or me.attributes.new('grp', 'INT', 'FACE')
ra = me.attributes.get('role')
role = [ra.data[p.index].value if ra else 0 for p in me.polygons]
for p in me.polygons:
    if ga.data[p.index].value == 2 or role[p.index]: continue
    w = {}
    for i in p.vertices:
        for ge in me.vertices[i].groups: w[ge.group] = w.get(ge.group, 0) + ge.weight
    bone = names[max(w, key=w.get)] if w else 'spine'
    ga.data[p.index].value = 1 if bone in ('head', 'jaw') else 0
grp = [ga.data[p.index].value for p in me.polygons]
activate(L); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.5 / TS, area_weight=1.0)
bpy.ops.object.mode_set(mode='OBJECT')
# per group, our own shelf packing (uv.pack_islands does nothing from a script): islands = faces joined by edges whose UVs
# match on both sides; scaled together as large as they fit, rows of islands sorted by height
import numpy as _np
uvl = me.uv_layers.active.data
def key(li): u = uvl[li].uv; return (round(u[0], 5), round(u[1], 5))
edge_faces = {}
for p in me.polygons:
    for k in range(len(p.vertices)):
        v1, v2 = p.vertices[k], p.vertices[(k + 1) % len(p.vertices)]
        l1, l2 = p.loop_indices[k], p.loop_indices[(k + 1) % len(p.vertices)]
        e = (min(v1, v2), max(v1, v2)); uvp = tuple(sorted([(v1, key(l1)), (v2, key(l2))]))
        edge_faces.setdefault((e, uvp), []).append(p.index)
par = list(range(len(me.polygons)))
def find(x):
    while par[x] != x: par[x] = par[par[x]]; x = par[x]
    return x
for fs in edge_faces.values():
    for f in fs[1:]:
        if grp[f] == grp[fs[0]]: par[find(f)] = find(fs[0])
isl = {}
for p in me.polygons: isl.setdefault(find(p.index), []).append(p.index)
for g in (0, 1, 2):
    w, h = SIZES[g]; asp = w / h; I = []
    for r, fs in isl.items():
        if grp[fs[0]] != g or role[fs[0]]: continue
        lis = [li for f in fs for li in me.polygons[f].loop_indices]
        uv = _np.array([uvl[li].uv[:] for li in lis]); mn, mx = uv.min(0), uv.max(0)
        I.append((lis, mn, _np.maximum(mx - mn, 1e-4)))
    I.sort(key=lambda t: -t[2][1]); pad = 1.0 / min(w, h)
    V0 = {0: 8 / TS, 1: 12 / 64, 2: 0.0}[g]                 # reserved bottom strip (claw patch / eye drawing)
    def place(sc):
        x = y = 0.0; rowh = 0.0; pos = []
        for lis, mn, sz in I:
            sw, sh = sz[0] * sc / asp, sz[1] * sc
            if x + sw > 1.0: x = 0.0; y += rowh + pad; rowh = 0.0
            pos.append((x, y)); x += sw + pad; rowh = max(rowh, sh)
        return pos, y + rowh
    lo, hi = 0.01, 50.0
    for _ in range(40):
        mid = (lo + hi) / 2; _, top = place(mid)
        if top <= 1.0 - V0: lo = mid
        else: hi = mid
    pos, _ = place(lo)
    for (lis, mn, sz), (x, y) in zip(I, pos):
        for li in lis:
            u = uvl[li].uv; uvl[li].uv = (x + (u[0] - mn[0]) * lo / asp, V0 + y + (u[1] - mn[1]) * lo)
    print('PACK', g, 'islands', len(I), 'scale', round(lo, 3))
ea = me.attributes.get('euv')
for p in me.polygons:                                      # fixed UVs: claws on the ivory patch, eyes on the drawn eye
    for li in p.loop_indices:
        e = ea.data[li].vector if ea else (0, 0)
        if role[p.index] == 1: uvl[li].uv = (1 / TS + e[0] * 6 / TS, 1 / TS + e[1] * 6 / TS)
        elif role[p.index] in (2, 3):                         # from the quad's own axes (corner attributes do not survive the join)
            o_, au, av = EQ[role[p.index]]; q = np.array(me.vertices[me.loops[li].vertex_index].co[:]) - o_
            su = float(q @ au / (au @ au)); sv_ = float(q @ av / (av @ av))
            if role[p.index] == 3: su = 1 - su
            uvl[li].uv = (min(max(su, 0), 1) * 16 / 64, min(max(sv_, 0), 1) * 12 / 64)
L.data.materials.clear(); IM = {}
for g in (0, 1, 2):
    w, h = SIZES[g]
    mat = bpy.data.materials.new(f'grp{g}'); mat.use_nodes = True; nt = mat.node_tree
    for key in ('albedo', 'normal'):
        im = bpy.data.images.new(f'{key}{g}', w * 4, h * 4, float_buffer=(key == 'normal')); IM[(key, g)] = im
        tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = im; tn.name = key
    L.data.materials.append(mat)
for p in me.polygons: p.material_index = grp[p.index]
bpy.ops.object.select_all(action='DESELECT')
for h in HP: h.select_set(True)
L.select_set(True); bpy.context.view_layer.objects.active = L
size = max(max(h.dimensions) for h in HP)
sc.render.bake.use_selected_to_active = True; sc.render.bake.cage_extrusion = size / 50; sc.render.bake.margin = 4
for key in ('albedo', 'normal'):
    for g in (0, 1, 2): L.data.materials[g].node_tree.nodes.active = L.data.materials[g].node_tree.nodes[key]
    if key == 'albedo': bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
    else: sc.render.bake.normal_space = 'OBJECT'; bpy.ops.object.bake(type='NORMAL')
for (key, g), im in IM.items(): im.filepath_raw = f'{OUT}_{key}{g}.png'; im.file_format = 'PNG'; im.save()
me = L.data; uv = me.uv_layers.active.data; names = [g.name for g in L.vertex_groups]; polys = []
for p in me.polygons:
    w = {}
    for i in p.vertices:
        for ge in me.vertices[i].groups: w[ge.group] = w.get(ge.group, 0) + ge.weight
    polys.append(dict(p=[list(me.vertices[i].co) for i in p.vertices], uv=[list(uv[li].uv) for li in p.loop_indices], b=names[max(w, key=w.get)] if w else 'spine', g=grp[p.index], r=role[p.index],
                      vb=[(names[max(((ge.group, ge.weight) for ge in me.vertices[i].groups), key=lambda t: t[1])[0]] if len(me.vertices[i].groups) else 'spine') for i in p.vertices]))
json.dump(dict(polys=polys), open(OUT + '.json', 'w')); print('EXPORTED', len(polys))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '_lp.blend')
