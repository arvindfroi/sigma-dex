"""Names each HeartGold sound by what MuScriptor hears it as: the same ear that labels the songs' parts, so a part
MuScriptor calls "trumpet" goes to the game's sound MuScriptor would also call a trumpet.

    python name_sounds_muscriptor.py SOUNDS_DIR OUT.tsv [--model large]

SOUNDS_DIR: hg_sounds_render.lua's output (one WAV per sound playing the same phrase, + sounds.json). Each WAV is
transcribed with every instrument allowed; the instrument groups of its notes are counted. Writes
data/music/hg_sound_names.tsv's format: id, kind, use, then the three likeliest names with their share of the notes.
"""
import argparse
import collections
import json
import pathlib

from muscriptor.events import NoteStartEvent
from muscriptor.transcription_model import TranscriptionModel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sounds")
    ap.add_argument("out")
    ap.add_argument("--model", default="large")
    a = ap.parse_args()
    src = pathlib.Path(a.sounds)
    meta = {s["id"]: s for s in json.loads((src / "sounds.json").read_text())}
    model = TranscriptionModel.load_model(a.model)
    rows = []
    files = sorted(src.glob("*.wav"))
    for i, f in enumerate(files):
        count = collections.Counter()
        for e in model.transcribe(str(f), cfg_coef=1.5):
            if isinstance(e, NoteStartEvent):
                count[e.instrument] += 1
        total = sum(count.values()) or 1
        top = count.most_common(3)
        while len(top) < 3:
            top.append(("none", 0))
        m = meta.get(f.stem, {})
        rows.append([f.stem, str(m.get("kind")), str(m.get("use", 0))] +
                    [x for name, n in top for x in (name, f"{n / total:.2f}")])
        if i % 25 == 0:
            print(i, f.stem, top, flush=True)
    with open(a.out, "w") as fh:
        fh.write("# id\tkind\tuse_seconds\tname1\tshare1\tname2\tshare2\tname3\tshare3  (MuScriptor "
                 f"{a.model}, cfg 1.5, on a C-E-G-C phrase per sound, 2026-11-16)\n")
        for r in sorted(rows):
            fh.write("\t".join(r) + "\n")
    names = collections.Counter(r[3] for r in rows)
    print(len(rows), "sounds named;", dict(names.most_common()))


if __name__ == "__main__":
    main()
