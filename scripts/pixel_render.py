"""Pixel renderer: build a sprite from clean cel-shaded art the way a spriter does, instead of shrinking it.

Shrinking a picture to 64 pixels turns its lines and faces to mud. Game sprites are built instead:
1. find the materials (flat colour areas) of the art, ignoring its line art and shading
2. lay the material map onto the sprite grid (majority per cell); specks of a material join their
   surroundings, except very dark and very light ones (pupils, glints)
3. hard tones per material from the art's own light and dark (shadows a little cooler, lights
   warmer); the inside of the bottom and right edges is in shadow, light comes from the upper left
4. a dark outline around the silhouette and between materials that contrast
5. small features (pupils, eye whites, glints, brows, mouths) always get their pixels

It needs clean cel-shaded art on a white or transparent background: the sprite worker's
"sprite-official" style has Qwen draw that first. Same input, same sprite: nothing is random.
`gen3` is the Sigma look, modelled on the games' own sprites (see shade_gen3); `bold` is the
older look (near-black outline, two flat tones).
"""
import cv2
import numpy as np
from PIL import Image


def lab(rgb):
    return cv2.cvtColor(rgb.astype(np.uint8).reshape(-1, 1, 3), cv2.COLOR_RGB2LAB).reshape(rgb.shape).astype(np.float32)


def to_rgb(l):
    return cv2.cvtColor(np.clip(l, 0, 255).astype(np.uint8).reshape(-1, 1, 3), cv2.COLOR_LAB2RGB).reshape(l.shape)


def mask_of(rgb):
    """The creature: everything not connected to the white border."""
    bg = (rgb.min(axis=2) > 232).astype(np.uint8)
    n, labels = cv2.connectedComponents(bg, connectivity=4)
    border = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))) - {0}
    outside = np.isin(labels, list(border)) & (bg == 1)
    return ~outside


def load(path):
    """The picture on white (a transparent background becomes white)."""
    image = Image.open(path).convert("RGBA")
    flat = Image.new("RGBA", image.size, "white")
    flat.alpha_composite(image)
    return np.array(flat.convert("RGB"))


