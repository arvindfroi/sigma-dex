"""Per texture group (export_parts.py: albedo{g} + normal{g}): our light with a grey sheen so black fur keeps its form
(as the DS sprite's greys do), each hi-res pixel snapped to the palette (Sabertann's 15 DS colours), then each block of
the final texture takes its most common colour (crisp, not muddy averages). python shade_tex2.py BASE [PAL_SPRITE]
-> BASE_tex{g}.png, BASE_tex{g}_idx.npy, BASE_tex_pal.npy"""
import sys, numpy as np
from PIL import Image
B = sys.argv[1]; PS = sys.argv[2] if len(sys.argv) > 2 else '/Users/arvind/Sigma pokemon pc port attempt/assets/sprites-ds/sabertann/front.png'
SIZES = {0: (128, 128), 1: (64, 64), 2: (32, 64)}
pa = np.asarray(Image.open(PS).convert('RGBA')); pal = np.unique(pa[pa[..., 3] > 0][:, :3], axis=0).astype(float)[:15]
def to_lab(c):
    c = c / 255.0; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089]); f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)
PL = to_lab(pal)
lin = lambda c: np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
srgb = lambda c: np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(np.clip(c, 0, 1), 1 / 2.4) - 0.055)
L = np.array([-0.35, -0.55, 0.75]); L /= np.linalg.norm(L)
for g, (w, h) in SIZES.items():
    al = np.asarray(Image.open(f'{B}_albedo{g}.png').convert('RGB')).astype(float) / 255
    nm = np.asarray(Image.open(f'{B}_normal{g}.png').convert('RGB')).astype(float) / 255 * 2 - 1
    nd = np.clip((nm * L).sum(-1), 0, 1)
    c = lin(al) * (0.45 + 0.75 * nd)[..., None] * 1.2 + (0.035 * nd ** 1.5)[..., None]
    rgb = srgb(np.clip(c, 0, 1)) * 255
    ix = ((to_lab(rgb)[..., None, :] - PL[None, None]) ** 2).sum(-1).argmin(-1)
    H, W = ix.shape; fy, fx = H // h, W // w
    blk = ix[:h * fy, :w * fx].reshape(h, fy, w, fx).transpose(0, 2, 1, 3).reshape(h, w, -1)
    out = np.zeros((h, w), int)
    for y in range(h):
        for x in range(w): out[y, x] = np.bincount(blk[y, x], minlength=15).argmax()
    Image.fromarray(pal[out].astype(np.uint8)).save(f'{B}_tex{g}.png'); np.save(f'{B}_tex{g}_idx.npy', out + 1)
np.save(f'{B}_tex_pal.npy', pal); print('ok')
