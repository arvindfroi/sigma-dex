# Opening movie: Sabertann instead of Ho-Oh

Our own tools, no Nintendo data. They run in a work folder outside the repo
(`~/sigma-origin/title3d`, base ROM = Origin HG + EN patch rc8 extracted to `~/sigma-origin/rc8/x_rc8`).

1. `cutout.py` - cuts Sabertann out of the concept art (`assets/concept-art/sabertann/624.webp`), white background and rock removed.
2. `pixel.py 104` - scales it to a 104 px tall sprite in the battle sprite's 15 colours, with crisp ink lines and an outline.
3. `build_intro.py` - builds the 6 animation cells (sails and flag flutter, body bobs) and writes
   `gs_opening` (`a/2/6/2`) members 23 (palette), 24 (tiles) and 26 (cells). Member 25 (the animation:
   path, zoom, timing) is kept byte for byte, so the scene plays exactly as Ho-Oh's did.
4. Copy `out_a262.narc` to `files/a/2/6/2` of an extracted ROM and rebuild it with `dsrom build`.

Budget: 367 tiles (Ho-Oh used 388), 14 sprites per frame, same 16-colour palette slot.

`nitro.py` / `geom.py` read NSBMD/NSBCA (the HeartGold title-screen 3D Ho-Oh) and export OBJ; written
from apicula's format notes (0BSD). Origin's title screen does not show that 3D model at all.

## Overview of the whole intro

`inventory.py` decodes every background (NSCR+NCGR+NCLR) and sprite cell of `a/2/6/2` into `inv/`;
`overview.py` builds `intro_oversikt.html` (scenes, pictures, size/colour limits, file numbers, status).
The page holds the game's own graphics: share it in the group only, never in the repo or publicly.
Scene to file map (pret `src/intro_movie_scene_1..5.c`): 1 sunset 0-30, 2 running 31-38 + 73-80,
3 towns 97-105 / rival 39-47 + 65-68 / beasts 47-49 / Eusine+Unown 69-72 / Rockets 41 + 50-52,
4 starters 53-58 + 81-96, 5 sea 59-64. Music: SDAT sequence 1004 `SEQ_GS_TITLE` (unchanged by Origin).

## Version 2: 3D Sabertann sails in (2026-11-13)

The first version (cut from the concept art) was not good enough. Version 2 builds a 3D model and renders
the sprite frames from it, so every frame is the same creature (no AI frames). Sabertann no longer flies out
of the sun: he sails in from the horizon in the sun's reflection, like a pirate ship (a nod to Kaptein Sabeltann
and Den sorte dame; the design stays our own).

Tools (run in `~/sigma-origin/title3d`, Blender 5.2 headless, `B=/Applications/Blender.app/Contents/MacOS/Blender`):

1. `saber3d/textures.py` - draws the sails, flag and hat emblem (own skull and crossbones).
2. `saber3d/model.py` - builds the model from the concept art (metaball body, tusks, bicorne, red shell with wale
   and gun ports, two masts, sails, flag, gold tail fin, legs), a rig of 30 bones under one root (DS friendly) with
   skin weights, and an 8-frame swim loop (flag ripple, sail belly, tail sway, paddling legs). `$B -b -P model.py -- sabertann.blend`
3. `saber3d/render_passes.py` - adds the water (holdout), animated foam built from the waterline, a low 3/4 camera,
   and renders data passes (albedo, camera-space normal, part id, depth). `SAB_LAYER=base|anim` renders the static
   body or only the flag and foam (the rest held out). Run at 30, 18 and 9 px per unit for three detail levels.
4. `saber3d/pixelize.py` - toon light, 15 fixed colours, weighted 4x4 downsample, dark outline, waterline contact line.
5. `build_saber_intro.py` - writes members 23 (palette), 24 (tiles), 25 (new path) and 26 (cells) of `a/2/6/2`.
6. `saber3d/preview.py`, `rigview.py`, `make_sheet.py` - pictures of the model, the rig and the frames.

Facts that shaped it (pret `intro_movie_scene_1.c`, `intro_movie.c` + emulator):
- The sprite sits at (128, 96) on the bottom screen; the animation runs 2 ticks per frame; the fade to white
  starts 90 frames after it appears and lasts about 65 frames. The water starts at row 164.
- OBJ VRAM is 32 KB (1024 tiles incl. 16 for the sun). The sprite is affine with forced double size: each piece
  costs 10 + 4 x width cycles on every line its (double) box touches, 2130 per line. Far away all pieces stack on
  the same lines, so there are three detail levels (few big pieces far away, 8-frame full version close up).
- Abutting affine pieces get 1 px seams when scaled or rotated. The static body is laid out on a grid with 1 px
  overlap; only the flag and foam are animated, drawn on top, so their seams show the body, not the sky.
- Result: 728/1024 tiles, worst line 1886/2130 cycles, 27-32 pieces per frame close up.

Not in the repo: the ROM data it reads, the renders, the test ROM (`~/sigma-origin/rc8/sabertann3d_intro.nds`).

## Version 3: tropical night (2026-11-13)

Arvind asked for a scene that suits Sabertann, who borrows from Kaptein Sabeltann and his ship Den sorte dame
(black and gold captain with a big gold-trimmed hat and a gold skull on it; a red hull with a black band, gold
trim, lanterns, white sails). We looked at photos and book covers for inspiration only; nothing is copied.

Changes to Sabertann (`saber3d/model.py`, `saber3d/pixelize.py`):
- Bigger bicorne with a large gold skull emblem on the front (it was too small to read in the sprite).
- Thicker black wale band and bigger gun ports. At night the ports glow like lamplit gun decks.
- Night palette (`SAB_THEME=night`, the default): blue moonlit greys, cooler red, silver moon rim, warm gold.
  `SAB_THEME=day` gives the old colours. `saber3d/rerender_all.sh` re-renders and pixelizes all six pass sets.

The scene (`night/`), all own art drawn by code:
- `night/paint.py` - top screen: deep sky with stars and a faint star band. Bottom screen: banded sky with a moon
  glow, moonlit clouds, islands on the horizon with tiny palms, a harbour with lamps and a lighthouse, the sea with
  wave streaks, lamp reflections and the moon's glitter path. BG2/BG1: far and near palms (they scroll down 16/32 px
  like the pines did). Also the 64x64 full moon sprite. Writes `night/art/*.png` and `preview.png`.
- `night/build_night.py IN.narc OUT.narc` - packs the art into 4bpp tiles with flip dedup and shared palettes and
  writes members 0, 1 (palettes), 6, 7 (tiles) and 15-18 (maps). Main palette 2 (logo) and sub palette 0
  (copyright) stay. It decodes what it wrote and checks it against the art pixel for pixel.
- `build_saber_intro.py` with `SAB_MOON=night/art/moon.png` puts the moon in place of the sun: 64 own tiles
  instead of one mirrored quarter, palette 0 of member 23. It rises the same 31 px the sun did.
- `night/make_video.py OLD.nds NEW.nds OUT` - records both ROMs every frame and writes a side-by-side mp4 and a gif.

Build (in `~/sigma-origin/title3d`):
`SAB_CELL=32 SAB_LAMBDA=15 SAB_MOON=night/art/moon.png python build_saber_intro.py out_a262_saber_night.narc`,
then `python night/build_night.py out_a262_saber_night.narc night/out_night.narc`, copy that to
`a/2/6/2` of a copy of the extracted rc8 ROM and build it with dsrom.

Limits met: main BG 809/1024 tiles, 5 of 9 free palettes; top screen 221 tiles, 1 palette; OBJ 778/1024 tiles
(64 for the moon); worst line still 1886/2130 cycles. Main BG1-3 share one tile file at 0x8000 (128 KB BG VRAM).
Rows 192-255 of the palm maps must stay empty: with the scroll at -32 they wrap to the top of the screen.

Test ROM: `~/sigma-origin/rc8/sabertann_natt.nds`. Video: `sabertann_intro_natt.mp4` (gitignored).
Not checked on a real DS. The next scene (grass, daylight) follows the fade to white as before.

## Version 5: a sabre-toothed cat coming straight at you (2026-11-13)

Arvind's corrections after v4:
- Sabertann is a **sabre-toothed cat** (Kaptein Sabeltann = Captain Sabretooth), not a walrus. The long white teeth
  are sabres.
- The intro must be **in the same style as Ho-Oh**: he comes straight at the camera on the water, the creature itself
  is animated, and at the end he opens his mouth or leaps out of the water at the camera.
- The gold thing at the back is a **gold skull**. Arvind sent a picture of a pirate ship whose bow is a big gold
  skull with round, red-framed eye windows and a row of teeth.

Model (`saber3d/model_head.py` + `saber3d/model_body.py`, concatenated to `model.py`):
- Cat head: round cranium, broad cheeks, short muzzle, gold cat nose, angry almond eyes, ears, mouth line, sabres from
  the upper jaw. The lower jaw is a separate mesh with a red mouth inside and gold lower fangs, so the jaw bone opens
  the mouth.
- Kaptein Sabeltann's look: a black curly mane round the face, gold fringed epaulettes, and a big bicorne worn
  athwart with a gold skull and crossbones in front.
- The ship on the back: the hull, deck, gold rail and black band from v4. At the stern sits a gold skull plate,
  extruded from the outline in `saber3d/skull_shape.py` and drawn by `textures.py` in the style of the ship picture,
  with two gold spikes behind it.
- Animation, 7 frames: frames 1-4 paddle (the front paws come up out of the water in turn, the head nods, the flag
  waves, and the sails stay still so their tiles are shared). Frames 5-7 are the leap: he rises out of the water
  with the body pitched up, the paws spread with claws out, the jaw opening to 46 degrees and the head up in a roar.

Rendering (`saber3d/rerender_v5.sh`):
- Camera head-on (yaw 0, elevation 8). The canvas is 3.8 x 5.9 units; Blender's ortho scale spans the longer side,
  which is fixed in `render_passes.py`.
- Full frames, with no base/anim split.
- The leap frames get a splash crown and flying drops instead of bow waves.
- Three detail levels at 22, 13 and 7 px per unit.

Sprite data (`build_saber_v5.py`):
- Every frame is laid out on one shared grid of 16 px pieces with 1 px overlap, so there are no seams and unchanged
  areas share tiles. The grid must never start at -1, because numpy wraps negative slices and a whole column of
  pieces went missing.
- The path goes straight at the camera. He paddles at 32 ticks per stroke, about Ho-Oh's wingbeat. The leap starts
  at tick 160, then scale grows faster, timed with the fade to white.
- Display scale is capped at 1.96x: an affine double-size piece cannot draw beyond twice its size, so above that
  the pieces leave gaps.
- Result: 872/1024 OBJ tiles (64 for the moon), and the worst line uses 1542/2130 cycles.

Build: `SAB_TLEAP=160 SAB_S0=0.34 SAB_CELL=16 SAB_MOON=night/art/moon.png python build_saber_v5.py out.narc`,
then `night/build_night.py`. Test ROM: `~/sigma-origin/rc8/sabertann_v5.nds`. Video: `sabertann_intro_v5.mp4`
(Ho-Oh side by side). Not tested on a real DS.

## Version 6: faithful to Arvind's drawing (2026-11-13)

Arvind: "stay as faithful to my drawing as possible". The model was rebuilt against the drawing itself:
- `saber3d/fit_view.py` renders the model flat from any angle.
- `saber3d/overlay.py` puts that render next to the drawing (624.webp, mask `art/keep.npy`) with the model's outline
  drawn on it.
- `saber3d/draw_compare.sh` does the same in game pixels, in day and night colours. It uses the drawing's pose:
  `SAB_REST=1`, head turned with `SAB_HEADTURN=-22`, legs splayed.
- The drawing is close to a 60 degree side view with the head in profile.

What the drawing has, now in the model (`saber3d/model_body.py`):
- Head: a big head held high, with a tall muzzle and a flat upright front. A small gold nose on top. Narrow white
  eyes with the pupil at the front, under a heavy brow, low enough to show under the brim. A line down the muzzle.
  Long sabres from the front of the upper jaw, and a gold fang at the corner of the jaw.
- Hat: a bicorne worn fore-and-aft, front tip curled up and back tip sweeping up. Gold trim on the top edge, a gold
  skull and crossbones on each side panel.
- Legs: long and thick, splayed. Shaggy gold cuffs up on the forearms, big paws with three big white claws.
- Hull: a rounded, arched red hull with a black rim on top and a thick black band low down that slopes aft.
  Triangle ports with gold inside, a round port aft, no gold rail.
- Stern: a gold skull with red-rimmed round eye sockets and rows of teeth, with two gold spikes above it.
- Rig: masts raked aft, the sail in front of the mast, the flag streaming aft.
- Removed from v5 because they are not in the drawing: mane, ears and epaulettes.

