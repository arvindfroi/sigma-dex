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
| Other DS flashcarts (R4/Acekard family and similar) | Closed or cloned cards, microSD | Widely sold | Many clones, uneven quality, some stop working after a console update; 3DS support varies per card |
| Patch only | Give friends the patch (and optionally a blank flashcart) and let them patch their own HeartGold ROM | The clean option legally | Not plug and play |

## Things to check before buying

1. **The ROM**: size of the finished patched `.nds` (HeartGold is 128 MB; Origin and the
   translation are not documented here) and that it boots on the card at all.
2. **Saving**: one report of a HeartGold hack froze when loading a save on a flashcart, and
   wrong save-file sizes caused trouble. Test a full save, power off and load on the real card.
3. **Which consoles our friends have.** DS, DS Lite and DSi are the easy cases. For a 3DS, check
   the DSpico project's compatibility notes for that model and firmware.
4. **Features that need real hardware**: Pokewalker needs the infrared in the game card, so it
   will not work from a flashcart.
5. **A test run** on an actual console per model before wrapping anything.

## Rules for ourselves

- Keep it to a few copies as gifts. Never sell them and never publish the ROM.
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
- [Retro Dodo: Origin HeartGold gets an English translation](https://retrododo.com/pokemon-origin-heartgold-finally-gets-english-translation/)
