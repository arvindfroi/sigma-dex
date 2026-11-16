#!/usr/bin/env python3
"""How sure Claude is about each field it filled in: design.claude_sure, 0-100, shown on the website.

    python scripts/claude_sure.py            # (re)write design.claude_sure for every Pokemon from filled_by_claude
    python scripts/claude_sure.py --show leafsteel

Arvind (16 Nov 2026): "I want you to add how sure you are about things". The number says how much the value is
backed by something firm, not how good the Pokemon is:
- 85-95  a fixed Game Freak habit (EV yield by stage, starters, legendaries, the usual friendship), the colour seen
         in its sprite, or a look text Claude wrote while looking at its art;
- 55-80  copied from similar official Pokemon that mostly agree (the share that agrees sets the number);
- 25-50  a guess: similar Pokemon disagree, there is no look text or art, or it only follows from its type.
species_fill.py apply and moveset_fill.py apply run it by themselves. When a person changes a field on the website, the import
(import_web.py) takes the field off filled_by_claude and claude_sure: it is theirs then.
"""
import argparse
import json
import re
import sys

import yaml

import dexlib

SURE = 85          # fixed habits
EVOLUTIONS = {     # the evolutions Claude wrote (16 Nov 2026): the line is clear, the level is a guess
    "santrock": 70,               # Cindreon's concept says it evolves from Santrock
    "cindreon": 65,               # Custodix's category is "Solar lion evolution"
    "glac-pee-mindre-evo": 60,    # its file name says it is Glacépée's smaller evolution
}


def share(why, default=50):
    m = re.search(r"(\d+) %", why or "")
    return int(m.group(1)) if m else default


def from_share(why):
    """Copied from similar Pokemon: 40 when a third agree, 85 when all do."""
    return max(40, min(85, round(25 + 0.6 * share(why))))


def numbers_sure(field, why, filler, sid):
    w = why or ""
    if "chosen by people" in w:
        return None
    if field in ("height_m", "weight_kg"):
        if w.startswith("Claude's choice"):
            return 65
        key = field
        vals = [f[key] for _, n, f in filler.donors(sid)[:3] if f.get(key)]
        spread = max(vals) / max(0.1, min(vals)) if vals else 9
        return 55 if spread <= 1.6 else 45 if spread <= 3 else 35
    if field == "body_color":
        return 90 if "sprite" in w else 35 if "models" in w else 80 if "look text (" in w else 65 if "look text" in w else 25
    if field in ("ev_yield", "base_exp"):
        return SURE
    if field == "catch_rate":
        return 90 if "models" not in w else 60
    if field == "base_friendship":
        return 90 if "usual 70" in w else from_share(w)
    if field == "gender":
        return 95 if "design says" in w else 90 if "starters" in w else 75 if "legendary" in w else from_share(w)
    if field in ("growth_rate", "egg_groups"):
        if "legendar" in w or "starters" in w or "strong three-stage" in w:
            return 90
        return from_share(w)
    if field == "egg_cycles":
        return 90 if "models" not in w else 65
    return 60


def compute():
    import species_fill
    import moveset_fill as mf
    import moveset_data
    filler = species_fill.Filler()
    sure = {}
    claude_moves = dexlib.load_claude_moves()
    art = {p.name for p in (dexlib.ROOT / "assets" / "concept-art").iterdir() if p.is_dir() and any(p.iterdir())}
    for sid, path, data in dexlib.load_species()[0]:
        design = data.get("design") or {}
        labels = list(design.get("filled_by_claude") or [])
        if not labels:
            continue
        prop = filler.propose(sid)
        out = {}
        # moves: how much its closest official models agree (the three most similar carry this share of the weight)
        try:
            top3 = sum(w for w, n in filler.prop.weighted_donors(sid)[:3])
        except Exception:
            top3 = 0.3
        moves = max(45, min(80, round(45 + 50 * top3)))
        for label in labels:
            field = next((f for f, l in species_fill.LABELS.items() if l == label), None)
            if field:
                p = prop.get(field)
                if p and dexlib.prune(p["value"]) == dexlib.prune(data.get(field)):
                    v = numbers_sure(field, p["why"], filler, sid)
                else:            # the value is no longer what the rule gives today: keep it modest
                    v = 55
                if v is not None:
                    out[label] = v
            elif label in ("level-up moves", "TM/HM moves", "tutor moves", "egg moves"):
                out[label] = moves + {"TM/HM moves": 5, "tutor moves": -5, "egg moves": -5}.get(label, 0)
            elif label in ("look", "body shape", "movement"):
                out[label] = 80 if sid in art else 50          # read from its art, or only from words
            elif label == "evolutions":
                out[label] = EVOLUTIONS.get(sid, 55)
            else:
                out[label] = 60
        sure[sid] = out
    return sure


def main():
    import os
    if os.environ.get("PYTHONHASHSEED") != "0":
        os.environ["PYTHONHASHSEED"] = "0"
        os.execv(sys.executable, [sys.executable] + sys.argv)
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--show", nargs="*")
    args = ap.parse_args()
    if args.show is not None:
        sure = compute()
        for sid in args.show or sorted(sure):
            print(sid, json.dumps(sure.get(sid), ensure_ascii=False))
        return
    print("claude_sure written for %d species" % write_all())


def write_all():
    """Write design.claude_sure into every species file whose numbers changed. Returns how many."""
    sure = compute()
    changed = 0
    for sid, path, data in dexlib.load_species()[0]:
        design = data.get("design") or {}
        new = sure.get(sid) or {}
        if (design.get("claude_sure") or {}) != new:
            data.setdefault("design", {})["claude_sure"] = new
            if not new:
                data["design"].pop("claude_sure", None)
            dexlib.write_species(path, data)
            changed += 1
    return changed


if __name__ == "__main__":
    sys.exit(main())
