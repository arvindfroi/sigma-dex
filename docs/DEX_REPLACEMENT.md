# Replacing the whole dex: where real Pokémon still show

Our mons go into Origin HeartGold **in place**: each one takes the slot (species number) of a
Pokémon it replaces. Everything that gives, shows, checks or battles with that species number then
uses our mon by itself: starters, the Kanto prologue (Pikachu, slot 25: tested with Bugmight on
2026-10-04), gifts, trades, wild encounters, trainers, static encounters, the Pokédex, the PC and
following Pokémon. This list is what that does **not** cover. Nothing here has to be solved now; it
is handled when it comes up.

Checked on 2026-10-05 against Origin HeartGold v4.0.3 + English patch rc3 (its own text and data,
read locally; nothing of it is in this repo).

## 1. Text

6925 lines in 384 text banks name a species (outside the species-name banks). Most named: Ho-Oh
205, Entei 201, Meowth 200, Suicune 190, Charmander 111, Gyarados 99, Mew 95, Lugia 95, Pikachu 93,
Unown 90, Raikou 89, Mewtwo 85, Arceus 84, Slowpoke 82, Celebi 80, Venusaur 77, Gloom 72,
Swablu 69, Magikarp 69, Eevee 63, Totodile 58, Lapras 57, Clefairy 55, Manaphy 54, Marill 52.

- **By script:** every old name becomes the new one (a name map from the slots we fill). Pokédex
  entries (bank 791) are replaced by ours.
- **By hand, where the story needs one particular Pokémon:**
  - Slowpoke Well and Team Rocket cutting Slowpoke tails (Azalea Town, Slowpoke Well).
  - The three legendary beasts and the Burned Tower; Eusine chasing Suicune (Ecruteak, many routes).
  - Ho-Oh / Bell Tower and Lugia / Whirl Islands, the Kimono Girls (with the Eevee evolutions).
  - The Red Gyarados at Lake of Rage.
  - Unown and the Ruins of Alph (researchers, Unown Report).
  - Sudowoodo on Route 36, the sleeping Snorlax, the Lapras in Union Cave on Fridays.
  - Celebi and Arceus events, Origin's extra legendary events (Kyogre, Palkia, Giratina, Manaphy, ...).
  - Trainer lines that name their party ("You're up first, Lucario!", bank 587): they must match
    the parties we give.
  - Lines in Origin's Kanto prologue that name Pikachu.

## 2. Pictures that are not the usual sprites

- Title screen: a **3D model** of Ho-Oh with animations (`a/0/4/6` members 20-29; Origin only
  changed the logo and backgrounds). Replacing it needs a 3D model; keeping Ho-Oh or hiding the
  model behind a drawn background is far easier.
