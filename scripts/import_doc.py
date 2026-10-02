#!/usr/bin/env python3
"""Copy changes from the group's Google Doc (the "#12 Name (Lv 16) (Type, Type)" list) into the species files.

    python scripts/import_doc.py              # uses the DOC_TXT_URL environment variable
    python scripts/import_doc.py doc.txt      # or a downloaded text file / another URL

The doc only carries name, types and how a Pokemon evolves from the entry before it. Rules:
- Only lines that CHANGED since the last import are applied (data/doc_snapshot.json remembers
  the doc), so the doc never overwrites what was edited on the website or in the sheet.
- A new line in an empty slot creates a new Pokemon.
- Anything on a line that is not understood is kept as a note on the Pokemon, not thrown away.
"""
import copy
import json
import os
import re
import sys
import urllib.request

import dexlib
import validate
from dexlib import ROOT, norm

REPORT = ROOT / "export" / "doc_problems.json"
SNAPSHOT = ROOT / "data" / "doc_snapshot.json"
TYPE_WORDS = {t.lower(): t for t in dexlib.TYPES + ["Stellar"]}
NOTE_PREFIXES = ("From the Google Doc:", "Doc lists", "Written as")   # notes this importer may replace


def parse_line(text):
    """'Brawleo (Lv 25) (Normal, Fighting)' -> name, types, how it is reached, leftover text."""
    groups = re.findall(r"\(([^)]*)\)", text)
    name = re.split(r"\(", text, 1)[0].strip()
    extra = []
    if "/" in name:                       # alternatives such as "Maagamad/gullmire": first one is the working name
        extra.append(name)
        name = name.split("/")[0].strip()
    name = " ".join(word.capitalize() if word.islower() else word for word in name.split())
    types, reached = [], None
    for group in groups:
        words = [w for w in re.split(r"[,/\s]+", group.strip()) if w and w != "?"]
        level = re.match(r"^lv\.?\s*(\d+)$", group.strip(), re.I)
        if level:
            reached = {"method": "level", "level": int(level.group(1))}
        elif words and all(w.lower() in TYPE_WORDS for w in words):
            types = [TYPE_WORDS[w.lower()] for w in words][:2]
            if "?" in group:
                extra.append("(%s)" % group)
        elif re.search(r"\bstone\b", group, re.I) and "?" not in group:
            reached = {"method": "item", "item": " ".join(w.capitalize() for w in group.split())}
        else:
            extra.append("(%s)" % group)
    return name, types, reached, " ".join(extra)


def read_lines(source):
    if re.match(r"^https?://", source):
        try:
            with urllib.request.urlopen(urllib.request.Request(source, headers={"User-Agent": "sigma-dex"})) as response:
                text = response.read().decode("utf-8-sig")
        except OSError as error:
            text = "<html %s" % error
        if "<html" in text[:300].lower():
            print("WARNING: the Google Doc is not readable. Set its sharing to 'Anyone with the link'. Nothing imported.")
            return None
    else:
        text = open(source, encoding="utf-8-sig").read()
    lines = {}
    for line in text.replace("\r", "").split("\n"):
        match = re.match(r"^\s*\\?#\s*(\d+)\s*(.*)$", line)
        if match:
            lines[int(match.group(1))] = match.group(2).strip()
    return lines


def main():
    config = dexlib.load_config()
    source = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("DOC_TXT_URL")
    if not source:
        print("No doc configured (DOC_TXT_URL is not set) - nothing to import.")
        return 0
    lines = read_lines(source)
    if lines is None:
        return 0
    species, problems = dexlib.load_species()
    if problems:
        sys.exit("Fix the species files first (run scripts/validate.py).")
    engine = dexlib.load_engine()
    by_dex = {data.get("dex"): [sid, path, data] for sid, path, data in species}
    ids = {sid for sid, _, _ in species}
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8")) if SNAPSHOT.exists() else {}
    new_snapshot, report, changed = dict(snapshot), [], set()

    def save(entry, updated, label):
        sid, path, current = entry
        errors = []
        others = {norm(e[2].get("name")) for e in by_dex.values() if e[0] != sid}
        if norm(updated.get("name")) in others:
            errors.append("the name '%s' is already used by another Pokemon" % updated.get("name"))
        validate.check_species(sid, updated, ids | {sid}, engine, errors, [])
        if errors:
            report.append({"row": label, "problem": "; ".join(errors)})
            return False
        if dexlib.prune(updated) != dexlib.prune(current):
            dexlib.write_species(path, updated)
            changed.add(sid)
        entry[2] = updated
        return True

    for dex in sorted(lines):
        text = lines[dex]
        if snapshot.get(str(dex), "") == text or not 1 <= dex <= config.get("dex_size", 100):
            continue
        label = "Doc line #%d %s" % (dex, text)
        if not text:
            new_snapshot[str(dex)] = text      # a line was emptied: Pokemon are never deleted automatically
            continue
        name, types, reached, extra = parse_line(text)
        if not name:
            report.append({"row": label, "problem": "no name found on this line"})
            continue
        if dex in by_dex:
            entry = by_dex[dex]
        else:
            sid = dexlib.slugify(name)
            if not sid or sid in ids:
                report.append({"row": label, "problem": "cannot create '%s': the name is empty or already used" % name})
                continue
            entry = by_dex[dex] = [sid, dexlib.SPECIES_DIR / (sid + ".yaml"), {"dex": dex}]
            ids.add(sid)
        updated = copy.deepcopy(entry[2])
        updated["name"] = name
        if types:
            updated["types"] = types
        design = updated.get("design") if isinstance(updated.get("design"), dict) else {}
        notes = design.get("notes")
        if extra and (not notes or str(notes).startswith(NOTE_PREFIXES)):
            design["notes"] = "From the Google Doc: %s" % text
        elif not extra and notes and str(notes).startswith(NOTE_PREFIXES):
            design["notes"] = None
        updated["design"] = design
        if not save(entry, updated, label):
            continue
        if reached and dex - 1 in by_dex:
            previous = by_dex[dex - 1]
            earlier = copy.deepcopy(previous[2])
            others = [e for e in dexlib.listing(earlier.get("evolutions")) if isinstance(e, dict) and e.get("into") != entry[0]]
            earlier["evolutions"] = others + [dict(reached, into=entry[0])]
            if not save(previous, earlier, label):
                continue
        new_snapshot[str(dex)] = text

    SNAPSHOT.write_text(json.dumps(new_snapshot, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for entry in report:
        print("SKIPPED %s: %s" % (entry["row"], entry["problem"]))
    print("Doc import: %d lines read, %d species files changed, %d lines skipped" % (len(lines), len(changed), len(report)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
