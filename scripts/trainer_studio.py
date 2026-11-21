r"""The trainer studio on the drawing PC (2026-11-21): a trainer's battle sprite AND map figure from a person's picture.

Each try makes both (Arvind: the studio mirrors the Pokemon sprite studio; one text box, the rest from the picture and the base):
1. BATTLE, the SWAP method (docs/ART.md#the-trainer-studio): a real gen 4 trainer class sprite with a body and pose like the
   one wanted is the START picture (frame 1 on magenta, 320 px), and the trainer LoRA (Klein, CREATE task: image 1 = the
   person's picture) repaints it from `strength` of the way down (SplitSigmasDenoise). The text = the base's class, pose,
   facing and build + the person's own words. Then klein_follower.to_back (80x80) and trainer_post.battle (T 40: lone pixels,
   closed outline, 15 colours, feet 1 px up).
2. MAP FIGURE: the NPC LoRA pkmn_followernpc_klein_v2 (checkpoint 1000; 750-1250 are best, the final one draws too tall),
   image 1 = the new battle sprite 4x on white, image 2 = the person's picture, the same words; 512x256 in the follower
   layout -> klein_follower.to_game -> trainer_post.to16 (the game's 16 NPC frames) -> trainer_post.overworld (one 15-colour
   palette, lone pixels cleaned). Held items drop out of some frames on some seeds: that is why there are several tries.
The swap core is the Legion's lora-train\v6cfg\trainer_swap.py (`graph`); the bases and their captions live only on the PC
(no Nintendo pictures in the repository): build_trainer_klein.frames / rows read them.

A job (sprite_jobs, stage 'trainer'): species_id = the slot ('trainer-<role>' or 'npc-<id>'), recipe = the base
('hgss:12' or 'pt:beauty'), prompt = JSON {strength, words, photo} (older jobs: fields), refs = a public trainer picture when
no private photo was uploaded. Each try: seed = job id x 100 + n (both steps); image = the 80x80 battle sprite, raw = the
model's 320 px battle picture, overworld = the 512x32 map sheet.

Settings: TRAINER_CFG (folder with trainer_swap.py and build_trainer_klein*.py, default D:\LocalAI\lora-train\v6cfg),
TRAINER_LORA (default pkmn_trainer_klein_c1_000002500.safetensors), NPC_LORA (default pkmn_followernpc_klein_v2_000001000).
"""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

import comfy
import klein_follower
import trainer_post

CFG = Path(os.environ.get("TRAINER_CFG", r"D:\LocalAI\lora-train\v6cfg"))
LORA = os.environ.get("TRAINER_LORA", "pkmn_trainer_klein_c1_000002500.safetensors")
NPC_LORA = os.environ.get("NPC_LORA", "pkmn_followernpc_klein_v2_000001000.safetensors")
FIELDS = ("cls", "who", "skin", "hair", "clothes", "extra", "held", "pose", "facing", "build", "mood")
SECONDS = 40
NPC_END = ("The sheet is a grid of 2 rows by 4 columns of 32x32 pixel art frames on a flat magenta background: the columns walk up "
           "(seen from behind), down (facing the viewer, as in image 1), left and right; the top row is the first step and the bottom "
           "row the second step. The same person in every frame, with the colours of image 1, drawn as a small overworld character "
           "with a big head, and a one-pixel dark outline.")


def _modules():
    if str(CFG) not in sys.path:
        sys.path.insert(0, str(CFG))
    import build_trainer_klein as T
    import build_trainer_klein_b as TB
    import trainer_swap as S
    return T, TB, S


def base_key(recipe):
    """'hgss:12' -> 12, 'pt:beauty' -> 'pt/beauty' (what build_trainer_klein.frames takes)."""
    game, _, name = str(recipe or "").partition(":")
    if game == "hgss" and name.isdigit():
        return int(name)
    if game == "pt" and name and all(c.isalnum() or c == "_" for c in name):
        return "pt/" + name
    raise RuntimeError("unknown base trainer %r" % recipe)


def words_of(settings):
    """the person's own words (one box); older jobs sent the eleven fields"""
    w = " ".join(str(settings.get("words") or "").split())[:400]
    if not w and settings.get("fields"):
        f = settings["fields"]
        w = ", ".join(str(f[k]).strip() for k in ("who", "hair", "clothes", "extra", "held") if str(f.get(k) or "").strip() not in ("", "-"))
    return w


def battle_text(base_row, words):
    """the base's class, pose, facing and build (the start picture already has them) + the person's words; the look comes from
    the picture"""
    T, TB, _ = _modules()
    row = {k: (base_row or {}).get(k) or "-" for k in ("cls", "pose", "facing", "build")}
    if row["cls"] == "-":
        row["cls"] = "Trainer"
    row["who"] = words or "-"
    return TB.caption(T.describe(row, drop=0), True)


