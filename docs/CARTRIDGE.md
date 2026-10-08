# Physical copies (cartridges) - under consideration

Status: **being considered, nothing decided.** The idea is to give friends the game as a
"plug and play" Christmas present on real Nintendo DS hardware. Nothing here has been bought or
tested. Checked on 2026-10-08, from reviews and articles only.

## What is possible

- A real DS or 3DS game card cannot be made for our hack. The only way to run it on real
  hardware is a **DS flashcart**: a cartridge that looks like a DS game but reads the ROM from a
  microSD card.
- Our game is a DS ROM (see [ENGINE.md](ENGINE.md)), so it needs a **DS-mode** flashcart. A 3DS
  runs it only in DS mode, never as a native 3DS game. A GBA cartridge is not an option.

## Candidates

| Option | What it is | For | Against / unknown |
|---|---|---|---|
| **DSpico** (LNH Team) | Open-source flashcart on the RP2040; microSD, FAT32; front-end Pico Launcher, game loader Pico Loader | Cheap (about $20 / £10 reported); open hardware and firmware, so it can be kept alive by the community; reported to work on DS, DS Lite, DSi and 3DS (DS software and DSiWare only) | Young product; reports of lockups with 64 GB and 128 GB cards (use a small FAT32 card); sources disagree on how well it works on a 3DS; no list of tested 3DS models or firmware found |
| Other DS flashcarts (R4/Acekard family and similar) | Closed or cloned cards, microSD | Widely sold; Acekard 2i and the original R4 with the Wood kernel are known to be fine | Many clones, uneven quality, some stop working after a console update; 3DS support varies per card; cheap "R4i Gold 3DS"-type clones often fail on HeartGold |
| Patch only | Give friends the patch (and optionally a blank flashcart) and let them patch their own HeartGold ROM | The clean option legally | Not plug and play |

## Things to check before buying

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

## Rules for ourselves

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

## Open

- Does the group want the gift version at all, or only the patch?
- Which card (DSpico first, since it is the one proposed).
- Who tests on which console.

## Sources

- [LON.tv: DSpico review](https://blog.lon.tv/2026/02/19/dspico-review-an-affordable-flash-cartridge-for-nintendo-ds-handhelds/)
- [omgmog: The DS Pico might be the last DS flashcart you'll ever need](https://blog.omgmog.net/post/ds-pico-flashcart/)
- [Hackster: This Is the Perfect Nintendo DS Flashcart](https://www.hackster.io/news/this-is-the-perfect-nintendo-ds-flashcart-8cf6b7868dff)
- [Notebookcheck: DSpico, the last flashcart the Nintendo DS will ever need](https://www.notebookcheck.net/DSpico-The-last-flashcart-the-Nintendo-DS-will-ever-need.1222851.0.html)
- [Time Extension: DSpico review](https://timeextension.com/reviews/dspico-this-insanely-cheap-open-source-nintendo-ds-flash-cart-is-utterly-essential)
- [GBAtemp: HeartGold freezing on flashcarts (anti-piracy)](https://gbatemp.net/threads/ghost-theme-problem.433043/post-6629770)
- [GBAtemp: HG/SS card compatibility thread](https://gbatemp.net/threads/pokemon-hs-ss-card-compatibility-thread.213309/post-2674548)
- [Retro Dodo: Origin HeartGold gets an English translation](https://retrododo.com/pokemon-origin-heartgold-finally-gets-english-translation/)
