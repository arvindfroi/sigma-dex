# Movesets: how the autocomplete decides

`scripts/moveset_fill.py` proposes level-up, TM/HM, tutor and egg moves for every evolution line, based on
real Pokemon in Origin HeartGold. It never removes or changes a move that is already in a species file; it only
fills gaps. Nothing reaches `data/species/` until someone runs `apply`, and that only happens after Arvind said
yes.

Always propose from the newest species files (main), not from an old branch: website edits land on main.

```
git fetch && git worktree add --detach /tmp/sigma-main origin/main      # or any up-to-date checkout of main
.venv/bin/python scripts/moveset_fill.py propose --data /tmp/sigma-main/data   # all lines, about 15 seconds
.venv/bin/python scripts/moveset_review.py                # review page -> proposals/review.html
.venv/bin/python scripts/moveset_fill.py show leafaxer    # one proposal with its reasons
.venv/bin/python scripts/moveset_fill.py propose --fresh  # new proposal for the part Claude added before; apply replaces it
.venv/bin/python scripts/moveset_fill.py apply --data /tmp/sigma-main/data --only leafing,leafsteel   # after approval
.venv/bin/python scripts/moveset_pick.py leafaxer 40      # best 4 moves at level 40 (for trainers)
```

Outputs: `proposals/movesets.json` (everything, with reasons), `proposals/MOVESETS.md` (readable summary),
`proposals/review.html` (the review page; published as an artifact so the group can mark each line OK or
"needs changes"). Rerun `propose` whenever species change: it starts again from the current files.

## On the website (anyone, any time)

Edit a Pokemon > MOVES > **Moveset suggestions**. Two choices:
- **Fill gaps**: moves it does not have yet, all ticked; untick what you do not want, then "Add the ticked moves
  to the form". Hover a move to see why it is suggested.
- **New proposal**: a fresh proposal for the part Claude filled in before (listed in `data/claude_moves.json`);
  "Replace Claude's moves with this" takes those out and adds the new ones. The moves your group wrote stay.
Nothing is saved until you press YES, and everything can still be changed by hand. The suggestions are remade on
every sync (`moveset_fill.py suggest` in `.github/workflows/dex.yml`, every 15 minutes), so after you save new
stats, types, abilities or notes, a new suggestion is ready within 15 minutes.

## Where the facts come from

- **The official games' Pokemon** (types, stats, abilities, evolutions, egg groups, level-up / TM / tutor / egg
  moves) from Pokemon Showdown's public data (MIT), fetched when it runs, so it works anywhere, also on GitHub.
