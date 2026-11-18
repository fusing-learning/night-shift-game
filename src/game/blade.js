import * as THREE from 'three';
import { BLADE, DEBUG } from '../config.js';
import { angDiff } from './rig.js';

// Energy blade. Style 0 is the original swing (still handled in player.js); 1–3 are driven from here.
// COMBO is the default; pick another with ?blade=0|1|3, cycle live with B (when ?blade or ?bladelab is in the URL).
export const STYLES = [
  { name: 'ORIGINAL', desc: 'the first swing, kept for comparison' },
  { name: 'CRESCENT', desc: 'wind-up, eased strike, tapered crescent trail, hits land as the blade passes' },
  { name: 'COMBO', desc: 'slash, backhand, then a lunging spin finisher (keep pressing)' },
  { name: 'LIGHTSWEEP', desc: 'the blade is a light: strobe after-images, floor scrape and burn' },
];

export const DEFAULT_STYLE = 2;          // COMBO
const TAU = Math.PI * 2;
const ARM = 0.36;                         // shoulder -> hand (sum of the three arm bones)
const ARM_REST = 0.9;                     // where the blade arm points (model yaw) while the body spins
const outCubic = (k) => 1 - (1 - k) ** 3, outSine = (k) => Math.sin(k * Math.PI / 2), inOut = (k) => (k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2);
const clamp01 = (k) => Math.min(1, Math.max(0, k));
const _v = new THREE.Vector3(), _d = new THREE.Vector3(), _w = new THREE.Vector3(), _s = new THREE.Vector3();
const FWD = new THREE.Vector3(0, 0, 1), UP = new THREE.Vector3(0, 1, 0);
// lowest elevation that keeps the tip just above the floor (shoulder is ~0.62 m up)
const FLOOR_EL = (m) => Math.asin(Math.max(-1, (0.04 - 0.62) / (ARM + m.reach)));
const dirOf = (out, th, el) => out.set(Math.sin(th) * Math.cos(el), Math.sin(el), Math.cos(th) * Math.cos(el));

// ── move tables ──
// Angles are yaw relative to the aim at swing start (+ = the player's left); el = blade elevation (+ up), blended a0 -> a1.
// wind: cock back by `pull`; strike: ease-out sweep that overshoots a1 by `over`; recover: settle, trail drains, blade retracts.
// reach = blade length from the hand; width = trail band at the blade; lag = how far back in time the trail reaches.
const BASE = {
  wind: 0.05, strike: 0.12, recover: 0.13, pull: 0.35, over: 0.16, el0: 0.3, el1: -0.1, reach: 1.62, width: 1.05, lag: 0.075,
  dmg: 1, kb: 1, stop: 0.05, lunge: 1.4, light: 10, lightRange: 5, pitch: 1, cd: 0.42, color: [0.25, 0.95, 1.4], spin: false, ghosts: false, scorch: false,
};
const M = (o) => ({ ...BASE, ...o });
const CRESCENT = M({});
const COMBO = [
  M({ a0: 1.35, a1: -1.25, el0: 0.26, el1: -0.08, wind: 0.04, strike: 0.11, recover: 0.12, dmg: 0.8, kb: 0.7, stop: 0.04, lunge: 3.2, pitch: 1.06 }),
  M({ a0: -1.3, a1: 1.35, el0: -0.06, el1: 0.34, wind: 0.04, strike: 0.11, recover: 0.12, dmg: 0.8, kb: 0.7, stop: 0.04, lunge: 3.2, pitch: 0.95 }),
  M({ a0: 0.9, a1: 0.9 - TAU - 0.5, el0: 0.07, el1: 0.03, wind: 0.11, strike: 0.27, recover: 0.2, pull: 0.55, over: 0.1, reach: 1.95, width: 1.4, lag: 0.13,
    dmg: 1.45, kb: 1.7, stop: 0.09, lunge: 7.5, light: 22, lightRange: 7, pitch: 0.8, spin: true, cd: 0.55, color: [0.3, 1.0, 1.6] }),
];
const LIGHTSWEEP = M({
  el0: 0.42, el1: -0.62, wind: 0.08, strike: 0.14, recover: 0.2, pull: 0.45, over: 0.1, width: 0.16, lag: 0.13,
  dmg: 1.15, kb: 1.2, stop: 0.07, lunge: 1, light: 24, lightRange: 8, pitch: 0.86, ghosts: true, scorch: true, cd: 0.55, color: [0.45, 1.05, 1.6],
});

