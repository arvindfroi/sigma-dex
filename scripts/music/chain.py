"""Song -> notes chain for the Sigma music studio (runs on the Legion, D:\\LocalAI\\music-chain\\venv).

    python chain.py SONG.(wav|mp3|...) OUTDIR [--model large] [--tempo fixed|map] [--beam 1] [--cfg 1.0]

Steps (each timed in OUTDIR/report.json; stems and notes are kept in OUTDIR and reused when run again):
  1. prepare    ffmpeg -> 44.1 kHz stereo WAV
  2. separate   a vocal model first (Mel-Band RoFormer, Kim), then BS-RoFormer SW on the instrumental (drums, bass,
                guitar, piano, other), then DrumSep on the drums (kick, snare, toms, hi-hat, ride, crash)
  3. beats      MuScriptor's beat grid on the full mix (BPM, bars; one grid for every part)
  4. notes      MuScriptor on each stem, told which instruments that stem may hold; the vocal stem becomes a lead
                instrument; drums from DrumSep's stems by onsets (each drum its own General MIDI key)
  5. midi       one MIDI on the mix's grid, quantized (steady tempo by default, so a live recording comes out straight)
  6. dynamics   each note's velocity from its stem's loudness where it starts, each track's volume (CC7) from how
                loud its stem is against the others (MuScriptor writes every note at one velocity)

Output: OUTDIR/song.mid (GM programs from the instrument groups, drums on channel 10), OUTDIR/stems/*.wav,
OUTDIR/report.json. Creature Maker turns song.mid into a HeartGold SSEQ (scripts/music/song_to_rom.lua).
"""
import argparse
import json
import pathlib
import subprocess
import sys
import time

import numpy as np
import soundfile as sf
import torch

MODELS = pathlib.Path(r"D:\LocalAI\music-chain\models")
VOCAL_MODEL = "vocals_mel_band_roformer.ckpt"  # Kim's Mel-Band RoFormer, vocals 12.6 dB SDR
SW_MODEL = "BS-Roformer-SW.ckpt"  # 6 stems; top of MVSEP's multisong board for bass and drums
DRUMSEP_MODEL = "MDX23C-DrumSep-aufr33-jarredou.ckpt"  # kick, snare, toms, hh, ride, crash
STEM_INSTRUMENTS = {  # which of MuScriptor's instrument groups each stem may hold (None: any)
    "vocals": ["voice"],
    "bass": ["electric_bass", "acoustic_bass", "contrabass", "tuba"],
    "piano": ["acoustic_piano", "electric_piano", "chromatic_percussion", "organ"],
    "guitar": ["acoustic_guitar", "clean_electric_guitar", "distorted_electric_guitar"],
    "other": None,
}
DRUM_KEYS = {"kick": 36, "snare": 38, "toms": 45, "hh": 42, "ride": 51, "crash": 49}
# the stem a mix note's instrument most likely sounds in (for its loudness)
STEM_OF_GROUP = {g: "piano" for g in STEM_INSTRUMENTS["piano"]}
STEM_OF_GROUP.update({g: "guitar" for g in STEM_INSTRUMENTS["guitar"]})
STEM_OF_GROUP.update({g: "bass" for g in STEM_INSTRUMENTS["bass"]})
STEM_OF_GROUP.update({"voice": "vocals", "drums": "drums"})


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def prepare(src: pathlib.Path, out: pathlib.Path) -> pathlib.Path:
    dst = out / "mix.wav"
    if not dst.exists():
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ar", "44100", "-ac", "2", str(dst)],
                       check=True)
    return dst


def run_separator(model: str, src: pathlib.Path, outdir: pathlib.Path, overlap: int) -> dict:
    """{stem name: path}; kept in outdir/done.json so a second run skips the model"""
    done = outdir / "done.json"
    if done.exists():
        return {k: pathlib.Path(v) for k, v in json.loads(done.read_text()).items()}
    from audio_separator.separator import Separator

    outdir.mkdir(parents=True, exist_ok=True)
    # overlap: how many overlapping windows each moment is predicted from (8 is the models' default; 2 was ~10x
    # faster here with the GPU's memory no longer full, and the stems are only read for notes, never heard)
    sep = Separator(output_dir=str(outdir), model_file_dir=str(MODELS), output_format="WAV",
                    mdxc_params={"segment_size": 256, "override_model_segment_size": False, "batch_size": 1,
                                 "overlap": overlap, "pitch_shift": 0})
    sep.load_model(model_filename=model)
    stems = {}
    for f in sep.separate(str(src)):
        p = pathlib.Path(f)
        if not p.is_absolute():
            p = outdir / p
        name = p.stem.split("_(")[-1].split(")")[0].lower()
        stems[name] = p
    done.write_text(json.dumps({k: str(v) for k, v in stems.items()}))
    del sep
    torch.cuda.empty_cache()
    return stems


