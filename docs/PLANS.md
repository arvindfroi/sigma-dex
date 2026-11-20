# Plans: roadmap, ideas for when we finalize, open questions, cartridges

What is left and in which order, ideas to look into once the dex and sprites are done, questions for the Council, and the idea of real DS cartridges.

Contents:
- [Roadmap (2026-11-12)](#roadmap-2026-11-12)
- [When we finalize the game](#when-we-finalize-the-game)
- [Open questions for the Council](#open-questions-for-the-council)
- [Physical copies (cartridges) - under consideration](#physical-copies-cartridges---under-consideration)


---

## Roadmap (2026-11-12)
*(was `docs/ROADMAP.md`)*

What is left before our dex is a playable game, sorted by when it fits best and who does it. The design of the game itself (versions, difficulty, story beats, fun moments): [Game design: making our version good and fun (2026-11-17)](STORY.md#game-design-making-our-version-good-and-fun-2026-11-17). Details: the export table in
[TRAINERS_AND_ASSETS.md](TRAINERS_AND_ASSETS.md) section 13, ideas in [When we finalize the game](#when-we-finalize-the-game).
Arvind's rule: everything in front of us before the export starts.

### Now, while the group finishes the dex and the sprites

**The group (website):** designs, dex data, sprites in the studio, claiming trainers once the Characters page opens.

**Legion (ComfyUI and LoRA training, the GPU):**
- Battle frame 2: choose the checkpoint (step 2000 was proposed) and put it in the sprite studio.
- Trainer battle sprites: model C is training; then a trainer studio on the website, built like the Pokemon studio.
- Next models, one at a time on the GPU:
  - overworld trainer sheets (12 frames of 32x32: 3 per direction; the player 24 with running), from the battle sprite,
    like the follower pipeline;
  - VS portraits (96x64 bust, 16 colours) from the battle sprite;
  - later: the intro Pokemon's hop animation, the Ho-Oh/Lugia flying frames (7 x 64x64), the cactus tree, sleeping Snorlax.

**Claude, no GPU needed:**
- Moveset autocomplete for every line (own session; proposals for review, nothing applied without a yes).
- Smart story team builder and the onboarding for claimed trainers (test branch characters-teams).
- Tools: wild-encounter table editor, map-event writer, the list of gift/static/trade species patches, a packer for the
  battle-intro archive (a/1/0/9), ndspy on the Mac.
- Switch the base to the maintained English patch (rc8 or newer) and re-check every offset we use.
- Fix Origin's leftover bugs (Goldenrod entry, S.S. Anne party) and give the message font Æ Ø æ ø.

### When the dex is done

- Claude fills the remaining game data (stats, learnsets, catch rate, exp, gender ...) by comparing with official Pokemon.
- Names final: at most 10 letters, written like official ones.
- Story roles: which of our mons takes each of the 60 essential roles (legendaries, starters, plot Pokemon).
- Shiny maker, icon palettes, cries, battle animation per mon.
- The export script: species data, sprites, icons, followers, footprints, dex text, wild tables, trainer teams (from the
  story team builder), gifts/statics/trades, story text with our names, legendary and trainer intro tables.
- Play-test in the emulator (scripted runs like the intro recordings).

### Later

- Norwegian translation (English patch tools), PokeDaisy support for our game, QoL update (nuzlocke, Move Deleter,
  PC anywhere, auto-run), one-chance legendaries and stuck quests reworked.
- Bigger: new quests and maps (needs a script assembler), wild Pokemon in the overworld, more trainer classes,
  Mega forms for our mons, a native PC version on the decompilation.

---

## When we finalize the game
*(was `docs/WHEN_WE_FINALIZE.md`)*

Things Arvind wants to look into once the dex and the sprites are done and we start putting everything into
the game (Origin HeartGold). Nothing here is decided; each item is "find out if we can, and how well".
Arvind (2026-11-11): "andre har jobbet mye med slike greier i det siste så om vi klarer det så er jo bare det gøy".

### Ideas to investigate

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

### Special pictures and story bits: Arvind's plan (2026-11-11)

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

### Origin's own problems to decide on (2026-11-12)

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

### Versions and scripted events (Arvind, 2026-11-16)

- **Two versions by difficulty.** Sabertann is the easy one, for less experienced players: no hard mode and no
  nuzlocke. Gravriel is the hard one, with two modes to pick: Nuzlocke and Hardcore Nuzlocke (healing-item rules in
  battle, forced nicknames, level cap). Not grindy: Exp Share stays on, and the usual hardcore-hack QoL comes in (Move
  Deleter, PC anywhere, auto-run). The nuzlocke code is our own (nobody owns the idea); other hacks only show how.
- **Gravriel's two modes (Arvind, 2026-11-16):** the player picks **Hard** (normal Nuzlocke) or **Hardcore**
  (Hardcore Nuzlocke) at the start. Both turn on the advanced trainer AI for every trainer (ALL). Hardcore forces the
  English patch's level cap (CAP) on, ITEMS DEFAULT and battle style SET, and allows no Bag items in battle except
  Poke Balls. Day Care may go past the cap (Arvind: fine). Dead Pokemon may be moved around in the PC, as long as
  they cannot be used: one taken into the party goes back to GRAVES when the PC closes. Built and tested:
  `scripts/origin_custom/nuzlocke/README.md`.
- **Mode flags and later pieces (2026-11-17):** the mode is event flags 0x2C4 (Hard) and 0x2C5 (Hardcore), so the
  new-game question is plain script in the intro. Gifts and static encounters do not use up an area. Forced
  nicknames, the game over screen (with the Gravriel blackout picture) and locked menu rows come with the intro,
  script and art work.
- **Game over on both screens (Arvind, 2026-11-17):** the Gravriel game over / blackout uses both DS screens, e.g.
  the top one Gravriel rising out of the water (picture or short frame animation from the intro film), the bottom
  one the message to the player and the run's memorial (deaths, the fallen by name). Each screen is 256x192; a full
  picture fits as a 256-colour bitmap or 16-colour tiles.
  Arvind: an **obituary** that rubs it in: each fallen Pokemon by nickname (with level, where and to what it died if
  we log that), the number of deaths, how far the run got (badges, play time) and **how many attempts** the player
  has made. Tone: mocking, in Gravriel's voice. Open question: a New Game wipes the save, so the attempt counter
  needs a place that survives it (ideas: a part of the save area New Game does not clear, or counting in the
  other save slot); to check when we build it. Come back to this together with the blackout art.
- **Harder trainers in Gravriel (Arvind):** some trainers get bigger teams and higher levels, and the level cap may
  be lower; but Hardcore Nuzlocke is hard already, so it must never become impossible. The two versions are two
  separate ROMs, so Gravriel can simply have its own trainer data and its own cap table (no switch in the game).
- **Special revive (Arvind, idea):** once in the Gravriel version, at a special story moment, one dead Pokemon can be
  brought back, e.g. when we meet the freed Meowthree and he thanks us by offering to heal one Pokemon. Needs a small
  script command of ours: pick one from GRAVES, clear its dead mark, give it back healed.
- **Hall of Fame on Hardcore:** maybe a special badge. Gen 4 Pokemon have ribbons on the summary page and some ribbon
  slots are unused, so a "Gravriel ribbon" with its own name and picture can work.
- **Trainer AI:** the advanced trainer AI (EN repo, from the Spanish translation) is built into rc8 for our tests and
  turned on by event flags. Gravriel can turn it on by script at game start; Sabertann leaves it off. Building the
  newest EN source (with the TRAINER AI menu row) needs the Chinese base patch "Pokémon Origin HeartGold v4.0.3
  Cn.delta", which is not public; we need it anyway to build our hack with their tools.
- **Scripted villain wipe (script only):** Origin already has 60 story battles you are allowed to lose
  (`TrainerBattle x,0,1,0` and then `CheckBattleWon`, e.g. Blue in Pewter): no blackout, the scene goes on. The
  villain gets a team far too strong; on the loss the screen fades to black with "SIGMA blacked out...", then he breaks
  the fourth wall, heals your team and mocks you (Arvind: like Thor: Ragnarok). Arvind: develop this further. A line
  idea (Arvind): "Get up, you are better than this. Need some help?" Not a priority; we work out the details later.
- **Trainer lines in battle (data only):** the trainer message bank has lines for the last Pokemon sent out (type 15),
  the last one at half HP (16) and the trainer winning (20); 71 trainers use them in Origin. **Checked 2026-11-17
  (emulator, Executive Proton = trainer 706, which has lines 15 and 16): when he sent out his last Pokemon no line
  came**, only "Proton sent out Golbat!". The half-HP line could not be tested yet (Golbat never got below half).
  So Origin's battle engine most likely ignores these lines; talking mid-battle needs Origin's own way of doing it
  (Giovanni's Mewtwo fight has lines in the middle of the battle, text bank 599: to look into) or our own code.
- **Gravriel blackout (new code):** instead of "blacked out", a picture or a short animation (10-20 frames from the
  intro film) of Gravriel rising out of the water, with a message to the player. Needs a hook in the blackout screen
  (the SoulSilver nuzlocke hack draws its own screen there). The game has no video player, so frames in a row.
- **Boss second stage:** easy as two battles in a row with a scene between; inside one battle it needs new code, see
  Meowthree below. Arvind: "we will need that" (the new-code parts).

### Meowth story idea (Arvind, 2026-11-12)

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

#### Meowth plan, round 2 (Arvind, 2026-11-12 evening)

Arvind's sketches: [the controlled form](img/meowthwo_sketch_controlled.webp) (the costumed man in the EXP harness with wires,
Persian's ghostly shape and red gem behind him) and [the costume](img/meowthwo_sketch_costume.png) (Meowth suit, Rocket
shirt and red scarf, psychic energy in his hand).

- **Names and Meowthree's final design (Arvind, 2026-11-20):** three stages, three names:
  **Meowthscot** (the costumed dude, replaces the working name "Furry Meowth"), **Meowthwo** (with the EXP harness on)
  and **Meowthree** (when he breaks free). [Meowthree's final design](img/meowthree_design.webp): a tall, slim cat-man
  standing wide, khaki fur, white eyes with yellow pupils and a calm sly smile, Meowth's coin on the forehead as a
  barred gold oval, a dark navy-purple bodysuit with gold V-shaped plates from the shoulders down the chest, gold
  shoulder caps and two gold knobs at the hips, big clawed hands and feet, and a thin tail curled behind him. No harness.
- **Meowth "dies" early.** The Meowth in the first one or two battles (Viridian Forest, Route 4) is the real Pokemon,
  no. 52, the trio's talking Meowth like in the series. After that he is gone, his death only implied (Jessie and James
  change the subject when asked). Next time the trio has **a dude dressed as Meowth** instead. Everyone thinks he is a
  gag, but he turns out to play a big role in the story.
- **The dude (Arvind):** an early teen / young adult who only does the job for the money. A bit hippie, aloof, does not
  care and takes nothing seriously, like a summer temp at a theme park: "I'm just tryna do my job". A bit out of place in
  this world. He is **added as his own Pokemon** (our own dex entry, working name "Furry Meowth" or a normal name), so
  he battles in James' team like a real mon.
- **What happens to him:** to earn extra money he signs up for Team Rocket's experiments, based on what happened to Bill
  (a human turned into a Pokemon). **No armour (Arvind):** what he wears in the sketch is a special **EXP Share
  harness** that steals EXP instead of sharing it. That is what juices him up, maybe past lv 100, and Giovanni's Persian
  keeps him in check and under Team Rocket's control.
- **Rocket reports as hints (Arvind liked this):** Origin already has Rocket reports you can read ("Keep reading?", bank
  572). We add a few about "subject 52" (a nod to Meowth's dex number), spread over the game so the reveal is built up.
  Drafts, game text in English:
  1. "New volunteer for the Bill transfer test: the part-timer in the Meowth suit. Signed without reading. Asked about
     overtime pay."
  2. "Transfer partly successful. Subject 52 shows psychic readings. Subject says this is 'kind of a lot, man'."
  3. "The EXP harness works too well. Subject 52 is past every limit. Only Persian's link keeps it under control."
  4. "Subject 52 no longer answers to its old name. We are calling the result Meowthwo."
- **Awakened attitude (Arvind):** once awakened he is stoic and cool like Mewtwo, maybe like Genji from Overwatch; a bit
  Dr. Manhattan, but he still does odd jobs from online ads.
- **How you get him:** in Origin you never catch Mewtwo. In Cerulean Cave you destroy the Master Ball Giovanni controls it
  with ("Catching a Pokemon depends on a Trainer and a Pokemon accepting each other", bank 599), and later at Indigo
  Plateau Mewtwo joins your party as a gift ("Add Mewtwo to your party?", bank 608). This fits Meowthwo: break Persian's
  hold, and he joins you because he chooses to. **Arvind's gag version:** we pay him to work for us ("I'm just tryna do my
  job"): the game asks for money before he joins (easy, the script language has money check and pay commands).
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
- **Boss in two phases:** phase 1 the harness form controlled by Giovanni's Persian (Giovanni talks during the
  battle), a scene where the harness breaks and Persian loses its hold, phase 2 the unleashed form with a legendary intro
  and its own music. A surprise and a real challenge.
- **Meowthree (Arvind, 2026-11-16):** in the boss fight Meowthwo **evolves in the middle of the battle** and is then
  called Meowthree; Arvind draws Meowthree. The theme can be evolution and human growth: humans cannot evolve, the
  EXP harness steals other mons' growth to force it, and real growth has to be earned. Giovanni's goal, one of two
  ideas (Arvind): he wants to become a "super trainer" himself (the harness on himself; in his final his own mons could
  evolve mid-battle with the same code), or he wants to use the technology on people to turn them into Pokemon, maybe
  so he can catch them. Engine facts: Origin has no in-battle Mega Evolution (Megas are held-item forms in the party,
  EN repo `work/notes/damage_calc_mechanics.md` section 6, although the battle text still has Mega Evolution lines),
  but its battle engine has handlers that change a Pokemon's form, and with it the species id (Origin's forms have their
  own ids), in the middle of a battle: Power Construct (Zygarde turns Complete below half HP and gets more max HP), Zen
  Mode, Schooling, Disguise, Ice Face. Meowthwo to Meowthree can use the same path, started by that battle's boss rule
  instead of an ability, with our own text ("What? Meowthwo is evolving!"). New code in overlay 14, like Weather Switch.
- **Forms after the story:** Meowthwo joins in the harness form; a held key item (working name "Deactivation Key")
  switches it to the unleashed form, the same way Steel Armor makes Armored Mewtwo in Origin (a held-item form). The
  harness form does not have to be Steel type like Armored Mewtwo.
- **Past lv 100, only in that one fight (Arvind):** the game stops at lv 100 (EXP tables, stat math and screens all
  assume it), but an exception for the boss alone may work: a trainer's mon gets its level from the battle data and
  never levels up, so setting the boss to e.g. lv 120 might just work. To test in the emulator: stats, the "Lv120" text,
  the EXP the player gets, and whether Origin's engine clamps it. When he joins you he is set to lv 100, since a player's
  mon above 100 would break the EXP tables. If the test fails: lv 100 with the PokeRogue-style boss rule, which gives the
  same feel.
- **Post-game restaurant:** Origin's Island Restaurant (Alto Mare islands, the trio as waiters, you choose to arrest them
  or ask Meowth's help with the Lucky Meowth God) becomes a **fast food place**. Meowth works there and
  explains why he disappeared: the real Meowth (no. 52) never died, he quit and took a fast food job. Origin's own line "You're a
  Pokemon, aren't you? You're free" turns into a joke.
- **Boss health in segments (later, new code):** like PokeRogue's bosses, the health bar is split into parts, one hit can
  never pass a part line (a stronger Sturdy, so no one-shot), and each broken part can raise its stats. **Not an
  ability** (Arvind): it is a boss rule the battle script turns on before the fight, so the mon keeps its normal ability.
  The damage cap and stat raise use the same kind of code patch as our Weather Switch test. Note: the decompiled code
  is the normal HeartGold, not Origin; Origin's battle engine (overlay 14) is new code that no decomp covers, so battle
  changes are still patches into the binary (doable, as Weather Switch showed). Map and script changes are easier; a drawn segmented bar needs
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

### Already planned for later

- More trainer classes than the game's 129 (class 130+), if we want many new ones instead of replacing: needs the class tables moved and a code patch.

- Names written like official ones ("Pikachu"), at most 10 letters; the long ones get shortened then.
- Cries: a fitting cry per mon made from official ones by body shape, height and weight; a few made by hand.
- Icon colours: each icon uses the best of the game's 3 shared icon palettes while keeping its design.
- Shiny maker on the website: make a shiny by adjusting colours easily, not pixel by pixel.
- Battle animation per mon (pick a fitting official one) and a real second battle frame (the frame 2 LoRA).
- The export to the game, once everything is in front of us ([TRAINERS_AND_ASSETS.md](TRAINERS_AND_ASSETS.md)).

---

## Open questions for the Council
*(was `docs/OPEN_QUESTIONS.md`)*

Things that came up when the Google Doc was imported on 2026-10-02 and when the dex was
compared against what the Emerald PC port can do. Delete an item once it is decided and the
species files are updated.

### Conflicts with the game engine

These were checked against the earlier GBA target, pokeemerald-expansion (see
[The game we build on](GAME_TECH.md#the-game-we-build-on)); the main target is now Origin HeartGold, so check them again against it. That base removed most of the
earlier conflicts: Fairy type, hidden abilities, the physical/special split and 846 moves /
319 abilities from generation 1-9 all exist. What is left:

1. **Rainbro is listed as "Stellar".** Stellar exists only as a Tera type, not as a type a
   Pokemon can have. What should it be?
2. **Names longer than 10 characters** (the real limit, found in the HeartGold decompilation on 2026-11-11):
   23 names, e.g. Tomaterdander (13) - to be shortened when names are finalized; new Pokemon can not get longer names.
   The three Sigmanian ones are regional variants, which show the original's name in the game
   ("Sudowoodo"), so their length is not a problem.
3. **New moves and abilities** (ones that do not exist in any official game) have to be
   programmed. For each one we need: name, type, physical/special/status, power, accuracy,
   PP, and exactly what it does. The fewer and the more precisely described, the better.

### Unclear in the doc

7. **Sigmanian Sudowoodo (#24), Sigmanian Eiscue (#32) and Sigmanian Unown (#57) are regional
   variants** of the official Pokemon (decided 2026-10-02), like Alolan Vulpix. Still open:
   Sigmanian Eiscue's second type is "?". The game export does not write regional variants yet.
8. **No types given:** Bolthook, Sigmanian Unown, Unknighted, Gentie, Cryoblade, Ciggiti, Chuchar,
   Parahaunt, Insectoid, Darkgonark. Rainbro is "Stellar", which is not usable.
9. **Unclear lines:** #58 "unknighted (unknown thunder stone?)" - does it evolve from Sigmanian Unown
   with a Thunder Stone? #100 "Maagamad/gullmire" - which name?
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
12. **Open slots** - see [TODO.md](../TODO.md).

### Project decisions

13. **Target game.** The main target is now Origin HeartGold (Nintendo DS, built on hg-engine). The
    earlier GBA plan (pokeemerald-expansion, with a possible native PC build) is no longer the focus
    (see [The game we build on](GAME_TECH.md#the-game-we-build-on)). Still open: how friends get to play it - a DS flashcart such as
    the DSpico as a gift, or the patch only (see [Physical copies (cartridges) - under consideration](#physical-copies-cartridges---under-consideration)).
14. **Our Pokemon replace existing ones in place** (changed when the target became Origin HeartGold; before that they were to be added
    next to the Hoenn dex). Each takes the species slot of a Pokemon it replaces; see
    [Replacing the whole dex: where real Pokémon still show](GAME_TECH.md#replacing-the-whole-dex-where-real-pokémon-still-show). Still open: which slots they take (pure, mixed or
    post-Champion dex).
15. **Region name** - goes in `data/config.yaml`.
16. **Leafing's values are a draft** made for the proof of concept. Review them.

---

## Physical copies (cartridges) - under consideration
*(was `docs/CARTRIDGE.md`)*

Status: **being considered, nothing decided.** The idea is to give friends the game as a
"plug and play" Christmas present on real Nintendo DS hardware. Nothing here has been bought or
tested. Checked on 2026-10-08, from reviews and articles only.

### What is possible

- A real DS or 3DS game card cannot be made for our hack. The only way to run it on real
  hardware is a **DS flashcart**: a cartridge that looks like a DS game but reads the ROM from a
  microSD card.
- Our game is a DS ROM (see [The game we build on](GAME_TECH.md#the-game-we-build-on)), so it needs a **DS-mode** flashcart. A 3DS
  runs it only in DS mode, never as a native 3DS game. A GBA cartridge is not an option.

### Candidates

| Option | What it is | For | Against / unknown |
|---|---|---|---|
| **DSpico** (LNH Team) | Open-source flashcart on the RP2040; microSD, FAT32; front-end Pico Launcher, game loader Pico Loader | Cheap (about $20 / £10 reported); open hardware and firmware, so it can be kept alive by the community; reported to work on DS, DS Lite, DSi and 3DS (DS software and DSiWare only) | Young product; reports of lockups with 64 GB and 128 GB cards (use a small FAT32 card); sources disagree on how well it works on a 3DS; no list of tested 3DS models or firmware found |
| Other DS flashcarts (R4/Acekard family and similar) | Closed or cloned cards, microSD | Widely sold; Acekard 2i and the original R4 with the Wood kernel are known to be fine | Many clones, uneven quality, some stop working after a console update; 3DS support varies per card; cheap "R4i Gold 3DS"-type clones often fail on HeartGold |
| Patch only | Give friends the patch (and optionally a blank flashcart) and let them patch their own HeartGold ROM | The clean option legally | Not plug and play |

### Things to check before buying

1. **The ROM**: that it boots on the card at all. Size is not a worry: HeartGold (USA) is
   128 MB, Origin HeartGold with the English patch about 266 MB, and our current test build
   512 MB only because the ROM build tool pads it to the maximum (512 MB is the largest a DS
   cartridge can be). A trim step in the final build brings it down to about Origin's size, and
   adding Pokemon and sprites keeps us well below the limit.
2. **HeartGold's anti-piracy checks**: on flashcarts they can give a black screen or a freeze,
   typically in the intro when the player shrinks. Not known whether hg-engine or Origin already
   removes them. If the game freezes on the card, add an anti-piracy fix step to the export.
3. **Saving**: one report of a HeartGold hack froze when loading a save on a flashcart, and
   wrong save-file sizes caused trouble. Test a full save, power off and load on the real card.
4. **Which consoles our friends have.** DS, DS Lite and DSi are the easy cases. For a 3DS, check
   the DSpico project's compatibility notes for that model and firmware.
5. **Features that need real hardware**: Pokewalker needs the infrared in the game card, so it
   will not work from a flashcart (the DSpico has no IR either). The DSpico has no save states;
   normal in-game saving works.
6. **A test run** on an actual console per model before wrapping anything.

### Rules for ourselves

- Keep it to a few copies as gifts. Never sell them and never publish the ROM.
- Even a gift card with the patched ROM on it copies Nintendo's game, also when the ROM was made
  from our own cartridge dump. The clean way: each friend owns a HeartGold cartridge; someone with
  a hacked console dumps it, applies the patch and puts the result on that friend's flashcart.
  The friend still only inserts the card.
- Ask the Origin HeartGold authors (Alex / Yannanfei TB) before sharing our patch publicly, for
  example on Discord.
- The repository stays free of ROMs and Nintendo's data. The microSD cards are prepared outside
  it.
- Credit the original authors of Origin HeartGold and the translator.

### Open

- Does the group want the gift version at all, or only the patch?
- Which card (DSpico first, since it is the one proposed).
- Who tests on which console.

### Sources

- [LON.tv: DSpico review](https://blog.lon.tv/2026/02/19/dspico-review-an-affordable-flash-cartridge-for-nintendo-ds-handhelds/)
- [omgmog: The DS Pico might be the last DS flashcart you'll ever need](https://blog.omgmog.net/post/ds-pico-flashcart/)
- [Hackster: This Is the Perfect Nintendo DS Flashcart](https://www.hackster.io/news/this-is-the-perfect-nintendo-ds-flashcart-8cf6b7868dff)
- [Notebookcheck: DSpico, the last flashcart the Nintendo DS will ever need](https://www.notebookcheck.net/DSpico-The-last-flashcart-the-Nintendo-DS-will-ever-need.1222851.0.html)
- [Time Extension: DSpico review](https://timeextension.com/reviews/dspico-this-insanely-cheap-open-source-nintendo-ds-flash-cart-is-utterly-essential)
- [GBAtemp: HeartGold freezing on flashcarts (anti-piracy)](https://gbatemp.net/threads/ghost-theme-problem.433043/post-6629770)
- [GBAtemp: HG/SS card compatibility thread](https://gbatemp.net/threads/pokemon-hs-ss-card-compatibility-thread.213309/post-2674548)
- [Retro Dodo: Origin HeartGold gets an English translation](https://retrododo.com/pokemon-origin-heartgold-finally-gets-english-translation/)
