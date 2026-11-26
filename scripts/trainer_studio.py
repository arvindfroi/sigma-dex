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
import re
import os
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

import comfy
import klein_follower
import trainer_post

CFG = Path(os.environ.get("TRAINER_CFG", r"D:\LocalAI\lora-train\v6cfg"))
LORA = os.environ.get("TRAINER_LORA", "pkmn_trainer_klein_c1_000002500.safetensors")
NPC_LORA = os.environ.get("NPC_LORA", "pkmn_followernpc_klein_v2_000001000.safetensors")
FIELDS = ("cls", "who", "skin", "hair", "clothes", "extra", "held", "pose", "facing", "build", "mood")
SECONDS = 40
# 2026-11-24 (Arvind: "jeg skjønner ikke hvorfor han lager en map sprite når vi lager front spriten"): a front try no longer
# draws a map figure; the MAP step makes them from the picked front (run_map). TRAINER_FRONT_MAP=1 brings the old way back.
FRONT_MAP = os.environ.get("TRAINER_FRONT_MAP") == "1"
SECONDS = 40 if FRONT_MAP else 25          # a front with its map figure took about 40 s
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


# Origin's own trainer pictures (2026-11-24, Arvind: "alle origins sprites burde også være der"): the classes Origin redrew
# in its a/0/5/8 (Red, Leaf, Steven, Cynthia, Gold, Lance, Misty ...), frame 1 as the game shows it (member 0 placed by
# cell 0, scripts/trainer_bases.py --origin). Like the other bases they live on the PC only:
# lora-train\data\trainers\origin_fronts\NNN.png (NNN = the class).
ORIGIN_FRONTS = Path(os.environ.get("TRAINER_ORIGIN", r"D:\LocalAI\lora-train\data\trainers\origin_fronts"))
_BASE_INDEX = None


def _origin_slot(recipe):
    game, _, name = str(recipe or "").partition(":")
    return int(name) if game == "origin" and name.isdigit() and len(name) <= 3 else None


def base_frame(recipe):
    """frame 1 of a base, 80x80 RGBA"""
    n = _origin_slot(recipe)
    if n is not None:
        f = ORIGIN_FRONTS / ("%03d.png" % n)
        if not f.exists():
            raise RuntimeError("unknown base trainer %r" % recipe)
        return Image.open(f).convert("RGBA")
    T, _, _ = _modules()
    return T.frames(base_key(recipe))[0]


def base_row(recipe):
    """the base's caption fields (cls, pose, facing, build ...); an Origin base has the fields of data/trainer_bases.json"""
    global _BASE_INDEX
    if _origin_slot(recipe) is not None:
        if _BASE_INDEX is None:
            f = Path(__file__).resolve().parent.parent / "data" / "trainer_bases.json"
            _BASE_INDEX = {b["id"]: b for b in json.loads(f.read_text(encoding="utf-8"))["bases"]} if f.exists() else {}
        b = _BASE_INDEX.get(str(recipe)) or {}
        return dict(b.get("fields") or {}, cls=(b.get("fields") or {}).get("cls") or "Trainer")
    T, _, _ = _modules()
    return T.rows().get(base_key(recipe)) or {}


def mirrored_row(row):
    """the caption of a mirrored base: left and right swapped in the facing and the pose"""
    swap = {"left": "right", "right": "left"}
    return {k: re.sub(r"\b(left|right)\b", lambda m: swap[m.group(1)], v) if isinstance(v, str) else v for k, v in row.items()}


def fields_of(settings):
    """the description fields the person filled in (2026-11-24: the PICTURE step's fields, as in trainer_swap.py P)"""
    f = settings.get("fields") or {}
    return {k: " ".join(str(f[k]).split())[:240] for k in FIELDS if str(f.get(k) or "").strip() not in ("", "-")}


def words_of(settings):
    """one line about the person for the steps after the front (VS, back, map): the look fields, then the free words"""
    w = " ".join(str(settings.get("words") or "").split())[:400]
    f = fields_of(settings)
    look = ", ".join(f[k] for k in ("who", "skin", "hair", "clothes", "extra", "held") if f.get(k))
    return ", ".join(x for x in (look, w) if x)


def battle_text(base_row, words, fields=None):
    """the caption of the tested recipe (trainer_swap.py: TB.caption(T.describe(P))): the base's class, pose, facing and build
    (the start picture already has them) with the person's description fields over them, and their free words; the face and
    colours come from the picture. Without fields: the base's four + the words as 'who' (2026-11-21 recipe)."""
    T, TB, _ = _modules()
    row = {k: (base_row or {}).get(k) or "-" for k in ("cls", "pose", "facing", "build")}
    if row["cls"] == "-":
        row["cls"] = "Trainer"
    f = dict(fields or {})
    if f:
        row.update(f)
        if words:
            row["extra"] = ", ".join(x for x in (f.get("extra"), words) if x)
        row.setdefault("who", "a trainer")
        row.setdefault("held", "a Poke Ball")
    else:
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
    recipe = job.get("recipe")
    base_frame(recipe)                               # an unknown base fails here, before the picture is fetched
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
    width = min(1.4, max(0.7, float(settings.get("width") or 1.0)))   # 2026-11-24: thinner too (0.7), not only wider
    height = min(1.1, max(0.85, float(settings.get("height") or 1.0)))   # 2026-11-24: shorter (a child) or taller
    flip = bool(settings.get("flip"))                # the BASE step's mirror (2026-11-24): the base turned the other way
    f1 = base_frame(recipe)
    if flip:
        f1 = ImageOps.mirror(f1)
    if width != 1.0 or height != 1.0:                # the BASE step's width and height sliders
        f1 = reshape_front(f1, width, height)
    f1.save(folder / "base_start.png")
    start = S.start("file:" + str(folder / "base_start.png"), folder / "start.png")
    row = base_row(recipe)
    text = battle_text(mirrored_row(row) if flip else row, " ".join(str(settings.get("words") or "").split())[:400], fields_of(settings))
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
            note = "base %s%s%s%s, strength %.2f, seed %d" % (recipe, " x%.2f wide" % width if width != 1.0 else "", " x%.2f tall" % height if height != 1.0 else "",
                                                             " mirrored" if flip else "", strength, seed)
            if status == "done" and FRONT_MAP:
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


