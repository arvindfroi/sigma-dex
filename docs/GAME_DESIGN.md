# Game design: making our version good and fun (2026-11-17)

This page gathers the design of the playable game in one place: what Arvind decided, what Claude proposes (marked
**Proposal**), and what is still open (**Open**). Details stay in their own pages: versions, nuzlocke and scripted
events in [WHEN_WE_FINALIZE.md](WHEN_WE_FINALIZE.md), story roles in [STORY_ROLES.md](STORY_ROLES.md), trainers in
[CHARACTERS.md](CHARACTERS.md), custom code in [ORIGIN_CUSTOM_CODE.md](ORIGIN_CUSTOM_CODE.md), the order of work in
[ROADMAP.md](ROADMAP.md).

## 1. Pillars: what the game should feel like

1. **A new region dex, Gen 5 style.** Only our mons until the main story is over; the official ones come back after
   (decided 2026-11-11). Every wild encounter is something the player has never seen.
2. **Evolution and growing up is the theme.** Humans cannot evolve; Team Rocket's EXP harness steals growth to force
   it; real growth has to be earned (decided 2026-11-16). Meowthwo becomes Meowthree in the middle of the boss fight.
3. **Two ways to play, chosen by the cartridge.** Sabertann is the standard game, Gravriel the hard one (decided).
4. **Never grindy, never unfair.** Hard comes from smarter trainers, rules and caps, not from hours of levelling.
   Exp Share stays on. "Hardcore is already hard, it must not become impossible" (Arvind).
5. **Funny and a bit cheeky.** Fourth-wall jokes (the cactus tree, the villain who heals you and mocks you, Gravriel's
   obituary that rubs it in, Meowth's fast food job).

## 2. The two versions

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

## 3. Difficulty curve

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
  the newest catch one step higher or lower. **Proposal:** our builder gives the ace one step more (e.g. 24 -> 30).
- **Hardcore: healing is limited (Arvind, 2026-11-17).** Each place that heals (every Pokemon Center, and other
  healers) can be used **once**. Built like the area rule: one bit per healing place in our save block, checked where
  the game heals the party. **Open:** are potions and other healing items outside battle still allowed? (If yes, the
  limit is soft; most hardcore rule sets allow them.)
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

## 4. Story beats with our mons

From the plans so far, in order (details in WHEN_WE_FINALIZE.md):

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
   legendary. But Origin brings Giovanni back two years later (Mt. Silver, text bank 539), so either he gets out
   of the Ball (a line in the Mt. Silver scene) or the catch moves to that last Mt. Silver meeting.
7. Post-game: official Pokemon return; Meowth's fast food place; the freed Meowthree (and in Gravriel the special
   revive).

**Open:** where Sabertann and Gravriel appear in the story (Origin's Ho-Oh/Lugia scenes: Bell Tower, Whirl Islands,
the two cutscenes each are already mapped in docs/LEGEND_CUTSCENES.md).

## 5. Fun moments to build (scripted events)

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

## 6. Quality of life (what makes it pleasant)

Already in Origin / the English patch: Move Reminder, EV allocator, Exp/Shiny/Catching charms, Exp Share option,
level cap option, text speed, the advanced AI, auto-save-friendly Options. To add (decided): Move Deleter, PC
anywhere, auto-run. Arvind (2026-11-17): also the other normal QoL things the game lacks; a portable PC is not in
Origin yet. Candidate list to check against Origin first: PC from the menu, auto-run toggle, field moves without
HMs (own the HM + badge), reusable TMs, "use another Repel?" prompt, Move Reminder/Deleter from the party menu, nature
mints and ability capsule/patch, IV/EV shown in the summary, type-effectiveness hints in battle. Arvind: yes to a **death counter that shows how many times you have tried to beat the hack** (attempts), the area
sign panel and the "been here before" joke. **Proposal:** also a nuzlocke status panel on the area sign (shows "encounter used / free" when
entering an area), and a running counter of deaths on the trainer card in Gravriel.

Also from Origin's own problems (decided 2026-11-12): remove the quests you can get stuck in, fix the leftover bugs.

## 7. After the story

Official Pokemon return (Gen 5 style). **Proposal:** make it a reason to keep playing: a post-game dex with both
our mons and the officials, the Battle Frontier with our mons, the one-chance legendaries reworked so they can be
found again, and version-exclusive legendaries/officials to trade for.

## 8. Testing so it really is fun

- The emulator test bench (DeSmuME, scripted inputs) already drives battles, the bag, the PC and saves. Extend it
  into **play-test scripts**: start at each gym with a "fair" team (catchable mons only, at the cap) and record
  win/loss and deaths. That finds walls before players do.
- Human play-tests by the group on Sabertann first (story, text, softlocks), then Gravriel Hardcore runs.

## 9. Open questions for Arvind

1. Version exclusives: Arvind's shortlist, decided when the dex is final.
2. Hardcore cap: minus 1 or minus 2 (Arvind confirmed the idea; the number is open)?
3. Which antagonist does the early scripted wipe?
4. Keep Giovanni or replace him with another character? (The plan above works for both.)
5. Catch-up EXP below the cap: yes or no?
6. Who or what Giovanni becomes in the harness (a new mon to design and draw).
