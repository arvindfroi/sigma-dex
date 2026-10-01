# Editing the dex on the website

**https://arvindfroi.github.io/sigma-dex/** - no account, no GitHub, works on a phone.

## How to contribute

1. Click a Pokemon, then **Edit**. Or click an **open slot** to add a new Pokemon.
2. Fill in what you know. Leave the rest empty - a half-finished Pokemon is fine.
3. At the bottom, write your name and the **edit key** (pinned in the Discord). The site
   remembers both on your device.
4. **Save.** You land on the Pokemon's page with your changes: its dex entry, its stats at
   any level, which moves it knows at that level, the damage it takes, and the list of what
   is still missing. That page is how you test a Pokemon without playing the game.

Everything about a Pokemon can be entered: name, types, credits, dex entry, size, abilities,
base stats, EV yield, catch rate, exp, growth rate, friendship, gender, egg groups, held
items, evolutions, level-up / TM / HM / tutor / egg moves, where it is found, and design
notes. Moves and abilities suggest the ones that exist in Emerald while you type.

Not on the website: art and sprites. Post concept art in the Discord for now.

## What happens after saving

- Everyone who opens the site sees your save right away, marked "just edited".
- Every 15 minutes the dex picks up new saves, checks them and stores them in this
  repository. `DEX.md`, `TODO.md` and the game export update with it.
- If a save cannot be used (for example a stat of 999), it is listed in a box at the top of
  the front page with the reason. Open the Pokemon, fix it, save again.
- Things that work but look off (a move that is not in Emerald, a name over 10 letters)
  appear as warnings on the Pokemon's page after the next check.
- If two people edit the same Pokemon at the same time, the later save wins. Say in the
  Discord which one you are working on.

## For the maintainer

- Saves go to a small database (Supabase project `sigma-dex`, free plan). Each save is one
  row holding the whole Pokemon; rows are never changed, so the table is the edit history.
  The layout is in [`supabase/schema.sql`](../supabase/schema.sql).
- `scripts/import_web.py` applies rows newer than `data/web_edits_cursor.txt`. Art paths and
  sprite details are always kept from the species file, never taken from the website.
- **The edit key** stops strangers from saving. Only its hash is stored in the database.
  To change it or remove it, run the statements at the bottom of `supabase/schema.sql` in
  the Supabase SQL editor. Change it if it leaks.
- **Undoing a bad edit:** restore the species file with git (or just fix it on the website).
  Older saves are never re-applied, so a restored file stays restored.
- To sync right now instead of waiting: GitHub > **Actions > Dex > Run workflow**.
