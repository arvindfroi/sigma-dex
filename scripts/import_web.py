#!/usr/bin/env python3
"""Copy what people saved on the website into the species files.

    python scripts/import_web.py              # reads the database named in data/config.yaml
    python scripts/import_web.py rows.json    # or a file with the same rows (for testing)

Every save on the website is one row in the database: a complete copy of that Pokemon.
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
        url = "%s/rest/v1/species_edits?select=id,species_id,data,editor,created_at&id=gt.%d&order=id.asc&limit=1000" % (
            settings["url"].rstrip("/"), rows[-1]["id"] if rows else cursor)
        request = urllib.request.Request(url, headers={"apikey": settings["key"], "User-Agent": "sigma-dex"})
        with urllib.request.urlopen(request) as response:
            page = json.load(response)
        rows.extend(page)
        if len(page) < 1000:
            return rows


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

    for row in rows:
        sid, editor = str(row.get("species_id")), row.get("editor") or "someone"
        label = "%s (saved by %s)" % (sid, editor)
        try:
            if not isinstance(row.get("data"), dict) or dexlib.slugify(sid) != sid or not sid:
                raise ValueError("the saved data is not a Pokemon")
            updated = known_fields_only(row["data"])
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
                if not isinstance(dex, int) or isinstance(dex, bool) or not 1 <= dex <= config.get("dex_size", 100):
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

    if rows:
        CURSOR.write_text("%d\n" % rows[-1]["id"])
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report[-50:], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for entry in report:
        print("NOT USED %s: %s" % (entry["row"], entry["problem"]))
    print("Website import: %d saves read, %d species files changed, %d problems listed" % (len(rows), changed, len(report)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
