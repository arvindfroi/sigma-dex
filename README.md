# Council of the Sigmas Pokedex

The single source of truth for our fakemon region: every Pokemon, with every piece of
information the game needs, in one place.

- **[The website](https://arvindfroi.github.io/sigma-dex/)** - every Pokemon's page, stats at any level, warnings
- **[DEX.md](DEX.md)** - the whole dex at a glance
- **[TODO.md](TODO.md)** - what is still missing, per Pokemon and per area
- **[docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md)** - decisions the Council still has to make

## How it works

Each Pokemon is one small text file in [`data/species/`](data/species), for example
[`leafing.yaml`](data/species/leafing.yaml). Every file has the same fields - types, stats,
abilities, moves, evolution, dex entry, breeding data, art, and so on.
[docs/FIELDS.md](docs/FIELDS.md) explains each one.

Everything else is produced from those files automatically, every time something changes:

| Generated file | What it is |
|---|---|
| `DEX.md` | Overview table of all 100 slots |
| `TODO.md` | What is missing before the dex is complete |
| `export/dex.csv` | The whole dex as a spreadsheet |
| `export/sheet.csv` | The same, laid out for the Google Sheet people fill in |
| `export/dex.json` | The whole dex as data, for tools |
| `export/engine/` | Every Pokemon written in the C format the Emerald PC port uses |
| `site/index.html` | The website: every Pokemon's page, stats at any level, warnings, what is missing |

Never edit the generated files by hand - they get overwritten.

## Contributing

- **Without GitHub:** type into the Google Sheet and look at the result on the website.
  See [docs/SHEET.md](docs/SHEET.md).
- **With GitHub:** edit a species file, open a pull request, wait for the green check, merge.
  See [CONTRIBUTING.md](CONTRIBUTING.md).

Both end up in the same species files. Concept art and decisions still buried in Discord
can be pulled out with [docs/DISCORD.md](docs/DISCORD.md).

## The game

The plan is a ROM hack on a PC port of Pokemon Emerald. [docs/ENGINE.md](docs/ENGINE.md)
describes how that game stores a Pokemon, what limits it sets (10-letter names, no Fairy
type, ...) and how our files map onto it.

## What is and is not in this repository

Only our own original work lives here: names, designs, stats, text and art we made. No ROMs,
no game code and no Nintendo / Game Freak graphics or sound, and none may be added. The
hack itself is developed separately and should only ever be shared as a patch.

Pokemon is a trademark of Nintendo / Creatures Inc. / GAME FREAK inc. This is a
non-commercial fan project and is not affiliated with or endorsed by them.