def box_of(path):
    ys, xs = np.nonzero(mask_of(load(path)))
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def render(path, size=54, k=12, materials=9, view="front", window=None, fit=None, bold=False, gen3=False):
    """window: the part of the picture to use (x0, y0, x1, y1), e.g. shared by two animation frames;
    fit: (width, height) in sprite pixels instead of `size` for the longest side;
    bold: the clean, bold look (near-black outline, two tones, only strong inner lines);
    gen3: the look of the games' own sprites, measured on them (see shade_gen3)."""
    art = load(path)
    mask = mask_of(art)
    x0, y0, x1, y1 = window or box_of(path)
    art, mask = art[y0:y1, x0:x1], mask[y0:y1, x0:x1]
    h, w = mask.shape
    scale = min(fit[0] / w, fit[1] / h) if fit else size / max(h, w)
    gh, gw = max(1, round(h * scale)), max(1, round(w * scale))
    big = cv2.resize(art, (gw * k, gh * k), interpolation=cv2.INTER_AREA)
    m = cv2.resize(mask.astype(np.uint8), (gw * k, gh * k), interpolation=cv2.INTER_NEAREST).astype(bool)
    L = lab(big)
    line = m & (L[..., 0] < 70)                                  # the art's ink lines (and very dark parts)

    # 1. materials: cluster colour mostly by hue and chroma, lightness counts less (so shadows join their base)
    pts = L[m & ~line].copy()
    feat = np.column_stack([pts[:, 0] * 0.35, pts[:, 1], pts[:, 2]])
    cv2.setRNGSeed(1)
    _, lab_idx, centers = cv2.kmeans(feat.astype(np.float32), materials, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.5), 4, cv2.KMEANS_PP_CENTERS)
    mat = np.full(m.shape, -1, np.int32)
    mat[m & ~line] = lab_idx.ravel()
    # line pixels take the material around them (so lines do not become their own material)
    filled = mat.copy()
    for _ in range(k):
        if not ((filled < 0) & m).any():
            break
        grown = cv2.dilate((filled + 1).astype(np.float32), np.ones((3, 3), np.uint8)).astype(np.int32) - 1
        filled = np.where((filled < 0) & m, grown, filled)

    # 2. onto the grid: majority material per cell, cell solid if half covered
    cells = np.full((gh, gw), -1, np.int32)
    tone = np.zeros((gh, gw), np.float32)                         # the art's lightness in the cell (non-line pixels)
    ink = np.zeros((gh, gw), np.float32)                          # share of the cell that is ink
    for y in range(gh):
        for x in range(gw):
            cm = m[y * k:(y + 1) * k, x * k:(x + 1) * k]
            if cm.mean() < 0.5:
                continue
            cf = filled[y * k:(y + 1) * k, x * k:(x + 1) * k][cm]
            cf = cf[cf >= 0]
            if not cf.size:
                continue
            cells[y, x] = np.bincount(cf).argmax()
            cl = line[y * k:(y + 1) * k, x * k:(x + 1) * k]
            ink[y, x] = cl[cm].mean()
            own = L[y * k:(y + 1) * k, x * k:(x + 1) * k][cm & ~cl]
            tone[y, x] = own[:, 0].mean() if own.size else 0

    base_lab = np.array([L[(filled == i) & ~line].mean(axis=0) if ((filled == i) & ~line).any() else [0, 128, 128] for i in range(materials)])
    # merge specks: a patch of a material smaller than `speck` pixels joins the material around it
    # (keeps mouths and bills calm); very dark and very light patches stay, they are eyes and glints
    speck = 4 if bold else 3
    for _ in range(2):
        for i in range(materials):
            if base_lab[i][0] < 50 or base_lab[i][0] > 235:
                continue
            n, lbl = cv2.connectedComponents((cells == i).astype(np.uint8), connectivity=4)
            for j in range(1, n):
                part = lbl == j
                if part.sum() >= speck:
                    continue
                ring = cv2.dilate(part.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~part & (cells >= 0) & (cells != i)
                if ring.any():
                    cells[part] = np.bincount(cells[ring]).argmax()

    # 5 (prepared). small features: tiny dark or light blobs in the art (pupils, eye whites, glints, nostrils)
    features = []
    for kind, sel in (("dark", m & (L[..., 0] < 45)), ("light", m & (L[..., 0] > 235))):
        n, lbl, stats, cent = cv2.connectedComponentsWithStats(sel.astype(np.uint8), connectivity=8)
        for i in range(1, n):
            area = stats[i, cv2.CC_STAT_AREA]
            bw, bh = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
            if area >= 0.25 * k * k and max(bw, bh) <= 4 * k and min(bw, bh) >= 0.35 * k:   # blob-like, not a long ink line
                features.append((kind, int(cent[i][1] // k), int(cent[i][0] // k), area / (k * k)))

    # face strokes: ink drawn inside the creature (brows, eyelids, mouth, pupils) that is not part of the
    # outer contour, in the upper part of the drawing; every cell such a stroke crosses becomes dark
    edge_band = m & ~cv2.erode(m.astype(np.uint8), np.ones((k // 2 * 2 + 1, k // 2 * 2 + 1), np.uint8)).astype(bool)
    n, lbl, stats, _ = cv2.connectedComponentsWithStats(line.astype(np.uint8), connectivity=8)
    strokes = np.zeros((gh, gw), bool)
    top_limit = int(gh * 0.5)
    for i in range(1, n):
        x0, y0, bw, bh, area = stats[i]
        if max(bw, bh) > 0.3 * size * k or area < 0.15 * k * k:
            continue
        comp = lbl == i
        if (comp & edge_band).mean() > 0 and (comp & edge_band).sum() > 0.3 * comp.sum():
            continue
        cov = comp.reshape(gh, k, gw, k).mean(axis=(1, 3))
        strokes |= (cov >= 0.18)
    strokes[top_limit:] = False

    if gen3:
        cells = smooth_silhouette(cells)
        out = shade_gen3(cells, tone, ink, base_lab, materials, strokes)
        # face strokes are drawn by shade_gen3 in the part's own outline tone, not stamped in black
        return finish(out, cells, features, np.zeros_like(strokes), by_material=True)

    # 3. three hard tones per material from the art's own light and dark
    rgb = np.zeros((gh, gw, 3), np.uint8)
    bandmap = np.ones((gh, gw), np.int8)                          # 0 shadow, 1 base, 2 light
    tones = {}
    for i in range(materials):
        sel = cells == i
        if not sel.any():
            continue
        t = tone[sel]
        lo, hi = np.percentile(t, 30), np.percentile(t, 88)
        b = base_lab[i]
        drop = 14 if b[0] > 200 else 28                      # white parts get a softer shadow
        tones[i] = [to_rgb(np.array(c, np.float32).reshape(1, 1, 3))[0, 0] for c in
                    (b + [-drop, 3, -6], b, b + [min(22, 250 - b[0]), -2, 4])]   # shadows a little cooler, lights warmer
        bandmap[sel] = np.where(t < lo - 4, 0, np.where(t > hi + 2, 2, 1)) if not bold else np.where(t < np.percentile(t, 22) - 6, 0, 1)
    solid = cells >= 0
    # Gen 3 rim shading: the inside of the bottom and right edges is always in shadow, lights only face the upper left
    pad = np.pad(cells, 1, constant_values=-1)
    below_or_right_empty = solid & ((pad[2:, 1:-1] < 0) | (pad[1:-1, 2:] < 0))
    rim = solid & ~below_or_right_empty & ((np.pad(below_or_right_empty, 1)[2:, 1:-1]) | (np.pad(below_or_right_empty, 1)[1:-1, 2:]))
    bandmap[rim & (bandmap == 1)] = 0
    up_or_left_empty = solid & ((pad[:-2, 1:-1] < 0) | (pad[1:-1, :-2] < 0))
    bandmap[(bandmap == 2) & below_or_right_empty] = 1
    # smooth the bands: a shade pixel with no same-shade neighbour takes the shade around it
    for _ in range(2):
        pb = np.pad(bandmap, 1, constant_values=-1); pc = np.pad(cells, 1, constant_values=-2)
        same = sum(((pb[1 + dy:gh + 1 + dy, 1 + dx:gw + 1 + dx] == bandmap) & (pc[1 + dy:gh + 1 + dy, 1 + dx:gw + 1 + dx] == cells)).astype(int)
                   for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)))
        lone = solid & (same == 0) & ~rim
        bandmap[lone] = 1
    for i, (s0, s1, s2) in tones.items():
        sel = cells == i
        rgb[sel & (bandmap == 0)] = s0; rgb[sel & (bandmap == 1)] = s1; rgb[sel & (bandmap == 2)] = s2

    # 4. outlines: silhouette edge (lighter on the lit upper-left side, darkest at the bottom right),
    #    and boundaries between materials that contrast
    out = rgb.copy()
    # how big the patch of its material is that each cell belongs to: lines are only drawn between
    # patches big enough to be parts (a bill, a belly), not between small flecks of a pattern
    patch = np.zeros((gh, gw), np.int32)
    for i in range(materials):
        n, lbl, stats, _ = cv2.connectedComponentsWithStats((cells == i).astype(np.uint8), connectivity=4)
        for j in range(1, n):
            patch[lbl == j] = stats[j, cv2.CC_STAT_AREA]
    part_size = 10 if bold else 0
    dark_of = {i: to_rgb(np.array(base_lab[i] * [0.32, 1, 1], np.float32).reshape(1, 1, 3))[0, 0] for i in range(materials)}
    if bold:
        dark_of = {i: to_rgb(np.array([base_lab[i][0] * 0.12, 128 + (base_lab[i][1] - 128) * 0.3, 128 + (base_lab[i][2] - 128) * 0.3], np.float32).reshape(1, 1, 3))[0, 0] for i in range(materials)}
    lit_of = {i: to_rgb(np.array(base_lab[i] * [0.55, 1, 1], np.float32).reshape(1, 1, 3))[0, 0] for i in range(materials)}
    for y in range(gh):
        for x in range(gw):
            c = cells[y, x]
            if c < 0:
                continue
            nb = [pad[y + 1 + dy, x + 1 + dx] for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))]
            if -1 in nb:
                lit = (nb[0] == -1 or nb[2] == -1) and nb[1] != -1 and nb[3] != -1
                out[y, x] = lit_of[c] if lit and not bold else dark_of[c]
                continue
            for o in nb:
                if o != c and o >= 0:
                    d = np.linalg.norm(base_lab[c] - base_lab[o])
                    # draw the line on the darker side, so the lighter part keeps its size
                    if d > (40 if bold else 28) and base_lab[c][0] <= base_lab[o][0] and patch[y, x] >= part_size and \
                            min(patch[y + dy, x + dx] for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
                                if 0 <= y + dy < gh and 0 <= x + dx < gw and cells[y + dy, x + dx] == o) >= part_size:
                        out[y, x] = dark_of[c]
                        break
            if ink[y, x] > (0.45 if y < gh * 0.5 else (2 if bold else 0.65)):     # strong ink inside a part (mouth, eyelid); stricter on the body
                out[y, x] = dark_of[c]

    return finish(out, cells, features, strokes)


def finish(out, cells, features, strokes, by_material=False):
    """Stamp the small features and clean stray pixels; returns the RGBA sprite.
    by_material: only a pixel whose material differs from all four neighbours is a stray pixel
    (single pixels of shading inside a part are texture, as in the games' sprites)."""
    gh, gw = cells.shape
    solid = cells >= 0
    out = out.copy()
    out[strokes & solid] = (40, 30, 40)
    # small features: pupils dark, eye whites and glints light, at least one pixel each
    for kind, fy, fx, area in features:
        if 0 <= fy < gh and 0 <= fx < gw and solid[fy, fx]:
            out[fy, fx] = (24, 24, 32) if kind == "dark" else (248, 248, 248)
    # clean: a pixel that shares its colour (or material) with none of its four neighbours is a stray
    # pixel; it takes the commonest colour around it (not the stamped eyes, brows and mouths)
    stamped = {(fy, fx) for _, fy, fx, _ in features} | set(zip(*np.nonzero(strokes)))
    for _ in range(3):
        key = out[..., 0].astype(int) * 65536 + out[..., 1].astype(int) * 256 + out[..., 2]
        keyp = np.pad(np.where(solid, key, -1), 1, constant_values=-1)
        cellp = np.pad(cells, 1, constant_values=-1)
        changed = False
        for y in range(gh):
            for x in range(gw):
                if not solid[y, x] or (y, x) in stamped:
                    continue
                four = [keyp[y + 1 + dy, x + 1 + dx] for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))]
                if -1 in four:                           # the outline along the silhouette stays
                    continue
                if by_material:
                    if cells[y, x] in [cellp[y + 1 + dy, x + 1 + dx] for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))]:
                        continue
                elif key[y, x] in four:
                    continue
                around = [(keyp[y + 1 + dy, x + 1 + dx], y + dy, x + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                          if (dy or dx) and keyp[y + 1 + dy, x + 1 + dx] >= 0]
                if not around:
                    continue
                best = max({a[0] for a in around}, key=lambda v: sum(1 for a in around if a[0] == v))
                yy, xx = next((a[1], a[2]) for a in around if a[0] == best)
                out[y, x] = out[yy, xx]
                changed = True
        if not changed:
            break
    rgba = np.zeros((gh, gw, 4), np.uint8)
    rgba[..., :3] = out
    rgba[..., 3] = np.where(solid, 255, 0)
    return Image.fromarray(rgba)


def smooth_silhouette(cells):
    """Clean the outer shape the way a spriter would: an empty pixel with solid pixels on three or
    four sides is a notch and gets filled; a solid pixel touching the shape on only one side is a
    spur and goes. Keeps outlines as smooth curves instead of jagged steps."""
    cells = cells.copy()
    gh, gw = cells.shape
    for _ in range(2):
        solid = cells >= 0
        pad = np.pad(solid, 1)
        n4 = pad[:-2, 1:-1].astype(int) + pad[2:, 1:-1] + pad[1:-1, :-2] + pad[1:-1, 2:]
        cp = np.pad(cells, 1, constant_values=-1)
        for y, x in zip(*np.nonzero(~solid & (n4 >= 3))):
            around = [cp[y + 1 + dy, x + 1 + dx] for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)) if cp[y + 1 + dy, x + 1 + dx] >= 0]
            cells[y, x] = max(set(around), key=around.count)
        cells[solid & (n4 <= 1)] = -1
    return cells