def separate(mix: pathlib.Path, out: pathlib.Path, overlap: int, vocals_first: bool, drumsep: bool) -> dict:
    stems = {}
    inst = mix
    if vocals_first:
        v = run_separator(VOCAL_MODEL, mix, out / "sep_vocals", overlap)
        stems["vocals"] = v["vocals"]
        inst = v.get("other") or v.get("instrumental") or next(p for k, p in v.items() if k != "vocals")
    sw = run_separator(SW_MODEL, inst, out / "sep_sw", overlap)
    for k in ("drums", "bass", "guitar", "piano", "other"):
        if k in sw:
            stems[k] = sw[k]
    if not vocals_first and "vocals" in sw:
        stems["vocals"] = sw["vocals"]
    if drumsep and "drums" in stems:
        d = run_separator(DRUMSEP_MODEL, stems["drums"], out / "sep_drums", overlap)
        for k, p in d.items():
            stems["drum_" + k] = p
    return stems


def load_mono(path, sr=22050):
    import librosa
    y, _ = librosa.load(str(path), sr=sr, mono=True)
    return y


def rms(path: pathlib.Path) -> float:
    data, _ = sf.read(str(path), dtype="float32", always_2d=True)
    return float(np.sqrt(np.mean(data ** 2))) if data.size else 0.0


class Envelope:
    """a stem's loudness over time (RMS in 10 ms frames)"""

    def __init__(self, path):
        y = load_mono(path)
        hop = 220
        n = len(y) // hop
        self.env = np.sqrt(np.mean(y[: n * hop].reshape(n, hop) ** 2, axis=1)) if n else np.zeros(1)
        self.rate = 22050 / hop

    def at(self, t, before=0.03, after=0.10):
        a, b = int(max(0, (t - before) * self.rate)), int(max(1, (t + after) * self.rate))
        seg = self.env[a:b]
        return float(seg.max()) if seg.size else 0.0


