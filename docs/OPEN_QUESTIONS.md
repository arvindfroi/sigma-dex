# Open questions for the Council

Things that came up when the Google Doc was imported on 2026-10-02 and when the dex was
compared against what the Emerald PC port can do. Delete an item once it is decided and the
species files are updated.

## Conflicts with the game engine

The base is now pokeemerald-expansion (see [ENGINE.md](ENGINE.md)), which removed most of the
earlier conflicts: Fairy type, hidden abilities, the physical/special split and 846 moves /
319 abilities from generation 1-9 all exist. What is left:

1. **Rainbro is listed as "Stellar".** Stellar exists only as a Tera type, not as a type a
   Pokemon can have. What should it be?
2. **Names longer than 12 characters:** Bulgarian Unown (15).
3. **New moves and abilities** (ones that do not exist in any official game) have to be
   programmed. For each one we need: name, type, physical/special/status, power, accuracy,
   PP, and exactly what it does. The fewer and the more precisely described, the better.

## Unclear in the doc

7. **Eiscue (#32)** is the name of an official Pokemon, and its second type is "?".
   Rename it? Is it meant as a regional form?
8. **No types given:** Bolthook, Bulgarian Unown, United, Gentie, Cryoblade, Ciggiti, Chuchar,
   Parahaunt, Insectoid, Darkgonark.
9. **Working titles?** "bulgarian unown" (#57) and "united" (#58) look like placeholders.
10. **Evolution lines without a stated method.** These look like families but the doc gives
    no level or item, so no evolution is recorded yet:
    - Erobi > Harpie > Smeatherace
    - Wump > Twemp > Florantula
    - Cowfin > Mooceon
    - Nucloid > Nuclobyl
    - Saucerl > Abyssys > Octopearl
    - Skiirtle > McSkiirtle
    - Balleisk > Greation > Ultragon
    - Are Bolthook, Hairyen, Panzerien, Gentie, Yanklet ... standalone?
11. **Assumption made during import:** where the doc says e.g. "Leafsteel (Lv.16)", it was
    recorded as "the previous entry evolves into this one at level 16". Wispole evolves into
    Galfrogtom with a Thunder Stone on the same assumption. Check
    [DEX.md](../DEX.md) for mistakes.
12. **31 open slots** - see [TODO.md](../TODO.md).

## Project decisions

13. **Native PC build or GBA ROM?** pokeemerald-expansion builds a GBA ROM, which runs on
    any computer or phone in an emulator. A native PC program of it does not exist ready-made
    (see [ENGINE.md](ENGINE.md)). The Pokemon data, moves, maps and scripts are the same
    work either way, so this can be decided later.
14. **Replace or add?** Do our 100 replace the Hoenn dex, or get added next to the 386
    existing Pokemon?
15. **Region name** - goes in `data/config.yaml`.
16. **Leafing's values are a draft** made for the proof of concept. Review them.
