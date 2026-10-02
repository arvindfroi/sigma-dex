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
    style = " ".join(settings["style"].split())
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
            out[view] = ("%s Redraw the sprite in <image1> with these changes: %s Keep everything else about the sprite the same: same creature, same pose, same view, same colors.%s"
                         % (style, " ".join(c if c.rstrip().endswith((".", "!", "?")) else c.rstrip() + "." for c in changes), others),
                         [parent["raw_" + view]] + refs)
        else:
            subject = "The creature is the one shown in <image1>. " if refs else ""
            out[view] = ("%s %s%s %s" % (style, subject, " ".join(settings[view].split()), job["look"]), refs)
    return out


def run(job, base, key, settings):
    style_version = hashlib.sha1(json.dumps([settings["style"], settings["front"], settings["back"]]).encode()).hexdigest()[:10]
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
            sprites.build(job["species_id"], raw, note="AI draft", grid=64, out=out)
            small = {}
            for view in ("front", "back"):
                small[view] = folder / ("%d_%s_64.png" % (number, view))
                sprites.as_rgba(out / (view + ".png")).save(small[view])
            prompt = "\n\n".join("%s: %s" % (view, recipe[0] if recipe else "(kept from the earlier sprite)") for view, recipe in plan.items())
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
