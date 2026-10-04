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
    trace=0.5,             # share of a sprite pixel's width an ink stroke must run through it to become a line
    trace_margin=0.8,      # strokes closer to the silhouette than this (in sprite pixels) belong to the outline
    thin_run=1 / 3,        # share of a sprite pixel's width a thin feature's middle line must run through it
    line_density=0.12,     # at most this share of a part is inner line (the games' median is 0.11)
    max_stretch=1.05,      # sized by covered area, the longest side is at most this times the stage's size
    accents=3,             # face marks in colours the sprite does not have (a pink blush) get at most this many palette slots
    accent_gap=35,         # Lab distance from every colour the sprite has, for a mark's colour to count as an accent
    eye_rim=True,          # eye whites on light skin get a dark rim
    speck=4,               # pixels: a bit this small that does not touch the creature is dropped
    base_band=None,        # lightness percentiles (lo, hi) of a part's pixels whose mean is its base colour; None = the average (tried (50, 85) on 2026-10-04: the group found it worse)
    small_white=12,        # pixels: a white patch this small is not shaded (its grey shadow would be a speck)
    hole=0.004,            # share of the creature: an enclosed patch of the page's colour at least this big is a hole
    hole_tolerance=6,      # how close to the page's colour (each channel) a hole's pixels are
    brighten=0,            # Lab lightness added to the artwork before tones are picked (sprites are lit brighter)
)
# The tones of a part, as (lightness change or factor, colourfulness factor, cool/warm shift).
# Shadows a little cooler and lights a little warmer. Outlines as measured on the games' starters:
# nearly black on the shadow side (about half of every outline is darker than brightness 30, which
# gives the sprites their "pop"), and a muted dark tone of the part on the lit side (brightness ~70-90).
RAMP = {
    "highlight": ("+", 30, 1.0, 3), "light": ("+", 16, 1.0, 5), "base": ("+", 0, 1.0, 0),
    "shadow": ("+", -30, 0.95, -7), "line": ("*", 0.42, 0.55, -4),
    "outline": ("*", 0.5, 0.6, -3), "outline_dark": ("*", 0.1, 0.12, -2),
}


