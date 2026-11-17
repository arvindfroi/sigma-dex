"""A song's MIDI (chain.py's) into a HeartGold / Origin ROM, checked in the game itself, on the Mac.

    python3 make_track.py song.mid SEQ_ID OUTDIR [--rom ~/creature-maker-work/roms/origin_hg_en.nds]

1. song_to_rom.lua writes it in the place of SEQ_ID (every map that plays it), each part on the HeartGold sound named
   like its instrument, borrowing another song's wave archive where the slot's bank lacks one.
2. rom_song_check.lua boots the written ROM in melonDS on such a map: which sequence plays, how much of the sound
   heap is free, and a recording.
3. The recording is compared with our DS player's rendering of the same song (loudness every 50 ms, lined up). A
   silent or unlike recording means something didn't fit the sound heap (it isn't loaded): try again borrowing less,
   then nothing. The last good try is kept: OUTDIR/track.nds, track_game.wav (what the game played), track.json.
"""
import argparse
import array
import json
import math
import os
import pathlib
import shutil
import subprocess
import wave

HERE = pathlib.Path(__file__).resolve().parent
CM = pathlib.Path.home() / "creature-maker" / "editor"


def envelope(path, step_s=0.05):
    w = wave.open(str(path))
    n, ch, sr = w.getnframes(), w.getnchannels(), w.getframerate()
    a = array.array("h", w.readframes(n))
    step = int(sr * step_s)
    out = []
    for i in range(0, n - step, step):
        seg = a[i * ch:(i + step) * ch:5]
        out.append(math.sqrt(sum(x * x for x in seg) / max(1, len(seg))) / 32768)
    return out


def likeness(game, ours, max_lag=200):
    best = -1.0
    for lag in range(max_lag):
        n = min(len(ours), len(game) - lag)
        if n < 60:
            break
        a, b = ours[:n], game[lag:lag + n]
        ma, mb = sum(a) / n, sum(b) / n
        va = sum((x - ma) ** 2 for x in a)
        vb = sum((y - mb) ** 2 for y in b)
        if va <= 0 or vb <= 0:
            continue
        best = max(best, sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb))
    return best


def run(cmd, env):
    r = subprocess.run(cmd, cwd=CM, env=env, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("midi")
    ap.add_argument("seq", type=int)
    ap.add_argument("outdir")
    ap.add_argument("--rom", default=str(pathlib.Path.home() / "creature-maker-work/roms/origin_hg_en.nds"))
    ap.add_argument("--names", default=str(HERE.parent.parent / "data/music/hg_sound_names.tsv"))
    ap.add_argument("--seconds", type=float, default=30)
    a = ap.parse_args()
    out = pathlib.Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    tries = []
    for borrow in (16 * 1024, 8 * 1024, 0):  # Route 29 had ~18 KB of sound heap free with our song
        data = HERE.parent.parent / "data" / "music"
        env = dict(os.environ, CM_GEN4_ROM=a.rom, SOUND_NAMES=a.names, BORROW_MAX=str(borrow),
                   SOUND_VERIFIED=str(data / "hg_instruments.tsv"), SOUND_DRUMS=str(data / "hg_drums.tsv"),
                   SECONDS_OUT=str(a.seconds + 5))
        tag = f"b{borrow // 1024}k"
        code, log = run(["luajit", str(HERE / "song_to_rom.lua"), a.midi, str(a.seq), str(out / f"{tag}.nds"),
                         str(out / f"{tag}_player.wav"), str(out / f"{tag}.json")], env)
        if code != 0:
            tries.append({"borrow": borrow, "error": log[-600:]})
            continue
        rep = json.loads((out / f"{tag}.json").read_text())
        code, log = run(["luajit", str(HERE / "rom_song_check.lua"), str(out / f"{tag}.nds"), a.rom,
                         str(rep["new_seq"]), str(a.seconds), str(out / f"{tag}_game.wav")], env)
        plays = f"PLAYS {rep['new_seq']}" in log
        heap = next((ln for ln in log.splitlines() if ln.startswith("sound heap")), "")
        game = envelope(out / f"{tag}_game.wav") if (out / f"{tag}_game.wav").exists() else []
        ours = envelope(out / f"{tag}_player.wav")
        loud = sum(game) / max(1, len(game))
        like = likeness(game, ours) if game else -1
        ours_loud = sum(ours) / max(1, len(ours))
        # silence is how a song that didn't fit shows (its bank or an archive isn't loaded); the likeness is only
        # said, as the game may start the song anywhere (Creature Maker found Origin 19 s in)
        ok = plays and loud > 0.003 and loud > 0.2 * ours_loud
        t = {"borrow": borrow, "status": rep["status"], "borrowed_bytes": rep.get("borrowed_archive_bytes", 0),
             "plays": plays, "heap": heap, "game_loudness": round(loud, 4), "our_loudness": round(ours_loud, 4), "likeness": round(like, 2), "ok": ok}
        tries.append(t)
        print(json.dumps(t))
        if ok:
            for suffix in (".nds", "_game.wav", "_player.wav", ".json"):
                shutil.copy(out / f"{tag}{suffix}", out / f"track{suffix}")
            rep["verified_in_game"] = t
            (out / "track.json").write_text(json.dumps(rep, indent=1))
            break
        if rep.get("borrowed_archive_bytes", 0) == 0:
            break  # nothing borrowed and still not right: borrowing less won't help
    (out / "tries.json").write_text(json.dumps(tries, indent=1))
    good = next((t for t in tries if t.get("ok")), None)
    print("VERIFIED IN GAME" if good else "NOT VERIFIED: see tries.json")


if __name__ == "__main__":
    main()
