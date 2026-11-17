import numpy as np, struct, os
from PIL import Image
from g2d import *
from narc import unpack
gs=unpack(open('../rc8/x_rc8/files/a/2/6/2','rb').read())
D=[lz10_dec(f) if f[0]==0x10 else f for f in gs]
def pal(i):
    p,_=read_nclr(D[i]); return np.array([((c&31)*255//31,(c>>5&31)*255//31,(c>>10&31)*255//31) for c in p],np.uint8)
def tiles(i):
    c=read_ncgr(D[i]); b=np.frombuffer(c['data'],np.uint8)
    if c['bpp']==4: px=np.stack([b&15,b>>4],1).reshape(-1)
    else: px=b
    return px.reshape(-1,8,8)
def nscr(i):
    mg,ver,s=sections(D[i]); o,sc=s[b'NRCS']; w,h,mode,fmt,sz=struct.unpack_from('<HHHHI',sc,8)
    e=np.array(struct.unpack_from(f'<{sz//2}H',sc,20)); return w,h,e
def render_bg(si,ci,pi,tile_off=0):
    w,h,e=nscr(si); T=tiles(ci); P=pal(pi)
    img=np.zeros((h,w,4),np.uint8)
    tw=w//8
    # screens >256 wide are stored as 256x256 blocks
    for k,v in enumerate(e):
        blk=k//1024; kk=k%1024
        bw=max(1,w//256); bx=(blk%bw)*32; by=(blk//bw)*32
        tx=bx+kk%32; ty=by+kk//32
        t=(v&1023)-tile_off
        if t<0 or t>=len(T): continue
        tl=T[t]
        if v&0x400: tl=tl[:,::-1]
        if v&0x800: tl=tl[::-1]
        pn=v>>12
        rgb=P[pn*16+tl]; a=np.where(tl>0,255,0)
        img[ty*8:ty*8+8,tx*8:tx*8+8,:3]=rgb; img[ty*8:ty*8+8,tx*8:tx*8+8,3]=a
    return Image.fromarray(img)
def render_cells(ci,pi,ei):
    T=tiles(ci); P=pal(pi); ce=read_ncer(D[ei]); out=[]
    for c in ce['cells']:
        if not c['oams']: out.append(None); continue
        xs=[o['x'] for o in c['oams']]+[o['x']+o['w'] for o in c['oams']]; ys=[o['y'] for o in c['oams']]+[o['y']+o['h'] for o in c['oams']]
        x0,y0=min(xs),min(ys); W,H=max(xs)-x0,max(ys)-y0
        img=np.zeros((H,W,4),np.uint8)
        for o in reversed(c['oams']):
            nt=(o['w']//8)*(o['h']//8); base=o['tile']
            for k in range(nt):
                if base+k>=len(T): continue
                tl=T[base+k]; tx=(k%(o['w']//8))*8; ty=(k//(o['w']//8))*8
                if o['hf']: tx=o['w']-8-tx; tl=tl[:,::-1]
                if o['vf']: ty=o['h']-8-ty; tl=tl[::-1]
                X=o['x']-x0+tx; Y=o['y']-y0+ty
                m=tl>0
                reg=img[Y:Y+8,X:X+8]
                reg[...,:3][m]=P[o['pal']*16+tl][m]; reg[...,3][m]=255
        out.append(Image.fromarray(img))
    return out
