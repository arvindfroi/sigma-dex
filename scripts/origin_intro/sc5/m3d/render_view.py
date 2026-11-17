"""Scene 5 v4, step 4: data passes of the coloured Moosus mesh from one view (Cycles, emission only, no AA).
Blender -b -P sc5/m3d/render_view.py -- COL.npz OUTDIR AZ EL [RES]
Writes OUTDIR/info.png (R = class/10, G = crown height 0..1, B = nearness 0..1) and OUTDIR/nrm.png (camera-space normal
*0.5+0.5, +Z toward the camera), 16-bit, Raw; alpha = coverage. az 0 = from -Y, positive swings toward +X."""
import bpy, sys, math, os, numpy as np
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]
d = np.load(a[0]); OUT = a[1]; AZ, EL = float(a[2]), float(a[3]); RES = int(a[4]) if len(a) > 4 else 768
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
V, F, cls, col = d['V'], d['F'], d['cls'], d['col']
cz = V[cls == 2, 2]; z0, z1 = (np.percentile(cz, 2), cz.max()) if len(cz) else (0, 1)
t = np.clip((V[:, 2] - z0) / max(1e-6, z1 - z0), 0, 1)
me = bpy.data.meshes.new('m'); me.from_pydata(V.tolist(), [], F.tolist()); me.update()
az, el = math.radians(AZ), math.radians(EL)
dv = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
D = V @ np.array(dv); dep = (D - D.min()) / np.ptp(D)            # 1 = nearest the camera
ca = me.color_attributes.new('info', 'FLOAT_COLOR', 'POINT')
ca.data.foreach_set('color', np.stack([cls / 10.0, t, dep, np.ones(len(V))], 1).astype(np.float32).ravel())
for p in me.polygons: p.use_smooth = True
ob = bpy.data.objects.new('m', me); bpy.context.scene.collection.objects.link(ob)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.samples = 1; sc.cycles.use_denoising = False
sc.cycles.filter_width = 0.01; sc.cycles.max_bounces = 0; sc.render.film_transparent = True
sc.view_settings.view_transform = 'Raw'; sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_depth = '16'; sc.render.image_settings.color_mode = 'RGBA'
sc.render.resolution_x = sc.render.resolution_y = RES
cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; c = Vector(((V.min(0) + V.max(0)) / 2).tolist()); cam.data.ortho_scale = float(np.ptp(V, 0).max()) * 1.15
cam.location = c + dv * 10; cam.rotation_euler = (-dv).to_track_quat('-Z', 'Y').to_euler()
def mat(kind):
    m = bpy.data.materials.new(kind); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputMaterial'); e = nt.nodes.new('ShaderNodeEmission')
    if kind == 'info':
        at = nt.nodes.new('ShaderNodeVertexColor'); at.layer_name = 'info'; nt.links.new(at.outputs['Color'], e.inputs['Color'])
    else:
        g = nt.nodes.new('ShaderNodeNewGeometry'); vt = nt.nodes.new('ShaderNodeVectorTransform')
        vt.vector_type = 'NORMAL'; vt.convert_from = 'WORLD'; vt.convert_to = 'CAMERA'
        mm = nt.nodes.new('ShaderNodeVectorMath'); mm.operation = 'MULTIPLY_ADD'
        mm.inputs[1].default_value = (0.5, 0.5, -0.5); mm.inputs[2].default_value = (0.5, 0.5, 0.5)
        nt.links.new(g.outputs['Normal'], vt.inputs[0]); nt.links.new(vt.outputs[0], mm.inputs[0]); nt.links.new(mm.outputs[0], e.inputs['Color'])
    nt.links.new(e.outputs[0], o.inputs[0]); return m
for kind in ('info', 'nrm'):
    ob.data.materials.clear(); ob.data.materials.append(mat(kind))
    sc.render.filepath = os.path.join(OUT, kind + '.png'); bpy.ops.render.render(write_still=True)
print('done', OUT)
