#!/usr/bin/env python3
"""Count how much each claimable character says in Origin HeartGold, and write the numbers into data/characters.yaml.

    python3 scripts/character_dialogue.py            # needs the unpacked game in ~/sigma-origin (never in this repo)

Arvind (2026-11-16): "inne på characters så tror jeg også vi kan si hvor mye dialog hver karakter har". Only the
numbers go into the repo, never the text (the text is Nintendo's and the Origin team's).

- story: text boxes the character speaks in the story. The game's text banks (~/sigma-origin/msg/*.txt) put the speaker
  in front ("Chuck: ..."); a message keeps that speaker until another name comes. One box = one \\r-separated part.
- battle: their lines in battle (before, when they lose, last Pokemon, ...), from the trainer text table a/0/5/7
  (trainer id, kind) whose lines are text bank 718 in the same order. Their trainer ids come from the trainer list
  ~/sigma-origin/docs/trainers.md ("#### Leader Chuck (#251)").
- words: all their words, story and battle together.

Koga is both the Fuchsia leader and an Elite Four member in Origin: both roles get his story lines (one person).
Green and Red are one role (a girl player meets Red instead, with the same lines): the bigger count is used.
"""
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME = Path.home() / "sigma-origin"
FILE = ROOT / "data" / "characters.yaml"

# character id -> (speaker names in the story, trainer names in the trainer list)
WHO = {
    "gym-bug": (["Bugsy"], ["Leader Bugsy"]),
    "gym-dragon": (["Clair"], ["Leader Clair"]),
    "gym-electric": (["Lt. Surge"], ["Leader Lt. Surge"]),
    "gym-fighting": (["Chuck"], ["Leader Chuck"]),
    "gym-fire": (["Blaine"], ["Leader Blaine"]),
    "gym-flying": (["Falkner"], ["Leader Falkner"]),
    "gym-ghost": (["Morty"], ["Leader Morty"]),
    "gym-grass": (["Erika"], ["Leader Erika"]),
    "gym-ice": (["Pryce"], ["Leader Pryce"]),
    "gym-normal": (["Whitney"], ["Leader Whitney"]),
    "gym-poison": (["Koga"], ["Leader Koga"]),
    "gym-psychic": (["Sabrina"], ["Leader Sabrina"]),
    "gym-rock": (["Brock"], ["Leader Brock"]),
    "gym-steel": (["Jasmine"], ["Leader Jasmine"]),
    "gym-water": (["Misty"], ["Cerulean Trnr Misty"]),
    "trainer-c": (["Eusine"], ["Mystery Man Eusine"]),
    "trainer-g": (["Gold"], ["Johto Trainer Gold", "PKMN Trainer Gold"]),
    "trainer-h": (["Koga"], ["Elite Four Koga"]),
    "trainer-i": (["Lance"], ["Elite Four Lance"]),
    "trainer-j": ([["Green"], ["Red"]], [["PKMN Trainer Green"], ["PKMN Trainer Red"]]),   # one role, two versions
    "trainer-k": (["Lorelei"], ["Elite Four Lorelei"]),
    "trainer-m": (["Agatha"], ["Elite Four Agatha"]),
    "trainer-o": (["Crystal"], ["Johto Trainer Crystal"]),
    "trainer-p": (["Yellow"], ["Viridian Trnr Yellow"]),
    "trainer-q": (["Bruno"], ["Elite Four Bruno"]),
    "trainer-u": (["Lorin"], ["Elite Four Lorin"]),
    "trainer-w": (["Silver"], ["Redhead Silver"]),
    "trainer-x": (["Goh"], ["One-Ball Man Goh"]),
}
TAG = re.compile(r"^\s*([A-Z][A-Za-z.'\- ]{0,24}):\s")
CODE = re.compile(r"\{[^}]*\}|\\[nrf]")


def words(text):
    return len(CODE.sub(" ", text).split())


def story_lines():
    """speaker -> [boxes, words] over every text bank."""
    out = {}
    for path in sorted((GAME / "msg").glob("*.txt")):
        if path.stem == "718":
            continue
        for message in path.read_text(encoding="utf-8").split("\n"):
            speaker = None
            for box in message.split("\\r"):
                m = TAG.match(box)
                if m:
                    speaker = m.group(1)
                    box = box[m.end():]
                if speaker and box.strip():
                    entry = out.setdefault(speaker, [0, 0])
                    entry[0] += 1
                    entry[1] += words(box)
    return out


def battle_lines():
    """trainer id -> [lines, words], from a/0/5/7 and text bank 718."""
    data = (GAME / "x_origin" / "files" / "a" / "0" / "5" / "7").read_bytes()
    fatb = struct.unpack_from("<I", data, 20)[0]
    start, end = struct.unpack_from("<II", data, 28)
    fntb = 16 + fatb
    image = fntb + struct.unpack_from("<I", data, fntb + 4)[0] + 8
    table = data[image + start:image + end]
    texts = (GAME / "msg" / "718.txt").read_text(encoding="utf-8").split("\n")
    out = {}
    for i in range(len(table) // 4):
        trainer, _kind = struct.unpack_from("<HH", table, i * 4)
        entry = out.setdefault(trainer, [0, 0])
        entry[0] += 1
        entry[1] += words(texts[i]) if i < len(texts) else 0
    return out


def trainer_ids():
    """trainer name ("Leader Chuck") -> its trainer ids."""
    out = {}
    for m in re.finditer(r"^#### (.+?) \(#(\d+)\)", (GAME / "docs" / "trainers.md").read_text(encoding="utf-8"), re.M):
        out.setdefault(m.group(1), []).append(int(m.group(2)))
    return out


def count(speakers, trainers, story, battle, ids):
    s = [story.get(n, [0, 0]) for n in speakers]
    b = [battle.get(t, [0, 0]) for name in trainers for t in ids.get(name, [])]
    return {"story": sum(x[0] for x in s), "battle": sum(x[0] for x in b), "words": sum(x[1] for x in s) + sum(x[1] for x in b)}


def main():
    story, battle, ids = story_lines(), battle_lines(), trainer_ids()
    result = {}
    for cid, (speakers, trainers) in WHO.items():
        if speakers and isinstance(speakers[0], list):
            options = [count(sp, tr, story, battle, ids) for sp, tr in zip(speakers, trainers)]
            result[cid] = max(options, key=lambda x: x["words"])
        else:
            result[cid] = count(speakers, trainers, story, battle, ids)
    text = FILE.read_text(encoding="utf-8")
    text = re.sub(r"^  dialogue: \{[^}]*\}\n", "", text, flags=re.M)
    for cid, c in result.items():
        line = "  dialogue: {story: %d, battle: %d, words: %d}\n" % (c["story"], c["battle"], c["words"])
        text, n = re.subn(r"(^- id: %s\n(?:  .*\n)*?)(  teams:)" % re.escape(cid), lambda m: m.group(1) + line + m.group(2), text, count=1, flags=re.M)
        if not n:
            print("not found in characters.yaml:", cid)
    if "# dialogue:" not in text:
        text = text.replace("\n- id:", "\n# dialogue: how much they say in Origin: story = text boxes in the story, battle = lines in battle, words =\n"
                            "# both together (scripts/character_dialogue.py, counted 2026-11-16; only numbers, never the text).\n- id:", 1)
    FILE.write_text(text, encoding="utf-8")
    for cid, c in sorted(result.items(), key=lambda kv: -kv[1]["words"]):
        print("%-13s story %4d  battle %3d  words %6d" % (cid, c["story"], c["battle"], c["words"]))


if __name__ == "__main__":
    main()