// ── shaders ──
const VS = 'attribute vec2 aT; varying vec2 vT; void main(){ vT = aT; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }';
const fxMat = (fragmentShader, uniforms) => new THREE.ShaderMaterial({
  vertexShader: VS, fragmentShader, uniforms, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
});
// blade: bright white core, coloured halo, soft hilt and pointed tip. vT.x = across (-1..1), vT.y = along (0..1)
const BLADE_FS = /* glsl */`uniform vec3 uCol; uniform float uA, uHot; varying vec2 vT;
  void main(){ float x = min(1.0, abs(vT.x)); float core = smoothstep(0.45, 0.04, x); float halo = (1.0-x)*(1.0-x);
    float ends = smoothstep(0.0, 0.05, vT.y) * smoothstep(1.0, 0.8, vT.y);
    vec3 c = uCol*halo*1.25 + vec3(1.0)*core*(1.8 + uHot);
    gl_FragColor = vec4(c*ends*uA, 1.0); }`;
// swept trail: vT.x = 0 at the blade .. 1 at the tail, vT.y = 0 inner .. 1 outer edge
const TRAIL_FS = /* glsl */`uniform vec3 uCol; uniform float uA, uRim; varying vec2 vT;
  void main(){ float k = clamp(vT.x, 0.0, 1.0), v = clamp(vT.y, 0.0, 1.0);   // clamp: pow() of a tiny negative is NaN, and bloom smears NaN over the whole frame
    float along = pow(1.0 - k, 1.7);
    float body = v*v*(3.0-2.0*v); body *= body;
    float rim = smoothstep(0.8, 0.97, v) * uRim;
    float streaks = 0.82 + 0.18*sin(v*46.0 + k*5.0);
    vec3 c = uCol*body*streaks*1.1 + vec3(1.0)*rim*(1.0-k)*1.6 + vec3(1.0)*pow(1.0-k, 7.0)*body*0.9;
    gl_FragColor = vec4(c*along*uA, 1.0); }`;
// impact streak: a lens-shaped cut line through the contact point. vT in 0..1
const STREAK_FS = /* glsl */`uniform vec3 uCol; uniform float uA; varying vec2 vT;
  void main(){ float x = vT.x*2.0-1.0, y = abs(vT.y*2.0-1.0); float w = max(1e-3, 1.0 - x*x);
    float a = smoothstep(w, w*0.2, y); float core = smoothstep(w*0.4, 0.0, y);
    gl_FragColor = vec4((uCol*a*0.8 + vec3(1.0)*core*1.1)*uA, 1.0); }`;
// expanding ground ring: bright outer edge, soft inside
const RING_FS = /* glsl */`uniform vec3 uCol; uniform float uA; varying vec2 vT;
  void main(){ float r = length(vT*2.0-1.0); float a = smoothstep(0.8, 0.985, r) * smoothstep(1.0, 0.985, r);
    gl_FragColor = vec4((uCol*a + vec3(1.0)*pow(a, 6.0))*uA, 1.0); }`;
// floor burn left by the scraping tip: white -> orange -> red as it cools
const SCORCH_FS = /* glsl */`uniform float uAge; varying vec2 vT;
  void main(){ float v = abs(vT.y*2.0-1.0); float a = smoothstep(1.0, 0.15, v) * smoothstep(0.0, 0.08, vT.x) * smoothstep(1.0, 0.85, vT.x);
    float heat = clamp(1.0 - uAge/1.7, 0.0, 1.0);
    vec3 hot = mix(vec3(2.4, 0.55, 0.08), vec3(2.6, 2.2, 1.8), smoothstep(0.82, 1.0, heat));
    vec3 c = mix(vec3(0.35, 0.03, 0.0), hot, smoothstep(0.0, 0.55, heat));
    float flick = 0.85 + 0.15*sin(vT.x*70.0 + uAge*24.0);
    gl_FragColor = vec4(c*a*heat*heat*flick, 1.0); }`;

