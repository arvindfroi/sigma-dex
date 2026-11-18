"""Azalea Gym looks like a Fairy gym (Arvind, 2026-11-18): the Bug gym's textures are repainted in their own pixels.

  ~/sigma-toolchain/venv312/bin/python scripts/origin_custom/fairy_gym/fairy_look.py IN.nds OUT.nds [PREVIEW_DIR]

Everything visible in the gym comes from two texture sets that only area 29 (maps 136 and 180, the gym) uses:
- a/0/4/4 file 29, the map textures: the autumn leaves (g02ochi*), trees (g02tree*, tree01gs), hedges (g02kusa_a),
  floor (g02yuka_*), back wall (g02wall_*), pit walls (g02pond), entrance carpet (g02ent_*), slope/cliff, the silk
  walkways (g02rope_a), the webs in the pit (g02spider) and the bug emblem on the floor (g02mark).
- a/0/7/0 file 27, the building textures: the Spinarak carts (g02lift_*), the levers (g2switch*), the switch bridges
  (gym02rope_1/2) and the potted plant (plant_x).
Neither archive has per-outfit copies in data/clothes1|2, and every texture keeps its size and format, so the files are
written back in place (same offsets: savestates and the test jump still work).

How each texture changes (the picture stays the game's own pixels; only colours change, except the two new ones):
- ramp: every palette colour is moved onto a Fairy colour ramp by its brightness, so shading and outlines stay.
- hue: only the colourful entries are moved to a new hue (grey metal and outlines stay).
- the cart (room model 118, the Spinarak) becomes Fleuroom's mushroom head: see fleuroom_cart.py.
- g02spider (A5I3, 8 colours + alpha) is drawn new: an opaque dusk-violet flower bed with glitter (Arvind: "flowers
  and glitter" in the pit). g02mark is drawn new: a sparkle in a ring instead of the bug emblem.
Nothing here holds game data; it reads Arvind's own ROM and writes a new one."""
import colorsys, os, struct, sys
import numpy as np
import ndspy.rom, ndspy.narc
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fleuroom_cart

# ---------------------------------------------------------------------------------------------- texture container
def u32(d, o): return struct.unpack_from('<I', d, o)[0]


def dict_read(d, o, esz):
    """NITRO dictionary: entries (esz bytes each) and 16-byte names"""
    n = d[o + 1]; size = struct.unpack_from('<H', d, o + 2)[0]
    p = o + 8 + 4 * (n + 1)                                   # after the patricia tree
    esz_, dsz = struct.unpack_from('<HH', d, p); p += 4
    ents = [bytes(d[p + esz_ * i:p + esz_ * (i + 1)]) for i in range(n)]
    names_o = p + esz_ * n
    names = [bytes(d[names_o + 16 * i:names_o + 16 * (i + 1)]).rstrip(b'\0').decode() for i in range(n)]
    return list(zip(ents, names))


def tex0(d):
    """textures and palettes of a BTX0 file, with absolute offsets"""
    assert d[:4] == b'BTX0', d[:4]
    bo = u32(d, 16); assert d[bo:bo + 4] == b'TEX0'
    toff = struct.unpack_from('<H', d, bo + 14)[0]; tbo = u32(d, bo + 20)
    poff = u32(d, bo + 52)
    pbo = u32(d, bo + 56)
    texs = {}
    for e, nm in dict_read(d, bo + toff, 8):
        p = struct.unpack_from('<I', e, 0)[0]
        fmt = (p >> 26) & 7; w = 8 << ((p >> 20) & 7); h = 8 << ((p >> 23) & 7)
        bpp = {1: 8, 2: 2, 3: 4, 4: 8, 6: 8, 7: 16}[fmt]
        texs[nm] = dict(name=nm, pal=PAL_OF.get(nm, nm + '_pl'), fmt=fmt, w=w, h=h, c0=(p >> 29) & 1, off=bo + tbo + ((p & 0xffff) << 3),
                        size=w * h * bpp // 8)
    pals = {}
    for e, nm in dict_read(d, bo + poff, 4):
        pals[nm] = bo + pbo + (struct.unpack_from('<H', e, 0)[0] << 3)
    return texs, pals


PAL_OF = {'d_mat01': 'd_mat01', 'tree01gs': 'tree01', 'cliff01gs': 'cliff01', 'tree01_un': 'tree01_un'}


def get_idx(d, x):
    raw = np.frombuffer(bytes(d[x['off']:x['off'] + x['size']]), np.uint8)
    if x['fmt'] == 2: a = np.stack([(raw >> s) & 3 for s in (0, 2, 4, 6)], 1).reshape(-1)
    elif x['fmt'] == 3: a = np.stack([(raw >> s) & 15 for s in (0, 4)], 1).reshape(-1)
    else: a = raw.copy()
    return a.reshape(x['h'], x['w'])


def put_idx(d, x, a):
    a = a.reshape(-1).astype(np.uint8)
    if x['fmt'] == 2: raw = a[0::4] | a[1::4] << 2 | a[2::4] << 4 | a[3::4] << 6
    elif x['fmt'] == 3: raw = a[0::2] | a[1::2] << 4
    else: raw = a
    assert len(raw) == x['size']
    d[x['off']:x['off'] + x['size']] = raw.astype(np.uint8).tobytes()


def ncols(fmt): return {2: 4, 3: 16, 6: 8, 1: 32, 4: 256}[fmt]


def get_pal(d, o, n): return [struct.unpack_from('<H', d, o + 2 * i)[0] for i in range(n)]
def set_pal(d, o, cols):
    for i, c in enumerate(cols): struct.pack_into('<H', d, o + 2 * i, c)
def to_rgb(c): return np.array([(c & 31) * 255 / 31, ((c >> 5) & 31) * 255 / 31, ((c >> 10) & 31) * 255 / 31])
def to15(rgb):
    r, g, b = [int(round(max(0, min(255, v)) * 31 / 255)) for v in rgb]
    return r | g << 5 | b << 10
def hexrgb(h): return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float)
def luma(rgb): return float(rgb @ [0.299, 0.587, 0.114]) / 255


