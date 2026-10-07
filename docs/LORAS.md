# Our LoRAs (Origin HeartGold / DS sprites)

Edit LoRAs for Qwen-Image 2.1 that turn a finished DS battle sprite (front, 80x80) into the other
pictures a Pokemon needs. They learn the step from pairs of pictures, not from words: a word-based
LoRA (SDXL, tried first) knew the style but redrew Pokemon it knew instead of ours.

| LoRA | In | Out | Used by |
|---|---|---|---|
| `pkmn_icon_edit_v2` | the front | the 32x32 party/PC icon | `ds_pixel.icon_from_front` |
| `pkmn_follower_edit_v1` | the front | the follower sheet: 8 frames (up, down, left, right x 2 steps) | `ds_pixel.follower_from_front` |

`ds_pixel.make` uses them when ComfyUI has them, and falls back to the older drawn icon (and no
follower) when it does not.

## How they were made

- **Data:** about 1400 HeartGold-style Pokemon from hg-engine's graphics (front sprite with its icon
  or its follower sheet), read only on the Legion and never put in this repo. Training on the games'
  sprites to imitate their style was Arvind's decision (2026-10-05); our sprites are always made from
  our own designs.
- **Icons:** the target icons were recoloured to their battle sprite's own colours first (`pairs2`):
  HeartGold's icons use three shared palettes, and v1, trained on them as they are, turned Waffy
  purple.
- **Tool:** ai-toolkit (ostris), arch `qwen_image_2`, LoRA rank 32, 3000 steps, batch 1,
  `low_vram`, on the Legion's RTX 5080 (16 GB; about 11-13 GB used; 3.5 s/step for icons, 5.5 s/step
  for follower sheets). It reads the Qwen files from ComfyUI's models folder (`MODELS_PATH`).