# 2026-11-26 Arvind: "many VS sprites look very alike". Cause: every portrait was asked for the same pose
# ("a hand raised in a confident gesture", plain: "holding a Poke Ball") and the caption ended "often with a hand in a strong
# gesture". The LoRA was trained with varied gesture/facing/mood words (vs_captions.tsv), so each try now gets its own from this
# list (same vocabulary as the training words), unless the person wrote a pose (settings or settings.fields: pose / facing / mood).
VS_POSES = [
    ("one fist raised beside the head", "turned to the right", "calm, determined"),
    ("hand on hip", "facing the viewer", "sly smile"),
    ("holding the ball up at the side", "facing the viewer", "calm, confident"),
    ("arms crossed over the chest", "facing the viewer", "confident smirk"),
    ("hand resting on cheek", "facing the viewer", "sweet smile"),
    ("pointing at the viewer with two fingers", "turned to the left", "fierce, determined"),
    ("both fists raised", "facing the viewer", "eager grin"),
    ("hand held near the chest", "turned to the left", "cool, serious"),
    ("one arm swung out to the side", "turned to the left", "excited open-mouth smile"),
    ("hand raised in a salute", "facing the viewer", "cocky grin"),
    ("hand tipping the hat", "facing the viewer", "amused smile"),
    ("thumb pointing at himself", "facing the viewer", "eyes closed, relaxed smile"),
    ("fist held up near the chest", "turned to the right", "calm, serious"),
    ("hand on chin", "facing the viewer", "sly smirk"),
    ("making a peace sign", "facing the viewer", "cheerful grin"),
    ("arm stretched out to the side", "turned to the left", "confident grin"),
    ("hands held low near the chest", "turned to the left", "calm, shy"),
    ("fist raised in front of the chest", "turned to the right", "smug smirk"),
]


def vs_pose(settings, seed, n):
    """(gesture, facing, mood) for try n: the person's own words win; the rest comes from VS_POSES, a different one per try"""
    import random as _random
    g, f, m = _random.Random(seed).choice(VS_POSES)
    fields = settings.get("fields") if isinstance(settings.get("fields"), dict) else {}
    own = lambda k: " ".join(str(settings.get(k) or fields.get(k) or "").split())[:120]
    return own("pose") or g, own("facing") or f, own("mood") or m


def vs_text(V, cls, words, plain=False, pose=None, fields=None):
    """plain (2026-11-23, vs_gen.py NODESC; tried on one test person: it looked more like them): no clothes or extra
    words, so the likeness comes from the pictures. 2026-11-26 (Arvind: Stevie Wonder's VS "ble bare en hvit person",
    "det virker jo som de ikke ser på bildet"): since the PICTURE fields (11-24) the person's words live in `fields`, not
    `words`, and this step only read `words`, so every VS was asked for "a trainer" with no skin, hair or glasses. The VS LoRA
    learnt from 54 portraits that are nearly all fair-skinned, so without the words it draws a light face whatever the
    pictures show. Now the fields go in like the other steps; plain keeps skin, hair and extras (glasses, moustache), the
    things that make the face, and leaves clothes and held items to the pictures."""
    g, f, m = pose or VS_POSES[0]
    fd = dict(fields or {})
    w = (words or "").strip().rstrip(".")
    who = fd.get("who") or w or "a trainer"
    if fd.get("build"):
        who = "%s, %s build" % (who, fd["build"])               # describe() has no build field (as in vs_gen.py)
    if plain:
        r = {"who": who, "skin": fd.get("skin"), "hair": fd.get("hair"), "extra": fd.get("extra")}
        desc = V.describe(r, "trainer", 0)
    else:
        r = {"who": who, "skin": fd.get("skin"), "hair": fd.get("hair"), "clothes": fd.get("clothes"),
             "extra": ", ".join(x for x in (fd.get("extra"), w if fd.get("who") else "") if x), "held": fd.get("held")}
        desc = V.describe(r, cls, 0)
    desc += "Gesture: %s. Facing: %s. Mood: %s. " % (g, f, m)
    text = V.caption(desc, True).replace("often with a hand in a strong gesture", "with the pose given in the words")
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
    ph = Image.open(person_picture(got, folder / "vs_photo_full0.png")).convert("RGB")   # PHOTOFULL: own size, up to 1 MP
    k = min(1.0, (1024 * 1024 / (ph.width * ph.height)) ** 0.5)
    ph.resize((max(16, round(ph.width * k) // 16 * 16), max(16, round(ph.height * k) // 16 * 16)), Image.LANCZOS).save(folder / "vs_photo_full.png")
    sprite_up = comfy.upload(folder / "vs_sprite.png")
    refs_of = {False: [sprite_up, comfy.upload(folder / "vs_photo.png")], True: [sprite_up, comfy.upload(folder / "vs_photo_full.png")]}
    row = base_row(job.get("recipe"))
    made = 0
    for n in range(1, int(job.get("count") or 1) + 1):
        seed = job["id"] * 100 + n
        t = post(base, key, {"action": "try_start", "job_id": job["id"], "n": n, "seed": seed,
                             "recipe": VS_LORA.replace(".safetensors", "").replace("pkmn_", "")[:60], "expected_seconds": VS_SECONDS})
        post(base, key, {"action": "progress", "job_id": job["id"], "state": "drawing a VS portrait: %d of %d" % (n, int(job.get("count") or 1))})
        started = time.time()
        try:
            raw = folder / ("vs_raw%d.png" % n)
            plain = n % 2 == 0                           # half the tries without the description (tested only on one person)
            pose = vs_pose(settings, seed, n)
            text = vs_text(V, row.get("cls") or "Pokemon Trainer", settings.get("words") or "", plain, pose, fields_of(settings))
            raw.write_bytes(comfy.run(comfy.klein(text, refs_of[plain], 384, 256, seed, "sigma/trainervs", lora=VS_LORA)))
            portrait = klein_follower.to_back(raw)
            image = folder / ("vs%d.png" % n)
            portrait.save(image)
            status = "done" if portrait.size == (96, 64) and portrait.getbbox() else "broken"
            post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": t["id"], "status": status,
                             "note": "VS portrait from battle sprite #%s + the picture%s, seed %d, pose: %s / %s / %s" % (src.get("id"), " (no description, full-size picture)" if plain else "", seed, pose[0], pose[1], pose[2]),
                             "seconds": round(time.time() - started, 1)}, {"image": image, "raw": raw})
            made += 1
        except Exception as problem:
            log("VS try %d of job %d failed: %s" % (n, job["id"], problem))
            post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": t["id"], "status": "failed",
                             "note": ("%s: %s" % (type(problem).__name__, problem))[:300], "seconds": round(time.time() - started, 1)})
    return made


