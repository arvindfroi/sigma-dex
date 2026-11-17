"""Dump the Oak-intro Marill set (a/1/2/0 members 63-66) and the other set 59-62: cells, animation, renders."""
import sys, json; sys.path.insert(0, '/Users/arvind/sigma-origin/title3d')
from narc import unpack
from g2d import read_ncer, read_nanr, read_ncgr, read_nclr
import numpy as np
from PIL import Image
SRC = '/Users/arvind/sigma-origin/rc8/x_rc8/files/a/1/2/0'
fs = unpack(open(SRC, 'rb').read())
def bgr(c): return ((c & 31) * 255 // 31, (c >> 5 & 31) * 255 // 31, (c >> 10 & 31) * 255 // 31)
for (pl, cg, ce, an) in [(59, 60, 61, 62), (63, 64, 65, 66)]:
    g = read_ncgr(fs[cg]); pal, bd = read_nclr(fs[pl]); c = read_ncer(fs[ce]); a = read_nanr(fs[an])
    print('SET', pl, cg, ce, an)
    print(' ncgr', {k: v for k, v in g.items() if k not in ('data', 'hdr')}, len(g['data']), 'bytes', len(g['data']) // 32, 'tiles')
    print(' nclr depth', bd, 'ncolors', len(pal))
    print(' ncer bank', c['bank'], 'map', c['mapping'], 'cells', len(c['cells']))
    for i, cell in enumerate(c['cells']):
        print('  cell', i, 'attr', hex(cell['attr']), 'bbox', cell['bbox'])
        for o in cell['oams']:
            print('    ', {k: o[k] for k in ('x', 'y', 'w', 'h', 'tile', 'pal', 'prio', 'hf', 'vf', 'aff', 'dbl', 'bpp8')})
    for si, s in enumerate(a['seqs']):
        print('  seq', si, {k: s[k] for k in ('nf', 'loop', 'el', 'at', 'pm')})
        for fr in s['frames']: print('     ', fr)
