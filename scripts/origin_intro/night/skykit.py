"""Shared sky pieces for the night scenes, after Arvind's notes on Gravriel v6 / Sabertann v15 (2026-11-14):
- hz_curve / warp_sea: the horizon is not flat in Ho-Oh's and Lugia's scenes (a wide-angle lens): in SoulSilver it
  sits about 5 px lower in the middle than out at the sides. The sea is painted flat, then each column is squeezed so
  its horizon lands on the curve; the waves bend with it, less and less toward the viewer.
- wisps: clouds like Ho-Oh's: long thin horizontal banks with puffy tops and tails that taper to a point, no outline,
  four tones: shade on the side away from the light, the body, a lit band and a bright edge on the side facing the
  light. Opaque, as in Ho-Oh's scene.
- moon: a clean disc (faint maria, one bright side) with two soft halo rings, like Ho-Oh's sun and Lugia's moon.
All colours are DS 5-bit values times 8 (arrays hold the 5-bit values)."""
import numpy as np
W, H = 256, 192
yy, xx = np.mgrid[0:H, 0:W]
U = (np.arange(W) + 0.5 - 128) / 128


def hz_curve(HZ, c=6.0):
    """horizon row per column: HZ in the middle, c px higher at the screen's edges"""
    return np.round(HZ - c * U * U).astype(int)


def warp_sea(flat, bot, hzx, HZ, mask=None):
    """flat: rows HZ..H-1 painted with a flat horizon. Column x of the sea is resampled into rows hzx[x]..H-1."""
    for x in range(W):
        h0 = hzx[x]
        for y in range(h0, H):
            yf = HZ + (y - h0) * (H - 1 - HZ) / max(1, H - 1 - h0)
            yi = int(np.floor(yf + 0.5))
            if mask is None or mask[yi, x]: bot[y, x] = flat[yi, x]
    return bot


def wisp_mask(lenses, S=4):
    """lenses: (cx, cy, L, T, bumps, seed). Each is a long lens, thickest in the middle, tapering to points; puffy
    heads on top, a flatter bottom. Returns the cloud mask at screen size."""
    hy, hx = np.mgrid[0:H * S, 0:W * S] / S
    m = np.zeros((H * S, W * S), bool)
    for (cx, cy, L, T, bumps, seed) in lenses:
        u = (hx - cx) / (L / 2)
        env = np.clip(1 - u * u, 0, None)
        th = T * env ** 1.3
        r = np.random.default_rng(seed)
        top = th * 0.65
        for _ in range(bumps):
            bx = cx + r.uniform(-0.4, 0.4) * L; bw = r.uniform(0.07, 0.16) * L; bh = r.uniform(0.35, 0.85) * T
            top = top + bh * np.exp(-((hx - bx) / bw) ** 2) * env ** 0.7
        bot = th * 0.35
        m |= (np.abs(u) < 1) & (hy > cy - top) & (hy < cy + bot)
    return m.reshape(H, S, W, S).mean((1, 3)) > 0.5


def _steps_out(mask, ys, xs, dx, dy, sgn, maxs):
    out = np.full(len(ys), maxs + 1)
    for s in range(maxs, 0, -1):
        qx = np.clip(np.round(xs + sgn * dx * s).astype(int), 0, W - 1)
        qy = np.clip(np.round(ys + sgn * dy * s).astype(int), 0, H - 1)
        out = np.where(~mask[qy, qx], s, out)
    return out


