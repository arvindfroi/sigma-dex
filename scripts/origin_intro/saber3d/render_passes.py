"""Render data passes of the swim loop for the pixel step (no AA, 1 sample, emission only).
Blender -b sabertann.blend -P render_passes.py -- OUTDIR [px_per_unit] [supersample]
Writes OUTDIR/passes.npz with per frame: alb (sRGB 0..1), nrm (camera space), oid (part id, 255 = water), dep, alpha.
Also adds the water (holdout) and the animated foam, and records the anchor pixel (waterline under the body centre)."""
import bpy, bmesh, math, os, sys, json
import numpy as np
from mathutils import Vector, Matrix
argv = sys.argv[sys.argv.index('--') + 1:]
OUT = argv[0]; PPU = float(argv[1]) if len(argv) > 1 else 30.0; SS = int(argv[2]) if len(argv) > 2 else 4
YAW = float(os.environ.get('SAB_YAW', 32)); EL = float(os.environ.get('SAB_EL', 9))
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
WATER = float(os.environ.get('SAB_WATER', sc['water'])); NFR = int(os.environ.get('SAB_NFR', sc.frame_end))
CW, CH = float(os.environ.get('SAB_CW', 5.6)), float(os.environ.get('SAB_CH', 4.9))   # canvas in model units
W1, H1 = int(round(CW * PPU)), int(round(CH * PPU))   # 1x canvas (168x147 at 30 px per unit)
sc.render.resolution_x = W1 * SS; sc.render.resolution_y = H1 * SS; sc.render.resolution_percentage = 100
sc.render.engine = 'CYCLES'
sc.cycles.samples = 1; sc.cycles.use_denoising = False; sc.cycles.filter_width = 0.01
sc.cycles.max_bounces = 0; sc.cycles.transparent_max_bounces = 8
sc.cycles.use_adaptive_sampling = False
sc.render.film_transparent = True
sc.view_settings.view_transform = 'Standard'
sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '32'
try:
    sc.cycles.device = 'GPU'
except Exception:
    pass

# ---------------- camera: orthographic, front-left 3/4, slightly above the water
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = max(W1, H1) / PPU   # Blender ortho scale spans the longer side
cam.data.clip_start = 0.1; cam.data.clip_end = 200
yr, er = math.radians(YAW), math.radians(EL)
d = Vector((math.sin(yr) * math.cos(er), -math.cos(yr) * math.cos(er), math.sin(er)))
TGT = Vector((float(os.environ.get('SAB_TX', 0.0)), 0.0, float(os.environ.get('SAB_TZ', 2.32))))
cam.location = TGT + d * 60
cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
bpy.context.view_layer.update()
def project(p):
    """world point -> 1x pixel (x right, y down)"""
    m = cam.matrix_world.inverted() @ Vector(p)
    sx = m.x / cam.data.ortho_scale; sy = m.y / cam.data.ortho_scale * (W1 / H1) * 1.0
    return (W1 / 2 + m.x * PPU, H1 / 2 - m.y * PPU)

# ---------------- water plane (holdout in colour passes, id 255 in the id pass)
bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=40)
me = bpy.data.meshes.new('Water'); bm.to_mesh(me); bm.free()
water = bpy.data.objects.new('Water', me); sc.collection.objects.link(water)
water.location = (0, 0, WATER); water['part'] = 'water'; water.pass_index = 255
wm = bpy.data.materials.new('water_mat'); wm.use_nodes = True; water.data.materials.append(wm)

# ---------------- foam: rebuilt per frame from the waterline of the posed body
body = bpy.data.objects['Body']
foam_mat = bpy.data.materials['foam']
FOAM_ID = 250
def waterline_points(depsgraph):
    ev = body.evaluated_get(depsgraph); me = ev.to_mesh()
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(body.matrix_world)
    ev.to_mesh_clear()
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, WATER), plane_no=(0, 0, 1))
    pts = [v.co.copy() for v in res['geom_cut'] if isinstance(v, bmesh.types.BMVert)]
    bm.free(); return pts