# ---------------------------------------------------------------------------------------------- colour rules
def ramp_map(keys, lo=None, hi=None):
    """colour -> the colour at its brightness on a ramp of key colours (dark to light). lo/hi: the brightness range of
    the source palette, so its darkest entry lands on the first key and its lightest on the last."""
    K = [hexrgb(k) for k in keys]
    def f(rgb):
        l = luma(rgb)
        t = 0.0 if hi is None or hi <= lo else (l - lo) / (hi - lo)
        t = min(max(t, 0), 1) * (len(K) - 1); i = min(int(t), len(K) - 2); u = t - i
        return K[i] * (1 - u) + K[i + 1] * u
    return f


def recolour_ramp(d, pal_off, n, keys, used):
    """used: the palette entries the textures really draw (their brightness range spans the ramp)"""
    cols = get_pal(d, pal_off, n); rgbs = [to_rgb(c) for c in cols]
    ls = [luma(rgbs[i]) for i in used]; f = ramp_map(keys, min(ls), max(ls))
    set_pal(d, pal_off, [to15(f(rgbs[i])) if i in used else cols[i] for i in range(n)])


def recolour_hue(d, pal_off, n, rules, min_sat=0.22):
    """rules: list of (hue range lo, hi in degrees, new hue, sat scale, value lift). Grey entries stay."""
    cols = get_pal(d, pal_off, n); out = []
    for c in cols:
        r, g, b = to_rgb(c) / 255; h, s, v = colorsys.rgb_to_hsv(r, g, b); deg = h * 360
        for lo, hi, nh, ss, vl in rules:
            if s >= min_sat and (lo <= deg < hi if lo <= hi else (deg >= lo or deg < hi)):
                h, s, v = nh / 360, min(1, s * ss), min(1, v + vl * (1 - v)); break
        out.append(to15(np.array(colorsys.hsv_to_rgb(h, s, v)) * 255))
    set_pal(d, pal_off, out)


# Fairy ramps (dark -> light). Pinks for blossoms and petals, lilac stone, mint hedges, cream floor.
SAKURA = ['#6b2d55', '#b4507f', '#e98bb0', '#f7c2d6', '#fff0f6']          # fallen petals
BLOSSOM = ['#4f2346', '#93406f', '#d5739f', '#f3aecb', '#ffe3ef']          # tree crowns
TRUNK = ['#3f2a35', '#6e4a5a', '#9a7282', '#c9a3b2']                       # trunk bases (rosy bark)
MINT = ['#1f4d45', '#3b8a74', '#6fc4a2', '#b4ecd2', '#e9fff4']             # hedges
FLOOR = ['#8a6f86', '#c4a3b9', '#e7cbd8', '#f6e6ee', '#fff8fb']            # gym floor
PEBBLE = ['#7d6595', '#ad94c6', '#d6c6ea', '#f1e9fb']                      # floor stones
WALL = ['#6c5486', '#a58bc0', '#d7c2e6', '#f3e8fb', '#fffaff']             # the wavy back wall
WALLUP = ['#4c3a63', '#8a73a8', '#cbb6e0', '#efe6f9']
PITWALL = ['#2c1b3a', '#5a3f6e', '#8f6fa3', '#c7a9d6', '#ecdcf4']          # pit walls
CLIFF = ['#7a5670', '#b38aa4', '#dcb6c9', '#f5dde8']                       # slope and cliff edge
CARPET = ['#7b2e5c', '#c2558e', '#ec90bb', '#fbd0e3']                      # entrance carpet (was green)
RIBBON = ['#d76a9b', '#fde3ee']                                            # silk walkways -> ribbon (2 tones)
BRIDGE_PINK = ['#8e2f62', '#d8679d', '#f7b4d2']                            # orange switch bridge -> pink
BRIDGE_BLUE = ['#3a4f93', '#7d97de', '#c3d4fb']                            # blue switch bridge -> periwinkle

