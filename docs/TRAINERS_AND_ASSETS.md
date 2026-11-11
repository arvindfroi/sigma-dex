# Trainer sprites, missing assets and battle animations

Research note, 2026-11-11. It answers three questions from Arvind:

1. How were the sprite LoRAs made, and how do we reuse the recipe for **trainer sprites**?
2. What other assets does the game need, and which are missing?
3. Do Pokemon have animations in battles, and what must we provide?

Labels used below: **Verified** = read in a file or measured in this session (path given). **Inferred** = a
reasonable conclusion that no file confirms. **Unknown** = could not be found.
Nothing here puts Nintendo data in the repo: the numbers were measured on local copies
(`~/sigma-hgengine`, `~/sigma-origin`) and only the numbers are written down.

---

## 1. How the sprite LoRAs were made, and a plan for trainers

### 1.1 The recipe in one page

**Idea (verified, docs/LORAS.md lines 1-30).** A word-only LoRA (SDXL, tried first) knew the style but redrew
Pokemon it already knew. So we switched to **edit LoRAs**: they learn a step from *pairs of pictures*
(front sprite in, icon out; front in, follower sheet out), and the real sprites of real Pokemon are the training
data. Our own designs only appear at use time. Arvind decided on 2026-10-05 that imitating the games' style
is acceptable; the game images stay local and never go in the repo (memory: sigma-lora-training).

**Three generations of tooling (verified):**

| Generation | Base model | Trainer | Used for | State |
|---|---|---|---|---|
| 1 (5 Oct) | NoobAI-XL v1.1 (SDXL) | kohya sd-scripts, dim 32, 8 epochs, about 45 min, 1438 icons at x16 on white | icon v1 (text LoRA) | dropped: knew Pokemon, not our designs |
| 2 (6-13 Oct) | Qwen-Image 2.1 (edit model, RGBA VAE) | ai-toolkit (ostris), arch `qwen_image_2`, rank 32 | icon v2, follower v1-v6, back v1-v6, front v7/v7d, art v1 | icon v2 and front v7 still used; the rest replaced |
| 3 (14 Oct on) | FLUX.2 Klein base 4B (Apache-2.0) | ai-toolkit, arch `flux2_klein_4b`, rank 32 | follower, icon, back, sketch-to-art | **current default**, free on the Legion |

**What the studio uses today (verified, docs/STUDIO.md "What draws what", lines 28-34):**

| Step | Model | Picked checkpoint |
|---|---|---|
| Cut the creature out of a card or sheet | base Qwen-Image (no LoRA) | - |
| Front 80x80 | Qwen front v7 (`fv7_600`, `fv7d_200`) at strength 0.75, cfg 2.5 + negative, 4-8 seeds, then `unfake` + loose-pixel clean-up, then a picker | v7 600, v7d 200 |
| Back 80x80 | Klein back v2 (needs a rear-view drawing as image 3) | step 2500 |
| Icon 32x32 (2 frames) | Klein icon v1 | step 2500 |
| Walking sprite (follower, 8 frames) | Klein follower v3 | step 2000 |
| Sketch to official-style art | Klein style v2 (pairs: 3D render / sprite / icon of a species to its artwork) | step 2500 |

