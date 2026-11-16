# Nuzlocke and Hardcore Nuzlocke (tests of 2026-11-16)

Gravriel gets two hard modes, Nuzlocke and Hardcore Nuzlocke (docs/WHEN_WE_FINALIZE.md, "Versions and scripted
events"). This folder is the first working piece, our own code. Other hacks were only used as a map of which game
events need hooks.

## What it does

1. **First encounter per area.** The first random wild battle in an area (map section: Route 1, Viridian Forest,
   ...) uses up that area. In every later random wild battle there, a Poke Ball is refused in the battle Bag with
   "This area's encounter is used up! The Ball won't work here." The Ball is not used up.
2. **Graveyard.** After a battle, every fainted Pokemon is marked dead (unused ribbon bit 53) and leaves the party
   for the last PC box (box 24), which is renamed "GRAVES" (box names hold 8 letters). In the PC its icon is
   **grey** (Arvind). If the whole party fainted, nothing moves; the blackout decides.
3. **Dead stay dead in the PC.** They may be moved around in the PC (Arvind: fine as long as they cannot be used);
   one taken into the party goes back to GRAVES when the PC closes. If only dead ones would be left, the last stays,
   fainted.
4. **Advanced trainer AI ALL** (both Gravriel modes), set before every battle.
5. **No revives.** Revive, Max Revive, Revival Herb and Sacred Ash are refused in the battle Bag ("Nuzlocke: a
   fainted Pokémon can't be brought back!") and on the party screen ("It won't have any effect.", item kept).

**Hardcore Nuzlocke** adds (checked against the English patch's DIFFICULTY page first, Arvind: "they already have
the level cap as a setting, so we force it on"):

| Hardcore rule | Already in the game? | What we do |
|---|---|---|
| Level cap | yes: CAP ON limits battle EXP by badges; Rare Candy and Day Care go past it | force CAP ON before every battle; Rare Candy refused at or above the cap (the same cap rule as the patch's caps.c) |
| No items in battle | partly: ITEMS DEFAULT still allows Potion, Super Potion, drinks, berries in trainer battles; wild battles unlimited | force ITEMS DEFAULT, and refuse every Bag item in every battle except Poke Balls ("Hardcore Nuzlocke: no items can be used in battle!") |
| Battle style SET | yes: an Options setting | forced before every battle |
| Trainer AI | yes (event flags 0x2C2/0x2C3) | ALL for every trainer, in both Gravriel modes (Arvind) |
| Forced nicknames | no (Origin has no nickname prompt after a catch) | not done yet |

The options are forced in the save's Options word just before each field battle is set up, so changing them in the
menu does not survive the next battle. Locking the menu rows is still to do. Day Care still ignores the cap.

The test build starts every save in the mode given to the build (1 nuzlocke, 2 hardcore). The real build will set it
from Gravriel's new-game choice.

## How it is put in

| File | What |
|---|---|
| `nuzlocke.c` | the rules, calling Origin's own functions (party, PC, map section, save data) |
| `hooks.s` | two small stubs where C cannot see the caller's registers |
| `nuzlocke.ld` | our code lives in main RAM `0x023D2000`-`0x023D4000`, right below the advanced trainer AI |
| `build_nuzlocke_test.py` | compiles, adds the code as a new ARM9 autoload section, patches the hooks, adds the Bag message |
| `test_nuzlocke.py`, `fix_test_save_pc.py` | the emulator test (English patch harness, py-desmume) |

Patched places (each one is checked before it is changed, so any other Origin build is refused):

| Where | Was | Now |
|---|---|---|
| arm9 `0x02050042` (random wild battle task, state 0) | `bl 0x0205E6F0` | `bl nz_hook_wild` (then the original) |
| arm9 `0x0204FBB8` (battle end, party copied back) | `bl 0x02051574` | `bl nz_battle_end` (the original first) |
| arm9 `0x02051278` (every field battle set up) | `bl 0x02051074` | `bl nz_hook_setup` (forces options, then the original) |
| arm9 `0x0207A8E6` (party screen: item on a Pokemon) | `bl 0x0208FA38` | `bl nz_hook_party_item` (revives, Rare Candy over cap) |
| arm9 `0x02042050` (the PC closes, script cmd 158) | `bl 0x020926B8` | `bl nz_pc_closed` (the original first, then dead ones back) |
| overlay 9 `0x021EB2A4` (battle Bag, Use, any item) | `ldr r1,=0x114D` ... | `adds r7,r0,#0 ; bl nz_bag_use` (prints 0x32/0x33 itself) |
| overlay 16 `0x021F211C` (PC box loaded its icon palettes) | `bl 0x020731FC` | `bl nz_hook_pc_palettes` (grey copies into OBJ palettes 10-12) |
| overlay 16 `0x021F2288`, `0x021F22F8` (PC icon palette) | `bl 0x020731A4` | `bl nz_icon_palette` (+7 for a dead Pokemon) |
| overlay 9 `0x021EB3D6` (battle Bag, Use on a Ball) | the "aim" flag test | `bl nz_ball_check` (prints message 0x31 itself) |
| arm9 `0x0202B2D0`, `0x0202B332` | apricorn loops over 128 trees | stop at 31 (Origin has 31 trees) |
| arm9 `0x020D1970` | main arena end `0x023D4000` | `0x023D2000` (8 KiB for us) |
| `a/0/2/7` bank 5 | 49 lines | + lines 0x31-0x33, the refusal texts |

Save data: SaveMisc apricorn slots 31..127 (388 bytes) are free in Origin; we use 40 bytes at SaveMisc+0x7C: magic
"NUZ1", mode, death count, one bit per map section. The magic matters: the old apricorn loops wrote 1 into bytes 0
and 1 of every slot, so old saves already have a pattern there.

The grey palettes are made by the build from the game's own three icon palettes (`a/0/2/0` file 0): each colour's
luma, a little lighter. The PC box draws on the main engine, whose OBJ palettes 10-15 are free there.

```bash
~/origin-en/.venv/bin/python scripts/origin_custom/nuzlocke/build_nuzlocke_test.py \
    ~/sigma-origin/rc8/origin_hg_en_rc8_ai.nds ~/sigma-origin/rc8/nuzlocke_test_hc.nds 2
export NZ_ROM=~/sigma-origin/rc8/nuzlocke_test_hc.nds
~/sigma-toolchain/venv312/bin/python scripts/origin_custom/nuzlocke/test_nuzlocke.py prep_hc
~/sigma-toolchain/venv312/bin/python scripts/origin_custom/nuzlocke/test_nuzlocke.py hc
```
(`prep` + `all` is the round for mode 1 on `nuzlocke_test.nds`.)

## Tested (DeSmuME, py-desmume)

| Step | Result |
|---|---|
| Battle 1 on Route 1 (first encounter) | area marked used, Ball thrown, Vullaby caught, Balls 20 -> 19 |
| Battle 2 on Route 1 | refusal text shown, Balls stay 19, flag cleared after fleeing |
| Battle 3, lead at 1 HP with only Splash | it faints, the 2nd Pokemon comes in, flee: the dead one is out of the party and in box 24, box named GRAVES, deaths = 1 |
| Save in the game, power off, Continue | party, box 24, its name, Route 1 used and the death count are all still there |
| Hardcore: Rare Candy on a Lv12 Pokemon with 0 badges (cap 12) | "It won't have any effect.", still Lv12; on a Lv5 Pokemon it works (Lv6) |
| Hardcore: Revive on a fainted party Pokemon | "It won't have any effect.", HP stays 0 |
| Hardcore: options ITEMS ALL / CAP off / SHIFT before a battle | in the battle: CAP on, ITEMS DEFAULT, SET (word 0x0220 -> 0x0248) |
| Hardcore: Potion in a wild battle | refused with the hardcore text; Poke Ball still works there |
| Hardcore: battles 2 and 3 as above, then the PC | the dead Pikachu's icon in GRAVES is grey, also when selected |
| After a battle | advanced AI flags: 0x2C2 set, 0x2C3 clear (ALL) |
| PC: withdraw the dead Pikachu (it comes in healed), Exit the Box | it is back in GRAVES, party as before (`test_nuzlocke.py pcclose 1`) |

Screens: `~/sigma-origin/nuzlocke_test_v1.png`, `~/sigma-origin/nuzlocke_hardcore_v1.png` (not in the repo, they
show game graphics).

Note: Origin has random **wild double battles**. A Ball cannot be aimed while both are up (the game's rule), but it
can once one has fainted, so a double as the first encounter of an area still allows one catch. The test walks on
from doubles.

Found on the way: an empty PC slot in a Gen 4 save is not 136 zero bytes but **zeros encrypted with checksum 0**.
Our earlier hand-made test save had plain zeros, so every slot looked like a broken Pokemon and box 24 was "full";
`fix_test_save_pc.py` writes proper empty slots.

## Not done yet

- Forced nicknames (Origin has no nickname prompt after a catch: open the naming screen in the field after the
  battle), the DIFFICULTY rows shown locked in the Options menu, Sacred Ash used from the Bag directly, Day Care
  past the cap.
- Gifts (GiveMon `0x02053380`, GiveEgg `0x02053424`) and static encounters (scripted `WildBattle`) do not count yet.
- Dupes and shiny clauses, Safari Zone and Bug Contest (own tasks, not hooked).
- The special revive event (Gravriel, once): a script command that brings one Pokemon back from GRAVES.
- Other ways into the party than the PC (none known yet besides the PC).
- Whiting out = run over screen, the Gravriel blackout picture, the new-game mode choice, a status panel per area.
- Story battles you may lose (`TrainerBattle x,0,1,0`) heal the party by script: decide what a wipe there means.
