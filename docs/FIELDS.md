# Field guide

Every species file in `data/species/` has these fields. Leave a field empty if it is not
decided yet - [TODO.md](../TODO.md) keeps track of what is missing.

## Identity

| Field | Meaning | Rules |
|---|---|---|
| `dex` | Slot in our regional dex | 1-100, unique |
| `name` | Name | Max 10 characters in the game |
| `credits.designer`, `credits.artist` | Who made it | Discord names |
| `types` | One or two types | `[Grass]` or `[Grass, Steel]` |

## Pokedex page

| Field | Meaning | Rules |
|---|---|---|
| `category` | The "Seed" in "Seed Pokemon" | Max 11 characters |
| `description` | Dex entry | Max 4 lines of about 40 characters |
| `height_m`, `weight_kg` | Size | One decimal, e.g. `0.7` and `6.9` |
| `body_color` | Color used by the dex search | red, blue, yellow, green, black, brown, purple, gray, white, pink |

## Battle data

| Field | Meaning | Rules and guidance |
|---|---|---|
| `abilities.primary` / `secondary` | Abilities | Emerald has two slots. Use existing Emerald abilities where possible |
| `abilities.hidden` | Hidden ability | Does not exist in Emerald - optional, needs extra game code |
| `base_stats` | HP, Attack, Defense, Sp. Attack, Sp. Defense, Speed | Each 1-255. Typical totals: first stage 300-320, middle 400-420, fully evolved 480-540, legendary 580-680 |
| `ev_yield` | EVs given when defeated | `{attack: 1}`. 1 point for a first stage, 2 for a middle stage, 3 for a final stage |
| `catch_rate` | How easy it is to catch | 3 legendary, 45 starters and rare, 120-190 uncommon, 255 very common |
| `base_exp` | Exp given when defeated | About 50-70 first stage, 130-150 middle, 200-240 final |
| `growth_rate` | How fast it levels | erratic, fast, medium_fast, medium_slow, slow, fluctuating. Starters use medium_slow |
| `base_friendship` | Starting friendship | 70 is standard, 35 for unfriendly ones |

## Breeding

| Field | Meaning | Rules |
|---|---|---|
| `gender` | Percent male | 0, 12.5, 25, 50, 75, 87.5, 100 or `genderless`. Starters use 87.5 |
| `egg_groups` | One or two | monster, water_1, water_2, water_3, bug, flying, field, fairy, grass, human_like, mineral, amorphous, dragon, ditto, undiscovered |
| `egg_cycles` | Hatch time | 20 is typical, 40 for rare, 120 for legendary |
| `held_items.common` / `rare` | Items wild ones hold | Optional. 50% and 5% chance |

## Evolution

`evolutions` lists what this Pokemon evolves **into** (the evolved form's file lists nothing
about where it came from). Up to 5.

```yaml
evolutions:
  - into: leafsteel      # file name of the target, without .yaml
    method: level
    level: 16
```

| `method` | Needs | Meaning |
|---|---|---|
| `level` | `level` | Reaches the level |
| `item` | `item` | Item used on it, e.g. `Thunder Stone` |
| `trade` | | Traded |
| `trade_item` | `item` | Traded while holding the item |
| `friendship`, `friendship_day`, `friendship_night` | | Levels up with high friendship (any time / day / night) |
| `level_attack_higher`, `level_attack_equal`, `level_defense_higher` | `level` | Like Tyrogue |
| `beauty` | `level` (the beauty value) | Like Feebas |
| `other` | `note` | Anything else - needs new game code, describe it in `note` |

## Moves

```yaml
learnset:
  level_up:
    - {level: 1, move: Tackle}
    - {level: 7, move: Vine Whip}
  tm_hm: [Cut, Solar Beam]
  tutor: [Body Slam]
  egg: [Leech Seed]
```

- `level_up` and `egg` may use any Emerald move. `egg` is only needed for the first stage of a line.
- `tm_hm` may only use the game's 50 TMs and 8 HMs; `tutor` only the 30 tutor moves.
- All valid names are listed in [`data/engine/gen3.yaml`](../data/engine/gen3.yaml).
- Remember that Emerald has no physical/special split: whether a move is physical or
  special depends on its **type** (Grass, Fire, Water, Electric, Ice, Psychic, Dragon and
  Dark are special, the rest physical).

## Location

```yaml
encounters:
  - {location: Route 1, method: grass, levels: 2-4, rate: 20}
```

`method` is free text for now: grass, surf, fishing, cave, gift, trade, static, ...

## Design and assets

| Field | Meaning |
|---|---|
| `design.concept` | What it is, in a sentence or two |
| `design.name_origin` | Where the name comes from |
| `design.notes` | Anything else |
| `assets.*` | Paths to files in this repo. See [ENGINE.md](ENGINE.md) for the exact sizes |
| `engine.*` | Sprite positioning details, only relevant once sprites exist |
