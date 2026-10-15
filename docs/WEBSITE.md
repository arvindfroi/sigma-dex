# Editing the dex on the website

**https://arvindfroi.github.io/sigma-dex/** - no account, no GitHub, works on a phone.

## How to contribute

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
   **SPRITES** (the sprite studio, see [STUDIO.md](STUDIO.md)) and **MORE**. Pointing at an
   ability (or tapping it) shows what it does in the dialog box.
4. Press **EDIT**. The top screen stays and follows the changes; the bottom screen becomes the
   form with the tabs BASICS, SKILLS, MOVES, POKEDEX and MORE. Base stats have a bar to drag, a
   number to type and arrows for steps of 5, with the total and what it compares to. The box at the
   bottom lists what changed ("Save the changes? ATTACK 65->80") and asks **YES** / **NO**.
5. **+ ADD A POKEMON** (under the list) adds a new one on the first open number; the number can be
   changed in the form. Open slots are listed under the filter "Open slots".

Do not want to work out moves and numbers? In the edit form's BASICS tab, tick **Let Claude fill
in what is missing** and describe how it should play. See [CLAUDE_FILL.md](CLAUDE_FILL.md).

New moves and abilities, the type balance, Lost and found and changing dex numbers are under
**MORE**.

## Progress and requests

**PROGRESS** shows how far the dex has come: designed, playable and sprites, eight badges (goals
for the whole group: first 25, half the dex, the full dex, 50 playable, all playable, 10 sprites,
all have stats, type balance), the types the dex needs most, the Pokemon that miss only one thing
before they are playable, and the open slots. Everything is counted from the dex itself.

**REQUESTS** is a board with four columns: WISHES, THE GAME NEEDS, BEING MADE and DONE. Anyone can
add a wish (+ ADD A REQUEST) and move a card along with its arrows. The cards the team writes
(what the story needs, from [STORY_ROLES.md](STORY_ROLES.md)) are in `data/requests.yaml`; cards
added or moved on the website are rows of kind `request` in `species_edits` (the newest row of a
card wins) and stay in the database: `scripts/import_web.py` skips them. Saving a card needs the
migration `supabase/migrations/2026-10-15_requests.sql`.

## Pictures

Open a Pokemon. Copy a picture and **paste it anywhere on its page** (Ctrl+V, Cmd+V on a Mac), or
drag it onto the box in the **ART** tab, or choose files there and press **Upload** (a caption is
optional). PNG, JPG, WEBP and GIF work. Big pictures are shrunk automatically. Sprites are made in
the **SPRITES** tab, not uploaded here.

The approved DS sprite (or else the first picture) is shown on the Pokemon's card and at the top of its page. Any image can be
removed again with its **Remove** button. Only upload art made by us.

## The list and the builder (Showdown style)

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

## Removing a Pokemon

Open the Pokemon, press **Edit**, and open **Remove this Pokemon from the dex** at the bottom. Type
its name to confirm and press the button. Its pictures are moved to **Lost and found** first (so
they can be given to another Pokemon), then the removal is saved. Within about 15 minutes the
import (`scripts/import_web.py`, `delete_species`) deletes its species file and sprite folders and
drops evolutions of other Pokemon into it. A starter (`starters` in `data/config.yaml`) cannot be
removed; the import reports it at the top of the front page. Nothing is truly gone: the file is
in git history and the removal is a row in `species_edits` (data `{"deleted": true}`), so it can
be restored. Its number becomes an open slot.

## Lost and found, and pictures on the wrong Pokemon

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
