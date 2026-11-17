# ---------------------------------------------------------------- v6: as close to Arvind's drawing (624.webp) as possible
# A big black sabre-toothed beast standing tall on long legs, a big head held high with a tall round muzzle and a small
# gold nose on top, narrow angry eyes under a bicorne worn fore-and-aft (gold trim, gold skull on the side), long
# white sabres, a gold fang at the jaw. Shaggy gold cuffs on the forelegs, big white claws. On the back a rounded red
# hull: black rim on top, a thick black band low down, triangle gun ports with gold inside, a round port aft, a gold
# skull with two spikes at the stern. Two masts raked aft with white sails (gold skull and crossbones) and a flag.
from mathutils.bvhtree import BVHTree
def metaball_mesh(name, elements, res=0.04):
    mb = bpy.data.metaballs.new(name + 'MB'); mb.resolution = res; mb.render_resolution = res; mb.threshold = 0.6
    mbo = bpy.data.objects.new(name + 'MB', mb); col.objects.link(mbo)
    for co, size in elements:
        e = mb.elements.new(); e.type = 'ELLIPSOID'; e.co = co; e.radius = 1.75   # visible half-axes ~= size
        e.size_x, e.size_y, e.size_z = size; e.stiffness = 2.0
    for o in bpy.context.view_layer.objects: o.select_set(False)
    bpy.context.view_layer.objects.active = mbo; mbo.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.view_layer.objects.active; o.name = name
    dec = o.modifiers.new('dec', 'DECIMATE'); dec.ratio = 0.8           # keep it smooth: the toon light shows facets
    bpy.ops.object.modifier_apply(modifier='dec')
    sm = o.modifiers.new('sm', 'SMOOTH'); sm.factor = 0.6; sm.iterations = 4
    bpy.ops.object.modifier_apply(modifier='sm')
    return o
G = dict(  # proportions, tuned against the drawing with fit_view.py + overlay.py
    torso=((0, 0.4, 1.5), (1.02, 1.18, 0.58)), chest=((0, -0.75, 1.62), (1.0, 0.75, 0.68)), neck=((0, -1.4, 2.1), (0.82, 0.55, 0.6)),
    cranium=((0, -1.92, 2.72), (0.78, 0.64, 0.6)), muzzle=((0, -2.5, 2.48), (0.6, 0.44, 0.58)),
    snout=((0, -2.78, 2.78), (0.4, 0.3, 0.32)), cheek=((0.5, -2.12, 2.25), (0.42, 0.42, 0.46)),
    jaw=[((0, -2.36, 1.98), (0.48, 0.4, 0.26)), ((0, -1.98, 2.02), (0.56, 0.4, 0.3))])
HS, HUP, HC = 1.12, 0.15, Vector((0, -1.4, 2.1))     # head scale about the neck, and lift
def hs(p): return tuple(HC + (Vector(p) - HC) * HS + Vector((0, 0, HUP)))
def hsz(z): return tuple(c * HS for c in z)
for k in ('cranium', 'muzzle', 'snout', 'cheek'): G[k] = (hs(G[k][0]), hsz(G[k][1]))
G['jaw'] = [(hs(c), hsz(z)) for c, z in G['jaw']]
G['face'] = (hs((0, -2.72, 2.42)), hsz((0.5, 0.16, 0.5)))       # flat upright front of the muzzle (the drawing)
BODY_EL = [G['torso'], G['chest'], G['neck'], G['cranium'], G['muzzle'], G['snout'], G['face'],
           G['cheek'], ((-G['cheek'][0][0], G['cheek'][0][1], G['cheek'][0][2]), G['cheek'][1])]
LEGS = dict(F=dict(y=-0.95, top=1.55, x=0.82), B=dict(y=1.25, top=1.35, x=0.8))
for sx in (1, -1):            # long thick legs into big paws
    f, b = LEGS['F'], LEGS['B']
    BODY_EL += [((f['x'] * sx, f['y'], 1.05), (0.5, 0.5, 0.68)), ((0.9 * sx, f['y'] - 0.1, 0.42), (0.4, 0.42, 0.46)),
                ((0.95 * sx, f['y'] - 0.24, 0.13), (0.44, 0.54, 0.18)),
                ((b['x'] * sx, b['y'], 0.95), (0.38, 0.42, 0.58)), ((0.86 * sx, b['y'] + 0.05, 0.38), (0.3, 0.32, 0.4)),
                ((0.9 * sx, b['y'] - 0.08, 0.1), (0.3, 0.4, 0.12))]
