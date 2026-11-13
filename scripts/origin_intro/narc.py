import struct,sys
def unpack(data):
    assert data[:4]==b'NARC'
    off=16
    # BTAF
    assert data[off:off+4]==b'BTAF'; sz,=struct.unpack_from('<I',data,off+4); n,=struct.unpack_from('<H',data,off+8)
    ents=[struct.unpack_from('<II',data,off+12+8*i) for i in range(n)]
    off+=sz
    assert data[off:off+4]==b'BTNF'; sz,=struct.unpack_from('<I',data,off+4); off+=sz
    assert data[off:off+4]==b'GMIF'; base=off+8
    return [data[base+s:base+e] for s,e in ents]
def pack(files):
    btaf=bytearray(b'BTAF'+b'\0'*4+struct.pack('<HH',len(files),0))
    pos=0; gm=bytearray()
    for f in files:
        btaf+=struct.pack('<II',pos,pos+len(f)); gm+=f; pos+=len(f)
        while len(gm)%4: gm+=b'\xff'; pos+=1
    struct.pack_into('<I',btaf,4,len(btaf))
    btnf=b'BTNF'+struct.pack('<I',16)+struct.pack('<IHH',4,0,1)
    gmif=b'GMIF'+struct.pack('<I',len(gm)+8)+gm
    body=bytes(btaf)+btnf+gmif
    return b'NARC'+struct.pack('<HHIHH',0xFFFE,0x0100,16+len(body),16,3)+body
if __name__=='__main__':
    fs=unpack(open(sys.argv[1],'rb').read())
    for i,f in enumerate(fs): print(i,len(f),f[:4])
