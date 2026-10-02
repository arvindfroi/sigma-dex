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

import yaml

import comfy
import dexlib
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
    views = {"front": settings["poses"].get(job.get("pose") or "front", settings["front"]), "back": settings["back"]}
    refs = list(job.get("refs") or [])
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
            out[view] = ("%s Redraw the creature picture in <image1> with these changes: %s Keep everything else about it the same: same creature, same pose, same view, same colors.%s"
                         % (style, " ".join(c if c.rstrip().endswith((".", "!", "?")) else c.rstrip() + "." for c in changes), others),
                         [parent["raw_" + view]] + refs)
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


def sprite_pixels(species_id, view):
    """How many pixels big the creature should be drawn, like official sprites of its strength.

    Measured on official GBA sprites: first stages are about 40 pixels (their backs 46), middle
    stages about 50, final stages and legendaries fill the 64 pixel frame.
    """
    stats = next((data.get("base_stats") or {} for sid, _, data in dexlib.load_species()[0] if sid == species_id), {})
    total = sum(v for v in stats.values() if isinstance(v, int))
    size = 42 if total and total < 360 else 52 if total and total < 480 else 62 if total else 52
    return min(63, size + 8) if view == "back" else size


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
    scale = sprite_pixels(species_id, view) * 8 / max(image.size)
    image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.LANCZOS)
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


def run(job, base, key, settings):
    style_version = hashlib.sha1(json.dumps([settings["style"], settings["illustration"], settings["poses"], settings["back"],
                                             settings["emerald_strength"]], sort_keys=True).encode()).hexdigest()[:10]
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
        for number in range(job["variations"]):
            seed = job["id"] * 100 + number          # the same request always gives the same pictures
            raw = {}
            for view, recipe in plan.items():
                raw[view] = folder / ("%d_%s.png" % (number, view))
                if recipe is None:
                    download(base, job["parent"]["raw_" + view], raw[view])
                else:
                    comfy.generate(recipe[0], raw[view], [local(p) for p in recipe[1]], seed=seed, transparent=True, quiet=True)
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
            sprites.build(job["species_id"], final, note="AI draft", grid=grid, out=out, detail=detail)
            small = {}
            for view in ("front", "back"):
                small[view] = folder / ("%d_%s_64.png" % (number, view))
                sprites.as_rgba(out / (view + ".png")).save(small[view])
            prompt = ("style: %s%s, pose: %s\n\n" % (job.get("style", "pixel"), " (%s)" % recipe if recipe else "", job.get("pose", "front"))) + "\n\n".join("%s: %s" % (view, recipe[0] if recipe else "(kept from the earlier sprite)") for view, recipe in plan.items())
            post(base, key, {"action": "candidate", "job_id": job["id"], "seed": seed, "prompt": prompt, "style_version": style_version},
                 {"raw_front": raw["front"], "raw_back": raw["back"], "front": small["front"], "back": small["back"], "preview": out / "preview.png"})
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
