"""Picture of the rig: the model in x-ray with every bone drawn as a coloured spindle.
Blender -b sabertann.blend -P rigview.py -- outdir"""
import bpy, bmesh, math, sys, os
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]; OUT = argv[0]; os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene; sc.frame_set(1)
rig = bpy.data.objects['Rig']
COL = dict(root=(1, 1, 1), spine=(0.2, 0.9, 0.3), chest=(0.2, 0.9, 0.3), head=(0.2, 0.9, 0.3), jaw=(0.9, 0.9, 0.2), hat=(0.9, 0.9, 0.2),
           shell=(0.3, 0.6, 1), mast=(0.3, 0.6, 1), mast2=(0.3, 0.6, 1), tail0=(1, 0.5, 0.1), tail1=(1, 0.5, 0.1))
for b in rig.pose.bones:
    h = rig.matrix_world @ b.head; t = rig.matrix_world @ b.tail
    L = (t - h).length; r = max(0.04, min(0.11, L * 0.12))
    bm = bmesh.new()
    d = (t - h).normalized(); a = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    u = d.cross(a).normalized(); v = d.cross(u)
    p0 = bm.verts.new(h); p1 = bm.verts.new(t)
    ring = [bm.verts.new(h + d * L * 0.15 + (u * math.cos(k * math.pi / 2) + v * math.sin(k * math.pi / 2)) * r) for k in range(4)]
    for k in range(4):
        bm.faces.new((p0, ring[k], ring[(k + 1) % 4])); bm.faces.new((p1, ring[(k + 1) % 4], ring[k]))
    me = bpy.data.meshes.new('b_' + b.name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('b_' + b.name, me); sc.collection.objects.link(o)
    c = COL.get(b.name)
    if c is None:
        c = (1, 0.3, 0.8) if 'sail' in b.name else (0.4, 1, 1) if 'flag' in b.name else (1, 0.35, 0.3)
    m = bpy.data.materials.new('bm_' + b.name); m.diffuse_color = (*c, 1); o.data.materials.append(m)
    o['bone'] = 1
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading; sh.light = 'FLAT'; sh.color_type = 'MATERIAL'
for m in bpy.data.materials:
    if m.name.startswith('bm_'): continue
    n = m.node_tree.nodes.get('Principled BSDF') if m.use_nodes else None
    base = n.inputs['Base Color'].default_value if n else (0.5, 0.5, 0.5, 1)
    m.diffuse_color = (base[0] * 0.6 + 0.25, base[1] * 0.6 + 0.25, base[2] * 0.6 + 0.28, 0.18)
sc.render.film_transparent = False
w = bpy.data.worlds.new('w'); sc.world = w; w.color = (0.07, 0.08, 0.12)
sc.display.render_aa = '8'
# x-ray look: model materials get alpha blending through Workbench 'show_xray'
sh.show_xray = True; sh.xray_alpha = 0.35
sc.render.resolution_x = 640; sc.render.resolution_y = 560
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 6.6
tgt = Vector((0, 0.2, 2.0))
for name, yaw, el in (('rig_34', 40, 12), ('rig_side', 90, 3)):
    yr, er = math.radians(yaw), math.radians(el)
    d = Vector((math.sin(yr) * math.cos(er), -math.cos(yr) * math.cos(er), math.sin(er)))
    cam.location = tgt + d * 30; cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(OUT, name + '.png'); bpy.ops.render.render(write_still=True)
