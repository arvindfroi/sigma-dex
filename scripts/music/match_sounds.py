"""Names each HeartGold sound by the General MIDI instrument it SOUNDS most like: every GM program of the MuseScore
General sound font plays the same phrase the HeartGold sounds played (hg_sounds_render.lua), and an audio model
(LAION CLAP, audio against audio) finds each HeartGold sound's nearest GM programs.

    python match_sounds.py SOUNDS_DIR OUT.tsv

Checked against the instruments the DS hacking guide names in HeartGold's basic bank (700): strings 23, Rhodes 3,
slap bass 21, vibraphone 5, marimba 6, tubular bell 8, flute 35, pizzicato 26, harp 27, clarinet 34.
"""
import json
import pathlib
import sys

import librosa
import numpy as np
import torch
from transformers import ClapModel, ClapProcessor

KNOWN = {"b700.23": 48, "b700.3": 4, "b700.21": 36, "b700.5": 11, "b700.6": 12, "b700.8": 14, "b700.35": 73,
         "b700.26": 45, "b700.27": 46, "b700.34": 71}


def phrase_gm(synth, prog, sr=44100):
    """the phrase hg_sounds_render.lua plays: C4 E4 G4 C5 a beat each, then C3 and C5 two beats each, 120 bpm"""
    import tinysoundfont  # noqa: F401
    beat = 0.5
    seq = [(60, 1), (64, 1), (67, 1), (72, 1), (48, 2), (72, 2)]
    out = []
    for p, b in seq:
        synth.noteon(0, p, 100)
        out.append(np.frombuffer(synth.generate(int(b * beat * sr)), dtype=np.float32).reshape(-1, 2).copy())
        synth.noteoff(0, p)
    out.append(np.frombuffer(synth.generate(int(1.0 * sr)), dtype=np.float32).reshape(-1, 2).copy())
    a = np.concatenate(out).mean(axis=1)
    return a / (np.abs(a).max() + 1e-9)


def main():
    src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    import tinysoundfont
    from muscriptor.soundfonts import SF2_URL
    from muscriptor.utils.download import download_if_necessary

    synth = tinysoundfont.Synth(samplerate=44100)
    sfid = synth.sfload(str(download_if_necessary(SF2_URL)))
    gm = []
    for prog in range(128):
        synth.program_select(0, sfid, 0, prog)
        gm.append(librosa.resample(phrase_gm(synth, prog), orig_sr=44100, target_sr=48000))
        synth.notes_off()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = ClapModel.from_pretrained("laion/clap-htsat-unfused").to(dev).eval()
    proc = ClapProcessor.from_pretrained("laion/clap-htsat-unfused")

    def embed(audios):
        outs = []
        for i in range(0, len(audios), 16):
            with torch.no_grad():
                x = proc(audio=audios[i:i + 16], sampling_rate=48000, return_tensors="pt").to(dev)
                e = model.get_audio_features(**x)
                e = e if torch.is_tensor(e) else e.pooler_output
                outs.append(torch.nn.functional.normalize(e, dim=-1).cpu())
        return torch.cat(outs)

    g = embed(gm)
    files = sorted(src.glob("*.wav"))
    h = embed([librosa.load(str(f), sr=48000, mono=True)[0] for f in files])
    sim = (h @ g.T).numpy()
    meta = {s["id"]: s for s in json.loads((src / "sounds.json").read_text())}
    rows, hits, fam = [], 0, 0
    for f, row in zip(files, sim):
        order = np.argsort(-row)[:3]
        sid = f.stem
        rows.append([sid, str(meta.get(sid, {}).get("kind")), str(meta.get(sid, {}).get("use", 0))] +
                    [x for j in order for x in (str(int(j)), f"{row[j]:.3f}")])
        if sid in KNOWN:
            ok = int(order[0]) == KNOWN[sid] or int(order[0]) // 8 == KNOWN[sid] // 8
            print(sid, "guide GM", KNOWN[sid], "found", [int(j) for j in order], "family right" if int(order[0]) // 8 == KNOWN[sid] // 8 else "")
            hits += int(order[0]) == KNOWN[sid]
            fam += int(order[0]) // 8 == KNOWN[sid] // 8
    with open(dst, "w") as fh:
        fh.write("# id\tkind\tuse_seconds\tgm1\tsim1\tgm2\tsim2\tgm3\tsim3  (CLAP audio-to-audio against MuseScore "
                 "General's 128 programs playing the same phrase, 2026-11-16)\n")
        for r in sorted(rows):
            fh.write("\t".join(r) + "\n")
    print(f"guide's {len(KNOWN)} known sounds: exact program {hits}, right family {fam}")


if __name__ == "__main__":
    main()
