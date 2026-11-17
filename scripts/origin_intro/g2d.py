"""LZ10 + NCLR/NCGR/NCER/NANR read/write helpers (formats per GBATEK / Tinke notes)."""
import struct
def lz10_dec(d):
    assert d[0]==0x10; n=d[1]|d[2]<<8|d[3]<<16; o=bytearray(); i=4
    while len(o)<n:
        fl=d[i]; i+=1
        for b in range(8):
            if len(o)>=n: break
            if fl&(0x80>>b):
                x=d[i]<<8|d[i+1]; i+=2; ln=(x>>12)+3; dist=(x&0xfff)+1
                for _ in range(ln): o.append(o[-dist])
            else: o.append(d[i]); i+=1
    return bytes(o)
def lz10_enc(d):
    o=bytearray([0x10,len(d)&255,len(d)>>8&255,len(d)>>16&255]); i=0; n=len(d)
    while i<n:
        flagpos=len(o); o.append(0); fl=0
        for b in range(8):
            if i>=n: break
            best=0; bd=0
            lo=max(0,i-4096)
            # search
            for j in range(i-1,lo-1,-1):
                l=0
                while l<18 and i+l<n and d[j+l]==d[i+l]: l+=1
                if l>best: best=l; bd=i-j
                if best==18: break
            if best>=3:
                fl|=0x80>>b; x=((best-3)<<12)|(bd-1); o+=bytes([x>>8,x&255]); i+=best
            else: o.append(d[i]); i+=1
        o[flagpos]=fl
    while len(o)%4: o.append(0)
    return bytes(o)
def sections(d):
    magic=d[:4]; bom,ver,fsz,hs,ns=struct.unpack_from('<HHIHH',d,4)
    out={}; o=hs
    for _ in range(ns):
        m=d[o:o+4]; sz=struct.unpack_from('<I',d,o+4)[0]; out[m]=(o,d[o:o+sz]); o+=sz
    return magic,ver,out
SHAPE={(0,0):(8,8),(0,1):(16,16),(0,2):(32,32),(0,3):(64,64),(1,0):(16,8),(1,1):(32,8),(1,2):(32,16),(1,3):(64,32),(2,0):(8,16),(2,1):(8,32),(2,2):(16,32),(2,3):(32,64)}
def read_ncer(d):
    mg,ver,secs=sections(d); o,s=secs[b'KBEC']
    n,bank,coff,mapm=struct.unpack_from('<HHII',s,8)
    esz=16 if bank==1 else 8; base=8+coff; oambase=base+n*esz
    cells=[]
    for i in range(n):
        e=base+i*esz; no,attr,oo=struct.unpack_from('<HHI',s,e)
        bbox=struct.unpack_from('<4h',s,e+8) if bank==1 else None
        oams=[]
        for k in range(no):
            a0,a1,a2=struct.unpack_from('<HHH',s,oambase+oo+6*k)
            y=a0&255; y=y-256 if y>=128 else y; x=a1&511; x=x-512 if x>=256 else x
            shp=a0>>14; sz=a1>>14; w,h=SHAPE[(shp,sz)]
            oams.append(dict(x=x,y=y,w=w,h=h,tile=a2&1023,pal=a2>>12,prio=(a2>>10)&3,a0=a0,a1=a1,a2=a2,bpp8=(a0>>13)&1,aff=(a0>>8)&1,dbl=(a0>>9)&1,hf=(a1>>12)&1,vf=(a1>>13)&1))
        cells.append(dict(attr=attr,bbox=bbox,oams=oams))
    return dict(bank=bank,mapping=mapm,cells=cells,secs=secs)
def read_nanr(d):
    mg,ver,secs=sections(d); o,s=secs[b'KNBA']
    nseq,nfr,so,fo,ao=struct.unpack_from('<HHIII',s,8)
    seqs=[]
    for i in range(nseq):
        e=8+so+16*i; nf,ls,el,at,pm,foff=struct.unpack_from('<HHHHII',s,e)
        frames=[]
        for k in range(nf):
            do,dur,pad=struct.unpack_from('<IHH',s,8+fo+foff+8*k)
            p=8+ao+do
            if el==0: fr=dict(cell=struct.unpack_from('<H',s,p)[0])
            elif el==1:
                c,rot,sxx,syy,tx,ty=struct.unpack_from('<HHiihh',s,p); fr=dict(cell=c,rot=rot,sx=sxx/4096,sy=syy/4096,tx=tx,ty=ty)
            else:
                c,pd,tx,ty=struct.unpack_from('<HHhh',s,p); fr=dict(cell=c,tx=tx,ty=ty)
            fr['dur']=dur; fr['doff']=do; frames.append(fr)
        seqs.append(dict(nf=nf,loop=ls,el=el,at=at,pm=pm,foff=foff,frames=frames))
    return dict(seqs=seqs,secs=secs)
def read_ncgr(d):
    mg,ver,secs=sections(d); o,s=secs[b'RAHC']
    h,w,bd,mp,mt,sz,off=struct.unpack_from('<HHIIIII',s,8)
    return dict(tiles_h=h,tiles_w=w,bpp=8 if bd==4 else 4,mapping=mp,mode=mt,data=s[8+off:8+off+sz],hdr=s[:32])
def read_nclr(d):
    mg,ver,secs=sections(d); o,s=secs[b'TTLP']
    bd,_,sz,off=struct.unpack_from('<IIII',s,8)
    raw=s[8+off:8+off+sz]
    return [struct.unpack_from('<H',raw,2*i)[0] for i in range(len(raw)//2)],bd