function bladeGeometry() {
  // two crossed tapered quads along +Z so the blade reads from any camera angle
  const P = [], T = [], I = [], w0 = 0.1, w1 = 0.022;
  for (const ax of [0, 1]) {
    const b = P.length / 3;
    for (const [s, z, w] of [[-1, 0, w0], [1, 0, w0], [-1, 1, w1], [1, 1, w1]]) { P.push(ax ? 0 : s * w, ax ? s * w : 0, z); T.push(s, z); }
    I.push(b, b + 1, b + 2, b + 1, b + 3, b + 2);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); g.setAttribute('aT', new THREE.Float32BufferAttribute(T, 2)); g.setIndex(I);
  return g;
}

// Triangle strip with per-frame CPU positions (a few dozen vertices).
class Strip {
  constructor(parent, n, mat) {
    this.n = n; const t = new Float32Array((n + 1) * 4), idx = [];
    for (let i = 0; i <= n; i++) { const k = i / n; t[i * 4] = k; t[i * 4 + 1] = 0; t[i * 4 + 2] = k; t[i * 4 + 3] = 1; if (i < n) { const j = i * 2; idx.push(j, j + 1, j + 2, j + 1, j + 3, j + 2); } }
    const g = this.geo = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array((n + 1) * 6), 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aT', new THREE.BufferAttribute(t, 2)); g.setIndex(idx);
    this.p = g.attributes.position.array;
    this.mesh = new THREE.Mesh(g, mat); this.mesh.frustumCulled = false; this.mesh.renderOrder = 8; parent.add(this.mesh);
  }
  set(i, a, b) { const p = this.p, j = i * 6; p[j] = a.x; p[j + 1] = a.y; p[j + 2] = a.z; p[j + 3] = b.x; p[j + 4] = b.y; p[j + 5] = b.z; }
  commit() { this.geo.attributes.position.needsUpdate = true; }
}

export class BladeSystem {
  constructor(G, P) {
    this.G = G; this.P = P;
    const lab = DEBUG.has('bladelab');
    const want = DEBUG.get('blade');
    this.style = want ? Math.max(0, Math.min(STYLES.length - 1, Math.round(+want) || 0)) : DEFAULT_STYLE;
    this.canCycle = lab || DEBUG.has('blade');
    this.s = null; this.side = 1; this.step = 0; this.chainT = 0; this.queued = false; this.bodyYaw = 0; this.cdT = 0;

    // world-space swing frame: origin at the shoulder, yaw locked to the aim at swing start
    this.frame = new THREE.Group(); G.scene.add(this.frame);
    this.bladeGeo = bladeGeometry();
    this.blade = new THREE.Mesh(this.bladeGeo, fxMat(BLADE_FS, { uCol: { value: new THREE.Color() }, uA: { value: 1 }, uHot: { value: 0 } }));
    this.blade.renderOrder = 9; this.blade.frustumCulled = false; this.frame.add(this.blade);
    this.trail = new Strip(this.frame, 64, fxMat(TRAIL_FS, { uCol: { value: new THREE.Color() }, uA: { value: 0 }, uRim: { value: 1 } }));
    // strobe after-images (lightsweep)
    this.ghosts = Array.from({ length: 8 }, () => {
      const m = new THREE.Mesh(this.bladeGeo, fxMat(BLADE_FS, { uCol: { value: new THREE.Color() }, uA: { value: 0 }, uHot: { value: 0 } }));
      m.renderOrder = 8; m.frustumCulled = false; G.scene.add(m); return { m, t: 0, life: 0 };
    });
    // impact cut lines
    const sg = new THREE.PlaneGeometry(1, 1); sg.rotateX(-Math.PI / 2);
    sg.setAttribute('aT', sg.attributes.uv);
    this.streaks = Array.from({ length: 10 }, () => {
      const m = new THREE.Mesh(sg, fxMat(STREAK_FS, { uCol: { value: new THREE.Color() }, uA: { value: 0 } }));
      m.renderOrder = 9; m.frustumCulled = false; G.scene.add(m); return { m, t: 0, life: 0, len: 1, w: 0.2 };
    });
    this.streakNext = 0;
    // finisher shock ring
    const rg = new THREE.RingGeometry(0.8, 1, 72); rg.rotateX(-Math.PI / 2); rg.setAttribute('aT', rg.attributes.uv);
    this.ring = new THREE.Mesh(rg, fxMat(RING_FS, { uCol: { value: new THREE.Color(0.3, 1.0, 1.6) }, uA: { value: 0 } }));
    this.ring.renderOrder = 7; this.ring.frustumCulled = false; G.scene.add(this.ring); this.ringT = 9;
    // floor burns
    this.scorches = Array.from({ length: 3 }, () => { const s = new Strip(G.scene, 40, fxMat(SCORCH_FS, { uAge: { value: 99 } })); s.mesh.renderOrder = 3; return { s, t: 99 }; });
    this.scorchNext = 0;
    // one light that travels with the blade (fixed for the whole run so the shader light count never changes)
    this.light = new THREE.PointLight(0x5ad8ff, 0, 6, 1.6); G.scene.add(this.light);
    this.hidden = false;   // everything starts visible (off-stage) so the boot-time shader compile covers it
    this.frame.position.set(0, -50, 0);
  }

