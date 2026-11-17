"""Which copy of a/1/2/0 does Oak's intro open? Hooks the archive path function (arm9 0x02007838, Thumb: archive id in
r0), logs ids 120 (a/1/2/0), 298 (clothes1/a120) and 299 (clothes2/a120) with the outfit inputs: the forcing bytes at
0x021CFCF0/1 and the save's outfit (r0 after the call at 0x0200786C). FORCE=n writes n to 0x021CFCF0 every frame from
frame FROM (n=2 -> clothes1, 3 -> clothes2), to test the copies (it swaps all 12 per-outfit archives and stalls the intro).
SAVE_OUTFIT_120=n makes the save's outfit read n only when archive 120 is opened (1 -> clothes1, 2 -> clothes2).
python clothes_probe.py ROM STATE KEYS_FILE FRAMES [OUTDIR_FOR_FRAMES FROM_FRAME]"""
import os, sys
os.environ["SDL_AUDIODRIVER"] = "dummy"
from desmume.emulator import DeSmuME
from desmume.controls import keymask, Keys
rom, state, kf, N = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
od = sys.argv[5] if len(sys.argv) > 5 else None; f0 = int(sys.argv[6]) if len(sys.argv) > 6 else 0
force = int(os.environ.get('FORCE', '0')); ffrom = int(os.environ.get('FROM', '0'))
keys = {}
for k in open(kf).read().strip().split(','):
    n, f = k.split('@'); keys[int(f)] = n
emu = DeSmuME(); emu.volume_set(0); emu.open(rom); emu.savestate.load_file(state)
R = emu.memory.register_arm9; frame = [0]; log = []; others = {}
cur = [0]; save_force = int(os.environ.get('SAVE_OUTFIT_120', '0'))
def on_path(addr, size):
    i = R.r0; cur[0] = i
    if i in (120, 298, 299):
        log.append((frame[0], i, emu.memory.unsigned[0x021CFCF0], emu.memory.unsigned[0x021CFCF1]))
    else: others[i] = others.get(i, 0) + 1
def on_save_outfit(addr, size):
    if save_force and cur[0] == 120 and frame[0] >= ffrom: R.r0 = save_force   # as if the save said this outfit, archive 120 only
    log.append((frame[0], 'save_outfit', R.r0))
emu.memory.register_exec(0x02007838, on_path); emu.memory.register_exec(0x0200786C, on_save_outfit)
if od: os.makedirs(od, exist_ok=True)
for f in range(N):
    frame[0] = f
    if force and f >= ffrom: emu.memory.write_byte(0x021CFCF0, force)
    if f in keys: emu.input.keypad_add_key(keymask(getattr(Keys, "KEY_" + keys[f])))
    if f - 6 in keys: emu.input.keypad_rm_key(keymask(getattr(Keys, "KEY_" + keys[f - 6])))
    emu.cycle(with_joystick=False)
    if od and f >= f0 and f % 2 == 0: emu.screenshot().save(f"{od}/f{f:05d}.png")
runs = []
for e in log:
    key = e[1:] if e[1] != 'save_outfit' else ('save_outfit', e[2])
    if runs and runs[-1][0] == key: runs[-1][2] = e[0]; runs[-1][3] += 1
    else: runs.append([key, e[0], e[0], 1])
for key, a, b, n in runs:
    if key[0] != 'save_outfit': print('frames %5d-%5d  archive %s (forcing bytes %s) x%d' % (a, b, key[0], key[1:], n))
outf = sorted({e[2] for e in log if e[1] == 'save_outfit'}); print('save outfit values seen:', outf)
