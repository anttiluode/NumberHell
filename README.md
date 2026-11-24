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

Test: indices 128–255 are a world the rule cannot write (a slowly drifting random signal); indices 0–127 are the brain, updated by the same rule, with the pairing forced across the boundary (bit 7 of a set). 20 runs × 600 ticks, second half measured:

| correlation | value |
|---|---:|
| brain value vs its world partner | ≈ 0.0 |
| brain loudness \|b\| vs its world partner, current address | +0.68 |
| same, partner under the previous address (ticks where it changed) | +0.40 |
| same, random crossing address | 0.00 |

The brain does not copy the world and does not invert it. Its loudness becomes a half-wave image of the world: tanh(g·b·w) amplifies b where the partner w is positive and drives it to zero where w is negative. The image is addressed by the board the head picked and partly outlasts an address change. It is a one-sided gate, not a predictive or inverse model.

## Not

- Not new mathematics (Rademacher/Walsh, Goldreich–Levin, Kushilevitz–Mansour; state-built matrices are what attention does).
- Not a learner or a benchmark.
- Not covered by the VP ≠ VNP paper: each zoom level is a cut of the 8 bits, the kind of cut it prices, but choosing the board from the state is branching, outside polynomial circuits.
