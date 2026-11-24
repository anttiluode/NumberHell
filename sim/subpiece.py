import numpy as np, warnings; warnings.filterwarnings("ignore")
exec(open(__file__.replace('subpiece.py','loop.py')).read().split("rng=np.random")[0])
H=N//2; j=np.arange(H)
def run(seed, eps=0.5, gain=1.0, T=600, drift=0.02):
    rng=np.random.default_rng(seed); x=rng.standard_normal(N); w=rng.standard_normal(H); prev=None; rec=[]; changes=0
    for t in range(T):
        w=np.sqrt(1-drift**2)*w+drift*rng.standard_normal(H); x[H:]=w/np.std(w)
        a=head(x)|128
        y=(1-eps)*x+eps*np.tanh(gain*x*x[i^a])+0.01*rng.standard_normal(N)
        b=y[:H]; b=b-b.mean(); b/=b.std()+1e-9; x[:H]=b
        if t>T//2 and prev is not None:
            now=np.corrcoef(np.abs(b), x[j^a])[0,1]
            old=np.corrcoef(np.abs(b), x[j^prev])[0,1] if prev!=a else np.nan
            rnd=np.corrcoef(np.abs(b), x[j^(128|int(rng.integers(0,128)))])[0,1]
            rec.append((now,old,rnd)); changes+= prev!=a
        prev=a
    r=np.array(rec); return np.nanmean(r,0), changes/len(rec)
R=[run(s) for s in range(20)]; m=np.nanmean([r[0] for r in R],0)
print(f"address changed on {np.mean([r[1] for r in R]):.2f} of ticks")
print(f"corr(|brain|, world partner): current address {m[0]:+.3f} | previous address (when it changed) {m[1]:+.3f} | random crossing address {m[2]:+.3f}")
