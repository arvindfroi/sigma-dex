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
| Dex height and weight | a table somewhere | species files: `height_m` 52, `weight_kg` 26 of 150 | partly | **Unknown** where Origin stores them: `a/2/1/4` and `a/0/7/4` were patched with no visible change (memory sigma-origin-hg, 2026-10-17) |
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
| Trainer class data | class names (text banks), gender, prize money, music | none | whole table; Origin's layout **unknown** (hg-engine source: `trainerclass.h`, `trainermoney.c`, banks 730 and 731) |
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
- **Origin (V).** The zukan_data layout is Origin's `a/2/1/4` (102 members: members 0, 1, 2 are height, weight, body style, 3-10 scales and offsets, 11+ the dex sort lists). Compared with the decomp: 492 of 493 height values and 492 of 493 body styles match. **It has 494 entries only (species 0-493)**, not 1441. Displayed strings are in **bank 801 (height, "０．７ｍ") and 799 (weight, "６．９ｋｇ")**, 1441 lines each. For slots above 493 the numeric table is out of range: sorting/size-comparison screen and weight-based moves for those slots are **unknown** (test needed; hg-engine extended the tables, Origin apparently did not). Earlier patches to `a/2/1/4` showed "no change" probably because the visible text comes from banks 799/801.
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
- Whether Origin's dex screens and Low Kick use `a/2/1/4` for species above 493 (table is too short).
- Where Origin keeps trainer class gender, music and prize money (decomp tables are in arm9 code at other addresses; not located in Origin).
