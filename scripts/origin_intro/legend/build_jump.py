"""Test ROM (local only): bedroom stairs -> 1F frame script warps to a legend map, whose header gets a frame-table
entry that starts the cutscene script at once. Written into the savestate's ROM without moving the NARC.
python legend/build_jump.py ROM_IN ROM_OUT ZONE X Z DEST_HDR DEST_SCRIPT_ID VAR VAL [extra make_jump args...]"""
import sys, os, struct, subprocess; sys.path.insert(0, '.')
from narc import unpack, pack
ROM_IN, ROM_OUT, ZONE, X, Z, HDR, SID, VAR, VAL = sys.argv[1:10]; extra = sys.argv[10:]
Y = os.path.expanduser('~/sigma-origin/legend_test/y'); orig = f'{Y}/a012_orig'; tmp = f'{Y}/a012_tmp'
F = unpack(open(os.environ.get('JUMP_BASE', orig), 'rb').read())
# 1F (zone 60: hdr 617, scripts 842): frame table -> jump script
code = struct.pack('<HHH', 41, 0x4000, 1)
for a in [f'{VAR}={VAL}'] + extra:
    if '=' in a: v, val = a.split('='); code += struct.pack('<HHH', 41, int(v, 0), int(val, 0))
    elif a[0] == '+': code += struct.pack('<HH', 30, int(a[1:], 0))
    elif a[0] == '-': code += struct.pack('<HH', 31, int(a[1:], 0))
code += struct.pack('<HHHHHH', 176, int(ZONE), 0, int(X), int(Z), 0) + struct.pack('<H', 2)
F[842] = struct.pack('<i', 2) + struct.pack('<H', 0xFD13) + code
F[617] = bytes([1]) + struct.pack('<i', 1) + bytes([0]) + struct.pack('<HHHH', 0x4000, 0, 1, 0)
# destination header: keep its fixed entries, add a frame table VAR==VAL -> SID
h = F[int(HDR)]; fixed = b''; i = 0
while h[i] != 0:
    if h[i] == 1: i += 5; continue                      # drop its own frame table
    fixed += h[i:i + 5]; i += 5
F[int(HDR)] = fixed + bytes([1]) + struct.pack('<i', 1) + bytes([0]) + struct.pack('<HHHH', int(VAR, 0), int(VAL), int(SID), 0)
new = pack(F); old = open(orig, 'rb').read(); assert len(new) <= len(old), (len(new), len(old))
open(tmp, 'wb').write(new)
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'inplace.py'), ROM_IN, orig, tmp, ROM_OUT], check=True)
