"""Nuzlocke test build for Origin HeartGold (EN rc8 with the advanced trainer AI). See README.md here.

Compiles nuzlocke.c + hooks.s for main RAM 0x023D2000 (8 KiB right below the AI's resident code), adds it as a
new ARM9 autoload section, lowers the main arena end to make room, and patches:

  arm9 0x02050042   random wild battle starts          bl nz_hook_wild         (was bl 0x0205E6F0)
  arm9 0x0204FBB8   battle end, party copied back      bl nz_battle_end        (was bl 0x02051574)
  arm9 0x02051278   every field battle is set up       bl nz_hook_setup        (was bl 0x02051074)
  arm9 0x0207A8E6   party screen, item on a Pokemon    bl nz_hook_party_item   (was bl 0x0208FA38)
  arm9 0x02042050   the PC closes (script cmd 158)     bl nz_pc_closed         (was bl 0x020926B8)
  ov9  0x021EB2A4   battle Bag, Use (any item)         adds r7,r0,#0 ; bl nz_bag_use
  ov9  0x021EB3D6   battle Bag, Use on a Ball          bl nz_ball_check        (was the "aim" flag test)
  ov16 0x021F211C   PC box loaded its icon palettes    bl nz_hook_pc_palettes  (was bl 0x020731FC)
  ov16 0x021F2288, 0x021F22F8   PC box icon palette    bl nz_icon_palette      (was bl 0x020731A4)
  arm9 0x0202B2D0, 0x0202B332   apricorn tree loops stop at 31 trees (Origin has 31), so slots 31..127 are ours
  arm9 0x020D1970   main arena end 0x023D4000 -> 0x023D2000

and adds messages 0x31-0x33 to the battle Bag's text bank (a/0/2/7 bank 5). The grey icon palettes are computed
from the game's own icon palettes (a/0/2/0 file 0). Every patched place is checked first, so any other Origin
build is refused. Runs on Arvind's own files (Nintendo data, never committed):

  ~/origin-en/.venv/bin/python scripts/origin_custom/nuzlocke/build_nuzlocke_test.py \
      ~/sigma-origin/rc8/origin_hg_en_rc8_ai.nds ~/sigma-origin/rc8/nuzlocke_test.nds [MODE]

MODE: the mode a save without nuzlocke data starts in (test builds only): 1 nuzlocke (default), 2 hardcore.
Needs arm-none-eabi-gcc (Homebrew) and the English patch repo at ~/origin-en (ndspy and its msgtool).
"""
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import ndspy.code
import ndspy.narc
import ndspy.rom

HERE = Path(__file__).resolve().parent
EN = Path.home() / "origin-en"
sys.path.insert(0, str(EN / "work/tools"))
import msgtool  # noqa: E402  (the English patch's message tool, Apache-2.0)

REGION, REGION_END = 0x023D2000, 0x023D4000
ARENA_HI_WORD = 0x020D1970
BAG_BANK = 5
BAG_TEXTS = {   # new lines of the battle Bag's text bank, by id
    0x31: "This area’s encounter is used up!{NEWLINE}The Ball won’t work here.",
    0x32: "Hardcore Nuzlocke: no items can be{NEWLINE}used in battle!",
    0x33: "Nuzlocke: a fainted Pokémon can’t{NEWLINE}be brought back!",
}
GRAVEYARD_NAME = "GRAVES"
CC = ["arm-none-eabi-gcc", "-mthumb", "-mcpu=arm946e-s", "-Os", "-ffreestanding", "-fno-builtin", "-nostdlib",
      "-fno-pic", "-fno-common", "-Wall", "-Wextra", "-Werror", "-c"]


def thumb_bl(at, dest):
    off = (dest & ~1) - (at + 4)
    assert -0x400000 <= off < 0x400000 and not off & 1, hex(off)
    off &= 0x7FFFFF
    return struct.pack("<HH", 0xF000 | (off >> 12), 0xF800 | ((off >> 1) & 0x7FF))