def wisps(img, lenses, light, cols, reach=(70, 120), lit_band=3):
    """paint opaque clouds into img. light = (x, y) the clouds are lit from (the moon); cols = [shade, body, lit, hi].
    Within reach[0] of the light the lit side gets the bright edge, out to reach[1] only the lit band."""
    m = wisp_mask(lenses)
    ys, xs = np.nonzero(m)
    lx, ly = light
    dx, dy = lx - xs, ly - ys; n = np.hypot(dx, dy) + 1e-6; dx, dy = dx / n, dy / n
    dl = _steps_out(m, ys, xs, dx, dy, 1, 5)          # steps to the edge facing the light
    dd = _steps_out(m, ys, xs, dx, dy, -1, 5)         # steps to the edge facing away
    k = np.ones(len(ys), int)
    k[dd <= 2] = 0
    dist = n
    k[(dl <= lit_band) & (dist < reach[1])] = 2
    k[(dl <= 1) & (dist < reach[0])] = 3
    k[(dl <= 1) & (dist >= reach[0]) & (dist < reach[1])] = 2
    C = np.array(cols)
    img[ys, xs] = C[k]
    return m


def moon_sprite(R, cols, rings, maria=True, size=64):
    """cols: base, bright, mare, limb; rings: [(width, colour), ...] outward from the disc"""
    M = np.zeros((size, size, 3), np.int32); Ma = np.zeros((size, size), bool)
    my_, mx_ = np.mgrid[0:size, 0:size]
    c = size / 2
    rr = np.hypot(mx_ + 0.5 - c, my_ + 0.5 - c)
    r0 = R
    for (w, col) in rings:
        ring = (rr >= r0) & (rr < r0 + w); M[ring] = col; Ma[ring] = True; r0 += w
    disc = rr < R
    M[disc] = cols[0]; Ma[disc] = True
    M[disc & (rr > R - 1.4)] = cols[3]
    if maria:      # a few faint, soft maria (own shapes), one tone off the base
        for (cx, cy, rx, ry) in ((c + 3, c - 5, 5.5, 3.8), (c + 6.5, c + 1, 3.2, 3.6), (c - 4, c + 0.5, 3.2, 5),
                                 (c - 6, c + 6.5, 2.6, 1.8), (c + 2, c + 8, 1.8, 1.6)):
            e = (((mx_ + 0.5 - cx) / rx) ** 2 + ((my_ + 0.5 - cy) / ry) ** 2) < 1
            M[disc & e & (rr < R - 1.4)] = cols[2]
    # the bright side: up and to the left
    hl = disc & (np.hypot(mx_ + 0.5 - (c - R * 0.35), my_ + 0.5 - (c - R * 0.35)) < R * 0.45) & (M == cols[0]).all(-1)
    M[hl] = cols[1]
    return M, Ma


def glow_levels(MX, MY, radii, levels):
    """circular glow around (MX, MY): level per pixel, interpolated over radii"""
    r = np.hypot(xx + 0.5 - MX, yy + 0.5 - MY)
    return np.interp(r, radii, levels, right=0)


def feather_pick(level, seed=0):
    """round a continuous level to bands whose edges are feathered with short horizontal dashes, as in Ho-Oh's sky"""
    lo = np.floor(level); f = level - lo
    r = np.random.default_rng(seed)
    # per row, a dash pattern: runs of 2..7 px with a random threshold each
    thr = np.zeros(level.shape)
    for y in range(level.shape[0]):
        x = 0
        while x < level.shape[1]:
            L = int(r.integers(3, 11)); thr[y, x:x + L] = r.uniform(0.38, 0.62); x += L
    up = np.where(np.abs(f - 0.5) < 0.12, f > thr, f >= 0.5)
    return (lo + up).astype(int)


