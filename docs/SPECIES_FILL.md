# The numbers: height, weight, body color, EV yield, catch rate, exp, growth, friendship, gender, egg groups, egg cycles

Nobody wants to work these out by hand, so `scripts/species_fill.py` fills them the way Game Freak would. It only
ever fills **empty** fields; a value a person wrote is never changed. Species without base stats get only their
height and weight; the rest waits.

**On the website:** edit a Pokemon > POKEDEX > *Catching, breeding and items* > **Fill in the empty ones for me**.
It fills only the empty fields in the form and says why for each one; change anything before you press YES. The
suggestions are remade on every sync (every 15 minutes), so after new stats or a new look text they follow.

```
.venv/bin/python scripts/species_fill.py propose          # what it would fill, and why -> proposals/species_fill.json
.venv/bin/python scripts/species_fill.py show leafaxer
.venv/bin/python scripts/species_fill.py apply --all      # fill the empty fields in data/species/
.venv/bin/python scripts/species_fill.py suggest          # -> site/species_suggestions.json (the website button)
```

## How it decides

**Legendary or not** comes from `data/legendaries.yaml` (legendary, mythical, undecided = ordinary until decided).
A Pokemon not listed there counts as legendary when it does not evolve and has a BST of 570 or more, or when its
concept says "legendary". **The whole line shares** growth rate, gender, egg groups and egg cycles; when a person
chose one of those for one Pokemon of the line, the others get the same.

Every species is compared with every official Pokemon, exactly like the moveset tool (`docs/MOVESETS.md`): stats,
types, stage, line length, evolution levels, words in its look, the designers' wishes, its archetype. Each value is
the weighted choice of the most similar ones, plus Game Freak's fixed habits:

| Field | How |
|---|---|
| EV yield | 1 point for a first stage, 2 for a middle stage, 3 for the last of three stages, 2-3 for other final or single ones (as its models), 3 for legendaries; on its highest stat, split when two stats are close |
| Catch rate | its models' value, snapped to the values the games use (255, 190, 120, 90, 75, 60, 45 ...); starters and strong three-stage lines 45, legendaries 3, earlier stages of a legendary line 45 |
| Base exp | its models' exp per stat point times its base stat total |
| Growth rate | the same for the whole line, as its models; starters Medium Slow, legendaries and strong three-stage lines Slow |
| Base friendship | its models' (newer games' 50 counts as Origin's usual 70); legendaries usually 0 |
| Gender | the same for the whole line, as its models; starters 87.5 % male; "always female/male" in the design wins; legendary lines like legendaries (mostly genderless) |
| Egg groups | the same for the whole line: its models' groups plus what it is (a turtle -> Monster, a cow -> Field, an insect -> Bug, a fish -> Water 2, a humanoid -> Human-Like, a rock or robot -> Mineral, a ghost or smoke -> Amorphous); legendary lines Undiscovered |
| Egg cycles | the same for the whole line, snapped to the games' values; starters 20, strong three-stage lines 40, legendaries 120 |
| Height | its models' height, a little more for a look that says big and less for one that says small; the whole line at once, so each evolution is at least 1.2 times as tall as the one before it |
| Weight | its models' weight for their size (weight / height squared, close to how official Pokemon scale) times its own height squared; lighter for ghosts, clouds and smoke, heavier for rock and metal; each evolution at least 1.3 times as heavy |
| Body color | the colour of its body in the look text ("a small tan turtle" -> brown, "deep blue fur" -> blue); colours of small parts (eyes, snout, spots, a helmet) do not count. Checked against the sprites: where text and sprite disagreed, Claude looked at the sprite and chose (`proposals/body_color_visual.json`, 24 species) |

**Height and weight (16 Nov 2026).** They matter for more than the Pokedex: the sprite LoRAs were trained with
"X m tall", and a big Pokemon fills more of its frame (docs/LORAS.md). Before the rule ran, the designers' own cards
in `assets/concept-art` were read (28 Pokemon had a height or weight printed there that never reached the dex;
Wreckingdrake's card says 1980 kg, kept at the website's 999.9). Where the rule did not fit the design after reading
its look and art, Claude's value is in `proposals/height_weight_review.json` (with the reason) and wins over the rule.

Not filled: **where it is found** (encounters). That depends on Origin HeartGold's maps and the story plan
(`docs/STORY_ROLES.md`), so it is decided there.

The official numbers come from PokeAPI's public data (fetched when it runs, kept in `.cache/`, nothing of it in
the repo).