def drum_hits(stems: dict) -> list:
    """(time, GM key, strength) for every hit DrumSep's stems have"""
    import librosa
    hits = []
    for name, key in DRUM_KEYS.items():
        p = stems.get("drum_" + name)
        if p is None:
            continue
        y = load_mono(p)
        if y.size == 0 or float(np.sqrt(np.mean(y ** 2))) < 0.002:
            continue
        env = librosa.onset.onset_strength(y=y, sr=22050, hop_length=220)
        times = librosa.onset.onset_detect(onset_envelope=env, sr=22050, hop_length=220, units="time",
                                           backtrack=False, wait=4, delta=0.1)
        frame = Envelope(p)
        loud = np.percentile(frame.env, 99.5) or 1e-6
        for t in times:
            level = frame.at(t, 0.0, 0.06)
            if level > 0.15 * loud:  # bleed from the other drums stays under this
                hits.append((float(t), key, min(1.0, level / loud)))
    return sorted(hits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("song")
    ap.add_argument("outdir")
    ap.add_argument("--model", default="large")
    ap.add_argument("--tempo", choices=["fixed", "map"], default="fixed")
    ap.add_argument("--grid", type=int, default=None, help="steps per beat (4 = sixteenths); default: detected")
    ap.add_argument("--vocals-as", default="synth_lead", help="MuScriptor instrument group the sung melody becomes")
    ap.add_argument("--overlap", type=int, default=2)
    ap.add_argument("--beam", type=int, default=1)
    ap.add_argument("--cfg", type=float, default=1.5, help="guidance; 1.5 named 73%% of parts right against 48%% at 1.0")
    ap.add_argument("--no-vocals-first", action="store_true")
    ap.add_argument("--drums", choices=["drumsep", "muscriptor"], default="muscriptor")
    ap.add_argument("--mode", choices=["hybrid", "stems", "mix"], default="hybrid",
                    help="hybrid: the mix's notes + the bass, drum and vocal stems; stems: every stem; mix: the mix")
    ap.add_argument("--mix", action="store_true", help="same as --mode mix")
    ap.add_argument("--separate-only", action="store_true")
    ap.add_argument("--name", default="song", help="output name: NAME.mid, NAME.json")
    a = ap.parse_args()
    if a.mix:
        a.mode = "mix"

    out = pathlib.Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    report = {"song": a.song, "settings": vars(a), "times": {}, "gpu": torch.cuda.get_device_name(0)}
    t_all = time.time()

    def timed(name, fn, *args, **kw):
        t = time.time()
        log("start", name)
        r = fn(*args, **kw)
        report["times"][name] = round(time.time() - t, 1)
        log("done", name, report["times"][name], "s")
        return r

    mix = timed("prepare", prepare, pathlib.Path(a.song), out)
    info = sf.info(str(mix))
    report["seconds"] = round(info.frames / info.samplerate, 2)

    stems = timed("separate", separate, mix, out, a.overlap, not a.no_vocals_first, a.drums == "drumsep")
    report["stems"] = {k: round(rms(v), 4) for k, v in stems.items()}
    if a.separate_only:
        report["times"]["total"] = round(time.time() - t_all, 1)
        (out / f"{a.name}.json").write_text(json.dumps(report, indent=2))
        log("DONE", json.dumps(report["times"]))
        return 0

    from muscriptor.events import NoteEndEvent, NoteStartEvent
    from muscriptor.transcription_model import TranscriptionModel
    from muscriptor.utils.midi import ExportOptions, resolve_grid

    torch.cuda.reset_peak_memory_stats()
    model = timed("load_model", TranscriptionModel.load_model, a.model)
    grid = timed("beats", model.detect_beat_grid_for, str(mix))

    notes_dir = out / "notes"
    notes_dir.mkdir(exist_ok=True)

    def notes(stem, path, instruments=None):
        """[(start, end, pitch, instrument)], kept per stem and setting"""
        key = notes_dir / f"{stem}_{a.model}_b{a.beam}_c{a.cfg}.json"
        if key.exists():
            return json.loads(key.read_text())
        starts, got = {}, []
        for e in model.transcribe(str(path), instruments=instruments, beam_size=a.beam, cfg_coef=a.cfg):
            if isinstance(e, NoteStartEvent):
                starts[e.index] = e
            elif isinstance(e, NoteEndEvent):
                s = e.start_event
                got.append((s.start_time, max(e.end_time, s.start_time + 0.02), s.pitch, s.instrument))
        key.write_text(json.dumps(got))
        return got

    sources = []  # (stem, [(start, end, pitch, instrument)])
    loud = {k: v >= 0.005 for k, v in report["stems"].items()}
    if a.mode == "hybrid":
        # measured on Route 29 played by the DS and on General MIDI instruments (2026-11-16): the full mix gives
        # the surest notes and names (MuScriptor is trained on mixes; the "other" stem lumps trumpet, strings,
        # piano and flute together and MuScriptor misnames them there), the bass stem the bass, MuScriptor on the
        # drum stem the drums (95 of 102 hits), the vocal stem the sung melody
        got = timed("notes_mix", notes, "mix", mix)
        drop = set(STEM_INSTRUMENTS["bass"]) | {"drums"} | ({"voice"} if loud.get("vocals") else set())
        by_stem = {}
        for n in got:
            if n[3] in drop:
                continue
            st = STEM_OF_GROUP.get(n[3], "other")
            by_stem.setdefault(st if loud.get(st) else "mix", []).append(n)
        sources += list(by_stem.items())
        if loud.get("bass"):
            sources.append(("bass", timed("notes_bass", notes, "bass", stems["bass"], STEM_INSTRUMENTS["bass"])))
        if loud.get("vocals"):
            got = timed("notes_vocals", notes, "vocals", stems["vocals"], ["voice"])
            sources.append(("vocals", [(s, e, p_, a.vocals_as) for s, e, p_, _ in got]))
    elif a.mode == "mix":
        sources.append(("mix", timed("notes_mix", notes, "mix", mix)))
    else:
        # each stem on its own, told which instruments it may hold: the stems keep the parts apart (on the full mix
        # MuScriptor heard Route 29's eight DS voices as one piano), and their names say what each part is
        for stem, insts in STEM_INSTRUMENTS.items():
            p = stems.get(stem)
            if p is None or report["stems"][stem] < 0.005:
                continue
            got = timed("notes_" + stem, notes, stem, p, insts)
            if stem == "vocals":
                got = [(s, e, p_, a.vocals_as) for s, e, p_, _ in got]
            sources.append((stem, got))
    if a.drums == "muscriptor" and loud.get("drums") and a.mode != "mix":
        sources.append(("drums", timed("notes_drums", notes, "drums", stems["drums"], ["drums"])))
    hits = timed("drum_hits", drum_hits, stems) if a.drums == "drumsep" else []
    if hits:
        sources = [(s, [n for n in ns if n[3] != "drums"]) for s, ns in sources]
        sources.append(("drums", [(t, t + 0.1, key, "drums") for t, key, _ in hits]))

    # one stream of MuScriptor's events
    events, index, from_stem = [], 0, {}
    for stem, ns in sources:
        for s, e, p, inst in ns:
            from_stem.setdefault(inst, []).append(stem)
            ns_ = NoteStartEvent(pitch=int(p), start_time=float(s), index=index, instrument=inst)
            index += 1
            events.append((float(s), 0, ns_))
            events.append((float(e), 1, NoteEndEvent(end_time=float(e), start_event=ns_)))
    events.sort(key=lambda x: (x[0], x[1]))
    events = [x[2] for x in events]
    onsets = [e.start_time for e in events if isinstance(e, NoteStartEvent)]
    if grid is not None:
        grid = grid.with_onset_delay(onsets)
    export = ExportOptions(tempo_map=(a.tempo == "map"), quantize=True, subdivision=a.grid)
    midi_bytes = model.events_to_midi_bytes(iter(events), beat_grid=grid, export=export)
    g = resolve_grid(grid, export, onsets) if grid is not None else None
    if g is not None:
        report["grid"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in vars(g).items()
                          if isinstance(v, (int, float, str)) or v is None}

    # dynamics: velocity from the stem's loudness where each note starts, volume per track from the stem's loudness
    midi_path = out / f"{a.name}.mid"
    midi_path.write_bytes(midi_bytes)
    t = time.time()
    try:
        import mido
        mid = mido.MidiFile(str(midi_path))
        envs = {stem: Envelope(stems[stem] if stem in stems else mix) for stem, _ in sources}
        drum_vel = {(round(tt, 2), key): v for tt, key, v in hits}
        stem_rms = {stem: report["stems"].get(stem, rms(mix)) for stem in envs}
        top = max(stem_rms.values() or [1e-6]) or 1e-6
        tempo_events = []
        for tr in mid.tracks:
            tick = 0
            for msg in tr:
                tick += msg.time
                if msg.type == "set_tempo":
                    tempo_events.append((tick, msg.tempo))
        tempo_events.sort()

        def seconds(tick):
            s, last, us = 0.0, 0, 500000
            for tk, tempo in tempo_events:
                if tk >= tick:
                    break
                s += mido.tick2second(tk - last, mid.ticks_per_beat, us)
                last, us = tk, tempo
            return s + mido.tick2second(tick - last, mid.ticks_per_beat, us)

        shift = (g.first_downbeat if g is not None and g.first_downbeat and g.first_downbeat < 0 else 0.0)
        for tr in mid.tracks:
            name = next((m.name for m in tr if m.type == "track_name"), "")
            inst = name.lower().replace(" ", "_")
            stems_of = from_stem.get(inst) or []
            stem = next((s for s in stems_of if s in envs), None)
            is_drums = any(m.type == "note_on" and m.channel == 9 for m in tr)
            env = envs.get(stem) if stem else None
            peak = None
            if env is not None:
                levels = [env.at(s) for s, *_ in next(ns for st, ns in sources if st == stem)]
                peak = float(np.percentile(levels, 95)) if levels else None
            tick = 0
            for msg in tr:
                tick += msg.time
                if msg.type == "note_on" and msg.velocity > 0:
                    tsec = seconds(tick) - shift
                    if is_drums and drum_vel:
                        v = max((vv for (tt, kk), vv in drum_vel.items() if kk == msg.note and abs(tt - tsec) < 0.08),
                                default=0.7)
                    elif env is not None and peak:
                        v = min(1.0, env.at(tsec) / peak)
                    else:
                        continue
                    msg.velocity = int(max(30, min(127, round(40 + 87 * v ** 0.5))))
            if stem and not is_drums:
                vol = int(max(50, min(127, round(127 * (stem_rms[stem] / top) ** 0.5))))
                ch = next((m.channel for m in tr if m.type == "note_on"), 0)
                tr.insert(1, mido.Message("control_change", channel=ch, control=7, value=vol, time=0))
        mid.save(str(midi_path))
        report["dynamics"] = "velocity from stems, CC7 per track"
    except Exception as ex:  # keep MuScriptor's MIDI if the dynamics step fails
        report["dynamics"] = f"failed: {ex!r}"
    report["times"]["dynamics"] = round(time.time() - t, 1)
    report["vram_peak_gb"] = round(torch.cuda.max_memory_allocated() / 2 ** 30, 2)

    per = {}
    for stem, ns in sources:
        for s, e, p, inst in ns:
            d = per.setdefault(inst, {"notes": 0, "low": 127, "high": 0, "stems": set()})
            d["notes"] += 1
            d["low"], d["high"] = min(d["low"], int(p)), max(d["high"], int(p))
            d["stems"].add(stem)
    report["instruments"] = {k: {**v, "stems": sorted(v["stems"])} for k, v in per.items()}
    report["times"]["total"] = round(time.time() - t_all, 1)
    (out / f"{a.name}.json").write_text(json.dumps(report, indent=2))
    log("DONE", json.dumps(report["times"]))


if __name__ == "__main__":
    sys.exit(main())
