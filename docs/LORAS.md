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

## Plan for the RunPod session

Before it (on the Legion, free):

1. One test script for every LoRA: the 40 held-out species (with the real answer) and our mons with
   concept art, 4 seeds, LoRA strength 0.7 / 0.85 / 1.0; agreed "good enough" per step.
2. Data v3: near-duplicates dropped (one Gen 4 version per species unless they differ), the same hue
   shift applied to both pictures of a pair as extra pairs (never flipped: fronts face left).
3. Pilot for the artwork LoRA: Qwen redraws ~200 Pokemon as real-looking drawings (pencil, crayon, ink,
   child's drawing), checked by hand before the full set is made.
4. Captions: the fixed instruction plus structured tags (view, format, body shape, colours; never real
   Pokemon names).

The session (RTX 6000 Ada 48 GB, bf16 without quantising, one script, no one watching; about 10 hours,
about 8-12 dollars): the drawing variants, then one LoRA per step (a family, not one big LoRA):
artwork, sprite -> artwork, artwork -> front, back v3, follower v3 (at 1024), icon v3. Each: lr 5e-5 with
cosine decay, EMA, 2000 steps, saved every 250, then the test sheet.

## Next ones (later)

- one LoRA for all directions (after the family works);
- trainers (about 160 examples in hg-engine);
- image to 3D (Hunyuan3D 2.1 shape-only / mini and Pixal3D fit 16 GB).
