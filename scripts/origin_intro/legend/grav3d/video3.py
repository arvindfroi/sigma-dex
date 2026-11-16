"""Three recordings of Lugia's film stacked (Origin's Lugia, Gravriel, Gravriel + water colour), 3x, in step.
python video3.py OUT.mp4 START COUNT DIR1:OFF:LABEL DIR2:OFF:LABEL [DIR3:OFF:LABEL]"""
import sys, os, shutil, subprocess
from PIL import Image, ImageDraw
OUT, START, N = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); rows = [a.split(':') for a in sys.argv[4:]]
R = os.path.expanduser('~/sigma-origin/legend_test'); tmp = '/tmp/v3frames'; shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
W, H, LB = 512, 384, 22
for j in range(N):
    im = Image.new('RGB', (W, len(rows) * (H + LB)), 'white'); d = ImageDraw.Draw(im)
    for k, (dd, off, lab) in enumerate(rows):
        f = START + j + int(off); p = f'{R}/{dd}/f{f:04d}.png'
        if os.path.exists(p): im.paste(Image.open(p).convert('RGB').crop((0, 0, 256, 192)).resize((W, H), Image.NEAREST), (0, k * (H + LB) + LB))
        d.text((6, k * (H + LB) + 5), lab, fill='black')
    im.save(f'{tmp}/g{j:04d}.png')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', os.environ.get('FPS', '60'), '-i', f'{tmp}/g%04d.png', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', OUT], check=True)
print('ok', OUT)
