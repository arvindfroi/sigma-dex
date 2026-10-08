# Council of the Sigmas Pokedex

The single source of truth for our fakemon region: every Pokemon, with every piece of
information the game needs, in one place.

- **[The website](https://arvindfroi.github.io/sigma-dex/)** - see every Pokemon and **edit it right there**
- **[DEX.md](DEX.md)** - the whole dex at a glance
- **[TODO.md](TODO.md)** - what is still missing, per Pokemon and per area
- **[docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md)** - decisions the Council still has to make

## How it works

Each Pokemon is one small text file in [`data/species/`](data/species), for example
[`leafing.yaml`](data/species/leafing.yaml). Every file has the same fields - types, stats,
abilities, moves, evolution, dex entry, breeding data, art, and so on.
[docs/FIELDS.md](docs/FIELDS.md) explains each one.

Everything else is produced from those files automatically, every time something changes:

| File or folder | What it is |
|---|---|
| `DEX.md` | Overview table of all 151 slots |
| `TODO.md` | What is missing before the dex is complete |
| `export/dex.csv` | The whole dex as a spreadsheet |
| `export/sheet.csv` | The same, laid out for the Google Sheet people fill in |
| `export/dex.json` | The whole dex as data, for tools |
| `export/expansion/` | The Pokemon that are ready, written as game code for the earlier GBA target (pokeemerald-expansion), plus automated checks for them |
| `game/` | Hand-written game code for the GBA target: new moves, new abilities and their tests (not generated) |
| `site/index.html` | The website: every Pokemon's page, stats at any level, warnings, what is missing |

Never edit the generated files by hand - they get overwritten.

## Contributing

- **On the website (easiest):** click a Pokemon, press Edit, save. No account needed.
  See [docs/WEBSITE.md](docs/WEBSITE.md).
- **In the Google Sheet:** good for filling in many Pokemon at once.
  See [docs/SHEET.md](docs/SHEET.md).
- **In the Google Doc:** the numbered list of names and types. New lines and changed lines
  are picked up automatically (name, types, and "Lv 16"-style evolutions). Lines are matched by name,
  so the numbers in the doc may be out of date after Pokemon were renumbered on the website; they are never applied.
- **With GitHub:** edit a species file, open a pull request, wait for the green check, merge.
  See [CONTRIBUTING.md](CONTRIBUTING.md).

All of them end up in the same species files, within about 15 minutes. Concept art and decisions still buried in Discord
can be pulled out with [docs/DISCORD.md](docs/DISCORD.md).

## The game

The main target is **Origin HeartGold**, a Nintendo DS hack built on hg-engine. Our Pokemon go in
"in place": each one takes the species slot of a Pokemon it replaces, so everything that uses that
species number (starters, gifts, wild encounters, trainers, the Pokedex) uses ours.
[docs/DEX_REPLACEMENT.md](docs/DEX_REPLACEMENT.md) lists what that does not cover. The export that
writes our Pokemon into Origin HeartGold is not in this repository yet. Giving friends a physical
copy on a DS flashcart (DSpico and others) is being considered: [docs/CARTRIDGE.md](docs/CARTRIDGE.md).

The earlier plan, a ROM hack on pokeemerald-expansion (Pokemon Emerald, GBA), is no longer the
focus, but its export and tests are still in the repository. See [docs/ENGINE.md](docs/ENGINE.md) and
[docs/BUILDING.md](docs/BUILDING.md).

## Sprites

The website's sprite studio makes DS (Gen 4) sprites: 80x80 front and back and a 32x32 menu icon,
drawn by an image model on our PC from the group's concept art. You can then draw on them in a
pixel editor or ask the AI for changes. Approved sprites are stored in `assets/sprites-ds/`. See
[docs/STUDIO.md](docs/STUDIO.md), [docs/SPRITE_STYLE.md](docs/SPRITE_STYLE.md),
[docs/COMFYUI.md](docs/COMFYUI.md) and [docs/LORAS.md](docs/LORAS.md). The website's **Sprites** tab
shows what exists.

## What is and is not in this repository

Only our own original work lives here: names, designs, stats, text and art we made. No ROMs,
no game code and no Nintendo / Game Freak graphics or sound, and none may be added. The
hack itself is developed separately and should only ever be shared as a patch.

Pokemon is a trademark of Nintendo / Creatures Inc. / GAME FREAK inc. This is a
non-commercial fan project and is not affiliated with or endorsed by them.
