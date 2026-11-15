import bpy, bmesh, sys, json, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
argv = sys.argv[sys.argv.index('--') + 1:]; OUT = argv[0]
SHIFT = float(argv[1]) if len(argv) > 1 else 0.8; LIFT = float(argv[2]) if len(argv) > 2 else 0.7
MASTFWD = float(argv[3]) if len(argv) > 3 else 0.7; STERNSCALE = float(argv[4]) if len(argv) > 4 else 1.35
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 4
rig = bpy.data.objects['Rig']; rig.data.pose_position = 'REST'
BUDGET = {'Body': 330, 'Hull': 100, 'Hat': 110, 'Deck': 18, 'Stern': 28, 'Mast': 10, 'Nose': 6, 'Rail': 16, 'Sail': 44, 'Flag': 6,
          'Tusk': 8, 'SkullHead': 40, 'SkullCheek': 6, 'SkullJaw': 8, 'SkullMaxilla': 8, 'SkullMouth': 8, 'EyeHole': 4,
          'EyeRim': 8, 'SkNose': 2, 'Brow': 6, 'Claw': 4}
LPDROP = ('Post', 'Tooth', 'LowTooth', 'Palate', 'MouthIn', 'Tongue', 'Eye1', 'HatEdge')   # baked into the texture, no geometry
STERN = ('Stern', 'Skull', 'SkNose', 'EyeHole', 'EyeRim', 'Tooth')
GRIDS = {'Sail': (3, 3), 'Flag': (2, 2)}
REMESH = {'Body': 140, 'Hull': 140, 'Hat': 170, 'Deck': 60, 'Stern': 110, 'Mast': 90, 'Rail': 200, 'Tusk': 80, 'Nose': 60, 'SkullHead': 80}
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
# ---------------------------------------------------------------------------------------------------------------- v5 main
"""v5 (Arvind 2026-11-16: follow MY design; the back is a ship (Den sorte dame), not a shell; the stern skull bigger and like
the ship's; the hat as drawn; no gap at the neck; verify yourself): the high-poly model already is the design, so it is
carried over faithfully — every part reduced on its own, the colours BAKED from the high-poly into textures (hull stripe,
deck planks, gold rail and leg rings, hat trim and emblem, skull eyes and teeth) instead of one flat colour per polygon.
Teeth, rail posts and the inside of the mouth are bake sources only. Eyes and mouth are drawn decals."""
src = [o for o in bpy.data.objects if o.type == 'MESH' and o.visible_get()]
HP = []; PARTS = []; eyes = []; copies = {}
for o in src:
    bn = base_name(o.name); c = copy_rest(o)
    vg = [g.name for g in o.vertex_groups]
    if o.name.startswith(STERN) or vg == ['stern']:
        for v in c.data.vertices: v.co.y -= SHIFT; v.co.z += LIFT
        c['stern'] = 1
    if bn in ('Mast', 'Sail', 'Flag'):
        for v in c.data.vertices: v.co.y -= MASTFWD; v.co.z += 0.2
    if 'paint' in [m.name if m else '' for m in o.data.materials]: pass
    if o.name.startswith('Eye1'): eyes.append(c); continue     # glowing eye balls: replaced by drawn eyes, not baked
    HP.append(c); copies.setdefault(bn, []).append(c)
    if not any(o.name.startswith(k) for k in LPDROP): PARTS.append((bn, c))
# the stern skull bigger (Arvind: too small next to Den sorte dame's), about the skull's centre
sk = copies.get('SkullHead', [None])[0]
if sk is not None and STERNSCALE != 1:
    SC_ = np.array([v.co[:] for v in sk.data.vertices]).mean(0)
    for c in HP:
        if c.get('stern'):
            for v in c.data.vertices: v.co = Vector(tuple(SC_ + (np.array(v.co[:]) - SC_) * STERNSCALE))
