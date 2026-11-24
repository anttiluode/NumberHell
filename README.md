# Number Hell

One vector of 256 numbers that reads itself. Open `index.html` (GitHub Pages: Settings → Pages → Deploy from branch → `main` / root).

## The picture

- A position number 0–255 is 8 bits. A 1D chessboard with squares of size 2^j flips sign on bit j, so there are 8 of them (Rademacher functions).
- Multiplying chessboards gives all 256 patterns (Walsh functions). They are orthogonal: every subset sum of the 256 numbers is a combination of them. 2²⁵⁶ subsets, 256 independent readings.
- **The head.** At zoom level k the vector is cut into coarse blocks of 2^k fine numbers. Each fine block is multiplied by a small chessboard and summed, and the squares add up to the energy of a whole family of patterns. The head keeps the louder family at each level: 16 readings instead of 256. This is the Goldreich–Levin / Kushilevitz–Mansour search, here greedy.
- **The loop.** The board `a` the head finds rewrites the vector:

```
x[i] ← (1−ε)·x[i] + ε·tanh(gain · x[i] · x[i XOR a]) + noise,   then remove the mean and rescale to RMS 1
```

So x_next = W(x)·x: the vector chooses the address it reads, and what it reads changes the vector that chooses the next address.

## Measured (`sim/`)

`sim/chessboard_search.py`: 3 hidden patterns plus noise in a 256-vector; the thresholded tree search found exactly the right 3 in 200/200 trials, with about 39 bucket decisions on average (max 42) instead of 256. Each decision still touches the whole vector, so at this size it is not faster than a fast Walsh transform; the search pays when the vector is huge and only sampled.

`sim/closure.py`: 30 starts × 400 ticks per row. Share of energy in the closed family {p, q, p⊕q} of the two loudest patterns (a random vector: about 1.2% for any three patterns).

| ε | gain | head picks the board | random board |
|---:|---:|---:|---:|
| 0.2 | 1 | 0.127 | 0.072 |
| 0.5 | 1 | 0.163 | 0.072 |
| 0.5 | 3 | 0.184 | 0.081 |
| 0.9 | 1 | 0.515 | 0.376 |
| 0.9 | 3 | 0.433 | 0.607 |

- Closed families come from the product rule: multiplying chessboards makes chessboards (XOR of bits). They appear with random boards too.
- Self-reading roughly doubles concentration at moderate mixing; at the strongest setting random picking concentrates more. It changes the dynamics; it is not simply better.
- Without removing the mean the loop collapses onto the flat board every time.


### The forced symmetry, and half the vector as a world (`sim/subpiece.py`)

`x[i]·x[i XOR a]` takes the same value at i and at i XOR a, so the nonlinear drive is always symmetric under the pairing: the 128 patterns k with popcount(k AND a) odd get no drive and only decay. That includes the board a itself whenever it has an odd number of 1-bits (every single chessboard does), so reading such a board starves it. Closed, the loop can only crystallise toward symmetric patterns.

Test: indices 128–255 are a world the rule cannot write (a slowly drifting random signal); indices 0–127 are the brain, updated by the same rule, with the pairing forced across the boundary (bit 7 of a set). 20 runs × 600 ticks, second half measured. Three ways to pick the rest of the address:

| address | changes per tick | signed corr(b, partner w) | corr(\|b\|, partner w) | partner under previous address | random partner |
|---|---:|---:|---:|---:|---:|
| head reads brain and world (`peek`) | 0.19 | +0.02 | +0.68 | +0.40 | 0.00 |
| head reads brain only (`blind`) | 0.35 | +0.00 | +0.54 | +0.31 | 0.00 |
| no head, a = 128 forever (`fixed`) | 0 | 0.00 | **+0.78** | – | –0.01 |

- The brain's signs carry nothing about the world: the update is odd in b, so a cell keeps whatever sign it had. Its loudness carries the positive half of the world: for small b the world partner sets the cell's gain, 1 − ε + ε·g·w, so cells paired with positive w grow and the rest fade.
- **The head does not help here.** A fixed wire gives the clearest image; letting the head move the wiring blurs it, and a blind head blurs it more. The "previous address" numbers are mostly the (1 − ε) fade of last tick's image.
- The world is a one-way tape: the brain cannot push on it and feel it push back. This is a multiplicative gate, not a predictive or inverse model. (Earlier version of this section, corrected after Sol and Neon pointed out the peeking head and the missing fixed-wire control.)

## Soar (`soar.html`)

The head leaves the chessboard: a 16-number eye flies over a 64×64 world, seeing a 4×4 picture at any of 5 heights. It climbs when the view is flat, dives toward what stands out, eats sparkles at ground level. 12 worlds × 4,000 ticks (`sim/soar_bench.js`), about 250 sparkles per 1,000 ticks:

| eye | eaten / 1000 ticks |
|---|---:|
| fixed wire (one ground window) | 1.0 ± 0.2 |
| random flight | 27.3 ± 1.3 |
| flies, writes nothing | **205.6 ± 2.0** |
| flies, writes a lure where it ate | 17.8 ± 1.2 |
| flies, writes a warning where it ate | 144.4 ± 1.8 |
| flies, its 16-number state ignored | 207.5 ± 2.5 |

When the world is 256× bigger than the eye, moving the reader wins by two orders of magnitude. All of it comes from the climb-and-dive rule; the NumberHell state adds nothing. Writing into the world hurt: lures trap the eye on its own memories, warnings push it away from springs that keep giving.

## Not

- Not new mathematics (Rademacher/Walsh, Goldreich–Levin, Kushilevitz–Mansour; state-built matrices are what attention does).
- Not a learner or a benchmark.
- Not covered by the VP ≠ VNP paper: each zoom level is a cut of the 8 bits, the kind of cut it prices, but choosing the board from the state is branching, outside polynomial circuits.
