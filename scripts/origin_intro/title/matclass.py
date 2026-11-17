"""Material classes of a title-clip picture by colour (Monarkhan v4, Arvind 2026-11-15: wing and spot colours looked wrong):
0 other, 1 red body, 2 yellow (wings), 3 brown spots, 4 pink (nose), 5 white (fangs, claws, eyes).
python title/matclass.py PIC.png OUT_preview.png   (as a module: classes(rgb) -> int array)"""
import sys, numpy as np
from PIL import Image
def classes(a):
    r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
    c = np.zeros(r.shape, int)
    c[(r > 45) & (r > 1.7 * g) & (b < r * 0.8)] = 1
    c[(r > 150) & (g > 105) & (b < 120) & (r - g < 95) & (g > 1.25 * b)] = 2
    c[(r > 60) & (r < 200) & (g > 30) & (g < 140) & (b < 90) & (r > g) & (g > b * 1.15) & (r - g < 90) & (r + g < 300)] = 3
    c[(r > 160) & (g > 80) & (g < 170) & (b > 90) & (b < 180) & (r - g > 35)] = 4
    c[(np.minimum(np.minimum(r, g), b) > 185)] = 5
    return c
if __name__ == '__main__':
    a = np.asarray(Image.open(sys.argv[1]).convert('RGB'))
    c = classes(a); col = np.array([(0, 0, 0), (200, 30, 30), (240, 200, 40), (120, 70, 20), (240, 140, 160), (255, 255, 255)], np.uint8)
    Image.fromarray(col[c]).resize((512, 384), Image.NEAREST).save(sys.argv[2]); print(np.bincount(c.ravel(), minlength=6))
