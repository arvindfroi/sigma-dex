"""Arvind: Sabertann has no tail (the turnaround sheet drew one). Paint it out of the side view (and its mirror)
before Hunyuan sees it. python mv/no_tail.py VIEWDIR   (side.png -> side.png, side_mirror.png; keeps side_tail.png)"""
import sys, os, numpy as np
from PIL import Image
d = sys.argv[1]
src = os.path.join(d, 'side_tail.png')
if not os.path.exists(src): os.replace(os.path.join(d, 'side.png'), src)
a = np.array(Image.open(src).convert('RGB')).astype(int)
H, W, _ = a.shape
yy, xx = np.mgrid[0:H, 0:W]
dark = a.sum(-1) < 260                        # the tail is black; the stern ornament above it is gold, its teeth white
rump = ((xx - 735) / 52.0) ** 2 + ((yy - 752) / 82.0) ** 2 < 1        # the thigh's round back, where the tail sat
cut = (xx > 755) & (yy > 690) & ~rump
cut &= dark | (yy > 705)                                            # above 705 only the black tail goes, not the gold
a[cut] = 255
Image.fromarray(a.astype(np.uint8)).save(os.path.join(d, 'side.png'))
Image.fromarray(a[:, ::-1].astype(np.uint8)).save(os.path.join(d, 'side_mirror.png'))
print('tail pixels removed', int((cut & (a.sum(-1) < 700)).sum()))
