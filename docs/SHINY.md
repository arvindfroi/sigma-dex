# Shinies

Every Pokemon with an approved sprite gets its shiny in the **SHINY** tab of its page on the website. Nothing is
drawn: a shiny is the same picture with other colours, like in the real games.

## Using it

- **CREATE / RETRY** suggests a whole shiny with random choices. Each try says what it did, for example "The blue
  turns green. The orange stays." There are several kinds:
  - **turn**: the main colour turns 40-180 degrees, and the other colours turn with it or stay;
  - **swap**: the two main colours trade places;
  - **gold, silver, black or pink**: the main colour takes that colour;
  - **softer** or **deeper** colours;
  - **subtle**, like many official shinies.
- **The line comes first.** If a relative already has a saved shiny, the first CREATE copies how it moved each colour
  (the closest colour in the relative's sprite). So a line matches.
- **Colour groups.** The colours of the front and back are sorted into groups: each colour family with its shades,
  then greys, whites and the outline. Whites are kept unless someone moves them. Each group except the outline has
  three sliders:
  - **Colour** turns every shade together, so the shading stays right;
  - **Strength** makes the group stronger or greyer;
  - **Light** makes it lighter or darker.

  The colour box on the right picks the new main colour directly.
- **The outline never changes** (decided 15 Nov 2026). The near-black outline row has no sliders and no colour box,
  CREATE leaves it alone, and no other colour may take its place. Official shinies keep the outline too.
- **The preview** shows normal and shiny side by side, the back and the walking sprite. The walking sprite has its own
  colours. Each of them follows the front colour closest to it.
- **SAVE THIS SHINY** stores it. The page's top screen then has a **SHINY** button.

## What is stored

The sync writes `assets/shiny/<pokemon>.json`, and the species file's `assets.shiny_palette` points at it:

```json
{"map": {"#0042a8": "#50b000", ...}, "follower": {"#2050c0": "#58b808", ...},
 "sliders": [{"colours": ["#051643", ...], "keep": false, "adj": {"hue": 120, "sat": 0, "light": 0}}, ...],
 "why": "The blue turns green", "front": "<the sprite it was made for>", "by": "Arvind", "at": "2026-11-14T..."}
```

- `map` covers every colour of the front and back. `follower` covers the walking sprite.
- Every shiny colour is a multiple of 8. The DS keeps 5 bits per channel.
- Two colours that were different stay different after rounding.
- When a sprite is approved again later, colours the shiny does not know follow the closest known colour.
- The game export later turns `map` into the 16-colour shiny palette, in the same order as the normal palette. It
  turns `follower` into `overworld-tsure_poke1.pal`.
- Party icons have no shiny in HeartGold.
