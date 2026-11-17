"""Merges the listening page's export (music_tests/lytt/index.html -> ~/Downloads/hg_instrumenter_arvind.json) into
data/music/hg_instruments.tsv: every sound Arvind named by ear becomes a verified row (source "arvind (by ear)"),
replacing that sound's earlier row. "unknown" choices are left out.

    python3 import_listen.py [~/Downloads/hg_instrumenter_arvind.json]
"""
import json
import pathlib
import sys

R = pathlib.Path(__file__).resolve().parents[2]
TSV = R / "data/music/hg_instruments.tsv"


def main():
    src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path.home() / "Downloads/hg_instrumenter_arvind.json")
    chosen = {k: v for k, v in json.loads(src.read_text()).items() if v and v != "unknown"}
    head, rows = [], {}
    for line in TSV.read_text().splitlines():
        if line.startswith("b"):
            f = line.split("\t")
            rows[f[0]] = f
        else:
            head.append(line)
    for sid, group in chosen.items():
        rows[sid] = [sid, group, "arvind (by ear)"]
    order = sorted(rows.values(), key=lambda f: [int(x) for x in f[0][1:].split(".")])
    TSV.write_text("\n".join(head + ["\t".join(f) for f in order]) + "\n")
    print(f"{len(chosen)} sounds from {src.name}; {len(rows)} verified rows in {TSV.name}")


if __name__ == "__main__":
    main()
