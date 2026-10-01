# Filling in the dex without GitHub

Two things exist for people who never want to touch GitHub:

- **The Google Sheet** - where you type.
- **The website** (`site/index.html`) - where you see the result: every Pokemon's dex page,
  its stats at any level, which moves it knows at that level, what damage it takes, its
  evolution, any warnings, and what is still missing. No game needed.

## How to use the sheet

One row per dex slot. Type in a cell; once an hour the dex picks it up, checks it and
updates the website.

- **An empty cell changes nothing.** To change a value, type the new one. (Removing a value
  completely has to be done in the species file on GitHub.)
- **To add a Pokemon**, write its name in an open slot's row.
- **Never change the `dex` column.** It is how rows are matched.
- The columns `id`, `bst` and `complete_percent` are calculated - typing in them does nothing.

| Column | How to write it |
|---|---|
| `type_1`, `type_2` | `Grass`, `Steel` |
| `ability_1`, `ability_2`, `hidden_ability` | `Overgrow` |
| `hp` ... `speed` | Base stats, 1-255 |
| `evolves_from`, `evo_condition` | On the **evolved** Pokemon's row: `Leafing` and `Lv 16`. Other conditions: `Thunder Stone`, `Trade`, `Trade holding Metal Coat`, `Friendship`, `Friendship (night)`, `Other: explain it here` |
| `height_m`, `weight_kg` | `0.5`, `5.8` |
| `ev_yield` | `1 attack` or `1 attack, 1 speed` |
| `gender` | Percent male: `87.5`, `50`, `0`, ... or `genderless` |
| `egg_group_1`, `egg_group_2` | `field`, `grass` |
| `level_up_moves` | `Tackle (1), Leer (1), Absorb (6)` - the level in brackets |
| `tm_hm_moves`, `tutor_moves`, `egg_moves` | `Cut, Solar Beam, Toxic` |
| `encounters` | `Route 1 \| grass \| 2-4 \| 20; Sigma Cave \| cave \| 8-10 \| 5` (place, method, levels, percent) |
| everything else | Plain text or a number. [FIELDS.md](FIELDS.md) explains each field and its allowed values |

## When something is wrong

- A row that cannot be used (a letter where a number belongs, a growth rate that does not
  exist, ...) is skipped **as a whole**, and the reason appears in a box at the top of the
  website. Fix the cell and it goes through on the next sync.
- Things that work but look off (a move that does not exist in Emerald, a name longer than
  10 letters) show up as **warnings** on that Pokemon's page.

## Setting it up (once)

1. Open `export/dex.csv` from this repository and import it into the Google Sheet
   (**File > Import > Upload**, "Replace current sheet"). That gives the sheet the right
   columns and everything already known.
2. **Share > General access > Anyone with the link: Viewer.** (Editing stays limited to the
   people you invite.) The sync reads the sheet through this link.
3. Put both links in `data/config.yaml`:

   ```yaml
   sheet_url: https://docs.google.com/spreadsheets/d/SHEET_ID/edit
   sheet_csv_url: https://docs.google.com/spreadsheets/d/SHEET_ID/export?format=csv&gid=0
   ```

   `gid` is the number after `gid=` in the address bar when the right tab is open.
4. To sync immediately instead of waiting for the hour: on GitHub, **Actions > Dex > Run workflow**.

The sheet and the species files are the same data. The sheet is for the everyday filling
in; the files additionally hold art paths and sprite details.
