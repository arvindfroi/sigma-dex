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
    names = {sid: data.get("name") for sid, _, data in species}
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
        entries.append({
            "id": sid, "data": data, "art": art, "bst": dexlib.bst(data),
            "complete": dexlib.completeness(data),
            "missing": ["%s: %s" % pair for pair in dexlib.missing(data)],
            "problems": errors + warnings,
            "evolutions": [{"into": e.get("into"), "name": names.get(e.get("into"), e.get("into")), "how": dexlib.evolution_to_text(e)}
                           for e in dexlib.listing(data.get("evolutions")) if isinstance(e, dict)],
        })
    report_path = ROOT / "export" / "sheet_problems.json"
    payload = {
        "project": config.get("project", "Pokedex"), "dex_size": config.get("dex_size", 100),
        "sheet_url": config.get("sheet_url"), "species": entries, "types": dexlib.TYPES,
        "sheet_problems": json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else [],
    }
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    page = PAGE.read_text(encoding="utf-8").replace("/*DATA*/null", blob).replace("@@TITLE@@", str(payload["project"]))
    (SITE / "index.html").write_text(page, encoding="utf-8")
    print("Built site/index.html")


if __name__ == "__main__":
    main()
