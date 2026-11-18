// Web Audio engine: manifest-driven one-shots (with distance + pan), loops, layered adaptive music, global reverb.
const MUSIC = {
  //            amb   drone tension combat boss  title
  none:        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
  title:       [0.25, 0.0, 0.0, 0.0, 0.0, 1.0],
  explore:     [1.0, 0.85, 0.0, 0.0, 0.0, 0.0],
  tension:     [0.9, 0.9, 1.0, 0.0, 0.0, 0.0],
  combat:      [0.6, 0.6, 0.35, 1.0, 0.0, 0.0],
  boss:        [0.4, 0.35, 0.0, 0.0, 1.0, 0.0],
  quiet:       [0.7, 0.3, 0.0, 0.0, 0.0, 0.0],
};
const LAYERS = ['amb_factory', 'mus_drone', 'mus_tension', 'mus_combat', 'mus_boss', 'mus_title'];

export class AudioEngine {
  constructor() {
    this.ctx = null; this.buffers = {}; this.manifest = { sounds: {} }; this.last = {}; this.loops = {};
    this.lx = 0; this.lz = 0; this.muted = false; this.musicState = 'none'; this.layers = {}; this.ready = false;
  }
  init() {
    if (this.ctx) return;
    const C = window.AudioContext || window.webkitAudioContext; if (!C) return;
    const ctx = this.ctx = new C({ latencyHint: 'interactive' });
    this.master = ctx.createGain(); this.master.gain.value = 0.9;
    const comp = ctx.createDynamicsCompressor(); comp.threshold.value = -14; comp.knee.value = 12; comp.ratio.value = 5; comp.attack.value = 0.004; comp.release.value = 0.22;
    this.master.connect(comp); comp.connect(ctx.destination);
    this.sfx = ctx.createGain(); this.sfx.connect(this.master);
    this.music = ctx.createGain(); this.music.gain.value = 0.8; this.music.connect(this.master);
    // synthetic hall impulse
    const len = Math.floor(ctx.sampleRate * 3.2), ir = ctx.createBuffer(2, len, ctx.sampleRate);
    for (let c = 0; c < 2; c++) { const d = ir.getChannelData(c); let lp = 0;
      for (let i = 0; i < len; i++) { const t = i / len; const n = Math.random() * 2 - 1; lp += (n - lp) * (0.55 - 0.45 * t); d[i] = lp * Math.pow(1 - t, 2.6) * (i < 600 ? i / 600 : 1); } }
    this.reverb = ctx.createConvolver(); this.reverb.buffer = ir;
    const wet = ctx.createGain(); wet.gain.value = 0.5; this.reverb.connect(wet); wet.connect(this.master);
  }
  resume() { if (this.ctx && this.ctx.state !== 'running') this.ctx.resume(); }
  toggleMute() { this.muted = !this.muted; if (this.master) this.master.gain.value = this.muted ? 0 : 0.9; return this.muted; }

  async load(onProgress = () => {}) {
    this.init(); if (!this.ctx) return;
    try { const r = await fetch(`${import.meta.env.BASE_URL}audio/manifest.json`); const t = await r.text(); if (!t.trim().startsWith('<')) this.manifest = JSON.parse(t); } catch { /* no audio yet */ }
    const files = new Set(); for (const s of Object.values(this.manifest.sounds || {})) for (const f of s.files) files.add(f);
    let done = 0; const total = files.size || 1;
    await Promise.all([...files].map(async (f) => {
      try { const r = await fetch(`${import.meta.env.BASE_URL}audio/${f}`); const ab = await r.arrayBuffer(); this.buffers[f] = await this.ctx.decodeAudioData(ab); } catch { /* skip */ }
      onProgress(++done / total);
    }));
    this.ready = true;
  }
  has(name) { return !!this.manifest.sounds?.[name]; }
  setListener(x, z) { this.lx = x; this.lz = z; }

  play(name, o = {}) {
    const s = this.manifest.sounds?.[name]; if (!s || !this.ctx) return null;
    const now = this.ctx.currentTime;
    if (now - (this.last[name] || -1) < (o.minGap ?? 0.035)) return null;
    this.last[name] = now;
    const buf = this.buffers[s.files[(Math.random() * s.files.length) | 0]]; if (!buf) return null;
    let gain = (s.gain ?? 1) * (o.gain ?? 1), pan = 0, send = o.reverb ?? 0.25;
    if (o.x !== undefined) {
      const dx = o.x - this.lx, dz = o.z - this.lz, d = Math.hypot(dx, dz); const ref = o.ref ?? 7;
      if (d > 48) return null;
      gain *= 1 / (1 + (d / ref) * (d / ref)); pan = Math.max(-0.85, Math.min(0.85, dx / 12)); send = Math.min(0.9, send + d * 0.02);
    }
    if (gain < 0.004) return null;
    const src = this.ctx.createBufferSource(); src.buffer = buf; src.playbackRate.value = o.rate ?? 1;
    const g = this.ctx.createGain(); g.gain.value = gain;
    let node = g; src.connect(g);
    if (pan !== 0 && this.ctx.createStereoPanner) { const p = this.ctx.createStereoPanner(); p.pan.value = pan; g.connect(p); node = p; }
    node.connect(this.sfx);
    if (send > 0) { const sg = this.ctx.createGain(); sg.gain.value = send; node.connect(sg); sg.connect(this.reverb); }
    src.start(now + (o.delay ?? 0));
    return src;
  }

  // Named sustained loop with adjustable gain (furnace roar, blade hum, heartbeat, alarm ...).
  loop(name, gain, rate, force) {
    const s = this.manifest.sounds?.[name]; if (!s || !this.ctx) return;
    let L = this.loops[name];
    if (!L) {
      if (gain <= 0.001 && !force) return;
      const buf = this.buffers[s.files[0]]; if (!buf) return;
      const src = this.ctx.createBufferSource(); src.buffer = buf; src.loop = true;
      const g = this.ctx.createGain(); g.gain.value = 0; src.connect(g); g.connect(name.startsWith('mus_') || name === 'amb_factory' ? this.music : this.sfx);
      src.start(); L = this.loops[name] = { src, g, base: s.gain ?? 1 };
    }
    L.g.gain.setTargetAtTime(gain * L.base, this.ctx.currentTime, 0.25);
    if (rate) L.src.playbackRate.setTargetAtTime(rate, this.ctx.currentTime, 0.2);
  }
  stopLoops() { for (const [k, L] of Object.entries(this.loops)) { if (LAYERS.includes(k)) continue; L.g.gain.setTargetAtTime(0, this.ctx.currentTime, 0.1); } }

  setMusic(state, time = 1.2) {
    if (!this.ctx || state === this.musicState) return;
    this.musicState = state; const mix = MUSIC[state] || MUSIC.none;
    LAYERS.forEach((name, i) => {
      const s = this.manifest.sounds?.[name]; if (!s) return;
      let L = this.loops[name];
      if (!L && mix[i] > 0) { this.loop(name, 0, undefined, true); L = this.loops[name]; }
      if (L) L.g.gain.setTargetAtTime(mix[i] * L.base, this.ctx.currentTime, time / 3);
    });
  }
}
