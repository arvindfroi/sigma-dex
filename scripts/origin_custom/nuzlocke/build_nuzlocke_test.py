"""Nuzlocke test build for Origin HeartGold (EN rc8 with the advanced trainer AI). See README.md here.

Compiles nuzlocke.c + hooks.s for main RAM 0x023D2000 (8 KiB right below the AI's resident code), adds it as a
new ARM9 autoload section, lowers the main arena end to make room, and patches four call sites and two loops:

  arm9 0x02050042   random wild battle starts       bl nz_hook_wild    (was bl 0x0205E6F0)
  arm9 0x0204FBB8   battle end, party copied back   bl nz_battle_end   (was bl 0x02051574)
  ov9  0x021EB3D6   battle Bag, Use on a Ball        bl nz_ball_check   (was the "aim" flag test)
  arm9 0x0202B2D0, 0x0202B332   apricorn tree loops stop at 31 trees (Origin has 31), so slots 31..127 are ours
  arm9 0x020D1970   main arena end 0x023D4000 -> 0x023D2000

and adds message 0x31 to the battle Bag's text bank (a/0/2/7 bank 5). Every patched place is checked first, so
any other Origin build is refused. Runs on Arvind's own files (Nintendo data, never committed):

  ~/origin-en/.venv/bin/python scripts/origin_custom/nuzlocke/build_nuzlocke_test.py \
      ~/sigma-origin/rc8/origin_hg_en_rc8_ai.nds ~/sigma-origin/rc8/nuzlocke_test.nds

Needs arm-none-eabi-gcc (Homebrew) and the English patch repo at ~/origin-en (ndspy and its msgtool).
"""
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import ndspy.code
import ndspy.rom

HERE = Path(__file__).resolve().parent
EN = Path.home() / "origin-en"
sys.path.insert(0, str(EN / "work/tools"))
import msgtool  # noqa: E402  (the English patch's message tool, Apache-2.0)

REGION, REGION_END = 0x023D2000, 0x023D4000
ARENA_HI_WORD = 0x020D1970
BAG_BANK, BAG_MSG = 5, 0x31
BAG_TEXT = "This area’s encounter is used up!{NEWLINE}The Ball won’t work here."
GRAVEYARD_NAME = "GRAVES"
CC = ["arm-none-eabi-gcc", "-mthumb", "-mcpu=arm946e-s", "-Os", "-ffreestanding", "-fno-builtin", "-nostdlib",
      "-fno-pic", "-fno-common", "-Wall", "-Wextra", "-Werror", "-c"]


def thumb_bl(at, dest):
    off = (dest & ~1) - (at + 4)
    assert -0x400000 <= off < 0x400000 and not off & 1, hex(off)
    off &= 0x7FFFFF
    return struct.pack("<HH", 0xF000 | (off >> 12), 0xF800 | ((off >> 1) & 0x7FF))


def build_code(name_codes):
    tmp = Path(tempfile.mkdtemp(prefix="nz_"))
    (tmp / "name.c").write_text("const unsigned short nz_graveyard_name[] = {%s};\n"
                                % ", ".join("0x%04X" % c for c in name_codes))
    objs = []
    for src in (HERE / "nuzlocke.c", HERE / "hooks.s", tmp / "name.c"):
        obj = tmp / (src.stem + ".o")
        subprocess.run(CC + [str(src), "-o", str(obj)], check=True)
        objs.append(str(obj))
    elf = tmp / "nuzlocke.elf"
    subprocess.run(["arm-none-eabi-ld", "-T", str(HERE / "nuzlocke.ld"), "-o", str(elf)] + objs, check=True)
    image = tmp / "nuzlocke.bin"
    subprocess.run(["arm-none-eabi-objcopy", "-O", "binary", "--set-section-flags", ".bss=alloc,load,contents",
                    str(elf), str(image)], check=True)
    syms = {}
    for line in subprocess.run(["arm-none-eabi-nm", str(elf)], check=True, capture_output=True,
                               text=True).stdout.splitlines():
        addr, kind, sym = line.split()
        syms[sym] = int(addr, 16)
    data = image.read_bytes()
    assert REGION + len(data) <= REGION_END, "code too big: %d bytes" % len(data)
    for sym in ("nz_hook_wild", "nz_battle_end", "nz_ball_check", "nz_no_catch"):
        assert REGION <= syms[sym] < REGION + len(data), sym
    return data, syms


