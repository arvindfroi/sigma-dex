#!/usr/bin/env python3
"""Copy what people typed into the Google Sheet into the species files.

    python scripts/import_sheet.py                 # uses sheet_csv_url from data/config.yaml
    python scripts/import_sheet.py some/file.csv   # or a downloaded CSV / another URL

The sheet has one row per dex slot and the same columns as export/dex.csv. Rules:
- A filled-in cell overwrites the value in the species file. An empty cell changes nothing.
- A row with a name in an empty slot creates a new Pokemon.
- A row that would break a species file is skipped as a whole, and the reason is written
  to export/sheet_problems.json (shown on the website), so one typo never blocks the rest.
"""
import copy
import csv
import io
import json
import os
import re
import sys
import urllib.request

import dexlib
import validate
from dexlib import ROOT, STATS, norm, section

REPORT = ROOT / "export" / "sheet_problems.json"

# Column header (letters and digits only, lowercase) -> what it is. Covers export/dex.csv
# and the headers of the original "Council of the sigmas Pokedex sheet".
COLUMNS = {
    "dex": "dex", "dexnumber": "dex", "number": "dex", "no": "dex", "name": "name",
    "type1": "type_1", "type2": "type_2",
    "ability1": "ability_1", "ability2": "ability_2", "hiddenability": "hidden_ability",
    "hp": "hp", "attack": "attack", "atk": "attack", "defense": "defense", "defence": "defense", "def": "defense",
    "spattack": "sp_attack", "specialattack": "sp_attack", "spatk": "sp_attack", "spa": "sp_attack",
    "spdefense": "sp_defense", "spdefence": "sp_defense", "specialdefense": "sp_defense",
    "specialdefence": "sp_defense", "spdef": "sp_defense", "spd": "sp_defense",
    "speed": "speed", "spe": "speed",
    "evolvesfrom": "evolves_from", "evocondition": "evo_condition", "evolutioncondition": "evo_condition",
    "category": "category", "heightm": "height_m", "height": "height_m", "weightkg": "weight_kg", "weight": "weight_kg",
    "bodycolor": "body_color", "bodycolour": "body_color", "evyield": "ev_yield", "catchrate": "catch_rate",
    "baseexp": "base_exp", "expyield": "base_exp", "growthrate": "growth_rate",
    "basefriendship": "base_friendship", "friendship": "base_friendship", "gender": "gender",
    "egggroup1": "egg_group_1", "egggroup2": "egg_group_2", "eggcycles": "egg_cycles",
    "helditemcommon": "held_item_common", "helditemrare": "held_item_rare",
    "levelupmoves": "level_up_moves", "tmhmmoves": "tm_hm_moves", "tutormoves": "tutor_moves", "eggmoves": "egg_moves",
    "encounters": "encounters", "description": "description", "dexentry": "description",
    "concept": "concept", "nameorigin": "name_origin", "notes": "notes", "designer": "designer", "artist": "artist",
}
STAT_WORDS = {norm(k): v for k, v in COLUMNS.items() if v in STATS}
INTEGERS = {"catch_rate", "base_exp", "base_friendship", "egg_cycles"}


class CellError(Exception):
    pass


def whole(text, what):
    try:
        return int(float(text.replace(",", ".")))
    except ValueError:
        raise CellError("%s '%s' is not a number" % (what, text))


def decimal(text, what):
    try:
        return float(text.replace(",", "."))
    except ValueError:
        raise CellError("%s '%s' is not a number" % (what, text))


def names(text):
    return [part.strip() for part in re.split(r"[,;\n]", text) if part.strip()]