BONES = [b.name for b in rig.data.bones]; HEADB = ('head', 'jaw')
def hat_retopo(target):
    # retopology: a clean hat mesh (crown + brim rings, 16 around) fitted to the hat's box, then every point pulled onto the
    # high-poly hat's surface, so it takes the drawn hat's real shape (brim, curl, front point) with a clean mesh
    P_ = np.array([(target.matrix_world @ v.co)[:] for v in target.data.vertices]); mn, mx = P_.min(0), P_.max(0)
    cx, cy = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2; rx, ry = (mx[0] - mn[0]) / 2, (mx[1] - mn[1]) / 2; z0 = mn[2]; H_ = mx[2] - mn[2]
    N = 12; RINGS = [(0.50, 0.05), (1.00, 0.17), (1.00, 0.24), (0.78, 0.23), (0.56, 0.30), (0.52, 0.60), (0.38, 0.85)]
    verts = []; base = []
    for rr, hh in RINGS:
        base.append(len(verts))
        for i in range(N):
            t = 2 * math.pi * i / N; verts.append((cx + rx * rr * math.cos(t), cy + ry * rr * math.sin(t), z0 + H_ * hh))
    top = len(verts); verts.append((cx, cy, z0 + H_))
    faces = []
    for a, b_ in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6)):
        for i in range(N): j = (i + 1) % N; faces.append((base[a] + i, base[a] + j, base[b_] + j, base[b_] + i))
    for i in range(N): faces.append((base[6] + i, base[6] + (i + 1) % N, top))
    me_ = bpy.data.meshes.new('Hat_retopo'); me_.from_pydata(verts, [], faces); me_.update()
    br = me_.attributes.new('brim', 'INT', 'FACE')
    for k in range(N, 2 * N): br.data[k].value = 1                          # the brim's edge band: the gold trim
    ob = bpy.data.objects.new('Hat_retopo', me_); sc.collection.objects.link(ob); activate(ob)
    sw = ob.modifiers.new('sw', 'SHRINKWRAP'); sw.target = target; sw.wrap_method = 'NEAREST_SURFACEPOINT'; sw.offset = 0.01
    bpy.ops.object.modifier_apply(modifier='sw'); return ob
def finish(lp, bn, at, forced=None):
    for g in list(lp.vertex_groups): lp.vertex_groups.remove(g)
    me = lp.data
    if me.uv_layers: [me.uv_layers.remove(u) for u in list(me.uv_layers)]
    for nm in [a.name for a in me.attributes if a.name in ('grp', 'role', 'bid', 'pid')]: me.attributes.remove(me.attributes[nm])
    upright_ok = True
    if bn in GRIDS:                                            # cloth: keep only standing sails (a lying spar / flat yards dropped)
        bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table(); kill = []
        bm.faces.ensure_lookup_table()
        # islands of the grid object
        seen = set(); comps = []
        for f in bm.faces:
            if f.index in seen: continue
            st = [f]; comp = []; seen.add(f.index)
            while st:
                x = st.pop(); comp.append(x)
                for e in x.edges:
                    for y in e.link_faces:
                        if y.index not in seen: seen.add(y.index); st.append(y)
            comps.append(comp)
        for comp in comps:
            P_ = np.array([v.co[:] for f in comp for v in f.verts]); u_, s_, vt = np.linalg.svd(P_ - P_.mean(0))
            if abs(vt[2][2]) > 0.6 or np.ptp(P_[:, 2]) < 0.35: kill += comp
        bmesh.ops.delete(bm, geom=list(set(kill)), context='FACES'); bm.to_mesh(me); bm.free()
    bid = me.attributes.new('bid', 'INT', 'POINT'); pid = me.attributes.new('pid', 'INT', 'FACE'); grp = me.attributes.new('grp', 'INT', 'FACE'); role = me.attributes.new('role', 'INT', 'FACE')
    vb = [forced] * len(me.vertices) if forced else [at(v.co)[3] for v in me.vertices]
    for i, b in enumerate(vb): bid.data[i].value = BONES.index(b) if b in BONES else BONES.index('spine')
    for p in me.polygons:
        pid.data[p.index].value = len(LP); role.data[p.index].value = 1 if bn == 'Claw' else (6 if (me.attributes.get('brim') and me.attributes['brim'].data[p.index].value) else 0)
        bs = [vb[i] for i in p.vertices] if len(vb) == len(me.vertices) else ['spine']
        grp.data[p.index].value = 2 if bn in GRIDS else (1 if max(set(bs), key=bs.count) in HEADB else 0)
    lp['part'] = bn; LP.append(lp)
