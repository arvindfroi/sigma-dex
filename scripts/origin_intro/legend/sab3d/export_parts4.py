"""Blender (headless): Sabertann as a DS model built like Ho-Oh's: every part is reduced ON ITS OWN (no voxel union, so no
blobs and no lost trims) and keeps its own colour. Painted parts (body, hull, hat, deck, stern, mast, nose) get their
procedural colour baked to their own vertices first, so the colour regions come from the material masks, not from a noisy
texture bake. Sails and flag keep their UVs and image. Smooth normals per part for the DS light. Eyes are quads in front of
the eye balls that carry a drawn eye (like Ho-Oh's hou_eye). Tiny parts (posts, teeth, mouth inside) are dropped.
blender -b sab_v15.blend --python export_parts4.py -- OUT [SHIFT=0.8] [LIFT=0.7]
Writes OUT_parts.json: polys with p (3 corners), n (3 normals), c (face colour 0-255 or None), uv (sails/flag), tex
('sail'/'flag'/None), part, g (0 body, 1 head, 2 cloth), b (main bone), vb (bone per corner), r (role: 1 claw, 2/3 eye)."""
import bpy, bmesh, sys, json, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
argv = sys.argv[sys.argv.index('--') + 1:]; OUT = argv[0]
SHIFT = float(argv[1]) if len(argv) > 1 else 0.8; LIFT = float(argv[2]) if len(argv) > 2 else 0.7
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 1
rig = bpy.data.objects['Rig']; rig.data.pose_position = 'REST'
BUDGET = {'Body': 300, 'Hull': 110, 'Hat': 120, 'HatEdge': 110, 'Deck': 24, 'Stern': 36, 'Mast': 10, 'Nose': 6, 'Rail': 24,
          'Sail': 44, 'Flag': 6, 'Tusk': 16, 'SkullHead': 22, 'SkullCheek': 6, 'SkullJaw': 6, 'SkullMaxilla': 6, 'SkullMouth': 6,
          'EyeHole': 4, 'EyeRim': 6, 'SkNose': 2, 'Brow': 8, 'Claw': 4}
DROP = ('Post', 'Tooth', 'LowTooth', 'Palate', 'MouthIn', 'Tongue', 'Eye1')       # Eye1 balls: replaced by drawn eye quads
STERN = ('Stern', 'Skull', 'SkNose', 'EyeHole', 'EyeRim')
GRIDS = {'Sail': (3, 3), 'Flag': (2, 2)}
REMESH = {'Body': 140, 'Hull': 140, 'Hat': 170, 'Deck': 50, 'Stern': 110, 'Mast': 90, 'Rail': 200, 'Tusk': 80, 'Nose': 60}
dg = bpy.context.evaluated_depsgraph_get()
def base_name(n):
    b = n.split('.')[0]
    for k in sorted(BUDGET, key=len, reverse=True):
        if b.startswith(k): return k
    return b
def activate(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
def copy_rest(o):
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    c = bpy.data.objects.new(o.name + '_c', me); c.matrix_world = o.matrix_world.copy(); sc.collection.objects.link(c)
    for g in o.vertex_groups: c.vertex_groups.new(name=g.name)
    for v in o.data.vertices:
        for ge in v.groups: c.vertex_groups[o.vertex_groups[ge.group].name].add([v.index], ge.weight, 'REPLACE')
    for m in o.data.materials: c.data.materials.append(m)
    activate(c); bpy.ops.object.transform_apply(location=True, rotation=True, scale=True); return c
def bake_vcol(c):                                         # procedural colour -> own vertices ('alb' per vertex: corner colours block the decimation)
    if 'alb' not in c.data.color_attributes: c.data.color_attributes.new('alb', 'FLOAT_COLOR', 'POINT')
    c.data.color_attributes.active_color = c.data.color_attributes['alb']
    activate(c); sc.render.bake.target = 'VERTEX_COLORS'; sc.render.bake.use_selected_to_active = False
    bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
def decimate_to(o, target):
    activate(o)
    for _ in range(20):
        n = sum(len(p.vertices) - 2 for p in o.data.polygons)
        if n <= target * 1.08: break
        mod = o.modifiers.new('dec', 'DECIMATE'); mod.ratio = max(0.15, target / n); mod.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier='dec')

