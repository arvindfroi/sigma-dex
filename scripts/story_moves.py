#!/usr/bin/env python3
"""The moves a story trainer's Pokemon uses at each level, for the smart story team builder on the website.

    python scripts/story_moves.py            # prints how many species were worked out

For every species, scripts/moveset_pick.py picks the 4 best moves it can know at each level where something new
becomes possible: a new level-up move, and level 30, from where trainers also use TM/HM moves. The website then
takes the last pick at or below a battle's level. Picking is slow (tens of milliseconds), so the result is kept in
export/story_moves.json with a fingerprint of everything it depends on; only species that changed are worked out
again, and a normal build adds almost no time.
"""
import hashlib
import json

import dexlib
from dexlib import ROOT

import moveset_pick

CACHE = ROOT / "export" / "story_moves.json"
TM_FROM = 30          # from this level on, trainers' Pokemon also use TM/HM moves


def fingerprint(data):
    keep = {k: data.get(k) for k in ("types", "base_stats", "abilities", "learnset")}
    keep["wishes"] = (data.get("design") or {}).get("wishes")
    keep["version"] = 1
    return hashlib.sha1(json.dumps(keep, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


def work_out(data):
    """[[level, [moves], role], ...] from level 1, only where the pick changes."""
    ls = data.get("learnset") or {}
    levels = {1, TM_FROM}
    for entry in ls.get("level_up") or []:
        if isinstance(entry, dict) and isinstance(entry.get("level"), int):
            levels.add(max(1, min(100, entry["level"])))
    mon = moveset_pick.mon_from_species(data)
    wishes = str((data.get("design") or {}).get("wishes") or "")
    out = []
    for level in sorted(levels):
        include = ("level_up", "tm_hm") if level >= TM_FROM else ("level_up",)
        pool = moveset_pick.learnable(data, level, include)
        if not pool:
            continue
        try:
            result = moveset_pick.pick(mon, level, pool, wishes=wishes)
        except Exception:
            continue
        moves = [m for m in result.get("moves") or [] if m]
        if moves and (not out or out[-1][1] != moves):
            out.append([level, moves, result.get("role") or ""])
    return out


def build():
    species, problems = dexlib.load_species()
    if problems:
        return {}, 0
    try:
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    result, fresh = {}, 0
    for sid, _, data in species:
        fp = fingerprint(data)
        hit = cache.get(sid)
        if hit and hit.get("fp") == fp:
            result[sid] = hit
            continue
        result[sid] = {"fp": fp, "picks": work_out(data)}
        fresh += 1
    if fresh or set(result) != set(cache):
        CACHE.parent.mkdir(exist_ok=True)
        CACHE.write_text(json.dumps(result, separators=(",", ":"), sort_keys=True) + "\n", encoding="utf-8")
    return {sid: v["picks"] for sid, v in result.items()}, fresh


if __name__ == "__main__":
    picks, fresh = build()
    print("Story moves: %d species, %d worked out again" % (len(picks), fresh))