- The intro (the professor shows a Pokémon).
- Ruins of Alph sliding puzzles (Kabuto, Omanyte, Aerodactyl, Ho-Oh panels).
- Overworld Pokémon on the maps (checked 2026-10-08 in Origin's map data, `a/0/3/2`):
  - **1544 objects use the normal follower sprite** of their species (the beasts in the Burned
    Tower, the birds, Mewtwo, Dialga/Palkia/Giratina, the Regis, Celebi, Shaymin, Kimono Girl
    Eeveelutions, Pokémon standing next to trainers, ...). They show our mon by themselves once it
    has a follower sprite. Origin moved most story Pokémon over to these; vanilla HeartGold used
    separate "static" copies.
  - **73 objects still use a separate sprite file** that must be drawn on its own (or the slot left
    alone): the Sudowoodo tree (Route 36), sleeping Snorlax (Route 12 + one cave), Lapras (11
    places, Union Cave), the Red Gyarados (Lake of Rage), tailless Slowpoke (7), the big Ho-Oh
    (Bell Tower roof) and big Lugia (Whirl Islands), the 5 Rotom appliances, and "static" copies of
    Clefairy (Mt. Moon dance), Miltank (farm), Machoke, Ampharos (lighthouse), Aipom, Kyogre,
    Jigglypuff, Abra, Dratini, Dodrio, Blissey, Diglett, Slowpoke, Slowbro, Psyduck, Poliwrath,
    Meowth, Oddish, Machop, Farfetch'd and Zubat. Same format as follower sprites.
- The Clear Bell / Lugia cutscenes (Origin keeps them in full): the bird is its own sprite,
  `HOU_OBJ01` / `LUG_OBJ01` (`a/0/8/1` members 210/211): 7 frames of 64x64, seen from the front
  while it flaps and lands, drawn to fill the whole frame (so it looks much bigger than the follower
  sprite), and shown with a bigger display mode. The code lowers it from the sky, flaps it and plays
  the cry from the species slot. The 3D models there are bells, leaves/waves and a light ring, not
  Pokémon. So a new bird needs 7 new frames, no 3D work.
- The opening movie (before the title) has its own animated Ho-Oh sprite (`a/2/6/2` members
  23-30), which Origin did not change.
- In Origin, Sudowoodo is not battled at all (it runs off after being watered), Ho-Oh is a gift
  (level 95) and Lugia and Snorlax are battles. All of them take the species number from the script,
  so the battle or gift becomes our mon by itself.
- **MUST FIX before the export (Arvind, 2026-10-18): menu icons and their palettes.** In the game every icon uses
  one of three shared 16-colour palettes (the same for all Pokémon); the studio's icons keep their own colours, so at
  export each icon is mapped to the nearest colours of one palette, and a wrong palette looks bad (Leafing on Pikachu's
  yellow palette came out olive and muddy in the 17 Oct test). The export must choose the best of the three palettes
  per mon (the one that keeps its colours closest), map the icon to it with care (keep the outline and shading), and
  write the choice into the palette table. Found on 17 Oct (`~/sigma-origin/lw/build_lw.py`): Origin reads
  `data/pokeicon.narc` (two icons per species at 7+2s and 8+2s, 8x8 tiles, its own palettes in member 0); the palette
  per species is a u8 table in `arm9.bin` at 0xFF7FC (needs a fresh boot to show, not a savestate). Better icons
  could also come from letting people pick the palette in the studio and showing the icon in the game's colours there.
- Pokédex footprints (16x16, one per species).
- Shiny palettes.

## 3. Sound

Every species has its own cry; changing the pictures keeps the old cry. Options: new cries
(synthesised or AI sound), existing cries changed (pitch, speed, mixed), or keep them for now.

## 4. Mechanics tied to a species

- Species with forms: Unown (28), Rotom, Deoxys, Giratina, Shaymin, Arceus and Origin's later-gen
  forms. Simplest: our mons go into slots without forms or events.
- **Our own forms (2026-10-20):** species files can now hold `forms` (docs/FIELDS.md): looks-only forms, forms with
  their own types/stats/abilities, and forms that change during play, each with a plain `how`. At export each needs a
  way in Origin: looks-only forms as extra sprites chosen by the game's form number; battle forms as their own species
  entries in Origin's form table (Origin already has later-gen forms; how it stores them is not checked yet); forms that
  switch by item, place, time or in battle need a trigger, possibly code (docs/ORIGIN_CUSTOM_CODE.md). To be worked out
  per form when the first ones are filled in.
- Event species: the Spiky-eared Pichu event, the Arceus event, Pokéwalker species.
- Pokéwalker, Pal Park and GTS connect outside the game: ignored.

### Slots our mons never take (unless on purpose)

The game runs special code for these species numbers, so a mon put there would get it too:

| Slot | Species | What the game does |
|---|---|---|
| 201 | Unown | 28 forms chosen at random; Ruins of Alph and the Unown Report |
| 327 | Spinda | paints random spots on top of the sprite |
| 351 | Castform | changes form with the weather |
| 386 | Deoxys | 4 forms |
| 412, 413 | Burmy, Wormadam | cloak forms from where they last battled |
| 421 | Cherrim | changes form in sun |
| 422, 423 | Shellos, Gastrodon | east and west sea forms |
| 479 | Rotom | 6 appliance forms |
| 487 | Giratina | Origin form with the Griseous Orb |
| 492 | Shaymin | Sky form, turns back at night or when frozen |
| 493 | Arceus | 17 type forms from plates |
| 172 | Pichu | the Spiky-eared Pichu event |

Origin also adds later species with forms (seasons, regional forms, Vivillon, Minior, ...); the
export script must check each slot for forms before using it.

In the training data the same species are trimmed to one picture each (one Unown, one Arceus, no
Gigantamax), so they do not dominate what the LoRAs learn.

## 5. Choices for the group

- Which slots our mons take (pure, mixed or post-Champion dex is not decided yet). The legendary
  and story Pokémon are where a mixed dex matters most: either a Sigma mon with a fitting role
  (a sea god for Lugia, three beasts for the beasts) or the real one kept until there is a design.
- Who redraws the title screen, intro and Alph puzzles.
- Our legendary trio fits Origin's own weather-trio story (checked 2026-10-08): Red Orb → Groudon
  (lava pool under Mt. Moon), Blue Orb → Kyogre (Seafoam Islands, Reversal Cave), Jade Orb →
  Rayquaza (Sky Pillar Peak, Four Island), the Embedded Tower, Prof. Oak telling the myth of
  Rayquaza calming the other two, and Team Rocket stealing them. Bergflabbser (Water/Ground,
  Drizzle) in slot 382, the drought one in 383 and Maagamad (Weather Switch) in 384 would take over
  all of it. Still needed: the myth lines rewritten by hand, Weather Switch and Oily Arsenal
  programmed (Origin has no source code), and a check that Primal Reversion / Mega Rayquaza cannot
  trigger in those slots. This is part of Origin's late-game Team Rocket story (Saffron and the
  Pokémon League taken over); Executive Ariana uses a level 100 Rayquaza with Delta Stream and
  Dragon Ascent at the League, so her party must be edited to fit Maagamad.
