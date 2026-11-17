"""Decode NSBMD geometry (rest pose) to Python lists, and export OBJ + PNG textures."""
import struct, numpy as np, sys, os
from nitro import *
NP={0:0,0x10:1,0x11:0,0x12:1,0x13:1,0x14:1,0x15:0,0x16:16,0x17:12,0x18:16,0x19:12,0x1a:9,0x1b:3,0x1c:3,0x20:1,0x21:1,0x22:1,0x23:2,0x24:1,0x25:1,0x26:1,0x27:1,0x28:1,0x29:1,0x2a:1,0x2b:1,0x30:1,0x31:1,0x32:1,0x33:1,0x34:32,0x40:1,0x41:0}
def sx(v,b): return v-(1<<b) if v&(1<<(b-1)) else v
def gx_decode(cmds):
    """yield (op, params)"""
    i=0; n=len(cmds)
    while i<n:
        ops=cmds[i:i+4]; i+=4
        for op in ops:
            k=NP[op]; ps=struct.unpack_from('<%dI'%k,cmds,i) if k else (); i+=4*k
            yield op,ps
def pivot_mat(sel,neg,a,b):
    o=-1 if neg&1 else 1; c=-b if neg&2 else b; d=-a if neg&4 else a
    M={0:[o,0,0,0,a,b,0,c,d],1:[0,o,0,a,0,b,c,0,d],2:[0,0,o,a,b,0,c,d,0],
       3:[0,a,b,o,0,0,0,c,d],4:[a,0,b,0,o,0,c,0,d],5:[a,b,0,0,0,o,c,d,0],
       6:[0,a,b,0,c,d,o,0,0],7:[a,0,b,c,0,d,0,o,0],8:[a,b,0,c,d,0,0,0,o]}[sel]
    return np.array(M,float).reshape(3,3)
def node_mat(nd):
    M=np.eye(4)
    if nd['s']: M=np.diag(nd['s']+[1])@M
    if nd['r']:
        if nd['r'][0]=='pivot': R=pivot_mat(*nd['r'][1:])
        else: R=np.array(nd['r'][1]).reshape(3,3)
        # apicula Matrix3::new is column-major: args fill columns. so R_rowmajor = transpose
        R4=np.eye(4); R4[:3,:3]=R.T; M=R4@M
    if nd['t']: T=np.eye(4); T[:3,3]=nd['t']; M=T@M
    return M
def read_invbinds(d,off,n):
    out=[]
    for i in range(n):
        e=struct.unpack_from('<12i',d,off+i*84)
        m=np.array(e,float).reshape(4,3)/4096  # rows: 3 rows of basis then translation (column-major 4x3)
        M=np.eye(4); M[:3,:3]=m[:3,:3].T; M[:3,3]=m[3]
        out.append(M)
    return out
def ssc_mul(cur,p,m,objm):
    nd=m['nodes'][p[0]][1]; par=m['nodes'][p[1]][1]
    if p[0]==p[1] or not par['s'] : return cur@objm[p[0]]
    T=np.eye(4)
    if nd['t']: T[:3,3]=nd['t']
    Sinv=np.diag([1/x for x in par['s']]+[1])
    rest=np.linalg.inv(T)@objm[p[0]]
    return cur@T@Sinv@rest
