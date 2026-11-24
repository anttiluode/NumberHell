import numpy as np
exec(open(__file__.replace('closure.py','loop.py')).read().split("rng=np.random")[0])
def run(eps,gain,seed,T=400,rule="self"):
    rng=np.random.default_rng(seed); f=rng.standard_normal(N); f-=f.mean(); f/=np.linalg.norm(f)/16
    for t in range(T):
        a=head(f) if rule=="self" else rng.integers(1,N)
        f=(1-eps)*f+eps*np.tanh(gain*f*f[i^a])+0.01*rng.standard_normal(N); f-=f.mean(); f/=np.linalg.norm(f)/16
    e=fwht(f)**2; e/=e.sum(); top=np.argsort(e)[::-1]
    p,q=top[0],top[1]; group={p,q,p^q}
    return e[list(group)].sum(), e[top[:3]].sum()
for eps,gain in [(0.2,1),(0.5,1),(0.5,3),(0.9,1),(0.9,3)]:
    for rule in ("self","random"):
        r=np.array([run(eps,gain,s,rule=rule) for s in range(30)])
        print(f"eps={eps} gain={gain} {rule:6s}: energy in {{p,q,p^q}} {r[:,0].mean():.3f}  vs top-3 any {r[:,1].mean():.3f}")
