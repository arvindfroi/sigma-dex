"""Turn the render passes into DS sprite frames: 15 fixed colours, toon light, dark outline.
python pixelize.py PASSDIR OUTDIR
Writes OUTDIR/f1..fN.png (palette images, index 0 = transparent), OUTDIR/pal.json, OUTDIR/sheet.png"""
import numpy as np, json, sys, os
from PIL import Image
PASS, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
d = np.load(os.path.join(PASS, 'passes.npz'))
meta = json.load(open(os.path.join(PASS, 'meta.json')))
SS, NFR, W1, H1 = meta['SS'], meta['NFR'], meta['W1'], meta['H1']
parts = {int(k): v for k, v in meta['parts'].items()}

PAL_DAY = [(0, 0, 0),
       (16, 16, 24),                     # 1 ink / outline
       (30, 30, 40), (52, 52, 64), (84, 84, 104),   # 2-4 body dark, mid, light
       (92, 16, 22), (154, 30, 34), (208, 56, 58),  # 5-7 red
       (154, 106, 20), (220, 162, 44), (248, 224, 112),  # 8-10 gold
       (136, 144, 168), (200, 206, 222), (244, 246, 252),  # 11-13 white
       (240, 160, 80),                   # 14 warm rim (the sunrise behind)
       (120, 184, 232)]                  # 15 foam shadow
# tropical night: moonlight is cool and blue, the gold and the lamplit gun ports stay warm
PAL_NIGHT = [(0, 0, 0),
       (10, 10, 24),                     # 1 ink / outline
       (24, 24, 34), (46, 48, 66), (84, 88, 116),  # 2-4 body: black like the drawing, a little moonlight in the greys
       (84, 14, 32), (146, 28, 44), (204, 54, 66),  # 5-7 red
       (156, 100, 24), (226, 164, 50), (255, 228, 122),  # 8-10 gold (and lamplight)
       (118, 132, 178), (186, 200, 236), (238, 244, 255),  # 11-13 white, moonlit
       (178, 210, 255),                  # 14 silver moon rim
       (92, 138, 204)]                   # 15 foam shadow
# Ho-Oh's own intro sprite (HG a/2/6/2): no black outline, the edge is the colour's own darker tone, muted colours,
# two or three tones per colour, tiny bright eyes in a dark face. v9 uses this (SAB_STYLE=hooh).
PAL_HOOH = [(0, 0, 0),
       (22, 22, 34),                     # 1 darkest: the black body's edge, pupils, mouth
       (30, 32, 44), (50, 54, 72), (82, 86, 110),   # 2-4 body black, moonlit
       (84, 26, 38), (132, 38, 46), (176, 66, 64),  # 5-7 red
       (128, 90, 40), (192, 146, 62), (236, 206, 118),  # 8-10 gold (10 = the eyes' glint too, like Ho-Oh's)
       (116, 124, 152), (172, 180, 204), (224, 228, 238),  # 11-13 white
       (124, 86, 54), (78, 54, 40)]      # 14-15 wood: deck and masts
# SoulSilver's Lugia (and HG's Ho-Oh) in their night/dawn scenes: every colour is pulled toward the scene's own light
# (Lugia is drawn entirely in teal), low contrast, light from the front, no rim; only the eyes glow (yellow glints)
PAL_LUGIA = [(0, 0, 0),
       (14, 20, 40),                     # 1 darkest: edges, pupils, mouth
       (24, 32, 56), (42, 56, 88), (70, 88, 122),   # 2-4 black body in blue night light
       (66, 30, 54), (98, 40, 62), (132, 62, 78),   # 5-7 red, dusky
       (112, 96, 64), (160, 138, 88), (204, 182, 114),  # 8-10 gold, muted (the eyes must outshine it)
       (98, 120, 150), (144, 164, 186), (190, 204, 218),  # 11-13 white cloth/teeth/claws in moonlight
       (255, 246, 206),                  # 14 the eyes' glow (v12: pale light, brighter than any gold)
       (78, 64, 64)]                     # 15 wood