# ---------- step MAP: more map figures for the picked battle sprite (2026-11-21). The way the first two test figures were
# made (Arvind: "they look great"): NPC LoRA v2, image 1 = the battle sprite 4x on white, image 2 = the person's picture, the
# person's words (+ a few words for the map figure only, e.g. "no hat"), then to16 + trainer_post.overworld. Checkpoints
# 750-1250 are the good ones and held items drop out on some seeds, so each try takes the next checkpoint and its own seed.
MAP_CKPTS = [c.strip() for c in os.environ.get("NPC_MAP_CKPTS", "1000,750,1250").split(",") if c.strip()]
MAP_SECONDS = 30


def run_map(job, base, key, post, download, folder, log=print):
    settings = json.loads(job.get("prompt") or "{}")
    src = job.get("from_try") or {}
    if not src.get("image"):
        raise RuntimeError("the map figure needs the battle sprite")
    sprite = Image.open(download(base, src["image"], folder / "battle.png")).convert("RGBA")
    if settings.get("photo"):
        link = post(base, key, {"action": "trainer_photo", "job_id": job["id"]})["url"]
        if link.startswith("/"):
            link = base + "/storage/v1" + link
        got = fetch(link, folder / "photo_in")
    elif job.get("refs"):
        got = download(base, job["refs"][0], folder / "photo_in")
    else:
        raise RuntimeError("no picture of the trainer")
    one = comfy.upload(on_white(sprite, folder / "battle_4x.png"))
    art2 = comfy.upload(square(got, folder / "person_sq.png"))
    words = words_of(settings)
    extra = " ".join(str(settings.get("extra") or "").split())[:200]
    text = npc_text((words + (". " + extra if extra else "")).strip(" ."), True)
    count = int(job.get("count") or 1)
    made = 0
    for n in range(1, count + 1):
        seed = job["id"] * 100 + n
        ck = MAP_CKPTS[(n - 1) % len(MAP_CKPTS)]
        lora = "pkmn_followernpc_klein_v2.safetensors" if ck == "final" else "pkmn_followernpc_klein_v2_%09d.safetensors" % int(ck)
        t = post(base, key, {"action": "try_start", "job_id": job["id"], "n": n, "seed": seed,
                             "recipe": ("followernpc v2 c%s" % ck)[:60], "expected_seconds": MAP_SECONDS})
        post(base, key, {"action": "progress", "job_id": job["id"], "state": "drawing a map figure: %d of %d" % (n, count)})
        started = time.time()
        try:
            nraw = folder / ("map_raw%d.png" % n)
            nraw.write_bytes(comfy.run(comfy.klein(text, [one, art2], 512, 256, seed, "sigma/trainermap", lora=lora)))
            sheet = trainer_post.overworld(trainer_post.to16(klein_follower.to_game(nraw, mirror_right=False).convert("RGBA")))
            ow = folder / ("map%d.png" % n)
            sheet.save(ow)
            status = "done" if sheet.size == (512, 32) and sheet.getbbox() else "broken"
            post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": t["id"], "status": status,
                             "note": ("map figure from battle sprite #%s, checkpoint %s, seed %d%s" % (src.get("id"), ck, seed, ", extra: " + extra if extra else ""))[:300],
                             "seconds": round(time.time() - started, 1)}, {"image": ow, "overworld": ow, "raw": nraw})
            made += 1
        except Exception as problem:
            log("map try %d of job %d failed: %s" % (n, job["id"], problem))
            post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": t["id"], "status": "failed",
                             "note": ("%s: %s" % (type(problem).__name__, problem))[:300], "seconds": round(time.time() - started, 1)})
    return made


def _photo(job, settings, base, key, post, download, folder):
    """the person's picture: the private upload (a two-minute link) or a public trainer picture"""
    if settings.get("photo"):
        link = post(base, key, {"action": "trainer_photo", "job_id": job["id"]})["url"]
        if link.startswith("/"):
            link = base + "/storage/v1" + link
        return fetch(link, folder / "photo_in")
    if job.get("refs"):
        return download(base, job["refs"][0], folder / "photo_in")
    raise RuntimeError("no picture of the trainer")


