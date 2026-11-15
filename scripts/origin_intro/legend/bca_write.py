"""NSBCA (joint animation) encoder, the inverse of geom.read_bca: per node and frame (T, R, S) -> a BCA0 file with one
J0AC animation. Rotations go into the basis table (two 13-bit columns, the third is their cross product), deduplicated;
translations as fx32 curves (or constants); special flags (no animation, zero/rest translation, identity/rest rotation,
unit/rest scale) can be kept per node. Self-test: python legend/bca_write.py NARC MODEL BCA OUT.bca"""
import struct, numpy as np
def enc_basis(R):
    a = R[:, 0]; b = R[:, 1]
    q = lambda v: int(round(max(-1.0, min(4095 / 4096, v)) * 4096)) & 0x1fff
    out = [q(b[1]), q(a[0]), q(a[1]), q(a[2]), q(b[0])]; o5 = q(b[2])
    low = [(o5 >> (3 * (4 - i))) & 7 for i in range(5)]
    inp = [((out[i] & 0x1fff) << 3) | low[i] for i in range(5)]
    # inp order is [in4, in0, in1, in2, in3]
    return (inp[1], inp[2], inp[3], inp[4], inp[0])
import os as _os
TOL_T = float(_os.environ.get("BCA_TOL_T", "0.01")); TOL_S = float(_os.environ.get("BCA_TOL_S", "0.001"))   # solved tracks carry tiny noise: still constant
def fx32(v): return int(round(v * 4096)) & 0xffffffff
def build(nframes, nodes, name=b'anim', template=None):
    """nodes: list of dicts: {'flags_keep': int or None, 'T': [nf x 3] or None, 'R': [nf x 3x3] or None, 'S': [nf x 3] or None}
    flags_keep: 1 = not animated; else bits 2/4 (T zero/rest), 0x40/0x80 (R identity/rest), 0x200/0x400 (S one/rest) are
    applied, and the missing parts are taken from T/R/S."""
    basis = []; bkey = {}
    def bidx(R):
        e = enc_basis(np.asarray(R, float)); k = e
        if k not in bkey: bkey[k] = len(basis); basis.append(e)
        return bkey[k]
    objs = []; datas = []
    for nd in nodes:
        fk = nd.get('flags_keep')
        if fk is not None and fk & 1: objs.append((1, b'', [])); continue
        flags = 0; head = bytearray(); curves = []                        # curves: (patch position in head, bytes)
        T, R, S = nd.get('T'), nd.get('R'), nd.get('S'); rate = nd.get('rate', 0); nv = nframes >> rate
        pick = lambda seq: [seq[(k << rate)] for k in range(nv)]
        if fk is not None and fk & 6: flags |= fk & 6
        else:
            T = np.asarray(T, float)
            for k in range(3):
                col = T[:, k]
                if np.allclose(col, col[0], atol=TOL_T): flags |= 1 << (3 + k); head += struct.pack('<I', fx32(col[0]))
                else:
                    info = (0) | ((nframes & 0xfff) << 16) | (0 << 28) | (rate << 30)
                    curves.append((len(head) + 4, b''.join(struct.pack('<I', fx32(v)) for v in pick(col)), 4)); head += struct.pack('<II', info, 0)
        if fk is not None and fk & 0xC0: flags |= fk & 0xC0
        else:
            ids = [bidx(r) for r in R]
            if len(set(ids)) == 1: flags |= 0x100; head += struct.pack('<HH', ids[0], 0)
            else:
                info = (0) | ((nframes & 0xfff) << 16) | (rate << 30)
                curves.append((len(head) + 4, b''.join(struct.pack('<H', i) for i in pick(ids)), 2)); head += struct.pack('<II', info, 0)
        if fk is not None and fk & 0x600: flags |= fk & 0x600
        else:
            S = np.asarray(S, float)
            if np.allclose(S, 1, atol=TOL_S): flags |= 0x200
            else:
                for k in range(3):
                    col = S[:, k]
                    if np.allclose(col, col[0], atol=TOL_S): flags |= 1 << (11 + k); head += struct.pack("<II", fx32(col[0]), fx32(1 / col[0] if abs(col[0]) > 1e-9 else 0))
                    else:
                        info = ((nframes & 0xfff) << 16)
                        curves.append((len(head) + 4, b''.join(struct.pack("<II", fx32(v), fx32(1 / v if abs(v) > 1e-9 else 0)) for v in col), 8)); head += struct.pack('<II', info, 0)
        objs.append((flags, bytes(head), curves))
    # layout: header(20) + u16 offsets + objects + curve data + basis table
    n = len(objs); off = 20 + 2 * n; off += (-off) % 4
    obj_off = []; blob = bytearray()
    for oi, (flags, head, curves) in enumerate(objs):
        nidx = nodes[oi].get('idx', oi)                    # the node this track drives
        obj_off.append(off + len(blob)); blob += struct.pack('<HBB', flags, 0, nidx) + head
        while len(blob) % 4: blob += b'\0'
    cur_base = off + len(blob); cdata = bytearray(); patches = []
    for oi, (flags, head, curves) in enumerate(objs):
        for pos, data, w in curves:
            patches.append((obj_off[oi] + 4 + pos, cur_base + len(cdata))); cdata += data
            while len(cdata) % 4: cdata += b'\0'
    bs = cur_base + len(cdata); btab = b''.join(struct.pack('<5H', *e) for e in basis)
    pv = bs + len(btab); pv += (-pv) % 4
    a = bytearray(struct.pack('<4sHHIII', b'J\0AC', nframes, n, 0, pv, bs))
    a += b''.join(struct.pack('<H', o) for o in obj_off); a += bytes(off - len(a)); a += blob + cdata + btab; a += bytes(pv - len(a))
    for p, v in patches: struct.pack_into('<I', a, p, v)
    if template is not None:                              # keep the original file's header and dictionary byte for byte
        import nitro
        d0 = template; bo = struct.unpack_from('<I', d0, 16)[0]
        ents, _ = nitro.dict_read(d0, bo + 8, 4); aoff = struct.unpack_from('<I', ents[0][0], 0)[0]
        out = bytearray(d0[:bo + aoff]) + a
        struct.pack_into('<I', out, 8, len(out)); struct.pack_into('<I', out, bo + 4, len(out) - bo)
        return bytes(out)
    # JNT0 block with a one-entry dictionary, then the BCA0 container
    nm = name.ljust(16, b'\0')[:16]
    dic = bytearray(struct.pack('<BBH', 0, 1, 8 + 4 * 2 + 4 + 4 + 16))
    dic += struct.pack('<HH', 8, 4 * 2 + 4) + struct.pack('<II', 0, 0)   # patricia-tree stub (2 nodes) as NNS writes for 1 entry
    dic += struct.pack('<HH', 4, 4 + 4); entry_pos = len(dic); dic += struct.pack('<I', 0) + nm
    jhdr = 8; jnt = bytearray(b'JNT0' + b'\0' * 4) + dic; aoff = len(jnt); aoff += (-aoff) % 4; jnt += bytes(aoff - len(jnt))
    struct.pack_into('<I', jnt, jhdr + entry_pos, aoff); jnt += a; struct.pack_into('<I', jnt, 4, len(jnt))
    hdr = struct.pack('<4sHHIHHI', b'BCA0', 0xFEFF, 1, 16 + 4 + len(jnt), 16, 1, 20)
    return hdr + bytes(jnt)
