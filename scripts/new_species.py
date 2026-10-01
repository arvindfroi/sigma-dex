#!/usr/bin/env python3
"""Create a blank species file.

    python scripts/new_species.py 17 "Leafmon" --types Grass Steel
"""
import argparse
import sys

import dexlib


def main():
    parser = argparse.ArgumentParser(description="Create a blank species file in data/species/.")
    parser.add_argument("dex", type=int, help="dex number (slot)")
    parser.add_argument("name", help="name of the Pokemon")
    parser.add_argument("--types", nargs="*", default=[], help="one or two types")
    args = parser.parse_args()

    species, _ = dexlib.load_species()
    for sid, path, data in species:
        if data.get("dex") == args.dex:
            sys.exit("Slot #%d is already taken by %s (%s)" % (args.dex, data.get("name"), path.name))
    path = dexlib.SPECIES_DIR / (dexlib.slugify(args.name) + ".yaml")
    if path.exists():
        sys.exit("%s already exists" % path.name)
    dexlib.write_species(path, {"dex": args.dex, "name": args.name, "types": args.types})
    print("Created %s - fill it in, then run scripts/validate.py" % path.relative_to(dexlib.ROOT))


if __name__ == "__main__":
    main()