def lock_palette(im, pal):
    """every pixel to the nearest colour of `pal` (frame 1's colours), alpha to 0/255; returns the picture and the mean
    distance the colours had to move (back_motion5_gen.lock)"""
    import numpy as np
    a = np.array(im.convert("RGBA"))
    a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
    m = a[..., 3] > 0
    px = a[m][:, :3].astype(int)
    if not len(px):
        return Image.fromarray(a), 99.0
    d = ((px[:, None, :] - pal[None]) ** 2).sum(-1)
    a[m, :3] = pal[d.argmin(1)]
    return Image.fromarray(a), float(np.sqrt(d.min(1)).mean())


def colours_of(im):
    import numpy as np
    a = np.array(im.convert("RGBA"))
    return np.unique(a[a[..., 3] >= 128][:, :3], axis=0).astype(int)


def widen_front(f, fx, fy=1.0):
    """a FRONT base frame widened by fx around the body centre, feet kept on the floor (widen_front.py, 2026-11-22)"""
    f = f.convert("RGBA")
    bb = f.getbbox()
    W, H = f.size
    w, h = round(W * fx), round(H * fy)
    g = f.resize((w, h), Image.NEAREST)
    cx = (bb[0] + bb[2]) / 2
    x0, y0 = round(cx * fx - cx), h - H
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.alpha_composite(g.crop((x0, y0, x0 + W, y0 + H)))
    return out


def reshape_front(f, fx, fy):
    """the BASE step's body width and height (2026-11-24): the figure scaled by fx and fy around its centre, the feet kept
    where they were; if the scaled figure would no longer fit the 80x80 frame it is made a little smaller as a whole"""
    f = f.convert("RGBA")
    bb = f.getbbox()
    if not bb:
        return f
    W, H = f.size
    fig = f.crop(bb)
    w, h = max(1, round(fig.width * fx)), max(1, round(fig.height * fy))
    k = min(1.0, (W - 2) / w, (bb[3] - 1) / h)              # keep a pixel free at the sides and the top
    w, h = max(1, round(w * k)), max(1, round(h * k))
    g = fig.resize((w, h), Image.NEAREST)
    cx = (bb[0] + bb[2]) / 2
    x0 = min(max(1, round(cx - w / 2)), W - 1 - w)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.alpha_composite(g, (x0, bb[3] - h))
    return out


def widen_back(f, fx):
    """a player BACK frame widened by fx (and a little lower), feet kept (back_f1_front.widen, 2026-11-22)"""
    f = f.convert("RGBA")
    bb = f.getbbox()
    W, H = f.size
    if fx == 1 or not bb:
        return f
    g = f.resize((round(W * fx), round(H * (1 - (fx - 1) * 0.15))), Image.NEAREST)
    cx = (bb[0] + bb[2]) / 2
    x0, y0 = round(cx * fx - cx), g.height - H
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.alpha_composite(g.crop((x0, max(0, y0), x0 + W, max(0, y0) + H)) if y0 >= 0 else g.crop((x0, 0, x0 + W, g.height)), (0, max(0, -y0)))
    return out


STOUT_WORDS = ("stout", "fat", "round", "sturdy", "chubby", "belly", "heavy", "plump", "big-bellied", "wide")


def is_stout(front, words):
    """the build words say so, or the front's torso is wide: median row width over the middle third / figure height > 0.45"""
    import numpy as np
    if any(w in (words or "").lower() for w in STOUT_WORDS):
        return True
    a = np.array(front.convert("RGBA"))[..., 3] > 0
    ys = np.nonzero(a.any(1))[0]
    if not len(ys):
        return False
    y0, y1 = ys.min(), ys.max() + 1
    mid = [a[y].sum() for y in range(y0 + (y1 - y0) // 3, y0 + 2 * (y1 - y0) // 3)]
    return float(np.median(mid)) / max(1, y1 - y0) > 0.45


# ---------- step ANIM (2026-11-22): the trainer's battle intro animation. Arvind's idea: people pick one of the animated
# classes' scripts (data/trainer_anims.json: poses = cells, shifts, timing from a/0/5/8) and get the extra poses drawn.
# Recipe v2 "side by side" (front_anim/approved_pair_v2, Arvind on the game GIF: "det ser sykt bra ut!"); v1 started from
# the leader's real pose and leaked its body. Each pose j > 0 = klein BASE (no LoRA) at 640x320: start = our battle sprite |
# our battle sprite (4x on magenta), only the right half re-noised (SetLatentNoiseMask), image 1 = our sprite, the text
# says what pose j shows (data/trainer_anim_poses.json: about the body, not the leader's things) + the person's words and
# build. The right half -> size lock (more than 8 % taller than frame 1: scaled down around the feet) -> 80x80 ->
# trainer_post.battle -> colours locked to the battle sprite. Image = a strip of 80x80 frames, frame j = cell j (cell 0 =
# the battle sprite; a cell the game has no pose for, as Koga's cell 3, = the battle sprite).
# Stage 2 (anim_trio_swap.py, tested on 4 people): before pixelizing, each pose panel is repainted once with the trainer LoRA
# c1 SWAP (image 1 = the battle sprite, start = the pose panel, denoise 0.55): keeps the pose and brings the face back.
ANIM_SECONDS = 45            # a pose (side by side + the swap)
ANIM_SWAP = float(os.environ.get("TRAINER_ANIM_SWAP", "0.55"))   # stage 2 denoise; 0 = off (0.65+ undid poses in the tests)
ANIM_STRICT = ("The trainer has exactly two arms and two hands, and both are part of the new pose: no arm or hand stays behind where it "
               "was in image 1. The hair is exactly as in image 1: the same length, shape and colour.")   # round 3: extra arms, longer hair
ANIM_SIZE = "exactly the same size as the left frame: the head just as big and the feet on the same line"
ANIM_LIKE = 0.22          # the most a new pose's colour shares may differ from the battle sprite's (good poses 0.06-0.19, drifted 0.25-0.57)
ANIM_TRIES = 3


def colour_gap(a, b):
    """half the summed difference of two sprites' colour shares (0 = the same colours in the same amounts, 1 = none shared)"""
    from collections import Counter
    def shares(im):
        px = [p[:3] for p in im.convert("RGBA").getdata() if p[3]]
        c = Counter(px)
        n = max(1, len(px))
        return {k: v / n for k, v in c.items()}
    x, y = shares(a), shares(b)
    return sum(abs(x.get(k, 0) - y.get(k, 0)) for k in set(x) | set(y)) / 2


def anim_scripts():
    here = Path(__file__).resolve().parent.parent / "data" / "trainer_anims.json"
    return {s["cls"]: s for s in json.loads(here.read_text(encoding="utf-8"))["scripts"]}


def anim_poses():
    here = Path(__file__).resolve().parent.parent / "data" / "trainer_anim_poses.json"
    return {int(k): v for k, v in json.loads(here.read_text(encoding="utf-8")).items() if k.isdigit()}


def pair_graph(text, ref, seed, start, mask):
    g = comfy.klein(text, [ref], 640, 320, seed, "sigma/animpair", lora=None)
    g["startimg"] = {"class_type": "LoadImage", "inputs": {"image": start}}
    g["startenc"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["startimg", 0], "vae": ["vae", 0]}}
    g["maskimg"] = {"class_type": "LoadImage", "inputs": {"image": mask}}
    g["mask"] = {"class_type": "ImageToMask", "inputs": {"image": ["maskimg", 0], "channel": "red"}}
    g["masked"] = {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["startenc", 0], "mask": ["mask", 0]}}
    g["sca"]["inputs"]["latent_image"] = ["masked", 0]
    return g


