"""Sprite studio v3: the worker's side of drawing TRIES (2026-10-14).

A job of mode "tries" asks for N pictures of one stage; each is registered as it starts (so the website can show it
drawing, with the time it should take), drawn, read as pixels and handed in with its time:

    art    the creature cut out of a chosen picture by base Qwen-Image 2.1 (a clean 640 drawing, see-through); or, with the
           recipe "sketch", a rough sketch redrawn as official artwork: Klein style v2 at step 2500 (trained on pairs: another
           style of a species -> its official artwork), the sketch as image 1 and as the start picture (85 % redrawn), "official pokemon artstyle. " + the dex words
    front  the DS front (80x80): front LoRA v7 600 at 0.75, cfg 2.5 + a negative prompt, 20 steps, then unfake
    back   the DS back (80x80) on the front's colours: back LoRA v6 (1800 / 2100 / 2400 in turn)
    icon   the menu icon (32x32): Klein icon v1 at step 2500 (frame 1 of its two), in Klein's own colours
    follower  the overworld walking sheet (128x64: up, down, left, right x 2 steps): Klein follower v3 at step 2000, from
           the picked front and back, halfway to the front's colours
    back   the DS back (80x80): Klein back v2 at step 2500, image 3 = the art drawn from behind first (base Qwen), in its
           own colours (the shared game palette is made at export)

Klein = FLUX.2 Klein base 4B with our LoRAs (docs/LORAS.md: "Follower, thought again", "Icon on Klein", "Back on Klein"),
drawn as ai-toolkit trained and sampled them (comfy.klein). Their text is the training captions' text: the dex words plus,
from the website, the body shape, its look and how it moves (job["prompt"], JSON).

The recipes are the ones tested in docs/LORAS.md (the whole-pipeline test of 14 Oct, the icon workshops). The LoRA files
are only on the drawing PC (they were trained on game sprites and never go in the repository); their names are below.
The machine only marks plainly broken pictures (empty, loose bits, a drawn frame, too many colours); people pick.
"""
import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import comfy
import dexlib
import ds_pixel
import klein_follower
import pixel_render
import sprite_colours

FRONT_LORA, FRONT_STRENGTH, FRONT_CFG = "fv7_600.safetensors", 0.75, 2.5
BACK_LORAS = ["bv6_1800.safetensors", "bv6_2100.safetensors", "bv6_2400.safetensors"]
ICON_LORA = "pkmn_icon_edit_v2.safetensors"
UNFAKE = os.environ.get("UNFAKE_EXE", r"D:\LocalAI\tools\pxvenv\Scripts\unfake.exe")
TIMINGS = Path(os.environ.get("SIGMA_TIMINGS_FILE", dexlib.ROOT / ".studio-timings.json"))
# Klein LoRAs approved by Arvind (15 Oct): follower v3 step 2000, icon v1 step 2500, back v2 step 2500 ("ja ta 2500 du";
# sha256 C8BC5E05...2B128DB5). In ComfyUI\models\loras\ on the drawing PC only.
FOLLOWER_KLEIN = "pkmn_follower_klein_v3_000002000.safetensors"
ICON_KLEIN = "pkmn_icon_klein_v1_000002500.safetensors"
BACK_KLEIN = "pkmn_back_klein_v2_000002500.safetensors"
# Sketch -> official artwork (16-17 Oct, Arvind on the step sweep: "a lot usable here, 2500 maybe best"; sha256 DBF17D1E...CE912609).
SKETCH_KLEIN = "pkmn_style_klein_v2_000002500.safetensors"
SKETCH_REDRAW = 0.85
# "NEW POSE" (17 Oct, Arvind: "can it make a pose that does not copy the sketch, but keeps the design?"): style v2 copies
# image 1's pose, so base Qwen-Image 2.1 turns the creature first and style v2 puts the official look back on.
POSES = ["in a new dynamic action pose (not the pose of <image1>): moving, leaning forward, limbs in different positions",
         "turned the other way: a three-quarter view facing the other side, in a relaxed new pose",
         "in a new lively pose (not the pose of <image1>), as if about to jump or attack"]
DEFAULT_SECONDS = {"art": 75, "art:sketch": 25, "art:pose": 60, "front": 100, "back": 55, "icon:pc": 8, "icon:canvas": 8, "icon": 30, "follower": 40, "back:klein": 30, "front2": 60, "back2": 60,
                   "rear": 70}   # measured on the Legion, 14 Oct (the Klein ones: a first guess until measured)
LINE = (175, 175, 175, 255)

ART = ("<image1> is a picture of a creature: a drawing, a character sheet with text and several views, or a scene. Draw the "
       "same creature alone, as in its MAIN picture (the biggest one, the creature facing forward or in a three-quarter view), not "
       "the small side, back or close-up views, with exactly the same design, pose, colours, proportions and drawing style; its "
       "whole body. Nothing else: no text, no labels, no badges, no other views, no other creatures, no background.")
FRONT = ("<image1> is its official artwork. <image2> is empty. <image3> is the template, only a guide that is never drawn: a box "
         "showing about where and how big this creature's front sprite is. {tags}Draw it as its own front battle sprite from "
         "Pokemon HeartGold (Gen 4): 80x80 pixel art in the games' three-quarter view, big flat areas with two or three tones per "
         "colour, dark interior lines between parts, a one-pixel dark outline, few detail pixels, the same design and colors, on "
         "a transparent background.")
NEGATIVE = ("blurry, smooth gradients, anti-aliasing, soft painterly shading, too many colours, noise, stray pixels, two creatures, "
            "background, text, frame")
BACK = ("<image1> is the Pokemon's front battle sprite. <image2> is a reference sheet of the same Pokemon: its official artwork "
        "(right). <image3> is the template, only a guide that is never drawn: a box showing about where and how big its back "
        "sprite is, the heavier bottom line where it is cut off flat. {tags}Draw its back sprite from Pokemon HeartGold: the "
        "same creature seen from behind as the player's own Pokemon, over its shoulder, big and cut off flat by the bottom edge, "
        "80x80 pixel art with the same colors, a one-pixel dark outline, on a transparent background.")
ICON = ("Turn the Pokemon battle sprite in the reference image into its party menu icon from Pokemon HeartGold: the same creature "
        "as a 32x32 pixel art icon, facing left, with a one-pixel dark grey outline, on a white background.")
# Klein: the texts the LoRAs were trained with (build_follower_klein_v3.py, build_icon_klein.py, build_back_klein_v2.py on the PC)
SHEET_K = ("Create the overworld walking sprite sheet from Pokemon HeartGold of the Pokemon in image 1 and image 2: image 1 is its "
           "front battle sprite, image 2 is its back battle sprite. {about}The sheet is a grid of 2 rows by 4 columns of 32x32 pixel "
           "art frames on a flat magenta background: the columns walk up (seen from behind, as in image 2), down (facing the viewer, "
           "as in image 1), left and right; the top row is the first step and the bottom row the second step. The same creature in "
           "every frame, with the colours of image 1 and image 2 and a one-pixel dark outline.")
ICON_K = ("Create the party menu icon from Pokemon HeartGold of the Pokemon in image 1: image 1 is its front battle sprite. {about}"
          "The picture shows the icon's two animation frames side by side, each a 32x32 pixel art frame on a flat magenta "
          "background: the same small creature in both, as in image 1 but simpler, with the icon's few colours and a one-pixel "
          "dark outline; in the second frame it moves a little.")
BACK_K = ("Create the back battle sprite from Pokemon HeartGold of the Pokemon in image 1, image 2 and image 3: image 1 is its front "
          "battle sprite, image 2 is its official artwork, for its design, {hint}{about}The picture is its 80x80 pixel art back "
          "sprite on a flat magenta background: the same creature seen from behind, as the player's Pokemon in battle, big and low "
          "in the frame and cut off by the bottom edge, with the colours of image 1 and a one-pixel dark outline.")
