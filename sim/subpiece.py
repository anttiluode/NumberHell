"""Half the vector is a world the rule cannot write; the other half (the brain) runs the NumberHell rule.
Pairing is forced across the boundary (bit 7 of a set). Three ways to choose the rest of the address:
  peek  - head reads brain AND world (the first version of this test)
  blind - head reads the brain only (world entries zeroed before the head sees them)
  fixed - no head, a = 128 forever (each brain cell always paired with the same world cell)
"""
import numpy as np, warnings; warnings.filterwarnings("ignore")
exec(open(__file__.replace('subpiece.py','loop.py')).read().split("rng=np.random")[0])
H=N//2; j=np.arange(H)
def run(seed, mode, eps=0.5, gain=1.0, T=600, drift=0.02):
    rng=np.random.default_rng(seed); x=rng.standard_normal(N); w=rng.standard_normal(H); prev=None; rec=[]; ch=0
    for t in range(T):
        w=np.sqrt(1-drift**2)*w+drift*rng.standard_normal(H); x[H:]=w/np.std(w)
        if mode=="peek": a=head(x)|128
        elif mode=="blind": a=head(np.r_[x[:H],np.zeros(H)])|128
        else: a=128
        y=(1-eps)*x+eps*np.tanh(gain*x*x[i^a])+0.01*rng.standard_normal(N)
        b=y[:H]; b=b-b.mean(); b/=b.std()+1e-9; x[:H]=b
        if t>T//2:
            wp=x[j^a]
            old=np.corrcoef(np.abs(b), x[j^prev])[0,1] if prev not in (None,a) else np.nan
            rec.append((np.corrcoef(b,wp)[0,1], np.corrcoef(np.abs(b),wp)[0,1], old,
                        np.corrcoef(np.abs(b), x[j^(128|int(rng.integers(1,128)))])[0,1]))
            ch+= prev is not None and prev!=a
        prev=a
    return np.nanmean(np.array(rec),0), ch/len(rec)
if __name__=="__main__":
    for mode in ("peek","blind","fixed"):
        R=[run(s,mode) for s in range(20)]; m=np.nanmean([r[0] for r in R],0)
        print(f"{mode:5s} address changes {np.mean([r[1] for r in R]):.2f} | signed corr(b,w) {m[0]:+.3f} | corr(|b|,w) {m[1]:+.3f} | previous-address partner {m[2]:+.3f} | random partner {m[3]:+.3f}")
