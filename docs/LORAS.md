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
  - **Style gap, measured at steps 750-2250** (`v6cfg\follower_style.py`, `follower_unfake.py`): real HGSS followers use
    ~11 colours per frame, a dark edge on 95 % of the outline, ~195 px filled; ours 155-185 colours, 81-87 % dark edge,
    198-252 px (1500 too big). unfake brings the colours to 10, yet they still look different: HGSS followers have their
    OWN lighter palettes and simplified, rounder shapes, while the model shrinks the battle sprite (its darker colours
    and inner detail). Arvind's evidence: **Jigglypuff from behind** (real: a round, flat, light-pink ball with almost no
    inner lines; ours: a spiky outline from the battle sprite, darker pink, shading) and **Diglett** (real: small and
    compact on a grey mound; ours: bigger on a brown mound, the front's colour). Partly unlearnable (Game Freak's per-
    species follower palettes, e.g. Graveler beige as a follower, grey in battle), partly a learnable general style
    (lighter, simpler, rounder) still improving at 0.6 passes. Jigglypuff and Diglett become fixed style canaries.
    Next: higher LoRA strength for followers at use time, unfake / palette lock, and a real-vs-ours style reward (DPO).
  - **Colour counting, corrected (Arvind: "very small differences count as much as big ones"):** counting unique RGB
    values overstated the problem ~10x: near-identical shades are invisible. Now colours are merged when closer than a
    delta-E in Lab (5 = just visible, 10 = clearly different; most-used first) and 1-pixel groups are dropped. Real HGSS
    followers: 10 / 10 visible colours; ours at step 3000: 21 / 15 (raw RGB 173), improving from 24 / 16 at 750. Use the
    perceptual count in every test from now on (`perceptual()` in `v6cfg\follower_style.py`).
  - Follower step 3000 (0.8 passes): best so far by the judge (score 0.207, recog 0.27, good/aha/noise 11/8/1) and by
    Arvind's eye; dark edge 90 % (real 95 %); a bit too big (242 vs 195 px; the box can steer size at use time).
  - **Left/right in the real followers (`v6cfg\mirror_check.py`, Arvind's question):** Game Freak's (1-493) right
    frames are the left frames mirrored for 460 of 481 species (96 %); the 20 exceptions are asymmetric designs (Kadabra's
    spoon, Farfetch'd's leek, Krabby/Kingler's big claw, Cubone/Marowak's bone, Roselia's two flowers, Weezing, Staryu,
    Croconaw, Sneasel, Magcargo). Fan-made (494+): 388 exact, 14 near, 115 own drawings. So: at use time draw left and
    mirror it (consistent sides, half the work, budget for best-of-N), drawing right separately only for asymmetric
    designs; next round train up / down / left only (~25 % less compute for the same result).
  - **Why the box beats the references for Bronzor's side view:** half the training boxes were predicted, yet the
    prediction is almost always close (1.6 px per side), so the model learns "follow the box"; the rare case where it is
    far off (a 5 px thin disk seen from the side, box 17 px wide) is too rare to learn. Next round: some boxes wrong on
    purpose (much too wide or narrow) and some examples with no box, so the references win when they disagree. At use
    time: set the box by hand for unusual shapes.
  - **"Why not just show it the answer?" (Arvind):** the answer as an input teaches copying (the answer is never there
    for a new mon). The useful variant is a **stylist LoRA**: input = a rough draft (our model's own output on training
    species, or the real sprite made worse: too many colours, scribbles, wrong lightness), target = the real sprite; it
    learns to correct "our style" into Game Freak's, and at use time it gets our draft, which always exists. Candidate
    for the next round, together with style tags (Game Freak vs fan-made: half the followers and ~40 % of icons and
    backs are fan-made, so the model learns an average style) and a style reward.
  - **End of the run (2026-10-11 23:45 JST, Arvind's choice):** stopped after checkpoint 5250 (1.4 passes) because he
    wants to try style references and better references first; the back was not trained this round (its data stays
    ready). Judge per checkpoint: 750 0.200, 1500 0.177, 2250 0.184, 3000 0.207, **3750 0.256** (recog 0.32), 4500
    weaker by Arvind's eye. Stop order on the pod: kill the queue script first (else it starts the back), then the
    training; tar the output (1.35 GB: 7 checkpoints x 152 MB + 192 pictures), download, check the size to the byte,
    then terminate. Pod time ~7.6 h, about **12.50 $**. Results: Legion `pod2_out\pkmn_follower_v5`.
  - **Lesson (Windows SSH again):** an ssh started inside an interactive SSH session on the Legion can hang even with
    `-n` (a `stat` call hung twice); started as its own process (Invoke-CimMethod) it works, and `cmd /c ssh ...` works.
    For the last critical steps fall back to the Mac, which never hung.
  - **Lesson (Windows SSH, cost an hour of blind monitoring):** `ssh.exe` started from a console-less process (Invoke-
    CimMethod) without `-n` waits for stdin forever: fetch2 and the live judge hung on their first `ssh ... cat`. Every
    scripted ssh on the Legion now runs `ssh -n -o BatchMode=yes -o StrictHostKeyChecking=no -o ServerAliveInterval=15`.
    Check a watcher's first round actually completes, not just that it started.
- **Style references at use time, first try (2026-10-12, `v6cfg\style_tests.py`, results\style; Arvind: "show it many
  other sprites in the right style ... then we could maybe skip the LoRA"):** a 4th reference with 12 Game Freak
  followers in one grid. Plain Qwen 2.1 scored 0.01 (it drew a grid of mini sprites), LoRA 3750 + the sheet 0.205 vs
  0.243 without (the LoRA never saw a 4th image), LoRA 4500 0.246. **The test broke Qwen's own rules**, found afterwards
  in the official Qwen 2.1 edit prompt enhancer's system prompt (ComfyUI template `image_qwen_image_2_1_image_edit.json`,
  copy in the session scratchpad) and the template notes: refer to images as `<image1>`... (we did); state each image's
  role and what is taken from each; **describe every reference individually, never several as one group** (our grid
  was one group); state requirements affirmatively (we wrote "never draw any of them"); no resolution or size in the
  prompt (the enhancer always strips them, so "32x32 pixels" is noise); image_1 is the edit target and the output
  follows its size; up to 10 references; **the negative prompt does nothing at cfg 1** (the official setting; raise cfg
  to use one); official steps 40-50 (we use 25). So "plain Qwen cannot do it" is not proven yet.
- **Style references the official way (2026-10-12, `v6cfg\style2_tests.py`, results\style2; then `style3_tests.py`):**
  plain Qwen 2.1, 40 steps, official artwork -> HeartGold front, each reference its own picture (80x80 front, nearest x8
  = 640), described one by one, affirmative wording, no sizes. First picture (Cyndaquil): the design alone + style words
  gives the illustration pixelated (design kept, not Game Freak's look); with 5 named real fronts it **draws the
  references instead of the design** (random refs: a mix of them; similar refs: Breloom, one of the five). Content
  leaks from style references. Research (a web agent, links in the session notes): QwenStyle (arXiv 2601.06202) and
  the Civitai/HF style-transfer LoRAs exist because the base edit model does not separate style from content by
  itself; their training triplets are [style ref of a different subject, content ref, target]. Next tests: the same
  without species names, and the **canvas swap** (SpriteForge's trick: `<image1>` = a real sprite of a similar
  species, `<image2>` = the design, "replace the creature in `<image1>` with the one from `<image2>`, keep `<image1>`'s
  pixel style", at 16x so the grid lines up with the VAE).
- **Results of the style tests (2026-10-12, plain Qwen 2.1, no LoRA; sheets in results\style2..6, `peek.py` on the Mac):**
  - Style references described one by one still **leak content**: with names it draws a reference (Breloom, Magby),
    without names a hybrid (Lickitung with a platypus tail, Magmar-Kadabra). A blur-word negative at cfg 3 does not stop it.
  - **Canvas swap** (`style3_tests.py`): the right creature every time (recog 0.74, DINO 0.74 on Cyndaquil / Jigglypuff /
    Kadabra; "looks like the donor" 0.002), on the 16 px grid for Waffy and Jigglypuff; Cyndaquil got the donor Bagon's
    helmet, Kadabra ignored the grid and stayed the artwork pixelated.
  - **Arvind's "style of + the reference's NAME in the negative" (cfg 3)** (`style4_tests.py`): no leak at all (the
    negative name works), but the result is the artwork pixelated.
  - **Arvind's verdict: "far too close to the original art, as if it does not dare to try anything; they just get
    pixelated; and the pixel size is wrong."** Measured (colour run lengths): our outputs had **1.5-3x too many pixels
    across** (Cyndaquil style-of ~80x100 sprite px, real ~40x50; Jigglypuff swap ~55x58, real 36x39; Kadabra swap ~170x150,
    real 60x72). An edit model is trained to keep its input, so with the design in charge it keeps the art's pose and
    detail. Forcing the 16 px grid with SigmaPixelLock fixes the pixel size but not the "copy the drawing" habit, and a
    palette taken from a design with a background (Waffy's blue snow) bleaches the colours (`style6_tests.py`).
    Taking the pose from the real sprite was rejected by Arvind: the creature should stand as it wants; the problem is
    that it keeps the rest of the drawing (lines, shading, small details).
  - Conclusion: plain Qwen with references gives grid and size (canvas) but not Game Freak's way of redrawing; that is
    what the LoRAs learn. Next: the free pipeline with the LoRAs we have (below).
- **The free pipeline (night 2026-10-12; Arvind's goal: "without spending money, a relatively safe pipeline that gives
  good results through the whole process; the existing LoRAs may be used").** All on the Legion, about 8 minutes per mon.
  Scripts `v6cfg\pipe_v1.py`, `pipe_v2.py`, `pipe_finish.py`, `colour_rule.py`, `back_size.py`, `front_place.py`;
  results in `results\pipe_v1`, `pipe_v2`, `pipe_final`. One design picture in, every sprite out:
  1. **front**: plain Qwen 2.1 with the approved Oct 5 DS prompt (`ds_pixel.FRONT`): the design + a silhouette guide at
     the stage's size (the canvas enforces size, place and grid), read on the 96 grid, best of 3 by
     `ds_pixel.front_score`. One seed in three copies the grey guide as the creature; the score throws it out.
  2. **back**: back v4 (front 8x + design), checkpoints 1000 / final x LoRA strength 1.0 / 0.75 x 2 seeds; the pick
     wants the area real backs have (595 HeartGold sets: **back area = 0.584 x front area + 1633**, median error 11 %), a
     flat cut, no face and no copy of the front; then lifted so the cut sits at row 71 (the real median). v1 (fixed
     area target, one strength) drew them far too big.
  3. **follower**: follower v5 step 3750 (front + sheet with our back and the design + the predicted box), down / up /
     left x 2 seeds, best by box fit + the two frames agreeing; right = left mirrored.
  4. **icon**: icon v6 A step 2000 at 0.75 (front + sheet with our back, our follower's down frames and the design + the
     predicted box), best of 3 by box fit + likeness to the front.
  5. **finish** (no drawing): the **game's colour rule**, learned on 468 artwork -> HeartGold front pairs (per quantile of
     lightness and chroma): Game Freak's sprites are more saturated (chroma +10-20) with darker shadows and outline than
     the artwork. On the held-out fronts it moved our colours 40 % closer to the real ones (chroma distance 18.5 -> 11.2,
     lightness 9.1 -> 7.5). The front's old -> new colour table is applied to back, follower and icon (they are all
     already in the front's palette), so a mon's sprites share one palette. Then the front is placed like real ones
     (595 fronts: **bottom row = 0.491 x height + 39.6**, median 14 empty rows below; ours stood on the last row).
  Every pick is a rule taken from real HeartGold data, so a bad seed loses instead of reaching the group.
  **Numbers (8 held-out species from their official artwork, judge = classifier x DINOv2 vs the real sprite):**

  | | front | back | follower | icon |
  |---|---|---|---|---|
  | v1 | 0.701 | 0.271 | 0.229 | 0.541 |
  | v2 (back area rule, strength 0.75 candidates) | 0.701 | 0.257 | 0.257 | 0.520 |
  | v2 + finish (colour rule, placement) | 0.664 | 0.260 | 0.236 | 0.599 |
  | from the TRUE front (oracle) | - | 0.233 | 0.258 | 0.435 |

  The front stage costs nothing downstream: back / follower / icon are as good from our front as from the real one. The
  colour rule moves DINO up (closer to the real sprites) and the classifier a little down. The back LoRA is the weak link.
  **Picking without truth (`select_study.py`, on v2's kept candidates):** "identity" = cosine of the classifier's 1025-way
  probabilities, candidate vs our own front (the same creature recognised in both, whatever it is, so it works for a new
  mon). Mean judge of the pick: back 0.27 by my rules -> **0.38 by identity** (best possible 0.41, average candidate 0.21);
  follower 0.28 -> **0.31** (= best possible); icon: rules 0.54 (= best possible), identity 0.50, both 0.54. DINO to the
  front alone picks badly (0.16 on backs). So identity is the picker, with a copy-of-the-front penalty kept for backs
  (a copied front would look the most "identical"). Pipeline v3 = v2 + this picker + 12 back candidates + the finish built in.
  **v3 (final sprites):** front 0.664, **back 0.320**, **follower 0.289**, **icon 0.588** (v1: 0.701 / 0.271 / 0.229 /
  0.541). No back is a copy (DINO back vs own front 0.40-0.72; real pairs ~0.6-0.7). By eye: Waffy's back is now a real
  over-the-shoulder back close to the approved one; followers look like the game's; Tentacool's back came out a flat sliver
  and Kadabra (the artwork's busy pose kept by the front) stays the weakest. About 3 minutes per mon once the candidates
  exist, 8 from scratch.
  **Our own mons (`pipe_ours.py`, results\pipe_ours; one clean concept picture each, front size 68/74/78 from the dex):**
  Erobi and Waffy good in every view; Autuman, Leafing, Stonma and Janenon good fronts, followers and icons, odd backs
  (Leafing's a green lump, Stonma's a grey slab). **Torchbat failed at first**: its concept is a thin line drawing and all 4
  seeds copied the grey guide as the creature, and the chain carried the grey through every view. Fix, now in the front
  stage: a **safety gate** - if no front scores 2 or more, a second round with an almost-white guide (fill 246, edge 190),
  and a `NEEDS_A_PERSON.txt` flag if that fails too. Torchbat's second round scored 6.8-7.9 and came out in colour, but a
  rough sketch still gives a rough front (and weak back/icon): sketches should go through the family's step 1 (sketch ->
  official-style artwork, approved by the group) before the chain.
  **Weakest link: the back.** Fronts, followers and icons are dependable; backs are right for round, simple bodies and odd
  for unusual shapes. Free next steps: more back candidates (identity pick scales with N), the Oct 5 plain-Qwen back
  (ds_pixel.BACK) as extra candidates, back v3 1000 as another source. Paid only if those fail: back v5 at 16x (data ready).
  **Back study (`back_study.py`, results\back_study):** 26 candidates per mon (back v4 1000/final x 1.0/0.75 x 5 seeds +
  back v3 1000 x 1.0/0.75 x 3 seeds, v3 on white references as trained), identity pick: held-out backs **0.320 -> 0.416**
  (best possible 0.498; Tentacool 0.00 -> 0.55 with its red eyes, Kadabra 0.13 -> 0.44, Diglett right size). v4 is the
  better source on average (0.229 vs 0.201 per candidate) and gives the best candidate 7 of 8 times. On our own mons the
  identity pick is noisier (the classifier has never seen them): Autuman's back got better, Waffy's and Erobi's worse than
  v3's pick. So for a new mon the pipeline should show the group its **top 3 backs** to choose from, and decide the rest
  (front, follower, icon) itself.
- **Arvind on the free pipeline (2026-10-12 morning): "does not look good enough."** My reading: the front is the chain's
  foundation and the one stage no LoRA has learned; plain Qwen gives the artwork pixelated, not a Game Freak redraw, and
  every later stage inherits that (the numbers missed it; his eye and the style detector did not). **art -> front v6**
  (`v6cfg\build_art2front_v6.py`, `audit_art2front.py`, `filter_art2front.py`, config `v6cfg\art2front_v6.yaml`, data
  `data\v9\art2front`): round 1's never-trained art2front B idea (a style sheet of real sprites as a trained-in second
  reference) rebuilt clean: Game Freak Gen 4 fronts only (DP / Pt / HGSS, species 1-493, base forms, held-out never),
  near-duplicates dropped (884 left of 1435), style sheet = 6 real HGSS fronts of the most similar OTHER species (DINOv2
  on the artwork, relatives left out). **The audit found wrong palettes in some DP / Pt sets** (Lickitung's DP and Pt
  fronts are red-orange, the HGSS one pink): versions whose colours differ from the species' HGSS front were dropped (38),
  plus the 5 % of pairs with the most recoloured modern artwork (32) and Spinda (the game paints its spots): 813 examples.
  Training on the Legion: 640, rank 32, lr 5e-5 cosine, EMA, 1500 steps, 8.8 s/step (about 3.6 h). Stopped at step 1186
  for Arvind to judge 500 / 750 / 1000 (`v6cfg\eval_art2front.py`, results\art2front_v6\eval.png): on the held-out species
  the judge is the same as plain Qwen (step 750 0.696 vs 0.701) and the fronts come out far too big (no size guide: the
  edit model keeps the artwork's layout, as in the style tests), still close to the artwork. On OUR mons it redraws more:
  Torchbat became a creature instead of a traced line drawing, Janenon and Stonma kept their colours (plain Qwen turned
  them grey), Waffy at 1000 turned into a new three-quarter pose. That fits Arvind's observation (Waffy took on the style
  best): a creature the base model has never seen leans on the LoRA, a known one on the model's memory.
- **Lesson (Legion memory):** the first start crashed while quantizing (0xC0000005) and PowerShell could not even start:
  17 orphaned multiprocessing workers from earlier runs (parents dead since 6-11 October) held about 49 GB of committed
  memory. `pod2\kill_orphans.ps1` kills only workers whose parent is gone (commit free 19 -> 48 GB). Run it before every
  Legion training.
- **"Too many references?" (Arvind, 2026-10-12: on RunPod, Waffy took on the style best).** Two explanations: the
  references (artwork, HOME render, back, icon) carry detail and rendering the model copies, or the base model pulls the
  real species towards how it remembers them (Waffy it has never seen). Test queued after the front eval
  (`v6cfg\refs_test.py`): follower v5 and icon v6 A on the 8 held-out + Waffy with the sheet blank / artwork only / full,
  same seeds and boxes. If fewer references look more like Game Freak, cut them in the chain.
- **Sketch -> artwork by canvas swap? (2026-10-12, `v6cfg\sketch_test.py`, results\sketch_test; Arvind's idea):** 7 rough
  sketches of ours, plain Qwen 2.1: the sketch alone + "redraw as official artwork" vs canvas swap (the most similar real
  official artwork as `<image1>`) vs swap + the donor's name in the negative (cfg 3). **Neither redraws**: the edit model
  keeps the sketch's lines and pose and only fills it in. Alone it guesses colours (Stonma and Nukfae came out red); with a
  donor it takes the DONOR's colours (Stonma green like Ludicolo, Freezrick yellow like Plusle). DINOv2 picks poor donors
  for line drawings (Geodude for Janenon). For line sketches the colours must come from words (the dex's `look` text the
  Oct 3 `official_front_gen4` prompt uses) or from the group, not from a reference picture.
- **Style detector (2026-10-11, `v6cfg\style_detector.py`, results\style\detector.json):** frozen DINOv2 + logistic
  regression, trained and tested on different species, tells real HeartGold icons from our icon v6 A/Aps pictures **on
  greyscale** with 94.3 % accuracy (AUC 0.991; 1008 real, 1720 ours, 968 species). So the gap is not only the palette:
  the drawing itself (shapes, outline, shading) gives ours away. Its "looks real" probability can rank best-of-N.
- **RunPod session 3 (2026-10-12; Arvind: "front LoRA at 16x with enough epochs; better tags; a size guide; keep it cheap
  without losing quality"; then "the backs should get the same smart ideas").** Reviewed against every front/back lesson
  first; changes from that review: the front size guide back to 1280 (same size as the target, the round-2 review; I had
  shrunk it to 640 to save money), the style sheet blank in half the examples (Arvind's 10 Oct hybrid worry + his untested
  "too many references"; compare with and without at use time) and 3 extra progress pictures without it, steps from the
  evidence that our LoRAs peak around 1-1.5 passes (front 1800 = 2.2 passes, back ~1.8 passes, saves every 300).
  **Back v6** replaces back v5 (`v6cfg\build_back_v6.py`, `data\v9\back6`): Game Freak Gen 4 backs AND hg-engine's
  fan-made backs (Arvind: "keep them, they are made very well"), the DP/Pt palette check, the sheet = artwork + ONE overworld frame seen from behind (Arvind) and nothing else
  (no HOME render: never exists for our mons; no icon: made after the back), the front dirty in 30 %, tags as front v7,
  the 1280 box with the heavier flat-cut line.
  - Pod `08cguk85555g3z`: RTX PRO 6000 Blackwell **Server Edition** (600 W; round 2's Max-Q was 300 W), Community,
    1.69 $/h, started 15:02 JST. Upload 387 MB from the Legion checked to the byte; models fetched in parallel (6 min).
    Front smoke: 0 errors, 0 OOM skips, 4 pictures, buckets 1280x1280 (813), weights moved, **5.6 s/step** (back 16x on the
    Max-Q was 7.2). The back v5 smoke was stopped (back v6 replaces it). Front training started 15:40 JST.
  - Lesson repeated: `pkill -f 'cfg/dash.py'` inside an ssh command that itself contains `cfg/dash.py` killed the
    session (and the dashboard); kill by pid from `ps | grep '[p]attern'` instead. Then the same again with
    `ps | grep '[c]fg/dash.py'` in a command that also STARTED `cfg/dash.py` (the regex matched the start command):
    restarts now go through `cfg/restart_dash.sh` (pgrep on the exact command, from a script file).
  - **Front v7 result (1800 steps, 3 h 25 min):** the progress pictures (WITH the similar-species style sheet, seed 42)
    turned into **merges**: Waffy with a Charmander tail, Erobi a Togepi mix, Autuman drawing the whole sheet into the
    picture, Leafing / Stonma hybrids, Tentacool with red balls; worse at 1200 than at 600 (Kadabra and Cyndaquil fine at
    600, broken at 1200). Arvind: "it cannot take ONLY the style from the reference sheets". The loss went 0.081 -> ~0.06
    in 150 steps and stayed flat: it rewards single denoising steps against the true sprite, so it never directly punishes
    copying the sheet. **With a BLANK sheet and 3 seeds** (free test on the Legion, `v6cfg\eval_front_v7.py`) step 600 has
    no merges: Cyndaquil, Houndour, Bronzor, Jigglypuff, Diglett look like real HGSS fronts at the right size; Erobi and
    Autuman good in all seeds, Leafing / Stonma / Torchbat (a real creature for the first time) / Waffy good in one seed of
    three. Seeds vary a lot, so best-of-N with a picker matters. The dashboard (sheet mode, one seed) was misleading.
  - Research (agent, 12 Oct): references must not be able to carry a creature (fragments, shuffled), pick references
    UNLIKE the target, effective batch 4-8, frequent checkpoints chosen on several seeds. **ai-toolkit's EMA has no
    warm-up**: at decay 0.999 the step-600 weights are still 55 % the initial ones (0.999^600), so keep 0.99.
  - **Front v7c = Arvind's PUZZLE** (`v6cfg\build_front_v7c.py`, `data\v9\front7c`): `<image2>` = this creature's OWN sprite
    cut into 8x8 pieces, ~70 % kept, rotated / mirrored, scattered (colours, cel shading and pixel style, not the shape); in
    half the examples cut from a DIRTIED sprite (colour shift, blocky, too many / too few colours), the way a new mon's
    puzzle is cut from our draft front; two puzzles per example, blank in 15 %; effective batch 4, lr 1e-4, saves every 50.
    Progress pictures use puzzles of the free pipeline's DRAFT fronts (honest), plus Cyndaquil / Kadabra with the real
    answer's puzzle (the ceiling). Queued after back v6 (`cfg/run_queue3b.sh`). A mosaic of OTHER species' fragments
    (v7b) was built first and dropped (Arvind: "it looks like random Pokemon in there").
  - **Back v6** started 19:05 JST (caching 1115 new captions ~14 min, 13 step-0 pictures), 5.7 s/step, buckets
    1280x1280 x 1115, 0 OOM; up to 3300 steps, Arvind stops it once it is saturated. **Step 0 vs 600** (sheet per mon:
    front | sheet | picture | truth, made on the pod by `back_sheet.py`): at step 0 the base model only pastes the sheet
    (follower frame + artwork side by side, small); at 600 it already draws big backs cut flat by the bottom edge (Haunter,
    Tentacool, Leafing, Waffy the most convincing), but several still draw two things side by side (what is left of
    pasting the sheet) or break into fragments. Arvind: "it learns much more than I thought, I see the direction".
  - **Free post-processing of front v7** (`v6cfg\post_fv7.py`): unfake (dominant colour per 16 px cell, auto palette,
    morph + jaggy clean-up) + loose pixels removed takes the colour count from 15-30 to 5-14 (real HGSS about 10) and
    cleans outlines; some seeds drop too far (Janenon 4 colours) and dirt already in the picture stays, so the picker still
    chooses the seed. Arvind: "hit or miss, but it will work; with the right tags and good reference pictures it will be
    good".
  - **Our mons' inputs were wrong** (found 12 Oct): (1) the stage tag was guessed from base stats and worded "a first-stage
    Pokemon", a phrase the LoRA never saw (training says "... that evolves" / "a middle evolution" / "a fully evolved
    Pokemon" / "a Pokemon that does not evolve"), and Erobi was called first stage though it does not evolve: tags now come
    from `data\species\*.yaml` (who evolves into whom), heights where we have them (5 of 7 have none in the dex; Torchbat's
    0.8 m is on its own sheet). (2) The artwork: Waffy's still had its snowy ground and background (removed with base
    Qwen-Image 2.1 edit, transparent output, `v6cfg\refs_clean.py`), Erobi had a stray line under it that made its box
    wrong, and Janenon and Torchbat were paint sketches although `assets\concept-art` holds far better pictures (Janenon on
    its card 259, Torchbat's coloured sheet 469): cut out, background removed, largest blob kept, framed like the training
    art (fit in 560 on 640). Arvind had said Janenon and Torchbat were bad "probably because of the art"; he was right.
  - **Fine-tuning at use time** (`v6cfg\tune_front.py`, free, after the strength 0.75 test): new tags + new art + 40
    sampling steps (Qwen's advice 40-50; we used 25) for our 7; the 8 Game Freak mons get only the 40 steps, so they show
    that effect alone against the truth. Checkpoints 600 and 900, seeds 1-3, unfake + loose pixels. Then the same at
    strength 0.75 (`TUNE_STRENGTH`), and `v6cfg\waffy_show.py` (Arvind: "one Pokemon, different seeds, variations and
    pipelines"): Waffy, 600 / 900 x 1.0 / 0.75 x 8 seeds, raw and unfaked, next to the old runs and the group's front.
    **Result at 600 (strength 1.0):** the reference art is what matters. Janenon now looks like the creature (the hair
    cannon with the pink muzzle and the small purple body) instead of a scribble, Torchbat is a clean coloured sprite with
    flame ears in all three seeds, Waffy has no snow; the 8 Game Freak mons (40 steps the only change) look the same as at
    25 steps, so 25 steps is enough; the corrected tags changed nothing visible (Erobi, Autuman, Leafing as before).
    **At 900 (strength 1.0) it is overtrained**: Kadabra in pieces, Autuman exploding into leaves, Janenon / Torchbat
    messy, a Cyndaquil merge. **Best so far: step 600 at strength 0.75 with the new inputs** (Janenon and Torchbat good
    in all three seeds, Waffy clean); seed 1 draws Leafing and Stonma tiny at every setting (a seed effect, the picker's
    job). At 0.75 step 900 is as steady as 600 (the lower strength hides the overtraining).
  - **Sampler knobs** (`v6cfg\sampler_grid.py`, front v7 600 at 1.0, Cyndaquil / Kadabra / Waffy / Torchbat / Janenon x
    2 seeds; Legion seconds per 1280 picture): **8 steps** (28 s) breaks up (Kadabra in fragments), **12** (33 s) nearly
    there, **16-20** (39-44 s) look like 25 (51 s): 16-20 is enough. **cfg 2.5 + a negative prompt** (95 s) is the one
    knob that changes the look: bolder dark outlines, cleaner, more saturated colours (Cyndaquil, Torchbat, Janenon
    closest to a real sprite), Kadabra in a different, more coherent pose. **euler_ancestral** (fresh noise every step,
    the nearest thing to "temperature") gives more varied seeds, useful for best-of-N. dpmpp_2m, res_multistep, the beta
    schedule and shift 1.5 / 3.1 / 6 change almost nothing.
    Lesson: the first start waited 50 min for a line that was already in the log, because PowerShell's own redirection
    (`*>>`, `Out-File`) writes UTF-16; a Python wait on a PowerShell log must decode by its BOM.
  - **Strength 0.75** (`eval_front_v7_s075.py`, old inputs): far steadier, nearly all three seeds usable per mon (Erobi,
    Autuman, Cyndaquil, Houndour, Bronzor good in all); the price is that it follows the drawing more (Kadabra in the
    artwork's pose, not the HGSS one; Haunter greyer). 600 slightly cleaner than 900. Arvind: "a lot of good in that".
  - **Back v6 at 1200 / 1800**: 1200 has big backs cut flat and almost no fragments, but Cyndaquil, Diglett and Kadabra
    still drawn twice side by side; at 1800 only Diglett is double, Cyndaquil and Kadabra are one creature built like
    the real back. Arvind's rule from this: **never two pictures inside one input** (the sheet's two panels are what it
    pasted as two creatures). ai-toolkit takes a LIST as `control_path` (more than 3 references in training; the
    progress pictures take at most 3), so the next back can get front, artwork and follower frame as separate images.
  - **Front v7d = Arvind's REAL BACK idea, replaces v7c** (`v6cfg\build_front_v7d.py`, `data\v9\front7d`, queued on
    the pod by `cfg/run_queue3c.sh` after back v6; `cfg/skip_front7c` set; Arvind: "we drop v7c"): `<image2>` = the
    creature's own back from the same game as the target front (all 813 matched exactly). The back is a TRAINING aid
    only (Arvind: "we have every sprite of the real mons, so it can learn to replicate the style; I hope it has
    understood it when our fakemons are made, no catch-22"; "the dirty back has not helped us so far"): every example
    twice, once with the clean real back, once with `<image2>` empty, which is how our mons are drawn. My first build
    (dirtied backs, back v6's backs at use time) was dropped for that. Progress pictures: the 8 held-out and our 7 with
    the new inputs and no back, + Cyndaquil / Kadabra with the real back. 400 steps at effective batch 4 (one pass);
    no step-0 pictures (`skip_first_sample`: they only show the base model, ~8 min). Back v6 was stopped at 2409 (Arvind:
    "2400 stagnates"; 1800 ~ 2400) and v7d started at once (23:43 JST).
  - **Unattended end (Arvind asleep: "VERY IMPORTANT that you terminate the pod when training is done")**, three layers:
    (1) the Legion (`pod3_src\fetch_v7d_flag.ps1`) waits for "all done 3", fetches the v7d archive (3 tries, size
    checked), puts every checkpoint in ComfyUI as `fv7d_<step>`, checks back v6's fetch, then touches `cfg/fetched_ok`
    on the pod; (2) the pod (`cfg/selfterm.sh`) waits for the end (or 10 min with no training process), then for
    `fetched_ok` (up to 2 h) and terminates itself with `runpodctl remove pod $RUNPOD_POD_ID` using the container's own
    key from `/proc/1/environ` (not in an ssh shell's environment; that key may not read pods, `get pod` says
    Unauthorized); with no fetch confirmation it only STOPS the pod (GPU billing ends, files kept); (3) a watcher on the
    Mac wakes me to check with get-pod and delete it myself if it is still there. **It worked**: v7d ended 02:59 JST,
    the Legion had the archive (1.53 GB, size checked) and every checkpoint in ComfyUI at 03:02:30, and the pod was gone
    (get-pod 404, list-pods empty) a minute later: `runpodctl remove pod` with the container's own key DOES terminate
    the pod. Round 3 cost about 20 $ (12 h at 1.69 $/h).
  - **Front v7d result** (progress pictures, one seed, `v6cfg\front_sheet_v7d.py`): with `<image2>` empty, as our mons
    are drawn, **step 200 is the cleanest** (= 800 examples, near where front v7 peaked at 600); at 300 / 400 it grows
    noisy (Erobi fuzzier, Autuman cluttered, Stonma falls apart, Tentacool worse). Janenon, Torchbat, Waffy, Leafing good
    at 200. With the REAL back it clearly uses it: Kadabra at 300 takes the real sprite's pose and brown body,
    Cyndaquil's colours come closer to the truth.
  - **Front v7d vs v7, no back, strength 1.0, 3 seeds, all 15 mons** (`v6cfg\eval_v7d.py`): v7d at 150 / 200 / 250 is
    far steadier than v7 600: the three seeds nearly agree for every mon and none breaks (v7 600's seed 2 broke Haunter,
    Tentacool and Kadabra); 150 ~ 200 ~ 250. It keeps closer to the drawing's pose (Kadabra still in the artwork's pose,
    not HGSS's). Whether that comes from the back or from the shorter training cannot be told apart from this; either
    way v7d 200 at full strength is as steady as v7 600 at 0.75. Seed 1 still draws Leafing / Stonma tiny.
  - **Torchbat, 6 ways x 8 seeds** (`v6cfg\show_mon.py torchbat`, Arvind: "make another one of a character"): every
    way is a big step up from the sketch-based run. v7 600 at 0.75 and v7d 200 at 1.0: all 8 seeds faithful and alike;
    **cfg 2.5 + negative prompt (at 0.75) gives the most sprite-like look** (bold dark outline, flat saturated colours)
    in all 8 seeds, at twice the time (~90 s); at strength 1.0 with cfg 2.5 the poses wander (one dark broken seed);
    euler_ancestral is softer and more varied. Candidate recipe: v7d 200 or v7 600 at 0.75, cfg 2.5 + negative,
    16-20 steps, 4-8 seeds, unfake + loose pixels, then the picker.
  - **The recipe on three new mons** (Arvind picked #069 Octopearl, #073 Leadling, #042 Gortiki; `v6cfg\refs_clean2.py`
    then `v6cfg\show_new.py`, 20 steps, 8 seeds, ways A = v7d 200 at 1.0, B = v7 600 at 0.75 + cfg 2.5 + negative,
    C = v7d 200 at 0.75 + cfg 2.5 + negative). Inputs: Gortiki cut from its card 234 by base Qwen (with torch and smoke),
    Leadling from its pixel sheet 452 (no shadow, no pebbles), Octopearl only has a marker sketch (573): base Qwen with
    the colours in words made it cleaner but kept the sketch's look. Results: **Leadling C 8 of 8 like real HGSS
    sprites**; Octopearl recognisable in all 24, B the most sprite-like, its face still sketchy (the input); Gortiki (fire,
    smoke, torch) varies most: B steadiest, v7d (A, C) draws it tiny in 2-3 seeds of 8, and one B seed drew the size
    box as a black frame. So cfg 2.5 + negative wins on all three; the picker must reject tiny sprites (box fill),
    drawn frames and fragments.
  - **Reading a picture's style (Arvind's /describe question):** a battery-frog picture he showed looked like official
    art; its prompt was not in his ChatGPT export (which keeps no image-tool prompts and ends 2026-07-08). Described by
    eye instead: thin outlines in darker shades of each fill colour (not black), soft airbrushed cel shading with one
    shadow tone, faint watercolour texture, a thin white glow round the silhouette, plain white background. As a style
    prompt on Octopearl's sketch (`v6cfg\style_sugimori.py`) it softened the look but kept the sketch's shapes: an EDIT
    model keeps its input. `v6cfg\sketch_methods.py` tests seven ways to loosen that on four sketches, three of which
    have a finished picture made from them (Torchbat 470 -> 469, Janenon 262 -> card 259, Erobi 396 -> 397): edit,
    blurred sketch, white canvas + sketch as reference, text only, img2img at 70 % noise, text + sketch "only as an
    idea", the same with the sketch at 384 px.
  - **Followers, measured on 481 real HGSS sheets** (`v6cfg\follower_frames.py`): the right-facing frames are the
    mirrored left ones in 96 % of species, so "right" need not be trained; but the two walking frames of a direction
    differ in ~19 % of pixels (legs move) and are never just a 1 px shift, so each direction still needs both: 6
    pictures to make, not 8. Arvind's plan: one frame per output, the other frames of the same mon as separate inputs;
    at use time make "down" first, then the rest one by one from the ones already made. Icon: no more training, improve
    it for free.
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

## Status 2026-10-13 (focus: in-game sprites that show OUR mons in the Gen 4 style)

- **Front: good with a good input.** Recipe: front v7 600 at 0.75 or v7d 200, cfg 2.5 + negative, 16-20 steps, 4-8
  seeds, unfake + loose pixels. Leadling 8/8, Torchbat, Janenon, Waffy, Erobi, Gortiki (B) good. To do: an automatic
  picker (reject tiny sprites, drawn size boxes, fragments; pick the best of 8); size (the box is not always obeyed);
  pose (it follows the drawing; real HGSS fronts stand in a three-quarter battle pose); the game format (at most 15
  colours + transparent, ONE palette shared by front and back, a shiny palette; `scripts/ds_pixel.py` already maps the
  back onto the front's palette).
- **Back: back v6** (1800 / 2100 / 2400 on the Legion as `bv6_<step>`) learned big backs cut flat; Diglett still double,
  Autuman messy; not yet run on our new fronts. Next training: front, artwork and follower frame as separate pictures.
- **Follower:** untouched this round; first a free baseline of follower v5 on the new fronts, then follower v6 (3
  directions x 2 frames, one frame per output, the other frames as inputs; paid).
- **Icon:** good enough (Arvind); improve for free (post-processing, the front's palette).
- **Input art:** finished art or a pixel render goes straight to the sprite recipe (Arvind: "the art step is only needed
  for mons with an unfinished sketch"); cut-outs from cards and background removal work (base Qwen, transparent);
  rough sketches -> Q1 (img2img 85 % + cfg 2.5 + negative + shape words); clear sketches -> being tested (keep the pose,
  official lineart); an inventory of every mon's concept art is being made.
- **Gap:** no new mon has gone the whole way (front -> back -> follower -> icon -> game files). Order proposed: front
  picker, back v6 on the new fronts, shared palette / game format, one mon (Leadling) fully into the game, follower v6,
  then DPO.
- **The whole way, first time** (Arvind: "pick a random Pokemon and test"; drawn: Blazterra #009, Fire/Flying, the last
  of the Torchbat line; `v6cfg\e2e_front.py` + `v6cfg\e2e_chain.py`, all free on the Legion, ~45 min): its sheet 378 cut
  out by base Qwen -> 24 fronts (A / B / C x 8) -> **the cheap picker** (hard checks: box fill under 0.5, over 6 % loose
  pixels, a drawn frame, over 24 colours; score = DINOv2 agreement with the other survivors + likeness to the artwork +
  box fill - touching the edge; no training, seconds on the CPU): picked B 6, B 5, A 5, sensible, it marked down the odd
  blue eye and the wings cut at the edge -> back v6 (1800 / 2100 / 2400 x 3 seeds; 2100 seed 3 picked): a real-looking
  back, wings spread, cut flat -> follower v5 (weak: the up and down frames look alike) -> icon v6A (a messy blob) ->
  front and back on ONE palette (8 colours) -> a mock battle screen that reads as Gen 4. Verdict: front and back are
  close; follower and icon are the weak end (follower v6 is planned last; the icon to be improved for free).
- **Arvind's review of the Blazterra chain:** B's fronts are superior (the picker's A5 at no. 3 was wrong), the black
  outline is too thick, the icon is surprisingly bad ("the icons in the PC box on 6 Oct were good").
  - **Icon:** the 6 Oct icons came from `pkmn_icon_edit_v2` with ONLY the approved battle front as input (8x on white) and
    one plain instruction (`legion_test\run.py`); icon v6A takes back + follower frame + artwork, so a muddy follower
    v5 frame made a muddy icon. `v6cfg\icon_edit_v2_test.py` reruns the 6 Oct way on the new fronts. Checked: the
    6 Oct script (`legion_test\run.py`) on the same fronts today reproduces those icons pixel for pixel (0 pixels
    different; LoRA file and ComfyUI unchanged), and on NEW fronts of the same mons (Erobi, Leafing, Stonma, Autuman,
    Waffy) it gives icons as good as on 6 Oct. So the bad Blazterra icon was (1) MY choice in the chain: icon v6A with
    the muddy follower frame in its sheet (copied from pipe_ours) instead of icon_edit_v2 with the front only, and (2) a
    hard design (huge wings, fire, a torch) for 32x32; Gortiki and Octopearl are hard the same way. Use icon_edit_v2,
    front only, in the chain. CORRECTION: the PC box Arvind loved (sent ~10 Oct) is the SEED 2 icons of that run
    (`legion_test\*_icon_2_px.png`, pixel-matched 100 % on all 8); I first compared against seed 1, which is clearly
    worse. Seeds matter a lot for icons (seed 2 was bigger and bolder for every mon, old and new fronts alike).
    **The exact PC box recipe** (`legion_test\run.py` via `after.ps1`, 6 Oct; checked again 14 Oct when Arvind asked
    whether a special prompt or extra steps were used): the approved front (`legion_test\fronts`) pasted on WHITE, 8x
    nearest to 640, RGB; `comfy.generate` -> `comfy.workflow` with the default `ref_resolution=1024` (ComfyUI scales the
    reference to ~1 MP, off the pixel grid: the 7 Oct commit made this optional for later LoRAs, but the PC box icons
    were made WITH it); only the one-sentence prompt "Turn the Pokemon battle sprite in the reference image into its
    party menu icon from Pokemon HeartGold: the same creature as a 32x32 pixel art icon, facing left, with a one-pixel
    dark grey outline, on a white background."; 512x512, 25 steps, cfg 1, euler / simple, `pkmn_icon_edit_v2` at 1.0;
    seeds 1 and 2, seed 2 picked; read at the cell centres (median of the middle 40 %, near-white = see-through). No
    other post-processing: the box sheet (`compare\make2.py`) only pastes the 32x32 icons. `icon_eval.py`'s "v2" column
    reproduces it pixel for pixel (all 8 mons identical), so v7c is compared against the real PC box recipe.
  - **Icon knobs** (`v6cfg\icon_play.py`, icon_edit_v2, seeds 1-3; Blazterra, Leadling, Octopearl, Stonma, Leafing,
    Autuman): strength 0.8 / 1.2, 15 / 40 steps, the artwork as `<image2>`, and a second edit on the result (50 % noise)
    change little. **The canvas swap wins: start from the front shrunk to icon size (figure fitted in 28 px on the 32
    grid, feet low, 16x on white), 70 % noise, the front as reference**: every part kept in all seeds (Leadling's
    skull, boulders and feet; Blazterra's spread wings; Octopearl's cap, tentacles and tube; Autuman's whole body),
    where the plain recipe lost limbs (Arvind: "Leadling seed 4 lacks arms and legs"; "Blazterra only seed 2, and it is
    borderline"). Character consistency comes from the start picture, the icon style from the LoRA. Arvind: "it worked,
    but the colours do not fit icons"; "they get so small". `v6cfg\icon_play2.py`: the start front shrunk to FILL the
    cell (32 wide or 30 high, feet on the bottom row), 60 / 70 / 80 % noise: full-size icons with every part for all six
    (Leadling, Stonma, Leafing, Autuman whole); 60-80 % differ little; colours stay the front's (darker, more shading than
    real icons), still to solve. Arvind: "Autuman V0 seed 2 is a splendid example" (= the PC box icon).
  - **Pose and size** (Arvind: "compare with Charizard"; "check Mega Charizard X / Y"): real fronts fill the frame:
    Charizard 76x79, Mega X 80x80, Mega Y 80x80, Crobat 78x65, with wings raised and an upright body; real icons
    32x25-29. Blazterra's front is 78x46 (wings spread flat as in its artwork) and its icon 30x19. Cause: the size box is
    predicted from the ARTWORK's aspect ratio, so a flat drawing gets a flat box; Game Freak re-poses big creatures to
    fill the square. `v6cfg\pose_size.py` tests a taller box (78x66, 78x78) and re-posing the artwork first. Lesson: my
    first re-pose prompt named Charizard as the pose model and base Qwen drew Charizard: never name a real Pokemon in a
    prompt that must keep our design. **Result:** a taller box (78x66, 78x78) changes nothing: with a flat artwork the
    LoRA keeps the flat pose (73-79 x 40-46). Re-posing the artwork first by a plain base-Qwen edit with the pose in
    words (P1: "wings raised high above its shoulders, half folded, standing upright, fits a square frame") gives upright,
    compact fronts (43-46 x 58-61) that keep the design; "vision only" (P2) loses the design (it drew a Charizard-like
    dragon with flame wings). So: re-pose flat drawings by edit, then set the box from the fill rule below.
  - **Size follows height** (Arvind: "big mons naturally fill the frame, not all; check height and weight"; "look at how
    much is background / transparent, not the dimensions"; `v6cfg\fill_stats.py`): fill = opaque share of the 80x80
    frame, 493 HGSS fronts: median 0.21 (10-90 % 0.11-0.41); Spearman with height 0.85, with weight 0.78. Median fill by
    height: under 0.5 m 0.12, 0.5-1 m 0.15, 1-1.5 m 0.25, 1.5-2.5 m 0.35, over 2.5 m 0.47; by stage: first 0.14, middle
    0.22, last 0.29, single 0.25. Fullest: Giratina 0.62, Palkia, Ho-Oh, Charizard 0.58; Crobat only 0.23, Pidgeot 0.43.
    Ours: Blazterra 0.26 (too little for a big last stage), Leadling 0.38 (FAR too much for a 0.5 m first stage: ~0.13),
    Gortiki 0.42, Octopearl 0.35, Waffy (approved) 0.27. So the size box should be set from a target FILL by height
    (stage when the dex has no height), not from the longest side by stage (68 / 74 / 78) nor the artwork's shape. The
    frame is 80x80 in the game; any pose inside it is allowed.
  - **Icon v7 on the Legion** (`v6cfg\build_icon_v7.py`, `pairs7`, `pod2\cfg\icon_v7_legion.yaml`,
    `v6cfg\icon_v7_train.ps1`, queued 13 Oct 15:54 behind the pose test): icon v2's exact recipe (pairs2, 3000 steps,
    lr 1e-4, rank 32) + one change: a second reference, the front shrunk to fill the icon cell at 16x, "only a guide
    for its layout and size", blank in half of the 1400 examples. v2 stays the fallback; judge v7 against the PC box.
  - **What real HGSS icons are** (`v6cfg\icon_stats.py`, 477 icons; Arvind: "teach the Pokemon icon style AND that it
    looks good and uses the space; recognisable features + the icon style"): REDRAWN, not shrunk fronts (silhouette IoU
    with the shrunk front median 0.41); fill a median 0.24 of the cell; small creatures are made relatively bigger than
    in battle (0.19 under 0.5 m vs 0.12 for the front: chibi), 0.39 over 2.5 m; figure 18x18 (small) to 24x30 (huge);
    feet on row 29 (room for the bob); icon fill follows the front's fill (Spearman 0.82), less the height (0.67).
  - **Icon v7b** (`v6cfg\build_icon_v7b.py`, `pairs7b`, `pod2\cfg\icon_v7b_legion.yaml`, `v6cfg\icon_v7b_train.ps1`,
    queued after v7): style from the real icon targets (v2's), features from the front AND the artwork (separate
    pictures; artwork empty in 20 %), space from an icon box template (real box +-1 or predicted from the front's box,
    50 / 50; fit in `data\v9\icon7b_boxfit.json`, mean height error 2.1 px). Use: best-of-8 with two cheap judges
    (icon realness: real vs our icons on DINOv2, as the front picker; recognisability: classifier likeness to the front)
    plus box fit; check that the picker chooses the PC box's seed 2 over seed 1 before trusting it.
  - **Icon v7a result and v7c** (13 Oct evening): v7a's progress pictures were best at step 500 (big, icon-like, every
    part kept); by 1000-1500 the icons shrank and lost parts. Arvind's review questions showed the design flaws: the
    guide filled the cell while real icons fill ~0.24 (so the model learned to ignore it), RGB on white, no held-out
    species, v2's learning rate copied untuned. v7a stopped at 2000. v7b was replaced before it started by **v7c**
    (`v6cfg\build_icon_v7c.py`, `pairs7c`): RGBA (white page flood-filled away), front + artwork + a box as big as the
    REAL icon (or predicted), icon masks, 41 held-out species left out (1358 examples), lr 5e-5, effective batch 4,
    EMA 0.99, 500 steps, saves every 50. **Icon judge** (`v6cfg\icon_judge.py`): realness 0.854 held-out accuracy;
    real icons: fill = 0.15 + 0.49 x front fill; it ranks the PC box's seed 2 above seed 1 for 6 of 8. Arvind: "why
    test instead of training?": the v7a evaluation was stopped so v7c trains first (20:50); `v6cfg\icon_queue3.ps1`
    finishes the v7a evaluation after v7c's (icon_eval skips what is drawn). Live page on the Legion:
    `v6cfg\legion_dash.py` at 127.0.0.1:8890 (SSH tunnel from the Mac). Precision: the Legion trains on an 8-bit base
    model with an 8-bit optimizer (the LoRA itself in bf16), as icon v2 did; quality cost expected small, speed ~5x
    slower than the pod.
  - **Icon v7c trained** (14 Oct 02:01, ~33 s/step on the Legion). The progress sheet had been empty all evening
    (`icon_progress.py` looked only for .jpg; v7c writes .png): fixed. The pictures at 0-400: Leadling and Leafing clean
    from 100, Stonma and Blazterra more icon-like over time, Octopearl loses its pink by 300-400, Autuman's cape gets
    noisy at 400.
  - **Box / no box / fill the cell, and direction** (`v6cfg\icon_tmpl_test.py`, final checkpoint, 12 mons x seeds 1-4,
    `results\icon_tmpl\`; Arvind: "what if no template? or fitting the canvas more? and they must point the right way"):
    - Real data: 79 % of the real HGSS icons face the same way as their front (837 of 1054 clear cases).
    - A box as trained: mean fill 0.36, realness 0.48, likeness 0.36, 7 of 48 the other way.
    - B no box: fill 0.42, realness 0.47, likeness 0.37, 6 of 48 the other way.
    - C box filling the cell: fill 0.41, realness 0.45, likeness 0.35, 6 of 48 the other way.
    - The box steers size only weakly: the seed decides more (seeds 2 and 4 are big and detailed in every variant,
      1 and 3 small). Without the box the icons get slightly bigger, not worse. A wrong-way icon can simply be
      mirrored; the check flags symmetric shapes (Nukfae) by mistake, so mirror only clear cases.
    - `v6cfg\icon_queue4.ps1` replaced the end of icon_queue2: the test first, then the full v7c evaluation.
  - **Reference size and the PC box conditions** (`v6cfg\icon_refres_test.py`, `results\icon_refres\`, 14 Oct; Arvind:
    "test it asap!!"). v7c was trained with ai-toolkit's `match_target_res` (references scaled to the 512 x 512 target's
    area), but icon_eval gave them to ComfyUI at their own size (resolution 0, the front at 640). Final v7c, 12 mons,
    seeds 1-4 (realness / likeness / fill / wrong way of 48):
    - v2, the PC box recipe: 0.50 / 0.34 / 0.29 / 7
    - v7c resolution 0 (as first evaluated): 0.48 / 0.36 / 0.36 / 7
    - v7c resolution 512 (as trained): 0.52 / 0.35 / 0.35 / 6
    - v7c resolution 1024: 0.47 / 0.35 / 0.41 / 3; the biggest and most detailed by eye (faces, wings, Stonma's eye)
    - v7c with exactly the PC box recipe (white, short prompt, 1024): 0.42 / **0.53** / 0.35 / **1**; the closest to
      the front and the most alike between seeds, but paler colours and thin grey outlines
    - Every v7c variant fills the cell more than v2. The full v7c evaluation (8 seeds, 4 checkpoints) runs at 1024
      (`ICON_REF_RES=1024` in icon_eval.py, `results\icon_eval_v7c_r1024\`, `v6cfg\icon_queue7.ps1`).
    - Lesson: give a LoRA its references at the size it was trained with; check the trainer's resize rule
      (`match_target_res`) before writing the inference graph. A wrongly sized reference still "works", so it is easy
      to miss.
    - Lesson (again): never kill by a pattern that appears in the calling ssh command (`icon_queue5|icon_eval.py`
      killed the session that was to start the next queue); and leave a watcher on every result, so a sheet that is
      done at 03:22 is sent at 03:22 (this one waited until morning).
  - **Colour LUTs** (Arvind: "make LUT files so the colours match how they shift from the Pokemon; Haunter's sprite was
    much greyer than in the game"; `v6cfg\lut_build.py`, `results\lut\*.cube`): Game Freak's own colour shifts learned
    from data, art -> front (official artwork vs HGSS front) and front -> icon (hg-engine's front vs icon): per species
    the source colours (k-means, 10, by area) matched to the target palette by optimal transport; the shifts at the
    source colours smoothed into a 3D Lab LUT (kernel sigma 12, no data -> no shift); fitted without the 40 held-out
    species and checked on them; exported as standard 33^3 .cube files. **Result:** art -> front (468 species, 24922
    colour pairs): held-out palette distance 21.5 -> 18.3 Delta E; moving OUR held-out fronts' palettes toward the LUT'd
    artwork colours (`v6cfg\lut_eval.py`, optimal transport, 8 species x 3 seeds): 22.9 -> 21.0 (50 %) / 20.6 (100 %),
    while moving toward the raw artwork colours makes it worse (23.8 / 25.7). Real but small, and it does not fix
    Haunter: Game Freak drew Haunter much LIGHTER (lilac) than its dark artwork, and one LUT for all species averages
    such choices away (it makes Haunter darker). front -> icon: the numbers improved (26.7 -> 20.7) but the pictures
    look duller: hg-engine's icon PNGs carry one display palette while the game picks one of three shared palettes per
    species, so the icon "truth" colours are unreliable; drop that LUT. Next: a LUT that also depends on how dark the
    whole creature is (dark designs are lifted for the small screen), and the icon colours from the game's palette choice.
  - **Picker v2** (`v6cfg\picker_v2.py`, CPU, minutes): logistic regression on DINOv2 features (colour + greyscale),
    700 real Gen 4 fronts against 530 of our generated ones (many of real species, so it judges the drawing):
    held-out accuracy 0.927. Mean P(real) per way: Blazterra B 0.53 / A 0.43 / C 0.44, Octopearl B 0.76, Gortiki B 0.58,
    Leadling C 0.90 (B 0.86): it agrees with Arvind and with the eye. v1's flaw: two of three ways were the same LoRA
    (v7d), so "typical" meant v7d's look, and nothing measured sprite-ness.
  - **Outlines measured, not hand-fixed** (Arvind: "do not touch it, it should look like the real ones";
    `v6cfg\outline_stats.py`, `v6cfg\outline_colour.py`): on 508 real fronts the outline pixel (darker than the one just
    inside) is fully black 46 %, grey 9 %, a dimmed colour 44 % (Arvind: "lots of dimmed colour, rarely fully black, it
    depends on the material"), a third as light as the colour inside (median 0.33), hue kept 78 %; yellow / green get
    the most coloured outlines (53-55 %), purple / blue the darkest; dark on 60 % of the outside edge. Ours: B (cfg 2.5)
    77 % fully black, ratio 0.02, dark on 94 % of the edge, thickness 2.63 vs 1.75 (too black, too thick, drawn all
    round); A (cfg 1) 30 % black, ratio 0.33 (the right dimming) but too few black. So the LoRA DID learn the dimmed
    outline (cfg 1 shows it); cfg 2.5 exaggerates it to black. unfake also makes outlines less black (0.66 -> 0.34).
    A thinning post-step (`v6cfg\outline_fix.py`) works; colouring it from the palette changed too little to see. Next:
    cfg 1.5 / 2.0 (`v6cfg\cfg_sweep.py`) to let the model's own outline land on the real numbers; for the next training
    round, weight the outline pixels more in the loss (they are a few % of the picture, so MSE barely punishes them);
    later the outline stats as part of a DPO reward.
- **Concept-art inventory** (agent, all 297 pictures of the 115 species; `scratchpad\inventory\inventory.csv`): 19
  finished art or pixel render (straight to sprites), 71 card / sheet (cut-out only), 13 clear sketches (P5 first),
  Yanklet + 11 with no drawing. Decisions needed: two designs in one folder (Sigmauler, Sigmanian Sudowoodo, Icy
  Freeze, Hairyen, Dragem), colours / face differ between pictures (Verrith, Erobi), card names that differ from the dex
  (Wisprake / Wyrmshade, Grincho / Grinetch, Furamire / Furamie, Maagamad / Gullmire), Unknighted (four bodies in a
  ring).

## Follower v6 (data built 2026-10-13, for a pod run on Arvind's yes)

Arvind's design: "one LoRA for all of the follower; two answers per direction, but not side by side (it gets confused by
more than one creature per picture); front and back as inputs (consider the art) and the two other directions as inputs;
that should teach the style, the colours, the size and the proportions"; "it is important that we LABEL the data well".
`v6cfg\build_follower_v6.py` -> `data\v10\follower6` (942 species, the 40 held-out left out, 5652 examples; real HGSS
followers + hg-engine's fan-made ones):
- target: ONE 32x32 frame at 16x (512, RGBA, mask widened one cell) for down / up / left (right = mirrored left); both
  walking steps are separate examples, the caption says "the first step" / "the second step"
- inputs, one picture each, always the same seven slots, an absent one is a see-through picture and the caption says
  "<imageN> is empty": 1 front 8x, 2 back 8x, 3 artwork (in 2878 = half; Arvind: "smart"), 4-5 a walking frame of each
  of the two OTHER directions (each present 60 %), 6 the OTHER step of the same direction (present 50 %: "draw the other
  step: the same picture with only the legs moved"; at use time step 2 is drawn from step 1 so the two always match),
  7 a size box (real +-1 px or predicted from the front, 50 / 50)
- tags as front v7; no dirtied inputs
- trap found and fixed: in 254 of the 2795 other-step inputs the two steps are identical (no leg move), which would
  teach copying: those inputs emptied and their captions changed
- use: down first (front, back, art, box), then left with down, then up with both, then every step 2 from its step 1
- ai-toolkit's progress pictures take only 3 references: `v6cfg\patch_ctrl8.py` adds ctrl_img_4..8 on the image AND the
  prompt-embedding side (config_modules, BaseSDTrainProcess, SDTrainer, base_model, qwen_image_2); tested on copies
- training needs the pod (seven references: the Legion would take 15+ h per pass); estimate 3-4 h, 5-8 $
- **RunPod session 4** (Arvind: "start it; the cheapest pod that works well, speed and quality"): pod `6txhw3tk92ozp1`,
  A100 SXM 80 GB, Community, 1.39 $/h (cheapest in stock with 80 GB and a CUDA >= 13 host; L40S / H200 hosts only had
  CUDA 12), started 22:23 JST. The bf16 transformer is 14 GB and the text encoder 17.5 GB. `cfg/prep4.sh` installs while
  the data uploads (lesson: `hf` comes with the requirements, so the model download must wait for pip). Upload 712 MB
  from the Legion in ~4 min; 435 MB of it was the artwork copied into every example (next time: one per species).
  Text-embedding cache OFF (seven references would make it ~100-200 GB). Smoke: 0 errors, 0 OOM, 4 pictures, weights
  move, buckets 512x512 x 5652, 23.7 s per step of 4 examples, 42 GB VRAM. Steps set to 600 (2400 examples, ~0.4 pass,
  ~4 h incl. pictures, ~6-7 $ in all), saves every 50, pictures every 100. End: `cfg/selfterm4.sh` (after
  `pod3_src\fetch_pod4.ps1` on the Legion has the archive) + Arvind's eye on the pictures.
- **Label bug found at step 300 and fixed (2026-10-14).** The pictures at 200 and 300:
  - Good: the sides were already close to the truth (Haunter, and Cyndaquil at 200), the colours held, and Haunter / Waffy
    "down" looked like small walking frames.
  - Bad: every "step 2 from step 1" drew TWO creatures side by side; Cyndaquil "left" at 300 copied the "down" frame it
    was given; the box was drawn into the "down" pictures.
  - Cause: ai-toolkit's `qwen_image_2.py` `_drop_repeats` drops any reference equal to the one before it (meant only for
    the sampler handing `ctrl_img` over twice as `ctrl_img_1`). Two empty inputs in a row are equal, so they merged into
    one and every later picture moved up a number. The prompt labels each picture `<imageN>` by position, so the
    caption's "<image6> is its other step" / "<image7> is the template" named the wrong picture in **2309 of 5652
    examples (41 %)** and in 8 of the 11 progress pictures.
  - ComfyUI's `qwen_image21.py` drops nothing, so use time was always labelled right; only training was wrong.
  - Fix: `v6cfg\patch_keep_empty.py` drops only the sampler's duplicate (the first two equal). Tested: seven references
    with three empty in a row stay seven; the duplicate case still becomes one.
  - The run was stopped at step 310 and resumed from the step-300 checkpoint and optimizer with the fix (same 600 steps,
    same end time, no extra cost). Pictures after the resume are marked "rettet".
  - Lesson: when a trainer takes several references, check how many actually reach the model and in what order (count
    them in the encoded prompt), not just that the files exist. Icon v7c (front, art, box) cannot have two empties in a
    row, so it is not affected.
- **Step 400 (after the fix) and an audit of what the loss rewards (2026-10-14; Arvind: "it doesn't look good. Are the
  tags and the prompt done properly? Are we rewarding it wrong?").**
  - Step 400: the box is no longer drawn; Waffy and Blazterra "down" became real small followers. Still bad: "left with
    down given" copies the down frame (Cyndaquil, now also Haunter; both drew a real side view at step 200), and every
    "step 2 from step 1" draws the two pixel pictures it was given side by side.
  - Captions and tags checked on random examples: every input named, direction, step, type, stage and height right.
  - **Wrong reward 1, invisible colours:** the follower targets keep the sprite sheet's key colour under the
    see-through pixels, 106 different ones (pink, yellow, green, blue...). ai-toolkit's RGBA path does not clear them
    (`convert('RGBA')`, no premultiply) and the RGBA VAE encodes them, so on ~3/4 of the canvas the loss punishes the
    model for not guessing a colour nobody sees. Likely also the grey patches around Cyndaquil at 400. The pixel-art
    inputs carry the same key colours; the artwork has black. Icon v7c has black everywhere (constant): not affected.
  - **Wrong reward 2, copying pays:** in half the examples the "other step" input is almost the answer, so copying a
    pixel input is the cheapest way to a low loss; the model learns "copy a pixel input".
  - Minor: the mask keeps weight 0.3 outside the creature (~37 % of the loss), so extra things drawn there are cheaper.
  - End (14 Oct): trained to 600 (ended 04:01 JST), the Legion fetched the archive at 04:05 (2.09 GB, size checked;
    12 checkpoints in ComfyUI as `fol6_50` ... `fol6_550`, `fol6_final`; 79 progress pictures in `pod4_out`), and the
    pod terminated itself (RunPod: no pods left, `6txhw3tk92ozp1` not found). Steps 500-600 as predicted: "down" stays
    good (Waffy, Blazterra), "left with down given" copies the down frame, "step 2" still draws two figures.
  - Next round (bundle): clear the colour under transparency to one constant in every target and input; separate the
    tasks ("draw a direction" never gets a near-copy input; "draw step 2" gets only step 1 + the front); a check sheet
    of the seven pictures exactly as the model receives them (after the dataloader) before any run.

## The whole pipeline on three new mons, timed (14 Oct)

Arvind: "take 2 Pokemon from our dex and 1 random real one through the whole pipeline except the follower; how long does it
take". Drawn at random: Obsidog (#103) and Wispole (#29) from the 77 untested mons with concept art, Metagross (#376) from
the held-out species with real HGSS sprites (the first draw, #942 Maschiff, has none). `v6cfg\pipe3.py`, `results\pipe3\`:
base-Qwen cut-out of the concept picture -> front v7 600 at 0.75, cfg 2.5 + negative, 8 seeds, unfake -> picker v2 ->
outline thinned + coloured -> back v6 1800 / 2100 / 2400 x 3 seeds -> icon (PC box recipe, 8 seeds, icon judge) -> game
format (15 colours, one palette for front and back, the icon in the game's icon palettes, 2 frames).
- **Time on the Legion:** Obsidog 20.2 min, Wispole 25.2, Metagross 29.5 (fronts 18.8 + the rest 10.7; the run died once:
  I killed the queue's PowerShell, which held the output redirection, so the Python child died at its next print -
  start long runs detached through `cmd.exe /c ... > log` and never kill their parent). The front step is most of it and
  got slower all afternoon (76 -> 104 -> 131-174 s per front: the laptop GPU warming up / memory after many model swaps);
  back 48-58 s per try, icon 6 s, cut-out 75 s.
- **Arvind:** Obsidog front seed 6 is best (picker v2 chose 2), icon s2 best (judge chose s8), the back (bv6_2400 s3) was
  good; the icon in the game palette went blue and looked bad. Kept in `results\arvind_picks.json` as the pickers' answer
  key. Metagross: the front is close to the real one; the back is the front's bulk from behind with the X copied onto it
  (the real back is a different view); the icon is teal where the real one is purple-blue.
- **Bug found:** `ds_pixel.in_icon_palette` left out the two dark greys (indexes 14, 15), which real dark icons use for
  their bodies (Umbreon, Houndoom, Absol), so dark bodies went to the nearest blue. Fixed in the repo (14 Oct); the game
  export (`sprites.make_icon`) already used all 15.
- **Facing:** real fronts face the way their artwork faces in only 70 % of clear cases, so "same as the art" is a weak
  rule; a classifier on DINOv2 patch features, real fronts against themselves mirrored (`v6cfg\front_facing_clf.py`,
  `results\front_facing\clf.pt`), tells the real orientation 82 % of the time on held-out fronts: usable to mirror fronts
  that clearly face the wrong way.
- **Icon workshop** (`v6cfg\icon_recipe3.py`, `results\icon_recipe3\`; Arvind: "here and on Obsidog it was very bad; not as
  good as in early October; we need something consistent"). 6 mons x 8 seeds; mean over the mons (consistency = DINOv2
  similarity between the 8 seeds; likeness to the front by the classifier; realness by the icon judge):
  - A the PC box recipe: 0.81 / 0.37 / 0.51. Still gives the PC box icons for the PC box mons (Autuman, Erobi, Waffy:
    their typical seed is as good as the PC box one), but breaks on the new hard designs: Obsidog (almost black) a grey
    blob, Metagross a crumpled lump without its legs. So the recipe is right; the new mons are harder than the 6 Oct ones.
  - A + finishing (no loose pixels, inside in 7 colours, one 64-grey outline): 0.83 / 0.34 / 0.68
  - B reference at 640: 0.80 / 0.36 / 0.51 (no different from A)
  - C canvas swap 70 %: **0.89 / 0.60** / 0.39; C + finishing **0.91** / 0.57 / 0.51. Every seed keeps the whole design
    (Obsidog a dark dog, Metagross with its four legs spread as in the real icon), so which seed is picked hardly
    matters; but it looks more like a shrunk front than a drawn icon, and keeps the front's colours.
  - Arvind: the pickers miss all the time (Metagross fronts 5, 7, maybe 1 are good enough; picker v2 chose 8): picking
    goes to a page in the sprite studio where he chooses, with the time each picture takes shown.
- **What a real follower sheet is** (`v6cfg\follower_mirror_stats.py`, 942 sheets): right = mirrored left in 87 %; step 2
  differs from step 1 in a median 5 % of the cell (the legs), and is a plain mirror of step 1 in only 6-7 %. So the job is
  three views of the same creature plus a small leg edit per view.

## Follower, thought again (14 Oct)

- **FLUX.2 Klein base 4B** (Apache-2.0; edits and generates in one model; Comfy-Org's split files, 16.2 GB, down in 3 min)
  with **svntax-dev's 4-walk sprite sheet LoRA** as it is (`v6cfg\klein_test.py`, `results\klein_test\`; their workflow:
  the character picture as reference at ~1 MP, their prompt, 512, 20 steps, euler, CFG 5): every mon became a little
  HUMAN in the mon's colours (Obsidog a dark boy with horns, Metagross a teal boy, Wispole a green boy with a blue tail).
  The author warns that non-human anatomy is bad. But the sheet is the point: four directions x three walking frames,
  all the SAME character, clean pixels, ~35 s per sheet. So the recipe (the whole sheet in one picture at 4x, the
  reference as the design) is worth training on our own data (940 HGSS follower sheets, 4 directions x 2 steps); Klein
  4B is small enough for the Legion.
- **Retro Diffusion** is out: its online models (RD Plus / Pro, FLUX-based) are closed, so no LoRA on top; the Aseprite
  extension's local model is an older, different one.
- **Rear-view drawing for the back** (`v6cfg\back_rear_test.py`, `results\back_rear\`): base Qwen draws the artwork from
  behind, the front recipe pixelates it. Metagross: a real back (no X, no eyes; back v6 pasted the X onto it); Obsidog:
  horns, collar and tail from behind; Wispole: the right side but an odd shape (a tadpole from straight behind is all
  tail). Still to do: the back's framing (big, cut flat at the bottom). ~1.2 min for the drawing + ~80 s per back.

## Next ones (later)

- **Fallback base model: FLUX.2 Klein 9B** (Comfy's style transfer handbook, March 2026: "a sweet spot for LoRA training",
  fast, learns from moderate datasets; edit LoRAs on before/after pairs are its recommended path for niche styles, and a
  style reference without a LoRA is "hit or miss" - what our tests found). Arvind (2026-10-12): Qwen 2.1 is better on
  benchmarks and lighter, so stay on Qwen; try Klein only if everything else fails. Closed services (NanoBanana Pro for
  restyling with likeness, Seedream 5.0-lite / Grok with a style reference) only as comparison points.
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
