"""Run a custom_jump test ROM from lw/g7.dst: walk down the bedroom stairs, wait for the warp and shoot the field a few
times (the figure's animation). Optional extra key steps after the warp. No sound.
python legend/custom_shots.py ROM OUTDIR [KEYS after the warp, e.g. 'U,U'] env SHOTS (8), GAP (frames, 20)"""
import os, sys
os.environ["SDL_AUDIODRIVER"] = "dummy"
from desmume.emulator import DeSmuME
from desmume.controls import keymask, Keys
ROM, OUT = sys.argv[1:3]; EXTRA = sys.argv[3] if len(sys.argv) > 3 else ''; os.makedirs(OUT, exist_ok=True)
emu = DeSmuME(); emu.volume_set(0); emu.open(ROM); emu.savestate.load_file(os.path.expanduser('~/sigma-origin/lw/g7.dst'))
K = {'U': Keys.KEY_UP, 'D': Keys.KEY_DOWN, 'L': Keys.KEY_LEFT, 'R': Keys.KEY_RIGHT, 'A': Keys.KEY_A, 'B': Keys.KEY_B}
def run(n):
    for _ in range(n): emu.cycle(with_joystick=False)
def step(k, hold=8, after=24):
    emu.input.keypad_add_key(keymask(K[k])); run(hold); emu.input.keypad_rm_key(keymask(K[k])); run(after)
run(30)
for k in 'UUUUUURU': step(k)
for k in 'RRR': step(k, 20)
run(240)
for k in [k for k in EXTRA.split(',') if k]: step(k, 8 if k in 'UDLR' else 6, 24)
run(60)
for i in range(int(os.environ.get('SHOTS', 8))):
    emu.screenshot().save(os.path.join(OUT, 'f%d.png' % i)); run(int(os.environ.get('GAP', 20)))
print('ok', OUT)
