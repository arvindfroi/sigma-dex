"""Minimal Nitro (NSBMD/NSBCA/...) reader. Format notes from apicula (scurest, MIT/0BSD) + GBATEK."""
import struct
def u8(d,o): return d[o]
def u16(d,o): return struct.unpack_from('<H',d,o)[0]
def u32(d,o): return struct.unpack_from('<I',d,o)[0]
def s16(d,o): return struct.unpack_from('<h',d,o)[0]
def s32(d,o): return struct.unpack_from('<i',d,o)[0]
def fx16(v): v&=0xffff; return (v-0x10000 if v&0x8000 else v)/4096
def fx32(v): v&=0xffffffff; return (v-0x100000000 if v&0x80000000 else v)/4096

def dict_read(d,o,esz=None):
    """returns list of (entry_bytes, name, entry_offset)"""
    assert d[o]==0, d[o]
    n=d[o+1]; hsz=u16(d,o+2)
    sub=u16(d,o+4); subsz=u16(d,o+6)
    p=o+8+4*(n+1); assert subsz==8+4*(n+1)-0 or True
    esz2=u16(d,p); dsz=u16(d,p+2)
    if esz: assert esz==esz2,(esz,esz2)
    data=p+4
    names=data+n*esz2
    out=[]
    for i in range(n):
        eo=data+i*esz2
        nm=d[names+16*i:names+16*i+16].rstrip(b'\0').decode('latin1')
        out.append((d[eo:eo+esz2],nm,eo))
    return out,(o,hsz,subsz,esz2,dsz)

def container(d):
    stamp=d[:4]; bom,ver,fsz,hs,ns=struct.unpack_from('<HHIHH',d,4)
    offs=[u32(d,16+4*i) for i in range(ns)]
    return stamp,ver,fsz,offs

RCMD_LEN={0:0,1:0,2:2,3:1,4:1,5:1,6:3,7:1,8:1,0xb:0,0xc:2,0xd:2,0x24:1,0x26:4,0x2b:0,0x40:0,0x44:1,0x46:4,0x47:2,0x66:5,0x80:0}
def render_cmds(d,o):
    out=[]
    while True:
        op=d[o]
        if op==9:
            cnt=d[o+2]; n=2+3*cnt
        else: n=RCMD_LEN[op]
        out.append((op,list(d[o+1:o+1+n]))); o+=1+n
        if op==1: return out

def read_node(d,o):
    flags=u16(d,o); m0=u16(d,o+2); p=o+4
    t=None;r=None;s=None
    if not flags&1:
        t=[fx32(u32(d,p+4*i)) for i in range(3)]; p+=12
    if flags>>3&1:
        a=fx16(u16(d,p)); b=fx16(u16(d,p+2)); p+=4
        r=('pivot',(flags>>4)&15,(flags>>8)&15,a,b)
    elif not flags>>1&1:
        r=('mat',[fx16(m0)]+[fx16(u16(d,p+2*i)) for i in range(8)]); p+=16
    if not flags>>2&1:
        s=[fx32(u32(d,p+4*i)) for i in range(3)]; p+=12
    return dict(flags=flags,t=t,r=r,s=s,size=p-o)

def read_bmd(d):
    stamp,ver,fsz,offs=container(d)
    res={'ver':ver,'blocks':offs}
    for bo in offs:
        st=d[bo:bo+4]
        if st==b'MDL0':
            ents,_=dict_read(d,bo+8,4)
            res['models']=[]
            for e,nm,_ in ents:
                mo=bo+u32(e,0)
                res['models'].append(read_model(d,mo,nm))
        elif st==b'TEX0':
            res['tex']=read_tex(d,bo)
    return res

def read_model(d,mo,nm):
    size,rc,mat,shp,inv=struct.unpack_from('<5I',d,mo)
    info=d[mo+20:mo+20+0x2C]
    sbcType,scal,texmtx,nnode,nmat,nshp,firstunused,pad=info[:8]
    up=fx32(u32(info,8)); down=fx32(u32(info,12))
    nv,npoly,ntri,nquad=struct.unpack_from('<4H',info,16)
    box=[fx16(u16(info,24+2*i)) for i in range(6)]
    boxs=(fx32(u32(info,36)),fx32(u32(info,40)))
    m=dict(name=nm,off=mo,size=size,info=dict(sbcType=sbcType,scaling=scal,texmtx=texmtx,nnode=nnode,nmat=nmat,nshp=nshp,firstunused=firstunused,up=up,down=down,nv=nv,npoly=npoly,ntri=ntri,nquad=nquad,box=box,boxscale=boxs),
           rawinfo=info)
    no=mo+20+0x2C
    ents,_=dict_read(d,no,4)
    m['nodes']=[(nm2,read_node(d,no+u32(e,0))) for e,nm2,_ in ents]
    m['rcmds']=render_cmds(d,mo+rc)
    # materials
    mbase=mo+mat
    toff=u16(d,mbase); poff=u16(d,mbase+2)
    ents,_=dict_read(d,mbase+4,4)
    mats=[]
    for e,mn,_ in ents:
        o=mbase+u32(e,0)
        f=struct.unpack_from('<HHIIIIIIHHHHii',d,o)
        mats.append(dict(name=mn,off=o,sizeof=f[1],difamb=f[2],speemi=f[3],polyattr=f[4],polymask=f[5],teximg=f[6],unk3=f[7],pltt=f[8],misc=f[9],w=f[10],h=f[11],raw=d[o:o+f[1]]))
    for (key,po) in (('tex',toff),('pal',poff)):
        ents,_=dict_read(d,mbase+po,4)
        for e,tn,_ in ents:
            off,num,_x=struct.unpack('<HBB',e)
            for k in range(num):
                mats[d[mbase+off+k]][key]=tn
    m['mats']=mats
    # shapes
    sbase=mo+shp
    ents,_=dict_read(d,sbase,4)
    shapes=[]
    for e,sn,_ in ents:
        o=sbase+u32(e,0)
        dummy,ssz,flag,co,cl=struct.unpack_from('<HHIII',d,o)
        shapes.append(dict(name=sn,flag=flag,cmds=d[o+co:o+co+cl]))
    m['shapes']=shapes
    m['invbind_off']=mo+inv
    return m

def read_tex(d,bo):
    f=struct.unpack_from('<4sIIHHIIIHHIIIIHHII',d,bo)
    (st,ssz,u0,tblen,toff,u1,tbo,u2,cblen,cinfo,u3,c1,c2,u4,pblen,u5,poff,pbo)=f
    t=dict(raw_hdr=f)
    ents,_=dict_read(d,bo+toff,8)
    texs=[]
    for e,nm,_ in ents:
        p,unk=struct.unpack('<II',e)
        fmt=(p>>26)&7; w=8<<((p>>20)&7); h=8<<((p>>23)&7)
        bpp={1:8,2:2,3:4,4:8,5:2,6:8,7:16}[fmt]
        off=(p&0xffff)<<3
        texs.append(dict(name=nm,param=p,unk=unk,fmt=fmt,w=w,h=h,c0=(p>>29)&1,data=d[bo+tbo+off:bo+tbo+off+w*h*bpp//8]))
    ents,_=dict_read(d,bo+poff,4)
    pal=d[bo+pbo:bo+pbo+(pblen<<3)]
    pals=[]
    for e,nm,_ in ents:
        o,unk=struct.unpack('<HH',e)
        pals.append(dict(name=nm,off=o<<3,unk=unk))
    t['texs']=texs; t['pals']=pals; t['paldata']=pal
    return t