def npc_text(words, has_photo):
    return ("human trainer npc. Create the overworld walking sprite sheet from Pokemon HeartGold of the trainer in image 1 and image 2: "
            + ("image 1 is their front battle sprite, image 2 is their official artwork. " if has_photo else "image 1 and image 2 are their front battle sprite. ")
            + "A trainer: " + (words or "the person in the pictures") + ". How they move: They walk upright on two legs. " + NPC_END)


def square(src, out, side=320, fit=300):
    """a picture centred on white in a side x side square (the NPC LoRA's image 2)"""
    im = Image.open(src).convert("RGBA")
    flat = Image.new("RGBA", im.size, (255, 255, 255, 255))
    flat.alpha_composite(im)
    im = flat.convert("RGB")
    k = fit / max(im.size)
    im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    bg = Image.new("RGB", (side, side), "white")
    bg.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
    bg.save(out)
    return out


def on_white(sprite, out):
    """the 80x80 battle sprite on white at 4x (image 1 of the NPC LoRA)"""
    ref = Image.new("RGBA", sprite.size, (255, 255, 255, 255))
    ref.alpha_composite(sprite.convert("RGBA"))
    ref.convert("RGB").resize((sprite.width * 4, sprite.height * 4), Image.NEAREST).save(out)
    return out


def person_picture(src, out):
    """The uploaded picture as image 1: flattened on white, at most 1024 px on its long side (Klein encodes it at its own
    size, as in the proved test)."""
    im = Image.open(src)
    im.load()
    im = im.convert("RGBA")
    flat = Image.new("RGBA", im.size, (255, 255, 255, 255))
    flat.alpha_composite(im)
    flat = flat.convert("RGB")
    flat.thumbnail((1024, 1024), Image.LANCZOS)
    flat.save(out)
    return out


def fetch(url, target):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "sigma-dex"}), timeout=120) as response:
        Path(target).write_bytes(response.read())
    return Path(target)


def run(job, base, key, post, download, folder, log=print):
    T, TB, S = _modules()
    settings = json.loads(job.get("prompt") or "{}")
    strength = min(0.95, max(0.5, float(settings.get("strength") or 0.75)))
    words = words_of(settings)
    count = int(job.get("count") or 1)
    bkey = base_key(job.get("recipe"))
    # the person's picture: the private upload (a two-minute link from the server) or a public trainer picture
    if settings.get("photo"):
        link = post(base, key, {"action": "trainer_photo", "job_id": job["id"]})["url"]
        if link.startswith("/"):
            link = base + "/storage/v1" + link
        got = fetch(link, folder / "photo_in")
    elif job.get("refs"):
        got = download(base, job["refs"][0], folder / "photo_in")
    else:
        raise RuntimeError("no picture of the trainer")
    art = comfy.upload(person_picture(got, folder / "person.png"))
    art2 = comfy.upload(square(got, folder / "person_sq.png"))
    start = S.start(bkey, folder / "start.png")
    text = battle_text(T.rows().get(bkey), words)
    ntext = npc_text(words, True)
    made = 0
    for n in range(1, count + 1):
        seed = job["id"] * 100 + n
        row = post(base, key, {"action": "try_start", "job_id": job["id"], "n": n, "seed": seed,
                               "recipe": ("%s d%.2f" % (job.get("recipe"), strength))[:60], "expected_seconds": SECONDS})
        post(base, key, {"action": "progress", "job_id": job["id"], "state": "drawing a trainer: %d of %d" % (n, count)})
        started = time.time()
        try:
            raw = folder / ("raw%d.png" % n)
            raw.write_bytes(comfy.run(S.graph(text, [art], seed, LORA, start, strength)))
            sprite = trainer_post.battle(klein_follower.to_back(raw))
            image = folder / ("trainer%d.png" % n)
            sprite.save(image)
            status = "done" if sprite.getbbox() else "broken"
            files = {"image": image, "raw": raw}
            note = "base %s, strength %.2f, seed %d" % (job.get("recipe"), strength, seed)
            if status == "done":
                post(base, key, {"action": "progress", "job_id": job["id"], "state": "drawing a map figure: %d of %d" % (n, count)})
                try:
                    one = comfy.upload(on_white(sprite, folder / ("battle%d_4x.png" % n)))
                    nraw = folder / ("npcraw%d.png" % n)
                    nraw.write_bytes(comfy.run(comfy.klein(ntext, [one, art2], 512, 256, seed, "sigma/trainernpc", lora=NPC_LORA)))
                    sheet = trainer_post.overworld(trainer_post.to16(klein_follower.to_game(nraw, mirror_right=False).convert("RGBA")))
                    ow = folder / ("overworld%d.png" % n)
                    sheet.save(ow)
                    files["overworld"] = ow
                    note += ", map figure %s" % NPC_LORA.replace(".safetensors", "")
                except Exception as problem:                          # the battle sprite still counts
                    log("map figure of try %d of job %d failed: %s" % (n, job["id"], problem))
                    note += ", no map figure (%s)" % type(problem).__name__
        except Exception as problem:                                  # one bad picture must not stop the others
            log("trainer try %d of job %d failed: %s" % (n, job["id"], problem))
            post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": row["id"], "status": "failed",
                             "note": ("%s: %s" % (type(problem).__name__, problem))[:300], "seconds": round(time.time() - started, 1)})
            continue
        post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": row["id"], "status": status,
                         "note": note[:300], "seconds": round(time.time() - started, 1)}, files)
        made += 1
    return made


