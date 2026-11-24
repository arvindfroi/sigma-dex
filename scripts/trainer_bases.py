r"""The trainer studio's base grid (2026-11-21): one sheet with frame 1 of every gen 4 trainer class the swap can start
from, and an index with each class's caption fields (the website fills the text boxes with them).

    python scripts/trainer_bases.py            (on the Legion, with the worker key)

Reads the classes where they live, on the PC only (lora-train\data\trainers\hgss and \pt, build_trainer_klein.frames and
rows; no Nintendo pictures in the repository) and puts trainer-bases/sheet.png (80x80 cells, 16 a row, see-through) and
data/trainer_bases.json in the repository (copy it back to the Mac; build_site.py puts it in the page) and the sheet
in the website's storage (sprite-worker action put_asset; the art bucket takes only pictures). HGSS 90-94 are left out: hg-engine's
pictures of them have broken palettes.

    python scripts/trainer_bases.py --origin   (on the Legion; 2026-11-24)

Adds Origin's own trainer pictures (the classes Origin redrew: Red, Leaf, Steven, Cynthia, Gold, Lance ...) as bases
'origin:N' with their own sheet trainer-bases/origin.png, so the first sheet and its cells stay as they are. The frames
come from the PC (lora-train\data\trainers\origin_fronts\NNN.png, dumped from Origin's a/0/5/8 member 0 by cell 0 with
~/sigma-origin/title3d/legend/trainers/dump_origin_fronts.py); labels and words from data/trainer_bases_origin.json.
"""
import json
import sys
import tempfile
from pathlib import Path

from PIL import Image

import dexlib
import sprite_worker
import trainer_studio

COLS, CELL = 16, 80
SKIP = set(range(90, 95))


def bases():
    T, _, _ = trainer_studio._modules()
    rows = T.rows()
    out = []
    for f in sorted((T.SRC).glob("*_enc.png")):
        n = int(f.name[:3])
        if n not in SKIP:
            out.append(("hgss:%d" % n, n, "HGSS"))
    for f in sorted((T.L / "data" / "trainers" / "pt").glob("*.png")):
        out.append(("pt:" + f.stem, "pt/" + f.stem, "Pt"))
    return T, rows, out


def upload(sheet, path):
    config = dexlib.load_config().get("web_edits") or {}
    base = (config.get("url") or "").rstrip("/")
    key = sprite_worker.KEY_FILE.read_text().strip()
    with tempfile.TemporaryDirectory() as folder:
        png = Path(folder) / "sheet.png"
        sheet.save(png, optimize=True)
        print(sprite_worker.post(base, key, {"action": "put_asset", "path": path}, {"file": png}))


def origin():
    meta = json.loads((dexlib.ROOT / "data" / "trainer_bases_origin.json").read_text(encoding="utf-8"))["bases"]
    cells, entries = [], []
    for m in meta:
        f = trainer_studio.ORIGIN_FRONTS / ("%03d.png" % m["n"])
        im = Image.open(f).convert("RGBA")
        if not im.getbbox():
            continue
        entries.append({"id": "origin:%d" % m["n"], "game": "Origin", "label": m["label"], "sheet": "trainer-bases/origin.png", "i": len(cells),
                        "fields": {k: m[k] for k in ("cls", "who") if m.get(k)}})
        cells.append(im)
    sheet = Image.new("RGBA", (COLS * CELL, -(-len(cells) // COLS) * CELL), (0, 0, 0, 0))
    for i, f in enumerate(cells):
        sheet.alpha_composite(f, ((i % COLS) * CELL, (i // COLS) * CELL))
    upload(sheet, "trainer-bases/origin.png")
    out = dexlib.ROOT / "data" / "trainer_bases.json"
    index = json.loads(out.read_text(encoding="utf-8"))
    index["bases"] = [b for b in index["bases"] if b.get("game") != "Origin"] + entries
    out.write_text(json.dumps(index, ensure_ascii=False, indent=0), encoding="utf-8")
    print(len(entries), "Origin bases")
    return 0


def main():
    if "--origin" in sys.argv:
        return origin()
    T, rows, found = bases()
    cells, index = [], []
    for bid, key, game in found:
        f1, _ = T.frames(key)
        if not f1.getbbox():
            continue
        r = rows.get(key) or {}
        label = r.get("cls") or str(key).split("/")[-1].replace("_", " ").title()
        index.append({"id": bid, "game": game, "label": label,
                      "fields": {k: r.get(k, "") for k in trainer_studio.FIELDS if r.get(k) and r.get(k) != "-"}})
        cells.append(f1)
    sheet = Image.new("RGBA", (COLS * CELL, -(-len(cells) // COLS) * CELL), (0, 0, 0, 0))
    for i, f in enumerate(cells):
        sheet.alpha_composite(f, ((i % COLS) * CELL, (i // COLS) * CELL))
    upload(sheet, "trainer-bases/sheet.png")
    old = dexlib.ROOT / "data" / "trainer_bases.json"
    index += [b for b in json.loads(old.read_text(encoding="utf-8"))["bases"] if b.get("game") == "Origin"] if old.exists() else []   # --origin's own sheet
    (dexlib.ROOT / "data" / "trainer_bases.json").write_text(json.dumps({"sheet": "trainer-bases/sheet.png", "cols": COLS, "cell": CELL, "bases": index},
                                                                       ensure_ascii=False, indent=0), encoding="utf-8")
    print(len(index), "bases:", sum(b["game"] == "Origin" for b in index), "Origin,", sum(b["game"] == "HGSS" for b in index), "HGSS,", sum(b["game"] == "Pt" for b in index), "Pt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
