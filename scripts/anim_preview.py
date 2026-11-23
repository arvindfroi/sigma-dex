"""Battle animation previews for frame-2 tries (2026-11-23; Arvind: "gifen på nettsiden bør vises MED animasjonsscripet
(det bør vi også kunne velge btw)").

A preview is our own frame 1 and frame 2 played the way the game plays the battle animation the Pokemon borrows
(docs/ART.md, "Battle animation"). The player that knows how the game moves a sprite reads game data, so it is PRIVATE:
it lives outside this repository on the drawing PC (SIGMA_ANIM_DIR, default D:\\LocalAI\\sigma-private\\anim, holding
poke_anim.py and its data/). Without it nothing happens and the website keeps showing the plain frame flip.

This file only finds the animation a Pokemon borrows (its engine.anim_from, else the closest official Pokemon from
scripts/anim_pick.py), asks the player for an animated WebP and hands it in (sprite-worker action try_anim)."""
import importlib.util
import json
import os
from pathlib import Path

from PIL import Image

import anim_pick
import dexlib

ANIM_DIR = Path(os.environ.get("SIGMA_ANIM_DIR", r"D:\LocalAI\sigma-private\anim"))
SIZE = (128, 128)                      # room for the moves: an 80x80 sprite, shifted and stretched
_player, _official, _picks = None, None, None


def player():
    """the private player module, or None"""
    global _player
    if _player is None:
        path = ANIM_DIR / "poke_anim.py"
        if not path.exists():
            _player = False
        else:
            os.environ.setdefault("POKE_ANIM_DATA", str(ANIM_DIR / "data"))
            spec = importlib.util.spec_from_file_location("poke_anim", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _player = module
    return _player or None


def official_number(name):
    global _official
    if _official is None:
        rows = json.loads((dexlib.ROOT / "data" / "engine" / "official_species.json").read_text(encoding="utf-8"))["species"]
        _official = {o["name"]: o["n"] for o in rows}
    return _official.get(name)


def donor_for(species_id):
    """the official Pokemon whose animation this one uses (its own pick in the dex, else the closest)"""
    global _picks
    data = {sid: d for sid, _, d in dexlib.load_species()[0]}.get(species_id) or {}
    if not (data.get("engine") or {}).get("anim_from") and _picks is None:
        _picks = anim_pick.all_picks()
    return anim_pick.donor(species_id, data, _picks)


def make(frame1, frame2, donor, face, out):
    """write an animated WebP of our two frames played as `donor`'s front or back animation; None if it cannot"""
    p = player()
    number = official_number(donor) if donor else None
    if not p or not number:
        return None
    frames = p.preview(Image.open(frame1), Image.open(frame2), number, face, size=SIZE)
    frames[0].save(out, format="WEBP", save_all=True, append_images=frames[1:], duration=33, loop=0, lossless=True)
    return out


def hand_in(post, base, key, job_id, try_id, donor, path):
    return post(base, key, {"action": "try_anim", "job_id": job_id, "try_id": try_id, "donor": donor}, {"anim": path})


def after_try(post, base, key, job, try_id, frame1, frame2, folder, log):
    """right after a FRONT 2 / BACK 2 try is handed in: its preview with the animation the Pokemon borrows now"""
    if not player():
        return
    try:
        donor = donor_for(job["species_id"])
        out = make(frame1, frame2, donor, "front" if job["stage"] == "front2" else "back", Path(folder) / ("anim_%d.webp" % try_id))
        if out:
            hand_in(post, base, key, job["id"], try_id, donor, out)
    except Exception as problem:                     # a preview must never cost the picture
        log("animation preview of try %s failed: %s" % (try_id, problem))


def run_job(job, base, key, post, download, folder, log):
    """an 'animprev' job: someone picked another animation on the website (or a preview was missing)"""
    if not player():
        raise RuntimeError("no animation player on this PC (SIGMA_ANIM_DIR)")
    t = job.get("from_try") or {}
    first = (t.get("parent") or {}).get("image")
    if not t.get("image") or not first or t.get("stage") not in ("front2", "back2"):
        raise RuntimeError("that frame 2 or its frame 1 is missing")
    try:
        donor = json.loads(job.get("prompt") or "{}").get("donor")
    except ValueError:
        donor = None
    donor = donor or donor_for(job["species_id"])
    f1 = download(base, first, folder / "f1.png")
    f2 = download(base, t["image"], folder / "f2.png")
    out = make(f1, f2, donor, "front" if t["stage"] == "front2" else "back", folder / "anim.webp")
    if not out:
        raise RuntimeError("no animation for %r" % donor)
    hand_in(post, base, key, job["id"], t["id"], donor, out)
    return 1
