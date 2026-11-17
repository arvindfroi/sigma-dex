"""Which vertices each turnaround view sees (orthographic, along the axes of the mv frame).
Blender -b -P mv/vis4.py -- MESH.ply OUT.npy      -> (n, 4) bool: front (-Y), left (+X), back (+Y), right (-X)"""
import bpy, sys, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
argv = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.ply_import(filepath=argv[0])
ob = bpy.context.scene.objects[0]; me = ob.data
bvh = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [p.vertices[:] for p in me.polygons], epsilon=0.0)
DIRS = [Vector((0, -1, 0)), Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((-1, 0, 0))]
vis = np.zeros((len(me.vertices), 4), bool)
for i, v in enumerate(me.vertices):
    for k, d in enumerate(DIRS):
        hit = bvh.ray_cast(v.co + d * 0.004, d, 10.0)
        vis[i, k] = hit[0] is None
np.save(argv[1], vis)
print('vis per view', vis.sum(0))
