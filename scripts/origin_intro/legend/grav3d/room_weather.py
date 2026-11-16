"""The Whirl Islands Lugia cave (map 244, MAP_WHIRL_ISLANDS_B3F_LUGIA_CAVE) gets a fog weather in the overworld too
(Arvind 2026-11-16: "the whole room should be like that, even when there is no cutscene"). Its map header (24 bytes in
arm9: scripts 104, script header 365, text bank 123, events 230, area 98) has weather in bits 1-7 of the last word.
Weathers with 3D fog: 9/10 white mist + a mist layer (9 is used by Sprout Tower 2F and Goldenrod Dept. Store 3F, the
colour is shared), 13 = LOW_LIGHT dark fog (0x421, used by maps 71 and 278). Only map 244's byte changes.
python room_weather.py ROM_IN ROM_OUT WEATHER"""
import sys, struct
src, dst, wt = sys.argv[1], sys.argv[2], int(sys.argv[3])
b = bytearray(open(src, 'rb').read())
pat = struct.pack('<HHH', 104, 365, 123)
hits = []; i = b.find(pat)
while i >= 0:
    rec = i - 6
    if struct.unpack_from('<H', b, rec + 16)[0] == 230: hits.append(rec)
    i = b.find(pat, i + 1)
assert len(hits) == 1, ('map 244 header not found once', [hex(h) for h in hits])
rec = hits[0]; w = struct.unpack_from('<I', b, rec + 20)[0]
print('map 244 header at ROM %#x, weather %d -> %d' % (rec, (w >> 1) & 0x7f, wt))
struct.pack_into('<I', b, rec + 20, (w & ~(0x7f << 1)) | (wt << 1))
open(dst, 'wb').write(b)
