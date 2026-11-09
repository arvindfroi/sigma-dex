"""Footprints: every Sigma Pokemon borrows the footprint of one official Pokemon from HeartGold.

The official footprints are Nintendo data, so they are NOT stored in this repo. A species file only
says which one it borrows, e.g. `footprint: "hgss:4"` = Charmander's footprint. The export to Origin
HeartGold copies the real picture from the ROM at build time.

How they were picked (2026-11-09): each of our evolution lines is matched to an official line with
similar feet, stage by stage (Tinky -> Motinky -> Gortiki = Chimchar -> Monferno -> Infernape), so every
Pokemon gets its own footprint and a line still looks related. Floating Pokemon without feet get one
of the official blank footprints, like Gastly or Drifloon in the real games.

  python3 scripts/footprints.py                    # write the choices into the species files
  python3 scripts/footprints.py --preview out.png  # picture of all choices (needs ~/sigma-origin, keep it out of the repo)
"""
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROM_FILES = Path.home() / "sigma-origin/x_spike_backup/files"   # extracted Origin HeartGold (outside the repo)

# Our species file -> official national dex number whose HeartGold footprint it uses.
FOOT = {
    # starters and their lines
    "leafing": 1, "leafsteel": 2, "leafaxer": 3,                 # Bulbasaur line
    "waffy": 258, "wealther": 259, "warrallier": 260,            # Mudkip line (webbed)
    "torchbat": 4, "heatbat": 5, "blazterra": 6,                 # Charmander line
    "erobi": 16, "harpie": 17, "smeatherace": 18,                # Pidgey line
    "bolthook": 430, "wump": 167, "twemp": 69, "florantula": 168,
    "pipwi": 84, "pipwi-utv": 85,                                # Doduo, Dodrio
    "slamquake": 68, "cowfin": 241, "mooceon": 128,
    "lapper": 58, "brawleo": 59,                                 # Growlithe, Arcanine
    "sigmanian-sudowoodo": 185,                                  # Sudowoodo
    "icy-freeze": 427, "freezrick": 428,                         # Buneary, Lopunny
    "bulbtle": 387, "bulbtoise": 388,                            # Turtwig, Grotle
    "wispole": 60, "galfrogtom": 61, "croakble": 62,             # Poliwag line
    "eiscue": 393, "chillalit": 394,                             # Piplup, Prinplup
    "rainbro": 280, "coati": 161, "coatail": 162,                # Ralts; Sentret, Furret
    "nukfae": 422, "toxiren": 423,                               # Shellos, Gastrodon
    "stonma": 74, "sigmauler": 76,                               # Geodude (blank), Golem
    "tinky": 390, "motinky": 391, "gortiki": 392,                # Chimchar line
    "chebbi": 207, "devampry": 472,                              # Gligar, Gliscor
    "zapana": 265, "ampeel": 290,
    "tomaterdander": 108, "crappy-meal": 463,                    # Lickitung, Lickilicky
    "beatld": 122, "fleuroom": 285, "fleuroom-utvikling": 286,   # Mr. Mime; Shroomish, Breloom
    "giga-circuit": 125, "hippore": 111, "docuphant": 232, "razox": 473,
    "bulgarian-unown": 81, "united": 82,                         # Magnemite, Magneton
    "hairyen": 114, "panzerien": 411, "nucloid": 345, "nuclobyl": 377,
    "yanklet": 351, "anjane": 106, "janenon": 40,
    "saucerl": 224, "abyssys": 138, "octopearl": 139,
    "cryoblade": 460, "roostasaur": 257, "bygon": 442,
    "leadling": 304, "leadling-utvikling": 305, "blylem": 306,   # Aron line
    "iglomodo-mindre-utv": 159, "iglomodo": 160,                 # Croconaw, Feraligatr
    "furamire": 77, "ciggiti": 92, "chuchar": 93, "parahaunt": 200,
    "insectoid": 123, "darkgonark": 149, "detecup": 447, "snownin": 478, "verrith": 67,
    "sigmanian-komala": 216, "dahrugula": 217,                   # Teddiursa, Ursaring
    "vires": 46, "flurina": 47, "dragem": 158, "quimsy": 63,
    "skiirtle": 7, "mcskiirtle": 9,                              # Squirtle, Blastoise
    "ambuger": 193, "ambcoptr": 469,                             # Yanma, Yanmega
    "tortoplasm": 98, "tortoplasm-utviklet": 99,                 # Krabby, Kingler
    "slothbaby": 287, "slothbaby-utviklet": 288,                 # Slakoth, Vigoroth
    "gaiafinn": 444, "obsidog": 228, "obsidog-utvikling": 229,   # Gabite; Houndour, Houndoom
    "limulk": 296, "mortbulk": 297, "eivomon": 143,              # Makuhita, Hariyama; Snorlax
    "oraclet": 396, "oraclaw": 397,                              # Starly, Staravia
    "alminimonk": 307, "alminimonk-utvikling": 308,              # Meditite, Medicham
    "zapitera-mindre-utv": 276, "zapitera": 277,                 # Taillow, Swellow
    "viridub": 403, "viridub-utvikling": 404,                    # Shinx, Luxio
    "shadeem": 64, "shadrove": 65,                               # Kadabra, Alakazam
    "autuman": 274, "bugmight": 214,
    "jawie": 408, "jawbreaker": 409,                             # Cranidos, Rampardos
    "dreadipede": 451, "dreadfang": 452,                         # Skorupi, Drapion
    "surfer": 37, "subwaysurfer": 38,                            # Vulpix, Ninetales
    "zyzzfu": 448, "grincho": 302, "glac-p-e": 475, "everdark": 461,
    "diedo": 176, "seraphinnen": 468,                            # Togetic, Togekiss
    "riftbloom": 425, "phantomb": 353, "sjef": 354,              # Drifloon; Shuppet, Banette
    "moosus": 234, "rockedeer": 78, "sabertann": 221, "gravriel": 355,
    "balleisk": 371, "greation": 372, "ultragon": 373,           # Bagon line
    "bergflabbser": 382, "maagamad": 279, "sandrema": 150,       # Kyogre, Pelipper, Mewtwo
}


