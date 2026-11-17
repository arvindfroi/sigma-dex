import numpy as np, cv2
from PIL import Image
src='/Users/arvind/Sigma pokemon pc port attempt/assets/concept-art/sabertann/624.webp'
im=np.array(Image.open(src).convert('RGB')).astype(int)
H,W,_=im.shape
r,g,b=im[...,0],im[...,1],im[...,2]
white=((r>232)&(g>232)&(b>232)).astype(np.uint8)
n,lab=cv2.connectedComponents(white,connectivity=4)
border=set(np.unique(np.r_[lab[0],lab[-1],lab[:,0],lab[:,-1]]))-{0}
bg=np.isin(lab,list(border))
brown=(r>70)&(r<200)&(g>40)&(g<140)&(b<100)&(r-b>35)&(r>g)
yy,xx=np.mgrid[:H,:W]
rock=brown&(yy>1150)
fg=(~bg&~rock).astype(np.uint8)
fg=cv2.morphologyEx(fg,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
n,lab,stats,_=cv2.connectedComponentsWithStats(fg,connectivity=8)
order=np.argsort(stats[1:,cv2.CC_STAT_AREA])[::-1]+1
print('largest',[(int(i),int(stats[i,cv2.CC_STAT_AREA]),stats[i,:4].tolist()) for i in order[:8]])
keep=(lab==order[0])
np.save('art/keep.npy',keep)
out=np.zeros((H,W,4),np.uint8); out[...,:3]=im; out[...,3]=keep*255
ys,xs=np.where(keep); print('bbox',xs.min(),xs.max(),ys.min(),ys.max())
Image.fromarray(out[ys.min():ys.max()+1,xs.min():xs.max()+1]).save('art/cut.png')
