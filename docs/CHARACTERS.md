# Characters with a type (for claiming)

The group plans to replace the game's important characters with themselves. This lists the trainers in Origin
HeartGold that are tied to a type, worked out from their real teams in the ROM (`~/sigma-origin/docs/trainers.md`,
every team of that trainer counted; percent = share of their Pokemon that have the type). Checked 2026-11-11.
A character can be redrawn and renamed; its type follows whoever claims it (our mons must fill the team).

## Gym leaders (16 badges)

| Region | Leader | Type | Share | Special rule in the gym |
|---|---|---|---|---|
| Johto | Falkner | Flying | 100 % | only Flying Pokemon may be used |
| Johto | Bugsy | Bug | 100 % | no type advantage allowed |
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

## Elite Four and champions

| Who | Type | Share |
|---|---|---|
| Lorelei | Ice | 91 % |
| Bruno | Fighting | 83 % |
| Agatha | Ghost | 83 % |
| Koga (Elite Four) | Ghost/Poison | 50 % / 33 % |
| Lance | Flying/Dragon | 83 % / 50 % |
| Lorin | Flying/Dragon | 83 % / 50 % |
| Steven (Hoenn champion) | Steel | 50 % |
| Cynthia (Sinnoh champion) | mixed (Ground, Water) | |

## Villains with a type

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

## Other named trainers with a type

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

## Code names on the website

Important trainers show only a code name and a random order, so nothing is spoiled. The key:

- Trainer A: Petrel (executive)
- Trainer B: Lawrence (executive, Flying)
- Trainer C: Eusine
- Trainer D: Ariana (executive)
- Trainer E: Giovanni (Rocket boss)
- Trainer F: Maxie (executive, Fire)
- Trainer G: Gold
- Trainer H: Koga (Elite Four)
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
- Trainer U: Lorin (Elite Four)
- Trainer V: Cyrus (executive)
- Trainer W: Silver (added 2026-11-12)
- Trainer X: Goh, the One-Ball Man (added 2026-11-12)

Left out on purpose (Arvind makes them himself): every champion (Steven, Cynthia) and the main rival (Blue).
The villains (codes A, B, D, E, F, L, N, R, S, T, V) were taken off the website on 2026-11-12 (Arvind); their codes are kept
here so the remaining letters keep their meaning.

## Text to fix when the characters are replaced

Found while counting dialogue (scripts/character_dialogue.py) and checking claims, 2026-11-16:

- **One person claims both Chuck and Bruno** (Emil has gym-fighting and Trainer Q). That is fine: the two never share a
  scene or a battle. One line has to change, though. In text bank 134 (Chuck's training scene on the beach, line 25)
  Chuck says he is not as strong as "Mr. Bruno of the Elite Four". With one person in both roles, he would be talking
  about himself. When the texts are rewritten, change or drop that comparison.
- **Koga is one person in two roles.** In Origin he is the Fuchsia gym leader (gym-poison, 4 teams, including the
  Venonat 80 battle) and an Elite Four member (Trainer H). Janine is only a Ninja Girl trainer there. His story lines
  (78 text boxes, banks 090, 329, 354 and 506) belong to both roles. If two different people claim gym-poison and
  Trainer H, the story has two people saying one person's lines. Make it one role, or let only the same person claim
  both.
