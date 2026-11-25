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
  brought back, e.g. when a character we helped thanks us by offering to heal one Pokemon. Needs a small
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
- **Boss second stage:** easy as two battles in a row with a scene between; inside one battle it needs new code (details
  in the private story notes). Arvind: "we will need that" (the new-code parts).

### Story notes kept private

Some story plans (a boss, its twist and the scenes around it) are kept out of this public repo on purpose,
so the group gets to be surprised. Arvind and Claude keep them.

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
