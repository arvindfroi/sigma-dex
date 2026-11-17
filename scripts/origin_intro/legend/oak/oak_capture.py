"""Boot a ROM with an empty battery, press keys on a schedule, save frames (both screens) and optional savestate.
usage: oak_capture.py ROM OUTDIR --frames N --every N [--keys 'START@1900,A@2100'] [--repeat KEY:FROM:PERIOD]
       [--load STATE] [--save STATE] [--from F]"""
import os, sys
os.environ["SDL_AUDIODRIVER"] = "dummy"
from desmume.emulator import DeSmuME
from desmume.controls import keymask, Keys
rom, out = sys.argv[1:3]; a = sys.argv[3:]
opt = lambda n, d=None: a[a.index(n) + 1] if n in a else d
N = int(opt("--frames", "3000")); every = int(opt("--every", "10")); start = int(opt("--from", "0"))
keys = {}
for k in (opt("--keys") or "").split(","):
    if k: name, f = k.split("@"); keys[int(f)] = name
if opt("--repeat"):
    name, f0, per = opt("--repeat").split(":")
    for f in range(int(f0), N, int(per)): keys.setdefault(f, name)
os.makedirs(out, exist_ok=True)
emu = DeSmuME(); emu.volume_set(0); emu.open(rom)
if opt("--load"): emu.savestate.load_file(opt("--load"))
for f in range(N):
    if f in keys: emu.input.keypad_add_key(keymask(getattr(Keys, "KEY_" + keys[f])))
    if f - 6 in keys: emu.input.keypad_rm_key(keymask(getattr(Keys, "KEY_" + keys[f - 6])))
    emu.cycle(with_joystick=False)
    if f >= start and f % every == 0: emu.screenshot().save(f"{out}/f{f:05d}.png")
if opt("--save"): emu.savestate.save_file(opt("--save"))
