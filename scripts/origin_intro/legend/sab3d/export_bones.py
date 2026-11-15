"""Blender: world-space bone matrices of Sabertann's rig at rest and at the given frames of its action (run_leap),
for building the DS joint animation. blender -b sab_v15.blend --python export_bones.py -- OUT.json FRAMES(comma)"""
import bpy, sys, json
argv = sys.argv[sys.argv.index('--') + 1:]; OUT = argv[0]; FR = [int(x) for x in argv[1].split(',')]
rig = bpy.data.objects['Rig']; sc = bpy.context.scene
res = {'rest': {b.name: [list(r) for r in (rig.matrix_world @ b.matrix_local)] for b in rig.data.bones},
       'parent': {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}, 'frames': {}}
rig.data.pose_position = 'POSE'
for f in FR:
    sc.frame_set(f)
    res['frames'][f] = {pb.name: [list(r) for r in (rig.matrix_world @ pb.matrix)] for pb in rig.pose.bones}
json.dump(res, open(OUT, 'w')); print('BONES', len(res['rest']), 'frames', FR)