SEGOF = {'root': 'spine', 'spine': 'spine', 'stern': 'spine', 'mast': 'spine', 'flag': 'spine', 'head': 'head', 'jaw': 'head'}
SEGBUDGET = {'spine': 120, 'head': 70}
def body_segments(c):
    """DS-style rigid segments (like Ho-Oh's): the high-poly body cut by its bone weights into torso, head and upper/lower
    legs, each grown two rings into its neighbours (overlap), closed and reduced on its own and moved by ONE bone, so a
    joint never stretches or tears when the legs swing."""
    me = c.data; names = [g.name for g in c.vertex_groups]
    vseg = []
    for v in me.vertices:
        b = names[max(v.groups, key=lambda ge: ge.weight).group] if len(v.groups) else 'spine'
        vseg.append(SEGOF.get(b, b))
    bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table(); out = []
    fseg = [max(set(vseg[v.index] for v in f.verts), key=[vseg[v.index] for v in f.verts].count) for f in bm.faces]
    vsize = max(c.dimensions) / 140
    for seg in sorted(set(fseg)):
        sel = {f.index for f in bm.faces if fseg[f.index] == seg}
        for _ in range(2):                                     # overlap into the neighbours
            grow = set()
            for fi in sel:
                for v in bm.faces[fi].verts:
                    for f2 in v.link_faces: grow.add(f2.index)
            sel |= grow
        sub = bmesh.new()
        vmap = {}
        for fi in sel:
            f = bm.faces[fi]; vs = []
            for v in f.verts:
                if v.index not in vmap: vmap[v.index] = sub.verts.new(v.co)
                vs.append(vmap[v.index])
            try: sub.faces.new(vs)
            except ValueError: pass
        m2 = bpy.data.meshes.new('Body_' + seg); sub.to_mesh(m2); sub.free()
        o2 = bpy.data.objects.new('Body_' + seg, m2); sc.collection.objects.link(o2); o2.matrix_world = c.matrix_world.copy()
        div = max(max(o2.dimensions) / vsize, 20)
        lp = remeshed(o2, SEGBUDGET.get(seg, 16), div)
        if len(lp.data.polygons) < 4: continue
        out.append((lp, seg))
    bm.free(); print('SEGMENTS', [(s_, len(l.data.polygons)) for l, s_ in out]); return out
LP = []
for bn, c in PARTS:
    at = sampler(c)
    if bn == 'Hat':                                            # hat + its gold trim as one closed shape (no floating ring)
        tmp = [c.copy() for _ in range(1)]; tmp[0].data = c.data.copy(); sc.collection.objects.link(tmp[0])
        for he in copies.get('HatEdge', []):
            t2 = he.copy(); t2.data = he.data.copy(); sc.collection.objects.link(t2); tmp.append(t2)
        bpy.ops.object.select_all(action='DESELECT')
        for t in tmp: t.select_set(True)
        bpy.context.view_layer.objects.active = tmp[0]; bpy.ops.object.join(); src_ = tmp[0]
        lp = hat_retopo(src_)
    elif bn == 'Body':
        for lp_, seg in body_segments(c): lp_['seg'] = seg; finish(lp_, bn, at, seg)
        continue
    elif bn in GRIDS: lp = grids(c, *GRIDS[bn])
    elif bn in REMESH: lp = remeshed(c, BUDGET.get(bn, 30), REMESH[bn])
    else:
        lp = c.copy(); lp.data = c.data.copy(); sc.collection.objects.link(lp); decimate_to(lp, BUDGET.get(bn, 6))
    finish(lp, bn, at)
