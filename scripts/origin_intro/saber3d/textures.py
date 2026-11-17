"""Textures for the 3D Sabertann (own drawings): sails, flag and hat emblem.
Flat key colours only, so the pixel step can tell the materials apart."""
from PIL import Image, ImageDraw
import math, os
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'tex')
INK=(12,12,16); GOLD=(224,176,48); WHITE=(216,220,232); BODY=(38,38,46)
def bone(d,x0,y0,x1,y1,w,col,ink,lw):
    # a bone from (x0,y0) to (x1,y1): shaft + two knuckles at each end
    ang=math.atan2(y1-y0,x1-x0); nx,ny=-math.sin(ang),math.cos(ang)
    r=w*0.62
    ends=[]
    for (x,y,s) in ((x0,y0,1),(x1,y1,-1)):
        for k in (-1,1):
            ends.append((x+nx*k*w*0.42+math.cos(ang)*s*r*0.2, y+ny*k*w*0.42+math.sin(ang)*s*r*0.2))
    for pass_ in (0,1):
        c=ink if pass_==0 else col; g=lw if pass_==0 else 0
        d.line((x0,y0,x1,y1),fill=c,width=int(w+2*g))
        for (ex,ey) in ends: d.ellipse((ex-r-g,ey-r-g,ex+r+g,ey+r+g),fill=c)
def skull(d,cx,cy,s,col=GOLD,ink=INK,lw=None,bones=True):
    lw=lw or max(2,int(s*0.06))
    if bones:
        L=s*1.15
        bone(d,cx-L,cy-L*0.55,cx+L,cy+L*0.75,s*0.24,col,ink,lw)
        bone(d,cx+L,cy-L*0.55,cx-L,cy+L*0.75,s*0.24,col,ink,lw)
    for pass_ in (0,1):
        c=ink if pass_==0 else col; g=lw if pass_==0 else 0
        d.ellipse((cx-s*0.62-g,cy-s*0.62-g,cx+s*0.62+g,cy+s*0.42+g),fill=c)          # cranium
        d.rounded_rectangle((cx-s*0.36-g,cy+s*0.1-g,cx+s*0.36+g,cy+s*0.72+g),radius=s*0.12,fill=c)  # jaw
    # eye sockets, nose, teeth
    for k in (-1,1):
        d.ellipse((cx+k*s*0.26-s*0.17,cy-s*0.12,cx+k*s*0.26+s*0.17,cy+s*0.2),fill=ink)
    d.polygon([(cx,cy+s*0.2),(cx-s*0.09,cy+s*0.36),(cx+s*0.09,cy+s*0.36)],fill=ink)
    for k in (-1,0,1):
        d.line((cx+k*s*0.13,cy+s*0.5,cx+k*s*0.13,cy+s*0.72),fill=ink,width=lw)
def sail(name,w,h,s,bones=True,dy=0.0):
    im=Image.new('RGB',(w,h),WHITE); d=ImageDraw.Draw(im)
    skull(d,w/2,h/2+dy*h,s,bones=bones)
    # hem: thin ink border so the sail edge reads
    d.rectangle((0,0,w-1,h-1),outline=INK,width=max(3,w//90))
    im.save(os.path.join(OUT,name))
os.makedirs(OUT,exist_ok=True)
sail('sail_main.png',512,400,118,True,-0.06)
sail('sail_rear.png',256,200,64,False,-0.02)
sail('flag.png',256,128,34,True,0.0)
# hat: black felt with gold trim band along the top edge is geometry; emblem is a decal
em=Image.new('RGBA',(256,256),(0,0,0,0)); d=ImageDraw.Draw(em)
# bold version so it still reads at ~10 px on the hat: thick crossbones, a round skull with big sockets
for (x0,y0,x1,y1) in ((40,70,216,216),(216,70,40,216)):
    d.line((x0,y0,x1,y1),fill=INK,width=58); d.line((x0,y0,x1,y1),fill=GOLD,width=36)
    for (x,y) in ((x0,y0),(x1,y1)):
        d.ellipse((x-30,y-30,x+30,y+30),fill=INK); d.ellipse((x-20,y-20,x+20,y+20),fill=GOLD)
d.ellipse((58,28,198,160),fill=INK); d.ellipse((70,40,186,148),fill=GOLD)
d.rounded_rectangle((88,120,168,186),radius=14,fill=INK); d.rounded_rectangle((98,120,158,176),radius=10,fill=GOLD)
d.ellipse((86,78,124,116),fill=INK); d.ellipse((132,78,170,116),fill=INK)
em.save(os.path.join(OUT,'hat_emblem.png'))
# stern skull plate: a pirate skull (same look as the one on the sails), drawn on the plate's front face
import sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skull_shape as SS
N=512
def P(x,y): return ((x+0.65)/1.3*N, (1-(y+0.65)/1.3)*N)
sp=Image.new('RGB',(N,N),GOLD); d=ImageDraw.Draw(sp)
RED=(142,26,28)
d.line([P(*q) for q in SS.outline()]+[P(*SS.outline()[0])],fill=INK,width=16,joint='curve')
for (cx,cy,rx,ry) in SS.SOCKETS:                       # round windows: red frame, dark glass, a gold cross bar
    box=lambda r: (P(cx-r,cy+r)[0],P(cx-r,cy+r)[1],P(cx+r,cy-r)[0],P(cx+r,cy-r)[1])
    d.ellipse(box(0.175),fill=INK); d.ellipse(box(0.15),fill=RED); d.ellipse(box(0.11),fill=INK)
    d.line((P(cx-0.11,cy),P(cx+0.11,cy)),fill=GOLD,width=8); d.line((P(cx,cy-0.11),P(cx,cy+0.11)),fill=GOLD,width=8)
d.polygon([P(*q) for q in SS.NOSE],fill=INK)
d.rounded_rectangle((P(-0.26,-0.31)[0],P(-0.26,-0.31)[1],P(0.26,-0.49)[0],P(0.26,-0.49)[1]),radius=12,fill=INK)
for k in range(6):                                   # big white teeth, upper and lower row
    x0=-0.24+0.08*k
    d.rounded_rectangle((P(x0+0.008,-0.32)[0],P(x0+0.008,-0.32)[1],P(x0+0.072,-0.395)[0],P(x0+0.072,-0.395)[1]),radius=5,fill=WHITE)
    d.rounded_rectangle((P(x0+0.008,-0.405)[0],P(x0+0.008,-0.405)[1],P(x0+0.072,-0.48)[0],P(x0+0.072,-0.48)[1]),radius=5,fill=WHITE)
sp.save(os.path.join(OUT,'skull_plate.png'))
print('ok')
