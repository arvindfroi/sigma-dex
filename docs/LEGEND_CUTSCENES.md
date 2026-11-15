# Ho-Oh and Lugia scenes: what Origin does and how we replace them

Arvind (2026-11-15): Sabertann takes Ho-Oh's role, Gravriel takes Lugia's. This page lists Origin's four scenes, what each
one is made of, and the plan. Tools and build commands: `scripts/origin_intro/README.md`, section "Legend cutscenes".

## Origin's four scenes

Origin gives each legendary two scenes: one in the League HQ round 4 story (Team Rocket steals it) and one after the final
Hall of Fame (you catch it). Guide: originheartgold.github.io/guide chapters 30 and 34. All four are recorded from the game
(local only, through a test ROM that jumps to the scene).

| Scene | Map | Script (`a/0/1/2`) | What happens | Pictures it uses |
|---|---|---|---|---|
| Ho-Oh, round 4 | Bell Tower roof (340) | 21, entry 8 (var 0x40a9 = 4) | Morty and "Kimono Girls" (Rocket's Joy and her Ditto) do the dance, Ho-Oh flies down, Goh catches it with one ball | the 7 bird frames, the Rainbow Wing feather, bell, leaves, rings |
| Ho-Oh, post-game | Bell Tower roof, sunset | 21, entry 7 (var 0x40a9 = 9) | Satsuki and her four sisters dance with Morty's Clear Bell, Ho-Oh flies down, battle at level 95, then catch | same |
| Lugia, round 4 | Whirl Islands B3F (244) | 104, entry 6 (var 0x40a4 = 7) | Lawrence uses Articuno, Zapdos and Moltres to wake Lugia; battles; Lugia appears and is caught by Lawrence | the 7 bird frames (it moves in by script, no 3D effect) |
| Lugia, post-game | Whirl Islands B3F | 104, the dancer's entry 2 | Satsuki's ritual with the Tidal Bell: eye glimmer, Lugia breaks out of the waterfall, flies down; wild battle at level 95, one chance | 7 bird frames, 6 silhouette frames for the eye glimmer, Silver Wing feather |

## The Lugia post-game scene is broken in Origin

The cutscene code (`legend_cutscene_camera.c`) chooses Ho-Oh's or Lugia's version from the game version, not from the map.
Origin is HeartGold, so the SoulSilver-only Lugia ritual runs with HeartGold's paths: autumn leaves in a sea cave,
Ho-Oh's camera angles, the camera clipping through the cave. Checked three ways:
- Origin's cutscene code still reads the game version in the same three places as vanilla HeartGold (same offsets apart).
- The Dance Theater's "I want to see Lugia" only clears flag 581 (the sisters appear); nothing else changes the path.
- Setting the version to SoulSilver in memory just before the ritual gives the right scene: waves, the camera on the water
  and the waterfall. A yellow speckled block over Lugia stays either way (probably the five invisible "stop" objects
  round Lugia whose sprite HeartGold lacks; not confirmed).

## Plan

1. **Pictures (sprite work, no 3D in the game):** Sabertann and Gravriel each need 7 front-view frames of 64x64 in 15
   colours (`a/0/8/1` 210/211), drawn to survive the close-ups. Gravriel also needs the 6 silhouette frames. Our 3D
   models from the intro can give consistent poses; the frames are then cleaned as pixel art and measured against Ho-Oh's.
2. **Motion:** the descent is code (starts 120 units up, 1 per frame). For Sabertann "sailing down from the sky" works with
   the existing motion. Gravriel rising out of the water needs a code change; the round 4 scene moves him by script and
   can show him rising there.
3. **Fix the Lugia ritual for Gravriel:** either make the cutscene code take the SoulSilver path on map 244 (a small code
   patch), or rewrite the script to leave out the leaves/waves and the broken camera moves and keep the eye glimmer, which
   suits Gravriel. Hide or replace the speckled objects.
4. **Story:** the texts name Ho-Oh, Lugia, the wings and the bells in about 40 text files. Arvind's idea: the Rainbow
   Wing could become something like a treasure map. Origin needs the Rainbow Wing and the Clear Bell (plus the dance) for
   Ho-Oh; the lore asks for the Tidal Bell and the Silver Wing for Lugia. To be decided with Arvind.
5. **Test in the scene:** put our frames into the test ROM and record the same scene side by side with Origin's.
