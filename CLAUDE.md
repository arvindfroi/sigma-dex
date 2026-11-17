# Map of this repository (for Claude)

The Sigma Dex: the Council of the Sigmas' own Pokemon, put into Origin HeartGold (Nintendo DS) in place of the
official ones. People edit on the website; this repo is the single source of truth. Read this page first, then only
the section you need.

## Where to read what

| Topic | Page and section |
|---|---|
| What a species field means, allowed values | [DEX_DATA.md › Field guide](docs/DEX_DATA.md#field-guide) |
| The website, the Google Sheet, how edits flow in | [DEX_DATA.md › Editing the dex on the website](docs/DEX_DATA.md#editing-the-dex-on-the-website), [› Google Sheet](docs/DEX_DATA.md#filling-in-the-dex-with-the-google-sheet) |
| Rules when Claude fills a Pokemon; people vs Claude | [DEX_DATA.md › Letting Claude fill in a Pokemon](docs/DEX_DATA.md#letting-claude-fill-in-a-pokemon) |
| Height, weight, catch rate ... filled like Game Freak | [DEX_DATA.md › The numbers](docs/DEX_DATA.md#the-numbers-height-weight-body-color-ev-yield-catch-rate-exp-growth-friendship-gender-egg-groups-egg-cycles) |
| Moveset autocomplete | [DEX_DATA.md › Movesets](docs/DEX_DATA.md#movesets-how-the-autocomplete-decides) |
| What the dex lacks (types, roles); Discord export; backups | [DEX_DATA.md](docs/DEX_DATA.md) (last four sections) |
| Sprite style, sprite studio, sprite formats, ComfyUI | [ART.md](docs/ART.md) |
| Shiny and cry makers | [ART.md › Shinies](docs/ART.md#shinies), [› Cries](docs/ART.md#cries) |
| LoRA training log (rounds, traps, lessons) | [LORAS.md](docs/LORAS.md) |
| Trainer sprites, every asset the game needs, export readiness | [TRAINERS_AND_ASSETS.md](docs/TRAINERS_AND_ASSETS.md) (13 numbered sections) |
| Where real Pokemon still show after the swap | [GAME_TECH.md › Replacing the whole dex](docs/GAME_TECH.md#replacing-the-whole-dex-where-real-pokémon-still-show) |
| New abilities/moves as code (overlay patch), nuzlocke | [GAME_TECH.md › New abilities and moves](docs/GAME_TECH.md#new-abilities-and-moves-in-origin-heartgold) |
| Moving Origin onto the C decomp (study) | [GAME_TECH.md › decomp](docs/GAME_TECH.md#origin-heartgold-on-the-c-decompilation-feasibility-study-2026-11-11) |
| Old GBA target (pokeemerald-expansion), history only | [GAME_TECH.md › The game we build on](docs/GAME_TECH.md#the-game-we-build-on), [› Building (GBA)](docs/GAME_TECH.md#building-the-game-gba-target) |
| Game design, versions, difficulty | [STORY.md › Game design](docs/STORY.md#game-design-making-our-version-good-and-fun-2026-11-17) |
| Which of our mons take which story role | [STORY.md › Story roles](docs/STORY.md#story-roles-which-pokémon-origin-heartgolds-story-needs-and-who-from-our-dex-takes-them) |
| Characters people claim, gyms (Fairy gym) | [STORY.md › Characters](docs/STORY.md#characters-with-a-type-for-claiming) |
| Sabertann/Gravriel in the Ho-Oh/Lugia scenes | [STORY.md › Ho-Oh and Lugia scenes](docs/STORY.md#ho-oh-and-lugia-scenes-what-origin-does-and-how-we-replace-them) |
| Steven and Cynthia as returning champions (Norwegian) | [STORY.md › Steven og Cynthia](docs/STORY.md#steven-og-cynthia-champions-som-kommer-tilbake-som-en-overraskelse) |
| Roadmap, ideas for finalizing, open questions, cartridges | [PLANS.md](docs/PLANS.md) |
| Opening movie and legend cutscene tools (long build log) | [scripts/origin_intro/README.md](scripts/origin_intro/README.md) |
| Nuzlocke patch | [scripts/origin_custom/nuzlocke/README.md](scripts/origin_custom/nuzlocke/README.md) |
| Hand-written GBA game code | [game/README.md](game/README.md) |

Each merged section starts with *(was `docs/OLD_NAME.md`)*, so an old name from a memory or a commit message can be
found with a search.

## Layout

- `data/species/*.yaml`: one file per Pokemon, the source of truth. Other data in `data/` (characters, requests,
  custom abilities/moves, lines, music tables).
- `assets/`: concept art, DS sprites (`sprites-ds/`), shinies, cries.
- `scripts/`: every tool. Main ones: `build.py` (DEX.md, TODO.md, export/), `build_site.py` (site/index.html from
  `site_template.html`), `validate.py`, `import_web.py` (website edits), `moveset_fill.py`, `species_fill.py`,
  `footprints.py`, `sprites.py`; `origin_intro/` (opening movie, legend scenes, custom sprites), `origin_custom/`
  (code patches, Fairy gym, nuzlocke), `music/` (S-theme pipeline, runs on the Legion).
- `supabase/`: the website's database schema.
- `site/`: the website (GitHub Pages).

## Generated files: never edit by hand

`DEX.md`, `TODO.md`, `export/*`, `site/index.html` (edit `scripts/site_template.html`, then run
`scripts/build_site.py`), `proposals/*` (from `moveset_fill.py` / `species_fill.py`). The GitHub workflow pulls website
edits every 15 minutes and commits "Sync edits from the website".

## Working rules

- Python: `~/sigma-toolchain/venv312/bin/python` (numpy, desmume ...).
- No Nintendo data in the repo: no ROM pieces, official sprites or footprints. Refer to them by id (e.g. `hgss:138`).
- Origin HeartGold work and ROMs live outside the repo in `~/sigma-origin/`.
- Docs are written in plain English; Arvind's own plans may be in Norwegian.
- New docs: add a section to the page whose topic it is, not a new file, and add a row to the table above.
