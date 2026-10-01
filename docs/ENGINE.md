# The game we build on

## The base: pokeemerald-expansion

[`rh-hideout/pokeemerald-expansion`](https://github.com/rh-hideout/pokeemerald-expansion)
(release 1.17.1, September 2026) is the standard base for modern Emerald hacks. It is
Pokemon Emerald's decompiled source with the battle system and data brought up to the
current games. It is what fixes "Emerald is out of date":

| Problem with plain Emerald | In pokeemerald-expansion |
|---|---|
| No Fairy type | 18 types, Fairy included |
| Physical/special decided by type | Decided per move, like the modern games |
| 354 moves, 77 abilities | 846 moves and 319 abilities from generation 1-9 |
| No hidden abilities | Three ability slots, one hidden |
| Names max 10 letters | 12 letters (category 12, move and ability names 16) |
| Generation 3 battle rules | Every rule can be set to any generation in `include/config/` |
| One file per kind of data | One block per Pokemon holds all of its data |

Also built in and switchable: Mega Evolution, Z-moves, Dynamax, Terastal, an HGSS-style
Pokedex, DexNav, level caps, following Pokemon, day and night, a debug menu, and an
automated battle-test system (`make check`) - useful for proving that a new move or
ability does what it should.

Checked against the source on 2026-10-02. Lists of what exists:
[`data/engine/expansion.yaml`](../data/engine/expansion.yaml).

## New moves and abilities

Anything not in that list is ours to program. In expansion a move is one block of data in
`src/data/moves_info.h` plus, for a new *effect*, battle-script code; an ability is an entry
in `src/data/abilities.h` plus code where it triggers. Each one can get an automated test.
To be programmable, a new move or ability needs an exact description: name, type,
physical/special/status, power, accuracy, PP, target, and what precisely happens.

## Native PC program or GBA ROM?

pokeemerald-expansion builds a **GBA ROM**. A ready-made native PC version of it does not
exist. What was found (2026-10-02):

| Project | What it is | State |
|---|---|---|
| `fuddlesworth/pokeemerald-native` | Native port of **plain** Emerald; Windows, Linux, macOS | Works - built and tested here |
| `NTx86/pokeemerald-sdl2pc` | The original native port of plain Emerald; Windows, Linux | Works |
| ...its branch `pc_port-expansion-test-attempt` | Attempt to port expansion | Experimental; last commit (2026-09-08) calls its own fixes "very bad and hacky" |
| `MinZe25/pokeemerald-rogue-vita` | Emerald Rogue (an older expansion) running natively on PS Vita, Linux, Windows | Works; had to fix many crashes that the GBA silently tolerates |
| `hirata-producoes/pokemon-regionalidades` | A hack on expansion 1.16.3 with a native Windows build | In development |

So a native expansion build is possible - two projects have done it - but it is a porting
job, not a download, and none of them builds on macOS.

**The plan this leaves:** build the game on expansion now and play it as a GBA ROM in an
emulator (mGBA runs on every computer and phone). Pokemon, moves, abilities, maps and
scripts are identical work for both targets, so nothing is lost. A native PC build can be
added later by porting the platform layer of one of the projects above.

## How a Pokemon is stored

In expansion every Pokemon is one block in `src/data/pokemon/species_info/`, holding base
stats, types, catch rate, exp and EV yield, items, gender ratio, egg data, three abilities,
name, category, height, weight, dex text, body color, sprites and their positions, and
links to its level-up, teachable and egg move lists and its evolutions. Our species files
contain all of that except the art.

`scripts/export_engine.py` still writes the **old plain-Emerald layout** into
`export/engine/`. It will be replaced by an expansion exporter once expansion can be built
here to test it against.

## Proof of concept so far (2026-10-02, plain Emerald)

Leafing was filled in with draft values and tested in a real game: `pokeemerald-native`
was built on macOS, Leafing's exported data was put in Treecko's slot (Treecko's sprite as
placeholder), and the port's automated test played a new game with it. The game showed
"Go! LEAFING!", "LEAFING used TACKLE!", type GRASS, ability OVERGROW and the expected
level 5 stats. That proved the route species file > export > game. It has to be repeated
on expansion.

## Tools the community uses

| Tool | For | macOS |
|---|---|---|
| [Porymap](https://github.com/huderlem/porymap) | Drawing maps | Yes |
| [Poryscript](https://github.com/huderlem/poryscript) | Writing events and dialogue in a readable language | Yes |
| [Porytiles](https://github.com/grunt-lucas/porytiles) | Turning PNG tilesets into game tilesets | Yes |
| [mGBA](https://github.com/mgba-emu/mgba) | Playing and debugging the ROM | Yes |
| Expansion's own `trainers.party` format | Trainer teams as plain text | - |
| Expansion's debug menu and sprite visualizer | Testing in-game, positioning sprites | - |

Sprites are ordinary indexed PNGs (any pixel-art editor); expansion's tutorial
[`how_to_new_pokemon.md`](https://github.com/rh-hideout/pokeemerald-expansion/blob/master/docs/tutorials/how_to_new_pokemon.md)
covers adding a species including sprites and cry.

## Sharing the game legally

- Hacks are shared as a **patch** (BPS/UPS) that players apply to their own Emerald ROM.
  The patch contains only the differences, not Nintendo's game.
- A native PC program contains the game's graphics and sound, so it cannot simply be handed
  out. The Vita port solves this by shipping without assets and reading them from the
  player's own ROM at startup.
- Expansion asks hacks to credit RHH (the team behind it).
- This repository holds only our own work. The game's source code stays out of it.