Gotchas:
- A positive `SAB_HEADTURN` turns the head toward +x, the camera side in the intro.
- The swim pose uses `HEADTURN`, and the drawing comparison passes a negative value (profile).
- A body made of metaballs needs a light decimate (0.8) plus a smooth modifier, or the toon light shows facets.

Intro variants (`night/build_variant.sh NAME YAW HEADTURN CANVAS_W PPU0`, with `SAB_PPU1` for the middle detail
level):
- `v6C`: yaw 50, head -15. The drawing's pose, sailing straight at the camera. 17/11/7 px per unit.
- `v6A`: yaw 10, head +10. Nearly head-on; the fore-and-aft hat turns into a thin crest and the face is hard to read.
- `v6B`: yaw 35, head toward the camera. Not sent; it read worst of the three.

Test ROMs are `~/sigma-origin/rc8/sabertann_v6C.nds` and `sabertann_v6A.nds`. Videos: `sabertann_intro_v6C.mp4` and
`sabertann_intro_v6A.mp4`, each beside Ho-Oh.

## Version 7: 3D model made from the drawing (2026-11-13)

Arvind liked v5's run straight at the camera but said v6 still did not look like Sabertann. The snout, the hat, the
gold cuffs, the paws, the ship on the back, the gold skull at the stern (Den sorte dame) and the eyes were all wrong.
So v7 stops modelling by hand. An image-to-3D model builds the shape from the drawing itself.

The pipeline lives in `h3d/`. Work folder: `~/sigma-origin/title3d/h3d`.

1. **Cutout.** The drawing (`assets/concept-art/sabertann/624.webp`) is cut out on white, without the rock or the
   water lines.
2. **`img2mesh.py IMAGE OUT.glb seed`.** Runs Hunyuan3D 2.1 in ComfyUI on the Legion (core nodes, checkpoint
   `hunyuan_3d_v2.1.safetensors` from Comfy-Org, 7.4 GB) through the SSH tunnel on 8188. A run takes about 2
   minutes. Seed 3 was chosen: its bicorne is worn athwart with the emblem in front, like Kaptein Sabeltann's hat,
   so the hat reads head-on.
3. **`prep.py`** (Blender). Joins the mesh, drops loose bits and the flat water squiggles, and decimates to 150k
   faces. It writes vertices, normals, faces and thickness to `.npz`, plus a `.ply`.
4. **`fit_cam.py`.** Finds the orthographic view whose silhouette matches the drawing: az -36, el 8, IoU 0.78.
   **`colour.py`** projects the drawing's colours from that view. Only the sail and flag emblems keep these
   colours, because the legs do not line up with the drawing.
5. **`paint.py`.** Paints colour classes by shape:
   - hat: black, gold trim along the brim edge, gold skull-and-bones in front
   - face: angry eyes cut by a slanted brow, a gold nose, white sabres
   - forelegs: ragged gold cuffs
   - paws: white claws
   - hull: red, with a black bottom rim and wale band, a gold line and gold ports
   - masts: found as small round blobs in horizontal slices; sails are white
6. **`build_v7.py`** (Blender). Moves the mesh into the old model frame (faces -Y, feet at z = 0, x3.3). It then
   builds the rest:
   - one object per part (for the outline step)
   - the gold stern skull after Den sorte dame: red-rimmed eye windows, nose hole, two rows of teeth
   - a rig: root, spine, head, mast, flag and stern, plus two bones per leg, with geometric weights
   - frames 1-4: a trot on the water surface (water 0.16)
   - frames 5-7: the leap, with the head tipped down so he glares at the camera
7. **`build_v7_variant.sh NAME YAW EL PPU0`.** Runs `render_v7.sh`, then the existing `build_saber_v5.py`,
   `night/build_night.py`, the ROM, the emulator shots and the video.
   - Sent version: yaw 24, el 11, PPU0 15.5, PPU1 11, PPU2 7.
   - Budget: 1004 of 1024 OBJ tiles; worst line 1204 of 2130 cycles.

`pixelize.py` gained `SAB_DEPTHLINE`, which draws an outline where one part folds over itself (a leg in front of the
chest). `render_passes.py` gained `SAB_NFR`, which renders only the first N frames, and tusk objects are now
optional.

Results (gitignored):
- `sabertann_intro_v7.mp4`
- `sabertann_v7_rundt.png`: turnaround including the stern skull
- `sabertann_v7_bilder.png`
- `sabertann_v7_3dform.png`

Licence note: Hunyuan3D 2.1 uses the Tencent Hunyuan Community License. Its territory excludes the EU, the UK and
South Korea; Norway is in the EEA but not in the EU. Only the generated mesh is used, and the mesh comes from our
own drawing.

## Version 8: seed 1's head, clean emblems, a pounce (2026-11-13)

Arvind's verdict on v7: much better, but not close enough. The snout was not good enough and other details were off.
He wants a mon that could pass as official and asked me to be very picky. The reference for "official" was the
SoulSilver opening (his own ROM, kept outside the repo in `~/sigma-origin/ss`). There, Lugia flies out of the moon
over a night sea. Its sprite is crisp, uses a few colours per material, and has bright eyes. The approved battle
sprite `assets/sprites-ds/sabertann/front.png` sets the target look for the mon itself.

What changed:
- **The head comes from seed 1.** A head-only Hunyuan run failed: a cut-out head became a flat board. Seed 1 of the
  full drawing has the clearest face: a real snout with the nose on its top front, a mouth, eye slits and sabres
  hanging from the mouth corners. Seed 3 keeps the better body, hull and sails. Both meshes come from the same
  drawing, so they line up:
  - **`align_head.py`.** Places seed 1 in seed 3's frame from the two camera fits. Depth is chosen so the head is
    mirror-symmetric about y = Y0.
  - **`graft.py`.** Seed 1's head ellipsoid and hat replace seed 3's. The seam overlaps a little under the chin and
    behind the head.
- **`paint8.py`.** Applies v7's rules to the body and its own rules to the new head:
  - a small gold nose on the snout's top front, and white sabres
  - open angry eyes (white, pupil toward the nose, heavy brow), placed forward enough to show from the front
  - a black hat with a gold edge along the brim, found where the thin brim turns over; the ears under the brim stay
    body
  - a gold skull and crossbones on the crown's front
  - gun ports as in the drawing: three black pointed arches with a gold cannon muzzle each, not gold triangles
- **`teeth_longer.py`.** Stretches the sabres down to drawing length (tips 0.11 lower).
- **`emblem.py` and `build_v8.py`.** Clean skull-and-crossbones textures for the main sail, the rear sail and the
  flag, on planar UVs. Laplacian smoothing on the sails, body, hull and hat removes Hunyuan's bumpy relief, so the
  toon light gives clean shapes. The leap is now a pounce: the front paws spread out first, then reach toward the
  camera.
- **`pixelize.py` with `SAB_CLEAN=1`:**
  - small features (pupil, eye, nose, sabres, brow) keep their pixels when they cover enough of a block
  - lone off-colour pixels and stray opaque pixels go
  - foam pixels with fewer than two foam neighbours go
- **`render_passes.py`.** `SAB_DROPS` and `SAB_DROPR` set the splash drops; v8 uses 5 drops of radius 0.09-0.14.

Build: `SAB_BLEND=../h3d/sab_v8.blend SAB_CLEAN=1 SAB_DROPS=5 SAB_DROPR=0.09,0.14 LABEL_B="Sabertann v8"
h3d/build_v7_variant.sh v8 24 9 15.2`
- Budget: 1012 of 1024 tiles; worst line 1204 of 2130 cycles.
- ROM: `~/sigma-origin/rc8/sabertann_v8.nds`

Results (gitignored): `sabertann_intro_v8.mp4`/`.gif`, `sabertann_v8_rundt.png` (the drawing next to six views),
`sabertann_v8_bilder.png`.

Known gaps:
- the hat crown is a tall block seen from the side
- small ears under the brim that the drawing does not have
- in the leap only the near paw shows, and the body is a dark mass
- the last frames are scaled 2x (chunky), like Ho-Oh in HG

## Version 9: a dog's muzzle, a deck, modelled details, a steady hand and Ho-Oh's pixel style (2026-11-13)

Arvind's notes on v8:
- the snout must stick out more, almost like a dog's
- the legs end in white paws (wrong)
- the stern skull does not look right
- the ship on the back has no deck, so it reads as a red barrel
- the paint looks done by an unsteady hand
- the paws look wrong in the leap
- the pixel style and the eyes should be like Ho-Oh's

He also sent a turnaround sheet (front, side, back, 3/4) and a clean 3/4 picture of the design. From those:
- the shell's dark marks are black spikes with a gold foot, not gun ports
- the wrist cuffs are clean gold bands
- he has gold marks on the flanks and a short tail with a gold tip
- the ears under the hat brim belong to the design

Ho-Oh's own intro sprite (HG `a/2/6/2` cells 1-6) was decoded and studied:
- no black outline; an edge pixel is the colour's own darker tone
- muted colours, two or three tones per colour, no dithering
- tiny bright eyes, one pixel wide, in a dark face

