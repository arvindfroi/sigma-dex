"""Render the low-poly 'LP' object of a saved blend from 4 sides (Workbench, flat texture). blender -b X_lp.blend --python render_lp.py -- OUT.png"""
import bpy, sys, math, mathutils
OUT = sys.argv[sys.argv.index('--') + 1]
sc = bpy.context.scene
for o in bpy.data.objects:
    if o.type == 'MESH': o.hide_render = (o.name != 'LP')
L = bpy.data.objects['LP']
sc.render.engine = 'BLENDER_WORKBENCH'; sc.display.shading.light = 'FLAT'; sc.display.shading.color_type = 'TEXTURE'
sc.render.resolution_x = 256; sc.render.resolution_y = 256; sc.render.film_transparent = False
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cen = sum((L.matrix_world @ mathutils.Vector(c) for c in L.bound_box), mathutils.Vector()) / 8
cam.data.ortho_scale = max(L.dimensions) * 1.15
import os
for k, az in enumerate((0, 90, 200, 300)):
    a = math.radians(az); d = 12
    cam.location = cen + mathutils.Vector((math.sin(a) * d, -math.cos(a) * d, 2.0))
    cam.rotation_euler = (cen - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = OUT.replace('.png', f'_{k}.png'); bpy.ops.render.render(write_still=True)