def write_species_files():
    seen = {}
    for species, num in FOOT.items():
        if num in seen:
            raise SystemExit(f"{species} and {seen[num]} both use #{num}")
        seen[num] = species
    for species, num in sorted(FOOT.items()):
        path = ROOT / "data/species" / f"{species}.yaml"
        text = path.read_text(encoding="utf-8")
        new = re.sub(r"(?m)^(  footprint:).*$", lambda m: f'{m.group(1)} "hgss:{num}"', text, count=1)
        if new != text:
            path.write_text(new, encoding="utf-8")
    missing = sorted(p.stem for p in (ROOT / "data/species").glob("*.yaml") if p.stem not in FOOT)
    print(len(FOOT), "footprints set; none yet:", missing)


# --- reading the official footprints from the ROM (a/0/6/9: member n+3 = footprint of species n) ---

def read_narc(path):
    d = path.read_bytes()
    n = struct.unpack_from("<I", d, 24)[0]
    fat = [struct.unpack_from("<II", d, 28 + 8 * i) for i in range(n)]
    off = 16 + struct.unpack_from("<I", d, 20)[0]
    base = off + struct.unpack_from("<I", d, off + 4)[0] + 8
    return [d[base + s:base + e] for s, e in fat]


def lz10(d):
    n = d[1] | d[2] << 8 | d[3] << 16; out = bytearray(); i = 4
    while len(out) < n:
        flags = d[i]; i += 1
        for b in range(8):
            if len(out) >= n:
                break
            if flags & (0x80 >> b):
                x = d[i] << 8 | d[i + 1]; i += 2
                for _ in range((x >> 12) + 3):
                    out.append(out[-((x & 0xFFF) + 1)])
            else:
                out.append(d[i]); i += 1
    return bytes(out)


def official_footprint(members, num):
    """16x16 grid (1 = ink). The graphic is 32x16 in 8x8 tiles; the print is tiles 4,5 over tiles 0,1."""
    g = lz10(members[num + 3])
    data = g[16 + 0x20:16 + 0x20 + 256]
    grid = [[0] * 16 for _ in range(16)]
    for t in (0, 1, 4, 5):
        tx, ty = (t % 4) * 8, (1 - t // 4) * 8
        for p in range(64):
            b = data[t * 32 + p // 2]
            if (b >> 4 if p % 2 else b & 15):
                grid[ty + p // 8][tx + p % 8] = 1
    return grid


def preview(out):
    import yaml
    from PIL import Image, ImageDraw, ImageFont
    members = read_narc(ROM_FILES / "a/0/6/9")
    official = [l.rstrip("\n") for l in open(Path.home() / "sigma-origin/msg/232.txt", encoding="utf-8")]
    rows = []
    for species, num in FOOT.items():
        y = yaml.safe_load(open(ROOT / "data/species" / f"{species}.yaml"))
        name = str(y.get("name") or species)
        rows.append((y.get("dex") or 999, name[:1].upper() + name[1:], num))
    rows.sort()
    bold = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 15)
    small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 12)
    cols, cw, ch, S = 10, 160, 100, 4
    img = Image.new("RGB", (cols * cw + 20, (len(rows) + cols - 1) // cols * ch + 70), (246, 244, 238))
    d = ImageDraw.Draw(img)
    d.text((14, 18), "Sigma Dex: fotavtrykk (lånt fra de offisielle i HeartGold, ett per Pokémon)", fill=(30, 30, 30),
           font=ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 24))
    for k, (dex, name, num) in enumerate(rows):
        x, y = 10 + (k % cols) * cw, 60 + (k // cols) * ch
        d.rounded_rectangle((x + 2, y, x + cw - 4, y + ch - 6), 8, fill="white", outline=(220, 215, 205))
        grid = official_footprint(members, num)
        for yy in range(16):
            for xx in range(16):
                if grid[yy][xx]:
                    d.rectangle((x + 10 + xx * S, y + 8 + yy * S, x + 9 + (xx + 1) * S, y + 7 + (yy + 1) * S), fill="black")
        if not any(map(any, grid)):
            d.text((x + 16, y + 34), "(tomt)", fill=(150, 150, 150), font=small)
        d.text((x + 80, y + 10), f"#{dex}", fill=(120, 0, 0), font=bold)
        d.text((x + 80, y + 30), name[:11], fill=(30, 30, 30), font=bold)
        d.text((x + 80, y + 52), f"som {official[num][:10]}", fill=(110, 110, 110), font=small)
    img.save(out)


if __name__ == "__main__":
    write_species_files()
    if "--preview" in sys.argv:
        preview(sys.argv[sys.argv.index("--preview") + 1])
