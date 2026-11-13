"""Render the model as a flat silhouette + a flat-colour image from a given angle, for overlaying on the drawing.
Blender -b sabertann.blend -P fit_view.py -- OUTDIR YAW EL [FRAME]"""
import bpy, math, sys, os
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
OUT, YAW, EL = argv[0], float(argv[1]), float(argv[2]); FR = int(argv[3]) if len(argv) > 3 else 1
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene; sc.frame_set(FR)
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sc.render.resolution_x = 900; sc.render.resolution_y = 900
w = bpy.data.worlds.new('w'); sc.world = w; w.color = (1, 1, 1)
sc.render.film_transparent = True
for m in bpy.data.materials:
    n = m.node_tree.nodes.get('Principled BSDF') if m.use_nodes else None
    if n: m.diffuse_color = n.inputs['Base Color'].default_value
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 8.0
tgt = Vector((0, 0.0, 2.2))
yr, er = math.radians(YAW), math.radians(EL)
d = Vector((math.sin(yr) * math.cos(er), -math.cos(yr) * math.cos(er), math.sin(er)))
cam.location = tgt + d * 30; cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
for name, light, ctype, outline in (('flat', 'FLAT', 'MATERIAL', True), ('shade', 'STUDIO', 'TEXTURE', True)):
    sh.light = light; sh.color_type = ctype; sh.show_object_outline = outline; sh.object_outline_color = (0, 0, 0)
    sc.render.filepath = os.path.join(OUT, f'{name}.png'); bpy.ops.render.render(write_still=True)
