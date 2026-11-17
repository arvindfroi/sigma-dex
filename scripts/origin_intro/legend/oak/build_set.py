"""The full Oak-intro set for one hop choice: a/1/2/0 with the stand (cell 0) and the chosen hop (cell 1), plus the two
per-outfit copies (data/clothes1/a120.narc, data/clothes2/a120.narc) with the same members 63 and 64.
python build_set.py CELLDIR TAG   -> final/a120_lapper_TAG.bin, final/a120_clothes{1,2}_lapper_TAG.bin (+ SHA256SUMS)"""
import sys, os, subprocess, hashlib
H = os.path.dirname(os.path.abspath(__file__)); F = os.path.join(H, '..', 'final')
cd, tag = sys.argv[1:3]
PY = [sys.executable]
a120 = os.path.join(F, 'a120_lapper_%s.bin' % tag)
subprocess.run(PY + [os.path.join(H, 'build_a120.py'), cd + '/cell0.png', cd + '/cell1.png', a120], check=True)
subprocess.run(PY + [os.path.join(H, 'verify_a120.py'), a120, cd + '/cell0.png', cd + '/cell1.png'], check=True)
subprocess.run(PY + [os.path.join(H, 'clothes_a120.py'), a120, F, 'lapper_' + tag], check=True)
with open(os.path.join(F, 'SHA256SUMS'), 'a') as s:
    for n in ('a120_lapper_%s.bin', 'a120_clothes1_lapper_%s.bin', 'a120_clothes2_lapper_%s.bin'):
        p = os.path.join(F, n % tag); s.write('%s  %s\n' % (hashlib.sha256(open(p, 'rb').read()).hexdigest(), n % tag)); print(n % tag)