  get name() { return STYLES[this.style].name; }
  get active() { return !!this.s; }
  cycle(d = 1) { this.setStyle((this.style + d + STYLES.length) % STYLES.length); }
  setStyle(i) {
    this.cancel(); this.style = i; this.step = 0; this.cdT = 0;
    this.G.hud.toast(`BLADE ${this.style} · ${this.name}`); this.G.audio.play('blade_ignite', { gain: 0.5 });
  }
  cancel() { if (this.s) { this.s = null; this.P.bladeT = 0; } this.queued = false; }

  // ── input + timeline (called from Player.update every frame; style 0 only ticks leftover effects) ──
  update(dt, can, inp) {
    const P = this.P;
    if (!this.hidden) this.hideAll();
    this.cdT -= dt; this.chainT -= dt;
    if (this.style === 0) { this.updateFx(dt); return; }
    if (P.dodgeT > 0 || P.dead) this.cancel();
    if (this.style === 2 && !this.s && this.step > 0 && this.chainT <= 0) this.step = 0;     // combo window lapsed
    if (can && inp.melee && P.dodgeT <= 0) this.queued = true;                               // buffered until it can start
    const s = this.s;
    if (s) {
      const m = s.m, strikeEnd = m.wind + m.strike, th0 = this.theta(s, Math.max(s.t, m.wind));
      s.t += dt;
      if (s.t >= m.wind && !s.struck) this.onStrike(s);
      // hits land as the blade actually passes each target
      if (s.t >= m.wind && s.t - dt < strikeEnd + 0.03) this.sweep(s, th0, this.theta(s, Math.min(s.t, strikeEnd)));
      if (m.ghosts && s.t >= m.wind && s.t - dt < strikeEnd) this.spawnGhosts(s);
      if (this.style === 2 && this.queued && this.step < 2 && s.t >= strikeEnd + 0.03) { this.step++; this.begin(); }   // cancel recovery into the next step
      else if (s.t >= strikeEnd + m.recover) this.finish(s);
      else P.bladeT = Math.max(0.001, strikeEnd + m.recover * 0.5 - s.t);   // blocks the gun and slows the walk, like the old swing
    }
    if (!this.s && this.queued) {
      if (this.cdT <= 0 && P.bladeCd <= 0) this.begin();
      else if (this.cdT > 0.16 || P.bladeCd > 0.16) this.queued = false;     // only keep presses made just before the cooldown ends
    }
    this.updateFx(dt);
  }
  finish(s) {
    if (s.scrape?.length > 1) this.burn(s);
    this.s = null; this.P.bladeT = 0;
    if (this.style === 2) { if (this.step < 2) { this.step++; this.chainT = 0.3; } else { this.step = 0; this.cdT = 0.3; } }
  }

  begin() {
    const P = this.P, G = this.G;
    let m;
    if (this.style === 1) m = CRESCENT; else if (this.style === 3) m = LIGHTSWEEP; else m = COMBO[this.step];
    let a0 = m.a0, a1 = m.a1;
    if (a0 === undefined) { this.side = -this.side; a0 = this.side * 1.3; a1 = -this.side * 1.3; }
    this.s = { m, t: 0, yaw: P.facing, a0, a1, dir: Math.sign(a1 - a0), hit: new Set(), n: 0, stop: 0, struck: false, ghostAt: null, scrape: m.scorch ? [] : null };
    this.queued = false;
    if (this.style !== 2) this.cdT = m.cd;
    G.audio.play('blade_ignite', { gain: 0.3, rate: 1.3 / m.pitch });
  }
  onStrike(s) {
    const G = this.G, P = this.P, m = s.m; s.struck = true;
    G.audio.play('blade_swing', { gain: 1, rate: m.pitch * (0.96 + Math.random() * 0.08) });
    if (m.spin) { G.audio.play('blade_swing', { gain: 0.7, rate: m.pitch * 0.75 }); G.shake(0.25); }
    // step into the swing
    P.kx += Math.sin(s.yaw) * m.lunge; P.kz += Math.cos(s.yaw) * m.lunge;
    if (m.spin) { this.ringT = 0; this.ring.position.set(P.x, 0.06, P.z); this.ring.visible = true; G.lights.burst(P.x, 0.6, P.z, 0x5ad8ff, 30, 8, 0.25); }
  }