if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from narc import unpack
    from lz11 import lz11_dec
    import nitro, geom
    F = unpack(open(sys.argv[1], 'rb').read()); D = lambda i: lz11_dec(F[i]) if F[i][:1] == b'\x11' else F[i]
    md = D(int(sys.argv[2])); m = nitro.read_bmd(md)['models'][0]; orig = D(int(sys.argv[3])); anim = geom.read_bca(orig)[0]
    nf = anim['nframes']; per = [geom.node_trs(m, anim, f) for f in range(nf)]
    nodes = []
    for i in range(len(anim['objs'])):
        o = anim['objs'][i]; fl = o['flags']
        nodes.append(dict(flags_keep=(fl & (1 | 6 | 0xC0 | 0x600)), T=[per[f][i][0] for f in range(nf)], R=[per[f][i][1] for f in range(nf)], S=[per[f][i][2] for f in range(nf)]))
    new = build(nf, nodes, template=orig); open(sys.argv[4], 'wb').write(new)
    back = geom.read_bca(new)[0]; err = 0
    for f in range(0, nf, 7):
        a1 = geom.node_trs(m, anim, f); a2 = geom.node_trs(m, back, f)
        for i in range(len(a1)):
            err = max(err, np.abs(np.subtract(a1[i][0], a2[i][0])).max(), np.abs(np.subtract(a1[i][1], a2[i][1])).max())
    print('nodes', len(nodes), 'frames', nf, 'size', len(new), 'orig', len(orig), 'max error', err)