def drop_small(o, frac=0.03):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table(); seen = set(); kill = []
    for v in bm.verts:
        if v.index in seen: continue
        st = [v]; comp = []; seen.add(v.index)
        while st:
            x = st.pop(); comp.append(x)
            for e in x.link_edges:
                y = e.other_vert(x)
                if y.index not in seen: seen.add(y.index); st.append(y)
        if len(comp) < frac * len(bm.verts): kill += comp
    bmesh.ops.delete(bm, geom=kill, context='VERTS'); bm.to_mesh(o.data); bm.free()
def remeshed(hp, target, div=140):
    """octree remesh closes the part (the Hunyuan skins are open and overlap), a voxel pass makes it manifold so it can be
    decimated; loose crumbs dropped. Each part on its own, so parts keep their own shape and colour."""
    lp = hp.copy(); lp.data = hp.data.copy(); sc.collection.objects.link(lp); lp.name = hp.name + '_lp'
    activate(lp); rm = lp.modifiers.new('rm', 'REMESH'); rm.mode = 'SMOOTH'; rm.octree_depth = 7; rm.scale = 0.9
    rm.use_remove_disconnected = False; bpy.ops.object.modifier_apply(modifier='rm')
    rm = lp.modifiers.new('rm', 'REMESH'); rm.mode = 'VOXEL'; rm.voxel_size = max(hp.dimensions) / div
    bpy.ops.object.modifier_apply(modifier='rm'); drop_small(lp); decimate_to(lp, target); return lp
def grids(hp, nu, nv):
    bm = bmesh.new(); bm.from_mesh(hp.data); bm.verts.ensure_lookup_table(); seen = set(); islands = []
    for v in bm.verts:
        if v.index in seen: continue
        st = [v]; isl = []; seen.add(v.index)
        while st:
            x = st.pop(); isl.append(x.co.copy())
            for e in x.link_edges:
                y = e.other_vert(x)
                if y.index not in seen: seen.add(y.index); st.append(y)
        if len(isl) > 20: islands.append(isl)
    bm.free(); out = bmesh.new()
    for isl in islands:
        P = np.array([tuple(p) for p in isl]); c = P.mean(0); u, s_, vt = np.linalg.svd(P - c)
        a, b = vt[0], vt[1]; pa = (P - c) @ a; pb = (P - c) @ b
        vs = [[out.verts.new(Vector(c + a * (pa.min() + (pa.max() - pa.min()) * i / (nu - 1)) + b * (pb.min() + (pb.max() - pb.min()) * j / (nv - 1))))
               for j in range(nv)] for i in range(nu)]
        for i in range(nu - 1):
            for j in range(nv - 1): out.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1]))
    me = bpy.data.meshes.new(hp.name + '_grid'); out.to_mesh(me); out.free()
    lp = bpy.data.objects.new(hp.name + '_lp', me); sc.collection.objects.link(lp)
    activate(lp); sw = lp.modifiers.new('sw', 'SHRINKWRAP'); sw.target = hp; sw.wrap_method = 'NEAREST_SURFACEPOINT'
    bpy.ops.object.modifier_apply(modifier='sw'); return lp
