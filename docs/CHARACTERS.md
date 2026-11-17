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

## Facts to know when claiming (checked against the game, 2026-11-17)

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

## Text to fix when the characters are replaced

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