def word(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def apply_row(data, row):
    """Put the filled-in cells of one sheet row into a species dict."""
    for key in ("credits", "abilities", "base_stats", "held_items", "learnset", "design"):
        if not isinstance(data.get(key), dict):
            data[key] = {}
    if row.get("name"):
        data["name"] = row["name"]
    types = [row.get("type_1"), row.get("type_2")]
    if types[0] or types[1]:
        old = (dexlib.listing(data.get("types")) + [None, None])[:2]
        merged = [(new.strip().capitalize() if new else None) or old[i] for i, new in enumerate(types)]
        data["types"] = [t for i, t in enumerate(merged) if t and t not in merged[:i]]
    for column, slot in (("ability_1", "primary"), ("ability_2", "secondary"), ("hidden_ability", "hidden")):
        if row.get(column):
            data["abilities"][slot] = row[column]
    for stat in STATS:
        if row.get(stat):
            data["base_stats"][stat] = whole(row[stat], stat)
    for column in ("category", "description"):
        if row.get(column):
            data[column] = row[column].replace("\r\n", "\n")
    for column in ("height_m", "weight_kg"):
        if row.get(column):
            data[column] = decimal(row[column], column)
    for column in INTEGERS:
        if row.get(column):
            data[column] = whole(row[column], column)
    for column in ("body_color", "growth_rate"):
        if row.get(column):
            data[column] = word(row[column])
    if row.get("gender"):
        data["gender"] = "genderless" if "less" in row["gender"].lower() else decimal(row["gender"].rstrip("% "), "gender")
        if isinstance(data["gender"], float) and data["gender"].is_integer():
            data["gender"] = int(data["gender"])
    groups = [word(row[c]) for c in ("egg_group_1", "egg_group_2") if row.get(c)]
    if groups:
        data["egg_groups"] = [g for i, g in enumerate(groups) if g not in groups[:i]]
    if row.get("ev_yield"):
        ev = {}
        for part in names(row["ev_yield"]):
            match = re.match(r"^(\d)\s*(.+)$", part) or re.match(r"^(.+?)\s*(\d)$", part)
            digits = [g for g in match.groups() if g.isdigit()] if match else []
            stat = STAT_WORDS.get(norm([g for g in match.groups() if not g.isdigit()][0])) if match else None
            if not stat:
                raise CellError("ev_yield '%s' not understood - write it like '1 attack, 1 speed'" % part)
            ev[stat] = int(digits[0])
        data["ev_yield"] = ev
    for column, slot in (("held_item_common", "common"), ("held_item_rare", "rare")):
        if row.get(column):
            data["held_items"][slot] = row[column]
    if row.get("level_up_moves"):
        moves = []
        for part in names(row["level_up_moves"]):
            match = re.match(r"^(.+?)\s*\(\s*(?:lv\.?\s*)?(\d+)\s*\)$", part, re.I)
            if not match:
                raise CellError("level-up move '%s' not understood - write it like 'Tackle (1), Vine Whip (7)'" % part)
            moves.append({"level": int(match.group(2)), "move": match.group(1).strip()})
        data["learnset"]["level_up"] = sorted(moves, key=lambda m: m["level"])
    for column, slot in (("tm_hm_moves", "tm_hm"), ("tutor_moves", "tutor"), ("egg_moves", "egg")):
        if row.get(column):
            data["learnset"][slot] = names(row[column])
    if row.get("encounters"):
        encounters = []
        for part in row["encounters"].split(";"):
            cells = [c.strip() for c in part.split("|")]
            if not cells[0]:
                continue
            entry = {"location": cells[0]}
            for key, value in zip(("method", "levels", "rate"), cells[1:]):
                if value:
                    entry[key] = int(value) if value.isdigit() else value
            encounters.append(entry)
        data["encounters"] = encounters
    for column in ("concept", "name_origin", "notes"):
        if row.get(column):
            data["design"][column] = row[column]
    for column in ("designer", "artist"):
        if row.get(column):
            data["credits"][column] = row[column]


def read_rows(source):
    if re.match(r"^https?://", source):
        try:
            with urllib.request.urlopen(urllib.request.Request(source, headers={"User-Agent": "sigma-dex"})) as response:
                text = response.read().decode("utf-8-sig")
        except OSError as error:
            text = "<html %s" % error
        if text.lstrip().lower().startswith("<!doctype html") or "<html" in text[:200].lower():
            print("WARNING: the Google Sheet is not readable. Set its sharing to 'Anyone with the link'. Nothing imported.")
            if os.environ.get("GITHUB_ACTIONS") == "true":
                print("::warning::The Google Sheet is not readable - set its sharing to 'Anyone with the link'.")
            return None
    else:
        text = open(source, encoding="utf-8-sig").read()
    table = list(csv.reader(io.StringIO(text)))
    if not table:
        sys.exit("The sheet is empty.")
    header = [COLUMNS.get(norm(cell)) for cell in table[0]]
    if "dex" not in header or "name" not in header:
        sys.exit("The first row of the sheet must have at least the columns 'dex' and 'name'.")
    return [{key: cell.strip() for key, cell in zip(header, line) if key and cell.strip()} for line in table[1:]]


def main():
    config = dexlib.load_config()
    source = sys.argv[1] if len(sys.argv) > 1 else config.get("sheet_csv_url")
    if not source:
        print("No sheet configured (sheet_csv_url in data/config.yaml is empty) - nothing to import.")
        return 0
    rows = read_rows(source)
    if rows is None:
        return 0
    species, problems = dexlib.load_species()
    if problems:
        sys.exit("Fix the species files first (run scripts/validate.py).")
    engine = dexlib.load_engine()
    by_dex = {data.get("dex"): (sid, path, data) for sid, path, data in species}
    by_name = {norm(data.get("name")): sid for sid, _, data in species}
    ids = {sid for sid, _, _ in species}
    report, changed, pending_evolutions = [], 0, []

    for row in rows:
        if not row.get("dex") or not row.get("name"):
            continue
        label = "#%s %s" % (row["dex"], row["name"])
        try:
            dex = whole(row["dex"], "dex")
            if dex in by_dex:
                sid, path, current = by_dex[dex]
            else:
                sid = dexlib.slugify(row["name"])
                if not sid or sid in ids:
                    raise CellError("cannot create '%s': the name is empty or already used" % row["name"])
                path, current = dexlib.SPECIES_DIR / (sid + ".yaml"), {"dex": dex}
            updated = copy.deepcopy(current)
            apply_row(updated, row)
            errors, warnings = [], []
            if not 1 <= dex <= config.get("dex_size", 100):
                errors.append("dex number %d is outside the dex" % dex)
            other = by_name.get(norm(updated.get("name")))
            if other and other != sid:
                errors.append("the name '%s' is already used by another Pokemon" % updated.get("name"))
            validate.check_species(sid, updated, ids | {sid}, engine, errors, warnings)
            if errors:
                raise CellError("; ".join(errors))
        except CellError as error:
            report.append({"row": label, "problem": str(error)})
            continue
        if dexlib.prune(updated) != dexlib.prune(current):
            dexlib.write_species(path, updated)
            changed += 1
        by_dex[dex] = (sid, path, updated)
        by_name[norm(updated.get("name"))] = sid
        ids.add(sid)
        if row.get("evolves_from") and row.get("evo_condition"):
            pending_evolutions.append((label, row["evolves_from"], row["evo_condition"], sid))

    # Evolutions are written on the evolved Pokemon's row, but stored on the one that evolves.
    for label, source_name, condition, target in pending_evolutions:
        source_id = by_name.get(norm(source_name))
        if not source_id or source_id == target:
            report.append({"row": label, "problem": "evolves_from '%s' is not the name of another Pokemon in the sheet" % source_name})
            continue
        sid, path, current = next(entry for entry in by_dex.values() if entry[0] == source_id)
        updated = copy.deepcopy(current)
        evolution = dict(dexlib.text_to_evolution(condition), into=target)
        others = [e for e in dexlib.listing(updated.get("evolutions")) if isinstance(e, dict) and e.get("into") != target]
        updated["evolutions"] = others + [evolution]
        errors = []
        validate.check_species(sid, updated, ids, engine, errors, [])
        if errors:
            report.append({"row": label, "problem": "; ".join(errors)})
        elif dexlib.prune(updated) != dexlib.prune(current):
            dexlib.write_species(path, updated)
            by_dex[updated["dex"]] = (sid, path, updated)
            changed += 1

    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for entry in report:
        print("SKIPPED %s: %s" % (entry["row"], entry["problem"]))
    print("Sheet import: %d rows read, %d species files changed, %d rows skipped" % (len(rows), changed, len(report)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