def sampler(hp):
    """nearest original face -> its colour ('alb' per vertex), material, UV at the hit point, main bone"""
    me = hp.data; bm = bmesh.new(); bm.from_mesh(me); tree = BVHTree.FromBMesh(bm); bm.free()
    ca = me.color_attributes.get('alb'); uvl = me.uv_layers.active.data if me.uv_layers else None
    names = [g.name for g in hp.vertex_groups]
    def at(pt):
        loc, nrm, fi, d = tree.find_nearest(Vector(tuple(pt)))
        p = me.polygons[fi]; col = None; uv = None
        if ca is not None: col = np.array([ca.data[i].color[:3] for i in p.vertices]).mean(0)
        if uvl is not None:                                  # barycentric-ish: nearest corner's UV is enough for flat cloth
            vs = [np.array(me.vertices[i].co[:]) for i in p.vertices]; k = int(np.argmin([np.linalg.norm(v - np.array(loc[:])) for v in vs]))
            uv = list(uvl[p.loop_indices[k]].uv)
        w = {}
        for i in p.vertices:
            for ge in me.vertices[i].groups: w[names[ge.group]] = w.get(names[ge.group], 0) + ge.weight
        bone = max(w, key=w.get) if w else 'spine'
        return col, p.material_index, uv, bone
    return at