def blob(bm, c, r, h):
    m = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    for v in m['verts']:
        v.co = Vector((v.co.x * r, v.co.y * r, v.co.z * h)) + c
LEAP0 = int(sc.get('leap0', 999))
def build_foam(f):
    ph = 2 * math.pi * (f - 1) / max(1, min(NFR, LEAP0 - 1))
    dg = bpy.context.evaluated_depsgraph_get()
    pts = waterline_points(dg)
    bm = bmesh.new()
    rng = np.random.default_rng(7 + f)
    cen = Vector((0, 0.2, WATER))
    # ring of foam hugging the body where it cuts the water (thinned to every ~0.12 units)
    pts.sort(key=lambda p: math.atan2(p.y - cen.y, p.x - cen.x))
    last = None; i = 0
    for p in pts:
        if last is not None and (p - last).length < 0.11: continue
        last = p; i += 1
        out = Vector((p.x - cen.x, p.y - cen.y, 0)).normalized()
        k = 0.5 + 0.5 * math.sin(ph * 2 + i * 1.7)
        r = 0.09 + 0.05 * k
        blob(bm, p + out * 0.05 + Vector((0, 0, 0.02 + 0.04 * k)), r, r * 0.7)
    if f >= LEAP0:
        # he bursts out of the water: a crown of splash where he left it, and drops flying toward the camera
        k = f - LEAP0
        c0 = Vector((0, -0.5 - 0.25 * k, WATER))
        for q in (range(16) if k <= 2 else ()):              # over the viewer (frames 8-9): the splash is left behind
            a = 2 * math.pi * q / 16
            r = 1.0 + 0.3 * k
            h = (0.6, 0.5, 0.3)[min(k, 2)] * (0.65 + 0.35 * math.sin(3 * a + 1.0))
            c = c0 + Vector((math.cos(a) * r, math.sin(a) * r * 0.55, 0))
            blob(bm, c + Vector((0, 0, h * 0.5)), 0.15, h * 0.6)
            blob(bm, c + Vector((0, 0, 0.03)), 0.26, 0.08)
        for q in range(int(os.environ.get('SAB_DROPS', 10)) + 4 * min(k, 2) if k <= 2 else 3):
            x = rng.uniform(-1.6, 1.6); y = rng.uniform(-2.8, -0.2); z = WATER + rng.uniform(0.2, 0.9 + 0.3 * k)
            r = rng.uniform(*[float(v) for v in os.environ.get('SAB_DROPR', '0.04,0.08').split(',')])
            blob(bm, Vector((x, y, z)), r, r * 1.8)
    else:
        # bow wave: two trails peeling back from the chest, moving one slot per loop
        front = min(pts, key=lambda p: p.y) if pts else Vector((0, -1.6, WATER))
        for sx in ((1, -1) if os.environ.get('SAB_TRAILS', '1') == '1' else ()):
            dirv = Vector((sx * math.sin(math.radians(42)), math.cos(math.radians(42)), 0))
            for j in range(12):
                s_ = (j + (f - 1) / max(1, LEAP0 - 1)) * 0.2
                fade = min(1.0, s_ / 0.25) * max(0.0, 1 - s_ / 1.7)
                if fade <= 0.02: continue
                c = Vector((front.x + sx * 0.35, front.y + 0.05, WATER)) + dirv * s_
                r = (0.1 + 0.07 * fade) * fade ** 0.3
                blob(bm, c + Vector((0, 0, 0.02 * fade)), r, r * (0.45 + 0.25 * fade))
        for k in range(5):
            a = (k - 2) * 0.22
            hgt = 0.12 + 0.1 * (0.5 + 0.5 * math.sin(ph + k * 1.3))
            c = Vector((front.x + a, front.y - 0.08 - 0.05 * abs(k - 2), WATER))
            blob(bm, c, 0.13, hgt)
        # rings where the sabres cut the water (only if they reach it)
        for sx in (1, -1):
            if f'Tusk{sx}' not in bpy.data.objects: continue
            tusk = bpy.data.objects[f'Tusk{sx}']
            ev = tusk.evaluated_get(dg); me_ = ev.to_mesh()
            ws = [ev.matrix_world @ v.co for v in me_.vertices]; ev.to_mesh_clear()
            if min(p.z for p in ws) > WATER: continue
            near = min(ws, key=lambda p: abs(p.z - WATER))
            c = Vector((near.x, near.y, WATER))
            rr = 0.12 + 0.03 * math.sin(ph + sx)
            for q in range(6):
                a = 2 * math.pi * q / 6 + ph * 0.5
                blob(bm, c + Vector((math.cos(a) * rr, math.sin(a) * rr, 0.02)), 0.06, 0.04)
    me = bpy.data.meshes.new(f'Foam{f}'); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    o = bpy.data.objects.new(f'Foam{f}', me); sc.collection.objects.link(o)
    o.data.materials.append(foam_mat); o.pass_index = FOAM_ID; o['part'] = 'foam'
    return o
