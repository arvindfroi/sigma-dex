"""Quick look: Workbench renders of the model from a few angles.
Blender -b file.blend -P preview.py -- outdir [frame]  -> outdir/view_<name>.png"""
import bpy, math, sys, os
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]; FR = int(argv[1]) if len(argv) > 1 else 1
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
sc.frame_set(FR)
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'; sh.color_type = os.environ.get('SAB_PREV_COLOR', 'TEXTURE'); sh.show_object_outline = True; sh.object_outline_color = (0, 0, 0)
sc.display.render_aa = '8'
for m in bpy.data.materials:
    n = m.node_tree.nodes.get('Principled BSDF') if m.use_nodes else None
    if n: m.diffuse_color = n.inputs['Base Color'].default_value
    if m.get('image'):
        m.diffuse_color = (0.68, 0.7, 0.78, 1) if m.get('key') == 'white' else (0.75, 0.45, 0.03, 1)
sc.render.resolution_x = 480; sc.render.resolution_y = 480
w = bpy.data.worlds.new('w'); sc.world = w; w.color = (0.35, 0.55, 0.8)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 7.4
tgt = Vector((0, 0.1, 2.35))
ONLY = os.environ.get('SAB_VIEWS')
views = [('intro', 32, 8), ('front', 0, 4), ('side', 90, 4), ('back', 160, 25), ('top', 35, 55),
         ('concept', 52, 16), ('y20', 20, 9), ('y35', 35, 9)]
views += [('head', 38, 8, Vector((0, -2.0, 1.6)), 2.6), ('stern', 120, 12, Vector((0, 2.1, 2.0)), 2.8), ('head28', 28, 9, Vector((0, -2.2, 1.5)), 2.0), ('stern32', 32, 9, Vector((0, 1.9, 2.4)), 2.4),
          ('front8', 0, 8, Vector((0, -0.5, 2.8)), 6.6), ('face', 0, 6, Vector((0, -2.0, 1.8)), 2.4), ('headside', 90, 5, Vector((0, -2.6, 2.6)), 3.2), ('leapface', 0, 8, Vector((0, -2.6, 3.0)), 3.4)]
for v in views:
    name, yaw, el = v[:3]
    if ONLY and name not in ONLY.split(','): continue
    t_ = v[3] if len(v) > 3 else tgt; cam.data.ortho_scale = v[4] if len(v) > 4 else 7.4
    yaw_r = math.radians(yaw); el_r = math.radians(el)
    d = Vector((math.sin(yaw_r) * math.cos(el_r), -math.cos(yaw_r) * math.cos(el_r), math.sin(el_r)))
    cam.location = t_ + d * 30
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(OUT, f'view_{name}.png')
    bpy.ops.render.render(write_still=True)
