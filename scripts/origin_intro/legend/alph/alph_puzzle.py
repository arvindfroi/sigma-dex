"""Ruins of Alph sliding puzzles with our Pokemon (Arvind 2026-11-17: Ho-Oh's puzzle becomes Sabertann, Aerodactyl's
(Old Amber) Ambuger, "a mosquito trapped in amber", Kabuto's (Dome) Tortoplasm; Omanyte's waits for the third fossil).
The puzzle archive (pret files/application/annon/puzzle_gra = Origin's a/1/7/2): members 4-7 hold the four pictures
(Kabuto, Aerodactyl, Omanyte, Ho-Oh), 16 pieces of 32x32 each, 4 bpp, drawn with palette 2 of member 0, a carved
sandstone relief: light stone (6) with stone dots (7), the figure cut into the darker layer (12) with dark dots (9, 8),
dark piece outlines (3), gaps (0) and a light outer rim (5).
This keeps each piece's outline, gaps and rim exactly (indices 0, 3, 5) and carves a new figure inside them from a
picture of our Pokemon: its dark areas, its outline and the strong edges inside it (where the colour changes a lot) are
cut into the stone; light areas stay raised. Dots are laid as in the original's density, seeded.
python alph_puzzle.py A172_IN A172_OUT MEMBER SOURCE.png OUT_PREVIEW.png
env: BOX (112: the figure's size inside the 128 picture), DX/DY (shift), DARK (0.36: luminance below this is cut),
     EDGE (0.22: edge strength that is cut), OUTLINE (2 px), FLIP (0/1 mirror), BG ('white' or 'alpha': how the
     source's background is found), SEED; RELIEF=1: SOURCE is a two-tone carving (qwen_relief.py), cut = its darker tone
     (Otsu), CROP (0.0: fraction cut off each side first), TSHIFT (move the threshold); LOCAL=sigma reads an engraved
     tablet's grooves instead (LT strength, COVER), FILLED=1 fills the figure, INVERT=1 gives the originals' look (a light
     margin of MARGIN px, the field cut away, the figure raised with its lines cut), CLOSE (outline closing);
     TILE=1: SOURCE is Qwen's redraw of the puzzle picture at 8 px per pixel (qwen_tile.py), each cell to light or dark sand"""