BACK_HINT = "image 3 shows what its back looks like, only for what is on its back (shapes, markings, colours), not for its style or pose. "
REAR = ("<image1> is the official artwork of a creature. Draw the same creature seen from behind, as in a Pokemon's back view in "
        "battle: the camera is behind it and a little above, so we see its back, the back of its head and its tail, and its face is "
        "turned away and hidden. Exactly the same design, colours, proportions and drawing style as the artwork. Nothing else: no "
        "background, no text.")


def about(job, words, move=True):
    """The dex words, then what the website sends about its body (JSON {shape, look, move}), as in the training captions."""
    try:
        body = json.loads(job.get("prompt") or "{}")
    except ValueError:
        body = {"look": job.get("prompt")}
    body = body if isinstance(body, dict) else {}
    s = words
    if body.get("shape"):
        s += "Its body shape: %s. " % str(body["shape"]).strip().rstrip(".")
    if body.get("look"):
        s += "Its look: %s " % str(body["look"]).strip()
    if move and body.get("move"):
        s += "How it moves: %s " % str(body["move"]).strip()
    if body.get("note"):                                         # the person's own words about a sketch's design
        s += "Its design: %s " % str(body["note"]).strip()
    return s


# where and how big the back sprite is, from the front's height and width (fitted on the real HGSS backs: back v6's box)
BACK_BOX = {"h": [0.6691373462851647, -0.1684466714078896, 34.8848780435225], "w": [-0.06479605707673408, 0.502819395442454, 45.97516911549472],
            "cx": [-0.0061761081279599166, 0.007810089409133081, 39.27945672744823], "bottom": [0.2051063369118864, -0.0403249530318881, 64.6804013672584]}


# ---------- the Pokemon's words (as the LoRAs were trained: type, stage, height)
def tags(species_id):
    species = {sid: d for sid, _, d in dexlib.load_species()[0]}
    data = species.get(species_id) or {}
    evolves = bool(data.get("evolutions"))
    prevo = any(isinstance(e, dict) and e.get("into") == species_id for d in species.values() for e in (d.get("evolutions") or []))
    stage = ("a Pokemon that does not evolve" if not evolves and not prevo else "a first-stage Pokemon that evolves" if not prevo
             else "a middle evolution" if evolves else "a fully evolved Pokemon")
    parts = []
    if data.get("types"):
        parts.append("a %s-type Pokemon" % "/".join(data["types"]))
    parts.append(stage)
    if data.get("height_m"):
        parts.append("%g m tall" % data["height_m"])
    side = {"a first-stage Pokemon that evolves": 64, "a middle evolution": 74, "a fully evolved Pokemon": 78}.get(stage, 72)
    return "It is " + ", ".join(parts) + ". ", side


