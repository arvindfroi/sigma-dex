"""How close a transcription (MIDI) is to a song's real notes, in seconds.

    python compare_notes.py truth.json song.mid [--until 58.3] [--tol 0.05] [--json]

truth.json: hg_song_render.lua's or gm_test_song.py's notes [channel, start, dur, pitch, program, "note"|"drum:KEY"].
A note counts as found when a transcribed note has the same pitch (or pitch class) and starts within `tol` seconds,
after the whole song is shifted by the best offset (a MIDI's first bar line moves everything a little; the game
doesn't care). Drums are scored apart, by kind (kick, snare, tom, hi-hat, cymbal). Where the truth knows each
channel's General MIDI program, also the share of found notes whose instrument group is the right one (MuScriptor's
groups) and of those in the right family (keys, guitar, bass, strings, brass, reed, pipe, synth, ...).
No third-party modules.
"""
import argparse
import json
import struct

GROUPS = [("acoustic_piano", [0, 1, 3, 6, 7]), ("electric_piano", [2, 4, 5]), ("chromatic_percussion", range(8, 16)),
          ("organ", range(16, 24)), ("acoustic_guitar", [24, 25]), ("clean_electric_guitar", [26, 27, 28]),
          ("distorted_electric_guitar", [29, 30, 31]), ("acoustic_bass", [32, 35]),
          ("electric_bass", [33, 34, 36, 37, 38, 39]), ("violin", [40]), ("viola", [41]), ("cello", [42]),
          ("contrabass", [43]), ("orchestral_harp", [46]), ("timpani", [47]), ("string_ensemble", [44, 45, 48, 49]),
          ("synth_strings", [50, 51]), ("voice", [52, 53, 54]), ("orchestra_hit", [55]), ("trumpet", [56, 59]),
          ("trombone", [57]), ("tuba", [58]), ("french_horn", [60]), ("brass_section", [61, 62, 63]),
          ("sax", range(64, 68)), ("oboe", [68]), ("english_horn", [69]), ("bassoon", [70]), ("clarinet", [71]),
          ("flutes", range(72, 80)), ("synth_lead", range(80, 88)), ("synth_pad", range(88, 96))]
GROUP = {p: g for g, ps in GROUPS for p in ps}


def family(p):
    return None if p is None or p < 0 else p // 8


def drum_kind(k):
    if k in (35, 36):
        return "kick"
    if k in (37, 38, 39, 40):
        return "snare"
    if k in (41, 43, 45, 47, 48, 50):
        return "tom"
    if k in (42, 44, 46):
        return "hat"
    return "cymbal"


def vlq(data, p):
    v = 0
    while True:
        c = data[p]
        p += 1
        v = (v << 7) | (c & 0x7F)
        if not c & 0x80:
            return v, p


def read_midi(path):
    """[(start s, dur s, pitch, channel, program)], [(s, bpm)]"""
    data = open(path, "rb").read()
    assert data[:4] == b"MThd"
    fmt, ntracks, division = struct.unpack(">HHH", data[8:14])
    pos, events, tempos = 14, [], [(0, 500000)]
    for tr in range(ntracks):
        length = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        p, end = pos + 8, pos + 8 + length
        tick, status = 0, 0
        while p < end:
            d, p = vlq(data, p)
            tick += d
            c = data[p]
            if c & 0x80:
                status = c
                p += 1
            if status == 0xFF:
                typ = data[p]
                ln, p = vlq(data, p + 1)
                if typ == 0x51:
                    tempos.append((tick, int.from_bytes(data[p:p + 3], "big")))
                p += ln
            elif status in (0xF0, 0xF7):
                ln, p = vlq(data, p)
                p += ln
            else:
                hi, ch = status & 0xF0, status & 0x0F
                if hi in (0xC0, 0xD0):
                    a, b = data[p], 0
                    p += 1
                else:
                    a, b = data[p], data[p + 1]
                    p += 2
                events.append((tick, hi, a, b, ch, tr))
        pos = end
    tempos.sort()

    def seconds(t):
        s, last, us = 0.0, 0, 500000
        for tk, tempo in tempos:
            if tk >= t:
                break
            s += (tk - last) * us / division / 1e6
            last, us = tk, tempo
        return s + (t - last) * us / division / 1e6

    notes, open_, prog = [], {}, {}
    for tick, hi, a, b, ch, tr in sorted(events, key=lambda e: e[0]):
        if hi == 0xC0:
            prog[(tr, ch)] = a
        elif hi == 0x90 and b > 0:
            open_[(ch, a, tr)] = tick
        elif hi == 0x80 or (hi == 0x90 and b == 0):
            t0 = open_.pop((ch, a, tr), None)
            if t0 is not None:
                notes.append((seconds(t0), seconds(tick) - seconds(t0), a, ch, prog.get((tr, ch), -1)))
    return notes, [(seconds(t), 60e6 / us) for t, us in tempos]


