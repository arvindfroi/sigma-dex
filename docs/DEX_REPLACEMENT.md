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

- Title screen (HeartGold: Ho-Oh).
- The intro (the professor shows a Pokémon).
- Ruins of Alph sliding puzzles (Kabuto, Omanyte, Aerodactyl, Ho-Oh panels).
- Big overworld figures in cutscenes (the legendaries in the towers and the Whirl Islands).
- Static overworld Pokémon (Sudowoodo, Snorlax, Lapras, Gyarados) use the following-Pokémon
  sprites, so they follow from the follower sprites of our mons.
- Pokédex footprints (16x16, one per species).
- Shiny palettes.

## 3. Sound

Every species has its own cry; changing the pictures keeps the old cry. Options: new cries
(synthesised or AI sound), existing cries changed (pitch, speed, mixed), or keep them for now.

## 4. Mechanics tied to a species

- Species with forms: Unown (28), Rotom, Deoxys, Giratina, Shaymin, Arceus and Origin's later-gen
  forms. Simplest: our mons go into slots without forms or events.
- Event species: the Spiky-eared Pichu event, the Arceus event, Pokéwalker species.
- Pokéwalker, Pal Park and GTS connect outside the game: ignored.

## 5. Choices for the group

- Which slots our mons take (pure, mixed or post-Champion dex is not decided yet). The legendary
  and story Pokémon are where a mixed dex matters most: either a Sigma mon with a fitting role
  (a sea god for Lugia, three beasts for the beasts) or the real one kept until there is a design.
- Who redraws the title screen, intro and Alph puzzles.