src = [o for o in bpy.data.objects if o.type == 'MESH' and o.visible_get()]
polys = []; eyes = []; parts = {}
for o in src:
    bn = base_name(o.name)
    if any(o.name.startswith(k) for k in DROP):
        if o.name.startswith('Eye1'): eyes.append(copy_rest(o))
        continue
    c = copy_rest(o)
    if bn in STERN or o.name.startswith(STERN):
        for v in c.data.vertices: v.co.y -= SHIFT; v.co.z += LIFT     # the stern skull in against the hull and up (concept)
    mats = [m.name if m else '' for m in o.data.materials]
    painted = 'paint' in mats
    if painted: bake_vcol(c)
    solid = None
    if not painted and mats:
        m = o.data.materials[0]; bsdf = [n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'] if m.use_nodes else []
        col = bsdf[0].inputs['Base Color'].default_value[:3] if bsdf else m.diffuse_color[:3]
        solid = [int(255 * min(1, max(0, x)) ** (1 / 2.2)) for x in col]
    at = sampler(c)
    if bn in GRIDS: lp = grids(c, *GRIDS[bn])
    elif bn in REMESH: lp = remeshed(c, BUDGET.get(bn, 30), REMESH[bn])
    elif bn == 'HatEdge':
        lp = c.copy(); lp.data = c.data.copy(); sc.collection.objects.link(lp); lp.name = c.name + '_lp'; decimate_to(lp, BUDGET[bn])
        P_ = np.array([v.co[:] for v in lp.data.vertices]); cc = P_.mean(0)
        for v in lp.data.vertices: v.co = Vector(tuple(cc + (np.array(v.co[:]) - cc) * np.array([1.04, 1.04, 1.0]) + np.array([0, 0, 0.02])))
    else:
        lp = c.copy(); lp.data = c.data.copy(); sc.collection.objects.link(lp); lp.name = c.name + '_lp'; decimate_to(lp, BUDGET.get(bn, 6))
    if bn == 'Sail':                                        # the sail hangs in front of the mast (concept): no mast across the skull
        for v in lp.data.vertices: v.co.y -= 0.12
    bm = bmesh.new(); bm.from_mesh(lp.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(lp.data); bm.free()
    me = lp.data
    vn = np.zeros((len(me.vertices), 3))                      # smooth normals within the part
    for p in me.polygons:
        for i in p.vertices: vn[i] += np.array(p.normal[:]) * p.area
    vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-9
    vbone = [at(me.vertices[i].co)[3] for i in range(len(me.vertices))]
    for p in me.polygons:
        cen = np.mean([np.array(me.vertices[i].co[:]) for i in p.vertices], 0)
        fcol, fmi, _, fb = at(cen)
        mname = mats[fmi] if fmi < len(mats) else ''
        tex = 'sail' if mname == 'sailtex' else ('flag' if mname == 'flagtex' else None)
        uv = [at(me.vertices[i].co)[2] for i in p.vertices] if tex else None
        col = None if tex else ([int(255 * min(1, max(0, x)) ** (1 / 2.2)) for x in fcol] if fcol is not None else solid)
        vb = [vbone[i] for i in p.vertices]; b = max(set(vb), key=vb.count)
        g = 2 if bn in ('Sail', 'Flag') else (1 if b in ('head', 'jaw') else 0)
        polys.append(dict(p=[list(me.vertices[i].co) for i in p.vertices], n=[list(vn[i]) for i in p.vertices], c=col, uv=uv, tex=tex,
                          part=bn, g=g, b=b, vb=vb, r=1 if bn == 'Claw' else 0))
    parts[bn] = parts.get(bn, 0) + len(me.polygons)
# drawn eyes: a quad just outside the head surface in front of each eye ball, facing forward and a little out
heads = [h for h in bpy.data.objects if h.name.startswith('Body_c_lp')] or [h for h in bpy.data.objects if h.name.startswith('Body_c')]
sbm = bmesh.new(); sbm.from_mesh(heads[0].data); stree = BVHTree.FromBMesh(sbm); sbm.free()
for e in eyes:
    P = np.array([v.co[:] for v in e.data.vertices]); mn, mx = P.min(0), P.max(0); c = (mn + mx) / 2
    side = 1.0 if c[0] > 0 else -1.0; n = np.array([0.35 * side, -1.0, -0.12]); n /= np.linalg.norm(n)
    t1 = np.cross([0, 0, 1.0], n); t1 /= np.linalg.norm(t1); t2 = np.cross(n, t1)
    w, h = (mx[0] - mn[0]) * 0.75, (mx[2] - mn[2]) * 0.55
    hit = stree.ray_cast(Vector(tuple(c + n * 1.5)), Vector(tuple(-n)), 3.0)
    ctr = (np.array(hit[0][:]) + n * 0.06) if hit[0] is not None else c - n * 0.0
    q = [ctr - w * t1 - h * t2, ctr + w * t1 - h * t2, ctr + w * t1 + h * t2, ctr - w * t1 + h * t2]
    uvq = [(0, 0), (1, 0), (1, 1), (0, 1)] if side > 0 else [(1, 0), (0, 0), (0, 1), (1, 1)]
    for tri in ((0, 1, 2), (0, 2, 3)):
        polys.append(dict(p=[list(q[k]) for k in tri], n=[list(n)] * 3, c=None, uv=[list(uvq[k]) for k in tri], tex='eye', part='Eye',
                          g=1, b='head', vb=['head'] * 3, r=2 if side > 0 else 3))
hats = [h for h in bpy.data.objects if h.name.startswith('Hat_c_lp')]
if hats:
    hm = hats[0]; hb = bmesh.new(); hb.from_mesh(hm.data); htree = BVHTree.FromBMesh(hb); hb.free()
    HP_ = np.array([v.co[:] for v in hm.data.vertices]); hmn, hmx = HP_.min(0), HP_.max(0); hc = (hmn + hmx) / 2
    n = np.array([0, -1.0, 0.45]); n /= np.linalg.norm(n); origin = np.array([hc[0], hmn[1] - 1.5, hc[2] + 0.10 * (hmx[2] - hmn[2])])
    hit = htree.ray_cast(Vector(tuple(origin)), Vector((0, 1.0, 0)), 5.0)
    if hit[0] is not None:
        ctr = np.array(hit[0][:]) + n * 0.05; t1 = np.array([1.0, 0, 0]); t2 = np.cross(n, t1); t2 /= np.linalg.norm(t2)
        w, h = 0.30, 0.23
        q = [ctr - w * t1 - h * t2, ctr + w * t1 - h * t2, ctr + w * t1 + h * t2, ctr - w * t1 + h * t2]
        uvq = [(0, 0), (1, 0), (1, 1), (0, 1)]
        for tri in ((0, 1, 2), (0, 2, 3)):
            polys.append(dict(p=[list(q[k]) for k in tri], n=[list(n)] * 3, c=None, uv=[list(uvq[k]) for k in tri], tex='emblem', part='Emblem',
                              g=1, b='head', vb=['head'] * 3, r=0))
        print('EMBLEM at', np.round(ctr, 2))
json.dump(dict(polys=polys), open(OUT + '_parts.json', 'w'))
print('PARTS', parts, 'TOTAL', len(polys))
