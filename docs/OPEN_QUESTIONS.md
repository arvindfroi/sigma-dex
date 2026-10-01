# Open questions for the Council

Things that came up when the Google Doc was imported on 2026-10-02 and when the dex was
compared against what the Emerald PC port can do. Delete an item once it is decided and the
species files are updated.

## Conflicts with the game engine

1. **Fairy type does not exist in Emerald.** Nukfae, Toxiren, Anjane, Janenon and Sandrema
   are Fairy. Either add the Fairy type to the game (new type, its matchups, an icon -
   doable, known procedure) or give them other types.
2. **Rainbro is listed as "Stellar".** That is not a type a Pokemon can have. What should it be?
3. **Names longer than 10 characters:** Smeatherace (11), Giga-Circuit (12), Bulgarian Unown (15).
   Shorten them, or accept the work of raising the limit in the game.
4. **Hidden abilities do not exist in Emerald** (the spreadsheet has a column for them).
   Two normal ability slots only, unless the game is extended.
5. **No physical/special split in Emerald.** Whether a move is physical or special depends on
   its type. This affects how stats should be spread (a Grass attacker wants Sp. Attack).
   Keep it, or add the split to the game?
6. **Only Emerald's 354 moves and 77 abilities exist.** Every newer or invented move/ability
   has to be programmed. Decide how many custom ones we are willing to build.

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

13. **Which PC port?** All three use the same data format, so the dex does not depend on it:
    `fuddlesworth/pokeemerald-native` (Windows, Linux, macOS), `NTx86/pokeemerald-sdl2pc`
    (the original; Windows, Linux), `gradenGnostic/pokeemerald-multiplatform` (also Android).
14. **Replace or add?** Do our 100 replace the Hoenn dex, or get added next to the 386
    existing Pokemon?
15. **Region name** - goes in `data/config.yaml`.
16. **Leafing's values are a draft** made for the proof of concept. Review them.
