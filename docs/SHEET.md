# Filling in the dex with the Google Sheet

The easiest way to contribute is the edit form on the website ([WEBSITE.md](WEBSITE.md)).
The sheet is the alternative for filling in many Pokemon at once.

Two things exist for people who never want to touch GitHub:

- **The Google Sheet** - where you type.
- **The website** (`site/index.html`) - where you see the result: every Pokemon's dex page,
  its stats at any level, which moves it knows at that level, what damage it takes, its
  evolution, any warnings, and what is still missing. No game needed.

## How to use the sheet

One row per dex slot, one column per piece of information (42 columns - everything a
Pokemon has except images). Row 1 is the column name, row 2 a hint about what to write.
Type in a cell; every 15 minutes the dex picks it up, checks it and updates the website.

- **Only cells you change are applied.** The sync remembers what the sheet looked like last
  time, so an old value sitting in the sheet never overwrites something that was edited on
  the website. The other way round does not happen automatically: an edit made on the
  website does not appear in the sheet. The website always shows the current state.
- **Emptying a cell** removes that value.
- **To add a Pokemon**, write its name in an open slot's row.
- **Never change the `Dex #` column.** It is how rows are matched.
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
| everything else | Plain text or a number. [FIELDS.md](FIELDS.md) explains each field and its allowed values |

## When something is wrong

- A row that cannot be used (a letter where a number belongs, a growth rate that does not
  exist, ...) is skipped **as a whole**, and the reason appears in a box at the top of the
  website. Fix the cell and it goes through on the next sync.
- Things that work but look off (a move that does not exist in the game yet, a name longer than
  12 letters) show up as **warnings** on that Pokemon's page.

## Setting it up (once)

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
