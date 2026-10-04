#!/usr/bin/env python3
"""Copy what people saved on the website into the species files.

    python scripts/import_web.py              # reads the database named in data/config.yaml
    python scripts/import_web.py rows.json    # or a file with the same rows (for testing)

Every save on the website is one row in the database: a complete copy of that Pokemon.
A row of kind "reorder" is different: it holds steps that move Pokemon to other dex numbers
(see dexlib.change_layout) and changes only the `dex` numbers.
Rows newer than data/web_edits_cursor.txt are applied in order, so the newest save wins.
A row that would break a species file is skipped and reported in export/web_problems.json
(shown on the website). Art paths and sprite details cannot be edited on the website and
are always kept from the species file.
"""
import copy
import json
import sys
import urllib.request

import dexlib
import validate
from dexlib import ROOT, norm

REPORT = ROOT / "export" / "web_problems.json"
CURSOR = ROOT / "data" / "web_edits_cursor.txt"
KEPT_FROM_FILE = ("assets", "engine")


def read_cursor():
    return int(CURSOR.read_text().strip() or 0) if CURSOR.exists() else 0


def fetch_rows(settings, cursor):
    rows = []
    while True:
        url = "%s/rest/v1/species_edits?select=id,kind,species_id,data,editor,created_at&id=gt.%d&order=id.asc&limit=1000" % (
            settings["url"].rstrip("/"), rows[-1]["id"] if rows else cursor)
        request = urllib.request.Request(url, headers={"apikey": settings["key"], "User-Agent": "sigma-dex"})
        with urllib.request.urlopen(request) as response:
            page = json.load(response)
        rows.extend(page)
        if len(page) < 1000:
            return rows


def empty(value):
    return value in (None, "", [], {})


def changed(new, old):
    return not (empty(new) and empty(old)) and new != old


def merge_edit(current, new, base):
    """Apply only what the editor actually changed (new versus the `base` they started from) onto the file.

    The website sends the whole Pokemon. If the page was opened before somebody else's change
    landed, saving everything would undo that change; this keeps it.
    """
    merged = copy.deepcopy(current)
    for key, parts in dexlib.FIELDS.items():
        if key in KEPT_FROM_FILE or key == "dex":
            continue
        if parts and isinstance(new.get(key) or {}, dict) and isinstance(base.get(key) or {}, dict):
            for part in parts:
                value, before = (new.get(key) or {}).get(part), (base.get(key) or {}).get(part)
                if changed(value, before):
                    if not isinstance(merged.get(key), dict):
                        merged[key] = {}
                    merged[key][part] = copy.deepcopy(value)
        elif changed(new.get(key), base.get(key)):
            merged[key] = copy.deepcopy(new.get(key))
    return merged


def known_fields_only(data):
    """Keep only fields a species file can hold, so stray input never reaches a file."""
    cleaned = {}
    for key, value in data.items():
        if key not in dexlib.FIELDS:
            continue
        if dexlib.FIELDS[key] and isinstance(value, dict):
            value = {sub: v for sub, v in value.items() if sub in dexlib.FIELDS[key]}
        cleaned[key] = value
    return cleaned