# ---------------------------------------------------------------- v2 clouds (Arvind: "flat, not enough transitions")
# Ho-Oh's clouds have 10-12 tones each: the edges melt into the sky through in-between colours, and the light runs
# from a dark top through grey and warm grey to the lit edge in uneven bands. wisps2 renders a soft density and a
# continuous light value at 4x (distance to the edge facing the light + the slope of each puff toward it), colours it
# along an 8-step ramp, blends it over the sky by density, shrinks to screen size and snaps to the ramp and the sky's
# own colours with a little streaky noise, so the bands get ragged horizontal edges like painted ones.
def _lens_fields(lenses, S):
    hy, hx = np.mgrid[0:H * S, 0:W * S] / S
    hgt = np.zeros((H * S, W * S))
    for (cx, cy, L, T, bumps, seed) in lenses:
        u = (hx - cx) / (L / 2)
        env = np.clip(1 - u * u, 0, None)
        th = T * env ** 1.3
        r = np.random.default_rng(seed)
        top = th * 0.65
        for _ in range(bumps):
            bx = cx + r.uniform(-0.4, 0.4) * L; bw = r.uniform(0.07, 0.16) * L; bh = r.uniform(0.35, 0.85) * T
            top = top + bh * np.exp(-((hx - bx) / bw) ** 2) * env ** 0.7
        # a ragged underside: long shallow waves and a trailing lower tail
        bot = th * 0.35 + 0.18 * T * env * np.sin(hx / (L * 0.11) + seed) ** 2
        y0, y1 = cy - top, cy + bot
        inside = (np.abs(u) < 1) & (hy > y0) & (hy < y1)
        h = np.where(inside, np.sqrt(np.clip((hy - y0) * (y1 - hy), 0, None)), 0)
        hgt = np.maximum(hgt, h)
        # fluffy (Arvind: "they should be fluffy like Ho-Oh's"): round puffs along the top and a few under it, each a
        # dome of its own so it gets its own light and shade
        if T >= 3.5:
            npf = max(3, int(L / 9))
            for k in range(npf):
                t = (k + 0.5) / npf * 1.6 - 0.8 + r.uniform(-0.05, 0.05)
                bx = cx + t * L / 2
                e = max(0.0, 1 - t * t)
                rb = T * (0.30 + 0.38 * e) * r.uniform(0.75, 1.15)
                by = cy - T * 0.55 * e ** 1.3 + r.uniform(-0.15, 0.15) * T
                d2 = (hx - bx) ** 2 + ((hy - by) * 1.15) ** 2
                hgt = np.maximum(hgt, np.sqrt(np.clip(rb * rb - d2, 0, None)))
            for k in range(max(1, npf // 3)):
                t = r.uniform(-0.6, 0.6); bx = cx + t * L / 2; e = 1 - t * t
                rb = T * (0.22 + 0.2 * e)
                by = cy + T * 0.15 * e
                d2 = ((hx - bx) / 1.6) ** 2 + (hy - by) ** 2
                hgt = np.maximum(hgt, np.sqrt(np.clip(rb * rb - d2, 0, None)))
    return hgt


def wisps2(img, lenses, light, ramp, extra_snap=(), soft=1.2, reach=150, lit_depth=6.0, seed=0, S=4):
    """img: (H, W, 3) 5-bit; ramp: 8 colours dark (shade) -> bright (lit edge). light = (x, y) point the clouds face."""
    from scipy import ndimage as nd
    hgt = _lens_fields(lenses, S)
    solid = hgt > 0
    if not solid.any(): return np.zeros((H, W), bool)
    # density: 1 inside, falling off over `soft` px at the edges (edges melt into the sky)
    dist_in = nd.distance_transform_edt(solid) / S
    dens = np.clip(dist_in / soft, 0, 1)
    # light: steps to the edge facing the light (0 = on it), and the puff slope toward the light
    hy, hx = np.mgrid[0:H * S, 0:W * S] / S
    lx, ly = light
    dx, dy = lx - hx, ly - hy; n = np.hypot(dx, dy) + 1e-6; dx, dy = dx / n, dy / n
    steps = int(lit_depth * S)
    dl = np.full(solid.shape, float(steps))
    for s in range(steps, 0, -1):
        qx = np.clip(np.round(hx * S + dx * s).astype(int), 0, W * S - 1)
        qy = np.clip(np.round(hy * S + dy * s).astype(int), 0, H * S - 1)
        dl = np.where(~solid[qy, qx], s, dl)
    edge = 1 - dl / steps                                   # 1 on the lit edge, 0 deep inside
    gy, gx = np.gradient(nd.gaussian_filter(hgt, S * 0.5))
    nz = 0.6
    nn = np.sqrt(gx * gx + gy * gy + nz * nz)
    lam = np.clip((-gx * dx - gy * dy) / nn, -1, 1)          # slope facing the light
    fall = np.clip(1 - n / reach, 0.25, 1)                  # farther from the light, dimmer
    v = np.clip((0.70 * edge ** 0.9 + 0.45 * (lam * 0.5 + 0.5) - 0.08) * (0.78 + 0.22 * fall) + 0.02, 0, 1)
    R = np.array(ramp, float)
    pos = v * (len(R) - 1); i0 = np.floor(pos).astype(int).clip(0, len(R) - 2); f = (pos - i0)[..., None]
    col = R[i0] * (1 - f) + R[i0 + 1] * f
    base = np.repeat(np.repeat(img.astype(float), S, 0), S, 1)
    mix = base * (1 - dens[..., None]) + col * dens[..., None]
    small = mix.reshape(H, S, W, S, 3).mean((1, 3))
    cov = dens.reshape(H, S, W, S).mean((1, 3))
    m = cov > 0.12
    # streaky noise, then snap to the ramp + the sky colours under the cloud
    r = np.random.default_rng(seed)
    noise = np.zeros((H, W))
    for y in range(H):
        x = 0
        while x < W:
            L_ = int(r.integers(2, 9)); noise[y, x:x + L_] = r.uniform(-0.9, 0.9); x += L_
    sky_cols = np.unique(img[m].reshape(-1, 3), axis=0) if m.any() else np.zeros((0, 3))
    snap = np.concatenate([np.array(ramp), sky_cols] + ([np.array(extra_snap)] if len(extra_snap) else []), 0)
    q = small + noise[..., None] * 0.9
    d = ((q[..., None, :] - snap[None, None]) ** 2).sum(-1)
    out = snap[d.argmin(-1)]
    img[m] = out[m]
    return m


def moon2(R, disc, bright, limb, shade, mare, rings, size=64):
    """v10 moon, after Ho-Oh's sun and Lugia's moon: a big, nearly flat bright disc, a thin warmer limb just inside the
    edge, a faint shaded crescent low on one side, very faint maria, then a few clean rings (Lugia's has a darker one
    that makes it stand out). rings: [(width, colour), ...] outward."""
    M = np.zeros((size, size, 3), np.int32); Ma = np.zeros((size, size), bool)
    my_, mx_ = np.mgrid[0:size, 0:size]; c = size / 2
    rr = np.hypot(mx_ + 0.5 - c, my_ + 0.5 - c)
    r0 = R
    for (w, col) in rings:
        ring = (rr >= r0) & (rr < r0 + w); M[ring] = col; Ma[ring] = True; r0 += w
    d = rr < R
    M[d] = disc; Ma[d] = True
    for (cx, cy, rx, ry) in ((c + 4, c - 7, 7.5, 5), (c + 9, c + 1, 4.2, 4.8), (c - 5, c + 1, 4.2, 6.5),
                             (c - 8, c + 9, 3.4, 2.4), (c + 3, c + 11, 2.4, 2.2)):
        e = (((mx_ + 0.5 - cx) / rx) ** 2 + ((my_ + 0.5 - cy) / ry) ** 2) < 1
        M[d & e] = mare
    cres = d & (np.hypot(mx_ + 0.5 - (c - R * 0.22), my_ + 0.5 - (c - R * 0.22)) > R * 1.02)
    M[cres] = shade
    hi = d & (np.hypot(mx_ + 0.5 - (c - R * 0.3), my_ + 0.5 - (c - R * 0.3)) < R * 0.5) & (M == disc).all(-1)
    M[hi] = bright
    M[d & (rr > R - 1.2)] = limb
    return M, Ma


def moon3(R, high, mare, crater_dark, rings, size=64, seed=4, S=8):
    """v11 moon surface (Arvind: "the moon's content did not look good, just round blobs"). Drawn like a small
    painting of the real near side: maria with ragged edges where the real ones lie (the map of the Moon is nature,
    not anyone's art), darker cores in them, craters with a shadowed inner wall toward the light and a bright far
    wall, one young bright crater low down with faint rays, light from the upper left with a darker lower-right limb.
    high: highland tones dark -> bright (4); mare: mare tones dark -> light (2); crater_dark: shadow inside craters."""
    from scipy import ndimage as nd
    N = size * S; c = N / 2
    yy_, xx_ = np.mgrid[0:N, 0:N]
    X = (xx_ + 0.5 - c) / (R * S); Y = (yy_ + 0.5 - c) / (R * S)
    rr = np.hypot(X, Y); disc = rr < 1
    r = np.random.default_rng(seed)
    def fbm(scale, oct=4):
        f = np.zeros((N, N))
        for o in range(oct):
            n = r.standard_normal((N, N)); f += nd.gaussian_filter(n, scale * N / (2 ** o) / 64) * (0.55 ** o)
        return f / f.std()
    nz = fbm(14.0, 2)
    M_ = np.zeros((N, N))
    for (mx, my, ax, ay) in ((-0.34, -0.38, 0.30, 0.26), (-0.58, 0.06, 0.26, 0.40), (0.18, -0.34, 0.19, 0.17),
                             (0.38, -0.04, 0.24, 0.21), (0.72, -0.26, 0.12, 0.11), (0.52, 0.26, 0.13, 0.17),
                             (-0.20, 0.36, 0.18, 0.14), (-0.08, -0.66, 0.44, 0.08)):
        M_ = np.maximum(M_, np.exp(-(((X - mx) / ax) ** 2 + ((Y - my) / ay) ** 2)))
    mf = M_ + 0.10 * nz
    is_mare = disc & (mf > 0.45)
    core = disc & (mf > 0.66)
    # brightness: highlands bright, slightly mottled; sphere light from the upper left
    Z = np.sqrt(np.clip(1 - rr ** 2, 0, 1))
    L = np.array([-0.45, -0.45, 0.77]); L = L / np.linalg.norm(L)
    lam = np.clip(-X * -L[0] * -1 + 0, 0, 0)  # placeholder, replaced below
    lam = np.clip(X * L[0] + Y * L[1] + Z * L[2], 0, 1)
    val = 0.62 + 0.30 * lam + 0.025 * fbm(10.0, 2)
    # craters (x, y, radius): named ones where the real ones are, plus a scatter in the highlands
    cr = [(-0.10, 0.62, 0.10, True), (-0.25, -0.05, 0.08, True)]
    dark = np.zeros((N, N), bool); bright = np.zeros((N, N), bool)
    for (cx, cy, cr_, young) in cr:
        d = np.hypot(X - cx, Y - cy)
        inside = d < cr_
        toward = ((X - cx) * L[0] + (Y - cy) * L[1]) > 0           # inner wall on the light's side is in shadow
        dark |= inside & toward & (d > cr_ * 0.45)
        bright |= inside & ~(toward & (d > cr_ * 0.45))
        bright |= (d >= cr_) & (d < cr_ * 1.4) & ~toward & ~is_mare             # the rim away from the light catches it
        if young:                                                      # Tycho: a bright halo and rays
            bright |= (d < cr_ * 1.3) & ~inside
            for a in r.uniform(0, 2 * np.pi, 9 if cr_ > 0.09 else 0):
                ux, uy = np.cos(a), np.sin(a)
                t = (X - cx) * ux + (Y - cy) * uy; pdist = np.abs(-(X - cx) * uy + (Y - cy) * ux)
                ray = (t > cr_) & (t < r.uniform(0.5, 0.9)) & (pdist < 0.02 + 0.012 * t)
                val = np.where(ray & disc & ~is_mare, val + 0.16 * (1 - t), val)
    out_tone = np.zeros((N, N), int)
    hv = np.clip(val, 0, 1.2)
    out_tone = np.digitize(hv, [0.66, 0.78, 0.90])                   # 0..3 highland tones
    tone_rgb = np.array(high)[out_tone]
    tone_rgb = np.where(is_mare[..., None], np.array(mare[1]), tone_rgb)
    tone_rgb = np.where(core[..., None], np.array(mare[0]), tone_rgb)
    tone_rgb = np.where((is_mare & (lam < 0.45))[..., None], np.array(mare[0]), tone_rgb)
    tone_rgb = np.where(dark[..., None], np.array(crater_dark), tone_rgb)
    tone_rgb = np.where((bright & disc)[..., None], np.array(high[3]), tone_rgb)
    # shrink: majority colour per pixel (keeps the pixels clean)
    cols = np.array(list(high) + list(mare) + [crater_dark])
    key = np.zeros((N, N), int)
    for i, cc in enumerate(cols): key[(tone_rgb == cc).all(-1)] = i
    kb = key.reshape(size, S, size, S).transpose(0, 2, 1, 3).reshape(size, size, S * S)
    cnt = np.stack([(kb == i).sum(-1) for i in range(len(cols))], -1)
    small = cols[cnt.argmax(-1)]
    my_, mx_ = np.mgrid[0:size, 0:size]
    rs = np.hypot(mx_ + 0.5 - size / 2, my_ + 0.5 - size / 2)
    M = np.zeros((size, size, 3), np.int32); Ma = np.zeros((size, size), bool)
    r0 = R
    for (w, col) in rings:
        ring = (rs >= r0) & (rs < r0 + w); M[ring] = col; Ma[ring] = True; r0 += w
    d1 = rs < R
    M[d1] = small[d1]; Ma[d1] = True
    # limb: the lower-right edge one tone darker
    lim = d1 & (rs > R - 1.3) & ((mx_ - size / 2) + (my_ - size / 2) > 0)
    M[lim & (M == np.array(high[3])).all(-1)] = high[2]
    M[lim & (M == np.array(high[2])).all(-1)] = high[1]
    return M, Ma


def moon4(R, tones, rings, size=64, seed=7, S=8, thresholds=None, depth=0.42):
    """v12 moon (Arvind: "it still looks odd, as if you just threw in squares and circles"). The surface is painted as
    a continuous picture first, like a photo of the full Moon: soft maria whose coasts are warped by noise, darker
    cores, highlands with faint crater mottling (more in the south), Tycho and Copernicus as bright spots with rays,
    a slight darkening toward the limb. Only then is it shrunk by averaging and cut into a few tones, so the shapes
    stay organic. tones: dark -> bright colours; thresholds: albedo cut points between them."""
    from scipy import ndimage as nd
    N = size * S; c = N / 2
    yy_, xx_ = np.mgrid[0:N, 0:N]
    X = (xx_ + 0.5 - c) / (R * S); Y = (yy_ + 0.5 - c) / (R * S)
    rr = np.hypot(X, Y)
    r = np.random.default_rng(seed)
    def noise(sig_px):            # smooth noise with a feature size of sig_px screen pixels
        n = nd.gaussian_filter(r.standard_normal((N, N)), sig_px * S)
        return n / (n.std() + 1e-9)
    # domain warp: maria coasts wander
    wx, wy = noise(2.2) * 0.07 + noise(0.9) * 0.025, noise(2.2) * 0.07 + noise(0.9) * 0.025
    Xw, Yw = X + wx, Y + wy
    mare = np.zeros((N, N))
    for (mx, my, ax, ay, dep) in ((-0.33, -0.40, 0.27, 0.22, 1.0),   # Imbrium
                                  (-0.62, 0.05, 0.20, 0.38, 0.8),    # Procellarum
                                  (0.17, -0.36, 0.15, 0.14, 0.95),   # Serenitatis
                                  (0.38, -0.06, 0.20, 0.17, 0.95),   # Tranquillitatis
                                  (0.73, -0.27, 0.10, 0.09, 1.0),    # Crisium
                                  (0.55, 0.24, 0.10, 0.15, 0.8),     # Fecunditatis
                                  (0.33, 0.32, 0.07, 0.07, 0.75),    # Nectaris
                                  (-0.20, 0.36, 0.15, 0.11, 0.7),    # Nubium
                                  (-0.46, 0.46, 0.07, 0.07, 0.8),    # Humorum
                                  (-0.05, -0.66, 0.40, 0.06, 0.6),   # Frigoris
                                  (0.02, -0.12, 0.10, 0.08, 0.6)):   # Vaporum/Medii
        mare = np.maximum(mare, dep * np.exp(-(((Xw - mx) / ax) ** 2 + ((Yw - my) / ay) ** 2) ** 1.6))
    mare = np.clip(mare * 1.4, 0, 1)
    alb = 1.0 - depth * mare - 0.08 * (depth / 0.42) * mare * np.clip(noise(1.5), -1, 2) * 0.5
    # highland mottling, more in the south; small craters as soft bright/dark pairs
    south = np.clip((Y + 0.2) / 1.2, 0, 1)
    alb += (1 - mare) * (0.02 + 0.03 * south) * noise(0.7)
    for _ in range(16):
        cx, cy = r.uniform(-0.85, 0.85), r.uniform(-0.2, 0.9)
        if cx * cx + cy * cy > 0.8: continue
        rad = r.uniform(0.025, 0.06)
        d2 = ((X - cx) ** 2 + (Y - cy) ** 2) / rad ** 2
        alb += 0.08 * np.exp(-((np.sqrt(d2) - 1) / 0.35) ** 2) - 0.07 * np.exp(-d2 * 2)
    # bright young craters with rays
    for (cx, cy, rad, nray, rlen) in ((-0.11, 0.63, 0.045, 11, 0.85), (-0.25, -0.07, 0.04, 7, 0.35), (-0.63, -0.30, 0.025, 0, 0)):
        d = np.hypot(X - cx, Y - cy)
        alb += 0.30 * np.exp(-(d / rad) ** 2) + 0.10 * np.exp(-(d / (rad * 2.6)) ** 2)
        for a in r.uniform(0, 2 * np.pi, nray):
            ux, uy = np.cos(a), np.sin(a)
            t = (X - cx) * ux + (Y - cy) * uy; p = -(X - cx) * uy + (Y - cy) * ux
            L = rlen * r.uniform(0.5, 1.0)
            alb += 0.10 * np.exp(-(p / (0.012 + 0.02 * t.clip(0))) ** 2) * (t > rad) * np.clip(1 - t / L, 0, 1)
    Z = np.sqrt(np.clip(1 - rr ** 2, 0, 1))
    alb *= 0.86 + 0.14 * Z ** 0.5                                    # a little darker toward the limb
    alb *= 1.0 + 0.04 * np.clip(-X - Y, -1, 1)                       # and a touch brighter to the upper left
    disc = rr < 1
    a_small = (np.where(disc, alb, 0)).reshape(size, S, size, S).mean((1, 3))
    cov = disc.reshape(size, S, size, S).mean((1, 3))
    a_small = a_small / np.maximum(cov, 1e-6)
    T = np.array(tones)
    th = thresholds if thresholds is not None else list(np.linspace(0.62, 0.98, len(T) - 1))
    k = np.digitize(a_small, th)
    my_, mx_ = np.mgrid[0:size, 0:size]
    rs = np.hypot(mx_ + 0.5 - size / 2, my_ + 0.5 - size / 2)
    M = np.zeros((size, size, 3), np.int32); Ma = np.zeros((size, size), bool)
    r0 = R
    for (w, col) in rings:
        ring = (rs >= r0) & (rs < r0 + w); M[ring] = col; Ma[ring] = True; r0 += w
    d1 = rs < R
    M[d1] = T[k][d1]; Ma[d1] = True
    return M, Ma, a_small
