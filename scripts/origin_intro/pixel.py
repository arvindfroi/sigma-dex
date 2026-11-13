import numpy as np, cv2
from PIL import Image
P="/Users/arvind/Sigma pokemon pc port attempt"
src=P+'/assets/concept-art/sabertann/624.webp'
im=np.array(Image.open(src).convert('RGB'))
keep=np.load('art/keep.npy').astype(np.uint8)
H,W=keep.shape
def er(x0,y0,x1,y1): keep[66+3*y0:66+3*y1,54+3*x0:54+3*x1]=0
er(0,397,500,500); er(40,365,118,500); er(262,352,305,393)
n,lab,st,_=cv2.connectedComponentsWithStats(keep,connectivity=8)
k=1+np.argmax(st[1:,cv2.CC_STAT_AREA]); keep=(lab==k)
ys,xs=np.where(keep); x0,x1,y0,y1=xs.min(),xs.max()+1,ys.min(),ys.max()+1
rgba=np.dstack([im,keep*255]).astype(np.uint8)[y0:y1,x0:x1]
Image.fromarray(rgba).save('art/cut2.png')
TH=int(__import__('sys').argv[1]) if len(__import__('sys').argv)>1 else 104
h,w=rgba.shape[:2]; s=TH/h; nw,nh=round(w*s),TH
# premultiplied area downscale
a=rgba[...,3:4]/255.0
pm=(rgba[...,:3]*a).astype(np.float32)
pm_s=cv2.resize(pm,(nw,nh),interpolation=cv2.INTER_AREA); a_s=cv2.resize(a.astype(np.float32),(nw,nh),interpolation=cv2.INTER_AREA)
col=np.where(a_s[...,None]>1e-3,pm_s/np.maximum(a_s[...,None],1e-3),0)
alpha=a_s>0.45
# palette from battle sprite
fr=np.array(Image.open(P+'/assets/sprites-ds/sabertann/front.png').convert('RGBA'))
cols=fr[fr[...,3]>0][:,:3]
pal=np.unique(cols,axis=0)
print('front sprite colours',len(pal))
np.save('art/pal_front.npy',pal)
# map in Lab
def lab(c): return cv2.cvtColor(c.reshape(-1,1,3).astype(np.uint8),cv2.COLOR_RGB2LAB).reshape(-1,3).astype(float)
L=lab(np.clip(col,0,255)); PL=lab(pal)
d=((L[:,None,:]-PL[None])**2).sum(-1); idx=d.argmin(1).reshape(nh,nw)
out=np.zeros((nh,nw,4),np.uint8); out[...,:3]=pal[idx]; out[...,3]=alpha*255
Image.fromarray(out).save('art/px.png')
big=Image.fromarray(out).resize((nw*4,nh*4),Image.NEAREST); bg=Image.new('RGBA',big.size,(90,150,220,255)); bg.alpha_composite(big); bg.save('art/px_x4.png')
print(nw,nh)
# --- crisp ink lines and outer outline
rgb=rgba[...,:3].astype(int)
ink=((rgb.sum(-1)<150)&(rgba[...,3]>0)).astype(np.float32)
ink_s=cv2.resize(ink,(nw,nh),interpolation=cv2.INTER_AREA)
lum=pal.astype(int).sum(1); dark=np.argmin(lum)
inkm=(ink_s>float(__import__('os').environ.get('INK','0.30')))&alpha
idx2=idx.copy(); idx2[inkm]=dark
# outer outline
A=alpha.astype(np.uint8)
er=cv2.erode(A,np.ones((3,3),np.uint8)); edge=(A==1)&(er==0)
idx2[edge]=dark
out=np.zeros((nh,nw,4),np.uint8); out[...,:3]=pal[idx2]; out[...,3]=alpha*255
np.save('art/idx.npy',np.where(alpha,idx2,-1))
Image.fromarray(out).save('art/px2.png')
big=Image.fromarray(out).resize((nw*4,nh*4),Image.NEAREST); bg=Image.new('RGBA',big.size,(90,150,220,255)); bg.alpha_composite(big); bg.save('art/px2_x4.png')
print('pal',pal.tolist(),'dark',dark)