def shade_gen3(cells, tone, ink, base_lab, materials, strokes):
    """Colours in the manner of the games' sprites, as measured on 844 of them (2026-10-03):
    - each part has four tones (dark, shadow, base, light) plus a rare highlight; shadows lean cool,
      lights warm;
    - volume comes from the shape: a pixel with the outside (or another big part) close below and to
      its right is in shadow, one with it close above and to its left is lit; added to the artwork's
      own light and dark. Light falls from the upper left; edges are not all darkened alike;
    - the outline is the part's own darkest tone (a coloured outline), nearly black only on the
      shadow side at the bottom right; lines between parts and the artwork's inner lines (fur,
      creases) are drawn in dark tones of the part, not in black."""
    gh, gw = cells.shape
    solid = cells >= 0
    def tint(i, dl, da=0.0, db=0.0, scale=None, chroma=1.0):
        b = base_lab[i].astype(np.float32).copy()
        b[0] = b[0] * scale if scale is not None else np.clip(b[0] + dl, 0, 255)
        b[1] = 128 + (b[1] - 128) * chroma + da; b[2] = 128 + (b[2] - 128) * chroma + db
        return to_rgb(b.reshape(1, 1, 3))[0, 0]
    ramp = {}
    for i in range(materials):
        L0 = base_lab[i][0]
        soft = 0.55 if L0 > 210 else 1.0                       # white parts get gentler shading
        # dark tones keep the part's hue but not its full colour: the games' outlines are muted
        ramp[i] = {"outline": tint(i, 0, 1, -3, scale=0.38, chroma=0.22), "outline_dark": tint(i, 0, 0, -2, scale=0.22, chroma=0.15),
                   "dark": tint(i, 0, 2, -4, scale=0.52, chroma=0.4), "shadow": tint(i, -26 * soft, 3, -7),
                   "base": tint(i, 0), "light": tint(i, min(16, 252 - L0), -2, 5), "highlight": tint(i, min(30, 254 - L0), -3, 3)}
    # parts: patches of a material big enough to count as a part
    patch = np.zeros((gh, gw), np.int32)
    for i in range(materials):
        n, lbl, stats, _ = cv2.connectedComponentsWithStats((cells == i).astype(np.uint8), connectivity=4)
        for j in range(1, n):
            patch[lbl == j] = stats[j, cv2.CC_STAT_AREA]
    big = patch >= 10
    # volume from the shape: look 1-3 pixels toward the light (up-left) and away from it (down-right)
    def outside(y, x, c):                                   # only the silhouette: inner part borders made false creases
        return not (0 <= y < gh and 0 <= x < gw) or cells[y, x] < 0
    light = np.zeros((gh, gw), np.float32)
    for y in range(gh):
        for x in range(gw):
            c = cells[y, x]
            if c < 0:
                continue
            s = 0.0
            for d, w in ((1, 1.0), (2, 0.6), (3, 0.35)):
                s += w * (outside(y - d, x - d, c) or outside(y - d, x, c)) - w * (outside(y + d, x + d, c) or outside(y + d, x, c))
            light[y, x] = s
    # and across each whole part: lighter toward its upper left, darker toward its lower right
    for i in range(materials):
        n, lbl, stats, cent = cv2.connectedComponentsWithStats((cells == i).astype(np.uint8), connectivity=4)
        for j in range(1, n):
            x0, y0, bw, bh, area = stats[j]
            if area < 6:
                continue
            ys, xs = np.nonzero(lbl == j)
            light[ys, xs] += -1.1 * ((xs - cent[j][0]) / max(bw, 2) + (ys - cent[j][1]) / max(bh, 2))
    # smooth light and the artwork's tone a little within each part, so shading comes in clusters
    def smooth(field, i):
        sel = (cells == i).astype(np.float32)
        num = cv2.GaussianBlur(field * sel, (0, 0), 0.9)
        den = cv2.GaussianBlur(sel, (0, 0), 0.9)
        return num / np.maximum(den, 1e-3)
    out = np.zeros((gh, gw, 3), np.uint8)
    for i in range(materials):
        sel = solid & (cells == i)
        if not sel.any():
            continue
        t = smooth(tone, i)[sel]
        z = (t - np.median(t)) / (t.std() + 6)
        score = 0.8 * z + smooth(light, i)[sel]
        level = np.select([score < -0.45, score < 0.8, score < 1.7], [0, 1, 2], 3)      # shadow, base, light, highlight
        band = np.full((gh, gw), -1, np.int8); band[sel] = level
        # a shade that touches no pixel of its own shade (four sides) joins the commonest one around it
        for _ in range(2):
            bp = np.pad(band, 1, constant_values=-1)
            for y, x in zip(*np.nonzero(sel)):
                four = [bp[y + 1 + dy, x + 1 + dx] for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))]
                own = [v for v in four if v >= 0]
                if own and band[y, x] not in own:
                    band[y, x] = max(set(own), key=own.count)
        names = ("shadow", "base", "light", "highlight")
        for y, x in zip(*np.nonzero(sel)):
            out[y, x] = ramp[i][names[band[y, x]]]
    # lines: silhouette outline, part boundaries, and the artwork's inner lines in dark tones
    pad = np.pad(cells, 1, constant_values=-1)
    for y in range(gh):
        for x in range(gw):
            c = cells[y, x]
            if c < 0:
                continue
            up, down, left, right = pad[y, x + 1], pad[y + 2, x + 1], pad[y + 1, x], pad[y + 1, x + 2]
            if -1 in (up, down, left, right):
                shadow_side = down == -1 or right == -1
                out[y, x] = ramp[c]["outline_dark"] if shadow_side else ramp[c]["outline"]
                continue
            for o, (dy, dx) in ((up, (-1, 0)), (down, (1, 0)), (left, (0, -1)), (right, (0, 1))):
                if o != c and big[y, x] and big[y + dy, x + dx] and base_lab[c][0] <= base_lab[o][0] and np.linalg.norm(base_lab[c] - base_lab[o]) > 22:
                    out[y, x] = ramp[c]["outline"]
                    break
            else:
                if strokes[y, x]:
                    out[y, x] = ramp[c]["outline"]
                elif ink[y, x] > 0.5:
                    out[y, x] = ramp[c]["dark"]
    return out
