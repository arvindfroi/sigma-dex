"""The trainer studio's animation scripts for the website (2026-11-22): the intro animation of each animated class of
a/0/5/8 (NANR sequence 1: pose = cell, tx/ty shift, dur in game frames at 30 a second) + English one-liners.
Only numbers and words, no Nintendo pictures. 119 shares 23's script; left out: 101 (blank cells), 102 (two figures), 106 (starts as a smoke cloud,
not the trainer) and 123 (a close-up of the upper body: a full-body sprite cannot follow it; tested 2026-11-22).
python anim_site.py OUT.json [ROM]"""
import sys, os, json
sys.path.insert(0, os.path.expanduser('~/sigma-origin/title3d')); sys.path.insert(0, os.path.expanduser('~/sigma-origin/title3d/legend'))
from custom_jump_fnt import fnt_files
from narc import unpack
from g2d import read_nanr
T = {  # cls: (name, what the poses show, how it moves)
 23: ("Rival", "Hand in a pocket, then reaches the other hand out at you as a challenge.", "Calm: holds pose 1, slides a little and switches to pose 2, ends holding pose 3."),
 66: ("Falkner", "Battle stance: bends forward and swings an arm out like a wing.", "Darts forward, switches pose and slides back, ends leaning back."),
 67: ("Bugsy", "Swings a net up and forward over the head.", "Holds, leans back a little, then two quick pose switches with a small push forward."),
 70: ("Whitney", "Jumps happily into the air with the arms up.", "Lively: several small hops and one big jump straight up, ends with small jerks."),
 72: ("Morty", "Reaches a hand out, turns away and pulls the scarf up over the face.", "Played backwards (3, 2, 1): a long pause, a small jerk, ends in pose 1."),
 73: ("Pryce", "Stands firm on a cane while an icy wind blows the scarf.", "Flutter: switches fast between poses 2 and 3, slower, faster, slower. No moving."),
 74: ("Jasmine", "Stands shy and still, looks down and folds the hands.", "Slow and calm: a long pause, slides gently, switches pose and ends calmly."),
 75: ("Chuck", "Crouches in a battle stance and flexes with a fist up.", "Shakes back and forth for a second, a hard push forward, then small hops."),
 76: ("Clair", "Turns so the cape swirls and looks at you over the shoulder.", "Slides in from the side and back again while the pose changes: a side step."),
 86: ("Champion slot", "Holds a hat, puts it on and tips it.", "A long pause, a jerk forward and a pose switch, ends with quick small shivers."),
 87: ("Will slot", "Raises a hand to the face, a Poke Ball ready in the other.", "A long pause, a small push, a quick shiver, then a slow sway before it holds."),
 88: ("Karen slot", "Flings the cape out with the arms spread: a dramatic entrance.", "Slides a little, switches pose, a short shiver, holds."),
 89: ("Koga slot", "Leans calmly on a cane and lifts it a little.", "Four poses: starts in pose 4, pushed forward and slides back while the poses change."),
 97: ("Tower Tycoon", "The coat flutters while bending the knees and clenching the fists (5 poses).", "Switches calmly between two poses four times, then shakes between two others and ends in a big pose."),
 98: ("Brock", "Crouches, clenches a fist and looks up.", "Short: quickly through three poses with a small jerk, then holds the last one long."),
 99: ("Hall Matron", "A hand over the eyes, looking out, several small steps (6 poses).", "Six poses in a row with long pauses and small side shifts, ends in the last pose."),
 100: ("Factory Head", "Shows a card, then puts a hand on the hip (5 poses).", "Five poses played backwards: two calm, then three fast, ends in pose 1."),
 103: ("Misty", "A sporty jump and kick, lands with the arms out.", "Jump: two poses, a jump up and down, lands with a small tip and slides back a little."),
 104: ("Lt. Surge", "Throws off the sunglasses and crosses the arms.", "A long pause, bobs 1 px up and down four times, then pose 3 with a small push."),
 105: ("Erika", "Turns calmly in a kimono and smiles (4 poses).", "Slides calmly to the side and back through two poses, then pose 3 and back to 2."),
 107: ("Sabrina", "Moves a hand from the face and stretches it out, like telekinesis.", "A long pause, a small dip down and up, then poses 1 and 3 held long."),
 108: ("Blaine", "Lifts the hat and waves it.", "Simple: three poses one after another with pauses, back to the first. No moving."),
 109: ("Red", "Pulls the cap down, almost standing still.", "Minimal: a long pause, a small jerk sideways, two short poses and back."),
 110: ("Blue", "Points at you, sure of himself.", "Switches slowly between two poses twice, slides forward and back, ends in pose 3."),
 112: ("Bruno slot", "Sits cross-legged and punches the fists together.", "Slides forward while the pose changes, then quick small jerks back and forth, holds."),
 124: ("Rocket Boss", "Throws a Poke Ball up in the air and catches it.", "Three poses, each held long: calm and slow, no moving."),
}
rom = open(sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser('~/sigma-origin/rc8/origin_hg_en_rc8.nds'), 'rb').read()
s, e = fnt_files(rom)['a/0/5/8']; F = unpack(rom[s:e]); out = []
for c, (name, poses, moves) in T.items():
    q = read_nanr(F[c * 5 + 3])['seqs'][1]
    seq = [[f['cell'], f.get('tx', 0), f.get('ty', 0), f['dur']] for f in q['frames']]
    out.append(dict(cls=c, name=name, poses=len({x[0] for x in seq}), cells=sorted({x[0] for x in seq}), seq=seq, shows=poses, moves=moves,
                    seconds=round(sum(x[3] for x in seq) / 30, 1)))
json.dump(dict(fps=30, scripts=out), open(sys.argv[1], 'w'), separators=(',', ':'), ensure_ascii=False); print(len(out), 'scripts')
