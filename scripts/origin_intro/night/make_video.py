"""Record opening scene 1 from two ROMs (every frame) and write a side-by-side mp4 and a gif of the new bottom screen.
python night/make_video.py OLD.nds NEW.nds OUT_BASENAME [first_frame] [n_frames]"""
import sys, os, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw
old, new, outb = sys.argv[1], sys.argv[2], sys.argv[3]
F0 = int(sys.argv[4]) if len(sys.argv) > 4 else 380
N = int(sys.argv[5]) if len(sys.argv) > 5 else 640
HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(HERE, 'video_tmp')
PY = os.path.expanduser('~/sigma-toolchain/venv312/bin/python')
DRIVE = os.path.join(HERE, '..', '..', 'lw', 'drive.py')
script = f'wait:{F0}' + ''.join(f',shot:f{i:04d},wait:1' for i in range(N))
for tag, rom in (('a', old), ('b', new)):
    subprocess.run([PY, DRIVE, rom, os.path.join(TMP, tag), script], check=True, capture_output=True)
S = 2
vw = cv2.VideoWriter(outb + '.mp4', cv2.VideoWriter_fourcc(*'avc1'), 60, (2 * 256 * S + 24, 384 * S + 40))
if not vw.isOpened():
    vw = cv2.VideoWriter(outb + '.mp4', cv2.VideoWriter_fourcc(*'mp4v'), 60, (2 * 256 * S + 24, 384 * S + 40))
gif = []
for i in range(N):
    a = Image.open(os.path.join(TMP, 'a', f'f{i:04d}.png')).convert('RGB')
    b = Image.open(os.path.join(TMP, 'b', f'f{i:04d}.png')).convert('RGB')
    canvas = Image.new('RGB', (2 * 256 * S + 24, 384 * S + 40), (24, 24, 28))
    canvas.paste(a.resize((256 * S, 384 * S), Image.NEAREST), (8, 32))
    canvas.paste(b.resize((256 * S, 384 * S), Image.NEAREST), (16 + 256 * S, 32))
    d = ImageDraw.Draw(canvas)
    d.text((8, 8), os.environ.get('LABEL_A', 'Origin HG (Ho-Oh)'), fill=(220, 220, 220))
    d.text((16 + 256 * S, 8), os.environ.get('LABEL_B', 'Sigma: Sabertann, tropisk natt'), fill=(220, 220, 220))
    vw.write(cv2.cvtColor(np.asarray(canvas), cv2.COLOR_RGB2BGR))
    if i % 2 == 0: gif.append(b.crop((0, 192, 256, 384)))
vw.release()
gif[0].save(outb + '.gif', save_all=True, append_images=gif[1:], duration=33, loop=0, optimize=True)
print('ok', outb)
