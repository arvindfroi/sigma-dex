"""The Sigma sprite renderer: builds a game sprite from clean cel-shaded artwork, pixel by pixel.

Shrinking a picture to 64 pixels turns its lines and faces to mud, so the sprite is built the way
a spriter builds one. Seven steps, each with one job; every number they use is in STYLE below,
with where it comes from:

1. segment   the artwork: its silhouette, its ink lines, and its parts. A part is one colour
             (one hue and colourfulness) in all its light and shadow, so light and shadow of the
             same colour can never become two parts with a line between them.
2. sample    the artwork onto the sprite grid: for every pixel its part, the artwork's lightness
             there and how much ink it holds.
3. shape     clean the shape: notches in the silhouette are filled and spurs removed; specks of
             a part smaller than a few pixels join the part around them.
4. face      find the features that must keep their pixels: pupils, glints, brows and mouths.
5. light     every pixel takes the tone of its part's ramp (shadow, base, light, highlight, line,
             outline) nearest to what the artwork shows there: the artwork's own light, shadow and
             strokes decide, so its detail (brows, mouths, scales) survives; where a dark stroke
             runs through a pixel, the stroke wins (the contrast rule of PixelOE). The older
             modelled light (faithful=False) invents light from the upper left instead.
6. lines     outline in each part's own dark tone (darkest on the shadow side at the bottom
             right), lines between parts that differ, and the artwork's inner lines where they
             form a line.
7. palette   each part gets a ramp of tones; the renderer itself fits all ramps into the 15
             colours the game allows (a later merge picked colours at random and ate small
             parts). A back view can be given the front's palette so both match.

Same artwork, same sprite: nothing is random. The look is modelled on measurements of the
games' own sprites (docs/SPRITE_STYLE.md); scripts/check_sprite_style.py renders a fixed test set
and compares it with locked reference sprites, so any change to these steps shows up there.
"""
import cv2
import numpy as np
from PIL import Image

STYLE = dict(
    supersample=12,        # artwork pixels looked at per sprite pixel (per side)
    background=232,        # brighter than this on every channel, connected to the border: background
    ink=70,                # Lab lightness below this: the artwork's ink lines
    neutral_chroma=10,     # below this colourfulness a colour counts as grey/white/black
    hue_clusters=8,        # colour groups looked for before same-hue groups are joined
    same_hue=12,           # degrees: closer hues with similar colourfulness are one part
    same_chroma=0.7,       # ...if the weaker is at least this share of the stronger
    neutral_gap=60,        # greys further apart than this in lightness are different parts (white belly, black claws)
    min_part=4,            # pixels: a smaller patch of a part joins the part around it
    big_part=10,           # pixels: only parts at least this big get lines between them
    part_line=22,          # Lab distance: parts at least this different get a line between them
    pupil=45, glint=235,   # Lab lightness of pupils and glints in the artwork
    face=0.55,             # pupils and face lines are only looked for in the upper 55% of the creature
    light_falloff=1.1,     # how strongly light falls off from the upper left across a part
    art_light=0.8,         # how much the artwork's own light and dark counts
    levels=(-0.45, 0.8, 1.7),  # light score thresholds: shadow | base | light | highlight
    colours=15,            # the game's limit per sprite (plus the see-through colour)
    faithful=True,         # tones and dark detail from the artwork itself (else: modelled light)
    detail_drop=60,        # Lab lightness below the part's colour at which a pixel's dark detail is drawn as a line
    stroke_contrast=35,    # Lab lightness: a cell whose darkest sixth is this much darker than its middle shows a stroke
)
# The tones of a part, as (lightness change or factor, colourfulness factor, cool/warm shift).
# Shadows a little cooler and lights a little warmer; outlines keep the hue but are muted, as the
# measured outlines of the games' sprites are (median brightness 44, about half nearly black).
RAMP = {
    "highlight": ("+", 30, 1.0, 3), "light": ("+", 16, 1.0, 5), "base": ("+", 0, 1.0, 0),
    "shadow": ("+", -26, 1.0, -7), "line": ("*", 0.52, 0.4, -4),
    "outline": ("*", 0.38, 0.22, -3), "outline_dark": ("*", 0.22, 0.15, -2),
}


RAMP_FLOOR = {"outline": 72, "outline_dark": 40, "line": 86}   # in Lab lightness (0-255): 72 is about brightness 44


# ---------- colour helpers ----------

def lab(rgb):
    return cv2.cvtColor(rgb.astype(np.uint8).reshape(-1, 1, 3), cv2.COLOR_RGB2LAB).reshape(rgb.shape).astype(np.float32)


def to_rgb(colour):
    return cv2.cvtColor(np.clip(np.asarray(colour, np.float32), 0, 255).astype(np.uint8).reshape(-1, 1, 3), cv2.COLOR_LAB2RGB).reshape(-1, 3)


def chroma_hue(colour):
    a, b = colour[..., 1] - 128, colour[..., 2] - 128
    return np.hypot(a, b), np.degrees(np.arctan2(b, a))


