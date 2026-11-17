# Steven og Cynthia: champions som kommer tilbake som en overraskelse

Bestemt av Arvind 2026-11-17: rollene til Steven og Cynthia skal spilles av folk Arvind kjenner. Overraskelsen er at de kommer tilbake som champions.

> «Ja vi kan bare si at de skal hjem da egentlig. Også på ryktene så fikser vi det.»

Kort sagt:
- De følger deg gjennom Kanto som i dag.
- Etter den første Hall of Fame-en sier de bare at de skal hjem.
- Ingen i Johto nevner dem med navn.
- Først i siste kapittel skjønner spilleren at de er blitt champions.

Steven og Cynthia kan tas på karaktersiden igjen fra 2026-11-17, som Trainer Y (Steven) og Trainer Z (Cynthia), commit adbb7cf. Bare Blue fyller Arvind selv. Romansen beholdes (Arvind: «Romance er bare morsomt»). En kort versjon av planen står i `docs/CHARACTERS.md` på main.

Alle tall under er tekstbank#linje i EN-patchen (rc8). Kildene er tekstbankene i `~/origin-en/work/translate/banks/a027/` og skriptene, lest med `scriptdump.py`.

## Slik er det i Origin i dag

| Når | Hva skjer | Hvor i dataene |
|---|---|---|
| Kapittel 1–13 (Kanto) | De er utvekslingselever i Viridian og reisefølget ditt gjennom Kanto. Du kjemper mot dem og med dem, og de kommer blant de åtte beste i Indigo Conference. | trenere 2–3, 63–65, 180, 210, 263–265, 270–271, 502, 504, 635, 638 |
| Etter første Hall of Fame | Avskjeden. Steven står utenfor skolen i Viridian med Metagross, og Cynthia gråter inne med Garchomp. Den er frivillig: de står bare der. | flagg 1107 slås på av Oak-scenen (skript 738 L558) eller etter at Yellow er reddet (skript 115 L3604). Steven: sone 50 objekt 29, tekst 445#128. Cynthia: sone 159 objekt 14. |
| Johto (kapittel 15–31) | De er ikke å se. Det finnes bare rykter, og navnene står i to romanse-menyer. | se del 2 og 3 |
| Siste kapittel | Avsløringen på Indigo Plateau. Etterpå er de partneren din i kamper mot Team Rocket. | skript 923 rundt L3843, tekst 608#48–55; trenere 490 og 491 |
| Etter historien | Steven er på besøk hos Norman i Goldenrod. Cynthia besøker skolen i Viridian. Med romanse kommer det også dater. | flagg 2322 (Steven) og 2321 (Cynthia) slås på av siste Hall of Fame (skript 822 L2550–L2554) |

## Del 1: Avskjeden (de skal bare hjem)

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

## Del 2: Ryktene i Johto (navnene ut)

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

## Del 3: Navnene i romanse-menyene

Navnene står som valg to steder i Johto, men bare hvis romanse-sporet er åpnet:
- Spåkona i Goldenrod (583#49 og 583#60).
- Den gamle mannen i Dream World (586#8 og 586#13).

Det avslører ikke at de er champions, men minner spilleren om at de finnes. Hva vi gjør her, henger sammen med åpent spørsmål 1.

## Del 4: Avsløringen (beholdes som den er)

- **Rett før:** i starten av siste kapittel sier Goodshow at han har bedt ligaene i Hoenn og Sinnoh om å sende sine sterkeste trenere (537#145). Det er et hint, men det sier ikke hvem.
- **Øyeblikket:** på Indigo Plateau stopper Cyrus og Charon deg. Cyrus spør hvem de to er, og Charon sier at de ikke er i arkivet deres. Så sier Steven «Long time no see», Cynthia «Did you miss us?», og Cyrus roper at de er de nye championene i Hoenn og Sinnoh (608#48–55, skript 923).
- **Forklaringen etterpå:** Hoenn og Sinnoh har startet egne ligaer etter mønster fra Kanto, og begge har blitt champion der (608#128, 608#142–143).

## Del 5: Kampene når de kommer tilbake

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

## Del 6: Utseende (spillet deler det allerede i to)

| | Steven | Cynthia |
|---|---|---|
| Figur på kartet i Kanto | sprite 142 | sprite 143 |
| Figur på kartet i siste kapittel og etter historien | sprite 295 | sprite 296 |
| Mon som følger med på kartet | Metagross (sprite 837) | Garchomp (sprite 918) |
| Trenerklasse i Kanto (kampbilde og tittel) | «Hoenn Trainer» | «Sinnoh Trainer» |
| Trenerklasse i siste kapittel og etter historien | «Hoenn Champion» (720#127) | «Sinnoh Champion» (720#128) |

Hver person får altså et skoleutseende og et champion-utseende uten ny kode. Vi tegner begge. Navnet står per kamp i tekstbank 719. Tittelen «Hoenn Champion» og «Sinnoh Champion» vises bare i kamper i siste kapittel og etter historien, så den røper ingenting før avsløringen.

## Arbeidsrekkefølge

1. Arvind svarer på de åpne spørsmålene under.
2. Personene får navn og tegninger: figur på kartet tidlig og sent, og kampbilde tidlig og sent.
3. Tekst: del 1 og 2 her, og alle andre linjer der navnene står (de byttes uansett når rollene får nye navn). Tekstbankene i EN-patchen er JSON og bygges med deres msgtool. Kjør deres QA-sjekk for bredden på tekstboksene.
4. Test i emulatoren:
   - En lagring rett etter første Hall of Fame: avskjeden i Viridian.
   - En i Johto: treneren i Mt. Mortar, Mt. Silver og Silver Conference, og Rowan i Goldenrod.
   - En i siste kapittel: avsløringen.

## Åpne spørsmål til Arvind

1. ~~**Romanse.**~~ Avgjort 2026-11-17: den beholdes («Romance er bare morsomt»).
2. **Hint.** Helt uten hint i Johto, eller ett lite hint? For eksempel kan treneren i Mt. Mortar si at Hoenns nye champion en gang trente i Kanto.
3. **Regioner.** Skal de fortsatt komme fra Hoenn og Sinnoh, eller får de egne steder?