# ---------- pictures
def framed(im, side=640, inner=560):
    """The creature cropped and fitted in a see-through square, as the LoRAs' artwork was."""
    im = im.convert("RGBA").crop(im.convert("RGBA").getbbox())
    s = inner / max(im.size)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    out = Image.new("RGBA", (side, side), (255, 255, 255, 0))
    out.alpha_composite(im, ((side - im.width) // 2, (side - im.height) // 2))
    return out


def solid(im, cut=48):
    """Fully opaque wherever the picture has the creature at all (alpha >= cut), clear elsewhere. Qwen's cut-outs and the
    Klein drawings come back partly see-through (24 Oct and again 8 Nov, Heatbat 6-16 % of the figure), and on white
    those parts turn pale. Only for the art step's own pictures (8 Nov: the front step stays as before 24 Oct)."""
    a = np.array(im.convert("RGBA")); al = a[..., 3].astype(int); rgb = a[..., :3].astype(int)
    sat = rgb.max(-1) - rgb.min(-1); luma = rgb @ np.array([30, 59, 11]) // 100
    shadow = (al < 160) & (sat < 40) & (luma < 140)               # a soft grey ground shadow is not the creature
    a[..., 3] = np.where((al >= 160) | ((al >= cut) & ~shadow), 255, 0).astype(np.uint8)
    return Image.fromarray(a)


def defringe(im, level=215, band=14):
    """Clear the white rim a cut-out keeps around the creature: near-white pixels reached from the see-through background
    through near-white pixels only, at most `band` px deep (the dark outline stops it; white parts inside it stay)."""
    import cv2
    a = np.array(im.convert("RGBA"))
    rgb = a[..., :3].astype(int)
    white = ((rgb.min(-1) >= level) & (rgb.max(-1) - rgb.min(-1) < 30) & (a[..., 3] >= 16)).astype(np.uint8)
    reach = (a[..., 3] < 16).astype(np.uint8)
    k = np.ones((3, 3), np.uint8)
    rim = np.zeros_like(white)
    for _ in range(band):
        grow = cv2.dilate(reach | rim, k) & white
        if (grow == rim).all():
            break
        rim = grow
    a[rim > 0, 3] = 0
    return Image.fromarray(a)


def keep_creature(im, near=0.06, touch=0.015, small=0.10, extra=0.30):
    """The creature: its biggest connected part plus loose parts drawn apart from it - small ones (each at most 10 % of
    the body: flames, sparks) up to 6 % of its size away, any size when they almost touch it (a fist, a wing) - but not
    far or big pieces (text, other views, a second creature); with more than 6 or over 35 % extra it counts as a sheet. Returns the picture and the share of everything drawn kept."""
    import cv2
    a = np.array(im.convert("RGBA"))
    m = (a[..., 3] >= 16).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n < 2:
        return Image.fromarray(a), 0.0
    main = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    body = float(st[main, cv2.CC_STAT_AREA])
    diag = float(np.hypot(st[main, 2], st[main, 3]))
    keep = lab == main
    added, parts = 0.0, 0
    for _ in range(2):                                   # parts near the body, then parts near those
        dist = cv2.distanceTransform((~keep).astype(np.uint8), cv2.DIST_L2, 3)
        for i in range(1, n):
            area = float(st[i, cv2.CC_STAT_AREA])
            part = lab == i
            if i == main or keep[part].any() or area < 0.002 * body:
                continue
            d = dist[part].min()
            if d <= max(6.0, touch * diag) or (area <= small * body and d <= max(24.0, near * diag) and added + area <= extra * body):
                keep |= part
                added += area
                parts += 1
    share = keep.sum() / max(1, m.sum())
    if parts > 6 or added > 0.35 * body:                # many or big pieces: a card or a sheet, not one creature
        share = body / max(1, m.sum())
    a[~keep, 3] = 0
    return Image.fromarray(a), float(share)


def largest_blob(im):
    """The biggest connected part (a cut-out sometimes keeps bits of text or other views) and its share."""
    import cv2
    a = np.array(im.convert("RGBA"))
    m = (a[..., 3] >= 16).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n < 2:
        return Image.fromarray(a), 0.0
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    share = st[k, cv2.CC_STAT_AREA] / max(1, m.sum())
    a[lab != k, 3] = 0
    return Image.fromarray(a), float(share)


def box_template(box, k=16, cut=False):
    t = Image.new("RGBA", (80 * k, 80 * k), (255, 255, 255, 0))
    d = ImageDraw.Draw(t)
    x0, y0, x1, y1 = box
    d.rectangle([x0 * k, y0 * k, x1 * k + k - 1, y1 * k + k - 1], outline=LINE, width=4 if not cut else 3 * k // 8)
    if cut:                                                       # the back's flat cut, drawn heavier
        d.line([x0 * k, y1 * k + k - 1, x1 * k + k - 1, y1 * k + k - 1], fill=LINE, width=7 * k // 8)
    a = np.array(t)
    a[a[..., 3] == 0, :3] = 255
    return Image.fromarray(a)


def front_box(side, art):
    b = art.getbbox()
    aspect = (b[2] - b[0]) / max(1, b[3] - b[1])
    w, h = (side, max(4, round(side / aspect))) if aspect >= 1 else (max(4, round(side * aspect)), side)
    w, h = min(w, 80), min(h, 80)
    bottom = min(79, max(h - 1, round(0.491 * h + 39.6)))
    x0 = min(max(0, round(39.5 - (w - 1) / 2)), 80 - w)
    return (x0, bottom - h + 1, x0 + w - 1, bottom)


def back_box(front):
    b = front.getbbox()
    fh, fw = b[3] - b[1], b[2] - b[0]
    f = lambda k: BACK_BOX[k][0] * fh + BACK_BOX[k][1] * fw + BACK_BOX[k][2]
    h, w, cx, bot = round(f("h")), round(f("w")), f("cx"), round(f("bottom"))
    x0 = round(cx - (w - 1) / 2)
    return (max(0, x0), max(0, bot - h + 1), min(79, x0 + w - 1), min(79, bot))


def on_clear(im, scale):
    big = im.convert("RGBA").resize((im.width * scale, im.height * scale), Image.NEAREST)
    a = np.array(big)
    a[a[..., 3] == 0, :3] = 255
    return Image.fromarray(a)


def cells(path, cell, w, h):
    """A drawing at `cell` pixels per sprite pixel read as w x h sprite pixels (the middle of each cell; white = see-through)."""
    a = np.array(Image.open(path).convert("RGBA"))[cell // 2::cell, cell // 2::cell][:h, :w].copy()
    white = a[..., :3].min(-1) > 240
    a[..., 3] = np.where((a[..., 3] >= 128) & ~white, 255, 0)
    a[a[..., 3] == 0] = 0
    return Image.fromarray(a)


def cells_median(path, n=32):
    """The PC box reading of icon_edit_v2's picture (legion_test/run.py): the median of the middle 40 % of each cell."""
    a = np.array(Image.open(path).convert("RGB")).astype(np.float32)
    c = a.shape[0] / n
    out = np.zeros((n, n, 4), np.uint8)
    for y in range(n):
        for x in range(n):
            blk = a[int(y * c + c * 0.3):int(y * c + c * 0.7) + 1, int(x * c + c * 0.3):int(x * c + c * 0.7) + 1].reshape(-1, 3)
            m = np.median(blk, axis=0)
            if m.min() < 238:
                out[y, x, :3], out[y, x, 3] = m, 255
    return Image.fromarray(out)


def unfake(path, out):
    """unfake (the pixel-art reader) on the front LoRA's 1280 picture -> 80x80; the cell middles when it is not installed.
    At most 15 colours, as a DS sprite (2026-10-15): --auto-colors gave dark designs 3-4 colours (Obsidog lost its eyes'
    shine, the horns' highlights and the body's shading); real HeartGold fronts have 13 (median), and the front's palette
    is the one the back and the follower take their colours from."""
    if Path(UNFAKE).exists() and not out.exists():
        subprocess.run([UNFAKE, str(path), "-o", str(out), "-s", "16", "-m", "dominant", "-c", "15", "--cleanup", "morph,jaggy"], capture_output=True)
    if not out.exists():
        return pixel_render.drop_specks(cells(path, 16, 80, 80))
    a = np.array(Image.open(out).convert("RGBA"))
    c = np.zeros((80, 80, 4), np.uint8)
    h, w = min(80, a.shape[0]), min(80, a.shape[1])
    c[:h, :w] = a[:h, :w]
    c[..., 3] = np.where(c[..., 3] >= 128, 255, 0)
    c[c[..., 3] == 0] = 0
    return pixel_render.drop_specks(Image.fromarray(c))


def thin_outline(sprite):
    """The outline after unfake is often two pixels and pure black; real fronts have one pixel, mostly a dark shade of the
    colour inside (docs/LORAS.md, outline): the second layer takes the colour inside it, the edge a dark shade of its hue."""
    import colorsys
    a = np.array(sprite.convert("RGBA")).copy()
    m = a[..., 3] > 0
    lum = lambda rgb: 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    dark = m & (lum(a[..., :3].astype(float)) < 60)
    H, W = m.shape
    inside = lambda y, x: 0 <= y < H and 0 <= x < W
    edge = np.zeros_like(m)
    for y, x in zip(*np.nonzero(m)):
        if any(not inside(y + dy, x + dx) or not m[y + dy, x + dx] for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))):
            edge[y, x] = True
    n8 = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    out = a.copy()
    for y, x in zip(*np.nonzero(dark & ~edge)):
        if not any(inside(y + dy, x + dx) and edge[y + dy, x + dx] and dark[y + dy, x + dx] for dy, dx in n8[:4]):
            continue
        inner = [tuple(a[y + dy, x + dx, :3]) for dy, dx in n8 if inside(y + dy, x + dx) and m[y + dy, x + dx] and not edge[y + dy, x + dx] and not dark[y + dy, x + dx]]
        if inner:
            out[y, x, :3] = max(set(inner), key=inner.count)
    pal = np.unique(out[m][:, :3], axis=0)
    hsv = np.array([colorsys.rgb_to_hsv(*(c / 255.0)) for c in pal])
    final = out.copy()
    for y, x in zip(*np.nonzero(dark & edge)):
        inner = [tuple(out[y + dy, x + dx, :3]) for dy, dx in n8 if inside(y + dy, x + dx) and m[y + dy, x + dx] and lum(np.array(out[y + dy, x + dx, :3], float)) >= 60]
        if not inner:
            continue
        h, _, _ = colorsys.rgb_to_hsv(*(np.array(max(set(inner), key=inner.count)) / 255.0))
        cand = [(hv[2], p) for hv, p in zip(hsv, pal) if hv[2] < 0.36 and hv[1] > 0.25 and min(abs(hv[0] - h), 1 - abs(hv[0] - h)) < 0.06]
        if cand:
            final[y, x, :3] = min(cand, key=lambda t: t[0])[1]
    return Image.fromarray(final)


def broken(sprite, box=None):
    """Why a picture is plainly broken ('' when it is not): empty, too small for its box, loose bits, a drawn frame,
    too many colours. Only these; which good one is best is for people to say (the pickers missed every time)."""
    import cv2
    a = np.array(sprite.convert("RGBA"))
    m = (a[..., 3] > 0).astype(np.uint8)
    if m.sum() < 12:
        return "empty"
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    loose = 1 - st[1:, cv2.CC_STAT_AREA].max() / m.sum()
    ys, xs = np.nonzero(m)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
    why = []
    if box is not None:
        bx0, by0, bx1, by1 = box
        if (x1 - x0 + 1) * (y1 - y0 + 1) / ((bx1 - bx0 + 1) * (by1 - by0 + 1)) < 0.5:
            why.append("too small")
    if loose > 0.06:
        why.append("loose bits")
    sides = [m[y0, x0:x1 + 1].mean(), m[y1, x0:x1 + 1].mean(), m[y0:y1 + 1, x0].mean(), m[y0:y1 + 1, x1].mean()]
    if sum(s > 0.85 for s in sides) >= 3 and box is not None:
        why.append("a drawn frame")
    if len(np.unique(a[m > 0][:, :3], axis=0)) > 24:
        why.append("too many colours")
    return ", ".join(why)


# ---------- the graphs
uploaded = {}


def up(path):
    path = str(path)
    if path not in uploaded:
        uploaded[path] = comfy.upload(path)
    return uploaded[path]


def with_refs(graph, refs):
    """References as RGBA (LoadImage + JoinImageWithAlpha), as the LoRAs were trained on see-through pictures."""
    for k, p in enumerate(refs, 1):
        graph["r%d" % k] = {"class_type": "LoadImage", "inputs": {"image": up(p)}}
        graph["j%d" % k] = {"class_type": "JoinImageWithAlpha", "inputs": {"image": ["r%d" % k, 0], "alpha": ["r%d" % k, 1]}}
        graph["text"]["inputs"]["images.image_%d" % k] = ["j%d" % k, 0]
    return graph


def draw(out, graph):
    out = Path(out)
    if not out.exists():
        out.write_bytes(comfy.run(graph))
    return out


# ---------- the stages: each returns (status, note, image path, raw path)
def white_out(im, level=236):
    """a drawing on white -> see-through: the near-white area that touches the edge goes"""
    import cv2
    a = np.array(im.convert("RGBA"))
    white = (a[..., :3].min(axis=2) >= level).astype(np.uint8)
    n, lab = cv2.connectedComponents(white, connectivity=4)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    clear = np.isin(lab, list(edge)) & (white > 0)
    alpha = np.where(clear, 0, 255).astype(np.uint8)
    a[..., 3] = cv2.GaussianBlur(alpha, (3, 3), 0)
    return Image.fromarray(a)


def try_art_sketch(n, seed, folder, job, inputs):
    """a rough sketch -> official artwork (Klein style v2), then cut from its white background"""
    sketch = folder / "sketch_in.png"
    if not sketch.exists():
        fit_white(Image.open(inputs["refs"][0]), 512, 482).save(sketch)
    words = sketch_words(job, inputs)
    # The sketch is image 1 AND the start picture, 85 % redrawn: a little closer to the sketch (where the arm, the marks
    # are) than image 1 alone (Arvind, 17 Oct: "push it a tiny bit more towards the original sketch"; sketch_closer2.py).
    raw = folder / ("art_raw_%d.png" % n)
    if not raw.exists():
        graph = comfy.klein("official pokemon artstyle. " + words, [up(sketch)], 512, 512, seed, "sigma/studio_sketch", SKETCH_KLEIN)
        graph["split"] = {"class_type": "SplitSigmasDenoise", "inputs": {"sigmas": ["sched", 0], "denoise": SKETCH_REDRAW}}
        graph["sca"]["inputs"]["sigmas"] = ["split", 1]
        graph["sca"]["inputs"]["latent_image"] = ["enc1", 0]
        raw.write_bytes(comfy.run(graph))
    im, share = keep_creature(solid(defringe(white_out(Image.open(raw)))))
    image = folder / ("art_%d.png" % n)
    framed(im).save(image)
    return ("broken", "loose bits (%.0f %% outside the creature)" % (100 - 100 * share), image, raw) if share < 0.9 else ("done", "", image, raw)


def sketch_words(job, inputs):
    """the dex words + body shape + look (+ the person's own words about the design), as style v2's captions"""
    try:
        body = json.loads(job.get("prompt") or "{}")
    except ValueError:
        body = {}
    body = body if isinstance(body, dict) else {}
    note = str(body.pop("note", "") or "").strip()
    words = about(dict(job, prompt=json.dumps(body)), inputs["tags"][0], move=False)
    if "Its look" not in words:                                  # nothing sent from the website: the dex's own words
        species = {sid: d for sid, _, d in dexlib.load_species()[0]}
        design = (species.get(job["species_id"]) or {}).get("design") or {}
        if design.get("body_shape"):
            words += "Its body shape: %s. " % str(design["body_shape"]).strip().rstrip(".")
        words += str(design.get("look") or "") + " "
    if note:                                                     # the person's own words last, so they can correct the look
        words += "Its design: %s" % note
    return words.strip()


def try_art_pose(n, seed, folder, job, inputs):
    """the picked drawing in a new pose: base Qwen turns it, style v2 (image 1 only) gives it the official look again"""
    clean = folder / "pose_in.png"
    if not clean.exists():
        fit_white(inputs["art"], 1024, 940).save(clean)
    words = sketch_words(job, inputs)
    turned = folder / ("pose_qwen_%d.png" % n)
    if not turned.exists():
        comfy.generate("The same creature as in <image1>, with exactly the same design, body parts, markings and colours, %s. Official "
                       "Pokemon artwork, its whole body, white background. %s" % (POSES[(n - 1) % len(POSES)], words),
                       turned, [clean], size=(1024, 1024), steps=30, seed=seed, quiet=True)
    small = folder / ("pose_small_%d.png" % n)
    Image.open(turned).convert("RGB").resize((512, 512), Image.LANCZOS).save(small)
    raw = klein_draw(folder / ("art_raw_%d.png" % n), "official pokemon artstyle. " + words, [small], 512, 512, seed, SKETCH_KLEIN)
    im, share = keep_creature(solid(defringe(white_out(Image.open(raw)))))
    image = folder / ("art_%d.png" % n)
    framed(im).save(image)
    return ("broken", "loose bits (%.0f %% outside the creature)" % (100 - 100 * share), image, raw) if share < 0.9 else ("done", "", image, raw)


def try_art(n, seed, folder, job, inputs):
    if job.get("recipe") == "sketch":
        return try_art_sketch(n, seed, folder, job, inputs)
    if job.get("recipe") == "pose":
        return try_art_pose(n, seed, folder, job, inputs)
    raw = folder / ("art_raw_%d.png" % n)
    prompt = ART + ((" " + job["prompt"]) if job.get("prompt") else "")
    comfy.generate(prompt, raw, inputs["refs"][:3], size=(1024, 1024), steps=40, seed=seed, quiet=True, transparent=True)
    im, share = keep_creature(solid(defringe(Image.open(raw))))
    image = folder / ("art_%d.png" % n)
    framed(im).save(image)
    return ("broken", "loose bits (%.0f %% outside the creature)" % (100 - 100 * share), image, raw) if share < 0.9 else ("done", "", image, raw)


def try_front(n, seed, folder, job, inputs):
    art = inputs["art"]
    words, side = inputs["tags"]
    shrink = inputs.get("shrink") or 1.0                          # a redraw after the edge check: a smaller box
    box = front_box(max(8, round(side * shrink)), art)
    template = folder / ("front_template.png" if shrink == 1.0 else "front_template_%g.png" % shrink)
    if not template.exists():
        box_template(box).save(template)
        Image.new("RGBA", (640, 640), (255, 255, 255, 0)).save(folder / "blank.png")
    graph = comfy.workflow(FRONT.format(tags=words) + ((" " + job["prompt"]) if job.get("prompt") else ""), [], 1280, 1280, 20, seed,
                           "sigma/studio_front", FRONT_LORA, FRONT_STRENGTH, 0)
    graph["sampler"]["inputs"]["cfg"] = FRONT_CFG
    graph["text"]["inputs"]["negative_prompt"] = NEGATIVE
    raw = draw(folder / ("front_raw_%d.png" % n), with_refs(graph, [inputs["art_path"], folder / "blank.png", template]))
    sprite = unfake(raw, folder / ("front_unfake_%d.png" % n))
    why = broken(sprite, box)
    sprite = ds_pixel.limit_colours(thin_outline(sprite), 15)
    image = folder / ("front_%d.png" % n)
    sprite.save(image)
    return ("broken" if why else "done", why, image, raw)


def try_back(n, seed, folder, job, inputs):
    front = inputs["front"]
    words, _ = inputs["tags"]
    box = back_box(front)
    if not (folder / "back_template.png").exists():
        box_template(box, cut=True).save(folder / "back_template.png")
        on_clear(front, 8).save(folder / "back_front8.png")
        sheet = Image.new("RGBA", (1024, 512), (255, 255, 255, 0))
        if inputs.get("art") is not None:
            art = inputs["art"].convert("RGBA").crop(inputs["art"].convert("RGBA").getbbox())
            s = min(496 / art.width, 496 / art.height)
            art = art.resize((max(1, round(art.width * s)), max(1, round(art.height * s))), Image.LANCZOS)
            sheet.alpha_composite(art, (512 + (512 - art.width) // 2, (512 - art.height) // 2))
        a = np.array(sheet)
        a[a[..., 3] == 0, :3] = 255
        Image.fromarray(a).save(folder / "back_sheet.png")
    lora = BACK_LORAS[(n - 1) % len(BACK_LORAS)]
    graph = comfy.workflow(BACK.format(tags=words) + ((" " + job["prompt"]) if job.get("prompt") else ""), [], 1280, 1280, 25, seed,
                           "sigma/studio_back", lora, 1.0, 0)
    raw = draw(folder / ("back_raw_%d.png" % n), with_refs(graph, [folder / "back_front8.png", folder / "back_sheet.png", folder / "back_template.png"]))
    sprite = pixel_render.drop_specks(ds_pixel.to_palette(cells(raw, 16, 80, 80), pixel_render.palette_of(front)))
    why = broken(sprite)
    image = folder / ("back_%d.png" % n)
    sprite.save(image)
    return ("broken" if why else "done", why, image, raw)


def icon_start(front):
    """The canvas swap's start picture: the front shrunk as big as the real icons' rule says (fill = 0.15 + 0.49 x the front's
    fill), feet on row 29, 16x on white (docs/LORAS.md, icon workshop 2)."""
    fill = (np.array(front)[..., 3] > 0).mean()
    want = 0.15 + 0.49 * fill
    g = front.crop(front.getbbox())
    area = (np.array(g)[..., 3] > 0).sum()
    s = min((want * 1024 / max(1, area)) ** 0.5, 32 / g.width, 30 / g.height)
    g = g.resize((max(1, round(g.width * s)), max(1, round(g.height * s))), Image.LANCZOS)
    b = np.array(g)
    b[..., 3] = np.where(b[..., 3] >= 100, 255, 0)
    c = Image.new("RGBA", (32, 32))
    c.alpha_composite(Image.fromarray(b), ((32 - g.width) // 2, 30 - g.height))
    w = Image.new("RGB", (32, 32), "white")
    w.paste(c, (0, 0), c)
    return w.resize((512, 512), Image.NEAREST)


def try_icon(n, seed, folder, job, inputs):
    front = inputs["front"]
    ref = folder / "icon_front640.png"
    if not ref.exists():
        w = Image.new("RGB", front.size, "white")
        w.paste(front, (0, 0), front)
        w.resize((640, 640), Image.NEAREST).save(ref)
        icon_start(front).save(folder / "icon_start.png")
    recipe = icon_recipe(job, n)
    graph = comfy.workflow(ICON + ((" " + job["prompt"]) if job.get("prompt") else ""), [up(ref)], 512, 512, 25, seed, "sigma/studio_icon", ICON_LORA, 1.0)
    if recipe == "canvas":
        graph["st"] = {"class_type": "LoadImage", "inputs": {"image": up(folder / "icon_start.png")}}
        graph["enc"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["st", 0], "vae": ["vae", 0]}}
        graph["sampler"]["inputs"]["latent_image"] = ["enc", 0]
        graph["sampler"]["inputs"]["denoise"] = 0.8
    raw = draw(folder / ("icon_raw_%d.png" % n), graph)
    sprite = ds_pixel.limit_colours(pixel_render.drop_specks(cells_median(raw)), 15)    # an icon has one 15-colour palette
    why = broken(sprite)
    image = folder / ("icon_%d.png" % n)
    sprite.save(image)
    return ("broken" if why else "done", why, image, raw)


def on_white(im, scale=4):
    """a sprite (see-through) on white, `scale`x nearest: the LoRAs' image 1 / image 2"""
    w = Image.new("RGB", im.size, "white")
    w.paste(im, (0, 0), im)
    return w.resize((im.width * scale, im.height * scale), Image.NEAREST)


def fit_white(im, side=320, inner=300, smooth=False):
    """a drawing fitted in `inner` px on a white square: the back LoRA's image 2 (the art) and image 3 (smoothed: the back)"""
    im = im.convert("RGBA")
    box = im.getbbox()
    if box:
        im = im.crop(box)
    s = inner / max(im.size)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.BICUBIC if smooth else Image.LANCZOS)
    if smooth:
        from PIL import ImageFilter
        im = im.filter(ImageFilter.GaussianBlur(1.2))
    w = Image.new("RGBA", (side, side), (255, 255, 255, 255))
    w.alpha_composite(im, ((side - im.width) // 2, (side - im.height) // 2))
    return w.convert("RGB")


def klein_draw(out, prompt, refs, width, height, seed, lora):
    out = Path(out)
    if not out.exists():
        out.write_bytes(comfy.run(comfy.klein(prompt, [up(r) for r in refs], width, height, seed, "sigma/studio_klein", lora)))
    return out


def too_small(sprite, least=40):
    a = np.array(sprite.convert("RGBA"))
    return "nothing drawn" if (a[..., 3] > 0).sum() < least else ""


def try_follower(n, seed, folder, job, inputs):
    words, _ = inputs["tags"]
    if not (folder / "k_front.png").exists():
        on_white(inputs["front"]).save(folder / "k_front.png")
    if not (folder / "k_back.png").exists():
        on_white(inputs["back"]).save(folder / "k_back.png")
    raw = klein_draw(folder / ("follower_raw_%d.png" % n), SHEET_K.format(about=about(job, words)),
                     [folder / "k_front.png", folder / "k_back.png"], 512, 256, seed, FOLLOWER_KLEIN)
    sheet = sprite_colours.follower_colours(klein_follower.to_game(raw), inputs["front"])
    sheet = klein_follower.merge_alike(sheet.convert("RGBA"), 15)
    why = too_small(sheet, 120)
    image = folder / ("follower_%d.png" % n)
    sheet.save(image)
    return ("broken" if why else "done", why, image, raw)


def try_icon_klein(n, seed, folder, job, inputs):
    words, _ = inputs["tags"]
    if not (folder / "k_front.png").exists():
        on_white(inputs["front"]).save(folder / "k_front.png")
    raw = klein_draw(folder / ("icon_raw_%d.png" % n), ICON_K.format(about=about(job, words, move=False)),
                     [folder / "k_front.png"], 512, 256, seed, ICON_KLEIN)
    # frame 1 (the game's second frame is made from it), straight into the game's icon palette (2026-11-23, Arvind: "det
    # beste er om det blir automatisk"): sprite_colours.icon_colours picks the palette where it survives best and keeps the
    # neighbour contrast (the 15 Oct nearest-colour snap made icons bluer or olive; this one was tested on HeartGold's icons)
    frame = klein_follower.to_icon(raw).crop((0, 0, 32, 32))
    why = too_small(frame, 30)
    frame, pal = sprite_colours.icon_colours(frame, sprite_colours.HG_ICON_PALETTES, inputs.get("body_color"), inputs.get("front"))
    image = folder / ("icon_%d.png" % n)
    frame.save(image)
    return ("broken" if why else "done", why or "in the game's icon palette %d" % (pal + 1), image, raw)


def rear_drawing(folder, art_path, seed):
    """base Qwen draws the art seen from behind (back_rear_test.py): what is on the back, for the back LoRA's image 3"""
    out = folder / "rear.png"
    if not out.exists():
        raw = folder / "rear_raw.png"
        comfy.generate(REAR, raw, [art_path], size=(1024, 1024), steps=40, seed=seed, quiet=True, transparent=True)
        im, _ = largest_blob(Image.open(raw))
        im.save(out)
    return Image.open(out)


def try_back_klein(n, seed, folder, job, inputs):
    words, _ = inputs["tags"]
    front = inputs["front"]
    if not (folder / "k_front.png").exists():
        on_white(front).save(folder / "k_front.png")
        art = inputs.get("art")
        if art is None:                     # a mirrored or drawn front with no picture chosen: the front stands in for the art
            art = front
        framed(art).save(folder / "k_art640.png")
        fit_white(art).save(folder / "k_art.png")
        if inputs.get("back_ref") is not None:   # a back to keep the look of (2026-11-25: the cut backs redrawn; their sticking-out
            on_white(inputs["back_ref"]).save(folder / "k_hint.png")      # parts must stay): image 3 = that back, not a drawing from behind
        else:
            fit_white(rear_drawing(folder, folder / "k_art640.png", job["id"] * 100), smooth=True).save(folder / "k_hint.png")
    shrink = inputs.get("shrink") or 1.0
    kfront, text = folder / "k_front.png", BACK_K.format(hint=BACK_HINT, about=about(job, words, move=False))
    if shrink != 1.0:                    # a redraw after the edge check: a smaller front as image 1 and "not so big" words
        kfront = folder / ("k_front_%g.png" % shrink)
        small = front.resize((max(1, round(front.width * shrink)), max(1, round(front.height * shrink))), Image.NEAREST)
        pad = Image.new("RGBA", front.size, (0, 0, 0, 0)); pad.alpha_composite(small, ((front.width - small.width) // 2, front.height - small.height))
        on_white(pad).save(kfront)
        text = text.replace("big and low in the frame", "low in the frame, with a few pixels free at the top and both sides")
    raw = klein_draw(folder / ("back_raw_%d.png" % n), text, [kfront, folder / "k_art.png", folder / "k_hint.png"], 320, 320, seed, BACK_KLEIN)
    # Klein's own colours (up to 15): snapping to the front's colours merged shades and made the backs flat (Arvind, 16 Oct:
    # "can't we just leave the shading"). The game's one palette for front and back is made at export, from both together;
    # the front's colours stay a button in the studio's editor.
    sprite = klein_follower.to_back(raw)
    why = too_small(sprite, 200)
    image = folder / ("back_%d.png" % n)
    sprite.save(image)
    return ("broken" if why else "done", why, image, raw)


# ---------- frame 2: the second animation frame of the front and the back (2026-11-23, the PAIR LoRA). The model draws frame 1 |
# frame 2 side by side (640x320), as the real HGSS pairs it was trained on (lora-train\v6cfg\build_f2_pair.py, train_f2pair.ps1);
# in use the start picture is frame 1 | frame 1 and only the RIGHT half gets noise (SetLatentNoiseMask), so it sees its own frame 1
# while it draws frame 2. The right half -> 80x80 -> every pixel takes frame 1's nearest colour (one palette in the game).
# Image 2 is white ("Image 2 is empty"), as in the tests on our own mons. How much it moves (Arvind 22.11, all three liked):
#   calm   denoise 0.85 (frame 1 partly kept), CFG 4          "0.85 og 1.0 funker bra"
#   clear  denoise 1.0, CFG 4
#   big    denoise 1.0, CFG 5.5 + the trained 'a big change of pose' words ("1.2"; "jeg tror jeg likte den best egentlig")
# Every drawing is checked for NEW or LOST body parts (Arvind: "den skaper nye kroppsdeler og slik er ikke bra"; f2parts.py in
# ~/sigma-origin/title3d/legend/frame2, here numpy only): up to F2_ATTEMPTS seeds, the first that passes is used; a big one that
# never passes gets one more drawing at 'clear'; if still none passes, the best is kept and marked broken (people can still pick
# it or EDIT it). The website may say what moves on the FRONT (the motion templates the LoRA learnt, front only).
PAIR_LORA = "pkmn_f2pair_klein_v1_000002250.safetensors"
F2_MODES = {"calm": (0.85, 4.0, "a clear change of pose, all over its body"),
            "clear": (1.0, 4.0, "a clear change of pose, all over its body"),
            "big": (1.0, 5.5, "a big change of pose, all over its body, and the top of the figure moves up 3 pixels")}
F2_MIX = ["big", "clear", "calm"]
F2_MOVES = {"M": "it opens its mouth wide, as if roaring", "H": "it raises or turns its head", "A": "it raises or moves its arms, hands or claws",
            "W": "it flaps or spreads its wings", "T": "it swings or raises its tail", "C": "it crouches low, ready to pounce",
            "L": "it leans forward to attack", "B": "its whole body rises and stretches, as if breathing in", "E": "it blinks or narrows its eyes",
            "R": "it turns its whole body a little",
            "X": "it moves or stretches out a part of its body (tentacles, vines, antennae, petals, flames or fins)"}
F2_ATTEMPTS = 3


def f2_choice(job):
    """the website's choice (JSON in job['prompt']): size = mix / big / clear / calm, move = a motion code (front only)"""
    try:
        body = json.loads(job.get("prompt") or "{}")
    except ValueError:
        body = {}
    body = body if isinstance(body, dict) else {}
    size = body.get("size") if body.get("size") in F2_MODES or body.get("size") == "mix" else "mix"
    move = body.get("move") if body.get("move") in F2_MOVES else ""
    return size, move


def f2_mode(job, n):
    size, _ = f2_choice(job)
    return F2_MIX[(n - 1) % len(F2_MIX)] if size == "mix" else size


def _blobs(m):
    """8-connected blobs of a small bool picture, as lists of (y, x)"""
    seen = np.zeros_like(m); out = []
    for y, x in zip(*np.nonzero(m)):
        if seen[y, x]:
            continue
        stack, blob = [(y, x)], []
        seen[y, x] = True
        while stack:
            cy, cx = stack.pop(); blob.append((cy, cx))
            for ny in (cy - 1, cy, cy + 1):
                for nx in (cx - 1, cx, cx + 1):
                    if 0 <= ny < m.shape[0] and 0 <= nx < m.shape[1] and m[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; stack.append((ny, nx))
        out.append(blob)
    return out


def _shift(m, dx, dy):
    o = np.zeros_like(m); h, w = m.shape
    o[max(0, dy):h + min(0, dy), max(0, dx):w + min(0, dx)] = m[max(0, -dy):h - max(0, dy), max(0, -dx):w - max(0, dx)]
    return o


def _near(m, r):
    """every pixel within r px (straight-line distance) of m"""
    o = np.zeros_like(m)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                o |= _shift(m, dx, dy)
    return o


def f2_check(f1, f2, front=True, R=3):
    """f2parts.check: new = % of frame 1's area that frame 2 has more than R px outside frame 1 (after the best whole-sprite shift,
    so a hop or a lean is motion), lost = % of frame 1 that frame 2 no longer covers within R px, extra = new separate pieces,
    edge = a front that now touches the box edge, moved = % of the sprite that changed. Real HGSS frame 2s score new 1-13 /
    lost 2-12, so this RANKS drawings; 'bad' is the line the tests drew (22.11)."""
    a, b = np.array(f1.convert("RGBA")), np.array(f2.convert("RGBA"))
    A, B0 = a[..., 3] > 0, b[..., 3] > 0
    area = max(1, int(A.sum()))
    best = (-1.0, 0, 0)
    for dy in range(-8, 9):
        for dx in range(-8, 9):
            S = _shift(B0, dx, dy); v = (A & S).sum() / max(1, (A | S).sum())
            if v > best[0]:
                best = (v, dx, dy)
    B = _shift(B0, best[1], best[2])
    new = float((B & ~_near(A, R)).sum() / area * 100)
    lost = float((A & ~_near(B, R)).sum() / area * 100)
    pieces = lambda m: sum(1 for bl in _blobs(m) if len(bl) >= 6)
    extra = max(0, pieces(B0) - pieces(A))
    sides = lambda m: {s for s, v in (("t", m[0]), ("b", m[-1]), ("l", m[:, 0]), ("r", m[:, -1])) if v.any()}
    edge = front and bool(sides(B0) - sides(A))
    on = A | B0
    diff = (A != B0) | (A & B0 & (np.abs(a[..., :3].astype(int) - b[..., :3]).sum(-1) > 30))
    moved = float(diff[on].mean() * 100) if on.any() else 0.0
    bad = new > 6 or lost > 10 or extra > 0 or edge
    score = new + 0.5 * lost + 8 * extra + 20 * edge + (1.5 * (10 - moved) if moved < 10 else 0)
    return dict(new=new, lost=lost, extra=extra, edge=edge, moved=moved, bad=bad, score=score)


def on_magenta4(sprite):
    bg = Image.new("RGBA", (80, 80), (255, 0, 255, 255))
    bg.alpha_composite(sprite.convert("RGBA"))
    return bg.convert("RGB").resize((320, 320), Image.NEAREST)


def frame1_colours(sprite, frame1):
    """every pixel takes the nearest colour of frame 1 (one palette for both frames in the game)"""
    a = np.array(sprite.convert("RGBA")).copy()
    b = np.array(frame1.convert("RGBA"))
    pal = np.unique(b[b[..., 3] > 0][:, :3].reshape(-1, 3), axis=0).astype(int)
    on = a[..., 3] >= 128
    if len(pal) and on.any():
        px = a[on][:, :3].astype(int)
        a[..., :3][on] = pal[((px[:, None, :] - pal[None, :, :]) ** 2).sum(-1).argmin(1)]
    a[..., 3] = np.where(on, 255, 0)
    a[..., :3][~on] = 0
    return Image.fromarray(a)


def f2_seam(sprite, frame1):
    """The pair picture's middle seam: where frame 1 touches its RIGHT edge (Waffy's beak), the model can carry a thin line
    over into frame 2's LEFT edge (test 23.11: all three Waffy backs). A piece of frame 2 that lies wholly in columns 0-2,
    where frame 1 has nothing in those rows, goes."""
    a = np.array(sprite.convert("RGBA")).copy()
    f = np.array(frame1.convert("RGBA"))[..., 3] > 0
    for blob in _blobs(a[..., 3] > 0):
        ys = [y for y, _ in blob]
        if max(x for _, x in blob) <= 2 and not f[max(0, min(ys) - 2):max(ys) + 3, :3].any():
            for y, x in blob:
                a[y, x] = 0
    return Image.fromarray(a)


def f2_caption(view, body, change):
    """build_f2_pair.caption, as trained (image 2 empty)"""
    return ("Create the two animation frames of the %s battle sprite from Pokemon HeartGold of the Pokemon in image 1, side by side: "
            "image 1 is its first frame. Image 2 is empty. %sThe picture shows its two 80x80 pixel art %s frames side by side on a flat "
            "magenta background: the left one is exactly image 1, the right one is its second frame, the same creature in the same place "
            "and size, with exactly the colours, outline and design of image 1, redrawn in a new pose: %s." % (view, body, view, change))


def f2_graph(text, refs, seed, start, mask, dn, cfg):
    g = comfy.klein(text, refs, 640, 320, seed, "sigma/studio_f2", PAIR_LORA, cfg=cfg)
    g["startimg"] = {"class_type": "LoadImage", "inputs": {"image": start}}
    g["startenc"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["startimg", 0], "vae": ["vae", 0]}}
    g["maskimg"] = {"class_type": "LoadImage", "inputs": {"image": mask}}
    g["mask"] = {"class_type": "ImageToMask", "inputs": {"image": ["maskimg", 0], "channel": "red"}}
    g["masked"] = {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["startenc", 0], "mask": ["mask", 0]}}
    g["sca"]["inputs"]["latent_image"] = ["masked", 0]
    if dn < 1:
        g["split"] = {"class_type": "SplitSigmasDenoise", "inputs": {"sigmas": ["sched", 0], "denoise": dn}}
        g["sca"]["inputs"]["sigmas"] = ["split", 1]
    return g


def f2_draw(n, seed, folder, job, view, frame1):
    words, _ = job["_tags"]
    _, move = f2_choice(job)
    if not (folder / ("f2_start_%s.png" % view)).exists():
        one = on_magenta4(frame1)
        one.save(folder / ("f2_one_%s.png" % view))
        Image.new("RGB", (320, 320), "white").save(folder / "f2_white.png")
        start = Image.new("RGB", (640, 320)); start.paste(one, (0, 0)); start.paste(one, (320, 0)); start.save(folder / ("f2_start_%s.png" % view))
        m = Image.new("RGB", (640, 320), "black"); m.paste((255, 255, 255), (320, 0, 640, 320)); m.save(folder / "f2_mask.png")
    refs = [up(folder / ("f2_one_%s.png" % view)), up(folder / "f2_white.png")]
    st, mk = up(folder / ("f2_start_%s.png" % view)), up(folder / "f2_mask.png")
    body = about(job, words, move=False)
    mode = f2_mode(job, n)
    plan = [(mode, seed + 1000 * k) for k in range(F2_ATTEMPTS)] + ([("clear", seed + 1000 * F2_ATTEMPTS)] if mode == "big" else [])
    best = None
    for k, (md, sd) in enumerate(plan):
        dn, cfg, change = F2_MODES[md]
        if move and view == "front":
            change = F2_MOVES[move] + "; " + change
        raw = folder / ("%s2_raw_%d_%d.png" % (view, n, k))
        if not raw.exists():
            raw.write_bytes(comfy.run(f2_graph(f2_caption(view, body, change), refs, sd, st, mk, dn, cfg)))
        right = folder / ("%s2_right_%d_%d.png" % (view, n, k))
        Image.open(raw).convert("RGB").crop((320, 0, 640, 320)).save(right)
        sprite = f2_seam(frame1_colours(klein_follower.to_back(right), frame1), frame1)
        c = f2_check(frame1, sprite, front=view == "front")
        if best is None or (not c["bad"], -c["score"]) > (not best[0]["bad"], -best[0]["score"]):
            best = (c, sprite, raw, md)
        if not c["bad"]:
            break
    c, sprite, raw, md = best
    why = ("" if not c["bad"] else "maybe new or lost body parts (new %d%%, lost %d%%%s%s)" % (
        c["new"], c["lost"], ", a new loose piece" if c["extra"] else "", ", touches the edge" if c["edge"] else ""))
    image = folder / ("%s2_%d.png" % (view, n))
    sprite.save(image)
    how = "%s%s, %d%% of it moved" % (md, " (from big: big broke)" if md != mode else "", c["moved"])
    return ("broken" if why else "done", (why + "; " + how) if why else how, image, raw)


def try_front2(n, seed, folder, job, inputs):
    job["_tags"] = inputs["tags"]
    return f2_draw(n, seed, folder, job, "front", inputs["front"])


def try_back2(n, seed, folder, job, inputs):
    job["_tags"] = inputs["tags"]
    return f2_draw(n, seed, folder, job, "back", inputs["back"])


def icon_recipe(job, n):
    if job.get("recipe") in ("pc", "canvas"):
        return job["recipe"]
    return "pc" if n % 2 else "canvas"                       # both, taking turns (Arvind picks between them)


STAGES = {"art": try_art, "front": try_front, "back": try_back_klein if BACK_KLEIN else try_back, "icon": try_icon_klein,
          "follower": try_follower, "front2": try_front2, "back2": try_back2}


def recipe_name(job, n):
    stage = job["stage"]
    if stage == "front":
        return "front v7 600 @%.2f cfg %.1f" % (FRONT_STRENGTH, FRONT_CFG)
    if stage == "back":
        if BACK_KLEIN:
            return Path(BACK_KLEIN).stem.replace("pkmn_", "").replace("_0000", " ")
        return BACK_LORAS[(n - 1) % len(BACK_LORAS)].replace(".safetensors", "")
    if stage == "icon":
        return "icon klein v1 2500"
    if stage == "follower":
        return "follower klein v3 2000"
    if stage in ("front2", "back2"):
        return "f2pair v1 2250 %s" % f2_mode(job, n)
    if job.get("recipe") == "pose":
        return "sketch new pose (Qwen + style v2)"
    return "sketch to art (style klein v2 2500)" if job.get("recipe") == "sketch" else "base Qwen cut-out"


# ---------- timings: a recent average per stage, on this PC and on the website
def load_timings():
    try:
        return json.loads(TIMINGS.read_text())
    except (OSError, ValueError):
        return {}


def expected(timings, key):
    seen = timings.get(key) or []
    return round(sum(seen) / len(seen), 1) if seen else DEFAULT_SECONDS.get(key, 60)


def remember(timings, key, seconds):
    timings[key] = (timings.get(key) or [])[-9:] + [round(seconds, 1)]
    try:
        TIMINGS.write_text(json.dumps(timings))
    except OSError:
        pass


# ---------- the edge check (2026-11-24; Arvind found many of our sprites cut by the game's 80x80 frame: "det blir nok bare å
# lage nye for alle mons som har alvorlig mye på kanten"). A front or back whose COLOUR reaches the top, left or right edge
# in a run of EDGE_RUN pixels or more is cut; the dark outline alone does not count, and the bottom does not either (backs
# are cut by the bottom edge on purpose). A cut try is drawn again a bit smaller (EDGE_SHRINK, a new seed each time); the
# least cut one is kept, and one that still touches gets the note "cut at the ... edge" (the website shows it on the tile).
# Frame 2 (front2/back2) is drawn again with a new seed only (it follows frame 1's size); a cut its frame 1 already has stays.
EDGE_RUN = 3          # coloured pixels in a row on an edge
EDGE_LINE = 8         # or a straight line of any pixels (a cut drawn as outline) this long
EDGE_SHRINK = (0.88, 0.76)


def _longest(v):
    best = run = 0
    for x in v:
        run = run + 1 if x else 0
        best = max(best, run)
    return best


def edge_cut(sprite, edges=("top", "left", "right")):
    """{edge: longest run on it} for the edges a sprite is cut at: EDGE_RUN coloured pixels in a row, or EDGE_LINE pixels of
    any kind (one or two outline pixels touching the edge are fine)"""
    a = np.asarray(sprite.convert("RGBA")).astype(int)
    op = a[..., 3] > 0
    if not op.any():
        return {}
    luma = (299 * a[..., 0] + 587 * a[..., 1] + 114 * a[..., 2]) // 1000
    colour = op & (luma > max(60, luma[op].min() + 40))          # not the outline (the darkest shade)
    pick = {"top": (0, None), "left": (None, 0), "right": (None, -1)}
    out = {}
    for e in edges:
        r, c = pick[e]
        o, k = (op[r], colour[r]) if r is not None else (op[:, c], colour[:, c])
        lo, lk = _longest(o), _longest(k)
        if lk >= EDGE_RUN or lo >= EDGE_LINE:
            out[e] = lo
    return out


def fit_frame(stage, n, seed, folder, job, inputs, first, log):
    """the edge check around one try: (status, note, image, raw)"""
    status, note, image, raw = first
    if stage not in ("front", "back", "front2", "back2") or status != "done":
        return first
    old = set(edge_cut(inputs["front" if stage == "front2" else "back"])) if stage.endswith("2") else set()   # frame 1's own cut
    check = lambda im: {e: v for e, v in edge_cut(im).items() if e not in old}
    cut = check(Image.open(image))
    if not cut:
        return first
    best, best_cut, kept = (status, note, image, raw), cut, Path(str(image).replace(".png", "_try0.png"))
    Path(image).replace(kept); best = (status, note, kept, raw)
    for k, shrink in enumerate(EDGE_SHRINK, 1):
        log("try %d of job %d is cut at the %s edge: drawn again%s" % (n, job["id"], "/".join(best_cut), "" if stage.endswith("2") else " at x%.2f" % shrink))
        inputs["shrink"] = shrink
        try:
            again = STAGES[stage](n + 100 * k, seed + 5000 * k, folder, job, inputs)   # another n: new file names (the stages reuse a raw that exists)
        finally:
            inputs.pop("shrink", None)
        if again[0] != "done":
            continue
        moved = Path(str(again[2]).replace(".png", "_try%d.png" % k)); Path(again[2]).replace(moved)
        c = check(Image.open(moved))
        if sum(c.values()) < sum(best_cut.values()):
            best, best_cut = (again[0], ((again[1] or "") + "; " if again[1] else "") + ("drawn again (new seed) to fit the frame" if stage.endswith("2")
                              else "drawn x%.2f smaller to fit the frame" % shrink), moved, again[3]), c
        if not c:
            break
    status, note, image, raw = best
    if best_cut:
        note = ((note + "; ") if note else "") + "cut at the %s edge" % " and ".join(sorted(best_cut))
    return status, note, image, raw


def run(job, base, key, post, download, folder, log=print):
    """Draw a job's tries one by one and hand each in as soon as it is done. Returns how many were handed in."""
    stage, count = job["stage"], int(job.get("count") or 1)
    seed0 = job["id"] * 100
    timings = load_timings()
    inputs = {"tags": tags(job["species_id"])}
    src = job.get("from_try") or {}
    if stage == "art" and job.get("recipe") == "pose":            # a new pose of a drawing made earlier
        if not src.get("image"):
            raise RuntimeError("pick the drawing to turn first")
        inputs["art"] = Image.open(download(base, src["image"], folder / "from_art.png")).convert("RGBA")
    elif stage == "art" or (stage == "front" and not src):
        inputs["refs"] = [download(base, p, folder / ("ref%d.png" % i)) for i, p in enumerate(job.get("refs") or [])]
        if not inputs["refs"]:
            raise RuntimeError("no picture was chosen")
        if stage == "front":                                     # a species picture used as the art directly
            inputs["art"] = framed(Image.open(inputs["refs"][0]))
    if stage == "front" and src:
        inputs["art"] = Image.open(download(base, src["image"], folder / "from_art.png")).convert("RGBA")
        if src.get("stage") == "front":                         # "more like this": a front drawn from the same art as a front
            parent = src.get("parent") or {}
            if parent.get("image"):
                inputs["art"] = Image.open(download(base, parent["image"], folder / "from_art.png")).convert("RGBA")
    if "art" in inputs:
        inputs["art_path"] = folder / "art_in.png"
        framed(inputs["art"]).save(inputs["art_path"])
        inputs["art"] = Image.open(inputs["art_path"])
    if stage in ("back", "icon", "follower"):
        inputs["front"] = Image.open(download(base, src["image"], folder / "from_front.png")).convert("RGBA")
        parent = src.get("parent") or {}
        art = parent if parent.get("stage") == "art" else (parent.get("parent") or {}) if parent.get("stage") == "front" else {}
        if stage == "back" and art.get("stage") == "art" and art.get("image"):   # a front drawn on by hand: its front's art (2026-11-24)
            inputs["art"] = Image.open(download(base, art["image"], folder / "from_art.png")).convert("RGBA")
        elif stage == "back" and job.get("refs"):                # the front was drawn from a chosen picture directly
            inputs["art"] = framed(Image.open(download(base, job["refs"][0], folder / "ref0.png")))
    if stage == "back":                                          # the website (or a batch) may name a back to keep the look of
        try:
            ref = (json.loads(job.get("prompt") or "{}") or {}).get("back_ref")
        except (ValueError, AttributeError):
            ref = None
        if ref:
            inputs["back_ref"] = Image.open(download(base, ref, folder / "back_ref.png")).convert("RGBA")
    if stage == "follower":
        other = job.get("with_try") or {}
        if not other.get("image"):
            raise RuntimeError("the walking sprite needs a back: pick one first")
        inputs["back"] = Image.open(download(base, other["image"], folder / "with_back.png")).convert("RGBA")
    if stage in ("front2", "back2"):                           # frame 2: only the picked frame 1 (the pair LoRA needs nothing else)
        inputs["front" if stage == "front2" else "back"] = Image.open(download(base, src["image"], folder / ("f2_%s.png" % stage))).convert("RGBA")
    if stage == "icon":
        species = {sid: d for sid, _, d in dexlib.load_species()[0]}
        inputs["body_color"] = (species.get(job["species_id"]) or {}).get("body_color")
    made = 0
    for n in range(1, count + 1):
        seed = seed0 + n
        name = recipe_name(job, n)
        tkey = "back:klein" if stage == "back" and BACK_KLEIN else ("art:" + job["recipe"]) if stage == "art" and job.get("recipe") in ("sketch", "pose") else stage
        row = post(base, key, {"action": "try_start", "job_id": job["id"], "n": n, "seed": seed, "recipe": name,
                               "expected_seconds": expected(timings, tkey)})
        post(base, key, {"action": "progress", "job_id": job["id"], "state": ("drawing %s: %s %d of %d" % (job["species_id"], stage, n, count))[:120]})
        started = time.time()
        try:
            status, note, image, raw = fit_frame(stage, n, seed, folder, job, inputs, STAGES[stage](n, seed, folder, job, inputs), log)
        except Exception as problem:                             # one bad picture must not stop the others
            log("try %d of job %d failed: %s" % (n, job["id"], problem))
            post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": row["id"], "status": "failed",
                             "note": ("%s: %s" % (type(problem).__name__, problem))[:300], "seconds": round(time.time() - started, 1)})
            continue
        seconds = time.time() - started
        remember(timings, tkey, seconds)
        files = {"image": image}
        if raw and not job.get("batch") and Path(raw).stat().st_size < 3 * 1024 * 1024:   # batch (whole-dex) jobs keep no raw: storage
            files["raw"] = raw
        post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": row["id"], "status": status, "note": note,
                         "seconds": round(seconds, 1)}, files)
        made += 1
        if stage in ("front2", "back2") and status in ("done", "broken"):   # the battle animation preview (2026-11-23)
            import anim_preview
            first = folder / ("anim_frame1_%s.png" % stage)
            inputs["front" if stage == "front2" else "back"].save(first)
            anim_preview.after_try(post, base, key, job, row["id"], first, image, folder, log)
        try:
            post(base, key, {"action": "timings", "timings": json.dumps({k: expected(timings, k) for k in timings})})
        except (RuntimeError, OSError):
            pass
    return made
