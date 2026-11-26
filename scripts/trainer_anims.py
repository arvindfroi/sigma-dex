"""The trainer studio's animation scripts for the website (2026-11-22): the intro animation of each animated class of
a/0/5/8 (NANR sequence 1: pose = cell, tx/ty shift, dur in game frames at 30 a second) + English one-liners.
Only numbers and words, no Nintendo pictures. 119 shares 23's script; left out: 101 (blank cells), 102 (two figures), 106 (starts as a smoke cloud,
not the trainer) and 123 (a close-up of the upper body: a full-body sprite cannot follow it; tested 2026-11-22).
python scripts/trainer_anims.py OUT.json [ROM [PLATINUM_FOLDER]]   (2026-11-27: + Platinum, see PT)"""
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
 86: ("Giovanni with his hat", "Holds a hat, puts it on and tips it.", "A long pause, a jerk forward and a pose switch, ends with quick small shivers."),
 87: ("Elite Four woman (orange hair)", "Raises a hand to the face, a Poke Ball ready in the other.", "A long pause, a small push, a quick shiver, then a slow sway before it holds."),
 88: ("Lance", "Flings the cape out with the arms spread: a dramatic entrance.", "Slides a little, switches pose, a short shiver, holds."),
 89: ("Agatha", "Leans calmly on a cane and lifts it a little.", "Four poses: starts in pose 4, pushed forward and slides back while the poses change."),
 97: ("Tower Tycoon", "The coat flutters while bending the knees and clenching the fists (5 poses).", "Switches calmly between two poses four times, then shakes between two others and ends in a big pose."),
 98: ("Brock", "Crouches, clenches a fist and looks up.", "Short: quickly through three poses with a small jerk, then holds the last one long."),
 99: ("Hall Matron", "A hand over the eyes, looking out, several small steps (6 poses).", "Six poses in a row with long pauses and small side shifts, ends in the last pose."),
 100: ("Factory Head", "Shows a card, then puts a hand on the hip (5 poses).", "Five poses played backwards: two calm, then three fast, ends in pose 1."),
 103: ("Misty", "A sporty jump and kick, lands with the arms out.", "Jump: two poses, a jump up and down, lands with a small tip and slides back a little."),
 104: ("Lt. Surge", "Throws off the sunglasses and crosses the arms.", "A long pause, bobs 1 px up and down four times, then pose 3 with a small push."),
 105: ("Erika", "Turns calmly in a kimono and smiles (4 poses).", "Slides calmly to the side and back through two poses, then pose 3 and back to 2."),
 107: ("Sabrina", "Moves a hand from the face and stretches it out, like telekinesis.", "A long pause, a small dip down and up, then poses 1 and 3 held long."),
 108: ("Blaine", "Lifts the hat and waves it.", "Simple: three poses one after another with pauses, back to the first. No moving."),
 109: ("Gold", "Pulls the cap down, almost standing still.", "Minimal: a long pause, a small jerk sideways, two short poses and back."),
 110: ("Blue", "Points at you, sure of himself.", "Switches slowly between two poses twice, slides forward and back, ends in pose 3."),
 112: ("Bruno", "Sits cross-legged and punches the fists together.", "Slides forward while the pose changes, then quick small jerks back and forth, holds."),
 124: ("Giovanni", "Throws a Poke Ball up in the air and catches it.", "Three poses, each held long: calm and slow, no moving."),
}
# The names follow what Origin shows in each slot (2026-11-27, Arvind asked for Origin's own animations: they were in the list all
# along, under the names of the HGSS trainer that had the slot before, e.g. "Karen slot" for Origin's Lance). Origin redrew these:
ORIGIN_DREW = {86, 87, 88, 89, 103, 107, 109, 124}
# Platinum's animated trainers (2026-11-27, Arvind: "på animations er det en grunn til at vi ikke kan velge fra dp og platinum?
# ... ja fix begge deler"). Read from pret/pokeplatinum res/trainers/classes/<name>/ front_anim.json, front_cell.json and
# front.png (put in a folder by hand as <name>.json, <name>_cell.json, <name>_front.png; not in the repository). In Platinum each
# cell has its own 80x80 picture (VRAM transfer, 100 tiles) and the moves are in the cells' positions, not in the animation:
# each distinct picture is kept once (pose 0 = the still pose of sequence 0, which is the battle sprite), and a cell's shift
# from the still cell becomes tx/ty. ids 1000+, so they never meet an Origin class number. Left out: elite_four_aaron (his jump
# moves the picture 32 px down, which a trainer drawn standing cannot follow); the five Frontier Brains are in HGSS already.
PT = {  # id: (pret name, name, what the poses show, how it moves)
 1000: ("champion_cynthia", "Cynthia", "Stands with one hand raised, then the wind blows the long hair and the coat out to one side.",
        "Sways softly between two poses for four seconds, a pause, then turns into the windblown pose and holds it."),
 1001: ("elite_four_bertha", "Bertha", "Holds a hand out, folds the hands at the chest, then chuckles with a hand at the mouth.",
        "Calm: a long pause, a short pose, then holds the last."),
 1002: ("elite_four_flint", "Flint", "Leans forward with a grin, then stands up laughing with the hands on the hips.",
        "Holds, laughs, bobs between two poses a few times and ends laughing."),
 1003: ("elite_four_lucian", "Lucian", "Stands sideways, calm, lifts one hand and touches the face.",
        "A long pause, the hand comes up slowly, a tiny slide, then holds."),
 1004: ("galactic_boss", "Cyrus", "Stands very still with the hands at the sides, then stretches one arm out with an open hand.",
        "Still for two seconds, a long pause, then a small step and the arm out."),
 1005: ("leader_byron", "Byron", "Swings one arm up over the shoulder with the cape flowing, then rests it there.",
        "A pause, the arm up, held, then a small push and it rests."),
 1006: ("leader_candice", "Candice", "Stands with the knees together, jumps up and cheers with a fist in the air.",
        "A long pause, a hop up and down, then holds the cheering pose."),
 1007: ("leader_fantina", "Fantina", "Bows deeply, then sweeps an arm out like a dancer.",
        "A pause, a bow with a sway to the side, then the sweeping arm, held."),
 1008: ("leader_gardenia", "Gardenia", "Laughs with the hands near the face, skips with an arm out, then points at you.",
        "A long pause, a quick skip to the side and back, ends pointing."),
 1009: ("leader_maylene", "Maylene", "Stretches high, drops into a low stance with clenched fists, then a wide fighting stance.",
        "Small fast sways while stretching, then the low stance, then the wide stance with a small shift."),
 1010: ("leader_roark", "Roark", "Points high up and forward, then puts a hand to the top of the head.",
        "Slides back a little in small steps while pointing, then the hand to the head."),
 1011: ("leader_volkner", "Volkner", "Sits on the ground looking bored, gets up turned away, then stands and faces you.",
        "Sits for a second, gets up bent over, holds, then turns to you."),
 1012: ("leader_wake", "Wake", "Flexes with the fists together, stands with the chest out, then raises both fists and shouts.",
        "Pumps between two flexes several times, then a big flex, held."),
 1013: ("rival", "Barry", "Bounces impatiently between a step and a jump, then stands with both fists up.",
        "Fast jittery bounces, a pause, then the fists-up pose."),
 1014: ("trainer_buck", "Buck", "Puts an arm behind the head, then lunges forward with a fist out.",
        "Swings between two poses for a few seconds, then a fast lunge, held."),
 1015: ("trainer_cheryl", "Cheryl", "Waves softly with one hand, then holds both hands shyly near the face.",
        "Slow: a pause, a gentle wave with small slides, ends shy."),
 1016: ("trainer_marley", "Marley", "Stands quietly and tilts the head a little.",
        "Very calm: two long holds with one short change between them."),
 1017: ("trainer_mira", "Mira", "Spins with the arms spread and skips with a knee up.",
        "Twirls back and forth through the poses three times, quick and bouncy."),
 1018: ("trainer_riley", "Riley", "Holds the hat, flings an arm out to the side, then stretches it forward.",
        "The arm goes out, then a long fast shiver between two poses."),
}


