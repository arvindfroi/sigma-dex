#!/usr/bin/env python3
"""Download move and ability details from Pokemon Showdown for the website's Pokemon builder.

    python scripts/fetch_showdown_data.py

Writes data/engine/showdown.json: for every move and ability the game knows (data/engine/expansion.yaml),
the type, category, power, accuracy, PP, priority and a one-line description, so the builder can show
them in a sortable list the way Showdown's teambuilder does. Run it again when the game's lists change.

The data is Pokemon Showdown's (https://github.com/smogon/pokemon-showdown), MIT licence,
copyright (c) 2011-2026 Guangcong Luo and other contributors.
"""
import json
import re
import urllib.request

import dexlib
from dexlib import ROOT, norm

SOURCES = {
    "moves": "https://play.pokemonshowdown.com/data/moves.json",
    "move_text": "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/text/moves.ts",
    "ability_text": "https://raw.githubusercontent.com/smogon/pokemon-showdown/master/data/text/abilities.ts",
}
OUT = ROOT / "data" / "engine" / "showdown.json"


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "sigma-dex"}), timeout=60) as response:
        return response.read().decode("utf-8")


def short_texts(source):
    """{id: shortDesc} from one of Showdown's data/text/*.ts files (top-level entries only)."""
    texts = {}
    for match in re.finditer(r"^\t([a-z0-9]+): \{(.*?)^\t\},", source, re.S | re.M):
        body = match.group(2)
        found = re.search(r'^\t\tshortDesc: "((?:[^"\\]|\\.)*)"', body, re.M) or re.search(r'^\t\tdesc: "((?:[^"\\]|\\.)*)"', body, re.M)
        if found:
            texts[match.group(1)] = json.loads('"%s"' % found.group(1))
    return texts


def main():
    engine = dexlib.load_engine()
    moves = json.loads(fetch(SOURCES["moves"]))
    move_text = short_texts(fetch(SOURCES["move_text"]))
    ability_text = short_texts(fetch(SOURCES["ability_text"]))
    out = {"source": "Pokemon Showdown (MIT licence), https://github.com/smogon/pokemon-showdown", "moves": {}, "abilities": {}}
    missing = []
    for name in engine["engine_names"]["moves"]:
        entry = moves.get(norm(name))
        if not entry:
            missing.append(name)
            continue
        out["moves"][name] = {
            "type": entry.get("type"), "category": entry.get("category"), "power": entry.get("basePower") or None,
            "accuracy": None if entry.get("accuracy") is True else entry.get("accuracy"), "pp": entry.get("pp"),
            "priority": entry.get("priority") or 0, "desc": move_text.get(norm(name), ""),
        }
    for name in engine["engine_names"]["abilities"]:
        text = ability_text.get(norm(name))
        if text is None:
            missing.append(name)
        out["abilities"][name] = text or ""
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")
    print("%d moves, %d abilities written to %s" % (len(out["moves"]), len(out["abilities"]), OUT.relative_to(ROOT)))
    if missing:
        print("Not found in Showdown's data: " + ", ".join(missing))


if __name__ == "__main__":
    main()
