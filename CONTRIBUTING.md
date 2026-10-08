# Contributing

The repository is the one place where dex information lives. Discord is for discussing;
once something is decided, it goes here. If it is not in the repo, it is not decided.

No GitHub account? Edit on the website instead: [docs/WEBSITE.md](docs/WEBSITE.md).

## Filling in or changing a Pokemon (in the browser)

1. Open the Pokemon's file in [`data/species/`](data/species) and click the pencil icon.
2. Fill in fields. Put the value after the colon and leave the `#` comments alone:
   `catch_rate: 45           # 3 (legendary) to 255 (very easy)`
3. Click **Commit changes**, choose **Create a new branch and start a pull request**.
4. Wait for the **Dex** check. A red cross means something is wrong - click **Details** to
   see exactly which field and why. Fix it by editing the file again on the same branch.
5. When it is green and the group is happy, merge.

After merging, `DEX.md`, `TODO.md`, `export/` and the website update themselves within a minute.

## Adding a new Pokemon

Pick an open slot from [TODO.md](TODO.md). Either open a **New Pokemon** issue to propose it,
or copy an existing file in `data/species/`, rename it (lowercase, `-` instead of spaces,
e.g. `icy-freeze.yaml`), and change `dex` and `name`. With Python installed you can
instead run `python scripts/new_species.py 17 "Name" --types Grass Steel`.

The file name is the Pokemon's permanent ID - evolutions point to it (`into: leafsteel`).
If a Pokemon is renamed, change `name` inside the file and leave the file name alone.

## Art

Put concept art in `assets/concept-art/` named after the species file (`leafing.png`), then
set `concept_art: assets/concept-art/leafing.png` in the species file. Sprites are made in the
sprite studio on the website ([docs/STUDIO.md](docs/STUDIO.md)); approved DS sprites land in
`assets/sprites-ds/<species>/` by themselves. Only upload art made by us.

## Rules of thumb

- One pull request per Pokemon or evolution line - small changes are easy to review.
- Anything that needs a group decision goes in an issue or
  [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md), not in a private chat.
- Stick to moves and abilities that already exist in the game where possible. The check warns about
  unknown ones; a truly new one must be described in `data/custom_moves.yaml` or
  `data/custom_abilities.yaml`, and somebody has to program it later.
- Never edit `DEX.md`, `TODO.md` or anything in `export/` or `site/`.

## Running the checks on your own computer (optional)

```bash
pip install -r requirements.txt
python scripts/validate.py
python scripts/build.py
```
