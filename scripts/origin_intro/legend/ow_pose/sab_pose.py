"""Sabertann's frames 6 (anticipation) and 7 (the roar) as cut-out puppets of the approved field sprite, posed far enough to
match Lugia's and Ho-Oh's change (Arvind 2026-11-17: "so little happens in the two frames compared with Lugia and Ho-Oh").
  6, the wind-up: the sails are furled, rolled up tight on two yards on the mast (Arvind: "the sail should be rolled up on the
     mast when it is closed"; FURLED=heap drops them behind the head instead), the bare mast shows; the ship and body
     sink, the head sinks lower still between the shoulders, the front legs splay out wide like a cat before a pounce
  7, the roar: the sails are thrown open bigger than in flight, the body rears up, the head is thrown up with the jaws open
     (roar v1's open mouth), the viewer's-left front paw is raised high with the claws out, the other leg braces out
These are rough layouts (turned pixels); Qwen redraws them as clean pixel art (qwen_clean.py).
python sab_pose.py REST_idx.npy ROAR_idx.npy PAL.npy OUTDIR  -> anticip_idx.npy, roar_idx.npy, *.png (64 px and 8x)"""
import sys, os
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from puppet import part, box, move, stack, rgba, close_gaps
RF, OF, PF, OD = sys.argv[1:5]; os.makedirs(OD, exist_ok=True)
rest = np.load(RF).astype(int); roar = np.load(OF).astype(int); PAL = np.load(PF)
E = lambda k, d: float(os.environ.get(k, d))
def parts(f):
    on = f > 0
    mastflag = box(0, 8, 29, 39) & on
    head = (box(24, 32, 21, 44) | box(32, 58, 16, 48)) & on
    head &= ~(box(0, 32, 0, 64) & np.isin(f, (15, 11, 9, 5)))    # sail cloth around the band belongs to the sails
    sails = box(7, 32, 0, 64) & ~head & ~mastflag & on
    legL = box(51, 64, 0, 24) & on & ~head; legR = box(51, 64, 40, 64) & on & ~head
    body = box(30, 58, 0, 64) & on & ~head & ~sails & ~legL & ~legR
    body &= ~(box(0, 34, 0, 64) & np.isin(f, (15, 11, 9, 5)))   # the sail flaps' cloth by the shoulder spikes
    return {k: part(f, m) for k, m in dict(mastflag=mastflag, head=head, sails=sails, legL=legL, legR=legR, body=body).items()}
R, O = parts(rest), parts(roar)
MAST, YARD = 2, 8
# --- 6: the wind-up
S = E('SINK', 3)
yard = np.zeros((64, 64), int)
yard[int(7 + S):30, 31:33] = MAST                               # the bare mast down to the head
GREY, WHITE, SHADE, TIE = 11, 15, 9, 2
def roll(img, y, x0, x1):                                       # a sail rolled up tight on its yard (Arvind: "rolled up on the mast")
    img[y + 1, x0 - 1:x1 + 1] = YARD                            # the yard, a little longer than the roll
    img[y - 2, x0 + 1:x1 - 1] = GREY; img[y - 1, x0:x1] = WHITE; img[y, x0:x1] = SHADE
    for x in range(x0 + 3, x1 - 2, 5): img[y - 1:y + 1, x] = TIE    # the ties (gaskets) round the roll
if os.environ.get('FURLED', 'roll') == 'roll':
    for y, (x0, x1) in ((int(10 + S), (21, 43)), (int(17 + S), (13, 51))): roll(yard, y, x0, x1)
    furled = np.zeros((64, 64), int)
else:                                                           # v3: the sails struck, dropped in a heap behind the head
    for y, (x0, x1) in ((int(9 + S), (20, 44)), (int(14 + S), (16, 48))): yard[y, x0:x1] = YARD
    furled = move(R['sails'], dy=S, sx=0.85, sy=E('FURL', 0.45), pivot=(31.5, 31))
a6 = close_gaps(stack([furled, move(R['body'], dy=S, sx=1.06, pivot=(31.5, 46)),
                       move(R['legL'], dx=-2), move(R['legR'], dx=2),
                       move(R['head'], dy=S + E('HEADLOW', 3), sx=0.96, sy=0.94, pivot=(31.5, 42))]))
a6 = stack([yard, a6, move(R['mastflag'], dy=S)])            # mast and yards after the gap filling (it would fill between the yards)
# --- 7: the roar
U = E('REAR', 3)
a7 = stack([move(O['sails'], dy=-1, sx=E('SAILX', 1.18), sy=E('SAILY', 1.12), pivot=(31.5, 8)), move(O['mastflag'], dy=-1),
            move(O['body'], dy=-U, sx=1.06, pivot=(31.5, 46)),
            move(O['legR'], dx=2),
            move(O['head'], dy=-U - E('HEADUP', 3), sy=1.06, pivot=(31.5, 40)),
            move(O['legL'], dx=E('PAWX', 9), dy=E('PAWY', -11), rot=E('PAWROT', 25), pivot=(12, 57))])
a7 = close_gaps(a7)
for name, a in (('anticip', a6), ('roar', a7), ('rest', rest), ('roar_v2src', roar)):
    np.save(os.path.join(OD, name + '_idx.npy'), a.astype(np.uint8))
    im = Image.fromarray(rgba(a, PAL)); im.save(os.path.join(OD, name + '.png'))
    bg = Image.new('RGBA', im.size, (40, 44, 60, 255)); bg.alpha_composite(im); bg.convert('RGB').resize((512, 512), Image.NEAREST).save(os.path.join(OD, name + '_8x.png'))
print('ok', OD)