def fig_box(im):
    """the figure's box on a magenta panel"""
    import numpy as np
    a = np.array(im.convert("RGB")).astype(int)
    fg = ~((a[..., 0] > 200) & (a[..., 1] < 80) & (a[..., 2] > 200))
    ys, xs = np.nonzero(fg)
    return (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1) if len(xs) else None


def size_lock(panel, ref_h):
    """a pose more than 8 % taller than frame 1 is scaled down to frame 1's height around its feet (magenta around it)"""
    bb = fig_box(panel)
    if not bb or (bb[3] - bb[1]) <= ref_h * 1.08:
        return panel, 1.0
    s = ref_h / (bb[3] - bb[1])
    fig = panel.crop(bb)
    fw, fh = max(1, round(fig.width * s)), max(1, round(fig.height * s))
    out = Image.new("RGB", panel.size, (255, 0, 255))
    cx = (bb[0] + bb[2]) / 2
    out.paste(fig.resize((fw, fh), Image.LANCZOS), (round(cx - fw / 2), bb[3] - fh))
    return out, s


def run_anim(job, base, key, post, download, folder, log=print):
    T, TB, S = _modules()
    settings = json.loads(job.get("prompt") or "{}")
    src = job.get("from_try") or {}
    if not src.get("image"):
        raise RuntimeError("the animation needs the battle sprite")
    script = anim_scripts().get(int(settings.get("script") or 0))
    if not script:
        raise RuntimeError("unknown animation %r" % settings.get("script"))
    cls = script["cls"]
    poses = anim_poses().get(cls) or []
    sprite = Image.open(download(base, src["image"], folder / "battle.png")).convert("RGBA")
    pal = colours_of(sprite)
    cells = [j for j in script["cells"] if j]
    # poses made earlier, maybe for another animation (2026-11-24, Arvind: "jeg vil ikke at de framesa skal være låst til den
    # animasjonen"): kept as they are, and only the poses this animation still lacks are drawn
    have = None
    if settings.get("frames"):
        have = Image.open(download(base, settings["frames"], folder / "frames_in.png")).convert("RGBA")
    kept = have.width // 80 if have is not None else 1
    drawn = [j for j in cells if j <= len(poses) and j >= kept]   # cells with pose words not made yet; the rest show the sprite
    words = words_of(settings)
    extra = " ".join(str(settings.get("extra") or "").split())[:200]
    who = (words + (". " + extra if extra else "")).strip(" .") or "the trainer in image 1"
    try:                                                   # the build: the battle sprite's base, or stout by the words/shape
        brow = base_row(str(src.get("recipe") or "").split(" ")[0])
    except Exception:
        brow = {}
    build = brow.get("build") or "-"
    fb = (fields_of(settings).get("build") or "").strip()
    if fb:                                                 # only a filled-in build: a wide cape looked stout to the measurement and
        build = fb                                         # "build: stout" made poses wider and bigger than frame 1
    swap_row = {"cls": brow.get("cls") or "Trainer", "facing": brow.get("facing") or "-", "build": build, "who": who, "held": "-"}
    T.on_magenta(sprite).save(folder / "anim_f1.png")
    i1 = Image.open(folder / "anim_f1.png").convert("RGB")
    ref = comfy.upload(folder / "anim_f1.png")
    bb = fig_box(i1)
    ref_h = bb[3] - bb[1] if bb else i1.height
    start = Image.new("RGB", (640, 320))
    start.paste(i1.resize((320, 320), Image.NEAREST) if i1.size != (320, 320) else i1, (0, 0))
    start.paste(start.crop((0, 0, 320, 320)), (320, 0))
    start.save(folder / "anim_start.png")
    start_up = comfy.upload(folder / "anim_start.png")
    mask = Image.new("RGB", (640, 320), "black")
    mask.paste((255, 255, 255), (320, 0, 640, 320))
    mask.save(folder / "anim_mask.png")
    mask_up = comfy.upload(folder / "anim_mask.png")
    count = int(job.get("count") or 1)
    made = 0
    for n in range(1, count + 1):
        seed = n if n <= 1 else job["id"] * 100 + n         # seed 1 kept the faces best in the tests; the others give choice
        t = post(base, key, {"action": "try_start", "job_id": job["id"], "n": n, "seed": seed,
                             "recipe": ("anim pair%s %s s%d" % ("+sw%g" % ANIM_SWAP if ANIM_SWAP > 0 else "", cls, seed))[:60], "expected_seconds": ANIM_SECONDS * len(drawn)})
        started = time.time()
        try:
            # the likeness check (2026-11-24): a pose whose colours drift from the battle sprite's by more than ANIM_LIKE makes the
            # WHOLE strip be drawn again with the next seed (a single pose redrawn with its own seed no longer matched its
            # neighbours: another shirt, a bigger body); the strip whose worst pose is closest is kept
            best = None
            for k in range(ANIM_TRIES):
                sd = seed + 7919 * k
                strip = Image.new("RGBA", (80 * max(max(script["cells"]) + 1, kept), 80), (0, 0, 0, 0))
                for j in [0] + [c for c in cells if c not in drawn]:
                    if have is not None and j < kept:
                        strip.alpha_composite(have.crop((80 * j, 0, 80 * j + 80, 80)), (80 * j, 0))
                    else:
                        strip.alpha_composite(sprite, (80 * j, 0))
                scales, gaps = [], []
                for i, j in enumerate(drawn):
                    post(base, key, {"action": "progress", "job_id": job["id"], "state": "drawing pose %d of %d (animation %d of %d%s)" % (i + 2, len(drawn) + 1, n, count, ", again" if k else "")})
                    text = ("Two 80x80 pixel art battle sprites of the same trainer (%s, build: %s) side by side on a flat magenta "
                            "background, like two animation frames. The left one is exactly image 1. The right one is the same trainer with "
                            "exactly the same face, hair, clothes, colours, body shape and outline, %s, in a new pose: the trainer %s. %s"
                            % (who, build, ANIM_SIZE, poses[j - 1], ANIM_STRICT))
                    raw = folder / ("anim_raw%d_%d_%d.png" % (n, j, k))
                    raw.write_bytes(comfy.run(pair_graph(text, ref, sd, start_up, mask_up)))
                    panel, s = size_lock(Image.open(raw).convert("RGB").crop((320, 0, 640, 320)), ref_h)
                    scales.append(round(s, 2))
                    right = folder / ("anim_right%d_%d_%d.png" % (n, j, k))
                    panel.save(right)
                    if ANIM_SWAP > 0:                      # stage 2: the trainer LoRA swap brings the face back
                        post(base, key, {"action": "progress", "job_id": job["id"], "state": "cleaning pose %d of %d (animation %d of %d)" % (i + 2, len(drawn) + 1, n, count)})
                        row = dict(swap_row, pose="the trainer " + poses[j - 1])
                        swapped = folder / ("anim_swap%d_%d_%d.png" % (n, j, k))
                        swapped.write_bytes(comfy.run(S.graph(TB.caption(T.describe(row, drop=0), True) + " " + ANIM_STRICT, [ref], sd, LORA, comfy.upload(right), ANIM_SWAP)))
                        right = swapped
                    pose, _ = lock_palette(trainer_post.battle(klein_follower.to_back(right)), pal)
                    strip.alpha_composite(pose, (80 * j, 0))
                    gaps.append(colour_gap(sprite, pose))
                worst = max(gaps) if gaps else 0
                if best is None or worst < best[0]:
                    best = (worst, strip, scales, sd, k)
                if worst <= ANIM_LIKE:
                    break
                log("anim job %d try %d: a pose looks different (%.2f): the whole animation is drawn again" % (job["id"], n, worst))
            worst, strip, scales, used_seed, again = best
            image = folder / ("anim%d.png" % n)
            strip.save(image)
            shrunk = [s for s in scales if s < 1]
            post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": t["id"], "status": "done",
                             "note": ("%s animation (%d poses) side by side%s from battle sprite #%s, seed %d, build %s%s%s" % (
                                 script["name"], len(drawn) + 1, " + swap %.2f" % ANIM_SWAP if ANIM_SWAP > 0 else "", src.get("id"), used_seed, build,
                                 ", size locked x" + "/".join("%.2f" % s for s in shrunk) if shrunk else "",
                                 ", extra: " + extra if extra else "") + (", kept %d poses from #%s" % (kept, settings.get("frames_try")) if have is not None else "")
                                 + (", drawn %d times to keep the look (worst pose %.2f)" % (again + 1, worst) if again else ""))[:300],
                             "seconds": round(time.time() - started, 1)}, {"image": image})
            made += 1
        except Exception as problem:
            log("anim try %d of job %d failed: %s" % (n, job["id"], problem))
            post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": t["id"], "status": "failed",
                             "note": ("%s: %s" % (type(problem).__name__, problem))[:300], "seconds": round(time.time() - started, 1)})
    return made


