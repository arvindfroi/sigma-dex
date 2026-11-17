"""LZ11 (Nintendo DS, header 0x11) decompressor."""
def lz11_dec(d):
    assert d[0] == 0x11
    n = d[1] | d[2] << 8 | d[3] << 16; p = 4
    if n == 0: n = int.from_bytes(d[4:8], 'little'); p = 8
    out = bytearray()
    while len(out) < n:
        flags = d[p]; p += 1
        for b in range(8):
            if len(out) >= n: break
            if not flags & (0x80 >> b): out.append(d[p]); p += 1; continue
            b1 = d[p]; ind = b1 >> 4
            if ind == 0:
                l = (((b1 & 0xF) << 4) | (d[p + 1] >> 4)) + 0x11; disp = ((d[p + 1] & 0xF) << 8 | d[p + 2]) + 1; p += 3
            elif ind == 1:
                l = (((b1 & 0xF) << 12) | (d[p + 1] << 4) | (d[p + 2] >> 4)) + 0x111; disp = ((d[p + 2] & 0xF) << 8 | d[p + 3]) + 1; p += 4
            else:
                l = ind + 1; disp = ((b1 & 0xF) << 8 | d[p + 1]) + 1; p += 2
            for _ in range(l): out.append(out[-disp])
    return bytes(out)