body = metaball_mesh('Body', BODY_EL)
finish(body, 'body', 'body')
parts = [body]
jaw = metaball_mesh('Jaw', G['jaw'])                     # own mesh: the jaw bone opens the mouth for the roar
parts.append(finish(jaw, 'body', 'jawmesh'))
parts.append(finish(ellipsoid('Maw', hs((0, -2.26, 2.14)), hsz((0.4, 0.38, 0.14))), 'red', 'maw'))
_bm = bmesh.new(); _bm.from_mesh(body.data); BVH = BVHTree.FromBMesh(_bm); _bm.free()
_bm = bmesh.new(); _bm.from_mesh(jaw.data); BVHJ = BVHTree.FromBMesh(_bm); _bm.free()
def surf(origin, direction, tree=None):
    d = Vector(direction).normalized()
    loc, nrm, _, _ = (tree or BVH).ray_cast(Vector(origin), d)
    assert loc is not None, (origin, direction)
    return loc, nrm.normalized()
def oriented(name, center, axes, radii, seg=16, ring=10):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=ring, radius=1.0)
    M = Matrix((axes[0] * radii[0], axes[1] * radii[1], axes[2] * radii[2])).transposed()
    for v in bm.verts: v.co = Vector(center) + M @ v.co
    return obj_from_bm(name, bm)
def tangent_frame(n, toward):
    t = Vector(toward) - n * Vector(toward).dot(n); t.normalize()
    return t, n.cross(t).normalized()

# eyes: narrow white slits high on the head under the hat brim, pupil at the front end, heavy brow sloping to the nose
for sx in (1, -1):
    P, N = surf(hs((sx * 1.3, -3.7, 2.8)), (-sx * 0.62, 1.0, 0.04))
    t_in, b = tangent_frame(N, Vector((-0.4 * sx, -1.0, -0.25)))
    if b.z < 0: b = -b
    a = math.radians(14)
    ax = (t_in * math.cos(a) - b * math.sin(a)).normalized()
    ay = N.cross(ax).normalized()
    if ay.z < 0: ay = -ay
    parts.append(finish(oriented(f'Eye{sx}', P + N * 0.01, (ax, ay, N), (0.27, 0.095, 0.05)), 'white', 'eye'))
    parts.append(finish(oriented(f'Pupil{sx}', P + N * 0.06 + ax * 0.15, (ax, ay, N), (0.075, 0.075, 0.02)), 'ink', 'pupil'))
    brow = [P + N * 0.03 - t_in * 0.3 + b * 0.2, P + N * 0.05 + b * 0.15, P + N * 0.045 + t_in * 0.32 + b * 0.03]
    parts.append(finish(tube(f'Brow{sx}', [tuple(p) for p in brow], [0.06, 0.09, 0.065], seg=6), 'ink', 'brow'))
    print('eye', sx, tuple(round(c, 2) for c in P))
# small gold nose on top of the snout
P, N = surf(hs((0, -3.3, 4.4)), (0, 0.42, -1.0))
t, b = tangent_frame(N, Vector((1, 0, 0)))
parts.append(finish(oriented('Nose', P + N * 0.02, (t, b, N), (0.15, 0.1, 0.06)), 'gold', 'nose'))
NOSE_P = P
# the drawing's lines: down the front of the muzzle from the nose, and the cheek line back under the eye
pts = []
for k in range(6):
    P, N = surf((0, -4.0, NOSE_P.z - 0.12 - 0.09 * k), (0, 1, 0)); pts.append(tuple(P + N * 0.015))
parts.append(finish(tube('MouthMid', pts, [0.035] * len(pts), seg=5), 'ink', 'mouth'))
for sx in (1, -1):
    pts = []
    for k in range(4):
        y = -2.62 + 0.1 * k; z = 2.32 - 0.06 * k
        P, N = surf(hs((sx * 2.5, y, z)), (-sx, 0, 0)); pts.append(tuple(P + N * 0.015))
    parts.append(finish(tube(f'Mouth{sx}', pts, [0.035] * len(pts), seg=5), 'ink', 'mouth'))
# sabres: long, white, from the front of the upper jaw, curving slightly back
TUSK_TIPS = []
for sx in (1, -1):
    P, N = surf(hs((0.26 * sx, -4.0, 2.12)), (0, 1, 0.05))
    r0 = P - N * 0.06
    pts = [r0, r0 + Vector((0.01 * sx, 0.0, -0.4)), r0 + Vector((0.02 * sx, 0.08, -0.8)), r0 + Vector((0.03 * sx, 0.2, -1.15))]
    parts.append(finish(tube(f'Tusk{sx}', [tuple(p) for p in pts], [0.1, 0.09, 0.06, 0.0], seg=8), 'white', 'tusk'))
    TUSK_TIPS.append(tuple(pts[-1]))
    # gold fang at the corner of the jaw, pointing down (the drawing's gold tooth under the cheek)
    P, N = surf(hs((sx * 2.5, -1.95, 1.92)), (-sx, 0, 0), BVHJ)
    f = [P - N * 0.04, P + Vector((0.03 * sx, -0.04, -0.3)), P + Vector((0.04 * sx, -0.06, -0.5))]
    parts.append(finish(tube(f'Fang{sx}', [tuple(p) for p in f], [0.075, 0.05, 0.0], seg=6), 'gold', 'fang'))