# ---------- step BACK (2026-11-22; 2026-11-23 the back A/B, Arvind: "Ja vs + foto var bra"; locked_back_throw_v2 "Step 1
# update"). Only player characters and tag-battle partners need it. The VS is made BEFORE the back and the back job carries
# the picked VS portrait (vs_image in its prompt).
# Stage 'tback' = frame 1, the back seen in battle: trainer LoRA c1 CREATE-back, start = a player back's real frame 1 whose
# look matches (BACK_SHAPES, named by what the base picture shows), the person PICKS one of several tries. Routes:
#   D (main): image 1 = the photo, image 2 = the picked VS 96x64 at 4x on white (+ one sentence about image 2), base
#     unwidened, denoise 0.6 (0.65 for the last tries), no colour lock. No VS -> photo only. No photo -> the VS as image 1.
#   F (2-3 of 8): image 1 = the picked FRONT sprite 4x on white, colours locked to the front: keeps the clothes better
#     through the throw.
# Stage 'throw' = frames 2-8 from the picked frame 1: pkmn_backmotion_klein_v5 checkpoint 750, each frame an EDIT of our
# frame k-1 toward the pose map of a template, with our frame 1 as image 3; seeds 1 and 2, colours locked to frame 1, the
# pick = IoU with the template - lock distance / 60 (back_motion5_gen.py). Template 14 (Barry Pt) for slim people, 21
# (Barry Pt wide, a real 8-frame set) for stout ones; a second try uses the other template.
BACKS = Path(os.environ.get("TRAINER_BACKS", r"D:\LocalAI\lora-train\data\trainers\backs"))
BACK_SHAPES = {"long": [13, 1], "short": [12, 24], "spiky": [5, 14, 4], "cap": [9, 0], "tied": [8, 7], "stout": [22, 21]}
# 2026-11-24: spiky got 05 (adult man, short hair) first: the tested spiky-haired person's best backs were on 05
#   13 long blond, 01 brown long hair, 12/24 short grey (24 an adult man), 14 spiky blond, 04 spiky orange, 09/00 caps,
#   08 blond ponytail, 07 side ponytail, 22/21 the real wide backs (Lucas Pt / Barry Pt wide)
WIDE_BACKS = (20, 21, 22)
BACK_SECONDS = 25
VS_SENTENCE = " Image 2 is a pixel art portrait of the same person: the same face, hair, clothes and colours."
THROW_LORA = os.environ.get("TRAINER_THROW_LORA", "pkmn_backmotion_klein_v5_000000750.safetensors")
THROW_SLIM, THROW_WIDE = 14, 21
THROW_SEEDS = (1, 2)


