#!/usr/bin/env python3
"""Put the exported dex into a checkout of pokeemerald-expansion.

    python scripts/apply_to_expansion.py /path/to/pokeemerald-expansion [--examples]

Copies export/expansion/ (the Pokemon) and game/ (hand-written moves, abilities, code
patches and tests) into the game's source and hooks them in. Safe to run again after
anything changes: it replaces what it added last time. --examples also applies the
reference examples in game/examples/. Written for expansion 1.17.x.
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import dexlib

SOURCE = dexlib.ROOT / "export" / "expansion"
GAME = dexlib.ROOT / "game"
BEGIN, END = "// SIGMA DEX BEGIN (generated, do not edit)", "// SIGMA DEX END"


def block(text):
    return "%s\n%s%s\n" % (BEGIN, text if text.endswith("\n") else text + "\n", END)


def strip_block(source):
    return re.sub(r"[ \t]*%s\n.*?%s\n" % (re.escape(BEGIN), re.escape(END)), "", source, flags=re.S)


def insert(path, anchor, text, before=True, exact=False, last=False):
    """Insert a marked block before (or after) the line containing `anchor`, replacing an older block.

    exact: the line must equal the anchor (ignoring indentation). last: use the last such line.
    An empty text only removes the older block.
    """
    source = strip_block(path.read_text(encoding="utf-8"))
    lines = source.split("\n")
    hits = [i for i, line in enumerate(lines) if (line.strip() == anchor if exact else anchor in line)]
    if last and hits:
        hits = hits[-1:]
    if len(hits) != 1:
        sys.exit("%s: expected exactly one line containing %r, found %d. Is this expansion 1.17.x?" % (path, anchor, len(hits)))
    if text.strip():
        at = hits[0] if before else hits[0] + 1
        lines[at:at] = block(text).rstrip("\n").split("\n")
    path.write_text("\n".join(lines), encoding="utf-8")


def git(game, *args):
    return subprocess.run(["git", "-C", str(game)] + list(args), capture_output=True, text=True)


def apply_game_code(game, examples):
    """Hand-written moves, abilities, patches and tests from game/ (and game/examples/)."""
    roots = [GAME] + ([GAME / "examples"] if examples else [])
    found = {kind: sorted(path for root in roots for path in (root / kind).glob(pattern))
             for kind, pattern in (("moves", "*.h"), ("abilities", "*.h"), ("patches", "*.patch"), ("tests", "*.c"))}

    constants = {}
    for kind, prefix in (("moves", "MOVE_"), ("abilities", "ABILITY_")):
        target = game / "src" / "data" / "sigma" / kind
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        constants[kind] = []
        for path in found[kind]:
            match = re.search(r"\[(%s\w+)\]\s*=" % prefix, path.read_text(encoding="utf-8"))
            if not match:
                sys.exit("%s does not define a [%sNAME] = entry." % (path, prefix))
            constants[kind].append(match.group(1))
            shutil.copyfile(path, target / path.name)
    insert(game / "include" / "constants" / "moves.h", "MOVES_COUNT_GEN9,", "".join("    %s,\n" % c for c in constants["moves"]), exact=True)
    insert(game / "src" / "data" / "moves_info.h", "// Z-Moves",
           "".join('    #include "sigma/moves/%s"\n' % path.name for path in found["moves"]), exact=True)
    insert(game / "include" / "constants" / "abilities.h", "ABILITIES_COUNT_GEN9,", "".join("    %s,\n" % c for c in constants["abilities"]), exact=True)
    insert(game / "src" / "data" / "abilities.h", "};",
           "".join('    #include "sigma/abilities/%s"\n' % path.name for path in found["abilities"]), exact=True, last=True)

    # Patches change the game's own code. Take out ones that are no longer wanted, add the rest.
    every = sorted(path for root in (GAME, GAME / "examples") for path in (root / "patches").glob("*.patch"))
    for path in every:
        applied = git(game, "apply", "--reverse", "--check", str(path)).returncode == 0
        if path in found["patches"] and not applied:
            result = git(game, "apply", str(path))
            if result.returncode != 0:
                sys.exit("Patch %s does not apply to this version of the game:\n%s" % (path.name, result.stderr))
        elif path not in found["patches"] and applied:
            git(game, "apply", "--reverse", str(path))

    for stale in (game / "test").glob("sigma_code_*.c"):
        stale.unlink()
    for path in found["tests"]:
        shutil.copyfile(path, game / "test" / ("sigma_code_" + path.name))
    return constants, found


def generated(name):
    text = (SOURCE / name).read_text(encoding="utf-8")
    return "".join(line + "\n" for line in text.split("\n") if line and not line.startswith("// GENERATED"))


def main():
    args = [a for a in sys.argv[1:] if a != "--examples"]
    if len(args) != 1:
        sys.exit(__doc__)
    game = Path(args[0]).expanduser()
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
    constants, found = apply_game_code(game, "--examples" in sys.argv)
    engine = dexlib.load_engine()
    for kind, prefix in (("moves", "MOVE_"), ("abilities", "ABILITY_")):
        for entry in engine["custom"][kind]:
            const = prefix + dexlib.constant(entry["name"])
            if entry.get("implemented") and const not in constants[kind]:
                sys.exit("%s is marked implemented in data/custom_%s.yaml but game/%s/ has no file defining %s."
                         % (entry["name"], kind, kind, const))
    print("Applied %d Pokemon, %d new moves, %d new abilities, %d code patches to %s" % (
        len(species.strip().split("\n")), len(constants["moves"]), len(constants["abilities"]), len(found["patches"]), game))
    print('Build the game as usual. To run the checks: make check TESTS="Sigma"')


if __name__ == "__main__":
    main()
