#!/usr/bin/env python3
"""Make sprites for many Pokemon in one go, with the sprite studio's recipe (the Sigma sprite style).

    python scripts/sprite_batch.py waffy torchbat leafing --attempts 4 --out batch/

For every Pokemon it draws `attempts` artworks (front and back), builds the sprites from them,
checks each against the sprite standard and against its own artwork (colours kept), and keeps the
best. It writes, per Pokemon, the best sprites (front.png, back.png, icon.png and the game files)
and all attempts, and one sheet with every Pokemon's best (artwork, front, back) to look over.
Nothing is put into the dex: the group picks, then the sprites go in through the studio or
`scripts/sprites.py`.

Needs ComfyUI with Qwen-Image (docs/COMFYUI.md). Each Pokemon's `look`, `refs` and `signature`
come from data/sprite_prompts.yaml; without refs, its first concept art pictures are used.
"""
import argparse
import sys
import tempfile
import time
from pathlib import Path

import yaml
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comfy
import pixel_render
import sprite_quality
import sprite_worker
import sprites
from dexlib import ROOT


def references(sid, entry):
    """The concept art to draw from: the `refs` in the settings (files, or a folder for its first two
    pictures), else the Pokemon's first two concept art pictures."""
    found = []
    for ref in entry.get("refs") or ["assets/concept-art/%s/" % sid]:
        path = ROOT / ref
        found += sorted(p for p in path.iterdir() if p.suffix.lower() in (".png", ".webp", ".jpg")) if path.is_dir() else [path]
    return [p for p in found if p.exists()][:3]


def attempt(job, settings, seed, folder):
    """One attempt: artwork, sprites, and their score. Returns (score, notes, files)."""
    plan = sprite_worker.recipes(job, settings)
    raw = {}
    for view in ("front", "back"):
        raw[view] = folder / ("%s_art.png" % view)
        prompt, refs = plan[view]
        draw(prompt, raw[view], [raw["front"] if r == "@front" else Path(r) for r in refs], seed)
        # a back that was drawn from the front again is drawn again, with other seeds
        for extra in range(1, 4 if view == "back" else 1):
            if sprite_quality.same_view(raw["front"], raw["back"]) <= 0.6:
                break
            raw[view].unlink()
            draw(prompt, raw[view], [raw["front"] if r == "@front" else Path(r) for r in refs], seed + 1000 * extra)
    if job.get("refs"):
        raw["concept"] = Path(job["refs"][0])            # the DS icon is drawn with the concept art too
    return finish(job["species_id"], raw, folder, job.get("gen", 3))


def draw(prompt, target, refs, seed):
    """One Qwen picture, unless an earlier run already drew it; retried when the connection drops."""
    if target.exists():
        return                                           # drawn by an earlier run that stopped: the same seed gives the same picture
    for wait in (0, 30, 60, 120, 240):                   # the connection to the GPU computer can drop; try again
        try:
            time.sleep(wait)
            comfy.generate(prompt, target, refs, seed=seed, quiet=True)
            return
        except comfy.ComfyError as error:
            print("  ComfyUI: %s - trying again" % error, flush=True)
    raise comfy.ComfyError("ComfyUI stayed unreachable")


def finish(sid, raw, folder, gen=3):
    """Sprites from the artwork of one attempt, and their score. For the DS (gen 4) the 80x80
    frames are kept as they are (the GBA converter, scripts/sprites.py, makes 64x64 game files)."""
    out = folder / "sprite"
    if gen == 4:                                         # the DS: Qwen draws the pixel art (scripts/ds_pixel.py)
        import ds_pixel
        files, _ = ds_pixel.make(raw, sid, out)
    else:
        files = sprite_worker.official_sprites(raw, sid, folder / "pixels_", gen)
        sprites.build(sid, files, note="AI draft (Sigma sprite style)", out=out)
    front, back = sprites.as_rgba(out / "front.png"), sprites.as_rgba(out / "back.png")
    failed = sprite_quality.standards(front, back, None)
    if sprite_quality.same_view(raw["front"], raw["back"]) > 0.6:
        failed.append("the back artwork shows the face (drawn from the front)")
    kept = sprite_quality.fidelity(raw["front"], front)
    score = sprite_quality.score(front)[0] - 10 * len(failed) - 20 * (1 - kept)
    notes = "score %.2f, colours kept %.0f%%%s" % (score, 100 * kept, ("; misses: " + "; ".join(failed)) if failed else "")
    return score, notes, dict(raw, sprite=out)


