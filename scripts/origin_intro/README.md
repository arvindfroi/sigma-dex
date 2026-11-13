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
