#!/usr/bin/env python3
"""Build the review page for the moveset proposals (proposals/review.html) from proposals/movesets.json.

    python scripts/moveset_fill.py propose     # first
    python scripts/moveset_review.py           # then this; publish proposals/review.html as the review page

The page shows every line, what each species gets (new moves marked), why, its role, the official Pokemon it
is modelled on, an example set and the notes. People mark each line OK / needs changes with a note; those
answers are kept in the page's shared store (the artifact's db) so Claude can read them back before `apply`.
"""
import json
import sys

import moveset_data
from dexlib import ROOT

SRC = ROOT / "proposals" / "movesets.json"
TEMPLATE = ROOT / "scripts" / "moveset_review_template.html"
OUT = ROOT / "proposals" / "review.html"
KEYS = ("level_up", "tm_hm", "tutor", "egg")


def main():
    prop = json.loads(SRC.read_text(encoding="utf-8"))
    ref = moveset_data.load()
    M = ref["moves"]
    species, used = {}, set()
    for sid, r in prop["species"].items():
        added = r["added"]
        new_lu = {(e["level"], e["move"]) for e in added["level_up"]}
        ls = r["learnset"]
        item = {
            "name": r["name"], "dex": r.get("dex"), "types": r.get("types") or [], "stage": r.get("stage", 0),
            "final": r.get("final"), "root": r["root"], "skipped": r.get("skipped"),
            "role": r.get("role"), "from": r.get("evolves_from"), "at": r.get("evolves_at"),
            "stats": r.get("stats"), "est": r.get("stats_estimated"), "fill": r.get("claude_fill"),
            "wishes": r.get("wishes"), "flags": r.get("flags") or [], "example": r.get("example_set") or [],
            "power": r.get("power"), "design_note": r.get("design_note"),
            "skipped_own": r.get("skipped_for_own_moves") or [],
            "model": (r.get("models") or {}).get("line"), "model_stage": (r.get("models") or {}).get("stage"),
            "similar": (r.get("models") or {}).get("similar") or [],
            "inspired": (r.get("models") or {}).get("inspired") or [],
            "lu": [[e.get("level"), e.get("move"), (e.get("level"), e.get("move")) in new_lu]
                   for e in ls["level_up"] if isinstance(e, dict)],
            "tm": [[mv, mv in added["tm_hm"]] for mv in ls["tm_hm"]],
            "tutor": [[mv, mv in added["tutor"]] for mv in ls["tutor"]],
            "egg": [[mv, mv in added["egg"]] for mv in ls["egg"]],
            "why": r.get("reasons") or {},
            "had": r.get("existing_counts") or {},
            "adds": {k: len(added[k]) for k in KEYS},
        }
        species[sid] = item
        used |= {x[1] for x in item["lu"]} | {x[0] for k in ("tm", "tutor", "egg") for x in item[k]}
        used |= set(item["example"])
    moves = {}
    for mv in used:
        m = M.get(mv)
        if m:
            moves[mv] = [m["type"], m["category"][0], m["power"] if m["power"] > 1 else 0,
                         m["accuracy"] if m["accuracy"] <= 100 else 0, m["tm"] or ""]
    tutors = {mv: "; ".join("%s (%s)" % (p["where"], p["payment"]) for p in places)
              for mv, places in ref["tutors"].items() if mv in used}
    lines = {}
    for sid, s in sorted(species.items(), key=lambda kv: (kv[1]["dex"] or 999, kv[1]["stage"])):
        lines.setdefault(s["root"], []).append(sid)
    for root, members in lines.items():
        members.sort(key=lambda x: (species[x]["stage"], species[x]["dex"] or 999))
    order = sorted(lines, key=lambda r: min(species[x]["dex"] or 999 for x in lines[r]))
    data = {"generated": prop["generated"], "order": order, "lines": lines, "species": species, "moves": moves,
            "tutors": tutors}
    html = TEMPLATE.read_text(encoding="utf-8").replace(
        "/*__DATA__*/null", json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/"))
    OUT.write_text(html, encoding="utf-8")
    print("wrote %s (%d lines, %d KB)" % (OUT.relative_to(ROOT), len(order), len(html) // 1024))


if __name__ == "__main__":
    sys.exit(main())