def rerender(out, gen=3):
    """Build every attempt's sprites again from its saved artwork (after a change to the renderer),
    rescore and pick the best again. No artwork is drawn."""
    best = []
    for sid_dir in sorted(p for p in Path(out).iterdir() if p.is_dir()):
        tries = []
        for folder in sorted(sid_dir.glob("attempt*")):
            raw = {"front": folder / "front_art.png", "back": folder / "back_art.png"}
            if not all(p.exists() for p in raw.values()):
                continue
            score, notes, files = finish(sid_dir.name, raw, folder, gen)
            (folder / "notes.txt").write_text(notes + "\n")
            tries.append((score, notes, files))
        if tries:
            best.append(keep_best(sid_dir.name, sid_dir, tries))
    sheet(best, Path(out) / "sheet.png")
    return best


def keep_best(sid, sid_dir, tries):
    score, notes, files = max(tries, key=lambda t: t[0])
    target = sid_dir / "best"
    if target.exists():
        for f in target.iterdir():
            f.unlink()
    target.mkdir(exist_ok=True)
    for f in files["sprite"].iterdir():
        (target / f.name).write_bytes(f.read_bytes())
    (target / "front_art.png").write_bytes(files["front"].read_bytes())
    (target / "notes.txt").write_text(notes + "\n")
    return sid, target, notes


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pokemon", nargs="*")
    parser.add_argument("--rerender", action="store_true", help="only build the sprites again from the saved artwork in --out")
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument("--out", default="batch")
    parser.add_argument("--seed", type=int, default=1000, help="first seed; the same seed gives the same sprites")
    parser.add_argument("--pose", default="three-quarter")
    parser.add_argument("--gen", type=int, choices=(3, 4), default=3, help="3: Emerald (GBA, 64x64); 4: Origin HeartGold (DS, 80x80)")
    args = parser.parse_args()
    settings = yaml.safe_load((ROOT / "data" / "sprite_prompts.yaml").read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.rerender:
        for sid, folder, notes in rerender(out, args.gen):
            print(sid, notes)
        return 0
    best = []
    started = time.time()
    for sid in args.pokemon:
        entry = (settings.get("pokemon") or {}).get(sid) or {}
        look = " ".join((entry.get("look") or sid).split())
        refs = references(sid, entry)
        if not refs:
            print("%s: no concept art, skipped" % sid)
            continue
        job = {"id": 0, "species_id": sid, "style": "sprite-official", "pose": args.pose, "look": look, "refs": [str(p) for p in refs], "gen": args.gen}
        tries = []
        for n in range(args.attempts):
            folder = out / sid / ("attempt%d" % (n + 1))
            folder.mkdir(parents=True, exist_ok=True)
            score, notes, files = attempt(job, settings, args.seed + n, folder)
            (folder / "notes.txt").write_text(notes + "\n")
            tries.append((score, notes, files))
            print("%s attempt %d: %s" % (sid, n + 1, notes), flush=True)
        best.append(keep_best(sid, out / sid, tries))
    sheet(best, out / "sheet.png")
    print("%d Pokemon in %d minutes; sheet: %s" % (len(best), (time.time() - started) / 60, out / "sheet.png"))
    return 0


def sheet(best, path, cell=192):
    """Every Pokemon's best: artwork, front and back (shown 3x), with its notes."""
    columns = 2
    rows = (len(best) + columns - 1) // columns
    image = Image.new("RGB", (columns * 3 * (cell + 4), rows * (cell + 20)), "white")
    draw = ImageDraw.Draw(image)
    for k, (sid, folder, notes) in enumerate(best):
        x, y = (k % columns) * 3 * (cell + 4), (k // columns) * (cell + 20)
        art = Image.open(folder / "front_art.png").convert("RGB"); art.thumbnail((cell, cell))
        image.paste(art, (x, y))
        for j, view in enumerate(("front", "back")):
            sprite = sprites.as_rgba(folder / (view + ".png"))
            back = Image.new("RGBA", sprite.size, (200, 222, 200, 255)); back.alpha_composite(sprite)
            image.paste(back.convert("RGB").resize((cell, cell), Image.NEAREST), (x + (j + 1) * (cell + 4), y))
        draw.text((x + 2, y + cell + 3), "%s  %s" % (sid, notes)[:90], fill="black")
    image.save(path)


if __name__ == "__main__":
    sys.exit(main())
