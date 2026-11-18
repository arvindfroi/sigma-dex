"""The Azalea Gym cart becomes Fleuroom's mushroom head (Arvind, 2026-11-18: "gjøre den spinarak om til sopphodet på
Fleuroom", the gym leader's signature Pokemon). Used by fairy_look.py.

The cart is room building model 118 `gym02lift` (a/1/4/8, the same bytes as fielddata/build_model/bm_room.narc):
a flat Spinarak back that the player stands on (top at y = 1), six legs on their own nodes. Its textures come from the
area's building texture set a/0/7/0 file 27 (g02lift_*, all 16x16 or 8x8, 4 colours).

What changes:
- the 22 display lists are rewritten in the same byte area (5544 bytes), so the model keeps its size and every other
  offset: the root node's shapes get the mushroom, the leg shapes get one invisible (zero-area) triangle;
- shape 1 (g02lift_body): the cap, an orange dome with cream spots; the player stands on its top (y about 1-2);
- shape 3 (g02lift_on1): the stem with Fleuroom's face (eyes, mouth, blush) on the camera side (+z);
- shape 0 (g02lift_body2): the gills under the cap rim (body2 shares the cap's palette);
- the three materials draw both faces (no winding worries);
- the four textures are drawn new in Fleuroom's colours (from his DS sprite: oranges, cream spots, dark eyes).
Nothing here holds game data."""
import struct
import numpy as np

# Fleuroom's colours (his front sprite in assets/sprites-ds/fleuroom)
CAP = ['#a5271a', '#e0502a', '#fa7a30', '#ffe2a0']          # dark rim, orange, light orange, cream spot
FACE = ['#2a1418', '#ffe6b4', '#e8b070', '#f08aa8']          # eye, skin, skin shade, blush


def hexrgb(h): return [int(h[i:i + 2], 16) for i in (1, 3, 5)]
def to15(rgb):
    r, g, b = [int(round(max(0, min(255, v)) * 31 / 255)) for v in rgb]
    return r | g << 5 | b << 10


# ------------------------------------------------------------------------------------------------ textures (16x16)
def cap_tex():
    """orange with a big and a small cream spot; tiles (repeat on)"""
    S = 16; a = np.full((S, S), 1, np.uint8)
    yy, xx = np.mgrid[0:S, 0:S]
    def dist(cx, cy):
        dx = np.minimum(abs(xx - cx), S - abs(xx - cx)); dy = np.minimum(abs(yy - cy), S - abs(yy - cy))
        return np.hypot(dx, dy)
    d1, d2 = dist(4.5, 4.5), dist(12, 11.5)
    a[d1 <= 3.7] = 2; a[d1 <= 3.0] = 3
    a[d2 <= 2.5] = 2; a[d2 <= 1.8] = 3
    return a


def face_tex():
    """u 0-16 spans the stem's front half (left to right), v 0-16 its height (top to bottom). One texel is about
    2 units wide and 0.5 high on the stem, so the eyes are two columns wide and seven rows tall."""
    a = np.full((16, 16), 1, np.uint8)
    a[:1, :] = 2; a[15:, :] = 2                                 # shade under the cap and at the foot
    for x in (4, 5, 10, 11):
        a[3:10, x] = 0                                          # two tall eyes, two columns each (the cap hides the stem top)
    a[11:14, 7:9] = 0                                           # small open mouth
    a[10:12, 3] = 3; a[10:12, 12] = 3                           # blush
    return a


def gill_tex():
    """drawn with the cap's palette (g02lift_body2 shares it): cream with light-orange gill lines"""
    a = np.full((16, 16), 3, np.uint8)
    for x in range(0, 16, 4): a[:, x] = 2
    a[:2, :] = 1
    return a


def textures():
    """{texture name: (indices, colours)}. In a/0/7/0 file 27 g02lift_body and g02lift_body2 share one palette, so
    the cap and the gills use the cap colours, and the face goes on g02lift_on1, which has its own palette and its
    own pixels (g02lift_body2 shares its pixels with leg1, on2 with leg2; the legs are not drawn any more)."""
    return {'g02lift_body': (cap_tex(), CAP), 'g02lift_body2': (gill_tex(), CAP), 'g02lift_on1': (face_tex(), FACE)}


