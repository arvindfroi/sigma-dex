"""Dump overworld sprites from a/0/8/1 (BTX0 textures) to PNG, all frames side by side, x4 (local only).
python legend/dump_ow.py NARC OUTDIR MEMBER..."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from narc import unpack
from g2d import lz10_dec
import nitro, numpy as np
from PIL import Image
from dump import decode
F = unpack(open(sys.argv[1], 'rb').read()); OUT = sys.argv[2]; os.makedirs(OUT, exist_ok=True)
for m in map(int, sys.argv[3:]):
    d = F[m]; d = lz10_dec(d) if d[:1] == b'\x10' else d
    o = [nitro.u32(d, 16 + 4 * k) for k in range(nitro.u16(d, 14))][0]
    t = nitro.read_tex(d, o)
    ims = []
    for x in t['texs']:
        p = t['pals'][0]; im = decode(x, t['paldata'][p['off']:], x['c0']); ims.append(im); im.save(os.path.join(OUT, f"{m}_{x['name']}.png"))
    W = sum(i.width for i in ims) + 4 * (len(ims) - 1); sheet = Image.new('RGBA', (W, 64), (40, 40, 60, 255)); xx = 0
    for i in ims: sheet.alpha_composite(i, (xx, 0)); xx += i.width + 4
    sheet.resize((W * 4, 256), Image.NEAREST).save(os.path.join(OUT, f'{m}_sheet.png'))
    print(m, [p['name'] for p in t['pals']], [(x['name'], x['c0']) for x in t['texs']])