PARTNAMES = [l['part'] for l in LP]
print('LP', {n: sum(len(l.data.polygons) for l in LP if l['part'] == n) for n in set(PARTNAMES)})
# decals: drawn eyes (role 2/3) and mouth (role 4) as quads just outside the low-poly face
body_lp = ([l for l in LP if l.get('seg') == 'head'] or [l for l in LP if l['part'] == 'Body'])[0]
bbm = bmesh.new(); bbm.from_mesh(body_lp.data); btree = BVHTree.FromBMesh(bbm); bbm.free()
def decal(name, ctr, n, w, h, rl, flip=False):
    t1 = np.cross([0, 0, 1.0], n); t1 /= np.linalg.norm(t1); t2 = np.cross(n, t1)
    q = [ctr - w * t1 - h * t2, ctr + w * t1 - h * t2, ctr + w * t1 + h * t2, ctr - w * t1 + h * t2]
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in q], [], [(0, 1, 2, 3)]); me.update()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob)
    for nm_, dom in (('bid', 'POINT'), ('pid', 'FACE'), ('grp', 'FACE'), ('role', 'FACE')): me.attributes.new(nm_, 'INT', dom)
    for i in range(4): me.attributes['bid'].data[i].value = BONES.index('head')
    me.attributes['pid'].data[0].value = len(LP); me.attributes['grp'].data[0].value = 1; me.attributes['role'].data[0].value = rl
    ob['part'] = name; ob['flip'] = 1 if flip else 0; LP.append(ob); return ob
for e in eyes:
    P_ = np.array([v.co[:] for v in e.data.vertices]); mn, mx = P_.min(0), P_.max(0); c = (mn + mx) / 2
    side = 1.0 if c[0] > 0 else -1.0; n = np.array([0.35 * side, -1.0, -0.12]); n /= np.linalg.norm(n)
    hit = btree.ray_cast(Vector(tuple(c + n * 1.5)), Vector(tuple(-n)), 3.0)
    ctr = (np.array(hit[0][:]) + n * 0.05) if hit[0] is not None else c
    decal('Eye', ctr, n, (mx[0] - mn[0]) * 0.75, (mx[2] - mn[2]) * 0.55, 2 if side > 0 else 3, flip=side < 0)
no = copies.get('Nose', [None])[0]
if no is not None:
    NP_ = np.array([v.co[:] for v in no.data.vertices]); nc = NP_.mean(0); nb = NP_[:, 2].min()
    n = np.array([0, -1.0, -0.15]); n /= np.linalg.norm(n)
    hit = btree.ray_cast(Vector((nc[0], nc[1] - 1.5, nb - 0.17)), Vector((0, 1.0, 0)), 4.0)
    if hit[0] is not None: decal('Mouth', np.array(hit[0][:]) + n * 0.04, n, 0.40, 0.20, 4)
hatlp = [l for l in LP if l['part'] == 'Hat']
if hatlp:
    hb = bmesh.new(); hb.from_mesh(hatlp[0].data); htree = BVHTree.FromBMesh(hb); hb.free()
    HP_ = np.array([v.co[:] for v in hatlp[0].data.vertices]); hmn, hmx = HP_.min(0), HP_.max(0); hc = (hmn + hmx) / 2
    n = np.array([0, -1.0, 0.35]); n /= np.linalg.norm(n)
    hit = htree.ray_cast(Vector((hc[0], hmn[1] - 2.0, hmn[2] + 0.58 * (hmx[2] - hmn[2]))), Vector((0, 1.0, 0)), 6.0)
    if hit[0] is not None: decal('Emblem', np.array(hit[0][:]) + n * 0.04, n, 0.30, 0.22, 5); print('EMBLEM ok')
