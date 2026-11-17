# The game, technically: Origin HeartGold, custom code, the decomp study and the old GBA target

How our mons go into Origin HeartGold and where real Pokemon still show, new abilities and moves as code, the study of moving Origin onto the C decompilation, and (at the end) the earlier GBA target with pokeemerald-expansion. Assets per species and trainers: [TRAINERS_AND_ASSETS.md](TRAINERS_AND_ASSETS.md).

Contents:
- [Replacing the whole dex: where real Pokémon still show](#replacing-the-whole-dex-where-real-pokémon-still-show)
- [New abilities and moves in Origin HeartGold](#new-abilities-and-moves-in-origin-heartgold)
- [Origin HeartGold on the C decompilation: feasibility study (2026-11-11)](#origin-heartgold-on-the-c-decompilation-feasibility-study-2026-11-11)
- [The game we build on](#the-game-we-build-on)
- [Building the game (GBA target)](#building-the-game-gba-target)


---

## Replacing the whole dex: where real Pokémon still show
*(was `docs/DEX_REPLACEMENT.md`)*

Our mons go into Origin HeartGold **in place**: each one takes the slot (species number) of a
Pokémon it replaces. Everything that gives, shows, checks or battles with that species number then
uses our mon by itself: starters, the Kanto prologue (Pikachu, slot 25: tested with Bugmight on
2026-10-04), gifts, trades, wild encounters, trainers, static encounters, the Pokédex, the PC and
following Pokémon. This list is what that does **not** cover. Nothing here has to be solved now; it
is handled when it comes up.

Checked on 2026-10-05 against Origin HeartGold v4.0.3 + English patch rc3 (its own text and data,
read locally; nothing of it is in this repo).

### 1. Text

6925 lines in 384 text banks name a species (outside the species-name banks). Most named: Ho-Oh
205, Entei 201, Meowth 200, Suicune 190, Charmander 111, Gyarados 99, Mew 95, Lugia 95, Pikachu 93,
Unown 90, Raikou 89, Mewtwo 85, Arceus 84, Slowpoke 82, Celebi 80, Venusaur 77, Gloom 72,
Swablu 69, Magikarp 69, Eevee 63, Totodile 58, Lapras 57, Clefairy 55, Manaphy 54, Marill 52.

- **By script:** every old name becomes the new one (a name map from the slots we fill). Pokédex
  entries (bank 791) are replaced by ours.
- **By hand, where the story needs one particular Pokémon:**
  - Slowpoke Well and Team Rocket cutting Slowpoke tails (Azalea Town, Slowpoke Well).
  - The three legendary beasts and the Burned Tower; Eusine chasing Suicune (Ecruteak, many routes).
  - Ho-Oh / Bell Tower and Lugia / Whirl Islands, the Kimono Girls (with the Eevee evolutions).
  - The Red Gyarados at Lake of Rage.
  - Unown and the Ruins of Alph (researchers, Unown Report).
  - Sudowoodo on Route 36, the sleeping Snorlax, the Lapras in Union Cave on Fridays.
  - Celebi and Arceus events, Origin's extra legendary events (Kyogre, Palkia, Giratina, Manaphy, ...).
  - Trainer lines that name their party ("You're up first, Lucario!", bank 587): they must match
    the parties we give.
  - Lines in Origin's Kanto prologue that name Pikachu.

### 2. Pictures that are not the usual sprites

- Title screen: vanilla HeartGold has a **3D model** of Ho-Oh (`a/0/4/6` members 25-29, sparkles 38-40),
  but **Origin's title screen never shows it** (checked in rc8 on 2026-11-12: the top screen is the logo,
  the bottom screen cycles 2D art of Red's starters). Nothing to replace there.
- The intro (the professor shows a Pokémon).
- Ruins of Alph sliding puzzles (Kabuto, Omanyte, Aerodactyl, Ho-Oh panels).
- Overworld Pokémon on the maps (checked 2026-10-08 in Origin's map data, `a/0/3/2`):
  - **1544 objects use the normal follower sprite** of their species (the beasts in the Burned
    Tower, the birds, Mewtwo, Dialga/Palkia/Giratina, the Regis, Celebi, Shaymin, Kimono Girl
    Eeveelutions, Pokémon standing next to trainers, ...). They show our mon by themselves once it
    has a follower sprite. Origin moved most story Pokémon over to these; vanilla HeartGold used
    separate "static" copies.
  - **73 objects still use a separate sprite file** that must be drawn on its own (or the slot left
    alone): the Sudowoodo tree (Route 36), sleeping Snorlax (Route 12 + one cave), Lapras (11
    places, Union Cave), the Red Gyarados (Lake of Rage), tailless Slowpoke (7), the big Ho-Oh
    (Bell Tower roof) and big Lugia (Whirl Islands), the 5 Rotom appliances, and "static" copies of
    Clefairy (Mt. Moon dance), Miltank (farm), Machoke, Ampharos (lighthouse), Aipom, Kyogre,
    Jigglypuff, Abra, Dratini, Dodrio, Blissey, Diglett, Slowpoke, Slowbro, Psyduck, Poliwrath,
    Meowth, Oddish, Machop, Farfetch'd and Zubat. Same format as follower sprites.
- The Clear Bell / Lugia cutscenes (Origin keeps them in full): the bird is its own sprite,
  `HOU_OBJ01` / `LUG_OBJ01` (`a/0/8/1` members 210/211): 7 frames of 64x64, seen from the front
  while it flaps and lands, drawn to fill the whole frame (so it looks much bigger than the follower
  sprite), and shown with a bigger display mode. The code lowers it from the sky, flaps it and plays
  the cry from the species slot. The 3D models there are bells, leaves/waves and a light ring, not
  Pokémon. So a new bird needs 7 new frames, no 3D work.
- The opening movie (before the title) has its own animated Ho-Oh sprite (`a/2/6/2` members
  23-26 for HG: palette, tiles, animation, cells; 27-30 = SoulSilver's Lugia). It is 2D, not 3D: 6 flap
  frames zoomed by the animation from 5 % to 210 %. **Done for Sabertann on 2026-11-12**
  (`scripts/origin_intro/`): same animation file, new cells/tiles/palette. The intro's other official
  mons (Suicune, Entei, Raikou with Eusine, Suicune on the sea) are still there.
- In Origin, Sudowoodo is not battled at all (it runs off after being watered), Ho-Oh is a gift
  (level 95) and Lugia and Snorlax are battles. All of them take the species number from the script,
  so the battle or gift becomes our mon by itself.
- **MUST FIX before the export (Arvind, 2026-10-18): menu icons and their palettes.** In the game every icon uses
  one of three shared 16-colour palettes (the same for all Pokémon); the studio's icons keep their own colours, so at
  export each icon is mapped to the nearest colours of one palette, and a wrong palette looks bad (Leafing on Pikachu's
  yellow palette came out olive and muddy in the 17 Oct test). The export must choose the best of the three palettes
  per mon (the one that keeps its colours closest), map the icon to it with care (keep the outline and shading), and
  write the choice into the palette table. Found on 17 Oct (`~/sigma-origin/lw/build_lw.py`): Origin reads
  `data/pokeicon.narc` (two icons per species at 7+2s and 8+2s, 8x8 tiles, its own palettes in member 0); the palette
  per species is a u8 table in `arm9.bin` at 0xFF7FC (needs a fresh boot to show, not a savestate). Better icons
  could also come from letting people pick the palette in the studio and showing the icon in the game's colours there.
- Pokédex footprints (16x16, one per species).
- Shiny palettes.

### 3. Sound

Every species has its own cry; changing the pictures keeps the old cry. Chosen (2026-11-14): existing cries changed
(pitch, speed, mixed, effects) as a recipe per Pokemon, made in the website's CRY tab; see [Cries](ART.md#cries).

### 4. Mechanics tied to a species

- Species with forms: Unown (28), Rotom, Deoxys, Giratina, Shaymin, Arceus and Origin's later-gen
  forms. Simplest: our mons go into slots without forms or events.
- **Our own forms (2026-10-20):** species files can now hold `forms` (docs/DEX_DATA.md ("Field guide")): looks-only forms, forms with
  their own types/stats/abilities, and forms that change during play, each with a plain `how`. At export each needs a
  way in Origin: looks-only forms as extra sprites chosen by the game's form number; battle forms as their own species
  entries in Origin's form table (Origin already has later-gen forms; how it stores them is not checked yet); forms that
  switch by item, place, time or in battle need a trigger, possibly code (docs/GAME_TECH.md ("New abilities and moves in Origin HeartGold")). To be worked out
  per form when the first ones are filled in.
- Event species: the Spiky-eared Pichu event, the Arceus event, Pokéwalker species.
- Pokéwalker, Pal Park and GTS connect outside the game: ignored.

#### Slots our mons never take (unless on purpose)

The game runs special code for these species numbers, so a mon put there would get it too:

| Slot | Species | What the game does |
|---|---|---|
| 201 | Unown | 28 forms chosen at random; Ruins of Alph and the Unown Report |
| 327 | Spinda | paints random spots on top of the sprite |
| 351 | Castform | changes form with the weather |
| 386 | Deoxys | 4 forms |
| 412, 413 | Burmy, Wormadam | cloak forms from where they last battled |
| 421 | Cherrim | changes form in sun |
| 422, 423 | Shellos, Gastrodon | east and west sea forms |
| 479 | Rotom | 6 appliance forms |
| 487 | Giratina | Origin form with the Griseous Orb |
| 492 | Shaymin | Sky form, turns back at night or when frozen |
| 493 | Arceus | 17 type forms from plates |
| 172 | Pichu | the Spiky-eared Pichu event |

Origin also adds later species with forms (seasons, regional forms, Vivillon, Minior, ...); the
export script must check each slot for forms before using it.

In the training data the same species are trimmed to one picture each (one Unown, one Arceus, no
Gigantamax), so they do not dominate what the LoRAs learn.

### 5. Choices for the group

- Which slots our mons take (pure, mixed or post-Champion dex is not decided yet). The legendary
  and story Pokémon are where a mixed dex matters most: either a Sigma mon with a fitting role
  (a sea god for Lugia, three beasts for the beasts) or the real one kept until there is a design.
- Who redraws the title screen, intro and Alph puzzles.
- Our legendary trio fits Origin's own weather-trio story (checked 2026-10-08): Red Orb → Groudon
  (lava pool under Mt. Moon), Blue Orb → Kyogre (Seafoam Islands, Reversal Cave), Jade Orb →
  Rayquaza (Sky Pillar Peak, Four Island), the Embedded Tower, Prof. Oak telling the myth of
  Rayquaza calming the other two, and Team Rocket stealing them. Bergflabbser (Water/Ground,
  Drizzle) in slot 382, the drought one in 383 and Maagamad (Weather Switch) in 384 would take over
  all of it. Still needed: the myth lines rewritten by hand, Weather Switch and Oily Arsenal
  programmed (Origin has no source code), and a check that Primal Reversion / Mega Rayquaza cannot
  trigger in those slots. This is part of Origin's late-game Team Rocket story (Saffron and the
  Pokémon League taken over); Executive Ariana uses a level 100 Rayquaza with Delta Stream and
  Dragon Ascent at the League, so her party must be edited to fit Maagamad.

---

## New abilities and moves in Origin HeartGold
*(was `docs/ORIGIN_CUSTOM_CODE.md`)*

Status (2026-10-08): **it works.** A brand-new ability, a test version of Maagamad's *Weather Switch*,
runs in Origin HeartGold v4.0.3 + English patch rc3 and was checked in the emulator: rain turns into
sun, sun turns into rain, and with no weather it picks one at random. It was done by adding our own
code to Origin's battle engine (route 2 below). New moves such as *Oily Arsenal* can be added the same
way, but that has not been built yet.

Short version of the three routes we compared:

| Route | Result |
|---|---|
| 1. Ask the Origin author for the source | Not pursued (Arvind's decision, 2026-10-08). |
| 2. Find the hg-engine version and add our own code | There is no hg-engine version to find: Origin's battle engine is not hg-engine's code (see [What Origin really is](#what-origin-really-is)). But the engine has a clean table of abilities and a list of moves, and **our own code can be added to it directly. Tested and working.** |
| 3. Reuse what is already there, no new code | Can give a new ability or move the exact behaviour of an existing one (a data change), but cannot make anything new. The closest no-code Weather Switch is plain Drizzle or Drought, which misses the point of the ability. |

Nothing from the ROM is in this repository. The test ROM, the screenshots and the working copy are in
`~/sigma-origin/` on Arvind's Mac. The code we wrote is in `scripts/origin_custom/`.

### What Origin really is

We expected a normal hg-engine build (the `README.txt` of the English patch says "v4.0.x: Alex (built on
hg-engine)"). The ROM says otherwise:

- **It is built on the Japanese HeartGold**, not the US one. The ROM header says `IPKJ` (Japan). The
  xdelta patch is applied to the US ROM but replaces almost everything.
- **The code layout is not HeartGold's or hg-engine's.** Origin has 120 overlays (code files that are
  loaded when needed), all uncompressed and at other addresses than in US HeartGold (129 overlays) or a
  stock hg-engine build (152: hg-engine adds overlays 129 and up for its own code). Origin has no
  such overlays.
- **hg-engine's battle scripts are not used.** The script archives hg-engine fills (`a/0/0/0`,
  `a/0/0/1`, `a/0/3/0`) and the old move data (`a/0/1/1`) are the same as in plain HeartGold. Origin
  reads its own files instead: `extra/new_move_data.narc` (moves), `battle/string/battle_string.narc`
  (battle text) and `test/battle_test.narc`.
- **The battle engine is a Gen 5 (Black/White-style) engine.** Overlay 14 (loaded at `0x022007E0`,
  337,216 bytes) contains the typical parts of the Black/White battle system: every ability and every
  special move is a small set of "handlers" that react to battle events (a Pokemon enters, a move's
  power is worked out, the turn ends...), registered through one table for abilities and one list for
  moves. Origin's own abilities (Dragonize, Desert Hawk...) and its own move (Rock Storm, id 920) are in
  those same tables.
- **No compiled hg-engine battle code was found.** We built stock hg-engine (`~/sigma-hgengine`,
  commit `027977c`) and searched Origin for its compiled battle functions (SwitchInAbilityCheck,
  CalcBaseDamage, ServerFieldConditionCheck and the rest of its battle code), ignoring the parts that depend on
  addresses. Almost no matches, so there is no hg-engine commit to line up with.

What Origin does share with hg-engine is **the numbering**:

- Ability ids 0-310 are the same as in hg-engine. Ids 311-326 are Origin's own (Blazing Awe, Mega Claws,
  Wildfire, Aurora Shine, Thunder Roar, Concentrate, Burning Skin, Azure Skin, Grass Skin, Dark Skin,
  Mega Sol, Flame Mane, Ninja Bond, Dragonize, Mystic Dance, Desert Hawk) and are **not** the same as
  hg-engine's 311-319. Id 327 has code and a description but no name, and one species has it.
- Move ids are the same up to 467. Current hg-engine has three placeholder moves at 468-470 that
  Origin does not have, so **from 468 on, an Origin move id is the hg-engine id minus 3** (Blood Moon is
  901 in Origin, 904 in hg-engine). Id 920 is Origin's Rock Storm.
- So the coming export script must look up abilities and moves **by name in Origin's own text banks**,
  not in hg-engine's header files. (`~/sigma-origin/spike_bugmight.py` uses hg-engine's
  `ability.h`, which is only right up to id 310.)

### How abilities work in Origin

| What | Where |
|---|---|
| Ability table: one "add handlers" function per ability id, ids 0-327, no bounds check | `0x0224FF2C` (overlay 14, file offset `0x4F74C`), 328 entries of 4 bytes; read in one place (`0x0223AA5C`, through the pointer at `0x0223AA9C`) |
| An "add handlers" function | 8 bytes: writes the number of handlers and returns a pointer to a list of `{event id, handler function}` pairs |
| Drizzle (2) / Drought (70) | handlers for events 10 (the Pokemon enters battle) and 31 (after its ability changed); both call `0x0223AB80` with the weather (1 = rain, 2 = sun) and the item that makes it last 8 turns instead of 5 (Damp Rock 285, Heat Rock 284) |
| Current weather | `0x02205784` returns it (0 while Cloud Nine or Air Lock is out); stored as a byte in the battle field data |
| Battle random number | `0x0222646C` (r0 = range, returns 0 to range-1) |
| Event value of the moment | `0x0220FCC0` (r0 = value id; id 6 = the Pokemon the event is about) |
| Move list: `{move id, add function}`, 411 entries, searched one by one | `0x02251C90`; the search is `0x0224775C`, the count `0x19B` is in the literal at `0x02247788` |

Ten ability ids have no entry in the table (Natural Cure, Early Bird, Run Away, Sticky Hold, Liquid Ooze,
Gluttony, No Guard, Honey Gather, Multitype and id 0): the engine handles those somewhere else.

### Route 2 in practice: the Weather Switch test

**What was done** (all in `scripts/origin_custom/`):

1. `weather_switch.s`: the new ability in ARM Thumb assembly, 76 bytes. When its Pokemon enters battle
   it reads the weather; rain becomes sun, sun becomes rain, anything else gives rain or sun at random.
   It sets the weather the same way Drizzle and Drought do, so the ability banner, the animation, the
   message and the 5 turns (8 with Heat Rock or Damp Rock) all come from Origin's own code. Plus a
   28-byte "add handlers" function with the list `{event 10, handler}, {event 31, handler}`.
2. Room for the code: overlay 14 has no free space, and during a battle the memory right after it is
   used by other overlays. So the code goes where **Zero to Hero**'s code was (two handlers of 116 and
   96 bytes that nothing else uses). Ability 278 (Zero to Hero) becomes Weather Switch: its table entry
   points at our function and its name and description are changed. With the whole dex replaced, many
   such abilities (Palafin's, and other signature abilities of Pokemon we do not keep) become free, and
   each one gives both an id and room for code.
3. `build_weather_switch_test.py` assembles the code, writes it into overlay 14 of a working copy of
   the ROM (it first checks that the table entry is the one we expect, so it refuses any other Origin
   build), renames ability 278 to "WeatherSwtch" (names have a 12-character limit), and gives the lab
   rival (trainer 497) two Pokemon: a level 1 Squirtle with Drizzle and a level 5 Vulpix with Weather
   Switch.

```bash
python3 scripts/origin_custom/build_weather_switch_test.py ~/sigma-origin/ws_weather_switch.nds 2
```

The last number is the Squirtle's ability: 2 = Drizzle (expect rain to sun), 70 = Drought (expect sun
to rain), 0 = none (random). It needs `arm-none-eabi-as` (Homebrew) and the hg-engine tools in
`~/sigma-hgengine/tools`.

**Checked in the emulator** (py-desmume, sound off, from the save state just before the lab battle;
ThunderShock knocks the Squirtle out, the rival sends in Vulpix):

| Squirtle's ability | What happened when Vulpix came in | Weather byte in memory |
|---|---|---|
| Drizzle | banner "Vulpix's WeatherSwtch", "The sunlight turned harsh!" | 1 (rain) before, 2 (sun) after, still 2 the next turn |
| Drought | banner "Vulpix's WeatherSwtch", "It started to rain!" | |
| none | banner "Vulpix's WeatherSwtch", "The sunlight turned harsh!" (random: this run picked sun) | |

Screenshots: `~/sigma-origin/poc_weather_switch.png` (not in the repo, it shows game graphics). Not
tested yet: melonDS, real hardware, double battles, Cloud Nine on the field, and Weather Switch against
Primordial Sea or Desolate Land (Origin's own weather code should block the change there, as it does
for Drizzle).

**Limits of this route:**

- The addresses belong to this exact build (v4.0.3 + English rc3). A new Origin version means finding
  the same places again. The table and helper functions are easy to find again, but it is work.
- Space for code comes from abilities and moves we do not use. Each new ability or move costs about
  100-300 bytes, and there are dozens of signature abilities and moves to take room from. A really big
  amount of new code would need a new overlay and free memory to load it, which we have not found yet.
- New ability ids **above 327** need the table moved somewhere bigger. Only one pointer refers to it
  (`0x0223AA9C`), so it is a small change once there is free space; see
  [New ids, not reused ones](#new-ids-not-reused-ones).
- Text: ability names have room for 12 characters (Origin already shortens names, e.g. "PoisnPuppetr").

### Route 3: what reuse can and cannot do

**Copying a behaviour to another id is a pure data change.** Because abilities and moves are found by
id in a table, any ability id can be given the exact behaviour of another ability by copying its table
entry, and any move id can be given another move's special behaviour by adding or changing an entry in
the move list. This is useful for "same as X, new name" abilities and moves.

**Move data is rich.** `extra/new_move_data.narc` has one 40-byte record per move in the Black/White
layout: type (byte 0), category (byte 2: 0 status, 1 physical, 2 special), power (3), accuracy (4),
PP (5), priority (6), number of hits (7: low half = min, high half = max; Double Slap `0x52` = 2-5,
Double Kick `0x22` = 2), status effect and chance (8-11), the Gen 4 effect number (`0x11`), target
(`0x14`), up to three stat changes with amounts and chances (`0x15`-`0x1D`), and flags (`0x20`).
Most ordinary moves need no code at all.

**But nothing here changes with the weather.** Category switching (Shell Side Arm, Photon Geyser),
weather-based power (Weather Ball) and hit-count changes (Skill Link) are each written in code for their
own move or ability. So without new code:

- *Weather Switch* can only be Drizzle or Drought (pick one), or the same as another existing ability.
- *Oily Arsenal* can only be one fixed version, for example Poison, physical, 60 power, 2 hits; or a
  copy of Shell Side Arm (physical or special depending on the target's defences, not the weather).

Both are far from what the designs say, so route 2 is needed for these two.

### Next step: Oily Arsenal

Not built yet. The plan, using the same method as Weather Switch:

- Data: a new record in `extra/new_move_data.narc` (Poison, physical, 60 power, 2-3 hits), the name in
  bank 739 and the description in bank 738, and an existing animation.
- Code: three small handlers, modelled on handlers that already do each part:
  category by weather (Photon Geyser handles event 59), power by weather (Weather Ball handles
  events 59 and 112) and number of hits by weather (Skill Link handles event 183). In drought: physical,
  60, 2 hits; in rain: special, 40, 3 hits. The exact meaning of each event value still has to be read
  from those handlers.
- An entry in the move list (`0x02251C90`) for the new move id. The id itself: a new one (921 or
  higher), see [New ids, not reused ones](#new-ids-not-reused-ones).

### Code our Pokemon need (besides new abilities and moves)

- **1 HP for Wonder Guard (Goatjo).** The dex sets base HP 1 for every Pokemon with Wonder Guard
  (`scripts/dex_rules.py`), but base HP 1 alone is not enough: the game gives "always 1 HP" only to Shedinja, by
  its species number, in the function that works out a Pokemon's stats (in the decomp: `CalcMonLevelAndStats`,
  `if (species == SPECIES_SHEDINJA) maxHp = 1`). Without a patch Goatjo would have about 60 HP at level 50. The
  patch: give max HP 1 to every species whose base HP is 1 (only Shedinja and ours have that).
- **Form-change abilities.** The game changes form only for the original Pokemon: Disguise (Mimikyu), Shields
  Down (Minior), Battle Bond (Greninja). Ours keep these abilities (Arvind, 2026-11-12): Phantomb and Phantail
  (Disguise), Aluminimonk and its evolution (Shields Down), Chillalit (Battle Bond). Each needs its battle form in
  the dex (Forms, with pictures) and the species checks extended to our species. `dex_rules.py check` warns until
  the form is in the dex.

### Names and descriptions (text)

All in the text archive `a/0/2/7`, encoded with hg-engine's `tools/msgenc -e -k 0` and `charmap.txt`
(as in the Bugmight spike):

| Bank | Content | Lines |
|---|---|---|
| 711 | Ability names (12 characters max) | 327 (ids 0-326; 327 has no name) |
| 712 | Ability descriptions (two lines, `\n` between) | 328 |
| 739 | Move names | 921 (ids 0-920) |
| 738 | Move descriptions | 921 |

The ability banner in battle takes its text from bank 711 (checked: it showed "WeatherSwtch").

### New ids, not reused ones

The goal is **brand-new** abilities, moves and evolutions with their own ids, not ones that take over
an existing id. The Weather Switch test borrowed Zero to Hero's id and code space only as a shortcut.

The limits found so far are not real limits, just the sizes Origin happened to be built with:

- **Abilities:** the handler table has 328 slots (ids 0-327) because that is how many abilities Origin
  has. Nothing after it is reserved; the next bytes are other data. Ability ids are stored as 16-bit
  numbers in species and trainer data, so ids up to the thousands fit. A bigger table can be put
  anywhere and the engine pointed at it by changing the one pointer at `0x0223AA9C`. Names and
  descriptions are just more lines in banks 711 and 712.
- **Moves:** ids 0-920 are taken because Origin has 921 moves. `extra/new_move_data.narc` and the text
  banks can take more entries, and the move handler list (count in one literal) can be moved and made
  longer the same way. Not yet known: whether other code or tables are sized for exactly 921 moves
  (animations, learnset or TM code, the move menu). That needs testing with a move id 921 or higher.
- **Evolutions:** new evolutions with existing methods (level, item, trade...) are only data. A
  brand-new evolution method needs code in the evolution check, which lives outside the battle engine
  and has not been looked at yet.

What blocks all of this is **memory for our code and the bigger tables**: overlay 14 has no free space,
and the memory around it is used by other overlays during battle. The candidate is a region near the
top of RAM (`0x023C111A`-`0x023E0000`, about 126 KB) that was all zeros during the test battle. If it is
free everywhere in the game, our own overlay can be loaded there (the way hg-engine does it in
stock HeartGold), holding the new handlers, the bigger ability table and the longer move list. Checking
that region is the next step.

**Solved for code that lives all the time (2026-11-16):** the English patch's rc8 builds already load
resident code there the clean way: a new ARM9 autoload section (the boot code copies it into place) plus a
lower main-arena end, so the heap never hands that memory out. rc8 with the advanced trainer AI has two such
sections (`0x023DC000` difficulty layer, `0x023D4000` the AI) and the arena ends at `0x023D4000`; about 77 KB
of the arena's tail is still unused by the root heaps. Our nuzlocke test uses the same method at
`0x023D2000`-`0x023D4000` and works in battle and in the field (`scripts/origin_custom/nuzlocke/README.md`).
New abilities and moves can use the same region instead of Zero to Hero's code space.

### Nuzlocke test (2026-11-16)

First encounter per area (a Poke Ball is refused in the battle Bag in an area already used) and a graveyard box
(fainted Pokemon move to box 24 "GRAVES" after the battle, with grey icons), no revives, and Hardcore Nuzlocke
(CAP, ITEMS DEFAULT and SET forced before every battle, no Bag items in battle except Balls, no Rare Candy at or
above the cap). Written in C against Origin's own functions and tested in the emulator, including save and reload. Details, patched places and what is still missing:
`scripts/origin_custom/nuzlocke/README.md`.

### Where things are

| Thing | Location |
|---|---|
| Our code and the test build script | `scripts/origin_custom/` (this repo) |
| Test ROMs | `~/sigma-origin/ws_weather_switch.nds` (Drizzle lead), `ws_weather_switch_drought.nds`, `ws_weather_switch_none.nds` |
| Working copy used by the build | `~/sigma-origin/x_ws/` (copy of the clean `x_spike_backup/`) |
| Screenshots of the test | `~/sigma-origin/poc_weather_switch.png` |
| Nuzlocke test ROM, screens, emulator runs | `~/sigma-origin/rc8/nuzlocke_test.nds`, `~/sigma-origin/nuzlocke_test_v1.png`, `~/sigma-origin/nuzlocke_run/` |

---

## Origin HeartGold on the C decompilation: feasibility study (2026-11-11)
*(was `docs/ORIGIN_ON_DECOMP.md`)*

(V) = verified fact with evidence. (I) = my assessment. Nothing was built or run; no MWCC compiler or Nitro SDK is available here, so "builds byte-for-byte" is NOT independently verified.

Clones (shallow, read-only) used: `scratchpad/dec/cc` (ctrl-cheeb-del/pokeheartgold, master @ cb614ad, 2026-11-06), `scratchpad/dec/pc` (elyro1/pokeheartgold_pc-port, pc-port-main @ 84ecdba, 2026-11-04), `scratchpad/pokeheartgold` (pret original, for comparison), `scratchpad/origin-en` (EN translation repo, reused). Helper scripts: `scratchpad/ovmatch.py`, `scratchpad/ovmatch2.py`.

### 1. Is the ctrl-cheeb-del decomp really complete C and matching? Does it build JP?

(V) README: "Fully decompiled: everything's C/C++ and both ROMs build byte-for-byte. Built with LLM agents." Fork of pret/pokeheartgold (5,935 commits in history, same contributors list as pret); explicitly "not affiliated with pret", pret does not accept AI code. No licence file (GitHub licenseInfo = null; pret has none either).
(V) Size now vs pret: src has 1,012 `.c` + 56 `.cpp` files, 633,941 lines of C in `src/` (745,157 lines C incl. `lib/`). pret original (local clone): 414 `.c`, 216,877 lines, plus 281 `.s` files / 1.22 M lines of asm. Remaining assembly in ctrl-cheeb-del: 89 `.s` files, nearly all `*_data.s` tables (and 52 files with some asm hint).
(V) `docs/progress/progress.json` (generated by `tools/progress/progress.py`, based on the linker map): of 4,075,354 mapped code bytes, C 3,988,736 (97.87 %), C++ 56,228 (1.38 %), combined 99.25 %; original hand-written asm 26,078 B (0.64 %), inline asm 1,536 B, SDK-generated 2,264 B, veneers 512 B. Metric is by linker-map symbol, so it counts real compiled C. `tracked_worktree_dirty: true` in that JSON. Zero `NONMATCHING` markers, zero `asm(` statements found in src.
(V) Code quality sample: readable, named structs and functions (battle_main.c etc.). `sub_0xxxxxxx` style names: 0 left in src (pret original: 1,343 distinct).
(V) ROM hashes in repo: `heartgold.us/rom.sha1` etc. = 4fcded0e... (HG) and f8dc38ea... (SS). Build = MWCC 2.0/sp2p2 (via Wine on macOS/Linux) + Nitro SDK, both user-supplied (INSTALL.md). `docs/DECOMP-NOTES.md` is a per-batch log saying both ROMs passed SHA-1 after each batch.
(V) JP: `main.lsf` has 129 overlays, only `heartgold.us/` and `soulsilver.us/` dirs exist, ROM_SPECS in the port only accept IPKE/IPGE. No IPKJ, no `.jp` config anywhere. pret never had JP for HGSS either.
(I) The claim looks credible (progress file + sha1 files + 1,000+ real C files + clean names), but I have not compiled it. Treat "byte-for-byte" as the author's claim until someone builds it; for our purpose (PC build with gcc) matching does not even matter, only that the C is semantically right. Caveat: LLM-written C for 3 MB of former asm can contain semantic slips that matching does not catch only where the compiler output happens to coincide, which is rare; matching is strong evidence of correctness.

#### The PC port (elyro1)
(V) Native 64-bit Linux/Windows port, "experimental" (README warning, 1 star, last push 2026-11-04). Built on that decomp plus libntr (github.com/elyro1/libntr fork of cybervisi0n/libntr, MIT: "drop-in replacement for NitroSDK that targets Nintendo DS, PC"). No MWCC/Wine/Nitro SDK needed. Features: HG+SS, 60 fps, keyboard/controller/mouse touch, autosave backups. Build: `make -f Makefile.pc linux`, needs SDL2, meson, GCC 13+, OpenGL 4.2.
(V) Structure: port = the decomp `src/` compiled with `SDK_PORT` defined. `diff cc/src pc/src`: 336 files differ, ~13.8k changed lines (e.g. heap sizes raised because 64-bit pointers enlarge structs, typed C definitions replacing pointer-laden asm tables, GameSpy/WFC code replaced by libntrdwc). Plus `pc/` dir: ~3.4k lines of glue C (overlay loading is a bookkeeping no-op: "Game and overlay functions are linked into the executable", `pc/support/overlays.c`), JSON manifests of fixed data (317 KB), Python tools. Autosave etc. are added.
(V) Assets: `tools/assets.py` requires an unmodified US rev 0 ROM (gamecode IPKE/IPGE, SHA-1 compared), then libntr's extractor (`SIM_NDSExtract`) unpacks the whole NitroFS into `run/` as ordinary files; the game reads NARCs from those files. Code and arm9/overlay tables are compiled from source (not read from the ROM at run time). INSTALL.md: "Other regions, revisions, and patched ROMs fail validation." Nothing about ROM hacks, mods or other regions. The validation is a Python check that is trivial to bypass, but the code behind it is US-vanilla-specific.

### 2. How Origin differs from its base

Local data: Origin = `~/sigma-origin/x_spike_backup` (v4.0.3 + EN rc3, gamecode IPKJ); vanilla = `x_vanilla` (US, IPKE). A direct diff mixes region and Origin changes, so I compared by content similarity.

(V) Header/arm9: Origin arm9.bin 1,115,808 B uncompressed (BSS end 0x021FF720...: 4,544 B less than US); US arm9.bin 1,120,352 B. Same base 0x02000000, same entry point/autoload callback addresses. No hg-engine style extra arm9 injection area visible in size. `docs/GAME_TECH.md` ("New abilities and moves in Origin HeartGold"): no synthetic overlay 129+ (hg-engine has 152 overlays; Origin has 120).
(V) Overlays: Origin 120 overlays (11 of them 32-byte dummies), all uncompressed, renumbered vs US 129. Method: matched every Origin overlay to the US overlay with most shared 8-halfword shingles after masking RAM pointers and BL/B offsets (so address shifts between regions/layouts do not count). Result (`scratchpad/ovmatch2.py`):
- 100 overlays (2.52 MB) have a clear US counterpart; 54 of them (1.05 MB) match >= 90 %, several match 100 % (e.g. Origin 22, 23, 27), which also shows JP code is essentially identical to US code outside pointers.
- Origin overlays with essentially no resemblance to any US overlay (<= 0.10): ov14 337,216 B (@0x022007E0, the Gen 5 style battle engine), ov11 73,824 B, ov74 22,272 B, ov12 6,112 B, ov105 5,120 B, ov114 4,896 B, ov58 2,072 B (the last is the EN patch's outfit chooser). Total 451,512 B (~441 KB) brand-new or fully replaced code.
- US overlays with no Origin counterpart (total ~791 KB): battle (OVY_12, 226 KB), trainer AI (OVY_10, 62.5 KB), link battle screen (OVY_5, 14 KB) = 303 KB replaced by the new engine; WiFi Club (44), WiFi Plaza (45-49, 88-93 incl. plaza games), union chat log (34), 122/123 ~ 488 KB removed (Nintendo WFC is dead). The overlay-89 (footprint stamp) mapping is the least certain.
- Partly rewritten matched overlays (similarity < 0.7): Origin 5 (96,192 B vs US 91,488), 28 (20,736 vs 13,728), 49 (14,912 vs 12,192), 72 (21,632 vs 12,928), 19 (9,344 vs 9,248): ~165 KB. Net growth of matched overlays +42 KB (e.g. Origin ov2 +9 KB, ov1 +5 KB; script commands such as opcode 357 CountAliveMons come from there).
- Upper bound on non-matching bytes inside the 100 matched overlays: ~311 KB (sum of size x (1 - similarity)); this is inflated by region differences and unmasked literal data, so realistic changed ARM code there is 100-300 KB.
(V) arm9: whole-file masked similarity to US 86 %; first 0xA0000 bytes 77-95 %, 0xA0000-0xE0000 99-100 % (identical), tail 0xE0000+ (data tables, 75-78 %). Not separable without a JP dump.
(V) Where injected code lives: Origin did not add an overlay; the engine is ov14 itself plus the 100+ renumbered ones. Everything in battle runs from ov14 (abilities, moves, messages, EXP, AI): addresses in `origin-en/work/notes/*.md` (ability table 0x0224FF2C, 328 entries; move list 0x02251C90, 411 pairs; EXP routine 0x022289EA etc.). EN patch changes are small armips patches (a few overlays, tens of bytes each).
(V) hg-engine relationship: Origin is "built on hg-engine" per its README, but `docs/GAME_TECH.md` ("New abilities and moves in Origin HeartGold") records that searching Origin for hg-engine's compiled battle functions found almost none; engine is a Black/White event-handler engine; ability ids 0-310 and move ids <= 467 equal hg-engine's, move ids from 468 are hg-engine minus 3. EN notes state the pret decomp "cannot build it".
(V) Data side: NitroFS 431 files vs 384 (+47 new NARCs: battle_graphics, battle_string, pokedex, pokeicon, pokemon_overworld_info, pokepic_f/m, egg_moves, namein, rep_scr_seq, clothes...), 266 files byte-identical to US, 117 differ (a/0/0/2 species 26,468 -> 86,512 B with 52-byte records, a/0/5/6 parties 28-byte records, a/0/3/x learnsets/evos, a/0/6/5 matrices 23.8 -> 19.5 MB, graphics NARCs). NitroFS total 263 MB vs 118 MB.

What can be measured with only the US dump: the above (code replaced/new/removed, function-level fraction unchanged). What it cannot do: tell which of the remaining 5-15 % deltas inside "matched" overlays are region differences (text-engine, font handling, kana/kanji, Japanese-specific tables) and which are Origin's edits. (I) A legal JP vanilla dump (IPKJ rev matching Origin's base) is required to do the second step properly: with it, the delta of Origin vs JP is exactly Origin's work. Arvind only has the US dump. (Note: the EN xdelta is distributed against the US ROM, but the Chinese original needs a JP ROM.)

### 3. Data vs code

Data that can mostly be imported as files into a decomp/port build (NitroFS contents): maps and matrices, script archives (event scripts), text banks, graphics (pokepic/pokeicon/followers/battle graphics/trainer pics), encounters, trainers (a/0/5/5, parties a/0/5/6), species/evolutions/learnsets, move data (`extra/new_move_data.narc`, 40 B BW layout), battle strings. About 260 MB of the 263 MB.
BUT (I): "as files" is only true if the code reading them agrees on the format. Vanilla decomp BaseStats is 32 bytes (`include/pokemon_types_def.h`) with u8 abilities and MAX_SPECIES = 493. Origin: 52-byte species, u16 abilities, 1,099 species plus forms, 28-byte trainer parties, BW move layout, 3-slot and form handling, new script commands, new Pokedex/icon/sprite lookup, 64-bit port structs. Every reader of those tables in the decomp (party, summary, box, dex, evolution, learnset, script, trainer, field follower, save) would need modification, i.e. real C work, even though the data itself is just files. Save format compatibility is a further unknown (1,099 species in a Gen 4 mon struct).
Code that must exist as C: battle engine ov14 (+ov11, ov12, ov74, ov105, ov114 etc., ~440 KB), plus modified code (field/script/overlays 1, 2, 5, 19, 28, 49, 72, arm9 changes, EN patch fixes, no-WFC build).
hg-engine as a shortcut: (V) hg-engine src is C, 46,503 lines in 66 files (battle 17.6 k, individual/species data 17.1 k, field 3.8 k) plus 2.9 k lines asm; it patches the original Gen 4 engine by address hooks. (I) It is NOT a shortcut for lifting Origin's engine: Origin's ov14 is a different architecture (BW event-handler tables), its numbering/tables differ (moves -3, 52-byte species, ability ids 311+ differ), and no hg-engine commit lines up. It IS a useful source of ideas/code for Plan B below (rebuild Gen 5+/hg-engine features on the Gen 4 decomp engine), because hg-engine is plain C against pret-style headers. I found no public Black/White decomp to borrow from (GitHub search returned nothing).

### 4. Plan, estimate, risks

Assumption: Arvind/agents do the work with LLM agents; no Origin source; no contact with Origin authors (his decision). Effort in calendar time for one person directing agents; wide error bars.

Plan A: faithful Origin on decomp + PC port
1. Setup and mapping (1-2 weeks): build the vanilla US port from source on a Linux box (Legion) to confirm the decomp builds and runs on his own dump; obtain a JP vanilla dump (Arvind must supply, legally his own); write a tool that maps decomp functions onto Origin (masked byte signatures, like `ovmatch2.py` but per function) -> every function labelled unchanged / modified / new. Output: exact amount of work.
2. Data layer (1-3 months): make the decomp+port read Origin's NitroFS: widen species/move/trainer structs, 1,099-species indexes, 52-byte BaseStats, 28-byte party, BW move records, new NARC lookups, new script commands, remove WFC. Goal: Origin overworld/menus boot in the port without battles.
3. Battle engine (the big one, 2-6+ months): decompile ov14 (337 KB) + ov11 (74 KB) + small ones to C. No byte-matching oracle exists for Origin (no compiler needed since PC build), so correctness comes from differential testing against the Origin ROM in an emulator (py-desmume harness exists) per ability/move/event. ~80 k lines of C-equivalent (decomp ratio: 4.07 MB code ~ 745 k lines). The US decomp itself went from pret's 414 to 1,012 .c files in weeks with agents *because a byte-exact compiler oracle existed*; that oracle is absent here, so expect slower, riskier work.
4. Modified overlays/arm9, EN-patch fixes, graphics/UI differences (1-2 months).
5. Verification and polish: savestate-based playthrough diffs, save compat (1+ month).
Total (I): roughly 6-12 months of agent-assisted work for "Origin-equivalent, running in the PC port"; the lower half only if the battle engine goes well.

Plan B: Sigma game on the vanilla decomp (not Origin)
(I) Take the verified US decomp + PC port (it already runs vanilla HGSS), add the dex expansion/Gen 5+ mechanics/abilities by porting hg-engine C into the decomp, and import our own data. Does not give Origin's maps/story/new battle engine exactly, but all code is in C we own and the PC target is real. Rough estimate 3-6 months; less risk than A but a different product ("hg-engine on PC", not Origin).

Plan C (baseline, not decomp): embed a DS emulator core in a PC app for the Origin ROM we already have patched. Days to weeks; no native rendering/widescreen/modding gain.

Main risks
- Battle engine has no oracle and no source (A, step 3). Biggest schedule risk.
- JP baseline missing: we cannot cleanly list what Origin changed until a JP dump is in hand.
- The port is experimental, 1 star, one maintainer; 64-bit pointer issues (13.8 k lines of SDK_PORT patches) apply again to everything new; the decomp is a young LLM-built fork outside pret, may be force-pushed/rewritten.
- Struct/save changes (1,099 species in Gen 4 structures) can ripple through the whole code base.
- Legal/ethics: decomp has no licence; Origin is someone else's unreleased-source binary hack: a C reconstruction is a derivative work, so keep it private/local (consistent with the notes that sharing needs authors' permission). Nothing from ROMs may be committed to our repo.
- LLM-written C needs semantic verification where the compiler cannot confirm (new Origin code).

### Verdict on Arvind's question ("er det virkelig det?")

(I) Partly true. True: a complete C decomp of vanilla HG/SS plus a native PC port now exist (documented claims; progress.json and file counts support them), so a PC game on vanilla decomp is real and much closer than before. Not true: it does not make Origin itself cheap. Origin is the JP game with ~11 % of code newly written (440 KB, almost all the battle engine, with a different architecture from the decomp's and from hg-engine), plus 100-300 KB of edits in other overlays, plus 52-byte/1,099-species data formats that the decomp code does not understand. The decomp removes the need to decompile the ~85-89 % that is unchanged, which would otherwise be the impossible part; the remaining work is months, not weeks, with the battle engine as the dominant risk. Cheaper realistic options: Plan B (Sigma on vanilla decomp with hg-engine features) or keep patching the Origin ROM binary and run it in an emulator.

---

## The game we build on
*(was `docs/ENGINE.md`)*

**Update (2026-10):** the main target is now Origin HeartGold (Nintendo DS, built on hg-engine), where our
Pokemon take existing species slots (see [Replacing the whole dex: where real Pokémon still show](#replacing-the-whole-dex-where-real-pokémon-still-show)). This page describes
the earlier GBA target, pokeemerald-expansion. Its export and tests are still in the repository, but it is no longer the focus.

### The base: pokeemerald-expansion

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

### New moves and abilities

Anything not in that list is ours to program. In expansion a move is one block of data in
`src/data/moves_info.h` plus, for a new *effect*, battle-script code; an ability is an entry
in `src/data/abilities.h` plus code where it triggers. Each one can get an automated test.
To be programmable, a new move or ability needs an exact description: name, type,
physical/special/status, power, accuracy, PP, target, and what precisely happens.

### Native PC program or GBA ROM?

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

### How a Pokemon is stored

In expansion every Pokemon is one block in `src/data/pokemon/species_info/`, holding base
stats, types, catch rate, exp and EV yield, items, gender ratio, egg data, three abilities,
name, category, height, weight, dex text, body color, sprites and their positions, and
links to its level-up, teachable and egg move lists and its evolutions. Our species files
contain all of that except the art.

`scripts/export_expansion.py` writes every Pokemon that is far enough along as game code
into `export/expansion/`, and `scripts/apply_to_expansion.py` puts it into the game's source.
[Building the game (GBA target)](#building-the-game-gba-target) has the steps.

### Proof of concept (2026-10-02)

**On pokeemerald-expansion (the real base):** expansion 1.17.1 was built on macOS. Leafing
(draft values) was exported and added as a **new** species, next to the existing ones.
The game compiled, and its automated test system confirmed both generated checks:

- "Leafing has the data from its species file" - stats, type, ability, first move and name
  in the running game match the species file.
- "Leafing can use its first move in battle" - a real battle against a Wobbuffet in which
  Leafing uses Tackle.

Sprites and cry are the game's question-mark placeholders until we have art.

**New move and new ability:** one example of each was programmed and tested the same way -
a move that is pure data (Sigma Strike) and an ability that needs new code (Sigma Aura).
All four of their tests passed. They live in [`game/examples/`](../game/examples) as a
reference for the real ones; [`game/README.md`](../game/README.md) describes the routine.

**Earlier, on plain Emerald:** the same Leafing was put into `fuddlesworth/pokeemerald-native`
(the native macOS port) in Treecko's slot and played through the first battle. That showed
the native port works on this machine, which matters if we port expansion to it later.

### Tools the community uses

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

### Sharing the game legally

- Hacks are shared as a **patch** (BPS/UPS/xdelta) that players apply to their own ROM (Emerald
  for the GBA plan; HeartGold, plus Origin's own patches, for Origin HeartGold). The patch
  contains only the differences, not Nintendo's game.
- A finished game on a flashcart as a gift is a copied patched ROM: a grey area, so only a few
  copies, never sold and never published. See [Physical copies (cartridges) - under consideration](PLANS.md#physical-copies-cartridges---under-consideration).
- A native PC program contains the game's graphics and sound, so it cannot simply be handed
  out. The Vita port solves this by shipping without assets and reading them from the
  player's own ROM at startup.
- Expansion asks hacks to credit RHH (the team behind it).
- This repository holds only our own work. The game's source code stays out of it.

---

## Building the game (GBA target)
*(was `docs/BUILDING.md`)*

This page is about the earlier GBA target. The main target is now Origin HeartGold (Nintendo DS);
see [Replacing the whole dex: where real Pokémon still show](#replacing-the-whole-dex-where-real-pokémon-still-show). Nothing here is needed for it.

The GBA game is [pokeemerald-expansion](https://github.com/rh-hideout/pokeemerald-expansion)
plus our Pokemon. Its source contains Nintendo's game data, so it lives in its own folder
outside this repository and is never uploaded here.

### One-time setup on macOS (Apple Silicon)

This is the setup that was built and tested on 2026-10-02. It needs no administrator
password. (The official route, devkitARM, works too but its installer asks for one.)

1. Tools from Homebrew:

   ```bash
   brew install make pkg-config libpng coreutils arm-none-eabi-gcc
   ```

2. Homebrew's ARM compiler comes without a C library, so build one (newlib) from source,
   compiled for the GBA's processor:

   ```bash
   mkdir -p ~/sigma-toolchain/src && cd ~/sigma-toolchain/src
   git clone --depth 1 https://sourceware.org/git/newlib-cygwin.git newlib
   mkdir build && cd build
   ../newlib/configure --target=arm-none-eabi --prefix=$HOME/sigma-toolchain \
     --disable-multilib --disable-nls --disable-newlib-supplied-syscalls MAKEINFO=true \
     CFLAGS_FOR_TARGET="-mthumb -mthumb-interwork -march=armv4t -mtune=arm7tdmi -O2 -ffunction-sections -fdata-sections"
   gmake -j8 MAKEINFO=true && gmake install MAKEINFO=true
   ```

3. Get the game's source, in a folder whose path has no spaces:

   ```bash
   git clone --depth 1 --branch expansion/1.17.1 https://github.com/rh-hideout/pokeemerald-expansion.git ~/sigma-expansion
   ```

### Building

From the game's folder (`~/sigma-expansion`):

```bash
gmake tools -j8
```

```bash
LIBGCC=$(dirname "$(arm-none-eabi-gcc -mthumb -print-file-name=libgcc.a)")
CPATH=$HOME/sigma-toolchain/arm-none-eabi/include gmake -j8 \
  LIBPATH="-L \"$LIBGCC\" -L \"$HOME/sigma-toolchain/arm-none-eabi/lib\""
```

The first command builds the helper programs (it must run without `CPATH`). The second
builds `pokeemerald.gba`, which runs in any GBA emulator, for example mGBA.

### Putting our Pokemon into the game

From this repository:

```bash
python scripts/apply_to_expansion.py ~/sigma-expansion
```

That copies the Pokemon in `export/expansion/` (with their sprites, where they have any),
sets the starters named in `data/config.yaml`, and copies the hand-written moves, abilities and
tests in [`game/`](../game/README.md) into the game's source and hooks them in. Run it again whenever the dex has changed, then
build again. Which Pokemon are included, and what each of the others still needs, is listed
in [`export/expansion/NOT_READY.md`](../export/expansion/NOT_READY.md).

### Checking that they work

The game has an automated test system that plays battles without a screen. The export
writes two checks per Pokemon - that its data in the game matches its species file, and that
it can use its first move in a battle. Run them with the same settings as a build:

```bash
gmake check-tools
CPATH=$HOME/sigma-toolchain/arm-none-eabi/include gmake check -j8 TESTS="Sigma" \
  LIBPATH="-L \"$LIBGCC\" -L \"$HOME/sigma-toolchain/arm-none-eabi/lib\""
```

`gmake check-tools` is only needed the first time. New moves and abilities have their own
tests in the same system; see [`game/README.md`](../game/README.md).

### Screenshots straight from the ROM

`tools/gbashot/gbashot.c` runs the ROM without a window, presses buttons from a script and
saves screenshots. It needs the mGBA library, built once from source (no administrator
password; `brew install cmake` first):

```bash
git clone --depth 1 --branch 0.10.5 https://github.com/mgba-emu/mgba.git ~/sigma-toolchain/src/mgba
cd ~/sigma-toolchain/src/mgba && mkdir build && cd build
cmake .. -DBUILD_QT=OFF -DBUILD_SDL=OFF -DBUILD_SHARED=OFF -DBUILD_STATIC=ON -DUSE_FFMPEG=OFF -DUSE_LUA=OFF \
  -DUSE_SQLITE3=OFF -DUSE_ELF=OFF -DUSE_EPOXY=OFF -DUSE_LIBZIP=OFF -DUSE_MINIZIP=OFF -DUSE_EDITLINE=OFF \
  -DUSE_GDB_STUB=OFF -DUSE_DISCORD_RPC=OFF -DM_CORE_GB=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build . -j8
M=~/sigma-toolchain/src/mgba
cc -O2 -o gbashot tools/gbashot/gbashot.c -I $M/include -I $M/build/include $M/build/libmgba.a -lz -L/opt/homebrew/lib -lpng -lm -framework Foundation
```

To see the starters without playing through the story, apply `game/test-patches/starter_test.patch`
to the game (`git apply`), build, and "New Game" jumps straight to Professor Birch's bag and the
first battle. Take the patch out again (`git apply -R`) before building the real game. The
pictures in [Sprites](ART.md#sprites) were made this way.
