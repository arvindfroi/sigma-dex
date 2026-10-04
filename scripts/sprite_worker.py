#!/usr/bin/env python3
"""The sprite worker: runs on the PC with the GPU and draws the sprites people ask for.

    python scripts/sprite_worker.py

It asks the website's database for the next sprite request, has ComfyUI draw it (starting
ComfyUI if it is not running), converts the result to game sprites and hands them in. It
only makes outgoing connections, so the PC does not have to be reachable from the internet.
Setup and settings: docs/STUDIO.md.

Settings (environment variables): SIGMA_WORKER_KEY_FILE (file with the worker key),
COMFY_DIR (ComfyUI's folder, used to start it), COMFY_URL (default http://127.0.0.1:8188).
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

import numpy as np
import yaml

import comfy
import dexlib
import pixel_render
import sprite_quality
import sprites
from dexlib import ROOT

KEY_FILE = Path(os.environ.get("SIGMA_WORKER_KEY_FILE", ROOT / ".worker-key"))
COMFY_DIR = os.environ.get("COMFY_DIR")
POLL_SECONDS, IDLE_UNLOAD_SECONDS, UPDATE_SECONDS = 8, 180, 600


def log(text):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), text, flush=True)


def post(base, key, fields, files=None):
    """Call the sprite-worker function: text fields plus PNG files, as a form."""
    boundary = uuid.uuid4().hex
    body = b""
    for name, value in dict(fields, key=key).items():
        body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, name, value)).encode()
    for name, path in (files or {}).items():
        body += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s.png\"\r\nContent-Type: image/png\r\n\r\n" % (boundary, name, name)).encode()
        body += Path(path).read_bytes() + b"\r\n"
    body += ("--%s--\r\n" % boundary).encode()
    request = urllib.request.Request(base + "/functions/v1/sprite-worker", body, {"Content-Type": "multipart/form-data; boundary=" + boundary})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        raise RuntimeError("the server said %d: %s" % (error.code, error.read().decode("utf-8", "replace")[:300]))


def download(base, path, target):
    with urllib.request.urlopen(urllib.request.Request("%s/storage/v1/object/public/art/%s" % (base, path), headers={"User-Agent": "sigma-dex"}), timeout=120) as response:
        Path(target).write_bytes(response.read())
    return Path(target)


def comfy_alive():
    try:
        comfy.call("/system_stats")
        return True
    except comfy.ComfyError:
        return False


def ensure_comfy():
    """Start ComfyUI if nothing answers, and wait until it does."""
    if comfy_alive():
        return
    if not COMFY_DIR:
        raise RuntimeError("ComfyUI is not running and COMFY_DIR is not set")
    log("starting ComfyUI")
    python = Path(COMFY_DIR) / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    out = open(Path(COMFY_DIR) / "sigma_comfyui.log", "ab")
    subprocess.Popen([str(python), "main.py", "--listen", "127.0.0.1", "--port", "8188"], cwd=COMFY_DIR, stdout=out, stderr=out)
    for _ in range(90):
        time.sleep(2)
        if comfy_alive():
            return
    raise RuntimeError("ComfyUI did not start within 3 minutes")


def where(comment):
    """Which view a pinned comment is about, and roughly where on it, from its spot on the preview."""
    x, y = comment.get("x"), comment.get("y")
    if x is None or y is None:
        return None, ""
    view = "front" if x < 1 / 3 else "back" if x < 2 / 3 else None       # the preview shows front, back, icon side by side
    inside = (x * 3) % 1
    spot = "%s %s" % ("upper" if y < 0.38 else "lower" if y > 0.62 else "middle", "left" if inside < 0.38 else "right" if inside > 0.62 else "center")
    return view, "About the %s area of the sprite: " % spot


def recipes(job, settings):
    """For every view: the prompt and the reference pictures (as storage paths)."""
    two_step = job.get("style", "pixel") != "pixel"          # these styles start from a clean illustration
    style = " ".join(settings["illustration" if two_step else "style"].split())
    pose = job.get("pose") or "front"
    views = {"front": settings["poses"].get(pose, settings["front"]), "back": settings["back"]}
    refs = list(job.get("refs") or [])
    redesign = job.get("style") == "sprite-clean" and refs   # free to redesign the first reference (needs one)
    official = job.get("style") == "sprite-official" and refs
    parent = job.get("parent")
    out = {}
    for view in ("front", "back"):
        if parent:                                   # redo an earlier sprite with changes
            changes = [job["notes"]] if job.get("notes") else []
            for comment in job.get("comments") or []:
                about, spot = where(comment)
                if about in (None, view):
                    changes.append(spot + comment["body"])
            if not changes:
                out[view] = None                     # nothing asked for this view: keep the old picture
                continue
            others = "".join(" The creature's design is shown in <image%d>." % (n + 2) for n in range(len(refs)))
            kept = ("Official Pokemon Ruby and Sapphire artwork in the same style as <image1>: thick dark outlines, flat colors, "
                    "crisp shadows, plain white background, exactly one creature." if official else style)
            out[view] = ("%s Redraw the creature picture in <image1> with these changes: %s Keep everything else about it the same: same creature, same pose, same view, same colors.%s"
                         % (kept," ".join(c if c.rstrip().endswith((".", "!", "?")) else c.rstrip() + "." for c in changes), others),
                         [parent["raw_" + view]] + refs)
        elif official:                               # official-style artwork; the back is drawn from the new front ("@front")
            look = job["look"].strip().rstrip(".")
            if view == "front":
                others = "".join(" <image%d> shows the same creature." % (n + 2) for n in range(len(refs[1:3])))
                pose = settings["official_poses"].get(job.get("pose") or "three-quarter", settings["official_poses"]["three-quarter"])
                text = settings["official_front"].replace("{pose}", pose)
                signature = job.get("signature") or (settings.get("pokemon", {}).get(job["species_id"]) or {}).get("signature")
                text = text.replace("{signature}", (" Its most important features must be big, bold and clearly readable even on a tiny sprite, "
                                                    "exaggerated if needed: %s." % signature.strip().rstrip(".")) if signature else "")
                out[view] = (" ".join(text.split()).replace("{look}", look).replace("{others}", others), refs[:3])
            else:
                # the concept art comes first: shown the new front picture first, Qwen copies its angle
                others = " (<image%d> shows how it was drawn from the front)" % (len(refs[:2]) + 1)
                out[view] = (" ".join(settings["official_back"].split()).replace("{look}", look).replace("{others}", others), refs[:2] + ["@front"])
        elif redesign:
            look = job["look"].strip().rstrip(".")
            others = "".join(" <image%d> shows the same creature." % (n + 2) for n in range(len(refs[1:3])))
            out[view] = (" ".join(settings["redesign_" + view].split()).replace("{look}", look).replace("{others}", others), refs[:3])
        else:
            subject = "The creature is the one shown in <image1>. " if refs else ""
            out[view] = ("%s %s%s %s" % (style, subject, " ".join(views[view].split()), job["look"]), refs)
    return out


LORA_BACKGROUND = (181, 238, 252)        # the flat light blue the Emerald LoRA puts behind its sprites


def emerald(picture, look, strength, seed, target):
    """Repaint an illustration as a Pokemon Emerald sprite with the LoRA; returns the path of the result.

    The LoRA only keeps a design it is shown at sprite size on its own kind of background, so
    the illustration is first shrunk to 60 pixels on light blue and blown up again.
    """
    import numpy as np
    from PIL import Image
    rgb, opaque = sprites.shrink(Image.open(picture), 60)
    canvas = np.zeros((64, 64, 3), np.uint8)
    canvas[:] = LORA_BACKGROUND
    height, width = opaque.shape
    top, left = (64 - height) // 2, (64 - width) // 2
    canvas[top:top + height, left:left + width] = np.where(opaque[..., None], rgb, canvas[top:top + height, left:left + width])
    small = Path(str(target) + ".in.png")
    Image.fromarray(canvas).resize((1024, 1024), Image.NEAREST).save(small)
    comfy.restyle(small, "no humans, pokemon (creature), solo, full body, " + look, target, denoise=strength, control=0.0, seed=seed, quiet=True)
    return target


SPRITE_XL = dict(checkpoint="NoobAI-XL-v1.1.safetensors", lora_name="pkspif_nb_v1-2.safetensors", trigger="", cfg=5.0, denoise=0.8, control=0.65,
                 negative="worst quality, low quality, human, trainer, text, watermark, signature, blurry, 3d, realistic, dithering, noise, jpeg artifacts")


BACK_ZOOM = 1.4


def sprite_pixels(species_id, view):
    """How many pixels big the creature should be drawn, like official sprites of its strength.

    Official GBA sprites: first stages are about 40 pixels (their backs 46), middle stages about
    50, final stages and legendaries fill the 64 pixel frame. That looked too small to the group
    and leaves too few pixels for a face, so ours are drawn bigger: 54, 60 and 63 (2026-10-03).
    """
    stats = next((data.get("base_stats") or {} for sid, _, data in dexlib.load_species()[0] if sid == species_id), {})
    total = sum(v for v in stats.values() if isinstance(v, int))
    size = 54 if total and total < 360 else 60 if total and total < 480 else 63 if total else 60
    return size


def sprite_area(species_id):
    """How many pixels of the frame the front sprite should cover. Measured on the games' 45 starter
    sprites (2026-10-03, median): first stages 764, middle 1224, final 1962; ours are a quarter
    bigger, as the group found the official ones small."""
    stats = next((data.get("base_stats") or {} for sid, _, data in dexlib.load_species()[0] if sid == species_id), {})
    total = sum(v for v in stats.values() if isinstance(v, int))
    official = 764 if total and total < 360 else 1224 if total and total < 480 else 1962 if total else 1224
    return round(official * 1.25)


def colour_lock(start, repainted, target, keep_light=0.35):
    """Keep the sprite model's pixel shading and outlines, but take the colors from the illustration.

    The sprite model drifts toward grey and invents colors; the illustration has the right ones.
    """
    import numpy as np
    from PIL import Image
    first = Image.open(start).convert("RGB")
    second = Image.open(repainted).convert("RGB").resize(first.size)
    a, b = np.array(first.convert("HSV")).astype(float), np.array(second.convert("HSV")).astype(float)
    drawn = np.abs(np.array(first).astype(int) - 255).sum(axis=2) > 40          # not the white background
    out = b.copy()
    out[..., 0] = np.where(drawn, a[..., 0], b[..., 0])
    out[..., 1] = np.where(drawn, a[..., 1], b[..., 1])
    out[..., 2] = np.where(drawn, b[..., 2] * (1 - keep_light) + a[..., 2] * keep_light, b[..., 2])
    dark = b[..., 2] < 70                                                       # the sprite model's outlines stay dark
    out[..., 1] = np.where(dark, np.minimum(out[..., 1], 120), out[..., 1])
    out[..., 2] = np.where(dark, b[..., 2], out[..., 2])
    Image.fromarray(out.clip(0, 255).astype(np.uint8), "HSV").convert("RGB").save(target)
    return target


def sprite_xl(picture, look, view, seed, target, species_id, repaint):
    """Turn an illustration into a sprite-sized picture (768x768, one sprite pixel = 8 pixels); returns its path.

    The creature is placed on the canvas at the size an official sprite of its strength has, so
    nothing has to be shrunk afterwards. Two recipes, because each wins on some creatures:
    - repaint False ("drawn"): the illustration itself; the converter then shrinks it while
      keeping outlines and small features alive (sprites.snap_detail).
    - repaint True ("repainted"): the Pokemon Sprite XL LoRA repaints it in sprite shading while
      a ControlNet holds its outlines; the colors are locked to the illustration afterwards.
    """
    from PIL import Image
    image = sprites.cutout(Image.open(picture))
    image = image.crop(image.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox())
    size = sprite_pixels(species_id, view)
    if view == "back":
        # The games draw the back view closer than the front and show only the upper body, cut off flat at the bottom.
        scale = min(size * BACK_ZOOM * 8 / image.height, 62 * 8 / image.width)
    else:
        scale = size * 8 / max(image.size)
    image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.LANCZOS)
    if view == "back":
        image = image.crop((0, 0, image.width, min(image.height, min(62, size + 2) * 8)))
    canvas = Image.new("RGBA", (768, 768), "white")
    canvas.alpha_composite(image, ((768 - image.width) // 2, (768 - image.height) // 2))
    start = Path(str(target) + ".in.png")
    canvas.convert("RGB").save(start)
    if not repaint:
        canvas.convert("RGB").save(target)
        return target
    tags = "pokemon sprite, gen3, pixel art, no humans, pokemon (creature), solo, %s, %s, white background, simple background" % (
        look.strip().rstrip("."), "from behind, back view, facing away" if view == "back" else "full body")
    repainted = Path(str(target) + ".lora.png")
    comfy.restyle(start, tags, repainted, seed=seed, quiet=True, **SPRITE_XL)
    return colour_lock(start, repainted, target)


def fit_into(image, box, side=1024):
    """The drawing in `image` (background cut away), scaled to fit `box` (left, top, right, bottom)
    and placed in it bottom-centered, on a white side x side picture."""
    from PIL import Image
    image = sprites.cutout(image)
    image = image.crop(image.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox())
    scale = min((box[2] - box[0]) / image.width, (box[3] - box[1]) / image.height)
    image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGBA", (side, side), "white")
    canvas.alpha_composite(image, ((box[0] + box[2] - image.width) // 2, box[3] - image.height))
    return canvas.convert("RGB")


def clean_sprite(picture, view, seed, target, species_id, prompt):
    """The sprite-clean finish: shrink the illustration to a rough sprite, then have the AI repaint
    that rough sprite at the same size and place, as a spriter draws over a shrunk reference.
    Returns a 1024 picture of the whole 64 frame (one sprite pixel = 16 pixels).

    The size is not left to the AI: the illustration it is shown is placed exactly over the rough
    sprite, and whatever it draws is scaled back into the rough sprite's box (official size)."""
    from PIL import Image
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        start = sprite_xl(picture, "", view, seed, folder / "start.png", species_id, False)
        sprites.build(species_id, {"front": start}, note="rough", grid=96, out=folder / "rough", detail=True)
        small = sprites.as_rgba(folder / "rough" / "front.png")
        guide = Image.open(start)
        guide.load()
    rough = Image.new("RGBA", small.size, "white")
    rough.alpha_composite(small)
    rough_path = Path(str(target) + ".rough.png")
    rough.convert("RGB").resize((1024, 1024), Image.NEAREST).save(rough_path)
    unit = 1024 // small.width
    box = tuple(v * unit for v in small.getchannel("A").getbbox())
    guide_path = Path(str(target) + ".guide.png")
    fit_into(guide, box).save(guide_path)
    comfy.generate(prompt, target, [rough_path, guide_path], seed=seed, quiet=True)
    if view == "back":                                # the AI likes to draw the legs back in: cut it off where the rough sprite ends
        cleaned = Image.open(target).convert("RGB")
        cleaned.paste("white", (0, box[3], cleaned.width, cleaned.height))
    else:
        cleaned = fit_into(Image.open(target), box)
    cleaned.save(target)
    return target


