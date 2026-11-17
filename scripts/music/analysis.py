"""A song's tempo, bars, key, chords and sections, from chain.py's stems (runs on the Legion).

    python analysis.py OUTDIR

OUTDIR is chain.py's (mix.wav, sep_vocals/, sep_sw/). Writes OUTDIR/analysis.json:
  bpm, beats, downbeats (seconds; beat_this, the same tracker MuScriptor uses)
  key ("A minor"), from the harmony's chroma (Krumhansl profiles)
  bars: [{start, end, chord}] - the chord each bar mostly holds: major, minor, 7th, minor 7th or none, found by
        matching each beat's chroma (bass, guitar, piano and other stems: no voice, no drums) to chord templates and
        smoothing with a Viterbi pass that prefers staying on a chord
  sections: [{start_bar, end_bar, label, energy}] - where the music changes (a novelty curve over the bars'
        self-similarity, boundaries on 4-bar steps where they fit), sections that sound alike share a letter
"""
import json
import pathlib
import sys

import librosa
import numpy as np
import soundfile as sf

NOTES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
QUALITIES = {"": [0, 4, 7], "m": [0, 3, 7], "7": [0, 4, 7, 10], "m7": [0, 3, 7, 10]}
MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]


def load(paths, sr=22050):
    total = None
    for p in paths:
        y, _ = librosa.load(str(p), sr=sr, mono=True)
        total = y if total is None else total[: len(y)] + y[: len(total)]
    return total


def beats_of(mix):
    from beat_this.inference import Audio2Beats
    x, sr = sf.read(str(mix), dtype="float32", always_2d=True)
    beats, downbeats = Audio2Beats("final0", device="cuda")(x.mean(axis=1), sr)
    return np.asarray(beats, float), np.asarray(downbeats, float)


def chord_templates():
    names, temps = ["N"], [np.ones(12) / np.sqrt(12)]
    for q, ivs in QUALITIES.items():
        for root in range(12):
            t = np.zeros(12)
            for i in ivs:
                t[(root + i) % 12] = 1.0
            t[root] += 0.5  # the root a little more
            names.append(NOTES[root] + q)
            temps.append(t / np.linalg.norm(t))
    return names, np.array(temps)


def chord_from_notes(notes, s, e, seventh_penalty=0.05):
    """the chord template closest to what sounds in [s, e): each pitch class by how long it sounds, the bass's root
    a little more (a 7th chord only where it clearly fits better)"""
    ch, low = np.zeros(12), np.zeros(12)
    for a0, b0, p in notes:
        a, b = max(s, a0), min(e, b0)
        if b > a:
            ch[p % 12] += b - a
            if p < 55:
                low[p % 12] += b - a
    if ch.sum() == 0:
        return "N"
    ch /= np.linalg.norm(ch)
    lowsum = low.sum() or 1.0
    best = (-9, "N")
    for q, ivs in QUALITIES.items():
        for r in range(12):
            t = np.zeros(12)
            t[[(r + i) % 12 for i in ivs]] = 1
            c = float(ch @ t / np.linalg.norm(t)) + 0.15 * low[r] / lowsum - (seventh_penalty if "7" in q else 0)
            if c > best[0]:
                best = (c, NOTES[r] + q)
    return best[1]


def viterbi(scores, stay=0.92):
    n, k = scores.shape
    logp = np.log(np.clip(scores, 1e-6, None))
    trans = np.full((k, k), np.log((1 - stay) / (k - 1)))
    np.fill_diagonal(trans, np.log(stay))
    dp, back = logp[0].copy(), np.zeros((n, k), int)
    for i in range(1, n):
        cand = dp[:, None] + trans
        back[i] = cand.argmax(0)
        dp = cand.max(0) + logp[i]
    path = [int(dp.argmax())]
    for i in range(n - 1, 0, -1):
        path.append(int(back[i][path[-1]]))
    return path[::-1]


