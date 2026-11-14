# Cries

Every Pokemon gets its cry in the **CRY** tab of its page on the website: press **CREATE**, listen, **RETRY** until
one fits, change it with the sliders if you like, then **SAVE**. Earlier tries stay in the list, so a good one is never
lost.

## Using it

- **CREATE / RETRY** makes a new random cry. The page does not say which official cries a try starts from: that is
  not important to the person making it (Arvind, 15 Nov 2026). It is still kept in the saved recipe.
- **The sliders** change the try that is playing. Moving one makes the cry again and plays it:

  | Slider | Recipe field | Range |
  | --- | --- | --- |
  | Pitch | added to every voice's `semi` (each stays within -12 to +7) | -8 to +8 steps |
  | Length | `stretch` | 0.7 to 1.4 |
  | Glide | `sweep` | -6 to +6 |
  | Brightness | `tone` | -1 to +1 |
  | Wobble | `vib.depth` (0 = off) | 0 to 1 |
  | Echo | `echo.gain` (0 = off) | 0 to 0.6 |
  | Rough | `drive` | 0 to 1 |
  | Buzz | `ring.mix` (0 = off) | 0 to 0.6 |

  **UNDO THE CHANGES** puts the sliders back. A changed try is marked ✎. SAVE stores the changed recipe, and its
  `reasons` get a last line such as "Changed by hand: pitch 3, echo 0.3". The engine's `knobsOf` and `tweak` do this.
- **Its line** plays the saved cries of its relatives, to compare.
- **Own sounds** (added 15 Nov 2026): **UPLOAD A SOUND** takes a sound file (.wav, .mp3, .m4a; .ogg where the
  browser reads it), and **RECORD** takes up to 4 seconds from the microphone. The page:
  - cuts the silence before and after;
  - mixes it to mono at 13379 Hz;
  - keeps at most 2 seconds;
  - makes it as loud as the official cries.

  The sliders work on it as on any try. A saved cry can always be replaced later. Use only a sound you made yourself
  or may use freely, never one from a game or a show: a saved sound is public in the dex.

## Own sounds in the files

A cry from an own sound has a voice `{"own": true, "semi": ..., ...}` instead of `{"dex": ...}`. On the website the
save carries the sound as `audio`, base64 of mono 16-bit PCM at 13379 Hz, at most 2 seconds (71 356 characters). The
database allows such a row up to 100 000 bytes; see `supabase/migrations/2026-11-15_own_cries.sql`.

The sync (`import_web.py`) writes:
- the sound to `assets/cries/<pokemon>.wav`;
- the recipe to `assets/cries/<pokemon>.json`, with `"audio": "assets/cries/<pokemon>.wav"`.

`build_site.py` copies the sound to `site/art/<pokemon>/cry.wav`.

When a relative's cry has an own sound, CREATE for the next stage starts from that sound too. Its save gets its own
copy. The game export renders the recipe with the .wav as the `own` source and encodes the result like any other cry.

## What a cry is

A cry is a **recipe**, not a sound file (except an own sound, see below). It names the official cries it starts from (HeartGold's own, by national dex
number 1-493, the same way footprints borrow `hgss:<dex>`) and says how they are bent. No Nintendo audio is stored in
this repo. The sync writes the recipe to `assets/cries/<pokemon>.json`, and the species file's `assets.cry` points at it.

```json
{"layers": [{"dex": 258, "semi": -2.1, "gain": 1, "at": 0, "rev": false},
            {"dex": 418, "semi": -4.0, "gain": 0.4, "at": 0.06, "rev": false}],
 "stretch": 1.1, "sweep": -1.5, "vib": {"rate": 6, "depth": 0.3}, "ring": null, "echo": {"ms": 90, "gain": 0.25},
 "tone": -0.2, "drive": 0.1, "len": 1.6, "seed": 123, "reasons": ["Starts from Mudkip's cry: ..."]}
```

| Field | Meaning |
| --- | --- |
| `layers` | 1-3 official cries mixed together: `semi` = pitch in semitones (-12 to +7, played faster or slower like a tape, so length changes too), `gain` = loudness, `at` = start in seconds, `rev` = played backwards |
| `stretch` | longer or shorter without changing the pitch (0.7-1.4) |
| `sweep` | the pitch glides this many semitones from start to end |
| `vib` | a wobble in the voice (rate per second, depth in semitones) |
| `ring` | a metallic buzz (ring modulation) |
| `echo` | one echo (delay in ms, loudness) |
| `tone` | -1 darker to +1 brighter |
| `drive` | a rough edge (0-1) |
| `len` | at most this many seconds (never above 1.6; HeartGold's sound memory is small) |

The output is mono at **13379 Hz**, the rate of HeartGold's cries, so the website already sounds as clear as the game.

## How CREATE chooses

The engine is `scripts/cry_engine.js` (`suggest`). Like the moveset tool, it looks at the Pokemon's own data:

1. **Its line comes first.** If a relative already has a saved cry, it starts from that one: each later stage is 2-3.5
   semitones lower and a little slower, earlier stages higher, sometimes with a low extra voice for the bigger one. On
   top of that comes one small random change, such as a wobble, an echo or a rougher edge. So a line sounds related.
2. **Otherwise it starts from official Pokemon like it.** Each of the 493 is scored on:
   - its footprint (`hgss:<dex>`: the official mon it was matched with, and that mon's line);
   - same body plan (the studio's 14 shapes);
   - shared types and egg groups;
   - the same stage;
   - legendary or not;
   - size (height, weight);
   - base stat total;
   - body colour.

   One of the best 14 is picked at random, weighted by the score. A second voice comes from another line. Official
   mons that other Sigma mons already use are a little less likely. The facts are in
   `data/engine/official_species.json`, which `scripts/fetch_official_species.py` writes from PokeAPI's public data.
3. **Pitch** follows stage and size: babies higher, big final stages and legendaries lower, plus a random part.
4. **Effects** come from its types, with random amounts and never more than three at once. For example:
   - Electric and Steel: a buzz;
   - Ghost: an echo or a backwards voice;
   - Water: a wobble;
   - Dragon, Rock and Ground: darker and rougher;
   - Flying: a rising pitch;
   - Fighting: cut short.

   Heavy mons are drawn out.
5. **Never just an official cry with a new name.** If a try is too close to where it started, it is bent further or
   gets a second voice.

Each recipe keeps its reasons (not shown on the page). RETRY uses a new random seed. The seed is saved, so a recipe
can be rebuilt.

## On the website versus in the game

The website plays the official cries from PokeAPI's public archive (`github.com/PokeAPI/cries`, the "legacy" DS-era
files). Browsers that cannot read `.ogg` load a small decoder from jsDelivr. The game export will run the same
`cry_engine.js` in Node on the ROM's own cries:

1. Read the IMA-ADPCM SWAV from `gs_sound_data.sdat`.
2. Render the recipe.
3. Encode the result with `ntrWavTool` (mono, 13379 Hz, ADPCM).
4. Put it in the Pokemon's cry slot. See `docs/TRAINERS_AND_ASSETS.md` section 5.1. In Origin every species has its
   own wave archive, so this is a data swap.

The game can therefore sound slightly different from the website, because the source recordings differ a little. The
export step is not built yet; it waits until every asset exists.
