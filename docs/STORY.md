# Story and game design: roles, characters, legends and plans for scenes

What the game should feel like, which of our mons take which story role, the characters people claim, the Ho-Oh/Lugia scenes with Sabertann and Gravriel, and the detailed plans for single story pieces.

Contents:
- [Game design: making our version good and fun (2026-11-17)](#game-design-making-our-version-good-and-fun-2026-11-17)
- [Story roles: which Pokémon Origin HeartGold's story needs, and who from our dex takes them](#story-roles-which-pokémon-origin-heartgolds-story-needs-and-who-from-our-dex-takes-them)
- [Characters with a type (for claiming)](#characters-with-a-type-for-claiming)
- [Ho-Oh and Lugia scenes: what Origin does and how we replace them](#ho-oh-and-lugia-scenes-what-origin-does-and-how-we-replace-them)
- [Steven og Cynthia: champions som kommer tilbake som en overraskelse](#steven-og-cynthia-champions-som-kommer-tilbake-som-en-overraskelse)
- [Gravriel: slik gjør vi ham enda bedre](#gravriel-slik-gjør-vi-ham-enda-bedre)


---

## Game design: making our version good and fun (2026-11-17)
*(was `docs/GAME_DESIGN.md`)*

This page gathers the design of the playable game in one place: what Arvind decided, what Claude proposes (marked
**Proposal**), and what is still open (**Open**). Details stay in their own pages: versions, nuzlocke and scripted
events in [When we finalize the game](PLANS.md#when-we-finalize-the-game), story roles in [Story roles: which Pokémon Origin HeartGold's story needs, and who from our dex takes them](#story-roles-which-pokémon-origin-heartgolds-story-needs-and-who-from-our-dex-takes-them), trainers in
[Characters with a type (for claiming)](#characters-with-a-type-for-claiming), custom code in [New abilities and moves in Origin HeartGold](GAME_TECH.md#new-abilities-and-moves-in-origin-heartgold), the order of work in
[Roadmap (2026-11-12)](PLANS.md#roadmap-2026-11-12).

### 1. Pillars: what the game should feel like

1. **A new region dex, Gen 5 style.** Only our mons until the main story is over; the official ones come back after
   (decided 2026-11-11). Every wild encounter is something the player has never seen.
2. **Evolution and growing up is the theme.** Humans cannot evolve; Team Rocket's EXP harness steals growth to force
   it; real growth has to be earned (decided 2026-11-16). Meowthwo becomes Meowthree in the middle of the boss fight.
3. **Two ways to play, chosen by the cartridge.** Sabertann is the standard game, Gravriel the hard one (decided).
4. **Never grindy, never unfair.** Hard comes from smarter trainers, rules and caps, not from hours of levelling.
   Exp Share stays on. "Hardcore is already hard, it must not become impossible" (Arvind).
5. **Funny and a bit cheeky.** Fourth-wall jokes (the cactus tree, the villain who heals you and mocks you, Gravriel's
   obituary that rubs it in, Meowth's fast food job).

### 2. The two versions

| | Sabertann | Gravriel |
|---|---|---|
| For | everyone: the standard game | players who want a challenge |
| Modes | one (normal) | Hard (Nuzlocke) or Hardcore (Hardcore Nuzlocke), picked at New Game |
| Trainer AI | the hack's own | advanced AI for every trainer (built, tested) |
| Trainers | normal teams | some bigger teams and higher levels, tuned with the cap (decided, to tune) |
| Items in battle | normal | Hard: no revives; Hardcore: no Bag items except Balls (built) |
| Level cap | off by default | Hardcore: forced on (built); maybe lower (open) |
| Losing | normal blackout | Gravriel picture on both screens + obituary (planned, needs the art) |
| Special | | one special revive event, e.g. from the freed Meowthree (idea) |
| Mascot / legend | Sabertann takes Ho-Oh's role | Gravriel takes Lugia's role |

**Proposal: version exclusives.** A handful of our lines appear in only one version (like Red/Blue), so trading
between the two matters. Pick them by theme: calm, friendly lines in Sabertann, fierce or spooky ones in Gravriel.
About 8-12 lines each is the classic size. Arvind has his own shortlist; decided when the dex is final.

**Sabertann is the one you graduate from (Arvind, 2026-11-17):** it is the standard game and teaches it; then you
move on to the real challenge in Gravriel. No extra graduation reward: Sabertann's version exclusives are reason
enough (Arvind).

### 3. Difficulty curve

- **Level cap (Arvind, 2026-11-17):** Hard uses the standard cap (the gym leader's level); Hardcore maybe the
  standard cap **minus 1 or 2**, so you are always a little underlevelled. The cap is a ceiling, not a gift: after a
  boss the cap rises, but the team still has to earn the levels on the way to the next boss.
- **Trainers' IVs, EVs and natures:** Origin has them per trainer Pokemon (party record: an IV level that is scaled to
  0-31, six EV bytes up to 252 each, the total not limited to 510, a nature or one made from the personality, plus
  ability, item and four moves; HP IVs follow the level because of a bug in the hack). So Gravriel's harder trainers
  can have real competitive spreads; the story team builder should fill these too.
  **Does Origin use them? Yes, for the important fights** (counted in the trainer list, 3,891 trainer Pokemon): Elite
  Four and Champions 60/60 with EVs, a set nature and IV 30; gym leaders 139 of 173; Rocket bosses and executives
  221 of 271; rivals 28 of 86; ordinary trainers only 597 of 2,949. IVs rise with the game: 0-6 early, 12-18 in the
  middle, 24-30 late. Our teams can follow the same pattern and adjust it where needed (Arvind). Within a team
  Origin almost always gives every Pokemon the same IV level (920 teams); only 36 teams differ, mostly an ace or
  the newest catch one step higher or lower. **Decided (Arvind, 2026-11-17): opponents' IVs are automatic and exactly
  as in Origin** ("vi gjør det bare slik spillet gjør"): each battle gets the IV level of Origin's own team for that
  battle (the level most of it has; dips such as Goh's Lv. 100 legendaries at IV 1 stay), the whole team the same, and
  HP as Origin's loader sets it: 10 up to Lv. 40, 20 at Lv. 41-79, 31 from Lv. 80. Done for the claimable roles
  (data/characters.yaml `iv`, scripts/character_ivs.py, the story team builder and Copy to TEAMS); every other trainer
  team we make follows the same rule when the trainer data are exported.
  **The IVs belong to the battle, not to the team** (Arvind asked how the website knows): a claimer's own team picked
  for a battle gets that battle's IVs. In TEAMS its IV fields are locked to them (with a note), the trainer page shows
  "IVs in the game" per battle, and the game export must take the IVs from the battle (characters.yaml `iv`), never
  from the team.
  **The HP rule is a bug in the hack, not a design** (EN patch notes trainer_runtime_review.md and
  damage_calc_mechanics.md): the loader picks 10/20/31 from the level and writes it six times in a loop that never
  moves to the next stat, so only HP gets it. The intent was clearly all six IVs from the level (which would have
  replaced the per-team IV levels). We keep the game as it plays.
- **Hardcore: healing is limited (Arvind, 2026-11-17).** Each place that heals (every Pokemon Center, and other
  healers) can be used **once**. Built like the area rule: one bit per healing place in our save block, checked where
  the game heals the party. **Open:** are potions and other healing items outside battle still allowed? (If yes, the
  limit is soft; most hardcore rule sets allow them.) **Arvind: the usual hardcore nuzlocke rules apply**, so
  healing items outside battle stay allowed; the one-heal-per-place limit is our own extra rule on top.
- **Not grindy under the cap (Arvind: "still just as grindy").** The cap does not make grinding, the EXP on the road
  does. Two tools: (1) place the route trainers so that fighting all of them brings the team to the cap (Exp Share
  on); (2) **Proposal: catch-up EXP**, more EXP the further a Pokemon is below the cap (for example x2 when 3 or more
  levels under), normal EXP close to the cap and none past it. Then a new catch or a benched mon reaches the cap in
  a few fights. It is a small change in the same EXP code the cap already patches.
- **Level cap, old note.** Hardcore uses the English patch's cap (the highest gym-leader level so far). The caps in Origin
  climb to 100 at the end of Kanto and are 80-88 for the Johto gyms after it. **Open:** once our trainers are set,
  make our own cap table that follows our curve, and check that the Johto half still feels hard (the Johto gyms come
  after a level-100 boss in Origin's order).
- **Proposal: boss levels lead, routes follow.** Every gym leader and story boss sits at the cap; the trainers on the
  way are 2-5 levels below; wild Pokemon a bit below those. Players who fight every trainer reach the cap without
  grinding (Exp Share on).
- **Proposal: Gravriel's harder trainers by role, not everywhere.** Gym leaders, rivals, Rocket executives and the
  Elite Four get a 6th Pokemon, held items and better movesets; ordinary route trainers stay as they are so the run
  does not drag. Our story team builder (lines that grow over battles) makes this a data choice.
- **Simulate instead of playing (Arvind: time is short):** run the boss fights in a battle simulator such as Pokemon
  Showdown's engine (open source, runs locally, thousands of battles in minutes) with our mons added as custom
  species, a "fair" team of what is catchable before each gym, and the boss team. It finds walls, not exact numbers.
  **What differs from Origin:** (1) the AI: Showdown has no copy of Origin's trainer AI, so our bot only imitates it,
  and the player side is a bot too, not a human; (2) Origin's own changes to moves, abilities and items (it has its
  own, e.g. Flame Mane) and our custom ones must each be written into the simulator; (3) small engine details (order
  of effects, the HP-IV bug) need checking. **Found:** the English patch has a damage calculator made for Origin's
  data and checked against the emulator (`work/tools/damage_parity`, `site/src/lib/calc`), so the damage numbers can
  come from there instead of plain Showdown.
- **Proposal: a play-test target per gym.** For each gym we write down "a careful Hardcore player with the
  catchable mons up to here should win with 0-2 deaths". The emulator test bench (already used for the nuzlocke)
  can check the numbers: levels, team sizes, type coverage of what is catchable before each gym.

### 4. Story beats with our mons

From the plans so far, in order (details in docs/PLANS.md ("When we finalize the game")):

1. Opening movie: Sabertann (or Gravriel) in the legend's role.
2. Meowth with Jessie and James, the real talking Meowth; he "dies" (only implied); a man in a Meowth costume
   takes his place.
3. Rocket reports about "subject 52" spread over the game (foreshadowing).
4. **Scripted wipe (Arvind: relatively early in the game, against an antagonist; which one is open):** a story battle you are allowed to lose; Giovanni
   breaks the fourth wall, heals your team and mocks you ("Get up, you're better than this. Need some help?").
   In Gravriel this battle must not count as a nuzlocke wipe (decide: the team is healed by the script).
5. The boss fight: Meowthwo under Persian's control evolves into **Meowthree** in the middle of the battle.
6. Giovanni's goal. Arvind's problem with "super trainer": then he would have made himself super, not
   Meowthwo. **Proposal (Claude): turn people into Pokemon**, because humans cannot evolve, so he makes them into
   something that can, and something you can catch and control. The costume man is his first test: Meowthwo is the
   proof that it works. It ties the theme, Meowthwo and the Rocket reports together. A possible last twist: in his
   final, Giovanni uses the harness on himself, so both ideas meet, and the mid-battle evolution code is reused.
   **Arvind (2026-11-17): likes it.** Whether Giovanni himself is replaced by another character is undecided.
   **Where it fits: the Beedrill "last stand"** (Arvind's idea, checked): Origin's final is three battles in the
   Pokemon League (script file 822, text bank 520): Giovanni (trainer 244), Giovanni with his past copy (288 + 287),
   then his first Pokemon Beedrill alone (trainer 289, one Lv100 Beedrill). The Beedrill part is short and simple: the
   Beedrill appears as person 9, cries (cry 15 = Beedrill), 5 lines, `TrainerBattle 289`, 2 lines after, it is hidden.
   To swap it for Giovanni putting on the harness: rewrite those 7 lines (easy); give trainer 289 the new creature
   (easy, team data); person 9's overworld sprite and the cry become the creature's (the same kind of work as our
   other mons); optional: the battle shows the creature as its own trainer, like Origin's Mewtwo battle (#1013), and
   the change happens in the battle with the Meowthree code (later). New art needed: one new mon (front, back, icon,
   overworld). Beedrill also stands in Giovanni's two other teams; those slots become our mons anyway.
   **Catch him (Arvind: "irony"):** possible with a scripted wild battle after (or instead of) trainer 289, like a
   legendary. **Checked the story order (corrected 2026-11-17):** the Mt. Silver meeting "two years" later (text
   bank 539) comes **before** the final, not after: Cerulean Cave (Kanto) -> two years -> Johto -> Mt. Silver
   (he finds the Adamant Orb) -> Dialga's space -> Distortion World (Giratina) -> the final at League HQ -> the final
   Hall of Fame -> post-game. After the final he is led away to stand trial and does not come back, so catching him
   at the very end needs no explanation. (Claude first wrote that he returns after the final: wrong.) The copy from
   the past already appears in the final itself; a post-game rematch with that copy is an optional extra, not needed.
7. Post-game: official Pokemon return; Meowth's fast food place; the freed Meowthree (and in Gravriel the special
   revive).

**Villains in Origin (counted 2026-11-17 from the trainer list):** one evil team only, Team Rocket. There is no
Team Aqua/Magma/Galactic/Plasma: Origin makes the other regions' villains Rocket executives.
- Boss: Giovanni (8 teams). A nameless "Rocket Boss" team (#700) is used in the Celebi time-travel scene.
- Executives (10): Archer, Ariana, Proton, Petrel (HeartGold's own), Maxie and Archie (Hoenn), Cyrus and Charon
  (Sinnoh), Lawrence and Marauder (Origin's own). 3-8 teams each.
- "Rocket Elite" (5): Karen, Will, Joy, Cassidy, Butch (3-5 teams each).
- Jessie and James (8 tag battles each, Meowth in James' team); Silver works with Rocket for a while ("Master Silver").
- 142 Rocket Grunt teams and about 20 named scientists.
Who takes Giovanni's role (or whether anyone does) is open (Arvind).
Origin's world is Kanto + Johto + the Sevii Islands (plus special places: Sinjoh Ruins, Dream World, Dialga's
space, Distortion World). No Hoenn or Sinnoh: Maxie, Archie, Cyrus and Charon only come over as Rocket executives.
**Size of a villain swap:** about 3,000 text entries name Rocket or one of its people (Rocket in 199 of the 805
text banks, Giovanni in 74). Three levels: (A) keep Rocket and its people, give them our mons and add our own
beats (Meowthwo, the harness, the Giovanni twist): least work, planned anyway; (B) rename: same plot, new names and
new trainer pictures (name swaps in the texts + about 16 new character pictures and a grunt): medium, can be done
late; (C) our own villain plot: hundreds of scenes rewritten, not realistic. **Arvind (2026-11-17): A for now**; he does not know yet what Rocket would be replaced
with. Ideas to keep in mind for B (Claude): (1) Rocket stays, but changes during the game as the harness spreads
(no new team, only new looks late in the story); (2) a team built on our theme, people who want to "evolve" humans,
e.g. a self-improvement company that sells growth (fits the harness and the fast-food humour); (3) a team per
version, each worshipping that version's legend (Sabertann / Gravriel), so the versions differ in story too.
**If B (same plot, new names and looks), concepts that fit Origin's plot (theft, experiments, the League gold,
legendaries) and our theme (names are placeholders):**
- **A growth company (Claude's pick):** a self-improvement/biotech firm that sells "faster growth" to trainers; the
  EXP harness is its product. Ads and shops early in the game (foreshadowing, cheeky humour), crime behind it. Boss =
  the founder, executives = department heads, grunts = sales staff/lab workers. Fits the League gold (funding) and
  the experiments (Meowthwo) directly.
- **A cat syndicate:** built around the boss's Persian that controls Meowthwo; Origin already has Persian statues
  with glowing eyes in the Mahogany base. Ties to the costume Meowth; check it does not clash with Sabertann (a cat).
- **A shedding cult:** people who believe humans can "molt" into something higher; executives are ranks, grunts
  are novices. Darkest of the three; fits the Giovanni-in-the-harness ending.
- Per version (one per legend) is possible on top, but doubles the text work.

**Open:** where Sabertann and Gravriel appear in the story (Origin's Ho-Oh/Lugia scenes: Bell Tower, Whirl Islands,
the two cutscenes each are already mapped in docs/STORY.md ("Ho-Oh and Lugia scenes: what Origin does and how we replace them")).

### 5. Fun moments to build (scripted events)

| Event | How | Status |
|---|---|---|
| Villain wipes your team, mocks and heals you | loss-allowed story battle + script | easy, to write |
| Boss in two phases, mid-battle evolution | our battle code, Origin's form-change path | planned (custom code) |
| Trainers talking mid-battle | Origin ignores the normal lines (checked); look at Giovanni's Mewtwo fight (bank 599) | to investigate |
| Gravriel game over on both screens + obituary | our code, needs the art | planned |
| Special revive (Gravriel, once) | small script command of ours | idea |
| Cactus tree with a fourth-wall joke | picture + text | planned |
| **Proposal:** a "you have been here before" joke in Gravriel after a game over (the attempt counter) | text keyed on attempts | idea |
| **Proposal:** the costume Meowth sometimes appears in the background of towns (a running gag before the reveal) | map objects | idea |

### 6. Quality of life (what makes it pleasant)

Already in Origin / the English patch: Move Reminder, EV allocator, Exp/Shiny/Catching charms, Exp Share option,
level cap option, text speed, the advanced AI, auto-save-friendly Options. To add (decided): Move Deleter, PC
anywhere, auto-run. Arvind (2026-11-17): also the other normal QoL things the game lacks; a portable PC is not in
Origin yet. **Checked 2026-11-17 (texts, item lists, emulator):**

| QoL (Arvind: yes to all) | In Origin? | To do |
|---|---|---|
| Reusable TMs | **yes** (emulator: TM17 taught, still 1 in the Bag) | nothing |
| "Use another Repel?" | **yes** (text bank 38) | nothing |
| Nature mints, Ability Capsule, Ability Patch | **yes**, sold in Celadon (25,000 / 50,000, mints 9,000) | maybe earlier or cheaper |
| IV/EV in the summary | **yes** (summary bank 295 has IVs/EVs pages) | nothing |
| EV Allocator | in the game's code and works (emulator), but **never given** by any script | give it (when?) |
| PC from the menu | **no**: a "Box Link" item exists ("access the Boxes ... at any time") but has no Use button and is never given | give Box Link a field use that opens the PC, hand it out early |
| Auto-run on/off | no (Options has no such row) | our code + an Options row |
| Field moves without HMs | no as far as checked (the guide notes one rock where you "don't need" Rock Smash, so normally you do) | our code: HM in the Bag + badge is enough |
| Move Reminder / Deleter from the party menu | no: reminder is Mr. Psychic in Saffron (1 Heart Scale), deleter in Blackthorn | party-menu entries |
| Type-effectiveness hints in battle | no | **Sabertann only**, and learned one by one: a matchup shows after you have seen it once (like Sun/Moon); one bit per type pair (18 x 18) in our save block |

Arvind: yes to a **death counter that shows how many times you have tried to beat the hack** (attempts), the area
sign panel and the "been here before" joke. **Proposal:** also a nuzlocke status panel on the area sign (shows "encounter used / free" when
entering an area), and a running counter of deaths on the trainer card in Gravriel.

Also from Origin's own problems (decided 2026-11-12): remove the quests you can get stuck in, fix the leftover bugs.

### 7. After the story

Official Pokemon return (Gen 5 style). **Proposal:** make it a reason to keep playing: a post-game dex with both
our mons and the officials, the Battle Frontier with our mons, the one-chance legendaries reworked so they can be
found again, and version-exclusive legendaries/officials to trade for.

### 8. Testing so it really is fun

- The emulator test bench (DeSmuME, scripted inputs) already drives battles, the bag, the PC and saves. Extend it
  into **play-test scripts**: start at each gym with a "fair" team (catchable mons only, at the cap) and record
  win/loss and deaths. That finds walls before players do.
- Human play-tests by the group on Sabertann first (story, text, softlocks), then Gravriel Hardcore runs.

### 9. Open questions for Arvind

1. Version exclusives: Arvind's shortlist, decided when the dex is final.
2. Hardcore cap: minus 1 or minus 2 (Arvind confirmed the idea; the number is open)?
3. Which antagonist does the early scripted wipe?
4. Keep Giovanni or replace him with another character? (The plan above works for both.)
5. Catch-up EXP below the cap: yes or no?
6. Who or what Giovanni becomes in the harness (a new mon to design and draw).

---

## Story roles: which Pokémon Origin HeartGold's story needs, and who from our dex takes them
*(was `docs/STORY_ROLES.md`)*

Made 2026-10-08 from Origin HeartGold v4.0.3 + English patch rc3 (its own scripts, trainer parties,
map objects, encounter tables and text, read locally). Our side: `data/species/` on the same day
(99 of 151 slots filled). Companion to [Dex analysis: what Sigma Dex is missing (2026-10-08)](DEX_DATA.md#dex-analysis-what-sigma-dex-is-missing-2026-10-08) (what the dex lacks
compared with the official generations) and [Replacing the whole dex: where real Pokémon still show](GAME_TECH.md#replacing-the-whole-dex-where-real-pokémon-still-show) (what does
not follow automatically when a slot is replaced).

Everything here is a **suggestion** for the group. "Fits" means an existing mon matches the role
well; "partly" means it could work but the designer should agree; "new" means nothing in the dex
fits and a new design is proposed.

### The size of the problem

Origin is huge: 770 of the 1025 species can be caught, and the story is a crossover. Kanto comes
first (levels 5-50), Johto after it (gym leaders at level 80-90), and Hoenn and Sinnoh characters
(Steven, Cynthia, Archie, Maxie, Cyrus) are part of it. About **34 legendaries and mythicals**
have an event, a gift or a place in a boss team.

With 151 mons we cannot replace everything. A line that holds together:

- **Our mons replace the Kanto/Johto Pokémon the story leans on** (this list).
- **Pokémon from Hoenn, Sinnoh and later stay real for now.** In Origin's story they already are
  "guests from other regions" (Steven's Metagross, Cynthia's Garchomp, the Sinnoh legendaries), so
  keeping them does not break the story. This is the "mixed dex" option, done on purpose.
- More of the real ones can be swapped out as the dex grows.

### 1. Pokémon the story needs by name

Ordered by how much the story uses them. "Text" = how many lines outside the Pokédex name it.

#### Starters and partners

| Origin Pokémon | Where it matters | Our candidate | Status |
|---|---|---|---|
| Pikachu (25) | Offered by Prof. Oak today; becomes Blue's starter (see below); Viridian Forest; text 93 | — | **new**: an electric mascot, mono Electric (also missing in DEX_ANALYSIS). Bugmight was only a test. |
| Bulbasaur line (1-3) | Gift on Route 5; Green's ace (Venusaur, text 77) | Leafing → Leafsteel → Leafaxer | fits |
| Charmander line (4-6) | Gift in Pewter (the weak Charmander story, text 111); Lance and Blaine use Charizard | Torchbat → Heatbat → Blazterra | fits (Blazterra is Fire/Flying like Charizard) |
| Squirtle line (7-9) | Blue's starter today; becomes one of the three player choices (see below); gift on Route 9 | Waffy → Wealther → Warrallier | fits |
| Chikorita (152) | Battle on Route 31 | Tinky → Motinky → Gortiki | partly (Grass/Fire; could also stay real) |
| Eevee (133) + 8 evolutions | Gift in Viridian Forest; Blue's Umbreon; the Kimono Girls' Eeveelutions; text 63 | Sigmanian Eevee (planned by Arvind) | see below |

**Sigmanian Eevee (idea 2026-10-08):** a Sigmanian Eevee with nine evolutions: Fighting, Poison,
Ground, Flying, Bug, Rock, Ghost, Dragon and Steel. Together with the eight real Eeveelutions that
covers every type except Normal. It fits the engine: Origin's evolution table has room for 10
evolutions per species (Eevee uses 9 entries today, one free). Simplest is to let Sigmanian Eevee
take Eevee's slot and its nine evolutions take the eight Eeveelution slots (134-136, 196, 197,
470, 471, 700) plus one free slot. The Kimono Girls, Blue's Umbreon and the Viridian Forest gift
then show our Eeveelutions by themselves. Each needs its own evolution method (stones, held items,
friendship by day/night, a place, knowing a move of a type: all exist in the engine). As mono types
they also fill the monotype gaps in DEX_ANALYSIS (Fighting, Poison, Ground, Flying, Dragon, Steel
have none today).

The other starters Origin gives away (Totodile, Cyndaquil, Torchic, Chimchar, Piplup, Shinx, ...)
can stay real as "guests".

**The starter choice:** the game starts in Pallet Town. Prof. Oak offers **Bulbasaur, Charmander
or Pikachu**; Pikachu sits in Squirtle's place because Blue came first and took Squirtle (text bank
444). Blue always has the Squirtle line; the other starters come later as gifts or battles. The
player is a new trainer from Pallet Town (boy or girl, own name); Red and Green are the
other-gender counterpart, and Gold, Silver and Crystal are Johto characters.  The Johto rivals follow the manga: **Silver** (Totodile → Feraligatr, Sneasel/Weavile,
Larvitar/Tyranitar, Magnemite, Gastly/Gengar, Ursaring; 8 battles), **Gold** (Cyndaquil line,
Aipom, Poliwag, Togepi, Sunkern, Mantine) and **Crystal** (Chikorita line, Natu, Cubone,
Parasect, Smoochum, Hitmonchan). Only Silver's three Dragon's Den battles change starter.

**Decided 2026-10-08 (Arvind): the player picks between our three starters (Leafing, Torchbat,
Waffy) and Blue gets the electric mascot.** Plan, keeping every mon in its natural slot (Leafing
1-3, Torchbat 4-6, Waffy 7-9, mascot 25-26):

- Oak's lab script (`a/0/1/2` member 738) holds the offered species as plain numbers (`SetVar …,
  25` / `4` / `1`); the 25s become 7.
- Blue's 19 teams: Squirtle/Wartortle/Blastoise (7/8/9) become the mascot's slots (trainer data).
- The Squirtle gift on Route 9 then gives Waffy, which suits Origin's idea of handing out the
  other starters later; the Viridian Forest Pikachu, Lt. Surge's love of Pikachu and the Light Ball
  all go to the mascot, which fits an electric mon.
- Oak's line "this one was supposed to be Squirtle, Blue took it, so I put Pikachu here" (bank
  444) is rewritten by hand.

(The other way, swapping which slots Waffy and the mascot take, needs no patch but sends all the
Pikachu story and the wild Viridian Forest Pikachu to the Water starter.)

#### Story Pokémon

| Origin Pokémon | Where it matters | Our candidate | Status |
|---|---|---|---|
| Meowth / Persian (52-53) | Team Rocket's **talking Meowth** (Jessie and James's trio); text 200 | — | **new**: a cat-like, mono Normal Rocket sidekick (mono Normal is a gap). Arvind 2026-11-12: Meowth is a man in a costume who becomes **Meowthwo** (takes Mewtwo's role), see docs/PLANS.md ("When we finalize the game") |
| Mew (151) | Team Rocket closes Mt. Moon to catch it (early Kanto story); gift on Five Island; text 95 | Sandrema (mythic, Fairy/Ground) | partly: Sandrema could be "the Mew" or "the Celebi", not both |
| Mewtwo (150) | Gift at Indigo Plateau; Giovanni's ace; text 85 | Cryoblade (Dark/Ice, 605, "Frozen Executioner") | partly: as Team Rocket's lab-made weapon. Otherwise **new**. Arvind 2026-11-12: **Meowthwo** takes this role |
| Slowpoke / Slowbro / Slowking (79, 80, 199) | Slowpoke Well, Team Rocket cutting tails; 21 Slowpoke figures in Azalea; text 82 | Saucerl → Abyssys / Octopearl (Psychic/Water) | partly: same types, but the designers must accept the "slow, tail gets cut" story |
| Magikarp / Gyarados (129-130) | Red Gyarados at Lake of Rage; Lance, Clair, Cyrus; text 69 + 99 | — | **new**: a useless fish that turns fearsome (Magikarp-like is a gap) |
| Snorlax (143) | Blocks Route 12, battle at level 35 | — | **new**: a big sleepy road-blocker, mono Normal (gap). Needs its own sleeping map figure |
| Sudowoodo (185) | Blocks Route 36 (the "odd tree") | Sigmanian Sudowoodo | fits perfectly. Needs the tree map figure |
| Lapras (131) | Union Cave on Fridays, gift in Saffron at level 70; 11 map figures; text 57 | Chillalit (Fire/Water surfer, single stage) | partly: the "ride on it" idea fits. Needs its own map figure |
| Miltank (241) | MooMoo Farm, Whitney's ace | Mooceon (Normal/Water cow) | fits. Cowfin (by its name and types probably the pre-evolution; not entered yet) then needs a free slot |
| Ampharos (181) | The sick Ampharos in the Olivine lighthouse | Bulbtle → Bulbtoise (glass shell full of light) | fits very well (a living lighthouse) |
| Murkrow (198) | Team Rocket's bird, static battle on Route 38 | Bolthook (Dark/Flying) | fits |
| Unown (201) | Ruins of Alph; text 90 | Sigmanian Unown | fits, but Unown has **28 letter forms**: each needs a picture |
| Electrode (101) | Power Plant, traps in the Team Rocket HQ | Giga-Circuit (Electric) | partly (no concept written yet) |
| Clefairy (35) | The dance on Mt. Moon (6 figures); text 55 | Vires (cute Fairy virus) | partly |
| Gastly line (92-94) | Lavender Tower, Morty, Agatha | Ciggiti → Chuchar → Parahaunt | fits |
| Pidgey line (16-18) | Rival Blue all game long, Route 1-2 | Erobi → Harpie → Smeatherace | fits |
| Caterpie / Weedle lines | Viridian Forest, Route 2 | Wump → Twemp → Florantula | fits |
| Geodude line (74-76) | Mt. Moon, Brock | Leadling → Leadling utv. → Blylem | fits |
| Rattata / Raticate (19-20) | Rival Blue's early team, Route 1 and 22 | — | **new**: early mono Normal rodent (gap #1 in DEX_ANALYSIS) |
| Abra line (63-65) | Rival Blue's Kadabra/Alakazam, Sabrina's ace | — | **new**: early mono Psychic line, 3 stages (gap #2) |
| Growlithe / Arcanine (58-59) | Gift on Route 5, Blue's and Maxie's ace | Obsidog → Obsidog utv. | partly (Dark/Rock, not Fire). Or **new** fire dog |
| Larvitar line (246-248) | Ariana's ace in every battle, Giovanni, Marauder | Obsidog → Obsidog utv. (Dark/Rock, 555) | fits Tyranitar better than Arcanine: pick one of the two |
| Dratini line (147-149) | Gift in the Resort Zone, Clair, Lance | Balleisk → Greation → Ultragon (Dragon/Bug) | partly (our pseudo-legendary) |
| Rhyhorn / Rhydon (111-112) | Rival Blue all game long | Panzerien (Steel/Ground tank) | partly |
| Nidoking / Nidoqueen (31, 34) | Giovanni's and Petrel's aces | — | keep real, or a later Poison/Ground pair |
| Machop line, Hitmonlee/chan | Gifts in Saffron, Chuck, Bruno | Brawleo, Sigmauler, Bugmight | partly. **New** mono Fighting line suggested (gap) |
| Farfetch'd, Jigglypuff, Marill, Swablu | Small side events | — | keep real for now |

#### Legendaries and mythicals

| Origin | Role in the story | Our candidate | Status |
|---|---|---|---|
| Kyogre / Groudon / Rayquaza (382-384) | Red/Blue/Jade Orb story, Embedded Tower, Team Rocket's League takeover (Archie, Maxie, Ariana) | Bergflabbser / WIP drought one / Maagamad | fits (see DEX_REPLACEMENT) |
| Raikou / Entei / Suicune (243-245) | Burned Tower, Eusine chasing Suicune, static battles at level 90; text 89 / 201 / 190 | Sabertann + Gravriel + the third, not yet made | fits: a pirate trio "roaming the seven seas" is the same idea as roaming beasts. **New**: the third pirate (Fire would make it Entei's) |
| Ho-Oh (250) | Bell Tower cutscene, gift at level 95, Archer's ace, **title screen**; text 205 | — | **new**: Arvind wants a Sigma cover legendary here. The title model is real-time 3D (see below) |
| Lugia (249) | Whirl Islands cutscene and battle, Lawrence's ace | — | same as Ho-Oh |
| Celebi (251) | Ilex Forest shrine, gift, time-travel cutscene; text 80 | Sandrema | partly (see Mew) |
| Articuno / Zapdos / Moltres | Static battles, Rocket executives' aces | — | keep real for now, or a **new** bird trio later |
| Arceus (493) | Sinjoh Ruins, Giovanni's ace; text 84 | Darkgonark ("when its song ends the universe is remade")? | keep real: the slot has 17 type forms |
| Dialga / Palkia / Giratina | Sinjoh, Cyrus, Charon, Giovanni | — | keep real (Sinnoh guests; Giratina has forms) |
| Deoxys | Marauder uses three | — | keep real (4 forms) |
| Regis, Regigigas, Latias/Latios, Uxie/Mesprit/Azelf, Heatran, Cresselia/Darkrai, Manaphy, Jirachi, Shaymin | Gifts and static battles in side places | — | keep real (guests from Hoenn/Sinnoh) |

#### Pseudo-legendaries

Five pseudo-legendaries carry big parts of the story (counted in all trainer parties and gifts):

| Line | Party slots | Who uses it | Kanto/Johto native? | Ours |
|---|---|---|---|---|
| Dratini → Dragonite | 28 | Lance, Clair, Charon; Dratini gift | yes | Balleisk → Greation → Ultragon |
| Larvitar → Tyranitar | 19 | Ariana (every battle), Giovanni, Marauder, Silver; Larvitar in Mt. Moon | yes | **new**, or Obsidog line (2 stages, 555) |
| Bagon → Salamence | 20 | Lance, Archer, Lawrence, Marauder; static battle on Route 34 | no (Hoenn) | guest, can stay real |
| Beldum → Metagross | 21 | Steven, Jasmine | no (Hoenn) | guest |
| Gible → Garchomp | 22 | Cynthia, Giovanni, Ariana, Clair | no (Sinnoh) | guest |

So one more pseudo-legendary is needed (Tyranitar's: Rock/Dark, desert or mountain), unless
Obsidog gets that role.

#### Mythicals

Mew (Team Rocket's Mt. Moon chase, Five Island gift, text 95) and Celebi (Ilex Forest, text 80)
are the two the story leans on; Manaphy (Alto Mare, text 54) and Jirachi are smaller, Arceus has
forms. With Sandrema taking one of Mew or Celebi, **at least one new mythical** is needed for the
other.

### 2. Types the trainers need

Gym leaders, the Elite Four and the rival use teams of 4-6 of one type, often twice (a Kanto and a
rematch team). A type with fewer than about 6 different mons gives weak or repetitive teams.

| Type | Our mons | Who needs it | Enough? |
|---|---|---|---|
| Fighting | 5 | Chuck, Bruno (2 teams) | **no**, and none is mono Fighting |
| Psychic | 6 (4 of them Psychic/Water or Unown) | Sabrina (6 Pokémon) | **no** |
| Flying | 7 | Falkner (6) | barely |
| Ground | 7 | Giovanni | barely |
| Ice | 7 | Pryce, Lorelei (both 6) | barely |
| Fire | 8 | Blaine (6) | OK |
| Dragon | 8 | Clair, Lance (6 in each of his two teams) | OK |
| Electric | 9 | Lt. Surge (6) | OK |
| Steel | 9 | Jasmine | OK |
| Ghost, Bug, Normal, Grass, Rock, Poison, Dark, Water | 11-17 | Morty/Agatha, Bugsy, Whitney, Erika, Brock, Koga, Rocket, Misty | OK |

Trainers can also keep a few real Pokémon in their teams, so "barely" is not a blocker.

### 3. The first hours

Route 1, Route 22, Route 2, Viridian Forest, Route 3 and Mt. Moon each have 8-14 species in Origin.
The early game needs these kinds of Pokémon, and our dex has:

| Kind | Origin examples | Ours |
|---|---|---|
| Rodent / Normal route Pokémon | Rattata, Sentret, Zigzagoon, Lillipup | Detecup (detective dog), Lapper → **new rodent needed** |
| Early bird | Pidgey, Spearow, Starly | Erobi line |
| Early bugs | Caterpie, Weedle, Wurmple | Wump line, ambuger (fossil, later) |
| Electric mouse | Pikachu, Plusle/Minun | **new mascot** |
| Cave rock and bat | Geodude, Zubat, Onix | Leadling line; bat: Torchbat is the Fire starter, so a cave bat is missing |
| Water and fishing | Magikarp, Poliwag, Tentacool | Wispole, Zapana, **new Magikarp-like** |

### 4. Proposed new mons, by priority

Each one fills a story role and, where possible, a gap from DEX_ANALYSIS.

1. **Electric mascot** (mono Electric, small, mouse-like or not): the player's first partner, Pikachu's slot.
2. **Magikarp-like fish → fearsome evolution** (mono Water → Water/Dragon or Water/Dark): Red Gyarados event, Lake of Rage.
3. **Early rodent line** (mono Normal, 2 stages): Rattata's slots, rival's early team.
4. **Early Psychic line** (mono Psychic, 3 stages, Abra/Ralts-like): rival's and Sabrina's ace.
5. **Team Rocket's cat** (mono Normal, 2 stages, cunning): Meowth/Persian; it talks in the story.
6. **Sleepy giant** (mono Normal, single stage, very heavy): Snorlax's road-block on Route 12.
7. **The third pirate legendary** (Fire to match Entei, or any type the trio needs): completes Sabertann + Gravriel.
8. **Mono Fighting line** (2-3 stages): Chuck, Bruno, the Hitmon gifts.
9. **Cave bat** (Poison/Flying or Dark/Flying): Zubat's place in every cave.
10. **Sigmanian Eevee + nine Eeveelutions** (Arvind's idea, see above).
11. **A Tyranitar-like pseudo-legendary** (Rock/Dark), unless Obsidog takes the role.
12. **A second mythical** (Mew or Celebi, whichever Sandrema does not take).
13. **A cover legendary** for Ho-Oh (title screen, Bell Tower) and one for Lugia.
14. Later: a **bird trio**, a **Rocket-made legendary** (if Cryoblade is not it).

Items 1-6 together add 5 monotype lines, which DEX_ANALYSIS asks for anyway (mono Normal, Psychic,
Electric, Water, Fighting).

### 5. The title screen model

HeartGold's title Ho-Oh (`a/0/4/6` member 25, internal name `houou_test`) is **real-time 3D, not
prerendered**: 1009 polygons (328 triangles + 681 quads, about 1690 triangles), 2360 vertices,
28 bones, 20 materials, textures inside the model, plus a bone animation (member 26), texture
scrolling (27), material animation (28) and texture swaps (29). Origin did not touch it. A
replacement is a low-poly rigged model of about the same size (the DS draws at most about 2048
polygons per frame), animated in Blender and converted to the DS model format. SoulSilver's Lugia
is similar (1481 polygons, 32 bones).

### 6. Things to keep in mind

- **Place names contain species names**: Diglett's Cave, Slowpoke Well. The automatic name swap
  must leave place names alone (or rename them on purpose).
- Some roles need **extra map figures** (Snorlax, Sudowoodo, Lapras, Red Gyarados, tailless
  Slowpoke, big Ho-Oh/Lugia): see DEX_REPLACEMENT.
- **Slots with special code** (Unown, Pichu, Arceus, Giratina, Deoxys, ...) are listed in
  DEX_REPLACEMENT. Sigmanian Unown in Unown's slot is the one place where we do it on purpose.
- Trainer teams are data and easy to change. A boss can get our mon or keep a real one.
- Roles here are based on types, names and the few concept texts we have. Most of our mons have
  no concept or description yet, so the designers should check every "fits" and "partly".

---

## Characters with a type (for claiming)
*(was `docs/CHARACTERS.md`)*

The group plans to replace the game's important characters with themselves. This lists the trainers in Origin
HeartGold that are tied to a type, worked out from their real teams in the ROM (`~/sigma-origin/docs/trainers.md`,
every team of that trainer counted; percent = share of their Pokemon that have the type). Checked 2026-11-11.
A character can be redrawn and renamed; its type follows whoever claims it (our mons must fill the team).

### Gym leaders (16 badges)

| Region | Leader | Type | Share | Special rule in the gym |
|---|---|---|---|---|
| Johto | Falkner | Flying | 100 % | only Flying Pokemon may be used |
| Johto | Bugsy | Bug, **Fairy in our game** (2026-11-17) | 100 % | no type advantage allowed (no Poison or Steel in ours) |
| Johto | Whitney | Normal | 90 % | |
| Johto | Morty | Ghost | 100 % | |
| Johto | Pryce | Ice | 100 % | |
| Johto | Jasmine | Steel | 100 % | only Pokemon with base Defense 130+ |
| Johto | Chuck | Fighting | 100 % | |
| Johto | Clair | Dragon | 83 % | only Dragon Pokemon |
| Kanto | Lt. Surge | Electric | 100 % | |
| Kanto | Brock | Rock | 75 % | |
| Kanto | Erika | Grass | 100 % | |
| Kanto | Koga (leader) | Poison | 100 % | |
| Kanto | Sabrina | Psychic | 100 % | |
| Kanto | Blaine | Fire | 91 % | |
| Kanto | Misty (Cerulean trainer) | Water | 95 % | not listed as a leader in Origin |
| Kanto | Blue | mixed (rival) | | the rival instead of the 8th Kanto leader |

### Elite Four and champions

| Who | Type | Share |
|---|---|---|
| Lorelei | Ice | 91 % |
| Bruno | Fighting | 83 % |
| Agatha | Ghost | 83 % |
| Lance | Flying/Dragon | 83 % / 50 % |
| Steven (Hoenn champion) | Steel | 50 % |
| Cynthia (Sinnoh champion) | mixed (Ground, Water) | |

**The Elite Four in Origin, checked in the game files (2026-11-17).** It is the Gen 1 line-up, not the Gen 2 one:
Lorelei (room 1), Agatha (room 2), Bruno (room 3) and Lance (room 4), then Blue in the champion's room. Origin reuses
HeartGold's rooms (Will's, Koga's, Bruno's, Karen's, Lance's). Each member has two teams: the story run (trainers 245,
247, 418, 246) and a rematch after the first Hall of Fame (702-705), started from the same room script (817-820).
Koga is only the Fuchsia gym leader; Will and Karen are Team Rocket. The Chinese trainer names call 703 "Koga" (阿桔)
and 705 "Lorin" (梨琳), but both use the same trainer class (so the same battle picture) as Agatha (class 89) and
Lance (class 88), and the line just before the battle is Agatha's (菊子) and Lance's (渡), also in the Chinese
original. The EN patch fixed the names in rc8 (their decision D-1442). So "Koga (Elite Four)" and "Lorin" were
never people; on the website they were merged into Agatha (Trainer M) and Lance (Trainer I).

### Villains with a type

| Who | Type | Share |
|---|---|---|
| Archie (executive) | Water | 83 % |
| Maxie (executive) | Fire | 85 % |
| Lawrence (executive) | Flying | 93 % |
| Charon (executive) | Ghost | 42 % |
| Ariana (executive) | Rock/Ground | 42 % / 33 % |
| Petrel (executive) | Poison/Dark | 44 % / 32 % |
| Giovanni (Rocket boss) | Ground/Poison | 36 % / 33 % |
| Archer, Proton, Cyrus, Marauder | mixed | |

### Other named trainers with a type

| Who | Type | Share |
|---|---|---|
| Elder Zhizhen | Grass | 100 % |
| Elder Wensha | Ice | 100 % |
| Elder Tianyuan | Dragon | 100 % |
| Hoenn trainer Steven | Steel | 54 % |
| Elder Huguo | Fire/Grass | 50 % / 50 % |

Mixed teams (no type): rival Blue, Green, Gold, Crystal, Yellow, Cynthia (trainer), Eusine, Copycat, the other elders.
The Battle Frontier brains (Palmer, Argenta, Thorton, Dahlia, Darach) have placeholder teams in the data (the facilities
build their teams).

### Code names on the website

Important trainers show only a code name and a random order, so nothing is spoiled. The key:

- Trainer A: Petrel (executive)
- Trainer B: Lawrence (executive, Flying)
- Trainer C: Eusine
- Trainer D: Ariana (executive)
- Trainer E: Giovanni (Rocket boss)
- Trainer F: Maxie (executive, Fire)
- Trainer G: Gold
- Trainer H: not used since 2026-11-17 (it was "Koga (Elite Four)", Agatha's second team; merged into Trainer M)
- Trainer I: Lance (Elite Four)
- Trainer J: Green (a girl player meets Red instead: the same teams and lines, so it is one role)
- Trainer K: Lorelei (Elite Four)
- Trainer L: Charon (executive)
- Trainer M: Agatha (Elite Four)
- Trainer N: Archie (executive, Water)
- Trainer O: Crystal
- Trainer P: Yellow
- Trainer Q: Bruno (Elite Four)
- Trainer R: Marauder (executive)
- Trainer S: Archer (executive)
- Trainer T: Proton (executive)
- Trainer U: not used since 2026-11-17 (it was "Lorin", Lance's second team; merged into Trainer I)
- Trainer V: Cyrus (executive)
- Trainer W: Silver (added 2026-11-12)
- Trainer X: Goh, the One-Ball Man (added 2026-11-12)
- Trainer Y: Steven (Hoenn champion; added back 2026-11-17)
- Trainer Z: Cynthia (Sinnoh champion; added back 2026-11-17)
- Trainer AA: Janine (Koga's daughter; added 2026-11-17, shown as "master of disguise"; all 26 letters were used or
  retired, hence AA)

Left out on purpose (Arvind makes him himself): the main rival (Blue). The two champions were left out on 2026-11-12 and
are claimable again since 2026-11-17 (Arvind: "Du kan faktisk legge de til som mulige trenere tilbake").
The villains (codes A, B, D, E, F, L, N, R, S, T, V) were taken off the website on 2026-11-12 (Arvind); their codes are kept
here so the remaining letters keep their meaning.

### Facts to know when claiming (checked against the game, 2026-11-17)

Every role's battles, levels, team sizes and sides were compared with Origin's trainer data and battle scripts (EN rc8).
All matched except one side: Crystal's first team (Route 46) only fights next to you; its "against you" use is in a
scene that never starts. Fixed. Other things a claimer should know:

- **Romance.** Origin has an optional romance route, and eight claimable roles can become the player's partner:
  for male players Green (Trainer J), Misty (gym-water), Yellow (P), Cynthia (Z) and Crystal (O); for female players
  Red (J), Steven (Y), Gold (G) and Silver (W). Blue is the fifth option for female players. A confession happens in
  the final chapter, and some partners have dates after the story (Cynthia even meets the player's mother). Arvind
  keeps it (2026-11-17: "Romance er bare morsomt").
- **Trainer J is two characters.** A male player meets Green (a girl), a female player meets Red (a boy), with the same
  lines and teams. Arvind decided 2026-11-17: J gets one design, used for both (Green's and Red's sprites are simply
  the same picture).
- **Johto is about two years after Kanto.** Several lines say so (Lance on Mt. Silver: Giovanni has hidden "these past
  two years"; a Silver Conference entrant went to the Indigo Conference "two years ago"). The game does not show it:
  every role keeps one figure on the map from start to end, Johto included. Only Steven and Cynthia change (to their
  champion look in the final chapter, below). In battle, Gold (G) has a second trainer class (109 instead of 125) for his Lv. 97 battle at the Mt. Silver summit, but the picture is the same (checked pixel by pixel 2026-11-17). Misty fights next to you under a second class (93; against you she is class 103). Its front picture is a boy in a green cap, but a partner is only ever seen from behind: tested in the emulator 2026-11-17 (Mt. Moon multi battle, MultiBattle 84 959 81), the game shows Misty's own back picture and never the front one. So nothing to fix; but every role that fights next to you also needs a back picture drawn. Looking older in Johto would be new work: a second map sprite plus a switch.
- **Some counted battles are optional or easy to miss:** Steven and Cynthia wait in Fuchsia City from the Soul Badge
  until Team Rocket takes over Saffron (Sabrina's call in Pokémon Tower), then leave for good, a known Origin bug
  (guide/known-issues.md, "Cynthia and Steven in Fuchsia City"); in the usual order there is a window, so battle them
  before Pokémon Tower. Also Cynthia on Route 12 (optional, one chance), Bruno in Pewter City (one chance), and the
  romance dates. Their teams are still worth making.
- **Not on the page:** Blue (Arvind makes him), the villains (taken off 2026-11-12), and small recurring trainers such
  as Norman (after the story, with Steven) and the Copycat. Gold's unused trainer 260 (it has Green's
  team) is left out.
- **Janine, Koga's daughter (checked 2026-11-17; on the page as Trainer AA since the same day).** All in Kanto; she is never seen in Johto (her old phone slot
  went to Koga). Fuchsia Gym: she is the "Koga" eight steps north of the door (trainer 325: Venomoth, Golbat,
  Ariados, Haunter, Lv. 46); after the loss the real Koga steps out: "Well done, Janine" (file 806 script 9). Fuchsia
  Forest: one of Koga's clones that scare off Granny Kin and the Rocket executives is Janine in disguise (90#115–117,
  no battle). After the Soul Badge she stays in the Gym as an Attack EV sparring partner for a Rawst Berry (trainer
  473, Lv. 10 Pinsir/Zangoose/Solrock, also after the story). Victory Road qualifiers: she is the League staff member
  hidden among the competitors (the job was meant for Koga, but then too few would pass). She shows up openly on 2F
  "on a secret break" (trainer 564: Crobat, Venomoth, Ditto, Swalot, Lv. 75), then disguises herself as one of five
  3F competitors, which one depends on gender, starter and the Route 11 choice (that battle uses the competitor's
  team). Beat that one and she reveals herself and gives the password 570819. Misty later says she saw through
  Janine's disguise thanks to your hint (588#10). So: 2 battles with her own team, 1 disguised, plus the sparring; the page counts 3 (the sparring included).
- **Other trainer-name fixes in the EN patch** (bank 719) do not touch these roles; only 703 and 705 did (see above).

### Text to fix when the characters are replaced

Found while counting dialogue (scripts/character_dialogue.py) and checking claims, 2026-11-16:

- **One person claims both Chuck and Bruno** (Emil has gym-fighting and Trainer Q). That is fine: the two never share a
  scene or a battle. One line has to change, though. In text bank 134 (Chuck's training scene on the beach, line 25)
  Chuck says he is not as strong as "Mr. Bruno of the Elite Four". With one person in both roles, he would be talking
  about himself. When the texts are rewritten, change or drop that comparison.
- **Koga has one role, not two** (corrected 2026-11-17). An earlier note here said he was also in the Elite Four
  (Trainer H). That was a wrong name in the Chinese trainer list: trainer 703 is Agatha's second team. Koga is only
  the Fuchsia gym leader (gym-poison).
- **Steven and Cynthia come back as a surprise** (Arvind, 2026-11-17). In Origin they are your friends all through Kanto,
  leave after the first Hall of Fame and only return in the final chapter, on the Indigo Plateau, as the new champions
  of Hoenn and Sinnoh. You never see them in Johto, but the text gives it away. Plan: they only say they are going
  home, and the Johto rumours lose their names. The romance with them stays (Arvind: "Romance er bare morsomt").
  Lines to change (bank#line in the EN patch rc8):
  - 445#128, Steven outside the school in Viridian: drop his plan to become champion and battle you again; keep the goodbye.
  - 393#153, #155, #159, #160, the Hoenn trainer in Mt. Mortar: no name, no "friend of Mr. Steven's" choice (only the menu text changes).
  - 364#9 and 124#145, Hoenn trainers on Mt. Silver and at the Silver Conference: no name, no hint that the champion knows you.
  - 579#24, Prof. Rowan in Goldenrod: drop "I heard about you from Sinnoh's new League Champion. She said...".
  - Keep the reveal (608#48-55: "Who are these two?" ... "The new League Champions of the Hoenn and Sinnoh regions?!")
    and Goodshow's hint before it (537#145). 145#9 (Sinjoh Ruins) comes after the story and can stay.
  - Their names are also choices in two romance menus in Johto (583#49/#60, 586#8/#13); fine, they only name them.
  Their looks already change at the reveal: overworld sprites 142/143 (Kanto) and 295/296 (final chapter and after),
  trainer classes Hoenn/Sinnoh Trainer and Hoenn/Sinnoh Champion (720#127/#128), so each claimer draws a Kanto look
  and a champion look.

### The Bug gym becomes a Fairy gym (Arvind, 2026-11-17)

GutnDin's idea (he has claimed the role). Arvind: "vi vil gjøre bug gym til en fairy gym". On the website the role
(id gym-bug, so claims keep working) is Fairy since 2026-11-17. It is the only gym that changes type. With it, the
gyms cover 15 types: Bug now has no gym, and Ground and Dark have none either (as before; they are only among the
villains: Giovanni, Ariana, Petrel). The Elite Four (Ice, Fighting, Ghost, Dragon) repeat gym types.

- **The rule: DONE in a test ROM** ("holy shit. broken på denne gymen. vi går for det"). Azalea Gym's script (file
  866, L393 on) is 203 `PlayerHasSpecies` checks in a row; Bugsy refuses if any party Pokemon is on the list. Now the
  list is the Poison and Steel species (any form): 168 national ids from the EN patch's species list, the last one
  repeated to fill 203 slots. His refusal (bank 559 line 22) now reads "None of your Pokémon can be Poison or Steel
  type. / Those two would make this battle far too easy for you!". Built by
  scripts/origin_custom/fairy_gym/build_fairy_gym.py (IN.nds OUT.nds); tested in the emulator 2026-11-17 on
  ~/sigma-origin/rc8/fairy_gym_test.nds: with a Bulbasaur in the party he refuses with the new line, with a
  Charmander (banned in Origin) the battle starts. Our own Poison/Steel species (20 so far) are added at export; if
  the list passes 203 the script has to be rebuilt longer.
- **The pit: flowers and glitter** (Arvind). The webs are the map texture `g02spider` (128x128, 8 colours with alpha,
  format A5I3) in the Azalea texture set a/0/4/4 file 29, on the `gym02spider` mesh of land data 248; the silk
  walkways are `g02rope_a` (32x32). Same size and format in, so no model change.
- **The Spinarak carts:** a Fairy Pokemon or a cute cart instead (overworld objects, command AzaleaGymSpinarak).
- **Also now:** the bug emblem on the floor at the entrance (`g02mark`, 64x64) and the gym trainers' teams (Fairy).
- **The look: DONE in a test ROM, approved by Arvind (2026-11-18, "looks good").** Built by
  scripts/origin_custom/fairy_gym/fairy_look.py (IN.nds OUT.nds [PREVIEW_DIR]); it runs after build_fairy_gym.py.
  Everything visible in the gym comes from two texture sets that only area 29 uses (maps 136 = the entrance hall and
  180 = the gym): map textures a/0/4/4 file 29 and building textures a/0/7/0 file 27. Neither has per-outfit copies in
  data/clothes1|2. Every texture keeps its size and format, so the script writes them back in place. Changes:
  - autumn leaves (`g02ochi*`) -> fallen cherry petals; the trees and the big tree -> pink blossom trees, rosy bark;
  - hedges -> mint; floor -> pale pink stone with lilac pebbles; the wavy back wall and the pit walls -> lavender;
  - entrance hall: the green diamond carpet -> pink, the red door mat -> pink, the potted plants -> pink bushes;
  - the pit: the transparent webs are replaced by an opaque dusk-violet flower bed with glitter (`g02spider` drawn
    new, A5I3; the pit shows it about 3x smaller than its texels, so the flowers are drawn big, radius 5-9);
  - silk walkways (`g02rope_a`) -> pink and white ribbon; the switch bridges: orange -> pink, blue -> periwinkle; the
    levers follow (red -> pink, blue -> periwinkle), so the colour clue of the puzzle stays;
  - the bug emblem (`g02mark`) -> a pink ring with a four-point sparkle (drawn new);
  - the Spinarak carts -> **Fleuroom's mushroom head** (Arvind 2026-11-18: Fleuroom is the leader's signature
    Pokemon). Built by scripts/origin_custom/fairy_gym/fleuroom_cart.py (called by fairy_look.py). The cart is room
    building model 118 `gym02lift` (a/1/4/8, also listed as fielddata/build_model/bm_room.narc; both FAT entries are
    patched, they are two copies). Its 22 display lists are rewritten in the same 5544 bytes: an orange dome cap with
    cream spots (the player stands on top, y about 2, the old platform was at 1), gills under the rim, and a cream stem
    with Fleuroom's face on the camera side; the six legs get one invisible triangle each. Colours come from his DS
    sprite. Texture gotcha: in a/0/7/0 file 27 g02lift_body and _body2 share one palette, body2 shares its pixels with
    leg1 and on2 with leg2, so the face is on g02lift_on1. Riding works in the emulator (the player stands on the cap
    and crosses the pit). Parked against a ledge only the cap shows (the ledge hides the stem, as it hid the Spinarak's
    body); while riding the face shows as a cream stem with two dark eyes. Pictures:
    ~/sigma-origin/fairy_gym/fleuroom_cart_model.png, ride6_zoom.png, side_v6.png.
  Method: "ramp" moves every palette colour onto a Fairy colour ramp by its brightness, so the original shading and
  outlines stay; "hue" moves only the colourful entries (grey metal stays). Tested in the emulator on
  ~/sigma-origin/origin_hg_en.nds (test jump into map 180), side by side with the original:
  ~/sigma-origin/fairy_gym/side_v2.png and mark_side.png. Applied to the rc8 rule ROM:
  ~/sigma-origin/rc8/fairy_gym_look_test.nds. Not changed yet: the gym trainers are still Bug Catchers (their
  sprites and classes go with the Fairy teams), the two gym statues and Bugsy himself.
- **Later:** the Hive Badge (name and picture), the reward TM81 X-Scissor, the Megahorn tutor at the door.
- **Rewrite:** Bugsy's Bug lines in the gym, and the Ilex Forest bug hunt he runs before the gym.

---

## Ho-Oh and Lugia scenes: what Origin does and how we replace them
*(was `docs/LEGEND_CUTSCENES.md`)*

Arvind (2026-11-15): Sabertann takes Ho-Oh's role, Gravriel takes Lugia's. This page lists Origin's four scenes, what each
one is made of, and the plan. Tools and build commands: `scripts/origin_intro/README.md`, section "Legend cutscenes".

### Origin's four scenes

Origin gives each legendary two scenes: one in the League HQ round 4 story (Team Rocket steals it) and one after the final
Hall of Fame (you catch it). Guide: originheartgold.github.io/guide chapters 30 and 34. All four are recorded from the game
(local only, through a test ROM that jumps to the scene).

| Scene | Map | Script (`a/0/1/2`) | What happens | Pictures it uses |
|---|---|---|---|---|
| Ho-Oh, round 4 | Bell Tower roof (340) | 21, entry 8 (var 0x40a9 = 4) | Morty and "Kimono Girls" (Rocket's Joy and her Ditto) do the dance, Ho-Oh flies down, Goh catches it with one ball | the 7 bird frames, the Rainbow Wing feather, bell, leaves, rings |
| Ho-Oh, post-game | Bell Tower roof, sunset | 21, entry 7 (var 0x40a9 = 9) | Satsuki and her four sisters dance with Morty's Clear Bell, Ho-Oh flies down, battle at level 95, then catch | same |
| Lugia, round 4 | Whirl Islands B3F (244) | 104, entry 6 (var 0x40a4 = 7) | Lawrence uses Articuno, Zapdos and Moltres to wake Lugia; battles; Lugia appears and is caught by Lawrence | the 7 bird frames (it moves in by script, no 3D effect) |
| Lugia, post-game | Whirl Islands B3F | 104, the dancer's entry 2 | Satsuki's ritual with the Tidal Bell: eye glimmer, Lugia breaks out of the waterfall, flies down; wild battle at level 95, one chance | 7 bird frames, 6 silhouette frames for the eye glimmer, Silver Wing feather |

### The Lugia post-game scene is broken in Origin

The cutscene code (`legend_cutscene_camera.c`) chooses Ho-Oh's or Lugia's version from the game version, not from the map.
Origin is HeartGold, so the SoulSilver-only Lugia ritual runs with HeartGold's paths: autumn leaves in a sea cave,
Ho-Oh's camera angles, the camera clipping through the cave. Checked three ways:
- Origin's cutscene code still reads the game version in the same three places as vanilla HeartGold (same offsets apart).
- The Dance Theater's "I want to see Lugia" only clears flag 581 (the sisters appear); nothing else changes the path.
- Setting the version to SoulSilver in memory just before the ritual gives the right scene: waves, the camera on the water
  and the waterfall. A yellow speckled block over Lugia stays either way (probably the five invisible "stop" objects
  round Lugia whose sprite HeartGold lacks; not confirmed).

### Plan

1. **Pictures (sprite work, no 3D in the game):** Sabertann and Gravriel each need 7 front-view frames of 64x64 in 15
   colours (`a/0/8/1` 210/211), drawn to survive the close-ups. Gravriel also needs the 6 silhouette frames. Our 3D
   models from the intro can give consistent poses; the frames are then cleaned as pixel art and measured against Ho-Oh's.
2. **Motion:** the descent is code (starts 120 units up, 1 per frame). For Sabertann "sailing down from the sky" works with
   the existing motion. Gravriel rising out of the water needs a code change; the round 4 scene moves him by script and
   can show him rising there.
3. **Fix the Lugia ritual for Gravriel:** either make the cutscene code take the SoulSilver path on map 244 (a small code
   patch), or rewrite the script to leave out the leaves/waves and the broken camera moves and keep the eye glimmer, which
   suits Gravriel. Hide or replace the speckled objects.
4. **Story:** the texts name Ho-Oh, Lugia, the wings and the bells in about 40 text files. Arvind's idea: the Rainbow
   Wing could become something like a treasure map. Origin needs the Rainbow Wing and the Clear Bell (plus the dance) for
   Ho-Oh; the lore asks for the Tidal Bell and the Silver Wing for Lugia. To be decided with Arvind.
5. **Test in the scene:** put our frames into the test ROM and record the same scene side by side with Origin's.

### Gravriel in the Lugia scenes: what we found and the plan (2026-11-16)

**Lugia's 3D film.** The post-game ritual (script 104) plays `Cinematic 1` = Lugia's 3D film `a/2/4/4` (84324 bytes) right before `LegendCutsceneLugiaArrivesEffect` and the descent. Clean 60 fps recording: `origin_lugia_film_jevn.mp4`. It runs 246 frames:
- the camera pans along the waterfall in the sea cave;
- a flash, then Lugia bursts out of the fall;
- Lugia spins in a ring of water and sparkles;
- it hovers in front of the fall and roars;
- fade to black.

**Easier to replace than Ho-Oh's film.** Lugia is its own model, not part of the scene models:

| Member | What it is |
|---|---|
| 5 `lugia_b09` | Skinned model (blend matrices, op 9). 26 joints: body, 4 per leg, 4 per arm, body_up, 2 neck, head, jaw (`ago1`), 4 tail. 2 shapes holding 61 KB of display lists. posScale 4. Textures `lugia_s` 64x64 and `lugia_foot` 32x32, 4bpp. |
| 6 | Lugia's animation, 246 frames, 26 tracks. |
| 0-4 `demoapri_r` | The cave, the fall, the water ring, and their animations. Kept as they are. |

**Gravriel's model.** The intro model (`title3d/grav/grav_v5.blend`) is one 160k-face Hunyuan mesh with vertex paint and a 3-bone face rig. It has no parts, no arms rig and no UVs. A film model needs work like Sabertann's:
- **Parts:** hat, owl face mask and beak, seaweed beard, coat, tatters, arms and hands, cutlass, built from the concept (`assets/concept-art/gravriel/240.webp`, 241).
- **Rig:** about 18 bones on Lugia's 26 joints.
- **Low-poly:** about 1000 triangles.
- **Textures:** Ho-Oh-style flat colour swatches plus a face decal (eyes, beak), within 64x64 + 32x32.

**Plan, in order:**
1. **The film:**
   - Build Gravriel's game model.
   - Write `rig_lugia.py` (Lugia's joints and shapes, our strips skinned per vertex, a new BCA), reusing `rig3d.py`'s pieces.
   - Key the motion by hand on Lugia's path and timing, so the camera, the flash and the water ring still fit.
2. **Overworld sprites:** 7 frames 64x64 (`a/0/8/1` 211) and the 6 eye-glimmer silhouettes, rendered from the same model.
3. **Fix the ritual:** make map 244 take the SoulSilver path (code patch), and hide the speckled block.
4. **Texts.**

### DONE 2026-11-17: the version switch for the Lugia ritual

**Built as a hook, not a flip** (`scripts/origin_intro/legend/version_switch/`):
- The three reads of `gGameVersion` in the legendary cutscene code (overlay 2: `LegendCutscene_BeginClearBellAnim` 0x02252D5C, `LegendCutscene_BirdFinalApproach` 0x0225388E, `LegendCutscene_BeginLugiaArrivesEffect` 0x02253FE2) each become one `bl` to 44 bytes of Thumb code at 0x01FFFE00, the top of ITCM.
- The hook answers SoulSilver (8) when `FieldSystem->location->mapId` is 244 (the Lugia cave) and the real version everywhere else.
- `gGameVersion` is never written. So the caught Pokemon is "met in HeartGold", and nothing else in the list below can see SoulSilver.
- `build.py IN OUT --section` adds the code as an ARM9 autoload section, so it is copied into ITCM at boot (checked on rc8 AI 30 fps).
- `build.py IN OUT` without it patches overlay 2 in place. Write the printed pokes after loading a savestate, since a savestate skips the boot's autoload.

**Checked (2026-11-17):**
- The Lugia ritual with the game still HeartGold now plays the SoulSilver path, like the old test that set the version to 8: the bell glow, water rings, the camera along the fall, and Gravriel coming down in front of the fall.
- Bell Tower with the patch is pixel-identical to Bell Tower without it (1701 frames).
- The round-4 scene (Lawrence) is also on map 244 and will take the SoulSilver path too; it is not reached in testing.

#### The plan as written 2026-11-16 (Arvind)

Origin is HeartGold. The Lugia ritual's scene picks its effects and camera from the game version (`gGameVersion`, a byte in arm9): autumn leaves and HeartGold's camera instead of waves and the sea camera. Arvind's idea is to flip the version to SoulSilver just before the ritual's scene and straight back after it. That should be the last change before the game is built.

**What else reads the version**, all of it in pret (pokeheartgold), checked 2026-11-16:

| Place | What it does | Matters during the ritual? |
|---|---|---|
| `field/legend_cutscene_camera.c` | 3 reads: camera presets, the bird's final approach, waves vs leaves | **yes, this is the point** |
| `pokemon.c` | "met in game" for Pokémon created or caught | flip back **before** `WildBattle`, so Lugia/Gravriel is "met in HeartGold" |
| `unk_0206D494.c` | checks "met in this game" (an event check) | no |
| `title_screen.c`, `oaks_speech.c` | title screen and intro palettes | no |
| `mail.c`, `safari_zone.c`, `unk_02069528.c`, ov74 main menu | version stamped on mail, link data, profile, wireless | no |
| `field/scrcmd_pokemon_misc.c` | Kurt's Apricorn box text | no |

The wild encounter tables are chosen when the game is built (separate HeartGold/SoulSilver files), not at runtime, so a temporary flip does not touch them.

**How:** a small code hook (or two script commands of our own) around the ritual in script 104: flip to SoulSilver before `LegendCutsceneClearBellAnimBegin`, flip back after `LegendCutsceneLugiaArrivesEffectEnd` and before `WildBattle 249`. Test it in the jump ROM: the waves, the sea camera and the waterfall should show.

**Fun to test:** setting the version to SoulSilver in memory before the ritual already showed the waves and the right camera (2026-11-15).

---

## Steven og Cynthia: champions som kommer tilbake som en overraskelse
*(was `docs/plans/STEVEN_CYNTHIA.md`)*

Bestemt av Arvind 2026-11-17: rollene til Steven og Cynthia skal spilles av folk Arvind kjenner. Overraskelsen er at de kommer tilbake som champions.

> «Ja vi kan bare si at de skal hjem da egentlig. Også på ryktene så fikser vi det.»

Kort sagt:
- De følger deg gjennom Kanto som i dag.
- Etter den første Hall of Fame-en sier de bare at de skal hjem.
- Ingen i Johto nevner dem med navn.
- Først i siste kapittel skjønner spilleren at de er blitt champions.

Steven og Cynthia kan tas på karaktersiden igjen fra 2026-11-17, som Trainer Y (Steven) og Trainer Z (Cynthia), commit adbb7cf. Bare Blue fyller Arvind selv. Romansen beholdes (Arvind: «Romance er bare morsomt»). En kort versjon av planen står i `docs/STORY.md` ("Characters with a type (for claiming)") på main.

Alle tall under er tekstbank#linje i EN-patchen (rc8). Kildene er tekstbankene i `~/origin-en/work/translate/banks/a027/` og skriptene, lest med `scriptdump.py`.

### Slik er det i Origin i dag

| Når | Hva skjer | Hvor i dataene |
|---|---|---|
| Kapittel 1–13 (Kanto) | De er utvekslingselever i Viridian og reisefølget ditt gjennom Kanto. Du kjemper mot dem og med dem, og de kommer blant de åtte beste i Indigo Conference. | trenere 2–3, 63–65, 180, 210, 263–265, 270–271, 502, 504, 635, 638 |
| Etter første Hall of Fame | Avskjeden. Steven står utenfor skolen i Viridian med Metagross, og Cynthia gråter inne med Garchomp. Den er frivillig: de står bare der. | flagg 1107 slås på av Oak-scenen (skript 738 L558) eller etter at Yellow er reddet (skript 115 L3604). Steven: sone 50 objekt 29, tekst 445#128. Cynthia: sone 159 objekt 14. |
| Johto (kapittel 15–31) | De er ikke å se. Det finnes bare rykter, og navnene står i to romanse-menyer. | se del 2 og 3 |
| Siste kapittel | Avsløringen på Indigo Plateau. Etterpå er de partneren din i kamper mot Team Rocket. | skript 923 rundt L3843, tekst 608#48–55; trenere 490 og 491 |
| Etter historien | Steven er på besøk hos Norman i Goldenrod. Cynthia besøker skolen i Viridian. Med romanse kommer det også dater. | flagg 2322 (Steven) og 2321 (Cynthia) slås på av siste Hall of Fame (skript 822 L2550–L2554) |

### Del 1: Avskjeden (de skal bare hjem)

Bare én linje må endres: Steven forteller i dag at han skal bli champion. Resten sier bare at de reiser.

| Tekst | Hvem og hvor | I dag | Endring |
|---|---|---|---|
| 445#128 | Steven, utenfor skolen i Viridian | sier at de reiser hjem, og avslutter med at han skal jobbe for å bli champion og kjempe mot deg igjen | **endres**, se utkastet under |
| 552#91 | Cynthia, inne på skolen | «I'm leaving soon. I'm going to miss this place...» | beholdes |
| 552#87 | læreren | stolt over topp 8, trist over avskjeden | beholdes |
| 552#88, 552#8 | elever | Cynthia drar hjem i dag, bestevennen gråter | beholdes |
| 552#83, 552#52 | elev, lærer | de har gått ut og reist | beholdes |

Utkast til 445#128 (spillet er på engelsk; `{PLAYER}` er `{VAR:0103:0}`):

> Steven: {PLAYER}, Cynthia and I are going home. We wanted to see the school one last time before we left. Cynthia's inside crying her eyes out. I can't really handle goodbyes, so I stepped out.
> Steven: Take care of yourself. I'm sure we'll meet again someday.

### Del 2: Ryktene i Johto (navnene ut)

Det kan godt snakkes om at Hoenn og Sinnoh har fått nye champions. Det bygger opp spenning. Men ingen skal si hvem det er, og ingen skal antyde at championen kjenner deg.

| Tekst | Hvor | I dag | Utkast |
|---|---|---|---|
| 393#153 | Mt. Mortar, trener fra Hoenn (banken brukes også på Route 42 og i Alto Mare Waters) | sier at Hoenns nye champion, Steven, en gang reiste og trente i Kanto og Johto | «I'm from the Hoenn region. Hoenn just set up its own Pokémon League, and everyone says Kanto and Johto are the places to train. So here I am!» |
| 393#155 | samme trener, valg i menyen | «Steven and I are friends» | «Tell me about Hoenn» |
| 393#160 | svaret på 393#155 | «a friend of Mr. Steven's», drømmer om å bli som ham | «Hoenn is warm and green, and full of Trainers. Our new League is still young, but everyone trains really hard.» |
| 393#159 | samme trener, etter kampen | «stronger than Steven, our Champion back in Hoenn» | «Wow, you're so strong. Maybe even stronger than our new Champion back in Hoenn.» |
| 364#9 | Mt. Silver og Route 28, trener fra Hoenn før Silver Conference | «Mr. Steven» har sagt til ham at Kanto-championen er den sterkeste | «I'm a Trainer from the Hoenn region. Back home, everyone says the Kanto Champion is the strongest there is. So I came all this way to see for myself.» |
| 124#145 | Mt. Silver, utfordreren fra Hoenn i Silver Conference | «Steven, our League Champion, never stops singing your praises» | «Hello, Champion. I'm a Trainer from the Hoenn region. Even back in Hoenn, people talk about you. So I came here to see you for myself.» |
| 579#24 | Goldenrod, professor Rowan | har hørt om deg fra Sinnohs nye champion, som sier du er den sterkeste hun har møtt | Behold starten. Bytt den siste delen til: «Even in Sinnoh, I heard a great deal about you. I never imagined I would run into you here.» |
| 145#9 | Sinjoh Ruins | Cynthia er champion i Sinnoh | beholdes: kommer etter historien og kan ikke nås i et vanlig spill |

Alt dette er bare tekst. Menyen hos treneren i Mt. Mortar beholder de tre valgene, bare teksten byttes.

### Del 3: Navnene i romanse-menyene

Navnene står som valg to steder i Johto, men bare hvis romanse-sporet er åpnet:
- Spåkona i Goldenrod (583#49 og 583#60).
- Den gamle mannen i Dream World (586#8 og 586#13).

Det avslører ikke at de er champions, men minner spilleren om at de finnes. Hva vi gjør her, henger sammen med åpent spørsmål 1.

### Del 4: Avsløringen (beholdes som den er)

- **Rett før:** i starten av siste kapittel sier Goodshow at han har bedt ligaene i Hoenn og Sinnoh om å sende sine sterkeste trenere (537#145). Det er et hint, men det sier ikke hvem.
- **Øyeblikket:** på Indigo Plateau stopper Cyrus og Charon deg. Cyrus spør hvem de to er, og Charon sier at de ikke er i arkivet deres. Så sier Steven «Long time no see», Cynthia «Did you miss us?», og Cyrus roper at de er de nye championene i Hoenn og Sinnoh (608#48–55, skript 923).
- **Forklaringen etterpå:** Hoenn og Sinnoh har startet egne ligaer etter mønster fra Kanto, og begge har blitt champion der (608#128, 608#142–143).

### Del 5: Kampene når de kommer tilbake

I historien kjemper du aldri mot dem som champions, bare sammen med dem.

1. **Avsløringen:** Steven og Cynthia kjemper mot Cyrus og Charon, som har Palkia og Giratina. Dette er en mellomsekvens, ikke en kamp du spiller, og de taper. Mewtwo bryter barrieren, og du og Mewtwo kjemper mot Cyrus og Charon (MultiBattle 1013/1014/1015, skript 923 L5468). Steven og Cynthia hviler mens dere kjemper.
2. **Ved hovedkvarteret til ligaen på Indigo Plateau:** Karen og Will går to mot én på dem.
   - Du kjemper sammen med Steven mot Karen og en Rocket-grunt (skript 815 L2885: trenere 490, 867 og 1021).
   - Så kjemper du sammen med Cynthia mot Will og en grunt (skript 815 L3049: trenere 491, 866 og 1020).
   - Etterpå knuser Steven og Cynthia Poké Ballene til Will og Karen og slipper Cresselia og Darkrai fri.
3. **Etter historien** kan du kjempe mot dem, og det er åpent for alle:
   - Steven hos Norman i Goldenrod: singel, dobbel, eller mot Steven og Norman sammen.
   - Cynthia på skolen i Viridian: singel eller dobbel, «to relive the day we met».
   - Med romanse kommer det i tillegg kamper der Cynthia er partneren din.

Det finnes også en ubrukt kamp mot hver av dem ved inngangen til ligaen (skript 816, trenere 490 og 491), men den kan ikke startes.

Vil vi ha et øyeblikk der du kjemper mot dem som champions før historien er over, må det bygges som ny scene. Den ubrukte kampen ved inngangen kan være et utgangspunkt.

### Del 6: Utseende (spillet deler det allerede i to)

| | Steven | Cynthia |
|---|---|---|
| Figur på kartet i Kanto | sprite 142 | sprite 143 |
| Figur på kartet i siste kapittel og etter historien | sprite 295 | sprite 296 |
| Mon som følger med på kartet | Metagross (sprite 837) | Garchomp (sprite 918) |
| Trenerklasse i Kanto (kampbilde og tittel) | «Hoenn Trainer» | «Sinnoh Trainer» |
| Trenerklasse i siste kapittel og etter historien | «Hoenn Champion» (720#127) | «Sinnoh Champion» (720#128) |

Hver person får altså et skoleutseende og et champion-utseende uten ny kode. Vi tegner begge. Navnet står per kamp i tekstbank 719. Tittelen «Hoenn Champion» og «Sinnoh Champion» vises bare i kamper i siste kapittel og etter historien, så den røper ingenting før avsløringen.

### Arbeidsrekkefølge

1. Arvind svarer på de åpne spørsmålene under.
2. Personene får navn og tegninger: figur på kartet tidlig og sent, og kampbilde tidlig og sent.
3. Tekst: del 1 og 2 her, og alle andre linjer der navnene står (de byttes uansett når rollene får nye navn). Tekstbankene i EN-patchen er JSON og bygges med deres msgtool. Kjør deres QA-sjekk for bredden på tekstboksene.
4. Test i emulatoren:
   - En lagring rett etter første Hall of Fame: avskjeden i Viridian.
   - En i Johto: treneren i Mt. Mortar, Mt. Silver og Silver Conference, og Rowan i Goldenrod.
   - En i siste kapittel: avsløringen.

### Åpne spørsmål til Arvind

1. ~~**Romanse.**~~ Avgjort 2026-11-17: den beholdes («Romance er bare morsomt»).
2. **Hint.** Helt uten hint i Johto, eller ett lite hint? For eksempel kan treneren i Mt. Mortar si at Hoenns nye champion en gang trente i Kanto.
3. **Regioner.** Skal de fortsatt komme fra Hoenn og Sinnoh, eller får de egne steder?

---

## Gravriel: slik gjør vi ham enda bedre
*(was `docs/plans/GRAVRIEL_INTRO.md`)*
> Status 2026-11-18: done. Gravriel is locked (see [the Ho-Oh and Lugia scenes](#ho-oh-and-lugia-scenes-what-origin-does-and-how-we-replace-them)); this was the plan on the way there.


Status nå (v3), testet i emulator, ikke committet:
- **3D og maling:** 3D-modellen er laget fra et turnaround-ark Qwen tegnet. Fjeset bruker modellens egen form, malt mørkt med lyst nebb.
- **Øynene:** halvåpne, runde og lysende, med tunge lokk og mørke ringer.
- **Scenen:** grønnblå tåkenatt med skipsvrak.
- **Sekvensen:**
  1. lys under vannet
  2. han stiger med lukkede øyne
  3. øynene åpner seg og stirrer
- **Plass:** 329 av 1024 tiles, altså god plass til mer.

### 1. Fjeset og øynene (viktigst)

Problemet er at øynene og nebbet blir laget av meg, ikke tegnet. Derfor blir de aldri helt like tegningen.

Forslag:
1. Qwen tegner et rent nærbilde av ansiktet rett forfra, i designets stil: mørk uglemaske, beige nebb, store blå øyne under tunge lokk.
2. Jeg legger det på fjeset som et ferdig «klistremerke», slik hatteemblemet til Sabertann ble gjort. Da blir øyne, maske og nebb nøyaktig som tegningen.
3. Bare den blå irisen får glød.
4. Du godkjenner nærbildet før noe bygges.

### 2. Bedre farger på hele kroppen

Undersøkelsen ga tre kandidater:
- **Hunyuan3D-2.0 Paint Turbo (anbefalt å teste først).**
  - Den maler en ferdig modell ut fra forfra-, side- og bakfrabildet, altså akkurat det vi har.
  - Tencent oppgir 16 GB samlet, så den passer PC-en din.
  - Den finnes som ferdigbygd Windows-pakke for nyere skjermkort.
  - Nedlasting: ca. 14 GB.
  - Plan: den fyller ut det tegningen ikke viser (baksiden og sidene), mens min projeksjon beholdes der tegningen er tydelig.
- **TRELLIS.2 (Microsoft, MIT-lisens).**
  - Den er allerede innebygd i ComfyUI-versjonen din, så installasjonen er enkel.
  - Den lager modell og farger fra ett bilde. Fin som sammenligning, men den bruker ikke turnaround-arket vårt.
- **Hunyuan3D-2.1-maleren.** Den gir best kvalitet, men trenger 21 GB. Den kan bare kjøre med tunge triks, så den lar vi ligge.

Om lisensen: Tencent-modellene unntar EU, Storbritannia og Sør-Korea. Norge er ikke nevnt, men er i EØS. Det gjelder også modellene vi bruker allerede. Spør gjerne noen om det juridiske før en offentlig utgivelse.

### 3. Sekvensen

- **Øynene åpner seg før fadingen.** Nå skjer det for sent. Jeg flytter det fram, og lar dem gløde sterkere et øyeblikk.
- **Lyset under vannet:** større og tydeligere. Det pulserer og vokser mens han nærmer seg overflaten.
- **Tregere stigning med flere bilder.** Det er plass til 4–6 bilder til (tiles).
- **Tang som driver:** skjegget og fillene svaier sakte fra bilde til bilde, mer jo lenger ned på tråden.
- **Ringer i vannet** som vokser der han bryter overflaten, og vann som drypper av hatten.
- **Tåke foran ham:** lave tåkebånd i forgrunnslaget, så han stiger opp gjennom tåka.

Kameravendingen du foreslo krever endring i spillkoden. Bakgrunnene i scenen kan ikke roteres. Det kan gjøres med en kodepatch, men det er et stort stykke arbeid. Jeg anbefaler å vente med det til resten sitter.

### 4. Når skal man se hvem?

Origin er bygd på HeartGold, så introen viser én figur. Tre muligheter:
- Sabertann i introen, og Gravriel et annet sted, for eksempel på tittelskjermen eller i en senere scene.
- Tilfeldig figur ved hver oppstart. Det krever en liten kodepatch.
- To separate spillversjoner, slik HeartGold og SoulSilver er.

### 5. Arbeidsmåte

- Nærbilder sendes til godkjenning før store bygg.
- Videoen viser alltid alle fire side ved side: Lugia, Ho-Oh, Sabertann og Gravriel.

### Rekkefølge jeg foreslår

1. Fjes-klistremerke fra et Qwen-nærbilde. Du godkjenner.
2. Sekvensen: tidligere øyeåpning, sterkere lys under vannet, flere stigebilder, svaiende tang og tåke foran.
3. Test av Hunyuan3D-2.0 Paint Turbo for kroppen. Krever ja til ca. 14 GB nedlasting.
4. Bestem hvor Gravriel skal vises (punkt 4).
