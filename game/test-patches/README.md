
## big_pic_prototype.patch (2026-10-04)

Prototype of 96x96 battle sprites. Every wild or opponent Pokemon is shown with one fixed picture
(Bugmight from our sprite pipeline), cut into four hardware sprites (64x64 + 32x64 + 64x32 + 32x32;
the GBA's largest sprite is 64x64). Only `src/battle_controllers.c` changes; the picture data is
`src/data/sigma_big_pic.h`, made from any PNG with
`python game/test-patches/make_big_pic.py sprite.png 96 src/data/sigma_big_pic.h` (use `64` for
the comparison at today's size). Apply together with `starter_test.patch` to see it in the first
battle. Known gaps (it is a prototype): the second animation frame and the affine animations
(stretching) are not handled, and the player's health box overlaps the bigger sprite's feet.
Comparison in the game: `docs/img/big_pic_prototype.png`.
