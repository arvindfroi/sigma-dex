# The dex data: fields, how they get filled, and where they came from

Everything about the species files in `data/species/`: what each field means, the ways people and Claude fill them (website, Google Sheet, Claude fill, number fill, moveset autocomplete), what the dex still lacks, the Discord export it started from, and the backups.

Contents:
- [Field guide](#field-guide)
- [Editing the dex on the website](#editing-the-dex-on-the-website)
- [Filling in the dex with the Google Sheet](#filling-in-the-dex-with-the-google-sheet)
- [Letting Claude fill in a Pokemon](#letting-claude-fill-in-a-pokemon)
- [The numbers: height, weight, body color, EV yield, catch rate, exp, growth, friendship, gender, egg groups, egg cycles](#the-numbers-height-weight-body-color-ev-yield-catch-rate-exp-growth-friendship-gender-egg-groups-egg-cycles)
- [Movesets: how the autocomplete decides](#movesets-how-the-autocomplete-decides)
- [Dex analysis: what Sigma Dex is missing (2026-10-08)](#dex-analysis-what-sigma-dex-is-missing-2026-10-08)
- [Getting everything out of the Discord channel](#getting-everything-out-of-the-discord-channel)
- [What came out of the Discord channel](#what-came-out-of-the-discord-channel)
- [Backup](#backup)


---

## Field guide
*(was `docs/FIELDS.md`)*

Every species file in `data/species/` has these fields. Leave a field empty if it is not
decided yet - [TODO.md](../TODO.md) keeps track of what is missing.

### Identity

| Field | Meaning | Rules |
|---|---|---|
| `dex` | Slot in our regional dex | 1 to dex_size in data/config.yaml (254), unique |
| `name` | Name | Max 10 characters in the game (a new Pokemon cannot get a longer name on the website; older ones get a warning) |
| `credits.designer`, `credits.artist` | Who made it | Discord names |
| `types` | One or two types | `[Grass]` or `[Grass, Steel]` |

### Pokedex page

| Field | Meaning | Rules |
|---|---|---|
| `category` | The "Seed" in "Seed Pokemon" | Max 12 characters |
| `description` | Dex entry | Max 4 lines of about 40 characters |
| `height_m`, `weight_kg` | Size | One decimal, e.g. `0.7` and `6.9` |
| `body_color` | Color used by the dex search | red, blue, yellow, green, black, brown, purple, gray, white, pink |

### Battle data

| Field | Meaning | Rules and guidance |
|---|---|---|
| `abilities.primary` / `secondary` | Abilities | Use abilities that already exist in the game where possible |
| `abilities.hidden` | Hidden ability | Optional |

**Fixed rules** (`scripts/dex_rules.py`, applied on every sync): a Pokemon with **Wonder Guard** always has base HP 1, like Shedinja (the website locks the HP box). Abilities that do not fit (Disguise or Shields Down without a form, Moody, Shadow Tag, Wonder Guard with few weaknesses) show as warnings: `python scripts/dex_rules.py check`.

**Legendary or not**: `data/legendaries.yaml` lists our legendaries, mythicals, trios and the undecided ones. The tools that fill in numbers and moves follow it.

| Field | Meaning | Rules and guidance |
|---|---|---|
| `base_stats` | HP, Attack, Defense, Sp. Attack, Sp. Defense, Speed | Each 1-255. Typical totals: first stage 300-320, middle 400-420, fully evolved 480-540, legendary 580-680 |
| `ev_yield` | EVs given when defeated | `{attack: 1}`. 1 point for a first stage, 2 for a middle stage, 3 for a final stage |
| `catch_rate` | How easy it is to catch | 3 legendary, 45 starters and rare, 120-190 uncommon, 255 very common |
| `base_exp` | Exp given when defeated | About 50-70 first stage, 130-150 middle, 200-240 final |
| `growth_rate` | How fast it levels | erratic, fast, medium_fast, medium_slow, slow, fluctuating. Starters use medium_slow |
| `base_friendship` | Starting friendship | 70 is standard, 35 for unfriendly ones |

### Breeding

| Field | Meaning | Rules |
|---|---|---|
| `gender` | Percent male | 0, 12.5, 25, 50, 75, 87.5, 100 or `genderless`. Starters use 87.5 |
| `egg_groups` | One or two | monster, water_1, water_2, water_3, bug, flying, field, fairy, grass, human_like, mineral, amorphous, dragon, ditto, undiscovered |
| `egg_cycles` | Hatch time | 20 is typical, 40 for rare, 120 for legendary |
| `held_items.common` / `rare` | Items wild ones hold | Optional. 50% and 5% chance |

### Evolution

`evolutions` lists what this Pokemon evolves **into** (the evolved form's file lists nothing
about where it came from). Up to 5.

```yaml
evolutions:
  - into: leafsteel      # file name of the target, without .yaml
    method: level
    level: 16
```

| `method` | Needs | Meaning |
|---|---|---|
| `level` | `level` | Reaches the level |
| `item` | `item` | Item used on it, e.g. `Thunder Stone` |
| `trade` | | Traded |
| `trade_item` | `item` | Traded while holding the item |
| `friendship`, `friendship_day`, `friendship_night` | | Levels up with high friendship (any time / day / night) |
| `level_attack_higher`, `level_attack_equal`, `level_defense_higher` | `level` | Like Tyrogue |
| `beauty` | `level` (the beauty value) | Like Feebas |
| `other` | `note` | Anything else - needs new game code, describe it in `note` |

### Forms

`forms` lists other forms of the Pokemon (a winter form, a form it turns into in battle, a regional form). Each form
holds only what differs from the normal form; on the website: Edit > MORE > Forms.

```yaml
forms:
  - name: Steel form           # what the form is called
    changes: battle            # looks = only its pictures | battle = its type, stats or ability too
    how: When it holds a Metal Coat, its leaf turns to steel.   # how and when it changes, in plain words
    types: [Grass, Steel]      # only if different
    abilities: {primary: Sharpness}                          # only if different
    base_stats: {defense: 85, speed: 30}                     # only the stats that differ
    look: Its leaf is grey and shines like metal.            # what it looks like in this form
    notes:                     # anything else
```

Pictures of a form go on the Pokemon's own page (PICTURES), with the form's name in the caption. How a form works in
the game (its own species slot, a form table, or code that switches it) is worked out from `how` when it is exported:
see docs/GAME_TECH.md ("Replacing the whole dex: where real Pokémon still show").

### Moves

```yaml
learnset:
  level_up:
    - {level: 0, move: Slash}          # level 0 = learned at the moment it evolves into this Pokemon
    - {level: 1, move: Tackle}
    - {level: 7, move: Vine Whip}
  tm_hm: [Cut, Solar Beam]
  tutor: [Body Slam]
  egg: [Leech Seed]
```

- A `level_up` move with level 0 is an **evolution move**: the Pokemon learns it when it evolves
  into this form, whatever its level. On the website it has its own list ("Moves learned when
  evolving"); in the Google Sheet write it as `Slash (evo)`.
- `level_up`, `tutor` and `egg` may use any move in the game (generation 1-9). `egg` is only
  needed for the first stage of a line.
- `tm_hm` may only use the game's TMs and HMs (Origin HeartGold's list: `data/engine/origin.yaml`).
- All existing names are listed in [`data/engine/expansion.yaml`](../data/engine/expansion.yaml).
- A move or ability that is not in that list is a **new** one. It gets a warning and has to be
  programmed into the game, so describe exactly what it does.
- Moves are physical or special per move, like in the modern games.

### Location

```yaml
encounters:
  - {location: Route 1, method: grass, levels: 2-4, rate: 20}
```

`method` is free text for now: grass, surf, fishing, cave, gift, trade, static, ...

### Design and assets

| Field | Meaning |
|---|---|
| `design.concept` | What it is, in a sentence or two |
| `design.name_origin` | Where the name comes from |
| `design.notes` | Anything else |
| `design.wishes` | Notes for Claude: how it should play, move ideas (see [Letting Claude fill in a Pokemon](#letting-claude-fill-in-a-pokemon)) |
| `design.claude_fill` | `true` = Claude may fill in what is still empty |
| `design.filled_by_claude` | The fields Claude filled in, so people know what to review |
| `design.claude_sure` | How sure Claude is about each of those fields, 0-100 (docs/DEX_DATA.md ("Letting Claude fill in a Pokemon")) |
| `assets.*` | Paths to files in this repo. See [Sprites](ART.md#sprites) for the exact sizes (DS sprites are in `assets/sprites-ds/`, found by the Pokemon's file name) |
| `engine.*` | Sprite positioning details for the GBA export, only relevant once GBA sprites exist |

---

## Editing the dex on the website
*(was `docs/WEBSITE.md`)*

**https://arvindfroi.github.io/sigma-dex/** - no account, no GitHub, works on a phone.

### How to contribute

The site looks like the DS games: every page has a **top screen** (what you look at) and a
**bottom screen** (what you do). The menu tabs are **POKEDEX**, **REQUESTS**, **SPRITES**,
**PROGRESS** and **MORE**. **AUTO / DAY / NIGHT** at the top follows the device's light or dark
setting, or fixes one (remembered on the device).

1. Write your name at the top of the page once; the site remembers it on your device.
2. Point at a Pokemon in the list: the top screen shows it (sprite or art, types, Pokedex entry).
   Tap it to open its page.
3. A Pokemon's page is two screens. The top screen shows it on a platform (FRONT / BACK / ICON /
   ART when it has them) and a dialog box. The bottom screen has coloured tabs: **INFO**,
   **SKILLS** (abilities, base stats, damage taken), **MOVES**, **ART** (concept art),
   **SPRITES** (the sprite studio, see [The sprite studio](ART.md#the-sprite-studio)) and **MORE**. Pointing at an
   ability (or tapping it) shows what it does in the dialog box.
4. Press **EDIT**. The top screen stays and follows the changes; the bottom screen becomes the
   form with the tabs BASICS, SKILLS, MOVES, POKEDEX and MORE. Base stats have a bar to drag, a
   number to type and arrows for steps of 5, with the total and what it compares to. The box at the
   bottom lists what changed ("Save the changes? ATTACK 65->80") and asks **YES** / **NO**.
5. **+ ADD A POKEMON** (under the list) adds a new one on the first open number; the number can be
   changed in the form. Open slots are listed under the filter "Open slots".

Do not want to work out moves and numbers? In the edit form's BASICS tab, tick **Let Claude fill
in what is missing** and describe how it should play. See [Letting Claude fill in a Pokemon](#letting-claude-fill-in-a-pokemon).

New moves and abilities, the type balance, Lost and found and changing dex numbers are under
**MORE**.

### Progress and requests

**PROGRESS** shows how far the dex has come: designed, playable and sprites, eight badges (goals
for the whole group: first 25, half the dex, the full dex, 50 playable, all playable, 10 sprites,
all have stats, type balance), the types the dex needs most, the Pokemon that miss only one thing
before they are playable, and the open slots. Everything is counted from the dex itself.

**REQUESTS** is a board with four columns: WISHES, THE GAME NEEDS, BEING MADE and DONE. Anyone can
add a wish (+ ADD A REQUEST), move a card along with its arrows, mark it **✓ DONE**, or bin it (🗑, tap twice) when it is not relevant. The cards the team writes
(what the story needs, from [Story roles: which Pokémon Origin HeartGold's story needs, and who from our dex takes them](STORY.md#story-roles-which-pokémon-origin-heartgolds-story-needs-and-who-from-our-dex-takes-them)) are in `data/requests.yaml`; cards
added or moved on the website are rows of kind `request` in `species_edits` (the newest row of a
card wins; a binned card is a row with `deleted`) and stay in the database: `scripts/import_web.py` skips them
(migration `supabase/migrations/2026-10-15_requests.sql`, applied 2026-10-15).

### Pictures

Open a Pokemon. Copy a picture and **paste it anywhere on its page** (Ctrl+V, Cmd+V on a Mac), or
drag it onto the box in the **ART** tab, or choose files there and press **Upload** (a caption is
optional). PNG, JPG, WEBP and GIF work. Big pictures are shrunk automatically. Sprites are made in
the **SPRITES** tab, not uploaded here.

The approved DS sprite (or else the first picture) is shown on the Pokemon's card and at the top of its page. Any image can be
removed again with its **Remove** button. Only upload art made by us.

### The list and the builder (Showdown style)

The front page shows the dex as a list like Pokemon Showdown's teambuilder: icon, number, name,
types, abilities, hidden ability, the six base stats and the total. Click a column heading to sort
by it (again to reverse); search, type and "show" filter it. **Cards** switches to the picture grid
(the choice is remembered on the device).

In **Edit**, every move and ability field works like Showdown's: tap it and a list of every move
(type, category, power, accuracy, PP, effect) or ability (what it does) opens right under it.
Type to filter, tap a column heading to sort, tap a type to show only that type, tap a row (or press
Enter) to pick. New moves and abilities described on the website are in the lists too. A Pokemon's
**Moves** tab shows its moves the same way.

The move and ability details come from Pokemon Showdown's data (MIT licence,
https://github.com/smogon/pokemon-showdown), saved in `data/engine/showdown.json` by
`scripts/fetch_showdown_data.py` (run it again when the game's move list changes).

### Removing a Pokemon

Open the Pokemon, press **Edit**, and open **Remove this Pokemon from the dex** at the bottom. Type
its name to confirm and press the button. Its pictures are moved to **Lost and found** first (so
they can be given to another Pokemon), then the removal is saved. Within about 15 minutes the
import (`scripts/import_web.py`, `delete_species`) deletes its species file and sprite folders and
drops evolutions of other Pokemon into it. A starter (`starters` in `data/config.yaml`) cannot be
removed; the import reports it at the top of the front page. Nothing is truly gone: the file is
in git history and the removal is a row in `species_edits` (data `{"deleted": true}`), so it can
be restored. Its number becomes an open slot.

### Lost and found, and pictures on the wrong Pokemon

**More > Lost and found** holds Discord pictures that nobody has linked to a Pokemon yet - mostly
because no name was written on the picture or in its message (102 were put there on 2026-10-07
from the Discord export; 34 pictures not suitable for a public site and one meme were left out).
Each one says who posted it, when, any name written on it, and a guess where there was one.

- Recognise one? Press **This is...**, choose the Pokemon, press **Move**. If it is a Pokemon that
  is not in the dex yet, add it first (**+ Add a Pokemon**).
- Not a design at all? **Not a design - remove**.
- A picture on the wrong Pokemon: open that Pokemon's **Pictures** tab, press **Wrong Pokemon?
  Move** under the picture and choose the right one - or "Lost and found" if you are not sure.

Every move is logged in the database table `species_image_moves` (picture, from, to, who, when),
so a wrong move can be undone by moving it back. The import (`scripts/import_images.py`) moves the
repository's copy along; pictures in lost and found live only in the database (species id
`lost-and-found`) until someone places them.

### New moves and abilities

Moves and abilities that exist in the Pokemon games (846 moves, 319 abilities, up to
generation 9) can simply be picked. Anything else is **new** and has to be programmed into
the game, so it needs an exact description:

1. Open the **New moves** or **New abilities** tab.
2. Press **Add a new move** - or, if a Pokemon already uses a name the game does not know,
   click its card marked "needs a description".
3. Fill in type, category, power, accuracy, PP and - most important - exactly what it does:
   extra effects and their chance, stat changes and by how many stages, how long things
   last. If it works like an existing move or ability, say which one.

Each card shows which Pokemon use it and whether it is already programmed into the game.

### What happens after saving

- Everyone who opens the site sees your save right away, marked "just edited".
- Every 15 minutes the dex picks up new saves, checks them and stores them in this
  repository. `DEX.md`, `TODO.md` and the game export update with it.
- If a save cannot be used (for example a stat of 999), it is listed in a box at the top of
  the front page with the reason. Open the Pokemon, fix it, save again.
- Things that work but look off (a move that is not in the game yet, a name over 12 letters)
  appear as warnings on the Pokemon's page after the next check.
- If two people edit the same Pokemon at the same time, the later save wins. Say in the
  Discord which one you are working on.

### For the maintainer

- Saves go to a small database (Supabase project `sigma-dex`, free plan). Each save is one
  row holding the whole Pokemon; rows are never changed, so the table is the edit history.
  The layout is in [`supabase/schema.sql`](../supabase/schema.sql).
- New moves and abilities are stored in `data/custom_moves.yaml` and `data/custom_abilities.yaml`.
  Set `implemented: true` there once one is programmed; the website cannot change that flag.
- Images are stored by the database's upload function and copied into `assets/concept-art/<pokemon>/`
  by `scripts/import_images.py`, so the repository keeps its own copy of all art (`data/images.json` lists them).
- A reorder is one row of kind `reorder` (steps `move` / `insert` / `close`, see `dexlib.change_layout`);
  it needs the migration `supabase/migrations/2026-10-04_reorder.sql`.
- `scripts/import_web.py` applies rows newer than `data/web_edits_cursor.txt`. Art paths and
  sprite details are always kept from the species file, never taken from the website.
- **There is no edit key** (removed 2026-10-02 because it confused people): anyone who finds
  the website can save edits, upload pictures and ask for sprites. What protects the dex is
  the hourly limits, the full history in git and in the database, and the checks that reject
  invalid data. If strangers start vandalising it, set a key again with the statements at the
  bottom of `supabase/schema.sql` and add the key field back to the forms.
- **Undoing a bad edit:** restore the species file with git (or just fix it on the website).
  Older saves are never re-applied, so a restored file stays restored.
- To sync right now instead of waiting: GitHub > **Actions > Dex > Run workflow**.

---

## Filling in the dex with the Google Sheet
*(was `docs/SHEET.md`)*

The easiest way to contribute is the edit form on the website ([Editing the dex on the website](#editing-the-dex-on-the-website)).
The sheet is the alternative for filling in many Pokemon at once.

Two things exist for people who never want to touch GitHub:

- **The Google Sheet** - where you type.
- **The website** (`site/index.html`) - where you see the result: every Pokemon's dex page,
  its stats at any level, which moves it knows at that level, what damage it takes, its
  evolution, any warnings, and what is still missing. No game needed.

### How to use the sheet

One row per dex slot, one column per piece of information (42 columns - everything a
Pokemon has except images). Row 1 is the column name, row 2 a hint about what to write.
Type in a cell; every 15 minutes the dex picks it up, checks it and updates the website.

- **Only cells you change are applied.** The sync remembers what the sheet looked like last
  time, so an old value sitting in the sheet never overwrites something that was edited on
  the website. The other way round does not happen automatically: an edit made on the
  website does not appear in the sheet. The website always shows the current state.
- **Emptying a cell** removes that value.
- **To add a Pokemon**, write its name in an open slot's row.
- **A row belongs to the Pokemon named in it, not to its number.** The `Name` column is how rows are
  matched, so it does not matter that the sheet shows old numbers after Pokemon were renumbered on
  the website: an edit in an old row still lands on the right Pokemon, and an old, untouched sheet changes nothing.
  Rules worth knowing:
  - **The `Dex #` column is never applied.** Changing a number in the sheet does nothing; move Pokemon
    with **Change numbers** on the website. The sheet's numbers only get refreshed when you paste a new `export/sheet.csv`
    (do that now and then for tidiness; nothing breaks if you do not).
  - **To add a Pokemon**, write a name that does not exist yet in a row whose number is an open slot.
    If that number now belongs to another Pokemon (because of a reorder), the row is reported - add it on the website
    or paste the current `export/sheet.csv` first.
  - **To rename a Pokemon**, change its name in its row. This only works while the Pokemon still has the
    number and name it had in the sheet; if it was moved or renamed on the website since, the row is reported
    instead of guessed at - rename it on the website.
  - A name that stands on two rows, or a row without a name on a number that may belong to someone else now, is
    reported and not applied.
- The `BST` column is calculated - typing in it does nothing.
- Columns are recognised by their name in row 1, so the order does not matter and extra
  columns of your own are ignored.

| Column | How to write it |
|---|---|
| `Type 1`, `Type 2` | `Grass`, `Steel` |
| `Ability 1`, `Ability 2`, `Hidden ability` | `Overgrow` |
| `HP` ... `Speed` | Base stats, 1-255 |
| `Evolves from`, `Evo condition` | On the **evolved** Pokemon's row: `Leafing` and `Lv 16`. Other conditions: `Thunder Stone`, `Trade`, `Trade holding Metal Coat`, `Friendship`, `Friendship (night)`, `Other: explain it here` |
| `Height (m)`, `Weight (kg)` | `0.5`, `5.8` (a comma works too) |
| `EV yield` | `1 attack` or `1 attack, 1 speed` |
| `Gender (% male)` | `87.5`, `50`, `0`, ... or `genderless` |
| `Egg group 1`, `Egg group 2` | `field`, `grass` |
| `Level-up moves` | `Tackle (1), Leer (1), Absorb (6)` - the level in brackets |
| `TM/HM moves`, `Tutor moves`, `Egg moves` | `Cut, Solar Beam, Toxic` |
| `Encounters` | `Route 1 \| grass \| 2-4 \| 20; Sigma Cave \| cave \| 8-10 \| 5` (place, method, levels, percent) |
| everything else | Plain text or a number. [Field guide](#field-guide) explains each field and its allowed values |

### When something is wrong

- A row that cannot be used (a letter where a number belongs, a growth rate that does not
  exist, ...) is skipped **as a whole**, and the reason appears in a box at the top of the
  website. Fix the cell and it goes through on the next sync.
- Things that work but look off (a move that does not exist in the game yet, a name longer than
  12 letters) show up as **warnings** on that Pokemon's page.

### Setting it up (once)

1. The sheet was filled from [`export/sheet.csv`](../export/sheet.csv) on 2026-10-02 (all
   columns, every known Pokemon, two frozen header rows). To rebuild it from scratch, paste
   or import that file into an empty tab.
2. The sheet must be shared as **Anyone with the link** (Viewer is enough for the sync;
   Editor lets people fill it in without being invited).
3. The sync finds the sheet through a repository secret named `SHEET_CSV_URL`
   (**Settings > Secrets and variables > Actions**), with the value
   `https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv&gid=0`.
   `gid` is the number after `gid=` in the address bar when the right tab is open.
   It is a secret because this repository is public: anyone who has the link to an
   "anyone can edit" sheet can change it, so share the sheet link in Discord only and never
   write it in a file here.
4. To sync immediately instead of waiting: on GitHub, **Actions > Dex > Run workflow**.

The sheet and the species files are the same data. The sheet is for the everyday filling
in; the files additionally hold art paths and sprite details.

---

## Letting Claude fill in a Pokemon
*(was `docs/CLAUDE_FILL.md`)*

Working out 20 level-up moves, 50 TMs, six base stats, catch rate, egg groups and growth rate is
the boring part of designing a Pokemon. On the website, a designer can open **Edit > Let Claude
fill in the rest**, tick the box and write a few lines about how it should play ("a slow tank
that walls physical attackers, should learn Rock Slide"). Claude then fills in everything that is
still empty, to fit the design.

Why not a button that does it instantly on the website: a convincing moveset needs judgment
(what the creature is, its family, what fits its concept, what is balanced next to the rest of
the dex). A fixed rule ("pick moves of its type by level") gives every Pokemon the same generic
list. So it is done by Claude, in batches, by whoever maintains the repo.

### For the maintainer: running it

Open Claude Code in this repository and say:

> Fill in the Pokemon that asked for it - follow docs/DEX_DATA.md ("Letting Claude fill in a Pokemon").

### For Claude: the rules

1. Run `python scripts/claude_fill.py` (with the repo's `.venv`). It lists every Pokemon with
   `design.claude_fill: true` that still misses something, with the designer's notes
   (`design.wishes`), its data and its evolution family.
2. **Never change a field a person filled in.** Only empty fields are filled. If the notes ask for
   something that contradicts a filled field, leave the field and say so in the summary.
3. Read the notes, the concept, the Pokedex entry and look at its concept art
   (`assets/concept-art/<id>/`). Fill in as a whole family when siblings also asked: stats grow
   with each stage, later stages keep the earlier stages' moves.
4. What to fill in, and how:
   - **Base stats**: a total that fits its stage and role (first stage ~300-330, middle ~400-420,
     final ~500-535, single-stage ~420-490), spread to match the notes and the design.
   - **Abilities**: from the game's list (`data/engine/expansion.yaml`) unless a new one is
     clearly wanted; a hidden ability is optional.
   - **Level-up moves**: 12-20 moves, levels like the official games (1, 4, 7, 10 ... ~50), a
     same-type move early, the signature move of the line late. Only moves that exist in the game
     unless the designer asked for a new one (then describe it under New moves on the website).
   - **Movesets for whole lines**: run `scripts/moveset_fill.py propose` first (see [Movesets: how the autocomplete decides](#movesets-how-the-autocomplete-decides));
     it proposes level-up, TM/HM, tutor and egg moves from similar official Pokemon, and `apply` adds them
     after the group approved.
   - **TM/HM**: only from the game's TM/HM list, what the body and type make sensible.
   - **Body color, EV yield, catch rate, exp, growth, friendship, gender, egg groups, egg cycles**: run
     `scripts/species_fill.py` (see [The numbers: height, weight, body color, EV yield, catch rate, exp, growth, friendship, gender, egg groups, egg cycles](#the-numbers-height-weight-body-color-ev-yield-catch-rate-exp-growth-friendship-gender-egg-groups-egg-cycles)); it fills only empty fields.
   - TM/HM lists: Origin HeartGold's 130 TMs and 8 HMs are in `data/engine/origin.yaml` (read from the game's docs
     2026-11-12), with its move tutors; the website's TM boxes and `validate.py` use that list.
   - **Egg moves** for first stages; **tutor** moves are optional.
   - Category, height, weight, body colour, catch rate, base exp, growth rate, friendship,
     gender, egg groups, egg cycles, EV yield: as official Pokemon of that kind and stage have.
   - **Pokedex entry**: only if empty; at most 4 short lines, in the tone of the games.
   - Do **not** fill in where it is found (`encounters`) - that depends on the game's maps - or
     the art.
5. Record what was filled in: `design.filled_by_claude` lists the fields (e.g. `[base stats,
   level-up moves, TM/HM moves, catch rate]`). The website shows that list on the Pokemon's page
   so people know what to review.
   Record how sure you are: `design.claude_sure` gives each of those fields a number 0-100.
   `scripts/species_fill.py apply` and `scripts/moveset_fill.py apply` write it themselves
   (`scripts/claude_sure.py`); for anything filled by hand, run `python scripts/claude_sure.py` or set it.
   85-95 = a fixed Game Freak habit, the colour seen in its sprite, or a look read from its art; 55-80 =
   copied from similar official Pokemon that mostly agree; 25-50 = a guess (they disagree, or no art).
6. Run `python scripts/validate.py` and `python scripts/build.py`, then commit with a message that
   names the Pokemon.

The species files are edited directly (not through the website), so the website's history does
not show these changes; the commit does.

### People and Claude on the website (16 Nov 2026)

Arvind: "maybe a person did 10 % and you 80 %, I want to see that". The list's **Done** bar is green for what
people filled in and purple for Claude (hover shows both numbers; "Sort: most done by people / by AI" sorts by
them). Separate People and AI columns were tried and taken out the same day ("we only need the green-purple bar"). Each Pokemon's INFO tab shows the same split under "% filled in", plus every field Claude filled in
with how sure it is (red under 50, yellow 50-74, green 75 and up; the filter "Claude is unsure about something"
lists them).

- A field counts as Claude's while it is on `design.filled_by_claude`. When a person changes it (website, Sheet
  or Doc), the import takes it off that list and off `claude_sure` (`dexlib.hand_over`): it is theirs then.
- A move list counts per move: the share of its moves that Claude added (`data/claude_moves.json`), also after
  people changed some of them.
- What the website's "Fill in the empty ones for me" button fills, and nobody changes before YES, is saved as
  Claude's, with its number.

---

## The numbers: height, weight, body color, EV yield, catch rate, exp, growth, friendship, gender, egg groups, egg cycles
*(was `docs/SPECIES_FILL.md`)*

Nobody wants to work these out by hand, so `scripts/species_fill.py` fills them the way Game Freak would. It only
ever fills **empty** fields; a value a person wrote is never changed. Species without base stats get only their
height and weight; the rest waits.

**On the website:** edit a Pokemon > POKEDEX > *Catching, breeding and items* > **Fill in the empty ones for me**.
It fills only the empty fields in the form and says why for each one; change anything before you press YES. The
suggestions are remade on every sync (every 15 minutes), so after new stats or a new look text they follow.

```
.venv/bin/python scripts/species_fill.py propose          # what it would fill, and why -> proposals/species_fill.json
.venv/bin/python scripts/species_fill.py show leafaxer
.venv/bin/python scripts/species_fill.py apply --all      # fill the empty fields in data/species/
.venv/bin/python scripts/species_fill.py suggest          # -> site/species_suggestions.json (the website button)
```

### How it decides

**Legendary or not** comes from `data/legendaries.yaml` (legendary, mythical, undecided = ordinary until decided).
A Pokemon not listed there counts as legendary when it does not evolve and has a BST of 570 or more, or when its
concept says "legendary". **The whole line shares** growth rate, gender, egg groups and egg cycles; when a person
chose one of those for one Pokemon of the line, the others get the same.

Every species is compared with every official Pokemon, exactly like the moveset tool (`docs/DEX_DATA.md` ("Movesets: how the autocomplete decides")): stats,
types, stage, line length, evolution levels, words in its look, the designers' wishes, its archetype. Each value is
the weighted choice of the most similar ones, plus Game Freak's fixed habits:

| Field | How |
|---|---|
| EV yield | 1 point for a first stage, 2 for a middle stage, 3 for the last of three stages, 2-3 for other final or single ones (as its models), 3 for legendaries; on its highest stat, split when two stats are close |
| Catch rate | its models' value, snapped to the values the games use (255, 190, 120, 90, 75, 60, 45 ...); starters and strong three-stage lines 45, legendaries 3, earlier stages of a legendary line 45 |
| Base exp | its models' exp per stat point times its base stat total |
| Growth rate | the same for the whole line, as its models; starters Medium Slow, legendaries and strong three-stage lines Slow |
| Base friendship | its models' (newer games' 50 counts as Origin's usual 70); legendaries usually 0 |
| Gender | the same for the whole line, as its models; starters 87.5 % male; "always female/male" in the design wins; legendary lines like legendaries (mostly genderless) |
| Egg groups | the same for the whole line: its models' groups plus what it is (a turtle -> Monster, a cow -> Field, an insect -> Bug, a fish -> Water 2, a humanoid -> Human-Like, a rock or robot -> Mineral, a ghost or smoke -> Amorphous); legendary lines Undiscovered |
| Egg cycles | the same for the whole line, snapped to the games' values; starters 20, strong three-stage lines 40, legendaries 120 |
| Height | its models' height, a little more for a look that says big and less for one that says small; the whole line at once, so each evolution is at least 1.2 times as tall as the one before it |
| Weight | its models' weight for their size (weight / height squared, close to how official Pokemon scale) times its own height squared; lighter for ghosts, clouds and smoke, heavier for rock and metal; each evolution at least 1.3 times as heavy |
| Body color | the colour of its body in the look text ("a small tan turtle" -> brown, "deep blue fur" -> blue); colours of small parts (eyes, snout, spots, a helmet) do not count. Checked against the sprites: where text and sprite disagreed, Claude looked at the sprite and chose (`proposals/body_color_visual.json`, 24 species) |

**Height and weight (16 Nov 2026).** They matter for more than the Pokedex: the sprite LoRAs were trained with
"X m tall", and a big Pokemon fills more of its frame (docs/LORAS.md). Before the rule ran, the designers' own cards
in `assets/concept-art` were read (28 Pokemon had a height or weight printed there that never reached the dex;
Wreckingdrake's card says 1980 kg; the website's old 999.9 limit was raised to 9999.9, as the game keeps weight
as a whole number of 100 g and shows it as text). Where the rule did not fit the design after reading
its look and art, Claude's value is in `proposals/height_weight_review.json` (with the reason) and wins over the rule.

Not filled: **where it is found** (encounters). That depends on Origin HeartGold's maps and the story plan
(`docs/STORY.md` ("Story roles: which Pokémon Origin HeartGold's story needs, and who from our dex takes them")), so it is decided there.

The official numbers come from PokeAPI's public data (fetched when it runs, kept in `.cache/`, nothing of it in
the repo).

---

## Movesets: how the autocomplete decides
*(was `docs/MOVESETS.md`)*

`scripts/moveset_fill.py` proposes level-up, TM/HM, tutor and egg moves for every evolution line, based on
real Pokemon in Origin HeartGold. It never removes or changes a move that is already in a species file; it only
fills gaps. Nothing reaches `data/species/` until someone runs `apply`, and that only happens after Arvind said
yes.

Always propose from the newest species files (main), not from an old branch: website edits land on main.

```
git fetch && git worktree add --detach /tmp/sigma-main origin/main      # or any up-to-date checkout of main
.venv/bin/python scripts/moveset_fill.py propose --data /tmp/sigma-main/data   # all lines, about 15 seconds
.venv/bin/python scripts/moveset_review.py                # review page -> proposals/review.html
.venv/bin/python scripts/moveset_fill.py show leafaxer    # one proposal with its reasons
.venv/bin/python scripts/moveset_fill.py propose --fresh  # new proposal for the part Claude added before; apply replaces it
.venv/bin/python scripts/moveset_fill.py apply --data /tmp/sigma-main/data --only leafing,leafsteel   # after approval
.venv/bin/python scripts/moveset_pick.py leafaxer 40      # best 4 moves at level 40 (for trainers)
```

Outputs: `proposals/movesets.json` (everything, with reasons), `proposals/MOVESETS.md` (readable summary),
`proposals/review.html` (the review page; published as an artifact so the group can mark each line OK or
"needs changes"). Rerun `propose` whenever species change: it starts again from the current files.

### On the website (anyone, any time)

Edit a Pokemon > MOVES > **Moveset suggestions**. Two choices:
- **Fill gaps**: moves it does not have yet, all ticked; untick what you do not want, then "Add the ticked moves
  to the form". Hover a move to see why it is suggested.
- **New proposal**: a fresh proposal for the part Claude filled in before (listed in `data/claude_moves.json`);
  "Replace Claude's moves with this" takes those out and adds the new ones. The moves your group wrote stay.
Nothing is saved until you press YES, and everything can still be changed by hand. The suggestions are remade on
every sync (`moveset_fill.py suggest` in `.github/workflows/dex.yml`, every 15 minutes), so after you save new
stats, types, abilities or notes, a new suggestion is ready within 15 minutes.

### Where the facts come from

- **The official games' Pokemon** (types, stats, abilities, evolutions, egg groups, level-up / TM / tutor / egg
  moves) from Pokemon Showdown's public data (MIT), fetched when it runs, so it works anywhere, also on GitHub.
- **Origin HeartGold** in `data/engine/origin.yaml`: its 130 TMs + 8 HMs, its 85 move tutors (place and price)
  and the moves it changed (e.g. Slam is Grass there). Read from the game's player docs (made by the English
  patch team). `SIGMA_MOVESET_SOURCE=origin` uses those docs directly (`~/sigma-origin/docs`, only on Arvind's Mac).
- **Pokemon Showdown's moves.json** (MIT) for what a move does: setup boosts, recovery, priority, pivoting,
  punch/sound/slicing flags.
- Both are cached in `.cache/movesets/` (gitignored). The repo keeps only our own species' moves and Origin's
  TM/tutor lists.

### Steps

1. **Lines.** From the `evolutions` fields, plus "evolves from X" on a concept card. Species with no evolution
   written that sit next to each other in the dex, share a type and grow clearly in stats (or have the same name
   with `-utv`/`-utvikling`) are treated as a line too, and the proposal says "guessed from the dex order".
2. **Learning from all of them.** Each species is compared with every official species: shape of the stats (which
   stats are high), total, types (same types count most), stage, evolution levels, shared abilities, words in its
   look/concept (turtle, bat, mushroom ...), official Pokemon the designers name ("like Zigzagoon", "inspiration
   from Tyranitar") and official Pokemon that can learn the moves the designers already chose. Legendaries are only
   compared with legendaries. Every official Pokemon then gets a weight that falls off smoothly with how different
   it is (the 60 closest count; the closest one usually weighs 10-30 %, so no single Pokemon decides). The page
   shows the eight biggest influences. The result is a Pokemon inspired by many, not a copy of one.
3. **Built around your own moves.** Moves already in the file never change, and they steer the rest: an official
   line that can learn the moves you chose counts as more similar; a model move that does the same job as one of
   yours (same type, side, about the same power and level, no different effect; or the same kind of status move)
   is left out and listed; nothing stronger of the same type comes before your own strong move; new moves never
   share a level with yours. Only level-up is thinned this way and only for moves learned at about the same
   level: the same kind of move can still come from a TM or tutor. A move that hits both foes (Heat Wave) and one
   that hits one (Flamethrower) are different moves.
4. **Level-up.** Every weighted official Pokemon votes with its level-up list: its levels are moved to our
   evolution levels, and its moves of a type we do not have are swapped for a move of our type at about the same
   power, on our physical/special side. Each move gets the sum of the votes and the weighted middle of their
   levels; the strongest moves are taken, as many as such Pokemon usually have, spread over the levels the way
   they spread them (start, before evolving, right after, middle, late), so a Pokemon keeps learning moves after
   it evolves. An evolved form also gets what its earlier stage learns after the evolution level, a bit later.
   The proposal flags a Pokemon that learns nothing after evolving or has a long gap without new moves.
   **Same-type ladder:** like Game Freak, each own type gets a weak (35-60), a middle (65-80) and a strong,
   reliable (85-100 power, 90 %+ accuracy) move by level-up on the side the Pokemon attacks with; a missing step
   is filled with the move official Pokemon of that type learn most (Autuman: Razor Leaf, Slam, Leaf Blade, and
   Power Whip as its big move). When translating a model's move, the commonly learned move of our type wins near
   ties, so the votes add up instead of splitting over many similar moves. Moves outside our own types need
   more agreement (15 % of the weight). Type-flavoured status moves are swapped (Sleep Powder -> our type's sleep
   move, Sunny Day -> our weather) or dropped; other species' signature moves are never copied; each of our types
   gets level-up attacks; at most six moves at level 1 for evolved forms; an evolved form keeps what its earlier
   stage learned before evolving; punches are skipped for bodies without arms.
5. **TM/HM, tutor, egg.** For every TM (Origin's list only) and every tutor move, a score from how much of the
   weighted official Pokemon learn it and how many official Pokemon of our types (at that stage) learn it; moves
   almost everyone learns (Protect, Rest ...) are in. Evolved forms keep their earlier stage's TMs and tutors.
   Tutor proposals list the tutor's place and price (tutors are spread over the map in Origin). Egg moves only
   for first stages, not for legendaries, genderless or Undiscovered ones, and (as breeding works) only moves a
   partner of the same egg group can pass on; when the file has no egg groups yet, the line model's are used.
   Translated level-up moves are held back to fitting levels (no 95-power move at level 12).
6. **Designers' moves.** Moves named in `design.wishes`, "Notable moves:" and similar in `design.notes`, and new
   moves from `data/custom_moves.yaml` that the card names, are added (TM moves as TMs, others in level-up).
   Signature moves from cards that are not in the game yet are listed as "describe them under New moves".
7. **Abilities and look.** Moves that cannot work are never added: with Wonder Guard (1 HP) no Rest, Substitute,
   Endure, healing, recoil moves or Skill Swap (`scripts/dex_rules.py`). Moves that make an ability work are added if they fit: Strong Jaw -> bite moves,
   Iron Fist -> punches, Sharpness -> slicing moves, Technician -> weak multi-hit moves of its own types,
   Drought/Chlorophyll/Leaf Mane -> Sunny Day and Solar Beam, Drizzle/Swift Swim -> Rain Dance, Snow Warning and
   Cold-hearted -> Hail, Weather Switch -> Rain Dance + Sunny Day + Weather Ball, surges -> their terrain,
   Prankster -> status moves, Sloth Combat -> Rest/Sleep Talk/Snore, Toxic/Liquid Voice and Punk Rock -> sound
   moves (full list in `ABILITY_SYNERGY`). Words in the look/concept add a move that shows the design when its type
   fits: a lamp or light bulb -> Flash, smoke -> Smokescreen, a beak -> Peck, horns -> Horn Attack, claws -> Slash,
   a shell -> Withdraw; a weight of 150 kg or more gives Heavy Slam to a bulky or Steel Pokemon. Wishes like
   "mostly fighting moves" make that type count more everywhere. An ability named in the wishes but missing from
   the file is flagged.
8. **Archetype.** Two kinds, both used. *Stat archetype*: what its stats and types make it (a fast physical
   Grass/Bug): attacks on the side it does not use get much less weight (0.45-0.6 of a vote, and lower TM/tutor
   scores) when attack and sp. attack are 25+ apart, so it learns Leaf Blade and X-Scissor rather than Energy Ball;
   fast attackers get a priority or pivot move like similar official Pokemon. *Design archetype*
   (`proposals/archetypes.json`, written by Claude from every design field: "shark boxer", "lamp-lit cave
   tortoise"): its themes (punching, biting, sound, light ...) count 1.6x in the votes and in TM/tutor scores, a
   few moves that show it are added, themes that clash with its body are left out, and its role is used unless the
   designers' wishes say otherwise. Run the archetype pass again (ask Claude) for new species.
9. **Design review.** A script cannot judge whether "a little lamp turtle that blinds enemies" should learn Flash,
   so Claude reads each design (look, concept, dex entry, category, notes, wishes, body, size) next to the proposal
   and writes `proposals/design_review.json`: moves to leave out because they clash with the design, a few moves
   the design asks for, and a one-line note. `propose` applies it on every run (only to added moves, names and
   TM/tutor lists checked), then the balance checks below run again. Update it when designs change.
10. **Coverage.** TMs and tutors that hit what its own types cannot score higher, and every final form gets
   coverage like official Pokemon of its kind: about 4 strong moves of other types for attackers, 3 for others,
   chosen from what the similar official Pokemon learn, preferring the types that add most.
11. **Role.** From the final stage's stats (offence, bulk, speed, physical or special, Huge Power counted) and
   role words in wishes/notes: fast/bulky/Trick Room attacker, wallbreaker, wall, support. If the role misses
   its tools and similar official Pokemon have them, they are added: a strong move (75+ power) of each own type,
   a setup move for attackers, recovery for walls, Trick Room only if the notes say so or similar Pokemon have it.
12. **Not broken.** Combos are checked against official Pokemon with about the same total (within 50) and attack
   (within 20). If none of them has the combo, an added move is taken out again ("Not added: ..."); if the
   combo came from the designers, it is flagged ("Check ..."). Checked: same-type priority + setup on a strong
   attacker, Speed Boost + setup, Huge Power + priority, recovery + setup on a bulky Pokemon, rare moves (Shell
   Smash, Quiver Dance, Belly Drum, Spore, Extreme Speed ...), Serene Grace + flinch, Contrary, Simple, banned
   abilities (Moody, Shadow Tag, Arena Trap). Some moves are never added at all (Spore, Shell Smash, Baton Pass,
   OHKO moves, Double Team-style evasion, Water Spout/Eruption ...). Finally the example set's damage is
   compared with every official final stage of about the same total: "Strong" if it beats all of them, "Weak"
   if an attacker is in the bottom 10 %.

### The 4-move picker (reusable)

`scripts/moveset_pick.py` picks 4 moves for one Pokemon at one level from the moves it can know. The proposals
use it for each line's example set; the story team builder can use it per battle (`pick(mon, level, pool)` from
Python, or `--json` from the command line). `battle="double"` (`--doubles`) is for double and multi battles:
moves that hit both foes count more, moves that also hit the partner a little less, and doubles support
(Fake Out, Protect, Follow Me, Tailwind ...) counts more. It works like Showdown's random-battle sets in small: each attack
gets a damage value (power x accuracy x same-type bonus x the right attacking stat x hits x ability, minus for
recharge, charging, self-KO, big self-drops); moves are taken one at a time, each time the one that adds most
(an attack adds the damage it brings against the 18 types beyond what the set already hits, plus a bonus for
the first strong move of each own type; a status move adds a share of the best attack depending on the role).
At most one setup, recovery, status and hazard move; at least two attacks (three for attackers).

### Known limits

- Tutor moves: Origin has about 85 tutor moves in 71 tutor scripts, spread over the towns and paid with items or
  money. Who may learn one is decided inside each tutor's script (a/0/1/2: GetPartyMonSpecies + a chain of
  CompareVarToValue), not by a species table. Proposals only use moves those tutors teach, and
  `proposals/movesets.json` records under `tutor_places` which tutor (place, price) teaches each tutor move, so
  the Origin export can add our species to those scripts' check chains. The single-species tutors (Headbutt,
  Surf, Charge, and the starter moves Blast Burn / Frenzy Plant / Hydro Cannon, which only our starters' final
  forms get) are not handed out otherwise. TM compatibility is a separate per-species list (NARC 273), and
  Origin's Move Reminder (Saffron, Blackthorn; 1 Heart Scale) re-teaches level-up moves.
- TMs: Origin also lets a Pokemon use a TM whose move it learns by level-up.
- Custom abilities (Drunken Rage, Sloth Combat ...) are not understood by the damage maths; read their flags.
- Species without types are skipped. Species without base stats wait (Arvind, 2026-11-12): their moves are
  proposed once the stats are in.
- Rainbro is Stellar (no weaknesses or strengths, Arvind 2026-11-12). The species files cannot hold that type yet, so
  `TYPE_OVERRIDES` in the script sets it. Stellar gets no same-type bonus and its moves are spread over many types.
  Origin HG has no Stellar type (its old ??? slot is Fairy), so the export needs new code for it.

### Rebuilt 16 Nov 2026

Arvind: the movesets nobody has changed can be built again with everything taken into account. `propose --fresh`
+ `apply --only` (all species whose moves people had not touched since Claude, plus new ones without moves; 96
species). It now knows the explicit lines (Santrock -> Cindreon -> Custodix and Sigmanian Charcadet -> Glacépée
written into the species files; `data/lines.yaml` stops Quimsy/ROKU and Felk/Moosus being guessed as lines, and
the legendary trios in `data/legendaries.yaml` are never guessed together), and weight (Heavy Slam for 150 kg and
up, now also Heat Crash for heavy Fire types). The 59 movesets people had changed, and SOLIDEDGE and Meowthwo
(moves made by people), were left as they are.

---

## Dex analysis: what Sigma Dex is missing (2026-10-08)
*(was `docs/DEX_ANALYSIS.md`)*

State: 99 of 151 slots filled, 96 with a type. Compared with all 9 official generations,
using pokeemerald-expansion 1.17.1 (modern types, Fairy applied backwards).
Pictures for sharing: `img/dex-types-per-gen.png`, `img/dex-trends.png`, `img/dex-roles.png`.

### How it was measured
- Official numbers: parsed from `~/sigma-expansion/src/data/pokemon/species_info/` and grouped by national dex number
  (Gen 1 = 1-151, Gen 2 = 152-251 and so on). Base forms only, 1011 species.
- Sigma numbers: `data/species/*.yaml`.
- Not reliable yet: evolution lines (only 16 links are recorded), base stats (60 of 99 have them),
  and every role marked partly or unknown (most species have no description or concept text).

### Monotypes
| | Mono share |
|---|--:|
| Gen 1 | 57 % |
| Gen 2 | 51 % |
| Gen 3 | 53 % |
| Gen 4 | 51 % |
| Gen 5 | 54 % |
| Gen 6 | 40 % |
| Gen 7 | 37 % |
| Gen 8 | 54 % |
| Gen 9 | 35 % |
| **Sigma** | **22 %** (21 of 96) |

- 8 types have no monotype at all: Fighting, Psychic, Poison, Ground, Flying, Dragon, Dark, Steel. Gen 1-3 had 17 mono Psychic, 13 Poison, 11 Fighting, 10 Ground.
- Only 1 pure Normal (Gen 1-3 had 37). Normal mono is the early-route backbone.
- To reach the Gen 9 level (~36 %, 54 mono in 151) 33 of the 55 remaining slots must be monotype. 45 % needs 47. 50 % needs all 55.
- Cheaper option: some existing dual types could lose their second type (the designers decide).

### Type share, generation by generation
See `img/dex-types-per-gen.png`. Closest official generation by type share: **Gen 9** (distance 42), then Gen 8 (51). Kanto is the furthest (85).

Where Sigma differs most from the old generations (Gen 1-3 average share, in % of Pokemon with the type):
- Too few: Flying 7 (13), Psychic 6 (11), Normal 11 (14), Fighting 5 (5 in Gen 1-3, 7 overall).
- Too many: Ghost 11 (3), Dark 12 (4), Steel 9 (3), Fairy 8 (2), Rock 11 (8), Poison 14 (11), Ice 7 (4).
- 30 % of Sigma Pokemon have Dark, Steel or Fairy (Gen 1-3: 3-16 %, Gen 8-9: 23-28 %). The dex plays like a modern one.

### Other trends
- Strong non-legendaries (BST 540+): 9 of the 60 with stats (Cryoblade 605, Insectoid 580, Chuchar 574, Verrith 570, Crappy Meal 560, Parahaunt 556, Obsidog utvikling 555, Darkgonark 550, Panzerien 540). Gen 1-3 together had 11 in 384 Pokemon.
- Legendaries: Sandrema (mythic), Bergflabbser, Maagamad (both BST 680), Sabertann, Gravriel and one unmade, about 6 of 151 (Gen 1: 5, Gen 2: 6, Gen 3: 10).
- Repeated dual pairs (3 each): Poison/Rock, Flying/Normal, Dark/Water, Bug/Dragon, Fairy/Poison, Psychic/Water.
- Rainbro is Stellar, which is not a species type in the game. Fleuroom utvikling, Gentie and Flurina have no type yet.
- Evolution structure (single-stage, two-stage, three-stage share) cannot be compared yet: most evolutions are not entered.

### Roles every generation has
See `img/dex-roles.png`.
- Have: three starters, early bird (Erobi), early bug (Wump), Geodude (Leadling), Diglett (Bulbtle), Gastly (Ciggiti), branching (Wispole), mythic (Sandrema).
- Partly: legendary trio (Sabertann, Gravriel + 1 to make), pseudo-legendary, fossil, early Normal route Pokemon, bat, fighter, cute Fairy/Normal. Unconfirmed guesses, check with the designers.
- Missing: electric mascot (Zapana is an eel), early Psychic, Magikarp-like, baby Pokemon.

### Suggested use of the 52 open slots (108-142 are 35 in a row)
Priority is monotypes first, then types and roles:
1. Mono Normal route Pokemon (2-3 lines): rodent, dog or pig.
2. Mono Psychic early line (Abra, Ralts) and a mono Fighting line.
3. Mono Flying (a second bird line) and mono Poison, Ground, Dragon, Steel, Dark.
4. Electric mono mascot.
5. Magikarp-like fish and a baby Pokemon.
6. Third legendary of the trio.

---

## Getting everything out of the Discord channel
*(was `docs/DISCORD.md`)*

The concept art and a lot of decisions only exist in Discord. `scripts/discord_export.py`
downloads every message and every attachment from a channel in one go.

It uses Discord's official bot API. That is the only way that is allowed: tools that log in
with your personal account ("self-bots", or DiscordChatExporter with a user token) break
Discord's terms of service and can get the account banned.

### One-time setup (about 5 minutes)

Someone with the **Manage Server** permission on the server has to do steps 3-4.

1. Go to <https://discord.com/developers/applications>, click **New Application**, name it
   (e.g. "Sigma Dex Export").
2. Open **Bot** in the left menu. Turn on **Message Content Intent**. Click **Reset Token**
   and copy the token. Treat it like a password - never paste it into Discord, a file in
   this repo, or a chat.
3. Open **OAuth2 > URL Generator**. Tick **bot**, then the permissions **View Channels** and
   **Read Message History**. Open the generated URL and add the bot to the server.
4. If the channel is private, add the bot to it (channel settings > Permissions).
5. In Discord: **Settings > Advanced > Developer Mode** on, then right-click the channel >
   **Copy Channel ID**.

### Run it

```bash
export DISCORD_BOT_TOKEN=paste-the-token-here
```

Or save the token as the only line of a file named `.discord-token` in this folder (git
ignores it).

```bash
python3 scripts/discord_export.py CHANNEL_ID
```

The result lands in `discord-export/<channel id>/`:

- `messages.md` - the whole conversation, readable, oldest first
- `messages.json` - the same with all details
- `attachments/` - every image and file, prefixed with the message ID

That folder is ignored by git on purpose: it holds everyone's private messages. Go through
it, copy the art that belongs to a Pokemon into `assets/concept-art/<species>.png`, and
move the decisions into the species files. Running the script again later only downloads
new attachments.

When you are done, remove the bot from the server or reset its token.

---

## What came out of the Discord channel
*(was `docs/DISCORD_SWEEP.md`)*

On 2026-10-03 the whole #official-sigma-pokedex channel was exported with the bot (625 messages,
245 pictures) and every picture was looked at. This is what happened to them. The export itself
stays on Arvind's computer and is not in this repository, because it holds private messages.

| | Pictures |
|---|---|
| Show one of the group's designs | 235 |
| Attached to a Pokemon in the dex | 144 (on 59 Pokemon) |
| Designs whose name is not in the dex (listed below) | 42 |
| Designs with no name anywhere | 46 |
| Not about the dex (memes, screenshots, photos) | 10 |

Pictures matched "from context" (the caption says so) had no name written in them; the match
comes from the message text or from the same design appearing on a named card. Remove a wrong
one on the Pokemon's page.

### Data taken from the concept cards

Only empty fields were filled; nothing that was already in the dex was changed. 40 Pokemon got data:

- **Ampeel**: category, height, weight, abilities, stats, dex entry
- **Anjane**: category, dex entry
- **Blylem**: category, height, weight, dex entry
- **Bolthook**: types, category, height, weight, abilities, dex entry
- **Brawleo**: category, dex entry
- **Bugmight**: category, height, weight, abilities, stats, dex entry
- **Bulbtle**: category, abilities, stats, dex entry
- **Bulbtoise**: category, abilities, stats, dex entry
- **Chebbi**: dex entry
- **Chillalit**: category, height, weight, abilities, stats, dex entry
- **Chuchar**: types, category, height, weight, abilities, stats, dex entry
- **Ciggiti**: types, category, height, weight, abilities, stats, dex entry
- **Crappy Meal**: category, height, weight, abilities, stats, dex entry
- **Darkgonark**: types, category, height, weight, abilities, stats, dex entry
- **Devampry**: dex entry
- **Erobi**: category, height, weight, abilities, stats, dex entry
- **Freezrick**: category, abilities, dex entry
- **Galfrogtom**: category, dex entry
- **Gortiki**: category, dex entry
- **Gravriel**: category, height, weight, abilities, stats, dex entry
- **Hairyen**: category, height, abilities, stats, dex entry
- **Icy Freeze**: category, abilities, dex entry
- **Iglomodo**: category, height, weight, abilities, dex entry
- **Janenon**: category, dex entry
- **Maagamad**: category, height, weight, abilities, stats, dex entry
- **Motinky**: category, dex entry
- **Nuclobyl**: category, height, weight, stats, dex entry
- **Nucloid**: category, height, weight, stats, dex entry
- **Nukfae**: category, height, weight, dex entry
- **Panzerien**: category, height, abilities, stats, dex entry
- **Parahaunt**: types, category, height, weight, abilities, stats, dex entry
- **Sigmanian Unown**: types, category, height, weight, stats, dex entry
- **Smeatherace**: category, height, weight, abilities, stats, dex entry
- **Stonma**: category, dex entry
- **Tinky**: category, dex entry
- **Tomaterdander**: category, height, weight, abilities, stats, dex entry
- **Toxiren**: category, height, weight, dex entry
- **Unknighted**: types, category, height, weight, stats, dex entry
- **Wispole**: category, dex entry
- **Zapana**: category, height, weight, abilities, stats, dex entry

Things to check:

- Icy Freeze: card says Ice/Dark, dex says Ice - dex kept
- Zapana: card says Electric, dex says Water/Electric - dex kept
- Ampeel: card says Electric, dex says Water/Electric - dex kept
- Bulbtoise: three abilities on the card, took the third (Electric Surge) as the hidden one
- Bulbtle: three abilities on the card, took the third (Electric Surge) as the hidden one
- Iglomodo: three abilities on the card, took the third (Ice Scales) as the hidden one
- Cards in trading-card style ("... ex") were attached as pictures, but their numbers are not game stats and were not used.
- Many abilities on the cards do not exist in the game (the dex warns about each); they have to be described under **New abilities** on the website before they can be programmed.

### Designs in the Discord that are not in the dex

These have a name in the picture that matches no Pokemon in the dex. Add them on the website (an open slot) and their art can be attached.

| Name in the picture | Pictures | Posted by | Types on the card |
|---|---|---|---|
| Ampergon | 1 | johnnes3204 | Electric |
| Bømelulu | 2 | dr.grey8421 | Poison/Ground |
| Colossloth | 1 | Arvind Frøiland | Fire/Rock |
| Crystallion | 1 | dr.grey8421 | Fairy/Ground |
| Dominator | 2 | dr.grey8421 | Lava/Steel |
| Equinn | 2 | dr.grey8421 | Electric/Steel |
| Equinox | 2 | dr.grey8421 | Electric/Steel |
| Fairyon | 2 | dr.grey8421 | Fairy/Normal |
| Gameprime | 3 | dr.grey8421 |  |
| Melodix | 2 | dr.grey8421 | Fairy/Normal |
| Nightshade | 2 | dr.grey8421 | Fairy/Normal |
| Pachi | 2 | dr.grey8421 | Poison/Ghost |
| Paxsoid | 4 | dr.grey8421 | Normal/Dragon |
| Psydregon | 1 | dr.grey8421 | Psychic/Dragon |
| Sabertann | 1 | SLOTHBABY | Dark/Water |
| Salamon | 2 | dr.grey8421 | Water/Normal |
| Siberian Dealer | 2 | dr.grey8421 | Poison/Fairy |
| Snusdealer | 4 | dr.grey8421 | Normal |
| Terrora | 1 | dr.grey8421 | Fairy/Ground |
| Toxalloy | 1 | Fugli | Poison/Steel |
| Unicron | 1 | dr.grey8421 | Psychic/Ground |
| Viridub | 2 | Ruben | Grass |
| Whaldrill | 1 | SLOTHBABY | Ice/Ground |

### The two older channels

The very first designs were posted on 2026-05-01 in #kanteradet and #pokemon-goons, before the
dex channel existed. Found there on 2026-10-03 and attached: the three starters (Leafing,
Torchbat, Waffy) with the Leafing line, Warrallier, Blazterra, Cryoblade, Giga-Circuit, Insectoid,
plus sketches of Ampeel and Darkgonark. Cryoblade and Insectoid got their card data.

Designs from those channels that are not in the dex: Zarevok, Slobbleaf, Bratgore, Scorcoal /
Combustace / Infernalace, Watt-ling and Ampe-reon (the stages before Giga-Circuit), Voidgen,
Pupdetect / Detecup / Gumshoe, Meteoric, Gemonite, Nosexus, Stenrik, Cholt / Voltralt / Zapitera,
Zapydra / Voltagar / Aero-Voltex, Aqualaveil, Brention and an own design called Parasect. Joke
cards and anything not suitable for a public site were left out.

### Second pass: linking by what the pictures show (2026-10-03)

The first pass only linked a picture when a name was written in it or in its message. A second
pass looked at every unlinked picture, every picture with several creatures in it, and all
pictures from the two older channels, and compared them with the art each Pokemon already had
and with what was posted right before and after.

- 178 pictures examined; 54 more pictures or cut-outs attached (captions say "probably" when
  the link rests on resemblance, not on a written name).
- Pictures with several creatures were cut up, so each Pokemon gets its own clean picture - for
  example the ghost trio (Ciggiti, Parahaunt, Chuchar), Hippore / Docuphant / Razox, the Leafing
  line, Tinky / Motinky / Gortiki, Stonma / Sigmauler. The cut-out boxes were estimated by eye.
- First art for: Saucerl, Octopearl, Balleisk (all "probably").
- Too uncertain to attach (low confidence): a larger ring creature that may be Abyssys, a pink
  gem-bodied creature and a small blue ghost that may be Gentie, a lizard with a green crystal
  shield that may be Dragem, a pencil bird that may be Erobi, a seagull sketch that may be Maagamad.
- Still without any art: Abyssys, Bygon, Dragem, Gentie, Greation, Lapper, Twemp, Ultragon, Wealther.
- 34 pictures were left out because they are not suitable for a public site or are not designs.
- A group member replaced Torchbat's pictures on the website with the Torchbat / Heatbat /
  Blazterra line sheet; that sheet is now Torchbat's reference, and the older "choose your
  starter" Torchbat was not re-attached.

### Left out on purpose

Three pictures were matched too weakly to attach: a bee-winged dragon sketch (maybe Balleisk), a leafy web sprite (maybe Twemp) and a spiky tree creature (maybe Sigmanian Sudowoodo).

---

## Backup
*(was `docs/BACKUP.md`)*

Everything is kept in three places:

1. **GitHub** (`arvindfroi/sigma-dex`): the full history of every species file, picture and sprite. There is no
   rule against force-pushes on GitHub (Arvind, 2026-11-11: not needed); the Legion's mirror below keeps every old
   commit anyway.
2. **The website's database** (Supabase): the edit log, uploaded pictures, the request board and the sprite studio.
3. **The Legion, `D:\SigmaBackup`**, written every night at 04:17 by `scripts/backup.py` (Windows task
   "Sigma dex backup"). It only ever adds, and on a night when nothing changed it writes nothing but the log line:
   - `git\sigma-dex.git`: a mirror of GitHub whose reflogs never expire, so old commits survive even a force-push.
   - `db\<date>\<table>.json.gz`: every table of the database, one folder per day on which something changed
     (`state.json` remembers what the last run saw).
   - `files\...`: every picture the database points to (uploads, Lost and found, studio tries), downloaded once.
   - **Raw pictures of unpicked studio tries live only here** (since 2026-11-13). After downloading, the backup sends
     the raws it holds with their sizes to the `sprite-worker` function (`prune_raws`, worker key from
     `SIGMA_WORKER_KEY_FILE`, default `D:\LocalAI\sigma-worker\worker.key`), which removes from the website storage
     every raw whose tries are all unpicked, have no follow-up try, were used by no job and finished more than a day
     ago (`RAW_DAYS`, rule in `raw_prune_candidates`), and only if the backup holds it at the same size. The path
     stays in `sprite_tries.raw`. Why: Supabase's free plan holds 1.1 GB, the bucket had reached 2.19 GB, 1.9 GB of
     it raws (a front's raw ~1.4 MB, its sprite 2 KB), and the website never shows a raw. Picked raws stay on the
     website.
   - **Old unchosen tries of Pokemon with a saved set live only here** (since 2026-11-23; Arvind: "ta den du" when
     the bucket was at 1.34 GB). After the raws, the backup sends every studio file it holds (`prune_unchosen`), and
     the function removes every file of a try of a Pokemon with an approved set that finished more than 7 days ago
     (`UNCHOSEN_DAYS`, rule in `unchosen_prune_candidates`), unless an approved or waiting set uses it, it belongs to
     a try such a set uses or a waiting job starts from, or it is the picture of a try one of those was made from;
     again only if the backup holds it at the same size, and only on a night when every picture was downloaded. The
     tries get `pruned_at` and the studio stops listing them. Trainer tries and Pokemon without a set are never
     touched. These two are the only things the backup ever deletes, and it never deletes here.
   - `backup.log`: one line per night with the free space left; a line with PROBLEMS means something was not copied
     or that less than 3 GB is free. Below 1.5 GB free no new pictures are downloaded, so the disk never fills up.

### Restoring

- A species file or picture: `git log -- data/species/<id>.yaml` in any clone (or in the mirror) and check out the old
  version. A Pokemon removed on the website comes back by taking its file from history and deleting its line from
  `data/removed_species.json`.
- The whole repository: `git clone D:\SigmaBackup\git\sigma-dex.git` gives every branch; `git reflog show main` in the
  mirror lists every state `main` has had.
- A database table: unzip `db\<date>\<table>.json.gz`; each file is a JSON list of rows, ready to insert again.
- Pictures: `files\<path>` is the same path as in the "art" storage. A pruned raw goes back by uploading
  `files\<path>` to the same path in the "art" bucket.

### The task script

`D:\SigmaBackup\run-backup.ps1` (only on the Legion) fetches the mirror, takes `scripts/` from `main` and runs
`backup.py`; its own output goes to `task-output.log`. Native commands (git, tar, python) run with
`$ErrorActionPreference = "Continue"` and are judged by their exit code: Windows PowerShell turns git's progress on
stderr ("From https://...") into an error, and with "Stop" that killed every night's run from 2026-11-12 (the task
showed result 1, nothing was logged) until it was fixed on 2026-11-13. A night without a new `backup.log` line
means the script itself stopped: look at `task-output.log` and the task's last result.