def back_frame1(b):
    f = next(BACKS.glob("%02d_*.png" % b))
    return Image.open(f).convert("RGBA").crop((0, 0, 80, 80))


def run_tback(job, base, key, post, download, folder, log=print):
    """Frame-1 tries: every base of the shape at 0.6, then at 0.65, by D = photo + VS (the locked recipe). F (from the front
    sprite, base widened) only for a stout person, once per round (2026-11-24: for a slim person F was the worst try every
    time). Without photo and VS every try takes the front route. The person's description fields go in the text."""
    T, _, S = _modules()
    import build_trainer_klein_c as C
    settings = json.loads(job.get("prompt") or "{}")
    shape = settings.get("shape") if settings.get("shape") in BACK_SHAPES else "short"
    bases = BACK_SHAPES[shape]
    src = job.get("from_try") or {}
    if not src.get("image"):
        raise RuntimeError("the back needs the battle sprite")
    front = Image.open(download(base, src["image"], folder / "front.png")).convert("RGBA")
    pal = colours_of(front)
    words = words_of(settings)
    extra = " ".join(str(settings.get("extra") or "").split())[:200]
    # the front route's base is widened for a stout person, unless the shape's bases are the wide ones already
    # a filled-in build decides (a wide cape or coat made a slim person look stout to the measurement)
    build = (fields_of(settings).get("build") or "").lower()
    stout = any(w in build for w in STOUT_WORDS) if build else is_stout(front, words + " " + extra)
    ffx = 1.3 if shape != "stout" and stout else 1.0
    plan = ([("D", b, 0.6) for b in bases] + ([("F", bases[0], 0.6)] if stout else [])
            + [("D", b, 0.65) for b in bases] + ([("F", bases[-1], 0.6)] if stout else []))
    f = fields_of(settings)
    if f:                                  # as the tested back recipe: the person's own description, seen from behind
        row = dict(f, cls=f.get("cls") or "Pokemon Trainer")
        row["extra"] = ", ".join(x for x in (f.get("extra"), " ".join(str(settings.get("words") or "").split()), extra) if x) or "-"
    else:
        row = {"cls": "Pokemon Trainer", "who": (words + (". " + extra if extra else "")).strip(" .") or "-"}
    row.update(facing="seen from behind, turned to the right", pose="about to throw a Poke Ball")
    text = C.create_caption(T.describe(row, drop=0), True, back=True)
    photo = vs = None
    try:
        photo = comfy.upload(person_picture(_photo(job, settings, base, key, post, download, folder), folder / "person.png"))
    except Exception as problem:
        log("back job %d: no picture (%s)" % (job["id"], problem))
    if settings.get("vs_image"):
        try:
            v = Image.open(download(base, settings["vs_image"], folder / "vs.png")).convert("RGBA")
            on_white(v, folder / "vs_ref.png")
            vs = comfy.upload(folder / "vs_ref.png")
        except Exception as problem:
            log("back job %d: no VS portrait (%s)" % (job["id"], problem))
    if photo and vs:
        d_refs, d_text, d_name = [photo, vs], text.rstrip() + VS_SENTENCE, "the picture + VS #%s" % settings.get("vs_try")
    elif photo:
        d_refs, d_text, d_name = [photo], text, "the picture"
    elif vs:
        d_refs, d_text, d_name = [vs], text, "VS #%s" % settings.get("vs_try")
    else:
        d_refs = None
        plan = [("F", b, 0.6) for _, b, _ in plan]
    on_white(front, folder / "front_ref.png")
    fref = comfy.upload(folder / "front_ref.png")
    starts = {}

    def start_of(b, fx):
        if (b, fx) not in starts:
            T.on_magenta(widen_back(back_frame1(b), fx)).save(folder / ("back_start%d_%g.png" % (b, fx)))
            starts[(b, fx)] = comfy.upload(folder / ("back_start%d_%g.png" % (b, fx)))
        return starts[(b, fx)]
    count = int(job.get("count") or 1)
    made = 0
    for n in range(1, count + 1):
        route, b, dn = plan[(n - 1) % len(plan)]
        fx = ffx if route == "F" else 1.0
        seed = job["id"] * 100 + n
        t = post(base, key, {"action": "try_start", "job_id": job["id"], "n": n, "seed": seed,
                             "recipe": ("back %s b%02d x%g d%.2f" % (route, b, fx, dn))[:60], "expected_seconds": BACK_SECONDS})
        post(base, key, {"action": "progress", "job_id": job["id"], "state": "drawing a back: %d of %d" % (n, count)})
        started = time.time()
        try:
            raw = folder / ("back_raw%d.png" % n)
            if route == "F":
                raw.write_bytes(comfy.run(S.graph(text, [fref], seed, LORA, start_of(b, fx), dn)))
            else:
                raw.write_bytes(comfy.run(S.graph(d_text, d_refs, seed, LORA, start_of(b, 1.0), dn)))
            im = klein_follower.to_back(raw).convert("RGBA")
            if route == "F":
                im, _ = lock_palette(im, pal)
            image = folder / ("back%d.png" % n)
            im.save(image)
            note = "back frame 1 from %s: base %02d (%s)%s, denoise %.2f, seed %d%s" % (
                "the battle sprite" if route == "F" else d_name, b, shape, " x%g wide" % fx if fx > 1 else "", dn, seed, ", extra: " + extra if extra else "")
            post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": t["id"], "status": "done" if im.getbbox() else "broken",
                             "note": note[:300], "seconds": round(time.time() - started, 1)}, {"image": image, "raw": raw})
            made += 1
        except Exception as problem:
            log("back try %d of job %d failed: %s" % (n, job["id"], problem))
            post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": t["id"], "status": "failed",
                             "note": ("%s: %s" % (type(problem).__name__, problem))[:300], "seconds": round(time.time() - started, 1)})
    return made