PARTNAMES = [l['part'] for l in LP]
# join, triangulate
bpy.ops.object.select_all(action='DESELECT')
for l in LP: l.select_set(True)
bpy.context.view_layer.objects.active = LP[0]; bpy.ops.object.join(); L = bpy.context.view_layer.objects.active; L.name = 'LP'
bm = bmesh.new(); bm.from_mesh(L.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.to_mesh(L.data); bm.free()
me = L.data
SIZES = {0: (128, 128), 1: (64, 64), 2: (32, 64)}
grp = [me.attributes['grp'].data[p.index].value for p in me.polygons]; role = [me.attributes['role'].data[p.index].value for p in me.polygons]
pidv = [me.attributes['pid'].data[p.index].value for p in me.polygons]
activate(L); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(80), island_margin=0.5 / 128, area_weight=1.0)   # big islands = long strips
bpy.ops.object.mode_set(mode='OBJECT')
uvl = me.uv_layers.active.data
def key(li): u = uvl[li].uv; return (round(u[0], 5), round(u[1], 5))
edge_faces = {}
for p in me.polygons:
    for k in range(len(p.vertices)):
        v1, v2 = p.vertices[k], p.vertices[(k + 1) % len(p.vertices)]; l1, l2 = p.loop_indices[k], p.loop_indices[(k + 1) % len(p.vertices)]
        e = (min(v1, v2), max(v1, v2)); uvp = tuple(sorted([(v1, key(l1)), (v2, key(l2))])); edge_faces.setdefault((e, uvp), []).append(p.index)
par = list(range(len(me.polygons)))
def find(x):
    while par[x] != x: par[x] = par[par[x]]; x = par[x]
    return x
for fs in edge_faces.values():
    for f in fs[1:]:
        if grp[f] == grp[fs[0]] and pidv[f] == pidv[fs[0]]: par[find(f)] = find(fs[0])
isl = {}
for p in me.polygons: isl.setdefault(find(p.index), []).append(p.index)
for g in (0, 1, 2):                                            # our own shelf packer per texture (uv.pack_islands is a no-op here)
    w, h = SIZES[g]; asp = w / h; I = []
    for r, fs in isl.items():
        if grp[fs[0]] != g or role[fs[0]] >= 2: continue
        lis = [li for f in fs for li in me.polygons[f].loop_indices]
        uv = np.array([uvl[li].uv[:] for li in lis]); mn, mx = uv.min(0), uv.max(0); I.append((lis, mn, np.maximum(mx - mn, 1e-4)))
    I.sort(key=lambda t: -t[2][1]); pad = 1.5 / min(w, h); V0 = {0: 0.0, 1: 12 / 64, 2: 0.0}[g]
    def place(scl):
        x = y = 0.0; rowh = 0.0; pos = []
        for lis, mn, sz in I:
            sw, sh = sz[0] * scl / asp, sz[1] * scl
            if x + sw > 1.0: x = 0.0; y += rowh + pad; rowh = 0.0
            pos.append((x, y)); x += sw + pad; rowh = max(rowh, sh)
        return pos, y + rowh
    lo, hi = 0.01, 60.0
    for _ in range(40):
        mid = (lo + hi) / 2; _, top = place(mid)
        if top <= 1.0 - V0: lo = mid
        else: hi = mid
    pos, _ = place(lo)
    for (lis, mn, sz), (x, y) in zip(I, pos):
        for li in lis: u = uvl[li].uv; uvl[li].uv = (x + (u[0] - mn[0]) * lo / asp, V0 + y + (u[1] - mn[1]) * lo)
    print('PACK', g, len(I), 'islands, scale', round(lo, 3))
for p in me.polygons:                                          # decals: fixed UVs in the bottom strip of texture 1 (drawn later)
    if role[p.index] < 2: continue
    vs = np.array([me.vertices[i].co[:] for i in p.vertices]); quad = [me.vertices[i].co for i in p.vertices]
    # quad corners in creation order: map by position in the decal's own axes
    c0 = vs.mean(0)
    for li, vi in zip(p.loop_indices, p.vertices):
        uvl[li].uv = (0, 0)
DEC = {}
for p in me.polygons:
    if role[p.index] >= 2: DEC.setdefault(pidv[p.index], []).append(p.index)
