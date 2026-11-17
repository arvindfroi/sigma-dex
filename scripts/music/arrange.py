"""A clean game arrangement of a song from what chain.py and analysis.py found: the tune, the bass, the chords and the
drums, each on the beat grid, instead of every note the transcription heard (its wrong notes are what sound wrong).

    python3 arrange.py OUTDIR out.mid [--melody vocals|lead|none] [--melody-program 56] [--chords pad|arp|both|none]
                       [--parts] [--cfg 1.5]

OUTDIR: chain.py's (notes/*.json kept per stem, analysis.json). No third-party modules.
- time: every note's start and end become beats through the tracked beats (so a live, drifting tempo comes out
  straight at the song's median BPM), snapped to sixteenths
- melody: the vocal stem's notes (or, with --melody lead, the highest line of the mix's own lead instruments), one
  note at a time, as --melody-program (General MIDI; 56 trumpet)
- bass: the bass stem's notes, one at a time, the lowest
- chords: each bar's chord from analysis.json, voiced near middle C moving as little as it can: a held pad (strings)
  and/or an arpeggio in eighths (harp)
- drums: MuScriptor's drum-stem hits on their General MIDI keys
- --parts: the mix's other transcribed parts too
- dynamics: each section's loudness against the loudest sets its velocities
"""
import argparse
import bisect
import json
import pathlib
import struct

NOTES = {"C": 0, "C#": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11}
QUALITY = {"": [0, 4, 7], "m": [0, 3, 7], "7": [0, 4, 7, 10], "m7": [0, 3, 7, 10]}
PPQ = 96
PROGRAM_OF = {"acoustic_piano": 0, "electric_piano": 4, "chromatic_percussion": 11, "organ": 19, "acoustic_guitar": 24,
              "clean_electric_guitar": 27, "distorted_electric_guitar": 30, "acoustic_bass": 32, "electric_bass": 33,
              "violin": 40, "viola": 41, "cello": 42, "contrabass": 43, "orchestral_harp": 46, "timpani": 47,
              "string_ensemble": 48, "synth_strings": 50, "voice": 52, "orchestra_hit": 55, "trumpet": 56,
              "trombone": 57, "tuba": 58, "french_horn": 60, "brass_section": 61, "soprano_and_alto_sax": 65,
              "tenor_sax": 66, "baritone_sax": 67, "oboe": 68, "english_horn": 69, "bassoon": 70, "clarinet": 71,
              "flutes": 73, "synth_lead": 80, "synth_pad": 89}
LEAD_GROUPS = {"trumpet", "flutes", "synth_lead", "clarinet", "oboe", "soprano_and_alto_sax", "tenor_sax", "violin",
               "french_horn", "trombone", "english_horn", "voice", "distorted_electric_guitar", "clean_electric_guitar"}


def vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.insert(0, 0x80 | (n & 0x7F))
        n >>= 7
    return bytes(out)


class Grid:
    """seconds <-> beats through the tracked beats"""

    def __init__(self, beats):
        self.b = beats

    def beat(self, t):
        b = self.b
        if t <= b[0]:
            return (t - b[0]) / (b[1] - b[0])
        if t >= b[-1]:
            return len(b) - 1 + (t - b[-1]) / (b[-1] - b[-2])
        i = bisect.bisect_right(b, t) - 1
        return i + (t - b[i]) / (b[i + 1] - b[i])


def mono(notes, keep="high"):
    """one note at a time: where notes overlap the higher (or lower) wins, the other is cut"""
    notes = sorted(notes, key=lambda n: (n[0], -n[2] if keep == "high" else n[2]))
    out = []
    for s, e, p in notes:
        if out and s < out[-1][1]:
            ps, pe, pp = out[-1]
            if s - ps < 0.25:  # a chord on one onset: keep one
                if (p > pp) == (keep == "high"):
                    out[-1] = (ps, max(pe, e), p)
                continue
            out[-1] = (ps, s, pp)
        out.append((s, e, p))
    return [n for n in out if n[1] - n[0] >= 0.12]