def match(truth, got, tol, same):
    """pairs (truth index, got index) found greedily in time order"""
    order = sorted(range(len(got)), key=lambda i: got[i][0])
    starts = [got[i][0] for i in order]
    import bisect
    used, pairs = set(), []
    for ti, t in enumerate(truth):
        k = bisect.bisect_left(starts, t[0] - tol)
        while k < len(order) and starts[k] <= t[0] + tol:
            gi = order[k]
            if gi not in used and same(t, got[gi]):
                used.add(gi)
                pairs.append((ti, gi))
                break
            k += 1
    return pairs


def prf(n_hit, n_got, n_truth):
    p, r = n_hit / max(1, n_got), n_hit / max(1, n_truth)
    return round(p, 3), round(r, 3), round(2 * p * r / max(1e-9, p + r), 3)


def evaluate(truth_path, midi_path, until=None, tol=0.05):
    t = json.load(open(truth_path))
    until = until or (t["loops"][0][2] if t.get("loops") else 1e9)
    truth = [(n[1], n[3], n[4]) for n in t["notes"] if n[5] == "note" and n[1] < until]
    tdrums = [(n[1], drum_kind(int(n[5].split(":")[1]))) for n in t["notes"]
              if n[5].startswith("drum:") and n[5].split(":")[1].isdigit() and n[1] < until]
    got_all, tempos = read_midi(midi_path)
    best = (-1, 0.0)
    for ms in range(-1500, 1501, 10):
        g = [(x[0] + ms / 1000, x[2]) for x in got_all if x[3] != 9]
        f = prf(len(match(truth, g, tol, lambda a, b: a[1] == b[1])), len(g), len(truth))[2]
        if f > best[0]:
            best = (f, ms / 1000)
    shift = best[1]
    got = [(x[0] + shift, x[2], x[4]) for x in got_all if x[3] != 9 and x[0] + shift < until]
    gdrums = [(x[0] + shift, drum_kind(x[2])) for x in got_all if x[3] == 9 and x[0] + shift < until]
    res = {"shift_ms": round(shift * 1000), "truth_notes": len(truth), "notes": len(got)}
    pairs = match(truth, got, tol, lambda a, b: a[1] == b[1])
    res["exact"] = prf(len(pairs), len(got), len(truth))
    res["pitch_class"] = prf(len(match(truth, got, tol, lambda a, b: a[1] % 12 == b[1] % 12)), len(got), len(truth))
    if "programs" in t:  # a General MIDI truth (gm_test_song.py); a ROM song's programs are the game's own
        ok = sum(1 for ti, gi in pairs if GROUP.get(truth[ti][2]) == GROUP.get(got[gi][2]))
        fam = sum(1 for ti, gi in pairs if family(truth[ti][2]) == family(got[gi][2]))
        res["instrument_group_right"] = round(ok / max(1, len(pairs)), 3)
        res["instrument_family_right"] = round(fam / max(1, len(pairs)), 3)
    if tdrums:
        res["drums"] = prf(len(match(tdrums, gdrums, tol, lambda a, b: a[1] == b[1])), len(gdrums), len(tdrums))
        res["drum_hits"] = [len(gdrums), len(tdrums)]
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("truth")
    ap.add_argument("midi")
    ap.add_argument("--until", type=float, default=None)
    ap.add_argument("--tol", type=float, default=0.05)
    a = ap.parse_args()
    print(json.dumps(evaluate(a.truth, a.midi, a.until, a.tol)))


if __name__ == "__main__":
    main()