# ------------------------------------------------------------------------------------------------ the mesh (world units)
N = 16                                       # segments round the cap and stem
CAP_C, CAP_RX, CAP_RZ = (0.0, 13.5), 16.0, 15.0
CAP_RINGS = [(0.0, 2.2), (0.35, 1.8), (0.6, 0.8), (0.8, -0.8), (0.93, -2.4), (1.0, -3.8)]
UNDER = [(1.0, -3.8), (0.97, -4.4), (0.62, -4.0)]
STEM_C, STEM_RX, STEM_RZ = (0.0, 18.5), 10.5, 11.0
STEM_RINGS = [(1.0, -3.9), (1.06, -9.0), (1.0, -14.0)]
LIGHT = np.array([0.0, 0.75, 0.65]); LIGHT /= np.linalg.norm(LIGHT)


def ell(c, rx, rz, f, ang):
    return np.array([c[0] + rx * f * np.sin(ang), c[1] + rz * f * np.cos(ang)])   # ang 0 = +z (towards the camera)


def shade(n, lo=0.62):
    n = n / (np.linalg.norm(n) or 1); return lo + (1 - lo) * max(0.0, float(n @ LIGHT))


def ring(c, rx, rz, f, y, u_of, v, sh_of, a0=0.0, a1=2 * np.pi, n=None):
    n = n or N; pts = []
    for k in range(n + 1):
        ang = a0 + (a1 - a0) * k / n; xz = ell(c, rx, rz, f, ang)
        pts.append((np.array([xz[0], y, xz[1]]), (u_of(k / n, ang), v), sh_of(ang)))
    return pts


def zip_strip(a, b):
    """one triangle strip between two rings of the same length"""
    out = []
    for p, q in zip(a, b): out += [p, q]
    return out


def cap_strips():
    """the cap: a centre fan (as a strip) and bands down to the rim. u wraps 3 times, v follows the radius"""
    rings = []
    for f, y in CAP_RINGS:
        def sh(ang, f=f):
            return shade(np.array([np.sin(ang) * f * 1.6, 1.0 - 0.75 * f ** 2, np.cos(ang) * f * 1.6]))
        rings.append(ring(CAP_C, CAP_RX, CAP_RZ, f, y, lambda t, ang: t * 3 * 16, f * 2 * 16, sh))
    return [zip_strip(a, b) for a, b in zip(rings, rings[1:])]


def under_strips():
    rings = [ring(CAP_C, CAP_RX, CAP_RZ, f, y, lambda t, ang: t * 6 * 16, (1 - f) * 40, lambda ang: 0.72)
             for f, y in UNDER]
    return [zip_strip(a, b) for a, b in zip(rings, rings[1:])]


