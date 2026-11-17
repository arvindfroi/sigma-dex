"""Make a copy of a Sabertann .blend that is nice to look at in the Blender window: colours shown (Material Preview),
the rig hidden, the view aimed at the model, frame 1 (the run) shown; frames 5-7 are the leap.
Blender -b IN.blend -P h3d/viewer.py -- OUT.blend"""
import bpy, sys
from mathutils import Vector
out = sys.argv[sys.argv.index('--') + 1]
sc = bpy.context.scene
sc.frame_set(1)
rig = bpy.data.objects.get('Rig')
if rig: rig.hide_set(True); rig.hide_viewport = False
pts = [o.matrix_world @ Vector(c) for o in sc.objects if o.type == 'MESH' for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
mid = (lo + hi) / 2; size = max(hi - lo)
for scr in bpy.data.screens:
    for area in scr.areas:
        for sp in area.spaces:
            if sp.type != 'VIEW_3D': continue
            sp.shading.type = 'MATERIAL'
            sp.overlay.show_floor = True
            r3 = sp.region_3d
            if r3:
                r3.view_location = mid
                r3.view_distance = size * 1.6
                # three-quarter view from the front left, a little from above (the creature faces -Y)
                from mathutils import Euler
                r3.view_rotation = Euler((1.25, 0, -0.6)).to_quaternion()
                r3.view_perspective = 'PERSP'
bpy.ops.wm.save_as_mainfile(filepath=out, copy=True)
print('saved', out, 'objects', len([o for o in sc.objects if o.type == 'MESH']))
