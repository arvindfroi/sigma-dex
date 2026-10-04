#!/usr/bin/env python3
"""Copy what people typed into the Google Sheet into the species files.

    python scripts/import_sheet.py                 # uses the SHEET_CSV_URL environment variable
    python scripts/import_sheet.py some/file.csv   # or a downloaded CSV / another URL

The sheet has one row per dex slot and the same columns as export/sheet.csv. Rules:
- Only cells that CHANGED since the last import are applied (data/sheet_snapshot.json remembers
  what the sheet looked like). So an old value sitting in the sheet never overwrites something
  that was edited on the website in the meantime.
- Emptying a cell that had a value clears that value.
- A row belongs to the Pokemon NAMED in it, not to its number (numbers change when the dex is reordered on
  the website while the sheet keeps the old ones). dexlib.identify has the rules; the Dex # column is never
  applied. data/sheet_snapshot.json is keyed by species id. A name that is new, on an open number, creates a
  new Pokemon. A row that cannot be matched safely (name on two rows, a new name on a number that is taken now,
  a rename of a Pokemon that has moved) is reported, not applied.
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
SNAPSHOT = ROOT / "data" / "sheet_snapshot.json"
# Columns that only make sense together: if one changes, both are applied.
PAIRS = (("egg_group_1", "egg_group_2"), ("type_1", "type_2"), ("evolves_from", "evo_condition"))

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
    "basefriendship": "base_friendship", "friendship": "base_friendship", "gender": "gender", "gendermale": "gender",
    "egggroup1": "egg_group_1", "egggroup2": "egg_group_2", "eggcycles": "egg_cycles",
    "helditemcommon": "held_item_common", "helditemrare": "held_item_rare",
    "levelupmoves": "level_up_moves", "tmhmmoves": "tm_hm_moves", "tutormoves": "tutor_moves", "eggmoves": "egg_moves",
    "encounters": "encounters", "description": "description", "dexentry": "description", "pokedexentry": "description",
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
            match = re.match(r"^(.+?)\s*\(\s*(?:lv\.?\s*)?(\d+|evo\w*)\s*\)$", part, re.I)
            if not match:
                raise CellError("level-up move '%s' not understood - write it like 'Tackle (1), Vine Whip (7)', or 'Slash (evo)' for a move learned when evolving" % part)
            level = match.group(2)
            moves.append({"level": int(level) if level.isdigit() else 0, "move": match.group(1).strip()})
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


def clear_cells(data, columns):
    """Empty the fields whose sheet cells were emptied."""
    for column in columns:
        if column in ("category", "description", "height_m", "weight_kg", "body_color", "growth_rate", "gender",
                      "catch_rate", "base_exp", "base_friendship", "egg_cycles", "ev_yield"):
            data[column] = None
        elif column in STATS:
            data["base_stats"][column] = None
        elif column in ("ability_1", "ability_2", "hidden_ability"):
            data["abilities"][{"ability_1": "primary", "ability_2": "secondary", "hidden_ability": "hidden"}[column]] = None
        elif column in ("held_item_common", "held_item_rare"):
            data["held_items"][column.rsplit("_", 1)[1]] = None
        elif column in ("level_up_moves", "tm_hm_moves", "tutor_moves", "egg_moves"):
            data["learnset"][{"level_up_moves": "level_up", "tm_hm_moves": "tm_hm", "tutor_moves": "tutor", "egg_moves": "egg"}[column]] = []
        elif column == "encounters":
            data["encounters"] = []
        elif column in ("concept", "name_origin", "notes"):
            data["design"][column] = None
        elif column in ("designer", "artist"):
            data["credits"][column] = None
        elif column == "type_2":
            data["types"] = dexlib.listing(data.get("types"))[:1]
        elif column == "egg_group_2":
            data["egg_groups"] = dexlib.listing(data.get("egg_groups"))[:1]


def changes(row, old):
    """(cells to apply, columns that were emptied) compared with the last import. old=None: first import."""
    if old is None:
        return dict(row), []
    delta = {key: value for key, value in row.items() if old.get(key) != value}
    for pair in PAIRS:
        if any(column in delta for column in pair):
            delta.update({column: row[column] for column in pair if column in row})
    cleared = [key for key in old if key not in row and key not in ("dex", "name")]
    return delta, cleared


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


def migrate_snapshot(snapshot, species):
    """The snapshot used to be keyed by dex number; it is keyed by species id now (numbers change when the dex is reordered).
    Old rows are matched to a Pokemon by the name they had. Returns (new snapshot, labels of rows that matched nobody)."""
    if not snapshot or not all(key.isdigit() and row.get("dex") == key for key, row in snapshot.items()):
        return snapshot, []
    by_name = {norm(data.get("name")): sid for sid, _, data in species}
    migrated, lost = {}, []
    for key, row in snapshot.items():
        sid = by_name.get(norm(row.get("name")))
        if sid and sid not in migrated:
            migrated[sid] = row
        else:
            lost.append("#%s %s" % (key, row.get("name", "")))
    return migrated, lost


def main():
    config = dexlib.load_config()
    source = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SHEET_CSV_URL")
    if not source:
        print("No sheet configured (SHEET_CSV_URL is not set) - nothing to import.")
        return 0
    rows = read_rows(source)
    if rows is None:
        return 0
    species, problems = dexlib.load_species()
    if problems:
        sys.exit("Fix the species files first (run scripts/validate.py).")
    engine = dexlib.load_engine()
    files = {sid: (path, data) for sid, path, data in species}
    by_name = {norm(data.get("name")): sid for sid, _, data in species}
    ids = set(files)
    report, changed, pending_evolutions = [], 0, []
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8")) if SNAPSHOT.exists() else None
    if snapshot is not None:
        snapshot, lost = migrate_snapshot(snapshot, species)
        for label in lost:
            print("NOTE: the old snapshot row %s matches no Pokemon any more and was dropped" % label)
    new_snapshot = dict(snapshot or {})       # rows nobody touched this time stay remembered
    # What the sheet showed at the last import: id -> (number, name). The numbers there are the sheet's, not the dex's.
    last = None if snapshot is None else {sid: (int(old["dex"]), old.get("name", "")) for sid, old in snapshot.items()
                                          if sid in ids and str(old.get("dex", "")).isdigit()}
    same_as_before = {json.dumps(old, sort_keys=True): sid for sid, old in (snapshot or {}).items() if sid in ids}
    names_in_sheet = [norm(row["name"]) for row in rows if row.get("dex") and row.get("name")]
    handled = set()                           # Pokemon that a row of this sheet has already been about

    for row in rows:
        if not row.get("dex"):
            continue
        label = "#%s %s" % (row["dex"], row.get("name", ""))
        sid = None
        try:
            dex = whole(row["dex"], "dex")
            sid = same_as_before.get(json.dumps(row, sort_keys=True))
            if sid:
                handled.add(sid)              # exactly what was imported last time, however the numbers have changed since
                continue
            if row.get("name") and names_in_sheet.count(norm(row["name"])) > 1:
                raise CellError("the name '%s' is on more than one row of the sheet - nothing was applied" % row["name"])
            current = {s: (d.get("dex"), d.get("name")) for s, (_, d) in files.items()}
            try:
                sid = dexlib.identify(row.get("name", ""), dex, current, last)
            except ValueError as error:
                raise CellError(str(error))
            if sid is None and not row.get("name"):
                continue                      # an open slot: nothing to do until it gets a name
            if sid in handled:
                raise CellError("another row of the sheet is already about %s" % files[sid][1].get("name"))
            old = None if snapshot is None else snapshot.get(sid, {})
            # The number in the sheet is never applied: Pokemon are moved on the website (Change numbers).
            delta, cleared = changes({k: v for k, v in row.items() if k != "dex"},
                                     None if old is None else {k: v for k, v in old.items() if k != "dex"})
            if old is not None and not delta and not cleared:
                new_snapshot[sid] = row
                handled.add(sid)
                continue
            if sid:
                path, before = files[sid]
            else:
                sid = dexlib.slugify(row["name"])
                if not sid or sid in ids:
                    raise CellError("cannot create '%s': the name is empty or already used" % row["name"])
                path, before = dexlib.SPECIES_DIR / (sid + ".yaml"), {"dex": dex}
            updated = copy.deepcopy(before)
            apply_row(updated, delta)
            clear_cells(updated, cleared)
            errors, warnings = [], []
            if not 1 <= dex <= config.get("dex_size", 151):
                errors.append("dex number %d is outside the dex" % dex)
            other = by_name.get(norm(updated.get("name")))
            if other and other != sid:
                errors.append("the name '%s' is already used by another Pokemon" % updated.get("name"))
            validate.check_species(sid, updated, ids | {sid}, engine, errors, warnings)
            if errors:
                raise CellError("; ".join(errors))
        except CellError as error:
            report.append({"row": label, "problem": str(error)})
            if sid in files:
                handled.add(sid)              # its old snapshot row stays, so it is tried again once fixed
            continue
        new_snapshot[sid] = row
        handled.add(sid)
        if dexlib.prune(updated) != dexlib.prune(before):
            dexlib.write_species(path, updated)
            changed += 1
        by_name = {n: s for n, s in by_name.items() if s != sid}
        by_name[norm(updated.get("name"))] = sid
        files[sid] = (path, updated)
        ids.add(sid)
        if delta.get("evolves_from") and delta.get("evo_condition"):
            pending_evolutions.append((label, delta["evolves_from"], delta["evo_condition"], sid))

    # Evolutions are written on the evolved Pokemon's row, but stored on the one that evolves.
    for label, source_name, condition, target in pending_evolutions:
        source_id = by_name.get(norm(source_name))
        if not source_id or source_id == target:
            report.append({"row": label, "problem": "evolves_from '%s' is not the name of another Pokemon in the sheet" % source_name})
            continue
        path, before = files[source_id]
        updated = copy.deepcopy(before)
        evolution = dict(dexlib.text_to_evolution(condition), into=target)
        others = [e for e in dexlib.listing(updated.get("evolutions")) if isinstance(e, dict) and e.get("into") != target]
        updated["evolutions"] = others + [evolution]
        errors = []
        validate.check_species(source_id, updated, ids, engine, errors, [])
        if errors:
            report.append({"row": label, "problem": "; ".join(errors)})
        elif dexlib.prune(updated) != dexlib.prune(before):
            dexlib.write_species(path, updated)
            files[source_id] = (path, updated)
            changed += 1

    SNAPSHOT.write_text(json.dumps(new_snapshot, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for entry in report:
        print("SKIPPED %s: %s" % (entry["row"], entry["problem"]))
    print("Sheet import: %d rows read, %d species files changed, %d rows skipped" % (len(rows), changed, len(report)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
