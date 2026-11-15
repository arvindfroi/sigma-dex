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
