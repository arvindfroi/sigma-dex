"""Quick look at a mesh: workbench renders from several angles, one sheet.
blender -b -P h3d/views.py -- MESH.glb OUT.png [yaw,el ...]
yaw 0 = looking at the mesh's front (-Y side after the import fix), positive yaw = camera moves to the mesh's right."""
import bpy, sys, math, os
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
mesh_path, out = argv[0], argv[1]
views = [tuple(float(x) for x in v.split(',')) for v in argv[2:]] or [(0, 8), (30, 12), (60, 20), (90, 5), (180, 10), (0, 89)]
bpy.ops.wm.read_factory_settings(use_empty=True)
if mesh_path.endswith('.glb'): bpy.ops.import_scene.gltf(filepath=mesh_path)
elif mesh_path.endswith('.ply'): bpy.ops.wm.ply_import(filepath=mesh_path)
else: bpy.ops.wm.obj_import(filepath=mesh_path)
obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in obs: o.select_set(True)
bpy.context.view_layer.objects.active = obs[0]
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in obs for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
ctr = (lo + hi) / 2; R = (hi - lo).length / 2
print('bounds', [round(v, 3) for v in lo], [round(v, 3) for v in hi])
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = os.environ.get('VCOL', 'SINGLE')
sc.display.shading.single_color = (0.75, 0.72, 0.68); sc.display.shading.show_cavity = True
sc.display.shading.show_object_outline = True
sc.render.resolution_x = sc.render.resolution_y = 512; sc.render.film_transparent = False
w = bpy.data.worlds.new('w'); sc.world = w
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.1 * R
if os.environ.get('ZOOM'):
    zx, zy, zz, zs = [float(v) for v in os.environ['ZOOM'].split(',')]; ctr = Vector((zx, zy, zz)); cam.data.ortho_scale = zs
import tempfile
tmp = tempfile.mkdtemp(); files = []
FRONT = os.environ.get('FRONT', '-y')     # which axis the creature faces
for i, (yaw, el) in enumerate(views):
    a = math.radians(yaw); e = math.radians(el)
    if FRONT == '-y': d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    elif FRONT == '+x': d = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
    elif FRONT == '-x': d = Vector((-math.cos(a) * math.cos(e), -math.sin(a) * math.cos(e), math.sin(e)))
    else: d = Vector((-math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    cam.location = ctr + d * 4 * R
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    if abs(el) > 85: cam.rotation_euler = (0, 0, 0) if FRONT in ('-y', '+y') else (0, 0, -math.pi / 2)
    sc.render.filepath = os.path.join(tmp, f'v{i}.png'); bpy.ops.render.render(write_still=True); files.append(sc.render.filepath)
# sheet
imgs = [bpy.data.images.load(f) for f in files]
import numpy as np
arrs = []
for im in imgs:
    a = np.array(im.pixels[:]).reshape(512, 512, 4)[::-1]; arrs.append(a)
cols = 3; rows = (len(arrs) + cols - 1) // cols
sheet = np.ones((rows * 512, cols * 512, 4))
for k, a in enumerate(arrs): r, c = divmod(k, cols); sheet[r * 512:(r + 1) * 512, c * 512:(c + 1) * 512] = a
img = bpy.data.images.new('sheet', cols * 512, rows * 512); img.pixels = sheet[::-1].ravel().tolist()
img.filepath_raw = out; img.file_format = 'PNG'; img.save()
print('saved', out, views)
