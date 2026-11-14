// Cry maker engine (2026-11-14). One file, two places: the website inlines it (build_site.py puts it where
// /*CRY_ENGINE*/ stands) and the game export runs it in Node on the ROM's own cries, so a cry sounds the same on the
// website and in the game. A cry is a RECIPE, never a sound file: which official cries it starts from ("hgss:<dex>",
// like the footprints) and how they are bent. No Nintendo audio is stored in the repo. How it decides: docs/CRIES.md.
//
//   CryEngine.suggest(mon, facts, rng)  -> a recipe with its reasons (what CREATE / RETRY on the website show)
//   CryEngine.render(recipe, sources)   -> Float32Array, mono, 13379 Hz (the rate of HeartGold's cries)
//   CryEngine.knobsOf(recipe) / tweak(recipe, knobs) -> the website's sliders (pitch, length, glide, ...) and back
//   sources = {<dex>: {data: Float32Array, rate: Number}}  - the official cries the recipe names
//             {own: {...}}  - for a layer {own: true}: the Pokemon's own sound (recipe.audio, assets/cries/<pokemon>.wav)
(function (root) {
  "use strict";
  const OUT_RATE = 13379;            // HeartGold's cry rate (hg-engine sound/cries/*.wav)
  const WORK = OUT_RATE * 2;         // everything is bent at twice that, then halved, so bending up adds no grit
  const MAX_LEN = 1.6;               // seconds; Origin's cries are 0.1-2.4 s, the sound memory is small
  const OWN_LEN = 2.0;               // seconds of an own sound that are kept (bent up, 2 s still fill a 1.6 s cry)
  const VERSION = 1;

  // ---------- random numbers that can be repeated (a recipe keeps its seed) ----------
  function rng(seed) {
    let a = seed >>> 0;
    const next = () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    next.range = (lo, hi) => lo + (hi - lo) * next();
    next.chance = p => next() < p;
    next.pick = list => list[Math.floor(next() * list.length)];
    return next;
  }

  // ---------- sound ----------
  function peakOf(x) { let p = 1e-6; for (let i = 0; i < x.length; i++) if (Math.abs(x[i]) > p) p = Math.abs(x[i]); return p; }
  function sinc(x) { return x === 0 ? 1 : Math.sin(Math.PI * x) / (Math.PI * x); }
  // Windowed-sinc resampling with a low-pass at the lower Nyquist, so nothing folds back.
  function resample(x, from, to) {
    if (from === to) return Float32Array.from(x);
    const ratio = to / from, cut = Math.min(1, ratio) * 0.94, half = 16, n = Math.max(1, Math.round(x.length * ratio));
    const out = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const centre = i / ratio, first = Math.ceil(centre - half / cut), last = Math.floor(centre + half / cut);
      let sum = 0, weights = 0;
      for (let j = Math.max(0, first); j <= Math.min(x.length - 1, last); j++) {
        const d = (j - centre) * cut, w = Math.abs(d) >= half ? 0 : 0.42 + 0.5 * Math.cos(Math.PI * d / half) + 0.08 * Math.cos(2 * Math.PI * d / half);
        const k = cut * sinc(d) * w;
        sum += x[j] * k; weights += k;
      }
      out[i] = weights ? sum / weights : 0;
    }
    return out;
  }
  // Longer or shorter without changing the pitch: overlapping grains (40 ms, 75 % overlap).
  function stretch(x, factor, rate) {
    if (Math.abs(factor - 1) < 0.01) return x;
    const size = Math.round(0.04 * rate), hopOut = Math.round(size / 4), hopIn = hopOut / factor;
    const n = Math.round(x.length * factor) + size, out = new Float32Array(n), norm = new Float32Array(n);
    const win = Float32Array.from({length: size}, (_, i) => 0.5 - 0.5 * Math.cos(2 * Math.PI * i / size));
    for (let k = 0; ; k++) {
      const src = Math.round(k * hopIn), dst = k * hopOut;
      if (src >= x.length || dst + size > n) break;
      for (let i = 0; i < size; i++) {
        const v = src + i < x.length ? x[src + i] : 0;
        out[dst + i] += v * win[i]; norm[dst + i] += win[i];
      }
    }
    for (let i = 0; i < n; i++) out[i] = norm[i] > 0.05 ? out[i] / norm[i] : 0;
    return out.subarray(0, Math.round(x.length * factor));
  }
  // Played faster or slower like a tape: pitch and length change together, the way the old games bent cries.
  // The pitch can glide (sweep, semitones from start to end) and wobble (vibrato).
  function bend(x, semi, sweep, vib) {
    const out = [];
    let pos = 0, t = 0;
    const len = x.length;
    while (pos < len - 1 && out.length < WORK * 4) {
      const progress = pos / len;
      const wobble = vib && vib.depth ? vib.depth * Math.sin(2 * Math.PI * vib.rate * t) : 0;
      const step = Math.pow(2, (semi + (sweep || 0) * progress + wobble) / 12);
      const i = Math.floor(pos), f = pos - i;
      const a = x[Math.max(0, i - 1)], b = x[i], c = x[Math.min(len - 1, i + 1)], d = x[Math.min(len - 1, i + 2)];
      out.push(b + 0.5 * f * (c - a + f * (2 * a - 5 * b + 4 * c - d + f * (3 * (b - c) + d - a))));   // cubic
      pos += step; t += 1 / WORK;
    }
    return Float32Array.from(out);
  }

  function render(recipe, sources) {
    const layers = [];
    for (const layer of recipe.layers || []) {
      const src = layer.own ? sources.own : sources[layer.dex];      // own: a sound someone uploaded or recorded
      if (!src) throw new Error(layer.own ? "the own sound is not loaded" : "the cry of #" + layer.dex + " is not loaded");
      let x = resample(src.data, src.rate, WORK);
      if (layer.rev) x = Float32Array.from(x).reverse();
      x = stretch(x, recipe.stretch || 1, WORK);
      x = bend(x, layer.semi || 0, recipe.sweep || 0, recipe.vib);
      layers.push({x, at: Math.round((layer.at || 0) * WORK), gain: layer.gain == null ? 1 : layer.gain});
    }
    const echo = recipe.echo && recipe.echo.gain ? recipe.echo : null;
    const total = Math.min(Math.round((recipe.len || MAX_LEN) * WORK), Math.max(...layers.map(l => l.at + l.x.length), 1) + (echo ? Math.round(echo.ms / 1000 * WORK * 2) : 0));
    let mix = new Float32Array(total);
    for (const l of layers) for (let i = 0; i < l.x.length && l.at + i < total; i++) mix[l.at + i] += l.x[i] * l.gain;

    // tone: below 0 darker (a low-pass coming down from 7 kHz), above 0 brighter (a high-pass going up to 700 Hz)
    const tone = recipe.tone || 0;
    const lowCut = 60 + Math.max(0, tone) * 640, highCut = tone < 0 ? 7000 - 5600 * Math.min(1, -tone) : 0;
    let lp = 0, hpIn = 0, hpOut = 0;
    const aHigh = Math.exp(-2 * Math.PI * lowCut / WORK), aLow = highCut ? 1 - Math.exp(-2 * Math.PI * highCut / WORK) : 1;
    for (let i = 0; i < total; i++) {
      let v = mix[i];
      if (highCut) { lp += aLow * (v - lp); v = lp; }
      const y = aHigh * (hpOut + v - hpIn); hpIn = v; hpOut = y;
      mix[i] = y;
    }
    if (recipe.drive) {
      const k = 1 + 5 * recipe.drive, scale = 1 / Math.tanh(k), peak = peakOf(mix);
      for (let i = 0; i < total; i++) mix[i] = Math.tanh(k * mix[i] / peak) * scale * peak;
    }
    if (recipe.ring && recipe.ring.mix) {
      for (let i = 0; i < total; i++) mix[i] *= 1 - recipe.ring.mix + recipe.ring.mix * Math.sin(2 * Math.PI * recipe.ring.hz * i / WORK);
    }
    if (echo) {
      const d = Math.round(echo.ms / 1000 * WORK);
      for (let i = total - 1; i >= d; i--) mix[i] += echo.gain * mix[i - d] + (i >= 2 * d ? echo.gain * echo.gain * mix[i - 2 * d] : 0);
    }
    const fade = Math.round(0.06 * WORK);                       // a short fade so the cut is never a click
    for (let i = Math.max(0, total - fade); i < total; i++) mix[i] *= (total - i) / fade;
    for (let i = 0; i < Math.min(total, 40); i++) mix[i] *= i / 40;
    let out = resample(mix, WORK, OUT_RATE);
    const peak = peakOf(out);
    for (let i = 0; i < out.length; i++) out[i] = out[i] / peak * 0.89;   // -1 dB, like a mastered cry
    return out;
  }

  // ---------- choosing ----------
  const STAGE_PITCH = {first: 2, middle: 0, final: -2, single: 0};   // semitones: babies higher, big final stages lower
  const SHAPE_FAMILY = {"a quadruped body": "legs", "an upright body on two legs with a tail": "upright", "an upright body on two legs without a tail": "upright",
    "a head and legs": "legs", "a head and arms": "arms", "a head and a base": "blob", "only a head": "blob", "a serpentine body": "long", "a body with fins": "water",
    "a body with one pair of wings": "wings", "a body with two or more pairs of wings": "bug", "an insect body with a hard shell": "bug",
    "tentacles or many legs": "bug", "several bodies joined together": "blob"};
  const TYPE_FX = {          // how a type tends to colour a cry; each is only a chance, so RETRY gives other mixes
    Electric: [["ring", 0.55], ["bright", 0.4], ["vib", 0.25]], Steel: [["ring", 0.5], ["echo", 0.25], ["dark", 0.2]],
    Ghost: [["echo", 0.6], ["rev", 0.35], ["vib", 0.4], ["dark", 0.3]], Psychic: [["vib", 0.5], ["echo", 0.35], ["rev", 0.2], ["bright", 0.2]],
    Dark: [["dark", 0.55], ["drive", 0.3], ["down", 0.35]], Water: [["vib", 0.45], ["dark", 0.2]], Ice: [["bright", 0.45], ["echo", 0.3], ["ring", 0.15]],
    Fire: [["drive", 0.4], ["up", 0.25]], Dragon: [["drive", 0.45], ["dark", 0.35], ["down", 0.3]], Ground: [["dark", 0.45], ["drive", 0.3], ["slow", 0.35]],
    Rock: [["dark", 0.4], ["drive", 0.35], ["slow", 0.3]], Flying: [["up", 0.45], ["bright", 0.3], ["fast", 0.3]], Bug: [["fast", 0.4], ["vib", 0.35], ["bright", 0.3]],
    Poison: [["vib", 0.45], ["down", 0.25], ["ring", 0.2]], Grass: [["bright", 0.35], ["up", 0.25]], Fairy: [["bright", 0.5], ["up", 0.35], ["echo", 0.2]],
    Fighting: [["fast", 0.45], ["drive", 0.3], ["short", 0.4]], Normal: [["up", 0.2], ["down", 0.2]],
  };
  const words = {ring: "a metallic buzz", bright: "a brighter sound", dark: "a darker sound", vib: "a wobble in the voice", echo: "an echo",
    rev: "a second voice played backwards", drive: "a rough edge", up: "a rising pitch", down: "a falling pitch", fast: "said quicker",
    slow: "drawn out", short: "cut short"};

  function sizeOf(m) {                                  // metres and kilograms when known, else a guess from stats and stage
    const h = Number(m.h) || 0, w = Number(m.w) || 0;
    return {h, w, guess: !(h || w)};
  }
  function score(mon, o, footprint) {
    let s = 0;
    const why = [];
    if (footprint && o.n === footprint.n) { s += 3; why.push("its footprint is " + o.name + "'s"); }
    else if (footprint && o.line === footprint.line) { s += 2; why.push("its footprint comes from " + o.name + "'s line"); }
    if (mon.shape && o.shape === mon.shape) { s += 4; why.push("same body plan"); }
    else if (mon.shape && SHAPE_FAMILY[o.shape] === SHAPE_FAMILY[mon.shape]) { s += 2; why.push("a similar body plan"); }
    const types = (mon.types || []).filter(t => o.types.includes(t));
    if (types.length) { s += 3 * types.length; why.push(types.length > 1 ? "both types" : "also " + types[0]); }
    const eggs = (mon.egg || []).filter(g => g !== "undiscovered" && o.egg.includes(g));
    if (eggs.length) { s += 2 * eggs.length; why.push("same egg group"); }
    if (mon.stage && o.stage === mon.stage) s += 1.5;
    if (mon.legend && o.legend) { s += 4; why.push("legendary too"); }
    else if (!mon.legend && o.legend) s -= 5;
    const a = sizeOf(mon);
    if (a.h && o.h) s -= Math.min(3, Math.abs(Math.log(a.h / o.h)) * 1.4);
    if (a.w && o.w) s -= Math.min(3, Math.abs(Math.log(a.w / o.w)) * 0.7);
    if (mon.bst) s -= Math.abs(mon.bst - o.bst) / 160;
    if (mon.color && o.color === mon.color) s += 0.5;
    return {o, s, why};
  }

  // mon = {types, egg, shape, h, w, bst, stage ("first" "middle" "final" "single"), legend, color, footprint (dex),
  //        line: [{stage index, recipe}] for relatives that already have a cry, myIndex, used: {dex: count}}
  // facts = the official Pokemon (data/engine/official_species.json)
  function suggest(mon, facts, seed) {
    const r = rng(seed);
    const reasons = [];
    const byDex = new Map(facts.map(o => [o.n, o]));
    const footprint = mon.footprint ? byDex.get(mon.footprint) : null;

    // 1. A relative already has a cry: the line keeps its sound, bigger stages lower and slower, smaller ones higher.
    const kin = (mon.line || []).filter(k => k.recipe && Array.isArray(k.recipe.layers) && k.recipe.layers.length);
    if (kin.length && r.chance(0.85)) {
      const k = kin.slice().sort((a, b) => Math.abs(a.index - mon.myIndex) - Math.abs(b.index - mon.myIndex))[0];
      const steps = mon.myIndex - k.index;
      const recipe = JSON.parse(JSON.stringify(k.recipe));
      const shift = -steps * r.range(2, 3.5);
      recipe.layers.forEach(l => { l.semi = clampSemi((l.semi || 0) + shift + r.range(-0.4, 0.4)); });
      recipe.stretch = clamp((recipe.stretch || 1) * (1 + steps * r.range(0.04, 0.1)), 0.8, 1.3);
      if (steps > 0 && recipe.layers.length < 3 && r.chance(0.5)) {
        const deep = pickDonors(mon, facts, r, recipe.layers.map(l => l.dex).filter(Boolean), 1)[0];
        if (deep) { recipe.layers.push({dex: deep.o.n, semi: clampSemi(r.range(-6, -3)), gain: round(r.range(0.25, 0.4)), at: round(r.range(0, 0.05)), rev: false});
          reasons.push("Adds a low " + deep.o.name + " under it, because it is bigger"); }
      }
      // a little of its own on top, so RETRY still gives different ones
      recipe.tone = round(clamp((recipe.tone || 0) + r.range(-0.25, 0.25) - steps * 0.08, -1, 1));
      const twist = r();
      if (twist < 0.25) { recipe.vib = recipe.vib ? null : {rate: round(r.range(4.5, 9)), depth: round(r.range(0.15, 0.5))}; reasons.push(recipe.vib ? "Adds a wobble" : "Without the wobble"); }
      else if (twist < 0.45) { recipe.echo = recipe.echo ? null : {ms: Math.round(r.range(60, 150)), gain: round(r.range(0.2, 0.35))}; reasons.push(recipe.echo ? "Adds an echo" : "Without the echo"); }
      else if (twist < 0.6) { recipe.sweep = round(clamp((recipe.sweep || 0) + r.range(-2, 2), -6, 6)); reasons.push(recipe.sweep >= 0 ? "Its pitch rises a little more" : "Its pitch falls a little more"); }
      else if (twist < 0.7 && steps > 0) { recipe.drive = round(clamp((recipe.drive || 0) + r.range(0.1, 0.3), 0, 1)); reasons.push("A rougher edge, it is bigger"); }
      recipe.seed = seed; recipe.v = VERSION;
      reasons.unshift("Keeps the sound of " + k.name + "'s cry, " + (steps > 0 ? Math.round(-shift) + " steps lower, because it is " + (steps > 1 ? "two stages" : "one stage") + " further"
        : Math.round(shift) + " steps higher, because it is " + (steps < -1 ? "two stages" : "one stage") + " earlier"));
      recipe.reasons = reasons;
      return recipe;
    }

    // 2. Otherwise: start from official Pokemon that are like this one.
    const [base, second] = pickDonors(mon, facts, r, [], 2);
    const recipe = {v: VERSION, seed, layers: [], stretch: 1, sweep: 0, vib: null, ring: null, echo: null, tone: 0, drive: 0, len: MAX_LEN};
    let semi = (STAGE_PITCH[mon.stage] || 0) - (STAGE_PITCH[base.o.stage] || 0);
    const a = sizeOf(mon);
    if (a.h && base.o.h) semi += clamp(-4 * Math.log2(a.h / base.o.h), -5, 5);
    else if (a.w && base.o.w) semi += clamp(-1.5 * Math.log2(a.w / base.o.w), -5, 5);
    if (mon.legend) semi -= r.range(1, 3);
    semi += r.range(-2.5, 2.5);
    recipe.layers.push({dex: base.o.n, semi: clampSemi(semi), gain: 1, at: 0, rev: false});
    reasons.push("Starts from " + base.o.name + "'s cry" + (base.why.length ? ": " + base.why.slice(0, 3).join(", ") : ""));
    const STAGE_WORD = {first: "a first stage", middle: "a middle stage", final: "a final stage", single: "a Pokemon that does not evolve"};
    const pitchWhy = a.h && base.o.h ? (a.h > base.o.h ? ", it is taller than " : ", it is smaller than ") + base.o.name
      : mon.stage && mon.stage !== base.o.stage && STAGE_PITCH[mon.stage] !== STAGE_PITCH[base.o.stage] ? ", it is " + STAGE_WORD[mon.stage] + " and " + base.o.name + " is " + STAGE_WORD[base.o.stage]
      : mon.legend ? ", it is legendary" : "";
    reasons.push("");                                   // the pitch, filled in at the end when it is final
    if (second && r.chance(mon.legend ? 0.8 : 0.6)) {
      const gain = round(r.range(0.3, 0.55)), semi2 = clampSemi(semi + r.range(-5, 3));
      recipe.layers.push({dex: second.o.n, semi: semi2, gain, at: round(r.range(0, 0.12)), rev: false});
      reasons.push("Mixed with a quieter " + second.o.name + (second.why.length ? " (" + second.why.slice(0, 2).join(", ") + ")" : ""));
    }

    // 3. Its types, body and size colour the sound. Each effect is a chance with a random amount.
    const fx = new Set();
    for (const t of mon.types || []) for (const [name, p] of TYPE_FX[t] || []) if (r.chance(p)) fx.add(name);
    if (mon.legend) { if (r.chance(0.6)) fx.add("echo"); if (r.chance(0.4)) fx.add("slow"); }
    if (SHAPE_FAMILY[mon.shape] === "wings" && r.chance(0.4)) fx.add("up");
    if (a.w > 150 || (a.guess && mon.stage === "final" && mon.bst >= 520)) { if (r.chance(0.5)) fx.add("slow"); if (r.chance(0.4)) fx.add("dark"); }
    if (fx.has("bright") && fx.has("dark")) fx.delete(r.chance(0.5) ? "bright" : "dark");
    if (fx.has("up") && fx.has("down")) fx.delete(r.chance(0.5) ? "up" : "down");
    if (fx.has("fast") && fx.has("slow")) fx.delete(r.chance(0.5) ? "fast" : "slow");
    while (fx.size > 3) fx.delete(r.pick([...fx]));             // never everything at once
    if (fx.has("ring")) recipe.ring = {hz: round(r.range(40, 130)), mix: round(r.range(0.15, 0.4))};
    if (fx.has("bright")) recipe.tone = round(r.range(0.25, 0.7));
    if (fx.has("dark")) recipe.tone = round(-r.range(0.25, 0.7));
    if (fx.has("vib")) recipe.vib = {rate: round(r.range(4.5, 9)), depth: round(r.range(0.15, 0.6))};
    if (fx.has("echo")) recipe.echo = {ms: Math.round(r.range(60, 150)), gain: round(r.range(0.2, 0.38))};
    if (fx.has("drive")) recipe.drive = round(r.range(0.15, 0.5));
    if (fx.has("up")) recipe.sweep = round(r.range(1, 3.5));
    if (fx.has("down")) recipe.sweep = round(-r.range(1, 3.5));
    if (fx.has("fast")) recipe.stretch = round(r.range(0.8, 0.92));
    if (fx.has("slow")) recipe.stretch = round(r.range(1.08, 1.25));
    if (fx.has("short")) recipe.len = round(r.range(0.7, 1));
    if (fx.has("rev") && recipe.layers.length > 1) recipe.layers[1].rev = true;
    else fx.delete("rev");
    if (fx.size) reasons.push("Its " + (mon.types || []).join("/") + " side" + (mon.legend ? " and being legendary" : "") + " gives " + [...fx].map(f => words[f]).join(", "));

    // 4. Never just an official cry with a new name: too close to its starting cry -> bend it further.
    const change = () => Math.abs(recipe.layers[0].semi) / 2 + (recipe.layers.length > 1 ? 1.5 : 0) + fx.size * 0.8 + Math.abs(recipe.stretch - 1) * 5;
    if (change() < 2) {
      const push = (recipe.layers[0].semi < 0 || (recipe.layers[0].semi === 0 && r.chance(0.5)) ? -1 : 1) * r.range(1.5, 3);
      recipe.layers.forEach(l => { l.semi = clampSemi(l.semi + push); });
      if (change() < 2 && second) {
        recipe.layers.push({dex: second.o.n, semi: clampSemi(recipe.layers[0].semi + r.range(-4, 2)), gain: round(r.range(0.3, 0.5)), at: round(r.range(0, 0.1)), rev: false});
        reasons.push("Mixed with a quieter " + second.o.name + " so it is its own cry");
      } else reasons.push("Bent " + (push < 0 ? "lower" : "higher") + " so it is its own cry, not " + base.o.name + "'s");
    }
    const steps = Math.round(recipe.layers[0].semi);
    reasons[1] = steps ? (steps < 0 ? "Lower" : "Higher") + " by " + Math.abs(steps) + " step" + (Math.abs(steps) === 1 ? "" : "s") + pitchWhy : "";
    recipe.reasons = reasons.filter(Boolean);
    return recipe;
  }
  function pickDonors(mon, facts, r, skip, count) {
    const footprint = mon.footprint ? facts.find(o => o.n === mon.footprint) : null;
    const ranked = facts.filter(o => !skip.includes(o.n)).map(o => score(mon, o, footprint))
      .map(x => Object.assign(x, {s: x.s - 1.5 * ((mon.used || {})[x.o.n] || 0)}))      // other mons already use it: a little less likely
      .sort((a, b) => b.s - a.s).slice(0, 14);
    const chosen = [];
    while (chosen.length < count && ranked.length) {
      const top = ranked[0].s, weights = ranked.map(x => Math.exp((x.s - top) / 2.2));
      let pick = r() * weights.reduce((a, b) => a + b, 0), i = 0;
      while (i < ranked.length - 1 && (pick -= weights[i]) > 0) i++;
      chosen.push(ranked[i]);
      const line = ranked[i].o.line;
      for (let j = ranked.length - 1; j >= 0; j--) if (ranked[j].o.line === line) ranked.splice(j, 1);   // the second voice comes from another line
    }
    return chosen;
  }
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const round = v => Math.round(v * 100) / 100;
  const clampSemi = v => round(clamp(v, -12, 7));        // above +7 the bending would add grit at the game's rate

  // ---------- the sliders on the website (15 Nov 2026) ----------
  // Arvind: "bare en retry knapp og en som endrer pitch og slik". A try's settings as slider values, and back:
  // pitch is steps up or down from the try (all voices together), the rest are the recipe's own values.
  function knobsOf(recipe) {
    return {pitch: 0, stretch: recipe.stretch || 1, sweep: recipe.sweep || 0, tone: recipe.tone || 0, drive: recipe.drive || 0,
      vib: recipe.vib ? recipe.vib.depth : 0, echo: recipe.echo ? recipe.echo.gain : 0, ring: recipe.ring ? recipe.ring.mix : 0};
  }
  function tweak(recipe, k) {
    const out = JSON.parse(JSON.stringify(recipe));
    out.layers.forEach(l => { l.semi = clampSemi((l.semi || 0) + (k.pitch || 0)); });
    out.stretch = round(clamp(k.stretch, 0.7, 1.4));
    out.sweep = round(clamp(k.sweep, -6, 6));
    out.tone = round(clamp(k.tone, -1, 1));
    out.drive = round(clamp(k.drive, 0, 1));
    out.vib = k.vib > 0 ? {rate: recipe.vib ? recipe.vib.rate : 6, depth: round(clamp(k.vib, 0, 1))} : null;
    out.echo = k.echo > 0 ? {ms: recipe.echo ? recipe.echo.ms : 100, gain: round(clamp(k.echo, 0, 0.6))} : null;
    out.ring = k.ring > 0 ? {hz: recipe.ring ? recipe.ring.hz : 70, mix: round(clamp(k.ring, 0, 0.6))} : null;
    return out;
  }

  const api = {VERSION, OUT_RATE, MAX_LEN, OWN_LEN, rng, render, suggest, resample, knobsOf, tweak};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.CryEngine = api;
})(typeof window !== "undefined" ? window : globalThis);