STYLE = os.environ.get('SAB_STYLE', '')
THEME = os.environ.get('SAB_THEME', 'night')
DEPTHLINE = float(os.environ.get('SAB_DEPTHLINE', 0))
PAL = PAL_NIGHT if THEME == 'night' else PAL_DAY
KEYS = dict(ink=(12, 12, 16), body=(38, 38, 46), hat=(30, 30, 38), red=(142, 26, 28), gold=(224, 176, 48),
            white=(216, 220, 232), foam=(236, 244, 255))
if STYLE in ('hooh', 'lugia'):
    PAL = PAL_HOOH if STYLE == 'hooh' else PAL_LUGIA
    KEYS.update(wood=(118, 76, 40), seam=(64, 40, 22), grey=(84, 84, 94))
CLS = list(KEYS)
RAMP = dict(ink=(1, 1, 1), body=(2, 3, 4), hat=(1, 2, 3), red=(5, 6, 7), gold=(8, 9, 10), white=(11, 12, 13), foam=(15, 13, 13))
TH = dict(ink=(9, 9), body=(0.12, 0.66), hat=(0.15, 0.72), red=(0.18, 0.74), gold=(0.0, 0.55), white=(-0.05, 0.45), foam=(-0.25, 0.1))
RIM_OK = dict(body=14, hat=14 if THEME == 'night' else 4, red=7, gold=10, white=13)
if STYLE in ('hooh', 'lugia'):
    CLS = list(KEYS)
    RAMP.update(body=(2, 3, 4), hat=(1, 2, 3), wood=(15, 14, 14), seam=(15, 15, 15), foam=(11, 13, 13), grey=(3, 4, 4))
    TH.update(wood=(0.1, 0.6), seam=(9, 9), body=(0.22, 0.74), hat=(0.22, 0.78), grey=(0.0, 0.5))
    RIM_OK = dict(body=4, hat=3, red=7, gold=10, white=13, wood=14)
if STYLE == 'lugia':
    RAMP.update(wood=(15, 15, 8), seam=(1, 1, 1))
    TH.update(body=(0.12, 0.8), hat=(0.12, 0.85), red=(0.1, 0.75), gold=(0.05, 0.7), white=(0.0, 0.6))
    RIM_OK = {}
    L = np.array([-0.25, 0.45, 0.86]); L /= np.linalg.norm(L)     # light from the front (the viewer's side), a bit up-left
# one step darker within the same colour: the edge colour in Ho-Oh's style (no black line)
DARK1 = {0: 0, 1: 1, 2: 1, 3: 2, 4: 3, 5: 1, 6: 5, 7: 6, 8: 15, 9: 8, 10: 9, 11: 11, 12: 11, 13: 12, 14: 15, 15: 1}
if STYLE == 'lugia': DARK1.update({8: 1, 14: 14, 15: 1})
L = np.array([-0.5, 0.6, 0.62]) if STYLE != 'lugia' else np.array([-0.25, 0.45, 0.86]); L /= np.linalg.norm(L)
S = np.array([0.35, 0.55, -0.75]); S /= np.linalg.norm(S)      # the sun, behind and above
NO_LINE = {'eye', 'pupil', 'brow', 'nose', 'emblem', 'port', 'portglow', 'spike', 'foam', 'trim', 'masttop', 'mouth', 'socket', 'rail'}
CLEAN = os.environ.get('SAB_CLEAN', '0') == '1'
FEAT = dict(pupil=0.12, eye=0.14, nose=0.18, tusk=0.2, brow=0.22, eyelid=0.22)   # part -> coverage that keeps it
if STYLE in ('hooh', 'lugia'):          # v9: the brow is a shape (it cuts the eye), not a mark; claws are marks
    FEAT = dict(eye=0.12, pupil=0.12, nose=0.18, tusk=0.2, claw=0.2)