def voice(chord, prev):
    root = NOTES.get(chord.rstrip("m7").rstrip("m"), None)
    q = chord[len(chord.rstrip("m7").rstrip("m")):] if root is not None else ""
    if root is None:
        return None
    pcs = [(root + i) % 12 for i in QUALITY.get(q, QUALITY[""])]
    best = None
    for low in range(52, 64):  # E3..Eb4: the lowest note of the voicing
        v = sorted(min((p for p in range(low, low + 12) if p % 12 == pc)) for pc in pcs)
        cost = sum(abs(a - b) for a, b in zip(v, prev)) if prev else abs(v[0] - 57)
        if best is None or cost < best[0]:
            best = (cost, v)
    return best[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("midi")
    ap.add_argument("--melody", choices=["vocals", "lead", "none"], default="vocals")
    ap.add_argument("--melody-program", type=int, default=56)
    ap.add_argument("--chords", choices=["pad", "arp", "both", "none"], default="both")
    ap.add_argument("--parts", action="store_true")
    ap.add_argument("--style", choices=["arrangement", "full"], default="arrangement",
                    help="full: every part the mix's transcription has (up to 8), the bass, the drums, no made chords")
    ap.add_argument("--vocals", choices=["on", "off"], default="on", help="the sung melody as the lead, or left out")
    ap.add_argument("--cymbals", choices=["off", "on"], default="off",
                    help="hi-hats and cymbals: transcription finds them worst (everyone's tools do), so left out")
    ap.add_argument("--loop", choices=["auto", "none"], default="auto",
                    help="auto: the intro, then each new section once until one comes back, looping after the intro")
    ap.add_argument("--cfg", default="1.5")
    a = ap.parse_args()
    d = pathlib.Path(a.outdir)
    an = json.loads((d / "analysis.json").read_text())
    grid = Grid(an["beats"])

    def notes(stem):
        p = d / "notes" / f"{stem}_large_b1_c{a.cfg}.json"
        return json.loads(p.read_text()) if p.exists() else []

    def tick(t):
        return max(0, round(grid.beat(t) * 4) * PPQ // 4)  # sixteenths

    # section loudness -> velocity scale
    secs = an["sections"]
    top = max((s["energy"] for s in secs), default=1) or 1

    def dyn(t):
        i = bisect.bisect_right([s["start"] for s in secs], t) - 1
        e = secs[i]["energy"] if i >= 0 else top
        return 0.65 + 0.35 * (e / top) ** 0.5

    tracks = []  # (name, channel, program, [(start_tick, end_tick, pitch, velocity)])

    def add(name, ch, prog, ns, vel):
        evs = []
        for s, e, p in ns:
            ts, te = tick(s), tick(e)
            if te <= ts:
                te = ts + PPQ // 4
            evs.append((ts, te, int(p), int(min(127, vel * dyn(s)))))
        if evs:
            tracks.append((name, ch, prog, evs))

    mix = notes("mix")
    if a.vocals == "off" and a.melody == "vocals":
        a.melody = "lead" if a.style == "arrangement" else "none"
    if a.style == "full" and a.melody == "lead":
        a.melody = "none"  # the mix's own lead parts are in already
    if a.melody == "vocals":
        mel = [(s, e, p) for s, e, p, _ in notes("vocals")]
        if not mel:
            a.melody = "lead"
    if a.melody == "lead":
        mel = [(s, e, p) for s, e, p, i in mix if i in LEAD_GROUPS and p >= 60]
    if a.melody != "none":
        add("melody", 0, a.melody_program, mono(mel, "high"), 104)
    bass = [(s, e, p) for s, e, p, _ in notes("bass")]
    if not bass:  # no bass stem (a cappella): the lowest voice is the bass
        bass = [(s, e, p) for s, e, p, _ in notes("vocals") if p < 52]
    add("bass", 1, 33, mono(bass, "low"), 108)

    # chords
    bars = an["bars"]
    prev = None
    pad, arp = [], []
    for b in bars:
        v = voice(b["chord"], prev) if b["chord"] != "N" else None
        if not v:
            continue
        prev = v
        for p in v:
            pad.append((b["start"], b["end"] - 0.02, p))
        beats = [x for x in an["beats"] if b["start"] - 0.05 <= x < b["end"] - 0.05]
        seq = v + [v[0] + 12]
        k = 0
        for j, bt in enumerate(beats):
            nxt = beats[j + 1] if j + 1 < len(beats) else b["end"]
            for half in (bt, (bt + nxt) / 2):
                arp.append((half, half + (nxt - bt) / 2, seq[k % len(seq)] + 12))
                k += 1
    if a.style == "full":
        a.chords = "none"
        groups = {}
        for s_, e_, p_, i in mix:
            if i not in ("drums", "voice") and "bass" not in i:
                groups.setdefault(i, []).append((s_, e_, p_))
        ch = 2
        for i, ns in sorted(groups.items(), key=lambda x: -len(x[1]))[:8]:
            if ch == 9:
                ch = 10
            add(i, ch, PROGRAM_OF.get(i, 0), ns, 90)
            ch += 1
    if a.chords in ("pad", "both"):
        add("chords pad", 2, 48, pad, 64)
    if a.chords in ("arp", "both"):
        add("chords arp", 3, 46, arp, 72)

    drums = notes("drums")
    # kicks, snares, claps and toms from MuScriptor's drum-stem notes; hi-hats and cymbals only with --cymbals on,
    # and then from DrumSep's own hi-hat, ride and crash stems (drums_extra.py), never the transcription's guesses
    drums = [n for n in drums if int(n[2]) in (35, 36, 37, 38, 39, 40, 41, 43, 45, 47, 48, 50)]
    extra = d / "drums_extra.json"
    if a.cymbals == "on" and extra.exists():
        drums += [(t, t + 0.1, k, "drums") for t, k, _ in json.loads(extra.read_text())]
    if drums:
        add("drums", 9, 0, [(s, s + 0.1, p) for s, e, p, _ in drums], 100)
    if a.parts:
        others = {}
        for s, e, p, i in mix:
            if i not in LEAD_GROUPS and i not in ("drums", "voice") and "bass" not in i:
                others.setdefault(i, []).append((s, e, p))
        for k_, (i, ns) in enumerate(sorted(others.items(), key=lambda x: -len(x[1]))[:3]):
            add(i, 4 + k_, 0, ns, 80)

    # a game song goes round: keep the intro and each new section once, up to the first that comes back
    loop_tick = end_tick = None
    if a.loop == "auto" and len(secs) > 2:
        seen, keep = set(), []
        for i, sec in enumerate(secs):
            kept = sum(x["end_bar"] - x["start_bar"] for x in keep)
            if i > 0 and ((sec["label"] in seen and kept >= 16) or kept >= 32):
                break  # a section comes back, or it is already as long as a game song (32 bars)
            seen.add(sec["label"])
            keep.append(sec)
        if len(keep) < len(secs):
            first = keep[1] if len(keep) > 1 and keep[0]["end_bar"] - keep[0]["start_bar"] <= 8 else keep[0]
            loop_tick = tick(bars[first["start_bar"]]["start"])
            end_tick = tick(bars[min(keep[-1]["end_bar"], len(bars)) - 1]["end"])
            cut = []
            for name, ch, prog, evs in tracks:
                evs = [(ts, min(te, end_tick), p, v) for ts, te, p, v in evs if ts < end_tick]
                if evs:
                    cut.append((name, ch, prog, evs))
            tracks[:] = cut

    # MIDI: the song's median tempo, steady
    bpm = an["bpm"] or 120
    data = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks) + 1, PPQ)
    us = int(60e6 / bpm)
    meta = vlq(0) + b"\xff\x51\x03" + us.to_bytes(3, "big")
    if loop_tick is not None:
        meta += vlq(loop_tick) + b"\xff\x06\x09loopStart" + vlq(end_tick - loop_tick) + b"\xff\x06\x07loopEnd"
    meta += vlq(0) + b"\xff\x2f\x00"
    data += b"MTrk" + struct.pack(">I", len(meta)) + meta
    for name, ch, prog, evs in tracks:
        msgs = [(0, 0, b"\xff\x03" + vlq(len(name)) + name.encode())]
        if ch != 9:
            msgs.append((0, 1, bytes([0xC0 | ch, prog])))
        for ts, te, p, v in evs:
            msgs.append((ts, 3, bytes([0x90 | ch, p, max(1, v)])))
            msgs.append((te, 2, bytes([0x80 | ch, p, 0])))
        msgs.sort(key=lambda m: (m[0], m[1]))
        body, last = b"", 0
        for t, _, m in msgs:
            body += vlq(t - last) + m
            last = t
        body += vlq(0) + b"\xff\x2f\x00"
        data += b"MTrk" + struct.pack(">I", len(body)) + body
    pathlib.Path(a.midi).write_bytes(data)
    print(json.dumps({"bpm": bpm, "key": an["key"], "tracks": {t[0]: len(t[3]) for t in tracks},
                      "loop": None if loop_tick is None else [round(loop_tick / PPQ, 1), round(end_tick / PPQ, 1)],
                      "sections": " ".join(f"{s['label']}" for s in secs)}))


if __name__ == "__main__":
    main()
