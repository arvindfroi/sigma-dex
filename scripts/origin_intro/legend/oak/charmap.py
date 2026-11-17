import sys, numpy as np
from PIL import Image
a = np.array(Image.open(sys.argv[1]).convert('RGBA'))
keys = [(0,0,0),(15,10,10),(51,25,14),(61,28,14),(78,35,15),(109,51,21),(197,60,68),(234,91,84),(207,170,144),(228,195,166),(242,217,188),(252,236,209)]
ch = 'ABCDEFGHIJKL'
for y in range(a.shape[0]):
    print('%2d ' % y + ''.join((ch[keys.index(tuple(int(v) for v in a[y, x, :3]))] if tuple(int(v) for v in a[y, x, :3]) in keys else '?') if a[y, x, 3] else '.' for x in range(a.shape[1])))
