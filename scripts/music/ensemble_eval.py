"""Which way of putting the stems' and the mix's notes together finds the song best, from chain.py's kept notes
(OUTDIR/notes/*.json: [start, end, pitch, instrument] in seconds, before any quantizing), scored against a truth.

    python3 ensemble_eval.py truth.json NOTES_DIR [--until 58.3]
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from compare_notes import GROUP, family, match, prf  # noqa: E402

GROUP_OF_NAME = {}
for p, g in GROUP.items():
    GROUP_OF_NAME.setdefault(g, p)
NAME_FIX = {"soprano_and_alto_sax": "sax", "tenor_sax": "sax", "baritone_sax": "sax"}


def program_of(name):
    return GROUP_OF_NAME.get(NAME_FIX.get(name, name), -1)


def dedupe(notes, tol=0.05):
    """notes from several sources, one kept where two say the same pitch at the same time (the first listed wins)"""
    kept = []
    by_pitch = {}
    for n in notes:
        lst = by_pitch.setdefault(n[2], [])
        if any(abs(m[0] - n[0]) <= tol for m in lst):
            continue
        lst.append(n)
        kept.append(n)
    return kept


def score(truth, notes, shift, tol=0.05, programs=True):
    got = [(n[0] + shift, n[2], program_of(n[3])) for n in notes if n[3] != "drums"]
    pairs = match(truth, got, tol, lambda a, b: a[1] == b[1])
    res = {"notes": len(got), "f1": prf(len(pairs), len(got), len(truth))}
    if programs:
        res["group"] = round(sum(1 for ti, gi in pairs if GROUP.get(truth[ti][2]) == GROUP.get(got[gi][2])) / max(1, len(pairs)), 3)
        res["family"] = round(sum(1 for ti, gi in pairs if family(truth[ti][2]) == family(got[gi][2])) / max(1, len(pairs)), 3)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("truth")
    ap.add_argument("notes")
    ap.add_argument("--until", type=float, default=58.3)
    a = ap.parse_args()
    t = json.load(open(a.truth))
    truth = [(n[1], n[3], n[4]) for n in t["notes"] if n[5] == "note" and n[1] < a.until]
    programs = "programs" in t
    d = pathlib.Path(a.notes)
    src = {}
    for f in d.glob("*_large_b1_c1.0.json"):
        src[f.name.split("_large")[0]] = [tuple(x) for x in json.loads(f.read_text()) if x[0] < a.until + 1]
    print("sources:", {k: len(v) for k, v in src.items()})
    # the raw times are the audio's: no shift to search (MuScriptor's own onsets)
    stems = [n for k in ("vocals", "bass", "piano", "guitar", "other") for n in src.get(k, [])]
    mix = src.get("mix", [])
    bass = src.get("bass", [])
    lowmix = [n for n in mix if program_of(n[3]) not in range(32, 40)]
    combos = {
        "stems": stems,
        "mix": mix,
        "mix+stems (mix first)": dedupe(sorted(mix, key=lambda n: n[0]) + sorted(stems, key=lambda n: n[0])),
        "stems+mix (stems first)": dedupe(sorted(stems, key=lambda n: n[0]) + sorted(mix, key=lambda n: n[0])),
        "mix without its bass + bass stem": dedupe(lowmix + bass),
    }
    for name, notes in combos.items():
        print(f"{name:34s}", json.dumps(score(truth, notes, 0.0, programs=programs)))


if __name__ == "__main__":
    main()
