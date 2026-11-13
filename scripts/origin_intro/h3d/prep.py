"""Clean the Hunyuan mesh and dump what the colouring step needs.
blender -b -P h3d/prep.py -- MESH.glb OUT.npz [target_faces]
- joins, drops loose bits smaller than 0.5 % of the vertices (water squiggles), decimates
- dumps vertices/faces/normals (Hunyuan frame: the input picture is the view from -Y, Z up)
- visibility from the picture's camera (-Y, orthographic): a ray from each vertex toward -Y that hits nothing
Saves the cleaned mesh as OUT.ply next to the npz too."""
import bpy, bmesh, sys, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
argv = sys.argv[sys.argv.index('--') + 1:]
src, out = argv[0], argv[1]
target = int(argv[2]) if len(argv) > 2 else 150000
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in obs: o.select_set(True)
bpy.context.view_layer.objects.active = obs[0]
if len(obs) > 1: bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(bpy.context.scene.objects):
    if o.type != 'MESH': bpy.data.objects.remove(o)
# loose parts
bm = bmesh.new(); bm.from_mesh(ob.data)
bm.verts.ensure_lookup_table()
seen = set(); islands = []
for v in bm.verts:
    if v.index in seen: continue
    stack = [v]; isl = []; seen.add(v.index)
    while stack:
        a = stack.pop(); isl.append(a)
        for e in a.link_edges:
            b = e.other_vert(a)
            if b.index not in seen: seen.add(b.index); stack.append(b)
    islands.append(isl)
n = len(bm.verts)
def flat(isl):
    zs = [v.co.z for v in isl]; return max(zs) - min(zs) < 0.03 and min(zs) < -0.6
drop = [v for isl in islands if len(isl) < 0.005 * n or flat(isl) for v in isl]
print('islands', len(islands), 'sizes', sorted((len(i) for i in islands), reverse=True)[:12], 'drop verts', len(drop))
bmesh.ops.delete(bm, geom=drop, context='VERTS')
bm.to_mesh(ob.data); bm.free()
# decimate
nf = len(ob.data.polygons)
if nf > target:
    m = ob.modifiers.new('dec', 'DECIMATE'); m.ratio = target / nf
    bpy.ops.object.modifier_apply(modifier='dec')
me = ob.data
for p in me.polygons: p.use_smooth = True
print('faces', len(me.polygons), 'verts', len(me.vertices))
V = np.array([v.co[:] for v in me.vertices], np.float32)
N = np.array([v.normal[:] for v in me.vertices], np.float32)
F = np.array([p.vertices[:] for p in me.polygons if len(p.vertices) == 3], np.int32)
# visibility toward -Y (the picture's camera)
bvh = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get())
vis = np.zeros(len(V), bool)
dirv = Vector((0, -1, 0))
for i, (p, nn) in enumerate(zip(V, N)):
    o = Vector(p) + Vector(nn) * 0.002 + dirv * 0.002
    hit = bvh.ray_cast(o, dirv)
    vis[i] = hit[0] is None
print('visible from -Y', int(vis.sum()), '/', len(V))
# thickness: distance through the solid along -normal
thick = np.full(len(V), 9.0, np.float32)
for i, (p, nn) in enumerate(zip(V, N)):
    nv = Vector(nn)
    hit = bvh.ray_cast(Vector(p) - nv * 0.002, -nv, 2.0)
    if hit[0] is not None: thick[i] = (hit[0] - Vector(p)).length
print('thickness median', float(np.median(thick)))
np.savez_compressed(out, V=V, N=N, F=F, vis=vis, thick=thick)
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True)
bpy.ops.wm.ply_export(filepath=out.replace('.npz', '.ply'), export_selected_objects=True, apply_modifiers=True, export_normals=True)
print('saved', out)