TOUCH = dict(SPRITE_XL, denoise=0.4, control=0.75)


def lora_touch(sprite64, look, view, seed, target):
    """A light pass of the Pokemon sprite LoRA over a finished 64 sprite: it is put on the LoRA's
    canvas at the scale the LoRA was trained on (one pixel = 8x8 in a 96 frame), repainted lightly
    while its outlines are held, and the colours are locked back. Calms noisy shading a little;
    stronger than 0.45 starts to wipe out eyes. Returns the 768 picture (snap it with grid 96)."""
    from PIL import Image
    canvas = Image.new("RGBA", (96, 96), "white")
    canvas.alpha_composite(sprite64, (16, 16))
    start = Path(str(target) + ".in.png")
    canvas.convert("RGB").resize((768, 768), Image.NEAREST).save(start)
    tags = "pokemon sprite, gen3, pixel art, no humans, pokemon (creature), solo, %s, %s, white background, simple background" % (
        look.strip().rstrip("."), "from behind, back view, facing away" if view == "back" else "full body")
    repainted = Path(str(target) + ".lora.png")
    comfy.restyle(start, tags, repainted, seed=seed, quiet=True, **TOUCH)
    return colour_lock(start, repainted, target, keep_light=0.5)


def official_sprites(raw, species_id, prefix):
    """The sprite-official finish: front, back and icon built from the artwork by the pixel renderer.
    The back uses the front's colours, is drawn closer than the front (BACK_ZOOM) and is cut off flat
    at the bottom (at the usual height, or its lowest 15% for low, wide creatures)."""
    size = sprite_pixels(species_id, "front")
    files = {"front": Path(str(prefix) + "front.png"), "back": Path(str(prefix) + "back.png"), "icon": Path(str(prefix) + "icon.png")}
    front = pixel_render.render(raw["front"], size=size, area=sprite_area(species_id))
    size = max(front.size)
    front.save(files["front"])
    # the back: drawn closer than the front (it covers BACK_ZOOM squared times the front's area, as the
    # games' backs do), fitting the frame's width, and cut off flat at the bottom (its lowest quarter)
    covered = int((np.array(front)[..., 3] > 0).sum())
    back = pixel_render.render(raw["back"], size=min(64, round(size * BACK_ZOOM)), area=covered * BACK_ZOOM ** 2, palette=pixel_render.palette_of(front))
    if back.width > 64:
        back = pixel_render.render(raw["back"], fit=(64, 200), palette=pixel_render.palette_of(front))
    back.crop((0, 0, back.width, min(64, round(back.height * 0.78)))).save(files["back"])
    pixel_render.render(raw["front"], size=28).save(files["icon"])
    return files


