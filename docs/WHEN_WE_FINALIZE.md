# When we finalize the game

Things Arvind wants to look into once the dex and the sprites are done and we start putting everything into
the game (Origin HeartGold). Nothing here is decided; each item is "find out if we can, and how well".
Arvind (2026-11-11): "andre har jobbet mye med slike greier i det siste så om vi klarer det så er jo bare det gøy".

## Ideas to investigate

1. **Wild Pokemon in the overworld.** Wild Pokemon you can see walking around on the map, instead of only
   random encounters in the grass. We already make an overworld sprite (the follower, 8 frames) for every mon,
   so the pictures exist; the question is the game code (spawning, movement, starting the battle).
2. **Better shading.** New improvements to how the sprites are shaded (light and shadow), for all our mons.
3. **One screen play with [PokeDaisy](https://github.com/lidor30/pokedaisy).** PokeDaisy is an open source
   (GPL-3.0) Game Boy to DS player for Android handhelds and phones, with two screens or one, and a live companion
   (party, bag, map, matchups, Pokedex, guide) that reads the game while you play. It already supports Origin HeartGold;
   we have to adapt it to ours before we share the game with the group: find out what it needs to support ours (our dex, names and sprites in its companion) so people can play on one screen.
4. **Our own quests and side quests.** New story events, quests and side quests made by us (scripts, maps, NPCs,
   rewards). Find out how far we can get in Origin, and whether it is easier on a decompiled base (pret pokeheartgold).
5. **Real time multiplayer.** Playing together live (seeing each other, trading, battling) beyond the DS's own
   wireless features. Others have recently done this for similar games; find out what exists and what it would take.

## Already planned for later

- More trainer classes than the game's 129 (class 130+), if we want many new ones instead of replacing: needs the class tables moved and a code patch.

- Names written like official ones ("Pikachu"), at most 10 letters; the long ones get shortened then.
- Cries: a fitting cry per mon made from official ones by body shape, height and weight; a few made by hand.
- Icon colours: each icon uses the best of the game's 3 shared icon palettes while keeping its design.
- Shiny maker on the website: make a shiny by adjusting colours easily, not pixel by pixel.
- Battle animation per mon (pick a fitting official one) and a real second battle frame (the frame 2 LoRA).
- The export to the game, once everything is in front of us ([TRAINERS_AND_ASSETS.md](TRAINERS_AND_ASSETS.md)).
