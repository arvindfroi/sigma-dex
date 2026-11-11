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

6. **A Norwegian translation.** The English translation project of Origin
   ([originheartgold/origin-heart-gold-EN-translation](https://github.com/originheartgold/origin-heart-gold-EN-translation),
   Apache-2.0) keeps every text bank as JSON and has tools that extract, check (text box widths) and rebuild the text,
   plus a style guide and AI-first-draft workflow. With those, all ~67,000 strings could be done in one go.
   The game's character table has Æ Ø Å æ ø å (pret pokeheartgold `tools/msgenc/charmap.txt`); check the font draws them.

## Special pictures and story bits: Arvind's plan (2026-11-11)

- **Pikachu-style static object** (12 frames): the extra frames are the follower with both feet planted. Either ignore
  them, or keep follower generations where both feet happen to be planted and use those.
- **Red Gyarados role:** the object is the same drawing as the normal Gyarados follower, recoloured (plus a little
  water splash), so ours is our follower with a special palette.
- **Sudowoodo's tree:** Claude redraws it as a cactus when the time comes, and in the game the characters remark that
  a cactus here is out of place and lazy game design (a little fourth-wall joke).
- **Lapras ferry:** Arvind draws a water variation of one of our existing mons and it goes through the follower pipeline.
- **Sleeping Snorlax (one 64x64 picture):** a custom job for Claude.
- **Ho-Oh and Lugia flying frames (7 x 64x64):** a special job, maybe with another image model. The descent scenes are
  script commands (camera moves, Clear Bell animation, "bird final approach", Lugia's eye glimmer, waves/leaves effect;
  pret `include/scrcmd.h`, `src/field/legend_cutscene_camera.c`, graphics in `files/demo/legend`): timing, camera, text
  and the picture used are easy to change; colours and effect graphics are files we can edit; the motion itself is code
  (a patch on Origin, plain C on the decompilation).
- **Oak's intro Pokemon:** its own small animated sprite (`a/1/2/0`, 3 cells, a 24-step animation), not the follower: after a white "poof" it pops in and hops beside Oak. Job for later: make a hopping, lively animation for the mon we put there.
- **Chatot-style recorded cry:** remind Arvind when we get there. PokeDaisy has no microphone support yet; suggested to
  them in https://github.com/lidor30/pokedaisy/discussions/643 (2026-11-11). Doing it ourselves in their app would be
  roughly 1-3 days (Android microphone permission, capture audio, feed it to melonDS' mic input, a setting and testing).

- **VS portraits** (battle intro of gym leaders, rival, Elite Four, champion): `a/1/0/9`, one 64x64 close-up bust per character (4 files: palette, picture, cell, animation), drawn only for this effect, not cut from the battle sprite. 16 leaders (members 63-126), 5 Elite Four/champion (131-150, with name plates 47-54), the player boy/girl (207-214). Origin redrew several (Misty, Elite Four slots, the player). Each replaced character needs one.

## Already planned for later

- More trainer classes than the game's 129 (class 130+), if we want many new ones instead of replacing: needs the class tables moved and a code patch.

- Names written like official ones ("Pikachu"), at most 10 letters; the long ones get shortened then.
- Cries: a fitting cry per mon made from official ones by body shape, height and weight; a few made by hand.
- Icon colours: each icon uses the best of the game's 3 shared icon palettes while keeping its design.
- Shiny maker on the website: make a shiny by adjusting colours easily, not pixel by pixel.
- Battle animation per mon (pick a fitting official one) and a real second battle frame (the frame 2 LoRA).
- The export to the game, once everything is in front of us ([TRAINERS_AND_ASSETS.md](TRAINERS_AND_ASSETS.md)).