def platinum(folder):
    import numpy as np
    from PIL import Image
    out = []
    for i, (name, label, poses, moves) in PT.items():
        an = json.load(open(os.path.join(folder, name + '.json')))
        ce = json.load(open(os.path.join(folder, name + '_cell.json')))
        pal = Image.open(os.path.join(folder, name + '_front.png'))
        blocks = [np.array(pal.crop((0, k * 81, 80, k * 81 + 80))) for k in range((pal.height + 1) // 81)]
        canon = []
        for b in range(len(blocks)):
            same = next((j for j in range(b) if np.array_equal(blocks[b], blocks[j])), b)
            canon.append(canon[same] if same != b else b)
        cellblk = [t['offset'] // 3200 for t in ce['transferData']]
        pos = [(c['OAM'][0]['Attr1']['XCoordinate'], c['OAM'][0]['Attr0']['YCoordinate']) if c['OAM'] else None for c in ce['cells']]
        res = an['animationResults']
        still = res[an['sequences'][0]['frameData'][0]['resultId']]['index']
        intro = [(res[f['resultId']]['index'], f['frameDelay']) for f in an['sequences'][1]['frameData']]
        order = [canon[cellblk[still]]]
        for cell, _ in intro:
            if canon[cellblk[cell]] not in order:
                order.append(canon[cellblk[cell]])
        seq = [[order.index(canon[cellblk[c]]), pos[c][0] - pos[still][0], pos[c][1] - pos[still][1], d] for c, d in intro]
        out.append(dict(cls=i, name=label, game='Platinum', base='pt:' + name, pt=name, blocks=order, poses=len(order), cells=list(range(len(order))),
                        seq=seq, shows=poses, moves=moves, seconds=round(sum(x[3] for x in seq) / 30, 1)))
    return out


rom = open(sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser('~/sigma-origin/rc8/origin_hg_en_rc8.nds'), 'rb').read()
s, e = fnt_files(rom)['a/0/5/8']; F = unpack(rom[s:e]); out = []
for c, (name, poses, moves) in T.items():
    q = read_nanr(F[c * 5 + 3])['seqs'][1]
    seq = [[f['cell'], f.get('tx', 0), f.get('ty', 0), f['dur']] for f in q['frames']]
    out.append(dict(cls=c, name=name, game='Origin' if c in ORIGIN_DREW else 'HGSS', poses=len({x[0] for x in seq}), cells=sorted({x[0] for x in seq}), seq=seq,
                    shows=poses, moves=moves, seconds=round(sum(x[3] for x in seq) / 30, 1)))
if len(sys.argv) > 3:                                  # python trainer_anims.py OUT.json ROM PLATINUM_FOLDER
    out += platinum(sys.argv[3])
# poses: the picker's sheet of the real poses, one row per script in this order (~/sigma-origin/title3d/legend/trainers/
# dump_anim_poses.py, uploaded to storage like the trainer bases; 2026-11-24)
json.dump(dict(fps=30, poses='trainer-bases/anim_poses_v2.png', scripts=out), open(sys.argv[1], 'w'), separators=(',', ':'), ensure_ascii=False); print(len(out), 'scripts')
