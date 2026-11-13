def lz10_enc(d):
    n=len(d); o=bytearray([0x10,n&255,n>>8&255,n>>16&255]); i=0
    heads={}
    def add(p):
        if p+3<=n: heads.setdefault(d[p:p+3],[]).append(p)
    while i<n:
        fp=len(o); o.append(0); fl=0
        for b in range(8):
            if i>=n: break
            best=0; bd=0
            for j in reversed(heads.get(d[i:i+3],[])):
                if i-j>4096: break
                l=3
                while l<18 and i+l<n and d[j+l]==d[i+l]: l+=1
                if l>best: best=l; bd=i-j
                if best==18: break
            if best>=3:
                fl|=0x80>>b; x=((best-3)<<12)|(bd-1); o+=bytes([x>>8,x&255])
                for k in range(best): add(i+k)
                i+=best
            else:
                o.append(d[i]); add(i); i+=1
        o[fp]=fl
    while len(o)%4: o.append(0)
    return bytes(o)