  // blade yaw (relative to the swing frame) at time t
  theta(s, t) {
    const m = s.m, d = s.dir, back = s.a0 - d * m.pull, end = s.a1 + d * m.over;
    if (t < m.wind) return s.a0 - d * m.pull * outSine(t / m.wind);
    t -= m.wind;
    if (t < m.strike) return back + (end - back) * outCubic(t / m.strike);
    t -= m.strike;
    return end - d * m.over * 0.35 * inOut(clamp01(t / m.recover));
  }
  elev(s, th) {
    const m = s.m, back = s.a0 - s.dir * m.pull, end = s.a1 + s.dir * m.over;
    const el = m.el0 + (m.el1 - m.el0) * clamp01((th - back) / (end - back));
    return Math.max(el, FLOOR_EL(m));      // never below the floor: a low blade lies along it and scrapes
  }
  range(m) { return BLADE.range * (ARM + m.reach) / (ARM + 1.62); }

  sweep(s, th0, th1) {
    const G = this.G, P = this.P, m = s.m;
    const lo = Math.min(th0, th1), hi = Math.max(th0, th1), mid = (lo + hi) / 2, R = this.range(m);
    for (const e of G.enemies) {
      if (e.dead || e.untargetable || s.hit.has(e)) continue;
      const dx = e.x - P.x, dz = e.z - P.z, d = Math.hypot(dx, dz);
      if (d - e.radius > R) continue;
      let phi = angDiff(s.yaw, Math.atan2(dx, dz)); phi += TAU * Math.round((mid - phi) / TAU);
      const pad = d < e.radius + 0.45 ? 1.2 : Math.asin(Math.min(1, e.radius / Math.max(d, 1e-3))) + 0.06;
      if (phi < lo - pad || phi > hi + pad) continue;
      s.hit.add(e); this.hit(s, e, phi);
    }
    // cut fireballs out of the air
    for (const f of G.weapons.shots) {
      if (f.kind !== 'fire' || f.life <= 0) continue;
      const dx = f.x - P.x, dz = f.z - P.z, d = Math.hypot(dx, dz); if (d > R) continue;
      let phi = angDiff(s.yaw, Math.atan2(dx, dz)); phi += TAU * Math.round((mid - phi) / TAU);
      if (phi < lo - 0.2 || phi > hi + 0.2) continue;
      f.life = 0; G.particles.sparks(f.x, 0.7, f.z, dx / d, dz / d, 12, [1.4, 0.6, 0.2], 5);
    }
  }

