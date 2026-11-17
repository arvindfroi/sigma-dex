"""Workbench preview of all frames: row 1 from the intro camera, row 2 from the side.
Blender -b FILE.blend -P h3d/frames_preview.py -- OUT.png [yaw] [el]"""
import bpy, sys, math, os, numpy as np, tempfile
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]; YAW = float(argv[1]) if len(argv) > 1 else 20; EL = float(argv[2]) if len(argv) > 2 else 9
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
sc.display.shading.show_object_outline = True; sc.view_settings.view_transform = 'Standard'
for m in bpy.data.materials:
    if m.use_nodes and m.node_tree.nodes.get('Principled BSDF'):
        m.diffuse_color = m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value
R = 384; sc.render.resolution_x = sc.render.resolution_y = R
w = bpy.data.worlds.new('w'); sc.world = w; w.color = (0.2, 0.25, 0.4)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 9.0
# water plane
bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, sc['water']))
wp = bpy.context.active_object; wm = bpy.data.materials.new('wpv'); wm.diffuse_color = (0.15, 0.3, 0.6, 1); wp.data.materials.append(wm)
tmp = tempfile.mkdtemp(); rows = []
for yaw, el in ((YAW, EL), (90, 4)):
    row = []
    a, e = math.radians(yaw), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    tgt = Vector((0, 0, 3.0)); cam.location = tgt + d * 40; cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    for f in range(1, sc.frame_end + 1):
        sc.frame_set(f); sc.render.filepath = os.path.join(tmp, f'{yaw}_{f}.png'); bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(sc.render.filepath); row.append(np.array(im.pixels[:]).reshape(R, R, 4)[::-1])
    rows.append(np.concatenate(row, 1))
sheet = np.concatenate(rows, 0)
img = bpy.data.images.new('s', sheet.shape[1], sheet.shape[0]); img.pixels = sheet[::-1].ravel().tolist()
img.filepath_raw = OUT; img.file_format = 'PNG'; img.save(); print('saved', OUT)
