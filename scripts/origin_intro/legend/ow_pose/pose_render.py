"""Render a rigged film model in a pose, front view like the overworld sprites, as a flat-colour picture and a silhouette
(Arvind 2026-11-17: frames 6 and 7 must change as much as Lugia's and Ho-Oh's; the new poses are set on the 3D models and
their silhouettes guide Qwen, which draws the approved sprite into them).
Blender -b MODEL.blend --python pose_render.py -- POSE.json OUT_PREFIX
POSE.json: {"camera": {"elev": deg, "azim": deg, "ortho": size, "target": [x,y,z]},
            "bones": {"Rig/bone": [rx, ry, rz] (degrees, local XYZ euler)},
            "objects": {"Name": {"rot": [rx,ry,rz], "pivot": [x,y,z]}}   (rigid parts turned about a pivot, world space)
            "scale_mesh": {"Name": {"axis": "z", "f": 0.3, "about": "max"}},   (base mesh squashed toward its top/bottom)
            "hide": ["Name", ...], "show_only_rigged": true, "res": 512}
-> OUT_PREFIX_col.png (flat colours) and OUT_PREFIX_sil.png (white silhouette on black)"""
import bpy, sys, json, math
from mathutils import Vector, Euler, Matrix
argv = sys.argv[sys.argv.index('--') + 1:]
P = json.load(open(argv[0])); OUT = argv[1]
sc = bpy.context.scene
for o in bpy.data.objects:                                   # only what the film uses: rigged objects (not the *_c copies)
    if o.type == 'MESH':
        keep = (not P.get('show_only_rigged', True)) or (o.parent is not None and o.parent.type == 'ARMATURE') or o.name in P.get('also', [])
        o.hide_render = not keep or o.name in P.get('hide', [])
for name, s in P.get('scale_mesh', {}).items():
    me = bpy.data.objects[name].data; ax = 'xyz'.index(s['axis']); vs = [v.co[ax] for v in me.vertices]
    ref = max(vs) if s.get('about', 'max') == 'max' else min(vs) if s['about'] == 'min' else s['about']
    for v in me.vertices: v.co[ax] = ref + (v.co[ax] - ref) * s['f']
for key, r in P.get('bones', {}).items():
    rig, bone = key.split('/'); pb = bpy.data.objects[rig].pose.bones[bone]
    pb.rotation_mode = 'XYZ'; pb.rotation_euler = Euler([math.radians(a) for a in r], 'XYZ')
for o in bpy.data.objects:                                   # no animation drives the pose
    if o.animation_data: o.animation_data.action = None
for name, t in P.get('objects', {}).items():
    o = bpy.data.objects[name]; pv = Vector(t['pivot']); R = Euler([math.radians(a) for a in t['rot']], 'XYZ').to_matrix().to_4x4()
    o.matrix_world = Matrix.Translation(pv) @ R @ Matrix.Translation(-pv) @ o.matrix_world
bpy.context.view_layer.update()
c = P.get('camera', {}); el, az = math.radians(c.get('elev', 20)), math.radians(c.get('azim', 0))
tgt = Vector(c.get('target', [0, 0, 1.5])); d = 40
cam_d = bpy.data.cameras.new('cam'); cam_d.type = 'ORTHO'; cam_d.ortho_scale = c.get('ortho', 7.0)
cam = bpy.data.objects.new('cam', cam_d); sc.collection.objects.link(cam)
fwd = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))   # camera on -Y (in front), above
cam.location = tgt + fwd * d; cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
sc.camera = cam
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'FLAT'; sc.display.shading.color_type = c.get('color', 'MATERIAL')
sc.render.film_transparent = True; sc.render.resolution_x = sc.render.resolution_y = P.get('res', 512); sc.render.resolution_percentage = 100
sc.display.render_aa = 'OFF'; sc.view_settings.view_transform = 'Standard'
sc.render.filepath = OUT + '_col.png'; bpy.ops.render.render(write_still=True)
sc.display.shading.color_type = 'SINGLE'; sc.display.shading.single_color = (1, 1, 1)
sc.render.filepath = OUT + '_sil.png'; bpy.ops.render.render(write_still=True)
print('rendered', OUT)
