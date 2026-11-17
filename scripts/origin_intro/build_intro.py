"""Replace the Ho-Oh flight in HG's opening (gs_opening a/2/6/2 members 23/24/26; 25 = animation kept as is)."""
import numpy as np, struct, sys
from PIL import Image
sys.path.insert(0,'.')
from g2d import *; from lz import lz10_enc
from narc import unpack, pack
SIZES=[(64,64),(64,32),(32,64),(32,32),(32,16),(16,32),(16,16),(32,8),(8,32),(16,8),(8,16),(8,8)]
INV={v:k for k,v in SHAPE.items()}
idx=np.load('art/idx.npy')            # -1 transparent, else palette index 0..14
pal=np.load('art/pal_front.npy')
ih,iw=idx.shape
CW,CH=128,104
ox=(CW-iw)//2; oy=CH-ih
canvas=np.full((CH,CW),-1); canvas[oy:oy+ih,ox:ox+iw]=idx
ORX,ORY=64,60                       # canvas pixel that sits at the sprite position (cell 0,0)
# --- sail mask (image coords: rows <= 44, x >= 70)
sail=np.zeros_like(canvas,bool); sail[:oy+45, ox+70:]=True; sail&=canvas>=0
body=np.where(sail,-1,canvas)
def phase_img(k,nph=4):
    out=np.full_like(canvas,-1)
    ys,xs=np.where(sail)
    top=ys.min(); bot=oy+44
    for y in range(top,bot+1):
        a=1.6*(bot-y)/(bot-top+1e-9)
        sh=int(round(a*np.sin(2*np.pi*k/nph+0.45*y)))
        row=np.where(sail[y],canvas[y],-1)
        out[y]=np.roll(row,sh) if sh else row
    return out
NPH=4
phases=[phase_img(k,NPH) for k in range(NPH)]
FRAME_PHASE=[0,1,2,3,2,1]
FRAME_DY=[0,-1,-2,-2,-1,0]
def tiles_of(img,x,y,w,h):
    out=[]
    for ty in range(y,y+h,8):
        for tx in range(x,x+w,8):
            t=img[ty:ty+8,tx:tx+8]
            out.append(np.where(t>=0,t+1,0))
    return out