foams = {}
for f in range(1, NFR + 1):
    sc.frame_set(f)
    if os.environ.get('SAB_NOFOAM') == '1':
        me = bpy.data.meshes.new(f'Foam{f}'); o = bpy.data.objects.new(f'Foam{f}', me); sc.collection.objects.link(o); o['part'] = 'foam'; foams[f] = o
    else:
        foams[f] = build_foam(f)

# layers: 'all', 'base' (everything static: no flag, no foam) or 'anim' (flag + foam, the rest held out)
LAYER = os.environ.get('SAB_LAYER', 'all')
ANIM_PARTS = {'flag', 'foam'}
for o in sc.objects:
    if o.type != 'MESH' or o.name == 'Water': continue
    part = o.get('part', '')
    if LAYER == 'base' and part in ANIM_PARTS:
        o.hide_render = True
    if LAYER == 'anim' and part not in ANIM_PARTS:
        o.is_holdout = True

# ---------------- pass materials
def set_pass(mat, which):
    nt = mat.node_tree; N = nt.nodes; L = nt.links
    for n in list(N):
        if n.name.startswith('P_'): N.remove(n)
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL')
    def node(t, name):
        n = N.new(t); n.name = 'P_' + name; return n
    if mat.name == 'water_mat':
        if which == 'oid':
            e = node('ShaderNodeEmission', 'e'); e.inputs['Color'].default_value = (1, 0, 0, 1)
            cd = node('ShaderNodeCameraData', 'cd'); mt = node('ShaderNodeMath', 'm'); mt.operation = 'DIVIDE'; mt.inputs[1].default_value = 200
            L.new(cd.outputs['View Z Depth'], mt.inputs[0])
            cmb = node('ShaderNodeCombineColor', 'c'); cmb.inputs[0].default_value = 1.0
            L.new(mt.outputs[0], cmb.inputs[1]); L.new(cmb.outputs[0], e.inputs['Color'])
            L.new(e.outputs[0], out.inputs['Surface'])
        else:
            h = node('ShaderNodeHoldout', 'h'); L.new(h.outputs[0], out.inputs['Surface'])
        return
    bsdf = N.get('Principled BSDF')
    tex = next((n for n in N if n.type == 'TEX_IMAGE'), None)
    e = node('ShaderNodeEmission', 'e')
    alb = N.get('ALB')                                   # a painted material's per-pixel colour (build_v9)
    if which == 'alb':
        if alb: L.new(alb.outputs[2], e.inputs['Color'])
        elif tex: L.new(tex.outputs['Color'], e.inputs['Color'])
        else: e.inputs['Color'].default_value = bsdf.inputs['Base Color'].default_value
    elif which == 'nrm':
        g = node('ShaderNodeNewGeometry', 'g')
        vt = node('ShaderNodeVectorTransform', 'vt'); vt.vector_type = 'NORMAL'; vt.convert_from = 'WORLD'; vt.convert_to = 'CAMERA'
        L.new(g.outputs['Normal'], vt.inputs[0])
        neg = node('ShaderNodeVectorMath', 'neg'); neg.operation = 'SCALE'; neg.inputs['Scale'].default_value = -1
        L.new(vt.outputs[0], neg.inputs[0])
        mix = node('ShaderNodeMix', 'mix'); mix.data_type = 'VECTOR'
        L.new(g.outputs['Backfacing'], mix.inputs['Factor'])
        L.new(vt.outputs[0], mix.inputs[4]); L.new(neg.outputs[0], mix.inputs[5])
        sc_ = node('ShaderNodeVectorMath', 's'); sc_.operation = 'MULTIPLY_ADD'
        L.new(mix.outputs[1], sc_.inputs[0]); sc_.inputs[1].default_value = (0.5, 0.5, 0.5); sc_.inputs[2].default_value = (0.5, 0.5, 0.5)
        L.new(sc_.outputs[0], e.inputs['Color'])
    elif which == 'oid':
        oi = node('ShaderNodeObjectInfo', 'oi'); mt = node('ShaderNodeMath', 'm'); mt.operation = 'DIVIDE'; mt.inputs[1].default_value = 255
        L.new(oi.outputs['Object Index'], mt.inputs[0])
        cd = node('ShaderNodeCameraData', 'cd'); md = node('ShaderNodeMath', 'md'); md.operation = 'DIVIDE'; md.inputs[1].default_value = 200
        L.new(cd.outputs['View Z Depth'], md.inputs[0])
        cmb = node('ShaderNodeCombineColor', 'c')
        L.new(mt.outputs[0], cmb.inputs[0]); L.new(md.outputs[0], cmb.inputs[1])
        L.new(cmb.outputs[0], e.inputs['Color'])
    shader = e
    if mat.get('alpha') and tex:
        tr = node('ShaderNodeBsdfTransparent', 't'); mx = node('ShaderNodeMixShader', 'mx')
        L.new(tex.outputs['Alpha'], mx.inputs[0]); L.new(tr.outputs[0], mx.inputs[1]); L.new(e.outputs[0], mx.inputs[2])
        shader = mx
    L.new(shader.outputs[0], out.inputs['Surface'])

