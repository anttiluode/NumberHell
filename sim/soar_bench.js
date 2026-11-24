const { makeWorld } = require("./soar_core.js");
const T = 4000, seeds = 12;
const cfgs = { "fixed window": { mode: "fixed", mark: 0 }, "random flight": { mode: "random", mark: 0 }, "flight, no marks": { mode: "fly", mark: 0 }, "flight, marks attract": { mode: "fly", mark: 1 }, "flight, marks repel": { mode: "fly", mark: -1 }, "flight, head state ignored": { mode: "fly", mark: 0, useH: false } };
for (const [name, c] of Object.entries(cfgs)) {
  const sc = []; for (let s = 1; s <= seeds; s++) { const w = makeWorld(Object.assign({ seed: s * 7919 }, c)); let total = 0; for (let t = 0; t < T; t++) w.step(); sc.push(w.head.eaten); }
  const m = sc.reduce((a, b) => a + b) / seeds, sd = Math.sqrt(sc.reduce((a, b) => a + (b - m) ** 2, 0) / (seeds - 1));
  console.log(name.padEnd(24), "food eaten per 1000 ticks", (m / T * 1000).toFixed(1), "±", (sd / Math.sqrt(seeds) / T * 1000).toFixed(1));
}
