"""Sprite studio v3: the worker's side of drawing TRIES (2026-10-14).

A job of mode "tries" asks for N pictures of one stage; each is registered as it starts (so the website can show it
drawing, with the time it should take), drawn, read as pixels and handed in with its time:

    art    the creature cut out of a chosen picture by base Qwen-Image 2.1 (a clean 640 drawing, see-through)
    front  the DS front (80x80): front LoRA v7 600 at 0.75, cfg 2.5 + a negative prompt, 20 steps, then unfake
    back   the DS back (80x80) on the front's colours: back LoRA v6 (1800 / 2100 / 2400 in turn)
    icon   the menu icon (32x32) with icon LoRA v2: the PC box recipe and the canvas swap, taking turns

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
import pixel_render

FRONT_LORA, FRONT_STRENGTH, FRONT_CFG = "fv7_600.safetensors", 0.75, 2.5
BACK_LORAS = ["bv6_1800.safetensors", "bv6_2100.safetensors", "bv6_2400.safetensors"]
ICON_LORA = "pkmn_icon_edit_v2.safetensors"
UNFAKE = os.environ.get("UNFAKE_EXE", r"D:\LocalAI\tools\pxvenv\Scripts\unfake.exe")
TIMINGS = Path(os.environ.get("SIGMA_TIMINGS_FILE", dexlib.ROOT / ".studio-timings.json"))
DEFAULT_SECONDS = {"art": 75, "front": 100, "back": 55, "icon:pc": 8, "icon:canvas": 8}   # measured on the Legion, 14 Oct
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
    """unfake (the pixel-art reader) on the front LoRA's 1280 picture -> 80x80; the cell middles when it is not installed."""
    if Path(UNFAKE).exists() and not out.exists():
        subprocess.run([UNFAKE, str(path), "-o", str(out), "-s", "16", "-m", "dominant", "--auto-colors", "--cleanup", "morph,jaggy"], capture_output=True)
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
def try_art(n, seed, folder, job, inputs):
    raw = folder / ("art_raw_%d.png" % n)
    prompt = ART + ((" " + job["prompt"]) if job.get("prompt") else "")
    comfy.generate(prompt, raw, inputs["refs"][:3], size=(1024, 1024), steps=40, seed=seed, quiet=True, transparent=True)
    im, share = largest_blob(Image.open(raw))
    image = folder / ("art_%d.png" % n)
    framed(im).save(image)
    return ("broken", "loose bits (%.0f %% outside the creature)" % (100 - 100 * share), image, raw) if share < 0.9 else ("done", "", image, raw)


def try_front(n, seed, folder, job, inputs):
    art = inputs["art"]
    words, side = inputs["tags"]
    box = front_box(side, art)
    template = folder / "front_template.png"
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


def icon_recipe(job, n):
    if job.get("recipe") in ("pc", "canvas"):
        return job["recipe"]
    return "pc" if n % 2 else "canvas"                       # both, taking turns (Arvind picks between them)


STAGES = {"art": try_art, "front": try_front, "back": try_back, "icon": try_icon}


def recipe_name(job, n):
    stage = job["stage"]
    if stage == "front":
        return "front v7 600 @%.2f cfg %.1f" % (FRONT_STRENGTH, FRONT_CFG)
    if stage == "back":
        return BACK_LORAS[(n - 1) % len(BACK_LORAS)].replace(".safetensors", "")
    if stage == "icon":
        return icon_recipe(job, n)
    return "base Qwen cut-out"


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


def run(job, base, key, post, download, folder, log=print):
    """Draw a job's tries one by one and hand each in as soon as it is done. Returns how many were handed in."""
    stage, count = job["stage"], int(job.get("count") or 1)
    seed0 = job["id"] * 100
    timings = load_timings()
    inputs = {"tags": tags(job["species_id"])}
    src = job.get("from_try") or {}
    if stage == "art" or (stage == "front" and not src):
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
    if stage in ("back", "icon"):
        inputs["front"] = Image.open(download(base, src["image"], folder / "from_front.png")).convert("RGBA")
        parent = src.get("parent") or {}
        if stage == "back" and parent.get("stage") == "art" and parent.get("image"):
            inputs["art"] = Image.open(download(base, parent["image"], folder / "from_art.png")).convert("RGBA")
    made = 0
    for n in range(1, count + 1):
        seed = seed0 + n
        name = recipe_name(job, n)
        tkey = "icon:" + icon_recipe(job, n) if stage == "icon" else stage
        row = post(base, key, {"action": "try_start", "job_id": job["id"], "n": n, "seed": seed, "recipe": name,
                               "expected_seconds": expected(timings, tkey)})
        post(base, key, {"action": "progress", "job_id": job["id"], "state": ("drawing %s: %s %d of %d" % (job["species_id"], stage, n, count))[:120]})
        started = time.time()
        try:
            status, note, image, raw = STAGES[stage](n, seed, folder, job, inputs)
        except Exception as problem:                             # one bad picture must not stop the others
            log("try %d of job %d failed: %s" % (n, job["id"], problem))
            post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": row["id"], "status": "failed",
                             "note": ("%s: %s" % (type(problem).__name__, problem))[:300], "seconds": round(time.time() - started, 1)})
            continue
        seconds = time.time() - started
        remember(timings, tkey, seconds)
        files = {"image": image}
        if raw and Path(raw).stat().st_size < 3 * 1024 * 1024:
            files["raw"] = raw
        post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": row["id"], "status": status, "note": note,
                         "seconds": round(seconds, 1)}, files)
        made += 1
        try:
            post(base, key, {"action": "timings", "timings": json.dumps({k: expected(timings, k) for k in timings})})
        except (RuntimeError, OSError):
            pass
    return made