def stem_strips():
    """front half (angles -90..90 deg, ang 0 = +z = the camera side) carries the face; the back half samples a
    plain column of the face texture"""
    H0, H1 = STEM_RINGS[0][1], STEM_RINGS[-1][1]; out = []
    def sh(ang): return shade(np.array([np.sin(ang), 0.15, np.cos(ang)]), 0.7)
    for (f0, y0), (f1, y1) in zip(STEM_RINGS, STEM_RINGS[1:]):
        v0, v1 = (y0 - H0) / (H1 - H0) * 16, (y1 - H0) / (H1 - H0) * 16
        for a0, a1, u in ((-np.pi / 2, np.pi / 2, lambda t, ang: t * 16), (np.pi / 2, 3 * np.pi / 2, lambda t, ang: 0.5)):
            r0 = ring(STEM_C, STEM_RX, STEM_RZ, f0, y0, u, v0, sh, a0, a1, N // 2)
            r1 = ring(STEM_C, STEM_RX, STEM_RZ, f1, y1, u, v1, sh, a0, a1, N // 2)
            out.append(zip_strip(r0, r1))
    return out


# ------------------------------------------------------------------------------------------------ display lists
def pack(cmds):
    """[(op, [params])] -> packed GX command bytes (4 ops per header word)"""
    out = b''
    for i in range(0, len(cmds), 4):
        grp = cmds[i:i + 4] + [(0, [])] * (4 - len(cmds[i:i + 4]))
        out += bytes(op for op, _ in grp)
        for _, ps in grp: out += b''.join(struct.pack('<I', p & 0xffffffff) for p in ps)
    return out


def fx(v, bits=12):
    i = int(round(v * (1 << bits)))
    assert -32768 <= i < 32768, v
    return i & 0xffff


def fx10(v):
    i = int(round(v * 64)); assert -512 <= i < 512, v
    return i & 1023


def strip_list(strips, to_local):
    """triangle strips; per vertex: COLOR (baked shade, modulates the texture), TEXCOORD, VTX_10"""
    cmds = []
    for st in strips:
        cmds.append((0x40, [2]))
        for p, uv, sh in st:
            g = 255 * sh
            cmds.append((0x20, [to15((g, g, g))]))
            cmds.append((0x22, [fx(uv[0], 4) | fx(uv[1], 4) << 16]))
            l = to_local(p)
            cmds.append((0x24, [fx10(l[0]) | fx10(l[1]) << 10 | fx10(l[2]) << 20]))
        cmds.append((0x41, []))
    return pack(cmds)


def empty_list():
    z = [(0x23, [0, 0])] * 3
    return pack([(0x40, [0])] + z + [(0x41, [])])


def rewrite_model(d, root_matrix, up):
    """d: the gym02lift BMD0 bytes; root_matrix: the 4x4 world matrix of node 0's shapes, up: the model's posScale"""
    d = bytearray(d)
    inv = np.linalg.inv(root_matrix)
    def to_local(p): return (inv @ np.array([p[0], p[1], p[2], 1.0]))[:3] / up
    mdl = struct.unpack_from('<I', d, 16)[0]                 # first block (MDL0)
    assert d[mdl:mdl + 4] == b'MDL0'
    n_models = d[mdl + 9]; assert n_models == 1
    # MDL0 dict: header 8 + tree 4*(n+1), then entry size/len, entries
    p = mdl + 8 + 8 + 4 * 2; mo = mdl + struct.unpack_from('<I', d, p + 4)[0]
    _, _, mat_off, shp_off, _ = struct.unpack_from('<5I', d, mo)
    # materials: draw both faces for the ones we use
    mb = mo + mat_off; n = d[mb + 4 + 1]
    q = mb + 4 + 8 + 4 * (n + 1); esz = struct.unpack_from('<H', d, q)[0]
    for i in range(n):
        o = mb + struct.unpack_from('<I', d, q + 4 + esz * i)[0]
        struct.pack_into('<I', d, o + 12, struct.unpack_from('<I', d, o + 12)[0] | 0xC0)
    # shapes
    sb = mo + shp_off; n = d[sb + 1]
    q = sb + 8 + 4 * (n + 1); esz = struct.unpack_from('<H', d, q)[0]
    heads = [sb + struct.unpack_from('<I', d, q + 4 + esz * i)[0] for i in range(n)]
    spans = [(h + struct.unpack_from('<I', d, h + 8)[0], struct.unpack_from('<I', d, h + 12)[0]) for h in heads]
    start = min(s for s, _ in spans); end = max(s + l for s, l in spans)
    assert sum(l for _, l in spans) == end - start, 'display lists are not one block'
    lists = {1: strip_list(cap_strips(), to_local), 3: strip_list(stem_strips(), to_local),
             0: strip_list(under_strips(), to_local)}             # shape 1 = body (cap), 3 = on1 (face), 0 = body2
    blob = b''; at = start
    for i, h in enumerate(heads):
        dl = lists.get(i, empty_list())
        struct.pack_into('<II', d, h + 8, at - h, len(dl)); blob += dl; at += len(dl)
    assert len(blob) <= end - start, ('the mushroom does not fit', len(blob), end - start)
    d[start:end] = blob + bytes(end - start - len(blob))
    return bytes(d), len(blob), end - start


def root_and_scale(d):
    """node 0's matrix (translation + scale, no rotation in this model) and the model's posScale"""
    mdl = struct.unpack_from('<I', d, 16)[0]; mo = mdl + struct.unpack_from('<I', d, mdl + 28)[0]
    up = struct.unpack_from('<i', d, mo + 20 + 8)[0] / 4096
    no = mo + 20 + 0x2C; n = d[no + 1]; q = no + 8 + 4 * (n + 1)
    o = no + struct.unpack_from('<I', d, q + 4)[0]
    flags = struct.unpack_from('<H', d, o)[0]; assert flags & 7 == 2, hex(flags)   # T present, R identity, S present
    t = [x / 4096 for x in struct.unpack_from('<3i', d, o + 4)]; s = [x / 4096 for x in struct.unpack_from('<3i', d, o + 16)]
    M = np.diag(s + [1.0]); M[:3, 3] = t
    return M, up


def build_model(d):
    M, up = root_and_scale(d)
    return rewrite_model(d, M, up)