# hat: bicorne worn fore-and-aft as in the drawing: front tip curled up over the snout, long back tip sweeping back
# and up, gold trim along the top edge, a gold skull and crossbones on each side panel near the front
HTOP, _ = surf(hs((0, -1.95, 6.0)), (0, 0, -1))
Z0 = HTOP.z - 0.16
YF, YB = hs((0, -2.85, 0))[1], -0.8
def hat_y(u): return YF + (YB - YF) * u
def hat_top(u):
    return Z0 + 0.78 * math.sin(math.pi * min(1.0, u * 1.08)) ** 0.6 + 0.55 * max(0.0, 1 - u / 0.24) ** 2 + 0.42 * max(0.0, (u - 0.72) / 0.28) ** 1.6
def hat_bot(u): return Z0 - 0.06 + 0.36 * max(0.0, 1 - u / 0.2) ** 2 + 0.36 * max(0.0, (u - 0.75) / 0.25) ** 1.6
def hat_w(u, v):
    wb = (0.66 * math.sin(math.pi * min(1.0, 0.03 + 0.97 * u)) ** 0.5 + 0.03) * (0.72 + 0.28 * min(1.0, u / 0.45))
    return wb + (0.04 - wb) * v ** 0.75
bm = bmesh.new(); NU, NV = 30, 6
rings = []
for i in range(NU + 1):
    u = i / NU; y = hat_y(u); zb, zt = hat_bot(u), hat_top(u)
    ring = [bm.verts.new((hat_w(u, j / NV), y, zb + (zt - zb) * j / NV)) for j in range(NV + 1)]
    ring += [bm.verts.new((-hat_w(u, j / NV), y, zb + (zt - zb) * j / NV)) for j in range(NV, -1, -1)]
    rings.append(ring)
n = len(rings[0])
for a, c in zip(rings, rings[1:]):
    for k in range(n): bm.faces.new((a[k], c[k], c[(k + 1) % n], a[(k + 1) % n]))
bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
parts.append(finish(obj_from_bm('Hat', bm), 'hat', 'hat'))
parts.append(finish(tube('HatTrim', [(0, hat_y(i / 32), hat_top(i / 32) + 0.01) for i in range(33)], [0.07] * 33, seg=6), 'gold', 'trim'))
EU, EV0, EV1 = 0.36, 0.1, 0.9
def emblem_pt(sx):
    def f(u, v):
        uu = EU + (u - 0.5) * 0.34 * sx
        vv = EV0 + (EV1 - EV0) * v
        zb, zt = hat_bot(uu), hat_top(uu)
        return (sx * (hat_w(uu, vv) + 0.02), hat_y(uu), zb + (zt - zb) * vv)
    return f
for sx in (1, -1):
    parts.append(finish(grid(f'Emblem{sx}', 6, 6, emblem_pt(sx)), 'emblem', 'emblem'))
parts.append(finish(ellipsoid('HatCrown', (0, hs((0, -1.92, 0))[1], Z0 + 0.02), (0.58, 0.8, 0.22)), 'hat', 'hat'))

# ---------------------------------------------------------------- the ship on his back: a rounded red hull
YBOW, YST = -0.95, 1.95
def hull_y(t): return YBOW + (YST - YBOW) * t
def beam(t): return 1.14 * math.sin(math.pi * min(1.0, 0.1 + 0.85 * t)) ** 0.55
def deck_z(t): return 2.18 + 0.5 * math.sin(math.pi * min(1.0, 0.08 + 0.9 * t)) ** 0.7    # arched like the drawing's shell
def band_z(t): return 2.02 - 0.3 * t + 0.1 * math.sin(math.pi * t)                      # the black band slopes down aft
def keel_z(t): return 1.45 - 0.12 * t + 0.25 * max(0.0, 1 - t / 0.15) ** 2 + 0.2 * max(0.0, (t - 0.88) / 0.12) ** 2
def section(t):
    B, zd, zb, zk = beam(t), deck_z(t), band_z(t), keel_z(t)
    return [(0.62 * B, zd), (0.88 * B, zd - 0.2), (1.02 * B, max(zb + 0.2, 0.5 * (zd + zb))), (1.06 * B, zb + 0.06), (1.04 * B, zb - 0.16),
            (0.9 * B, 0.5 * (zb - 0.16 + zk)), (0.55 * B, zk)]