def load(path):
    """The picture on white (a transparent background becomes white)."""
    image = Image.open(path).convert("RGBA")
    flat = Image.new("RGBA", image.size, "white")
    flat.alpha_composite(image)
    return np.array(flat.convert("RGB"))


def mask_of(rgb):
    """The creature: everything not connected to the white border."""
    bg = (rgb.min(axis=2) > STYLE["background"]).astype(np.uint8)
    n, labels = cv2.connectedComponents(bg, connectivity=4)
    border = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))) - {0}
    return ~(np.isin(labels, list(border)) & (bg == 1))


def box_of(path):
    ys, xs = np.nonzero(mask_of(load(path)))
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def neighbours4(a, fill):
    p = np.pad(a, 1, constant_values=fill)
    return p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]          # up, down, left, right


def thin(binary):
    """Zhang-Suen thinning: wears a drawn stroke down to its one-pixel middle line."""
    img = binary.astype(np.uint8).copy()
    while True:
        changed = False
        for step in (0, 1):
            p = np.pad(img, 1)
            n = [p[:-2, 1:-1], p[:-2, 2:], p[1:-1, 2:], p[2:, 2:], p[2:, 1:-1], p[2:, :-2], p[1:-1, :-2], p[:-2, :-2]]   # P2..P9
            b = sum(x.astype(int) for x in n)
            a = sum(((n[i] == 0) & (n[(i + 1) % 8] == 1)).astype(int) for i in range(8))
            if step == 0:
                c1, c2 = n[0] * n[2] * n[4], n[2] * n[4] * n[6]
            else:
                c1, c2 = n[0] * n[2] * n[6], n[0] * n[4] * n[6]
            drop = (img == 1) & (b >= 2) & (b <= 6) & (a == 1) & (c1 == 0) & (c2 == 0)
            if drop.any():
                img[drop] = 0
                changed = True
        if not changed:
            return img.astype(bool)


def clean_lines(lines):
    """One-pixel lines without doubled corners (the pixel-perfect rule): a line pixel with line
    pixels on two touching sides (an L) goes if those two also touch diagonally through it."""
    lines = lines.copy()
    up, down, left, right = neighbours4(lines, False)
    for vert, horiz in ((up, left), (up, right), (down, left), (down, right)):
        corner = lines & vert & horiz
        # keep it if it is the only link (an end or a junction): more than the two L neighbours
        n8 = sum(x.astype(int) for x in neighbours8(lines))
        lines[corner & (n8 == 2)] = False
        up, down, left, right = neighbours4(lines, False)
    return lines


def neighbours8(a):
    p = np.pad(a, 1)
    return [p[:-2, :-2], p[:-2, 1:-1], p[:-2, 2:], p[1:-1, :-2], p[1:-1, 2:], p[2:, :-2], p[2:, 1:-1], p[2:, 2:]]


# ---------- 1. segment ----------

