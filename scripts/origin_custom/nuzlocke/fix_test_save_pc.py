"""Fill the PC block of a save's valid slot with properly empty box slots (encrypted zeros) and fix its CRC."""
import sys, struct
sys.path.insert(0, '/Users/arvind/origin-en/work/advanced-ai/testbench/lib')
from savetool import image, Save, _crypt, crc16_ccitt
PC_OFF, PC_SIZE, BOXES, SLOTS = 0xF800, 0x18408, 24, 30
def fix(path_in, path_out):
    img = bytearray(image(open(path_in, 'rb').read()))
    base = Save(data=bytes(img)).base
    empty = bytes(8) + bytes(_crypt(bytes(128), 0))
    pc = base + PC_OFF
    for b in range(BOXES):
        for s in range(SLOTS):
            o = pc + 0x1000 * b + 0x88 * s
            img[o:o + 0x88] = empty
    crc = crc16_ccitt(img[pc:pc + PC_SIZE - 0x10])
    struct.pack_into('<H', img, pc + PC_SIZE - 2, crc)
    open(path_out, 'wb').write(bytes(img))
    print('fixed PC of slot', hex(base), 'crc', hex(crc))
if __name__ == '__main__':
    fix(sys.argv[1], sys.argv[2])
