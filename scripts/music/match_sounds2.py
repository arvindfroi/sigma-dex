"""Timbre matching of HeartGold sounds to General MIDI programs (MFCCs, brightness, attack and decay; no remote
model code), tried two ways and scored on the guide's 10
known sounds (see match_sounds.py). Writes the best method's matches.

    python match_sounds2.py SOUNDS_DIR OUT.tsv
"""
import json
import pathlib
import sys

import librosa
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from match_sounds import KNOWN, phrase_gm  # noqa: E402

SR = 22050


def timbre(y):
    """the first note (C4, 0.5 s) and the held low C: MFCCs' mean and spread, brightness, how fast it starts and
    fades, how noisy"""
    y = y / (np.abs(y).max() + 1e-9)
    n1 = y[: int(0.5 * SR)]
    held = y[int(2.0 * SR): int(3.0 * SR)]
    feats = []
    for seg in (n1, held):
        if seg.size < 2048:
            seg = np.pad(seg, (0, 2048 - seg.size))
        m = librosa.feature.mfcc(y=seg, sr=SR, n_mfcc=20)
        feats += list(m.mean(1)[1:]) + list(m.std(1)[1:])
        feats.append(float(librosa.feature.spectral_centroid(y=seg, sr=SR).mean()) / 1000)
        feats.append(float(librosa.feature.spectral_flatness(y=seg).mean()) * 10)
        env = librosa.feature.rms(y=seg, hop_length=256)[0]
        pk = int(env.argmax())
        feats.append(pk / len(env) * 10)  # attack
        feats.append(float(env[-1] / (env[pk] + 1e-9)) * 5)  # how much is left at the end
    return np.array(feats, float)


def main():
    src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    import tinysoundfont
    from muscriptor.soundfonts import SF2_URL
    from muscriptor.utils.download import download_if_necessary

    synth = tinysoundfont.Synth(samplerate=44100)
    sfid = synth.sfload(str(download_if_necessary(SF2_URL)))
    gm_audio = []
    for prog in range(128):
        synth.program_select(0, sfid, 0, prog)
        gm_audio.append(librosa.resample(phrase_gm(synth, prog), orig_sr=44100, target_sr=SR))
        synth.notes_off()
    files = sorted(src.glob("*.wav"))
    hg_audio = [librosa.load(str(f), sr=SR, mono=True)[0] for f in files]
    ids = [f.stem for f in files]

    G = np.array([timbre(y) for y in gm_audio])
    H = np.array([timbre(y) for y in hg_audio])
    mu, sd = np.vstack([G, H]).mean(0), np.vstack([G, H]).std(0) + 1e-9
    Gz, Hz = (G - mu) / sd, (H - mu) / sd
    methods = {}
    d = ((Hz[:, None, :] - Gz[None, :, :]) ** 2).sum(-1)
    methods["timbre_euclid"] = -d
    Gn = Gz / np.linalg.norm(Gz, axis=1, keepdims=True)
    Hn = Hz / np.linalg.norm(Hz, axis=1, keepdims=True)
    methods["timbre_cos"] = Hn @ Gn.T

    best = None
    for name, s in methods.items():
        exact = fam = top3 = 0
        for sid, gmp in KNOWN.items():
            if sid not in ids:
                continue
            row = s[ids.index(sid)]
            order = np.argsort(-row)
            exact += int(order[0]) == gmp
            fam += int(order[0]) // 8 == gmp // 8
            top3 += gmp in [int(j) for j in order[:3]] or gmp // 8 in [int(j) // 8 for j in order[:3]]
        print(f"{name:14s} exact {exact}/10, family {fam}/10, family in top 3 {top3}/10")
        if best is None or (fam, exact) > best[0]:
            best = ((fam, exact), name)
    s = methods[best[1]]
    meta = {x["id"]: x for x in json.loads((src / "sounds.json").read_text())}
    with open(dst, "w") as fh:
        fh.write(f"# id\tkind\tuse_seconds\tgm1\tscore1\tgm2\tscore2\tgm3\tscore3  ({best[1]} against MuseScore "
                 "General's 128 programs, same phrase, 2026-11-16)\n")
        for i, sid in enumerate(ids):
            order = np.argsort(-s[i])[:3]
            fh.write("\t".join([sid, str(meta.get(sid, {}).get("kind")), str(meta.get(sid, {}).get("use", 0))] +
                               [x for j in order for x in (str(int(j)), f"{s[i][j]:.3f}")]) + "\n")
    print("wrote", dst, "with", best[1])


if __name__ == "__main__":
    main()
