# Letting Claude fill in a Pokemon

Working out 20 level-up moves, 50 TMs, six base stats, catch rate, egg groups and growth rate is
the boring part of designing a Pokemon. On the website, a designer can open **Edit > Let Claude
fill in the rest**, tick the box and write a few lines about how it should play ("a slow tank
that walls physical attackers, should learn Rock Slide"). Claude then fills in everything that is
still empty, to fit the design.

Why not a button that does it instantly on the website: a convincing moveset needs judgment
(what the creature is, its family, what fits its concept, what is balanced next to the rest of
the dex). A fixed rule ("pick moves of its type by level") gives every Pokemon the same generic
list. So it is done by Claude, in batches, by whoever maintains the repo.

## For the maintainer: running it

Open Claude Code in this repository and say:

> Fill in the Pokemon that asked for it - follow docs/CLAUDE_FILL.md.

## For Claude: the rules

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
   - **TM/HM**: only from the game's TM/HM list, what the body and type make sensible.
   - About the lists (checked 2026-10-08): `data/engine/expansion.yaml` comes from the earlier
     GBA target, but its moves and abilities are also in hg-engine, the base of Origin HeartGold
     (only spellings differ, e.g. Vise Grip / ViceGrip). The TM/HM list is not the same: the file
     has Emerald's 50 TMs and 8 HMs, HeartGold has 92 TMs and 8 HMs, and Origin HeartGold may have
     changed them. Until Origin's list is read from the game, a TM move outside Emerald's list is
     fine as long as the move exists (`validate.py` warns about it, which can be ignored for now);
     the Origin export will check TMs against the real list.
   - **Egg moves** for first stages; **tutor** moves are optional.
   - Category, height, weight, body colour, catch rate, base exp, growth rate, friendship,
     gender, egg groups, egg cycles, EV yield: as official Pokemon of that kind and stage have.
   - **Pokedex entry**: only if empty; at most 4 short lines, in the tone of the games.
   - Do **not** fill in where it is found (`encounters`) - that depends on the game's maps - or
     the art.
5. Record what was filled in: `design.filled_by_claude` lists the fields (e.g. `[base stats,
   level-up moves, TM/HM moves, catch rate]`). The website shows that list on the Pokemon's page
   so people know what to review.
6. Run `python scripts/validate.py` and `python scripts/build.py`, then commit with a message that
   names the Pokemon.

The species files are edited directly (not through the website), so the website's history does
not show these changes; the commit does.
