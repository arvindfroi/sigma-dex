"""A test song with real instruments and a known answer: a ROM song's true notes (hg_song_render.lua's JSON), each
channel given a General MIDI instrument, written as MIDI and rendered with the MuseScore General sound font (MIT,
fetched by MuScriptor from huggingface.co/MuScriptor/assets) by TinySoundFont.

    python gm_test_song.py truth.json OUTDIR [--until 58.3] [--programs 1=56,2=24,...]

OUTDIR gets gm.mid (the answer, programs included), gm.wav (what the chain hears) and gm_truth.json (notes with
their channel's program, for compare_notes.py and for checking instrument names).
"""
import argparse
import json
import pathlib
import struct

import numpy as np
import soundfile as sf

# Route 29's eight channels as instruments a song might have (ranges from its notes)
DEFAULT = {1: 56, 2: 24, 3: 48, 4: 33, 5: 0, 6: 9, 7: 71, 8: 73}


def vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.insert(0, 0x80 | (n & 0x7F))
        n >>= 7
    return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("truth")
    ap.add_argument("outdir")
    ap.add_argument("--until", type=float, default=58.3)
    ap.add_argument("--programs", default="")
    a = ap.parse_args()
    out = pathlib.Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    progs = dict(DEFAULT)
    for kv in filter(None, a.programs.split(",")):
        k, v = kv.split("=")
        progs[int(k)] = int(v)

    t = json.load(open(a.truth))
    notes = []  # (start, dur, pitch, midi channel, velocity)
    chans = sorted({n[0] for n in t["notes"] if n[5] == "note"})
    chan_of = {}
    for c in chans:
        mc = len(chan_of)
        if mc >= 9:
            mc += 1  # skip the drum channel
        chan_of[c] = mc
    for n in t["notes"]:
        if n[1] >= a.until:
            continue
        if n[5] == "note" and n[3] >= 0:
            notes.append((n[1], max(0.03, n[2]), n[3], chan_of[n[0]], 96))
        elif n[5].startswith("drum:"):
            key = int(n[5].split(":")[1]) if n[5].split(":")[1].isdigit() else 38
            notes.append((n[1], 0.1, key, 9, 100))

    # MIDI: 480 ticks a beat at 120 bpm = 960 ticks a second; one track per channel
    tracks = []
    for c, mc in sorted(chan_of.items(), key=lambda x: x[1]):
        evs = [(0, bytes([0xC0 | mc, progs.get(c, 0)]))]
        for s, d, p, ch, v in notes:
            if ch == mc:
                evs.append((round(s * 960), bytes([0x90 | ch, p, v])))
                evs.append((round((s + d) * 960), bytes([0x80 | ch, p, 0])))
        tracks.append(evs)
    tracks.append([(round(s * 960), bytes([0x99, p, v])) for s, d, p, ch, v in notes if ch == 9] +
                  [(round((s + d) * 960), bytes([0x89, p, 0])) for s, d, p, ch, v in notes if ch == 9])
    data = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks) + 1, 480)
    tempo = vlq(0) + b"\xff\x51\x03\x07\xa1\x20" + vlq(0) + b"\xff\x2f\x00"
    data += b"MTrk" + struct.pack(">I", len(tempo)) + tempo
    for evs in tracks:
        evs.sort(key=lambda e: (e[0], e[1][0] & 0xF0 != 0x80))
        body, last = b"", 0
        for tick, msg in evs:
            body += vlq(tick - last) + msg
            last = tick
        body += vlq(0) + b"\xff\x2f\x00"
        data += b"MTrk" + struct.pack(">I", len(body)) + body
    (out / "gm.mid").write_bytes(data)

    # render
    import tinysoundfont
    from muscriptor.soundfonts import SF2_URL
    from muscriptor.utils.download import download_if_necessary
    sf2 = str(download_if_necessary(SF2_URL))
    synth = tinysoundfont.Synth(samplerate=44100, gain=-3)
    sfid = synth.sfload(sf2)
    for c, mc in chan_of.items():
        synth.program_select(mc, sfid, 0, progs.get(c, 0))
    synth.program_select(9, sfid, 128, 0)
    events = []
    for s, d, p, ch, v in notes:
        events.append((s, 1, ch, p, v))
        events.append((s + d, 0, ch, p, 0))
    events.sort(key=lambda e: (e[0], e[1]))
    sr, pos, chunks = 44100, 0, []
    for when, on, ch, p, v in events:
        n = int(when * sr) - pos
        if n > 0:
            chunks.append(np.frombuffer(synth.generate(n), dtype=np.float32).reshape(-1, 2).copy())
            pos += n
        if on:
            synth.noteon(ch, p, v)
        else:
            synth.noteoff(ch, p)
    chunks.append(np.frombuffer(synth.generate(sr * 2), dtype=np.float32).reshape(-1, 2).copy())
    audio = np.concatenate(chunks)
    audio = audio / max(1e-6, float(np.abs(audio).max())) * 0.9
    sf.write(str(out / "gm.wav"), audio, sr)

    truth = {"notes": [[mc, s, d, p, progs.get(next(k for k, v in chan_of.items() if v == mc), 0) if mc != 9 else -1,
                        "note" if mc != 9 else f"drum:{p}"] for s, d, p, mc, v in notes],
             "loops": [[0, 0, a.until]], "programs": {str(chan_of[c]): progs.get(c, 0) for c in chan_of}}
    (out / "gm_truth.json").write_text(json.dumps(truth))
    print("wrote", out / "gm.mid", out / "gm.wav", len(notes), "notes", round(len(audio) / sr, 1), "s")


if __name__ == "__main__":
    main()
