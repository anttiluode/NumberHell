import numpy as np
n=8; N=2**n; i=np.arange(N)
# 1D chessboards with square size 2^j are the Rademacher functions: sign = (-1)^(bit j of i)
board=lambda s: np.where((i//s)%2==0,1,-1)
assert all((board(2**j)==(-1)**((i>>j)&1)).all() for j in range(n))
# products of boards = 256 Walsh patterns, an orthogonal basis
H=np.array([np.prod([(-1)**((i>>j)&1) for j in range(n) if (a>>j)&1] or [np.ones(N)],axis=0) for a in range(N)])
assert np.allclose(H@H.T, N*np.eye(N))
rng=np.random.default_rng(0)
hits=0; costs=[]
for trial in range(200):
    heavy=rng.choice(N,3,replace=False)
    c=np.zeros(N); c[heavy]=rng.choice([-1,1],3)*rng.uniform(1,2,3)
    f=H.T@c/N*N**0.5 + 0.02*rng.standard_normal(N)       # signal + noise
    fhat=H@f/N**0.5
    # tree search: bucket = Walsh patterns whose low k bits equal alpha.
    # its energy is read from the vector itself: reshape to (2^(n-k) coarse, 2^k fine),
    # dot every fine row with the alpha-board, square, sum.
    def energy(alpha,k):
        M=f.reshape(2**(n-k),2**k)                       # row = one coarse block
        w=np.prod([(-1)**((np.arange(2**k)>>j)&1) for j in range(k) if (alpha>>j)&1] or [np.ones(2**k)],axis=0)
        return ((M@w)**2).sum()/2**k
    frontier=[(0,0)]; reads=0; thr=0.25
    for k in range(1,n+1):
        nxt=[]
        for a,_ in frontier:
            for b in (a, a|(1<<(k-1))):
                e=energy(b,k); reads+=1
                if e>thr: nxt.append((b,e))
        frontier=nxt
    found={a for a,_ in frontier}
    hits+= found==set(heavy); costs.append(reads)
    if trial==0: print("check energy at full depth equals coefficient^2:", np.allclose([energy(a,n) for a in heavy], fhat[heavy]**2))
print(f"exact recovery {hits}/200, bucket reads mean {np.mean(costs):.1f} (max {max(costs)}) vs 256 patterns")
