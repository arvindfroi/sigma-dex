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

- **VS portraits** (battle intro of gym leaders, rival, Elite Four, champion): `a/1/0/9`, one 96x64 close-up bust per character, 16 colours (4 files: palette, picture, cell, animation, plus 3 for the banner background), drawn only for this effect, not cut from the battle sprite. 16 leaders (members 63-126), 5 Elite Four/champion (131-150, with name plates 47-54), the player boy/girl (207-214). Origin redrew several (Misty, Elite Four slots, the player). Each replaced character needs one.

## Origin's own problems to decide on (2026-11-12)

- **Still broken after the English patch rc8** (the rest of the loss-freezes and the double-battle cursor are fixed there):
  the Goldenrod entry flag bug, the S.S. Anne party (their fix exists but is switched off), and a few unconfirmed crashes.
  Most are one-flag or one-jump script fixes we can make ourselves.
- **One-chance legendaries by design:** Lugia, Raikou, the lake trio, Dialga/Palkia, Giratina, Arceus (catching, beating or
  fleeing hides them; only a loss lets you retry), plus order-dependent losses (Bruno's Pewter challenge, TM14 Blizzard,
  the Azure Flute after the Hall of Fame). Our mons take these roles, so we decide whether they stay one-chance.
  Arvind (2026-11-12) leans to the middle way: one chance, but with a clear warning before, and a second chance after
  the Hall of Fame.
- **Quests you can get stuck in** (Arvind: "det er jo ikke gøy hvis det skal være softlocked i oppdrag"): the S.S. Anne
  honey and salt order, the Celadon stolen Gloom, the Route 7 bicycle, the Mahogany Rocket PC password, the Fan Club,
  Route 3 Ralts. Fix with clearer hints and by removing the dead ends when we rewrite the story.
- **QoL to add** (a typical update): nuzlocke mode, Move Deleter, PC anywhere, auto-run. Already there: Move Reminder,
  EV allocator, Exp/Shiny/Catching charms, chain bonuses, level cap / items / Exp Share options and the Advanced trainer AI
  (we use it). Origin has no wild Pokemon walking in the overworld (encounters in the grass as usual).
- **Mega forms for our mons:** possible as a held-item form (like Charizardite, Steel Armor, Ninja Scroll).

## Meowth story idea (Arvind, 2026-11-12)

Meowth is a real person in a Meowth costume (comic relief); later Team Rocket experiments on him and he becomes a
human/Pokemon hybrid ("Meowthwo"), used as a weapon that Giovanni's Persian controls; it goes too far, he runs amok or
escapes, and becomes a boss. What Origin already has (msg banks, docs/trainers.md):
- Meowth talks in ~110 lines over 24 text banks (441, 585, 582, 313 most), always next to Jessie and James. He is not a
  trainer: he is a Pokemon in James' team (lv 5-25) in every one of their ~12 battles, which are tag battles (Jessie and
  James each have their own team, side by side; you often have a partner too).
