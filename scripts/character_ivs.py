#!/usr/bin/env python3
"""Write each claimable battle's IV level (from Origin's own team) into data/characters.yaml as `iv:`.

    python3 scripts/character_ivs.py      # needs the EN patch's trainer list in ~/origin-en (never in this repo)

Arvind (2026-11-17): "gjør det slik at IV blir gjort automatisk hos motstanderene ... de skaleres automatisk oppover".
Origin's IVs already rise through the game (0-6 early, 12-18 in the middle, 24-30 late; see docs/STORY.md#game-design-making-our-version-good-and-fun-2026-11-17), so
every battle keeps the IV level of the original battle (the level most of its Pokemon have), exactly as the game has
it (Arvind: "vi gjør det bare slik spillet gjør"), odd dips included (Goh's Lv. 100 legendaries have IV 1).
The HP IV is not stored: Origin sets it from the level (10 up to Lv. 40, 20 at Lv. 41-79, 31 from Lv. 80), and the
website does the same.
"""
import collections
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "data" / "characters.yaml"
TRAINERS = Path.home() / "origin-en" / "site" / "src" / "data" / "trainers.json"
EXTRA = {"trainer-aa": [325]}          # Janine disguised as Koga: the record is called "Leader Koga"

spec = importlib.util.spec_from_file_location("cd", ROOT / "scripts" / "character_dialogue.py")
cd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cd)


def flat(x):
    return [i for s in x for i in (s if isinstance(s, list) else [s])]


def main():
    tj = {t["id"]: t for t in json.loads(TRAINERS.read_text(encoding="utf-8"))}
    ids_by_name = cd.trainer_ids()
    text = FILE.read_text(encoding="utf-8")
    text = re.sub(r", iv: \d+\}", "}", text)
    out, cid, missing = [], None, []
    for line in text.splitlines(keepends=True):
        m = re.match(r"- id: (\S+)", line)
        if m:
            cid = m.group(1)
            speakers, trainers = cd.WHO.get(cid, ([], []))
            ids = {i for n in flat(trainers) for i in ids_by_name.get(n, [])} | set(EXTRA.get(cid, []))
            recs = [tj[i] for i in ids if i in tj and tj[i]["team"]]
        t = re.match(r"  - \{lv: (\d+), size: (\d+),", line)
        if t and cid:
            lv, size = int(t.group(1)), int(t.group(2))
            same = [r for r in recs if max(m["level"] for m in r["team"]) == lv and len(r["team"]) == size]
            if same:
                iv = max(collections.Counter(m["ivs"] for m in r["team"]).most_common(1)[0][0] for r in same)
                line = line.rstrip("\n")
                line = line[:-1] + ", iv: %d}\n" % iv
            else:
                missing.append((cid, lv, size))
        out.append(line)
    FILE.write_text("".join(out), encoding="utf-8")
    for x in missing:
        print("no Origin record for", x)


if __name__ == "__main__":
    main()
