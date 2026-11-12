# Roadmap (2026-11-12)

What is left before our dex is a playable game, sorted by when it fits best and who does it. Details: the export table in
[TRAINERS_AND_ASSETS.md](TRAINERS_AND_ASSETS.md) section 13, ideas in [WHEN_WE_FINALIZE.md](WHEN_WE_FINALIZE.md).
Arvind's rule: everything in front of us before the export starts.

## Now, while the group finishes the dex and the sprites

**The group (website):** designs, dex data, sprites in the studio, claiming trainers once the Characters page opens.

**Legion (ComfyUI and LoRA training, the GPU):**
- Battle frame 2: choose the checkpoint (step 2000 was proposed) and put it in the sprite studio.
- Trainer battle sprites: model C is training; then a trainer studio on the website, built like the Pokemon studio.
- Next models, one at a time on the GPU:
  - overworld trainer sheets (12 frames of 32x32: 3 per direction; the player 24 with running), from the battle sprite,
    like the follower pipeline;
  - VS portraits (96x64 bust, 16 colours) from the battle sprite;
  - later: the intro Pokemon's hop animation, the Ho-Oh/Lugia flying frames (7 x 64x64), the cactus tree, sleeping Snorlax.

**Claude, no GPU needed:**
- Moveset autocomplete for every line (own session; proposals for review, nothing applied without a yes).
- Smart story team builder and the onboarding for claimed trainers (test branch characters-teams).
- Tools: wild-encounter table editor, map-event writer, the list of gift/static/trade species patches, a packer for the
  battle-intro archive (a/1/0/9), ndspy on the Mac.
- Switch the base to the maintained English patch (rc8 or newer) and re-check every offset we use.
- Fix Origin's leftover bugs (Goldenrod entry, S.S. Anne party) and give the message font Æ Ø æ ø.

## When the dex is done

- Claude fills the remaining game data (stats, learnsets, catch rate, exp, gender ...) by comparing with official Pokemon.
- Names final: at most 10 letters, written like official ones.
- Story roles: which of our mons takes each of the 60 essential roles (legendaries, starters, plot Pokemon).
- Shiny maker, icon palettes, cries, battle animation per mon.
- The export script: species data, sprites, icons, followers, footprints, dex text, wild tables, trainer teams (from the
  story team builder), gifts/statics/trades, story text with our names, legendary and trainer intro tables.
- Play-test in the emulator (scripted runs like the intro recordings).

## Later

- Norwegian translation (English patch tools), PokeDaisy support for our game, QoL update (nuzlocke, Move Deleter,
  PC anywhere, auto-run), one-chance legendaries and stuck quests reworked.
- Bigger: new quests and maps (needs a script assembler), wild Pokemon in the overworld, more trainer classes,
  Mega forms for our mons, a native PC version on the decompilation.