- Mewtwo's arc is almost this story: Team Rocket made it, Giovanni used it as his weapon (Cerulean Cave, lv 100 in his
  team), it hurt the player and left its energy in their body (Sabrina, Misty, Brock scenes), it comes back in the
  final fight against Giovanni (a copy from the past made with Arceus and Dialga), and Mewtwo even fights as its own
  "trainer" in a multi battle at Indigo Plateau (#1013). Since our mons take every story role, Meowthwo can take
  Mewtwo's role. Rocket's "enhancement experiments" on Pokemon and on people, Persian statues with glowing eyes (the
  Mahogany base) and Giovanni's Persian (bank 441) are there too.
- Possible with what the game has: text (easy), a Pokemon fighting as a trainer (done in Origin), battles chained in a
  script (Giovanni then his Beedrill), a legendary intro and music keyed by species id (table in arm9, patch to our id),
  a fleeing/roaming encounter (the roamer system, keyed by species), a catch after the boss.
- Hard parts: Meowth still travels with Jessie and James after the main story (hospital, Island Restaurant scenes), so
  those scenes need a new reason or he comes back; a costumed person needs new overworld and battle pictures (and stays
  a "Pokemon" in James' team unless we give him his own trainer, which takes Jessie's or James' slot: at most two
  opponents per battle); real boss mechanics (several health bars, extra moves per turn) need new code; and ~17 text
  banks name Mewtwo.
- Checked later the same day: Meowth (Jessie, James) and Mewtwo never share a scene, so the illusion holds. The game shows
  Mewtwo's birth (bank 546: it wakes in Dr. Fuji's lab, talks by telepathy, Amber's clone story) and Giovanni says it went
  berserk, killed the scientists and escaped (bank 599). In its multi battle at Indigo Plateau Mewtwo is the player's
  partner (its own "trainer", team = itself, lv 95) against Cyrus and Charon. Armored Mewtwo is form 3 (Psychic/Steel,
  hidden ability Berserk), made by holding Steel Armor (an item ball on Cinnabar Island); no trainer uses it, so a
  "controlled by Persian" form of Meowthwo can work the same way (an item, or the form set in the trainer's team).
  Boss tools Origin already uses: trainer lines in the middle of a battle (Giovanni's Mewtwo fight, bank 599),
  battles in a row (Giovanni, then his Beedrill alone; the eight Silver Conference challengers), Giovanni and his copy as
  two opponents at once, and Pokemon that go berserk out of battle (the Beedrill grooming scene, bank 492). No battle in
  Origin has more than six Pokemon per trainer, several health bars or a stage that changes the rules.

### Meowth plan, round 2 (Arvind, 2026-11-12 evening)

Arvind's sketches: [the controlled form](img/meowthwo_sketch_controlled.webp) (the costumed man in armour with wires,
Persian's ghostly shape and red gem behind him) and [the costume](img/meowthwo_sketch_costume.png) (Meowth suit, Rocket
shirt and red scarf, psychic energy in his hand).

- **Meowth "dies" early.** The Meowth in the first battles (Viridian Forest, Route 4) is the real one, the trio's third
  member who talks and acts like in the series. After the first battles he is gone, only implied (Jessie and James change
  the subject when asked). From then on the trio uses a **stand-in**: some dude in a cheap Meowth suit (comic: wrong
  colours, cannot do the voice). In battle he can still be the "Pokemon" in James' team; the cheapest way is the costume
  species' own battle sprite with other colours (a palette form, like a shiny), so no new drawing is needed.
- **Rocket reports as hints (Arvind liked this, write them):** Origin already has Rocket reports you can read ("Keep
  reading?", bank 572). We add a few about "test subject 52" (Meowth's dex number), spread over the game so the reveal
  is built up. Drafts, game text in English:
  1. "Subject 52 arrived today. Uncooperative. Talks back. Bit two of our staff."
  2. "Psychic response in subject 52 is rising. It keeps asking for its friends."
  3. "The armour holds subject 52 in place. Persian's link is the only thing it obeys."
  4. "Subject 52 no longer answers to its old name. We are calling the result M2-52."
- **Then the reveal: Meowthwo.** Origin's Rocket reports you can read ("Keep reading?", bank 572) can foreshadow it
  (a test subject numbered 52, Meowth's dex number). Meowthwo takes Mewtwo's whole role: the birth scene in the lab
  (bank 546: Dr. Fuji, Blaine, Green/Red, an explosion; it is overworld sprites plus text, so the text is an easy rewrite
  and the actors need script work), Giovanni's weapon, going berserk and escaping (bank 599), fighting next to the
  player at Indigo Plateau.
- **Mewtwo's overworld figure is its follower sprite.** Every scene where Mewtwo stands on the map uses the normal
  Mewtwo follower sprite: the lab birth scene (event file 68, with Red, Blaine, Rocket staff and the emergency doors),
  Indigo Plateau with Palkia and Giratina (82), the Giovanni scene (214) and the final at the Pokemon League (277, next
  to Giovanni, Arceus, Dialga and Beedrill). So if Meowthwo takes Mewtwo's dex slot, all four scenes show Meowthwo
  without script work.
- **Boss in two phases:** phase 1 the armoured form controlled by Giovanni's Persian (Giovanni talks during the
  battle), a scene where the armour cracks and Persian loses its hold, phase 2 the unleashed form with a legendary intro
  and its own music. A surprise and a real challenge.
- **Forms after the story:** Meowthwo is caught in the armoured form; a held key item (working name "Deactivation Key")
  switches it to the unleashed form, the same way Steel Armor makes Armored Mewtwo in Origin (a held-item form).
- **Post-game restaurant:** Origin's Island Restaurant (Alto Mare islands, the trio as waiters, you choose to arrest them
  or ask Meowth's help with the Lucky Meowth God) becomes a **fast food place**. Meowth works there and
  explains where he went. It is the **real** Meowth who ends up there (not the stand-in). Origin's own line "You're a
  Pokemon, aren't you? You're free" turns into a joke.
- **Boss health in segments (later, new code):** like PokeRogue's bosses, the health bar is split into parts, one hit can
  never pass a part line (a stronger Sturdy, so no one-shot), and each broken part can raise its stats. **Not an
  ability** (Arvind): it is a boss rule the battle script turns on before the fight, so the mon keeps its normal ability.
  The damage cap and stat raise use the same kind of code patch as our Weather Switch test; a drawn segmented bar needs
  battle screen code, so a first version shows a message per broken part.
- **Facts checked:** Giovanni's final in Origin is three battles in a row: Giovanni alone (Arceus, Dialga and 4 more),
  then a double battle against Giovanni and his past copy at once (you alone against both, the copy has Mewtwo), then
  his very first Pokemon, Beedrill, alone (lv 100, "one last stand"). The berserk Beedrill in Celadon is a different,
  unrelated scene (a groomer's Rocket product). Only one battle in Origin changes with the player's starter: Silver in
  Dragon's Den, where only his ace changes (Meganium, Typhlosion or Feraligatr; Crobat and Gengar stay). Arvind: keep
  the note on that battle, no slot system for now.
- **Giovanni's final, maybe rewritten (Arvind):** build it more around Meowthwo. Present and past Giovanni can stay;
  the past one could be the one with Persian (the Persian that controls Meowthwo). Beedrill's "last stand" is his first
  Pokemon; we have plenty of our own mons to pick from for that role and for the Celadon Beedrill. Decide later.

## Already planned for later

- More trainer classes than the game's 129 (class 130+), if we want many new ones instead of replacing: needs the class tables moved and a code patch.

- Names written like official ones ("Pikachu"), at most 10 letters; the long ones get shortened then.
- Cries: a fitting cry per mon made from official ones by body shape, height and weight; a few made by hand.
- Icon colours: each icon uses the best of the game's 3 shared icon palettes while keeping its design.
- Shiny maker on the website: make a shiny by adjusting colours easily, not pixel by pixel.
- Battle animation per mon (pick a fitting official one) and a real second battle frame (the frame 2 LoRA).
- The export to the game, once everything is in front of us ([TRAINERS_AND_ASSETS.md](TRAINERS_AND_ASSETS.md)).
