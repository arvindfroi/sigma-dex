"""Sabertann's field sprite (7 frames), eyes v2 (Arvind: grumpy but angry/focused, not flat): gold hat studs that read as
yellow eyes go; angry eyes under the brim with depth: lit brow ridge, brow sloping hard down to the nose, white with a
shaded lower part, black pupil looking ahead, dark lower lid. Rows are relative to the hat emblem ('a' gold at cols 31-32);
grids cover cols 24-31 of the left eye and are mirrored. python eyes_fix2.py VARIANT -> eyes2/f{n}_idx.npy"""
import sys, os, numpy as np
V = sys.argv[1]
K, N, D, M, L, G, A, W = 1, 2, 3, 5, 6, 9, 11, 15
CH = {'K': K, 'N': N, 'D': D, 'M': M, 'L': L, 'G': G, 'A': A, 'W': W, 'P': K}
GRID = {           # rows ny+3 .. ny+7, cols 24..31
 '1': ["MM......", "KKMM....", "NWKKKM..", "NAWPKK..", "DNGGNN.."],
 '2': ["MM......", "KKKMM...", "WWKKKKM.", "AWWPPK..", "NGGNNN.."],
 '3': [".MMM....", "KKKKMM..", "KWWKKKK.", "KAWPPWK.", ".NGGGNN."],
 '5': [".LLL....", "KKKKLL..", "KWWKKKK.", "KAWPPWK.", ".NGGGNN."],
 '4': ["LM......", "KKML....", "KWKKKM..", "KWWPKK..", "NGGNND.."],
}[V]
STUDS = [(0, 27), (0, 36), (1, 26), (1, 37), (2, 30), (2, 33)]
os.makedirs('eyes2', exist_ok=True)
for n in range(1, 8):
    a = np.load(f'f{n}_idx.npy').copy()
    ny = min(y for y in range(26, 38) if a[y, 31] == 10 and a[y, 32] == 10)
    for dy, c in STUDS:
        for cc in (c, 63 - c):
            if a[ny + dy, cc] == 14: a[ny + dy, cc] = 2
    for r, row in enumerate(GRID):
        for k, ch in enumerate(row):
            if ch == '.': continue
            c = 24 + k; a[ny + 3 + r, c] = CH[ch]; a[ny + 3 + r, 63 - c] = CH[ch]
    np.save(f'eyes2/f{n}_idx_{V}.npy', a)
