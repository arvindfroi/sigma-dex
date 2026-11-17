"""Hi-hats and cymbals from DrumSep's own stems (transcribing them from the whole drum stem is what everyone's tools
get wrong): each of hi-hat, ride and crash on its own stem, hits found by onsets, bleed from the other drums kept
out by loudness, a hi-hat open where it rings on. Runs on the Legion.

    python drums_extra.py OUTDIR
OUTDIR is chain.py's. Writes OUTDIR/drums_extra.json: [[seconds, General MIDI key, strength 0-1]]
(42 closed hi-hat, 46 open hi-hat, 51 ride, 49 crash). arrange.py --cymbals on plays them on the game's own kit.
"""
import json
import pathlib
import sys

import librosa
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from chain import DRUMSEP_MODEL, run_separator  # noqa: E402

SR, HOP = 22050, 220


def hits(path, min_gap=0.06, bleed=0.2):
    y, _ = librosa.load(str(path), sr=SR, mono=True)
    if y.size == 0 or float(np.sqrt(np.mean(y ** 2))) < 0.002:
        return [], y
    env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    times = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=HOP, units="time", backtrack=False,
                                       wait=int(min_gap * SR / HOP), delta=0.08)
    rms = librosa.feature.rms(y=y, hop_length=HOP)[0]
    loud = float(np.percentile(rms, 99.5)) or 1e-6
    out = []
    for t in times:
        i = int(t * SR / HOP)
        level = float(rms[i:i + 4].max()) if i < len(rms) else 0.0
        if level >= bleed * loud:
            out.append((float(t), min(1.0, level / loud), i))
    return out, rms


def main():
    out = pathlib.Path(sys.argv[1])
    sw = {k: pathlib.Path(v) for k, v in json.loads((out / "sep_sw" / "done.json").read_text()).items()}
    if "drums" not in sw:
        print("no drum stem")
        return
    d = run_separator(DRUMSEP_MODEL, sw["drums"], out / "sep_drums", 2)
    res = []
    hh, rms = hits(d["hh"]) if "hh" in d else ([], None)
    for t, s, i in hh:
        # open where the hat still rings 120-250 ms on at more than half of its hit (a third called 3 of 4 open)
        tail = float(rms[i + 12:i + 25].mean()) if rms is not None and i + 25 < len(rms) else 0.0
        peak = float(rms[i:i + 4].max()) if rms is not None else 1.0
        res.append([round(t, 4), 46 if peak and tail / peak > 0.5 else 42, round(s, 3)])
    for name, key, gap in (("ride", 51, 0.08), ("crash", 49, 0.25)):
        if name in d:
            for t, s, _ in hits(d[name], min_gap=gap, bleed=0.3 if name == "crash" else 0.2)[0]:
                res.append([round(t, 4), key, round(s, 3)])
    res.sort()
    (out / "drums_extra.json").write_text(json.dumps(res))
    kinds = {}
    for _, k, _ in res:
        kinds[k] = kinds.get(k, 0) + 1
    print(json.dumps({"hits": len(res), "by_key": kinds}))


if __name__ == "__main__":
    main()
