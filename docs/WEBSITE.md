# Editing the dex on the website

**https://arvindfroi.github.io/sigma-dex/** - no account, no GitHub, works on a phone.

## How to contribute

1. Click a Pokemon, then **Edit**. Or click an **open slot** to add a new Pokemon.
2. Fill in what you know. Leave the rest empty - a half-finished Pokemon is fine.
3. At the bottom, write your name. The site remembers it on your device.
4. **Save.** You land on the Pokemon's page with your changes: its dex entry, its stats at
   any level, which moves it knows at that level, the damage it takes, and the list of what
   is still missing. That page is how you test a Pokemon without playing the game.

Everything about a Pokemon can be entered: name, types, credits, dex entry, size, abilities,
base stats, EV yield, catch rate, exp, growth rate, friendship, gender, egg groups, held
items, evolutions, level-up / TM / HM / tutor / egg moves, where it is found, design
notes, and images. Moves and abilities suggest the ones that already exist in the game while you type.

## Changing the numbers (moving Pokemon, adding a slot between two)

Press **Change numbers** above the grid. The page shows every slot as a list.

- **Move a Pokemon:** type the number it should get in its row and press **Move**. If that slot
  is empty it simply goes there. If another Pokemon sits there, the Pokemon in between move one
  number up or down to make room, so numbers never repeat. **Up** and **Down** swap a Pokemon
  with its neighbour. On a computer you can also drag a Pokemon onto another row.
- **Add an empty slot between two Pokemon:** press **Add empty slot here** on the row that
  should come after the new slot. That Pokemon and everything after it move down one number.
  This needs the last slot (#151) to be empty; otherwise the page says so.
- **Close a gap:** press **Remove empty slot** on an empty row; everything after it moves up one.
- Changes are only a preview until you write your name and press **Save new order** (one save for
  all your steps; **Undo last step** and **Cancel** are available before that). The import then
  applies all of it or none of it, within about 15 minutes. Only the numbers change; nothing else
  about a Pokemon is touched, and evolutions and starters keep working (they use names, not numbers).
- If someone else changes numbers at the same time, steps are applied in the order they were saved.
  Check the grid after saving; a step that no longer fits is listed in the box at the top.
- After a reorder the Google Sheet and Google Doc still show the old numbers, and that is fine: both are
  matched by the Pokemon's name, not its number, so an edit in an old row or line still lands on the right
  Pokemon, and numbers typed there are ignored. Pasting the new `export/sheet.csv` over the sheet (and
  renumbering the doc list) is optional tidying. What cannot be done there is adding a Pokemon on a number
  that is taken now, or renaming one that was moved - those are reported in the box at the top; do them here.
  The import remembers each sheet row and doc line per Pokemon (`data/sheet_snapshot.json`,
  `data/doc_snapshot.json`, keyed by species id), so a reorder does not make every row look changed.

## Images

Open a Pokemon and scroll to **Images**. Choose one or more pictures - concept art, sketches,
sprite drafts - add a caption if you like, and press **Upload**. PNG, JPG, WEBP and GIF work.
Big pictures are shrunk automatically; small ones such as sprites are kept exactly as they are.

The first image is shown on the Pokemon's card and at the top of its page. Any image can be
removed again with its **Remove** button. Only upload art made by us.

## New moves and abilities

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

## What happens after saving

- Everyone who opens the site sees your save right away, marked "just edited".
- Every 15 minutes the dex picks up new saves, checks them and stores them in this
  repository. `DEX.md`, `TODO.md` and the game export update with it.
- If a save cannot be used (for example a stat of 999), it is listed in a box at the top of
  the front page with the reason. Open the Pokemon, fix it, save again.
- Things that work but look off (a move that is not in the game yet, a name over 12 letters)
  appear as warnings on the Pokemon's page after the next check.
- If two people edit the same Pokemon at the same time, the later save wins. Say in the
  Discord which one you are working on.

## For the maintainer

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
