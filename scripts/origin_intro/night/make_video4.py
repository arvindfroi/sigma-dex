"""Opening scene 1 from several ROMs side by side (both screens), e.g. Lugia (SS), Ho-Oh (HG), Sabertann, Gravriel.
python night/make_video4.py OUT_BASENAME LABEL=ROM [LABEL=ROM ...]   (env F0 first frame, N frames, S scale)
Each ROM's recording is kept in night/video_tmp/<hash> and reused while the ROM file is unchanged.
The ROMs boot at different speeds (SoulSilver reaches scene 1 about 210 frames after HeartGold), so each recording
runs EXTRA frames longer. Each is shifted so the fade to white starts on the same video frame: SoulSilver's scene 1
waits longer and its Lugia shows for ~195 frames before the fade, Ho-Oh for ~106. So each recording is time-stretched
only before the creature appears: scene start and the creature's first frame land on HeartGold's frames; from there on
everything runs at normal speed (Lugia's fade then starts later than Ho-Oh's)."""
import sys, os, subprocess, hashlib
import numpy as np, cv2
from PIL import Image, ImageDraw
outb = sys.argv[1]; pairs = [a.split('=', 1) for a in sys.argv[2:]]
F0 = int(os.environ.get('F0', 380)); N = int(os.environ.get('N', 720)); S = float(os.environ.get('S', 1.5))
HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.expanduser('~/sigma-toolchain/venv312/bin/python')
DRIVE = os.path.join(HERE, '..', '..', 'lw', 'drive.py')
EXTRA = int(os.environ.get('EXTRA', 440)); NR = N + EXTRA
script = f'wait:{F0}' + ''.join(f',shot:f{i:04d},wait:1' for i in range(NR))
def marks(d):
    b = np.array([np.asarray(Image.open(os.path.join(d, f'f{i:04d}.png')).convert('L'), float)[:192].mean() for i in range(NR)])
    bb = np.array([np.asarray(Image.open(os.path.join(d, f'f{i:04d}.png')).convert('L'), float)[192:].mean() for i in range(NR)])
    first = int(np.argmax(b > 3)); base = bb[min(first + 300, NR - 1)]; fade = NR - 1
    for i in range(first + 300, NR):
        if bb[i] > base + 15: fade = i; break
    box = lambda i: np.asarray(Image.open(os.path.join(d, f'f{i:04d}.png')).convert('RGB'), float)[192 + 40:192 + 170, 80:176]
    r0 = max(first + 262, fade - 260); ref = box(r0)
    for i in range(r0, fade):          # the creature's first frame: the scene is still by then (scroll done)
        if (np.abs(box(i) - ref).sum(-1) > 60).sum() > 4: return first, i
    return first, fade
dirs = []
for label, rom in pairs:
    st = os.stat(rom); key = hashlib.sha1(f'{os.path.abspath(rom)}|{st.st_size}|{st.st_mtime}|{F0}|{NR}'.encode()).hexdigest()[:12]
    d = os.path.join(HERE, 'video_tmp', key)
    if not os.path.exists(os.path.join(d, f'f{NR - 1:04d}.png')):
        subprocess.run([PY, DRIVE, rom, d, script], check=True, capture_output=True)
    dirs.append((label, d, marks(d)))
ref = next((m for label, _, m in dirs if label.startswith('Ho-Oh')), dirs[0][2])   # (start, creature appears) of HeartGold
# ROMs built on HeartGold run its exact timing (and ours may show the creature earlier): no stretching for them
dirs = [(label, d, (ref if abs(m[0] - ref[0]) < 20 else m)) for label, d, m in dirs]
def src(m, i):
    (a, f), (ra, rf) = m, ref
    if i < ra: return max(0, a + i - ra)
    if i < rf: return int(round(a + (i - ra) * (f - a) / (rf - ra)))
    return min(NR - 1, f + i - rf)
for label, _, m in dirs: print(label, 'start/appears', m, 'speed %.2f' % ((m[1] - m[0]) / (ref[1] - ref[0])))
dirs = [(label + ('' if abs((m[1] - m[0]) / (ref[1] - ref[0]) - 1) < 0.05 else ' x%.1f' % ((m[1] - m[0]) / (ref[1] - ref[0]))), d, m) for label, d, m in dirs]
w, h = int(256 * S), int(384 * S); pad = 8
W = len(dirs) * (w + pad) + pad; H = h + 40
vw = cv2.VideoWriter(outb + '.mp4', cv2.VideoWriter_fourcc(*'avc1'), 60, (W, H))
if not vw.isOpened(): vw = cv2.VideoWriter(outb + '.mp4', cv2.VideoWriter_fourcc(*'mp4v'), 60, (W, H))
for i in range(N):
    canvas = Image.new('RGB', (W, H), (24, 24, 28)); dr = ImageDraw.Draw(canvas)
    for k, (label, d, m) in enumerate(dirs):
        im = Image.open(os.path.join(d, f'f{src(m, i):04d}.png')).convert('RGB').resize((w, h), Image.NEAREST)
        x = pad + k * (w + pad); canvas.paste(im, (x, 32)); dr.text((x, 10), label, fill=(220, 220, 220))
    vw.write(cv2.cvtColor(np.asarray(canvas), cv2.COLOR_RGB2BGR))
vw.release()
print('ok', outb + '.mp4')
