# Hand-written game code

The Pokemon themselves are generated from the species files. This folder holds what has to
be written by hand: new moves, new abilities, and the tests that prove they work.
`scripts/apply_to_expansion.py` puts all of it into a checkout of pokeemerald-expansion
(see [docs/BUILDING.md](../docs/BUILDING.md)).

| Folder | Contains |
|---|---|
| `moves/` | One `.h` file per new move: its entry for the game's move table, starting with `[MOVE_NAME] =` |
| `abilities/` | One `.h` file per new ability: its entry for the game's ability table, starting with `[ABILITY_NAME] =` |
| `patches/` | Changes to the game's own code (`git diff` format), for behaviour that plain data cannot express |
| `tests/` | Battle tests for all of the above, in the game's test language |
| `examples/` | One worked example of each, applied only with `--examples` |

## Adding a new move or ability

1. It is described on the website under **New moves** / **New abilities**, which stores it
   in `data/custom_moves.yaml` or `data/custom_abilities.yaml`.
2. Write its entry in `moves/` or `abilities/`. The constant must be the name in capitals
   with underscores (`Sigma Strike` > `MOVE_SIGMA_STRIKE`).
   - Many moves need nothing more: damage, accuracy, priority, contact, stat changes, status
     chances, recoil, multi-hit and more are fields in the move table.
   - Anything else needs code. Make the change in the game checkout, then save it with
     `git diff > game/patches/<name>.patch`.
3. Write a test in `tests/` whose name starts with `Sigma`.
4. Apply, build, and run `make check TESTS="Sigma"`.
5. When the tests pass, set `implemented: true` on its entry in the data file. From then on
   Pokemon that use it are exported with it, and the website shows it as "in the game".

## The examples

`examples/` contains Sigma Strike (a move made of data only) and Sigma Aura (an ability that
needs a code patch), with four tests. They were applied to expansion 1.17.1 on 2026-10-02
and all tests passed. They are references, not part of our dex.
