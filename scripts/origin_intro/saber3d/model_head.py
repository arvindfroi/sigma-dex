"""Build the 3D Sabertann (own model, after Arvind's concept art 624.webp) with a rig and a swim cycle.
v5: a sabre-toothed cat (Kaptein Sabeltann = Captain Sabretooth) with a ship on his back: cat head with sabres, black
ruff, gold cuffs, fore-and-aft bicorne, a real ship hull with a gold pirate skull on each stern quarter.
Run: Blender -b --factory-startup -P model.py -- out.blend
Creature faces -Y, up is +Z, water level is WATER. One armature, single root bone (DS friendly)."""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.join(HERE, 'tex')
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUT = argv[0] if argv else os.path.join(HERE, 'sabertann.blend')
WATER = 0.9                  # v6: he stands tall (drawing); in the intro the water reaches the cuffs
NFR = 7                      # 4 swim frames + 3 leap frames

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection

# ---------------------------------------------------------------- materials
KEY = dict(body=(38, 38, 46), hat=(30, 30, 38), red=(142, 26, 28), gold=(224, 176, 48),
           white=(216, 220, 232), ink=(12, 12, 16), foam=(236, 244, 255))
def lin(c):
    c = c / 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
MATS = {}
def material(name, key=None, image=None, alpha=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    if key:
        r, g, b = KEY[key]
        bsdf.inputs['Base Color'].default_value = (lin(r), lin(g), lin(b), 1)
        m['key'] = key
    if image:
        img = bpy.data.images.load(os.path.join(TEX, image), check_existing=True)
        tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img; tn.interpolation = 'Closest'
        nt.links.new(tn.outputs['Color'], bsdf.inputs['Base Color'])
        if alpha:
            nt.links.new(tn.outputs['Alpha'], bsdf.inputs['Alpha'])
        m['image'] = image
    m['alpha'] = 1 if alpha else 0
    m.use_fake_user = True
    MATS[name] = m
    return m
for k in ('body', 'hat', 'red', 'gold', 'white', 'ink', 'foam'):
    material(k, k)
material('sail_main', 'white', 'sail_main.png')
material('sail_rear', 'white', 'sail_rear.png')
material('flag', 'white', 'flag.png')
material('emblem', 'gold', 'hat_emblem.png', alpha=True)
material('skull_plate', 'gold', 'skull_plate.png')
sys.path.insert(0, HERE)
import skull_shape

PART_ID = {}
def finish(o, mat, part):
    o.data.materials.clear(); o.data.materials.append(MATS[mat])
    if part not in PART_ID: PART_ID[part] = len(PART_ID) + 1
    o.pass_index = PART_ID[part]
    o['part'] = part
    for p in o.data.polygons: p.use_smooth = True
    return o

def obj_from_bm(name, bm):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o)
    return o

# ---------------------------------------------------------------- helpers
def ellipsoid(name, loc, rad, seg=20, ring=12, rot=(0, 0, 0)):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=1.0)
    bmesh.ops.scale(bm, vec=Vector(rad), verts=bm.verts)
    bmesh.ops.rotate(bm, cent=Vector((0, 0, 0)), matrix=Matrix.LocRotScale(None, __import__('mathutils').Euler(rot), None).to_3x3(), verts=bm.verts)
    bmesh.ops.translate(bm, vec=Vector(loc), verts=bm.verts)
    return obj_from_bm(name, bm)

def tube(name, pts, radii, seg=8, cap=True, flat=1.0):
    """tube along a polyline; radii per point (0 = pointed tip). flat squashes the cross-section in its local x."""
    bm = bmesh.new(); rings = []
    pts = [Vector(p) for p in pts]
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        a = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
        u = t.cross(a).normalized(); v = t.cross(u).normalized()
        r = radii[i]
        if r <= 0:
            rings.append([bm.verts.new(p)]); continue
        ring = []
        for k in range(seg):
            th = 2 * math.pi * k / seg
            ring.append(bm.verts.new(p + u * math.cos(th) * r * flat + v * math.sin(th) * r))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1 and len(b) == 1: continue
        if len(a) == 1:
            for k in range(seg): bm.faces.new((a[0], b[k], b[(k + 1) % seg]))
        elif len(b) == 1:
            for k in range(seg): bm.faces.new((a[k], b[0], a[(k + 1) % seg]))
        else:
            for k in range(seg): bm.faces.new((a[k], b[k], b[(k + 1) % seg], a[(k + 1) % seg]))
    if cap:
        for ring in (rings[0], rings[-1]):
            if len(ring) > 2: bm.faces.new(ring if ring is rings[-1] else ring[::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(name, bm)

def grid(name, nu, nv, fn):
    """grid surface; fn(u,v) -> (x,y,z) with u,v in 0..1; gets UVs"""
    bm = bmesh.new(); V = []
    uvl = bm.loops.layers.uv.new('UVMap')
    for j in range(nv + 1):
        V.append([bm.verts.new(fn(i / nu, j / nv)) for i in range(nu + 1)])
    for j in range(nv):
        for i in range(nu):
            f = bm.faces.new((V[j][i], V[j][i + 1], V[j + 1][i + 1], V[j + 1][i]))
            for lp, (a, b) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                lp[uvl].uv = (a / nu, b / nv)
    o = obj_from_bm(name, bm)
    o['two_sided'] = 1
    return o

def solidify(o, t):
    m = o.modifiers.new('solid', 'SOLIDIFY'); m.thickness = t; m.offset = 0