def main():
    config = dexlib.load_config()
    cursor = read_cursor()
    if len(sys.argv) > 1:
        rows = [r for r in json.load(open(sys.argv[1], encoding="utf-8")) if r["id"] > cursor]
    else:
        settings = config.get("web_edits") or {}
        if not settings.get("url") or not settings.get("key"):
            print("No website database configured (web_edits in data/config.yaml) - nothing to import.")
            return 0
        try:
            rows = fetch_rows(settings, cursor)
        except OSError as error:
            print("WARNING: the website database could not be read (%s). Nothing imported." % error)
            return 0

    species, problems = dexlib.load_species()
    if problems:
        sys.exit("Fix the species files first (run scripts/validate.py).")
    engine = dexlib.load_engine()
    files = {sid: (path, data) for sid, path, data in species}
    report = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else []
    changed = 0

    custom = {kind: dexlib.load_custom(kind) for kind in ("moves", "abilities")}
    custom_changed = set()

    for row in rows:
        sid, editor = str(row.get("species_id")), row.get("editor") or "someone"
        label = "%s (saved by %s)" % (sid, editor)
        if row.get("kind") in ("move", "ability"):
            kind = "moves" if row["kind"] == "move" else "abilities"
            label = "new %s %s" % (row["kind"], label)
            try:
                data = row.get("data")
                if not isinstance(data, dict) or dexlib.slugify(sid) != sid or not sid:
                    raise ValueError("the saved data is not a %s" % row["kind"])
                old = next((e for e in custom[kind] if e["id"] == sid), None)
                if data.get("deleted"):
                    custom[kind] = [e for e in custom[kind] if e["id"] != sid]
                else:
                    entry = {k: data.get(k) for k in dexlib.CUSTOM_FIELDS[kind] if k not in ("id", "implemented")}
                    entry["id"] = sid
                    if old and old.get("implemented"):
                        entry["implemented"] = old["implemented"]   # only set by whoever programs it
                    existing = {norm(name) for name in engine["engine_names"][kind]}
                    taken = {norm(e["name"]) for e in custom[kind] if e["id"] != sid}
                    found = dexlib.check_custom(kind, entry, existing)
                    if norm(entry.get("name") or "") in taken:
                        found.append("another new %s already has that name" % row["kind"])
                    if found:
                        raise ValueError("; ".join(found))
                    custom[kind] = [e for e in custom[kind] if e["id"] != sid] + [entry]
                custom_changed.add(kind)
                report = [entry for entry in report if entry.get("species") != row["kind"] + ":" + sid]
            except Exception as error:
                report.append({"id": row.get("id"), "species": row["kind"] + ":" + sid, "row": label, "problem": str(error)})
            continue
        if row.get("kind") == "reorder":
            # Several dex numbers change at once: all of it is applied, or none of it.
            label = "reorder (saved by %s)" % editor
            try:
                size = config.get("dex_size", 151)
                layout = [None] * size
                for other, (_, data) in files.items():
                    if isinstance(data.get("dex"), int) and 1 <= data["dex"] <= size:
                        layout[data["dex"] - 1] = other
                new = dexlib.change_layout(layout, (row.get("data") or {}).get("ops"))
                for number, other in enumerate(new, 1):
                    if other and files[other][1].get("dex") != number:
                        path, data = files[other]
                        data = dict(data, dex=number)
                        dexlib.write_species(path, data)
                        files[other] = (path, data)
                        changed += 1
                report = [entry for entry in report if entry.get("species") != "reorder"]
            except Exception as error:
                report.append({"id": row.get("id"), "species": "reorder", "row": label, "problem": str(error)})
            continue
        try:
            if not isinstance(row.get("data"), dict) or dexlib.slugify(sid) != sid or not sid:
                raise ValueError("the saved data is not a Pokemon")
            updated = known_fields_only(row["data"])
            base = row["data"].get("_base")
            if sid in files and isinstance(base, dict):
                updated = merge_edit(files[sid][1], updated, known_fields_only(base))
            if sid in files:
                path, current = files[sid]
                updated["dex"] = current.get("dex")
                for key in KEPT_FROM_FILE:
                    updated.pop(key, None)
                    if key in current:
                        updated[key] = copy.deepcopy(current[key])
            else:
                path, current = dexlib.SPECIES_DIR / (sid + ".yaml"), None
                for key in KEPT_FROM_FILE:
                    updated.pop(key, None)
                dex = updated.get("dex")
                if not isinstance(dex, int) or isinstance(dex, bool) or not 1 <= dex <= config.get("dex_size", 151):
                    raise ValueError("a new Pokemon needs a dex slot inside the dex")
                if any(data.get("dex") == dex for _, data in files.values()):
                    raise ValueError("dex slot %d is already taken" % dex)
            others = {norm(data.get("name")) for other, (_, data) in files.items() if other != sid}
            if norm(updated.get("name")) in others:
                raise ValueError("the name '%s' is already used by another Pokemon" % updated.get("name"))
            errors = []
            validate.check_species(sid, updated, set(files) | {sid}, engine, errors, [])
            if errors:
                raise ValueError("; ".join(errors))
            if current is None or dexlib.prune(updated) != dexlib.prune(current):
                dexlib.write_species(path, updated)
                changed += 1
            files[sid] = (path, updated)
            report = [entry for entry in report if entry.get("species") != sid]
        except Exception as error:  # one bad save must never stop the others
            report.append({"id": row.get("id"), "species": sid, "row": label, "problem": str(error)})

    for kind in sorted(custom_changed):
        dexlib.write_custom(kind, custom[kind])
        changed += 1
    if rows:
        CURSOR.write_text("%d\n" % rows[-1]["id"])
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report[-50:], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for entry in report:
        print("NOT USED %s: %s" % (entry["row"], entry["problem"]))
    print("Website import: %d saves read, %d files changed, %d problems listed" % (len(rows), changed, len(report)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
