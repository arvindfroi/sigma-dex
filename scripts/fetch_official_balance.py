#!/usr/bin/env python3
"""Work out how the official games' dexes are built, for the website's Balance page.

    python scripts/fetch_official_balance.py

Writes data/engine/official_balance.json: for every generation and for all of them together, how many evolution
lines have 1, 2 or 3 stages (legendaries and mythicals apart), the share of single-type Pokemon, the average base
stat total of first, middle and final stages, of Pokemon that do not evolve and of legendaries, and the share of
non-legendaries with a BST of 540 or more. A line counts for the generation of its earliest member, in the shape
it has today. Base species only.

The data is Pokemon Showdown's pokedex (https://github.com/smogon/pokemon-showdown), MIT licence,
copyright (c) 2011-2026 Guangcong Luo and other contributors.
"""
import json
import urllib.request
from collections import defaultdict

from dexlib import ROOT

SOURCE = "https://play.pokemonshowdown.com/data/pokedex.json"
OUT = ROOT / "data" / "engine" / "official_balance.json"
GENS = [(1, 151), (152, 251), (252, 386), (387, 493), (494, 649), (650, 721), (722, 809), (810, 905), (906, 1025)]
LEGEND_TAGS = {"Sub-Legendary", "Restricted Legendary", "Mythical"}


def tid(name):
    return "".join(c for c in name.lower() if c.isalnum())


def main():
    with urllib.request.urlopen(urllib.request.Request(SOURCE, headers={"User-Agent": "sigma-dex"}), timeout=60) as r:
        dex = json.loads(r.read().decode("utf-8"))
    species = {k: d for k, d in dex.items() if not d.get("forme") and 1 <= d.get("num", 0) <= 1025}
    kids, parent = defaultdict(set), {}
    for k, d in species.items():
        if d.get("prevo"):
            p = dex[tid(d["prevo"])]
            p = tid(p.get("baseSpecies") or p["name"])
            kids[p].add(k)
            parent[k] = p

    def root(k):
        while k in parent:
            k = parent[k]
        return k

    def depth(k):
        return 1 + max((depth(c) for c in kids[k]), default=0)

    def members(r):
        out, todo = [], [r]
        while todo:
            k = todo.pop()
            out.append(k)
            todo += kids[k]
        return out

    gen_of = lambda num: next(i + 1 for i, (a, b) in enumerate(GENS) if a <= num <= b)
    bst = lambda k: sum(species[k]["baseStats"].values())
    legend = lambda k: bool(set(species[k].get("tags") or []) & LEGEND_TAGS)
    groups = defaultdict(lambda: {"lines": {"1": 0, "2": 0, "3": 0, "legendary": 0}, "species": 0, "mono": 0,
                                  "bst": defaultdict(list), "strong": 0, "normal": 0})
    for r in {root(k) for k in species}:
        line = members(r)
        g = gen_of(min(species[k]["num"] for k in line))
        stages = depth(r)
        is_legend = any(legend(k) for k in line)
        for key in (str(g), "all"):
            G = groups[key]
            G["lines"]["legendary" if is_legend else str(min(stages, 3))] += 1
            for k in line:
                G["species"] += 1
                G["mono"] += len(species[k]["types"]) == 1
                if is_legend:
                    G["bst"]["legendary"].append(bst(k))
                    continue
                G["normal"] += 1
                G["strong"] += bst(k) >= 540
                place = "single" if stages == 1 else "first" if k == r else "final" if not kids[k] else "middle"
                G["bst"][place].append(bst(k))
    out = {"source": "Pokemon Showdown's pokedex (MIT licence), https://github.com/smogon/pokemon-showdown", "gens": {}}
    for key, G in groups.items():
        out["gens"][key] = {"lines": G["lines"], "species": G["species"], "mono_share": round(G["mono"] / G["species"], 3),
                            "avg_bst": {p: round(sum(v) / len(v)) for p, v in G["bst"].items() if v},
                            "strong_share": round(G["strong"] / max(1, G["normal"]), 3)}
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    a = out["gens"]["all"]
    print("Wrote %s: %d species; lines %s; mono %.0f%%" % (OUT.relative_to(ROOT), a["species"], a["lines"], 100 * a["mono_share"]))


if __name__ == "__main__":
    main()
