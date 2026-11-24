/* Soar core: a 16-number head flying over a 64x64 world it can mark. */
function makeWorld(opts) {
  const o = Object.assign({ G: 64, springs: 3, spawn: 0.25, spread: 3, drift: 0.04, seed: 1,
    eps: 0.5, gain: 1.0, mark: 1.0, markDecay: 0.997, mode: "fly" }, opts);
  let s = o.seed >>> 0 || 1;
  const rnd = () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
  const gauss = () => Math.sqrt(-2 * Math.log(rnd() + 1e-12)) * Math.cos(2 * Math.PI * rnd());
  const G = o.G, F = new Float32Array(G * G), M = new Float32Array(G * G);
  const springs = [...Array(o.springs)].map(() => ({ x: rnd() * G, y: rnd() * G, vx: 0, vy: 0 }));
  const food = [];
  const head = { x: G / 2, y: G / 2, L: 4, h: new Float32Array(16).map(() => gauss()), view: new Float32Array(16), eaten: 0, trail: [] };
  const wrap = (v) => ((v % G) + G) % G;
  function field() {
    F.fill(0);
    for (const f of food) {
      const r = 2;
      for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
        const X = wrap(Math.round(f.x) + dx), Y = wrap(Math.round(f.y) + dy);
        F[Y * G + X] += f.e * Math.exp(-(dx * dx + dy * dy) / 2);
      }
    }
    if (o.mark) for (let k = 0; k < G * G; k++) F[k] += o.mark * M[k];
  }
  function look() {
    const L = head.L, cell = 1 << L, span = 4 * cell, x0 = head.x - span / 2, y0 = head.y - span / 2;
    for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) {
      let sum = 0;
      for (let yy = 0; yy < cell; yy++) for (let xx = 0; xx < cell; xx++) sum += F[wrap(Math.floor(y0 + r * cell + yy)) * G + wrap(Math.floor(x0 + c * cell + xx))];
      head.view[r * 4 + c] = sum / (cell * cell);
    }
  }
  function step() {
    // world: springs wander, food appears near springs and slowly fades
    for (const sp of springs) { sp.vx = 0.95 * sp.vx + o.drift * gauss(); sp.vy = 0.95 * sp.vy + o.drift * gauss(); sp.x = wrap(sp.x + sp.vx); sp.y = wrap(sp.y + sp.vy); }
    if (rnd() < o.spawn) { const sp = springs[Math.floor(rnd() * springs.length)]; food.push({ x: wrap(sp.x + o.spread * gauss()), y: wrap(sp.y + o.spread * gauss()), e: 1, age: 0 }); }
    for (const f of food) { f.e *= 0.995; f.age++; }
    for (let k = food.length - 1; k >= 0; k--) if (food[k].e < 0.05) food.splice(k, 1);
    for (let k = 0; k < G * G; k++) M[k] *= o.markDecay;
    field();
    const events = [];
    if (o.mode === "fixed") { head.L = 0; look(); }
    else {
      look();
      // the head's 16 numbers: world enters as gain (NumberHell rule), then RMS 1
      const v = head.view; let vm = 0, vs = 0; for (const a of v) vm += a / 16; for (const a of v) vs += (a - vm) ** 2 / 16; vs = Math.sqrt(vs) || 1;
      let hs = 0;
      for (let k = 0; k < 16; k++) { const vn = (v[k] - vm) / vs; head.h[k] = (1 - o.eps) * head.h[k] + o.eps * Math.tanh(o.gain * head.h[k] * vn) + 0.02 * gauss(); hs += head.h[k] ** 2; }
      hs = Math.sqrt(hs / 16) || 1; for (let k = 0; k < 16; k++) head.h[k] /= hs;
      // attention: where the gain-weighted view is loudest
      let best = 0, bv = -1e9; for (let k = 0; k < 16; k++) { const a = (o.useH === false ? 1 : Math.abs(head.h[k])) * (v[k] - vm); if (a > bv) { bv = a; best = k; } }
      const contrast = (Math.max(...v) - vm) / (Math.abs(vm) + 0.05);
      const cell = 1 << head.L;
      if (o.mode === "random") { head.x = wrap(head.x + 3 * gauss()); head.y = wrap(head.y + 3 * gauss()); head.L = Math.max(0, Math.min(4, head.L + (rnd() < 0.5 ? -1 : 1))); }
      else {
        const tx = head.x + ((best % 4) - 1.5) * cell, ty = head.y + (Math.floor(best / 4) - 1.5) * cell;
        head.x = wrap(head.x + 0.6 * (tx - head.x)); head.y = wrap(head.y + 0.6 * (ty - head.y));
        if (contrast > 1.2 && bv > 0.02) head.L = Math.max(0, head.L - 1); else if (contrast < 0.6 || bv <= 0.02) head.L = Math.min(4, head.L + 1);
      }
    }
    // eating: only at the finest zoom, inside the 4x4 window
    if (head.L === 0) {
      for (let k = food.length - 1; k >= 0; k--) {
        const f = food[k], dx = ((f.x - head.x + G * 1.5) % G) - G / 2, dy = ((f.y - head.y + G * 1.5) % G) - G / 2;
        if (Math.abs(dx) <= 2 && Math.abs(dy) <= 2) {
          head.eaten += f.e; events.push({ x: f.x, y: f.y, e: f.e }); food.splice(k, 1);
          // write back: the world keeps a mark where food was found
          for (let yy = -3; yy <= 3; yy++) for (let xx = -3; xx <= 3; xx++) M[wrap(Math.round(f.y) + yy) * G + wrap(Math.round(f.x) + xx)] += 0.25 * Math.exp(-(xx * xx + yy * yy) / 6);
        }
      }
    }
    if (o.mode === "fixed") { head.x = G / 2; head.y = G / 2; }
    head.trail.push([head.x, head.y, head.L]); if (head.trail.length > 60) head.trail.shift();
    return events;
  }
  return { o, F, M, food, springs, head, step, G };
}
if (typeof module !== "undefined") module.exports = { makeWorld };
