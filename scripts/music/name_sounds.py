"""Gives each HeartGold sound an instrument name, so a transcribed trumpet can go to the game's trumpet.

    python name_sounds.py SOUNDS_DIR OUT.json

SOUNDS_DIR: hg_sounds_render.lua's output (one WAV per sound + sounds.json). Each sound is heard by LAION-CLAP
(laion/clap-htsat-unfused, Apache-2.0; larger_clap_music gave every text the same embedding here) and compared with a sentence per instrument; the instrument names are
MuScriptor's groups, so the transcription's labels and the game's sounds speak the same words. Writes, per sound, its
best three names with scores. A first guess: Claude and Arvind correct it by ear (instrument_names.json).
"""
import json
import pathlib
import sys

import librosa
import numpy as np
import torch
from transformers import ClapModel, ClapProcessor

NAMES = {
    "acoustic_piano": "a piano",
    "electric_piano": "an electric piano",
    "chromatic_percussion": "a glockenspiel, music box, marimba or vibraphone",
    "organ": "an organ",
    "acoustic_guitar": "an acoustic guitar",
    "clean_electric_guitar": "a clean electric guitar",
    "distorted_electric_guitar": "a distorted electric guitar",
    "acoustic_bass": "an acoustic bass",
    "electric_bass": "an electric bass guitar",
    "violin": "a violin",
    "viola": "a viola",
    "cello": "a cello",
    "contrabass": "a double bass",
    "orchestral_harp": "a harp",
    "timpani": "timpani drums",
    "string_ensemble": "a string section",
    "synth_strings": "synth strings",
    "voice": "a choir singing aah",
    "orchestra_hit": "an orchestra hit",
    "trumpet": "a trumpet",
    "trombone": "a trombone",
    "tuba": "a tuba",
    "french_horn": "a french horn",
    "brass_section": "a brass section",
    "soprano_and_alto_sax": "an alto saxophone",
    "tenor_sax": "a tenor saxophone",
    "baritone_sax": "a baritone saxophone",
    "oboe": "an oboe",
    "english_horn": "an english horn",
    "bassoon": "a bassoon",
    "clarinet": "a clarinet",
    "flutes": "a flute",
    "synth_lead": "a synth lead, square wave",
    "synth_pad": "a soft synth pad",
}


def emb(x):
    # transformers 5 returns an output object here; its pooled output is the projected embedding
    if not torch.is_tensor(x):
        x = getattr(x, "text_embeds", None) if getattr(x, "text_embeds", None) is not None else x.pooler_output
    return torch.nn.functional.normalize(x, dim=-1)


def main():
    src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    meta = {s["id"]: s for s in json.loads((src / "sounds.json").read_text())}
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = ClapModel.from_pretrained("laion/clap-htsat-unfused").to(dev).eval()
    proc = ClapProcessor.from_pretrained("laion/clap-htsat-unfused")
    keys = list(NAMES)
    texts = [f"the sound of {NAMES[k]} playing notes" for k in keys]
    out = []
    files = sorted(src.glob("*.wav"))
    spread = []
    for i in range(0, len(files), 16):
        batch = files[i:i + 16]
        audio = [librosa.load(str(f), sr=48000, mono=True)[0] for f in batch]
        with torch.no_grad():
            inputs = proc(text=texts, audio=audio, sampling_rate=48000, return_tensors="pt", padding=True).to(dev)
            o = model(**inputs)
            sims = o.logits_per_audio.float().cpu().numpy()  # [audio, text]
        for f, row in zip(batch, sims):
            order = np.argsort(-row)[:3]
            spread.append(float(row.max() - row.min()))
            sid = f.stem
            out.append({"id": sid, "kind": meta.get(sid, {}).get("kind"), "use": meta.get(sid, {}).get("use"),
                        "names": [[keys[j], round(float(row[j]), 3)] for j in order]})
    print("score spread per sound (max-min): median", round(float(np.median(spread)), 3))
    dst.write_text(json.dumps(out, indent=1))
    counts = {}
    for o in out:
        counts[o["names"][0][0]] = counts.get(o["names"][0][0], 0) + 1
    print(len(out), "sounds named;", json.dumps(dict(sorted(counts.items(), key=lambda x: -x[1]))))


if __name__ == "__main__":
    main()