  hit(s, e, phi) {
    const G = this.G, P = this.P, m = s.m;
    const wa = s.yaw + phi, rx = Math.sin(wa), rz = Math.cos(wa);
    const tx = Math.cos(wa) * s.dir, tz = -Math.sin(wa) * s.dir;          // blade travel direction at the contact
    let kx = rx * 0.55 + tx * 0.85, kz = rz * 0.55 + tz * 0.85; const kl = Math.hypot(kx, kz) || 1; kx /= kl; kz /= kl;
    const hx = e.x - rx * e.radius * 0.5, hz = e.z - rz * e.radius * 0.5, hy = Math.max(0.35, e.height);
    e.damage(BLADE.damage * m.dmg, kx, kz, 'blade', hx, hz);
    e.knock(kx * BLADE.knockback * m.kb, kz * BLADE.knockback * m.kb);
    P.addEnergy(BLADE.energyOnHit);
    s.n++;
    // first contact gets the full freeze (a little longer on a kill); the rest of a crowd only add short ticks, capped per swing
    const want = s.n === 1 ? m.stop * (e.dead ? 1.3 : 1) : 0.018, stop = Math.min(want, m.stop * 2 - s.stop);
    if (stop > 0.005) { G.hitStop(stop); s.stop += stop; }
    G.shake(0.16 + 0.1 * Math.min(3, s.n) + (m.spin ? 0.2 : 0));
    G.focus.x += tx * 0.16; G.focus.z += tz * 0.16;                          // camera kicks along the cut
    G.audio.play('blade_hit', { gain: 1, rate: m.pitch * (1 + 0.07 * (s.n - 1)) });
    // effects
    const hot = m.scorch, col = hot ? [2.4, 0.7, 0.15] : m.color, first = s.n <= 2;
    this.streak(hx, hy + 0.05, hz, Math.atan2(tx, tz), hot ? 0.3 : 0.17, m.spin ? 1.5 : 1.15, col);
    if (first) G.particles.glow(hx, hy, hz, m.spin ? 1.2 : 0.85, [0.9, 1.2, 1.5], 0.05);
    for (let i = 0; i < (first ? 8 : 4); i++) {                               // sparks thrown along the cut
      const sp = 4 + Math.random() * 6, j = (Math.random() - 0.5) * 0.9;
      G.particles.add.emit(hx, hy, hz, (tx + rx * j) * sp, 1 + Math.random() * 3, (tz + rz * j) * sp, 0.15 + Math.random() * 0.2, 0.08, 0.02,
        col[0] * 2, col[1] * 2, col[2] * 2, 1, 12, 2);
    }
    if (s.n === 1) G.lights.burst(hx - rx * 0.3, 1.0, hz - rz * 0.3, hot ? 0xff8a3a : 0x60e0ff, hot ? 26 : 16, 5, 0.12);
    if (hot) { e.hitGlow?.(hx, 0.62, hz, 1.2); G.particles.smoke(hx, hy, hz, 3, 0.45, [0.5, 0.5, 0.55], 1.3, 0.3); G.particles.embers(hx, hy, hz, 4, 0.4); }
  }

  streak(x, y, z, yaw, life, len, col) {
    const k = this.streaks[this.streakNext]; this.streakNext = (this.streakNext + 1) % this.streaks.length;
    k.t = 0; k.life = life; k.len = len; k.m.position.set(x, y, z);
    // lie along the cut, tilted a little toward the camera so it doesn't flatten out
    k.m.rotation.set(0.35, yaw + Math.PI / 2 + (Math.random() - 0.5) * 0.8, 0, 'YXZ'); k.m.material.uniforms.uCol.value.setRGB(col[0], col[1], col[2]); k.m.visible = true;
  }

  spawnGhosts(s) {
    // drop a frozen copy of the blade every ~0.36 rad of travel
    const th = this.theta(s, Math.min(s.t, s.m.wind + s.m.strike));
    if (s.ghostAt === null) s.ghostAt = th;
    while ((th - s.ghostAt) * s.dir >= 0) {
      const g = this.ghosts.find((x) => x.t >= x.life) || this.ghosts[0];
      this.poseBlade(s, s.ghostAt, 1, g.m); g.m.updateMatrix(); g.m.matrix.premultiply(this.frame.matrixWorld); g.m.matrix.decompose(g.m.position, g.m.quaternion, g.m.scale);
      g.t = 0; g.life = 0.11; g.m.visible = true;
      s.ghostAt += s.dir * 0.3;
    }
  }

  burn(s) {
    const pts = s.scrape; s.scrape = null;
    const B = this.scorches[this.scorchNext]; this.scorchNext = (this.scorchNext + 1) % this.scorches.length;
    const n = B.s.n;
    for (let i = 0; i <= n; i++) {
      const f = i / n * (pts.length - 1), a = Math.floor(f), b = Math.min(pts.length - 1, a + 1), u = f - a;
      const x = pts[a][0] + (pts[b][0] - pts[a][0]) * u, z = pts[a][1] + (pts[b][1] - pts[a][1]) * u;
      const p0 = pts[Math.max(0, a - 1)], p1 = pts[Math.min(pts.length - 1, a + 2)];
      let nx = -(p1[1] - p0[1]), nz = p1[0] - p0[0]; const l = Math.hypot(nx, nz) || 1; nx /= l; nz /= l;
      const w = 0.075;
      B.s.set(i, _v.set(x - nx * w, 0.02, z - nz * w), _w.set(x + nx * w, 0.02, z + nz * w));
    }
    B.s.commit(); B.t = 0; B.s.mesh.visible = true;
    for (let i = 0; i < pts.length; i += 3) this.G.decals.burn(pts[i][0], pts[i][1], 0.32);
  }

