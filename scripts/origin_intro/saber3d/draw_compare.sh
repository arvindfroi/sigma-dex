#!/bin/zsh
# design check: the drawing pose at the drawing's angle, rendered to pixels (day and night colours), next to the drawing
cd "$(dirname "$0")"
B=/Applications/Blender.app/Contents/MacOS/Blender; PY="/Users/arvind/Sigma pokemon pc port attempt/.venv/bin/python"
cat model_head.py model_body.py > model.py
SAB_REST=1 $B -b --factory-startup -P model.py -- rest.blend > log_rest.txt 2>&1 || { tail -20 log_rest.txt; exit 1; }
SAB_WATER=-3 SAB_NOFOAM=1 SAB_YAW=60 SAB_EL=20 SAB_CW=6.4 SAB_CH=6.4 SAB_TZ=2.85 SAB_TX=0.3 SAB_LAYER=all $B -b rest.blend -P render_passes.py -- passes_draw 30 4 > log_draw.txt 2>&1
for th in day night; do SAB_THEME=$th "$PY" pixelize.py passes_draw px_draw_$th > /dev/null; done
"$PY" - "$1" <<'PYEOF'
import sys
from PIL import Image
import numpy as np, json
c=Image.open('/Users/arvind/Sigma pokemon pc port attempt/assets/concept-art/sabertann/624.webp').convert('RGB')
H=560; c=c.resize((int(c.width*H/c.height),H))
row=[c]
for th,bg in (('day',(255,255,255)),('night',(28,40,84))):
    P=np.array(json.load(open(f'px_draw_{th}/pal.json'))['palette'],np.uint8)
    a=np.array(Image.open(f'px_draw_{th}/f1.png')); rgb=P[a]; rgb[a==0]=bg
    ys,xs=np.where(a>0); im=Image.fromarray(rgb[max(0,ys.min()-2):ys.max()+3, max(0,xs.min()-2):xs.max()+3])
    row.append(im.resize((int(im.width*H/im.height),H),Image.NEAREST))
W=sum(r.width for r in row)+20; s=Image.new('RGB',(W,H),'white'); x=0
for r in row: s.paste(r,(x,0)); x+=r.width+10
s.save(sys.argv[1]); print(s.size)
PYEOF
