#!/usr/bin/env python3
"""Facts about the 493 official Pokemon of HeartGold, for the website's cry maker.

The cry maker (a Pokemon's page > CRY) starts every cry from the cries of official Pokemon that are like ours:
same body plan, type, egg group, size and stage. This script writes those facts to
data/engine/official_species.json: name, types, egg groups, body shape, height, weight, base stat total,
legendary or not, and where it stands in its evolution line. Numbers and words only - no pictures or sounds.

Source: PokeAPI's public data tables (BSD 3-clause licence), https://github.com/PokeAPI/pokeapi/tree/master/data/v2/csv

  python3 scripts/fetch_official_species.py
"""
import csv
import io
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "engine" / "official_species.json"
BASE = "https://raw.githubusercontent.com/PokeAPI/pokeapi/master/data/v2/csv/"
LAST = 493                          # HeartGold's own Pokemon: their cries are in the game we build on

# PokeAPI's words -> ours (scripts/dexlib.py EGG_GROUPS, the studio's body shapes)
EGG = {"monster": "monster", "water1": "water_1", "water2": "water_2", "water3": "water_3", "bug": "bug",
       "flying": "flying", "ground": "field", "fairy": "fairy", "plant": "grass", "humanshape": "human_like",
       "mineral": "mineral", "indeterminate": "amorphous", "dragon": "dragon", "ditto": "ditto", "no-eggs": "undiscovered"}
SHAPE = {"ball": "only a head", "squiggle": "a serpentine body", "fish": "a body with fins", "arms": "a head and arms",
         "blob": "a head and a base", "upright": "an upright body on two legs with a tail", "legs": "a head and legs",
         "quadruped": "a quadruped body", "wings": "a body with one pair of wings", "tentacles": "tentacles or many legs",
         "heads": "several bodies joined together", "humanoid": "an upright body on two legs without a tail",
         "bug-wings": "a body with two or more pairs of wings", "armor": "an insect body with a hard shell"}


def table(name):
    with urllib.request.urlopen(BASE + name + ".csv", timeout=60) as response:
        return list(csv.DictReader(io.StringIO(response.read().decode("utf-8"))))


def main():
    species = {int(r["id"]): r for r in table("pokemon_species")}
    names = {int(r["pokemon_species_id"]): r["name"] for r in table("pokemon_species_names") if r["local_language_id"] == "9"}
    types = {r["id"]: r["identifier"].capitalize() for r in table("types")}
    shapes = {r["id"]: r["identifier"] for r in table("pokemon_shapes")}
    colours = {r["id"]: r["identifier"] for r in table("pokemon_colors")}
    eggs = {r["id"]: r["identifier"] for r in table("egg_groups")}
    pokemon = {int(r["species_id"]): r for r in table("pokemon") if r["is_default"] == "1"}
    by_pokemon = {int(r["id"]): sid for sid, r in pokemon.items()}
    mon_types, egg_groups, bst = {}, {}, {}
    for r in sorted(table("pokemon_types"), key=lambda r: int(r["slot"])):
        if int(r["pokemon_id"]) in by_pokemon:
            mon_types.setdefault(by_pokemon[int(r["pokemon_id"])], []).append(types[r["type_id"]])
    for r in table("pokemon_egg_groups"):
        egg_groups.setdefault(int(r["species_id"]), []).append(EGG[eggs[r["egg_group_id"]]])
    for r in table("pokemon_stats"):
        if int(r["pokemon_id"]) in by_pokemon:
            sid = by_pokemon[int(r["pokemon_id"])]
            bst[sid] = bst.get(sid, 0) + int(r["base_stat"])

    children = {}
    for sid, r in species.items():
        if r["evolves_from_species_id"]:
            children.setdefault(int(r["evolves_from_species_id"]), []).append(sid)

    def depth(sid):
        parent = species[sid]["evolves_from_species_id"]
        return 0 if not parent else 1 + depth(int(parent))

    out = []
    for sid in range(1, LAST + 1):
        r, mon = species[sid], pokemon[sid]
        below, above = depth(sid), bool(children.get(sid))
        stage = "single" if not below and not above else "first" if not below else "middle" if above else "final"
        out.append({"n": sid, "name": names[sid], "types": mon_types[sid], "egg": egg_groups.get(sid, []),
                    "shape": SHAPE.get(shapes.get(r["shape_id"]), ""), "color": colours.get(r["color_id"], ""),
                    "h": int(mon["height"]) / 10, "w": int(mon["weight"]) / 10, "bst": bst[sid],
                    "legend": 2 if r["is_mythical"] == "1" else 1 if r["is_legendary"] == "1" else 0,
                    "stage": stage, "line": int(r["evolution_chain_id"]), "from": int(r["evolves_from_species_id"] or 0)})
    OUT.write_text(json.dumps({"source": "PokeAPI public data tables (BSD 3-clause licence), https://github.com/PokeAPI/pokeapi",
                               "species": out}, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print("Wrote %s (%d official Pokemon)" % (OUT.relative_to(ROOT), len(out)))


if __name__ == "__main__":
    main()