- **Origin HeartGold** in `data/engine/origin.yaml`: its 130 TMs + 8 HMs, its 85 move tutors (place and price)
  and the moves it changed (e.g. Slam is Grass there). Read from the game's player docs (made by the English
  patch team). `SIGMA_MOVESET_SOURCE=origin` uses those docs directly (`~/sigma-origin/docs`, only on Arvind's Mac).
- **Pokemon Showdown's moves.json** (MIT) for what a move does: setup boosts, recovery, priority, pivoting,
  punch/sound/slicing flags.
- Both are cached in `.cache/movesets/` (gitignored). The repo keeps only our own species' moves and Origin's
  TM/tutor lists.

## Steps

1. **Lines.** From the `evolutions` fields, plus "evolves from X" on a concept card. Species with no evolution
   written that sit next to each other in the dex, share a type and grow clearly in stats (or have the same name
   with `-utv`/`-utvikling`) are treated as a line too, and the proposal says "guessed from the dex order".
2. **Learning from all of them.** Each species is compared with every official species: shape of the stats (which
   stats are high), total, types (same types count most), stage, evolution levels, shared abilities, words in its
   look/concept (turtle, bat, mushroom ...), official Pokemon the designers name ("like Zigzagoon", "inspiration
   from Tyranitar") and official Pokemon that can learn the moves the designers already chose. Legendaries are only
   compared with legendaries. Every official Pokemon then gets a weight that falls off smoothly with how different
   it is (the 60 closest count; the closest one usually weighs 10-30 %, so no single Pokemon decides). The page
   shows the eight biggest influences. The result is a Pokemon inspired by many, not a copy of one.
3. **Built around your own moves.** Moves already in the file never change, and they steer the rest: an official
   line that can learn the moves you chose counts as more similar; a model move that does the same job as one of
   yours (same type, side, about the same power and level, no different effect; or the same kind of status move)
   is left out and listed; nothing stronger of the same type comes before your own strong move; new moves never
   share a level with yours. Only level-up is thinned this way and only for moves learned at about the same
   level: the same kind of move can still come from a TM or tutor. A move that hits both foes (Heat Wave) and one
   that hits one (Flamethrower) are different moves.
4. **Level-up.** Every weighted official Pokemon votes with its level-up list: its levels are moved to our
   evolution levels, and its moves of a type we do not have are swapped for a move of our type at about the same
   power, on our physical/special side. Each move gets the sum of the votes and the weighted middle of their
   levels; the strongest moves are taken, as many as such Pokemon usually have, spread over the levels the way
   they spread them (start, before evolving, right after, middle, late), so a Pokemon keeps learning moves after
   it evolves. An evolved form also gets what its earlier stage learns after the evolution level, a bit later.
   The proposal flags a Pokemon that learns nothing after evolving or has a long gap without new moves.
   **Same-type ladder:** like Game Freak, each own type gets a weak (35-60), a middle (65-80) and a strong,
   reliable (85-100 power, 90 %+ accuracy) move by level-up on the side the Pokemon attacks with; a missing step
   is filled with the move official Pokemon of that type learn most (Autuman: Razor Leaf, Slam, Leaf Blade, and
   Power Whip as its big move). When translating a model's move, the commonly learned move of our type wins near
   ties, so the votes add up instead of splitting over many similar moves. Moves outside our own types need
   more agreement (15 % of the weight). Type-flavoured status moves are swapped (Sleep Powder -> our type's sleep
   move, Sunny Day -> our weather) or dropped; other species' signature moves are never copied; each of our types
   gets level-up attacks; at most six moves at level 1 for evolved forms; an evolved form keeps what its earlier
   stage learned before evolving; punches are skipped for bodies without arms.
5. **TM/HM, tutor, egg.** For every TM (Origin's list only) and every tutor move, a score from how much of the
   weighted official Pokemon learn it and how many official Pokemon of our types (at that stage) learn it; moves
   almost everyone learns (Protect, Rest ...) are in. Evolved forms keep their earlier stage's TMs and tutors.
   Tutor proposals list the tutor's place and price (tutors are spread over the map in Origin). Egg moves only
   for first stages, not for legendaries, genderless or Undiscovered ones, and (as breeding works) only moves a
   partner of the same egg group can pass on; when the file has no egg groups yet, the line model's are used.
   Translated level-up moves are held back to fitting levels (no 95-power move at level 12).
6. **Designers' moves.** Moves named in `design.wishes`, "Notable moves:" and similar in `design.notes`, and new
   moves from `data/custom_moves.yaml` that the card names, are added (TM moves as TMs, others in level-up).
   Signature moves from cards that are not in the game yet are listed as "describe them under New moves".
7. **Abilities and look.** Moves that make an ability work are added if they fit: Strong Jaw -> bite moves,
   Iron Fist -> punches, Sharpness -> slicing moves, Technician -> weak multi-hit moves of its own types,
   Drought/Chlorophyll/Leaf Mane -> Sunny Day and Solar Beam, Drizzle/Swift Swim -> Rain Dance, Snow Warning and
   Cold-hearted -> Hail, Weather Switch -> Rain Dance + Sunny Day + Weather Ball, surges -> their terrain,
   Prankster -> status moves, Sloth Combat -> Rest/Sleep Talk/Snore, Toxic/Liquid Voice and Punk Rock -> sound
   moves (full list in `ABILITY_SYNERGY`). Words in the look/concept add a move that shows the design when its type
   fits: a lamp or light bulb -> Flash, smoke -> Smokescreen, a beak -> Peck, horns -> Horn Attack, claws -> Slash,
   a shell -> Withdraw; a weight of 150 kg or more gives Heavy Slam to a bulky or Steel Pokemon. Wishes like
   "mostly fighting moves" make that type count more everywhere. An ability named in the wishes but missing from
   the file is flagged.
8. **Archetype.** Two kinds, both used. *Stat archetype*: what its stats and types make it (a fast physical
   Grass/Bug): attacks on the side it does not use get much less weight (0.45-0.6 of a vote, and lower TM/tutor
   scores) when attack and sp. attack are 25+ apart, so it learns Leaf Blade and X-Scissor rather than Energy Ball;
   fast attackers get a priority or pivot move like similar official Pokemon. *Design archetype*
   (`proposals/archetypes.json`, written by Claude from every design field: "shark boxer", "lamp-lit cave
   tortoise"): its themes (punching, biting, sound, light ...) count 1.6x in the votes and in TM/tutor scores, a
   few moves that show it are added, themes that clash with its body are left out, and its role is used unless the
   designers' wishes say otherwise. Run the archetype pass again (ask Claude) for new species.
9. **Design review.** A script cannot judge whether "a little lamp turtle that blinds enemies" should learn Flash,
   so Claude reads each design (look, concept, dex entry, category, notes, wishes, body, size) next to the proposal
   and writes `proposals/design_review.json`: moves to leave out because they clash with the design, a few moves
   the design asks for, and a one-line note. `propose` applies it on every run (only to added moves, names and
   TM/tutor lists checked), then the balance checks below run again. Update it when designs change.
10. **Coverage.** TMs and tutors that hit what its own types cannot score higher, and every final form gets
   coverage like official Pokemon of its kind: about 4 strong moves of other types for attackers, 3 for others,
   chosen from what the similar official Pokemon learn, preferring the types that add most.
11. **Role.** From the final stage's stats (offence, bulk, speed, physical or special, Huge Power counted) and
   role words in wishes/notes: fast/bulky/Trick Room attacker, wallbreaker, wall, support. If the role misses
   its tools and similar official Pokemon have them, they are added: a strong move (75+ power) of each own type,
   a setup move for attackers, recovery for walls, Trick Room only if the notes say so or similar Pokemon have it.
12. **Not broken.** Combos are checked against official Pokemon with about the same total (within 50) and attack
   (within 20). If none of them has the combo, an added move is taken out again ("Not added: ..."); if the
   combo came from the designers, it is flagged ("Check ..."). Checked: same-type priority + setup on a strong
   attacker, Speed Boost + setup, Huge Power + priority, recovery + setup on a bulky Pokemon, rare moves (Shell
   Smash, Quiver Dance, Belly Drum, Spore, Extreme Speed ...), Serene Grace + flinch, Contrary, Simple, banned
   abilities (Moody, Shadow Tag, Arena Trap). Some moves are never added at all (Spore, Shell Smash, Baton Pass,
   OHKO moves, Double Team-style evasion, Water Spout/Eruption ...). Finally the example set's damage is
   compared with every official final stage of about the same total: "Strong" if it beats all of them, "Weak"
   if an attacker is in the bottom 10 %.

## The 4-move picker (reusable)

`scripts/moveset_pick.py` picks 4 moves for one Pokemon at one level from the moves it can know. The proposals
use it for each line's example set; the story team builder can use it per battle (`pick(mon, level, pool)` from
Python, or `--json` from the command line). `battle="double"` (`--doubles`) is for double and multi battles:
moves that hit both foes count more, moves that also hit the partner a little less, and doubles support
(Fake Out, Protect, Follow Me, Tailwind ...) counts more. It works like Showdown's random-battle sets in small: each attack
gets a damage value (power x accuracy x same-type bonus x the right attacking stat x hits x ability, minus for
recharge, charging, self-KO, big self-drops); moves are taken one at a time, each time the one that adds most
(an attack adds the damage it brings against the 18 types beyond what the set already hits, plus a bonus for
the first strong move of each own type; a status move adds a share of the best attack depending on the role).
At most one setup, recovery, status and hazard move; at least two attacks (three for attackers).

## Known limits

- Tutor moves: Origin has about 85 tutor moves in 71 tutor scripts, spread over the towns and paid with items or
  money. Who may learn one is decided inside each tutor's script (a/0/1/2: GetPartyMonSpecies + a chain of
  CompareVarToValue), not by a species table. Proposals only use moves those tutors teach, and
  `proposals/movesets.json` records under `tutor_places` which tutor (place, price) teaches each tutor move, so
  the Origin export can add our species to those scripts' check chains. The single-species tutors (Headbutt,
  Surf, Charge, and the starter moves Blast Burn / Frenzy Plant / Hydro Cannon, which only our starters' final
  forms get) are not handed out otherwise. TM compatibility is a separate per-species list (NARC 273), and
  Origin's Move Reminder (Saffron, Blackthorn; 1 Heart Scale) re-teaches level-up moves.
- TMs: Origin also lets a Pokemon use a TM whose move it learns by level-up.
- Custom abilities (Drunken Rage, Sloth Combat ...) are not understood by the damage maths; read their flags.
- Species without types are skipped. Species without base stats wait (Arvind, 2026-11-12): their moves are
  proposed once the stats are in.
- Rainbro is Stellar (no weaknesses or strengths, Arvind 2026-11-12). The species files cannot hold that type yet, so
  `TYPE_OVERRIDES` in the script sets it. Stellar gets no same-type bonus and its moves are spread over many types.
  Origin HG has no Stellar type (its old ??? slot is Fairy), so the export needs new code for it.
