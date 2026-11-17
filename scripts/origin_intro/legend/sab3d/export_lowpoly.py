"""Blender (headless): Sabertann's intro rig (mv/sab_v15.blend) -> a low-poly mesh for the DS legendary cinematic.
Bakes the material colour into vertex colours (Cycles DIFFUSE colour, per high-poly object), joins everything at the
chosen pose, decimates to about TARGET triangles, and writes JSON: per triangle 3 positions (Blender world space),
the baked colour and the bone that weighs most. blender -b sab_v15.blend --python export_lowpoly.py -- OUT.json TARGET [FRAME]"""
import bpy, bmesh, sys, json
argv = sys.argv[sys.argv.index('--') + 1:]; OUT = argv[0]; TARGET = int(argv[1]); FRAME = int(argv[2]) if len(argv) > 2 else 0
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 1; sc.cycles.device = 'CPU'
rig = bpy.data.objects['Rig']
if FRAME:
    sc.frame_set(FRAME)
else:
    rig.data.pose_position = 'REST'
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.visible_get()]
# 1. bake colour per object into a new colour attribute 'bk'
for o in meshes:
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    if 'bk' not in o.data.color_attributes: o.data.color_attributes.new('bk', 'FLOAT_COLOR', 'POINT')
    o.data.color_attributes.active_color = o.data.color_attributes['bk']
    try:
        bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'}, target='VERTEX_COLORS')
    except Exception as e:
        print('bake failed', o.name, e)
# 2. evaluated copies (pose applied), joined
copies = []
dg = bpy.context.evaluated_depsgraph_get()
for o in meshes:
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    c = bpy.data.objects.new(o.name + '_lp', me); c.matrix_world = o.matrix_world.copy(); sc.collection.objects.link(c)
    for g in o.vertex_groups: c.vertex_groups.new(name=g.name)
    # vertex groups are not carried by new_from_object: copy weights by index (same topology)
    for v in o.data.vertices:
        for ge in v.groups:
            c.vertex_groups[o.vertex_groups[ge.group].name].add([v.index], ge.weight, 'REPLACE')
    copies.append(c)
bpy.ops.object.select_all(action='DESELECT')
for c in copies: c.select_set(True)
bpy.context.view_layer.objects.active = copies[0]
bpy.ops.object.join(); J = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
n0 = len(J.data.polygons)
# the scanned mesh has non-manifold edges, so collapse stalls (~48k): rebuild it as a closed voxel mesh, decimate that,
# then take colours and bone weights back from the original by nearest surface
src = J; bpy.ops.object.select_all(action='DESELECT'); src.select_set(True); bpy.context.view_layer.objects.active = src
bpy.ops.object.duplicate(); L = bpy.context.view_layer.objects.active
dims = max(src.dimensions); vs = float(argv[3]) if len(argv) > 3 else dims / 140
rm = L.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = vs; rm.use_smooth_shade = False
bpy.ops.object.modifier_apply(modifier='rm'); print('REMESH', len(L.data.polygons), 'voxel', vs)
for g in list(L.vertex_groups): L.vertex_groups.remove(g)
for it in range(14):
    n = len(L.data.polygons)
    if n <= TARGET * 1.05: break
    mod = L.modifiers.new('dec', 'DECIMATE'); mod.ratio = max(0.2, TARGET / n); mod.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier='dec'); print('STEP', it, n, '->', len(L.data.polygons))
for g in src.vertex_groups: L.vertex_groups.new(name=g.name)
if 'bk' not in L.data.color_attributes: L.data.color_attributes.new('bk', 'FLOAT_COLOR', 'POINT')
dt = L.modifiers.new('dt', 'DATA_TRANSFER'); dt.object = src
dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS', 'COLOR_VERTEX'}; dt.vert_mapping = 'POLYINTERP_NEAREST'
dt.layers_vgroup_select_src = 'ALL'; dt.layers_vgroup_select_dst = 'NAME'; dt.layers_vcol_vert_select_src = 'ALL'; dt.layers_vcol_vert_select_dst = 'NAME'
bpy.ops.object.modifier_apply(modifier='dt')
J = L
bm = bmesh.new(); bm.from_mesh(J.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(J.data); bm.free()
me = J.data; col = me.color_attributes.get('bk'); names = [g.name for g in J.vertex_groups]
tris = []
for p in me.polygons:
    vs = [me.vertices[i] for i in p.vertices]
    if col is not None and col.domain == 'POINT': cs = [tuple(col.data[i].color[:3]) for i in p.vertices]
    elif col is not None: cs = [tuple(col.data[li].color[:3]) for li in p.loop_indices]
    else: cs = [(0.5, 0.5, 0.5)] * 3
    w = {}
    for v in vs:
        for ge in v.groups: w[ge.group] = w.get(ge.group, 0) + ge.weight
    bone = names[max(w, key=w.get)] if w else 'root'
    tris.append(dict(p=[list(v.co) for v in vs], c=[sum(c[k] for c in cs) / 3 for k in range(3)], n=list(p.normal), b=bone))
json.dump(dict(tris=tris, before=n0), open(OUT, 'w'))
print('EXPORTED', len(tris), 'tris from', n0)