def segment(rgb, mask):
    """Silhouette, ink and parts of the artwork. Returns (Lab picture, ink mask, part map, part colours)."""
    L = lab(rgb)
    dark = mask & (L[..., 0] < STYLE["ink"])
    # ink is dark and thin; a dark area wider than half a sprite pixel (black claws, sunglasses) is
    # a part of the design, not a line
    k = STYLE["supersample"]
    solid_dark = cv2.morphologyEx(dark.astype(np.uint8), cv2.MORPH_OPEN, np.ones((k // 2 + 1,) * 2, np.uint8)).astype(bool)
    ink = dark & ~solid_dark
    paint = mask & ~ink
    chroma, hue = chroma_hue(L)
    part = np.full(mask.shape, -1, np.int32)
    colours = []
    # greys (white, grey, black parts): up to three groups around their commonest lightnesses;
    # groups closer than neutral_gap are one part (antialiased edges between black and white would
    # otherwise join everything into one grey)
    grey = paint & (chroma < STYLE["neutral_chroma"])
    if grey.any():
        values = L[..., 0][grey].astype(np.float32).reshape(-1, 1)
        k3 = int(min(3, max(1, len(values) // 50)))
        cv2.setRNGSeed(1)
        _, gidx, centres = cv2.kmeans(values, k3, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.5), 4, cv2.KMEANS_PP_CENTERS)
        order = np.argsort(centres.ravel())
        groups = [[order[0]]]
        for i in order[1:]:
            if centres[i, 0] - centres[groups[-1][-1], 0] < STYLE["neutral_gap"]:
                groups[-1].append(i)
            else:
                groups.append([i])
        gidx = gidx.ravel()
        sub = np.full(len(gidx), -1)
        for g in groups:
            sub[np.isin(gidx, g)] = len(colours)
            colours.append(L[grey][np.isin(gidx, g)].mean(axis=0))
        part[grey] = sub
    # colours: grouped by hue and colourfulness only (lightness is light and shadow, not a part)
    colour = paint & ~grey
    if colour.any():
        pts = np.column_stack([L[..., 1][colour], L[..., 2][colour]]).astype(np.float32)
        k = int(min(STYLE["hue_clusters"], max(1, len(pts) // 50)))
        cv2.setRNGSeed(1)
        _, lab_idx, _ = cv2.kmeans(pts, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.5), 4, cv2.KMEANS_PP_CENTERS)
        lab_idx = lab_idx.ravel()
        cent = [L[colour][lab_idx == i].mean(axis=0) for i in range(k)]
        join = list(range(k))
        def root(i):
            while join[i] != i:
                i = join[i]
            return i
        c, h = chroma_hue(np.array(cent))
        for i in range(k):
            for j in range(i + 1, k):
                dh = abs((h[i] - h[j] + 180) % 360 - 180)
                if dh < STYLE["same_hue"] and min(c[i], c[j]) >= STYLE["same_chroma"] * max(c[i], c[j]):
                    join[root(j)] = root(i)
        roots = sorted({root(i) for i in range(k)})
        ids = np.array([len(colours) + roots.index(root(i)) for i in range(k)])
        part[colour] = ids[lab_idx]
        for _ in roots:                                   # ids run on from the greys, in root order
            colours.append(L[colour][ids[lab_idx] == len(colours)].mean(axis=0))
    # ink takes the part around it, so lines are drawn by the renderer and not mistaken for parts
    grown = part.copy()
    for _ in range(STYLE["supersample"]):
        todo = (grown < 0) & mask
        if not todo.any():
            break
        d = cv2.dilate((grown + 1).astype(np.float32), np.ones((3, 3), np.uint8)).astype(np.int32) - 1
        grown = np.where(todo, d, grown)
    return L, ink, grown, np.array(colours, np.float32)


# ---------- 2. sample ----------

def sample(L, ink, part, mask, gh, gw, k):
    """Per sprite pixel: part (majority, -1 = empty), the artwork's lightness, the share of ink."""
    cells = np.full((gh, gw), -1, np.int32)
    tone = np.zeros((gh, gw), np.float32)
    inkshare = np.zeros((gh, gw), np.float32)
    global detail, rep
    detail = np.zeros((gh, gw), np.float32)
    rep = np.zeros((gh, gw, 3), np.float32)
    for y in range(gh):
        for x in range(gw):
            cm = mask[y * k:(y + 1) * k, x * k:(x + 1) * k]
            if cm.mean() < 0.5:
                continue
            p = part[y * k:(y + 1) * k, x * k:(x + 1) * k][cm]
            p = p[p >= 0]
            if not p.size:
                continue
            cells[y, x] = np.bincount(p).argmax()
            ci = ink[y * k:(y + 1) * k, x * k:(x + 1) * k]
            inkshare[y, x] = ci[cm].mean()
            own = L[y * k:(y + 1) * k, x * k:(x + 1) * k][cm & ~ci]
            tone[y, x] = own[:, 0].mean() if own.size else L[y * k:(y + 1) * k, x * k:(x + 1) * k][cm][:, 0].mean()
            cl = L[y * k:(y + 1) * k, x * k:(x + 1) * k][cm][:, 0]
            detail[y, x] = np.percentile(cl, 20)          # the dark detail in the cell (PixelOE-style: contrast wins)
            cells_lab = L[y * k:(y + 1) * k, x * k:(x + 1) * k][cm]
            med = np.median(cl)
            dark_part = cells_lab[cl <= np.percentile(cl, 15)]
            # what the cell shows: its darkest sixth where a dark stroke runs through it, else its middle
            rep[y, x] = dark_part.mean(axis=0) if med - np.percentile(cl, 15) > STYLE["stroke_contrast"] else np.median(cells_lab, axis=0)
    return cells, tone, inkshare


# ---------- 3. shape ----------

def clean_shape(cells, colours):
    """See below; specks in the face (the upper part of the creature: eye whites, irises, a nose)
    of two pixels or more are kept, they are what makes the face."""
    return _clean_shape(cells, colours)


def _clean_shape(cells, colours):
    """Fill one-pixel notches, drop one-pixel spurs, and let specks of a part join their surroundings
    (very dark and very light specks stay: they are pupils and glints)."""
    cells = cells.copy()
    for _ in range(2):
        solid = cells >= 0
        n4 = sum(n.astype(int) for n in neighbours4(solid, False))
        cp = np.pad(cells, 1, constant_values=-1)
        for y, x in zip(*np.nonzero(~solid & (n4 >= 3))):
            around = [cp[y + 1 + dy, x + 1 + dx] for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)) if cp[y + 1 + dy, x + 1 + dx] >= 0]
            cells[y, x] = max(set(around), key=around.count)
        cells[solid & (n4 <= 1)] = -1
    cells = pixel_perfect(cells)
    for _ in range(2):
        for i in range(len(colours)):
            if colours[i][0] < STYLE["pupil"] + 5 or colours[i][0] > STYLE["glint"]:
                continue
            n, lbl = cv2.connectedComponents((cells == i).astype(np.uint8), connectivity=4)
            for j in range(1, n):
                speck = lbl == j
                if speck.sum() >= STYLE["min_part"]:
                    continue
                if speck.sum() >= 2 and np.nonzero(speck)[0].mean() < STYLE["face"] * cells.shape[0]:
                    continue
                ring = cv2.dilate(speck.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~speck & (cells >= 0) & (cells != i)
                if ring.any():
                    cells[speck] = np.bincount(cells[ring]).argmax()
    return cells


def pixel_perfect(cells):
    """Round the outer corners, as spriters do on round shapes: a pixel that sticks out at a corner
    of the silhouette (empty on two touching sides, solid on the other two and diagonally inside)
    goes, so steps along curves and diagonals are single pixels instead of doubled ones (the
    "pixel-perfect" rule of Aseprite, applied to the edge). A pixel a thin part hangs on stays."""
    cells = cells.copy()
    gh, gw = cells.shape
    solid = cells >= 0
    up, down, left, right = (n for n in neighbours4(solid, False))
    p = np.pad(solid, 1)
    diag = {(-1, -1): p[:-2, :-2], (-1, 1): p[:-2, 2:], (1, -1): p[2:, :-2], (1, 1): p[2:, 2:]}
    remove = np.zeros_like(solid)
    # a corner pixel: empty on two touching sides, its other two sides solid, and the pixel diagonally
    # inside solid; the corners on both sides of it continue the edge (so the step is doubled)
    for (vy, empty_v), (hx, empty_h) in (((-1, ~up), (-1, ~left)), ((-1, ~up), (1, ~right)), ((1, ~down), (-1, ~left)), ((1, ~down), (1, ~right))):
        full_v = down if vy == -1 else up
        full_h = right if hx == -1 else left
        inside = diag[(-vy, -hx)]
        remove |= solid & empty_v & empty_h & full_v & full_h & inside
    # keep pixels that a thin part hangs on (removing them would split the shape)
    for y, x in zip(*np.nonzero(remove)):
        before = cv2.connectedComponents((cells >= 0).astype(np.uint8), connectivity=4)[0]
        cells[y, x], keep = -1, cells[y, x]
        if cv2.connectedComponents((cells >= 0).astype(np.uint8), connectivity=4)[0] > before:
            cells[y, x] = keep
    return cells


# ---------- 4. face ----------

def find_face(L, ink, mask, gh, gw, k, size):
    """Pupils and glints (blobs in the artwork) and face lines (ink inside the creature that is not
    its outline), in the upper part of the creature. Returns ([(kind, y, x)], face line mask)."""
    features = []
    # a pupil is a solid dark blob; in the artwork it often touches the eye's own outline, so thin
    # lines are first worn away (an opening of a third of a sprite pixel) and only solid dark stays
    thin = np.ones((max(3, k // 3),) * 2, np.uint8)
    dark = cv2.morphologyEx((mask & (L[..., 0] < STYLE["pupil"])).astype(np.uint8), cv2.MORPH_OPEN, thin).astype(bool)
    for kind, sel in (("pupil", dark), ("glint", mask & (L[..., 0] > STYLE["glint"]))):
        n, lbl, stats, cent = cv2.connectedComponentsWithStats(sel.astype(np.uint8), connectivity=8)
        for i in range(1, n):
            area, bw, bh = stats[i, cv2.CC_STAT_AREA], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
            if area < 0.2 * k * k or max(bw, bh) > 4 * k or min(bw, bh) < 0.3 * k:
                continue                                          # not a blob: a speck or a long line
            y, x = int(cent[i][1] // k), int(cent[i][0] // k)
            if kind == "pupil" and y > STYLE["face"] * gh:
                continue                                          # a dark spot low on the body is a spot, not a pupil
            features.append((kind, y, x))
    edge = mask & ~cv2.erode(mask.astype(np.uint8), np.ones((k // 2 * 2 + 1,) * 2, np.uint8)).astype(bool)
    n, lbl, stats, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
    lines = np.zeros((gh, gw), bool)
    for i in range(1, n):
        x0, y0, bw, bh, area = stats[i]
        if max(bw, bh) > 0.3 * size * k or area < 0.15 * k * k:
            continue
        comp = lbl == i
        if (comp & edge).sum() > 0.3 * comp.sum():
            continue                                              # part of the outline
        lines |= comp.reshape(gh, k, gw, k).mean(axis=(1, 3)) >= 0.18
    lines[int(gh * 0.5):] = False
    return features, lines


def draw_eyes(rgb, L, ink, mask, cells, k):
    """The eyes, taken from the artwork. An eye is a white (an eye white) in the upper part of the
    creature, together with what sits inside it. A white patch surrounded by dark is not an eye
    white but a glint. Every sprite pixel of an eye becomes pupil or iris where the artwork is
    mostly dark there (iris where that dark is coloured), white where it is mostly white; each
    glint becomes one light pixel. Returns ({(y, x): kind}, {kind: Lab colour})."""
    gh, gw = cells.shape
    chroma, _ = chroma_hue(L)
    white = mask & (L[..., 0] > 200) & (chroma < 15)
    dark = mask & (L[..., 0] < 100)
    eyes, colours, glints = {}, {}, []
    n, lbl, stats, cent = cv2.connectedComponentsWithStats(white.astype(np.uint8), connectivity=8)
    creature = mask.sum()
    ring_kernel = np.ones((max(3, k // 4),) * 2, np.uint8)
    candidates = []
    for i in range(1, n):
        x0, y0, bw, bh, area = stats[i]
        if area < 0.15 * k * k or y0 + bh / 2 > STYLE["face"] * mask.shape[0] or area > 0.06 * creature:
            continue
        comp = lbl == i
        ring = cv2.dilate(comp.astype(np.uint8), ring_kernel).astype(bool) & ~comp & mask
        if ring.any() and dark[ring].mean() > 0.6:
            glints.append((int(cent[i][1] // k), int(cent[i][0] // k)))     # white inside dark: a glint
        elif area >= 0.5 * k * k:
            candidates.append(i)
    for i in candidates:
        x0, y0, bw, bh, area = stats[i]
        ys0, ys1, xs0, xs1 = max(0, y0 - k // 2), min(mask.shape[0], y0 + bh + k // 2), max(0, x0 - k // 2), min(mask.shape[1], x0 + bw + k // 2)
        # the whole eye: the white with the holes in it filled (the iris and pupil sit in a hole)
        # (filled from outside the box; holes are what the fill cannot reach). An iris often runs out
        # through a gap in the white at the bottom, so the white's convex hull is used as the eye
        comp = (lbl == i).astype(np.uint8)
        pts = cv2.findNonZero(comp)
        hull = np.zeros(mask.shape, np.uint8)
        cv2.fillConvexPoly(hull, cv2.convexHull(pts), 1)
        whole = hull.astype(bool) & mask
        iris_px = whole & dark & (chroma > 14) & (L[..., 0] > STYLE["pupil"])
        if iris_px.sum() > 0.3 * k * k:
            colours["iris"] = L[iris_px].mean(axis=0)
        for y in range(max(0, ys0 // k), min(gh, (ys1 - 1) // k + 1)):
            for x in range(max(0, xs0 // k), min(gw, (xs1 - 1) // k + 1)):
                if cells[y, x] < 0:
                    continue
                cw = whole[y * k:(y + 1) * k, x * k:(x + 1) * k]
                if cw.mean() < 0.35:
                    continue                                       # the rim and the skin around it
                d = dark[y * k:(y + 1) * k, x * k:(x + 1) * k][cw].mean()
                if d >= 0.4:
                    coloured = iris_px[y * k:(y + 1) * k, x * k:(x + 1) * k][cw].mean()
                    eyes[(y, x)] = "iris" if "iris" in colours and coloured > 0.5 * d else "pupil"
                else:
                    eyes[(y, x)] = "white"
        colours["white"] = np.array([244, 128, 128], np.float32)
    for y, x in glints:
        if (y, x) in eyes or (0 <= y < gh and 0 <= x < gw and cells[y, x] >= 0):
            eyes[(y, x)] = "glint"
    return eyes, colours


# ---------- 5. light ----------

def faithful_levels(cells, tone, colours):
    """0 shadow, 1 base, 2 light, 3 highlight for every pixel, from the artwork itself: each pixel
    takes the tone of its part's ramp nearest to the artwork's own lightness there. The artwork's
    light, shadow and detail decide; nothing is invented. Lone shade pixels join their neighbours."""
    gh, gw = cells.shape
    solid = cells >= 0
    level = np.full((gh, gw), -1, np.int8)
    names = ("shadow", "base", "light", "highlight")
    for i in np.unique(cells[solid]):
        sel = cells == i
        ramp = np.array([tone_of(colours[i], n)[0] for n in names])
        level[sel] = np.abs(tone[sel][:, None] - ramp[None, :]).argmin(axis=1)
    lp = np.pad(level, 1, constant_values=-1); cp = np.pad(cells, 1, constant_values=-1)
    for y, x in zip(*np.nonzero(solid)):
        own = [lp[y + 1 + dy, x + 1 + dx] for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)) if cp[y + 1 + dy, x + 1 + dx] == cells[y, x]]
        if len(own) >= 3 and level[y, x] not in own:
            level[y, x] = max(set(own), key=own.count)
    return level


def light_levels(cells, tone):
    """0 shadow, 1 base, 2 light, 3 highlight for every pixel (-1 empty)."""
    gh, gw = cells.shape
    solid = cells >= 0
    out_up, out_down, out_left, out_right = (n < 0 for n in neighbours4(cells, -1))
    shape = np.zeros((gh, gw), np.float32)
    # near the silhouette: lit where the outside is above or to the left, shaded below or to the right
    for d, w in ((1, 1.0), (2, 0.6), (3, 0.35)):
        def empty(dy, dx):
            p = np.pad(solid, d, constant_values=False)
            return ~p[d + dy:d + dy + gh, d + dx:d + dx + gw]
        shape += w * ((empty(-d, -d) | empty(-d, 0)).astype(np.float32) - (empty(d, d) | empty(d, 0)).astype(np.float32))
    # across each part: lighter toward its upper left
    for i in np.unique(cells[solid]):
        n, lbl, stats, cent = cv2.connectedComponentsWithStats((cells == i).astype(np.uint8), connectivity=4)
        for j in range(1, n):
            x0, y0, bw, bh, area = stats[j]
            ys, xs = np.nonzero(lbl == j)
            shape[ys, xs] -= STYLE["light_falloff"] * ((xs - cent[j][0]) / max(bw, 2) + (ys - cent[j][1]) / max(bh, 2))
    level = np.full((gh, gw), -1, np.int8)
    a, b, c = STYLE["levels"]
    for i in np.unique(cells[solid]):
        sel = cells == i
        weight = cv2.GaussianBlur(sel.astype(np.float32), (0, 0), 0.9)
        def smooth(field):
            return cv2.GaussianBlur(field * sel, (0, 0), 0.9) / np.maximum(weight, 1e-3)
        t = smooth(tone)[sel]
        score = STYLE["art_light"] * (t - np.median(t)) / (t.std() + 6) + smooth(shape)[sel]
        level[sel] = np.select([score < a, score < b, score < c], [0, 1, 2], 3)
    # shades come in clusters: a pixel whose shade none of its four same-part neighbours shares takes theirs
    for _ in range(2):
        lp = np.pad(level, 1, constant_values=-1); cp = np.pad(cells, 1, constant_values=-1)
        for y, x in zip(*np.nonzero(solid)):
            own = [lp[y + 1 + dy, x + 1 + dx] for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)) if cp[y + 1 + dy, x + 1 + dx] == cells[y, x]]
            if own and level[y, x] not in own:
                level[y, x] = max(set(own), key=own.count)
    return level


# ---------- 6. lines ----------

def line_art(ink, mask, cells, k):
    """The artwork's inner lines as one-pixel sprite lines, the way a spriter traces them: every
    ink stroke is thinned to its middle line, a sprite pixel the middle line runs through for at
    least half its width becomes a line pixel, and the result is thinned again and cleaned of
    doubled corners. Strokes along the silhouette are left out (the outline draws those), and so
    are lone dots."""
    gh, gw = cells.shape
    inner = cv2.erode(mask.astype(np.uint8), np.ones((int(k * 0.8) | 1,) * 2, np.uint8)).astype(bool)
    middle = thin(ink) & inner
    lines = middle.reshape(gh, k, gw, k).sum(axis=(1, 3)) >= 0.5 * k
    lines = clean_lines(thin(lines) & (cells >= 0))
    n, lbl, stats, _ = cv2.connectedComponentsWithStats(lines.astype(np.uint8), connectivity=8)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < 2:
            lines[lbl == i] = False
    return lines


def line_kinds(cells, colours, drawn_lines):
    """For every pixel which tone it takes instead of its shade: 'outline', 'outline_dark', 'line' or ''."""
    gh, gw = cells.shape
    solid = cells >= 0
    kinds = np.full((gh, gw), "", object)
    up, down, left, right = neighbours4(cells, -1)
    sizes = np.zeros((gh, gw), np.int32)
    for i in np.unique(cells[solid]):
        n, lbl, stats, _ = cv2.connectedComponentsWithStats((cells == i).astype(np.uint8), connectivity=4)
        for j in range(1, n):
            sizes[lbl == j] = stats[j, cv2.CC_STAT_AREA]
    big = sizes >= STYLE["big_part"]
    bigp = np.pad(big, 1)
    face_top = STYLE["face"] * gh
    for y, x in zip(*np.nonzero(solid)):
        c = cells[y, x]
        nb = (up[y, x], down[y, x], left[y, x], right[y, x])
        if -1 in nb:
            kinds[y, x] = "outline_dark" if nb[1] == -1 or nb[3] == -1 else "outline"
            continue
        for o, (dy, dx) in zip(nb, ((-1, 0), (1, 0), (0, -1), (0, 1))):
            if o != c and big[y, x] and bigp[y + 1 + dy, x + 1 + dx] and colours[c][0] <= colours[o][0] \
                    and np.linalg.norm(colours[c] - colours[o]) > STYLE["part_line"]:
                kinds[y, x] = "outline"                            # the line goes on the darker part's side
                break
        else:
            if drawn_lines[y, x]:                                  # traced lines: darkest in the face
                kinds[y, x] = "outline" if y < face_top else "line"
    return kinds


# ---------- 7. palette ----------

def tone_of(colour, name):
    mode, amount, chroma_factor, shift = RAMP[name]
    c = np.array(colour, np.float32)
    if mode == "*":
        # a dark part's outline would be plain black: outlines keep at least this much light, as
        # the games do (their outlines median brightness is 44); the shadow side may go darker
        c[0] = max(c[0] * amount, RAMP_FLOOR.get(name, 0))
    else:
        room = 252 - c[0] if amount > 0 else 255
        c[0] = np.clip(c[0] + min(amount * (0.55 if amount < 0 and colour[0] > 210 else 1.0), room), 0, 255)
    c[1] = 128 + (c[1] - 128) * chroma_factor + shift * 0.4
    c[2] = 128 + (c[2] - 128) * chroma_factor + shift
    return c


def fit_palette(wanted, counts, limit):
    """Choose at most `limit` colours for the wanted (part, tone) colours, merging the least used
    and most similar first, so big parts keep their whole ramp. Returns {(part, tone): Lab colour}."""
    keys = list(wanted)
    colour = {k: wanted[k] for k in keys}
    group = {k: k for k in keys}
    while len(set(group.values())) > limit:
        reps = sorted(set(group.values()), key=str)
        best = None
        for a in range(len(reps)):
            for b in range(a + 1, len(reps)):
                ra, rb = reps[a], reps[b]
                cost = np.linalg.norm(colour[ra] - colour[rb]) * (1 + 0.02 * min(counts.get(ra, 0), counts.get(rb, 0)))
                if best is None or cost < best[0]:
                    best = (cost, ra, rb)
        _, keep, drop = best
        if counts.get(drop, 0) > counts.get(keep, 0):
            keep, drop = drop, keep
        for k in keys:
            if group[k] == drop:
                group[k] = keep
        counts[keep] = counts.get(keep, 0) + counts.get(drop, 0)
    return {k: colour[group[k]] for k in keys}


# ---------- the whole ----------

def render(path, size=54, window=None, fit=None, palette=None):
    """The sprite for the artwork at `path` as an RGBA picture.
    size: longest side in pixels; fit: (width, height) to fit instead; window: (x0, y0, x1, y1) part
    of the picture to use (shared by two animation frames); palette: RGB colours to use (the
    front's, for a back view), else the renderer chooses its own 15.
    Thin tips thinner than half a pixel drop out, so the drawn creature can come out smaller than
    asked; then it is drawn once more, scaled up by the difference."""
    image = draw(path, size, window, fit, palette)
    if fit is None and window is None:
        a = np.array(image)[..., 3] > 0
        ys, xs = np.nonzero(a)
        drawn = max(np.ptp(ys), np.ptp(xs)) + 1 if len(ys) else size
        if drawn < size - 1:
            image = draw(path, size * size / drawn, window, fit, palette)
    return image


def draw(path, size=54, window=None, fit=None, palette=None):
    """One drawing pass of render() (same arguments)."""
    k = STYLE["supersample"]
    rgb = load(path)
    mask = mask_of(rgb)
    x0, y0, x1, y1 = window or box_of(path)
    rgb, mask = rgb[y0:y1, x0:x1], mask[y0:y1, x0:x1]
    h, w = mask.shape
    scale = min(fit[0] / w, fit[1] / h) if fit else size / max(h, w)
    gh, gw = max(1, round(h * scale)), max(1, round(w * scale))
    big_rgb = cv2.resize(rgb, (gw * k, gh * k), interpolation=cv2.INTER_AREA)
    big_mask = cv2.resize(mask.astype(np.uint8), (gw * k, gh * k), interpolation=cv2.INTER_NEAREST).astype(bool)

    L, ink, part, colours = segment(big_rgb, big_mask)                       # 1
    cells, tone, inkshare = sample(L, ink, part, big_mask, gh, gw, k)        # 2
    cells = clean_shape(cells, colours)                                       # 3
    features, face_lines = find_face(L, ink, big_mask, gh, gw, k, size)      # 4
    eyes, eye_colours = draw_eyes(big_rgb, L, ink, big_mask, cells, k)
    drawn_lines = line_art(ink, big_mask, cells, k) | (face_lines & (cells >= 0))
    # no lines inside eye whites (or other very light parts): an eye is its rim, pupil and glint
    light_part = np.isin(cells, [i for i in range(len(colours)) if colours[i][0] > 200])
    drawn_lines &= ~light_part
    if STYLE["faithful"]:
        level = faithful_levels(cells, tone, colours)                         # 5
        # dark detail of the artwork (brows, creases, scale edges) that the traced lines missed
        base_L = np.array([c[0] for c in colours])
        dark_detail = (cells >= 0) & (detail < np.where(cells >= 0, base_L[np.maximum(cells, 0)], 0) - STYLE["detail_drop"])
        drawn_lines = drawn_lines | (dark_detail & ~light_part)
    else:
        level = light_levels(cells, tone)                                     # 5
    kinds = line_kinds(cells, colours, drawn_lines)                           # 6

    # 7: what every pixel wants, then fitted into the palette
    names = ("shadow", "base", "light", "highlight")
    solid = cells >= 0
    want = {}
    counts = {}
    tone_names = names + ("line", "outline")
    if STYLE["faithful"]:
        # every pixel inside the silhouette takes the tone of its part nearest to what the artwork
        # shows there (strokes included): the artwork's detail decides, the ramp keeps it clean
        for y, x in zip(*np.nonzero(solid)):
            if kinds[y, x] in ("outline_dark",) or (kinds[y, x] == "outline" and -1 in [n[y, x] for n in neighbours4(cells, -1)]):
                continue
            c = int(cells[y, x])
            options = [(n, tone_of(colours[c], n)) for n in tone_names]
            best = min(options, key=lambda o: np.linalg.norm((o[1] - rep[y, x]) * np.array([1.0, 0.6, 0.6])))[0]
            if best in names:
                level[y, x], kinds[y, x] = names.index(best), ""
            else:
                kinds[y, x] = best
    for y, x in zip(*np.nonzero(solid)):
        key = (int(cells[y, x]), kinds[y, x] or names[level[y, x]])
        want[(y, x)] = key
        counts[key] = counts.get(key, 0) + 1
    wanted = {key: tone_of(colours[key[0]], key[1]) for key in counts}
    pupil = min((wanted[key] for key in wanted if key[1] == "outline_dark"), key=lambda c: c[0], default=np.array([20, 128, 128], np.float32))
    eye = {"pupil": pupil.copy(), "glint": np.array([248, 128, 128], np.float32)}
    # every pupil has its glint: if the artwork's glint did not land next to it, it goes just above it
    # (or beside it), as in the games' eyes
    pupils = [(y, x) for kind, y, x in features if kind == "pupil"]
    glints = [(y, x) for kind, y, x in features if kind == "glint"]
    for y, x in pupils:
        if not any(abs(y - gy) <= 1 and abs(x - gx) <= 1 and (gy, gx) != (y, x) for gy, gx in glints):
            for gy, gx in ((y - 1, x), (y - 1, x - 1), (y, x - 1), (y, x + 1)):
                if 0 <= gy < gh and 0 <= gx < gw and solid[gy, gx] and (gy, gx) not in pupils:
                    features.append(("glint", gy, gx)); glints.append((gy, gx))
                    break
    for kind, y, x in features:
        if 0 <= y < gh and 0 <= x < gw and solid[y, x]:
            old_key = want[(y, x)]
            if old_key == ("eye", kind):
                continue
            want[(y, x)] = ("eye", kind)
            counts[("eye", kind)] = counts.get(("eye", kind), 0) + 1
            counts[old_key] -= 1
    eye.update(eye_colours)
    for (y, x), kind in eyes.items():
        if kind not in eye:
            continue
        old_key = want[(y, x)]
        if old_key == ("eye", "glint"):
            continue                                             # the glint stays on top
        want[(y, x)] = ("eye", kind)
        counts[("eye", kind)] = counts.get(("eye", kind), 0) + 1
        counts[old_key] -= 1
    wanted.update({("eye", k2): v for k2, v in eye.items()})
    counts = {key: n for key, n in counts.items() if n > 0}
    wanted = {key: wanted[key] for key in counts}
    if palette is not None:                                                   # the front's palette: take the nearest, exactly
        table = lab(np.array(palette, np.uint8).reshape(1, -1, 3)).reshape(-1, 3)
        rgb_of = {key: tuple(int(v) for v in palette[int(np.argmin(np.linalg.norm(table - c, axis=1)))]) for key, c in wanted.items()}
    else:
        counts = dict(counts)
        for kind in ("pupil", "glint", "iris", "white"):                     # eyes are never merged away
            if ("eye", kind) in counts:
                counts[("eye", kind)] += 10 ** 6
        chosen = fit_palette(wanted, counts, STYLE["colours"])
        rgb_of = {key: tuple(int(v) for v in to_rgb(c)[0]) for key, c in chosen.items()}
    out = np.zeros((gh, gw, 4), np.uint8)
    for (y, x), key in want.items():
        out[y, x, :3] = rgb_of[key]
        out[y, x, 3] = 255
    return Image.fromarray(out)


def palette_of(image):
    """The colours a rendered sprite uses (to give a back view the same ones)."""
    a = np.array(image.convert("RGBA"))
    return sorted({tuple(int(v) for v in c) for c in a[a[..., 3] >= 128][:, :3]})


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build a sprite from clean cel-shaded art (the Sigma sprite style).")
    parser.add_argument("art", help="the artwork (official-style, white or transparent background)")
    parser.add_argument("out", help="where to save the sprite (a PNG, to give to scripts/sprites.py)")
    parser.add_argument("--size", type=int, default=54, help="longest side in pixels: 54 first stage, 60 middle, 63 final")
    parser.add_argument("--back", action="store_true", help="a back view: drawn 1.4 times closer, cut off flat at the bottom")
    parser.add_argument("--palette-from", help="a front sprite whose colours the back must use")
    args = parser.parse_args()
    palette = palette_of(Image.open(args.palette_from)) if args.palette_from else None
    if args.back:
        image = render(args.art, fit=(62, round(args.size * 1.4)), palette=palette)
        image = image.crop((0, 0, image.width, min(args.size + 2, int(image.height * 0.85))))
    else:
        image = render(args.art, size=args.size, palette=palette)
    image.save(args.out)
    print("%s: %d x %d pixels, %d colours" % (args.out, image.width, image.height, len(palette_of(image))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
