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

## Transparency: data v5 (2026-10-08)

A big mistake, fixed before the RunPod round: data v4 and the DS pipeline put every picture on white and guessed the
background back as "near white". 1542 of the 2172 real Gen 4 fronts have white pixels inside the creature (eye glints,
white patches), so that guess eats light parts (it is also why Sandrema, a beige mon, failed). Qwen-Image 2.1's VAE is
RGBA: an x8 sprite goes through it with not one alpha pixel wrong, and ai-toolkit trains it with
`model_kwargs: {rgba: true}`. Data v5 keeps every picture's own transparency; the loss masks are the alpha, widened a
little (the background keeps 0.3 of the weight, its clear alpha has to be learned too). A 200-step icon test on the
Legion kept clean transparency and the white parts (Poliwag's tail, Poliwrath's gloves).

Also in v5:
- the main references (front sprite, artwork) are "dirty" in 30% of the examples, like the extra ones: for our mons
  they are made by LoRAs, so the LoRAs must cope with slightly soft, slightly off pictures;
- a style LoRA `art_style_v1`: the 968 official artworks alone, no reference picture, at 1024. It learns only what the
  artwork style looks like; used on top of an edit with a concept drawing as reference, Qwen keeps the design and the
  LoRA gives the rendering (the idea of OmniConsistency, NeurIPS 2025: learn the style apart from keeping the content).
  Tested together with `art_v1` (sprites and HOME renders -> artwork) on the concept art of our 10 test mons.

Using them: ComfyUI's LoadImage drops the alpha, so a reference goes through JoinImageWithAlpha; `ds_pixel` must be
switched to transparent references and to reading the alpha (instead of "near white") before the new LoRAs are used.

## Running a RunPod round (as done on 2026-10-08)

Everything is on the Legion in `D:\LocalAI\lora-train`: `v5.tar` (data v5, 3.3 GB, RGBA with loss masks),
`v5cfg\*.yaml` (pod configs; `*_smoke.yaml` are the Legion test versions), `v5cfg_s\*.yaml` (the same with progress
pictures), `v5cfg\pod_setup.sh`, `v5cfg\pod_train.sh`, `v5cfg\dash.py` + `dash.html` (live page), `v5cfg\fetch_loras.ps1`
(download + stop), `v2cfg\make_samples.py` (progress-picture inputs and configs).

1. **Pod.** RTX PRO 6000 (96 GB), Secure Cloud, image `runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404`, 60 GB container
   disk, 150 GB volume on `/workspace`, ports `22/tcp` and `8888/http`, `startSsh`. Costs 2.09-2.19 dollars an hour.
   The Mac and Legion SSH keys are registered on the RunPod account: the `ssh.runpod.io` proxy only accepts account
   keys. Use the direct SSH address from the pod (`ssh -p <port> root@<ip>`), which also allows `scp`.
   If the pod has no `runtime` and no logs after about 5 minutes, delete it and try another data center (two pods in
   EU-RO-1 never started; US-NE-1 was up in 30 seconds).
2. **Files.** `scp` from the Legion straight to the pod (`v5.tar` took about 4 minutes), configs to `/workspace/cfg/`
   (strip the Windows line endings with `sed -i 's/\r$//'`).
