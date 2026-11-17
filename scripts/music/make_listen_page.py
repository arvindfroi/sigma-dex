"""A local listening page for naming HeartGold's basic-bank sounds by ear (as ROM hackers do), pre-filled with the
best guess: the hacking guide's verified ones, else MuScriptor's / CLAP's name, with the nearest General MIDI sounds
by timbre as a hint. Writes music_tests/lytt/index.html (local only: it plays the game's own samples).

    python3 make_listen_page.py GM_MATCH_TSV
The page exports hg_instrumenter_arvind.json (id -> group) to the Downloads folder; import_listen.py merges it into
data/music/hg_instruments.tsv.
"""
import html
import json
import pathlib
import sys

R = pathlib.Path(__file__).resolve().parents[2]
GROUPS = ["acoustic_piano", "electric_piano", "chromatic_percussion", "organ", "acoustic_guitar", "clean_electric_guitar",
          "distorted_electric_guitar", "acoustic_bass", "electric_bass", "violin", "viola", "cello", "contrabass",
          "orchestral_harp", "timpani", "string_ensemble", "pizzicato", "synth_strings", "voice", "orchestra_hit",
          "trumpet", "trombone", "tuba", "french_horn", "brass_section", "soprano_and_alto_sax", "tenor_sax",
          "baritone_sax", "oboe", "english_horn", "bassoon", "clarinet", "flutes", "synth_lead", "synth_pad",
          "sound_effect", "unknown"]
NB = {"acoustic_piano": "piano", "electric_piano": "el-piano / Rhodes",
      "chromatic_percussion": "klokkespill / vibrafon / marimba", "organ": "orgel", "acoustic_guitar": "akustisk gitar",
      "clean_electric_guitar": "el-gitar (ren)", "distorted_electric_guitar": "el-gitar (vreng)",
      "acoustic_bass": "akustisk bass", "electric_bass": "el-bass", "violin": "fiolin", "viola": "bratsj",
      "cello": "cello", "contrabass": "kontrabass (strøk)", "orchestral_harp": "harpe", "timpani": "pauker",
      "string_ensemble": "strykere", "pizzicato": "pizzicato-strykere", "synth_strings": "synth-strykere",
      "voice": "kor / stemme", "orchestra_hit": "orkesterslag", "trumpet": "trompet", "trombone": "trombone",
      "tuba": "tuba", "french_horn": "valthorn", "brass_section": "messing (gruppe)",
      "soprano_and_alto_sax": "altsaks", "tenor_sax": "tenorsaks", "baritone_sax": "barytonsaks", "oboe": "obo",
      "english_horn": "engelsk horn", "bassoon": "fagott", "clarinet": "klarinett", "flutes": "fløyte",
      "synth_lead": "synth lead / firkantbølge", "synth_pad": "synth pad", "sound_effect": "lydeffekt",
      "unknown": "vet ikke"}
GMNAME = ["Grand Piano", "Bright Piano", "Electric Grand", "Honky-tonk", "Rhodes", "Chorus E.Piano", "Harpsichord",
          "Clavinet", "Celesta", "Glockenspiel", "Music Box", "Vibraphone", "Marimba", "Xylophone", "Tubular Bells",
          "Dulcimer", "Drawbar Organ", "Perc. Organ", "Rock Organ", "Church Organ", "Reed Organ", "Accordion",
          "Harmonica", "Bandoneon", "Nylon Guitar", "Steel Guitar", "Jazz Guitar", "Clean Guitar", "Muted Guitar",
          "Overdrive Guitar", "Distortion Guitar", "Guitar Harmonics", "Acoustic Bass", "Finger Bass", "Pick Bass",
          "Fretless Bass", "Slap Bass 1", "Slap Bass 2", "Synth Bass 1", "Synth Bass 2", "Violin", "Viola", "Cello",
          "Contrabass", "Tremolo Strings", "Pizzicato", "Harp", "Timpani", "Strings", "Slow Strings",
          "Synth Strings 1", "Synth Strings 2", "Choir Aahs", "Voice Oohs", "Synth Voice", "Orchestra Hit", "Trumpet",
          "Trombone", "Tuba", "Muted Trumpet", "French Horn", "Brass Section", "Synth Brass 1", "Synth Brass 2",
          "Soprano Sax", "Alto Sax", "Tenor Sax", "Baritone Sax", "Oboe", "English Horn", "Bassoon", "Clarinet",
          "Piccolo", "Flute", "Recorder", "Pan Flute", "Bottle", "Shakuhachi", "Whistle", "Ocarina", "Square Lead",
          "Saw Lead", "Calliope", "Chiff", "Charang", "Voice Lead", "Fifths", "Bass+Lead", "New Age Pad", "Warm Pad",
          "Polysynth", "Choir Pad", "Bowed Pad", "Metallic Pad", "Halo Pad", "Sweep Pad", "Rain", "Soundtrack",
          "Crystal", "Atmosphere", "Brightness", "Goblin", "Echoes", "Sci-fi", "Sitar", "Banjo", "Shamisen", "Koto",
          "Kalimba", "Bagpipe", "Fiddle", "Shanai", "Tinkle Bell", "Agogo", "Steel Drums", "Woodblock", "Taiko",
          "Melodic Tom", "Synth Drum", "Reverse Cymbal", "Fret Noise", "Breath", "Seashore", "Bird", "Telephone",
          "Helicopter", "Applause", "Gunshot"]


def load(p):
    d = {}
    for line in open(p):
        if not line.startswith("#"):
            f = line.rstrip("\n").split("\t")
            d[f[0]] = f
    return d


def main():
    names = load(R / "data/music/hg_sound_names.tsv")
    gm = load(sys.argv[1])
    ver = {}
    for line in open(R / "data/music/hg_instruments.tsv"):
        if line.startswith("b"):
            f = line.rstrip("\n").split("\t")
            ver[f[0]] = (f[1], f[2])
    lyd = R / "music_tests/lytt/lyd"
    ids = sorted((p.stem for p in lyd.glob("b700.*.mp3")), key=lambda s: int(s.split(".")[1]))
    rows = []
    for sid in ids:
        n, g = names.get(sid), gm.get(sid)
        rows.append({"id": sid, "prog": int(sid.split(".")[1]), "use": float(n[2]) if n else 0,
                     "guess": ver[sid][0] if sid in ver else (n[3] if n else "unknown"), "verified": sid in ver,
                     "src": ver[sid][1] if sid in ver else (n[5] if n and len(n) > 5 else ""),
                     "gm": ", ".join(GMNAME[int(g[i])] for i in (3, 5, 7)) if g else ""})
    opts = "".join(f'<option value="{k}">{html.escape(NB[k])}</option>' for k in GROUPS)
    page = (R / "scripts/music/listen_page_template.html").read_text()
    page = page.replace("__ROWS__", json.dumps(rows)).replace("__OPTS__", json.dumps(opts))
    (R / "music_tests/lytt/index.html").write_text(page)
    print(len(rows), "sounds; verified", sum(r["verified"] for r in rows))


if __name__ == "__main__":
    main()
