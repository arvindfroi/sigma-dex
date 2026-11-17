"""Workbench look at a rigged .blend: chosen frames x chosen views, one sheet (material colours, outlines).
Blender -b BLEND -P h3d/pose_preview.py -- OUT.png FRAMES VIEWS   e.g. 1,5,6,7  24,9;90,3;0,60
yaw 0 = in front of the creature (it faces -Y), positive yaw = toward its left (+X side)... as in render_passes."""
import bpy, sys, math, os, tempfile
import numpy as np
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
out = argv[0]; frames = [int(f) for f in argv[1].split(',')]
views = [tuple(float(v) for v in s.split(',')) for s in argv[2].split(';')]
RES = int(os.environ.get('RES', 384))
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'MATERIAL'
sc.display.shading.show_object_outline = True
sc.view_settings.view_transform = 'Standard'
sc.render.resolution_x = sc.render.resolution_y = RES; sc.render.film_transparent = False
w = bpy.data.worlds.new('w'); sc.world = w; w.color = (0.25, 0.3, 0.42)
if os.environ.get('ENGINE', 'eevee') == 'eevee':      # the real materials (painted per pixel), lit simply
    for eng in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        try: sc.render.engine = eng; break
        except TypeError: pass
    w.use_nodes = True; bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.5, 0.55, 0.65, 1); bg.inputs[1].default_value = 0.9
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun)
    sun.data.energy = 3.0; sun.rotation_euler = (math.radians(50), 0, math.radians(30))
for o in sc.objects:
    if o.type == 'MESH' and o.name.lower().startswith('foam'): o.hide_render = True
cam = bpy.data.objects.new('pcam', bpy.data.cameras.new('pcam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = float(os.environ.get('OSCALE', 9.0))
ctr = Vector([float(v) for v in os.environ.get('CTR', '0,0,3.0').split(',')])
tmp = tempfile.mkdtemp(); tiles = []
for f in frames:
    sc.frame_set(f)
    for yaw, el in views:
        a, e = math.radians(yaw), math.radians(el)
        d = Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
        cam.location = ctr + d * 20
        cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
        sc.render.filepath = os.path.join(tmp, f'f{f}_{yaw}_{el}.png'); bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(sc.render.filepath)
        tiles.append(np.array(im.pixels[:]).reshape(RES, RES, 4)[::-1])
nc = len(views); nr = len(frames)
sheet = np.ones((nr * RES, nc * RES, 4))
for k, t in enumerate(tiles): r, c = divmod(k, nc); sheet[r * RES:(r + 1) * RES, c * RES:(c + 1) * RES] = t
img = bpy.data.images.new('sheet', nc * RES, nr * RES); img.pixels = sheet[::-1].ravel().tolist()
img.filepath_raw = out; img.file_format = 'PNG'; img.save()
print('saved', out)
