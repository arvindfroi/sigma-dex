"""Blender (headless): dump an FBX armature's walk as world-space bone heads/tails per frame (JSON), for retargeting.
blender -b --python extract_anim.py -- IN.fbx ACTION_SUBSTRING OUT.json"""
import bpy, sys, json
a = sys.argv[sys.argv.index('--') + 1:]; IN, ACT, OUT = a
bpy.ops.wm.read_factory_settings(use_empty=True); bpy.ops.import_scene.fbx(filepath=IN)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
act = [x for x in bpy.data.actions if ACT in x.name][0]
arm.animation_data.action = act
f0, f1 = (int(x) for x in act.frame_range)
rest = {b.name: dict(head=list(arm.matrix_world @ b.head_local), tail=list(arm.matrix_world @ b.tail_local), parent=b.parent.name if b.parent else None)
        for b in arm.data.bones}
frames = []
for f in range(f0, f1):
    bpy.context.scene.frame_set(f); fr = {}
    for pb in arm.pose.bones:
        fr[pb.name] = dict(head=list(arm.matrix_world @ pb.head), tail=list(arm.matrix_world @ pb.tail), m=[list(r) for r in (arm.matrix_world @ pb.matrix)])
    frames.append(fr)
json.dump(dict(rest=rest, frames=frames, action=act.name), open(OUT, 'w')); print('frames', len(frames))
