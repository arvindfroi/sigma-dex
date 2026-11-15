"""Albedo + object-space normal bakes -> a DS texture: our own light (a sun from above-front-left plus ambient, in the
model's Blender frame), reduced to TS px and snapped to a fixed palette (default: Sabertann's DS front sprite colours),
so red, gold, black and white stay clean. python shade_tex.py BASE OUT.png [TS=128] [PAL_SPRITE]"""
import sys, numpy as np
from PIL import Image
B, OUT = sys.argv[1:3]; TS = int(sys.argv[3]) if len(sys.argv) > 3 else 128
PS = sys.argv[4] if len(sys.argv) > 4 else '/Users/arvind/Sigma pokemon pc port attempt/assets/sprites-ds/sabertann/front.png'
al = np.asarray(Image.open(B + '_albedo.png').convert('RGBA')).astype(float) / 255
nm = np.asarray(Image.open(B + '_normal.png').convert('RGB')).astype(float) / 255 * 2 - 1
lin = lambda c: np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
srgb = lambda c: np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(np.clip(c, 0, 1), 1 / 2.4) - 0.055)
L = np.array([-0.35, -0.55, 0.75]); L /= np.linalg.norm(L)      # Blender frame: model faces -Y; light from front-left-above
nd = np.clip((nm * L).sum(-1), 0, 1)
shade = 0.42 + 0.75 * nd
col = srgb(np.clip(lin(al[..., :3]) * shade[..., None] * 1.25, 0, 1))
img = Image.fromarray((col * 255).astype(np.uint8)).resize((TS, TS), Image.BOX)
pa = np.asarray(Image.open(PS).convert('RGBA')); pal = np.unique(pa[pa[..., 3] > 0][:, :3], axis=0).astype(float)[:15]
a = np.asarray(img).astype(float)
def to_lab(c):
    c = c / 255.0; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089]); f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
idx = ((to_lab(a)[..., None, :] - to_lab(pal)[None, None]) ** 2).sum(-1).argmin(-1)
q = pal[idx].astype(np.uint8)
Image.fromarray(q).save(OUT); np.save(OUT.replace('.png', '_idx.npy'), idx + 1); np.save(OUT.replace('.png', '_pal.npy'), pal)
print('palette', len(pal))