Approved checkpoints are kept in `D:\LocalAI\lora-train\approved\` with sha256 recorded in `results\arvind_picks.json`
(LORAS.md lines 1249-1261, 1352-1356).

### 1.2 The Klein recipe (the one to copy for trainers)

Read from the real training config on the Legion, `D:\LocalAI\lora-train\pod2\cfg\follower_klein_v3.yaml`
(read-only over `ssh pc`). **Verified.**

| Setting | Value |
|---|---|
| Base | `flux2_klein_4b` (Comfy-Org split files in `D:\LocalAI\ComfyUI\models\diffusion_models`), `quantize: true`, `quantize_te: true`, `low_vram: true` |
| LoRA | `linear: 32`, `linear_alpha: 32` (rank 32) |
| Optimiser | `adamw8bit`, `lr 1e-4` constant, `timestep_type: weighted`, flowmatch |
| Batch | `batch_size 1`, `gradient_accumulation 2` (effective 2), gradient checkpointing on |
| Resolution | 512 for sheets (icon sheet 512x256, follower sheet 512x256, back 320x320) |
| Steps | follower v3 4000 (best 2000), icon v1 3000 (best 2500), back v2 3000 (best 2500), style v2 3500 (best 2500) |
| Saves and samples | every 250 steps, 12 checkpoints kept, progress pictures with 5 fixed test creatures (3 held-out real ones, 2 of ours), `guidance_scale 4`, `sample_steps 25` |
| Speed and hardware | Legion RTX 5080 Laptop 16 GB: 2.75 s/step (follower v1), 3.1 s/step (icon), 3.6 s/step (follower v3), 4.5-6.5 s/step (back with 2-3 references). About 3 h per LoRA. Free. |

**Dataset building (verified, LORAS.md 1062-1260):**

- **Where the references come from.** hg-engine's graphics folder (`~/sigma-hgengine/data/graphics/sprites/<id>/`: `male/front.png`,
  `male/back.png`, `icon.png`, `overworld.png`) copied to the Legion (`data\hg-engine`, `hge_sprites.tgz`),
  plus PokeAPI sprites and official artwork (`data\pokeapi-sprites`), Bulbapedia text and Showdown data.
  Never in the repo. About 940 follower sheets and 968 icons/backs after dropping near-duplicates; 40 species are
  held out of every training set so we can test on real creatures the LoRA never saw.
- **Targets.** The whole picture the game uses, scaled up with nearest neighbour (4x or 8x) and put on a flat
  **magenta** background (no hidden colours, no transparency problems). Follower: all 8 frames in one 512x256 sheet.
  Icon: the 2 frames side by side. Back: the real 80x80 frame including its position.
- **Inputs.** One picture per input slot (Arvind's rule, memory lora-input-rules: never two pictures in one image).
  Front 4x on white as image 1; back as image 2 (follower); official artwork as a further image (back).
  Real extras are a *training aid* only and are left empty in part of the examples so that our mons (which never
  have the real extra) work.
- **Captions.** Fixed instruction + the Pokemon's type and stage + **body shape** (PokeAPI's 14 shapes in plain words)
  + **look** (first paragraph of the Bulbapedia Biology section) + **how it moves** (walks on two/four legs, floats,
  flies, from shape, Levitate and measured leg movement). Each part is dropped in 15 % of examples. No Pokemon names.
  Our mons need `design.body_shape`, `design.movement`, `design.look` (the studio asks for them; 138 of 150 species have them).
- **Pairs for edit LoRAs.** Real pairs only (front to its own icon, front to its own follower sheet). A synthetic-sketch
  pair set was built but not trained: Arvind did not believe in it (LORAS.md line 1417).

**How results were judged (verified):**

1. Progress pictures every 250 steps on fixed test creatures, with 2 seeds, next to the real sprite when it exists.
2. Side-by-side sheets of all candidate checkpoints, 10 mons x 2 seeds; **Arvind picks** (sheets are sent to him as soon as they exist).
3. Metrics only to throw out broken results: DINOv2 similarity, a species classifier, a "real versus ours" realness judge
   (picker v2, held-out accuracy 0.927; icon judge 0.854), format rules from `scripts/sprite_quality.py`.
4. Held-out real species must win at least 27 of 40 for a new version to replace the old one.
5. After every round a written good / bad / improve review goes into docs/LORAS.md (memory: lora-rounds-document-and-review).

**Traps and lessons (verified; pick the ones that matter for trainers):**

- hg-engine's `back.png` holds the *shiny* palette; backs and shiny must be recoloured to the front's palette.
- Near-duplicates (DP, Pt and HGSS share sprites) make the model memorise: drop them, weight species equally.
- Too many steps: edit LoRAs start copying the input. Peak was at 1-1.5 passes over the data; always pick a checkpoint, never "the last".
- One seed is not evidence; use 4-8 and a picker. Seeds change icon size and boldness a lot.
- Pixel grid: 640 px for 80 px = one latent cell per pixel on Qwen (16x VAE cells). Train and run at the size the trainer's resize rule expects
  (`match_target_res`), otherwise it "works" but is worse.
- Transparency: Qwen's VAE is RGBA, but a white background guessed back as "near white" eats light parts. Magenta flat backgrounds
  (Klein) or true alpha (Qwen) both work; "white and guess" does not.
- ai-toolkit: sample prompts crash with references unless patched (`v6cfg\patch_sdtrainer.py`); OOM only prints "skipping batch"; its EMA has no warm-up (use 0.99);
  resume picks the newest file whose name starts with the job name; delete `_t_e_cache` folders after a run (D: filled up once with 290 GB).
- Legion habits (memory legion-long-runs): start long jobs through `cmd.exe /c ... > log`, never kill a queue whose child runs, PowerShell logs are UTF-16,
  never `pkill -f` a pattern that is in your own ssh command.
- Keep provenance of approved results (script, LoRA file, seed, inputs) in docs/LORAS.md; never swap an approved step without a pixel comparison.
- Colours differ per kind of sprite (docs/LORAS.md 1263-1318): back = front palette exactly; follower = its own palette near the front's;
  icon = one of the 3 (HeartGold) or 6 (hg-engine) shared palettes. Rules are in `scripts/sprite_colours.py`.
- Sizes follow the real data: a front fills the 80x80 frame by the creature's height; measure the real fill before choosing a size box.
- RunPod is only for what the Legion cannot do (96 GB models, many references); about $20 per round, always terminate the pod ("avslutte").

### 1.3 What a DS trainer sprite is (measured)

All of this is **verified** from `~/sigma-hgengine` (folders `data/graphics/trainer_gfx`, `trainer_back_gfx`, `overworlds`), the
hg-engine wiki page `documentation/wiki/Adding-New-Trainer-Classes.md`, and Origin's own files in `~/sigma-origin/x_spike_backup/files`.

**Battle sprite of a trainer (front, the person you fight):**

| Property | Value |
|---|---|
| One frame | 80x80 pixels, 4 bits per pixel, 16-colour palette, index 0 transparent |
| Files per class in hg-engine | `NNN_enc.png` (160x80: frame 1 and frame 2 side by side, second half empty if not animated), `NNN.png` (80 x 80*frames, "garbled" tile order for the cell bank), `NNN_anim.json`, `NNN_cell.json`, `NNN_enc.png.key` |
| Classes | **129** in hg-engine (000-128). Origin's `a/0/5/8` has 645 members = 129 x 5 (NCGR, NCLR, NCER, NANR, extra): the same set |
| Animated or not | 92 of 129 are a single 80x80 frame (static). 37 are taller: 80x240 (25), 80x400 (4), 80x640 (3) and a few other lengths: more frames (a pose change when the battle starts) |
| Colours used | median 16 (including the transparent one), 12 at the lowest |
| Size of the figure | median 43 px wide x 72 px tall (min height 41, max 80), standing 1 px above the bottom edge (median), covers about 22 % of the frame (a creature front: median 21 %) |
| Palette | one palette per class, no shiny; no shared palettes (unlike icons) |

**Trainer back sprite (the player character's back):** `data/graphics/trainer_back_gfx`: **17** entries, `NN.png` is 80x640 (8 frames of 80x80: the
throw animation) or 80x400 (5 frames). Origin's `a/0/0/6` has 85 members = 17 x 5. Only the player-character classes use these
(Ethan, Lyra, Barry and similar). Our game has a player from Pallet Town (docs/STORY_ROLES.md), so a replaced player needs this too (not needed for NPCs).

**Where trainer sprites live in the ROM:** `a/0/5/8` (front, 5 NARC members per class) and `a/0/0/6` (back). Trainer data is `a/0/5/5`
(1024 entries) and parties `a/0/5/6` (1024 entries). **Verified** in Origin's NARCs (member counts above) and `narcs.mk` lines 814-817.

**Class and sprite are bound (verified, wiki):** in HeartGold a class *is* the sprite, and it also decides gender, prize money, battle music
and class name (text banks 730 and 731 in hg-engine). To add classes, hg-engine has a source commit and tables for roughly 120 more classes;
**Origin has no source**, so adding classes would need the overlay-patch route (docs/ORIGIN_CUSTOM_CODE.md). **Simplest and inferred
to work:** *replace* an existing class in place, as we already do for species (same trick: swap the NCGR/NCLR members, keep the cell bank
and animation bank of the old class, optionally rename the class in the text bank). It is unproven for trainers. Nobody has tried it in
this project (no trainer work exists in the repo, the memory notes or on the Legion: I looked at `D:\LocalAI\lora-train` and its data folders).

**Overworld trainer / NPC sprites (the walking person on the map):** `data/graphics/overworlds`: 266 PNG sheets (verified). 177 of them are
**32x384** (12 frames of 32x32), others 32x32, 32x64, 32x96, 32x192, 32x256, 32x768 and a few 64x64. They share the same NARC as the
followers, `a/0/8/1` (Origin: 1734 members). **Inferred:** the 12 frames are 4 directions x 3 (stand, two walk steps); not checked frame by
frame. Our follower format (8 frames: up0 up1 down0 down1 left0 left1 right0 right1, 32x32 each, 4bpp + 16-colour palette) already
works in the game and `~/sigma-origin/lw/btx.py` encodes it (verified in `lw/build_lw.py`). An NPC sheet is the same file type with more frames,
so the encoder can be reused; which table says "this map object uses member N" is **unknown** (we found the followers by species order).

### 1.4 Plan for a trainer LoRA

**What Arvind's group would hand in:** one full-body drawing of the trainer, standing, facing roughly toward the viewer (three-quarter is fine),
colours as intended, plus three words of text (age, gender, clothes: the caption "look"). A rough sketch can first go through the existing
sketch-to-art step (Klein style v2, in the studio as the art step) to become clean official-style art. For the overworld sprite the same drawing is enough;
the back view of a trainer is not needed (Gen 4 trainers have no back view except the player).

**Data (all local, never in the repo):**

| Source | Count | Notes |
|---|---|---|
| hg-engine `trainer_gfx/*_enc.png` first frame | 129 classes (verified) | HeartGold/Platinum-style plus fan-made classes (the wiki shows Brendan by hyo-oppa); Arvind treats fan sprites like Nintendo's: local only |
| Extra animation frames (37 animated classes) | up to 8 frames each | usable as extra examples ("pose 2"), or ignored |
| Gen 4 DP/Pt trainer sprites from Arvind's own dumps | would add roughly 100 | **Inferred**: needs extraction from his DP/Pt ROMs; not started; PokeAPI has none |
| Trainer artwork (Bulbapedia) as the "drawing" input | **Unknown** how many exist per class | needed if we want real pairs |
| Overworld NPC sheets | 266 (verified), 177 with 12 frames | for a second, small LoRA (walking trainer) |

129 is small next to 940-1000 for Pokemon. Klein learned the follower from 942 examples in 1500 steps; the style LoRA on 4148 pictures. With 129 real
sprites, expect a style LoRA to work (it learns "what a HGSS trainer looks like") but a pair-based edit LoRA to over-fit. Mitigations that fit
Arvind's rules: hue-shift copies in pairs (done before for backs), mirror copies (trainers are not left/right-handed in a way that matters;
check clothes with text), the other animation frames, and the overworld sheet of the same class as an extra reference.

**Two designs to try (A/B, both on the Legion, free):**

- **A. Style LoRA plus start picture (the sketch-to-art recipe, LORAS.md 1396-1465).** Text-to-image LoRA on Klein: caption =
  "trainer battle sprite pixelart" + describer words for the person (age, hair, clothes, colours; the Qwen3-VL-8B describer
  `v6cfg\describe_species.py` can write them from the sprite), target = the 80x80 frame at 4x on magenta (320 x 320) or 8x (640 x 640).
  At use time give the drawing as image 1 *and* as the start picture at about 80 % noise (the "sweet spot" found for sketch-to-art).
  No pairs needed, no chain of LoRAs. This is the safer first test.
- **B. Edit LoRA with a reversed pair.** Image 1 = the trainer drawn in official style (made *from* the real sprite by base Qwen or Klein
  style v2 in the reverse direction, "sprite to art", exactly what `art_v1` did for Pokemon), target = the real sprite. This copies how Pokemon
  edit LoRAs were built, but the inputs are synthetic art made from the answer, so it can leak (the model learns to undo our own art model).
  Arvind rejected synthetic sketches before, so treat B as a challenger to A.

**Concrete numbers to start with (copied from the working Klein recipe):** rank 32, lr 1e-4, effective batch 2, adamw8bit, quantised, 512 or 640,
target on flat magenta, 3000 steps with a checkpoint every 250 (expect the best checkpoint at 1.0-1.5 passes: with 129 examples that is only
about 200-300 steps at batch 2, so save every 50 and look hard at the early ones), 4-8 seeds per test, 12 of the 129 classes held out
(the real sprite is then the truth), plus our own trainer drawings as the "does it work on our designs" test. Time: about 40 min per 1000
steps at 512 (3 s/step), so under 3 h per run; no RunPod needed.

**Scripts to reuse (all verified to exist):**

| Need | Reuse |
|---|---|
| Dataset builder pattern (targets + control + captions) | `D:\LocalAI\lora-train\v6cfg\build_follower_klein_v3.py`, `build_icon_klein.py`, `build_back_klein_v2.py`, `build_style_klein_v2.py` (Legion; not in the repo) |
| Training config | `pod2\cfg\follower_klein_v3.yaml` and `style_klein_v2.yaml`; run via the `aitk_train*.ps1` queue that pauses the sprite worker |
| Cut a person out of a card or sheet | base Qwen cut-out in `scripts/studio_tries.py` (the studio's "CUT OUT") |
| ComfyUI call for Klein | `scripts/comfy.py` `comfy.klein` |
| Magenta sheet back to game pixels (grid phase, median per cell, magenta out, fringe, rarest-merge colours) | `scripts/klein_follower.py` (`to_game`, `to_icon`); make a `to_trainer` that reads 80x80 |
| Colour limit, snap to grid, outline thinning | `scripts/ds_pixel.py` (`limit_colours`), `scripts/sprites.py` (`--grid`), `v6cfg\outline_fix.py` |
| Quality rules (colours, outline, stray pixels) | `scripts/sprite_quality.py`, `scripts/check_sprite_style.py`; the realness judge/picker v2 must be retrained on trainer sprites |
| Studio page | `scripts/sprite_worker.py` / `studio_tries.py` would need a new "trainer" job kind; website is a later step |
| Writing into the ROM | `~/sigma-origin/lw/build_lw.py` pattern (replace members in a NARC, `S.write_narc`), `lw/btx.py` for the overworld sheet; hg-engine `tools/nitrogfx` converts PNG to NCGR/NCLR |

**Game format rules for the trainer export (from the measurements):** 80x80 frame, at most 15 colours plus transparent index 0, figure about
43x72 px (width 35-55, height 60-80) standing 0-2 rows above the bottom, one palette, 160x80 `enc` sheet (second half a copy if static),
cell and animation JSON copied from an existing static class (e.g. class 000), NCGR/NCLR members replace the old class's members in `a/0/5/8`.
Whether Origin's trainer NCGR uses the same linear 4bpp layout as its Pokemon NCGR (`S.ncgr`, 48-byte header then packed pixels) is
**unknown**; the first step is to open one member from `x_spike_backup/files/a/0/5/8` and compare it with the hg-engine PNG.

**Next steps, in order:**

1. (1 h, no GPU) Extract the 129 first frames and measure fill, size box and bottom gap per class; open Origin's `a/0/5/8` member 0-4 and decode one (proves the format).
2. (2 h) Build the caption list (describer on the sprite, hand-corrected) and a held-out split of 12 classes.
3. (3 h Legion) Style LoRA A, picking by sheets sent to Arvind; in parallel decide with Arvind whether DP/Pt trainer dumps may be added to the data.
4. Replace one class in a test ROM with a placeholder trainer (like the Leafing/Waffy test) and look at it in the emulator.
5. Only then the overworld LoRA and any new-class work.

---

## 2. Inventory of assets for putting our mons (and trainers) into Origin HeartGold

Counts are from the repo checkout (branch detached on `origin/main`): **150 species files** (`data/species/*.yaml`), of which the dex plan fills
254 slots (`data/config.yaml` `dex_size: 254`). **Verified** unless stated.

### 2.1 Per creature

| Asset | Game format | Pipeline / tool | Have | Missing or unknown |
|---|---|---|---|---|
| Concept art | any picture | the group; `assets/concept-art` | 141 of 150 have art | 9 without (e.g. Yanklet) |
| **Front sprite** | 80x80, 15 colours + transparent; Origin sheet 160x80 = 2 frames | studio: cut-out, front v7, picker, `unfake` (`scripts/ds_pixel.py`, `studio_tries.py`) | **71 of 150** (`assets/sprites-ds/<id>/front.png`) | 79 not yet drawn; 70 of them have concept art; the sheet's 2nd frame is always a copy (see 3) |
| **Back sprite** | 80x80, same palette as the front | Klein back v2 + rear-view drawing | 71 of 150 | same 79; the back has been the weakest step |
| **Normal palette** | the front's 15 colours | automatic at export (`build_lw.py` `frame_of`, asserts at most 15 colours) | implicit in the 71 | - |
| **Shiny palette** | second palette, same colour order (members 5 and 7 of the 8 per species in `data/pokepic_m.narc`) | **none** | **0** | no rule or tool; the test script writes the normal palette into the shiny slot, so shinies look normal. Arvind: "shiny and cry last" |
| Female forms | `pokepic_f.narc` (separate files) | not needed | n/a | `build_lw.py` writes the same picture to male and female files, which is enough unless a species has a real gender difference |
| **Party/PC icon** | 32x32, 2 frames (32x64), index 0 transparent, one of 3 (Origin: its own palettes in member 0) shared palettes | Klein icon v1 + `scripts/sprite_colours.py` palette rules | 71 of 150 | the palette index must be written to the arm9 table at `0xFF7FC` (u8 per species, found 2026-10-17); `engine.icon_palette` is set for only 4 species; MUST-FIX list in docs/DEX_REPLACEMENT.md |
| **Follower** (overworld) | 8 frames of 32x32 stacked, 4bpp + 16 colours, in `a/0/8/1` (BTX0 `tsure_poke`) | Klein follower v3 + `klein_follower.py`; encoder `lw/btx.py` | 71 of 150 (128x64 sheet each) | tested in the game for 2 mons only; no female-model entries for species that have two models |
| **Footprint** | 16x16, 2 colours | `scripts/footprints.py` (on branch `studio-v3-tries`, commit a2a9e5d: each of 142 mons *borrows* an official footprint, stored as `hgss:<dex>`) | **0 on main**, 142 chosen on the branch | not written into the ROM yet (no export step); plan: copy the real picture from the ROM at build time |
| **Cry** | `.wav` in hg-engine (`sound/cries`, 1099 files); in Origin: sound archive | **none** | **0** (`assets/cries` is empty) | every mon keeps the old slot's cry; options in docs/DEX_REPLACEMENT.md section 3; how Origin loads new cries is unknown (hg-engine `CONFIG.md` mentions pseudo-banks from SBNK 778) |
| **Battle animation entry** | 0x59 = 89 bytes per species in `a/1/8/0`: see section 3 | **none** | **0** (the test script never touches it) | choice of animation ids and frame timing; verified that the slot keeps the old species' motion |
| Height table (y offset in battle) | `a/0/0/5`, 4 bytes per species: value = 79 minus the feet row | done in `build_lw.py` (`79 - bottom row`) | works | only species up to 493; for slots 494+ pick slots by feet row (spike notes); extending the table hangs the game |
| Dex text | entry (banks 791-793), category (803, 809), 12-character limit for category | `build_lw.py` | `description` 41 of 150, `category` 40 of 150 | 109 and 110 missing; text is written in `docs/FIELDS.md` rules |
| Dex height and weight | a table somewhere | species files: `height_m` 52, `weight_kg` 26 of 150 | partly | Found (section 6): the numbers are in `a/0/7/4` members 0 and 1 (1026 heights, 1389 weights), the shown text in banks 801/799; the 2026-10-17 patches showed no change because the text banks are what the dex displays |
| Species name | text bank 232 (line = species id); other banks may repeat it | `build_lw.py` | all 150 have a name; **8 are placeholders** with "utvikling"-style notes in the name field (e.g. "Leadling Utvikling"), 14 exceed 12 characters, 23 exceed 10 | the real in-game limit is **unknown**: docs say 12 (`FIELDS.md`); vanilla HGSS allows 10 visible characters (inferred, from general knowledge of the games) |
| Pokedex body shape and colour | PokeAPI-style fields | dex has `design.body_shape` 138 of 150, `body_color` **2 of 150** | shape yes | **Unknown** where Origin keeps them; the colour is also the best predictor of the icon palette (LORAS.md 1296-1303), so fill `body_color` anyway |
| Species data | stats, types, abilities, catch rate, exp, growth, gender, egg groups | `spike_bugmight.species_record` (52-byte records, `a/0/0/2`) | `base_stats` 135, `types` 149, abilities 138 | `catch_rate`, `base_exp`, `growth_rate`, `gender`, `egg_groups` filled for **1 of 150**: inherited from the old slot otherwise |
| Learnset | `a/0/3/3`, (level, move) pairs, move id = line in `msg/739.txt` | `build_lw.py` | `learnset.level_up` **39 of 150** | 111 mons would have no moves of their own; TM/HM and tutor compatibility (hg-engine `tmlearnset.txt`) **not looked at anywhere** |
| Evolutions | table in Origin | none written yet | `evolutions` 55 of 150 | not tested; evolution lines without a method (docs/OPEN_QUESTIONS.md 10) |
| New moves and abilities | ids 468+ / 311+ via an overlay-14 patch | `scripts/origin_custom` (Weather Switch PoC works) | 1 proof of concept | each custom ability or move needs code (new ids, not reused ids) |
| Forms of our own | extra sprites or species entries | docs/FIELDS.md `forms` | 1 species has `forms` | how Origin stores forms is **not checked** |
| **Automatic export** | writes everything above into a patch | **`scripts/export_origin.py` does not exist** | the one-off `~/sigma-origin/lw/build_lw.py` (132 lines, outside the repo) did Leafing (slot 25) and Waffy (slot 7) end to end | the repo has no exporter; all of the above is wired by hand for 2 mons |

### 2.2 In general (not per creature)

| Asset | What | Have | Missing / unknown |
|---|---|---|---|
| Trainer battle sprites | see section 1.3; 129 classes, 80x80 | none of ours | everything; no tool, no data prepared |
| Trainer class data | class names (text banks), gender, prize money, music | none | whole table; locations in Origin found, see section 6.1 (arm9 `0xFF77C` gender, `0xF91E2`/`0xF9222` battle music, `0xF9434` encounter music, overlay 14 `0x4DCD4` money, text bank 720) |
| Trainer parties | `a/0/5/6`, 28 bytes per Pokemon | format known (memory) | no tool to write our parties; Origin docs (`~/sigma-origin/docs/trainers.md`) list them; trainer lines naming a party Pokemon must match (DEX_REPLACEMENT.md section 1) |
| NPC / trainer overworld sprites | 32x32 frames in `a/0/8/1` | follower encoder works | NPC frame order and the object-to-sprite table **unknown** |
| Player-character sprites | back (80x640), overworld, trainer card | none | only if the player is changed |
| Text that names species | 6925 lines in 384 banks | name map idea only | script for the name swap, hand edits for story lines (DEX_REPLACEMENT.md) |
| 73 map objects with their own sprite file | Sudowoodo tree, sleeping Snorlax, Lapras, Red Gyarados, Rotom appliances, ... | none | same format as followers; leave the slot alone or draw them |
| Legendary cutscene sprites | Ho-Oh and Lugia, 7 frames of 64x64 each | none | only if those slots are replaced |
| Title screen (3D Ho-Oh), intro, Ruins of Alph puzzles, opening movie Ho-Oh | various | none | keep Ho-Oh or cover with a drawing (DEX_REPLACEMENT.md section 2) |
| Slots with special code | Unown, Spinda, Castform, Deoxys, Burmy, Cherrim, Shellos, Rotom, Giratina, Shaymin, Arceus, Pichu | table exists | choose slots that avoid them |

### 2.3 Ranking: what blocks "a playable mon in the game" most

The first three are not art, but they decide whether a mon is playable at all.

| Rank | Gap | Why it blocks |
|---|---|---|
| 1 | **No exporter in the repo; game data for most mons incomplete** (learnset 39/150, catch rate / exp / growth / gender 1/150, 8 placeholder names) | A mon with the old slot's data plays like the old mon and has no moves of its own. The proof exists for 2 mons only |
| 2 | **Sprites for the other 79 mons** (front, back, icon, follower; 70 have art) | No sprites, no mon. The pipeline exists and works; it is queue time and picking |
| 3 | **Battle animation entry and second front frame** | Every battle shows it. A mon now moves like the species it replaced (Waffy like Squirtle, Leafing like Pikachu) and its two frames are identical |
| 4 | **Cry** | Heard every battle and in the dex. The old cry plays (a Pikachu cry on Leafing). No tool, no plan chosen |
| 5 | **Icon palette index per mon** | The icon draws in the wrong colours if the slot's old palette is kept. Table found, not automated |
| 6 | Shiny palette | Only wrong when shiny; Arvind postponed it |
| 7 | Dex height/weight, body shape/colour, footprint | Cosmetic; locations unknown (height/weight, shape) or not exported (footprint) |
| 8 | Trainer sprites and classes | Only if own trainers are wanted: the story and parties work with the existing classes. A bigger project (section 1) |

---

## 3. Do Pokemon animate in battle? (Gen 4 against Black/White)

**Short answer: yes, a little, and it is not animation in the Black/White sense.** In HeartGold a battle sprite is **two still pictures**, and
the game moves them with a small per-species script (which picture, for how long, shifted how far) plus a built-in motion type. That script is
a table, not a picture, and we have never edited it.

### 3.1 The pieces (verified)

**Two frames in one file.** Each species has a front and a back sprite stored as 160x80, which is two 80x80 frames side by side
(hg-engine wiki "Adding New Pokemon": "Front and back sprites have 2 frames each"; the PNGs are 160 x 80, measured). Our test builder writes the same
picture into both halves: `~/sigma-origin/spike_bugmight.py` line 76-79, `ncgr()` doc string: "two animation frames side by side (same picture twice)".

**A per-species animation table: 89 bytes (0x59) per species.** Source: `~/sigma-hgengine/data/SpriteOffsets.c` (struct `SpriteFrameData` in
`include/sprite.h` lines 35-56) and the wiki page "Editing Pokemon Data", section `spriteoffsets.s`. In Origin the same table is the single
member of `a/1/8/0` (128249 bytes = 1441 species x 89; measured). Slot 1 matches hg-engine's Bulbasaur byte for byte, so slot numbers are species numbers. Layout:

| Part | Bytes | Meaning |
|---|---|---|
| Front header | 3 | `cryDelay` (when the cry starts), `animation` (an id for a code-driven motion: "how to contract/move the sprite"), `animationDelay` |
| Front frames | 10 x 4 | per step: `frameNo` (0 or 1 = which half of the sheet, -1 = end), `duration` (ticks), `horizontalShift`, `verticalShift` |
| Back header + back frames | 3 + 40 | the same for the player's side |
| Tail | 3 | `spriteYOffset`, `shadowXOffset`, `shadowSize` (0-3) |

Example, Bulbasaur (verified): front animation id 2, frames (0 for 4 ticks), (1 for 10 ticks); back animation id 5, cry delay 9, delay 11, frames 0 for 11 ticks then 1 for 15.

**What the animation ids look like (measured in Origin's table, species 1-649):** the front uses 24 different ids (id 2 on 190 species, id 1 on 56, id 13 on 42,
id 0 on 39); the back uses 91 different ids (id 5 on 171 species, id 1 on 55). Species have 1 to 10 steps in their front script (3 steps is the most common
after 2). **Unknown:** what each id looks like on screen. The hg-engine wiki says the ids "don't seem to match up with anything as far as we know" and
that Lhea documented the whole structure in hg-engine issue 146 (not read: no network lookup was done in this session). The motion code itself is
in the ROM's arm9/overlays, not in a data file in `~/sigma-hgengine`.

**How hg-engine gives new species an animation (verified in the wiki):** "New mons are prefilled with Bulbasaur's data as placeholder", and you
copy the animation ids and frame list from an existing species whose motion you like. Nothing generates animations.

### 3.2 What happened for Leafing and Waffy (verified)

`~/sigma-origin/lw/build_lw.py` replaces the front/back NCGR and palette members, the height table, followers, icons, dex text, names and learnsets.
It **does not touch `a/1/8/0`** (grep: no match for `a/1/8`). So in the in-game test:

- Leafing (slot 25) kept Pikachu's entry (front id 0, frames start (1, 6 ticks); back id 105) and Waffy (slot 7) kept Squirtle's (front id 6, delay 8,
  frames (1, 3 ticks), (0, 3 ticks); back id 6). Their two sprite frames were identical copies, so the visible motion is only the shifts and the
  motion type of the old species.
- The project docs record screenshots and that "all working", but **no note says whether the battle motion was looked at or judged**. Treat it as unchecked.

### 3.3 What we would provide for each mon

| Item | What | Effort and tool |
|---|---|---|
| Second front frame (optional) | A pose slightly different from frame 1: mouth open, breathing, tail up. Real HeartGold uses frame 1 and 2 in the sequence above | Could be a small Klein edit LoRA "front frame 1 to frame 2", trained on the 2-frame hg-engine sheets (same recipe as the follower: real pairs, magenta, 4x). Not built. Until then duplicate frame 1 (works) |
| Animation entry | Pick a species whose body plan and size resemble ours and **copy its 89-byte entry** (front and back ids, delays, shifts) into our slot; adjust `spriteYOffset` and the shadow | Easy: add one table write to the export step; choose by body shape and movement words (`design.body_shape`, `design.movement`), which we already have for 138 of 150 |
| Back second frame | The same, for the back | Same copy |
| Cry delay | `cryDelay` in the header must fit our cry if we make our own | Only with the cry work |
| Shadow | `shadowSize` 0-3 by creature size, 0 for floaters | In the copied entry; check that floating mons keep it small |
| Check | Look at each type of motion once in the emulator (py-desmume in `~/sigma-toolchain/venv312`, `scratchpad/ds/play.py`, sound off) and write down what each id does, so that picking becomes a table | A 1-2 h job; would also close the "Unknown" above |

### 3.4 Contrast with Black/White

- **HeartGold (Gen 4, our target):** 80x80 pixels, **2 still frames**, a 15-colour palette. The "animation" is the engine moving and squashing
  these two pictures by a small script, plus the cry. The art cost per mon is two frames (one is enough).
- **Black/White (Gen 5):** the battle sprites are **fully animated**: each species has its own looping sequence of many separate pictures (tens of frames), so it
  breathes, flaps and attacks; they are bigger (96x96 range) and are the game's animated sprites, not tweens. (General knowledge, not checked in this
  repo.) Making one new animated sprite needs dozens of frames, the same creature drawn consistently over time.
  Origin HeartGold keeps the Gen 4 two-frame format even for its Gen 5+ species; hg-engine's fan-made Gen 5+ sprites are cut down to two frames
  and 80x80 (CREDITS.md and memory: fan-made, kept local).
- **Consequence for us:** we do not need an animation LoRA to put a mon in the game. We need (a) our front/back, (b) optionally a second front frame,
  and (c) one table entry copied from a similar species. A true Black/White-style animation would need a different engine and is outside this plan.

---

## 4. Summary of the answers

- **Recipe:** ai-toolkit LoRA on FLUX.2 Klein 4B (rank 32, lr 1e-4, effective batch 2, 512 px, 2000-3000 steps, a checkpoint chosen by Arvind from
  side-by-side sheets), trained on hg-engine/PokeAPI references kept local, whole sheet on magenta as target, the real front as image 1, captions with body shape,
  look and movement, 40 species held out. All on the Legion for free; RunPod only for the early Qwen rounds (about $10-20 per round).
- **Trainer sprites:** 129 front classes (92 static, 37 animated), 80x80, 15 colours + transparent, figure about 43x72 px, `a/0/5/8` (645 members in Origin);
  17 back sprites in `a/0/0/6`; 266 overworld sheets in `a/0/8/1`. Plan: a Klein style LoRA plus start picture first, with the 129 sprites as local data and our
  drawings as input; replace an existing class in place.
- **Missing, ranked:** exporter and per-mon game data; the other 79 sprite sets; the battle animation entry and second frame; cries; the icon palette index;
  then shiny, dex height/weight, footprint export, trainers.
- **Animations:** two frames plus a per-species table (`a/1/8/0`, 89 bytes each, verified); our test mons simply inherited the old slot's entry.
  Black/White animates every sprite frame by frame; Gen 4 does not.

### Could not find or not checked

- What each animation id looks like on screen; hg-engine issue 146 (Lhea's full documentation of the 0x59-byte structure) was not fetched.
- Whether Origin's trainer NCGR members use the linear layout of its Pokemon members, and where Origin keeps class names, gender and prize money.
- Where Origin stores Pokedex height, weight, body shape and body colour.
- How Origin loads a new cry; any existing trainer data or trainer LoRA work (none found in the repo, memory notes or on the Legion).
- The NPC overworld frame order and the object-to-sprite table.
- Whether Origin's species-name limit is 10 or 12 characters.
- The sprite counts above are for `origin/main` (71 sets); the tree of commit `a2a9e5d` on `studio-v3-tries` contains 33 sets plus the footprint choices, so the two lines
  are not merged yet.

---

## 5. Answers found 2026-11-11

Sources: the public pret decompilation (`pret/pokeheartgold`, cloned shallow), `~/sigma-hgengine`, and Origin's extracted ROM (`~/sigma-origin/x_origin`, which is byte-identical to `x_spike_backup` for arm9 and the sound archive). Tags: **V** = verified in a file, **I** = inferred. Corrections to earlier sections are listed at the end.

### 5.1 Cries

- **Storage (V).** All cries live in `data/sound/gs_sound_data.sdat` (Origin: 12,365,504 bytes; decomp: 8.6 MB). Every cry is **one wave archive (SWAR) holding exactly one sample (SWAV)**. Parsed in Origin: 1099 cry SWARs, each with 1 wave, all IMA-ADPCM (wave type 2) except one PCM16 (the Shaymin-Sky slot).
- **How a cry plays (V).** Decomp `asm/unk_02005D10.s`, `PlayCry` (0x02006218): species number -> `sub_02006A0C` (only Egg 494 and Shaymin Sky return "special", cry id 494) -> `sub_02006C14` starts **sequence 2 (`SEQ_PV`, one shared sequence, `include/constants/sndseq.h`) with bank number = species number**. The bank (`BANK_PV001`/`PV002`) points at wave archive number = species. Species above 495 are clamped to 1 (Bulbasaur) in vanilla. `PlayCryEx` (0x020063A4) adds 15 "patterns" (plain, pan/volume, a pitch bend down used for fainting/low-HP style cries, delayed start, Chatot recording path `src/sound_chatot.c`). Pitch bend is done at play time with `GF_SndHandleSetTrackPitch`, so **we cannot attach per-species pitch/chatter data**; it is code-driven and the same for every species. Cry delay is per species in the 89-byte animation table (`cryDelay`, section 3.1).
- **Origin (V for layout, I for the code).** Origin's SDAT has `BANK` 778 entries of which only 74 are filled (`BANK_PV001`, `BANK_PV002`, sound effects) and `WAVARC` 1384 entries: indices 1-493 = species 1-493, index 494 = Shaymin Sky, **indices 778-1383 = species 494-1099** (index = species + 284). That is exactly hg-engine's "pseudo-bank" scheme (`CRY_PSEUDOBANK_START 778`, `src/sound.c` `NNSi_SndArcLoadBank`: every cry bank borrows bank 1's instrument and loads wave archive = cry number; `rebuild_json.py` deletes all `BANK_PV` except 001/002). Origin's arm9 PlayCry equivalent was not disassembled (JP build, literals differ), so "Origin uses the hg-engine cry code" is **I**, but the SDAT layout leaves little doubt. **So Origin has 1099 cry entries, not 493**, covering the same slots we use. Each slot already has a cry; replacing it is a data swap, no code.
- **hg-engine (V).** `sound/cries/NNN.wav` (1099 files, 16-bit mono PCM, **13379 Hz**), built by `narcs.mk` lines 577-600: `tools/ntrWavTool.py wav swav 16384 --adpcm-xq` (mono wav -> IMA-ADPCM, block 16384), unpack SDAT with `tools/SDATTool.py -u`, copy the new `WAVE_ARC_PVnnn/00.swav`, `scripts/rebuild_json.py`, repack `-b`. The same tools can patch Origin's SDAT.
- **Format limits (V from Origin's 1099 cries).** Mono, ADPCM; sample rates seen 10512 (414 cries), 13379 (483), 16000, 22050, 32000, 44100 Hz. Size 116 bytes to 19,708 bytes of ADPCM (median 7.1 kB, about 1 s at 13 kHz). No loop. Stay at **<= about 16 kB ADPCM (~1.5-2.4 s at 13.4 kHz)**; the sound heap is small (the hg-engine author's reason for pseudo-banks). Unknown: the hard heap limit.
- **Making cries (R = web research, nothing built).** No fan-game "pokemon cry generator" exists. Found only cry *inserters* (Gen 2/3: CryEd, Cry Editor) and walshyb/CryEd which just pitch/length-shifts base cries. Options:
  - (a) **Recipe from official cries** (layer 2 cries, pitch-shift, time-stretch, formant shift, reverse tail, ring-mod; stored like footprints as `hgss:<dex>` recipes so no Nintendo audio enters the repo; render at build time from the ROM's own SDAT, which we can already read). Zero cost, safe, sounds "Pokemon" by construction. Best first step.
  - (b) **Generative audio** on the RTX: Stable Audio Open (up to 47 s, 44.1 kHz stereo; license is Stability Community License, free for non-commercial/small orgs, check the model card), AudioLDM2 (weights CC-BY-NC), MusicGen/AudioGen. Prompted animal-vocal output is usually mushy; use only as raw material, then clip to 1-2 s, pitch/EQ, and downsample.
  - (c) **RAVE** (IRCAM) or timbre transfer trained on the official cries (1099 files are enough for a small model): our own voice/animal recordings -> "Pokemon cry" timbre. Strongest result, most work; training on game audio stays local like the sprite LoRAs. Spectrogram-diffusion training is the same idea with more effort.
  - **Recommendation:** start with (a) as a deterministic recipe per mon (base cry chosen by body plan, plus pitch/formant/layer parameters), then try (c) (voice -> cry via RAVE or a similar converter) for hero mons. Always finish with the real cry chain: mono, 13379 Hz, normalize, 1-2 s, ADPCM via `ntrWavTool`. Shiny and cry stay last.

### 5.2 Height, weight, body shape, body colour

- **V.** In the decomp these are `files/application/zukanlist/zkn_data/zukan_data.json` (members: height u32 in decimetres, weight u32 in hectograms, body_style u8, player/mon scale and y-offset s16), read by `src/dex_mon_measures.c`. Displayed text comes from **text banks** (decomp 812 weight, 814 height; Giratina origin 813/815).
- **CORRECTED in section 6.2: the main table is Origin's `a/0/7/4` (the decomp maps `zukan_data.narc` to `a/0/7/4`; `a/2/1/4` is only the Giratina-variant copy), and `a/0/7/4` has 1026 heights / 1389 weights, not 494.** Original text, kept for the trail: The zukan_data layout is Origin's `a/2/1/4` (102 members: members 0, 1, 2 are height, weight, body style, 3-10 scales and offsets, 11+ the dex sort lists). Compared with the decomp: 492 of 493 height values and 492 of 493 body styles match. **It has 494 entries only (species 0-493)**, not 1441. Displayed strings are in **bank 801 (height, "０．７ｍ") and 799 (weight, "６．９ｋｇ")**, 1441 lines each. For slots above 493 the numeric table is out of range: sorting/size-comparison screen and weight-based moves for those slots are **unknown** (test needed; hg-engine extended the tables, Origin apparently did not). Earlier patches to `a/2/1/4` showed "no change" probably because the visible text comes from banks 799/801.
- **Colour (V).** Decomp `BaseStats.color` (7 bits) + `flip` at 0x19 of the personal record, and hg-engine writes it there. **Origin's 52-byte records do not keep it** (0x19 is the high byte of the second ability; no column matches the decomp colours, best 0/200). Body colour is not used by the game; keep `body_color` only as our own design field.

### 5.3 Species name length

**10 (V).** `POKEMON_NAME_LENGTH 10` in decomp `include/constants/global.h`; nickname/name buffers are `u16[POKEMON_NAME_LENGTH + 1]` in the save-related structs (`hall_of_fame.h`, `daycare.h`, `trainer_house.h`), so it cannot grow without changing the save. Origin bank 232 (decomp bank 237): all 1439 names are at most 10 characters and the English patch **shortened** the long ones ("FluttrMane", "RoarngMoon", "RagingBolt"). Use <= 10. The older doc's "12 characters" applies to the Pokedex category line, not the name.

### 5.4 Battle animations

- **V.** `a/1/8/0` (decomp `NARC_a_1_8_0`; read by `NARC_ReadPokepicAnimScript` in `src/pokemon.c` 4188): 89 bytes per species = for front then back: `cryDelay`, **animation id**, `delay`, then 10 steps of `PokepicAnimScript` (`include/pokepic.h`): `next`/frame (0 or 1 = which half of the 160x80 sheet, -1 = end, <-1 = loop back to step `-2-next`, repeating `duration` times), `duration` ticks, x shift, y shift; then 3 tail bytes. **Frame 2 = the right 80x80 half, selected by frame number 1 in the steps** (V).
- **What the id means (V from asm, names I).** `sub_02016F40` (`asm/unk_02016EDC.s`) clamps the id to 0-142 and loads **member `id` of NARC `a/0/9/0`** (Origin: 143 members, 44 to 728 bytes). That member is a script for a small virtual machine with 34 opcodes (dispatch table `_020F61F8`) acting on the picture's attributes (offset, scale, rotation, pivot, alpha, fade, mosaic, shadow). The decomp has only asm for it and no names, so **a plain-words motion per id is not in the source**; getting it needs either a hand disassembly of the 34 opcodes or capturing each id in the emulator.
- **Usage in Origin, species 1-493 (V).** Front uses 24 ids, back 91. Front id -> species count, script size, examples: 2 -> 74, 96 B (Bulbasaur, Caterpie, Pidgey); 1 -> 55, 44 B (Ivysaur, Charizard); 0 -> 39, 132 B (Pikachu, Clefairy); 13 -> 37, 80 B (Starmie, Voltorb); 18 -> 26 (Fearow, Persian); 17 -> 25 (Butterfree, Golbat, Gastly); 3 -> 25, 280 B (Alakazam, Hitmonchan); 5 -> 24, 44 B (Metapod, Rhyhorn); 16 -> 24 (Seel, Krabby); 11 -> 22, 392 B (Charmander, Magikarp, Togepi); 14 -> 21, 412 B (Blastoise, Machamp); 6 -> 19 (Squirtle, Rattata); 9 -> 16 (Jigglypuff, Lapras); 7 -> 14 (Farfetch'd, Gengar); 8 -> 13 (Zubat, Beedrill); 15 -> 11 (Abra, Mewtwo); 4, 20, 22, 19, 10 (728 B, the longest: Pichu, Mareep), 21, 23, 12 for 2-9 species each. Back: id 1 -> 55, 2 -> 29, 6 -> 20, 92 -> 17, 5 -> 16, 93 -> 12, rest <= 11. Short scripts (44 B: ids 1, 5, 8, 16) are simple one-axis moves; the long ones (280-728 B) are multi-part. **Recommended rule for our mons:** choose by size and movement words: copy the entry of an official species that already moves the way we want (e.g. heavy: Machamp/Blastoise id 14; small hopper: Pikachu id 0; floaty: Butterfree/Gastly id 17; plain: Bulbasaur id 2). Confirm by looking at them once in the emulator.

### 5.5 Icon palettes

- **V.** HG has **3 shared icon palettes** (16 colours each): `sPokemonPalNoBySpeciesAndForm` in decomp `src/pokemon_icon_idx.c` holds 0, 1 or 2 per species (268 / 121 / 155); loaders request 3 palettes from member 0 of `poke_icon` (`battle_arcade_game_board.c` 1336). Origin: `data/pokeicon.narc` member 0 is 552 bytes (a palette with 16 slots, only 3 are used); the per-species byte table is in arm9 at 0xFF7FC (values 0/1/2: 774/305/362 in the first 1441). hg-engine keeps the same 3 (`data/IconPaletteTable.c`; wiki: "0, 1, or 2").
- **Adding palettes: not in hg-engine/Origin.** The 16-slot palette file has room, but the loaders pass a fixed count of 3 and the draw code adds fixed offsets (+1 main, +3 sub screen), so more palettes need an arm9/overlay patch.
- **Design colours (I).** Within these limits: (1) quantise each icon to its best of the 3 existing palettes (what `scripts/sprite_colours.py` does); (2) the three shared palettes themselves must stay as they are: every official Pokemon stays in the game (Black/White model, Arvind 2026-11-11), so redefining them would spoil their icons; (3) only if (1) loses too much of a design, consider a code patch for more palettes.

### 5.6 Trainer sprites and classes

- **V.** Decomp `sub_02070D3C` (`src/pokemon.c` 2719): front pictures are in `a/0/5/8` (`NARC_a_0_5_8`), member = `trainer_class * 5 + {0 NCGR, 1 NCLR, 2 NCER, 3 NANR, 4 NCBR}`; backs are in `a/0/0/6` through `TrainerClassToBackpicID`. Palette is 1 x 16 colours. Origin: 645 members = **129 classes** (class names bank 720 has 129 lines; 85 back members = 17). The trainer record (`a/0/5/5`, `TRAINER_FILE` in `trdata.json.txt`) stores `trainerClass`, so a trainer's sprite is simply its class.
- **Class data elsewhere (V).** Gender: `sTrainerGenders[]` in code (decomp `src/trainer_data.c` 133). Encounter music: `sTrainerEncounterMusicParam[][3]` in code (`src/field_bgm.c` 30). Prize money and the "animation + music combo" are code tables too; hg-engine puts class names in banks 730/731.
- **New classes (V for hg-engine, I for Origin).** hg-engine documents adding about 120 classes (wiki "Adding New Trainer Classes": more NARC members, text lines, extend the gender, money and music tables via `bytereplacement`). Origin has no source, so a new class means patching those arm9 tables; **replacing an existing class in place** (new picture in the same 5 members, same class id) is the safe route.

### 5.7 Corrections to earlier sections

- 2.1 "Cry ... how Origin loads a new cry is unknown": layout now known (5.1); the 12-character claim for species names is wrong (5.3); "Dex height and weight: unknown" is `a/2/1/4` (494 entries) plus banks 799/801 (5.2); "body colour: unknown" is a personal-record field in the decomp that Origin does not keep (5.2).
- 3.1 "front uses 24 ids, back 91" confirmed. "unknown what each id looks like" narrowed: the id selects a VM script in `a/0/9/0` (5.4); still not described in words.
- 4 "Could not find": the icon palette count (3) and trainer class mapping are answered above.

### 5.8 Still unknown

- Plain-words motion for each animation id (needs the 34-opcode VM read or emulator captures).
- Whether Origin's arm9 uses hg-engine's cry mapping for species >= 494 (layout says yes); sound heap limit for a long cry.
- ~~Whether Origin's dex screens and Low Kick use `a/2/1/4` for species above 493~~ answered in section 6.2 (they use `a/0/7/4`, which is long enough).
- ~~Where Origin keeps trainer class gender, music and prize money~~ located, section 6.1.

---

## 6. Trainer classes and species above 493 (2026-11-11)

Method: the tables of the decompilation (`pret/pokeheartgold`, shallow clone) were turned into byte patterns and searched in Origin's clean extraction (`~/sigma-origin/x_spike_backup`: `arm9/arm9.bin`, `arm9_overlays/ov0NN.bin`, `files/`), then the literal-pool pointers to each table were searched too, so every table below is **both found and referenced by code**. Arm9 RAM base is `0x02000000` (file offset + base); overlay 14 is loaded at `0x22007E0` (`arm9_overlays/overlays.yaml`). Tags: **V** = verified in Origin's files, **I** = inferred.

### 6.1 Trainer classes

**Count (V).** 129 classes (ids 0-128, `TRAINERCLASS_PKMN_TRAINER_ETHAN` .. `_DAWN_PT`). Evidence: class names bank 720 has 129 lines, front pictures `a/0/5/8` have 645 = 129 x 5 members, prize table has 129 entries. **Origin did not change any of the tables below**: gender, battle-music, encounter-music and prize-money tables are byte-identical to the vanilla HGSS ones generated from the decomp (full-length match). Origin added no trainer class; it re-uses the vanilla ones with new names in bank 720 and new pictures (e.g. 91 "Hoenn Trainer", 92 "Sinnoh Trainer" for Steven and Cynthia, 127/128 "Hoenn/Sinnoh Champion").

| What | Decomp | Origin location (all V) | Entries |
|---|---|---|---|
| (a) Gender | `sTrainerGenders[]` (`src/trainer_data.c` 133), `TrainerClass_GetGenderOrTrainerCount` | **arm9 `0xFF77C`** (RAM `0x020FF77C`; literal pointer at arm9 `0x72728`). 1 byte per class: 0 male, 1 female, 2 "double" (Twins, Young Couple style). Counts 77 / 49 / 2 | **128** (class 128 reads one byte past the table, which is the first byte of the icon-palette table that starts right after at `0xFF7FC`; value 0 = male; harmless) |
| (b1) Battle intro + battle music, per class | `NPCTrainerGetBattleIntroAndMusicParam` (`asm/unk_020517A4.s`): table `_020FC3CA` of u16 `class \| (combo << 10)`; a class not in the table gets combo 41 (`0xFFFF` transition, `SEQ_GS_VS_TRAINER`) | **arm9 `0xF91E2`**, 32 entries (the 11 wild-species entries of the same shape sit just before at `0xF91CC`; pointer literals at arm9 `0x50BEC` and `0x50C30`) | 32 classes (leaders, Elite Four, Champion, Rival, Rocket ranks, Kimono Girl, Red) |
| (b2) Combo -> (transition id, music sequence) | `_020FC40A` | **arm9 `0xF9222`**, 45 x (u16 transition, u16 `SEQ_GS_*`); pointer literal at arm9 `0x50B24` | 45 combos (0 = Falkner .. 44 = Red). Combo 37/38/41 are plain trainer/rocket/gym-leader music |
| (b3) "Eyes meet" music when the trainer sees you | `sTrainerEncounterMusicParam[][3]` (`src/field_bgm.c` 30): `{class, Johto seq, Kanto seq}`; a class not in the table gets `SEQ_GS_EYE_J_SHOUNEN` | **arm9 `0xF9434`**, 44 x 6 bytes; pointer literal at arm9 `0x54224` | 44 classes |
| (c) Prize money | `sPrizeMoneyTbl[0x81][2]` in overlay 12 (`CalcPrizeMoney`, `src/battle/battle_command.c` 2157): money = last mon level x 4 x multiplier (x2 in doubles) | **overlay 14 `0x4DCD4`** (file offset; pointer literal in ov14 at `0x2BA88`), 129 x (u16 class, u16 multiplier), **unsorted list searched linearly**; a class not found trips an assert and falls back to entry 2 (Youngster) | 129 (every class once) |
| (d) Class name text | `msg_0730` (`BufferTrainerClassName`) | **text bank 720**, line = class id, 129 lines (the decomp's 729 trainer names = Origin bank **719**, 1024 lines). The decomp's "with article" bank 731 has **no counterpart found** (no other bank has 129 lines) | 129 |
| (e) Front picture | `sub_02070D3C` (`src/pokemon.c` 2719) | **`a/0/5/8`**, member `class*5 + k`: 0 NCGR (3248 B), 1 NCLR (72 B = one 16-colour palette, so the palette "index" is just the member next to the picture, there is no mapping table), 2 NCER, 3 NANR, 4 the 160x80 two-frame sheet (6448 B, hg-engine's `_enc.png`) | 645 members |
| (e) Back picture | `TrainerClassToBackpicID` (`src/pokemon.c` 4132) | **`a/0/0/6`**, member `backpic*5 + k`, 85 members = 17 back pictures (Ethan, Lyra, Rival, Lance, Cheryl, Riley, Buck, Mira, Marley, Lucas DP, Dawn DP, Barry DP, Lucas PT, Dawn PT, Barry PT, Ethan 2, Lyra 2). A class with no special case gets Lyra if its gender byte is 1, else Ethan. | 17 |

What the gender byte really does (V from the decomp, only two readers exist): it biases the personality of an NPC trainer's mons (`CreateNPCTrainerParty`: female class 0x78, otherwise 0x88, which decides the gender of species with mixed ratios) and chooses the default back picture. It is **not** what prints the male/female sign in class names: those are literal characters in bank 720 ("Swimmer" with the male/female sign, "PKMN Trainer" is the ligature glyphs). The battle intro animation is the transition id of (b2), not the gender.

**Individual trainers (V).** `a/0/5/5`: 1024 records of 20 bytes, **identical to vanilla**: `u8 trainerType, u8 class, u8 0, u8 partySize, u16 items[4], u32 aiFlags, u32 doubleBattle` (byte 2 is 0 in all 1024; hg-engine uses it as the high byte of a 16-bit class). 963 trainers have type 3, 54 type 0, 5 type 1, 2 type 2, but the party file ignores the type. Record 0 is empty, the other 1023 have 1-6 mons; no free slot. Names: text bank 719 (line = trainer id; `{TRNAME}` prefix for scripted names; the rival class is replaced by the player's rival name at runtime). Win/lose lines: separate per-trainer message bank (not looked up here). `a/0/5/6`: 1024 members, each exactly `28 x partySize` bytes (checked for all 1024, 3891 mons). **Origin's party record is a fixed 28 bytes, not vanilla's 18 and not hg-engine's variable-length bitfield format** (hg-engine's `TrainerPokemonData` is also bigger, with `TRAINER_DATA_TYPE_*` flags deciding which fields exist). Layout seen in data: `u8 @0` difficulty/IV scale (150, 250, 200, 100, 50, 10 ...), `u8 @1` 0 or 0x20 (0x20 = ability slot 2, matches hg-engine's `TRAINER_POKEMON_ABILITY_2`), `u8 @2` mostly 0, `u8 @3` 255 or small values (nature or extra flag, I), **`u16 @4` ability id, `u16 @6` level, `u16 @8` species, `u16 @10` item, `u16 @12..@18` four moves**, `@20..@27` 8 bytes that are non-zero in 1162 of 3891 mons and look like EV/IV or PP bytes such as `06 fc 00 00 00 fc 00 00` (I; meaning not decoded). Species up to 1013 occur (36 different species above 493 are used by trainers), so species ids need no form bits here. Move ids are Origin's (hg-engine id minus 3, see the memory note); abilities are hg-engine ids.

**What this means for adding our own trainers.**
1. *New trainer using an existing class* (new name, party, picture reused): just edit one of the 1023 records (they are all in use, so each one we take replaces an existing trainer or gets a map script that points at it). Name = bank 719, party = `a/0/5/6` in the 28-byte format above. Safe, no code.
2. *New picture for an existing class*: replace the 5 members `class*5 .. class*5+4` of `a/0/5/8` (the picture then changes for every trainer of that class). **Four classes are used by no trainer at all and are free to repurpose**: 59 Worker, 119 Redhead, 121 Double Team, 122 Young Couple (V, from the 1024 records; scripts could still give them to a gym-less NPC, not checked). Classes with exactly one trainer are also cheap to repurpose: 18 Breeder, 28 Ninja Boy, 35 Socialite, 80 Parasol Lady, 97 Tower Tycoon, 99 Hall Matron, 100 Factory Head, 101 Arcade Star, 102 Castle Valet, 109 PKMN Trainer (Red), 120 Mystery Man, 123 (blank name, Lance), 127, 128. Then set gender byte, prize multiplier, name in bank 720, and optionally music entries: all are in-place data edits to existing tables, no relocation.
3. *A 130th class*: needs growth of the tables (gender, prize, music, intro) and of `a/0/5/8`; the tables sit in arm9/overlay 14 next to other data, so it means relocating each table to free space and patching its pointer literal (addresses above) and the count constants in the code (the count constants, e.g. `0x20`, `0x2D`, `0x81`, `0x2C`, were not located in Origin; hg-engine's wiki lists their vanilla USA addresses in `bytereplacement`, but Origin is the JP build). Possible but real reverse-engineering; avoid unless the group needs more than ~18 distinct trainer pictures.

### 6.2 Species numbers above 493

**What the slots are (V).** Origin's species numbers follow the national dex: 1-493 Gen 1-4, **494-1025 Gen 5-9 (532 base species)**, then **1026-1440 are alternate forms** (docs `pokemon_1026-1440.md`: e.g. 1026 Venusaur form 1) and the ROM's name bank 232 has 1439 lines. The player docs generated from the ROM (`~/sigma-origin/docs/pokemon.md`, "Obtainable" column) mark **255** base slots as "not obtainable", all above 493 (the memory note says 254; the one-slot difference was not resolved, probably a script gift that the earlier check counted as used): 494, 504-505, 511-516, 522-523, 527-528, 538-539, 556-558, 561, 577-579, 582-584, 599-601, 605-606, 615, 618, 621, 626, 638-649, 667-668, 672-675, 677-678, 682-687, 696-697, 701, 707, 710-711, 716-721, 741, 746, 764-768, 772-774, 776, 785-818, 821-823, 827-830, 835-836, 843-845, 852-855, 862, 867, 870-871, 874-884, 888-898, 905-923, 926-927, 931-945, 948-950, 953-956, 960-968, 971-978, 980, 984-995, 999-1010, 1014-1018, 1020-1025. **So every slot we can take is above 493 and every item below applies to all of them.**

**Correction to 5.2 (V).** The dex numbers are **not** `a/2/1/4`. In the decomp `zukan_data.narc` is `a/0/7/4` (`heartgold.us/filesystem.csv` line 171) and `a/2/1/4` is `zukan_data_gira.narc`, the Giratina-Altered variant (decomp `sDataNarcId`/`SetDexBanksByGiratinaForm`). Origin's arm9 static data at `0x10F74C` (RAM `0x0210F74C`) holds the initial triple `{weight bank 799, narc id 74, height bank 801}` (V; 74 = a/0/7/4 as in the decomp), so Origin loads the same file. **Origin extended `a/0/7/4`** (102 members, same layout as the decomp):

| Member | Content | Origin size | Covers |
|---|---|---|---|
| 0 | height, u32, decimetres | 1026 entries | species 0-1025 (all our slots) |
| 1 | weight, u32, hectograms (used for the dex weight compare **and Low Kick, Heavy Slam, Grass Knot**: `battleMon.weight = PokedexData_GetWeight`) | 1389 entries | 0-1388 (all our slots) |
| 2 | body style, u8 | 650 entries | 0-649 only; **entries 494-649 are all 0 (no style)**, 650-1025 are beyond the member (the code does not bounds-check, so it reads whatever follows the buffer on the heap; the dex search by body shape uses the sort lists in members 11+, so the value is cosmetic) |
| 3-10 | player/mon scale and y-offset for the "size compare" screen, s16, male and female | 1026 entries each | 0-1025 |
| 11+ | dex sort lists (a-z, light/heavy, body shape, type, ...) | 986-2050 bytes | species up to about 1025 |

Check (V): for species 1-493 all 493 heights and weights equal the shown text; for 494-1025 all 532 heights and 523 weights equal the text of banks 801/799 (the other 9 differ only by rounding or typos). Members 3-10 hold the **same filler value for about 520 of the 532 Gen 5+ slots** (e.g. member 3: 272 in 522 slots, 6 distinct values; for 1-493 there are 46), so size-compare placement is not tuned per species; our values can simply overwrite them (entries exist). `a/2/1/4` (494 entries) is only read for the Giratina variant, so it needs no work for us.

Per item, for an existing species above 493 (take 504 Patrat as the example, V from files):

| Item | Where | Slots above 493 | Our new species |
|---|---|---|---|
| Name | text bank 232, line = species id | present (1439 lines; English patch shortened names to <= 10 characters) | overwrite the line |
| Dex entry | bank **791** (1441 lines), banks 792/793 have only 494 lines (older version texts, not used for these species, I) | present | overwrite line `species` of 791 |
| Category ("Scout Pokemon") | bank **803** (1441 lines); 809 and neighbours (494 lines) are other-language copies of the old dex | present | overwrite line of 803 |
| Height / weight shown | banks **801** / **799** (1441 lines, full-width digits such as `０．５ｍ`, `１１．６ｋｇ`) | present | overwrite both lines |
| Height / weight used by the game | `a/0/7/4` members 0 / 1 | present (table long enough) | write dm / hg values |
| Size-compare scales/offsets | `a/0/7/4` members 3-10 | present (mostly filler) | write per-species values |
| Body shape | `a/0/7/4` member 2 and the sort lists | zero / short for 494-649, missing beyond 649 | leave 0; the shape search filter would not list our mons (cosmetic, I) |
| Cry | SDAT wave archive: `data/sound/gs_sound_data.sdat` index **species + 284** for species >= 494 (indices 778-1383) | present, 1099 cries; Origin's arm9 contains hg-engine's patched `NNSi_SndArcLoadBank` with the pseudo-bank constants `778 (0x30A)` and `495 (0x1EF)` at arm9 `0xC9518` (V, disassembled the head of the function at `0x020C93A0`; the same cry-bank detection as in hg-engine `src/sound.c`) | replace the SWAV of that wave archive (section 5.1); the species -> bank mapping function itself was not located in Origin (I) |
| Battle sprite height offset | `a/0/0/5`, **1976 members = 494 species x 4**, 1 byte each (this is "mon height offsets" = y shift of the battle sprite, **not** the dex height) | only species up to 493 | nothing to write; the engine uses a fixed offset per slot above 493 (memory note 2026-10-04: choose slots by the feet row of the original sprite; extending the table hangs the game) |
| Icons, battle sprites, personal data, learnsets, evolutions | `pokeicon.narc`, `pokepic_m/f.narc` (8 members per species), `a/0/0/2`, `a/0/3/3`, `a/0/3/4` | all present for 1-1025 | in-place data swap as already built in `build_lw.py` |

**What Origin does for species above 493: it has real data for all of them (V).** Unlike vanilla (where species above 493 would be clamped to Bulbasaur's cry and would read past the end of a 494-entry table), Origin extended the cry archive, the dex text banks, `a/0/7/4` and the sprite NARCs to 1025+. The only tables that stay short are the body-style byte (650) and the battle y-offset (494). Not run in the emulator: a dex screen for a Gen 5 species was not opened (several menu steps from the available savestates); the conclusions come from the files and one disassembled function.

**What it means for our species (I from V data).**
- Every field we need (name, dex text, category, shown and numeric height/weight, scales, cry) is an in-place overwrite of an existing line/entry at the slot number, **no code patch and no table growth**, as long as we stay within the 255 free base slots (all in the covered ranges, since the longest table in use ends at 1025).
- Keep the stored weight, shown weight and height consistent (a/0/7/4 and banks 799/801 are separate copies; the game shows the text but uses the numbers for Low Kick and the dex size screen).
- Species numbers 1026-1440 (forms) are a separate pool; heights are not defined there (member 0 ends at 1025) and form handling is out of scope: use only base slots.
- Slots above 649 will have no body style (reads past the member). Harmless unless the dex shape search is used.

### 6.3 Still unknown after this pass

- The count constants in code for the class tables (needed only for a 130th class), and the Origin counterpart of the decomp's "class name with article" bank 731.
- Meaning of the last 8 bytes of Origin's 28-byte party record and of bytes 2-3.
- Which of the 1023 trainer records are actually reachable in the game (some may be dead slots that are safe to take).
- In-game confirmation of the dex size screen and a Low Kick on a new slot (files say yes; not run).
- The species -> cry-bank function in Origin's arm9 (only the bank loader was located).

## 7. Trainer pictures, counted (2026-11-11, checked in Origin's `a/0/5/8` and the decompilation)

Every class has **5 files** (`class * 5 + 0..4`, `sub_02070D3C` in `src/pokemon.c` of pret/pokeheartgold):

| File | What it is | Used for |
|---|---|---|
| 0 NCGR | the picture tiles, one or more 80x80 frames | the animated trainer at the start of a battle |
| 1 NCLR | palette (15 colours + transparent) | both pictures |
| 2 NCER | cells (how the frames are cut) | the animated trainer |
| 3 NANR | animation (which frame, how long) | the animated trainer |
| 4 NCBR | the same trainer as a still "Pokemon style" picture: two 80x80 frames (160x80), scrambled like DP Pokemon sprites (`UnscanPokepic_DP`) | the battle's picture system (`PokepicManager`, opponent side) and the Hall of Fame (player) |

Frames in file 0 (all 129 classes):
- **97 classes: 1 still picture.**
- **31 classes are animated**: 3 frames for most (gym leaders Falkner, Bugsy, Whitney, Morty, Pryce, Jasmine, Chuck, Clair, Erika, Koga, Sabrina, Blaine; Elite Four Lorelei, Lance, Bruno; Giovanni; Silver; Misty; Blue; Gold), 4 for Lt. Surge, 5 for Factory Head Thorton and Tower Tycoon Palmer, 6 for Hall Matron Argenta, 7 for Castle Valet Darach, 8 for class 123 (an Origin class with no name, used by the trainer "Mewtwo"), and **11 for Arcade Star Dahlia**, the most. The animations have 5 to 30 steps (Chuck's is the longest, 30).
- **Class 21 (Pokefan, female) is the odd one:** its picture is 2880 bytes instead of 3200 (90 tiles, not 100). Vanilla HeartGold has exactly the same file, so it is the original game's quirk, not an Origin bug; it still shows fine.

Back pictures (`a/0/0/6`, 17 classes, the trainer seen from behind throwing the Poke Ball at the start of a battle): the player (Ethan, Lyra, and a second Ethan/Lyra set), the rival, Lance, the tag-battle partners Cheryl, Riley, Buck, Mira and Marley (5 frames each), and Lucas, Dawn and Barry from DP and Platinum (for link battles). The player-type ones have 8 frames.

**What this means for replacing important characters with our own:** we write all 5 files of a class, so a replacement can be a still picture even where the original was animated (1 frame, 1 cell, a 1-step animation, like the 97 still classes). Animated ones are a bonus: the extra frames can come from an edit model trained on the real trainer frame pairs (the same idea as the Pokemon frame-2 LoRA). File 4 must hold the same trainer (two frames, may be identical), scrambled. A new player character needs a back picture with 8 throw frames as well.

**Kept for later (Arvind, 2026-11-11):** if we want many brand-new classes instead of replacing, a class 130+ needs the class tables moved and the code patched; possible, do it when the time comes.

## 8. Which free slots are clean (2026-11-11)

Question: of the 255 free base slots (section 6.2), which hold a species that is "dirty", meaning it has alternate forms in Origin, species-specific battle or menu code, or is used by a story script? Tags: **V** = verified in a file, **I** = inferred.

**Result: 204 clean, 8 latent (usable with care), 43 dirty (18 with active code, 25 with form entries only).**

### 8.1 Method and how far to trust it

1. **Forms in Origin (V).** The 415 alternate-form records 1026-1440 (`~/sigma-origin/docs/pokemon_1026-1440.md`) were mapped to their base species by name; every base that is one of the 255 free species is listed below with its entry numbers. 43 free species are the base of at least one entry.
2. **Code (V for stock hg-engine, I for Origin).** For each of the 255 species the stock `~/sigma-hgengine` source (`src`, `include`, `armips`, `data/battle_scripts`, `asm`, `hooks`; species written as `SPECIES_*`, found by name because hg-engine's numbers differ from Origin's) was searched for every reference outside data tables. Hits were read one by one. **Origin is not built from this source** (it is the JP ROM with its own Black/White-style battle code in overlay 14), so what hg-engine does is the best available picture of what such an engine does, not a fact about Origin's binary. Searching Origin's overlays for species numbers was tried and abandoned: the numbers occur as table data everywhere and give no signal.
3. **Scripts and data (V).** (c) was checked three ways: the 1024 trainer parties in `a/0/5/6` (read directly: none of the 255 species is used), the gift/static-battle/trade tables in `trades_tutors.md` and the encounter, trainer and item docs searched for each of the 255 names (no hit except Hawlucha in a tutor's "can learn" list, which is not an acquisition). The docs count 770 of 1025 species as obtainable, which is exactly 1025 - 255, so the free list and the "obtainable" derivation agree (the memory note's 254 is one short). A script that builds a species from a variable would not show up in these tables (I).
4. **Items that drive forms are not in the game (V).** `items.md` lists DNA Splicers, Reveal Glass, Prison Bottle, Zygarde Cube, Reins of Unity, Scroll of Dark, Mega Ring and Key Stone as existing but never given, and has no Rusted Sword/Shield, Drive, Memory, Nectar, Booster Energy, mask or Diancite at all. So most item-driven forms below cannot be triggered by a normal player even while the code is there.

### 8.2 Dirty, active code (18)

Species whose form or rules change by themselves in battle or through a menu item. Putting our own creature in the slot would make the engine try to change it into the entry's data. Avoid, or neutralise the entries and code first.

| Slot | Species in the slot | Why it is dirty (source) |
|---|---|---|
| 641 | Tornadus | Therian form (entry 1185), Reveal Glass menu code (`CanUseRevealGlass`), cry per form. Reveal Glass is never given (V). (entries V, code V in hg-engine / I for Origin) |
| 642 | Thundurus | Therian form (entry 1186), Reveal Glass menu code, cry per form. (entries V, code V in hg-engine / I for Origin) |
| 645 | Landorus | Therian form (entry 1187), Reveal Glass menu code, cry per form. (entries V, code V in hg-engine / I for Origin) |
| 646 | Kyurem | Fuses with Reshiram/Zekrom (DNA Splicers, `CanUseDNASplicersGrabSplicerPos`), 4 form entries 1188-1191, swaps Glaciate/Scary Face for Ice Burn/Freeze Shock or Fusion Flare/Bolt (`correct_zacian_zamazenta_kyurem_moves_for_form`), own cry per form. DNA Splicers is never given in Origin (V). (entries V, code V in hg-engine / I for Origin) |
| 648 | Meloetta | Aria/Pirouette: entry 1193; switches form when it uses Relic Song (`BattleFormChangeCheck`, `ability.c`, `battle_script_commands.c`). (entries V, code V in hg-engine / I for Origin) |
| 716 | Xerneas | Entry 1238; forced into Active Mode in every battle (`ChangeToBattleForm`, `BattleFormChangeCheck`, `battle_pokemon.c`). (entries V, code V in hg-engine / I for Origin) |
| 718 | Zygarde | Entries 1239-1241 (10%, 50%, Complete); Power Construct form change at half HP (`BattleFormChangeCheck`); Zygarde Cube never given (V). (entries V, code V in hg-engine / I for Origin) |
| 720 | Hoopa | Entry 1243 (Unbound); Hyperspace Fury can only be used by Hoopa and fails for Confined (`BattleController_BeforeMove`); Prison Bottle never given (V). (entries V, code V in hg-engine / I for Origin) |
| 741 | Oricorio | 3 style forms (entries 1244-1246), nectar items change the form (`CanUseNectar`), cry per form. No nectar item found in Origin's item docs (V). (entries V, code V in hg-engine / I for Origin) |
| 746 | Wishiwashi | Schooling: entry 1249; code switches School form in battle by species + HP (`BattleFormChangeCheck`), own cry. (entries V, code V in hg-engine / I for Origin) |
| 773 | Silvally | 17 type forms (entries 1250-1266, none for ???); RKS System + memory item sets the form; item cannot be removed; Multi-Attack takes its type from it. Memory items not found in Origin (V). (entries V, code V in hg-engine / I for Origin) |
| 774 | Minior | Shields Down: entries 1267-1273 (7 core colours); form and status-immunity code keyed on species (`BattleController_BeforeMove`). (entries V, code V in hg-engine / I for Origin) |
| 875 | Eiscue | Ice Face: entry 1339 (Noice); species checks in damage calculation, switch-in and post-move code (4 places). (entries V, code V in hg-engine / I for Origin) |
| 877 | Morpeko | Hunger Switch: entry 1341; end-of-turn form toggle (`ServerFieldConditionCheck`), Aura Wheel only works for Morpeko and takes its type from the form. (entries V, code V in hg-engine / I for Origin) |
| 888 | Zacian | Crowned form (entry 1342) from Rusted Sword, Iron Head <-> Behemoth Blade swap, item lock (`ChangeToBattleForm`, `other_battle_calculators.c`). No Rusted Sword in Origin items (V). (entries V, code V in hg-engine / I for Origin) |
| 889 | Zamazenta | Crowned form (entry 1343) from Rusted Shield, Iron Head <-> Behemoth Bash swap, item lock. (entries V, code V in hg-engine / I for Origin) |
| 964 | Palafin | Zero to Hero: entry 1375; switches to Hero form on switch-out (`SwitchInAbilityCheck`, `btl_scr_cmd_125`). (entries V, code V in hg-engine / I for Origin) |
| 1017 | Ogerpon | 11 mask/Tera forms (entries 1383-1393); masks lock the held item; Ivy Cudgel and Tera type code keyed on species (`CalcBaseDamage`, `effect_script_0309_IVY_CUDGEL`). No masks in Origin items (V). (entries V, code V in hg-engine / I for Origin) |

### 8.3 Dirty, form entries only (25)

Origin has form records with this species as base (V) but hg-engine has no active species code for them, or the forms are cosmetic, gender, regional or G-Max copies. Our creature could sit in the slot; the leftover entries (1026-1440) would just be unreachable orphans as long as nothing in Origin points at them (I: not tested in game). Cleaner choice: do not use these slots first.

| Slot | Species in the slot | Why it is dirty |
|---|---|---|
| 618 | Stunfisk | Galarian Stunfisk entry 1184 (separate regional form, orphan data) |
| 647 | Keldeo | Resolute form entry 1192; no species-specific code found in hg-engine |
| 678 | Meowstic | Female form entry 1236 (gender form; hg-engine gives wild Meowstic a random gender form only when a disabled option is on) |
| 719 | Diancie | Mega entry 1242; Mega Ring and Diancite are not obtainable (V); hg-engine also has a species mega table entry |
| 800 | Necrozma | Dusk Mane, Dawn Wings and Ultra forms (entries 1275-1278); cry per form; fusion items not obtainable (V) |
| 801 | Magearna | Original Color entry 1279 |
| 809 | Melmetal | G-Max entry 1417 |
| 812 | Rillaboom | G-Max entry 1418 |
| 815 | Cinderace | G-Max entry 1419 |
| 818 | Inteleon | G-Max entry 1420 |
| 823 | Corvknight | G-Max entry 1421 |
| 844 | Sandaconda | G-Max entry 1427 |
| 845 | Cramorant | Gulp Missile: 2 forms (entries 1280-1281); form change is ability-driven; hg-engine has no species code for it, how Origin does it is unknown (I) |
| 876 | Indeedee | Female form entry 1340 (gender form) |
| 879 | Copperajah | G-Max entry 1434 |
| 884 | Duraludon | G-Max entry 1435 |
| 890 | Eternatus | Eternamax entry 1436 |
| 892 | Urshifu | Rapid Strike entry 1344 plus two G-Max entries 1437-1438, cry code |
| 898 | Calyrex | Ice/Shadow Rider forms (entries 1345-1346), cry per form; Reins of Unity never given (V) |
| 905 | Enamorus | Therian form entry 1372, cry per form; Reveal Glass code only names the other three |
| 916 | Oinkologne | Female form entry 1373 (gender form) |
| 931 | Squawkably | 3 plumage forms (entries 1379-1381) |
| 978 | Tatsugiri | Commander: 2 colour forms (entries 1377-1378); needs Dondozo in doubles; hg-engine has no code for it (I for Origin) |
| 999 | Gimmighoul | Roaming form entry 1382 |
| 1024 | Terapagos | Tera Shell / Teraform Zero: 2 forms (entries 1394-1395); hg-engine's Tera Shift is an empty stub, Tera Starstorm is checked by Tera state not species (I for Origin) |

### 8.4 Latent (8): no Origin form entries, only code or partner rules

| Slot | Species in the slot | Note |
|---|---|---|
| 643 | Reshiram | Reshiram: only the other half of Kyurem's DNA Splicers fusion; no forms of its own |
| 644 | Zekrom | Zekrom: as Reshiram |
| 649 | Genesect | Genesect: Drive forms, Techno Blast type and item lock exist in hg-engine code, but Origin has NO Genesect form entries (V) and no Drive items (V); dormant unless a Drive is given |
| 668 | Pyroar | Pyroar: hg-engine gender-form and Z-A mega code (not in Origin: no entries, Mega Ring never given); the male/female sprites are a normal pokepic_m/pokepic_f pair |
| 710 | Pumpkaboo | Pumpkaboo: size forms in hg-engine (random size and a cry quirk), no Origin entries (V); only inert code |
| 711 | Gourgeist | Gourgeist: as Pumpkaboo |
| 854 | Sinistea | Sinistea: Antique form code in hg-engine (inert, option off), no Origin entries (V) |
| 855 | Poltegeist | Polteageist: as Sinistea |

### 8.5 Clean slots (204)

No form entry (V), no species-specific code found in hg-engine apart from the harmless lists below (V), not used by any trainer, gift, trade, static battle or encounter (V).

494, 504, 505, 511, 512, 513, 514, 515, 516, 522, 523, 527, 528, 538, 539, 556, 557, 558, 561, 577, 578, 579, 582, 583, 584, 599, 600, 601, 605, 606, 615, 621, 626, 638, 639, 640, 667, 672, 673, 674, 675, 677, 682, 683, 684, 685, 686, 687, 696, 697, 701, 707, 717, 721, 764, 765, 766, 767, 768, 772, 776, 785, 786, 787, 788, 789, 790, 791, 792, 793, 794, 795, 796, 797, 798, 799, 802, 803, 804, 805, 806, 807, 808, 810, 811, 813, 814, 816, 817, 821, 822, 827, 828, 829, 830, 835, 836, 843, 852, 853, 862, 867, 870, 871, 874, 878, 880, 881, 882, 883, 891, 893, 894, 895, 896, 897, 906, 907, 908, 909, 910, 911, 912, 913, 914, 915, 917, 918, 919, 920, 921, 922, 923, 926, 927, 932, 933, 934, 935, 936, 937, 938, 939, 940, 941, 942, 943, 944, 945, 948, 949, 950, 953, 954, 955, 956, 960, 961, 962, 963, 965, 966, 967, 968, 971, 972, 973, 974, 975, 976, 977, 980, 984, 985, 986, 987, 988, 989, 990, 991, 992, 993, 994, 995, 1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009, 1010, 1014, 1015, 1016, 1018, 1020, 1021, 1022, 1023, 1025

Names: 494 Victini, 504 Patrat, 505 Watchog, 511 Pansage, 512 Simisage, 513 Pansear, 514 Simisear, 515 Panpour, 516 Simipour, 522 Blitzle, 523 Zebstrika, 527 Woobat, 528 Swoobat, 538 Throh, 539 Sawk, 556 Maractus, 557 Dwebble, 558 Crustle, 561 Sigilyph, 577 Solosis, 578 Duosion, 579 Reuniclus, 582 Vanillite, 583 Vanillish, 584 Vanilluxe, 599 Klink, 600 Klang, 601 Klinklang, 605 Elgyem, 606 Beheeyem, 615 Cryogonal, 621 Druddigon, 626 Bouffalant, 638 Cobalion, 639 Terrakion, 640 Virizion, 667 Litleo, 672 Skiddo, 673 Gogoat, 674 Pancham, 675 Pangoro, 677 Espurr, 682 Spritzee, 683 Aromatisse, 684 Swirlix, 685 Slurpuff, 686 Inkay, 687 Malamar, 696 Tyrunt, 697 Tyrantrum, 701 Hawlucha, 707 Klefki, 717 Yveltal, 721 Volcanion, 764 Comfey, 765 Oranguru, 766 Passimian, 767 Wimpod, 768 Golisopod, 772 Type: Null, 776 Turtonator, 785 Tapu Koko, 786 Tapu Lele, 787 Tapu Bulu, 788 Tapu Fini, 789 Cosmog, 790 Cosmoem, 791 Solgaleo, 792 Lunala, 793 Nihilego, 794 Buzzwole, 795 Pheromosa, 796 Xurkitree, 797 Celesteela, 798 Kartana, 799 Guzzlord, 802 Marshadow, 803 Poipole, 804 Naganadel, 805 Stakataka, 806 Blacephaln, 807 Zeraora, 808 Meltan, 810 Grookey, 811 Thwackey, 813 Scorbunny, 814 Raboot, 816 Sobble, 817 Drizzile, 821 Rookidee, 822 Corvsquire, 827 Nickit, 828 Thievul, 829 Gossifleur, 830 Eldegoss, 835 Yamper, 836 Boltund, 843 Silicobra, 852 Clobbopus, 853 Grapploct, 862 Obstagoon, 867 Runerigus, 870 Falinks, 871 Pincurchin, 874 Stonjournr, 878 Cufant, 880 Dracozolt, 881 Arctozolt, 882 Dracovish, 883 Arctovish, 891 Kubfu, 893 Zarude, 894 Regieleki, 895 Regidrago, 896 Glastrier, 897 Spectrier, 906 Sprigatito, 907 Floragato, 908 Meowscrada, 909 Fuecoco, 910 Crocalor, 911 Skeledirge, 912 Quaxly, 913 Quaxwell, 914 Quaquaval, 915 Lechonk, 917 Tarountula, 918 Spidops, 919 Nymble, 920 Lokix, 921 Pawmi, 922 Pawmo, 923 Pawmot, 926 Fidough, 927 Dachsbun, 932 Nacli, 933 Naclstack, 934 Garganacl, 935 Charcadet, 936 Armarouge, 937 Ceruledge, 938 Tadbulb, 939 Bellibolt, 940 Wattrel, 941 Kilowattrl, 942 Maschiff, 943 Mabosstiff, 944 Shroodle, 945 Grafaiai, 948 Toedscool, 949 Toedscruel, 950 Klawf, 953 Rellor, 954 Rabsca, 955 Flittle, 956 Espathra, 960 Wiglett, 961 Wugtrio, 962 Bombirdier, 963 Finizen, 965 Varoom, 966 Revavroom, 967 Cyclizar, 968 Orthworm, 971 Greavard, 972 Houndstone, 973 Flamigo, 974 Cetoddle, 975 Cetitan, 976 Veluza, 977 Dondozo, 980 Clodsire, 984 Great Tusk, 985 ScreamTail, 986 BruteBonnt, 987 FluttrMane, 988 SlithrWing, 989 SandyShcks, 990 IronTreads, 991 IronBundle, 992 Iron Hands, 993 IronJuguls, 994 Iron Moth, 995 IronThorns, 1000 Gholdengo, 1001 Wo-Chien, 1002 Chien-Pao, 1003 Ting-Lu, 1004 Chi-Yu, 1005 RoarngMoon, 1006 IronValint, 1007 Koraidon, 1008 Miraidon, 1009 WalkngWake, 1010 IronLeaves, 1014 Okidogi, 1015 Munkidori, 1016 Fezndipiti, 1018 Archaludon, 1020 GougngFire, 1021 RagingBolt, 1022 IronBouldr, 1023 Iron Crown, 1025 Pecharunt

**Harmless species lists inside the clean set (V in hg-engine, behaviour only):** the 11 Ultra Beasts (793, 794, 795, 796, 797, 798, 799, 803, 804, 805, 806) get the Beast Ball catch-rate rule (`CalculateBallShakes`, I for Origin); the paradox mons (984, 985, 986, 987, 988, 989, 990, 991, 992, 993, 994, 995, 1005, 1006, 1009, 1010, 1020, 1021, 1022, 1023) are the species allowed to hold Booster Energy, an item not in Origin (V); `IS_SPECIES_LEGENDARY` and the mythical macro in `include/pokemon.h` have no users. Five clean slots (687, 701, 768, 870, 807) have a Z-A mega entry in hg-engine's `mega.c`; Origin has no such forms and no Mega Ring item (V), so it is dead there.

### 8.6 The guesses, confirmed or rejected

| Guess | Verdict |
|---|---|
| Kyurem | **Confirmed** (fusion, 4 entries, move swaps). Reshiram 643 and Zekrom 644 are only its partners: latent, not dirty. |
| Keldeo | **Confirmed as dirty, but weak**: Origin has a Resolute entry (1192), hg-engine has no code for it. |
| Meloetta | **Confirmed** (Relic Song form switch, entry 1193). |
| Genesect (646-649 group) | **Rejected as active**: Origin has no Genesect form entries and no Drive items; the hg-engine Drive code would only run if a Drive were held. Latent. |
| Wishiwashi, Eiscue, Morpeko, Palafin | **Confirmed** (Schooling, Ice Face, Hunger Switch, Zero to Hero; all have entries and species checks). |
| Zacian, Zamazenta | **Confirmed** (crowned forms, move swap, item lock; the Rusted items do not exist in Origin). |
| Eternatus | **Confirmed, weak**: only an Eternamax entry (1436), no code. |
| Urshifu | **Confirmed, weak**: 3 entries, cry code, no menu or battle code. |
| Calyrex | **Confirmed, weak**: 2 rider entries; Reins of Unity is never given. |
| Ogerpon | **Confirmed** (11 mask entries, Ivy Cudgel species check, item lock). |
| Terapagos | **Confirmed, weak**: 2 entries; hg-engine's Tera Shift is an empty stub. |
| Also dirty, not on the list | Xerneas (forced Active Mode), Zygarde, Hoopa, Silvally, Minior, Oricorio, the three Forces of Nature (Reveal Glass), Necrozma, Magearna, Diancie, Cramorant, Tatsugiri, Gimmighoul, Squawkably, Enamorus, the three gender-form species Meowstic/Indeedee/Oinkologne, Galarian Stunfisk and the 8 G-Max species. |

### 8.7 Not verified

- Nothing was run in the emulator. Whether Origin's own battle code really contains each form change above (Schooling, Ice Face, Hunger Switch, Zero to Hero, Shields Down, Gulp Missile, Commander) is inferred from the abilities and form entries being in its data (V) and from hg-engine; the overlay was not disassembled for species checks (I).
- The 8 G-Max and Eternamax entries exist in Origin's data, but whether Origin has Dynamax at all was not checked; if not, those 9 are inert (I).
- Which forms of our slot the engine would pick up if we left the old entries in place (and whether they could be deleted) was not tested. For a dirty slot the safe action is to overwrite the entries too, or just not use the slot.
- Tutor "can learn" lists are species lists inside scripts (one tutor lists Hawlucha). They apply to every slot, clean or not: our creatures will not be on any tutor's list unless the scripts are edited.
- Gender sprite pairs (`pokepic_m`/`pokepic_f`) were compared and are not a usable signal (the two NARCs differ for most species); no sprite-dimorphism check was done (I).

## 9. Special assets beyond the per-species set (2026-11-11)

Question (Arvind): do we know every picture or model in the game that shows one particular Pokemon or character outside the normal per-species set
(front/back 2 frames, shiny palette, icon, follower, footprint, cry, dex data)? Method: every NARC of Origin (`~/sigma-origin/x_spike_backup/files`)
was compared member by member with the vanilla US extract (`x_vanilla`; V), the NARC names and loaders were read in the pret decompilation (`src/`, `asm/`,
`include/constants/mmodel.h`), and a few pictures were rendered locally to see what they show. Only numbers and file names are written here.
Labels: **V** = verified in a file or in decompilation source, **I** = inferred, **U** = unknown. Caveat: Origin is built on the Japanese ROM and vanilla is US, so
"changed" means the bytes differ from the US file; text banks and tables that Origin enlarged always differ. Member numbers of untouched NARCs match the decompilation (V).

### 8.1 What Origin changed (V, from the member comparison)

| NARC | What | Change |
|---|---|---|
| `a/0/4/6` titledemo | title screen | members 0-4 and 15 (logo and 2D backgrounds; two backgrounds shrank 30784 to 24640 bytes). **The Ho-Oh/Lugia 3D members 20-29 and the sparkle models 38-43 are untouched** |
| `a/2/6/2` gs_opening | opening movie | members 1, 3, 4, 5, 13 (palettes, logo, one background). All sprite and 3D members untouched |
| `a/1/2/0` intro | Prof. Oak's speech pictures | members 12-29 (the player boy/girl pictures, two palettes shrank 552 to 72 bytes). **Marill sprite members 53-66 untouched** |
| `a/0/9/3` choose_starter_sub_res | starter selection, sub screen | members 6, 7, 11, 17, 20, 23: these are the player's head sprites (cap seen from above), not Pokemon. The 3D ball/table models (`a/0/8/2`) are untouched |
| `a/0/8/1` mmodel (map-object sprites and models) | 78 of the first 863 members | almost all human NPCs, gym leaders, the player (recoloured/redrawn). **The only Pokemon-like object touched is `YADON` (member 209, the tailless Slowpoke)**; 161 `GSDSBOY`, 89 `BANZAIHERO`, 224 `JUPETTA` are people. Origin appends members 863-1733 (more followers) |
| `a/0/0/6`, `a/0/5/8` | trainer back/front pictures | 44 of 85 and 132 of 645 members (section 7) |
| `a/1/7/5` resdat | sprite resource id lists | members 30, 31, 79 only |
| `a/0/7/4`, `a/2/1/4`, `a/1/3/3` | dex data, Giratina-form data, dex area data | enlarged to 1026 species (e.g. area data 3962 to 8210 members) |
| `data/pokepic_m.narc`, `pokepic_f.narc`, `pokeicon.narc`, `pokemon_overworld_info.narc` | Origin's replacement for `a/0/0/4` (now a 1-byte stub), the icon NARC and the follower table | 11528 members (1441 x 8), 2890, 1026 (6 bytes each) |
| `extra/intro_data.narc` (10 members), `a/2/6/5` (18) | Origin-only | a re-made intro with its own backgrounds, plus a clothes/dressing-room screen (one member shows a boutique interior). **No Pokemon found in them** (rendered; U for intro_data's cell/anim members) |
| `extra/new_battle_bg.narc` (104), `battle/battle_graphics.narc` (51), `extra/ev_set.narc` (3) | Origin-only battle backgrounds and battle graphics | not checked for Pokemon (U) |

Not changed by Origin (V, byte-identical): `a/1/7/4` demo/legend (Ho-Oh/Lugia cutscene models), `a/1/9/4` puzzle_gra (Ruins of Alph panels, `a/1/7/2`), `a/1/6/9` performance (Pokeathlon stats),
`a/2/4/7-9` (Pokewalker app), `a/0/6/9` pokefoot (497 members: footprints only up to Gen 4), all of `a/1/4/x` Pokegear/radio/phone, the 28 Unown follower objects.

### 8.2 Easy: picture swap in the formats we already write (follower-style sprite sheets, palette and tile data)

| Asset | Where (V unless marked) | Shows | Origin | If our mon takes the role |
|---|---|---|---|---|
| **Follower sprites** of every species, also used for the 1544 map objects that show a story Pokemon (Burned Tower beasts, birds, Mewtwo, Dialga/Palkia, Regis, Celebi, Kimono Girl Eeveelutions) | `a/0/8/1` `MMODEL_FOLLOWER_MON_*` members 297-862 (then Origin's 863+), BTX0 4544 bytes | the species | untouched for species 1-493 | already covered by the follower pipeline; nothing extra |
| **Separate static copies** (73 objects) | `a/0/8/1` members below 297 and Origin's extra ones (list in DEX_REPLACEMENT.md section 2) | Sudowoodo tree `USOKKY` (186), sleeping Snorlax `KABIGON` (194), Lapras `RAPURASU` (228), Red Gyarados `RGYARADOSU` (183), tailless Slowpoke `YADON` (209), 5 Rotom appliances (196-200), Pikachu `PIKACHU` (68), plus static Clefairy, Miltank, Ampharos, Kyogre etc. | only `YADON` | Same file type as followers (BTX0, 32x32 frames; `lw/btx.py` writes it). Rotom, Sudowoodo, Lapras, Gyarados have fewer frames (1128-4712 bytes): count frames first (U: exact frame order of the NPC format, see 1.3). 183/186/194/228 are single-frame or few-frame, the easiest of the legendary-like roles |
| **Oak's Marill** | `a/1/2/0` members 59-66 (NCLR 59/63, NCGR 60/64, NCER 61/65, NANR 62/66); drawn as a 2D sprite with palette overrides 4 and 5 (`src/oaks_speech.c` states `APPEAR_MARILL`..`HIDE_MARILL`, `src/oaks_speech_obj.c`); rendered: Marill plus a Poke Ball in 3 poses, blue and red palette | Marill, hard-coded; `PlayCry(SPECIES_MARILL)` | untouched | Redraw member 64 (4528 bytes = 141 tiles, 4bpp) and keep the cell bank, or keep Marill (Origin keeps it). The cry follows the Marill slot, so a mon in slot 183 also changes the cry |
| **Opening movie, scene 3 "Unown, Eusine, Silver silhouette"** | `a/2/6/2` members 65-72 (struct fields `silverSilhouetteSprite`, `eusineSprite`, `unownSprites[3]`, `include/intro_movie_internal.h`) | 3 Unown, characters | untouched | 2D sprite sheets; swap pictures only if Unown is replaced (Sigmanian Unown is planned) |
| **Opening movie, scene 4 starters** | `a/2/6/2` members 81-96 (`starterSprites[3]`, hands, sparkles) | Chikorita, Cyndaquil, Totodile | untouched | 2D sprites; Origin never changed them, so the opening still shows the Johto starters. Replace only if wanted |
| **Opening movie, scene 1 bird and sun** | `a/2/6/2` members 23-30 (`sunSprite`, `birdSprite`) | the bird is Ho-Oh in HG (I: not looked at as a picture) | untouched | one animated sprite, 2D |
| **Ruins of Alph sliding puzzles** | `a/1/7/2` puzzle_gra (16 members); `alph_puzzle.c` takes `puzzleIndex + member 4` NCGR for panels | Kabuto, Omanyte, Aerodactyl, Ho-Oh panels (V from the code: 4 puzzles; which fossil is which: I) | untouched | 4 pictures 6x6 tiles; replace tile graphics, the rotation/position tables (`dAlphPuzzles`) are code |
| **Dex and species search** | `a/0/7/4` zukan_data: per species `height`, `weight`, `body_style` (the body-type search icon), `scale`/`ypos` for the player and the mon in the size-comparison screen (`ov18_021E5C40.c`) | numbers, not pictures | enlarged to 1026 | numbers only (see section 5.2); the icons for body types are shared UI graphics in `a/0/6/8` (33 members changed by Origin: UI) |
| **Wallpapers of the PC (box)** | constants in `include/constants/box_wallpaper.h`: bonus wallpapers Heart, Soul, Big Brother, **Pokeathlon, Trio, Spiky-eared Pichu ("Spiky Pika"), Kimono Girl, Revival** | art of fixed Pokemon (I: which ones show which) | not checked (U: NARC not found, belongs to the PC overlay) | decorative; do nothing or redraw |
| **Mail graphics** | `mail.c` `sFormOverrides`: icons of Giratina Origin, Sky Shaymin and 5 Rotoms; mail designs Grass..Brick | form icons only | I: untouched | only matters for those slots |
| **Pokewalker (Connect to Pokewalker app, overlay 112)** | loads NARCs `a/2/4/7`, `a/2/4/8` (540 members, each 384 bytes after LZ decompression), `a/2/4/9` (V: ids 0xF9-0xFB in `asm/overlay_112.s`); `a/2/2/8` has 533 palettes of 1072 bytes in the same 540 count (U who uses them) | I: one small (about 1-2 bit) walker picture per species slot up to Gen 4 plus forms; layout not decoded (a tile dump looked like two stacked figures) | untouched, so slots above 493 and our mons have none | per-mon file; extra slots needed for dex numbers above 540 (the count caps at 540). The cheapest fix is to leave it: the walker shows the slot's old picture. The course lists (27 courses, `pokewalker_courses.h`) hold species numbers (U where) |
| **Pokeathlon** (overlays 96-99, assembly only) | NARCs `a/1/6/9` performance (554 x 20 bytes: per species stat ratings), `a/2/1/9`, `a/2/5/8` (100 x 8 bytes), plus `poke_icon` and `mmodel` (V: ids 169, 221, 260, 81, 20 in `asm/overlay_96.s`) | the player's Pokemon drawn from icon/follower sprites (I), event art is generic | untouched | stats table needs our species at their slots (20 bytes each; only up to species 553); art: I: no per-species pictures beyond icon and follower |
| **Hall of Fame** | `register_hall_of_fame.c`: standard front sprite plus per-species animation table; **hard-coded position fix for Krabby and Kingler** (V lines 1535 and 1642) | the party | untouched | nothing, unless a mon takes Krabby's slot (then the offset applies to it) |
| **Pokegear map, radio, phone** | `a/1/4/x` (3 map members changed: 70 members) | no species art (I) | map only | none |
| **Trainer Card, ribbons, bag, shop** | `a/0/6/0` etc. | the player's trainer class picture; ribbons are generic icons (I) | trainer pics changed (section 7) | none |

### 8.3 Harder: big sprites with several frames, or special code

| Asset | Where | Notes |
|---|---|---|
| **Ho-Oh and Lugia in the cutscenes** (flying in over the Bell Tower and the Whirl Islands, level 95 gift) | `a/0/8/1` members 210 `HOU_OBJ01`, 211 `LUG_OBJ01`: BTX0 of 14700 bytes, 7 frames of 64x64, sit on a 64x64 plane model (`mmdl_m64x64`); `src/field/legend_cutscene_camera.c` `Task_BirdFinalApproach` sets species, flap delay and flap sound per game | both untouched. Origin keeps the full cutscene (V). The bells, leaves, waves, light ring are separate 3D models in `a/1/7/4` (110 members, e.g. members 34-35 are `NSBMD`/`NSBCA` used by `BirdFinalApproach`) and contain no Pokemon (I). **Needs 7 new 64x64 frames** from a new bird; the code picks species 249/250 and uses their cry, so the slot decides the cry. The map objects `obj_D17R0110_hou_obj01` and `obj_D40R0107_lug_obj01` stay |
| **`TSURE_250`** (members 274, 275) | `a/0/8/1`, BMD0 model 17236 bytes with a 48x48 plane | named for species 250 (Ho-Oh): a 3D-plane Pokemon that follows or stands on the map; where it is placed: U |
| **`SPPOKE4`** (269) | BMD0 on a 64x64 plane | "special Pokemon 4": U which |
| **Embedded Tower Kyogre, Groudon, Rayquaza** | Origin events with the standard follower sprite or the static copies; scripts take the species number (V per DEX_REPLACEMENT.md and trades_tutors.md) | only a slot swap needed; Kyogre has a static copy (list above) |
| **Opening movie scene 2 Ethan and Lyra**, scene 5 | `a/2/6/2` members 31-38, 73-80 | characters, not Pokemon (V from struct names) |
| **Pokemon that change look with a form** (Unown 28 letters, Deoxys 4, Giratina 2, Shaymin 2, Rotom 6, Castform, Arceus 17) | `a/0/8/1` follower forms 501-528 (Unown), 716-719, 837-862 | each form is its own follower and its own front sprite set; code uses `SPECIES_` special cases in `pokedex.c`, `overlay_94.c`, `mail.c`, `follow_mon.c` (V) |
| **Pokemon cries as special events** | `PlayCry(SPECIES_...)` at the title (`TITLE_SCREEN_SPECIES` = Ho-Oh in HG), Oak's Marill, Chatot cry (`sound_chatot.c`, a recorded user voice), Ho-Oh/Lugia final approach | the species slot decides which cry plays. The title cry is a compile-time constant (V, `src/title_screen.c` lines 36-38) |

### 8.4 3D models (NSBMD/BMD0), a separate and harder category

| Model | NARC and member | Shows | Origin |
|---|---|---|---|
| **Title screen Ho-Oh** (HG) | `a/0/4/6` members 25 (NSBMD), 26 (NSBCA bones), 27 (NSBTA texture scroll), 28 (NSBMA material anim), 29 (NSBTP texture swap); `TitleScreen_Load3DObjects` in `src/title_screen.c` lines 493 and 496 | Ho-Oh, 1009 polygons, 28 bones (STORY_ROLES.md section 5) | untouched |
| **Title screen Lugia** (SS) | the same members 20-24; stays in the HG ROM but is unused (V: code branch on game version) | Lugia | untouched, unused |
| **Title sparkles** | members 38-40 (HG) and 41-43 (SS) | an effect, not a Pokemon | untouched |
| **Opening movie 3D** | `a/2/6/2` members 97-105: three map models of New Bark, Goldenrod and Ecruteak with `NSBCA`/`NSBTA` | maps | untouched |
| **Starter selection** | `a/0/8/2` main_res members 00-07: table, turntable, balls, ball effect (`choose_starter_app.c`) | Poke Balls only. The starter Pokemon themselves are standard front sprites (`sSpecies` = Chikorita, Cyndaquil, Totodile) | untouched; Origin starts in Pallet and does not seem to use this screen (I) |
| **Legend cutscenes** | `a/1/7/4` demo/legend (110 members) | bells, light, leaves/waves | untouched |
| **Map 3D objects** | `a/0/4/0` (353 members, BMD0 on the map) | buildings, props | I: not Pokemon |
| **Dynamic overworld planes** | `a/0/8/1` BMD0 entries 269, 274, 275, 277 | billboard planes for the 48/64 px Pokemon sprites (see 8.3) | untouched |

So the only real 3D Pokemon is the title Ho-Oh (HG) / Lugia (SS). Replacing it is a Blender job: rigged low poly model of at most about 1,700 triangles (the DS draws at most about 2048 polygons a frame), bone animation, then convert to NSBMD/NSBCA (tool and format not tried here; U).
Easy fallback: keep Ho-Oh and hide it behind a drawn background, or accept a re-themed title using only members 0-4 that Origin already replaced.

### 8.5 Code, not pictures

- Compile-time species: `TITLE_SCREEN_SPECIES` (cry), Oak's Marill cry, `sSpecies` of the starter screen, Chatot cry, Krabby/Kingler offset in Hall of Fame, `SPECIES_` cases for forms. Changing a *slot's* content changes all of them without code; changing *which* slot needs an overlay-14 style patch (docs/ORIGIN_CUSTOM_CODE.md).
- Special static battles and gifts (Ho-Oh gift, Lugia, Snorlax, legendary quests in `~/sigma-origin/docs/trades_tutors.md`) take a species number from a script; the slot swap covers them (V, DEX_REPLACEMENT.md section 2).
- Sudowoodo is not fought in Origin (it runs off after watering): only the tree picture and the script matter.

### 8.6 Spriters Resource asset 27185

Not identified. The site returns HTTP 403 to automated fetches (both the asset page and the game page) and a web search found no entry for the number; the game page only shows "40 assets". Arvind should open https://www.spriters-resource.com/ds_dsi/pokemonheartgoldsoulsilver/asset/27185/ and tell us the sheet name; the ROM-side inventory above does not depend on it. (U)

### 8.7 Still unknown

- Which NARC holds the PC box wallpapers, and which Pokemon the bonus ones show.
- Where Pokewalker course species lists and the Pokewalker picture layout are; whether `a/2/2/8` belongs to the Pokewalker.
- What `TSURE_250` and `SPPOKE4` are used for, and the exact frame layout of NPC-style sheets (needed for Snorlax/Lapras/Gyarados replacements).
- Contents of Origin's `extra/intro_data.narc`, `extra/new_battle_bg.narc`, `battle/battle_graphics.narc` beyond "no Pokemon seen".
- Whether Origin's Pokeathlon, Safari Zone, Bug-Catching Contest and Kimono Girl dance have any hard-coded species outside the NARCs listed (overlays 96-99 are assembly only).
- Whether vanilla US and Origin's Japanese base differ in file layout for members that do not show up as changed (hash comparison cannot tell).

## 10. Translation and native play (2026-11-11, web research)

- **Scandinavian translations:** none found for any Gen 4 DS game or DS hack (Norwegian, Swedish or Danish), finished or in progress; official Pokemon games were never localised into Norwegian or Danish. Reddit and Discord could not be searched directly. The Origin EN translation repo's pipeline (JSON text banks, `msgtool.py`, `qa.py` width checks against the 216 px two-line box, `build.py` to ROM + xdelta, STYLE.md, AGENTS.md, AI first draft + human review) is reusable for a Norwegian translation; ask its maintainers about a downstream fork. Glyphs: the game's character table has Æ Ø Å æ ø å; still to check that the font draws them.
- **Native play / recompilation:** pret/pokeheartgold is a work-in-progress disassembly (not fully C), builds matching US ROMs, active (last commit 2026-11-09). A Platinum SDL port exists (`arcanite24/pokeplatinum-portable`); no HeartGold PC port and no general DS static recompiler were found. Origin is JP HeartGold plus binary patches; a native Origin would need a HeartGold PC port first and then every Origin change (injected code, data, text) lifted onto the decomp. Assessment: months of expert work; emulator or the DS ROM stays the practical route, with the decomp as reference.

## 11. Our mons take the whole main story (Arvind, 2026-11-11)

"Våres mons skal erstatte hele hoved historien ... når de snakker om lugia og hooh så gjelder det våres": every story role
(starters, Oak's intro Pokemon, Ho-Oh and Lugia, the beasts, the weather trio, static encounters, the text that names them)
goes to one of our mons; official species stay in the game and come back after the main story, like Black and White.
So the special assets of section 9 are required work, not optional. Two more things found in the decompilation
(pret `asm/unk_020517A4.s`, V):

- **Legendary battle intros are keyed by species number** (`_020FC3B4`): Raikou, Entei, Suicune, Lugia, Ho-Oh,
  Groudon, Kyogre, Rayquaza, Mewtwo, Latios and Latias each get a special encounter effect (and their music). For our
  legendaries to get them, this small table in arm9 must be patched to our species numbers (a data patch; find the same
  table in Origin's arm9 by its bytes).
- **Important trainers get special battle intros and music by class** (`_020FC3CA` + `_020FC40A`): all 16 gym leaders,
  the Elite Four, the Champion, the rival, the four Rocket executives, the Rocket boss, grunts, Kimono Girls and Red
  (e.g. `SEQ_GS_VS_GYMREADER`). These are the "Trainer Vs." portraits (The Spriters Resource asset 27185 shows them:
  close-up portraits of Ethan, Lyra, Silver, every leader, the Elite Four, Rocket, Giovanni and the Frontier Brains).
  **Replacing an important character therefore also needs a VS portrait.** Where the portraits are stored is not yet
  found (I: the encounter effect graphics loaded by this code).

**Base patch:** we switch from EN v1.0.0-rc3 to the maintained English translation (v1.0.0-rc8 of 2026-10-13 or newer)
and use its tools; offsets verified on the old base must be checked again after the switch.

**Native play:** native HeartGold PC ports now exist: [elyro1/pokeheartgold_pc-port](https://github.com/elyro1/pokeheartgold_pc-port)
(built from ctrl-cheeb-del's decompilation with libntr; vanilla US HeartGold/SoulSilver only, experimental) and
[Gen2Recomped](https://github.com/UNDERdecoded/Gen2Recomped) (a hand-written rebuild that reads data from canonical dumps;
HeartGold/SoulSilver plus a few GBC hacks). Neither runs Origin, which is a binary hack of the Japanese ROM: native Origin
would need Origin's changes lifted onto the decompilation first (section 10).

## 12. Every story tie to official species (2026-11-11)

Question (Arvind): "noe annet enn det? sjekk gjennom spillet". Besides the Ho-Oh title model, the Ho-Oh/Lugia cutscenes, the starters, Oak's Marill, the
beasts and the weather trio, what else in Origin HeartGold links the story to a particular species? Rule from section 11: our mons replace every story role;
official species come back after the main story.

Sources (all read locally, nothing copied into the repo except counts, ids and a few short phrases): Origin's player docs (`~/sigma-origin/docs`:
`trades_tutors.md`, `encounters.md`, `trainers.md`), the extracted Origin ROM (`x_spike_backup`: `a/0/3/2` map events parsed by hand, `arm9.bin`, overlays),
the English translation repo (`work/translate/banks/*.json`, 802 a027 banks plus 4 battle banks, `play_order.json`, `bank_maps.json`; `guide/` quest guide
with 368 quest entries) and the pret decompilation (scripts, `src/`, `asm/`). Labels: **V** = verified in a file, **I** = inferred, **U** = unknown.

**Which part of Origin is "the main story".** The guide's chapters 1-13 are Kanto up to the first Hall of Fame (Indigo Conference, Blue), 14-32 are Mt. Silver,
Johto, the Rocket League-HQ chain, the island pilgrimage and the final Hall of Fame, and 33-34 are post-game (V, `guide/chapters/*.toml`, `kind = "story"` vs
`"postgame"`). Quest entries are tagged main (96) or side (272); 147 of the 368 name a species in the title (24 main, 123 side). "Before first HoF" and
"before final HoF" below follow these chapters.

### 12.1 Summary: what must be replaced, in order of size

| # | Tie | Size | Replace by | Effort |
|---|---|---|---|---|
| 1 | Trainer teams | 1,023 teams, 3,891 party slots, 495 different official species (458 of Gen 1-4, 37 later); Kanto-side maps 589 teams / 2,100 slots, Johto-side 419 / 1,749, 15 not placed (V, `trainers.md`) | party data (slot swap or re-pointing) | big but data only |
| 2 | Story text that names a species | 4,791 of 24,434 main-story map-script strings (19.6 %), 6,332 mentions, 429 different species (V, EN banks) | text edit (names, per bank) | big, semi-automatic |
| 3 | Wild encounter tables | 136 tables, 4,087 slot rows, 523 different species (V, `encounters.md`) | table data | medium |
| 4 | Map objects that show a Pokemon | 1,619 objects in 489 map event files: 1,537 follower-sprite objects (417 different sprites), 48 static follower objects, 34 special objects (V, parsed) | sprite id or sprite picture | medium; most are covered by the follower pipeline |
| 5 | Gifts, static battles, eggs, trades | 159 gift/battle/egg rows (118 battles, 37 gifts, 4 eggs), 13 trades, 32 "wild" fights built as trainer records (V) | script/trade data | medium |
| 6 | Move tutors keyed by species | 89 tutor rows, 79 with a species list (5,209 entries in all), 6 single-species checks (V) | script lists | medium (balance, not story) |
| 7 | Code keyed by species number | about 12 places that matter for the story (section 12.6) | data patches (some overlay-14-style) | small but each is a trap |
| 8 | Special pictures/models | already in section 9 (title Ho-Oh model, Ho-Oh/Lugia plane objects, Marill 2D sprite, Alph puzzles, opening movie) | art | big art |
| 9 | Pokegear phone, radio, TV, minigame text | 178 + 13 + 15 + 29 strings name a species (V) | text edit | small |

New finds compared with sections 8 and 9 (not listed there before): the 32 wild-fights-as-trainers, the 1,537 follower-sprite map objects, Safari Zone owner
test species, Trainer House team, the Magikarp record script, species-checking tutor lists, gym rules that depend on types or stats, "Pokemon League" map showing
stolen legendaries, and the counts in 12.3 to 12.5.

### 12.2 Pokemon given, traded, fought or scripted in the story (V from `trades_tutors.md`, quest guide, decomp scripts)

Counts: 159 rows = 118 `WildBattle`, 37 `GiveMon`, 4 `GiveEgg`; 48 of the battles are the Safari Zone Gate challenge list (below), so 111 are real events.
"Phase" = when it happens: **K** before the first Hall of Fame (Kanto), **J** between the first and final Hall of Fame (Johto and the Rocket chain),
**P** after the final Hall of Fame, **S** side quest (any time before P).

| Group | Who (Origin species) | Where / what | Phase |
|---|---|---|---|
| Player starters (3) | Bulbasaur, Charmander, Pikachu (the choice) + Oak's intro Marill | Pallet Town (already known, section 9 and STORY_ROLES) | K |
| Starter-dependent side gifts | Poliwag (Bulbasaur starters), Charmander/Meowth/Mankey/Pikachu "thief" events by starter, Light Ball / Charcoal | Pallet, Viridian, Route 2; one entry per starter (guide ch. 1) | K |
| Early gifts | Eevee (Viridian Forest), Charmander (Pewter, Route 3), Bulbasaur and Growlithe (Route 5 shelter), Squirtle (Route 9), Horsea (Vermilion), Hitmonlee/Hitmonchan (Saffron dojo), Lapras (Silph, lv 70), Cubone, Bellsprout, Ralts, Doduo, Barboach, Dratini (Resort Zone), Torchic, Treecko egg | listed place by place in `trades_tutors.md` | K, S |
| Legendaries, Kanto side (see 12.8 for the exact timing; corrected 2026-11-11) | Gifts before the final HoF: Regirock/Regice/Registeel (Rock Tunnel, round 1), Latios/Latias (Secret Forest, round 4), Mew (Five Island, pilgrimage), Mewtwo (Indigo Plateau, take it before the Elite Four). Story only, cannot be caught before the final HoF: Zapdos (trainer-style fight, no catch), Articuno (no Balls), Moltres, Kyogre, Rayquaza (Rocket takes it); Mewtwo in the Cinnabar lab (scripted) | guide ch. 3, 5, 6 | K / J |
| Johto story Pokemon | Slugma (Cherrygrove, main), Arceus, Dialga, Palkia (Giovanni/Rocket catch them, main), Giratina (Reversal Cave chase), Entei (Alph, Molly), Suicune (Ice Path trap), Raikou (Route 47 device), Ho-Oh and Lugia (stolen by Rocket, fought trainer-style; main), Celebi (Forest of Time, catchable), Salamence (Route 34, catchable), Sudowoodo (Route 36 tree), Miltank (MooMoo Farm), red Gyarados (Lake of Rage, catchable), Chatot (Rocket HQ), Teddiursa (S.S. Anne), Swinub (Ice Path), Kabuto (Alph chamber) | guide ch. 8-12 | J |
| Johto side gifts | Cyndaquil, Totodile, Chikorita (wild "challenger"), Chimchar, Shinx, Houndour, Tentacool, Shellos, Mareep/Slugma/Wooper egg (Violet, choose one), Heatran (Tuesdays), Uxie/Mesprit/Azelf (Lake of Rage, lv 90) | `trades_tutors.md` | J, S |
| Post-game legends (catchable only after the final HoF) | Ho-Oh (Bell Tower, lv 95), Lugia (Whirl Islands, lv 95), Zapdos, Moltres, Articuno, Kyogre (Blue Orb), Groudon (Red Orb), Rayquaza (Jade Orb), Deoxys, Jirachi, Entei/Suicune/Raikou (after the Burned Tower scene), Dialga/Palkia/Giratina (after Lance's visit), Regigigas and Arceus (Sinjoh Ruins), Cresselia/Darkrai, Celebi time-travel event | guide ch. 2, 3, 5, 6, 9-12, 33-34: "after the final Hall of Fame" | P |
| Safari Zone Gate challenge list | 48 battle rows, all level 10: Hoenn and Sinnoh species only (Absol ... Turtwig) | Safari Zone Gate | S |
| Other | Manaphy egg (Alto Mare), Jirachi (Frontier Access), Shaymin (Ilex shrine), Kecleon, Onix form, Hypno, Mr. Mime (Route 21), Electrode x3 at Victory Road and Team Rocket HQ | various | S |

In short (corrected 2026-11-11, see 12.8): before the final Hall of Fame the story **uses** the box legendaries (Rocket steals or captures them, you fight Zapdos, Articuno, Ho-Oh, Lugia, Suicune and others trainer-style) but you can only **keep** Regirock, Regice, Registeel, Latios, Latias, Mew, Mewtwo, Celebi, Shaymin, Uxie, Mesprit, Azelf, Heatran and Manaphy; the rest become catchable after the final Hall of Fame. Our dex must cover every one of them for the story, post-game or not (section 12.11).

**In-game trades (13, V):** Butterfree/Raticate pair (S.S. Anne), Budew for Ditto, Goldeen for Feebas, Hoothoot for Pineco, Bagon for Torkoal, Shellder for
Mudkip, Dragonair for Porygon2, Bonsly for Rhydon, Exeggutor for Skarmory, Beedrill for Onix, Dugtrio for Gyarados (loan), Pidgeot (loan, Viridian Forest).
Both sides of every trade are species numbers in `a/1/1/2`; the loans return a Pokemon to the NPC.

**Vanilla script references (pret, V):** 81 of the 1,502 vanilla scripts mention a `SPECIES_` constant (78 different), among them the beasts' cries, the
Dialga/Palkia/Giratina gifts (`D51R0201`), Rotom appliances, the three Egg gifts, Kyogre/Groudon/Rayquaza (`D52R010x`), the Lake of Rage Magikarp
record (`T29`) and the Snorlax roadblock (`R11`, `R12`). Origin keeps these scripts and rewrites many; the species numbers in them are the only link.

### 12.3 Pokemon seen as map objects or in cutscenes (V: `a/0/3/2` parsed, 6,731 objects in 489 zone files)

Origin did not keep vanilla's 137 static follower objects (it has 48 of 25 kinds). Instead it places **1,537 follower-sprite objects** (sprite ids 428-976, the
same table as pret's `SPRITE_FOLLOWER_MON_*`; 417 different sprites, in 277 map files) and 34 special objects. Map names below come from `bank_maps.json` and are
approximate (I).

| Role | Objects (V) | Notes |
|---|---|---|
| Ho-Oh `HOU_OBJ01` | 1 (Bell Tower) + a follower in the Pokemon League HQ map | the 64x64 cutscene plane; section 9 |
| Lugia `LUG_OBJ01` | 2 (Whirl Islands) + a follower in the League HQ map | same |
| Entei / Raikou / Suicune followers | 10 / 7 / 9 (Burned Tower, Ruins of Alph, Routes 25/27/30/42/47, Cherrygrove, Cianwood, Ice Path, New Bark, Victory Road) | the beasts are not only in the Burned Tower; each location needs the same replacement |
| Celebi followers | 3 (Ilex Forest) | |
| Mew followers | 8 (Mt. Moon, Route 1, Route 27, Five Island, Cinnabar) | Rocket's Mt. Moon story |
| Mewtwo followers | 4 (Cerulean Cave, Cinnabar, Indigo Plateau, League HQ) | |
| Kyogre / Groudon / Rayquaza followers | 3 / 2 / 2 (League HQ, Seafoam, Mt. Moon, Sky Pillar) | |
| Dialga / Palkia / Giratina (+ Origin form) / Arceus | 3 / 7 / 2+3 / 3 | Sinjoh Ruins, League HQ, Radio Tower, Ritual Shrine, Victory Road |
| Zapdos / Moltres / Articuno | 3 / 5 / 2 | Power Plant, Seafoam, Whirl Islands, League HQ |
| Slowpoke (followers) + `YADON` | 21 followers (Azalea, Route 43, Slowpoke Well) + 7 tailless `YADON` (Burned Tower, Ice Path, Frontier Access, Route 42, Route 47, Six Island) | the tailless one is the only Pokemon object Origin redrew |
| Lapras | 11 `RAPURASU` objects (Alto Mare, Sevii islands 1-4, Route 40, Route 47) + 2 followers | the Lapras "ride" boat quest |
| Red Gyarados `RGYARADOSU` | 3 (Lake of Rage; vanilla had 1) | |
| Snorlax `KABIGON` | 2 (Route 12, Five Island) + 1 follower on Route 32 | |
| Sudowoodo tree `USOKKY` | 1 (Route 36) + `TREE` 2 | |
| Rotom appliances (5) | 5 (Silph Co. Rotom's Room) | |
| Eevee and its evolutions | Eevee 3, Vaporeon 2, Jolteon 2, Flareon 2, Espeon 1, Umbreon 1, Leafeon 5, Glaceon 3 | the "Kimono Girl Eeveelutions" are **not** objects: V, in vanilla and Origin they are trainer party Pokemon. Origin has 3 Kimono Girl teams (Sakura: Vaporeon..., Tamao x2: Umbreon...) in `trainers.md`; the Dance Theater has no Eeveelution object |
| Pikachu `PIKACHU` / followers | 2 + 17 followers | |
| Marill, Pichu, Clefairy, Miltank, Murkrow, Ampharos, Unown E/H/O/P/?/! | 7, 6, 4+6, 16+5, 3+3, 1+2, 6 | the Alph Unown are letter-form followers |
| Electrode | 10 followers (Cianwood, Fuchsia, Indigo, Route 15, Rocket HQ) | the "item ball" Electrodes (Victory Road 1F, Power Plant) are scripted battles |
| Dragonite | 17 followers | Lance, Lake of Rage, Mt. Silver, Radio Tower |
| Mt. Silver Red | trainer, not an object | Origin has 8 "PKMN Trainer Red" teams used as a partner; the vanilla Mt. Silver fight (Pikachu, Espeon, Snorlax, Venusaur, Charizard, Blastoise) was not found as such (U), see 12.4 |

Not Pokemon but looks like one in the sprite list: `MONSTARBALL` (item balls, 264 in vanilla). One object uses sprite id 1565, beyond vanilla's range (Cerulean City, U which).
**Cutscenes (V, pret):** Ho-Oh and Lugia flying in (`legend_cutscene_camera.c`, overlay 2), Celebi and Spiky-eared Pichu events, Shaymin (`event_cutscene_shaymin.c`),
Kimono Girls summoning the legendary, Rocket's Electrodes (Radio Tower and Power Plant scripts), the legendary-bird scripts (`D11R0105`, `D41R0105`: Articuno
and Moltres), Kyogre/Groudon/Rayquaza in the Embedded Tower (`D52R010x`), the Latios/Latias roamers, Arceus (`D51R0301`) and the vanilla beasts (`D18R0102`).
Origin-only events (guide): the League HQ chain makes Giovanni capture Arceus, Dialga, Palkia, Kyogre, Rayquaza, Zapdos, Moltres, Mewtwo, Ho-Oh and Lugia in
turn; the League HQ map shows them as followers (I: from the object list). That whole chain is built from named species.

### 12.4 Trainer teams (V, parsed `trainers.md`)

- 1,023 team records (the whole of `a/0/5/5`), 3,891 party slots. Kanto-side maps 589 teams (2,100 slots, 461 species), Johto-side 419 (1,749 slots, 375 species),
  15 not placed on any map. Union: 495 species, 458 of them Gen 1-4.
- Named teams: Rival Blue 19 teams (Pidgey, Squirtle line, Venusaur, Umbreon ...), Gym Leaders 33 (14 Kanto + 19 Johto), Elite Four 8, Rocket bosses and executives
  58 (Giovanni 8, Archie 7, Maxie 8, Petrel 6, Lawrence 6, Ariana 5, Cyrus 4, Charon 4, Archer 3, Proton 3, Marauder 3, 1 unnamed boss; 3 not placed),
  Steven 8 and Cynthia 8 (plus 2 Champion records), Red 8 (a partner in multi battles, Viridian Forest to Victory Road; a separate Mt. Silver Red fight was not identified, U), Gold 11, Crystal 9, Green 8, Misty 10, Yellow 2, Eusine 1, Kimono Girls 3, Frontier-style heads 5.
- **32 "wild" fights are stored as trainer records named after the Pokemon** (Ho-Oh, Lugia, Entei x2, Zapdos, Articuno, Mewtwo, Mew, Gyarados, Dragonite,
  Rhydon, Tauros, Kangaskhan, Slugma, Beedrill, Squirtle, Weepinbell, Tangela ...). They are in the 1,023 and need the same treatment as the legend list.
- Gym rules that fit only certain types or stats (guide, V): Falkner Flying only and at most 4 Pokemon, Jasmine three Pokemon with base Defense 130 or more,
  Clair Dragon only, Bugsy "no type advantage", Whitney's Lopunny kid Normal types only, Chuck and Pryce double battles with a rule. Our mons must satisfy these
  on the replaced slots: a type/stat check, not a species one.
- Slot-swap effect (I, from DEX_REPLACEMENT): if every species number used in a team is a slot we fill, the teams change automatically. All 495 species are used,
  so every slot that stays official in a main-story team must be re-pointed by hand. Teams only used after the final Hall of Fame can keep official species.
- Trainer-class battle intros and music (section 11) are by class; Kimono Girls, Red and rival share them. VS portraits (asset 27185) are still not located.

### 12.5 Story text that names a species (V, English banks counted with word-boundary regex; "Gloom" removed because it is also an English word)

Counted on 802 a027 banks; 383 strings have no English yet (counts are a lower bound). 821 banks are classed in `play_order.json`.

| Group (phase / category) | Banks | Strings | With a species name | Mentions | Different species |
|---|---|---|---|---|---|
| Kanto early (Pallet to Cerulean) | 43 | 3,878 | 612 | 791 | 147 |
| Kanto mid (to Victory Road, Sevii excluded) | 115 | 6,441 | 1,162 | 1,451 | 232 |
| Kanto league (Indigo, HQ final chapter) | 29 | 2,826 | 480 | 676 | 88 |
| Johto (to the final Hall of Fame) | 187 | 11,289 | 2,537 | 3,414 | 316 |
| **Main story total** | **374** | **24,434** | **4,791** | **6,332** | **429** |
| Kanto side quests (Sevii, extras) | 19 | 1,997 | 519 | 725 | 107 |
| Pokegear phone calls | 78 | 1,665 | 178 | 239 | 46 |
| Pokegear radio/map, TV news | 15 + 11 | 332 + 358 | 13 + 15 | 23 + 28 | 11 + 10 |
| Trainer battle text, Frontier trainer text | 1 + 2 | 1,717 + 1,866 | 39 + 4 | 45 + 4 | 30 + 3 |
| Side minigames (Alph, Safari etc.) | 73 | 2,679 | 29 | 35 | 13 |
| Walking-Pokemon reactions | 1 | 759 | 7 | 7 | 6 |
| Common script text (starter-choice help, PC) | 12 | 940 | 12 | 12 | 9 |
| Dex flavour (HG) | 1 | 1,441 | 197 | 209 | 172 |
| Item / move / ability descriptions | 3 | 2,022 | 70 | 76 | ~45 |
| Trainer names (the 32 "wild" records), place names (Diglett's Cave, Slowpoke Well, Rotom's Room) | 5 | 1,344 | 34 | 35 | |

Of the 4,791 main-story strings: 1,188 name a legendary or mythical (Johto 804, league 210, Kanto 174), 625 name a starter or Eeveelution, 820 name one of the
other plot Pokemon (Meowth, Slowpoke, Magikarp/Gyarados, Snorlax, Lapras, Unown, Marill, Miltank, Dragonite, Kabuto ...). The rest name ordinary NPC Pokemon.
Most mentioned in the main story: Entei 248, Ho-Oh 217, Suicune 208, Meowth 110, Lugia 102, Mewtwo 101, Celebi 96, Gyarados 92, Raikou 92, Charmander 90, Venusaur 83,
Arceus 83, Pikachu 78, Unown 75, Swablu 75, Slowpoke 74, Magikarp 71, Eevee 67, Mew 65. Only 3 species above 493 appear at all. Heaviest single banks:
Mt. Silver (77 strings), Alto Mare/Route 42 side bank (73), the Indigo/League HQ bank (73), Ruins of Alph research center (70), Viridian Forest (68),
Cherrygrove (67), Ecruteak (65). Map-script banks mix NPC dialogue, signposts and trainer lines; they cannot be split by type from the data (I). Dex flavour text is
not story and can wait: only 197 of its 1,441 strings name a species.

### 12.6 Systems and code tied to species

| System | What ties it to species | Count / place | Replace? |
|---|---|---|---|
| **Wild tables** (V) | `a/0/3/7`, one table per map | 136 tables (Kanto 51, Mt. Silver and Cerulean Cave 14, Johto 65, Sevii/Safari/Alto 6), 4,087 rows, 523 species (343 of Gen 1-4); Unown tables 3, Slowpoke tables 9, Snorlax 1; legends are never wild | yes, all of it appears in the main story except Sinjoh, Sky Pillar and similar post-game maps |
| **Bug-Catching Contest** (V) | 4 sets of 10 species with score tables (Caterpie/Weedle lines, Scyther, Pinsir, Wurmple, Kricketot ...) | 21 species in contest and headbutt tables | yes (data) |
| **Safari Zone** (V + I) | area customiser; the "owner" tests need a Geodude then a Sandshrew (`ScrCmd_CheckSafariZoneChallengeCompleted` hard-codes both); vanilla default slots are Rattata/Magikarp lv 5 (`unk_02097268.c`) | 1 table + 48 gate battles | change the two test species if their slots become ours |
| **Pokeathlon** (I) | per-species stat ratings `a/1/6/9` (554 x 20 bytes) | stats only up to species 553; no per-species art found | stats table entry per slot |
| **Pokewalker** (U) | 27 courses (`pokewalker_courses.h`); per-species pictures up to 540 | species lists per course not found | leave |
| **Radio** (I) | Pokemon Talk/Music/Poke Flute/Unown/Rocket/Mahogany signal; Unown station tied to Unown; Poke Flute wakes Snorlax; 13 radio and map strings name species (Slowpoke 5, Giratina 4, Gyarados 3, Unown 2 ...) | 12 stations | small text edit |
| **Phone calls** (V) | 77 contact banks, 178 strings name a species (Clefairy 26, Farfetch'd 15, Unown 14, Pikachu 13, Magikarp 10 ...); `phone_scripts_generic.c` falls back to Rattata | | text edit |
| **Day Care / eggs** (V code) | baby species come from the evolution table; `get_egg.c` special-cases Nidoran, Illumise/Volbeat, Manaphy, Ditto; 4 egg gifts (Treecko Cinnabar, Violet Mareep/Slugma/Wooper), Manaphy egg, Togepi egg in vanilla (`SetEggStats SPECIES_TOGEPI`) | | data |
| **Move tutors** (V) | 89 tutor rows; 79 list species (5,209 entries), 6 check one species (Headbutt, Charge, Surf, Blast Burn, Frenzy Plant, Hydro Cannon), 2 event moves | | script lists by number; balance only |
| **Ruins of Alph / Unown** (V) | 4 sliding puzzles (Kabuto, Omanyte, Aerodactyl, Ho-Oh panels), 28 Unown forms, `encounter_check.c` allows Unown by encounter generation, Unown tables | 28 form sprites | art, section 9 |
| **Fossils** (V code) | `scrcmd_fossils.c`: Kabuto, Omanyte, Aerodactyl, Lileep, Anorith, Cranidos, Shieldon; Origin's Pewter errands name Anorith, Bastiodon, Relicanth | 7 | data |
| **Trainer House** (V code, I in Origin) | `overlay_25.c` fixed party: Meganium, Typhlosion, Feraligatr (+ Sitrus Berry) | 3 | data |
| **Catching tutorial / mail** (V code) | `battle_setup.c`: Marill lv 5 vs Rattata lv 2 with 20 Poke Balls; `overlay_36.c` Marill in the first PC mail | 2 | slot swap covers it; check Origin uses it (U) |
| **Roamers** (V code) | `field_roamer.c`: Raikou/Entei (by starter) and Latias/Latios | 4 | Origin makes the beasts static (V, 12.2), so probably unused (I) |
| **Magikarp record** (V) | Lake of Rage script `T29` uses `BufferRecordSize Magikarp` | 1 | slot swap |
| **Species special cases in code** (V decomp) | Burmy, Shellos, Gastrodon, Wormadam, Pichu, Deoxys, Rotom, Giratina, Shaymin, Arceus, Unown (forms, dex, icons, mail); Chatot (recorded cry); Krabby/Kingler (Hall of Fame offset); Shedinja; Spinda; Hidden Power "no type" list (Magikarp, Ditto, Wobbuffet, Beldum, Caterpie ...); Light Ball / Thick Club / Stick / Soul Dew / Deep Sea items (battle code `overlay_12`: Pikachu, Cubone/Marowak, Farfetch'd, Latias/Latios, Clamperl, Ditto); Sinnoh rival starters (`sys_vars.c`: Turtwig/Chimchar/Piplup) | about 40 files | only matters if a story-relevant mon takes one of those slots; see section 8 |

**Code tables keyed by species number:**

1. **Legendary battle-intro table, Origin arm9 offset 0xF91CC (V, decoded here):** 11 entries of `species | (effect << 10)`: Raikou 243 (effect 22), Entei 244 (23),
   Suicune 245 (24), Lugia 249 (26), Ho-Oh 250 (25), Groudon 383 / Kyogre 382 / Rayquaza 384 (27), Mewtwo 150 / Latios 381 / Latias 380 (28). Identical to
   pret's `_020FC3B4`. The 22 bytes are followed at 0xF91E2 by the trainer-class intro table (32 entries `class | (id << 10)`: all 16 gym leaders, the Elite Four,
   Champion, rival, Rocket executives and boss) and a second 32-entry table at 0xF9222 (V, read; meaning of the second one: I, music/effect pairs).
2. **Title screen cry and model:** `TITLE_SCREEN_SPECIES` (Ho-Oh) in the `intro_title` overlay; the model members are in `a/0/4/6` (section 9). Candidate
   instruction sites in Origin by immediate scan (I): overlay 41 offsets 0x536C/0x5370 (249 and 250 close together). Not confirmed.
3. **Ho-Oh/Lugia final approach:** `legend_cutscene_camera.c` in overlay 2; Origin overlay 2 offsets 0xD992 and 0xD9A0 hold the 249 and 250 immediates close together (I).
4. **Starters:** `choose_starter.c`/`choose_starter_app.c` (overlay 61) hold Chikorita, Cyndaquil, Totodile, but Origin's Oak script uses `SetVar` species numbers
   in `a/0/1/2` (section 5 and STORY_ROLES). `GiveMon VAR_SPECIAL_x8004` in `T01R0301` takes the choice from the same variable.
5. **Oak's Marill:** `oaks_speech.c` (overlay 53) `PlayCry(SPECIES_MARILL)`; an immediate scan of Origin's overlay 53 found no 183, so Origin may load it
   from a table or a rebuilt intro (U). The 2D sprite (members 59-66 of `a/1/2/0`) is untouched.
6. **Overlay 14 (battle) immediates:** species compares for 249/250 at 0x354C6/0x354CA (I: probably Lugia/Ho-Oh battle messages or abilities; not read).
7. **Event scripts** (`a/0/1/2` in Origin, `scr_seq_*` in pret): `SetVar`, `Compare`, `WildBattle`, `GiveMon`, `PlayCry`, `LoadNPCTrade`; replaced by the slot swap.
8. **NARC tables with one record per species:** `a/0/0/2` base stats, `a/0/3/3` learnsets, `a/0/3/4` evolutions, `a/0/7/4` dex data, `a/1/6/9` Pokeathlon stats,
   `a/2/4/7-9` Pokewalker, follower table, footprints; covered by sections 5 and 8.
9. **Trainer-class tables (not species):** battle intro/music by class, trainer pictures (section 7); needed for new boss characters only.

### 12.7 What we must do, by group (counts)

1. **Legend roles (about 34 species with events, 21 of them essential, 11 with battle intros):** one of our mons per role, plus the intro table patch (11 entries), cutscene sprite
   (Ho-Oh, Lugia), title model, 13 follower sprites for the beasts/legends in about 25 map files. Post-game ones may keep official species.
2. **Plot Pokemon (about 35 essential outside the legends, see 12.9 and 12.11):** Meowth/Persian, Gloom, Slugma, Salamence, Sudowoodo, Miltank, Gyarados/Magikarp, Chatot, Teddiursa, Swinub, Slowpoke, Dragonite/Dragonair, the rivals' starter lines, Alph fossils, Bugsy's four bugs, Marill, Pikachu. Snorlax, Lapras and the Eevee gift are side quests (optional).
3. **Trainer teams:** all 1,023 team records, 3,891 slots, 495 species; plus the 32 pseudo-trainers.
4. **Text:** 4,791 strings in 374 banks (main story), plus about 250 in phone/radio/TV/minigame banks; do it per species name with a script and a hand
   check of the 1,188 legend strings and the 820 plot strings.
5. **Wild tables:** 136 tables; decide first which official species stay as "guests" in the main story (none, by section 11).
6. **Map objects:** 1,619 Pokemon objects; the 1,537 follower ones follow the sprite id, so they need no art beyond the follower pipeline; the 34 special objects need pictures.
7. **Gifts, trades, tutors:** 159 + 13 + 89 rows; the tutor lists can stay by number.

**Still unknown (U):** which of the 1,537 follower objects are only reachable after the final Hall of Fame (map names are inferred); whether the Trainer House and the
Marill/Rattata catching tutorial are reachable in Origin; the Pokewalker course lists; the Pokeathlon art; sprite id 1565 in Cerulean City; where the VS portraits
are stored; exact overlay sites of the title cry and the Marill cry; what the other 31 `FOLLOWER_MON_STATIC` kinds (vanilla only) were replaced by.

### 12.8 When is each legendary available in Origin's story? (corrected 2026-11-11; V from the quest guide, `msg/071` hint menu and `trades_tutors.md`)

I had this partly backwards in 12.2 and in my first report: I treated "story role" as "obtainable". In Origin almost every box legend is **taken by Team Rocket in the story** and only becomes catchable after the **final** Hall of Fame (the one after Giovanni at League HQ; the first HoF, after Blue, is Kanto only). The guide's phrase "post-game" means after the final entry. Prof. Hale's hint menu (`msg/071`, 12 legend topics) is consistent: it only points to the places (Rock Tunnel God Pillars, Mt. Moon with the Red Orb, Seafoam with the Blue Orb, Sky Pillar with the Jade Orb, Ice Path for Dialga, Mt. Mortar for Palkia, Dark Cave world for Giratina, Burned Tower for the beasts, Whirl Islands and Bell Tower with a token and a dance, Lake of Rage on Wednesdays, "wait for Mewtwo", Five Island for Mew).

| Legend | Story use before the final HoF (chapter) | You can keep it |
|---|---|---|
| Regirock, Regice, Registeel | Rock Tunnel quiz, Goh and Rocket Joy (League HQ round 1, ch. 3) | **before**, lv 90 gift (needs Wailord first slot, Relicanth sixth) |
| Zapdos | Power Plant: lv 90 trainer-style fight, no catch (TM25 reward); Lawrence catches it (round 1) | **after final HoF** (wild lv 90) |
| Moltres | Lawrence lures it at Cinnabar, Rocket catches it (round 1) | **after final HoF** (lava edge, wild lv 90) |
| Articuno | Seafoam: lv 90 fight, no Balls; Rocket takes it in round 2 | **after final HoF** (wild lv 90) |
| Kyogre | Archie summons it with Misty's Blue Orb and escapes (round 2, after the Silver Conference) | **after final HoF** (Blue Orb from Lance, wild lv 95) |
| Groudon | Team Rocket Groudon story (Red Orb) | **after final HoF** (Mt. Moon altar, lv 95) |
| Rayquaza | Four Island trial: Proton and Ariana catch it with the Jade Orb (pilgrimage) | **after final HoF** (Sky Pillar, lv 95) |
| Latios, Latias | Secret Forest (round 4) | **before**, lv 80 gift |
| Mew | Mt. Moon Rocket chase, Cinnabar lab logs | **before**, lv 90 (Five Island finale, pilgrimage) |
| Mewtwo | Cinnabar lab scripted event (ch. 5); Indigo Plateau final chapter | **before**, lv 95 gift after Mewtwo breaks Palkia's barrier; missable, removed by the final HoF |
| Celebi, Shaymin | Ilex Forest, Sammy, injured Celebi (round 3) | **before**, Forest of Time shrine, one each |
| Uxie, Mesprit, Azelf | Lake of Rage trials (after Petrel scene) | **before**, lv 90 each |
| Heatran, Manaphy (egg) | side quests (Tuesday lava pool; Alto Mare) | before |
| Arceus | Giovanni catches it at Alph/Sinjoh (ch. 8) | **after final HoF** (Sinjoh Ruins, lv 95) |
| Dialga, Palkia | Rocket catches both in the Distortion World (final chapter); Ice Path/Mt. Mortar spaces | **after Lance's visit** |
| Giratina | Reversal Cave chase | **after Lance's visit** |
| Entei, Suicune, Raikou | Alph with Molly (Entei), Cianwood with Eusine and Ice Path trap (Suicune), Route 47 device (Raikou) | **after final HoF** (Burned Tower scene first) |
| Ho-Oh | Rainbow Wing, Morty and the Bell Tower: stolen by Rocket (round 4); lv 95 trainer-style fight comes with the post-game catch | **after final HoF** (Clear Bell from Morty, Satsuki) |
| Lugia | Lawrence wakes it with the birds, you fight Rocket, Lawrence catches it (round 4) | **after final HoF** (Whirl Islands B3F lv 95, Silver Wing) |
| Deoxys, Jirachi, Cresselia, Darkrai, Regigigas | Deoxys in the Six Island trial story; others not in the story | **after final HoF** |

Consequence for Arvind's rule: our legends are needed **in the story before the final HoF** (cutscene sprites, battles, text, captured-by-Rocket scenes) for Zapdos, Moltres, Articuno, Kyogre, Groudon, Rayquaza, Arceus, Dialga, Palkia, Giratina, Entei, Raikou, Suicune, Ho-Oh and Lugia, and as **gifts you keep** for Regis, Latios/Latias, Mew, Mewtwo, Celebi, Shaymin, Uxie/Mesprit/Azelf. Origin's HeartGold-style "box legend caught before the League" does not exist; Ho-Oh and Lugia are the least obtainable of all (one battle each, post-game).

### 12.9 The "plot" Pokemon checked one by one (V: guide text, EN banks and parsed objects)

| Species | Real story role | Main or side | Sprites it needs |
|---|---|---|---|
| Meowth, Persian | Jessie and James's talking Meowth (Rocket trio, 110 text mentions); Persian statue password puzzle in the Celadon warehouse; Viridian Meowth thief (Charmander starters), Route 8 Persian quarrel | main + side | follower (Meowth 7, Persian 5 objects), 1 vanilla static Meowth; the statue is probably a map prop, not an object (I) |
| Gloom | Celadon "stolen Gloom" chain (main, easy to get stuck) | main | follower (5); the 80 "Gloom" hits in text are partly the English word |
| Slugma | Cherrygrove: Rhett's Slugma, a fight with three Slugma (pseudo-trainer record #745), Slugma egg gift | main | follower (4) |
| Salamence | Route 34: Ruby and Sapphire's angry Salamence, lv 60 wild, catchable once | main | follower (2), battle sprite |
| Sudowoodo | Route 36 "odd tree" blocks the road; Crystal waters it and it runs off, no fight (guide); an unmasked Sudowoodo already stands further west | main | **special**: tree object `USOKKY` (1) + `TREE` + Sudowoodo follower (4) |
| Miltank | MooMoo Farm sick Miltank chain, leads to the Dream World (round 3); Whitney's ace | main | follower 16 + 5 static |
| Chatot | Rocket HQ (radio-wave investigation, 8 text mentions, lv 10 static battle); also a recorded-voice cry code (`sound_chatot.c`) | main | follower (6); cry is special code |
| Teddiursa | S.S. Anne party: the girl's Teddiursa needs Honey and salt, then goes missing | main | follower (6) |
| Swinub | Ice Path cursed tunnel: the Swinub trainer, Durin Berries, Sacred Ash, Anti-Age Spray (needed in the final chapter) | main | follower (1) |
| Gyarados, Magikarp | Misty's runaway Gyarados (Route 3, lv 65), red Gyarados at the Lake of Rage (lv 30, Lance catches one, Gold another), Magikarp evolves in the scene, Magikarp record script | main | **special**: `RGYARADOSU` (3) + follower (7) |
| Pikachu | one of the three starters; Pikachu thief events; Viridian | main | **special**: `PIKACHU` object (2) + followers (17) + 2 vanilla static |
| Marill | Oak's intro Pokemon, catching tutorial code, first PC mail icon; Violet runaway Marill (side) | main (code), side | 2D intro sprite (section 9) + followers (7) |
| Dragonair, Dragonite | Secret Potion for the Warden's Dragonair (main); Lance's Dragonite at the Lake of Rage; Dratini gift (side) | main | follower (Dragonite 17, Dragonair 3) |
| Snorlax | Route 12 roadblock, wake with Poke Flute, lv 35, catchable (and Five Island monk); not needed to progress | **side** | **special**: `KABIGON` sleeping (2) + 1 follower |
| Lapras | Silph hostage Lapras (side), ferry/ride quests on the Sevii islands | **side** | **special**: `RAPURASU` (11) + 2 followers |
| Eevee | Viridian Forest rescued Eevee (side); Blue's Umbreon, Kimono Girls' teams | side + teams | followers (Eevee 3, evolutions 21) |
| Slowpoke | Slowpoke Well (chapter 19) and Azalea | main | follower 21 + **special** tailless `YADON` (7) + 1 static |

So two of my first list were wrong in kind: Snorlax and Lapras are optional side quests, and the Eevee gift is optional. Only Sudowoodo, red Gyarados, Pikachu and Slowpoke (tailless) need a special object graphic; every other "plot" Pokemon is the normal follower sprite plus the battle sprite.

### 12.10 The 34 special map objects, by name and graphic (V: `a/0/3/2` parsed; sprite ids from pret `sprites.h`; mmodel members from section 9)

All are files in `a/0/8/1` (map-object models/sprites, BTX0 32x32 or 64x64 frames); they use fewer frames than a follower.

| Name (sprite id) | Count | Where (map names approximate, I) | Graphic |
|---|---|---|---|
| `PIKACHU` (71) | 2 | Rock Tunnel, Route 44 | static Pikachu sprite, mmodel 68 |
| `RGYARADOSU` (237) | 3 | Lake of Rage | red Gyarados, mmodel 183 |
| `USOKKY` (381) | 1 | Route 36 | Sudowoodo disguised as a tree, mmodel 186 |
| `RAPURASU` (390) | 11 | Alto Mare Waters, One to Four Island, Route 40, Route 47 | Lapras you can ride/see in water, mmodel 228 |
| `KABIGON` (395) | 2 | Route 12, Five Island | sleeping Snorlax, mmodel 194 |
| `ROTOMF`, `ROTOMS`, `ROTOMI`, `ROTOMW`, `ROTOMG` (409-413) | 5 (1 each) | Silph Co. Rotom's Room | the five appliance forms, mmodel 196-200 |
| `YADON` (414) | 7 | Burned Tower, Frontier Access, Ice Path, Route 42, Route 47, Six Island | tailless Slowpoke; the only Pokemon sprite Origin redrew, mmodel 209 |
| `HOU_OBJ01` (425) | 1 | Bell Tower | Ho-Oh cutscene plane, mmodel 210, 7 frames 64x64 |
| `LUG_OBJ01` (426) | 2 | Whirl Islands | Lugia cutscene plane, mmodel 211, 7 frames 64x64 |

Total 34. Plus sprite id 1565 (1 object, Cerulean City) that is outside vanilla's table (U), and generic `TREE` (2) and `ROCK` (25) props that look like Pokemon only in the Sudowoodo and Rock Smash events.

### 12.11 Essential versus incidental species (Arvind: "historien inkluderer 500 arter men alle er ikke essensielle")

Definitions (I; the line is mine, based on the data below): **Essential** = named in the main plot, given as a plot reward, scripted or in a cutscene, required to progress, in the code tables, or the rivals' signature lines. **Optional scripted** = a gift, trade or static battle or side quest title, but not needed. **Incidental** = only in random trainer teams or wild tables (or in one line of NPC text).

Counts (V for the sets, I for the line between them): of 1,025 official species, **336 never appear anywhere** in Origin (no wild table, trainer team, gift or trade). **60 are essential**, **127 are optional scripted** (gift/trade/static battle rows or side-quest titles), and **502 are incidental** (only in trainer teams or wild tables). 494 species are in trainer teams and 523 in wild tables, but only 52 of the 60 essentials are in a trainer team and 26 in a wild table: 21 legends and 6 gift-only species never appear in either.

**The 60 essential species:**
- Player and Oak (4): Bulbasaur, Charmander, Pikachu, Marill.
- Kanto plot (17): Meowth, Persian, Gloom, Gyarados, Magikarp, Teddiursa, Mew, Mewtwo, Kabuto, Slowpoke, Sudowoodo, Dragonite, Dragonair, Squirtle, Venusaur, Blastoise (rival Blue and Green), Hypno (Three Island pilgrimage).
- Johto plot (18): Slugma, Salamence, Miltank, Chatot, Swinub, Unown, Celebi, Totodile, Cyndaquil, Chikorita (Silver, Gold, Crystal's lines), Ariados, Kricketune, Burmy, Skorupi (Bugsy's honey hunt), Aerodactyl, Omanyte (Alph panels with Kabuto and Ho-Oh), Tyranitar, Larvitar (Ariana's ace).
- Legendary roles (21): Zapdos, Moltres, Articuno, Regirock, Regice, Registeel, Kyogre, Groudon, Rayquaza, Latios, Latias, Arceus, Dialga, Palkia, Giratina, Entei, Raikou, Suicune, Ho-Oh, Lugia, Deoxys.

Borderline (I): Hypno, Burmy, Skorupi, Larvitar, Venusaur, Blastoise could be argued incidental; Snorlax, Lapras, Eevee, Shaymin, Uxie/Mesprit/Azelf, Heatran, Jirachi, Manaphy are optional (side quests) even though they have special objects or code.

**Optional scripted (127)** includes every gift and trade species, the Sevii and Dream World legends, and the species named only in side-quest titles (Snorlax, Lapras, Eevee, Clefairy, Hitmonlee/chan, Pidgeot, Pidgey, Zubat, Rotom ...). They can follow the essential ones in order of effort.

**Incidental (502)**: e.g. Remoraid. What Remoraid does: it is one injured patient in the Route 32 Pokemon Center storm scene (9 text lines, a side quest "storm patients", before Route 33), a boy's fear of the sea in Olivine (side), a Water Spout tutor entry, 3 trainer teams, 4 wild tables and 1 follower object. No gift, no cutscene, no battle, no code. Remoraid is typical: **about half of the 1,025 species (502 + the 336 unused) are not part of the story at all**; they only fill wild tables and trainer teams, and any of our mons (or none) can sit there.

What this means for the work: the 60 essentials plus about 25 of the optional ones (Snorlax, Lapras, Eevee line, Pichu/Cleffa/Igglybuff, Heatran ...) must be designed or chosen deliberately; the other ~500 slots can be filled by whichever of our mons suit the route's type and level, and the roughly 340 unused species can be left alone or reused as free slots (check section 8 for which are clean).

### 12.12 The special map pictures, looked at (2026-11-11, rendered locally from Origin's `a/0/8/1`)

- **Correction:** member 209 (`YADON`, "tailless Slowpoke") is **not a Slowpoke in Origin**: Origin redrew it as event props (a red pyramid, a crystal in a frame, a glass orb on a stand, purple crystals; 12 frames). So Slowpoke needs no special picture; the Slowpoke Well uses the normal follower.
- Static Pikachu (68): 12 frames of 32x32 in follower style: the 8 walking frames plus extra poses for events.
- Red Gyarados (183): 8 frames of 32x32, not a walking follower but Gyarados thrashing in the water (splash poses), shiny-red.
- Sudowoodo tree (186): 6 frames of 32x32, the tree disguise shaking.
- Lapras (228): 8 frames of 32x32, Lapras in the water facing each way (ferry).
- Sleeping Snorlax (194): one big 64x64 picture.
- Ho-Oh (210) and Lugia (211) cutscenes: 7 frames of 64x64 each, seen from the front, a wing-beat cycle (wings up, spread, down, folded) for the flying scenes.
- Ruins of Alph panels (`a/1/7/2` members 4-7, identical in Origin and vanilla): four sliding puzzles of 16 pieces, carved stone pictures of Kabuto, Aerodactyl, Omanyte and Ho-Oh in sand colours (one shared palette).
- Microphone: PokeDaisy's DS core answers "nothing there" for the microphone (`app/src/main/cpp/nds/pk_nds_platform.cpp`), so a Chatot-style recorded cry would not work there today.
