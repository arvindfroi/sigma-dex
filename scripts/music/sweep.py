"""Runs chain.py on the test songs with several settings and scores each against its truth (compare_notes.py).

    python sweep.py RESULTS.json

Test songs (D:\\LocalAI\\music-chain\\work): r29 = Route 29 played by the DS (truth from the ROM), gm29 = the same
notes on General MIDI instruments (gm_test_song.py, truth knows each channel's instrument).
"""
import json
import pathlib
import subprocess
import sys
import time

from compare_notes import evaluate

W = pathlib.Path(r"D:\LocalAI\music-chain\work")
SONGS = {"r29": (W / "r29" / "input.wav", W / "r29" / "truth.json", 58.3),
         "gm29": (W / "gm29" / "gm.wav", W / "gm29" / "gm_truth.json", 58.3)}
CONFIGS = {
    "v2": [],
    "beam4": ["--beam", "4"],
    "cfg2": ["--cfg", "2.0"],
    "mix": ["--mix"],
    "drums_muscriptor": ["--drums", "muscriptor"],
    "medium": ["--model", "medium"],
    "mix_cfg15": ["--mix", "--cfg", "1.5", "--drums", "muscriptor"],
    "mix_cfg2": ["--mix", "--cfg", "2.0", "--drums", "muscriptor"],
    "hybrid15": ["--cfg", "1.5"],
}


def main():
    out = pathlib.Path(sys.argv[1])
    results = json.loads(out.read_text()) if out.exists() else {}
    only = sys.argv[2:] or list(CONFIGS)
    for song, (wav, truth, until) in SONGS.items():
        for name in only:
            key = f"{song}/{name}"
            t = time.time()
            r = subprocess.run([sys.executable, "chain.py", str(wav), str(W / ("v2_" + song)), "--tempo", "map",
                                "--name", name] + CONFIGS[name], capture_output=True, text=True)
            took = round(time.time() - t, 1)
            if r.returncode != 0:
                results[key] = {"error": r.stderr[-1500:]}
            else:
                rep = json.loads((W / ("v2_" + song) / f"{name}.json").read_text())
                results[key] = {"score": evaluate(str(truth), str(W / ("v2_" + song) / f"{name}.mid"), until),
                                "times": rep["times"], "wall": took}
            out.write_text(json.dumps(results, indent=1))
            print(key, json.dumps(results[key])[:400], flush=True)


if __name__ == "__main__":
    main()
