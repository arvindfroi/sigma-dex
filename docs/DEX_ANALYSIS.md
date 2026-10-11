# Dex analysis: what Sigma Dex is missing (2026-10-08)

State: 99 of 151 slots filled, 96 with a type. Compared with all 9 official generations,
using pokeemerald-expansion 1.17.1 (modern types, Fairy applied backwards).
Pictures for sharing: `img/dex-types-per-gen.png`, `img/dex-trends.png`, `img/dex-roles.png`.

## How it was measured
- Official numbers: parsed from `~/sigma-expansion/src/data/pokemon/species_info/` and grouped by national dex number
  (Gen 1 = 1-151, Gen 2 = 152-251 and so on). Base forms only, 1011 species.
- Sigma numbers: `data/species/*.yaml`.
- Not reliable yet: evolution lines (only 16 links are recorded), base stats (60 of 99 have them),
  and every role marked partly or unknown (most species have no description or concept text).

## Monotypes
| | Mono share |
|---|--:|
| Gen 1 | 57 % |
| Gen 2 | 51 % |
| Gen 3 | 53 % |
| Gen 4 | 51 % |
| Gen 5 | 54 % |
| Gen 6 | 40 % |
| Gen 7 | 37 % |
| Gen 8 | 54 % |
| Gen 9 | 35 % |
| **Sigma** | **22 %** (21 of 96) |

- 8 types have no monotype at all: Fighting, Psychic, Poison, Ground, Flying, Dragon, Dark, Steel. Gen 1-3 had 17 mono Psychic, 13 Poison, 11 Fighting, 10 Ground.
- Only 1 pure Normal (Gen 1-3 had 37). Normal mono is the early-route backbone.
- To reach the Gen 9 level (~36 %, 54 mono in 151) 33 of the 55 remaining slots must be monotype. 45 % needs 47. 50 % needs all 55.
- Cheaper option: some existing dual types could lose their second type (the designers decide).

## Type share, generation by generation
See `img/dex-types-per-gen.png`. Closest official generation by type share: **Gen 9** (distance 42), then Gen 8 (51). Kanto is the furthest (85).

Where Sigma differs most from the old generations (Gen 1-3 average share, in % of Pokemon with the type):
- Too few: Flying 7 (13), Psychic 6 (11), Normal 11 (14), Fighting 5 (5 in Gen 1-3, 7 overall).
- Too many: Ghost 11 (3), Dark 12 (4), Steel 9 (3), Fairy 8 (2), Rock 11 (8), Poison 14 (11), Ice 7 (4).
- 30 % of Sigma Pokemon have Dark, Steel or Fairy (Gen 1-3: 3-16 %, Gen 8-9: 23-28 %). The dex plays like a modern one.

## Other trends
- Strong non-legendaries (BST 540+): 9 of the 60 with stats (Cryoblade 605, Insectoid 580, Chuchar 574, Verrith 570, Crappy Meal 560, Parahaunt 556, Obsidog utvikling 555, Darkgonark 550, Panzerien 540). Gen 1-3 together had 11 in 384 Pokemon.
- Legendaries: Sandrema (mythic), Bergflabbser, Maagamad (both BST 680), Sabertann, Gravriel and one unmade, about 6 of 151 (Gen 1: 5, Gen 2: 6, Gen 3: 10).
- Repeated dual pairs (3 each): Poison/Rock, Flying/Normal, Dark/Water, Bug/Dragon, Fairy/Poison, Psychic/Water.
- Rainbro is Stellar, which is not a species type in the game. Fleuroom utvikling, Gentie and Flurina have no type yet.
- Evolution structure (single-stage, two-stage, three-stage share) cannot be compared yet: most evolutions are not entered.

## Roles every generation has
See `img/dex-roles.png`.
- Have: three starters, early bird (Erobi), early bug (Wump), Geodude (Leadling), Diglett (Bulbtle), Gastly (Ciggiti), branching (Wispole), mythic (Sandrema).
- Partly: legendary trio (Sabertann, Gravriel + 1 to make), pseudo-legendary, fossil, early Normal route Pokemon, bat, fighter, cute Fairy/Normal. Unconfirmed guesses, check with the designers.
- Missing: electric mascot (Zapana is an eel), early Psychic, Magikarp-like, baby Pokemon.

## Suggested use of the 52 open slots (108-142 are 35 in a row)
Priority is monotypes first, then types and roles:
1. Mono Normal route Pokemon (2-3 lines): rodent, dog or pig.
2. Mono Psychic early line (Abra, Ralts) and a mono Fighting line.
3. Mono Flying (a second bird line) and mono Poison, Ground, Dragon, Steel, Dark.
4. Electric mono mascot.
5. Magikarp-like fish and a baby Pokemon.
6. Third legendary of the trio.
