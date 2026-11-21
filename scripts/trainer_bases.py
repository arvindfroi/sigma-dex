r"""The trainer studio's base grid (2026-11-21): one sheet with frame 1 of every gen 4 trainer class the swap can start
from, and an index with each class's caption fields (the website fills the text boxes with them).

    python scripts/trainer_bases.py            (on the Legion, with the worker key)

Reads the classes where they live, on the PC only (lora-train\data\trainers\hgss and \pt, build_trainer_klein.frames and
rows; no Nintendo pictures in the repository) and puts trainer-bases/sheet.png (80x80 cells, 16 a row, see-through) and
data/trainer_bases.json in the repository (copy it back to the Mac; build_site.py puts it in the page) and the sheet
in the website's storage (sprite-worker action put_asset; the art bucket takes only pictures). HGSS 90-94 are left out: hg-engine's
pictures of them have broken palettes.
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


def main():
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
    config = dexlib.load_config().get("web_edits") or {}
    base = (config.get("url") or "").rstrip("/")
    key = sprite_worker.KEY_FILE.read_text().strip()
    with tempfile.TemporaryDirectory() as folder:
        png = Path(folder) / "sheet.png"
        sheet.save(png, optimize=True)
        print(sprite_worker.post(base, key, {"action": "put_asset", "path": "trainer-bases/sheet.png"}, {"file": png}))
    (dexlib.ROOT / "data" / "trainer_bases.json").write_text(json.dumps({"sheet": "trainer-bases/sheet.png", "cols": COLS, "cell": CELL, "bases": index},
                                                                       ensure_ascii=False, indent=0), encoding="utf-8")
    print(len(index), "bases:", sum(b["game"] == "HGSS" for b in index), "HGSS,", sum(b["game"] == "Pt" for b in index), "Pt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