3. **Setup.** The image's Python refuses `pip install` unless `PIP_BREAK_SYSTEM_PACKAGES=1`. Install
   `torch==2.14.1 torchvision==0.29.1` from the cu130 index (the Legion's versions), then ai-toolkit's requirements.
   No torchaudio exists for torch 2.14: put a stand-in `torchaudio/__init__.py` (one comment line) in site-packages,
   as on the Legion. Models with `hf download` (`huggingface-cli` no longer works), about 30 GB in 5 minutes.
4. **Smoke test** (`pod_setup.sh`): 30 steps with s/step, a check that the LoRA weights are not zero, and **the
   progress pictures switched on**. In this round the smoke test ran without them, and two LoRAs then crashed on
   their first pictures.
5. **Train** (`pod_train.sh <names>`), with the live page (`python dash.py <random token>`, then
   `https://<pod>-8888.proxy.runpod.net/<token>/`: step, loss curve, time and money left, checkpoint pictures) and
   `fetch_loras.ps1` on the Legion. It downloads each LoRA as it ends and stops the pod (the pod-scoped key is in
   `/proc/1/environ`; `runpodctl stop pod`) once all are in.
6. **Test** on the Legion (ComfyUI) and decide what goes into the next round.

### What we learned (round 1, 2026-10-08)

- **The LoRAs barely saw their data** (Arvind: "den lærer ikke så mye", with such a big dataset). 1500 steps at batch 1
  was carried over from the small Legion datasets (back v2 had a few hundred examples and over-fitted from 1250
  steps), but v5 is 5-10x bigger: art style saw each of its 968 examples about 1.5 times, art about 0.8 times, back
  and follower (about 2900 each) only about **half** of their examples, once. LoRAs usually need several passes. With
  the cautious lr 5e-5 and hue-shifted copies that add little new information, the models learned the format and
  little else. Next time plan in **epochs** (passes over the data) and derive the steps from them, make the data
  smarter instead of only bigger (truly different examples, drop weak sources), let the judge decide when a run stops
  improving, and first run one LoRA long on the Legion overnight (free) to see where its quality curve flattens.
- **Every warm-up costs about 12 minutes per LoRA** (model load and caching the text embeddings). Fewer, bigger
  LoRAs (the "all directions" one) save that.
- **Speed.** 640 px with references: 2.1 s/step with gradient checkpointing, 1.4 s/step without. Without it the GPU
  ran at 100 % and up to 87 GB. But **with several references or a big picture it runs out of memory**: back v4
  (up to 4 references) silently skipped 99 of 1500 steps, and follower v3 (1024x512) started skipping too. ai-toolkit
  only prints `# OOM during training step, skipping batch`, so watch for that line. Rule: checkpointing **on** for
  more than 2 references, anything above 640 px and batch 2; off only for art style and single-reference LoRAs.
- **Progress pictures**: ai-toolkit's cached sample prompts (`cache_text_embeddings`) were encoded for 512 px references
  whatever the sample size, so every LoRA with references crashed at step 0. Fixed in the pod with one line in
  `extensions_built_in/sd_trainer/SDTrainer.py` (pass `width`/`height` of the sample item to `GenerateImageConfig`).
  Use `guidance_scale: 1` (Qwen-Image 2.1 is meant to run without guidance). One picture costs about 8-12 seconds.
  The same one-line fix is applied to the Legion's ai-toolkit (`v5cfg\patch_sdtrainer.py`, run with `PYTHONUTF8=1`);
  a fresh ai-toolkit checkout needs it again.
- **Spare VRAM**: without checkpointing and with one reference the GPU is full in compute but not in memory; the room
  can buy batch 2+ or a bigger LoRA rank (64) instead, at the cost of time. Only worth it once the basics above work.
- **Being on top of it** (Arvind had to ask "går det bra nå?"): check every LoRA myself when it starts, after its
  first pictures and when it ends; never report "fine" before checking, and test on the hardest LoRA, not the easiest.
- **Batch 2** (only art -> front A/B) needs checkpointing on 96 GB.
- **SSH habits**: never `pkill -f` / `pgrep -f` a pattern that also appears in the same remote command (it kills the
  session); start long Legion jobs with `Invoke-CimMethod Win32_Process Create`, never `Start-Process` over SSH (it
  dies with the session). A downloaded tar can be caught while it is still being written: compare sizes and retry.
- **Prompts at use time** (art style on Cowfin/Saucerl): the training sentence works best without the "same creature,
  nothing added or left out" part; a bare "Official Pokemon artwork." copies the whole picture, including
  backgrounds and text.
- **Results** (to be completed after the round): art style v1 **fails the transfer test** (cat, owl, lamp creature,
  robot, llama): plain Qwen-Image 2.1 already draws clean, convincing official-looking Pokemon art from the style
  sentence, and the LoRA makes it scratchier and messier, sometimes a hybrid (the robot turned into a bug Pokemon, the
  llama grew wings); on concept art its effect was small. Likely causes, both in our data: **every PokeAPI official
  artwork is only 475x475**, so training at 1024 blew each one up about 2x and the LoRA learned the soft, ragged look
  of an enlarged picture (art v1's 640 px targets are enlarged 1.35x too); and **one identical caption for 968
  artworks from 30 years** (Sugimori's sketchy Gen 1-2 watercolours next to today's clean digital art) taught an
  average of all eras. Base Qwen already knows the style well. Fix: check source resolution before choosing the
  training size (train at about 512, or find bigger sources), name the era in the caption ("Gen 1 watercolour" vs
  "modern digital"), or leave the oldest eras out of style LoRAs. The style may not need a LoRA at all.
  **Icon v3 is the best of the round**: real, sharp pixel icons, Waffy included; it was the only one trained at 16x
  (one icon pixel per latent cell), which supports the blob explanation. Bronzor is best around step 1000 and turns
  into a lump at 1250-1500. Its truth icon for Cyndaquil looks wrong (black head): `recolour_icon` keeps icon colours
  darker than luma 70 as outline, so dark body parts in the shared HGSS icon palettes stay near black, in the
  training targets too. **Art v1 from sprites works**: from an 80x80 sprite it draws recognisable official artwork
  (Houndour, Bronzor, Cyndaquil, our Waffy), colours moving towards the truth; little change after step 500.
  Two steps for a rough sketch (plain Qwen cleans it, then art v1) no longer falls apart, but stays close to the
  cleaned drawing instead of redrawing it. Open: back v4 was only shown front + art in its progress pictures; test it
  with the follower sheet as an extra input (it had one in half its training examples).
- **Round 2 test on the Legion (icon v4, night 2026-10-09).** Icon v4 (v3's data plus a template reference, front + art
  inputs) and a control without the template (v4c), both trained on the Legion's int8 `convrot8` base. Their RAW
  pictures (ai-toolkit samples and ComfyUI) looked noisy next to v3 (RunPod, bf16), and I first concluded the int8
  training was the problem. **The judge showed otherwise**: snapped to the 32x32 grid (as our pipeline does with every
  sprite), on the 21 held-out species that have a truth icon, DINOv2 similarity was v3 1500 0.772, v3 1000 0.806,
  **v4 1000 0.813**, v4c 1000 0.798, and v4 beat v3 1500 on 16 of 21 species. The sheet agrees: after snapping all
  four are decent and v4 most often has the right SIZE (compact like the truth; v3 often too big), which is what the
  template was for. Lesson: **judge the finished output after the pipeline's own clean-up, never raw pictures**; the
  Legion can be used for icon-sized experiments. At step 0 the base model copied the template's blue frame into the
  picture (gone after training). Judge fixes needed: only 21 of 40 species have a truth icon (`recolour_icon`
  rejects the rest), and the "hybrid" share (nearest training icon closer than the own truth) came out 0.8 for every
  run, so it does not separate anything; use the retrieval rank of the own truth instead.
  **More passes help** (v4 resumed from 1000, judged again at 3000, 2026-10-09 11:00): silhouette overlap (IoU) rose
  steadily, v4 1000 0.528 -> 2000 0.567 -> **3000 0.616** (v3: 0.534 / 0.545); DINO jumped around (0.813 / 0.760 /
  0.803, v3 0.806 / 0.772), so with 21 species x 2 seeds DINO alone cannot tell these apart. By eye v4 3000 looks
  the most like real HGSS icons: right size, the dark ground under Diglett/Dugtrio, Jigglypuff's eyes. Best icon
  LoRA so far: `pkmn_icon_v4_000003000`.
  **Judge calibration (Arvind, 63 blind A/B pairs of those runs, 2026-10-09)**: agreement on the 49 pairs he decided:
  DINO 59 %, Claude 53 % (63 % leaving out its "same"), silhouette IoU 41 % (worse than chance: it prefers what he
  does not). None reaches the 75 % bar. His wins were nearly flat across the five runs (9-11 each, 14 "same"): **to him
  the versions are about equal** (so icon training on the Legion is as good as on RunPod), and the template + extra
  passes made no difference he sees. His criteria: "how much it looks like the truth, and can I recognise it" on a
  scale noise / "aha, now I see it" / good; every run produces a mix of the three. So: drop IoU as a quality score;
  the judge to build is a **recognisability test** (retrieval rank: "which of the ~1000 Pokemon is this?", DINO or
  the trained head; for our own mons the rank of their own artwork among all artworks), calibrated with a 3-grade
  rating (noise / aha / good, one click per picture) instead of A/B, on sets with real quality differences.
  Page: https://claude.ai/artifact/DbydQsB4gUJ8TorPnreja7 (votes in its db).
  **A ready-made classifier works** (Arvind: build on what exists): `skshmjn/Pokemon-classifier-gen9-1025` (ViT,
  Apache-2.0, index + 1 = dex number), run on CPU, recognised all 21 real front sprites, 14/21 real icons top-1
  (17 top-5) and 10-12/21 of our LoRA icons; imzynoxprince was close, dima806 weak, JJMack failed to load. As a judge
  on Arvind's A/B votes: classifier probability of the right species 63 %, DINO 59 %, **classifier x DINO 69 %**
  (best so far, on the hardest possible set). His scale mapped automatically (top-1 = good, top-5 = aha, else
  noise): 56 good / 27 aha / 22 noise of 105 LoRA icons.
  **Colour drift explained (2026-10-09)**: Houndour turned lighter grey and Waffy grew grey around the head from step
  3500 on. Cause in the data: `recolour_icon` maps only colours of luma >= 70 to the battle sprite's palette and keeps
  darker ones as "outline", so dark body parts keep the shared HGSS icon palette's greys (Umbreon's training icon is
  slate grey-blue with a (65,65,65) outline, not black). The LoRA learned "dark body = grey" and learns it better the
  longer it trains. Fix for icon v5: recolour every colour to the sprite's own and keep only the outermost outline
  ring as the outline colour (Arvind to choose: own colours everywhere, as chosen for icon v2, or real HGSS palettes). Next: a 3-grade rating round to check those grades against
  his, then use it to pick checkpoints, best-of-N and later rewards. Scripts `v6cfg\test_classifiers.py`,
  `classifier_probs.py`.
  Files: `v6cfg\` (icon_v4/v4c configs, build scripts, `diag_icon.py`, `eval_icon.py`), sheets in `results\`.
- **Icon finishing step** (`v6cfg\finish_icons.py`, 2026-10-10; Arvind: ours are bigger, have more colours and more
  shading than real icons): snap to the grid (best offset), drop stray pixels, map to the best of HeartGold's own
  shared icon palettes (7 found in hg-engine's indexed icon.png files, used by >= 20 icons each; `sprites.py` uses
  Emerald's 6) and despeckle. On v4 step 4000: raw icons have ~190 colours (soft shading), finished 6.6 (real icons
  8.1); size is already close (21.4 x 20.9 px vs real 20.9 x 19.8). Finished icons look flat and game-like; the palette
  pick can go wrong on dark creatures (Venonat, Haunter turn grey), which a model trained on the game palettes
  (icon v5) should avoid.
- **Icon v5 (Legion, night 2026-10-10)**: real game icons as targets, no hue copies (998 examples), template with grey
  corner marks, lr 1e-4 constant, rank 64, 4000 steps, all bundled (Arvind's choice). Judge v2 (40 species x 3 seeds):
  recognisability v4 step 4000 **0.31** (good/aha/noise 71/24/25 of 120) vs v5 0.15-0.19 (40-50 good, 39-56 noise).
  Not a judge bias: the classifier recognises the real game icons at 0.35 (23/40 top-1) and the recoloured ones at
  0.38, so v4 is close to the real icons' own level. By eye v5's colours and flat look are closer to the game palette
  (Tyranitar, Metagross, Venonat) but more of them are muddled. Which bundled change hurt is unknown; prime suspects:
  the constant lr 1e-4 (no decay at the end, v4 ended at a low lr) and fewer, harder targets (palette colours
  unrelated to the input's colours; the hue copies also worked as augmentation). So far the best icon recipe is v4
  (recoloured targets, cosine 5e-5) + the finishing step for the game palette.
- **Follower v5 (2026-10-10)**, replacing v4 before any paid run. Arvind: the abstract template was not good and the
  follower should see more views (he had asked for back and icon). The free Legion preview of v4 ran at 20 s/step
  (VRAM full, spilling into RAM) and was stopped at step ~244. New references, within ai-toolkit's 3-sample limit:
  front sprite (8x), a **reference sheet** with every other view in one picture (back, menu icon, official artwork,
  HOME render; dropped at random 10-30 % each, the caption names what is present) and a **box template**: two thin
  light-grey boxes, one per walking frame, sized for this creature, each with an arrow inside pointing the walking
  way; the caption says it is only a guide that is never drawn. A first version used an *example* (the real follower
  of another species walking the same way); Arvind rejected it before any run because an example of another Pokemon
  invites the hybrid problem from round 1.
  **Box size, measured on all 3768 examples:** one fixed box per direction (the v4 median, 19x21 px) held the whole
  figure in only 32 % of frames; small creatures filled about half of it (p10 0.55 of the box area), big ones went
  outside (p90 1.63). Followers range 12-29 px wide and 14-28 px tall (p5-p95); the feet sit at row 29. The front
  sprite's size predicts the follower's size (height r 0.75, width 0.61), so every example now gets its own box:
  half the real box (union of both frames, each side moved by up to 1 px), half the box **predicted from the front
  size** (least squares per direction; mean error 1.6 px per side, 76 % within 2 px), which is what a new Pokemon
  gets. The mix teaches that the box is only about right and that the shape comes from the references (Bronzor seen
  from the side is 5 px thin; its predicted box is 17 px wide). For our own mons the box is also a size control: set
  it by hand. Code `v6cfg\follower_boxes.py` (box, fit, predict, template, build); coefficients and every box in
  `data\v7\follower5_boxfit.json`; the progress pictures use predicted boxes.
  Targets as v4 (own two walking frames, 16x, 1024x512). `v6cfg\build_follower_v5.py` (the switch to boxes on the
  built data: `follower_v5_boxes.py`, `_boxes2.py`, `_boxes3.py`), data `data\v7\follower5` (3768 examples),
  samples `pod2\samples\follower_v5`, config `pod2\cfg\follower_v5.yaml` (7500 steps; after the review lr 5e-5 cosine, rank 32, resolution [1024]),
  check sheet `results\follower_v5_boxes2_check.png`. Session 2 now runs follower v5 only (icon: v4 step 4000 +
  finishing stays the best). **Not on the Legion:** the v4 preview ran at 20 s/step there (VRAM full, spilling into
  RAM), so 7500 steps would take about 42 hours with v4's two references and longer with v5's three; on the RunPod
  RTX Pro 6000 it is about 4 hours, about 8-9 dollars.
  The session 2 pod (`gtxnx4srb1ip7z`, US-NE-1) was created, stopped after about 4 minutes when Arvind said to wait,
  and then terminated at his request; the next start makes a new pod.
- **Why icon v5 lost (2026-10-10, from the judge reports):** not the constant lr at the end: v5 was as weak at step
  1000 (recognisability 0.17) as at 4000 (0.19) and never came near v4 (0.28-0.31 at steps 3000-6000). Its shapes are
  as good as v4's (DINO 0.78-0.80 for both); what it lost is recognisability, i.e. colours and details (worse on 18 of
  40 species, better on 11). Most likely the game-palette targets (colours that do not follow the input's colours: the
  model must guess one of 7 shared palettes) with fewer examples (998 vs 1678, no hue copies). Icon v6 A vs B tests it.
- **Back v5 (2026-10-10)**, the follower v5 recipe on backs: front (8x) + reference sheet (its overworld frames seen from
  behind = the back view in pixels, menu icon recoloured, artwork, HOME; pixel ones dirty in 30 %) + placement box (real
  or predicted from the front's size, 50/50; the bottom line drawn heavier = the flat cut). Backs are big (median 73 px
  wide, 62 tall; bottom row median 72), the front predicts the box less well than for followers (3.9 px per side).
  **Near-duplicate trap, measured:** 57 % of the extra versions of a species (DP / Pt / HGSS) differed in < 2 % of
  their pixels; extra versions that differ in < 10 % were dropped (693), leaving **1230 examples of 968 species**
  (`v6cfg\build_back_v5.py`, `back5_post.py`). Trained at **16x** (1280, one sprite pixel per latent cell, the cure for
  blobs) with the references at their own size (`model_kwargs: match_target_res: false`: ai-toolkit otherwise scales
  every reference to the target's area, which would make a 1280 target cost about 4x the tokens); fallback
  `back_v5_8x.yaml` (640) if the smoke test is too slow. 4000 steps (3.3 passes), EMA; after the review lr 5e-5 cosine, rank 32.
- **ai-toolkit reference sizing (checked in the code, ecee894):** Qwen-Image 2 sets `use_raw_control_images`, so
  references are NOT stretched to the target's shape (a false alarm I raised); with `match_target_res` (default on)
  each is scaled to the target's AREA, keeping its aspect (follower v5's 640 front became 724, 9.05x, smoothed). Both
  RunPod LoRAs now use `match_target_res: false`: references keep their exact pixel size. **At use time ComfyUI must
  get the references at the same sizes** (pre-scaled, `TextEncodeQwenImage21` resolution 0); icon v6 keeps v4's
  scaling (16 GB).
- **Judge for progress pictures** (`v6cfg\judge_samples.py <lora> <samples folder>`): the progress pictures are the
  test set (follower 24: 0155 x4, 0228 x2, 0436 x2, 12 more held-out species one direction each, Waffy x4; back 17;
  icon v6 21), references made like in training with predicted boxes, truths saved next to them
  (`make_judge_samples.py`, `make_icon_v6_cfg.py`). Snaps to the sprite grid, then recog x DINO per checkpoint and a
  sheet. Self-test with the truths as outputs: follower ceiling recog 0.35, back 0.62. **Trap found by the self-test:**
  a back that only copies the front scored 0.58 vs 0.62 for real backs (the classifier knows fronts better), so a copy
  (output closer to the input front than to the real back, by DINO) now scores 0 (a gated reward).
- **RunPod session 2, final plan (2026-10-10):** one pod; `pod_setup2.sh` smoke-tests EVERY LoRA (20 steps, 2 pictures,
  s/step, errors, out-of-memory skips, weights moved) before the real run; then `pod_train2.sh follower_v5 back_v5`
  (follower about 4 h, back about 4 h at 16x, to be measured; about 20 dollars). The live page (`dash.py`) reads the
  queue from train.log, shows inputs and truth next to every progress picture and flags skipped steps. `fetch2.ps1
  -names follower_v5,back_v5` downloads and stops the pod. In parallel on the Legion (free): **icon v6 A/B**
  (`build_icon_v6.py`, configs `v6cfg\icon_v6A/B.yaml`): front + reference sheet (back, overworld frames walking down,
  artwork, HOME) + the 32x32 grid with a grey box per creature (predicted or real, 50/50); v4's recipe (rank 32, lr
  5e-5 cosine, EMA, int8); A = v4's targets (keeps v4's duplicates and the "dark = grey" drift on purpose, so A vs v4
  shows what the new references do), B = the game-palette targets. Icon v6 is the canary for the new inputs: step 1000
  catches gross failures (box drawn into the picture, sheet confusion); the full verdict comes from the judge.
- **Independent review of the round-2 plan (2026-10-10, a research agent; claims checked against the code before acting):**
  1. **Bug:** follower `resolution: [724]` gives ai-toolkit bucket 992x512 (max resolution^2 pixels in multiples of 32;
     724^2 < 1024x512), so every target was centre-cropped by one sprite pixel per side and shifted against the
     template, silently. Fixed to `[1024]`; the smoke test now prints the bucket sizes. (Round 1's 724 had the same flaw.)
  2. The RunPod recipe (rank 64, lr 1e-4) was not what the icon canary tests, and is about 3-4x more aggressive than
     icon v4's (update size scales with alpha x lr, and with rank at alpha = rank: Thinking Machines "LoRA Without
     Regret", rsLoRA); it is icon v5's losing recipe. Follower and back now use v4's: rank 32, alpha 32, lr 5e-5 cosine.
  3. The back's placement template is now 1280 like its 16x target (each picture's rotary positions are centred on its
     own token grid, so a same-size template lines up with the target position by position; follower and icon already
     matched); `template16`, the 8x fallback keeps 640.
  4. Train on references as they will be at use time: views that a new mon only gets from another LoRA (back, icon,
     follower) are now missing in 50 % of the examples (was 10-30 %), artwork / HOME degraded in 35 %, the follower
     sheet's pixel views dirty in 30 % (principle: conditioning augmentation, Ho et al. 2021).
  5. The judge's copy gate: a copy is an output more like the input front than the REAL back is (+0.05), not "closer to
     the front than to the truth" (good backs of round creatures would fail). The 69 % agreement rests on 49 decided
     pairs (about +-13 points): use the judge to reject broken checkpoints and leave the final pick among the top 3 to
     Arvind. Also fixed: loss masks widened by a whole 16 px latent cell on every side (a 17 px filter reached only the
     right/bottom cells once sampled on the latent grid), and the back sheet's icon recoloured per version.
  Later, from the review: finishing step + real-vs-ours detector (a classifier two-sample test; the biggest lever for
  "indistinguishable"), re-sampling the top 3 checkpoints with 3+ seeds, hue-rotated held-out inputs and a few Smogon
  CAP designs as canaries, held-out loss at fixed noise as a second checkpoint signal, a palette swatch in the sheet's
  empty column, paired hue copies (about 20 %) for follower and back. Arvind (2026-10-10): no examples of other Pokemon
  as inputs (hybrid risk); inputs in other styles (Gen 3/5 fronts, our own tool's fronts) only once a LoRA nails
  Nintendo's fronts but not ours. Evidence on lr / rank / epochs for edit LoRAs on
  1-4k multi-reference pairs is thin (community numbers are for 20-200 pairs).
- **Forms trap (2026-10-10, found after Arvind asked "does it train on the wrong Dugtrio, maybe Alolan?"):** v2's sets
  include forms (regional forms, Primal / Castform / Burmy cloaks, spiky-eared Pichu ...) under the BASE species number
  (48 regional-form sets alone; Diglett, Dugtrio and Graveler have Alolan sets among the held-out). The held-out
  progress pictures were fine (they take the HGSS set), but in training a form's front/back/target sat next to the base
  species' artwork / HOME / icon / follower in the reference sheet: contradictory signals. Dropped: back5 74 (-> 1156),
  follower5 1 species (Terapagos Stellar, 4 examples -> 3764), icon_B 15 (-> 983); icon A (already training) keeps
  its 38 (2.3 %). Rule: a form is its own creature; keep it only with references of that form, else leave it out.
- **Existing pixel cleaners vs ours (2026-10-10, icon v6 A step 2000, 20 held-out + Waffy; `v6cfg\tools_compare.py`,
  `tools_judge.py`, `unfake_palette.py`; tools in `D:\LocalAI\tools`):** Retro-Diffusion's Pixel Art Fixer (MIT; its CLI
  has a broken import, the Python API works) finds the right 32x32 grid every time but so does our snap, since we draw
  at exactly 16x; it keeps every colour (~174). unfake (MIT, `pip install unfake`, CLI with `-s 16`) cuts ~180 colours
  to ~11 (real icons ~8) with the image's own colours: flatter, more game-like, recognisability 0.35 vs 0.40 (11
  species, 1 seed: within noise). Locked to the FRONT's palette (`--palette`) it gets 8.7 colours and the highest DINO
  (0.84) but sometimes takes a wrong front colour (olive ground on Dugtrio and Tentacool; recog 0.28). Use unfake
  (auto palette) as the colour step now; the front-palette lock once the model already draws with the front's colours
  (palette hint in training).
- **Test day on icon v6 A (2026-10-10/11, `v6cfg\tests_legion.py`, results\tests; 20 held-out + Waffy, the 11 with a
  truth judged, 1 seed unless noted; differences under ~0.06 are noise).** Icon v6 A itself: judge best at step 2000
  (recog 0.40, about the real icons' own 0.35-0.38), lower after (0.30 at 3000-4000). Canary passed: from step 500 no
  box or sheet drawn. Findings: (1) **ComfyUI draws the same as ai-toolkit's own sampler** (same seed: near pixel-identical;
  seeds 42/43/44 score 0.27/0.35/0.34 vs ai-toolkit 0.33) and is ~6x faster (8-9 s vs 52 s per icon): past ComfyUI
  failures were settings (reference size 1024, lost alpha, prompts), not the program. (2) **LoRA strength 0.75 scored
  best** (0.40; 1.0 ~0.32; 1.25 0.26; 1.5 0.18): more of the base model's own knowledge of the creature. (3) **The text
  hardly matters**: training caption 0.27 = no prompt 0.27, a short prompt 0.21; the pictures carry the task.
  (4) Draft -> refine at denoise 0.5: fewer colours, DINO up, recognition not (0.25): not worth the time. (5) Train-fit:
  13 TRAINING species are drawn no better than new ones (0.25 vs 0.27): it does not memorise; the limit is how well it
  draws icons at all (suspects: A's recolouring errors, too little training). (6) **The game's icon palette cannot be
  predicted from the front** (least colour error 14 %, kNN on colour histograms 53 %): a game-palette hint would be wrong
  half the time at use time, and this is the likely reason icon v5 (game-palette targets) failed. Bugs of mine caught on
  the way: ComfyUI's upload keeps the base name, so three references with the same file name overwrote each other
  (fixed with unique names); a test folder's judge report overwrote the run's own (reports now named per folder).
- **Data audit (2026-10-10, `v6cfg\audit_data.py`, `placeholders.py`):** backs are clean (colours match the front, median
  100 %). **Follower placeholders:** hg-engine reuses Bulbasaur's overworld for 23 Gen 9 species without one (Chien-Pao,
  Miraidon, Koraidon, Scream Tail, Baxcalibur ...): 92 follower examples taught "draw Bulbasaur"; dropped (-> 3672).
  Icons and backs have no shared placeholder pictures. DINO retrieval (does the target look like its own front?) works
  for backs (median rank 2) but not across formats (32 px frames / icons vs 80 px fronts).
- **Overworld palettes and the full data contract (2026-10-11, `v6cfg\ow_palettes.py`, `data_contract.py`):** every
  hg-engine species folder has `overworld.png` plus `overworld-tsure_poke0.pal` (normal) and `...poke1.pal` (shiny).
  1459 of 1535 overworld.png files carry poke0 (normal), 75 neither (Gen 8-9; incl. the placeholders), **one carries the
  shiny palette: Kubfu** (dropped, follower5 -> 3668). HGSS follower palettes differ from the battle sprites: Zubat and
  Golbat follow in teal + purple in the real game (their shiny is green + pink), so a low colour match with the front is
  not by itself an error. The contract check passed with 0 problems on all 3668 follower and 1156 back examples: every
  file present at the right size, binary alpha, masks covering the target, captions naming exactly the views drawn in the
  sheet, no held-out species, no forms, no placeholders; a random 36 of each checked by eye. Package 588 MB.
- **Night 2026-10-10/11 (Legion queue, `v6cfg\night_queue.ps1` then `night_queue2.ps1`):** icon v6 Ap (A + the FRONT's
  colours as a palette swatch in the sheet's empty column; the hint a new mon really has, and exactly what backs use),
  icon v6 As (A + `content_or_style: style`: more practice at low noise), both 2000 steps on A's lr curve, no ai-toolkit
  pictures; then ComfyUI judges A / Ap / As at 500-2000, a sampling-steps x LoRA-strength grid, Qwen's prompt rewriter
  (Qwen-Image-2.1-PE-I2I, 4-bit) as a fourth prompt variant, the **pixel lock while drawing** (our ComfyUI node
  `custom_nodes\sigma_pixel_lock`: after every step the model's guess is decoded, snapped to the 16 px grid and optionally
  the front's colours, encoded and handed back, via the post-CFG hook dynamic-thresholding nodes use), a region lock
  (top half kept, bottom redrawn) and icon v6 A vs v4 on all 40 held-out species x 3 seeds.
- **RunPod session 2, run log (2026-10-11, notes taken during the run):**
  - 16:35 JST pod `q533evql026u6p`: **RTX PRO 6000 Blackwell Max-Q (Community, 1.64 $/h)**, 96 GB, 300 W power limit
    (the Server Edition draws up to 600 W, so expect it slower), driver 580 (CUDA 13), 251 GB RAM, 16 vCPU. Community
    RTX PRO 6000 Server/Workstation and all H100s were sold out at that moment; Secure RTX PRO 6000 (2.49 $/h) was the
    fallback. Direct SSH appeared after ~10 min (`runtime` null until then; the proxy SSH also works from the Mac).
  - Upload from the Legion straight to the pod: 588 MB in ~2.5 min, size checked to the byte. Live page:
    `dash.py <token> <pod start epoch> 1.64` on port 8888, reached through `https://<pod>-8888.proxy.runpod.net/<token>/`.
  - Lesson (SSH): a background job started with plain `nohup ... &` keeps the SSH session open; use
    `setsid nohup ... < /dev/null &` so the command returns.
  - Setup ~1 h in all: models 6 min to download, then each smoke test caches the text embeddings of its WHOLE dataset
    (follower 3668 in ~15 min at ~4/s, back 1156 in ~5 min) - not wasted, the real run reuses the cache.
  - Smoke tests passed: 0 errors, 0 out-of-memory skips, 4 pictures each, LoRA weights moved; **buckets now exactly the
    target size** (follower 1024x512: 3668 files, back 1280x1280: 1156; the [724] crop is gone). Speed on the Max-Q:
    **follower 3.5 s/step, back at 16x 7.2 s/step** (the Server Edition did 2.1 s/step at 640 in round 1; the Max-Q and
    the bigger inputs are both slower). Estimate: follower 7500 steps ~8 h (~13 $), back 16x 3000 steps ~6.7 h (~11 $).
  - 17:35 JST follower_v5 started (`cfg/run_queue.sh`: follower, then the back named in `cfg/back_choice`, read only
    when the back starts, so 16x/8x can be decided during the follower). Legion `fetch2.ps1` downloads and stops the pod.
    Arvind chose 16x for the back (+~7 $ over 8x; the evidence for 16x against blobs is the strongest we have).
  - **Early stopping instead of guessing the step count** (Arvind's question "is 7500 right?"): icons peaked at 0.9-1.5
    passes; the follower is harder, so 2 passes is the ceiling, and a live judge (`pod2\live_judge.ps1` on the Legion:
    copies the progress pictures every 10 min and scores each finished checkpoint on the CPU) shows the curve. Arvind
    decides when to stop from the pictures; the best checkpoint is used either way, so stopping early costs no quality.
  - Follower, first numbers: step 0 recog 0.08 / DINO 0.67 (base model drawing the template and sheet); step 750 recog
    0.24 / DINO 0.83 / good-aha-noise 10/6/4 of 20; step 1500 0.23 / 0.79 / 8/6/6 (real followers' own recog ~0.35).
    By eye at 750 already real follower sprites (two frames, right size and direction, outline, colours; Waffy a blue bird
    with a yellow beak in all four directions); weak: Cyndaquil's back (up), Graveler's colours, Kadabra, Bronzor's thin
    side view. Far better than round 1's blobby whole sheets.
  - **Lesson (Windows SSH, cost an hour of blind monitoring):** `ssh.exe` started from a console-less process (Invoke-
    CimMethod) without `-n` waits for stdin forever: fetch2 and the live judge hung on their first `ssh ... cat`. Every
    scripted ssh on the Legion now runs `ssh -n -o BatchMode=yes -o StrictHostKeyChecking=no -o ServerAliveInterval=15`.
    Check a watcher's first round actually completes, not just that it started.
- **Towards "you cannot tell ours from the real ones"** (Arvind, 2026-10-10): in order of evidence: the right format
  (16x everywhere), the right information in (reference sheet, boxes), enough passes with the judge picking the
  checkpoint, clean data (real, no near-duplicates, right palettes), a **finishing step for every format** (as for
  icons: grid, at most 16 colours from the front's palette, dark outline where missing, stray pixels removed; real
  backs have about 10 colours and a dark outline on 79 % of their edge, ours had 58 %), best-of-8 with the judge at
  use time, then reward training (DPO) on judge-ranked pairs. Measure it with (1) a blind test for Arvind and friends
  ("which is real?", goal about 50 %) and (2) a real-vs-ours detector trained on real HGSS sprites against our finished
  ones: at about 50 % accuracy we are there, and what it keys on (colour count, outline, shading) says what to fix
  next; later it becomes part of the DPO reward (realism x recognisability x not-a-copy).
- **RunPod session 2 (prepared 2026-10-09 for 2026-10-10 12:00 JST)**: icon v5b (bf16, the same data and recipe as
  the Legion's icon v5) and **follower v4**: one direction per example, its two walking frames side by side at 16x
  (1024x512), inputs front + back + a per-direction template (grid, small arrow, grey corner marks; no solid
  frames), 942 species x 4 = 3768 real examples, 7500 steps, lr 1e-4 constant, rank 64, checkpoint and pictures every
  750 steps; stop early if it looks bad at about one pass. Package `D:\LocalAI\lora-train\pod2.tar` (313 MB: configs,
  samples, data v7) + `pod2\cfg\pod_setup2.sh` (pip flag, torch 2.14.1 cu130, torchaudio stand-in, SDTrainer patch,
  rebuilds the template folders, smoke test WITH pictures) + `pod_train2.sh` (writes "ended" only after the tar is
  packed) + `dash.py <token> <pod start epoch> <$/h>` + `pod2\fetch2.ps1 -pod root@<ip> -port <port>`. Lesson from
  packing: ai-toolkit writes its text-embedding cache (`_t_e_cache`, 7 GB for 1000 icons) into the data folder:
  exclude it, the pod makes its own.
- **The family idea** (Arvind): one LoRA per step means a round does not have to get everything right; find the
  weakest link and retrain only that. Art v1 redraws clean concept art in a new official pose but breaks
  down on rough line sketches (it never saw a sketch as input). The idea for the next round is synthetic sketches made
  from official artwork. Back v4 learned the format (pixels, outline, flat cut) but not the design.

## Next ones (later)

- **first: judge the LoRAs properly** (agreed with Arvind 2026-10-09). Round 1 was judged on loss (says little about
  quality) and 3-4 progress pictures with one seed: too few to tell an improvement from a lucky seed. Before the next
  round: score every checkpoint automatically on all 40 held-out species with several seeds against the truth (shape:
  alpha overlap; colours: palette distance; format rules: size, outline, the follower's grid placement, reusing
  `sprite_quality.standards()`), show that score next to the loss on the live page, pick checkpoints and configs by
  it, and keep the sheets for Arvind's final call. Try changes as short (300-step) A/B runs on the Legion first and
  send only the winners to RunPod. Later, Arvind's picks on the sheets can become preference data.
  Judges for "is it still the same, legible creature" (Arvind: results look like blobs): DINOv2 similarity to the truth
  (or to our input artwork for our own mons; the DreamBooth-style "DINO score"), a species classifier trained on all
  1025 species including the 40 held out of the LoRAs ("recognised as Cyndaquil?" = legible), plus the format rules.
  Use them in this order: pick checkpoints/configs, then best-of-N at use time (generate 8, the judge keeps 2-3 for
  Arvind), and only later reward training (DDPO / DRaFT / Diffusion-DPO / Flow-GRPO for flow models; needs our own
  code, and watch for reward hacking).
- **judge and reward plan** (research 2026-10-09, three web reviews; details and links in the session notes):
  - *No ready-made Pokemon classifier fits*: the public ones (skshmjn gen9-1025, dima806 1000 types, JJMack gen1-9,
    imzynoxprince) are ViT-B/16 trained on artwork, cards or screenshots, with no pixel-art or unseen-species results.
    Build our own judge: a frozen backbone (DINOv2 / DINOv3 / SigLIP 2, chosen by cross-format recall: artwork ->
    real sprite among all species) plus a small contrastive head trained on all formats of all 1025 species (PokeAPI
    sprites has gen I-IX sprites, icons, HOME, official artwork; synthetic downscaled sprites for #650+), about 100
    species kept out of the head as a stand-in for our own mons. Real species: probability of the right species plus
    similarity to the real sprite. Our own mons: rank of the input artwork among all artworks (retrieval rank).
    Upscale pixel art with integer nearest neighbour to the backbone's patch grid. A quick version (frozen DINOv2 +
    cosine to the truth) takes 1-2 hours; the full judge 2-3 days.
  - *Which measures follow people*: DINO beats CLIP-I (DreamBooth r 0.32 vs 0.27) but both are weak; a VLM with
    explicit criteria does best (DreamBench++: GPT-4o 83 % of human agreement), pairwise ("which is the same design as
    the reference?", both orders) beats absolute scores. Calibrate any judge against about 60-100 of Arvind's blind
    A/B choices and keep it only at about 75 % agreement. A "drift" check flags outputs closer to another training
    species than to their own truth (the hybrid problem). With 40 test species a new version must win at least 27 of 40.
  - *Transfer test* (Arvind): subjects that are not Pokemon (cat, owl, lamp creature, robot, llama) through the style
    LoRA, and a fixed set of our own mons through every LoRA, every round.
  - *Reward training*: Flow-Factory (Apache-2.0) supports Qwen-Image 2.1 with a LoRA edit-GRPO example (written for 8
    GPUs); DiffusionNFT and DPO are in it too. Order: validate the judge, measure the headroom (oracle best-of-8 vs the
    average), then offline best-vs-worst DPO on LoRA (samples from our LoRA, pairs with a clear judge margin, small
    beta and learning rate; fits a 96 GB pod), and online GRPO/NFT only if headroom remains. Against reward hacking:
    a gated reward (format valid x species probability x identity, not a sum; editing models otherwise learn to copy
    the input), a small KL to the reference plus EMA, drop groups whose rewards hardly differ, a held-out judge from a
    different model family, and human spot checks with early stopping.
  - Qwen-Image 2.1 is under the Qwen Research License (non-commercial): fine for the fan project, but nothing built on
    it can be sold.
- **better captions and prompts** (Arvind: "vi bommet litt på promptene"). Round 1's captions described the task, never
  the creature: one template per LoRA ("<image1> is the front sprite ... draw its back sprite"), and one identical
  sentence for all 968 art style examples. So text could not help keep a design, and the style LoRA had to soak up
  everything as "style". Next round: a short, fixed feature list per species written by Qwen3-VL from the official
  artwork (colours, parts, markings) in every caption, plus what varies per example (facing, crop, pose); at use time
  the same model writes the list for our own mons from their artwork. Use-time prompts follow the training captions
  (round 1: the "same creature, nothing added or left out" clause made Qwen only clean up a sketch). Prompt and
  caption variants are tested like any other change: A/B on the 40 held-out species with the judge.
- **is LoRA the right tool?** (Arvind, research 2026-10-09): no evidence that another adapter fixes our problems; the
  known causes come first. ai-toolkit (ecee894) has lora, locon, lokr, dora, full rank; worth a short A/B later: rank
  64 vs 32 and LoKr (`lokr_factor` 8). Skip DoRA (ComfyUI reads `dora_scale`, ai-toolkit saves `.magnitude`: it would
  load silently wrong). Qwen-Image 2.1 already takes references in context (the Kontext recipe), so IC-LoRA,
  OminiControl, UNO etc. add nothing. Multi-view models (Zero123++, SV3D, MV-Adapter, Era3D) target 3D, not pixel
  creatures; use them, or HOME renders, only as a guide picture for back/follower views. **Deployment checks**:
  ai-toolkit's default for this model is int8 `convrot8`, the same file ComfyUI runs, so the pod's bf16 training was
  the odd one out (the Legion trains on convrot8); and ComfyUI's `TextEncodeQwenImage21` resizes references to
  `resolution=1024` by default while training scaled them to the target's area: set `resolution` to the square root
  of the target area (640 for sprites, 512 for icons) or 0 with pre-scaled references. First diagnostic: the same
  checkpoint, seeds and prompts in ai-toolkit's sampler and in ComfyUI; if only ComfyUI is worse, it is deployment.
  Grid snap + palette quantisation as deterministic cleanup after generation (as `sprites.py` already does).
- **blobs, a likely cause**: Qwen-Image 2.1's VAE works in 16x16 pixel cells, and front/back/follower are trained at
  8x (80 px -> 640), so one latent cell covers 2x2 sprite pixels and 1-pixel outlines and eyes smear. Icons are at
  16x (one sprite pixel per cell). Test front/back at 16x (1280 px) on the Legion before the next round.
- the main lever is what each LoRA gets to see: it knows Pokemon already, so whenever information is missing it fills
  the gap with Pokemon it knows and the design drifts (round 1: every LoRA learned its format, none kept the design
  well when turning or shrinking the creature). Hence the guide pictures below, smaller tasks (one follower direction
  at a time), and more inputs: the follower should get the back sprite and icon, the back the follower sheet (it had it
  in half of its training examples, but the progress pictures only gave front + art);

- one LoRA for all directions (agreed with Arvind 2026-10-08 for the round after this one): the same data, each example
  gets a random subset of the species' pictures (art, front, back, icon, follower sheet, HOME render) as references
  and the caption says which one to draw. People can start from whatever they have, a mistake can be fixed by
  drawing a view again with the others as references, and one LoRA learns that every format is the same creature.
  Compared directly with this round's single LoRAs;
- guide pictures as extra references (Arvind's ideas, 2026-10-08), to weigh after the round 1 review:
  - **a layout template** for fixed formats: the follower sheet as an empty 4x2 grid with an arrow per cell (up, down,
    left, right; two walking frames), the icon's two frames side by side. It is the same picture for every example,
    so no new data is needed, and the LoRA no longer has to guess the layout from the caption;
  - **placement guides**: a frame that shows where the creature stands, how big it is and where the back sprite is cut
    off at the bottom. These can be made for our own mons too. Exact silhouette masks only exist for real Pokemon (the
    back silhouette of a new mon is what we want to draw), so they stay training-only loss masks, as now;
  - **the 3D form**: Pokemon HOME renders (3D models of the 2D designs, already in our data and already an input of
    art v1) as a reference for the views that turn the creature (back, follower), plus depth maps from them with Depth
    Anything V2 (cleaner than depth from flat artwork). For our own mons the chain would be artwork -> HOME-style
    render (Qwen already makes convincing ones from Sugimori art, tested 2026-10-08) -> depth -> back/follower;
- trainers (about 160 examples in hg-engine);
- image to 3D (Hunyuan3D 2.1 shape-only / mini and Pixal3D fit 16 GB).