RAMP_FLOOR = {"outline": 72, "outline_dark": 0, "line": 62}   # in Lab lightness (0-255): 72 is about brightness 44


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
    outside = np.isin(labels, list(border)) & (bg == 1)
    # a hole in the creature (the gap between an arm and the body) is background too: an enclosed
    # area of exactly the background's colour, bigger than a speck, with nothing dark inside it.
    # Eye whites have a pupil and teeth are a little grey; a hole is the flat white of the page
    page = np.median(rgb[outside], axis=0) if outside.any() else np.array([255, 255, 255])
    creature = (~outside).sum()
    rows = np.nonzero((~outside).any(axis=1))[0]
    top, bottom = (rows.min(), rows.max()) if len(rows) else (0, 1)
    flat = (np.abs(rgb.astype(np.int16) - page).max(axis=2) <= STYLE["hole_tolerance"]) & ~outside
    n, holes, stats, _ = cv2.connectedComponentsWithStats(flat.astype(np.uint8), connectivity=4)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < STYLE["hole"] * creature:
            continue
        hole = holes == i
        # what the patch encloses (an eye white encloses its iris and pupil, of any colour); a hole
        # encloses nothing
        filled = np.zeros(hole.shape, np.uint8)
        contours, _ = cv2.findContours(hole.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(filled, contours, -1, 1, -1)
        # and a hole is edged by the creature's dark outline; a glow or a shine is edged by colour
        ring = cv2.dilate(filled, np.ones((5, 5), np.uint8)).astype(bool) & ~filled.astype(bool)
        edged = (rgb[ring].max(axis=1) < 130).mean() if ring.any() else 0
        # high up on the creature, a patch with colour at its edge is an eye white with its iris on the
        # rim (measured on 20 cases: eyes lie in the upper 40% with 4-15% colour around them; holes
        # have none, or lie low, between an arm and the body or the body and a tail)
        lab_ring = lab(rgb[ring].reshape(-1, 1, 3)).reshape(-1, 3)
        coloured = (np.hypot(lab_ring[:, 1] - 128, lab_ring[:, 2] - 128) > 25).mean() if ring.any() else 0
        height = (stats[i, cv2.CC_STAT_TOP] + stats[i, cv2.CC_STAT_HEIGHT] / 2 - top) / max(1, bottom - top)
        # (and a small patch up there may be an eye white with its pupil on the rim: an eye lost is far
        # worse than a little hole left white)
        eye_like = height < 0.45 and (coloured > 0.03 or stats[i, cv2.CC_STAT_AREA] < 0.01 * creature)
        if (filled.astype(bool) & ~hole).sum() < 0.02 * stats[i, cv2.CC_STAT_AREA] and edged > 0.5 and not eye_like:
            outside |= hole
    return ~outside


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
    # the same for light: a light area thinner than half a sprite pixel (rim light along an edge, a
    # shine) is lighting, not a part of the design; it belongs to the part it lies on
    light = mask & (L[..., 0] > 200)
    solid_light = cv2.morphologyEx(light.astype(np.uint8), cv2.MORPH_OPEN, np.ones((k // 2 + 1,) * 2, np.uint8)).astype(bool)
    shine = light & ~solid_light
    paint = mask & ~ink & ~shine
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
    # a part's colour is its lit colour, not its average: a spriter picks the colour of the part in
    # light as the base and puts shadow under it; the average of the artwork's light and shadow is a
    # muddy middle (our sprites were darker inside than the games': interior lightness 129 vs 161)
    for i in range(len(colours) if STYLE["base_band"] else 0):
        own = L[(grown == i) & ~ink]
        if len(own) > 50:
            lo, hi = np.percentile(own[:, 0], [STYLE["base_band"][0], STYLE["base_band"][1]])
            band = own[(own[:, 0] >= lo) & (own[:, 0] <= hi)]
            if len(band):
                colours[i] = band.mean(axis=0)
    return L, ink, grown, np.array(colours, np.float32)


# ---------- 2. sample ----------

def sample(L, ink, part, mask, gh, gw, k):
    """Per sprite pixel: part (majority, -1 = empty), the artwork's lightness, the share of ink."""
    cells = np.full((gh, gw), -1, np.int32)
    tone = np.zeros((gh, gw), np.float32)
    inkshare = np.zeros((gh, gw), np.float32)
    global detail, rep, stroke, middle
    detail = np.zeros((gh, gw), np.float32)
    middle = np.zeros((gh, gw, 3), np.float32)
    stroke = np.zeros((gh, gw), bool)
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
            stroke[y, x] = med - np.percentile(cl, 15) > STYLE["stroke_contrast"]
            middle[y, x] = np.median(cells_lab, axis=0)
            rep[y, x] = dark_part.mean(axis=0) if stroke[y, x] else middle[y, x]
    return cells, tone, inkshare


def thin_features(mask, part, ink, cells, k):
    """Parts of the artwork thinner than a sprite pixel - antennae, thin horns, tail tips, narrow
    stripes, wing veins - would drop out of the grid (a pixel needs half its area covered). A
    spriter draws them as one-pixel lines, and so does this: every thin structure is worn down to
    its middle line, and each sprite pixel that middle line runs through for a third of its width
    takes the part it belongs to. Thin structures of the silhouette (antennae) and thin stripes of
    one colour inside the creature (a gold stripe on red) are both found. Returns (cells, mask of
    the pixels so drawn, which the shape step must keep)."""
    gh, gw = cells.shape
    cells = cells.copy()
    kernel = np.ones((k // 2 + 1,) * 2, np.uint8)
    keep = np.zeros((gh, gw), bool)
    def trace(region, owner, min_run=None):
        min_run = STYLE["thin_run"] * k if min_run is None else min_run
        middle = thin(region)
        run = middle.reshape(gh, k, gw, k).sum(axis=(1, 3)) >= min_run      # the middle line is continuous, so is the traced line
        for y, x in zip(*np.nonzero(run)):
            o = owner[y * k:(y + 1) * k, x * k:(x + 1) * k][middle[y * k:(y + 1) * k, x * k:(x + 1) * k]]
            o = o[o >= 0]
            if o.size:
                cells[y, x] = np.bincount(o).argmax()
                keep[y, x] = True
    # thin parts of the silhouette (outside what the grid already holds)
    whole = mask & ~ink
    thin_out = mask & ~cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, kernel).astype(bool)
    grid = np.repeat(np.repeat(cells >= 0, k, axis=0), k, axis=1)
    trace(thin_out & ~grid, part)
    # thin stripes of one part inside the creature
    for i in np.unique(part[part >= 0]):
        sel = (part == i) & whole
        thin_in = sel & ~cv2.morphologyEx(sel.astype(np.uint8), cv2.MORPH_OPEN, kernel).astype(bool)
        n, lbl, st, _ = cv2.connectedComponentsWithStats(thin_in.astype(np.uint8), connectivity=8)
        long = np.isin(lbl, [j for j in range(1, n) if max(st[j, 2], st[j, 3]) >= 2 * k])   # a stripe, not an edge fringe
        trace(long & grid, np.where(long, part, -1), k / 3)
    return cells, keep


def face_marks(rgb, L, mask, ink, cells, k):
    """Every mark is drawn, as a spriter draws it: each small region of the artwork that differs
    from what is around it - a blush, a mouth, teeth, a stripe on a shoulder, a spot - keeps at least
    one pixel in its own colour: its middle line if it is a stroke, the pixels it covers most if it
    is a blob. (A pixel otherwise takes the colour of the part that covers most of it, and a dark
    red stripe on yellow became a muddy dark yellow.) Returns {(y, x): Lab colour}."""
    gh, gw = cells.shape
    # the whole creature: a stripe on a shoulder is as much a mark as a blush on a cheek
    head = mask & cv2.erode(mask.astype(np.uint8), np.ones((k // 2 + 1,) * 2, np.uint8)).astype(bool)
    smooth = cv2.medianBlur(rgb, 5)
    Ls = lab(smooth)
    skin = cv2.medianBlur(rgb, 4 * k + 1 if (4 * k + 1) % 2 else 4 * k + 2)       # the surroundings of every point
    # a mark differs in colour (hue, colourfulness), or is near white or near black on a coloured
    # skin (teeth, an eye); a region that is only darker or lighter is shading, not a mark
    Lk = lab(skin)
    colour_diff = np.linalg.norm(Ls[..., 1:] - Lk[..., 1:], axis=2)
    extreme = ((Ls[..., 0] > 225) | (Ls[..., 0] < 50)) & (np.abs(Ls[..., 0] - Lk[..., 0]) > 60)
    mark = head & ((colour_diff > 22) | extreme) & ~ink
    marks = {}
    n, lbl, st, _ = cv2.connectedComponentsWithStats(mark.astype(np.uint8), connectivity=8)
    for i in range(1, n):
        x0, y0, bw, bh, area = st[i]
        if area < 0.08 * k * k or area > 6 * k * k:
            continue                                           # a speck, or not a mark but a whole part
        comp = lbl == i
        # the mark's own colour: its core, the half that differs most from the skin around it (the
        # mean of the whole mark includes its blurred edge, and a small white mark on purple skin
        # came out grey-lavender, then a grey speck)
        differ = colour_diff[comp] + np.abs(Ls[..., 0] - Lk[..., 0])[comp]
        core = differ >= np.median(differ)
        colour = L[comp][core].mean(axis=0)
        cover = comp.reshape(gh, k, gw, k).mean(axis=(1, 3))
        cellsof = list(zip(*np.nonzero(cover >= 0.3)))
        if not cellsof:
            middle = thin(comp)
            cellsof = list(zip(*np.nonzero(middle.reshape(gh, k, gw, k).sum(axis=(1, 3)) >= max(1, k // 4))))
        if not cellsof:
            y, x = np.unravel_index(cover.argmax(), cover.shape); cellsof = [(y, x)]
        for y, x in cellsof:
            if cells[y, x] >= 0:
                marks[(int(y), int(x))] = colour
    return marks


# ---------- 3. shape ----------

def clean_shape(cells, colours, keep=None):
    """See below; specks in the face (the upper part of the creature: eye whites, irises, a nose)
    of two pixels or more are kept, they are what makes the face."""
    return _clean_shape(cells, colours, keep)


def _clean_shape(cells, colours, keep=None):
    """Fill one-pixel notches, drop one-pixel spurs, and let specks of a part join their surroundings.
    Pupils and glints are not parts: the face step draws them, so no speck needs to be kept for them."""
    cells = cells.copy()
    for _ in range(2):
        solid = cells >= 0
        n4 = sum(n.astype(int) for n in neighbours4(solid, False))
        cp = np.pad(cells, 1, constant_values=-1)
        for y, x in zip(*np.nonzero(~solid & (n4 >= 3))):
            around = [cp[y + 1 + dy, x + 1 + dx] for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)) if cp[y + 1 + dy, x + 1 + dx] >= 0]
            cells[y, x] = max(set(around), key=around.count)
        cells[solid & (n4 <= 1) & ~(keep if keep is not None else False)] = -1
    traced = cells.copy()
    cells = pixel_perfect(cells)
    if keep is not None:
        cells[keep] = traced[keep]                                # traced thin features stay as drawn
    for _ in range(2):
        for i in range(len(colours)):
            n, lbl = cv2.connectedComponents((cells == i).astype(np.uint8), connectivity=4)
            for j in range(1, n):
                speck = lbl == j
                if speck.sum() >= STYLE["min_part"] or (keep is not None and keep[speck].any()):
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
    # A dark eye is a solid dark blob with the artwork's own glint in it (Autuman's black ovals); a
    # dark blob without a glint is a tail, a claw or a marking, never an eye. Glints are never
    # invented: only light the artwork has inside a pupil is a glint. (Eyes with an eye white are
    # found by draw_eyes.) Thin lines are worn away first, as a pupil often touches the eye's rim.
    wear = np.ones((max(3, k // 3),) * 2, np.uint8)
    dark = cv2.morphologyEx((mask & (L[..., 0] < STYLE["pupil"])).astype(np.uint8), cv2.MORPH_OPEN, wear).astype(bool)
    shine = mask & (L[..., 0] > 190)                              # inside a pupil, anything light is its glint
    n, lbl, stats, cent = cv2.connectedComponentsWithStats(dark.astype(np.uint8), connectivity=8)
    for i in range(1, n):
        area, bw, bh = stats[i, cv2.CC_STAT_AREA], stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT]
        if area < 0.2 * k * k or max(bw, bh) > 4 * k or min(bw, bh) < 0.3 * k:
            continue                                              # not a blob: a speck or a long line
        y, x = int(cent[i][1] // k), int(cent[i][0] // k)
        if y > STYLE["face"] * gh:
            continue
        blob = lbl == i
        # the blob with its holes filled: a glint sits in a hole of the pupil, or on its edge
        hull = np.zeros(mask.shape, np.uint8)
        cv2.fillConvexPoly(hull, cv2.convexHull(cv2.findNonZero(blob.astype(np.uint8))), 1)
        glint = shine & hull.astype(bool)
        if glint.sum() < 0.015 * k * k:
            continue                                              # no glint of its own: not an eye
        cov = blob.reshape(gh, k, gw, k).mean(axis=(1, 3))
        for cy, cx in (list(zip(*np.nonzero(cov >= 0.33))) or [(y, x)]):
            features.append(("pupil", int(cy), int(cx)))
        gy, gx = np.nonzero(glint)
        features.append(("glint", int(gy.mean() // k), int(gx.mean() // k)))
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
        # traced along its middle line, at least one pixel: a short mouth spread over three pixels
        # covers none of them much, but is still a mouth
        middle = thin(comp).reshape(gh, k, gw, k).sum(axis=(1, 3))
        stroke = middle >= k / 4
        if not stroke.any():
            stroke = middle == middle.max()
        lines |= stroke
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
    eyes, colours = {}, {}
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
            continue                     # white inside dark: a glint (find_face draws those, inside pupils) or a claw tip
        elif area >= 0.5 * k * k:
            candidates.append(i)
    # a narrow (angry, squinting) eye has little white: if one eye was found, a smaller white at
    # the same height is the other eye
    if candidates:
        heights = [cent[i][1] for i in candidates]
        for i in range(1, n):
            if i in candidates:
                continue
            x0, y0, bw, bh, area = stats[i]
            if area >= 0.12 * k * k and any(abs(cent[i][1] - hy) < 2 * k for hy in heights) and y0 + bh / 2 <= STYLE["face"] * mask.shape[0]:
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
        # an eye has a pupil: a white with no solid dark inside it is a horn, a tooth or a marking;
        # and the eye is the pupil and the white close around it (a horn touching the eye is not eye)
        pupil_px = whole & (L[..., 0] < STYLE["pupil"] + 20)
        if pupil_px.sum() < 0.05 * k * k:
            continue
        # and it is not a grin: a grin is white crossed by two or more thin dark gaps between the
        # teeth, each running across most of its height; an eye has one pupil (which may be a thin
        # slit too, in a narrow angry eye)
        gn, glbl, gst, _ = cv2.connectedComponentsWithStats(pupil_px.astype(np.uint8), connectivity=8)
        gaps = sum(1 for j in range(1, gn) if gst[j, cv2.CC_STAT_HEIGHT] >= 0.6 * bh and gst[j, cv2.CC_STAT_WIDTH] <= 0.35 * k)
        if gaps >= 2:
            continue
        whole &= cv2.dilate(pupil_px.astype(np.uint8), np.ones((4 * k + 1,) * 2, np.uint8)).astype(bool)
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
        # a small or thin pupil still gets its pixel: the one holding most of it
        if not any(eyes.get((y, x)) in ("pupil", "iris") for y in range(max(0, ys0 // k), min(gh, (ys1 - 1) // k + 1)) for x in range(max(0, xs0 // k), min(gw, (xs1 - 1) // k + 1))):
            share = pupil_px.reshape(gh, k, gw, k).sum(axis=(1, 3))
            y, x = np.unravel_index(share.argmax(), share.shape)
            if share[y, x] > 0 and cells[y, x] >= 0:
                eyes[(int(y), int(x))] = "pupil"
        colours["white"] = np.array([244, 128, 128], np.float32)
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
        level[sel] = np.abs(tone[sel][:, None] + STYLE["brighten"] - ramp[None, :]).argmin(axis=1)
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
    inner = cv2.erode(mask.astype(np.uint8), np.ones((int(k * STYLE["trace_margin"]) | 1,) * 2, np.uint8)).astype(bool)
    middle = thin(ink) & inner
    lines = middle.reshape(gh, k, gw, k).sum(axis=(1, 3)) >= STYLE["trace"] * k
    lines = clean_lines(thin(lines) & (cells >= 0))
    n, lbl, stats, _ = cv2.connectedComponentsWithStats(lines.astype(np.uint8), connectivity=8)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < 2:
            lines[lbl == i] = False
    # texture (muscles, fur, scales) is suggested, not drawn stroke for stroke: where a part's lines
    # would cover more than STYLE["line_density"] of it, its longest lines are kept first
    n, lbl, stats, _ = cv2.connectedComponentsWithStats(lines.astype(np.uint8), connectivity=8)
    patches = []                                         # each connected patch of a part on its own (a head, a wing)
    for i in np.unique(cells[cells >= 0]):
        pn, plbl = cv2.connectedComponents((cells == i).astype(np.uint8), connectivity=4)
        patches += [plbl == j for j in range(1, pn)]
    for sel in patches:
        budget = STYLE["line_density"] * sel.sum()
        comps = sorted({int(c) for c in np.unique(lbl[sel & lines]) if c}, key=lambda c: -stats[c, cv2.CC_STAT_AREA])
        used = 0
        for c in comps:
            size = int((lbl[sel] == c).sum())
            if used + size > budget:
                lines[(lbl == c) & sel] = False
            else:
                used += size
    return lines


def line_kinds(cells, colours, drawn_lines, face_lines=None):
    face_lines = np.zeros(cells.shape, bool) if face_lines is None else face_lines
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
            if face_lines[y, x]:                                   # brows and mouths: darkest
                kinds[y, x] = "outline"
            elif drawn_lines[y, x]:                                # other traced lines: the part's line tone
                kinds[y, x] = "line"
    return kinds


# ---------- 7. palette ----------

def tone_of(colour, name):
    mode, amount, chroma_factor, shift = RAMP[name]
    c = np.array(colour, np.float32)
    if mode == "*":
        # a dark part's outline would be plain black: outlines keep at least this much light, as
        # the games do (their outlines median brightness is 44); the shadow side may go darker
        c[0] = max(c[0] * amount, RAMP_FLOOR.get(name, 0))
        if colour[0] > 200 and np.hypot(colour[1] - 128, colour[2] - 128) < 15:
            # white's lines (an eye's rim, the gaps between teeth) are near black, not mid grey: a
            # mid-grey line on a sprite reads as a grey speck
            c[0] = RAMP_FLOOR.get(name, 0) if name != "outline_dark" else c[0]
    else:
        room = 252 - c[0] if amount > 0 else 255
        c[0] = np.clip(c[0] + min(amount * (0.8 if amount < 0 and colour[0] > 210 else 1.0), room), 0, 255)
    if name in SHADE_TONES:
        # shadows turn the hue the way the games' own palettes do (SHADOW_HUE_TURN), not one fixed
        # way: a fixed "cooler" shift turns yellow toward green, which reads as olive mud
        a, b = c[1] - 128, c[2] - 128
        chroma, hue = np.hypot(a, b) * chroma_factor, np.arctan2(b, a) + np.radians(shadow_turn(np.degrees(np.arctan2(b, a))) * SHADE_TONES[name])
        c[1], c[2] = 128 + chroma * np.cos(hue), 128 + chroma * np.sin(hue)
        return c
    c[1] = 128 + (c[1] - 128) * chroma_factor + shift * 0.4
    c[2] = 128 + (c[2] - 128) * chroma_factor + shift
    return c


# How the games turn a colour's hue in its shadow, by the colour's hue (Lab hue angle, degrees):
# measured on 2026-10-04 over the 844 front sprite palettes of pokeemerald-expansion (each bright
# colour against its nearest darker shade 20-60 darker, median per 30 degrees). Yellow turns toward
# orange (-10), blue toward purple (+7 to +13), reds and greens hardly turn.
SHADOW_HUE_TURN = {0: 2.1, 30: 0.7, 60: -7.4, 90: -9.7, 120: 1.3, 150: 0.0, 180: 0.9, 210: 9.9,
                   240: 12.7, 270: 6.9, 300: 1.0, 330: -0.5}
SHADE_TONES = {"shadow": 1.5, "line": 3.0, "outline": 3.0, "outline_dark": 3.0}   # how far each darker tone turns (the darker, the further: Pikachu goes yellow, orange, brown)


def shadow_turn(hue):
    hue %= 360
    lo = int(hue // 30) * 30
    t = (hue - lo) / 30
    return SHADOW_HUE_TURN[lo] * (1 - t) + SHADOW_HUE_TURN[(lo + 30) % 360] * t


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
                ca, cb = colour[ra], colour[rb]
                # a change of hue is far worse than a change of lightness: a yellow must never become olive
                d = np.sqrt((ca[0] - cb[0]) ** 2 + 4 * ((ca[1] - cb[1]) ** 2 + (ca[2] - cb[2]) ** 2))
                same_part = ra[0] == rb[0] and ra[0] != "eye"
                cost = d * (0.5 if same_part else 1.0) * (1 + 0.02 * min(counts.get(ra, 0), counts.get(rb, 0)))
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

def render(path, size=54, window=None, fit=None, palette=None, area=None):
    """The sprite for the artwork at `path` (see _render), without stray specks."""
    return drop_specks(_render(path, size, window, fit, palette, area))


def drop_specks(image):
    """Remove stray specks: bits of at most STYLE["speck"] pixels that do not touch the creature (not
    even at a corner). They come from thin tips of the artwork that fall between two sprite pixels;
    a spriter never leaves them. Everything joined to the creature (antenna tips, claws) stays."""
    a = np.array(image)
    n, lbl, stats, _ = cv2.connectedComponentsWithStats((a[..., 3] > 0).astype(np.uint8), connectivity=8)
    if n > 2:
        biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        for i in range(1, n):
            if i != biggest and stats[i, cv2.CC_STAT_AREA] <= STYLE["speck"]:
                a[lbl == i] = 0
    return Image.fromarray(a)


def _render(path, size=54, window=None, fit=None, palette=None, area=None):
    """The sprite for the artwork at `path` as an RGBA picture.
    size: longest side in pixels; fit: (width, height) to fit instead; window: (x0, y0, x1, y1) part
    of the picture to use (shared by two animation frames); palette: RGB colours to use (the
    front's, for a back view), else the renderer chooses its own 15.
    Thin tips thinner than half a pixel drop out, so the drawn creature can come out smaller than
    asked; then it is drawn once more, scaled up by the difference."""
    if area and fit is None and window is None:
        # the game sizes creatures by how much of the frame they cover, not by their longest side: a
        # compact creature and a long one of the same stage cover about the same number of pixels
        first = draw(path, size, window, fit, palette)
        covered = max(1, int((np.array(first)[..., 3] > 0).sum()))
        # but a thin creature is not drawn taller than its stage allows (STYLE["max_stretch"] x size)
        size = min(64.0, size * STYLE["max_stretch"], size * (area / covered) ** 0.5)
        image = draw(path, size, window, fit, palette)
        drawn = max(image.size)
        return image if drawn <= 64 else draw(path, size * 64 / drawn, window, fit, palette)
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
    cells, thin_kept = thin_features(big_mask, part, ink, cells, k)           # 2b
    cells = clean_shape(cells, colours, thin_kept)                            # 3
    features, face_lines = find_face(L, ink, big_mask, gh, gw, k, size)      # 4
    eyes, eye_colours = draw_eyes(big_rgb, L, ink, big_mask, cells, k)
    eye_cells = np.zeros((gh, gw), np.uint8)
    for (y, x), kind in eyes.items():
        if kind in ("white", "pupil", "iris"):
            eye_cells[y, x] = 1
    for kind, y, x in features:
        if kind == "pupil":
            eye_cells[y, x] = 1
    LAST["eyes"] = cv2.connectedComponents(cv2.dilate(eye_cells, np.ones((2, 2), np.uint8)), connectivity=8)[0] - 1
    marks = face_marks(big_rgb, L, big_mask, ink, cells, k)
    # the face is where the eyes are: brows and mouth lie around them; elsewhere a stroke is a line
    eye_px = [yx for yx, kind in eyes.items()] + [(y, x) for kind, y, x in features if kind == "pupil"]
    face_box = np.zeros((gh, gw), bool)
    if eye_px:
        ys = [p[0] for p in eye_px]; xs = [p[1] for p in eye_px]
        reach = max(3, (max(xs) - min(xs)) // 2 + 2)
        face_box[max(0, min(ys) - 3):min(gh, max(ys) + reach + 2), max(0, min(xs) - reach):min(gw, max(xs) + reach + 1)] = True
    face_lines = face_lines & face_box
    drawn_lines = line_art(ink, big_mask, cells, k) | (face_lines & (cells >= 0))
    # no lines inside eye whites: an eye is its rim, pupil and glint. Other white parts (teeth, a white
    # belly) keep their lines: the gaps between teeth and the edge between a grin and the eyes are
    # what makes a face readable
    light_part = np.zeros((gh, gw), bool)
    for (y, x), kind in eyes.items():
        light_part[y, x] = kind == "white"
    drawn_lines &= ~light_part
    if STYLE["faithful"]:
        level = faithful_levels(cells, tone, colours)                         # 5
        # dark detail of the artwork (brows, creases, scale edges) that the traced lines missed
        base_L = np.array([c[0] for c in colours])
        dark_detail = (cells >= 0) & (detail < np.where(cells >= 0, base_L[np.maximum(cells, 0)], 0) - STYLE["detail_drop"])
        # in white parts other than eyes (teeth, a white belly) a thin dark line through a pixel does
        # not make it dark: a grin's tooth gaps would turn the whole grin grey. Only a pixel that is
        # dark on the whole is a line there
        white_part = np.isin(cells, [i for i in range(len(colours)) if colours[i][0] > 200]) & ~light_part
        soft = white_part & (middle[..., 0] > np.where(cells >= 0, base_L[np.maximum(cells, 0)], 0) - STYLE["detail_drop"])
        dark_detail &= ~soft
        stroke[soft] = False
        rep[soft] = middle[soft]
        drawn_lines = drawn_lines | (dark_detail & ~light_part)
    else:
        level = light_levels(cells, tone)                                     # 5
    kinds = line_kinds(cells, colours, drawn_lines, face_lines & (cells >= 0))  # 6

    # 7: what every pixel wants, then fitted into the palette
    names = ("shadow", "base", "light", "highlight")
    solid = cells >= 0
    want = {}
    counts = {}
    tone_names = names + ("line", "outline")
    if STYLE["faithful"]:
        # every pixel inside the silhouette takes the tone of its part nearest to what the artwork
        # shows there (strokes included): the artwork's detail decides, the ramp keeps it clean
        traced = drawn_lines.copy()
        for y, x in zip(*np.nonzero(solid)):
            if kinds[y, x] in ("outline_dark",) or (kinds[y, x] == "outline" and -1 in [n[y, x] for n in neighbours4(cells, -1)]):
                continue
            if traced[y, x] and kinds[y, x]:
                continue                                   # a traced line of the artwork stays a line
            c = int(cells[y, x])
            # line and outline tones only where the artwork has a stroke: a deep shadow is still a shadow
            allowed = names + ("line",) if stroke[y, x] else names       # the outline tone belongs to the silhouette
            options = [(n, tone_of(colours[c], n)) for n in allowed]
            # a sprite is lit brighter than the artwork (the games' sprites are lighter inside than ours
            # were: STYLE["brighten"]); a stroke stays as dark as the artwork draws it
            seen = rep[y, x] + (np.array([STYLE["brighten"], 0, 0], np.float32) if not stroke[y, x] else 0)
            best = min(options, key=lambda o: np.linalg.norm((o[1] - seen) * np.array([1.0, 0.6, 0.6])))[0]
            if best in names:
                level[y, x], kinds[y, x] = names.index(best), ""
            else:
                kinds[y, x] = best
        # inner strokes are one pixel wide, as a spriter draws them: thick dark runs from the artwork
        # are thinned to their middle (pupils are drawn separately and keep their shape)
        edge = np.zeros_like(solid)
        for n in neighbours4(cells, -1):
            edge |= solid & (n < 0)
        inner = solid & ~edge & np.isin(kinds, ["line", "outline"])
        keep = thin(inner) | (traced & inner)
        for y, x in zip(*np.nonzero(inner & ~keep)):
            c = int(cells[y, x])
            options = [(n, tone_of(colours[c], n)) for n in names]
            kinds[y, x] = ""
            level[y, x] = names.index(min(options, key=lambda o: np.linalg.norm(o[1] - rep[y, x]))[0])
    # small white details (teeth, claw tips, a small eye white) stay white: the shadow tone of white is
    # grey, and on a few pixels it reads as a grey speck, not as shading. Only big white areas (a
    # belly) are shaded
    whites = [i for i in range(len(colours)) if colours[i][0] > 200]
    if whites:
        n_w, lbl_w, st_w, _ = cv2.connectedComponentsWithStats((np.isin(cells, whites) & solid).astype(np.uint8), connectivity=4)
        for j in range(1, n_w):
            if st_w[j, cv2.CC_STAT_AREA] <= STYLE["small_white"]:
                spot = (lbl_w == j) & (kinds == "") & (level == 0)
                level[spot] = 1
    for y, x in zip(*np.nonzero(solid)):
        key = (int(cells[y, x]), kinds[y, x] or names[level[y, x]])
        want[(y, x)] = key
        counts[key] = counts.get(key, 0) + 1
    wanted = {key: tone_of(colours[key[0]], key[1]) for key in counts}
    pupil = min((wanted[key] for key in wanted if key[1] == "outline_dark"), key=lambda c: c[0], default=np.array([20, 128, 128], np.float32))
    eye = {"pupil": pupil.copy(), "glint": np.array([248, 128, 128], np.float32)}
    # glints are drawn after pupils, so they stay on top
    features = [f for f in features if f[0] != "glint"] + [f for f in features if f[0] == "glint"]
    for kind, y, x in features:
        if 0 <= y < gh and 0 <= x < gw and solid[y, x]:
            old_key = want[(y, x)]
            if old_key == ("eye", kind):
                continue
            want[(y, x)] = ("eye", kind)
            counts[("eye", kind)] = counts.get(("eye", kind), 0) + 1
            counts[old_key] -= 1
    eye.update(eye_colours)
    wanted_marks = {}
    for (y, x), kind in eyes.items():
        if kind not in eye:
            continue
        old_key = want[(y, x)]
        if old_key == ("eye", "glint"):
            continue                                             # the glint stays on top
        want[(y, x)] = ("eye", kind)
        counts[("eye", kind)] = counts.get(("eye", kind), 0) + 1
        counts[old_key] -= 1
    # an eye white on light skin (yellow, cream, pale) has a dark rim, as spriters draw it: without it
    # the white and the skin run together into one pale blob
    for (y, x), kind in eyes.items():
        if kind != "white" or not STYLE["eye_rim"]:
            continue
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if not (0 <= ny < gh and 0 <= nx < gw) or not solid[ny, nx] or (ny, nx) in eyes:
                continue
            old_key = want[(ny, nx)]
            if old_key[0] == "eye" or old_key[1] in ("line", "outline", "outline_dark") or colours[old_key[0]][0] < 150:
                continue
            want[(ny, nx)] = key = (old_key[0], "line")
            wanted.setdefault(key, tone_of(colours[key[0]], "line"))
            counts[key] = counts.get(key, 0) + 1
            counts[old_key] -= 1
    # face marks: a mark takes the nearest colour the sprite already has (a mouth is the line tone, teeth
    # the white); only a true accent - a colour far from all of them, like a pink blush - gets a palette
    # slot of its own, at most STYLE["accents"] of them (palette budgeting, as spriters do it)
    existing = dict(wanted); existing.update({("eye", k2): v for k2, v in eye.items()})
    accents = {}
    for colour in marks.values():
        if min(np.linalg.norm(v - colour) for v in existing.values()) > STYLE["accent_gap"]:
            near = next((a for a in accents if np.linalg.norm(accents[a][0] - colour) < 20), None)
            if near is None:
                accents[("mark", len(accents))] = [colour, 1]
            else:
                accents[near][1] += 1
    keep_accents = dict(sorted(accents.items(), key=lambda a: -a[1][1])[:STYLE["accents"]])
    for key, (colour, n) in keep_accents.items():
        wanted_marks[key] = colour
    pool = dict(existing); pool.update(wanted_marks)
    for (y, x), colour in marks.items():
        if want.get((y, x), ("", ""))[0] == "eye" or kinds[y, x] in ("outline", "outline_dark") and -1 in [n[y, x] for n in neighbours4(cells, -1)]:
            continue                                             # marks never replace the eyes or the outline
        key = min(pool, key=lambda kk: np.linalg.norm(pool[kk] - colour))
        if key[0] == "eye" and key[1] in ("pupil", "glint") and key not in counts:
            continue
        old_key = want[(y, x)]
        want[(y, x)] = key
        counts[key] = counts.get(key, 0) + 1
        counts[old_key] -= 1
    look_the_same_way(want, lambda key: pool.get(key, wanted.get(key)), L, k)
    wanted.update(wanted_marks)
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
        for key in list(counts):                                              # nor are the face marks
            if key[0] == "mark":
                counts[key] += 10 ** 5
        chosen = fit_palette(wanted, counts, STYLE["colours"])
        rgb_of = {key: tuple(int(v) for v in to_rgb(c)[0]) for key, c in chosen.items()}
    out = np.zeros((gh, gw, 4), np.uint8)
    for (y, x), key in want.items():
        out[y, x, :3] = rgb_of[key]
        out[y, x, 3] = 255
    return Image.fromarray(out)


def look_the_same_way(want, colour_of, L, k):
    """Both eyes look where the artwork's eyes look. Each eye is laid on the grid on its own (and its
    white and pupil come from several rules), and rounding can put a pupil on the wrong side of its
    white, so the creature squints. Run on the finished pixels: an eye is a patch of white with dark
    beside it, in the upper part. The gaze is measured in the artwork over all eyes together (where
    the dark of each eye lies against its white); an eye whose dark sits on the other side has dark
    and white swapped, row by row. A dark eye with only a glint shows no gaze and is left alone."""
    def light(key):
        c = colour_of(key)
        return c is not None and c[0] > 200 and np.hypot(c[1] - 128, c[2] - 128) < 20
    def dark(key):
        c = colour_of(key)
        return c is not None and c[0] < 70
    gh = max(y for y, _ in want) + 1
    white = {yx for yx, key in want.items() if light(key) and yx[0] < STYLE["face"] * gh and key[1] != "glint"}
    if not white:
        return
    grid = np.zeros((gh, max(x for _, x in want) + 1), np.uint8)
    for y, x in white:
        grid[y, x] = 1
    n, lbl, stats, _ = cv2.connectedComponentsWithStats(grid, connectivity=8)
    groups, gaze = [], []
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] > 16:
            continue                                  # a white belly or face, not an eye
        whites = [(int(y), int(x)) for y, x in zip(*np.nonzero(lbl == i))]
        wy, wx = zip(*whites)
        pupils = [(y, x) for y in range(min(wy), max(wy) + 1) for x in range(min(wx) - 1, max(wx) + 2)
                  if (y, x) in want and (y, x) not in white and dark(want[(y, x)])]
        if not pupils:
            continue
        ys, xs = zip(*(whites + pupils))
        art = L[min(ys) * k:(max(ys) + 1) * k, min(xs) * k:(max(xs) + 1) * k, 0]
        dark_x, light_x = np.nonzero(art < 90)[1], np.nonzero(art > 200)[1]
        if len(dark_x) and len(light_x):
            gaze.append((dark_x.mean() - light_x.mean()) / art.shape[1])
        groups.append((whites, pupils))
    if not groups or not gaze or abs(np.mean(gaze)) < 0.08:
        return                                        # looking straight ahead
    side = np.sign(np.mean(gaze))
    for whites, pupils in groups:
        if np.sign(np.mean([x for _, x in pupils]) - np.mean([x for _, x in whites])) != side:
            for y, x in pupils:
                row = sorted(xx for yy, xx in whites if yy == y)
                if row:
                    target = (y, row[-1] if side > 0 else row[0])
                    if (target[1] - x) * side > 0:
                        want[(y, x)], want[target] = want[target], want[(y, x)]


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
        image = image.crop((0, 0, image.width, round(image.height / 1.4) + 2))
    else:
        image = render(args.art, size=args.size, palette=palette)
    image.save(args.out)
    print("%s: %d x %d pixels, %d colours" % (args.out, image.width, image.height, len(palette_of(image))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


LAST = {}    # what the last drawing found (LAST["eyes"]: how many eyes)


def faces_viewer(path):
    """Whether the artwork shows the face from the front: a pair of eyes - two round dark blobs of
    about the same size, side by side at the same height in the upper half of the creature (each
    may sit in an eye white). A back view shows at most one eye in profile."""
    rgb = load(path)
    mask = mask_of(rgb)
    ys, xs = np.nonzero(mask)
    top, bottom, left, right = ys.min(), ys.max(), xs.min(), xs.max()
    H, W = bottom - top + 1, right - left + 1
    L = lab(rgb)[..., 0]
    dark = (mask & (L < 60)).astype(np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lbl, st, cent = cv2.connectedComponentsWithStats(dark, connectivity=8)
    creature = mask.sum()
    blobs = []
    for i in range(1, n):
        x0, y0, bw, bh, area = st[i]
        if not (0.0004 * creature <= area <= 0.012 * creature) or cent[i][1] > top + 0.55 * H:
            continue
        if area < 0.55 * bw * bh or max(bw, bh) > 2.6 * min(bw, bh):
            continue                                   # not round enough to be an eye (a stroke, a brow)
        blobs.append((cent[i][0], cent[i][1], area))
    for i in range(len(blobs)):
        for j in range(i + 1, len(blobs)):
            (x1, y1, a1), (x2, y2, a2) = blobs[i], blobs[j]
            if abs(y1 - y2) < 0.05 * H and 0.04 * W < abs(x1 - x2) < 0.4 * W and max(a1, a2) < 2.5 * min(a1, a2):
                return True
    return False
