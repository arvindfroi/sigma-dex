"""Origin keeps per-outfit copies of a/1/2/0: data/clothes1/a120.narc (archive 298) and data/clothes2/a120.narc (299).
The game opens a copy instead of a/1/2/0 when the outfit in the save (or the forcing byte 0x021CFCF0) is set
(arm9 0x02007838 / 0x020077F8, table at 0x020F233C). Their members 59-66 are Marill's set, byte for byte as in
a/1/2/0 (only 12-29, the outfit's player pictures, differ). This copies members 63 and 64 of a built a/1/2/0 into both,
in place (same offsets and sizes). python clothes_a120.py BUILT_A120 OUTDIR TAG"""
import sys, os, struct
sys.path.insert(0, '/Users/arvind/sigma-origin/title3d')
from narc import unpack
X = '/Users/arvind/sigma-origin/rc8/x_rc8/files'
def inplace(raw, members):
    off = 16; bsz, = struct.unpack_from('<I', raw, off + 4); n, = struct.unpack_from('<H', raw, off + 8)
    ents = [struct.unpack_from('<II', raw, off + 12 + 8 * i) for i in range(n)]
    off += bsz; bsz, = struct.unpack_from('<I', raw, off + 4); off += bsz; base = off + 8; out = bytearray(raw)
    for i, new in members.items():
        a, b = ents[i]; assert len(new) == b - a, (i, len(new), b - a); out[base + a:base + b] = new
    return bytes(out)
if __name__ == '__main__':
    built, od, tag = sys.argv[1:4]; os.makedirs(od, exist_ok=True)
    B = unpack(open(built, 'rb').read()); O = unpack(open(X + '/a/1/2/0', 'rb').read())
    assert [i for i in range(len(B)) if B[i] != O[i]] == [63, 64]
    for c in ('clothes1', 'clothes2'):
        raw = open('%s/data/%s/a120.narc' % (X, c), 'rb').read(); C = unpack(raw)
        assert all(C[i] == O[i] for i in range(59, 67)), c + ': Marill members differ from a/1/2/0'
        out = inplace(raw, {63: B[63], 64: B[64]}); N = unpack(out)
        assert len(out) == len(raw) and [i for i in range(len(N)) if N[i] != C[i]] == [63, 64] and N[63] == B[63] and N[64] == B[64]
        p = '%s/a120_%s_%s.bin' % (od, c, tag); open(p, 'wb').write(out); print('wrote', p, len(out), 'members 63, 64 changed')