def run_throw(job, base, key, post, download, folder, log=print):
    import numpy as np
    import re
    _modules()
    import build_back_motion as B
    import build_back_motion2 as B2
    import build_back_motion5 as B5
    T, _, _ = _modules()
    settings = json.loads(job.get("prompt") or "{}")
    src = job.get("from_try") or {}
    if not src.get("image"):
        raise RuntimeError("the throw needs a picked back")
    f1 = Image.open(download(base, src["image"], folder / "throw_f1.png")).convert("RGBA").crop((0, 0, 80, 80))
    pal = colours_of(f1)
    m = re.search(r"\bb(\d\d)\b", str(src.get("recipe") or ""))
    wide = (m and int(m.group(1)) in WIDE_BACKS) or any(w in (settings.get("words") or "").lower() for w in STOUT_WORDS)
    templates = [THROW_WIDE, THROW_SLIM] if wide else [THROW_SLIM, THROW_WIDE]

    def up(im, name):
        T.on_magenta(im).save(folder / name)
        return comfy.upload(folder / name)

    def iou(a, b):
        x = np.array(a)[..., 3] > 0
        y = np.array(b.convert("RGBA"))[..., 3] > 0
        return (x & y).sum() / max(1, (x | y).sum())
    r3 = up(f1, "throw_one.png")
    count = min(2, int(job.get("count") or 1))
    made = 0
    for n in range(1, count + 1):
        tpl = templates[n - 1]
        fr = B.frames(tpl)
        nfr = len(fr)
        t = post(base, key, {"action": "try_start", "job_id": job["id"], "n": n, "seed": THROW_SEEDS[0],
                             "recipe": "throw v5 c750 b%02d" % tpl, "expected_seconds": BACK_SECONDS * len(THROW_SEEDS) * (nfr - 1)})
        started = time.time()
        try:
            ours = [f1]
            for k in range(1, nfr):
                post(base, key, {"action": "progress", "job_id": job["id"], "state": "drawing the throw: frame %d of %d (throw %d of %d)" % (k + 1, nfr, n, count)})
                r1 = up(ours[-1], "throw_prev%d_%d.png" % (n, k))
                r2 = up(B2.pose(fr[k]), "throw_pose%d_%d.png" % (n, k))
                best = None
                for sd in THROW_SEEDS:
                    raw = folder / ("throw_raw%d_%d_s%d.png" % (n, k, sd))
                    raw.write_bytes(comfy.run(comfy.klein(B5.caption(k + 1, nfr), [r1, r2, r3], 320, 320, sd, "sigma/backmotion5", lora=THROW_LORA)))
                    im, dist = lock_palette(klein_follower.to_back(raw), pal)
                    score = iou(im, fr[k]) - dist / 60
                    if best is None or score > best[0]:
                        best = (score, im, sd)
                ours.append(best[1])
            strip = Image.new("RGBA", (80 * nfr, 80), (0, 0, 0, 0))
            for k, im in enumerate(ours):
                strip.alpha_composite(im, (80 * k, 0))
            image = folder / ("throw%d.png" % n)
            strip.save(image)
            post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": t["id"], "status": "done",
                             "note": ("throw from back #%s: v5 c750, template %02d (%s), seeds %s" % (src.get("id"), tpl, "wide" if tpl == THROW_WIDE else "slim", ",".join(map(str, THROW_SEEDS))))[:300],
                             "seconds": round(time.time() - started, 1)}, {"image": image})
            made += 1
        except Exception as problem:
            log("throw %d of job %d failed: %s" % (n, job["id"], problem))
            post(base, key, {"action": "try_done", "job_id": job["id"], "try_id": t["id"], "status": "failed",
                             "note": ("%s: %s" % (type(problem).__name__, problem))[:300], "seconds": round(time.time() - started, 1)})
    return made