MAP_RULES = [  # (texture name(s), palette name, rule, args)
    ('g02ochi01_a_pl', 16, 'ramp', SAKURA), ('g02ochi04_pl', 16, 'ramp', SAKURA),
    ('g02tree_pl', 16, 'ramp', BLOSSOM), ('g02tree2_pl', 16, 'ramp', BLOSSOM), ('tree01', 16, 'ramp', BLOSSOM),
    ('g02tree_un_pl', 16, 'ramp', TRUNK), ('g02tree_un2_pl', 16, 'ramp', TRUNK), ('tree01_un', 16, 'ramp', TRUNK),
    ('g02kusa_a_pl', 16, 'ramp', MINT),
    ('g02yuka_b_pl', 16, 'ramp', FLOOR), ('g02yuka_sub_pl', 16, 'ramp', PEBBLE),
    ('g02wall_b1_pl', 16, 'ramp', WALL), ('g02wall_up1_pl', 4, 'ramp', WALLUP),
    ('g02pond_pl', 16, 'ramp', PITWALL), ('slope_pl', 16, 'ramp', CLIFF), ('cliff01', 16, 'ramp', CLIFF),
    ('g02ent_b_pl', 16, 'ramp', CARPET),
    ('g02rope_a_pl', 2, 'ramp', RIBBON),
]
GREEN_TO_PINK = [(60, 180, 330, 0.75, 0.25)]
BUILD_RULES = [
    ('gym02rope_1_pl', 4, 'ramp', BRIDGE_PINK), ('gym02rope_2_pl', 4, 'ramp', BRIDGE_BLUE),
    ('g2switch_r.1_pl', 16, 'hue', [(330, 60, 330, 0.8, 0.2)]), ('g2switch_r.2_pl', 16, 'hue', [(330, 60, 330, 0.8, 0.2)]),
    ('g2switch.1_pl', 16, 'hue', [(170, 260, 225, 0.7, 0.25)]), ('g2switch.2_pl', 16, 'hue', [(170, 260, 225, 0.7, 0.25)]),
    ('plant_x_pl', 16, 'hue', GREEN_TO_PINK),
    ('d_mat01', 4, 'hue', [(330, 40, 335, 0.7, 0.3)]),   # the red door mat -> pink
]

def used_entries(d, texs, pals, pal_off):
    """palette entries drawn by every texture that uses this palette (a clear index 0 is not drawn)"""
    used = set()
    for x in texs.values():
        if x['pal'] in pals and pals[x['pal']] == pal_off and x['fmt'] in (2, 3):
            u = set(np.unique(get_idx(d, x)).tolist())
            if x['c0']: u.discard(0)
            used |= u
    return sorted(used)


def apply_rules(d, rules):
    texs, pals = tex0(d)
    for name, n, kind, arg in rules:
        o = pals[name]
        if kind == 'ramp': recolour_ramp(d, o, n, arg, used_entries(d, texs, pals, o))
        else: recolour_hue(d, o, n, arg)
    return texs, pals


# ---------------------------------------------------------------------------------------------- the two new pictures
def blossom(img, cx, cy, R, petal, rim, centre, S=128):
    """a five-petal blossom of radius R texels, drawn with wrap-around"""
    for dy in range(-R - 1, R + 2):
        for dx in range(-R - 1, R + 2):
            r = np.hypot(dx, dy); ang = np.arctan2(dy, dx)
            edge = R * (0.62 + 0.38 * abs(np.cos(2.5 * ang)))       # five round petals
            if r <= edge:
                v = centre if r <= R * 0.28 else (rim if r > edge - 1.0 else petal)
                img[(cy + dy) % S, (cx + dx) % S] = v