def main():
    out = pathlib.Path(sys.argv[1])
    mix = out / "mix.wav"
    sw = {k: pathlib.Path(v) for k, v in json.loads((out / "sep_sw" / "done.json").read_text()).items()}
    harm = [sw[k] for k in ("bass", "guitar", "piano", "other") if k in sw]
    sr, hop = 22050, 512
    beats, downbeats = beats_of(mix)
    ibi = np.diff(beats)
    bpm = float(60 / np.median(ibi)) if len(ibi) else 0.0

    y = load(harm, sr)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
    frames = librosa.time_to_frames(beats, sr=sr, hop_length=hop)
    bsync = librosa.util.sync(chroma, frames, aggregate=np.median)  # 12 x (beats + 1)
    bsync = bsync / (np.linalg.norm(bsync, axis=0, keepdims=True) + 1e-9)

    # key
    prof = chroma.sum(axis=1)
    best = (-2, "")
    for r in range(12):
        for name, p in (("major", MAJOR), ("minor", MINOR)):
            c = np.corrcoef(prof, np.roll(p, r))[0, 1]
            if c > best[0]:
                best = (c, f"{NOTES[r]} {name}")
    key = best[1]

    # chords per beat, then per bar
    names, temps = chord_templates()
    sim = temps @ bsync  # chords x beats
    # "no chord" only where the harmony is quiet (chroma is normalised per frame, so loudness comes from the audio)
    level = librosa.util.sync(librosa.feature.rms(y=y, hop_length=hop), frames, aggregate=np.mean)[0]
    quiet = level < 0.1 * np.percentile(level, 90)
    sim[0] = np.where(quiet, 1.0, 0.0)
    probs = np.exp(sim * 12)
    probs /= probs.sum(0, keepdims=True)
    path = viterbi(probs.T)
    beat_chord = [names[i] for i in path]
    bars = []
    starts = list(downbeats) if len(downbeats) > 1 else list(beats[::4])
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else (beats[-1] if len(beats) else s)
        idx = [j for j, b in enumerate(beats) if s - 0.05 <= b < e - 0.05]
        votes = {}
        for j in idx:
            c = beat_chord[min(j + 1, len(beat_chord) - 1)]  # sync column 0 is before the first beat
            votes[c] = votes.get(c, 0) + 1
        chord = max(votes, key=votes.get) if votes else "N"
        bars.append({"start": round(float(s), 3), "end": round(float(e), 3), "chord": chord})

    # better: the chord from the transcribed notes (the mix's and the bass stem's), where chain.py kept them; on the
    # General MIDI test song this found the right root in 76 % of bars (74 % with major/minor), the chroma 47 %
    nd = out / "notes"
    srcs = [p for p in [nd / "mix_large_b1_c1.5.json", nd / "bass_large_b1_c1.5.json"] if p.exists()]
    if srcs:
        ns = [(s, e, p) for f in srcs for s, e, p, i in json.loads(f.read_text()) if i not in ("drums", "voice")]
        voc = nd / "vocals_large_b1_c1.5.json"
        if sum(e - s for s, e, p in ns) < 0.2 * (beats[-1] - beats[0] if len(beats) > 1 else 1) and voc.exists():
            # hardly any instruments (a cappella): the voices are the harmony
            ns += [(s, e, p) for s, e, p, i in json.loads(voc.read_text())]
        for b in bars:
            b["chord_audio"] = b["chord"]
            b["chord"] = chord_from_notes(ns, b["start"], b["end"])
        res_from = "notes"
    else:
        res_from = "audio"

    # sections: bar features (harmony chroma + the mix's timbre), self-similarity, novelty
    ym, _ = librosa.load(str(mix), sr=sr, mono=True)
    mfcc = librosa.feature.mfcc(y=ym, sr=sr, hop_length=hop, n_mfcc=13)
    rmsf = librosa.feature.rms(y=ym, hop_length=hop)[0]
    bframes = librosa.time_to_frames([b["start"] for b in bars] + [bars[-1]["end"]], sr=sr, hop_length=hop)
    feat_c = librosa.util.sync(chroma, bframes, aggregate=np.mean)[:, 1:-1]
    feat_m = librosa.util.sync(mfcc, bframes, aggregate=np.mean)[:, 1:-1]
    bar_rms = librosa.util.sync(rmsf[None, :], bframes, aggregate=np.mean)[0, 1:-1]
    n = min(len(bars), feat_c.shape[1])
    f = np.vstack([feat_c[:, :n] / (np.linalg.norm(feat_c[:, :n], axis=0) + 1e-9),
                   (feat_m[:, :n] - feat_m[:, :n].mean(1, keepdims=True)) / (feat_m[:, :n].std(1, keepdims=True) + 1e-9) * 0.3])
    f = f / (np.linalg.norm(f, axis=0) + 1e-9)
    ssm = f.T @ f
    k = 4
    kern = np.kron(np.array([[1, -1], [-1, 1]]), np.ones((k, k)))
    nov = np.zeros(n)
    for i in range(k, n - k):
        nov[i] = (ssm[i - k:i + k, i - k:i + k] * kern).sum()
    peaks = [i for i in range(k, n - k) if nov[i] == nov[max(0, i - 3):i + 4].max() and nov[i] > np.percentile(nov, 70)]
    bounds = sorted(set([0] + [p for p in peaks] + [n]))
    merged = [bounds[0]]
    for b in bounds[1:]:
        if b - merged[-1] >= 4 or b == n:
            merged.append(b)
        if b == n and merged[-1] != n:
            merged.append(n)
    sections, sigs = [], []
    letters = "ABCDEFGHIJKLMNOP"
    for a, b in zip(merged[:-1], merged[1:]):
        if b <= a:
            continue
        sig = f[:, a:b].mean(1)
        sig /= np.linalg.norm(sig) + 1e-9
        label = None
        for lab, s in sigs:
            if float(sig @ s) > 0.92:
                label = lab
                break
        if label is None:
            label = letters[len(sigs)] if len(sigs) < len(letters) else "Z"
            sigs.append((label, sig))
        sections.append({"start_bar": int(a), "end_bar": int(b), "label": label,
                         "start": bars[a]["start"], "energy": round(float(bar_rms[a:b].mean()), 4)})
    res = {"bpm": round(bpm, 1), "key": key, "chords_from": res_from, "beats": [round(float(b), 3) for b in beats],
           "downbeats": [round(float(b), 3) for b in downbeats], "bars": bars, "sections": sections}
    (out / "analysis.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({"bpm": res["bpm"], "key": key, "bars": len(bars),
                      "sections": " ".join(f"{s['label']}{s['end_bar'] - s['start_bar']}" for s in sections),
                      "chords": " ".join(b["chord"] for b in bars[:16])}))


if __name__ == "__main__":
    main()