def eval_model(d,m,node_mats=None):
    """Run render cmds -> list of draws (material, piece, stackmats snapshot)."""
    N=len(m['nodes'])
    objm=node_mats if node_mats is not None else [node_mat(nd) for _,nd in m['nodes']]
    inv=read_invbinds(d,m['invbind_off'],N)
    ssc=m['info']['scaling']==1
    stack=[np.eye(4)]*32; cur=np.eye(4); mat=None; up=m['info']['up']; draws=[]
    for op,p in m['rcmds']:
        if op in (6,0x26,0x46,0x66):
            if op==0x46: cur=stack[p[3]]
            if op==0x66: cur=stack[p[4]]
            if ssc and p[0]!=p[1] and m['nodes'][p[1]][1]['s'] and (p[2]&1):
                cur=cur@objm[p[0]][:, :]  # placeholder replaced below
            cur=ssc_mul(cur,p,m,objm) if ssc else cur@objm[p[0]]
            if op in (0x26,0x66): stack=list(stack); stack[p[3]]=cur
        elif op==3: cur=stack[p[0]]
        elif op==9:
            M=np.zeros((4,4))
            for k in range(p[1]):
                sp,ib,w=p[2+3*k:5+3*k]
                M+=w/256*(stack[sp]@inv[ib])
            stack=list(stack); stack[p[0]]=M; cur=M
        elif op in (4,0x24,0x44): mat=p[0]
        elif op==5: draws.append((mat,p[0],list(stack),cur.copy()))
        elif op==0xb: pass
    return draws,up
def decode_piece(cmds,stack,cur,scale):
    tris=[]; verts=[]; prim=None; uv=(0,0); nrm=(0,0,1); col=(1,1,1); v=np.zeros(3); M=cur
    strip=[]
    def emit(p):
        P=M@np.array([p[0]*scale,p[1]*scale,p[2]*scale,1.0])
        verts.append((P[:3].copy(),uv,nrm,col))
    for op,ps in gx_decode(cmds):
        if op==0x14: M=stack[ps[0]&31]
        elif op==0x1b: pass
        elif op==0x40: prim=ps[0]&3; start=len(verts)
        elif op==0x41: pass
        elif op==0x22: uv=(sx(ps[0]&0xffff,16)/16, sx(ps[0]>>16,16)/16)
        elif op==0x21: nrm=(sx(ps[0]&1023,10)/512,sx(ps[0]>>10&1023,10)/512,sx(ps[0]>>20&1023,10)/512)
        elif op==0x20: col=((ps[0]&31)/31,(ps[0]>>5&31)/31,(ps[0]>>10&31)/31)
        elif op in (0x23,0x24,0x25,0x26,0x27,0x28):
            if op==0x23: v=np.array([sx(ps[0]&0xffff,16),sx(ps[0]>>16,16),sx(ps[1]&0xffff,16)])/4096
            elif op==0x24: v=np.array([sx(ps[0]&1023,10),sx(ps[0]>>10&1023,10),sx(ps[0]>>20&1023,10)])/64
            elif op==0x25: v=np.array([sx(ps[0]&0xffff,16)/4096,sx(ps[0]>>16,16)/4096,v[2]])
            elif op==0x26: v=np.array([sx(ps[0]&0xffff,16)/4096,v[1],sx(ps[0]>>16,16)/4096])
            elif op==0x27: v=np.array([v[0],sx(ps[0]&0xffff,16)/4096,sx(ps[0]>>16,16)/4096])
            elif op==0x28: v=v+np.array([sx(ps[0]&1023,10),sx(ps[0]>>10&1023,10),sx(ps[0]>>20&1023,10)])/4096
            emit(v); i=len(verts)-1-start
            if prim==0 and i%3==2: tris.append((len(verts)-3,len(verts)-2,len(verts)-1))
            elif prim==1 and i%4==3: a=len(verts)-4; tris.append((a,a+1,a+2,a+3))
            elif prim==2 and i>=2:
                a,b,c=len(verts)-3,len(verts)-2,len(verts)-1
                tris.append((a,b,c) if i%2==0 else (b,a,c))
            elif prim==3 and i>=3 and i%2==1:
                a=len(verts)-4; tris.append((a,a+1,a+3,a+2))
    return verts,tris
