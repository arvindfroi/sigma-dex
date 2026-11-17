"""Render the mesh with its colour classes (workbench, vertex colours) from a few angles.
blender -b -P h3d/preview_lab.py -- MESH.ply LABELS.npy OUT.png [yaw,el ...]   (creature faces -X; yaw 0 = head-on)
ZOOM=x,y,z,orthoscale optional."""
import bpy, sys, math, os, numpy as np
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
mesh_path, lab_path, out = argv[:3]
views = [tuple(float(x) for x in v.split(',')) for v in argv[3:]] or [(0, 8), (22, 10), (54, 12), (90, 5), (160, 15), (0, 70)]
COL = {0: (0.13, 0.13, 0.16), 1: (0.06, 0.06, 0.08), 2: (0.55, 0.08, 0.09), 3: (0.95, 0.72, 0.18), 4: (0.93, 0.93, 0.97),
       5: (1.0, 1.0, 1.0), 6: (0.0, 0.0, 0.0), 7: (0.02, 0.02, 0.03), 8: (0.42, 0.26, 0.13), 9: (0.22, 0.13, 0.07)}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.ply_import(filepath=mesh_path)
ob = bpy.context.scene.objects[0]
lab = np.load(lab_path)
me = ob.data
assert len(me.vertices) == len(lab), (len(me.vertices), len(lab))
if os.environ.get('FLAB'):                     # per-face labels (clean_labels.py): FLAB=prefix -> prefix_flab.npy
    fl = np.load(os.environ['FLAB'] + '_flab.npy'); fpp = np.load(os.environ['FLAB'] + '_fpart.npy')
    ca = me.color_attributes.new('lab', 'FLOAT_COLOR', 'CORNER')
    cols = np.zeros((len(me.loops), 4), np.float32)
    for p_ in me.polygons:
        for li in p_.loop_indices: cols[li] = COL[int(fl[p_.index])] + (1.0,)
    ca.data.foreach_set('color', cols.ravel())
    os.environ['DROPF'] = '1'
else:
    ca = me.color_attributes.new('lab', 'FLOAT_COLOR', 'POINT')
    cols = np.array([COL[int(k)] + (1.0,) for k in lab], np.float32)
    ca.data.foreach_set('color', cols.ravel())
me.color_attributes.active_color = ca
for p in me.polygons: p.use_smooth = True
if os.environ.get('DROPF'):
    import bmesh
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if fpp[f.index] == 12], context='FACES')
    bm.to_mesh(me); bm.free()
elif os.environ.get('DROP'):                    # DROP=parts.npy:12 -> faces with a vertex of that part go
    import bmesh
    pf, pid = os.environ['DROP'].rsplit(':', 1); pa = np.load(pf)
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if any(pa[v.index] == int(pid) for v in f.verts)], context='FACES')
    bm.to_mesh(me); bm.free()
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'; sc.display.shading.color_type = 'VERTEX'
sc.display.shading.show_object_outline = True; sc.display.shading.show_cavity = False
sc.view_settings.view_transform = 'Standard'
sc.render.resolution_x = sc.render.resolution_y = 512
w = bpy.data.worlds.new('w'); sc.world = w; w.color = (0.25, 0.3, 0.4)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'
ctr = Vector((0, 0, 0.03)); cam.data.ortho_scale = 2.0
if os.environ.get('ZOOM'):
    zx, zy, zz, zs = [float(v) for v in os.environ['ZOOM'].split(',')]; ctr = Vector((zx, zy, zz)); cam.data.ortho_scale = zs
import tempfile
tmp = tempfile.mkdtemp(); arrs = []
for i, (yaw, el) in enumerate(views):
    a, e = math.radians(yaw), math.radians(el)
    d = Vector((-math.cos(a) * math.cos(e), -math.sin(a) * math.cos(e), math.sin(e)))
    cam.location = ctr + d * 6
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(tmp, f'v{i}.png'); bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(sc.render.filepath)
    arrs.append(np.array(im.pixels[:]).reshape(512, 512, 4)[::-1])
cols_ = 3; rows = (len(arrs) + cols_ - 1) // cols_
sheet = np.ones((rows * 512, cols_ * 512, 4))
for k, a in enumerate(arrs): r, c = divmod(k, cols_); sheet[r * 512:(r + 1) * 512, c * 512:(c + 1) * 512] = a
img = bpy.data.images.new('sheet', cols_ * 512, rows * 512); img.pixels = sheet[::-1].ravel().tolist()
img.filepath_raw = out; img.file_format = 'PNG'; img.save()
print('saved', out)
