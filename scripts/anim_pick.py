#!/usr/bin/env python3
"""Which official Pokemon's battle animation fits each of ours (2026-11-23; Arvind: "vi må kunne velge animasjon script
også. Vi velger etter nærmeste pokemon basert på alle variablene").

In HeartGold every species has an animation record (a/1/8/0, 89 bytes: the front sprite's movement script, when frame 2
shows and for how long, the back sprite's movement and frames, cry delay). Origin keeps one for every species slot. Our
Pokemon get the record of the official Pokemon (1-493, the ones HeartGold made animations for) that is most like them.
The body shape counts most (a snake moves like a snake), then the types, the size and weight, the base stat total, the
colour, the evolution stage, legendary or not and the egg groups. The website shows the three closest and lets anyone
pick another; the pick is saved in the dex as engine.anim_from (an official name) and wins over the closest.

python scripts/anim_pick.py [POKEMON ...]     print the three closest for each (all when none given)
python scripts/anim_pick.py --json OUT.json   write {id: [{"name", "n", "why"}, ...]} for every Pokemon"""
import json
import math
import sys

import dexlib
from dexlib import ROOT

OFFICIAL = ROOT / "data" / "engine" / "official_species.json"
MOVE_SHAPES = (("flies", "a body with one pair of wings"), ("flapping", "a body with one pair of wings"),
               ("swimming with its fins", "a body with fins"), ("slithers", "a serpentine body"),
               ("many legs", "tentacles or many legs"), ("four legs", "a quadruped body"),
               ("upright on two legs", "an upright body on two legs without a tail"), ("floats in the air", "only a head"))
# shapes that move alike: half the points when the shape is not the same but close
NEAR = {frozenset(p) for p in (("an upright body on two legs with a tail", "an upright body on two legs without a tail"),
                               ("a body with one pair of wings", "a body with two or more pairs of wings"),
                               ("a head and arms", "an upright body on two legs without a tail"),
                               ("a head and legs", "a quadruped body"), ("only a head", "a head and a base"),
                               ("a serpentine body", "a body with fins"), ("tentacles or many legs", "an insect body with a hard shell"))}


def official():
    return json.loads(OFFICIAL.read_text(encoding="utf-8"))["species"]


def stages(species):
    """id -> first / middle / final / single, from the evolutions written on the earlier Pokemon"""
    into = {}
    for sid, _, d in species:
        for e in d.get("evolutions") or []:
            t = e.get("into") or e.get("species") or e.get("target") if isinstance(e, dict) else None
            if t:
                into.setdefault(dexlib.norm(str(t)), []).append(sid)
    names = {dexlib.norm(str(d.get("name") or sid)): sid for sid, _, d in species}
    evolved = {names.get(k, k) for k in into}
    out = {}
    for sid, _, d in species:
        has = bool(d.get("evolutions"))
        was = sid in evolved
        out[sid] = "middle" if has and was else "first" if has else "final" if was else "single"
    return out


def facts(sid, d, stage):
    design = d.get("design") or {}
    shape = str(design.get("body_shape") or "").strip()
    move = str(design.get("movement") or "").lower()
    if not shape:
        shape = next((s for w, s in MOVE_SHAPES if w in move), "")
    stats = d.get("base_stats") or {}
    bst = sum(v for v in stats.values() if isinstance(v, (int, float))) or None
    legend = bool((d.get("catch_rate") or 255) <= 3 or "legend" in str(design.get("concept") or "").lower())
    return {"name": d.get("name") or sid, "types": [t for t in d.get("types") or [] if t], "shape": shape, "move": move,
            "color": str(d.get("body_color") or "").lower(), "h": d.get("height_m"), "w": d.get("weight_kg"), "bst": bst,
            "legend": legend, "stage": stage, "egg": [str(e).lower() for e in d.get("egg_groups") or []]}


def score(o, f):
    """(points, reasons) for the official Pokemon o against our facts f"""
    pts, why = 0.0, []
    if f["shape"] and f["shape"] == o["shape"]:
        pts += 3.0; why.append("same body shape")
    elif f["shape"] and frozenset((f["shape"], o["shape"])) in NEAR:
        pts += 1.5; why.append("close body shape")
    shared = [t for t in f["types"] if t in o["types"]]
    if f["types"]:
        pts += 1.2 * len(shared) / len(f["types"]) - 0.3 * len([t for t in o["types"] if t not in f["types"]])
        if shared: why.append("/".join(shared))
    if f["h"] and o["h"]:
        k = math.exp(-abs(math.log(float(f["h"]) / o["h"])))
        pts += 1.2 * k
        if k > 0.7: why.append("about as tall (%g m vs %g m)" % (o["h"], float(f["h"])))
    if f["w"] and o["w"]:
        pts += 0.6 * math.exp(-abs(math.log(float(f["w"]) / o["w"])) / 1.5)
    if f["bst"]:
        pts += 0.6 * math.exp(-abs(f["bst"] - o["bst"]) / 80)
    if f["color"] and f["color"] == o["color"]:
        pts += 0.3; why.append(o["color"])
    if f["stage"] == o["stage"]:
        pts += 0.4
    if f["legend"] != bool(o["legend"]):
        pts -= 1.0
    elif f["legend"]:
        pts += 0.4; why.append("legendary")
    if set(f["egg"]) & set(o["egg"]):
        pts += 0.3
    return pts, why


def closest(f, ref, k=3):
    ranked = sorted(((score(o, f), o) for o in ref), key=lambda t: -t[0][0])[:k]
    return [{"name": o["name"], "n": o["n"], "points": round(p, 2), "why": ", ".join(w) or "nearest overall"} for (p, w), o in ranked]


def all_picks(k=3):
    species, _ = dexlib.load_species()
    ref, st = official(), stages(species)
    return {sid: closest(facts(sid, d, st[sid]), ref, k) for sid, _, d in species}


def donor(sid, data, picks=None):
    """the official name whose animation this Pokemon uses: its own pick, else the closest"""
    chosen = ((data or {}).get("engine") or {}).get("anim_from")
    if chosen:
        return chosen
    return ((picks or all_picks()).get(sid) or [{}])[0].get("name")


def main(argv):
    if argv[:1] == ["--json"]:
        out = all_picks()
        (ROOT / argv[1]).write_text(json.dumps(out, indent=1), encoding="utf-8") if not argv[1].startswith("/") else open(argv[1], "w").write(json.dumps(out, indent=1))
        print("wrote", len(out))
        return
    picks = all_picks()
    for sid in argv or sorted(picks):
        print("%-16s %s" % (sid, " | ".join("%s (%s)" % (p["name"], p["why"]) for p in picks.get(sid, []))))


if __name__ == "__main__":
    main(sys.argv[1:])