  // place a blade mesh (in swing-frame space) at yaw th; ext 0..1 = how far the blade is lit out of the emitter
  poseBlade(s, th, ext, mesh = this.blade) {
    dirOf(_d, th, this.elev(s, th));
    mesh.position.copy(_d).multiplyScalar(ARM); mesh.quaternion.setFromUnitVectors(FWD, _d);
    mesh.scale.set(1, 1, Math.max(0.001, s.m.reach * ext));
  }

  // ── body pose (called from Player.sync while the rig is posed) ──
  // returns the extra body yaw (spin finisher) or 0
  bodySpin() {
    const s = this.s; if (!s || !s.m.spin) { this.bodyYaw = 0; return 0; }
    const m = s.m, th = this.theta(s, s.t), want = s.yaw + th - this.P.facing - ARM_REST;
    if (s.t < m.wind) this.bodyYaw = angDiff(0, want) * outSine(s.t / m.wind);
    else if (s.t < m.wind + m.strike) this.bodyYaw = want;
    else this.bodyYaw = angDiff(0, want) * (1 - inOut(clamp01((s.t - m.wind - m.strike) / m.recover)));
    return this.bodyYaw;
  }
  twist() {
    const s = this.s; if (!s || s.m.spin) return 0;
    return Math.max(-0.8, Math.min(0.8, angDiff(0, s.yaw + this.theta(s, s.t) - this.P.facing) * 0.32));
  }
  // left arm straight along the blade so the hand sits exactly at the blade's root
  poseArm(R) {
    const s = this.s, th = this.theta(s, s.t);
    dirOf(_d, th, this.elev(s, th)).applyAxisAngle(UP, s.yaw - this.P.facing - this.bodyYaw);
    R.aim('arm_L_upper', _d); R.aim('arm_L_lower', _d); R.aim('arm_L_hand', _d);
  }

  // ── visuals (called from Player.sync after the rig is posed) ──
  sync() {
    const s = this.s, P = this.P;
    if (!s || P.dead) { if (this.hidden) { this.blade.visible = false; this.trail.mesh.visible = false; } this.light.intensity = 0; return; }
    const m = s.m, R = P.rig, strikeEnd = m.wind + m.strike;
    // frame origin = actual shoulder joint
    const sh = R?.bones.arm_L_upper;
    if (sh) { sh.bone.updateWorldMatrix(true, false); sh.bone.getWorldPosition(_s); } else _s.set(P.x + Math.cos(P.facing) * 0.13, 0.62, P.z - Math.sin(P.facing) * 0.13);
    this.frame.position.copy(_s); this.frame.rotation.set(0, s.yaw, 0); this.frame.updateMatrixWorld();
    const th = this.theta(s, s.t);
    // blade lights out of the emitter during the wind-up and retracts at the end of recovery
    const kr = clamp01((s.t - strikeEnd) / m.recover);
    const ext = s.t < m.wind ? 0.3 + 0.7 * outSine(s.t / m.wind) : (kr < 0.45 ? 1 : 1 - inOut((kr - 0.45) / 0.55));
    this.poseBlade(s, th, ext);
    const u = this.blade.material.uniforms;
    u.uCol.value.setRGB(m.color[0], m.color[1], m.color[2]); u.uA.value = 1; u.uHot.value = s.t >= m.wind && s.t < strikeEnd ? 1.2 : 0.2;
    this.blade.visible = true;
    // swept trail between the blade now and where it was `lag` seconds ago
    const tt = Math.min(s.t, strikeEnd), headT = Math.max(m.wind, tt), tailT = Math.max(m.wind, Math.min(s.t - m.lag, strikeEnd));
    const thH = this.theta(s, headT), thT = this.theta(s, tailT), Rt = ARM + m.reach;
    const ta = s.t < m.wind ? 0 : (kr > 0 ? (1 - kr) ** 1.5 : 1);
    const tr = this.trail;
    tr.mesh.visible = ta > 0.01 && Math.abs(thH - thT) > 0.01;
    if (tr.mesh.visible) {
      for (let i = 0; i <= tr.n; i++) {
        const k = i / tr.n, a = thH + (thT - thH) * k, el = this.elev(s, a);
        const w = Math.min(Rt - ARM, m.width * (1 - k) ** 0.8);
        dirOf(_d, a, el); tr.set(i, _v.copy(_d).multiplyScalar(Rt - w), _w.copy(_d).multiplyScalar(Rt));
      }
      tr.commit();
      const tu = tr.mesh.material.uniforms; tu.uCol.value.setRGB(m.color[0], m.color[1], m.color[2]); tu.uA.value = ta * (m.ghosts ? 1.4 : 1); tu.uRim.value = m.ghosts ? 1.6 : 1;
    }
    // travelling light at mid-blade
    dirOf(_d, th, this.elev(s, th)); _v.copy(_d).multiplyScalar(ARM + m.reach * 0.6 * ext).applyMatrix4(this.frame.matrixWorld);
    this.light.position.copy(_v); this.light.distance = m.lightRange; this.light.color.setRGB(m.color[0] / 1.6, m.color[1] / 1.6, m.color[2] / 1.6);
    this.light.intensity = m.light * (s.t < m.wind ? 0.35 * s.t / m.wind : (s.t < strikeEnd ? 1 : (1 - kr) ** 2));
    // tip scraping the floor (lightsweep)
    if (s.scrape && s.t >= m.wind && s.t <= strikeEnd + 0.02) {
      _w.copy(_d).multiplyScalar(ARM + m.reach * ext).applyMatrix4(this.frame.matrixWorld);
      if (_w.y < 0.14) {
        const last = s.scrape[s.scrape.length - 1];
        if (!last || Math.hypot(last[0] - _w.x, last[1] - _w.z) > 0.08) s.scrape.push([_w.x, _w.z]);
        const G = this.G, a = s.yaw + th, tx = Math.cos(a) * s.dir, tz = -Math.sin(a) * s.dir;
        for (let i = 0; i < 4; i++) { const sp = 2 + Math.random() * 5; G.particles.add.emit(_w.x, 0.05, _w.z, tx * sp + (Math.random() - 0.5) * 2, 1.5 + Math.random() * 3.5, tz * sp + (Math.random() - 0.5) * 2, 0.25 + Math.random() * 0.35, 0.07, 0.015, 3, 1.4 + Math.random(), 0.4, 1, 14, 1.2); }
        if (s.scrape.length === 1) G.audio.play('metal_clank', { x: _w.x, z: _w.z, gain: 0.45, rate: 1.6 });
      }
    }
  }

