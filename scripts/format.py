#!/usr/bin/env python3
"""Rewrite every species file in the standard layout (same content, tidy formatting)."""
import sys

import dexlib


def main():
    species, problems = dexlib.load_species()
    for path, msg in problems:
        print("ERROR %s: %s" % (path.name, msg))
    failed = len(problems)
    for sid, path, data in species:
        try:
            dexlib.write_species(path, data)
        except ValueError as error:
            print("ERROR %s" % error)
            failed += 1
    print("%d files formatted, %d skipped" % (len(species) + len(problems) - failed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
