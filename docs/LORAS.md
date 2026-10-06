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

A whole Pokemon from rough concept art, one approved step at a time:

1. sketch -> Ken Sugimori style artwork (Qwen prompt today, `official_front_gen4`); the group approves it;
2. artwork -> DS front (`ds_pixel.make`, approved);
3. front -> back (`pkmn_back_edit_v1`, training);
4. front + back -> follower sheet (`pkmn_follower_edit_v2`, queued: v1 saw only the front and had to
   guess the back and sides) and icon.

## What to try next (research, 2026-10-06)

1. A held-out test set of our own mons (never trained on), checkpoints every 250 steps, pick by the
   test set, not the loss. A comparable public Qwen-Image 2.1 edit LoRA (same tool, rank 32, 3000
   steps) was best at step 1500.
2. Structured tags next to the fixed instruction (view, generation, format, body shape, colours;
   never real Pokemon names), made by Qwen3-VL with a fixed word list and spot-checked.
3. One LoRA for 1-3 optional inputs: train some pairs with an input left out (untested idea).
4. Short A/B runs: LoKr vs LoRA, rank 16 vs 32, latents cached to disk.
5. Other trainers (DiffSynth-Studio supports 2.1 edit training; musubi-tuner not confirmed for 2.1)
   only if speed becomes the problem. Not now: NVFP4 training, another base model, image-to-3D
   (Hunyuan3D 2.1 shape-only / mini and Pixal3D fit 16 GB, for later).

## Next ones (planned, same recipe)

- back: front -> back (training, `pairs4`);
- front from a drawing: needs pairs of drawings and sprites first (Qwen drawing a Sugimori-style
  picture of each battle sprite, about a day of GPU time);
- trainers (about 160 examples).