def run(job, base, key, settings):
    style_version = hashlib.sha1(json.dumps([settings["style"], settings["illustration"], settings["poses"], settings["back"],
                                             settings["emerald_strength"], settings["redesign_front"], settings["redesign_back"], settings["cleanup"],
                                             settings["official_front"], settings["official_back"], settings["official_poses"]], sort_keys=True).encode()).hexdigest()[:10]
    strength = settings["emerald_strength"].get(job.get("style"))
    plan = recipes(job, settings)
    made = 0
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        fetched = {}
        def local(path):
            if path not in fetched:
                fetched[path] = download(base, path, folder / ("ref%d.png" % len(fetched)))
            return fetched[path]
        clean_style = job.get("style") in ("sprite-clean", "sprite-official")
        candidates = []
        for number in range(job["variations"] * (2 if clean_style else 1)):   # clean style: make twice as many, hand in the better half
            seed = job["id"] * 100 + number          # the same request always gives the same pictures
            raw = {}
            for view, recipe in plan.items():
                raw[view] = folder / ("%d_%s.png" % (number, view))
                if recipe is None:
                    download(base, job["parent"]["raw_" + view], raw[view])
                else:
                    for extra in range(4 if view == "back" and job.get("style") == "sprite-official" else 1):
                        comfy.generate(recipe[0], raw[view], [raw["front"] if p == "@front" else local(p) for p in recipe[1]], seed=seed + 1000 * extra,
                                       transparent=job.get("style") != "sprite-official", quiet=True)
                        if view != "back" or job.get("style") != "sprite-official" or sprite_quality.same_view(raw["front"], raw["back"]) <= 0.6:
                            break                     # a back drawn from the front again is drawn again
            out = folder / ("sprite%d" % number)
            final = dict(raw)
            if strength:                              # second step: the Emerald sprite LoRA
                for view in raw:
                    final[view] = emerald(raw[view], job["look"], strength, seed, folder / ("%d_%s_emerald.png" % (number, view)))
            grid = 64
            detail, recipe = False, ""
            if job.get("style") == "sprite-xl":       # second step: make it a sprite; odd attempts are repainted by the LoRA
                repaint = number % 2 == 1
                for view in raw:
                    final[view] = sprite_xl(raw[view], job["look"], view, seed, folder / ("%d_%s_spritexl.png" % (number, view)), job["species_id"], repaint)
                grid, detail, recipe = 96, not repaint, "repainted" if repaint else "drawn"
            if job.get("style") == "sprite-clean":     # second step: rough sprite, repainted clean at sprite size
                cleanup = " ".join(settings["cleanup"].split())
                for view in raw:
                    clean = clean_sprite(raw[view], view, seed, folder / ("%d_%s_clean.png" % (number, view)), job["species_id"], cleanup)
                    sprites.build(job["species_id"], {"front": clean}, note="step", grid=64, out=folder / ("%d_%s_step" % (number, view)), detail=True)
                    final[view] = lora_touch(sprites.as_rgba(folder / ("%d_%s_step" % (number, view)) / "front.png"), job["look"], view, seed,
                                             folder / ("%d_%s_touch.png" % (number, view)))
                grid = 96
            if job.get("style") == "sprite-official":  # second step: build the sprite from the artwork, pixel by pixel
                final = official_sprites(raw, job["species_id"], folder / ("%d_pixels_" % number))   # own names: raw[...] must stay the artwork
                grid = None
            sprites.build(job["species_id"], final, note="AI draft", grid=grid, out=out, detail=detail)
            small = {}
            for view in ("front", "back"):
                small[view] = folder / ("%d_%s_64.png" % (number, view))
                sprites.as_rgba(out / (view + ".png")).save(small[view])
            prompt = ("style: %s%s, pose: %s\n\n" % (job.get("style", "pixel"), " (%s)" % recipe if recipe else "", job.get("pose", "front"))) + "\n\n".join("%s: %s" % (view, recipe[0] if recipe else "(kept from the earlier sprite)") for view, recipe in plan.items())
            mark, _ = sprite_quality.score(sprites.as_rgba(out / "front.png"), "front")
            failed = sprite_quality.standards(sprites.as_rgba(out / "front.png"), sprites.as_rgba(out / "back.png"), sprite_pixels(job["species_id"], "front"))
            mark -= 10 * len(failed)                  # an attempt that misses the standard goes to the back of the queue
            if job.get("style") == "sprite-official":  # and one whose colours drifted from its artwork too
                keep = sprite_quality.fidelity(raw["front"], sprites.as_rgba(out / "front.png"))
                mark -= 20 * (1 - keep)
                prompt = prompt.replace("\n\n", " (colours kept %.0f%%)\n\n" % (100 * keep), 1)
            if failed:
                prompt += "\n\nMisses the sprite standard: " + "; ".join(failed)
            candidates.append((mark, seed, prompt, {"raw_front": raw["front"], "raw_back": raw["back"], "front": small["front"], "back": small["back"], "preview": out / "preview.png"}))
        if clean_style:
            candidates = sorted(candidates, key=lambda c: -c[0])[:job["variations"]]
        for mark, seed, prompt, files in candidates:
            if clean_style:
                prompt = prompt.replace("\n\n", " (quality %.1f)\n\n" % mark, 1)
            post(base, key, {"action": "candidate", "job_id": job["id"], "seed": seed, "prompt": prompt, "style_version": style_version}, files)
            made += 1
    return made