# ---------- step 4 VS: the VS-screen portrait (2026-11-21). The VS LoRA (trained 12 Nov, step 2000; Arvind on kind "both":
# "looks much better") draws it from the battle sprite (image 1, 80x80 on magenta at 4x) and the person's picture (image 2,
# on white at 320), with the text of lora-train\v6cfg\vs_gen.py. 384x256 -> the game's 96x64 portrait, 15 colours.
VS_LORA = os.environ.get("TRAINER_VS_LORA", "pkmn_vs_klein_v1_000002000.safetensors")
VS_SECONDS = 25


def vs_text(V, cls, words):
    r = {"who": (words or "").strip().rstrip(".") or "a trainer", "gesture": "a hand raised in a confident gesture"}
    text = V.caption(V.describe(r, cls, 0), True)
    return text.replace("clothes and colours. ", "clothes and colours. Image 2 is a photo of the same person: keep their real face, age and build. ", 1)


def run_vs(job, base, key, post, download, folder, log=print):
    T, _, S = _modules()
    if str(CFG) not in sys.path:
        sys.path.insert(0, str(CFG))
    import build_vs_klein as V
    settings = json.loads(job.get("prompt") or "{}")
    src = job.get("from_try") or {}
    if not src.get("image"):
        raise RuntimeError("the VS portrait needs the battle sprite")
    sprite = Image.open(download(base, src["image"], folder / "battle.png")).convert("RGBA")
    T.on_magenta(sprite).save(folder / "vs_sprite.png")
    if settings.get("photo"):
        link = post(base, key, {"action": "trainer_photo", "job_id": job["id"]})["url"]
        if link.startswith("/"):
            link = base + "/storage/v1" + link
        got = fetch(link, folder / "photo_in")
    elif job.get("refs"):
        got = download(base, job["refs"][0], folder / "photo_in")
    else:
        raise RuntimeError("no picture of the trainer")
    square(got, folder / "vs_photo.png")
    refs = [comfy.upload(folder / "vs_sprite.png"), comfy.upload(folder / "vs_photo.png")]
    row = T.rows().get(base_key(job.get("recipe"))) or {}
    text = vs_text(V, row.get("cls") or "Pokemon Trainer", settings.get("words") or "")
    made = 0
    for n in range(1, int(job.get("count") or 1) + 1):
        seed = job["id"] * 100 + n
        t = post(base, key, {"action": "try_start", "job_id": job["id"], "n": n, "seed": seed,
                             "recipe": VS_LORA.replace(".safetensors", "").replace("pkmn_", "")[:60], "expected_seconds": VS_SECONDS})
        post(base, key, {"action": "progress", "job_id": job["id"], "state": "drawing a VS portrait: %d of %d" % (n, int(job.get("count") or 1))})
        started = time.time()
        try:
            raw = folder / ("vs_raw%d.png" % n)
            raw.write_bytes(comfy.run(comfy.klein(text, refs, 384, 256, seed, "sigma/trainervs", lora=VS_LORA)))
            portrait = klein_follower.to_back(raw)
            image = folder / ("vs%d.png" % n)
            portrait.save(image)
            status = "done" if portrait.size == (96, 64) and portrait.getbbox() else "broken"
            post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": t["id"], "status": status,
                             "note": "VS portrait from battle sprite #%s + the picture, seed %d" % (src.get("id"), seed),
                             "seconds": round(time.time() - started, 1)}, {"image": image, "raw": raw})
            made += 1
        except Exception as problem:
            log("VS try %d of job %d failed: %s" % (n, job["id"], problem))
            post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": t["id"], "status": "failed",
                             "note": ("%s: %s" % (type(problem).__name__, problem))[:300], "seconds": round(time.time() - started, 1)})
    return made
