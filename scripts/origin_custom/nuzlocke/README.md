# Nuzlocke mode: first test (2026-11-16)

Gravriel gets two hard modes, Nuzlocke and Hardcore Nuzlocke (docs/WHEN_WE_FINALIZE.md, "Versions and scripted
events"). This folder is the first working piece, our own code. Other hacks were only used as a map of which game
events need hooks.

## What it does

1. **First encounter per area.** The first random wild battle in an area (map section: Route 1, Viridian Forest,
   ...) uses up that area. In every later random wild battle there, a Poke Ball is refused in the battle Bag with
   "This area's encounter is used up! The Ball won't work here." The Ball is not used up.
2. **Graveyard.** After a battle, every fainted Pokemon leaves the party for the last PC box (box 24), which is
   renamed "GRAVES" (box names hold 8 letters). If the whole party fainted, nothing moves; the blackout decides.

The test build starts every save in nuzlocke mode. The real build will set the mode from Gravriel's new-game choice.

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
| overlay 9 `0x021EB3D6` (battle Bag, Use on a Ball) | the "aim" flag test | `bl nz_ball_check` (prints message 0x31 itself) |
| arm9 `0x0202B2D0`, `0x0202B332` | apricorn loops over 128 trees | stop at 31 (Origin has 31 trees) |
| arm9 `0x020D1970` | main arena end `0x023D4000` | `0x023D2000` (8 KiB for us) |
| `a/0/2/7` bank 5 | 49 lines | + line 0x31, the refusal text |

Save data: SaveMisc apricorn slots 31..127 (388 bytes) are free in Origin; we use 40 bytes at SaveMisc+0x7C: magic
"NUZ1", mode, death count, one bit per map section. The magic matters: the old apricorn loops wrote 1 into bytes 0
and 1 of every slot, so old saves already have a pattern there.

```bash
~/origin-en/.venv/bin/python scripts/origin_custom/nuzlocke/build_nuzlocke_test.py \
    ~/sigma-origin/rc8/origin_hg_en_rc8_ai.nds ~/sigma-origin/rc8/nuzlocke_test.nds
~/sigma-toolchain/venv312/bin/python scripts/origin_custom/nuzlocke/test_nuzlocke.py prep
~/sigma-toolchain/venv312/bin/python scripts/origin_custom/nuzlocke/test_nuzlocke.py all
```

## Tested (DeSmuME, py-desmume)

| Step | Result |
|---|---|
| Battle 1 on Route 1 (first encounter) | area marked used, Ball thrown, Vullaby caught, Balls 20 -> 19 |
| Battle 2 on Route 1 | refusal text shown, Balls stay 19, flag cleared after fleeing |
| Battle 3, lead at 1 HP with only Splash | it faints, the 2nd Pokemon comes in, flee: the dead one is out of the party and in box 24, box named GRAVES, deaths = 1 |
| Save in the game, power off, Continue | party, box 24, its name, Route 1 used and the death count are all still there |

Screens: `~/sigma-origin/nuzlocke_test_v1.png` (not in the repo, it shows game graphics).

Found on the way: an empty PC slot in a Gen 4 save is not 136 zero bytes but **zeros encrypted with checksum 0**.
Our earlier hand-made test save had plain zeros, so every slot looked like a broken Pokemon and box 24 was "full";
`fix_test_save_pc.py` writes proper empty slots.

## Not done yet

- Hardcore rules: no healing items in battle, Revive blocked (battle: item-effect table entry `0x0224D1E0`; field
  bag: call site `0x0207A8E6`), level cap enforcement, forced nicknames (Origin has no nickname prompt after a catch:
  open the naming screen in the field after the battle).
- Gifts (GiveMon `0x02053380`, GiveEgg `0x02053424`) and static encounters (scripted `WildBattle`) do not count yet.
- Dupes and shiny clauses, Safari Zone and Bug Contest (own tasks, not hooked).
- A withdrawn dead Pokemon must go back to the graveyard when the PC closes (script cmd 158, `0x02042050`).
- Whiting out = run over screen, the Gravriel blackout picture, the new-game mode choice, a status panel per area.
- Story battles you may lose (`TrainerBattle x,0,1,0`) heal the party by script: decide what a wipe there means.