def main():
    config = dexlib.load_config().get("web_edits") or {}
    base = (config.get("url") or "").rstrip("/")
    if not base or not KEY_FILE.exists():
        sys.exit("Needs web_edits.url in data/config.yaml and the worker key in %s." % KEY_FILE)
    key = KEY_FILE.read_text().strip()
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    log("sprite worker started (%s)" % head[:7])
    idle_since, unloaded, checked = time.time(), True, time.time()
    while True:
        try:
            job = post(base, key, {"action": "claim"}).get("job")
        except (RuntimeError, OSError) as error:
            log("could not reach the database: %s" % error)
            time.sleep(60)
            continue
        if not job:
            if "--once" in sys.argv:           # for testing: stop when the queue is empty
                return 0
            if not unloaded and time.time() - idle_since > IDLE_UNLOAD_SECONDS and comfy_alive():
                try:                                 # give the graphics memory back while nobody is drawing
                    comfy.call("/free", json.dumps({"unload_models": True, "free_memory": True}).encode(), {"Content-Type": "application/json"})
                    log("idle: unloaded the model")
                except comfy.ComfyError:
                    pass
                unloaded = True
            if time.time() - checked > UPDATE_SECONDS:      # newer scripts or style in the repository? restart with them
                checked = time.time()
                subprocess.run(["git", "-C", str(ROOT), "pull", "--ff-only", "--quiet"], capture_output=True)
                if subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() != head:
                    log("the repository changed: restarting")
                    return 0
            time.sleep(POLL_SECONDS)
            continue
        log("job %d: %s x%d" % (job["id"], job["species_id"], job["variations"]))
        error = ""
        try:
            ensure_comfy()
            settings = yaml.safe_load((ROOT / "data" / "sprite_prompts.yaml").read_text(encoding="utf-8"))
            made = run(job, base, key, settings)
            log("job %d: %d sprites handed in" % (job["id"], made))
        except Exception as problem:                  # one bad job must not stop the worker
            error = "%s: %s" % (type(problem).__name__, problem)
            log("job %d failed: %s" % (job["id"], error))
        try:
            post(base, key, {"action": "finish", "job_id": job["id"], "error": error[:480]})
        except (RuntimeError, OSError) as problem:
            log("could not report job %d: %s" % (job["id"], problem))
        idle_since, unloaded = time.time(), False


if __name__ == "__main__":
    sys.exit(main())