for pid_, fs in DEC.items():                                   # planar UVs over each decal quad
    vids = sorted({vi for f in fs for vi in me.polygons[f].vertices}); V = np.array([me.vertices[i].co[:] for i in vids]); c0 = V.mean(0)
    u_, s_, vt = np.linalg.svd(V - c0); ax1 = vt[0] if abs(vt[0][0]) > abs(vt[1][0]) else vt[1]; ax1 = ax1 * np.sign(ax1[0])
    ax2 = np.cross(vt[2], ax1); ax2 = ax2 * (1 if ax2[2] >= 0 else -1)
    a = (V - c0) @ ax1; b = (V - c0) @ ax2; A = {vi: ((x - a.min()) / np.ptp(a), (y - b.min()) / np.ptp(b)) for vi, x, y in zip(vids, a, b)}
    rl = role[fs[0]]
    if rl == 6:
        for f in fs:
            for li in me.polygons[f].loop_indices: uvl[li].uv = (60.5 / 64, 9.5 / 64)        # gold patch
        continue
    for f in fs:
        for li, vi in zip(me.polygons[f].loop_indices, me.polygons[f].vertices):
            uu, vv = A[vi]
            if rl == 3: uu = 1 - uu                               # right eye: the drawing mirrored
            if rl in (2, 3): uvl[li].uv = (0.5 / 64 + uu * 23 / 64, 0.5 / 64 + vv * 11 / 64)          # eye 24 x 12
            elif rl == 4: uvl[li].uv = (25.5 / 64 + uu * 15 / 64, 0.5 / 64 + vv * 11 / 64)                     # mouth 16 x 12
            else: uvl[li].uv = (42.5 / 64 + uu * 15 / 64, 0.5 / 64 + vv * 11 / 64)                   # hat emblem 16 x 12
# bake the high-poly colours into the three textures
L.data.materials.clear(); IM = {}
for g in (0, 1, 2):
    w, h = SIZES[g]; mat = bpy.data.materials.new(f'grp{g}'); mat.use_nodes = True; nt = mat.node_tree
    im = bpy.data.images.new(f'albedo{g}', w * 4, h * 4); IM[g] = im; tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = im; nt.nodes.active = tn
    L.data.materials.append(mat)
for p in me.polygons: p.material_index = grp[p.index]
bpy.ops.object.select_all(action='DESELECT')
for hcp in HP: hcp.hide_render = False; hcp.select_set(True)
L.select_set(True); bpy.context.view_layer.objects.active = L
sc.render.bake.use_selected_to_active = True; sc.render.bake.cage_extrusion = 0.12; sc.render.bake.max_ray_distance = 0.6; sc.render.bake.margin = 4
sc.render.bake.target = 'IMAGE_TEXTURES'
bpy.ops.object.bake(type='DIFFUSE', pass_filter={'COLOR'})
for g, im in IM.items(): im.filepath_raw = f'{OUT}_albedo{g}.png'; im.file_format = 'PNG'; im.save()
# export in rig3d's format; normals: smooth per part (parts share no vertices)
names = BONES; polys = []
vn = np.zeros((len(me.vertices), 3))
for p in me.polygons:
    for i in p.vertices: vn[i] += np.array(p.normal[:]) * p.area
vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-9
bidv = [me.attributes['bid'].data[i].value for i in range(len(me.vertices))]
for p in me.polygons:
    vb = [names[bidv[i]] for i in p.vertices]
    polys.append(dict(p=[list(me.vertices[i].co) for i in p.vertices], n=[list(vn[i]) for i in p.vertices], uv=[list(uvl[li].uv) for li in p.loop_indices],
                      b=max(set(vb), key=vb.count), g=grp[p.index], r=role[p.index], vb=vb, part=PARTNAMES[pidv[p.index]]))
json.dump(dict(polys=polys), open(OUT + '.json', 'w')); print('EXPORTED', len(polys))
bpy.ops.wm.save_as_mainfile(filepath=OUT + '_lp.blend')
