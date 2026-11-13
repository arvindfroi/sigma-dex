from PIL import Image, ImageDraw, ImageFont
import numpy as np, json
try:
    F=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',26); f2=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',18)
except: F=f2=None
W=1500
rows=[]
# row 1: model views
views=[Image.open(f'prev/view_{k}.png').convert('RGB') for k in ('intro','side','back')]
r1=Image.new('RGB',(W,500),(32,30,40))
for i,v in enumerate(views): r1.paste(v.resize((460,460)),(20+i*490,30))
rows.append(('3D-modellen (Blender, egen modell etter konseptkunsten, ca. 11 500 flater)',r1))
# row 2: rig
a=Image.open('rigv/rig_34.png').convert('RGB'); b=Image.open('rigv/rig_side.png').convert('RGB')
r2=Image.new('RGB',(W,520),(32,30,40)); r2.paste(a.resize((640,500)),(60,10)); r2.paste(b.resize((640,500)),(780,10))
d=ImageDraw.Draw(r2)
leg=[('grønn: rygg, bryst, hode',(0.2,0.9,0.3)),('gul: kjeve, hatt',(0.9,0.9,0.2)),('blå: skjold og master',(0.3,0.6,1)),('rosa: seilene',(1,0.3,0.8)),('turkis: flagget (3 ledd)',(0.4,1,1)),('oransje: halefinnen',(1,0.5,0.1)),('rød: fire bein, 3 ledd hver',(1,0.35,0.3))]
for i,(t,c) in enumerate(leg):
    y=14+i*24; d.rectangle((1430-260,y,1430-246,y+14),fill=tuple(int(v*255) for v in c)); d.text((1430-240,y-3),t,fill=(230,230,230),font=f2)
rows.append(('Riggen: 30 bein under ett rotbein (kan også brukes til 3D på tittelskjermen senere)',r2))
# row 3: pixel frames (base + anim composite) at 3x
P=np.array(json.load(open('px_base/pal.json'))['palette'],np.uint8)
base=np.array(Image.open('px_base/f1.png'))
fr=[]
for k in range(1,9):
    an=np.array(Image.open(f'px_anim/f{k}.png')); comp=np.where(an>0,an,base)
    rgb=P[comp]; rgb[comp==0]=(28,40,84); fr.append(Image.fromarray(rgb[0:130,30:168]))
r3=Image.new('RGB',(W,300),(32,30,40))
for i,im in enumerate(fr[:8]):
    r3.paste(im.resize((im.width*1,im.height*1)),(20+i*(im.width+44)//1 if False else 20+i*183,10))
r3b=Image.new('RGB',(W,420),(32,30,40))
for i,k in enumerate((0,2,4,6)):
    im=fr[k]; r3b.paste(im.resize((im.width*3//1,im.height*3//1),Image.NEAREST),(10+i*372,0))
rows.append(('Pikselbildene i spillet: 15 nattfarger (månelys, lysende kanonluker), 8 bilder i svømmeløkka, vist 3x',r3b))
H=sum(r.height+46 for _,r in rows)
out=Image.new('RGB',(W,H),(24,22,30)); dd=ImageDraw.Draw(out); y=0
for t,r in rows:
    dd.rectangle((0,y,W,y+40),fill=(60,50,90)); dd.text((14,y+6),t,fill=(255,255,255),font=F); y+=46
    out.paste(r,(0,y)); y+=r.height
out.save('/Users/arvind/Sigma pokemon pc port attempt/sabertann_3d_modell.png')
print(out.size)
