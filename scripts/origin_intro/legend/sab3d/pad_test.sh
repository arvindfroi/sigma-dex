#!/bin/zsh
# discriminating test: X1's film (sky textures 212.8 KB + Ho-Oh's old pagoda, worked) with 24 KB of zeros appended to the
# pagoda members' decompressed data: same texture VRAM, more RAM. Pagoda fails -> RAM (heap) limit; works -> VRAM limit.
set -e
cd ~/sigma-origin/title3d; Y=~/sigma-origin/legend_test/y; L=~/sigma-origin/legend_test; PY2=~/sigma-toolchain/venv312/bin/python
$PY2 - <<'PYEOF'
import sys, os
sys.path.insert(0, os.path.expanduser('~/sigma-origin/title3d')); sys.path.insert(0, os.path.expanduser('~/sigma-origin/title3d/legend'))
from narc import unpack, pack
from lz11 import lz11_dec
from lz import lz10_enc
def lz10_dec(src):
    n = int.from_bytes(src[1:4], 'little'); out = bytearray(); i = 4
    while len(out) < n:
        fl = src[i]; i += 1
        for b_ in range(8):
            if len(out) >= n: break
            if fl & (0x80 >> b_):
                v = src[i] << 8 | src[i + 1]; i += 2; ln = (v >> 12) + 3; ds = (v & 0xfff) + 1
                for _ in range(ln): out.append(out[-ds])
            else: out.append(src[i]); i += 1
    return bytes(out)
Y = os.path.expanduser('~/sigma-origin/legend_test/y/')
F = unpack(open(Y + 'a243_x1', 'rb').read())
for i in (15, 19, 23):
    raw = F[i]; d = lz11_dec(raw) if raw[:1] == b'\x11' else lz10_dec(raw); F[i] = lz10_enc(d + bytes(24576))
open(Y + 'a243_pad', 'wb').write(pack(F)); print('padded')
PYEOF
OUT=$($PY2 legend/relocate.py $L/base_hover.nds $Y/a243_orig $Y/a243_pad $L/jump_hooh2_pad.nds); echo $OUT
NS=$(echo $OUT | sed -E 's/.*-> (0x[0-9a-f]+) \(([0-9]+) bytes\).*/\1/'); NL=$(echo $OUT | sed -E 's/.*-> (0x[0-9a-f]+) \(([0-9]+) bytes\).*/\2/')
P=$($PY2 legend/grav3d/fat_pokes.py 0x023BFDB8 $NS $(printf '0x%x' $(( NS + NL ))))
cd $L; S="$P,wait:20,R,R,R,U,U,R,R,U,U,L,U,R,R,wait:180"
for i in $(seq 0 2100); do if [ $i -ge 1960 ] && [ $((i % 10)) -eq 0 ]; then S="$S,shot:f$(printf %04d $i),wait:1"; else S="$S,wait:1"; fi; [ $((i % 36)) -eq 35 ] && [ $i -lt 600 ] && S="$S,A"; done
rm -rf rec_pad; timeout 3000 $PY2 ../lw/drive.py jump_hooh2_pad.nds rec_pad "$S" --load ../lw/g7.dst >/dev/null 2>&1; ls rec_pad | wc -l
