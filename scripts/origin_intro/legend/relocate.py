"""Put a changed file at the end of the ROM's used data and point its FAT entry there (for files that outgrew their
slot, e.g. Lugia's film a/2/4/4 with Gravriel and a longer scene). The old bytes stay but are no longer referenced.
The file is found by its current content (must occur once); its FAT entry by that offset.
python legend/relocate.py ROM_IN OLD_FILE NEW_FILE ROM_OUT"""
import sys, struct
rom = bytearray(open(sys.argv[1], 'rb').read()); old = open(sys.argv[2], 'rb').read(); new = open(sys.argv[3], 'rb').read()
i = rom.find(old); assert i >= 0 and rom.find(old, i + 1) < 0, 'old file not found once'
fat_off, fat_size = struct.unpack_from('<II', rom, 0x48); n = fat_size // 8
ents = [struct.unpack_from('<II', rom, fat_off + 8 * k) for k in range(n)]
idx = [k for k, (s, e) in enumerate(ents) if s == i and e == i + len(old)]; assert len(idx) == 1, ('FAT entry', idx)
end = max(e for s, e in ents); used = struct.unpack_from('<I', rom, 0x80)[0]
start = (max(end, used) + 0x1ff) & ~0x1ff
assert start + len(new) <= len(rom), 'no room at the end of the ROM image'
assert all(b == 0xff or b == 0 for b in rom[start:start + len(new)]), 'end of ROM not free'
rom[start:start + len(new)] = new
struct.pack_into('<II', rom, fat_off + 8 * idx[0], start, start + len(new))
struct.pack_into('<I', rom, 0x80, max(used, start + len(new)))          # total used ROM size
def crc16(data, crc=0xFFFF):
    for byte in data:
        crc ^= byte
        for _ in range(8): crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc
assert crc16(sys.argv and open(sys.argv[1], 'rb').read(0x15E)) == struct.unpack_from('<H', open(sys.argv[1], 'rb').read(0x160), 0x15E)[0], 'header CRC check failed on the input'
struct.pack_into('<H', rom, 0x15E, crc16(rom[:0x15E]))                     # header CRC after the size change
open(sys.argv[4], 'wb').write(rom)
print('file %d moved: %#x (%d bytes) -> %#x (%d bytes); used ROM %#x -> %#x' % (idx[0], i, len(old), start, len(new), used, max(used, start + len(new))))
