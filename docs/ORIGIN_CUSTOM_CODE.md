# New abilities and moves in Origin HeartGold

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

## What Origin really is

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

## How abilities work in Origin

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

## Route 2 in practice: the Weather Switch test

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

## Route 3: what reuse can and cannot do

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

## Next step: Oily Arsenal

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

## Names and descriptions (text)

All in the text archive `a/0/2/7`, encoded with hg-engine's `tools/msgenc -e -k 0` and `charmap.txt`
(as in the Bugmight spike):

| Bank | Content | Lines |
|---|---|---|
| 711 | Ability names (12 characters max) | 327 (ids 0-326; 327 has no name) |
| 712 | Ability descriptions (two lines, `\n` between) | 328 |
| 739 | Move names | 921 (ids 0-920) |
| 738 | Move descriptions | 921 |

The ability banner in battle takes its text from bank 711 (checked: it showed "WeatherSwtch").

## New ids, not reused ones

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

## Where things are

| Thing | Location |
|---|---|
| Our code and the test build script | `scripts/origin_custom/` (this repo) |
| Test ROMs | `~/sigma-origin/ws_weather_switch.nds` (Drizzle lead), `ws_weather_switch_drought.nds`, `ws_weather_switch_none.nds` |
| Working copy used by the build | `~/sigma-origin/x_ws/` (copy of the clean `x_spike_backup/`) |
| Screenshots of the test | `~/sigma-origin/poc_weather_switch.png` |