NT = 32
bm = bmesh.new(); rings = []
for i in range(NT + 1):
    t = i / NT; y = hull_y(t); sd = section(t)
    rings.append([bm.verts.new((x, y, z)) for (x, z) in sd] + [bm.verts.new((-x, y, z)) for (x, z) in reversed(sd)])
n = len(rings[0])
for a, c in zip(rings, rings[1:]):
    for k in range(n - 1): bm.faces.new((a[k], c[k], c[k + 1], a[k + 1]))
bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
parts.append(finish(obj_from_bm('Hull', bm), 'red', 'shell'))
parts.append(finish(grid('Deck', 4, NT, lambda u, v: ((u * 2 - 1) * 0.62 * beam(v), hull_y(v), deck_z(v) + 0.1 * (1 - (u * 2 - 1) ** 2))), 'red', 'deck'))
# black rim along the top edge
rim = [(0.64 * beam(i / NT), hull_y(i / NT), deck_z(i / NT) - 0.02) for i in range(0, NT + 1)]
rim_pts = rim + [(-x, y, z) for (x, y, z) in reversed(rim)]
parts.append(finish(tube('Rim', rim_pts, [0.07] * len(rim_pts), seg=6, cap=True), 'hat', 'rim'))
def side_x(t, z):
    sd = section(t)
    for (x0, z0), (x1, z1) in zip(sd, sd[1:]):
        if z1 <= z <= z0: return x0 + (x1 - x0) * (z - z0) / (z1 - z0)
    return sd[0][0]
# thick black band
for sx in (1, -1):
    def wale(u, v, sx=sx):
        t = v; z = band_z(t) - 0.16 + 0.32 * u
        return (sx * (side_x(t, z) + 0.025), hull_y(t), z)
    parts.append(finish(grid(f'Wale{sx}', 3, NT, wale), 'hat', 'wale'))
# gun ports: black triangles pointing up with a gold glint inside (lamplit at night); a round port aft
for sx in (1, -1):
    for k, t in enumerate((0.3, 0.5, 0.68)):
        y = hull_y(t); zc = band_z(t) + 0.36; x = side_x(t, zc) + 0.03
        tri = lambda s, o=0.0, dz=0.0: [(sx * (x + o), y - 0.17 * s, zc - 0.15 * s + dz), (sx * (x + o), y + 0.17 * s, zc - 0.15 * s + dz), (sx * (x + o), y - 0.03 * s, zc + 0.2 * s + dz)]
        for name, s, o, dz, mat, part in ((f'Port{sx}{k}', 1.0, 0.0, 0.0, 'ink', 'port'), (f'PortGlow{sx}{k}', 0.45, 0.015, -0.07, 'gold', 'portglow')):
            bm = bmesh.new(); vs = [bm.verts.new(p) for p in tri(s, o, dz)]; bm.faces.new(vs)
            o_ = obj_from_bm(name, bm); o_['two_sided'] = 1
            parts.append(finish(o_, mat, part))
    t = 0.84; y = hull_y(t); zc = band_z(t) + 0.3; x = side_x(t, zc) + 0.02
    parts.append(finish(ellipsoid(f'RoundPort{sx}', (sx * x, y, zc), (0.04, 0.11, 0.12)), 'ink', 'port'))
    parts.append(finish(ellipsoid(f'RoundGlow{sx}', (sx * (x + 0.02), y + 0.02, zc - 0.03), (0.03, 0.05, 0.05)), 'gold', 'portglow'))
# the gold skull at the stern, facing aft (in profile from the drawing's angle), after the pirate-ship picture:
# rounded cranium, round eye holes with red rims, nose hole, rows of teeth; two gold spikes rise above it
SK = Vector((0, YST + 0.12, 1.95))
def sk(ox, oy, oz): return SK + Vector((ox, oy, oz))
for name, c, r in (('SkullDome', sk(0, -0.05, 0.08), (0.44, 0.4, 0.42)), ('SkullFace', sk(0, 0.17, -0.18), (0.36, 0.27, 0.28)),
                   ('SkullJaw', sk(0, 0.14, -0.44), (0.27, 0.23, 0.14))):
    parts.append(finish(ellipsoid(name, c, r), 'gold', 'skull'))
for sx in (1, -1):
    parts.append(finish(ellipsoid(f'SkullCheek{sx}', sk(0.36 * sx, 0.14, -0.14), (0.14, 0.2, 0.13)), 'gold', 'skull'))
    parts.append(finish(tube(f'SocketRim{sx}', [tuple(sk(0.2 * sx + 0.15 * math.cos(a), 0.36, 0.02 + 0.15 * math.sin(a))) for a in [2 * math.pi * k / 16 for k in range(17)]], [0.04] * 17, seg=5, cap=False), 'red', 'socket'))
    parts.append(finish(ellipsoid(f'Socket{sx}', sk(0.2 * sx, 0.33, 0.02), (0.13, 0.06, 0.13)), 'ink', 'socket'))
