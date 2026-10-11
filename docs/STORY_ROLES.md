# Story roles: which Pokémon Origin HeartGold's story needs, and who from our dex takes them

Made 2026-10-08 from Origin HeartGold v4.0.3 + English patch rc3 (its own scripts, trainer parties,
map objects, encounter tables and text, read locally). Our side: `data/species/` on the same day
(99 of 151 slots filled). Companion to [DEX_ANALYSIS.md](DEX_ANALYSIS.md) (what the dex lacks
compared with the official generations) and [DEX_REPLACEMENT.md](DEX_REPLACEMENT.md) (what does
not follow automatically when a slot is replaced).

Everything here is a **suggestion** for the group. "Fits" means an existing mon matches the role
well; "partly" means it could work but the designer should agree; "new" means nothing in the dex
fits and a new design is proposed.

## The size of the problem

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

## 1. Pokémon the story needs by name

Ordered by how much the story uses them. "Text" = how many lines outside the Pokédex name it.

### Starters and partners

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

### Story Pokémon

| Origin Pokémon | Where it matters | Our candidate | Status |
|---|---|---|---|
| Meowth / Persian (52-53) | Team Rocket's **talking Meowth** (Jessie and James's trio); text 200 | — | **new**: a cat-like, mono Normal Rocket sidekick (mono Normal is a gap) |
| Mew (151) | Team Rocket closes Mt. Moon to catch it (early Kanto story); gift on Five Island; text 95 | Sandrema (mythic, Fairy/Ground) | partly: Sandrema could be "the Mew" or "the Celebi", not both |
| Mewtwo (150) | Gift at Indigo Plateau; Giovanni's ace; text 85 | Cryoblade (Dark/Ice, 605, "Frozen Executioner") | partly: as Team Rocket's lab-made weapon. Otherwise **new** |
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

### Legendaries and mythicals

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

### Pseudo-legendaries

Five pseudo-legendaries carry big parts of the story (counted in all trainer parties and gifts):

| Line | Party slots | Who uses it | Kanto/Johto native? | Ours |
|---|---|---|---|---|
| Dratini → Dragonite | 28 | Lance, Lorin, Clair, Charon; Dratini gift | yes | Balleisk → Greation → Ultragon |
| Larvitar → Tyranitar | 19 | Ariana (every battle), Giovanni, Marauder, Silver; Larvitar in Mt. Moon | yes | **new**, or Obsidog line (2 stages, 555) |
| Bagon → Salamence | 20 | Lance, Lorin, Archer, Lawrence, Marauder; static battle on Route 34 | no (Hoenn) | guest, can stay real |
| Beldum → Metagross | 21 | Steven, Jasmine | no (Hoenn) | guest |
| Gible → Garchomp | 22 | Cynthia, Giovanni, Ariana, Clair | no (Sinnoh) | guest |

So one more pseudo-legendary is needed (Tyranitar's: Rock/Dark, desert or mountain), unless
Obsidog gets that role.

### Mythicals

Mew (Team Rocket's Mt. Moon chase, Five Island gift, text 95) and Celebi (Ilex Forest, text 80)
are the two the story leans on; Manaphy (Alto Mare, text 54) and Jirachi are smaller, Arceus has
forms. With Sandrema taking one of Mew or Celebi, **at least one new mythical** is needed for the
other.

## 2. Types the trainers need

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
| Dragon | 8 | Clair, Lance/Lorin (6 each) | OK |
| Electric | 9 | Lt. Surge (6) | OK |
| Steel | 9 | Jasmine | OK |
| Ghost, Bug, Normal, Grass, Rock, Poison, Dark, Water | 11-17 | Morty/Agatha, Bugsy, Whitney, Erika, Brock, Koga, Rocket, Misty | OK |

Trainers can also keep a few real Pokémon in their teams, so "barely" is not a blocker.

## 3. The first hours

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

## 4. Proposed new mons, by priority

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

## 5. The title screen model

HeartGold's title Ho-Oh (`a/0/4/6` member 25, internal name `houou_test`) is **real-time 3D, not
prerendered**: 1009 polygons (328 triangles + 681 quads, about 1690 triangles), 2360 vertices,
28 bones, 20 materials, textures inside the model, plus a bone animation (member 26), texture
scrolling (27), material animation (28) and texture swaps (29). Origin did not touch it. A
replacement is a low-poly rigged model of about the same size (the DS draws at most about 2048
polygons per frame), animated in Blender and converted to the DS model format. SoulSilver's Lugia
is similar (1481 polygons, 32 bones).

## 6. Things to keep in mind

- **Place names contain species names**: Diglett's Cave, Slowpoke Well. The automatic name swap
  must leave place names alone (or rename them on purpose).
- Some roles need **extra map figures** (Snorlax, Sudowoodo, Lapras, Red Gyarados, tailless
  Slowpoke, big Ho-Oh/Lugia): see DEX_REPLACEMENT.
- **Slots with special code** (Unown, Pichu, Arceus, Giratina, Deoxys, ...) are listed in
  DEX_REPLACEMENT. Sigmanian Unown in Unown's slot is the one place where we do it on purpose.
- Trainer teams are data and easy to change. A boss can get our mon or keep a real one.
- Roles here are based on types, names and the few concept texts we have. Most of our mons have
  no concept or description yet, so the designers should check every "fits" and "partly".
