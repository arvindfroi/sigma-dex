"""Blender (headless): a game-ready low-poly Sabertann built part by part, like a hand-made DS model: big parts are
remeshed and decimated to their own budget; sails and the flag become small grids shrink-wrapped onto the cloth;
claws, tusks and the mast get a handful of triangles; small details (teeth, mouth, the hat's skull, gold trims, eyes)
are not geometry but are baked into the texture. One UV set packed by area, albedo + object normal baked from every
high-poly part. blender -b sab_v15.blend --python export_parts.py -- OUT [TEXSIZE=128]"""
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
def remesh_part(hp, target, div=140):
    lp = hp.copy(); lp.data = hp.data.copy(); sc.collection.objects.link(lp); lp.name = hp.name + '_lp'
    for g in list(lp.vertex_groups): lp.vertex_groups.remove(g)
    activate(lp); rm = lp.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = max(hp.dimensions) / div
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
for o in src:
    hp = posed_copy(o, '_hp'); apply_tf(hp); HP.append(hp)
    base = o.name.split('.')[0]
    SOLID.append(hp)                   # every part goes into the voxel mesh (without the sails the remesh falls apart)
    if base in GRID: LP.append(grids(hp, *GRID[base]))
# the solid parts only close up together (the body is open where the hull sits): one voxel mesh, one budget
bpy.ops.object.select_all(action='DESELECT')
cps = []
for h in SOLID:
    c = h.copy(); c.data = h.data.copy(); sc.collection.objects.link(c); c.select_set(True); cps.append(c)
bpy.context.view_layer.objects.active = cps[0]; bpy.ops.object.join(); U = bpy.context.view_layer.objects.active; U.name = 'SolidSrc'
solid = remesh_part(U, int(argv[2]) if len(argv) > 2 else 900, 160)
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
for o in src: o.hide_render = True; o.hide_set(True)
for l in LP: print('LP', l.name, len(l.data.polygons))
# join the low-poly, triangulate, UV by area, bake from all high-poly parts
bpy.ops.object.select_all(action='DESELECT')
for l in LP: l.select_set(True)
bpy.context.view_layer.objects.active = LP[0]; bpy.ops.object.join(); L = bpy.context.view_layer.objects.active; L.name = 'LP'
bm = bmesh.new(); bm.from_mesh(L.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(L.data); bm.free()
activate(L); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(70), island_margin=1.0 / TS, area_weight=1.0)
bpy.ops.uv.pack_islands(rotate=True, margin=1.0 / TS)
bpy.ops.object.mode_set(mode='OBJECT')
imgs = {k: bpy.data.images.new(k, TS * 4, TS * 4, float_buffer=(k == 'normal')) for k in ('albedo', 'normal')}
mat = bpy.data.materials.new('lpmat'); mat.use_nodes = True; nt = mat.node_tree; tn = nt.nodes.new('ShaderNodeTexImage'); nt.nodes.active = tn
L.data.materials.clear(); L.data.materials.append(mat)
bpy.ops.object.select_all(action='DESELECT')
for h in HP: h.select_set(True)
L.select_set(True); bpy.context.view_layer.objects.active = L
size = max(max(h.dimensions) for h in HP)
sc.render.bake.use_selected_to_active = True; sc.render.bake.cage_extrusion = size / 50; sc.render.bake.margin = 6
tn.image = imgs['albedo']; bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
tn.image = imgs['normal']; sc.render.bake.normal_space = 'OBJECT'; bpy.ops.object.bake(type='NORMAL')
for k, im in imgs.items(): im.filepath_raw = OUT + '_' + k + '.png'; im.file_format = 'PNG'; im.save()
me = L.data; uv = me.uv_layers.active.data; names = [g.name for g in L.vertex_groups]; polys = []
for p in me.polygons:
    w = {}
    for i in p.vertices:
        for ge in me.vertices[i].groups: w[ge.group] = w.get(ge.group, 0) + ge.weight
    polys.append(dict(p=[list(me.vertices[i].co) for i in p.vertices], uv=[list(uv[li].uv) for li in p.loop_indices], b=names[max(w, key=w.get)] if w else 'spine'))
json.dump(dict(polys=polys), open(OUT + '.json', 'w')); print('EXPORTED', len(polys))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '_lp.blend')
