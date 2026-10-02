#!/usr/bin/env python3
"""Let the AI draw sprites for Pokemon and turn them into game sprites.

    python scripts/ai_sprites.py [pokemon ...] [--redo]

Draws a front and a back view with ComfyUI (see docs/COMFYUI.md) for every Pokemon listed in
data/sprite_prompts.yaml (or only the ones named), converts them with scripts/sprites.py and
marks the result as an "AI draft". Pokemon that already have sprites are skipped unless
--redo is given or their text in sprite_prompts.yaml changed. Sprites someone made by hand
are never replaced.
"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

import yaml

import comfy
import dexlib
import sprites
from dexlib import ROOT

PROMPTS = ROOT / "data" / "sprite_prompts.yaml"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    redo = "--redo" in sys.argv
    settings = yaml.safe_load(PROMPTS.read_text(encoding="utf-8"))
    known = {sid for sid, _, _ in dexlib.load_species()[0]}
    wanted = {dexlib.slugify(a) for a in args} or set(settings["pokemon"])
    made = 0
    for sid in sorted(wanted):
        entry = settings["pokemon"].get(sid)
        if not entry or sid not in known:
            print("%s: not in data/sprite_prompts.yaml or not in the dex - skipped" % sid)
            continue
        refs = [ROOT / ref for ref in entry.get("refs") or []]
        subject = "The creature is the one shown in <image1>. " if refs else ""
        prompts = {"front": "%s %s%s %s" % (settings["style"], subject, settings["front"], entry["look"]),
                   "back": "%s %s%s %s" % (settings["style"], subject, settings["back"], entry.get("back_look") or entry["look"])}
        seeds = entry.get("seeds") or {}
        recipe = hashlib.sha1(json.dumps([prompts, seeds, [str(r) for r in refs]], sort_keys=True).encode()).hexdigest()[:16]
        facts_path = sprites.SPRITES / sid / "sprite.json"
        old = json.loads(facts_path.read_text(encoding="utf-8")) if facts_path.exists() else {}
        if old.get("note") not in (None, "AI draft"):
            print("%s: has sprites that were not made by the AI - left alone" % sid)
            continue
        if old.get("recipe") == recipe and not redo:
            continue
        with tempfile.TemporaryDirectory() as folder:
            used = {}
            try:
                for view, prompt in prompts.items():
                    used[view] = comfy.generate(prompt, Path(folder) / (view + ".png"), refs, seed=seeds.get(view) if not redo else None,
                                                transparent=True, quiet=True)
                facts = sprites.build(sid, {view: Path(folder) / (view + ".png") for view in prompts}, note="AI draft", grid=64)
            except (comfy.ComfyError, sprites.SpriteError) as error:
                print("%s: failed - %s" % (sid, error))
                continue
        facts.update(recipe=recipe, seeds=used)
        facts_path.write_text(json.dumps(facts, indent=2) + "\n", encoding="utf-8")
        sprites.record(sid, facts)
        made += 1
        print("%s: done (seeds %s)" % (sid, used))
    print("%d Pokemon drawn" % made)
    return 0


if __name__ == "__main__":
    sys.exit(main())
