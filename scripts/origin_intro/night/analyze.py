import sys; sys.path.insert(0,'.')
from inventory import *
import collections
for i in (0,1,23):
    p,bd=read_nclr(D[i]); print('pal',i,'n',len(p),'bd',bd)
for i in (4,5,6,7):
    c=read_ncgr(D[i]); print('char',i,'bpp',c['bpp'],'ntiles',len(c['data'])//(32 if c['bpp']==4 else 64),'w,h',c['tiles_w'],c['tiles_h'],'map',hex(c['mapping']))
for i in (12,13,14,15,16,17,18):
    w,h,e=nscr(i); t=e&1023; pn=e>>12
    print('scr',i,w,h,'tiles',t.min(),t.max(),'uniq',len(set(t)),'pals',dict(collections.Counter(pn.tolist())), 'flips',int(((e>>10)&3).astype(bool).sum()))
