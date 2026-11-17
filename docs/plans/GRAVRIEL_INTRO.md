> Status 2026-11-18: done. Gravriel is locked (see [LEGEND_CUTSCENES.md](../LEGEND_CUTSCENES.md)); this was the plan on the way there.

# Gravriel: slik gjør vi ham enda bedre

Status nå (v3), testet i emulator, ikke committet:
- **3D og maling:** 3D-modellen er laget fra et turnaround-ark Qwen tegnet. Fjeset bruker modellens egen form, malt mørkt med lyst nebb.
- **Øynene:** halvåpne, runde og lysende, med tunge lokk og mørke ringer.
- **Scenen:** grønnblå tåkenatt med skipsvrak.
- **Sekvensen:**
  1. lys under vannet
  2. han stiger med lukkede øyne
  3. øynene åpner seg og stirrer
- **Plass:** 329 av 1024 tiles, altså god plass til mer.

## 1. Fjeset og øynene (viktigst)

Problemet er at øynene og nebbet blir laget av meg, ikke tegnet. Derfor blir de aldri helt like tegningen.

Forslag:
1. Qwen tegner et rent nærbilde av ansiktet rett forfra, i designets stil: mørk uglemaske, beige nebb, store blå øyne under tunge lokk.
2. Jeg legger det på fjeset som et ferdig «klistremerke», slik hatteemblemet til Sabertann ble gjort. Da blir øyne, maske og nebb nøyaktig som tegningen.
3. Bare den blå irisen får glød.
4. Du godkjenner nærbildet før noe bygges.

## 2. Bedre farger på hele kroppen

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

## 3. Sekvensen

- **Øynene åpner seg før fadingen.** Nå skjer det for sent. Jeg flytter det fram, og lar dem gløde sterkere et øyeblikk.
- **Lyset under vannet:** større og tydeligere. Det pulserer og vokser mens han nærmer seg overflaten.
- **Tregere stigning med flere bilder.** Det er plass til 4–6 bilder til (tiles).
- **Tang som driver:** skjegget og fillene svaier sakte fra bilde til bilde, mer jo lenger ned på tråden.
- **Ringer i vannet** som vokser der han bryter overflaten, og vann som drypper av hatten.
- **Tåke foran ham:** lave tåkebånd i forgrunnslaget, så han stiger opp gjennom tåka.

Kameravendingen du foreslo krever endring i spillkoden. Bakgrunnene i scenen kan ikke roteres. Det kan gjøres med en kodepatch, men det er et stort stykke arbeid. Jeg anbefaler å vente med det til resten sitter.

## 4. Når skal man se hvem?

Origin er bygd på HeartGold, så introen viser én figur. Tre muligheter:
- Sabertann i introen, og Gravriel et annet sted, for eksempel på tittelskjermen eller i en senere scene.
- Tilfeldig figur ved hver oppstart. Det krever en liten kodepatch.
- To separate spillversjoner, slik HeartGold og SoulSilver er.

## 5. Arbeidsmåte

- Nærbilder sendes til godkjenning før store bygg.
- Videoen viser alltid alle fire side ved side: Lugia, Ho-Oh, Sabertann og Gravriel.

## Rekkefølge jeg foreslår

1. Fjes-klistremerke fra et Qwen-nærbilde. Du godkjenner.
2. Sekvensen: tidligere øyeåpning, sterkere lys under vannet, flere stigebilder, svaiende tang og tåke foran.
3. Test av Hunyuan3D-2.0 Paint Turbo for kroppen. Krever ja til ca. 14 GB nedlasting.
4. Bestem hvor Gravriel skal vises (punkt 4).
