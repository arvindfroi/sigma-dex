# The sprite studio

On every Pokemon's page on the website there is a **Sprite studio**: ask the AI for sprites,
look at the attempts, comment on them, have them redone and approve one. Nobody needs
anything but the website.

## How to use it (studio v4, since 2026-10-15)

Arvind about v3: "hard to take in, you have to scroll; lots of times, make it one total time; editing an existing sprite
is stressful". v4 has the site's two screens:

- **Top screen: the sprite set as it is now** - FRONT, BACK, ICON and WALK (the walking sprite that follows the player,
  animated). Each shows the picked picture, or the one in the game now ("in the game"). **EDIT** under any of them opens
  the editor on it, also on the sprite in use. The dialog box says what happens and how long it takes **in all**
  ("Drawing 4 backs, then 4 icons. Ready in about 6 minutes (2 requests from others first)").
- **Bottom screen: one step at a time** - 1 PICTURE, 2 FRONT, 3 BACK, 4 ICON, 5 WALK, SAVE. A step shows what it is
  made from, **MAKE** with how many (and roughly how long), and the pictures as tiles: **tap a tile to use it** (it goes
  into the set, marked IN USE). Pictures still being drawn are grey tiles; there are no times per picture.
  - 1 PICTURE: choose the Pokemon's pictures (up to 3) and, for a messy sheet, **CUT OUT** the creature first.
  - 3 BACK, 4 ICON, 5 WALK show **ABOUT ITS BODY** (body shape, how it moves, what it looks like): the Klein LoRAs
    were trained with it, so the PC draws better with it. It is saved in the dex (`design.body_shape`, `movement`,
    `look`; also in Edit > POKEDEX).
  - SAVE: the picked front and back (icon and walk optional) in a battle, the menu and walking on grass, and "Make these
    its sprite? **YES** / NO". YES puts them together (`assemble_sprite`) and approves them (`review_sprite`) in one go.
    Earlier sprites are listed below with **USE IT AGAIN**.
- **The editor** takes the bottom screen (the top stays): tools on the left (PEN, ERASE, FILL, SWAP = one colour into
  another everywhere, PICK, MIRROR, UNDO, REDO, GRID), the picture in the middle as big as it fits, the colours on the
  right with the 15-colour count and **GAME COLOURS** for that kind of sprite (the back: the front's colours; the icon:
  palette 1/2/3 with the suggested one starred; the walking sprite: closer to the front). "Save as a new picture?
  YES / NO". The saved picture is a new tile of that step, picked and in use; nothing is overwritten.