def nonempty(img,x,y,w,h): return (img[y:y+h,x:x+w]>=0).any()
def cover(img,x,y,w,h,pen=24):
    """best decomposition of block into OAMs: list of (x,y,w,h)"""
    if not nonempty(img,x,y,w,h): return []
    cost_full=(w*h)//64+pen; best=[(x,y,w,h)]; bc=cost_full
    if w>8 or h>8:
        if w>=h and w>8: parts=[(x,y,w//2,h),(x+w//2,y,w//2,h)]
        else: parts=[(x,y,w,h//2),(x,y+h//2,w,h//2)]
        if all((p[2],p[3]) in INV for p in parts):
            sub=[]; c=0
            for p in parts:
                s=cover(img,*p,pen=pen); sub+=s; c+=sum(q[2]*q[3]//64+pen for q in s)
            if c<bc: best,bc=sub,c
    return best
def layout(img,bx0,by0,bx1,by1):
    oams=[]
    y=by0
    for (y0,hh) in [(by0+k,min(64,by1-(by0+k))) for k in range(0,by1-by0,64)]:
        # split height into valid sizes
        rem=hh; yy=y0
        while rem>0:
            h=64 if rem>=64 else 32 if rem>=32 else 16 if rem>=16 else 8
            for x0 in range(bx0,bx1,64):
                w=min(64,bx1-x0)
                ws=64 if w>=64 else 32 if w>=32 else 16 if w>=16 else 8
                xx=x0
                while xx<x0+w:
                    ww=min(ws,x0+w-xx); ww=64 if ww>=64 else 32 if ww>=32 else 16 if ww>=16 else 8
                    hb=h
                    if (ww,hb) not in INV:
                        hb=min(hb,ww*2); ww=min(ww,hb*2)
                    oams+=cover(img,xx,yy,ww,hb)
                    xx+=ww
            yy+=h; rem-=h
    return oams
body_oams=layout(body,0,0,CW,CH)
sys_=np.where(np.any([p>=0 for p in phases],axis=0))
sx0,sx1=sys_[1].min()//8*8,(sys_[1].max()//8+1)*8; sy0,sy1=sys_[0].min()//8*8,(sys_[0].max()//8+1)*8
union=np.where(np.any([p>=0 for p in phases],axis=0),0,-1)
sail_oams=layout(union,sx0,sy0,sx1,sy1)
print('body oams',len(body_oams),'sail oams',len(sail_oams))
# --- tiles
gs=unpack(open('../rc8/x_rc8/files/a/2/6/2','rb').read())
cg=read_ncgr(lz10_dec(gs[24]))
SUN_TILES=16
tiledata=bytearray(cg['data'][:SUN_TILES*32])
def put_tiles(tl):
    start=len(tiledata)//32
    for t in tl:
        for row in t:
            for k in range(0,8,2): tiledata.append(int(row[k])|int(row[k+1])<<4)
    return start
body_t=[(o,put_tiles(tiles_of(body,*o))) for o in body_oams]
phase_t=[[(o,put_tiles(tiles_of(p,*o))) for o in sail_oams] for p in phases]
ntiles=len(tiledata)//32
print('tiles total',ntiles,'(Ho-Oh file had',len(cg['data'])//32,')')
# --- NCGR
hdr=bytearray(lz10_dec(gs[24])[:16+32])
rahc_size=32+len(tiledata)
struct.pack_into('<I',hdr,8,16+rahc_size); struct.pack_into('<I',hdr,16+4,rahc_size); struct.pack_into('<I',hdr,16+24,len(tiledata))
ncgr=bytes(hdr)+bytes(tiledata)
# --- NCER
old=read_ncer(lz10_dec(gs[26]))
def oam(x,y,w,h,tile,palno=1):
    shp,sz=INV[(w,h)]
    return struct.pack('<HHH',(shp<<14)|(y&255),(sz<<14)|(x&511),(palno<<12)|tile)
cells=[]
c0=old['cells'][0]; cells.append((c0['attr'],c0['bbox'],[struct.pack('<HHH',o['a0'],o['a1'],o['a2']) for o in c0['oams']]))
for f in range(6):
    dy=FRAME_DY[f]; ol=[]; xs=[];ys=[]
    for (x,y,w,h),t in phase_t[FRAME_PHASE[f]]+body_t:
        X=x-ORX; Y=y-ORY+dy; ol.append(oam(X,Y,w,h,t)); xs+=[X,X+w-1]; ys+=[Y,Y+h-1]
    bb=(max(xs),max(ys),min(xs),min(ys))
    r=int(np.ceil(max(np.hypot(a,b) for a in (bb[0],bb[2]) for b in (bb[1],bb[3]))/4))
    cells.append((0x900|min(r,0x3f),bb,ol))
kb=bytearray(b'KBEC'+b'\0'*4+struct.pack('<HHIIII',len(cells),1,0x18,0,0,0)+b'\0'*4)
table=bytearray(); oamb=bytearray()
for attr,bb,ol in cells:
    table+=struct.pack('<HHI4h',len(ol),attr,len(oamb),*bb); oamb+=b''.join(ol)
kb+=table+oamb
while len(kb)%4: kb+=b'\0'
struct.pack_into('<I',kb,4,len(kb))
_,_,osecs=sections(lz10_dec(gs[26]))
rest=osecs[b'LBAL'][1]+osecs[b'TXEU'][1]
ncer=b'RECN'+struct.pack('<HHIHH',0xFEFF,0x0100,16+len(kb)+len(rest),16,3)+bytes(kb)+rest
# --- NCLR: palette 1 = transparent + our 15 colours
cl=bytearray(lz10_dec(gs[23]) if gs[23][0]==0x10 else gs[23])
_,_,ps=sections(bytes(cl)); po=ps[b'TTLP'][0]; base=po+8+struct.unpack_from('<I',cl,po+20)[0]
for i,c in enumerate(pal):
    v=(int(c[0])>>3)|(int(c[1])>>3)<<5|(int(c[2])>>3)<<10
    struct.pack_into('<H',cl,base+2*(17+i),v)
gs[23]=bytes(cl); gs[24]=lz10_enc(ncgr); gs[26]=lz10_enc(ncer)
assert lz10_dec(gs[24])==ncgr and lz10_dec(gs[26])==ncer
open('out_a262.narc','wb').write(pack(gs))
# preview of the six cells
prev=Image.new('RGBA',(6*140,130),(90,150,220,255))
P=[tuple(int(v) for v in c)+(255,) for c in pal]
for f in range(6):
    img=np.full((CH+8,CW),-1)
    for y in range(CH):
        for x in range(CW):
            v=phases[FRAME_PHASE[f]][y,x] if phases[FRAME_PHASE[f]][y,x]>=0 else body[y,x]
            if v>=0 and 0<=y+4+FRAME_DY[f]<CH+8: img[y+4+FRAME_DY[f],x]=v
    im=Image.new('RGBA',(CW,CH+8))
    px=im.load()
    for y in range(CH+8):
        for x in range(CW):
            if img[y,x]>=0: px[x,y]=P[img[y,x]]
    prev.alpha_composite(im,(f*140+6,10))
prev.resize((prev.width*2,prev.height*2),Image.NEAREST).save('art/cells_preview.png')
print('ok')
