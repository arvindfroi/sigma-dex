# Cries

Every Pokemon gets its cry in the **CRY** tab of its page on the website: press **CREATE**, listen, **RETRY** until
one fits, then **SAVE**. Earlier tries stay in the list, so a good one is never lost.

## What a cry is

A cry is a **recipe**, not a sound file. It names the official cries it starts from (HeartGold's own, by national dex
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

Each try lists its reasons in the top screen. RETRY uses a new random seed. The seed is saved, so a recipe can be
rebuilt.

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