parts.append(finish(ellipsoid('SkullNose', sk(0, 0.45, -0.18), (0.06, 0.05, 0.09)), 'ink', 'socket'))
for row, z in ((0, -0.34), (1, -0.46)):
    for k in range(6):
        x = -0.22 + 0.088 * k
        y = 0.3 + 0.06 * math.cos(x / 0.3)
        parts.append(finish(ellipsoid(f'Tooth{row}{k}', sk(x, y, z), (0.036, 0.05, 0.05)), 'white', 'skullteeth'))
def flat_spike(name, base0, base1, tip):
    bm = bmesh.new(); vs = [bm.verts.new(p) for p in (base0, base1, tip)]; bm.faces.new(vs)
    o = obj_from_bm(name, bm); solidify(o, 0.11); return o
parts.append(finish(flat_spike('Crest0', (0, YST - 0.05, SK.z + 0.3), (0, YST + 0.3, SK.z + 0.38), (0, YST + 0.5, SK.z + 0.88)), 'gold', 'crest'))
parts.append(finish(flat_spike('Crest1', (0, YST + 0.25, SK.z + 0.25), (0, YST + 0.5, SK.z + 0.05), (0, YST + 0.92, SK.z + 0.38)), 'gold', 'crest'))

# masts raked aft, yards, sails (billowing aft), flag streaming aft
RAKE = math.radians(12)
def raked(base, h): return (base[0], base[1] + h * math.tan(RAKE), base[2] + h)
MAST = (0, -0.2)
MZ0 = deck_z((MAST[1] - YBOW) / (YST - YBOW))
MB = (MAST[0], MAST[1], MZ0 - 0.1); MH = 5.25 - MB[2]
parts.append(finish(tube('Mast', [MB, raked(MB, MH)], [0.08, 0.06], seg=8), 'hat', 'mast'))
def on_mast(z): return MB[1] + (z - MB[2]) * math.tan(RAKE)
for zz, hw in ((4.82, 1.18), (3.05, 1.34)):
    parts.append(finish(tube(f'Yard{zz}', [(-hw, on_mast(zz) - 0.08, zz), (hw, on_mast(zz) - 0.08, zz)], [0.05, 0.05], seg=6), 'hat', 'yard'))
def sail_pt(u, v, x0=1.12, x1=1.3, z0=3.1, z1=4.78, bel=0.5):
    hw = x1 + (x0 - x1) * v
    x = (u * 2 - 1) * hw
    z = z0 + (z1 - z0) * v - 0.12 * (1 - (u * 2 - 1) ** 2) * (1 - v) ** 3
    y = on_mast(z) - 0.12 - bel * (1 - (u * 2 - 1) ** 2) * math.sin(math.pi * (0.15 + 0.85 * v)) ** 0.8   # wind from astern: the sail is in front of the mast
    return (x, y, z)
parts.append(finish(grid('Sail', 16, 12, sail_pt), 'sail_main', 'sail'))
RM = (0, 1.12)
RZ0 = deck_z((RM[1] - YBOW) / (YST - YBOW))
RB = (0, RM[1], RZ0 - 0.1)
parts.append(finish(tube('Mast2', [RB, raked(RB, 4.15 - RB[2])], [0.065, 0.05], seg=8), 'hat', 'mast'))
def on_mast2(z): return RB[1] + (z - RB[2]) * math.tan(RAKE)
for zz, hw in ((3.95, 0.66), (3.0, 0.74)):
    parts.append(finish(tube(f'Yard2_{zz}', [(-hw, on_mast2(zz) - 0.07, zz), (hw, on_mast2(zz) - 0.07, zz)], [0.04, 0.04], seg=6), 'hat', 'yard'))
def sail2_pt(u, v):
    hw = 0.7 + (0.62 - 0.7) * v; x = (u * 2 - 1) * hw; z = 3.05 + 0.86 * v
    return (x, on_mast2(z) - 0.1 - 0.3 * (1 - (u * 2 - 1) ** 2) * math.sin(math.pi * (0.15 + 0.85 * v)) ** 0.8, z)
parts.append(finish(grid('Sail2', 12, 8, sail2_pt), 'sail_rear', 'sail2'))
FL = 1.05
FTOP = raked(MB, MH)
FD = Vector((0.42, 0.91, 0.0))           # the flag streams aft (to the right in the drawing)
FN = Vector((-FD.y, FD.x, 0.0))
def flag_pt(u, v):
    p = Vector((FTOP[0], FTOP[1], FTOP[2] - 0.05 - 0.48 * (1 - v) - 0.1 * u)) + FD * (u * FL)
    p += FN * (0.08 * math.sin(math.pi * 1.6 * u) * u)
    return tuple(p)