What draws what (`scripts/studio_tries.py` on the PC): the cut-out with base Qwen-Image, the front with front v7, the
icon with **Klein icon v1 (step 2500)**, the walking sprite with **Klein follower v3 (step 2000)** from the picked front
and back, the back with **Klein back v2 (step 2500)**, which first draws the art from behind (base Qwen) as its image 3. Colours (`scripts/sprite_colours.py`): the back keeps Klein's own colours (snapping to the front's colours flattened its shading; the game's one palette for front and back is made at export from both together, and the front's colours are a button in the editor); the walking sprite is pulled halfway to the front's colours; the icon keeps Klein's own colours (the game's icon palettes are a button in the editor: snapping automatically made icons bluer or olive). Database: migration
`supabase/migrations/2026-10-15_studio_v4.sql` (stage `follower`, `sprite_jobs.with_try`, `sprite_candidates.follower`,
`[ds-follower]` pictures -> `assets/sprites-ds/<pokemon>/follower.png`, 128x64). `sprite-draw` also takes a drawing on
the sprite in use (`version` + `view`) and saves it as a new try.

**The sprite tray** (bottom right of every page while something is drawn): the drawing line with everyone's requests,
yours starred, how far each is ("2/4") and the time until it is done; and "N new pictures - PICK" for your Pokemon whose
pictures finished since you last looked. A tap opens that Pokemon's SPRITES. On the SPRITES tab, **MINIMIZE** closes the
page and leaves the tray (Arvind: "it feels a bit scary to leave it while it works"). Your requests are remembered on
your device (`sigma-my-sprites`).

The older ways below (v2: one AI sprite at a time, versions, "Ask the AI") still work in the database but are no longer
on the page.

## How to use it (2026-10-05 to 2026-10-14)

Open a Pokemon and press the **Sprite** tab.

1. **Pick the pictures the AI should follow** - tap up to three of the Pokemon's pictures; the
   first one matters most. (Add concept art under **Pictures** first if there is none.)
2. **Make a sprite.** The request joins one line shared by everybody; the studio shows the line,
   what the drawing PC is doing right now ("front sprite 2 of 3") and where your request is. One
   sprite is drawn at a time: front and back (80x80) and the menu icon (32x32), in the DS style
   ([the approved pipeline](SPRITE_STYLE.md), `scripts/ds_pixel.py`). A new sprite takes about
   5 to 10 minutes. The menu icon comes from our icon edit LoRA ([LORAS.md](LORAS.md)). `ds_pixel.make` also draws a follower
   walking sheet when the follower LoRA is on the PC, but the studio does not hand that in or show it yet.
3. **Pick a version and make it perfect.** Every version is shown in a row; tap one to open it in
   the editor:
   - **Draw on it yourself**: pencil, eraser, fill, recolour (every pixel of one colour at once),
     pick a colour, undo/redo, a pixel grid. The game allows 15 colours per picture; the editor
     counts them. **Save my drawing** makes it a new version.
   - **Ask the AI**: write what should change and choose front, back or both - or press
     **Mark area**, drag a box, and only that part is changed (everything outside the box stays
     exactly the same, pixel for pixel). Takes 1 to 2 minutes. The result is a new version.
   - **Approve** the one you like (or **Reject**). The approved one becomes the Pokemon's DS
     sprite within about 15 minutes (`assets/sprites-ds/<pokemon>/`, made by `scripts/sprites.py
     auto` from the pictures captioned `[ds-front]`, `[ds-back]`, `[ds-icon]`).

How the AI change works: Qwen-Image-Edit is shown the finished pixel sprite (blown up on its
grid, plus a copy with a red frame for an area) and asked for the change; its picture is read back
on the sprite's own grid (`ds_pixel.edit`). For an area, only the cells inside the box are taken.
Two attempts are drawn and the cleaner one is kept. Colours are kept at 15 at most by merging the
rarest new colour into its nearest.

Versions drawn by hand are saved by the edge function `sprite-draw` (no key; it accepts only
80x80 / 64x64 / 32x32 PNGs, at most 200 per hour). Older 64x64 attempts (GBA styles) are still
listed under "older attempts".

Database (migration `supabase/migrations/2026-10-05_studio_v2.sql`): `sprite_jobs.mode` (`new` or
`edit`), `view`, `area`; `sprite_candidates.gen` (4 = DS), `kind` (`ai`, `edit`, `drawn`),
`parent_id`, `note`, `editor`, `icon`; RPC `request_sprite_edit`. Edge functions are in
`supabase/functions/`.

## The styles (retired)

Since 2026-10-05 the website only asks for DS sprites (style `ds`, above). The worker still knows the
older GBA styles below, for scripts and old requests, but none of them is used for new sprites any more.
The Sprite XL and Emerald styles need the models listed (as no longer used) in [COMFYUI.md](COMFYUI.md).

- **Sigma sprite style (`sprite-official`, GBA 64x64, the default 2026-10-03 to 2026-10-05).** Qwen
  draws the concept art as official-style Pokemon artwork, and `scripts/pixel_render.py` builds
  the sprite from it pixel by pixel; every attempt is checked against the sprite standard. What
  the standard is and how it works: [SPRITE_STYLE.md](SPRITE_STYLE.md). Its renderer still makes the rough draft
  whose silhouette guides the DS pipeline.
- **Redesigned with more character (`sprite-clean`).** Most
  concept art is a plain drawing without pose or expression, and shrinking it loses the face.
  So: (1) Qwen *redraws* the first reference picture with freedom - bigger head and eyes, a
  face with attitude, a dynamic pose (`redesign_front` / `redesign_back` in
  `data/sprite_prompts.yaml`; telling it to "keep the design exactly" makes it copy the
  reference instead); (2) that is shrunk to a rough sprite at official size, as below;
  (3) Qwen repaints the rough sprite at exactly its size and place (`cleanup`); (4) that is
  snapped to the 64 grid. Results vary a lot between attempts. Test on the starters (front and back, two
  attempts each):
  ![sprite-clean](img/sprite_clean_test.png)
  Tried and worse: a cleanup that is told to stay pixel art (cleaner but lifeless), and the
  Sprite XL LoRA on top of this (softer and muddier):
  ![LoRA finish](img/sprite_clean_lora_test.png)
- **Close to the concept art (`sprite-xl`).** Two steps: Qwen-Image-2.1 draws a clean
  illustration of the creature in the chosen pose from the concept art; then NoobAI-XL with
  the [Pokemon Sprite XL PixelArt LoRA](https://civitai.com/models/378602) repaints it as a
  Pokemon sprite while a ControlNet holds its outlines in place.
  The illustration is drawn in the angles the games use (front: three-quarter view turned
  left; back: over the shoulder, facing up and right), the creature is drawn at the size
  official sprites of its strength have (first stages about 40 pixels, final stages fill the
  frame). The back view is drawn 1.4 times closer and only its upper part is kept, cut off
  flat at the bottom, as the games do. The attempts of one request alternate between two ways of finishing, because each
  wins on some creatures: **drawn** (the illustration is shrunk with a method that keeps thin
  outlines, eyes and claws alive - PixelOE) and **repainted** (the sprite LoRA repaints it and
  the colors are then locked to the illustration).
  How freely it repaints is a trade-off (`denoise` and `control` in `SPRITE_XL`): more freedom
  looks more like Pokemon but drifts toward grey and invents things, less keeps the colors and
  the design. Set to 0.55 / 0.6 after this test on 2026-10-02 (d = denoise, c = control):
  ![strengths](img/sprite_xl_strengths.png)
- **Plain pixel art.** Qwen draws the sprite as pixel art directly. Keeps the most detail of
  the design, but looks less like Pokemon.

Tried and dropped on 2026-10-02: the "Pokemon Emerald Sprite Style" LoRA (civitai 1523016).
It only looked like Gen 3 when it was free to redesign the creature
(![comparison](img/emerald_lora_test.png)). The worker still understands the styles
`emerald-light` and `emerald-medium`, but the website no longer offers them.

The Sprite XL and Emerald LoRAs were trained on official Pokemon sprites. Whether such models may be used is
legally unsettled; Arvind decided to use them (2026-10-02).

## What is fixed and what is free

The goal: the same request must always give the same result, and all sprites must look like
they belong to one game - without every Pokemon coming out the same.

| Fixed (the same for every sprite) | Where |
|---|---|
| The DS style text and the prompts for the front, back and edits | `STYLE`, `FRONT`, `BACK` in `scripts/ds_pixel.py` |
| The artwork prompts (Diamond/Pearl-era official artwork, front and back) | `official_front_gen4`, `official_back_gen4` in `data/sprite_prompts.yaml` |
| The sizes per stage, the 96 grid and the 15 colours | `scripts/sprite_worker.py` (`GAMES`), `scripts/ds_pixel.py` |
| The icon and follower LoRAs | `ICON_LORA`, `FOLLOWER_LORA` in `scripts/ds_pixel.py`, see [LORAS.md](LORAS.md) |
| The model, its settings and the conversion | `scripts/comfy.py`, `scripts/sprites.py` |
| The seeds of a request: request number x 100, plus 5, 6, 7 for the three fronts (+1, +2 for edits) | `scripts/sprite_worker.py`, `scripts/ds_pixel.py` |

| Free (decided per Pokemon by people) | Where |
|---|---|
| The look and the pose (`look`, `ds_pose`, `signature`) | `data/sprite_prompts.yaml` |
| Which concept art the AI sees | ticked in the studio |
| What to change, and on which spot | "Ask the AI" and the marked area, or the pixel editor |
| Which version wins | Approve |

Every version stores its prompt and seed, so it can be reproduced. To
change the style of the whole dex, change the prompts above: sprites
drawn after that use the new style; approved ones stay as they are until redone.

## How it works

```
website --request--> database (queue) <--asks for work-- worker on the PC with the GPU
website <--attempts-- database + file storage <--hands in sprites-- worker
approved attempt --> attached to the Pokemon as sprite pictures --> dex (within 15 minutes)
```

The worker (`scripts/sprite_worker.py`) only makes outgoing connections; the PC is not
reachable from the internet. It starts ComfyUI when it needs it and gives the graphics
memory back after three minutes without work. See [COMFYUI.md](COMFYUI.md) for the PC.

### The worker on the PC

Installed on 2026-10-02 on Arvind's Legion:

| What | Where |
|---|---|
| A copy of this repository with its own Python | `D:\LocalAI\sigma-dex` |
| The worker key (lets the worker hand in sprites; not in the repository) | `D:\LocalAI\sigma-worker\worker.key` |
| Start script and log | `D:\LocalAI\sigma-worker\run_worker.bat`, `worker.log` |
| Starts at Windows login | shortcut `sigma-sprite-worker.bat` in the Startup folder (`shell:startup`) |

The worker updates its copy of the repository by itself (`git pull`) and restarts when
something changed, so whoever can push to the repository decides what runs on that PC.
To stop it: delete the Startup shortcut and end the `python` process running
`sprite_worker.py` in Task Manager.

Limits: 40 requests waiting at once, 120 requests and 300 comments per hour.

## Sketch -> official art (17 Oct)

The first step can now also redraw a rough sketch as official artwork before the fronts. In the guided start the
person says what kind of picture it is: a finished drawing with other things on it (cut out, as before), a clean
drawing of just the creature (used as it is), or **a rough sketch**: the PC draws N official-art versions (Klein style
v2 at step 2500, `SKETCH_KLEIN` in `scripts/studio_tries.py`, art job with recipe `sketch`), the person taps one, and the
fronts are drawn from it. In the full studio the PICTURE step has the same choice ("redraw a sketch as official art").
The drawing is made at 512 on white from the sketch fitted in 482 px (image 1 and the start picture, 85 % redrawn), with "official pokemon artstyle. " + type, stage,
height, body shape and look, then cut from its white background. About 25 s per drawing. See docs/LORAS.md (Sketch -> art).

**NEW POSE** (17 Oct): every drawing in the PICTURE step has a NEW POSE button. It asks for an art job with recipe `pose`
from that drawing: base Qwen-Image 2.1 draws the same creature in a new pose (action / turned the other way / about to
jump, in turn), then style v2 (image 1 only) gives it the official look again, cut from white. About a minute each. In
the guided flow the new poses appear among the sketch drawings; the one tapped is what the fronts are drawn from.
**Describe the design**: with "rough sketch" chosen, a text box takes the person's own words about the design. They go
to sketch and new-pose drawings as "Its design: ..." after the dex's look (JSON `note` in the job's prompt), so they
can correct what the look text or the sketch gets wrong.

## Colours: 15 without losing the shading (18 Oct)

Arvind: "the backs still come out very flat ... the way we handle colours is not good enough". Klein draws 1000-2000
colours; the old reduction to 15 (`merge_alike`) merged each colour into the more used of a close pair, so whole runs of
shades collapsed into one flat colour (Sabertann's hull, Obsidog's body, Stonma drifting pink). `merge_alike` in
`scripts/klein_follower.py` now does a quick greedy pass to 64, Ward merging to 15 (size-weighted, into weighted means),
then k-means over every original colour in Lab: each final colour is the mean of its shades, so light, mid and dark
tones stay apart. Used for backs, walking sprites and icons. Still 15 colours (the game's limit per front/back/walk
palette). Still open: the walking sprite is pulled halfway to the front's colours first; icons must use one of the
three shared icon palettes in the game (choose the best one per mon at export).

**Holes in pink creatures (20 Oct).** Klein draws backs, walking sprites and icons on magenta; `magenta_to_clear` took
every pink with little green as background, so pink and purple mons got holes (Vires' head, 206/107/153). Now only real
magenta, and the pinkish fringe within 2 pixels of it, is background. Fronts (the Qwen front LoRA, its own alpha) were
not affected; a scan of all approved sprites found only natural gaps (between legs, tails, sails). Studio tiles, the set
and the editor now show sprites on a light checker in both themes (the dark one hid the black outline).