def sparkle(img, cx, cy, R, S=128, core=5, arm=4):
    for k in range(-R, R + 1):
        w = 1 if abs(k) < R * 0.45 else 0
        for t in range(-w, w + 1):
            img[(cy + k) % S, (cx + t) % S] = arm; img[(cy + t) % S, (cx + k) % S] = arm
    img[cy % S, cx % S] = core


def flower_bed(seed=7):
    """128x128 A5I3 (8 colours, 5-bit alpha), opaque, tiles seamlessly: a dusk-violet flower bed with glitter.
    The pit shows this texture about three times smaller than its texels, so flowers are drawn big (radius 5-9).
    0 base, 1 shade, 2 leaf, 3 deep pink, 4 light pink, 5 white, 6 yellow, 7 lilac"""
    rng = np.random.default_rng(seed); S = 128
    img = np.zeros((S, S), np.uint8)
    yy, xx = np.mgrid[0:S, 0:S]
    n = sum(np.sin(2 * np.pi * (xx * a + yy * b) / S + p) for a, b, p in [(1, 2, 0.3), (3, -1, 1.7), (2, 3, 4.1), (-4, 1, 2.2)])
    img[n > 1.1] = 1
    pts = []
    def free(x, y, r):
        return all(np.hypot(min(abs(x - a), S - abs(x - a)), min(abs(y - b), S - abs(y - b))) > r + q for a, b, q in pts)
    for _ in range(140):                                     # leaves: short diagonal strokes
        x, y = map(int, rng.integers(0, S, 2))
        for k in range(3): img[(y + k) % S, (x + k * (1 if x % 2 else -1)) % S] = 2
    kinds = [(3, 1, 6), (4, 3, 6), (7, 2, 5), (5, 4, 6)]    # (petal, rim, centre)
    for R, count in [(9, 5), (7, 8), (5, 12)]:
        k = tries = 0
        while k < count and tries < 4000:
            tries += 1; x, y = map(int, rng.integers(0, S, 2))
            if not free(x, y, R + 2): continue
            pts.append((x, y, R)); k += 1
            p_, rim, c = kinds[int(rng.integers(0, len(kinds)))]
            blossom(img, x, y, R, p_, rim, c)
    k = tries = 0
    while k < 14 and tries < 4000:
        tries += 1; x, y = map(int, rng.integers(0, S, 2)); R = int(rng.integers(3, 6))
        if not free(x, y, R + 1): continue
        pts.append((x, y, R)); k += 1; sparkle(img, x, y, R, arm=4 if R > 3 else 7)
    for _ in range(70):                                       # single-texel glitter
        x, y = rng.integers(0, S, 2)
        if img[y, x] in (0, 1): img[y, x] = 5 if rng.random() < 0.4 else 7
    cols = ['#3b2153', '#2c173f', '#5a3a72', '#e0609c', '#f6b3d1', '#fff7fb', '#ffe27a', '#b99cf0']
    return (img | (31 << 3)).astype(np.uint8), [to15(hexrgb(c)) for c in cols]


def sparkle_mark():
    """64x64, 4 colours, index 0 clear: a ring with a four-point sparkle and two small ones (was the bug emblem).
    1 deep rose, 2 pink, 3 white"""
    S = 64; c = (S - 1) / 2; yy, xx = np.mgrid[0:S, 0:S]; r = np.hypot(xx - c, yy - c)
    img = np.zeros((S, S), np.uint8)
    img[(r <= 29.5) & (r > 25.5)] = 1
    img[(r <= 25.5) & (r > 23.5)] = 2
    img[r <= 23.5] = 3
    def star(cx, cy, R, w, val):
        dx, dy = np.abs(xx - cx), np.abs(yy - cy)
        m = (dx / w) ** 0.6 + (dy / R) ** 0.6 <= 1
        m |= (dx / R) ** 0.6 + (dy / w) ** 0.6 <= 1
        img[m & (r <= 23.5)] = val
    star(c, c + 1, 17.5, 5.5, 1); star(c, c + 1, 12, 3.2, 2)
    star(c + 13, c - 12, 6, 2.0, 2); star(c - 13, c + 13, 5, 1.8, 2)
    cols = [to15(hexrgb(h)) for h in ('#f6b3d1', '#b03a77', '#e98bb0', '#fff7fb')]
    return img, cols