def render_np(path):
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path); img.colorspace_settings.name = 'Non-Color'
    a = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)[::-1]
    bpy.data.images.remove(img); os.remove(path)
    return a
def to_srgb(x):
    x = np.clip(x, 0, 1); return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)

data = {}
for which in ('alb', 'nrm', 'oid'):
    for m in bpy.data.materials:
        if m.use_nodes: set_pass(m, which)
    for f in range(1, NFR + 1):
        sc.frame_set(f)
        for k, o in foams.items():
            o.hide_render = (k != f) or LAYER == 'base'
        a = render_np(os.path.join(OUT, f'tmp_{which}_{f}.exr'))
        if which == 'alb':
            data[f'alb{f}'] = to_srgb(a[..., :3]).astype(np.float32); data[f'alpha{f}'] = a[..., 3]
        elif which == 'nrm':
            data[f'nrm{f}'] = (a[..., :3] * 2 - 1).astype(np.float32)
        else:
            data[f'oid{f}'] = np.rint(a[..., 0] * 255).astype(np.uint8) * (a[..., 3] > 0.5)
            data[f'dep{f}'] = (a[..., 1] * 200).astype(np.float32)
        print('pass', which, f, flush=True)
ids = {o.name: o.pass_index for o in sc.objects if o.type == 'MESH'}
parts = {}
for o in sc.objects:
    if o.type == 'MESH' and 'part' in o: parts[str(o.pass_index)] = o['part']
anchor = project((0, 0.0, WATER))
meta = dict(W1=W1, H1=H1, SS=SS, PPU=PPU, NFR=NFR, anchor=anchor, parts=parts, yaw=YAW, el=EL,
            keys={m.name: m.get('key') for m in bpy.data.materials if m.get('key')})
np.savez_compressed(os.path.join(OUT, 'passes.npz'), **data)
json.dump(meta, open(os.path.join(OUT, 'meta.json'), 'w'), indent=1)
print('done', meta['anchor'])