parts.append(finish(grid('Flag', 12, 5, flag_pt), 'flag', 'flag'))
parts.append(finish(ellipsoid('MastTop', (FTOP[0], FTOP[1], FTOP[2] + 0.04), (0.09, 0.09, 0.09)), 'gold', 'masttop'))

# legs: shaggy gold cuffs on the forelegs just above the paws, big white claws
for sx in (1, -1):
    f = LEGS['F']
    cx, cy = 0.9 * sx, f['y'] - 0.1
    parts.append(finish(tube(f'CuffF{sx}', [(cx, cy + 0.05, 0.5), (cx - 0.02 * sx, cy + 0.08, 1.0)], [0.46, 0.52], seg=14), 'gold', 'cuff'))
    for k in range(11):
        a = 2 * math.pi * k / 11
        p0 = Vector((cx + 0.48 * math.cos(a), cy + 0.08 + 0.48 * math.sin(a), 0.96))
        parts.append(finish(tube(f'TuftF{sx}{k}', [tuple(p0), tuple(p0 + Vector((0.1 * math.cos(a), 0.1 * math.sin(a), 0.24 + 0.08 * (k % 2))))], [0.11, 0.0], seg=5), 'gold', 'cuff'))
    for nm, yy, xx, cs in (('F', LEGS['F']['y'] - 0.26, 0.95, 1.25), ('B', LEGS['B']['y'] - 0.08, 0.9, 0.9)):
        for k in (-1, 0, 1):
            parts.append(finish(tube(f'Claw{nm}{sx}{k}', [(xx * sx + 0.17 * k, yy - 0.46 * cs, 0.12), (xx * sx + 0.2 * k, yy - 0.66 * cs, 0.07), (xx * sx + 0.21 * k, yy - 0.78 * cs, -0.06)], [0.085 * cs, 0.055 * cs, 0.0], seg=6), 'white', 'claw'))

for o in parts:
    for m in list(o.modifiers):
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier=m.name)

# ---------------------------------------------------------------- armature
arm = bpy.data.armatures.new('Rig'); rig = bpy.data.objects.new('Rig', arm); col.objects.link(rig)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
B = {}
def bone(name, head, tail, parent=None):
    b = arm.edit_bones.new(name); b.head = head; b.tail = tail
    if parent: b.parent = B[parent]
    B[name] = b; return b
bone('root', (0, 0, 0), (0, 0, 0.4))
bone('spine', (0, 1.2, 1.45), (0, -0.4, 1.55), 'root')
bone('chest', (0, -0.4, 1.55), (0, -1.3, 1.95), 'spine')
bone('head', (0, -1.3, 2.15), hs((0, -2.6, 2.55)), 'chest')
bone('jaw', hs((0, -1.85, 2.15)), hs((0, -2.75, 1.95)), 'head')
bone('hat', (0, hs((0, -1.92, 0))[1], Z0), (0, hs((0, -1.92, 0))[1], Z0 + 0.5), 'head')
bone('shell', (0, 0.6, 1.9), (0, 0.6, 2.4), 'spine')
bone('mast', MB, raked(MB, MH), 'shell')
bone('sail_belly', (0, on_mast(3.9) - 0.1, 3.9), (0, on_mast(3.9) - 0.6, 3.9), 'mast')
bone('sail_bl', (1.3, on_mast(3.0) - 0.1, 3.0), (1.3, on_mast(3.0) - 0.5, 3.0), 'mast')
bone('sail_br', (-1.3, on_mast(3.0) - 0.1, 3.0), (-1.3, on_mast(3.0) - 0.5, 3.0), 'mast')
prev = 'mast'
for k in range(3):
    p0 = Vector(FTOP) + Vector((0, 0, -0.3)) + FD * (k * FL / 3); p1 = Vector(FTOP) + Vector((0, 0, -0.3)) + FD * ((k + 1) * FL / 3)
    bone(f'flag{k}', tuple(p0), tuple(p1), prev); prev = f'flag{k}'