- **Where:** `D:\LocalAI\lora-train\` on the Legion: `ai-toolkit\` (own venv; `torchaudio` is a
  stand-in package, no build exists for torch 2.14), `pairs*\` (data and the yaml config),
  `aitk_train*.ps1` (waits for a running studio job, pauses the sprite worker so the GPU is free,
  trains, starts the worker again), `aitk_out\` (results, copied to `ComfyUI\models\loras\`).

## The family (agreed with Arvind, 2026-10-06)

A whole Pokemon from rough concept art, one approved step at a time. Every step can take 1-3 pictures in
(sketch and drawing together give one result):

1. sketch / drawing -> Ken Sugimori style artwork (today: Qwen prompt `official_front_gen4`; close, but the
   real style has softer, better rendering); the group approves it;
2. artwork -> DS front (`ds_pixel.make`, approved; a near-white guide silhouette, else Qwen keeps the grey
   guide as the creature on single-coloured mons like Sandrema);
3. front -> back (`pkmn_back_edit_v2`: right colours, best at step 1000);
4. front + back -> follower sheet (`pkmn_follower_edit_v2b`) and icon.

Tested and dropped (2026-10-06): the Civitai Sugimori LoRAs for Illustrious (_GAi, Fakemon-Sugimori)
image to image: at denoise 0.6 nothing changes, at 0.85 the style is right but the design is lost.

## Traps found (2026-10-07)

- **hg-engine's `back.png` holds the shiny palette.** Backs must take the front's palette (back v1 and
  follower v2 were trained on shiny backs and dropped).
- **hg-engine species numbers** are the national dex up to 493, then +50 (Victini is 544).
- **Near-duplicates:** 777 of 1838 same-species pairs are almost identical (DP, Pt and HGSS often share a
  sprite), so Gen 1-4 species are seen 3-4 times and newer ones once: memorising instead of learning.
- **Too many steps:** back v2 was best at step 1000; at 1500-2000 the backs broke up, at 3000 it copied
  the front (a known edit-LoRA failure: copying the input is the easy way to lower the loss). Constant
  lr 1e-4 with no decay keeps the weights jumping.
- **One seed per checkpoint** is not enough to choose; use 4-8.
- **Pixel grid:** 640 px for an 80 px sprite is exactly one VAE latent cell per pixel. The follower
  sheets (1024x512) were trained at resolution 640, so they were shrunk to 896x448 (7 px per pixel, off
  the latent grid); train them at 1024.
- **16 GB:** training against a quantised base with offloading is noisier than bf16 on a 48 GB card.

## What the tests showed (2026-10-07)

- **Back v3** (front + official artwork in, species balanced to 3 entries with paired hue shifts, 20% without
  artwork, lr 5e-5 cosine, EMA 0.99, 1500 steps) is clearly better than v2 on our own mons (Autuman, Bugmight,
  Chillalit, Leafing, Nukfae, Waffy get real backs with their details) and no longer copies the front late in
  training: the lower rate, decay and EMA fixed that. Without the artwork it is worse. Best at step 1000.
- Not good enough yet (Arvind: "a couple I would use"): the framing depends on the seed (seed 2 is best for
  almost all), the dark outline is often missing, shading is softer than the games', single-coloured designs
  (Erobi, Sandrema) stay vague.
- Real HGSS backs (300 measured): about 10 colours, 79% of the edge is a dark outline (ours 58%), about 36% of
  the frame filled, and they end in a flat cut around row 71, not on the bottom row.
- References at 640 px (as trained) or 1024 px: no clear difference; use 640.

## Plan for the RunPod session (agreed 2026-10-07)

**Every LoRA takes "everything in":** any subset of the other pictures of a Pokemon as references (front sprite,
official artwork, back, follower sheet, menu icon), named in the instruction ("image 1 is the front sprite,
image 2 the artwork, ..."). In training each example picks the target and a random subset of the rest as
inputs (sometimes only the front), so it learns to use whatever is there and to manage with little. Artwork
and front are kept in most examples, the others in about half. One LoRA per output (not one for everything:
80 px backs and 32 px icons in one LoRA tend to blur the tasks); merging them is a later step.

One RunPod round only, to finish the sprites (fronts are solved without a LoRA, icons work with icon v2):

| LoRA | Out | In (any subset) |
|---|---|---|
| back v4 (A/B: which references / lr) | back sprite | front, artwork, follower sheet, icon (less often) |
| follower v3 | follower sheet (trained at 1024, on the latent grid) | front, artwork, icon (less often) |
| icon v3 | menu icon | front, artwork, follower sheet (its "down" frames look like an icon) |
| sprite -> artwork | Sugimori artwork | only if money is left, else later |

Front + artwork are in almost every example; the other references are extra help, often degraded (scaled
down and up, colour jitter) or real LoRA outputs, because for our mons they are made by LoRAs, not real
(otherwise it learns to copy their mistakes; independent review, 2026-10-07). ai-toolkit skips a missing
control file per example, so the number of references can vary; the instruction names the images per example.
Tests weight our own mons and the Smogon CAP fakemon (new designs with real sprites) over the held-out real
species, which the base model already knows; single-seed results shown next to best-of-3.

Order for our mons: front + artwork (as today) -> follower -> icon -> back from everything.

Recipe for all: data v3 (catalogue of 2344 unique fronts for 1025 species from DP/Pt/HGSS, BW fronts that fit
80x80 unscaled, Smogon and hg-engine variants; near-duplicates dropped; every species weighted the same;
paired hue shifts; 40 held-out species), lr 5e-5 cosine, EMA, about 1500 steps, saved every 250, bf16 without
quantising on an RTX Pro 6000 96 GB (about $2/h). About 5-6 hours, about 12-16 dollars, schedule set from the smoke test with a 5-dollar reserve.

Before the session (Legion, free): the data v3 builds for all four; tags (closed word list: body plan,
material, features, pose; colours from pixels; PokeAPI shape/colour/Pokedex text as ground truth; tagged once
per species from the artwork and copied to its sprites; never a Pokemon name); the test sheet script (held-out
species + our mons, 3 seeds, best-of-3); one queue only.

In the session: a 50-step smoke test (s/step, non-zero weights, exact price) before the rest; then the four
LoRAs with A/B; test sheets; download; the pod stops itself. Spend limit $25. Arvind judges the sheets; the
numbers only throw out broken results.

In the pipeline afterwards: best of 3 in every step, chosen by framing (fill, flat cut, outline), the front's
palette, stray pixels removed, a dark outline added where missing.

Waits: the sketch -> Sugimori artwork LoRA (we have Qwen's artwork for now); first a test of Qwen with real
Sugimori artworks as style references (running).

## Next ones (later)

- one LoRA for all directions (after the family works);
- trainers (about 160 examples in hg-engine);
- image to 3D (Hunyuan3D 2.1 shape-only / mini and Pixal3D fit 16 GB).
