#!/usr/bin/env python3
"""The worklist for Claude: Pokemon whose designers ticked "Let Claude fill in the rest" on the website.

    python scripts/claude_fill.py            # those that asked and still miss something
    python scripts/claude_fill.py waffy      # one Pokemon, whether it asked or not

For each one it prints what is filled in, what is missing, the designer's notes for Claude
(`design.wishes`), and its evolution family (so a line is filled in as a whole: stats that grow,
shared moves). How Claude should fill them in: docs/CLAUDE_FILL.md.
"""
import sys

import yaml

import dexlib


def family(sid, species):
    """Every species in the same evolution line, first stage first."""
    into = {s: [e.get("into") for e in dexlib.listing(d.get("evolutions")) if isinstance(e, dict)] for s, _, d in species}
    parent = {child: s for s, children in into.items() for child in children}
    root = sid
    while root in parent:
        root = parent[root]
    line, todo = [], [root]
    while todo:
        current = todo.pop(0)
        line.append(current)
        todo += into.get(current, [])
    return line


def main():
    species, _ = dexlib.load_species()
    by_id = {sid: data for sid, _, data in species}
    wanted = sys.argv[1:] or [sid for sid, _, data in species if dexlib.section(data, "design").get("claude_fill")]
    shown = 0
    for sid in wanted:
        data = by_id.get(sid)
        if data is None:
            print("%s: no such Pokemon" % sid)
            continue
        missing = [label for section, label, path in dexlib.CHECK_LIST if section != "Art" and not dexlib.has(data, path)]
        if not missing and not sys.argv[1:]:
            continue
        shown += 1
        design = dexlib.section(data, "design")
        print("=" * 80)
        print("%s (#%s, %s)" % (data.get("name"), data.get("dex"), "/".join(data.get("types") or ["no type"])))
        print("Missing: " + (", ".join(missing) or "nothing"))
        print("Notes for Claude: " + (design.get("wishes") or "(none)"))
        line = family(sid, species)
        if len(line) > 1:
            print("Family: " + " -> ".join("%s%s" % (by_id[s].get("name"), " (this one)" if s == sid else "") for s in line if s in by_id))
        print("-" * 80)
        print(yaml.safe_dump({k: v for k, v in data.items() if k not in ("assets", "engine")}, sort_keys=False, allow_unicode=True).rstrip())
    if not shown:
        print("Nobody is waiting for Claude.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
