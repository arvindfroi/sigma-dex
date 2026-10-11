"""Proof of concept: a brand-new ability (Weather Switch) in Origin HeartGold v4.0.3 + English patch rc3.

Assembles weather_switch.s, puts it into overlay 14 (the battle engine) in place of Zero to Hero's code,
points ability 278 at it, renames ability 278 to "WeatherSwtch", and gives the lab rival (trainer 497)
two Pokemon: a level 1 Squirtle with FIRST_ABILITY and a level 5 Vulpix with Weather Switch.
Beat the Squirtle and the Vulpix comes in and flips the weather. See docs/ORIGIN_CUSTOM_CODE.md.

Everything here runs outside the dex repo, on Arvind's own files (Nintendo data, never committed):
  ~/sigma-origin/x_spike_backup   clean extracted Origin HG (EN rc3), read only
  ~/sigma-origin/x_ws             working copy that gets patched and rebuilt
  ~/sigma-hgengine/tools          dsrom (build) and msgenc (text)

  python3 scripts/origin_custom/build_weather_switch_test.py ~/sigma-origin/ws_weather_switch.nds [FIRST_ABILITY]
FIRST_ABILITY: 2 = Drizzle (expect rain -> sun, default), 70 = Drought (expect sun -> rain), 0 = none (random).
"""
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
CLEAN = HOME / "sigma-origin/x_spike_backup"
WORK = HOME / "sigma-origin/x_ws"
TOOLS = HOME / "sigma-hgengine/tools"
HERE = Path(__file__).resolve().parent

OV14_BASE = 0x022007E0          # overlay 14 load address (battle engine)
ABILITY_TABLE = 0x0224FF2C      # one "add handlers" function per ability id, 328 entries (ids 0-327)
ABILITY = 278                   # Zero to Hero: its id, name and code space become Weather Switch
OLD_ADD = 0x02238DCD            # Zero to Hero's add function, checked so we only patch the build we know
CAVES = {".handler": (0x02238DD8, 116), ".add": (0x02238E4C, 96)}   # Zero to Hero's two handlers
TRAINER = 497                   # Rival Blue, lab battle (first battle of the game)


def read_narc(path):
    d = path.read_bytes()
    n = struct.unpack_from("<I", d, 24)[0]
    fat = [struct.unpack_from("<II", d, 28 + 8 * i) for i in range(n)]
    off = 16 + struct.unpack_from("<I", d, 20)[0]
    fnt = d[off:off + struct.unpack_from("<I", d, off + 4)[0]]
    base = off + len(fnt) + 8
    return [d[base + s:base + e] for s, e in fat], fnt


def write_narc(path, members, fnt):
    data, fat = bytearray(), bytearray()
    for m in members:
        fat += struct.pack("<II", len(data), len(data) + len(m)); data += m
        while len(data) % 4:
            data += b"\xff"
    btaf = b"BTAF" + struct.pack("<II", 12 + len(fat), len(members)) + bytes(fat)
    gmif = b"GMIF" + struct.pack("<I", 8 + len(data)) + bytes(data)
    body = btaf + fnt + gmif
    path.write_bytes(b"NARC" + struct.pack("<HHIHH", 0xFFFE, 0x0100, 16 + len(body), 16, 3) + body)


def assemble(tmp):
    obj, elf = tmp / "ws.o", tmp / "ws.elf"
    subprocess.run(["arm-none-eabi-as", "-mcpu=arm946e-s", "-mthumb", str(HERE / "weather_switch.s"), "-o", str(obj)], check=True)
    subprocess.run(["arm-none-eabi-ld", "-T", str(HERE / "weather_switch.ld"), str(obj), "-o", str(elf)], check=True)
    out = {}
    for sec in CAVES:
        b = tmp / (sec[1:] + ".bin")
        subprocess.run(["arm-none-eabi-objcopy", "-O", "binary", "-j", sec, str(elf), str(b)], check=True)
        out[sec] = b.read_bytes()
    syms = subprocess.run(["arm-none-eabi-nm", str(elf)], check=True, capture_output=True, text=True).stdout
    add = next(int(l.split()[0], 16) for l in syms.splitlines() if l.endswith(" ws_add"))
    return out, add | 1


def text_bank(msg, bank, line, text, tmp):
    lines = (HOME / f"sigma-origin/msg/{bank:03d}.txt").read_text(encoding="utf-8").split("\n")
    lines[line] = text
    src, dst = tmp / f"{bank}.txt", tmp / f"{bank}.bin"
    src.write_text("\n".join(lines), encoding="utf-8")
    subprocess.run([str(TOOLS / "msgenc"), "-e", "-k", "0", "-c", str(HOME / "sigma-hgengine/charmap.txt"), str(src), str(dst)], check=True)
    msg[bank] = dst.read_bytes()


def main():
    out = Path(sys.argv[1]).expanduser()
    first = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    if not WORK.exists():
        shutil.copytree(CLEAN, WORK)
    tmp = WORK.parent / "ws_tmp"; tmp.mkdir(exist_ok=True)

    # 1. code into overlay 14, and the ability table entry
    code, add = assemble(tmp)
    ov = bytearray((CLEAN / "arm9_overlays/ov014.bin").read_bytes())
    entry = ABILITY_TABLE - OV14_BASE + 4 * ABILITY
    assert struct.unpack_from("<I", ov, entry)[0] == OLD_ADD, "not the Origin build this patch was written for"
    for sec, (addr, room) in CAVES.items():
        assert len(code[sec]) <= room, (sec, len(code[sec]), room)
        ov[addr - OV14_BASE:addr - OV14_BASE + len(code[sec])] = code[sec]
    struct.pack_into("<I", ov, entry, add)
    (WORK / "arm9_overlays/ov014.bin").write_bytes(ov)

    # 2. the test battle: rival party = [Lv1 Squirtle with FIRST_ABILITY, Lv5 Vulpix with Weather Switch]
    heads, hfnt = read_narc(CLEAN / "files/a/0/5/5")
    party, pfnt = read_narc(CLEAN / "files/a/0/5/6")
    h = bytearray(heads[TRAINER]); h[3] = 2; heads[TRAINER] = bytes(h)        # byte 3 = number of Pokemon
    mon = party[TRAINER][:28]                                                  # 28 bytes: ability u16 @4, level @6, species @8, item @10, moves @12
    m1 = bytearray(mon); struct.pack_into("<HHHH", m1, 4, first, 1, 7, 0)
    m2 = bytearray(mon); struct.pack_into("<HHHH", m2, 4, ABILITY, 5, 37, 0); struct.pack_into("<4H", m2, 12, 33, 0, 0, 0)
    party[TRAINER] = bytes(m1 + m2)
    write_narc(WORK / "files/a/0/5/5", heads, hfnt)
    write_narc(WORK / "files/a/0/5/6", party, pfnt)

    # 3. name and description (bank 711 = ability names, 712 = ability descriptions; 12 characters max for names)
    msg, mfnt = read_narc(CLEAN / "files/a/0/2/7")
    text_bank(msg, 711, ABILITY, "WeatherSwtch", tmp)
    text_bank(msg, 712, ABILITY, "Turns rain into sun\\nand sun into rain.", tmp)
    write_narc(WORK / "files/a/0/2/7", msg, mfnt)

    subprocess.run([str(TOOLS / "dsrom"), "build", "-c", str(WORK / "config.yaml"), "-o", str(out)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("built", out)


if __name__ == "__main__":
    main()