# ---------------------------------------------------------------------------------------------- ROM
MAP_TEX, MAP_IDX = 'a/0/4/4', 29
BLD_TEX, BLD_IDX = 'a/0/7/0', 27
CART = [('a/1/4/8', 118), ('fielddata/build_model/bm_room.narc', 118)]   # two FAT entries of the room models


def build(d_map, d_bld):
    d_map, d_bld = bytearray(d_map), bytearray(d_bld)
    texs, pals = apply_rules(d_map, MAP_RULES)
    img, cols = flower_bed(); x = texs['g02spider']; assert x['fmt'] == 6 and x['w'] == 128
    put_idx(d_map, x, img); set_pal(d_map, pals['g02spider_pl'], cols)
    img, cols = sparkle_mark(); x = texs['g02mark']; assert x['fmt'] == 2 and x['w'] == 64
    put_idx(d_map, x, img); set_pal(d_map, pals['g02mark_pl'], cols)
    btexs, bpals = apply_rules(d_bld, BUILD_RULES)
    for nm, (img, cols) in fleuroom_cart.textures().items():     # the cart's textures: Fleuroom's cap and face
        x = btexs[nm]; assert x['fmt'] == 2 and img.shape == (x['h'], x['w']), nm
        put_idx(d_bld, x, img); set_pal(d_bld, bpals[nm + '_pl'], [fleuroom_cart.to15(fleuroom_cart.hexrgb(c)) for c in cols])
    return bytes(d_map), bytes(d_bld)


def narc_member_span(rom_bytes, rom, path, idx):
    """absolute ROM offset of NARC member idx of file path"""
    fid = rom.filenames.idOf(path)
    start = struct.unpack_from('<I', rom_bytes, u32(rom_bytes, 0x48) + 8 * fid)[0]
    n = ndspy.narc.NARC(rom.files[fid])
    raw = bytes(rom.files[fid])
    # FATB follows the 16-byte header; FIMG data base after FNTB
    fatb = 16; nfiles = u32(raw, fatb + 8)
    s, e = struct.unpack_from('<II', raw, fatb + 12 + 8 * idx)
    fntb = fatb + u32(raw, fatb + 4); fimg = fntb + u32(raw, fntb + 4)
    assert bytes(n.files[idx]) == raw[fimg + 8 + s:fimg + 8 + e]
    return start + fimg + 8 + s, e - s


def main(src, dst, preview=None):
    rom = ndspy.rom.NintendoDSRom.fromFile(src); out = bytearray(open(src, 'rb').read())
    spans = {}
    for path, idx in ((MAP_TEX, MAP_IDX), (BLD_TEX, BLD_IDX)):
        spans[path] = narc_member_span(out, rom, path, idx)
    o1, n1 = spans[MAP_TEX]; o2, n2 = spans[BLD_TEX]
    new_map, new_bld = build(out[o1:o1 + n1], out[o2:o2 + n2])
    assert len(new_map) == n1 and len(new_bld) == n2
    out[o1:o1 + n1] = new_map; out[o2:o2 + n2] = new_bld
    done = set()
    for path, idx in CART:                                      # the cart model becomes Fleuroom's mushroom head
        o, n = narc_member_span(out, rom, path, idx)
        if o in done: continue
        new, used, room = fleuroom_cart.build_model(bytes(out[o:o + n])); assert len(new) == n
        out[o:o + n] = new; done.add(o); print('cart model at', hex(o), '%d of %d display-list bytes' % (used, room))
    open(dst, 'wb').write(out)
    print('fairy gym textures ->', dst)
    if preview: write_preview(bytes(out[o1:o1 + n1]), bytes(out[o2:o2 + n2]), preview)


def write_preview(d_map, d_bld, outdir):
    """all repainted textures as PNGs (local check only)"""
    from PIL import Image
    os.makedirs(outdir, exist_ok=True)
    for d in (d_map, d_bld):
        texs, pals = tex0(d)
        for nm, x in texs.items():
            pn = x['pal']
            if pn not in pals: continue
            a = get_idx(d, x); cols = np.array([to_rgb(c) for c in get_pal(d, pals[pn], ncols(x['fmt']) if x['fmt'] != 6 else 8)], np.uint8)
            if x['fmt'] == 6: rgb = cols[a & 7]; al = ((a.astype(int) >> 3) * 255 // 31).astype(np.uint8)
            else: rgb = cols[a]; al = np.where((a == 0) & bool(x['c0']), 0, 255).astype(np.uint8)
            Image.fromarray(np.dstack([rgb, al]), 'RGBA').save(os.path.join(outdir, nm + '.png'))


if __name__ == '__main__':
    main(*sys.argv[1:4])
