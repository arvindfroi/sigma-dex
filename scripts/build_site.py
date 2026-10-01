#!/usr/bin/env python3
"""Build site/index.html: a website that shows every Pokemon the way the game will use it.

One self-contained file - open it in a browser, or host the site/ folder anywhere.
"""
import json
import shutil

import dexlib
import validate
from dexlib import ROOT, section

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
        art = section(data, "assets").get("concept_art")
        if art and (ROOT / art).is_file():
            art_dir.mkdir(exist_ok=True)
            target = art_dir / (sid + (ROOT / art).suffix.lower())
            shutil.copyfile(ROOT / art, target)
            art = "art/" + target.name
        else:
            art = None
        entries.append({"id": sid, "data": data, "art": art, "problems": errors + warnings})

    def report(name):
        path = ROOT / "export" / name
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

    cursor_path = ROOT / "data" / "web_edits_cursor.txt"
    payload = {
        "project": config.get("project", "Pokedex"), "dex_size": config.get("dex_size", 100),
        "species": entries, "types": dexlib.TYPES, "checks": dexlib.CHECK_LIST,
        "problems": report("sheet_problems.json") + report("web_problems.json"),
        "web": dict(config.get("web_edits") or {}, cursor=int(cursor_path.read_text().strip() or 0) if cursor_path.exists() else 0),
        "lists": {
            "moves": engine["names"]["moves"], "abilities": engine["names"]["abilities"],
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
