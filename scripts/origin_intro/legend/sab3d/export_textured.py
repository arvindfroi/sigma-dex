"""Blender (headless): Sabertann's rig (mv/sab_v15.blend) -> a DS-style textured low-poly model, like the game's own
Ho-Oh: voxel remesh of the posed high-poly, QuadriFlow to about QUADS clean quads, Smart UV, and a 128x128 texture baked
from the high-poly (Cycles COMBINED: the model's own colours under a soft sun + sky, so the shading lives in the texture,
as on Ho-Oh whose materials are unlit). Writes OUT.json (quads/tris with positions, UVs, bone) and OUT.png.
blender -b sab_v15.blend --python export_textured.py -- OUT QUADS [FRAME] [TEXSIZE]"""
import bpy, bmesh, sys, json, math
argv = sys.argv[sys.argv.index('--') + 1:]; OUT = argv[0]; QUADS = int(argv[1]); FRAME = int(argv[2]) if len(argv) > 2 else 0
TS = int(argv[3]) if len(argv) > 3 else 128
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 32
rig = bpy.data.objects['Rig']
if FRAME: sc.frame_set(FRAME)
else: rig.data.pose_position = 'REST'
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.visible_get()]
dg = bpy.context.evaluated_depsgraph_get()
# 1. posed high-poly copies (kept for baking), joined into one source
copies = []
for o in meshes:
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    c = bpy.data.objects.new(o.name + '_hp', me); c.matrix_world = o.matrix_world.copy(); sc.collection.objects.link(c)
    for g in o.vertex_groups: c.vertex_groups.new(name=g.name)
    for v in o.data.vertices:
        for ge in v.groups: c.vertex_groups[o.vertex_groups[ge.group].name].add([v.index], ge.weight, 'REPLACE')
    copies.append(c)
for o in meshes: o.hide_render = True; o.hide_set(True)
bpy.ops.object.select_all(action='DESELECT')
for c in copies: c.select_set(True)
bpy.context.view_layer.objects.active = copies[0]; bpy.ops.object.join(); HP = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
# 2. low-poly: voxel remesh -> QuadriFlow
bpy.ops.object.select_all(action='DESELECT'); HP.select_set(True); bpy.context.view_layer.objects.active = HP
bpy.ops.object.duplicate(); LP = bpy.context.view_layer.objects.active; LP.name = 'LP'
for g in list(LP.vertex_groups): LP.vertex_groups.remove(g)
rm = LP.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = max(HP.dimensions) / 160
bpy.ops.object.modifier_apply(modifier='rm')
r = bpy.ops.object.quadriflow_remesh(target_faces=QUADS, use_mesh_symmetry=False, use_preserve_sharp=False, use_preserve_boundary=False, smooth_normals=False, seed=0)
print('QF result', r, len(LP.data.polygons))
if len(LP.data.polygons) > QUADS * 3:                  # QuadriFlow refused: decimate the voxel mesh instead (manifold, so it works)
    for it in range(14):
        n = len(LP.data.polygons)
        if n <= QUADS * 2.1: break
        mod = LP.modifiers.new('dec', 'DECIMATE'); mod.ratio = max(0.2, QUADS * 2 / n); mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier='dec')
    print('DECIMATED', len(LP.data.polygons))
print('QUADRIFLOW', len(LP.data.polygons))
# bone weights back from the source
for g in HP.vertex_groups: LP.vertex_groups.new(name=g.name)
dt = LP.modifiers.new('dt', 'DATA_TRANSFER'); dt.object = HP; dt.use_vert_data = True; dt.data_types_verts = {'VGROUP_WEIGHTS'}
dt.vert_mapping = 'POLYINTERP_NEAREST'; dt.layers_vgroup_select_src = 'ALL'; dt.layers_vgroup_select_dst = 'NAME'
bpy.ops.object.modifier_apply(modifier='dt')
# 3. UVs and the bake
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(float(argv[4]) if len(argv) > 4 else 80), island_margin=1.5 / TS, area_weight=1.0)
bpy.ops.object.mode_set(mode='OBJECT')
imgs = {}
for key in ('albedo', 'normal'):
    imgs[key] = bpy.data.images.new(key, TS * 4, TS * 4, float_buffer=(key == 'normal'))
mat = bpy.data.materials.new('lpmat'); mat.use_nodes = True; nt = mat.node_tree
tn = nt.nodes.new('ShaderNodeTexImage'); nt.nodes.active = tn
LP.data.materials.clear(); LP.data.materials.append(mat)
bpy.ops.object.select_all(action='DESELECT'); HP.select_set(True); LP.select_set(True); bpy.context.view_layer.objects.active = LP
sc.render.bake.use_selected_to_active = True; sc.render.bake.cage_extrusion = max(HP.dimensions) / 60; sc.render.bake.margin = 8
sc.cycles.samples = 4
tn.image = imgs['albedo']; bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
tn.image = imgs['normal']; sc.render.bake.normal_space = 'OBJECT'; bpy.ops.object.bake(type='NORMAL')
for key, im in imgs.items():
    im.filepath_raw = OUT + '_' + key + '.png'; im.file_format = 'PNG'; im.save()
# 4. export geometry
me = LP.data; uv = me.uv_layers.active.data; names = [g.name for g in LP.vertex_groups]; polys = []
for p in me.polygons:
    w = {}
    for i in p.vertices:
        for ge in me.vertices[i].groups: w[ge.group] = w.get(ge.group, 0) + ge.weight
    polys.append(dict(p=[list(me.vertices[i].co) for i in p.vertices], uv=[list(uv[li].uv) for li in p.loop_indices],
                      b=names[max(w, key=w.get)] if w else 'root'))
json.dump(dict(polys=polys), open(OUT + '.json', 'w'))
print('EXPORTED', len(polys), 'faces')
