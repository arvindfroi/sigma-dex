# How the game stores a Pokemon

The target is a PC port of Pokemon Emerald. All ports found (checked 2026-10-02) are built on
the `pret/pokeemerald` decompilation and share one data layout, so the dex does not depend
on which one is chosen:

| Port | Platforms |
|---|---|
| `fuddlesworth/pokeemerald-native` | Windows, Linux, macOS |
| `NTx86/pokeemerald-sdl2pc` (the original) | Windows, Linux |
| `gradenGnostic/pokeemerald-multiplatform` | Windows, Linux, Android |

They are **vanilla Emerald** (generation 3 rules), not `pokeemerald-expansion`. That sets the limits below.

## A Pokemon is spread over these files

`scripts/export_engine.py` writes each of them into `export/engine/`, in the game's own format.

| File in the game | Holds | Our fields |
|---|---|---|
| `include/constants/species.h` | The internal number (`SPECIES_LEAFING`) | `name` |
| `include/constants/pokedex.h` | Dex order | `dex` |
| `src/data/text/species_names.h` | Name, max 10 letters, written in capitals | `name` |
| `src/data/pokemon/species_info.h` | Base stats, types, catch rate, exp yield, EV yield, held items, gender ratio, egg cycles, friendship, growth rate, egg groups, 2 abilities, safari flee rate, body color, no-flip flag | most of the species file |
| `src/data/pokemon/evolution.h` | Up to 5 evolutions: method, parameter, target | `evolutions` |
| `src/data/pokemon/level_up_learnsets.h` + `level_up_learnset_pointers.h` | Level-up moves | `learnset.level_up` |
| `src/data/pokemon/tmhm_learnsets.h` | Which of the 50 TMs / 8 HMs it can use | `learnset.tm_hm` |
| `src/data/pokemon/tutor_learnsets.h` | Which of the 30 tutor moves | `learnset.tutor` |
| `src/data/pokemon/egg_moves.h` | Egg moves | `learnset.egg` |
| `src/data/pokemon/pokedex_entries.h` + `pokedex_text.h` | Category (max 11 letters), height, weight, entry text, picture scale | `category`, `height_m`, `weight_kg`, `description` |
| `graphics/pokemon/<name>/` + `src/data/graphics/pokemon.h` | `front.png`, `anim_front.png`, `back.png`, `icon.png`, `footprint.png`, `normal.pal`, `shiny.pal` | `assets` |
| `src/data/pokemon_graphics/*` and `src/pokemon_icon.c` | Sprite position, elevation, animation, icon palette | `engine` |
| `src/data/pokemon/cry_ids.h` + `sound/` | Cry | `assets.cry` |
| `src/data/wild_encounters.json` | Where it appears | `encounters` |

## Limits that affect design

- **17 types, no Fairy.** Fairy has to be added to the game before a Fairy Pokemon can exist.
- **Names: 10 characters. Category: 11. Move and ability names: 12.**
- **Two abilities per Pokemon, no hidden ability.**
- **354 moves and 77 abilities exist** (`data/engine/gen3.yaml`). Anything else is new code.
- **No physical/special split** - it depends on the move's type.
- **TMs, HMs and tutor moves are fixed lists.**
- **EV yield:** 0-3 per stat. **Base stats, catch rate, base exp:** 0-255.
- **Sprites:** 64x64 pixels, 16 colors (one is transparent), front and back share a palette.

## Proof of concept (2026-10-02)

Leafing was filled in (draft values) and tested in the real game:

1. `fuddlesworth/pokeemerald-native` was cloned and built on macOS (`gmake macos`).
2. The blocks from `export/engine/` were pasted over Treecko's entries (so Treecko's sprite
   acts as placeholder art) and the build was repeated - no errors.
3. The port's own automated test played a new game with Leafing as the starter.

Result: the game shows "Go! LEAFING!" and "LEAFING used TACKLE!", and the summary screen
shows type GRASS, ability OVERGROW, the expected level 5 stats (HP 20) and the moves
Tackle and Leer. The website's "Try it at any level" numbers match the game.

So the route **species file > export > game** works. Still to solve before real use:
adding species as *new* entries instead of replacing existing ones, sprites, and cries.

## Legal note

The port's source code contains Nintendo's game data, so it must stay out of this
repository, and a finished hack should be shared as a patch against it, never as a full
copy or a built game.
