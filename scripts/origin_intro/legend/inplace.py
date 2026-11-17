"""Write a patched file into a ROM image at the original file's offset (padded), so savestates made on the
original ROM still work. python legend/inplace.py ROM_IN ORIG_FILE NEW_FILE ROM_OUT"""
import sys
rom = bytearray(open(sys.argv[1], 'rb').read()); old = open(sys.argv[2], 'rb').read(); new = open(sys.argv[3], 'rb').read()
i = rom.find(old); assert i >= 0 and rom.find(old, i + 1) < 0, 'not found once'
assert len(new) <= len(old), (len(new), len(old))
rom[i:i + len(old)] = new + bytes(len(old) - len(new)); open(sys.argv[4], 'wb').write(rom); print('at', hex(i), len(new), '/', len(old))