WEIGHT = np.ones(16); WEIGHT[1] = 2.4; WEIGHT[[8, 9, 10]] = 1.25; WEIGHT[[11, 12]] = 1.35; WEIGHT[13] = 2.0; WEIGHT[14] = 1.2

def frame(f):
    alb, al, nrm, oid, dep = d[f'alb{f}'], d[f'alpha{f}'], d[f'nrm{f}'], d[f'oid{f}'], d[f'dep{f}']
    nrm = nrm * np.array([1, 1, -1], np.float32)     # Cycles camera space looks along +Z; make +Z face the viewer
    H, W = al.shape
    keys = np.array([KEYS[c] for c in CLS], float) / 255
    cls = np.argmin(((alb[..., None, :] - keys[None, None]) ** 2).sum(-1), -1)
    shade = (nrm * L).sum(-1)
    cloth = np.isin(oid, [k for k, v in parts.items() if v in ('sail', 'sail2', 'flag')])
    shade = np.where(cloth, shade * 1.1 - 0.12, shade)
    flag = np.isin(oid, [k for k, v in parts.items() if v == 'flag'])
    shade = np.where(flag, np.abs(shade) * 0.6 + 0.35, shade)
    rim = ((nrm * S).sum(-1) > 0.6) & (nrm[..., 2] < 0.32) & ~cloth
    idx = np.zeros((H, W), np.uint8)
    for k, c in enumerate(CLS):
        m = cls == k
        r = RAMP[c]; t0, t1 = TH[c]
        lvl = np.where(shade < t0, 0, np.where(shade < t1, 1, 2))
        v = np.array(r)[lvl]
        if c in RIM_OK: v = np.where(rim, RIM_OK[c], v)
        idx[m] = v[m]
    if THEME == 'night' and STYLE not in ('hooh', 'lugia'):
        port = np.isin(oid, [k for k, v in parts.items() if v == 'portglow'])
        idx[port] = np.where(shade[port] > 0.25, 10, 9)
    eye = np.isin(oid, [k for k, v in parts.items() if v == 'eye'])
    idx[eye] = np.where(shade[eye] > -0.4, 13, 12)                 # the eyes always catch the light: a glare
    if STYLE == 'lugia': idx[eye] = 14
    opaque = al > 0.5
    idx[~opaque] = 0
    # ---- 4x4 -> 1x: coverage + weighted mode
    B = lambda a: a.reshape(H1, SS, W1, SS).transpose(0, 2, 1, 3).reshape(H1, W1, SS * SS)
    ob, ib, pb, db = B(opaque), B(idx), B(np.where(opaque, oid, 0)), B(np.where(opaque, dep, 1e9))
    water = (B(oid == 255).mean(-1) > 0.5)
    cov = ob.mean(-1)
    out = np.zeros((H1, W1), np.uint8); part = np.zeros((H1, W1), np.uint8); depth = np.full((H1, W1), 1e9)
    for y in range(H1):
        for x in range(W1):
            if cov[y, x] < 0.42: continue
            v = ib[y, x][ob[y, x]]
            sc = np.bincount(v, minlength=16) * WEIGHT
            out[y, x] = np.argmax(sc)
            pv = pb[y, x][ob[y, x]]
            part[y, x] = np.bincount(pv).argmax()
            depth[y, x] = db[y, x].min()
    if CLEAN:
        # ---- small features survive the downscale (as a pixel artist would keep them): a block that a feature part
        # covers for at least its threshold and where that part is in front takes the feature's colour
        for pn, thr in FEAT.items():
            ids = [k for k, v in parts.items() if v == pn]
            if not ids: continue
            fm = np.isin(pb, ids) & ob
            fcov = fm.mean(-1)
            fdep = np.where(fm, db, 1e9).min(-1)
            for y, x in zip(*np.where(fcov >= thr)):
                if fdep[y, x] > depth[y, x] + 0.05 and out[y, x] != 0: continue
                v = ib[y, x][fm[y, x]]
                out[y, x] = np.bincount(v, minlength=16).argmax(); part[y, x] = pb[y, x][fm[y, x]][0]
                depth[y, x] = min(depth[y, x], fdep[y, x])
        # ---- speckles: a lone pixel of one colour inside another area takes the area's colour; stray opaque
        # pixels with at most one opaque neighbour go (features excepted)
        featids = [k for k, v in parts.items() if v in FEAT or (v in NO_LINE and v != 'foam')]
        for _ in range(2):
            o2 = out.copy()
            for y in range(1, H1 - 1):
                for x in range(1, W1 - 1):
                    c = out[y, x]
                    if c == 0 or part[y, x] in featids: continue
                    n4 = [out[y - 1, x], out[y + 1, x], out[y, x - 1], out[y, x + 1]]
                    if c in n4: continue
                    n8 = out[y - 1:y + 2, x - 1:x + 2].ravel(); n8 = np.delete(n8, 4)
                    if (n8 > 0).sum() <= 1: o2[y, x] = 0; continue
                    bc = np.bincount(n8[n8 > 0], minlength=16)
                    if bc.max() >= 5: o2[y, x] = bc.argmax()
            out = o2
        foamids = [k for k, v in parts.items() if v == 'foam']
        fo = np.isin(part, foamids) & (out > 0)
        nbf = sum(np.roll(np.roll(fo, dy, 0), dx, 1) for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)))
        out[fo & (nbf < 2)] = 0
    # ---- outlines
    res = out.copy()
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    for y in range(H1):
        for x in range(W1):
            if out[y, x] == 0: continue
            pn = parts.get(int(part[y, x]), '')
            for dy, dx in nb:
                yy, xx = y + dy, x + dx
                outside = not (0 <= yy < H1 and 0 <= xx < W1)
                if outside or out[yy, xx] == 0:
                    if pn == 'foam': break
                    if not outside and water[yy, xx]:
                        if STYLE in ('hooh', 'lugia'): res[y, x] = DARK1[int(out[y, x])]
                        elif res[y, x] in (3, 4, 14): res[y, x] = 2       # dark contact line at the waterline
                        break
                    res[y, x] = DARK1[int(out[y, x])] if STYLE in ('hooh', 'lugia') else 1; break
                qn = parts.get(int(part[yy, xx]), '')
                if part[yy, xx] != part[y, x] and pn not in NO_LINE and qn not in NO_LINE and depth[y, x] > depth[yy, xx] + 0.12:
                    res[y, x] = DARK1[int(out[y, x])] if STYLE in ('hooh', 'lugia') else 1; break
                if DEPTHLINE and part[yy, xx] == part[y, x] and pn in ('body', 'hull') and depth[y, x] > depth[yy, xx] + DEPTHLINE:
                    res[y, x] = DARK1[int(out[y, x])] if STYLE in ('hooh', 'lugia') else 1; break      # same part folding over itself (a leg in front of the chest)
    return res

frames = [frame(f) for f in range(1, NFR + 1)]
pal_flat = [c for rgb in PAL for c in rgb]
for i, fr in enumerate(frames, 1):
    im = Image.fromarray(fr).convert('P'); im.putpalette(pal_flat + [0] * (768 - len(pal_flat))); im.info['transparency'] = 0
    im.save(os.path.join(OUT, f'f{i}.png'), transparency=0)
json.dump(dict(palette=PAL, anchor=meta['anchor'], W=W1, H=H1), open(os.path.join(OUT, 'pal.json'), 'w'))
# preview sheet: 3x, sky background
P = np.array(PAL, np.uint8)
row = []
for fr in frames:
    rgb = P[fr]; rgb[fr == 0] = (28, 40, 84) if THEME == 'night' else (96, 150, 210)
    row.append(np.pad(rgb, ((4, 4), (4, 4), (0, 0)), constant_values=255))
img = Image.fromarray(np.concatenate(row, 1))
img.resize((img.width * 3, img.height * 3), Image.NEAREST).save(os.path.join(OUT, 'sheet.png'))
print('frames', len(frames), 'opaque px', [(int((f > 0).sum())) for f in frames])