bone('mast2', RB, raked(RB, 4.15 - RB[2]), 'shell')
bone('sail2_belly', (0, on_mast2(3.5) - 0.1, 3.5), (0, on_mast2(3.5) - 0.5, 3.5), 'mast2')
bone('stern', (0, YST, 2.0), (0, YST + 0.6, 2.1), 'shell')
for sx, s in ((1, 'L'), (-1, 'R')):
    for n, par in (('F', 'chest'), ('B', 'spine')):
        Lg = LEGS[n]; yy = Lg['y']
        bone(f'{n}leg_up.{s}', (Lg['x'] * sx, yy, Lg['top']), (0.88 * sx, yy - 0.05, 0.75), par)
        bone(f'{n}leg_lo.{s}', (0.88 * sx, yy - 0.05, 0.75), (0.92 * sx, yy - 0.12, 0.14), f'{n}leg_up.{s}')
        bone(f'{n}paw.{s}', (0.92 * sx, yy - 0.12, 0.14), (0.94 * sx, yy - 0.7, 0.05), f'{n}leg_lo.{s}')
bpy.ops.object.mode_set(mode='OBJECT')

# ---------------------------------------------------------------- skinning
def seg_dist(p, a, b):
    ab = b - a; t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (a + ab * t - p).length
BODY_BONES = ['spine', 'chest', 'head'] + [f'{n}{p}.{s}' for n in 'FB' for p in ('leg_up', 'leg_lo', 'paw') for s in 'LR']
RIGID = dict(eye='head', pupil='head', brow='head', nose='head', mouth='head', tusk='head', maw='head',
             jawmesh='jaw', fang='jaw', hat='hat', trim='hat', emblem='hat',
             shell='shell', deck='shell', rim='shell', wale='shell', port='shell', portglow='shell', mast='mast', yard='mast', masttop='mast',
             skull='stern', socket='stern', skullteeth='stern', crest='stern', cuff=None, claw=None)
def bone_pos(n):
    b = arm.bones[n]; return b.head_local.copy(), b.tail_local.copy()
def nearest_leg(p, kinds=('leg_up', 'leg_lo', 'paw')):
    best = None
    for n in [f'{a}{b}.{s}' for a in 'FB' for b in kinds for s in 'LR']:
        h, t = bone_pos(n); d = seg_dist(p, h, t)
        if best is None or d < best[0]: best = (d, n)
    return best[1]
def weight(o, fn):
    groups = {}
    for v in o.data.vertices:
        w = fn(o.matrix_world @ v.co); s = sum(w.values()) or 1.0
        for n, x in w.items():
            if x <= 0: continue
            if n not in groups: groups[n] = o.vertex_groups.new(name=n)
            groups[n].add([v.index], x / s, 'REPLACE')
    mod = o.modifiers.new('rig', 'ARMATURE'); mod.object = rig
    o.parent = rig
for o in parts:
    part = o['part']
    if part == 'body':
        def fn(p):
            ds = {n: seg_dist(p, *bone_pos(n)) for n in BODY_BONES}
            near = sorted(ds.items(), key=lambda kv: kv[1])[:2]
            return {n: 1.0 / (d + 0.08) ** 3 for n, d in near}
        weight(o, fn)
    elif part == 'sail':
        def fn(p):
            u = p.x / 1.3; v = (p.z - 3.1) / 1.68
            belly = max(0.0, (1 - u * u)) * math.sin(math.pi * max(0, min(1, v)))
            bl = max(0.0, (u - 0.4) / 0.6) * max(0.0, 1 - v * 2.5)
            br = max(0.0, (-u - 0.4) / 0.6) * max(0.0, 1 - v * 2.5)
            return {'sail_belly': belly, 'sail_bl': bl, 'sail_br': br, 'mast': max(0.05, 1 - belly - bl - br)}
        weight(o, fn)
    elif part == 'sail2':
        def fn(p):
            u = p.x / 0.7; v = (p.z - 3.05) / 0.86
            belly = max(0.0, 1 - u * u) * math.sin(math.pi * max(0, min(1, v)))
            return {'sail2_belly': belly, 'mast2': max(0.05, 1 - belly)}
        weight(o, fn)
    elif part == 'flag':
        def fn(p):
            t = (Vector((p.x - FTOP[0], p.y - FTOP[1], 0)).dot(FD)) / FL * 3
            w = {'mast': max(0.0, 1 - t * 2)}
            for k in range(3): w[f'flag{k}'] = max(0.0, 1 - abs(t - (k + 0.5)) / 1.0)
            return w
        weight(o, fn)
    elif part == 'claw':
        weight(o, lambda p: {nearest_leg(p, ('paw',)): 1.0})
    elif part == 'cuff':
        weight(o, lambda p: {nearest_leg(p, ('leg_lo',)): 1.0})
    else:
        weight(o, lambda p, b=RIGID[part]: {b: 1.0})

# ---------------------------------------------------------------- animation: frames 1-4 swim (paddling), 5-7 the leap
NFR = 7; LEAP0 = 5
scene.frame_start = 1; scene.frame_end = NFR
scene.render.fps = 30
rig.animation_data_create()
act = bpy.data.actions.new('swim_leap'); rig.animation_data.action = act
pb = rig.pose.bones
for p in pb: p.rotation_mode = 'XYZ'
def key(f):
    for p in pb:
        p.keyframe_insert('location', frame=f); p.keyframe_insert('rotation_euler', frame=f)