def rgb555(c): return ((c&31)*255//31,(c>>5&31)*255//31,(c>>10&31)*255//31)
def decode_tex(t,paldata,paloff):
    from PIL import Image
    w,h,f,data=t['w'],t['h'],t['fmt'],t['data']
    pal=[rgb555(struct.unpack_from('<H',paldata,paloff+2*i)[0]) if paloff+2*i+2<=len(paldata) else (0,0,0) for i in range(256)]
    img=Image.new('RGBA',(w,h)); px=img.load()
    for y in range(h):
        for x in range(w):
            i=y*w+x
            if f==3: v=(data[i//2]>>(4*(i&1)))&15; a=0 if (v==0 and t['c0']) else 255; c=pal[v]
            elif f==2: v=(data[i//4]>>(2*(i&3)))&3; a=0 if (v==0 and t['c0']) else 255; c=pal[v]
            elif f==4: v=data[i]; a=0 if (v==0 and t['c0']) else 255; c=pal[v]
            elif f==1: b=data[i]; c=pal[b&31]; a=(b>>5)*255//7
            elif f==6: b=data[i]; c=pal[b&7]; a=(b>>3)*255//31
            elif f==7: v=struct.unpack_from('<H',data,2*i)[0]; c=rgb555(v); a=255 if v&0x8000 else 0
            else: c=(255,0,255); a=255
            px[x,y]=c+(a,)
    return img
def export_obj(fn,outdir,model_idx=0,node_mats=None,skip_nodes=()):
    d=open(fn,'rb').read(); r=read_bmd(d); m=r['models'][model_idx]
    os.makedirs(outdir,exist_ok=True)
    tex={t['name']:t for t in r['tex']['texs']}; pals={p['name']:p['off'] for p in r['tex']['pals']}
    for mt in m['mats']:
        tn=mt.get('tex')
        if tn and tn in tex:
            decode_tex(tex[tn],r['tex']['paldata'],pals.get(mt.get('pal'),0)).save(f"{outdir}/{mt['name']}.png")
    draws,up=eval_model(d,m,node_mats)
    o=open(f'{outdir}/model.obj','w'); ml=open(f'{outdir}/model.mtl','w'); o.write('mtllib model.mtl\n')
    vi=1
    for mat,pc,stack,cur in draws:
        mt=m['mats'][mat]; tn=mt.get('tex'); t=tex.get(tn)
        ml.write(f"newmtl {mt['name']}\nmap_Kd {mt['name']}.png\nmap_d {mt['name']}.png\n")
        verts,polys=decode_piece(m['shapes'][pc]['cmds'],stack,cur,up)
        o.write(f"o {m['shapes'][pc]['name']}\nusemtl {mt['name']}\n")
        for p,uv,n,c in verts:
            o.write('v %f %f %f %f %f %f\n'%(*p,*c))
            if t: o.write('vt %f %f\n'%(uv[0]/t['w'],1-uv[1]/t['h']))
            else: o.write('vt 0 0\n')
        for f in polys: o.write('f '+' '.join(f'{vi+k}/{vi+k}' for k in f)+'\n')
        vi+=len(verts)
    o.close(); ml.close()
    return m,draws
if __name__=='__main__':
    export_obj(sys.argv[1],sys.argv[2])

def basis_mat(ins):
    in0,in1,in2,in3,in4=ins
    inp=[in4,in0,in1,in2,in3]; out=[0]*6
    for i in range(5):
        out[i]=inp[i]>>3; out[5]=((out[5]<<3)|(inp[i]&7))&0xffff
    f=lambda x: sx(x&0x1fff,13)/4096
    a=np.array([f(out[1]),f(out[2]),f(out[3])]); b=np.array([f(out[4]),f(out[0]),f(out[5])]); c=np.cross(a,b)
    return np.column_stack([a,b,c])
def read_bca(d):
    stamp,ver,fsz,offs=container(d)
    bo=offs[0]; assert d[bo:bo+4]==b'JNT0'
    ents,_=dict_read(d,bo+8,4)
    anims=[]
    for e,nm,_ in ents:
        a=bo+u32(e,0)
        assert d[a:a+4]==b'J\0AC'
        nfr,nobj=struct.unpack_from('<HH',d,a+4); unk,pv,bs=struct.unpack_from('<III',d,a+8)
        objs=[]
        for i in range(nobj):
            o=a+u16(d,a+20+2*i)
            flags=u16(d,o); idx=d[o+3]; p=o+4
            cur={'flags':flags,'idx':idx,'t':[None]*3,'r':None,'s':[None]*3}
            if flags&1: objs.append(cur); continue
            def rd_curve(p,kind):
                info=u32(d,p); off=u32(d,p+4)
                st=info&0xffff; en=(info>>16)&0xfff; w=(info>>28)&3; rate=info>>30
                n=(en-st)>>rate
                return (st,en,rate,w,off,n)
            if not (flags>>1)&3:
                for k in range(3):
                    if (flags>>(3+k))&1: cur['t'][k]=('c',fx32(u32(d,p))); p+=4
                    else:
                        st,en,rate,w,off,n=rd_curve(p,'t'); p+=8
                        vals=[fx32(u32(d,a+off+4*j)) for j in range(n)] if w==0 else [fx16(u16(d,a+off+2*j)) for j in range(n)]
                        cur['t'][k]=('s',st,en,rate,vals)
            def fetch(x):
                if x>>15: sel,A,B=struct.unpack_from('<HHH',d,a+pv+6*(x&0x7fff)); 
                else: return basis_mat(struct.unpack_from('<5H',d,a+bs+10*(x&0x7fff)))
                return pivot_mat(sel&15,(sel>>4)&15,fx16(A),fx16(B)).T
            if not (flags>>6)&3:
                if (flags>>8)&1: cur['r']=('c',fetch(u16(d,p))); p+=4
                else:
                    st,en,rate,w,off,n=rd_curve(p,'r'); p+=8
                    cur['r']=('s',st,en,rate,[fetch(u16(d,a+off+2*j)) for j in range(n)])
            if not (flags>>9)&3:
                for k in range(3):
                    if (flags>>(11+k))&1: cur['s'][k]=('c',fx32(u32(d,p))); p+=8
                    else:
                        st,en,rate,w,off,n=rd_curve(p,'s'); p+=8
                        vals=[fx32(u32(d,a+off+8*j)) for j in range(n)] if w==0 else [fx16(u16(d,a+off+4*j)) for j in range(n)]
                        cur['s'][k]=('s',st,en,rate,vals)
            objs.append(cur)
        anims.append(dict(name=nm,nframes=nfr,objs=objs,raw_unk=unk))
    return anims
def sample(c,f,default):
    if c is None: return default
    if c[0]=='c': return c[1]
    st,en,rate,vals=c[1],c[2],c[3],c[4]
    i=(f-st)>>rate if f>st else 0
    i=min(max(i,0),len(vals)-1); return vals[i]
def anim_node_mats(m,anim,f):
    mats=[]
    for i,(nm,nd) in enumerate(m['nodes']):
        o=anim['objs'][i] if i<len(anim['objs']) else None
        if o is None or o['flags']&1: mats.append(node_mat(nd)); continue
        rest=node_mat(nd)
        t=[sample(o['t'][k],f,(nd['t'] or [0,0,0])[k]) for k in range(3)] if o['t'][0] is not None or o['t'][1] is not None else (nd['t'] or [0,0,0])
        s=[sample(o['s'][k],f,(nd['s'] or [1,1,1])[k]) for k in range(3)] if o['s'][0] is not None else (nd['s'] or [1,1,1])
        if o['r'] is not None: R=sample(o['r'],f,None)
        else:
            R=rest[:3,:3]@np.linalg.inv(np.diag(nd['s'])) if nd['s'] else rest[:3,:3]
        M=np.eye(4); M[:3,:3]=R@np.diag(s); M[:3,3]=t
        mats.append(M)
    return mats

def node_trs(m,anim,f):
    """per node (T(3), R(3x3 row-major math), S(3)) at frame f, NNS semantics incl. identity flags."""
    out=[]
    for i,(nm,nd) in enumerate(m['nodes']):
        rest_t=nd['t'] or [0,0,0]; rest_s=nd['s'] or [1,1,1]
        if nd['r'] is None: rest_r=np.eye(3)
        elif nd['r'][0]=='pivot': rest_r=pivot_mat(*nd['r'][1:]).T
        else: rest_r=np.array(nd['r'][1]).reshape(3,3).T
        o=anim['objs'][i] if (anim and i<len(anim['objs'])) else None
        if o is None or o['flags']&1: out.append((rest_t,rest_r,rest_s)); continue
        fl=o['flags']
        if fl&2: t=[0,0,0]
        elif fl&4: t=rest_t
        else: t=[sample(o['t'][k],f,0) for k in range(3)]
        if fl&0x40: r=np.eye(3)
        elif fl&0x80: r=rest_r
        else: r=sample(o['r'],f,None)
        if fl&0x200: s=[1,1,1]
        elif fl&0x400: s=rest_s
        else: s=[sample(o['s'][k],f,1) for k in range(3)]
        out.append((t,r,s))
    return out
def eval_frame(d,m,anim=None,f=0):
    trs=node_trs(m,anim,f)
    inv=read_invbinds(d,m['invbind_off'],len(m['nodes']))
    ssc=m['info']['scaling']==1
    def local(i,parent):
        t,r,s=trs[i]; T=np.eye(4); T[:3,3]=t; R=np.eye(4); R[:3,:3]=r; S=np.diag(list(s)+[1])
        if ssc and parent!=i:
            ps=trs[parent][2]; return T@np.diag([1/x for x in ps]+[1])@R@S
        return T@R@S
    stack=[np.eye(4)]*32; cur=np.eye(4); mat=None; draws=[]
    for op,p in m['rcmds']:
        if op in (6,0x26,0x46,0x66):
            if op==0x46: cur=stack[p[3]]
            if op==0x66: cur=stack[p[4]]
            cur=cur@local(p[0],p[1])
            if op in (0x26,0x66): stack=list(stack); stack[p[3]]=cur
        elif op==3: cur=stack[p[0]]
        elif op==9:
            M=np.zeros((4,4))
            for k in range(p[1]):
                sp,ib,w=p[2+3*k:5+3*k]; M+=w/256*(stack[sp]@inv[ib])
            stack=list(stack); stack[p[0]]=M; cur=M
        elif op in (4,0x24,0x44): mat=p[0]
        elif op==5: draws.append((mat,p[0],list(stack),cur.copy()))
    return draws,m['info']['up']
def export_frame_obj(fn,outdir,anim=None,f=0,name='model'):
    d=open(fn,'rb').read(); r=read_bmd(d); m=r['models'][0]
    os.makedirs(outdir,exist_ok=True)
    tex={t['name']:t for t in r['tex']['texs']}; pals={p['name']:p['off'] for p in r['tex']['pals']}
    for mt in m['mats']:
        tn=mt.get('tex'); p=f"{outdir}/{mt['name']}.png"
        if tn and tn in tex and not os.path.exists(p):
            decode_tex(tex[tn],r['tex']['paldata'],pals.get(mt.get('pal'),0)).save(p)
    draws,up=eval_frame(d,m,anim,f)
    o=open(f'{outdir}/{name}.obj','w'); ml=open(f'{outdir}/{name}.mtl','w'); o.write(f'mtllib {name}.mtl\n'); vi=1
    for mat,pc,stack,cur in draws:
        mt=m['mats'][mat]; t=tex.get(mt.get('tex'))
        ml.write(f"newmtl {mt['name']}\nmap_Kd {mt['name']}.png\nmap_d {mt['name']}.png\n")
        verts,polys=decode_piece(m['shapes'][pc]['cmds'],stack,cur,up)
        o.write(f"o {m['shapes'][pc]['name']}_{mt['name']}\nusemtl {mt['name']}\n")
        for p,uv,n,c in verts:
            o.write('v %f %f %f\n'%tuple(p)); o.write('vt %f %f\n'%((uv[0]/t['w'],1-uv[1]/t['h']) if t else (0,0)))
        for fc in polys: o.write('f '+' '.join(f'{vi+k}/{vi+k}' for k in fc)+'\n')
        vi+=len(verts)
    o.close(); ml.close()
