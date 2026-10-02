#!/usr/bin/env python3
"""Build site/index.html: a website that shows every Pokemon the way the game will use it.

One self-contained file - open it in a browser, or host the site/ folder anywhere.
"""
import json
import shutil

import yaml

import dexlib
import validate
from dexlib import ROOT

SITE = ROOT / "site"
PAGE = ROOT / "scripts" / "site_template.html"


def main():
    config = dexlib.load_config()
    species, problems = dexlib.load_species()
    if problems:
        raise SystemExit("Fix the species files first (run scripts/validate.py).")
    engine = dexlib.load_engine()
    ids = {sid for sid, _, _ in species}
    SITE.mkdir(exist_ok=True)
    art_dir = SITE / "art"
    if art_dir.exists():
        shutil.rmtree(art_dir)

    entries = []
    for sid, _, data in species:
        errors, warnings = [], []
        validate.check_species(sid, data, ids, engine, errors, warnings)
        entries.append({"id": sid, "data": data, "problems": errors + warnings})

    # Attached images: copied next to the page so the site does not depend on the database.
    images = {}
    manifest_path = ROOT / "data" / "images.json"
    for entry in (json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else []):
        source = ROOT / entry["file"]
        if not source.is_file() or entry["species"] not in ids:
            continue
        target = art_dir / entry["species"] / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        images.setdefault(entry["species"], []).append({
            "id": entry["id"], "src": "art/%s/%s" % (entry["species"], source.name),
            "caption": entry.get("caption"), "editor": entry.get("editor")})

    # Sprites: the enlarged preview of each Pokemon's game sprites.
    sprite_info = {}
    for sid in sorted(ids):
        folder = ROOT / "assets" / "sprites" / sid
        if (folder / "preview.png").is_file():
            target = art_dir / sid / "sprite.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(folder / "preview.png", target)
            facts = json.loads((folder / "sprite.json").read_text(encoding="utf-8")) if (folder / "sprite.json").is_file() else {}
            sprite_info[sid] = {"src": "art/%s/sprite.png" % sid, "note": facts.get("note"), "back": "back" in facts,
                                "drafts": [d.split(" ")[0] for d in facts.get("drafts", [])]}

    def report(name):
        path = ROOT / "export" / name
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

    cursor_path = ROOT / "data" / "web_edits_cursor.txt"
    payload = {
        "project": config.get("project", "Pokedex"), "dex_size": config.get("dex_size", 100),
        "species": entries, "types": dexlib.TYPES, "checks": dexlib.CHECK_LIST,
        "custom": {"move": engine["custom"]["moves"], "ability": engine["custom"]["abilities"]},
        "images": images, "sprites": sprite_info,
        "type_shares": yaml.safe_load((ROOT / "data" / "engine" / "type_shares.yaml").read_text(encoding="utf-8")),
        "problems": report("doc_problems.json") + report("sheet_problems.json") + report("web_problems.json"),
        "web": dict(config.get("web_edits") or {}, cursor=int(cursor_path.read_text().strip() or 0) if cursor_path.exists() else 0),
        "lists": {
            "moves": engine["engine_names"]["moves"], "abilities": engine["engine_names"]["abilities"],
            "move_categories": dexlib.MOVE_CATEGORIES, "move_targets": dexlib.MOVE_TARGETS,
            "move_name_limit": dexlib.MOVE_NAME_LIMIT, "ability_name_limit": dexlib.ABILITY_NAME_LIMIT,
            "tm_hm": engine["tm_hm_order"],
            "growth_rates": dexlib.GROWTH_RATES, "egg_groups": dexlib.EGG_GROUPS, "body_colors": dexlib.BODY_COLORS,
            "evolution_methods": list(dexlib.EVOLUTION_METHODS),
            "name_limit": dexlib.NAME_LIMIT, "category_limit": dexlib.CATEGORY_LIMIT,
        },
    }
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    page = PAGE.read_text(encoding="utf-8").replace("/*DATA*/null", blob).replace("@@TITLE@@", str(payload["project"]))
    (SITE / "index.html").write_text(page, encoding="utf-8")
    print("Built site/index.html")


if __name__ == "__main__":
    main()
