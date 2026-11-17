"""Quick look at a coloured mesh from 8 sides (Workbench, vertex colours).
Blender -b -P sc5/m3d/turntable.py -- COL.npz OUT.png [EL]"""
import bpy, sys, math, numpy as np
from mathutils import Vector
a = sys.argv[sys.argv.index('--') + 1:]; d = np.load(a[0]); OUT = a[1]; EL = float(a[2]) if len(a) > 2 else 15
bpy.ops.wm.read_factory_settings(use_empty=True)
V, F, col = d['V'], d['F'], d['col'] / 255.0
me = bpy.data.meshes.new('m'); me.from_pydata(V.tolist(), [], F.tolist()); me.update()
ca = me.color_attributes.new('Col', 'FLOAT_COLOR', 'POINT')
ca.data.foreach_set('color', np.concatenate([col, np.ones((len(col), 1))], 1).astype(np.float32).ravel())
ob = bpy.data.objects.new('m', me); bpy.context.scene.collection.objects.link(ob)
for p in me.polygons: p.use_smooth = True
sc = bpy.context.scene; sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.color_type = 'VERTEX'; sc.display.shading.light = 'STUDIO'
sc.render.resolution_x = sc.render.resolution_y = 384; sc.render.film_transparent = False
sc.world = bpy.data.worlds.new('w')
cam = bpy.data.objects.new('c', bpy.data.cameras.new('c')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; c = Vector(V.mean(0)); cam.data.ortho_scale = float(np.ptp(V, 0).max()) * 1.25
import os, tempfile
tiles = []
for k in range(8):
    az = math.radians(k * 45); el = math.radians(EL)
    dv = Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))
    cam.location = c + dv * 10; cam.rotation_euler = (-dv).to_track_quat('-Z', 'Y').to_euler()
    p = os.path.join(tempfile.gettempdir(), f'tt_{k}.png'); sc.render.filepath = p
    bpy.ops.render.render(write_still=True); tiles.append(p)
img = bpy.data.images.new('sheet', 384 * 4, 384 * 2)
px = np.zeros((384 * 2, 384 * 4, 4), np.float32)
for k, p in enumerate(tiles):
    im = bpy.data.images.load(p); arr = np.array(im.pixels[:], np.float32).reshape(384, 384, 4)
    r, cc = 1 - k // 4, k % 4; px[r * 384:(r + 1) * 384, cc * 384:(cc + 1) * 384] = arr
img.pixels = px.ravel(); img.filepath_raw = OUT; img.file_format = 'PNG'; img.save()