def patch(buf, base, at, before, after, what):
    off = at - base
    have = bytes(buf[off:off + len(before)])
    if have != before:
        sys.exit("refusing: %s at 0x%08X holds %s, expected %s (not the build this was written for)"
                 % (what, at, have.hex(), before.hex()))
    buf[off:off + len(after)] = after
    print("  %-34s 0x%08X  %s -> %s" % (what, at, before.hex(), after.hex()))


def main(src, out):
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    cm = msgtool.Charmap.load([str(EN / "work/tools/charmap_en.tsv")])
    name = msgtool.encode_text(GRAVEYARD_NAME, cm)
    name = [u for u in name if u != 0xFFFF] + [0xFFFF]
    assert len(name) <= 9
    code, syms = build_code(name)
    print("code: %d bytes at 0x%08X" % (len(code), REGION))

    arm9 = rom.loadArm9()
    main_sec = arm9.sections[0]
    assert main_sec.ramAddress == 0x02000000
    for s in arm9.sections[1:]:
        lo, hi = s.ramAddress, s.ramAddress + len(s.data) + s.bssSize
        assert hi <= REGION or lo >= REGION_END, "autoload section 0x%08X overlaps our region" % lo
    m = main_sec.data
    patch(m, 0x02000000, ARENA_HI_WORD, struct.pack("<I", REGION_END), struct.pack("<I", REGION), "main arena end")
    patch(m, 0x02000000, 0x02050042, thumb_bl(0x02050042, 0x0205E6F0), thumb_bl(0x02050042, syms["nz_hook_wild"]),
          "wild battle start")
    patch(m, 0x02000000, 0x0204FBB8, thumb_bl(0x0204FBB8, 0x02051574), thumb_bl(0x0204FBB8, syms["nz_battle_end"]),
          "battle end copy-back")
    patch(m, 0x02000000, 0x0202B2D0, bytes.fromhex("802c"), bytes.fromhex("1f2c"), "apricorn loop (daily)")
    patch(m, 0x02000000, 0x0202B332, bytes.fromhex("802b"), bytes.fromhex("1f2b"), "apricorn loop (refill)")
    arm9.sections.append(ndspy.code.MainCodeFile.Section(code, REGION, 0))
    rom.arm9 = arm9.save(compress=False)

    ovs = rom.loadArm9Overlays()
    ov9 = ovs[9]
    assert not ov9.compressed and ov9.ramAddress == 0x021E4DA0
    d9 = bytearray(rom.files[ov9.fileID])
    patch(d9, 0x021E4DA0, 0x021EB3D6, bytes.fromhex("201c2030007801280cd1"),
          thumb_bl(0x021EB3D6, syms["nz_ball_check"]) + bytes.fromhex("c046" "0128" "0cd1"), "battle Bag ball check")
    rom.files[ov9.fileID] = bytes(d9)

    narc_id = rom.filenames.idOf(msgtool.MSG_NARC_PATH)
    narc = msgtool.Narc.parse(rom.files[narc_id])
    seed, strings, trailer = msgtool.decrypt_bank(narc.files[BAG_BANK])
    assert len(strings) == BAG_MSG, "bank %d has %d lines, expected %d" % (BAG_BANK, len(strings), BAG_MSG)
    units = msgtool.encode_text(BAG_TEXT, cm)
    if not units or units[-1] != 0xFFFF:
        units.append(0xFFFF)
    strings.append(units)
    narc.files[BAG_BANK] = msgtool.encrypt_bank(seed, strings, trailer)
    rom.files[narc_id] = narc.build()
    print("  bag message 0x%02X: %s" % (BAG_MSG, BAG_TEXT))

    Path(out).write_bytes(rom.save())
    print("wrote", out)
    for sym in sorted(syms):
        if sym.startswith("nz_"):
            print("  %-20s 0x%08X" % (sym, syms[sym]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