What changed:
- **`v9_mesh.py`** (on seed 3 + seed 1's head, after `teeth_longer.py`; vertex order kept):
  - the muzzle is stretched forward by 0.13 with a smooth falloff, a little narrower and lower at the tip, and a gold
    nose pad is painted on the new tip
  - the fused Hunyuan sabres and their leftovers in front of the chin are dropped (part 12)
  - the blotchy painted eyes and the painted hat emblem are cleared
  - the white paw soles become black again
  - cuffs are clean bands; the hull's thin gold line and painted ports go
  - the gold flank marks are added
  - the hull's top becomes a deck: planks inside a black gunwale, a gold rail line where the deck turns down
  - writes the eye spots, the sabre roots, the toe tips (three claws per paw, found as local maxima of the paw
    outline), the spike spots and the deck outline to `*_extra.json`
- **`clean_labels.py`.** The steady-hand pass. It turns the vertex labels into face colours, merges islands smaller
  than `MIN_AREA` into the colour around them, and lets saw-tooth faces take their neighbours' colour.
- **`build_v9.py`.** A per-pixel paint:
  - Every vertex carries colour weights: area-weighted from its faces, blurred twice over the mesh.
  - The `paint` material takes the strongest weight per pixel, so borders are smooth curves through the triangles.
  - Deck planks (a seam every 0.07 across) and the hat's skull-and-crossbones (`tex/hat.png`, projected onto the
    crown's front) are drawn per pixel too.
  - `render_passes.py` reads the material's `ALB` node for the albedo pass.
- **`build_v9.py`, modelled pieces** (clean geometry instead of paint):
  - almond eyes with a pupil toward the nose and a body-coloured brow cutting the top, for an angry look
  - sabres hanging from the muzzle's front corners
  - claws on the toe tips
  - a gold balustrade (rail on posts) around the deck
  - six black spikes with gold feet on the shell
  - a short tail with a gold tip
  - the stern ornament: a gold skull facing aft with Den sorte dame's red-rimmed eye windows and an open grin with
    two rows of teeth, crowned by gold spikes
  - masts in dark wood
- **The pounce, rebuilt.** Front legs reach forward and up (45/80/96 degrees), nearly parallel. The paws bend down so
  the claws face the camera, and the hind legs stretch back. v8 spread the legs sideways like a lizard.
- **`pixelize.py` with `SAB_STYLE=hooh`:**
  - Ho-Oh's style: the silhouette and part edges take the colour's own darker tone (`DARK1`) instead of black ink
  - a muted moonlit palette: black, red, gold, white and two woods
  - darker thresholds, so the body reads black
  - eyes, pupils, nose, sabres and claws keep their pixels
- **`viewer.py`.** Writes a copy of a `.blend` that opens nicely in Blender: Material Preview, the rig hidden, a
  three-quarter view. `pose_preview.py` renders frames × angles with the real materials (EEVEE).

Build: `SAB_BLEND=../h3d/sab_v9.blend SAB_STYLE=hooh SAB_CLEAN=1 SAB_DROPS=5 SAB_DROPR=0.09,0.14
LABEL_B="Sabertann v9" h3d/build_v7_variant.sh v9 24 9 15.2`
- Budget: 1010 of 1024 tiles; worst line 1236 of 2130 cycles.
- ROM: `~/sigma-origin/rc8/sabertann_v9.nds`
- To look at the model in Blender: `h3d/se_sabertann_v9.blend`

Results (gitignored): `sabertann_intro_v9.mp4`/`.gif`, `sabertann_v9_rundt.png` (four views, as on the turnaround
sheet), `sabertann_v9_bilder.png`.

Known gaps:
- the last pounce frames are scaled 2x and chunky (as Ho-Oh's are), and the body is still a large dark mass there
- the hat crown is a tall block seen from the side
- the small rear sail and the flag keep Hunyuan's ragged edges
- from the intro's low camera the deck shows only as a thin strip
- a better base would be a multi-view mesh (Hunyuan3D-2mv) from the turnaround sheet, with colours projected from
  its views

## Version 10: a multi-view model from Arvind's turnaround sheet (2026-11-13)

Arvind OK'd the step suggested after v9: build the 3D shape from all of his turnaround views, not from a single picture.
- The model is **Hunyuan3D-2mv** (Tencent, the same community licence as 2.1).
  - Location: `D:\LocalAI\ComfyUI\models\checkpoints\hunyuan3d-dit-v2-mv.safetensors`, 4.9 GB.
  - ComfyUI's native `Hunyuan3Dv2ConditioningMultiView` takes front, left, back and right CLIP-vision encodings.
- Sabertann has **no tail**. Arvind said so; the turnaround sheet drew one.

Steps (`mv/`; his pictures stay local in `~/sigma-origin/title3d/mv/ref`, not in the repo):
- **`prep_views.py SHEET OUTDIR`.** Cuts the sheet into front, side, back and 3/4:
  - the paper and the floor shadow are removed by a flood fill that stops at the ink lines
  - all views share one scale and one vertical placement
  - the right view is the side view mirrored
- **`no_tail.py`.** Paints the tail out of the side views; the rump stays round.
- **`mv2mesh.py F L B R OUT.glb`.**
  - Runs at octree 384, 50 steps, latent 3072; about 2 minutes on the 5080.
  - Swapping left and right gives the same body, because the views are symmetric, but different sails. The run with
    square sails across the ship (`mvD`) was chosen, because those face the intro camera.
  - Frame: the creature faces -Y, +X is its left, Z is up.
- **`h3d/prep.py`** cleans and decimates the mesh to 160k faces. **`vis4.py`** records which vertices each view sees
  (ray casts).
- **`paint_mv.py`.** Colours come straight from his drawings:
  - Each view is fitted to the mesh silhouette (scale and offset); only the body is used, since the sails differ.
  - Each vertex takes the colour class voted by the views that see it, weighted by how squarely they see it.
  - These parts are set by shape, where a drawing cannot land exactly: masts are wood, sabres are white along their
    axis, the hat is black with a gold rim on the brim's top edge, and the nose is gold.
  - It also paints the deck planks on the shell's up-facing top and records the deck outline.
- **`eyes.py`.** Places the eyes from where they sit in the side view.
- **`build_v10.py`.** Same tools as v9:
  - per-pixel paint from blurred colour weights
  - modelled eyes with an angry brow
  - the gold deck balustrade
  - the hat emblem projected onto the crown front
  - a skull and crossbones on the square sails
  - The rig uses joints measured on this mesh (`joints_D.json`).
  - The pounce keeps the paws at chin height and out to the sides, so the face and sabres stay in view.
- **`run_v10.sh NAME`.** Runs eyes, clean, build and a look in one go.

Build: `SAB_BLEND=../mv/sab_v10.blend SAB_STYLE=hooh SAB_CLEAN=1 SAB_DROPS=5 SAB_DROPR=0.09,0.14
LABEL_B="Sabertann v10" h3d/build_v7_variant.sh v10 24 9 17.5`
- PPU0 is 17.5, since this model is lower than v9's.
- Budget: 933 of 1024 tiles; worst line 1458 of 2130 cycles.
- ROM: `~/sigma-origin/rc8/sabertann_v10.nds`
- To look at the model in Blender: `mv/se_sabertann_v10.blend`

Known gaps:
- the gold stern ornament and the flagpole are still a little blotchy
- the shell's spikes show only as shape, without their gold feet
- the last pounce frames are scaled 2x and chunky, as Ho-Oh's are

## Version 11: eyes on the face, white claws, the stern skull, head-on, Lugia's night colours (2026-11-13)

Arvind's notes on v10:
- the eyes sit on the sides and there is no brow ridge
- no white claws
- the hat needs its gold edge
- no skull on the back
- he does not run straight at the camera
- the flag and the mast are off
- the colours and the light are not like Lugia's or Ho-Oh's
- the pupils are white

SoulSilver's Lugia, from his ROM (kept local), was studied for the light:
- the whole sprite is drawn in the scene's teal night light, with low contrast and light from the front
- only the eyes glow: tiny yellow glints, the same yellow as Ho-Oh's eyes

What changed (same `mv/` pipeline; `build_v10.py` now builds v11):
- **Eyes.**
  - They are placed from the front view (`eyes.py` with `EYE_VIEW=front`, `EYE_Z=0.135`): narrow eyes on the face
    under the hat brim.
  - The inner ends are lower (angry), with a dark pupil at the inner end and a grey brow ridge over each eye.
  - In the sprite they are Lugia/Ho-Oh glints (palette 14) with dark pupils.
- **Claws.**
  - Modelled white claws sit on the toe tips: four in front and three behind as found, from a paw-outline search in
    `paint_mv.py`.
  - The water line went down from 0.16 to 0.03. The claws had been under water, hidden by the water holdout.
- **The hat's gold edge** is a clean gold tube along the brim's top-view outline, not paint.
- **The gold skull** sits at the aft end of the gold stern ornament, facing aft. The ornament's fin stays as a crest
  above it, and the ornament is all gold.
- **Masts and flag.** The mast is followed up its whole (leaning) length, slice by slice, and is wood. The flag is a
  part of its own with the gold skull texture.
- **Head-on run.** Camera yaw 0 (was 24), so he runs straight at the viewer like Ho-Oh and Lugia.
- **`pixelize.py` with `SAB_STYLE=lugia`:**
  - every colour is pulled toward the night blue
  - muted gold and red
  - light from the front
  - no rim light
  - Ho-Oh-style edges in the colour's own darker tone, not black

Build: `SAB_BLEND=../mv/sab_v11.blend SAB_STYLE=lugia SAB_CLEAN=1 SAB_DROPS=5 SAB_DROPR=0.09,0.14
LABEL_B="Sabertann v11" h3d/build_v7_variant.sh v11 0 9 17.5`
- To look at the model in Blender: `mv/se_sabertann_v11.blend`
- Budget: 816 of 1024 tiles; worst line 1194 of 2130 cycles. Head-on, he is narrower.
- ROM: `~/sigma-origin/rc8/sabertann_v11.nds`
- Results (gitignored): `sabertann_intro_v11.mp4`, `sabertann_v11_bilder.png`, `sabertann_v11_rundt.png`

## Version 12: glowing eyes, an outward pounce, no stuck toes, moving through the fade (2026-11-13)

Arvind's notes on v11:
- Ho-Oh's eyes are not gold: they glow and have no pupils
- something odd happens at the paws in the leap
- the forelegs should go out, not in, like a real jumper
- in the fade to white Ho-Oh keeps flying, but Sabertann stood still

Fixes:
- **Eyes.** They are emissive pale light (`eyeglow`) with no pupils (`SAB_PUPIL=1` brings the pupils back). Palette
  14 is now (255,246,206), brighter than any gold.
- **Stuck toes.** The first tusk rule (white, in front, low) had also caught the white toe tips. Those vertices were
  bound rigidly to the head bone and stretched into long black rods in the leap. The tusk rule now stops at z -0.42.
- **Outward forelegs.** The spread sign came over from v9, where the left side was on the model's -x. In v10's frame
  the left side is +X, so the paws had swung inward. Fixed, and frames 6 and 7 were retuned so the paws are out to the
  sides.
- **Moving through the fade** (`build_saber_v5.py` with `SAB_AIRLOOP=1`):
  - after the leap, the cells alternate between leap frames 6 and 7, so the paws pump
  - he keeps growing slowly up to the affine cap
  - he rises, sways and rolls gently until the end
  - before this he held the last frame at the cap

Build: `SAB_AIRLOOP=1 SAB_BLEND=../mv/sab_v12.blend SAB_STYLE=lugia SAB_CLEAN=1 SAB_DROPS=5 SAB_DROPR=0.09,0.14
LABEL_B="Sabertann v12" h3d/build_v7_variant.sh v12 0 9 17.5`
- To look at the model in Blender: `mv/se_sabertann_v12.blend`
- Budget: 823 of 1024 tiles; worst line 1246 of 2130 cycles.
- ROM: `~/sigma-origin/rc8/sabertann_v12.nds`
- Results (gitignored): `sabertann_intro_v12.mp4`, `sabertann_v12_bilder.png`

## Version 13: he jumps over you, and new clouds (2026-11-13)

Arvind's notes on v12:
- the air loop during the fade looked silly; he should carry on and jump over the viewer
- the clouds were flat and much worse than the ones in Ho-Oh's scene

What changed:
- **The jump over the viewer** cannot be a sprite moving up the screen. Double-size affine pieces wrap around (top to
  bottom) once their box goes more than 64 px above the screen, and at the zoom cap he has only about 20 px of room.
  So the motion is in the pictures instead:
  - two more leap frames, 8 and 9: he rises out through the top of the picture, pitched back (chest and belly
    showing), forelegs reaching over, head turned down to keep glaring at you
  - the splash stays behind
  - `build_saber_v5.py` with `SAB_OVER=1` and `SAB_F0=1..9` plays them during the fade
  - the air loop (`SAB_AIRLOOP`) is dropped
- **Clouds** (`night/paint.py`), after Ho-Oh's scene:
  - cumulus banks made of ellipse "puffs", each shaded as a dome, with flat bottoms and long tails reaching toward
    the moon
  - 6 tones: a dark blue upper part, a lit body, and a broad moonlit underside band whose lowest row is silver near
    the moon
  - the old version is kept as `night/paint_v12.py` in the work folder
- **Stray white** on the mesh (the drawing's sabres projected onto the chest behind them) goes to black. On the mesh,
  white stays only on sails, flag and sabres.

- **A livelier run.** Arvind said the run was super stiff. Most of the approach used only 1 picture (far: LOD2) or
  2 (middle: LOD1), and only the legs moved.
  - The run is now a cat's bound in 4 key poses: gather, push, stretch, land.
  - Front and hind legs work in pairs, with the right pair a little behind the left.
  - The body pitches and rises with each stride, the head nods less than the body, and the mast lags a beat.
  - All three detail levels get the 4 run pictures (`SAB_F1=1,2,3,4`, `SAB_F2=1,2,3,4`). PPU0 went down to 16.0 to
    pay for the extra tiles.

- **Tiles.**
  - With 9 frames up close and 4 at each of the other two levels, the total was 1111 of 1024.
  - Leap frame 5 is left out (`SAB_NOF5=1`): the run's gather pose leads into frame 6.
  - The farthest level (LOD2) keeps 2 run frames.
  - Result: 993 of 1024 tiles; worst line 1120 of 2130 cycles.
  - `mv/finish_variant.sh` reruns only the steps after the renders.

Build: `SAB_BLEND=../mv/sab_v13.blend SAB_STYLE=lugia SAB_CLEAN=1 SAB_DROPS=5 SAB_DROPR=0.09,0.14
h3d/render_v7.sh`, then `SAB_PPU0=16.0 SAB_OVER=1 SAB_NOF5=1 SAB_F0=1,2,3,4,6,7,8,9 SAB_F1=1,2,3,4 SAB_F2=1,3
LABEL_B="Sabertann v13" mv/finish_variant.sh v13`. Run the render with `SAB_YAW=0 SAB_EL=9 SAB_PPU0=16.0
SAB_PPU1=11 SAB_PPU2=7`.
- ROM: `~/sigma-origin/rc8/sabertann_v13.nds`
- To look at the model in Blender: `mv/se_sabertann_v13.blend`

## Version 14: the attack, layered clouds (2026-11-13)

Arvind's notes on v13:
- the jump over the viewer looked thick
- the jump should be an attack at the viewer instead
- Ho-Oh's clouds are layers with slightly see-through highlights

What changed:
- **Frames 8 and 9 are now the attack.** He lunges straight at the camera, body stretched out level, forelegs thrust
  forward with the claws open, hind legs flung back, head low.
- **Clouds** (`night/paint.py`) come in two layers:
  - a pale back layer, higher and further out, at 35-55 % opacity
  - the front banks at 85 % opacity, with highlights at 60 %
  - each layer is blended over what lies below it and then snapped to the scene's own colours, so the sky's glow shows
    through in bands
  - v13's version is kept as `night/paint_v13.py` in the work folder

Build: as v13, with `SAB_BLEND=../mv/sab_v14.blend` and the name `v14`, through `h3d/build_v7_variant.sh v14 0 9 16.0`
with the v13 env.
- Budget: 958 of 1024 tiles; worst line 1120 of 2130 cycles.
- ROM: `~/sigma-origin/rc8/sabertann_v14.nds`
- To look at the model in Blender: `mv/se_sabertann_v14.blend`

## Version 15: the roar (2026-11-13)

Arvind wanted to see the mouth open in the attack, roaring or going for a bite.
- **A jaw bone**, hinged at the mouth corners. The lower jaw (below the lip line at z -0.03, in front of y -0.64) goes
  to it with soft edges toward the throat and the sides.
- **The lips part.** The mesh is one closed skin, so opening the jaw only stretched a membrane over the mouth. Faces
  across the lip line are now cut. Shut, that leaves a thin mouth line, as in the drawing.
- **Inside the mouth:** a red cavity and palate (on the head), and a tongue and four small lower teeth (on the jaw).
- **How far it opens:** 14° in frame 7, 45° in frame 8 and 58° in frame 9, with the head tipped up a little so the
  mouth faces the camera.

Build: as v14, with `SAB_BLEND=../mv/sab_v15.blend` and the name `v15`.
- Budget: 958/1024; worst line 1120 of 2130 cycles.
- ROM: `~/sigma-origin/rc8/sabertann_v15.nds`
- To look at the model in Blender: `mv/se_sabertann_v15.blend`

## Sabertann v22 and Gravriel v16: locked (2026-11-14)

Arvind locked both after the rounds on 2026-11-14 (lighting, outline, clouds, moon, horizon, motion, foreground).
What Ho-Oh and Lugia taught us, applied to both scenes:
- **No outline.** Silhouette edges are the inner colour a shade darker. The figures are backlit, a little darker than
  the sky, in the scene's own hues.
- **Clouds** (`night/skykit.py` `wisps2`): soft-edged banks with an 8-step ramp from a dark top to a lit underside, and
  round puffs on top. Ho-Oh's clouds use 10–12 tones.
- **Horizon** (`hz_curve`, `warp_sea`): about 6 px higher at the edges than in the middle, as in SoulSilver.
- **Moon** (`moon4`): a continuous albedo (noise-warped maria at their real places, mottling, rayed craters, limb
  darkening), area-averaged and only then cut to 6 tones. Hard thresholds looked like "squares and circles".
- **Motion:** the moon rises with its glow; the foreground sinks; clouds and sea stand still.

**Sabertann v22:** v15's frames, relit by `night/saber_light.py` (palette only, no rim), in the scene from
`night/paint_v16.py`. The glow is part of the moon sprite, so it rises with the moon.
Build: `SNAME=v22 night/build_sab16.sh`. ROM `~/sigma-origin/rc8/sabertann_v22.nds`, md5 `75740de4a630a361732bf64f19045b64`.

**Gravriel v16:** a 2D sprite from his front view (`grav/grav2d.py`, backlit grade plus `harmonize` into the scene's
blue-green) rising out of the sea (`grav/build_grav4.py`): rings before he surfaces, foam at his sides, a swaying
reflection in his own colours, three heaves with sink-backs, drips, then a ghost-green checker dissolve.
- Scene `night/paint_grav10.py`: BG3 still (sky, clouds, sea, far wrecks), BG2 the moon (+16 rise), BG1 the near
  wreckage (the game's own scroll). The water in front of his waist is a strip in his own sprite (palette 2).
- Overlay 56 is patched only while building (`grav/patch_prio.py`): moon-sprite priority, the bird at timer 5 with a
  longer wait so the fade time is unchanged, BG2 rise, and 4 sprite palettes. It is reverted after the build.
- Build: `grav/build_v4.sh v16` (the defaults are v16's). 890/1024 tiles. ROM `~/sigma-origin/rc8/gravriel_v16.nds`,
  md5 `ab4acb0b25f920d3e632016d9448c0bd`.
- Both ROMs were rebuilt from these scripts on 2026-11-14 and matched byte for byte. `NO_SHOTS=1` builds the ROM only.

## Scene 3 deer strips v11: locked (2026-11-15)

Rockedeer, Moosus and Felk replace Entei, Suicune and Raikou in the three strips of scene 3 (a/2/6/2: palette 39, shared BG
tiles 40, screens 48/47/49). Order and directions as the originals: Rockedeer on top looking left (Entei), Moosus in the middle
head-on (Suicune), Felk at the bottom looking right (Raikou). Scripts in `deer/`; work folder `~/sigma-origin/title3d/deer`.

How the pictures were made (1536x384 each, kept locally, not in the repo):
- **Rockedeer and Felk** (`deer/gen_copystyle.py rockedeer 1`, `felk 5`): Qwen-Image 2.1 gets our design as `<image1>` and the
  original strip of the same slot (6x nearest from `inv/bg048/049`, local only) as `<image2>`, as a style reference only; the
  prompt forbids the old beast's shapes and colours. Felk's design is Arvind's own picture (`scratch_intro/src/felk_arvind6.png`).
  Our design FIRST is what made this work; with the original first (v3, `deer/gen_swap.py`) the old beast leaked in.
- **Moosus** (`deer/gen_swap.py moosus 2`, v3): Qwen replaced the beast in an original strip; Arvind liked it best.
- md5 of the pictures: `copy/rockedeer_1.png` a86ab37284ca5511b47229e1908283ac, `swap/moosus_2.png`
  7cd64e479472f77df321e0328b766c4b, `copy/felk_5.png` e9230e16fda5edaf738afbe68fa687a2.

The strips (`deer/build_strips.py IN.narc OUT.narc`, defaults are v11's): a 4:1 window round the eyes, zoomed so the creature
covers ~33 % of the band (as the originals), graded to the originals' luma (~66), 9 flat colours by k-means, tiles deduped with
flips into the slots only the beasts used plus never-used slots >= 688 (lower never-used slots are overwritten at runtime).
**Eyes** (`stamp_eyes`): the originals' eye is one flat almond of bright gold with a crisp 1-px black ring (Entei one side eye,
Suicune two, Raikou one, 30-40 px); ours are drawn the same way at eye centres measured in our pictures (32 / 14+14 / 32 px).
`deer/measure.py` prints the numbers for originals and ours. Tried and dropped on the way (kept as options): our own line
art (`DEER_LINES`, v2), Sugimori/Qwen style LoRAs (`style_test.py`, v6-v7), a cel pass with base + shadow per material
(`STYLE3=1`, v8-v9: right on painterly pictures, noisy on already-clean ones).

Build: `python deer/build_strips.py night/out_sabv22.narc deer/out_intro_wip.narc` (narc md5 `8268ed9823264abad7bcd716d1bcf006`),
copied to `rc8/x_night/files/a/2/6/2` and `dsrom build`. ROM `~/sigma-origin/rc8/intro_hjort_v11.nds`, md5
`9713f7feb4b250ba52c26f81da6210a9`; rebuilt from these scripts on 2026-11-15 and matched byte for byte. It sits on Sabertann
v22's narc only: Gravriel v16 is not in this ROM yet.

## Scene 5 night fjord v8: Moosus on the rock (2026-11-15)

Suicune standing on its rock by the sea is now Moosus, on a night fjord under the northern lights. Arvind approved v8.
Scripts are in `sc5/`. Work folder: `~/sigma-origin/title3d/sc5`.

### What it replaces in `a/2/6/2`

- **Screen 62: Suicune's rock.** Cells x0-4, y17-23. Charset 60 tiles 2-30, plus tiles 444-459. Palette 31 bank 3.
- **Screen 64: bottom screen sky, fjord and sea.** Map rows 12-51. Charset 60. Palette 31 banks 0, 4, 5, 2 and 6.
- **Screen 61: top screen sky.** Map rows 0-44. Charset 59. Palette 39 banks 7 and 8.
  - Bank 0 is shared with the deer strips, so it is not used.
  - Rows 320+ were visible as a blue strip, which is why rows up to 44 are written.
- **Screen 63: the light flare.** Its shape is kept. It moves to palette 39 bank 9 and gets night colours (mint and teal).
  - It used bank 1 colours 10-14, but `deer/build_strips.py` writes the whole of bank 1 for Rockedeer. Since scene 3 the
    flare had shown as black and gold, also in the locked v11 ROM.
- **Charset 60's spare room.** It holds 768 tiles and the original fills only 0-443. Tiles 444-767 are free, and this was
  tested in the emulator.

### Scroll, measured in the emulator

- While the scene plays, the bottom screen shows screen 64 rows o..o+191, in `bg64` coordinates (map rows 96+), with o
  going from 64 to 29.
- The top screen shows screen 61 rows o+96..o+287.
- So the two screens meet when canvas row = screen 61 row = screen 64 row + 288. The horizon is at canvas row 496.

### Moosus: a 3D model rendered to a sprite (`sc5/m3d/`)

The earlier routes did not work:
- Qwen swaps (v1-v2).
- Back-sprite tracing.
- An SDXL sprite LoRA.
- Qwen artwork run through `pixel_render` (v3).

What works:
1. **`gen_ref.py 2`.** Qwen draws a clean full-body Moosus on white (`ref_2.png`, md5 e58b27a4…), from the DS front and
   Arvind's drawing.
2. **`h3d/img2mesh.py`.** Hunyuan3D 2.1 makes the mesh (`mesh_2.glb`, md5 36f18016…). `h3d/prep.py` then cleans it to
   120k faces.
3. **`colour_fit.py`.** `h3d/fit_cam.py` finds the view the picture was drawn from (az -38, el 20). The script colours
   the mesh through that view with a z-buffer and a mirror pass. It gives four classes: pale, brown, crown and dark
   (`colf_2.npz`, md5 2b4740c0…).
4. **`render_view.py COL OUT 188 8`.** Blender Cycles renders emission-only data passes as 16-bit PNG: class, crown
   height, depth and a camera-space normal. Read them with cv2; in Cycles camera space +Z points away from the viewer.
   - Az 188 is Suicune's angle: a side profile facing right, with the body cut off by the left edge.
5. **`sprite.py PASS N188.png 40 tip:38 night`** (env `SC5_AUT=0.3 SC5_AMT=0.55`).
   - A majority shrink to 40 px tall.
   - Each material gets a night base, one shadow layer (the originals' cel rule) and a green layer where the northern
     lights hit it. The crown glows.
   - Inner lines are drawn where the depth jumps. The outline is dark navy.
   - It sits on the original rock, relit to slate with a teal top. That rock comes from the local `orig_crop.png` and
     is not in the repo.
   - Result: 10 colours of its own, `N188.png` md5 72234201….
6. **`build_sc5.py`** (env `SC5_EXTRA=16`). Writes screen 62. When the picture has 15 colours or fewer it keeps them
   exactly.

### Background: drawn by rules (`sc5/bg/`)

**`paint_night.py 2`** draws the background in the originals' style: flat bands, stepped ragged edges, few colours and no
dithering. A painted picture shrunk to size looked like a pixelated photo.
- **Sky.** Night bands that curve down at the sides (the original's dome). Stars sit on three spots inside a tile, so
  their tiles repeat.
- **Northern lights.** Curtains of vertical rays: runs of 1-3 px, a bright mint hem, greens fading upward and a sparse
  violet fringe. There is a second, fainter curtain far away.
- **Fjord (`headland()`).**
  - Steep glacier-cut walls straight into the water, with rounded shoulders, domed sloping tops and snow fields.
  - Granite ledges and gullies, and cliff faces lit by the northern lights.
  - Far, mid and near headlands alternate left and right. There is a two-peaked snowy end and a waterfall.
- **Water.** Ragged bands, the walls mirrored dark, and a green glitter path.
- Output: `night61.png` md5 0f5cbdf4…, `night64.png` md5 2255564e….

**`build_bg.py IN OUT 16`** dedupes tiles with flips and packs tiles into 15-colour banks with a greedy fit. It uses 366
of 462 tiles on screen 61 and 512 of 722 on screen 64. It also moves the flare.

### Build

Run in this order:
1. `build_sc5.py deer/out_intro_wip.narc A N188_x8.png` (N188 on magenta, 8x nearest).
2. `bg/build_bg.py A B 16`. narc md5 `e37fa15d85587553c320fa556591c798`.
3. Copy it to `rc8/x_night/files/a/2/6/2` and run `dsrom build`.

ROM `~/sigma-origin/rc8/intro_sc5_v8.nds`, md5 `c3411fa8c2379173847c9ab0cdca77e5`. It was rebuilt from these scripts on
2026-11-15 and matched byte for byte (the Blender pass PNGs differ, but the sprite they produce is identical). It sits on
scene 3 v11 and Sabertann v22. Gravriel v16 is not in this ROM yet.

## Title screen bottom clips: Warrallier and Monarkhan (2026-11-15)

The bottom of the title screen (`a/2/6/4`) plays three clips of 50 frames each. Members 14-163 are 256x192 8bpp NCGR frames
(tiled, uncompressed) with the shared palette 13. Clip 0 is Blastoise, clip 1 Charizard and clip 2 Venusaur. In the game the
green clip plays first, then orange, then blue.

Our final evolutions replace two of the starters:
- **Clip 0: Warrallier** (Water) replaces Blastoise. Arvind picked flash strength B.
- **Clip 1: Monarkhan** (Fire) replaces Charizard. The design is Arvind's drawing.
- **Clip 2: Venusaur** waits for Leafaxer.

There is no trainer yet. A trainer can be added later as one more layer with its own depth.
Scripts are in `title/`. Work folder: `~/sigma-origin/title3d/title`.

### How the originals work

`dump.py` dumps the frames, and `tittel_analyse.png` shows the analysis.
- **The picture does not move.** The camera is still, and each clip is one picture.
- **A light plane sweeps left to right through 3D.** A pixel lights at about `T0 + B*(x - K*near)`, so the edge of the light
  bends over the forms. It stays lit for about 14 frames, with one darker tone on its first and last lit frame.
- **Colour.** Each clip is one hue in 6-7 tones, plus black lines, white and greys. Only 28 of the 256 palette entries are
  used, so our clips reuse each clip's own entries and palette 13 is not touched.
- **Effect layers live longer than the sweep.**
  - Blastoise's cannon flashes on every other frame. A pale disc swells and shrinks, the flash brightens what is around it,
    and stars twinkle.
  - Charizard starts with fire in the dark that spreads into a glowing rim along its head.

### `render_clip.py COMP DEPTH OUT CLIP`

It makes one clip from a still picture and a depth map, both drawn by Qwen 2.1 edit:
- tones ranked inside the figure, plus 20 % from the depth
- black lines where a pixel is much darker than its surroundings
- the sweep
- 3D point lights: Lambert shading on normals taken from the depth map, falling off with 3D distance

Options are set with environment variables:
- **Warrallier (orb):**
  - `T_ORB_REF`/`T_ORB_DRAW=0`: the flash sits where a ball was, without the ball.
  - `T_FL_START`: when the flashes start.
  - `T_GAIN`/`T_REACH`/`T_FULL`: how strong and how far the flash light goes. Revealed pixels get their own sweep tone.
  - `T_HAND_*`: the fingers drawn in front of the flash.
  - Stars and a water drop are our own shapes.
- **Monarkhan (fire):**
  - `T_FLAMES`: a mask of the flames. Each flame is a layer that sways, licks up and has rising heat noise.
  - Each flame is also a point light with a rim/back term (`T_FIRE_RIM`, `T_FIRE_REACH`), so edges facing it glow like
    Charizard's fire rim.
  - `T_MAT=1` (`matclass.py`): tones per material (red body, yellow wings, brown spots, pink nose, white claws), so the yellow
    wings do not turn white.
  - `T_FUR`: a mask of the fur, drawn with gold tones. It shines for 3 frames after the light reaches it, and glints twinkle
    on it.

### Pictures

These are local, not in the repo:
- **Warrallier:**
  - `war/gen_comp.py v2 5` drew `comp2_5` (md5 0d9fee4f…). It is head-on, with white eyes, holding a water orb.
  - `war/gen_noorb.py 1` drew `noorb_1` (8d313ad5…), the same picture with the ball removed.
  - `war/gen_depth.py noorb_1 depth3_2 2` drew the depth map (43e73cb7…).
- **Monarkhan:**
  - The design is `monarkhan_design.png` (a31f80ff…).
  - `mon/gen_comp.py v3 4` drew `comp3_4`: an arched C neck, the mane hiding the eyes, free floating flames.
  - `mon/gen_edit.py 5` then drew `comp5_5` (230bd960…): a thick red wing arm and bigger flames.
  - `TAGM=5 FUR=1 mon/gen_maps.py comp5_5 1` and seed 2 drew `depth5_2` (c9d6467c…), `flames5_2` (f73623e3…) and `fur5_1`
    (5618af82…).
- Original frames were shown to Qwen as style references, locally only.

### Build

```
T_FULL=0.8 T_T0=11 T_GAIN=1.8 T_REACH=1.6 T_HAND_DN=0.45 T_HAND_R=6 T_HAND_X=1.9 T_ORB_REF=war/comp2_5.png T_ORB_DRAW=0 \
  python title/render_clip.py war/noorb_1.png war/depth3_2.png war/clip9b 0
T_MAT=1 T_FUR=mon/fur5_1.png T_FIRE_RIM=3.5 T_FIRE_REACH=2.6 T_ORB=0 T_FLAMES=mon/flames5_2.png T_T0=6 T_B=0.072 \
  python title/render_clip.py mon/comp5_5.png mon/depth5_2.png mon/clip5 1
python title/build_title.py VANILLA_a264 OUT 0=war/clip9b 1=mon/clip5
```

- The narc md5 is `b4d3a0fad15354f1553746f03d97c3f1`.
- Copy it to `files/a/2/6/4`, next to scene 5 v8's `a/2/6/2`, and run `dsrom build`.
- ROM `~/sigma-origin/rc8/title_mon_v5.nds`, md5 `525e263304aca5be1d7397de2feb862f`. It was rebuilt from these scripts and
  matched byte for byte.
- That ROM has Sabertann v22, the deer v11, scene 5 v8 and both title clips. Gravriel v16 is not in it.

## Legend cutscenes: Ho-Oh and Lugia (analysis, 2026-11-15)

Arvind: Sabertann takes Ho-Oh's role, Gravriel takes Lugia's. Nothing is replaced yet; these tools find and record the scenes.
Work folder `~/sigma-origin/title3d/legend` and `~/sigma-origin/legend_test` (local only: game data, test ROMs, recordings).

- **The birds** are 2D: `a/0/8/1` 210 `hou_obj01` and 211 `lug_obj01`, 7 frames of 64x64, 4 bpp, one palette, front view
  (1-5 wingbeat, 6 wings folded, 7 cry). They are also shown big in close-ups (Ho-Oh past the sun, Lugia out of the waterfall).
  Lugia also has 6 translucent 64x64 silhouette frames (`a/1/7/4` 28). The wing items have 4-frame 32x32 textures
  (`a/1/7/4` 55 Rainbow Wing, 65 Silver Wing). The rest of `a/1/7/4` (pret `files/demo/legend`) is bells, flashes, rings,
  leaves and waves.
- **Scripts** (`a/0/1/2` 21 Bell Tower roof, map 340; 104 Whirl Islands, map 244): Origin plays the Kimono Girls' ceremony
  for both. Ho-Oh is summoned, caught by Team Rocket, and later comes back as a gift at level 95. Lugia is woken by Lawrence and
  caught by him; later the ceremony with the Tidal Bell, then a battle. The cutscene code (`legend_cutscene_camera.c`) branches on
  the game version, so the Lugia scene runs HeartGold paths (autumn leaves in the cave, yellow speckles over Lugia).
- **Tools** (`legend/`): `dump.py` (list and decode every texture of a NARC), `dump_ow.py` (overworld sprite frames),
  `find_ow.py`, `test_sheet.py` (our intro frames shrunk next to the originals), `scrdis.py` (script disassembler from pret's
  `asm/macros/script.inc`), `zev.py` (zone events), `build_jump.py` (a test ROM: walk down the stairs from savestate
  `lw/g7.dst` and a frame script warps to the scene and starts it; the NARC is written in place with `inplace.py` because a
  rebuilt ROM breaks savestates), `to_video.sh` (shots to mp4, no sound).
- Ho-Oh: `build_jump.py ROM OUT 340 15 18 282 8 0x40a9 4 -580 -2336 +1140 +1366`. Lugia needs an extra script entry that
  sets a temp var and goes to the dancer's own script (Satsuki asks, answer yes): `JUMP_BASE=y/a012_lug_base2 ... 244 16 35
  365 14 0x4001 0 -581 +579 +1366 +2333`. Map ids are pret's `include/constants/maps.h`.
- **3D Sabertann in Ho-Oh's film** (`a/2/4/3`, the Clear Bell film; see `docs/LEGEND_CUTSCENES.md`). The film is an exported
  3D scene: Ho-Oh is joint1..joint27 inside each shot model. We replace him the same way the game made him: a low-poly,
  rigged model with its own walk animation.
  1. Model in Blender (`sab3d/`): `blender -b sab_v15.blend --python export_parts3.py -- pt7 128 900 0.8 0.7` (parts in one
     octree-then-voxel remesh, stern skull moved in and up, claw cones, eye quads with their own UVs, per-vertex bones,
     three texture groups like Ho-Oh's: body 128x128, head 64x64, sails 32x64), then `python shade_tex3.py pt7` (flat cel
     shading in the DS sprite's colours plus wood tones, the hand-drawn grumpy eye). Check with `preview_tex2.py pt7 OUT.png`
     and `preview_head.py pt7 OUT.png`.
  2. Walk: `python walkcycle.py bones.json bones_walk2.json 16 -12 44 70` (walking on air, nose up).
  3. Film: for each member pair (0 1, 5 6, 10 11, 15 16, 19 20, 23 24) `ROLL=1 PATHFRAME=1 rig3d.py IN OUT sab3d/pt7
     sab3d/bones_walk2.json SCENE BCA 340 1,...,16 3`, then `pack_shared.py OUT FINAL 1=6 11=6 16=20 24=20` (the three
     times of day share one animation) and `inplace.py` into the test ROM. All six shots must be built: the emulator's clock
     is the real time and picks the variant.
- **Field sprite that comes down** (`a/0/8/1` 210): `sab/eyes_fix2.py 5` (angry, focused, with a lit brow ridge; v1 `eyes_fix.py b` was too flat) swaps the gold hat studs that read as yellow eyes
  for the concept's grumpy eyes under the brim (white, black pupil, brow sloping to the nose), then `write_ow.py ... 210
  sab/pxd_2_pal.npy sab/eyes2/f{1..7}_idx_5.npy`. `hover_patch.py OV002 ROM_IN ROM_OUT 20` makes the bird land 20 units above
  its map object (overlay 2, Task_BirdFinalApproach: yEnd = pos.y + 20; the dead SoulSilver branch makes room), so he
  hovers above Satsuki instead of standing behind her. Test ROM `legend_test/jump_hooh2_hover.nds`.
- **Ho-Oh's glow** is part of Ho-Oh's own model: the translucent `hou_tail_l` (sky shot) / `hou_tail_l2` (pagoda) disc,
  about 600 units across, plus the `hou_tail_p` sparkle quads, all on joint27. `rig3d.py` keeps those shapes, keeps
  joint27 (and its parents) on Ho-Oh's animation and takes our bones from the other joints. Found by bisecting with test
  ROMs (`RIGTEST=noshapes|nomats|notex|rigid|nomtx|minimal|noplace` switches in rig3d).
- **Flat colours like Ho-Oh** (its film textures are near-solid swatches): `sab3d/clean_tex.py pt7 pt9_6 6` (one colour per
  material, islands under 6 texels removed, no painted light bands, angry eye); check with `sab3d/preview_lit.py pt9_6 OUT`.
  Film v11: `rig3d.py ... legend/sab3d/pt9_6 legend/sab3d/bones_walk2.json SCENE BCA 460 1,...,16 3`.
- **Model built part by part (pt10, 2026-11-16)**, the way Ho-Oh's film model is built: `blender -b mv/sab_v15.blend --python
  sab3d/export_parts4.py -- sab3d/pt10` (each part remeshed and reduced on its own, the painted parts' procedural colour baked
  to their own vertices first, sails/flag as shrink-wrapped grids with their UVs, smooth normals per part, drawn eye quads),
  then `python sab3d/build_tex4.py sab3d/pt10 h3d/tex/sail.png h3d/tex/flag.png` (one palette colour per polygon as swatches,
  angry eye, sail picture in the cloth texture). Check: `sab3d/preview_lit.py` and `sab3d/preview_lit_head.py`.
- **Film v18**: `RIPPLE_R=50 rig3d.py ... sab3d/pt10 ... 460 1,...,16 3` with `LIGHTS=0 HIDE_TAIL=8` for the sky shot (members
  0/5/10: unlit like Ho-Oh there, light baked into per-vertex COLOR; hidden in the last 8 frames where the camera flies
  through him) and `LIGHTS=3` (normals, DS light) for the pagoda shot. Ho-Oh's glow disc (joint27, texture redrawn as a ring)
  becomes a ripple under each paw that touches down. Bug fixed: restores of a moved bone slot were not redirected, so three
  leg bones built on stale matrices (the long stretched streak).
- **Correct walk (v19, 2026-11-16)**: the cycle advances with the distance travelled (stride measured from the backward part of
  the cycle, never faster than one cycle per 20 frames), and in the pagoda shot each paw is locked where it touched down while
  the leg bends (analytic two-bone IK, 4-frame ease out); ripples start at each touchdown at the locked paw. Sky shot:
  `FOOTLOCK=0` (Ho-Oh is far too fast to walk). Bone tracks are full rate now (`HALFRATE=1` for the old half rate); the film
  then needs the original 437100-byte slot, so the test ROM is built from `jump_hooh2_sab.nds` (sprite eyes + hover patch, then
  the film). Hat: gold trim kept as its own part, drawn emblem quad; sail/flag: planar UVs over the whole cloth, sail picture
  stored turned, sail in front of the mast. Recordings every frame (`wait:1`) and videos at 60 fps.
- **v20 (2026-11-16)**: hand-built low-poly tricorne in `export_parts4.py` (domed crown, brim curled up between three points,
  gold edge strip in the same surface; the Hunyuan hat + floating trim ring left gaps); mast, sail and flag 0.7 forward to
  mid-back (geometry + mast/flag bones: `bones_walk3.json`); walk generator fixed: the hind legs swung with the opposite sign
  and moonwalked (`walkcycle.py`, `bones_walk4.json`); locked paws now drift 0.000-0.011 per frame. `walk_sheet.py` draws a
  cycle from the side for checking.
- **v21 (2026-11-16), cross-referenced with the concept (624.webp)**: black fur (not grey), the head lowered 18 degrees onto
  the shoulders in Blender before the export (stored pose in the .blend reset first; the posed bone matrices become the new
  rest, `bones_rest13.json`), the hat follows the head but stays fairly upright, a hand-built red domed shell with a black
  band and six gold spikes (replaces Hull/Deck/Rail), a drawn grumpy mouth decal under the gold nose, flat cloth pieces
  (yards, a lying spar) dropped, the sail raised above the shell. Command: `blender -b mv/sab_v15.blend --python
  sab3d/export_parts4.py -- sab3d/pt13 0.8 0.7 0.7 18 0.3 0.85`.
- **Walk from an existing animation**: Quaternius "Animated Animales Low Poly" (CC0, opengameart.org, 2.1 MB; kept outside
  the repo in `legend/ext/`): `extract_anim.py Cat.fbx Walking Cat_walk.json` (Blender), then `retarget_walk.py Cat_walk.json
  bones_rest13.json pt13.json bones_cat13.json -12` carries the paw paths (scaled by leg length), body bob/pitch and head nod
  onto our rig with two-bone IK. rig3d with CYCLE `1,...,40`.
- **v22 (2026-11-16), faithful to the high-poly (= Arvind's design)**: `blender -b mv/sab_v15.blend --python
  sab3d/export_parts5.py -- sab3d/pt15 0.8 0.7 0.7 1.35` reduces every part on its own (the ship hull, deck, gold rail, the
  big gold stern skull with red eye rims, 1.35x), bakes the high-poly colours, cuts the body into rigid segments per bone
  (torso, head, upper/lower legs, overlapping, DS style like Ho-Oh), retopologises the hat onto the drawn hat (gold brim band,
  emblem decal) and adds eye/mouth decals (mouth: line down from the nose, corners down). `python sab3d/build_tex6.py
  sab3d/pt15` = Ho-Oh-style swatches for flat parts + the baked picture for hull/deck/legs/skull (long strips, fits).
  Run: Quaternius Farm Animals (CC0) Horse Run, `PROFILE=horse retarget_walk.py Horse_run.json bones_rest14.json pt15.json
  bones_run14.json -8`. rig3d: unused Ho-Oh joints no longer animated (BCA half the size), the shape-to-texture assignment is
  searched (all strips placed), `HALFRATE=1`. Film 434120/437100, ROM `legend_test/jump_hooh2_v22.nds`.
- **v23 (2026-11-16), the run**: smooth joints. The body is one skin again; each point carries its two strongest high-poly
  bones and their share (`vw` from `export_parts5.py`); a point between two connected bones (25-75 %) follows a HELPER bone
  (9: shoulders, hips, elbows/knees, neck) whose matrix is the halfway rotation of both about their joint, solved per frame
  in `rig3d.py` like the other bones and carried by unused Ho-Oh joints. Their stores were freed by turning the unused
  joints' NODEDESC stores off in place (0x26 -> 0x06 + NOP, 0x66 -> 0x46 + NOP). The horse gallop is retargeted with shorter
  swings for the stocky body: `AMP=0.45 BODYAMP=0.6 PROFILE=horse retarget_walk.py ...`. The cycle steps on its own keys
  (`PHASE_SNAP=1`, pace from the distance), so poses repeat and the animation stays small; `FOOTLOCK=0`. Strips that cannot
  reach a late helper fall back to its parent bone. Film 434568/437100, ROM `legend_test/jump_hooh2_v23.nds`.
- **v24 (2026-11-16), the gallop redone**: v23's paw-path IK gave the left front leg +-48 deg and the right one +-4 deg,
  hind legs +-10 deg, and no body rocking (the Quaternius horse run has no body pitch). On screen that read as a small,
  quick shuffle. `sab3d/retarget_fk.py` now carries the source's LEG ANGLES over (upper-leg swing and knee bend in the
  side plane, relative to the source rest). Settings: front swing x0.8 (-53..41 deg); hind x0.55, 14 deg forward
  (-31..20 deg, shorter so the stocky haunches do not stretch); knee x0.9. It adds a +-7 deg rocking-horse pitch (nose
  highest while the hind legs push), the source bob, and a head that partly holds against the rock. Output: 18 keys.
  `rig3d.py` `CADENCE=36` gives a steady gallop: one stride per 36 film frames (~1.7 strides/s, like Ho-Oh's wingbeat),
  one key per 2 frames (half-rate tracks), instead of 20 frames per stride tied to the distance. Ripples now come from
  one clean touchdown per paw per stride (the paw's most-forward key), shown for the first hind paw and the last front
  paw. Before, the stance test flickered and gave ~8 per stride. Previews: `walk_sheet.py` with `SPLIT=0` (the DS
  skins per vertex) and `EL=` for a view from above.
  Build: `AMP_H=0.55 OFF_H=14 retarget_fk.py Horse_run.json bones_rest14.json bones_run17.json -8`, then rig3d with
  `CADENCE=36` and cycle `1..18`. Film 431908/437100, all 445 strips in all six shots, ROM
  `legend_test/jump_hooh2_v24.nds`.
- **v25 (2026-11-16), the hind legs** (Arvind: "bakbeina er ikke så bra"). The body was decimated as one 300-triangle piece, so the hind legs were a few points on a column under the haunch. The high-poly thigh bone covered the whole round haunch, and the shin and the big flat paw were one rigid part. Swinging the thigh dragged the flank into a slab, and the paw could only paddle.
  - `sab3d/export_parts7.py` (HINDSPLIT) makes the hind legs their own part, `BodyLeg`, from the high-poly points whose strongest bone is a hind leg, below z 0.95. The part reaches 0.3 into the haunch, so no gap opens when it swings. Only the left leg is rebuilt (44 triangles); the right one is its mirror, so both are alike. The body is remeshed without them (250 triangles).
  - `sab3d/hind_rig.py` keeps the same two bones per hind leg, because the matrix slots are full. They get new joints: a hip at the bottom of the haunch (z 0.95) and an ankle (z 0.3). The haunch stays with the body; leg and paw get helpers at the hip and the ankle.
  - `retarget_fk.py` `HIND=design` keys the hind legs by hand on the horse's timing (right leg 3 frames after the left): land forward with a flat paw, push back, kick the paw up behind, swing forward under the belly.
  - `walk_sheet.py` `ZC`/`ZS` give close-ups.
  - Build: `export_parts7.py -- pt19 0.8 0.7 0.7 1.35`, `build_tex6.py pt19`, `HIP_Z=0.95 hind_rig.py pt19 bones_rest14.json pt19r bones_rest19.json`, `retarget_fk.py Horse_run.json bones_rest19.json bones_run19.json -8`, then rig3d on `pt19r` with `CADENCE=36`.
  - Film 435160/437100, all 475 strips in all six shots, ROM `legend_test/jump_hooh2_v25.nds`.
- **v29 (2026-11-16), the ripples under the paws. LOCKED** (Arvind: "ja det ser bra ut. bare pass på at de ripple effekten under beina er gjort riktig nå 🙂 så er det en lock").
  Faults found in v25's ripples, all fixed in `rig3d.py`:
  - **Timing.** The touchdown was taken as the paw's most forward point. The front paw is furthest forward high up in its reach, so the front ring appeared ~120 units up in the air before the paw came down. Touchdown is now the key where the paw enters the lowest quarter of its own height range and stays there: hind left key 7, front left key 16 of 18.
  - **Spacing.** One ring per pair, made by the paw that lands first. Hind ring and front ring are now 18 frames apart (was 12/24), so one ring always shows.
  - **Size.** The ring joint (joint27) hangs under joint1 and inherits its 0.1 scale, so the drawn ring is `sig x 0.72 x RIPPLE_R`. Ho-Oh's disc fan is at x = -0.187 of the joint, and the bright line of the texture sits at 0.72 of the disc radius. That makes the ring paw-sized: it goes under one paw, not between two.
  - **Height.** The disc drop (`sig x 0.73 x radius`) is lifted back. The ring sits at the paw's lowest level.
  - **Placement.** While the paw stays down and pushes, the ring follows it (10 frames hind, 18 front). When the paw lifts, the ring stays where it was. In the pagoda shot he gallops nearly on the spot while Ho-Oh's path sinks, so a ring fixed at the first touch was left behind within a few frames.
  - **Checks.** `DIAG_RIPPLE=1` prints the paw heights and distances from the ring line per event. `DEBUG_RING=BL_lo` (or any paw, or `MID`) builds a test ROM with a small ring locked to that paw. Recorded side by side, the v29 ring sits where the paw-locked ring does.
  - **Build.** Same as v25 (`pt19r`, `bones_run19.json`, `ROLL=1 PATHFRAME=1 RIPPLE_R=50 HALFRATE=1 FOOTLOCK=0 CADENCE=36`, cycle 1..18 step 3, `pack_shared 1=6 11=6 16=20 24=20`, `inplace` onto `base_hover.nds`).
  - **Result.** Film 435160/437100, all 475 strips in all six shots, ROM `legend_test/jump_hooh2_v29.nds`. sha256 prefixes: film `4675ad183ae41c99`, ROM `0366de60f163ed7e`, pt19r.json `43571836d5f43ec9`, bones_run19.json `fd5dc4365a740001`.
- **v30 (2026-11-16), a ripple from every paw, where it pushes off** (Arvind on v29: "hvorfor kommer det ikke på hver pote når de lander på lufta" and "det skal se ut som det kommer en ripple effekt hvor han tråkker fra ... hver gang han presser fra for å løpe/hoppe fremover"). This replaces v29 as the lock candidate.
  - **When.** Each paw makes its own ring at its push-off: the last frame it is down, i.e. the last frame in the lowest quarter of its height range. Per stride that is front left, front right, hind left, hind right.
  - **Where.** At the spot the paw pushes from, on the paw's lowest level. The ring stays there and grows. It no longer follows the paw.
  - **Second disc.** One disc could only show one ring at a time, so `rig3d.py` RIPPLE2 adds a second one, patched in place in the render commands:
    - joint16 (Ho-Oh's tail joint, no slot) restores the world root, applies its own track and stores its matrix in a free slot. Its draw still carries our strips.
    - Right after disc 1 is drawn, that slot is restored and the same disc shape is drawn again.
    - Disc 2 comes after disc 1's POSSCALE command (0x0b), so the posScale is folded into its matrix. Without this it was 128 times too small.
    - Its NODEDESC flag is 0. The world root keeps no parent scale for scale compensation.
    - The bytes for the new commands come from repeated material commands in front of Ho-Oh's sparkle quads, and from world-root visibility checks. NOPs pad the list to its old length.
  - **Cheaper tracks.** Both discs hang on the world root, so their tracks stand still between rings. The drawn size is kept at sig x 0.72 x RIPPLE_R. Hidden discs wait, tiny, where their next ring comes. Disc tracks are written at full rate, so a ring never slides to its next spot.
  - **Ring lengths.** The two discs take turns. Front rings live 10 frames and hind rings 18.
  - **Checks.**
    - `DEBUG_RING2=<paw>` locks disc 2 to a paw (`DEBUG_RING` does disc 1).
    - The hind rings were recorded against paw-locked test rings: each starts where its paw is at push-off.
    - `DIAG_RIPPLE=1` prints each ring's paw distance.
  - **Result.**
    - Film 437068/437100, all 475 strips in all six shots.
    - ROM `legend_test/jump_hooh2_v30.nds`.
    - sha256 prefixes: film `63d1b4ccd7d4130e`, ROM `54b1dba9891fca98`. Build env as for v29.
- **Gravriel in Lugia's 3D film, draft 1 (2026-11-16)** (`legend/grav3d/`). Lugia's film `a/2/4/4` plays only in Origin's post-game Lugia ritual. Lugia is its own skinned model there (member 5, 26 joints, 2 shapes) with its own animation (member 6, 246 frames); the cave (members 0-4) is kept.
  - **Model:** `export_gravfilm.py` (Blender, on the intro model `title3d/grav/grav_v5.blend`). It takes the mesh as posed by its intro rig, voxel-remeshes it (0.035) and decimates to about 1230 triangles; the eye slits and sockets are added on top.
    - **Colours:** the intro paint is the argmax of 7 weights (attributes `wa`/`wb`), read per vertex; each face takes the majority label.
    - **Rig:** Quaternius' CC0 Universal Animation Library (standard, from OpenGameArt; `title3d/ual_dl/`). Its rig is scaled to his shoulder height and the arms are aimed at his hands; that pose is the bind pose. Vertices go to the nearest of 14 DEF bones. The coat below the waist and the feet follow the hips, so he floats with no legs. The cutlass follows the right hand. A face across far-apart bones goes to one bone (no spikes).
    - **Motion:** `Swim_Idle_Loop` (rise, arms out), then `Sword_Attack` at film frame 150 (the water ring), then `Sword_Idle`. Library 30 fps against the film's 60; 6-frame blends.
  - **Into the film:** `rig_lugia.py`.
    - **Nodes:** our bones on Lugia's nodes 1-14 in the real hierarchy (0x66: restore the parent's slot, store its own), with node 0 as a still root. Bone offsets stay constant, which made the animation 18 KB instead of 36 KB.
    - **Geometry:** per-vertex MTX_RESTORE strips. The body goes in shape 0 (`lugia_s` 64x64 swatches), the face, sword, shells and eyes in shape 1 (`lugia_foot` 32x32). Bone matrices carry K=16; posScale is not used.
    - **Path:** hidden deep below the water until film frame 124 (the flash), rising at the foot of the fall through the falling water until 154, out in front of it by 176, then hovering where Lugia hovers. Env for draft 1: `SHOW=124 RISE0=124 RISE1=154 OUT1=176 CY=68`.
  - **Water:** `cave_tint.py` maps the water palettes (sea, falling water frames, pond line, waves) by brightness onto a dark-teal to sea-green gradient.
  - **Fog:** the cave is authored for fog (fog flag on most materials), but the film code turns fog off (`G3X_SetFog(0,0,0,0)` in ov106_021E5D70, shared by all three films). Adding fog needs a small code patch in the film overlay, limited to Lugia's film.
  - **Files:** film 79424/84324 bytes (80164 with the water colour). ROMs `legend_test/jump_lug_g2.nds` and `jump_lug_g2w.nds`. Video `gravriel_lugiafilm_utkast1.mp4` (`video3.py`).
- **Gravriel v3 in Lugia's film, and the room (2026-11-16)**. Arvind on draft 1: out of the portal/fall like Lugia, slower and eerier; mostly kelp and seaweed, not grey; more fog, scarier; the whole room like that, not only the cutscene; fix the darkness, the loose tatters, the sword and the face.
  - **`export_gravfilm.py` (v3):**
    - **Kelp colours:** the coat is kelp in three greens, in strands by position; the weed is olive, the skin a paler sea-green. The cutlass has its own steel label.
    - **Cross-chain faces:** faces that bridge the arm and body chains are dropped (no loose shards). Within the body they become one bone, so the waist has no gap.
    - **Eyes:** the eye glow is 1.6x. The slash is slower (`S_SLASH` 1.0).
  - **`rig_lugia.py` (v3):**
    - **Path:** `KEYS`. He waits behind the fall from film frame 60, crosses the curtain at the flash (124) and drifts out to Lugia's hover spot (178).
    - **Lighting:** brighter materials (ambient 26, emission 7). The eye glow sits 2 units in front of the socket.
    - **Fog:** 7 see-through mist layers (4 low sheets over the water, 3 veils in front of the fall) on spare nodes 15/16, drifting slowly. Each layer has its own `POLYGON_ATTR` (unlit, both faces, alpha 7-13, its own polygon id) in shape 1.
    - **Why geometry fog:** the film code turns hardware fog off for all three films, there is no room for code in the film overlay (Origin's ov097 = pret ov106), and Ho-Oh's film materials carry the fog flag too.
  - **The room** (map 244, `MAP_WHIRL_ISLANDS_B3F_LUGIA_CAVE`; header at arm9 0xF4EA4, ROM 0xF8EA4):
    - **Water:** `room_tint.py` gives texture set 98 (`a/0/4/4`) the film's green water. Area 98 is shared with map 486 (Whirl Islands B3F), so that floor changes too.
    - **Weather:** `room_weather.py` sets the weather. 10 = mist, unused; 9 is the same but used by Sprout Tower 2F and the Goldenrod Dept. Store 3F, sharing graphics and the white fog colour. 13 = dark fog. From the overhead camera both are faint, because their fog starts far away.
    - **Green fog in the room:** needs a code change, because the mist colour (ov001 literal at 0x7E34) is shared.
  - **Files:** film 82136/84324 bytes. ROM `legend_test/jump_lug_v3.nds`. Video `gravriel_lugiafilm_v3.mp4`, room picture `gravriel_rommet_groent_vann.png`.
- **Gravriel v5 (2026-11-16)**. Arvind on v3: silly that he comes out before the portal opens, extend the scene instead; the flight is stiff; not enough like the artwork; the fog shows only in the video, put it in the room; the waterfall at the back of the room too; the face like the intro.
  - **Timing and sway:** he appears in the curtain when the portal opens (film frame 126), drifts out to the hover spot by 204, leans into the glide and sways slowly (`LEAN`, `ROLL_SW`, `YAW_SW`).
  - **Look:** `tex_project.py` projects the turnaround the 3D model was made from (`title3d/grav/turn_11.png`; the figures are split at white columns). The background takes the nearest inner colour. Colours are a saturation-weighted k-means.
    - The fully painted 64x64 body came out muddy brown at film size.
    - So it is a **hybrid**: the face (head front) is painted from the artwork (32x32, brightened), and the body uses swatches in the artwork's scheme (near-black coat, bright kelp strands, sea-green skin; `rig_lugia.py` sets them when `tex` is present).
    - Only the veil behind him is kept; the ones in front washed him out. The mist is still (no drift), which keeps the film in its slot.
  - **Room:** `room_tint.py 96` on `a/0/7/0` recolours the waterfall building at the back (falls, whirlpool). Building pack 96 is used only by area 98.
  - **Film length:** the film runs until the longest animation of its models ends (overlay code: every AnmObj frame +1 until numFrames; ends when none is left). A longer scene therefore means a longer Gravriel BCA. The cave's BTA/BTP/BMA/BCA (246 frames) would then freeze on their last frame unless they are extended too.
  - **`relocate.py`:** moves a file that outgrew its slot to the end of the ROM, updating its FAT entry, the used-ROM size and the header CRC. **It does not show in tests that start from a savestate (`g7.dst`)**, because the game keeps the file table in RAM. It needs a cold boot.
  - **Files:** film 84268/84324 bytes. ROM `legend_test/jump_lug_v5.nds`. Video `gravriel_lugiafilm_v5.mp4`, room `gravriel_rommet_v5.png`.
- **Gravriel v6 (2026-11-16)**. Arvind on v5: lots of holes in the model; the animation is messy; fly out of the portal like Lugia and float up, it need not be about the sword, he must be clearly visible; same quality as the Pokémon models; the rocks by the fall.
  - **Model (`export_gravparts.py`):** separate closed parts (coat, beard, head, hat, both arms, cutlass), each made solid before it is reduced:
    - The cut loops are capped and the surface gets a thin solidify. The sculpt has open sheets and folds, so a plain voxel remesh leaked and broke the coat into 82 crumbs.
    - Voxel remesh, cavities inside the solid dropped (ray parity), the surface cleaned to a proper manifold, decimated to a triangle budget per part, and flat triangle pairs joined into quads (a quad is one DS polygon).
    - QuadriFlow was tried. It needs that clean manifold (Blender also refuses edges shorter than 1e-4), and on the thin beard strands and the face it made blobs, so decimation won.
    - Result: one closed figure with no holes, 1374 polygons (about 450 quads); Lugia has 1128.
  - **Motion:** `Swim_Idle_Loop` while he rises, then the standing `Idle_Loop` (arms down, cutlass in the right hand, like the artwork). The Spell idle turned him side-on. The right wrist is locked to the forearm, because the cutlass hangs about 2 units below it and the wrist turns swung it off his hand (`lock_wrist.py` for older exports).
  - **Path and facing:** Lugia's own body path from its animation, at half speed from the moment the portal opens (`LUGIA_PATH`, `SLOW` 0.5, `T0` 124). **The film camera looks along x**: Lugia's body node turns its +z to -x for the whole film. Gravriel is turned +90 degrees (`BASE_YAW`; -90 showed his back).
  - **Film (`rig_lugia.py`):**
    - The two shapes' display lists lie back to back, so the boundary between them moves to where the body needs it (body 44 KB, face and mist 13 KB, of 61 KB).
    - Colours are darker (near-black coat, dark kelp, olive beard, sea-teal hands), because the film's light made the old greens lime (`SCHEME=old` for v5).
    - The face material glows more than the body (`EMI1` 13). In `tex_project.py` the face paint is brighter (`FACE_GAIN` 1.45) and the blue eyes glow pale cyan (`EYE_GLOW`); at film size they are 1-2 pixels.
    - **Back faces are culled** (polygon attr 0x80, `BOTH=1` for the old 0xC0). Drawing both sides showed the brim's underside and the solidify inner sheets as a black band over the face (found with `DEBUG_FACE=1`, a magenta face texture). It also halves the polygons the DS draws.
  - **Size:** the film is now about 102 KB against its 84 KB slot. `relocate.py` moves it to the end of the ROM. Savestate tests point the in-RAM file table at it with `fat_pokes.py` (file 364 at RAM 0x023BFDC0). A final ROM build places it normally.
  - **Room:** `room_tint.py` also recolours the blue boulders in the pool in front of the fall (`r_sea_rock`) and the blue wet-rock pattern (`cliff01gs`) to a wet grey-green stone (`ROCKS`, `RDARK`/`RMID`/`RLIGHT`).
  - **Fog in the room, not working yet:**
    - The mist weathers 9/10 run one task in overlay 1 that passes two pool literals to the fog setup: `ov001+0x7E30` = fog offset 0x7555 (far) and `+0x7E34` = colour 0x7FFF (white), shift 6. Both are shared with weather 9 (Sprout Tower 2F, Goldenrod Dept. Store 3F).
    - `fog_test.py` patches them for a look test. Neither the ROM patch nor RAM pokes showed anything, and neither does weather 10's mist layer.
    - So the weather is not active in our tests at all. The savestate (`g7.dst`) is already inside map 244 with weather 0 stored, and the field after the film keeps it. The header change needs a real entry into the map, and the earlier note that the fog is "faint from the overhead camera" was untested.
  - **Files:** film 101,888 bytes (relocated). ROM `legend_test/jump_lug_v6g.nds`. Video `gravriel_lugiafilm_v6.mp4`, room `gravriel_rommet_v6_steiner.png`. Build and record steps: `build_film.sh` pattern (tex_project, rig_lugia, cave_tint, relocate, inplace room, room_weather, fat_pokes, drive.py).
- **Gravriel v7 (2026-11-16)**. Arvind on v6: there are holes and it does not look like Gravriel; the face is not visible at all; the model and the animation were not good; the video was very fast. Close-ups confirmed it: v6's decimated parts were jagged shards with the background showing between them.
  - **Model:** `export_gravparts.py` with `WHOLE=1` (default). Everything but the cutlass is ONE closed body: capped cuts, solidify, a coarse voxel (`VOXW` 0.08) that fuses the kelp tatters into one skirt with a wavy hem, a smoothing pass, and reduction as one piece (1300 triangles, joined to 888 polygons). The cutlass is its own small part. No seams or gaps between parts.
  - **Look, like the Pokémon film models (detail in the texture, not the geometry):** `tex_atlas.py` paints him from the turnaround his 3D model was made from (`title3d/grav/turn_11.png`). Each face takes the view its normal points at: front, back, or a side (only when `|nx| > 1.6 |ny|`; otherwise the head's flanks showed a second face). Real UVs, 8-bpp 256-colour textures: the front in a 128x128 texture (shape 0, `lugia_s`), back and both sides in 128x64 (shape 1, `lugia_foot`, plus the mist colour). The blue of the eyes is lifted to a pale glow (`EYE_GLOW`). Unlit (`LIGHTS=0`), so the painting shows as it is.
  - **`tex0_grow.py`:** rebuilds the TEX0 block at the end of Lugia's model so textures can change size and format (dict names kept, data and palettes laid out again, params, header, block and file size updated; an identity rebuild gives the same bytes). `rig_lugia.py` uses it when the atlas sizes differ and sets the materials' width and height.
  - **Texture budget:** 128x128 + 256x128 at 8 bpp (48 KB, 74 KB with the cave's 26 KB) came out as garbled streaks in the film, most likely overwritten in VRAM. 24 KB of textures (50 KB in total) shows correctly, at 16 or 256 colours. 16 colours lost the greens.
  - **Facing:** `BASE_YAW` 60 faces the film camera (tested 60, 90, 120; 120 is side-on). Sway is calmer (`YAW_SW` 3, `ROLL_SW` 2, `BOB` 1.5), because the film's motion-blur effect smears anything that keeps moving.
  - **Path (`PATH_MODE=glide`, default):** he starts behind the falling water in the middle of the fall (`G0` 8,40,-90) and glides, ease-out, to where Lugia hovers (`T0` 124 to `T1` 204), rising a little (`ARC`). Breaking through the water fast keeps the smear behind the curtain short. Lugia's own start point (v6's half-speed copy of its path) is off to the side near the camera, so he popped in at the bottom right.
  - **Motion:** the library motions are applied at a fraction on top of the artwork pose (`AMP1` 0.35 for `Swim_Idle_Loop` while he rises, `AMP2` 0.6 for `Idle_Loop` at the hover), so the one-piece body is not torn.
  - **Checks:** `render_proj.py` (mesh painted straight from the sheet), `preview_uv.py` (skinned, textured with the atlas, culled like the film). `build_film7.sh G V` builds and records; `quick_film.sh` records only the end of the film for A/B tests.
  - **Files:** film 111 KB (relocated). ROM `legend_test/jump_lug_v7d.nds`. Videos `gravriel_lugiafilm_v7_halv_fart.mp4` (half speed) and `gravriel_lugiafilm_v7.mp4` (real speed); close-up `gravriel_v7_naerbilde.png`.
- **Gravriel v7e (2026-11-16)**. Arvind on v7: the face looks great and very like him; but the direction he faces is wrong (face where Lugia faces at the end), it still looks like holes in the body (test it with a magenta background), and the scream ring lies in front of him because he arrives later than Lugia.
  - **Holes, found and fixed:** `magenta_cave.py` turns every palette colour of the cave model magenta, so anything seen through him shows magenta. The test showed magenta through his body. Cause: the strip builder in `rig_lugia.py` extended a triangle strip without checking winding. A strip draws triangle k as (s[k], s[k+1], s[k+2]) for even k and with the first two swapped for odd k. Triangles added the wrong way round were culled once back faces were (v6g on), and the previews draw triangles, not strips, so they looked whole. Now a triangle is only added when the strip's order is its own winding (`STRIP_FIX=1`). Magenta test: `gravriel_magenta_hulltest.png` (old strips left, fixed right).
  - **Facing:** at the end Lugia's head and jaw point to +z (about -4 degrees), so `BASE_YAW` defaults to -4 in the glide; he is seen three-quarter like Lugia.
  - **The scream ring:** three cave nodes (`polySurface758/759/760`, wave2/3/6) grow from film frame ~150 at Lugia's hover spot. With `RING_FOLLOW=1` (default) their translation follows his middle each frame, keeping their offset to Lugia's body at the hover. All cave tracks are re-encoded from their decoded values with `bca_write`.
  - **Speed (Arvind: half speed looks right, the original looks fast, on YouTube too):** in our test ROM the overworld and the film draw a new picture every frame (60 per second), and walking scrolls 2 px per frame (a tile in 8 frames). Vanilla HGSS draws the overworld at 30 per second, and the known 60-fps patches for DPP/HGSS speed the whole game up as a side effect. So Origin probably runs the game at 60 where vanilla runs at 30. Not confirmed against a vanilla ROM yet.
  - **Files:** ROM `legend_test/jump_lug_v7e.nds`. Videos `gravriel_lugiafilm_v7e_halv_fart.mp4` and `gravriel_lugiafilm_v7e.mp4`.
- **Gravriel v8 (2026-11-16)**. Arvind on v7e: the model is amazing; now the animation. In the intro he turned green and faded out, so do something with the green, with the halo matching it; he is green and see-through at the start, flies out of the portal, gets his own colours on the way, points his sword where Lugia looks, and freezes with Lugia (Lugia stops on purpose: a freeze frame before the battle).
  - **Freeze:** in the original the picture is identical from film frame ~160 until the fade (Lugia stops; the motion-blur trails die out by ~176). `FREEZE` 160: his path, bones and the ring stop there; the glide ends there (`T1` 160).
  - **Ghost (`export_gravparts.py` part `ghost`, 351 polygons):** a lighter copy of the whole body, drawn untextured and see-through (alpha 14, polygon id 50), rigid on one node (the two mist layers now share one node). Each vertex gets the intro ghost's colour: the brightness of the painted texture at that point turned into pale sea green with `build_grav4.py`'s formula, in steps of 24 (`GHOST_Q`, fewer COLOR commands), with the eyes kept bright.
  - **Timeline:** the ghost shows from the portal flash (124, behind the falling water) and glides out after the flash (`G_START` 132, eased in and out) toward where Lugia hovers. At `SWITCH` 147 his own body appears (it waits 900 units below before that). For `AURA` 14 frames the ghost swells around him (1.06x) and shrinks into him (0.86x), so the green drains out of him as the scream ring reaches him.
  - **Green halo:** the scream ring is the white band on `pCylinder1` (`de_ap_e4`) plus the growing discs `polySurface758-760` (`uzu_taki_ha/ha2`). `cave_tint.py` maps their palettes onto a mint-green gradient (`RING_PALS`, `RDARK/RMID/RLIGHT`). The portal flash uses the same band, so it is green too. `RING_FOLLOW` now moves node 1 (the band) as well.
  - **Sword:** from `TP0` 134 to `TP1` 156 the right arm chain swings about the shoulder until the blade (grip to tip, measured on the cutlass) lies along `POINT_DIR`: his forward and a little up, where Lugia looks. The arms are their own closed parts again (`ARMS_APART`, hands included by the skin colour near the hand bone), so the coat is not dragged along. The cutlass is pulled 0.67 into the fist (`SWORD_PULL`), closing the gap that showed once he pointed it. The coat takes coat bones only.
  - **Files:** ROM `legend_test/jump_lug_v8b.nds`. Videos `gravriel_lugiafilm_v8_halv_fart.mp4` and `gravriel_lugiafilm_v8.mp4`; stills `gravriel_v8_tre_bilder.png`.
- **Gravriel v9 (2026-11-16)**. Arvind on v8: looks great, but he should come up out of the water instead, with the portal effect coming from there too; a different camera angle is my call; maybe something lying at the water right in front of him that follows his eye line when the portal comes.
  - **The film camera, measured:** it is set in code, not in the files. `MARKERS` in `rig_lugia.py` draws opaque coloured cubes at known film-space points (`film_camera_markers.txt`). `film_camera_calib.py` finds them in a recorded frame and solves the camera by DLT; the reprojection error is under 0.11 px. The camera never moves: centre (229, 49, 286), focal length about 386 px (about 28 degrees vertically), looking toward the fall and slightly up. Saved as `film_camera.json`.
  - **New camera = the world moved the other way:** for every frame M = V_orig^-1 V_new is applied to the cave's root node (all of the cave hangs under it), to his root and to the mist node. `VCAM` with `PATH_MODE=rise` (default): a low camera at the water (`CAM_Y0` 18, cranes to `CAM_Y1` 40 as he rises), `CAM_D` 320 away, `CAM_ANG` 40 degrees to the side of his front. It looks up a little, so the water line sits at the bottom edge (lower, it saw through the see-through water into the black void below). From the portal on, it aims at his eye line (`AIM` 0.55 of his height) and freezes with everything at 160.
  - **Cave scene map:** water surface at y about 10; the fall curtain at z about -100. Node 1 `pCylinder1` (`de_ap_e1`) is the portal burst; nodes 3/4 (`de_ap_e4`) are the band rings; node 5 (`de_ap_e5`) the sparkles; node 2 the dark dome.
  - **Out of the water:** `PATH_MODE=rise`. He goes straight up from `DEPTH` 200 below Lugia's hover spot to the hover (124 to 160, ease-out), as the green ghost until the switch. The portal burst (node 1) is placed on the water where he rises (`BURST_Y` 9); the rings still follow him.
  - **Files:** ROM `legend_test/jump_lug_v9b.nds`. Videos `gravriel_lugiafilm_v9_halv_fart.mp4` and `gravriel_lugiafilm_v9.mp4`; stills `gravriel_v9_fire_bilder.png`.
- **Gravriel v10 (2026-11-16)**. Arvind on v9: very close to what he imagined; but the camera should be in front of him (it was on his left side), the portal is still made for something coming out horizontally and must be vertical now, and the blue outline should be the same green as his see-through form.
  - **Camera in front:** `CAM_ANG` 0 (320 behind his front, past the cave's back wall; the wall's inside faces are culled from there, so it does not block the view).
  - **Vertical portal:** the burst (node 1, `de_ap_e1`) stretches along its own z (frames 122-140, up to 14x), out of the fall toward the camera. Turned so that z points up (`BURST_UP`), it shoots straight up out of the water where he rises.
  - **Ring from the front:** the band ring (node 4) grows to hundreds of units within a few frames and stood edge-on to a low camera in front. It keeps its own orientation, which matters: turning the discs showed their culled back side and they vanished. It is tipped back 25 degrees (`HOOP_TILT`; -25 hides it), scaled to a third (`RING_SCALE` 0.33), and centred on him (`HOOP_DY` 20). It reads as a green hoop round him that widens.
  - **Green outline:** the outline is the DS edge marking. The film overlay (ov097 = pret ov106) sets 8 colours by polygon-ID group from a table at ov097+0x1578 (`0x0000, 0x7A89, 0x1084 x6`); it was found by reading the EDGE_COLOR registers during the film and locating the table in RAM. Group 1 (ids 8-15) is used only by Lugia's materials in Lugia's film; the Ho-Oh film and the third film use group 0. `edge_color.py` sets entry 1 to the ghost green (104,192,152), so only he changes. `build_film7.sh` applies it with `EDGE=`.
  - **Files:** ROM `legend_test/jump_lug_v10e.nds`. Videos `gravriel_lugiafilm_v10_halv_fart.mp4` and `gravriel_lugiafilm_v10.mp4`; stills `gravriel_v10_fire_bilder.png`.
- **Gravriel v11 (2026-11-16)**. Arvind on v10: his right arm is wrong in the pose, and he does not look at the camera.
  - **Arm:** pointing the blade at the camera in front foreshortened the arm, so it looked like he held the cutlass up beside his head, and the shoulder blend twisted the sleeve. Now the blade goes out and up to his right and a little forward (`POINT_DIR` -0.55,-0.45,0.7), a clear diagonal from the front. The sword arm swings as one piece with the upper arm (no shoulder bone in `armR`).
  - **Looking at the camera:** the low camera is about 20 degrees below his eyes. He faces it (`BASE_YAW` 0 in `rise`), and his head bows 20 degrees about the head joint while he rises (`HEAD_PITCH`, same timing as the sword), so he looks into the camera at the freeze.
  - **Files:** ROM `legend_test/jump_lug_v11.nds`. Videos `gravriel_lugiafilm_v11_halv_fart.mp4` and `gravriel_lugiafilm_v11.mp4`; before/after `gravriel_v11_pose_for_etter.png`.
- **Gravriel v12 (2026-11-16)**. Arvind on v11: v9 was better; go back to v9's camera angle and v9's pose, but keep the new portal and the green outline (and the rest of the new).
  - **Back to v9:** the camera is 40 degrees to his side again (`CAM_ANG` 40) and he faces Lugia's heading (`BASE_YAW` -4 in `rise`). The model and motion are v9's own export `g8.json`, unchanged (made before v9; v9, v10 and v12 use it). The `export_gravparts.py` defaults are back to that pose too: `POINT_DIR` -0.2,-1,0.38, the shoulder bone in `armR` (`ARM_WHOLE=1` is v11's whole-arm swing), no head bow (`HEAD_LOOK=1` is v11's).
  - **Kept from v10:** the vertical portal burst out of the water (`BURST_UP`), the green hoop round him (`HOOP_TILT` 25, `RING_SCALE` 0.33, `HOOP_DY` 20; it reads well from the side angle too) and the green outline (`EDGE=104,192,152`).
  - **Build:** `EDGE=104,192,152 build_film7.sh g8 v12`. ROM `legend_test/jump_lug_v12.nds`.
  - **Files:** videos `gravriel_lugiafilm_v12_halv_fart.mp4` and `gravriel_lugiafilm_v12.mp4`; stills `gravriel_v12_fire_bilder.png`, freeze next to v9 `gravriel_v12_frys_mot_v9.png`.
