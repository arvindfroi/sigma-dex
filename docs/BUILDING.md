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

That copies everything in `export/expansion/` into the game's source and hooks it in at the
places expansion reserves for custom species. Run it again whenever the dex has changed, then
build again. Which Pokemon are included, and what each of the others still needs, is listed
in [`export/expansion/NOT_READY.md`](../export/expansion/NOT_READY.md).

## Checking that they work

The game has an automated test system that plays battles without a screen. The export
writes two checks per Pokemon - that its data in the game matches its species file, and that
it can use its first move in a battle. Run them with the same settings as a build:

```bash
CPATH=$HOME/sigma-toolchain/arm-none-eabi/include gmake check -j8 TESTS="Sigma dex" \
  LIBPATH="-L \"$LIBGCC\" -L \"$HOME/sigma-toolchain/arm-none-eabi/lib\""
```

New moves and abilities get their own tests in the same system when they are programmed.