import sys, os, struct
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(H, '..', '..'))
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
from narc import unpack
import g2d
IN, OUT, MEMBER, SRC, PREV = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
E = lambda k, d: float(os.environ.get(k, d))
raw = open(IN, 'rb').read(); F = unpack(raw)
g = g2d.read_ncgr(F[MEMBER]); assert g['bpp'] == 4 and len(g['data']) == 8192
pal, _ = g2d.read_nclr(F[0]); P = np.array([[(c & 31) * 255 // 31, ((c >> 5) & 31) * 255 // 31, ((c >> 10) & 31) * 255 // 31] for c in pal], np.uint8)[32:48]
d = np.frombuffer(g['data'], np.uint8); tiles = np.stack([d & 15, d >> 4], -1).reshape(256, 8, 8)
pieces = [np.vstack([np.hstack(tiles[k * 16 + r * 4:k * 16 + r * 4 + 4]) for r in range(4)]) for k in range(16)]
pic = np.vstack([np.hstack(pieces[r * 4:(r + 1) * 4]) for r in range(4)]).astype(int)
frame = np.isin(pic, (0, 3, 5)) | ((pic == 7) & ndimage.binary_dilation(pic == 5, iterations=2))   # outline, gaps, rim and its bevel
# --- the figure from the source picture
im = Image.open(SRC).convert('RGBA')
if E('FLIP', 0): im = im.transpose(Image.FLIP_LEFT_RIGHT)
a = np.asarray(im).astype(float)
if os.environ.get('BG', 'white') == 'alpha': sil = a[..., 3] > 128
else:
    rgb = np.where(a[..., 3:4] > 128, a[..., :3], 255); white = (rgb.min(-1) > 235)
    lbl, n = ndimage.label(white); border = set(np.unique(np.concatenate([lbl[0], lbl[-1], lbl[:, 0], lbl[:, -1]]))) - {0}
    sil = ~np.isin(lbl, list(border)); a[..., :3] = rgb
sil = ndimage.binary_opening(sil, iterations=1)
lab, n = ndimage.label(sil); sizes = ndimage.sum(sil, lab, range(1, n + 1)); sil = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 0.02 * sizes.max()])
ys, xs = np.nonzero(sil); y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
BOX = E('BOX', 112); s = BOX / max(y1 - y0, x1 - x0); w, h = max(1, round((x1 - x0) * s)), max(1, round((y1 - y0) * s))
crop = Image.fromarray(np.dstack([a[y0:y1, x0:x1, :3], sil[y0:y1, x0:x1] * 255]).astype(np.uint8), 'RGBA')
small = np.asarray(crop.resize((w, h), Image.LANCZOS)).astype(float) / 255
ox, oy = int((128 - w) / 2 + E('DX', 0)), int((128 - h) / 2 + E('DY', 0))
M = np.zeros((128, 128)); RGB = np.ones((128, 128, 3))
M[oy:oy + h, ox:ox + w] = small[..., 3]; RGB[oy:oy + h, ox:ox + w] = small[..., :3]
fig = M > 0.5
lum = RGB @ np.array([0.3, 0.55, 0.15])
gx = ndimage.sobel(RGB, axis=1); gy = ndimage.sobel(RGB, axis=0); grad = np.sqrt((gx ** 2 + gy ** 2).sum(-1)) / 4
edge = (grad > E('EDGE', 0.22)) & ndimage.binary_erosion(fig, iterations=1)
edge = edge & (ndimage.maximum_filter(grad, 3) == grad)                     # thin the edge to its crest
OUTL = int(E('OUTLINE', 2)); outline = fig & ~ndimage.binary_erosion(fig, iterations=OUTL)
cut = fig & (lum < E('DARK', 0.36)) | edge | outline
cut = ndimage.binary_closing(cut, iterations=1) & (fig | outline)
lbl, n = ndimage.label(cut); sz = ndimage.sum(cut, lbl, range(1, n + 1)); cut = np.isin(lbl, [i + 1 for i, s_ in enumerate(sz) if s_ >= 4])
raised = fig & ~cut; lbl, n = ndimage.label(raised); sz = ndimage.sum(raised, lbl, range(1, n + 1))
cut |= np.isin(lbl, [i + 1 for i, s_ in enumerate(sz) if s_ < 3])         # single raised specks inside a cut area go
if os.environ.get('RELIEF') == '1':                             # the source is a two-tone carving (qwen_relief.py)
    rimg = Image.open(SRC).convert('RGB'); W_, H_ = rimg.size; c = float(os.environ.get('CROP', 0.0))
    rimg = rimg.crop((int(W_ * c), int(H_ * c), int(W_ * (1 - c)), int(H_ * (1 - c)))).resize((128, 128), Image.BOX)
    L = np.asarray(rimg).astype(float) @ np.array([0.3, 0.55, 0.15])
    hist, bins = np.histogram(L, 64); mids = (bins[:-1] + bins[1:]) / 2; best = (-1, 0)
    for i in range(1, 64):                                       # Otsu's threshold between the two sand tones
        w0, w1 = hist[:i].sum(), hist[i:].sum()
        if w0 and w1:
            m0, m1 = (hist[:i] * mids[:i]).sum() / w0, (hist[i:] * mids[i:]).sum() / w1; v = w0 * w1 * (m0 - m1) ** 2
            if v > best[0]: best = (v, mids[i])
    cut = L < best[1] + float(os.environ.get('TSHIFT', 0))
    if os.environ.get('LOCAL'):                                  # grooves against the local stone tone (an engraved tablet)
        src_im = Image.open(SRC).convert('RGB').crop((int(W_ * c), int(H_ * c), int(W_ * (1 - c)), int(H_ * (1 - c))))
        def grooves(img, size):
            hi = np.asarray(img.resize((size, size), Image.LANCZOS)).astype(float) @ np.array([0.3, 0.55, 0.15])
            sm = ndimage.gaussian_filter(hi, 1.2 * size / 512); hp = sm - ndimage.gaussian_filter(sm, float(os.environ['LOCAL']) * size / 512)
            g_ = hp < -float(os.environ.get('LT', 16))
            lb, nn = ndimage.label(g_); sz = ndimage.sum(g_, lb, range(1, nn + 1))
            keep = np.isin(lb, [k + 1 for k, v in enumerate(sz) if v >= 40 * (size / 512) ** 2])   # stone grain goes
            bw = max(2, int(0.012 * size)); keep[:bw] = keep[-bw:] = False; keep[:, :bw] = keep[:, -bw:] = False   # and the tablet's own edge
            return keep
        g0 = grooves(src_im, 512); ys_, xs_ = np.nonzero(g0)                     # the figure's box on the tablet
        mg = 0.03 * 512; by0, by1, bx0, bx1 = max(0, ys_.min() - mg), min(512, ys_.max() + mg), max(0, xs_.min() - mg), min(512, xs_.max() + mg)
        side = max(by1 - by0, bx1 - bx0); cy, cx = (by0 + by1) / 2, (bx0 + bx1) / 2
        sw, sh = src_im.size; k_ = sw / 512
        sq = src_im.crop((int((cx - side / 2) * k_), int((cy - side / 2) * k_), int((cx + side / 2) * k_), int((cy + side / 2) * k_)))
        BOXR = int(E('BOX', 112)); gb = grooves(sq, BOXR * 4)
        gs = np.asarray(Image.fromarray((gb * 255).astype(np.uint8)).resize((BOXR, BOXR), Image.BOX)).astype(float) / 255
        g128 = np.zeros((128, 128)); o_ = (128 - BOXR) // 2; g128[o_ + int(E('DY', 0)):o_ + int(E('DY', 0)) + BOXR, o_ + int(E('DX', 0)):o_ + int(E('DX', 0)) + BOXR] = gs
        lines = g128 > float(os.environ.get('COVER', 0.22))
        if os.environ.get('FILLED') == '1':                      # Ho-Oh's style: the figure dark, its lines left as raised gaps
            body = ndimage.binary_fill_holes(ndimage.binary_closing(lines, iterations=int(os.environ.get('CLOSE', 2))))
            body = ndimage.binary_opening(body, iterations=1)
            if E('THICK_GAPS', 0): lines = ndimage.binary_dilation(lines, iterations=int(E('THICK_GAPS', 0)))   # the originals' gaps are ~2 px
            if os.environ.get('INVERT') == '1':                  # the originals' look: a light margin, the field inside it cut away,
                body |= ndimage.binary_dilation(lines, iterations=1)   # the figure raised with its lines cut; thin parts stay as ridges
                yy_, xx_ = np.mgrid[0:128, 0:128]; dist = np.minimum.reduce([yy_, xx_, 127 - yy_, 127 - xx_])
                field = dist >= int(E('MARGIN', 10))
                cut = (field & ~body) | (lines & body)
            else:
                cut = body & ~lines
                cut |= body & ~ndimage.binary_erosion(body, iterations=1)    # the outer contour stays cut, so the figure keeps its edge
        else:
            cut = lines
    if not os.environ.get('LOCAL'): cut = ndimage.binary_opening(ndimage.binary_closing(cut, iterations=1), iterations=1)
    fig = np.ones((128, 128), bool); RGB = np.asarray(rimg).astype(float) / 255
    print('relief threshold %.0f' % best[1])
if os.environ.get('TILE') == '1':                              # the source is Qwen's redraw of the puzzle picture on its own grid
    q = np.asarray(Image.open(SRC).convert('RGB').resize((1024, 1024), Image.NEAREST)).astype(float)
    cellL = q.reshape(128, 8, 128, 8, 3).transpose(0, 2, 1, 3, 4).reshape(128, 128, 64, 3)
    Lc = np.median(cellL @ np.array([0.3, 0.55, 0.15]), axis=-1)            # each cell's middle tone
    light, dark = P[6] @ np.array([0.3, 0.55, 0.15]), P[12] @ np.array([0.3, 0.55, 0.15])
    cut = Lc < (light + dark) / 2 + E('TSHIFT', 0)
    cut = ndimage.binary_opening(ndimage.binary_closing(cut, iterations=1), iterations=1) if E('SMOOTH', 1) else cut
    fig = np.ones((128, 128), bool); RGB = q[::8, ::8] / 255
    print('tile: cut %.0f%%' % (100 * cut.mean()))
    if os.environ.get('TONES'):                                  # several of the puzzle's own sand tones instead of two
        tones = [int(v) for v in os.environ['TONES'].split(',')]  # light to dark, e.g. 6,7,12,9,8
        tl = np.array([P[t] @ np.array([0.3, 0.55, 0.15]) for t in tones])
        lo_, hi_ = np.percentile(Lc, [3, 97]); z_ = (Lc - lo_) / max(hi_ - lo_, 1)          # stretch to the tones' range
        target = tl.min() + np.clip(z_, 0, 1) * (tl.max() - tl.min())
        TILEIDX = np.array(tones)[np.abs(target[..., None] - tl[None, None]).argmin(-1)]
        for _ in range(2):                                       # lone specks (the parchment's grain) take their neighbours' tone
            T2 = TILEIDX.copy()
            for y in range(1, 127):
                for x in range(1, 127):
                    nb = np.delete(TILEIDX[y - 1:y + 2, x - 1:x + 2].ravel(), 4)
                    if (nb == TILEIDX[y, x]).sum() <= 1: T2[y, x] = np.bincount(nb).argmax()
            TILEIDX = T2
# --- the new interior: stone with dots, the cut figure with dark dots
rng = np.random.default_rng(int(E('SEED', 7)))
new = np.where(cut, 12, 6)
r = rng.random((128, 128))
new[(new == 6) & (r < E('DOTS', 0.04))] = 7                    # the originals' stone is smooth with a few dots
new[(new == 12) & (r < 0.02)] = 9
new[r > 0.996] = 8
if os.environ.get('TILE') == '1' and os.environ.get('TONES'): new = TILEIDX
out = np.where(frame, pic, new)
# --- back into pieces and the archive (same size, written in place)
pc = [out[(k // 4) * 32:(k // 4) * 32 + 32, (k % 4) * 32:(k % 4) * 32 + 32] for k in range(16)]
t2 = np.stack([pc[k][rr * 8:rr * 8 + 8, cc * 8:cc * 8 + 8] for k in range(16) for rr in range(4) for cc in range(4)])
flat = t2.reshape(-1, 2); data = (flat[:, 0] | (flat[:, 1] << 4)).astype(np.uint8).tobytes()
mo = F[MEMBER].find(g['data']); assert mo > 0 and F[MEMBER].count(g['data']) == 1
newmember = F[MEMBER][:mo] + data + F[MEMBER][mo + len(data):]
ro = raw.find(F[MEMBER]); assert raw.count(F[MEMBER]) == 1
open(OUT, 'wb').write(raw[:ro] + newmember + raw[ro + len(newmember):])
before = np.pad(P[pic], ((4, 4), (4, 4), (0, 0)), constant_values=255); after = np.pad(P[out], ((4, 4), (4, 4), (0, 0)), constant_values=255)
srcv = np.pad((RGB * 255).astype(np.uint8) * fig[..., None] + 255 * (~fig[..., None]).astype(np.uint8), ((4, 4), (4, 4), (0, 0)), constant_values=255)
z = np.hstack([before, srcv, after]); Image.fromarray(z).resize((z.shape[1] * 3, z.shape[0] * 3), Image.NEAREST).save(PREV)
print('member %d: cut %.0f%% of the figure, written %s' % (MEMBER, 100 * (cut & fig).sum() / max(fig.sum(), 1), OUT))
