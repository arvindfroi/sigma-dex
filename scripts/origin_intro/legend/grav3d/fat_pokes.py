"""drive.py pokes that point the game's in-RAM file table at a relocated file (savestate tests: the table is cached in
RAM, so relocate.py's FAT change alone is not seen). Prints 'poke:ADDR=BYTE' steps for the 8 bytes of the entry.
python fat_pokes.py RAM_ADDR NEW_START NEW_END        (Lugia's film a/2/4/4 = file 364: RAM 0x023BFDC0 with g7.dst)"""
import sys
a, s, e = (int(x, 0) for x in sys.argv[1:4])
print(','.join('poke:%#x=%d' % (a + k, b) for k, b in enumerate(s.to_bytes(4, 'little') + e.to_bytes(4, 'little'))))
