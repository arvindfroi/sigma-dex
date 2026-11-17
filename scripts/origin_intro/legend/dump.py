"""Legend cutscene archive a/1/7/4 (pret files/demo/legend): list every file and decode every texture to PNG (local only).
python legend/dump.py NARC OUTDIR"""
import sys, os, struct, numpy as np
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from narc import unpack
import nitro
def bgr(v): return ((v & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, ((v >> 10) & 31) * 255 // 31)
def decode(t, pal, c0):
    w, h, f, d = t['w'], t['h'], t['fmt'], t['data']
    a = np.frombuffer(d, np.uint8); img = np.zeros((h * w, 4), np.uint8)
    P = lambda i: bgr(struct.unpack_from('<H', pal, 2 * i)[0]) if 2 * i + 2 <= len(pal) else (255, 0, 255)
    if f in (2, 3, 4):
        if f == 4: ix = a
        elif f == 3: ix = np.stack([a & 15, a >> 4], 1).reshape(-1)
        else: ix = np.stack([a & 3, (a >> 2) & 3, (a >> 4) & 3, a >> 6], 1).reshape(-1)
        for k, i in enumerate(ix[:w * h]): img[k] = (*P(int(i)), 0 if (c0 and i == 0) else 255)
    elif f in (1, 6):
        ib = 5 if f == 1 else 3
        for k, v in enumerate(a[:w * h]):
            i = v & ((1 << ib) - 1); al = v >> ib; al = al * 255 // ((1 << (8 - ib)) - 1)
            img[k] = (*P(int(i)), al)
    elif f == 7:
        v = np.frombuffer(d, '<u2')
        for k, x in enumerate(v[:w * h]): img[k] = (*bgr(int(x)), 255 if x & 0x8000 else 0)
    else: return None
    return Image.fromarray(img.reshape(h, w, 4))
def main():
  SRC, OUT = sys.argv[1:3]; os.makedirs(OUT, exist_ok=True)
  F = unpack(open(SRC, 'rb').read())
  for i, d in enumerate(F):
      if d[:1] == b'\x10':
          from g2d import lz10_dec; d = lz10_dec(d)
      st = d[:4]
      line = f'{i:3d} {st!r} {len(d)}'
      if st in (b'BMD0', b'BTX0'):
          offs = [nitro.u32(d, 16 + 4 * k) for k in range(nitro.u16(d, 14))]
          for o in offs:
              if d[o:o + 4] == b'TEX0':
                  t = nitro.read_tex(d, o)
                  line += ' TEX ' + ', '.join(f"{x['name']}:{x['fmt']}:{x['w']}x{x['h']}" for x in t['texs']) + ' PAL ' + ','.join(p['name'] for p in t['pals'])
                  for x in t['texs']:
                      pn = [p for p in t['pals'] if p['name'].startswith(x['name'])] or t['pals'][:1]
                      if not pn: continue
                      im = decode(x, t['paldata'][pn[0]['off']:], x['c0'])
                      if im: im.save(os.path.join(OUT, f"{i:02d}_{x['name']}.png"))
      print(line)

if __name__ == '__main__': main()