  updateFx(dt) {
    for (const g of this.ghosts) {
      if (g.t >= g.life) { g.m.visible = false; continue; }
      g.t += dt; const k = clamp01(g.t / g.life), u = g.m.material.uniforms;
      u.uA.value = (1 - k) ** 1.5 * 0.75; u.uHot.value = -1.2; u.uCol.value.setRGB(0.12 + 0.3 * (1 - k), 0.5 + 0.5 * (1 - k), 1.6);
    }
    for (const k of this.streaks) {
      if (k.t >= k.life) { k.m.visible = false; continue; }
      k.t += dt; const p = clamp01(k.t / k.life);
      k.m.scale.set(k.len * (0.45 + 0.55 * outCubic(Math.min(1, p * 2.5))), 1, 0.18 * (1 - p) ** 0.6 + 0.01);
      k.m.material.uniforms.uA.value = 1 - p * p;
    }
    if (this.ringT < 0.32) {
      this.ringT += dt; const k = clamp01(this.ringT / 0.32);
      this.ring.scale.setScalar(0.6 + 2.4 * outCubic(k)); this.ring.material.uniforms.uA.value = (1 - k) ** 1.5 * 1.4;
      if (k >= 1) this.ring.visible = false;
    }
    for (const b of this.scorches) {
      if (b.t > 2) { b.s.mesh.visible = false; continue; }
      b.t += dt; b.s.mesh.material.uniforms.uAge.value = b.t;
      if (Math.random() < dt * 14) { const p = b.s.p, i = (Math.random() * (b.s.n + 1)) | 0; this.G.particles.embers(p[i * 6], 0.05, p[i * 6 + 2], 1, 0.1); }
    }
  }

  hideAll() {
    this.hidden = true; this.frame.position.set(0, 0, 0);
    this.blade.visible = false; this.trail.mesh.visible = false;
    for (const g of this.ghosts) g.m.visible = false; for (const k of this.streaks) k.m.visible = false; this.ring.visible = false; for (const b of this.scorches) b.s.mesh.visible = false;
  }
}
