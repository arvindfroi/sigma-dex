#!/usr/bin/env python3
"""Put the exported dex into a checkout of pokeemerald-expansion.

    python scripts/apply_to_expansion.py /path/to/pokeemerald-expansion

Copies export/expansion/ into the game's source and hooks it in at the places the game
reserves for custom species. Safe to run again after the dex changes: it replaces what it
added last time. Written for expansion 1.17.x.
"""
import re
import shutil
import sys
from pathlib import Path

import dexlib

SOURCE = dexlib.ROOT / "export" / "expansion"
BEGIN, END = "// SIGMA DEX BEGIN (generated, do not edit)", "// SIGMA DEX END"


def block(text):
    return "%s\n%s%s\n" % (BEGIN, text if text.endswith("\n") else text + "\n", END)


def strip_block(source):
    return re.sub(r"[ \t]*%s\n.*?%s\n" % (re.escape(BEGIN), re.escape(END)), "", source, flags=re.S)


def insert(path, anchor, text, before=True):
    """Insert a marked block before (or after) the line containing `anchor`, replacing an older block."""
    source = strip_block(path.read_text(encoding="utf-8"))
    lines = source.split("\n")
    hits = [i for i, line in enumerate(lines) if anchor in line]
    if len(hits) != 1:
        sys.exit("%s: expected exactly one line containing %r, found %d. Is this expansion 1.17.x?" % (path, anchor, len(hits)))
    at = hits[0] if before else hits[0] + 1
    lines[at:at] = block(text).rstrip("\n").split("\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def generated(name):
    text = (SOURCE / name).read_text(encoding="utf-8")
    return "".join(line + "\n" for line in text.split("\n") if line and not line.startswith("// GENERATED"))


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    game = Path(sys.argv[1]).expanduser()
    if not (game / "src" / "data" / "pokemon" / "species_info.h").is_file():
        sys.exit("%s does not look like a pokeemerald-expansion checkout." % game)

    target = game / "src" / "data" / "pokemon" / "sigma"
    target.mkdir(exist_ok=True)
    for name in ("species_info.h", "level_up_learnsets.h", "teachable_learnsets.h", "egg_moves.h"):
        shutil.copyfile(SOURCE / name, target / name)
    shutil.copyfile(SOURCE / "sigma_dex_test.c", game / "test" / "sigma_dex.c")

    species = generated("species_enum.h")
    dex = generated("pokedex_enum.h")
    if not species.strip():
        sys.exit("No Pokemon are ready to export yet - see export/expansion/NOT_READY.md.")
    last = dex.strip().split("\n")[-1].strip().rstrip(",")

    insert(game / "include" / "constants" / "species.h", "Add any custom species between here and SPECIES_CUSTOM_END", species, before=False)
    pokedex = game / "include" / "constants" / "pokedex.h"
    insert(pokedex, "NATIONAL_DEX_PECHARUNT,", dex, before=False)
    source = pokedex.read_text(encoding="utf-8")
    source, count = re.subn(r"(#if P_GEN_9_POKEMON == TRUE\n\s*#define NATIONAL_DEX_COUNT\s+)NATIONAL_DEX_\w+", r"\g<1>" + last, source)
    if count != 1:
        sys.exit("%s: could not find the NATIONAL_DEX_COUNT line to update." % pokedex)
    pokedex.write_text(source, encoding="utf-8")
    insert(game / "src" / "pokemon.c", '#include "data/pokemon/egg_moves.h"',
           '#include "data/pokemon/sigma/level_up_learnsets.h"\n#include "data/pokemon/sigma/teachable_learnsets.h"\n#include "data/pokemon/sigma/egg_moves.h"\n',
           before=False)
    insert(game / "src" / "data" / "pokemon" / "species_info.h", "You may add any custom species below this point",
           '    #include "sigma/species_info.h"\n')
    print("Applied %d Pokemon to %s" % (len(species.strip().split("\n")), game))
    print('Build the game as usual. To run the generated checks: make check TESTS="Sigma dex"')


if __name__ == "__main__":
    main()
