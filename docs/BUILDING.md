# Building the game

The game is [pokeemerald-expansion](https://github.com/rh-hideout/pokeemerald-expansion)
plus our Pokemon. Its source contains Nintendo's game data, so it lives in its own folder
outside this repository and is never uploaded here.

## One-time setup on macOS (Apple Silicon)

This is the setup that was built and tested on 2026-10-02. It needs no administrator
password. (The official route, devkitARM, works too but its installer asks for one.)

1. Tools from Homebrew:

   ```bash
   brew install make pkg-config libpng coreutils arm-none-eabi-gcc
   ```

2. Homebrew's ARM compiler comes without a C library, so build one (newlib) from source,
   compiled for the GBA's processor:

   ```bash
   mkdir -p ~/sigma-toolchain/src && cd ~/sigma-toolchain/src
   git clone --depth 1 https://sourceware.org/git/newlib-cygwin.git newlib
   mkdir build && cd build
   ../newlib/configure --target=arm-none-eabi --prefix=$HOME/sigma-toolchain \
     --disable-multilib --disable-nls --disable-newlib-supplied-syscalls MAKEINFO=true \
     CFLAGS_FOR_TARGET="-mthumb -mthumb-interwork -march=armv4t -mtune=arm7tdmi -O2 -ffunction-sections -fdata-sections"
   gmake -j8 MAKEINFO=true && gmake install MAKEINFO=true
   ```

3. Get the game's source, in a folder whose path has no spaces:

   ```bash
   git clone --depth 1 --branch expansion/1.17.1 https://github.com/rh-hideout/pokeemerald-expansion.git ~/sigma-expansion
   ```

## Building

From the game's folder (`~/sigma-expansion`):

```bash
gmake tools -j8
```

```bash
LIBGCC=$(dirname "$(arm-none-eabi-gcc -mthumb -print-file-name=libgcc.a)")
CPATH=$HOME/sigma-toolchain/arm-none-eabi/include gmake -j8 \
  LIBPATH="-L \"$LIBGCC\" -L \"$HOME/sigma-toolchain/arm-none-eabi/lib\""
```

The first command builds the helper programs (it must run without `CPATH`). The second
builds `pokeemerald.gba`, which runs in any GBA emulator, for example mGBA.

## Putting our Pokemon into the game

From this repository:

```bash
python scripts/apply_to_expansion.py ~/sigma-expansion
```

That copies the Pokemon in `export/expansion/` (with their sprites, where they have any),
sets the starters named in `data/config.yaml`, and copies the hand-written moves, abilities and
tests in [`game/`](../game/README.md) into the game's source and hooks them in. Run it again whenever the dex has changed, then
build again. Which Pokemon are included, and what each of the others still needs, is listed
in [`export/expansion/NOT_READY.md`](../export/expansion/NOT_READY.md).

## Checking that they work

The game has an automated test system that plays battles without a screen. The export
writes two checks per Pokemon - that its data in the game matches its species file, and that
it can use its first move in a battle. Run them with the same settings as a build:

```bash
gmake check-tools
CPATH=$HOME/sigma-toolchain/arm-none-eabi/include gmake check -j8 TESTS="Sigma" \
  LIBPATH="-L \"$LIBGCC\" -L \"$HOME/sigma-toolchain/arm-none-eabi/lib\""
```

`gmake check-tools` is only needed the first time. New moves and abilities have their own
tests in the same system; see [`game/README.md`](../game/README.md).

## Screenshots straight from the ROM

`tools/gbashot/gbashot.c` runs the ROM without a window, presses buttons from a script and
saves screenshots. It needs the mGBA library, built once from source (no administrator
password; `brew install cmake` first):

```bash
git clone --depth 1 --branch 0.10.5 https://github.com/mgba-emu/mgba.git ~/sigma-toolchain/src/mgba
cd ~/sigma-toolchain/src/mgba && mkdir build && cd build
cmake .. -DBUILD_QT=OFF -DBUILD_SDL=OFF -DBUILD_SHARED=OFF -DBUILD_STATIC=ON -DUSE_FFMPEG=OFF -DUSE_LUA=OFF \
  -DUSE_SQLITE3=OFF -DUSE_ELF=OFF -DUSE_EPOXY=OFF -DUSE_LIBZIP=OFF -DUSE_MINIZIP=OFF -DUSE_EDITLINE=OFF \
  -DUSE_GDB_STUB=OFF -DUSE_DISCORD_RPC=OFF -DM_CORE_GB=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build . -j8
M=~/sigma-toolchain/src/mgba
cc -O2 -o gbashot tools/gbashot/gbashot.c -I $M/include -I $M/build/include $M/build/libmgba.a -lz -L/opt/homebrew/lib -lpng -lm -framework Foundation
```

To see the starters without playing through the story, apply `game/test-patches/starter_test.patch`
to the game (`git apply`), build, and "New Game" jumps straight to Professor Birch's bag and the
first battle. Take the patch out again (`git apply -R`) before building the real game. The
pictures in [SPRITES.md](SPRITES.md) were made this way.