SGN = dict(leg=float(os.environ.get('SAB_LEGSIGN', -1)), jaw=float(os.environ.get('SAB_JAWSIGN', 1)), pitch=float(os.environ.get('SAB_PITCHSIGN', -1)), head=float(os.environ.get('SAB_HEADSIGN', 1)))
LEAP = {5: dict(up=0.35, fwd=0.2, pitch=8, legs=60, jaw=18, head=2, spread=12),
        6: dict(up=0.95, fwd=0.55, pitch=16, legs=100, jaw=38, head=0, spread=40),
        7: dict(up=1.2, fwd=0.9, pitch=20, legs=115, jaw=46, head=-2, spread=48)}
HEADTURN = float(os.environ.get('SAB_HEADTURN', 20))   # the head looks at the camera like in the drawing (+x side)
REST = os.environ.get('SAB_REST') == '1'          # rest pose for comparing with the drawing (standing, no motion)
for f in range(1, NFR + 1):
    for p in pb: p.location = (0, 0, 0); p.rotation_euler = (0, 0, 0)
    if REST:
        pb['head'].rotation_euler = (math.radians(float(os.environ.get('SAB_HEADPITCH', -6))), 0, -math.radians(float(os.environ.get('SAB_HEADTURN', 22))))
        for s, sg in (('L', 1), ('R', -1)):
            pb[f'Fleg_up.{s}'].rotation_euler = (math.radians(SGN['leg'] * 12), 0, math.radians(-20 * sg))
            pb[f'Bleg_up.{s}'].rotation_euler = (math.radians(SGN['leg'] * -10), 0, math.radians(-16 * sg))
    elif f < LEAP0:
        ph = 2 * math.pi * (f - 1) / (LEAP0 - 1)
        for k in range(3):
            pb[f'flag{k}'].rotation_euler = (math.radians(6 * math.sin(ph - 1.1 * k + 0.7)), 0, math.radians(12 * math.sin(ph - 1.1 * k)))
        pb['head'].rotation_euler = (math.radians(3 * math.sin(ph + 0.8)), 0, -math.radians(HEADTURN + 2 * math.sin(ph)))
        for s, sh in (('L', 0.0), ('R', math.pi)):
            stroke = 0.5 + 0.5 * math.cos(ph + sh)
            pb[f'Fleg_up.{s}'].rotation_euler = (math.radians(SGN['leg'] * (95 * stroke - 15)), 0, math.radians(-10 * stroke * (1 if s == 'L' else -1)))
            pb[f'Fleg_lo.{s}'].rotation_euler = (math.radians(SGN['leg'] * (-45 * stroke)), 0, 0)
            pb[f'Bleg_up.{s}'].rotation_euler = (math.radians(SGN['leg'] * (-20 * stroke + 10)), 0, 0)
    else:
        L = LEAP[f]
        pb['root'].location = (0, L['up'], L['fwd'])
        pb['root'].rotation_euler = (math.radians(SGN['pitch'] * L['pitch']), 0, 0)
        pb['head'].rotation_euler = (math.radians(SGN['head'] * L['head']), 0, -math.radians(HEADTURN))
        pb['jaw'].rotation_euler = (math.radians(SGN['jaw'] * L['jaw']), 0, 0)
        pb['sail_belly'].location = (0, 0.1, 0)
        for k in range(3): pb[f'flag{k}'].rotation_euler = (0, 0, math.radians(-14 + 8 * k))
        for s in 'LR':
            pb[f'Fleg_up.{s}'].rotation_euler = (math.radians(SGN['leg'] * L['legs']), 0, math.radians(-L['spread'] * (1 if s == 'L' else -1)))
            pb[f'Fleg_lo.{s}'].rotation_euler = (math.radians(SGN['leg'] * -30), 0, 0)
            pb[f'Fpaw.{s}'].rotation_euler = (math.radians(SGN['leg'] * -40), 0, 0)
            pb[f'Bleg_up.{s}'].rotation_euler = (math.radians(SGN['leg'] * -35), 0, 0)
    key(f)
for fc in getattr(act, 'fcurves', []):
    for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'

bpy.ops.object.select_all(action='DESELECT')
scene['water'] = WATER
scene['leap0'] = LEAP0
scene['part_ids'] = str(PART_ID)
scene['tusk_tips'] = str(TUSK_TIPS)
bpy.ops.wm.save_as_mainfile(filepath=OUT)
print('saved', OUT, 'objects', len(parts), 'tris', sum(len(o.data.polygons) for o in parts))
