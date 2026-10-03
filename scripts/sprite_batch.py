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
        comfy.generate(prompt, raw[view], [raw["front"] if r == "@front" else Path(r) for r in refs], seed=seed, quiet=True)
    files = sprite_worker.official_sprites(raw, job["species_id"], folder / "pixels_")
    out = folder / "sprite"
    sprites.build(job["species_id"], files, note="AI draft (Sigma sprite style)", out=out)
    front, back = sprites.as_rgba(out / "front.png"), sprites.as_rgba(out / "back.png")
    failed = sprite_quality.standards(front, back, None)
    kept = sprite_quality.fidelity(raw["front"], front)
    score = sprite_quality.score(front)[0] - 10 * len(failed) - 20 * (1 - kept)
    notes = "score %.2f, colours kept %.0f%%%s" % (score, 100 * kept, ("; misses: " + "; ".join(failed)) if failed else "")
    return score, notes, dict(raw, sprite=out)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pokemon", nargs="+")
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument("--out", default="batch")
    parser.add_argument("--seed", type=int, default=1000, help="first seed; the same seed gives the same sprites")
    parser.add_argument("--pose", default="three-quarter")
    args = parser.parse_args()
    settings = yaml.safe_load((ROOT / "data" / "sprite_prompts.yaml").read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    best = []
    started = time.time()
    for sid in args.pokemon:
        entry = (settings.get("pokemon") or {}).get(sid) or {}
        look = " ".join((entry.get("look") or sid).split())
        refs = references(sid, entry)
        if not refs:
            print("%s: no concept art, skipped" % sid)
            continue
        job = {"id": 0, "species_id": sid, "style": "sprite-official", "pose": args.pose, "look": look, "refs": [str(p) for p in refs]}
        tries = []
        for n in range(args.attempts):
            folder = out / sid / ("attempt%d" % (n + 1))
            folder.mkdir(parents=True, exist_ok=True)
            score, notes, files = attempt(job, settings, args.seed + n, folder)
            (folder / "notes.txt").write_text(notes + "\n")
            tries.append((score, notes, files))
            print("%s attempt %d: %s" % (sid, n + 1, notes), flush=True)
        score, notes, files = max(tries, key=lambda t: t[0])
        target = out / sid / "best"
        if target.exists():
            for f in target.iterdir():
                f.unlink()
        target.mkdir(exist_ok=True)
        for f in files["sprite"].iterdir():
            (target / f.name).write_bytes(f.read_bytes())
        (target / "front_art.png").write_bytes(files["front"].read_bytes())
        (target / "notes.txt").write_text(notes + "\n")
        best.append((sid, target, notes))
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
