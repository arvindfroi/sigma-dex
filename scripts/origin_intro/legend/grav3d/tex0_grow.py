"""Rebuild the TEX0 block at the end of an NSBMD (BMD0) so named textures can change size and format and named palettes
can grow (v7: Gravriel's 128x128 and 256x128 8-bpp textures in place of Lugia's 64x64/32x32 4-bpp ones). The dicts (names,
order) stay; texture data and palette data are laid out again (8-byte aligned textures, 16-byte aligned palettes), the
image params (offset, size, format, colour-0 transparency off) and the dict extras (w | h << 11) are rewritten, and the
header offsets, the block size and the BMD0 file size follow. TEX0 must be the last block; no compressed textures.
grow(d, tex={name: (fmt, w, h, bytes)}, pal={name: bytes}) -> new bytes"""
import struct
import nitro
HDR = '<4sIIHHIIIHHIIIIHHII'
def grow(d, tex, pal):
    d = bytes(d); stamp, ver, fsz, offs = nitro.container(d)
    bo = [b for b in offs if d[b:b + 4] == b'TEX0']; assert len(bo) == 1; bo = bo[0]
    f = list(struct.unpack_from(HDR, d, bo)); (st, ssz, u0, tblen, toff, u1, tbo, u2, cblen, cinfo, u3, c1, c2, u4, pblen, u5, poff, pbo) = f
    assert bo + ssz == len(d), 'TEX0 is not the last block'
    assert cblen == 0, 'compressed textures not handled'
    assert toff < tbo and poff < tbo, 'dicts after the texture data'
    t = nitro.read_tex(d, bo)
    blk = bytearray(d[bo:bo + tbo])                       # header + dicts, patched below
    tents, _ = nitro.dict_read(d, bo + toff, 8); pents, _ = nitro.dict_read(d, bo + poff, 4)
    tdata = bytearray()
    for (e, nm, eo), x in zip(tents, t['texs']):
        if nm in tex:
            fmt, w, h, raw = tex[nm]
        else:
            fmt, w, h, raw = x['fmt'], x['w'], x['h'], x['data']
        bpp = {1: 8, 2: 2, 3: 4, 4: 8, 5: 2, 6: 8, 7: 16}[fmt]; assert len(raw) == w * h * bpp // 8, (nm, len(raw), w, h, bpp)
        while len(tdata) % 8: tdata.append(0)
        off = len(tdata); tdata += raw
        sw, sh = (w // 8).bit_length() - 1, (h // 8).bit_length() - 1; assert 8 << sw == w and 8 << sh == h
        p = x['param'] & ~(0xffff | (7 << 20) | (7 << 23) | (7 << 26))
        if nm in tex: p &= ~(1 << 29)
        p |= (off >> 3) | (sw << 20) | (sh << 23) | (fmt << 26)
        struct.pack_into('<II', blk, eo - bo, p, 0x80000000 | w | (h << 11))
    while len(tdata) % 16: tdata.append(0)
    old = t['paldata']; pdata = bytearray()
    for (e, nm, eo), x in zip(pents, t['pals']):
        if nm in pal: raw = pal[nm]
        else:
            nxt = sorted(o['off'] for o in t['pals'] if o['off'] > x['off']); end = nxt[0] if nxt else len(old); raw = old[x['off']:end]
        while len(pdata) % 16: pdata.append(0)
        off = len(pdata); pdata += raw
        struct.pack_into('<H', blk, eo - bo, off >> 3)
    while len(pdata) % 8: pdata.append(0)
    npbo = tbo + len(tdata)
    f[1] = npbo + len(pdata); f[3] = len(tdata) >> 3; f[11] = npbo; f[12] = npbo; f[14] = len(pdata) >> 3; f[17] = npbo
    struct.pack_into(HDR, blk, 0, *f)
    out = bytearray(d[:bo]) + blk + tdata + pdata
    struct.pack_into('<I', out, 8, len(out))              # BMD0 file size
    return bytes(out)
