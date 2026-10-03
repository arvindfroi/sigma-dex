# The Sigma sprite style

Every Sigma Pokemon's battle sprites are made the same way, so the whole dex has one look and
anyone can make the next one. This page says what the standard is, how the sprites are made,
and how a sprite is checked. In the sprite studio on the website this is the style
"Sigma sprite style" (`sprite-official`), and it is the default.

![The style on eight Pokemon](img/sprite_style_test.png)

## The standard

What the Game Boy Advance games' sprites do, and what ours must do too:

- **Frame:** 64 x 64 pixels. Front and back share one palette of at most 15 colours (plus the
  see-through one).
- **Size:** bigger than the official sprites, because ours looked too small and a face needs
  pixels: first stages about 54 pixels, middle stages 60, final stages 63 (from the base stat
  total; `sprite_pixels` in `scripts/sprite_worker.py`).
- **Front:** three-quarter view turned to the left, the whole body, an expressive battle pose.
- **Back:** seen over the shoulder, head turned up and to the right, drawn closer than the
  front and cut off flat at the bottom.
- **Outline:** a closed, nearly black outline around the creature, and dark lines between
  parts that contrast (a bill against a face, a belly against a body).
- **Shading:** flat colour areas with two hard tones each, no gradients, no dithering, no stray
  pixels. Light comes from the upper left; the inside of the bottom and right edges is in shadow.
- **Face:** every eye has a dark pupil and a light glint, and brows and mouth keep their pixels.

## How a sprite is made

1. **Official-style artwork.** Qwen-Image redraws the group's concept art (up to three
   reference pictures) as official Pokemon artwork: clean thin outlines, flat cel shading, head
   and eyes a little bigger than in the reference, simple shapes, in the chosen pose. Then it
   draws the same creature from behind, using its new front picture as the reference, so front
   and back match. Prompts: `official_front`, `official_back` and `official_poses` in
   `data/sprite_prompts.yaml`.
2. **Built pixel by pixel.** `scripts/pixel_render.py` does not shrink the artwork (that turns
   lines and faces to mud). It finds the artwork's colour areas, lays them on the 64 grid, gives
   each two hard tones from the artwork's own light and dark, draws the outlines and stamps the
   eyes, brows and mouth. The icon (32 x 32) is built the same way at its own size.
3. **Checked.** `standards()` in `scripts/sprite_quality.py` measures each attempt against the
   standard above (colours, closed outline, stray pixels, readable eye, size, halo, flat-cut
   back). The worker makes twice as many attempts as asked for and hands in the better half;
   an attempt that misses the standard goes to the back and says why in its notes.
4. **People choose.** The checks find technical faults, not a wrong design. The group picks the
   attempt that looks like their Pokemon, or comments on it for a redo.

The same request always gives the same sprites (the seeds come from the request number, and the
renderer is not random).

## What helps

- Clear concept art: a front view, and if possible a back view and an action pose (like the
  character sheets for Leafing and Torchbat). Pictures with a lot of text work, but the creature
  should be big in them.
- A short look on the Pokemon's page (colours and the 2-3 things that must be there).
- The pose choice in the studio, for creatures whose personality shows in a pose.

## Tried and dropped (2026-10-03)

Shrinking an illustration (with or without PixelOE), having the AI "clean up" a shrunk sprite,
the Pokemon sprite LoRAs (Emerald and Sprite XL, also with an IP-Adapter), and a free redesign
by the AI. They gave muddy faces, lost the group's design, or both. Comparison pictures are in
[STUDIO.md](STUDIO.md).