def grey_icon_palettes(rom):
    """The game's three icon palettes (a/0/2/0 file 0, NCLR) as grey: each colour's luma, a little lighter so
    the icons look faded. Colour 0 (transparent) stays."""
    nclr = ndspy.narc.NARC(rom.getFileByName("a/0/2/0")).files[0]
    assert nclr[:4] == b"RLCN" and nclr[0x10:0x14] == b"TTLP"
    off = struct.unpack_from("<I", nclr, 0x24)[0]
    data = nclr[0x18 + off:0x18 + off + 0x60]
    out = []
    for i, c in enumerate(struct.unpack("<48H", data)):
        if i % 16 == 0:
            out.append(c)
            continue
        r, g, b = (c & 31), (c >> 5 & 31), (c >> 10 & 31)
        y = (r * 77 + g * 150 + b * 29) >> 8
        y = min(31, 6 + y * 3 // 4)
        out.append(y | y << 5 | y << 10)
    return out


def build_code(name_codes, grey, mode):
    tmp = Path(tempfile.mkdtemp(prefix="nz_"))
    (tmp / "gen.c").write_text(
        "const unsigned short nz_graveyard_name[] = {%s};\n" % ", ".join("0x%04X" % c for c in name_codes)
        + "const unsigned short nz_grey_icon_pal[48] = {%s};\n" % ", ".join("0x%04X" % c for c in grey))
    objs = []
    for src in (HERE / "nuzlocke.c", HERE / "hooks.s", tmp / "gen.c"):
        obj = tmp / (src.stem + ".o")
        subprocess.run(CC + ["-DNZ_TEST_MODE=%d" % mode, str(src), "-o", str(obj)], check=True)
        objs.append(str(obj))
    elf = tmp / "nuzlocke.elf"
    subprocess.run(["arm-none-eabi-ld", "--no-warn-rwx-segments", "-T", str(HERE / "nuzlocke.ld"), "-o", str(elf)]
                   + objs, check=True)
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
    for sym in ("nz_hook_wild", "nz_battle_end", "nz_hook_setup", "nz_hook_party_item", "nz_bag_use",
                "nz_ball_check", "nz_hook_pc_palettes", "nz_icon_palette", "nz_no_catch", "nz_battle_mode",
                "nz_pc_closed"):
        assert REGION <= syms[sym] < REGION + len(data), sym
    return data, syms, elf


def patch(buf, base, at, before, after, what):
    off = at - base
    have = bytes(buf[off:off + len(before)])
    if have != before:
        sys.exit("refusing: %s at 0x%08X holds %s, expected %s (not the build this was written for)"
                 % (what, at, have.hex(), before.hex()))
    buf[off:off + len(after)] = after
    print("  %-36s 0x%08X  %s -> %s" % (what, at, before.hex(), after.hex()))


def patch_bl(buf, base, at, old_dest, new_dest, what):
    patch(buf, base, at, thumb_bl(at, old_dest), thumb_bl(at, new_dest), what)


def main(src, out, mode=1):
    rom = ndspy.rom.NintendoDSRom.fromFile(src)
    cm = msgtool.Charmap.load([str(EN / "work/tools/charmap_en.tsv")])
    name = [u for u in msgtool.encode_text(GRAVEYARD_NAME, cm) if u != 0xFFFF] + [0xFFFF]
    assert len(name) <= 9
    code, syms, elf = build_code(name, grey_icon_palettes(rom), mode)
    print("code: %d bytes at 0x%08X, test mode %d (%s)" % (len(code), REGION, mode, elf))

    arm9 = rom.loadArm9()
    main_sec = arm9.sections[0]
    assert main_sec.ramAddress == 0x02000000
    for s in arm9.sections[1:]:
        lo, hi = s.ramAddress, s.ramAddress + len(s.data) + s.bssSize
        assert hi <= REGION or lo >= REGION_END, "autoload section 0x%08X overlaps our region" % lo
    m, A = main_sec.data, 0x02000000
    patch(m, A, ARENA_HI_WORD, struct.pack("<I", REGION_END), struct.pack("<I", REGION), "main arena end")
    patch_bl(m, A, 0x02050042, 0x0205E6F0, syms["nz_hook_wild"], "wild battle start")
    patch_bl(m, A, 0x0204FBB8, 0x02051574, syms["nz_battle_end"], "battle end copy-back")
    patch_bl(m, A, 0x02051278, 0x02051074, syms["nz_hook_setup"], "field battle setup")
    patch_bl(m, A, 0x0207A8E6, 0x0208FA38, syms["nz_hook_party_item"], "party screen item check")
    patch_bl(m, A, 0x02042050, 0x020926B8, syms["nz_pc_closed"], "PC closed")
    patch(m, A, 0x0202B2D0, bytes.fromhex("802c"), bytes.fromhex("1f2c"), "apricorn loop (daily)")
    patch(m, A, 0x0202B332, bytes.fromhex("802b"), bytes.fromhex("1f2b"), "apricorn loop (refill)")
    arm9.sections.append(ndspy.code.MainCodeFile.Section(code, REGION, 0))
    rom.arm9 = arm9.save(compress=False)

    ovs = rom.loadArm9Overlays()
    ov9, ov16 = ovs[9], ovs[16]
    assert not ov9.compressed and ov9.ramAddress == 0x021E4DA0
    assert not ov16.compressed and ov16.ramAddress == 0x021E4980
    d9 = bytearray(rom.files[ov9.fileID])
    patch(d9, 0x021E4DA0, 0x021EB2A4, bytes.fromhex("6549071c685c"),
          bytes.fromhex("071c") + thumb_bl(0x021EB2A6, syms["nz_bag_use"]), "battle Bag item check")
    patch(d9, 0x021E4DA0, 0x021EB3D6, bytes.fromhex("201c2030007801280cd1"),
          thumb_bl(0x021EB3D6, syms["nz_ball_check"]) + bytes.fromhex("c046" "0128" "0cd1"), "battle Bag ball check")
    rom.files[ov9.fileID] = bytes(d9)
    d16 = bytearray(rom.files[ov16.fileID])
    patch_bl(d16, 0x021E4980, 0x021F211C, 0x020731FC, syms["nz_hook_pc_palettes"], "PC grey palettes")
    patch_bl(d16, 0x021E4980, 0x021F2288, 0x020731A4, syms["nz_icon_palette"], "PC icon palette (box)")
    patch_bl(d16, 0x021E4980, 0x021F22F8, 0x020731A4, syms["nz_icon_palette"], "PC icon palette (one)")
    rom.files[ov16.fileID] = bytes(d16)

    narc_id = rom.filenames.idOf(msgtool.MSG_NARC_PATH)
    narc = msgtool.Narc.parse(rom.files[narc_id])
    seed, strings, trailer = msgtool.decrypt_bank(narc.files[BAG_BANK])
    assert len(strings) == min(BAG_TEXTS), "bank %d has %d lines, expected %d" % (BAG_BANK, len(strings),
                                                                                 min(BAG_TEXTS))
    for msg_id in sorted(BAG_TEXTS):
        units = msgtool.encode_text(BAG_TEXTS[msg_id], cm)
        if not units or units[-1] != 0xFFFF:
            units.append(0xFFFF)
        strings.append(units)
        print("  bag message 0x%02X: %s" % (msg_id, BAG_TEXTS[msg_id]))
    narc.files[BAG_BANK] = msgtool.encrypt_bank(seed, strings, trailer)
    rom.files[narc_id] = narc.build()

    Path(out).write_bytes(rom.save())
    Path(str(out) + ".symbols.json").write_text(json.dumps({k: v for k, v in syms.items() if k.startswith("nz_")},
                                                           indent=1))
    print("wrote", out, "and its .symbols.json")
    for sym in sorted(syms):
        if sym.startswith("nz_"):
            print("  %-24s 0x%08X" % (sym, syms[sym]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1)
