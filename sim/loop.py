import numpy as np
n=8;N=256;i=np.arange(N)
def fwht(v):
    v=v.copy();h=1
    while h<N:
        v=v.reshape(-1,2*h); a=v[:,:h].copy(); b=v[:,h:].copy(); v[:,:h]=a+b; v[:,h:]=a-b; v=v.reshape(-1); h*=2
    return v/np.sqrt(N)
def head(f):  # greedy descent: at level k keep the heavier child bucket
    a=0
    for k in range(1,n+1):
        best=None
        for b in (a,a|(1<<(k-1))):
            M=f.reshape(2**(n-k),2**k); w=np.prod([(-1)**((np.arange(2**k)>>j)&1) for j in range(k) if (b>>j)&1] or [np.ones(2**k)],axis=0)
            e=((M@w)**2).sum()/2**k
            if best is None or e>best[0]: best=(e,b)
        a=best[1]
    return a
rng=np.random.default_rng(1)
for eps in (0.2,0.5,0.9):
  for gain in (1.0,3.0):
    f=rng.standard_normal(N); f/=np.linalg.norm(f)/16
    seq=[]
    for t in range(400):
        a=head(f)
        prod=f*f[i^a]
        f=(1-eps)*f+eps*np.tanh(gain*prod)+0.01*rng.standard_normal(N)
        f=f-f.mean()
        f/=np.linalg.norm(f)/16
        seq.append(a)
    s=seq[200:]
    spec=np.abs(fwht(f)); top=np.argsort(spec)[::-1][:4]
    print(f"eps={eps} gain={gain}: distinct boards last200={len(set(s))}, last 12 {s[-12:]}, top patterns {list(top)} share {spec[top].round(1)}")
