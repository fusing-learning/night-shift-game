import * as THREE from 'three';
import { Enemy, damp, angDiff } from './base.js';

const _v = new THREE.Vector3(), _t = new THREE.Vector3(), _pole = new THREE.Vector3(), _shift = new THREE.Vector3(), _d = new THREE.Vector3();
const ease = (k) => k * k * (3 - 2 * k);

// Foot-planting IK for multi-legged creatures: feet stay glued to the floor and step in alternating groups.
export class Legs {
  constructor(enemy, defs, o = {}) {
    this.e = enemy; this.o = { stepDist: 0.32, stepTime: 0.09, lift: 0.16, lead: 0.08, spread: 1, ...o };
    this.legs = [];
    const R = enemy.rig;
    for (const d of defs) {
      const end = R?.bones[d.end]; if (!end) continue;
      this.legs.push({ ...d, rest: end.pos.clone(), baseY: this.o.keepY ? end.pos.y : 0, foot: new THREE.Vector3(), from: new THREE.Vector3(), to: new THREE.Vector3(), t: 1, init: false, override: null, ov: new THREE.Vector3() });
    }
    this.turn = 0;
  }
  home(leg, out) {
    const e = this.e; out.set(leg.rest.x * this.o.spread, 0, leg.rest.z * this.o.spread);
    e.model.localToWorld(out); out.y = 0;
    out.x += (e.vx + e.kx) * this.o.lead; out.z += (e.vz + e.kz) * this.o.lead; return out;
  }
  update(dt, shiftY = 0, speedScale = 1) {
    const e = this.e, R = e.rig; if (!R) return;
    e.root.updateMatrixWorld(true);
    const stepping = [0, 0]; for (const l of this.legs) if (l.t < 1) stepping[l.group]++;
    const stepTime = this.o.stepTime / Math.max(0.6, speedScale);
    for (const l of this.legs) {
      const h = this.home(l, _t);
      if (!l.init) { l.foot.copy(h); l.init = true; }
      if (l.override) {
        l.ov.lerp(l.override, Math.min(1, dt * (l.overrideRate || 12))); l.t = 1; l.foot.set(l.ov.x, 0, l.ov.z);
        _v.copy(l.ov); e.model.worldToLocal(_v); _pole.set(l.rest.x * 0.35, 1, l.rest.z * 0.35);
        R.ik(l.a, l.b, l.end, _v, _pole, _shift.set(0, shiftY, 0)); continue;
      }
      l.ov.set(l.foot.x, l.foot.y + l.baseY, l.foot.z);
      if (l.t >= 1) {
        const d = Math.hypot(l.foot.x - h.x, l.foot.z - h.z);
        if ((d > this.o.stepDist && stepping[1 - l.group] === 0) || d > this.o.stepDist * 2.6) {
          l.t = 0; l.from.copy(l.foot); l.to.copy(h); l.to.x += (h.x - l.foot.x) * 0.35 + (e.vx) * stepTime; l.to.z += (h.z - l.foot.z) * 0.35 + (e.vz) * stepTime;
          stepping[l.group]++;
        }
      } else {
        l.t = Math.min(1, l.t + dt / stepTime);
        l.foot.lerpVectors(l.from, l.to, ease(l.t)); l.foot.y = Math.sin(l.t * Math.PI) * this.o.lift;
        if (l.t >= 1) { l.foot.y = 0; if (this.onStep) this.onStep(l); }
      }
      _v.copy(l.foot); _v.y += l.baseY; e.model.worldToLocal(_v);
      _pole.set(l.rest.x * 0.35, 1, l.rest.z * 0.35);
      R.ik(l.a, l.b, l.end, _v, _pole, _shift.set(0, shiftY, 0));
    }
  }
}

// ───────────────────────── CRAWLER ─────────────────────────
export class Crawler extends Enemy {
  constructor(G, x, z, o = {}) {
    super(G, 'crawler', x, z, o);
    this.radius = 0.4; this.hp = this.maxHp = 30; this.speed = 5.3 + Math.random() * 0.5; this.mass = 0.6; this.height = 0.35; this.wakeRange = o.wakeRange ?? 8;
    this.corpse = false; this.gibCount = 5; this.dropChance = 0.14; this.cd = 0.3 + Math.random() * 0.5; this.zig = Math.random() * 10; this.hitDone = false; this.crouch = 0;
    this.lunge = { x: 0, z: 0 }; this.turnRate = 12; this.chitterT = 2 + Math.random() * 4;
    if (this.rig) {
      const defs = []; let g = 0;
      for (const s of ['L', 'R']) for (const i of [1, 2, 3]) { defs.push({ a: `leg_${s}${i}_a`, b: `leg_${s}${i}_b`, end: `leg_${s}${i}_end`, group: (i + (s === 'L' ? 0 : 1)) % 2 }); g++; }
      this.legs = new Legs(this, defs, { stepDist: 0.3, stepTime: 0.075, lift: 0.2, lead: 0.07 });
    }
  }
  onAlert(silent) { if (!silent) this.G.audio.play('crawler_chitter', { x: this.x, z: this.z, gain: 0.9 }); this.setState('chase'); }
  think(dt) {
    const G = this.G, P = G.player; this.cd -= dt;
    if (!this.alerted) { this.brake(dt); return; }
    switch (this.state) {
      case 'chase': {
        this.zig += dt * 5;
        const dir = this.seek(dt, this.speed, 9);
        // sideways weave so the swarm doesn't arrive in a straight line
        const w = Math.sin(this.zig) * 1.6 * Math.min(1, this.distToPlayer / 6);
        this.vx += -dir.z * w * dt * 6; this.vz += dir.x * w * dt * 6;
        this.faceVelocity(dt);
        this.chitterT -= dt; if (this.chitterT <= 0) { this.chitterT = 3 + Math.random() * 5; G.audio.play(Math.random() < 0.5 ? 'crawler_chitter' : 'crawler_skitter', { x: this.x, z: this.z, gain: 0.5 }); }
        if (this.distToPlayer < 2.7 && this.sees && this.cd <= 0 && !P.dead) this.setState('wind');
        break;
      }
      case 'wind':
        this.brake(dt, 14); this.facePlayer(dt, 16); this.crouch = damp(this.crouch, 1, 18, dt);
        if (this.stateT > 0.26) {
          const a = this.angleToPlayer(); this.lunge.x = Math.sin(a); this.lunge.z = Math.cos(a); this.hitDone = false; this.setState('lunge');
          G.audio.play('crawler_attack', { x: this.x, z: this.z, gain: 0.8 });
        }
        break;
      case 'lunge':
        this.vx = this.lunge.x * 10.5; this.vz = this.lunge.z * 10.5; this.crouch = damp(this.crouch, -0.6, 20, dt);
        if (!this.hitDone && this.distToPlayer < this.radius + P.radius + 0.15) { this.hitDone = true; P.damage(10, this.x, this.z, 3.5); }
        if (this.stateT > 0.3) { this.cd = 0.9 + Math.random() * 0.5; this.setState('recover'); }
        break;
      case 'recover':
        this.brake(dt, 8); this.crouch = damp(this.crouch, 0, 8, dt);
        if (this.stateT > 0.45) this.setState('chase');
        break;
      default: this.setState('chase');
    }
  }
  animate(dt) {
    if (!this.rig) return;
    const sp = Math.hypot(this.vx, this.vz);
    const bob = Math.sin(this.age * 22) * 0.012 * Math.min(1, sp / 2) + Math.sin(this.age * 2.3 + this.zig) * 0.012 - this.crouch * 0.1;
    this.rig.offset('body', 0, bob, 0);
    this.model.rotation.x = this.state === 'lunge' ? -0.35 : damp(this.model.rotation.x, 0, 10, dt);
    this.legs.update(dt, bob, sp / 5);
  }
  onDeath() { this.G.audio.play('crawler_death', { x: this.x, z: this.z, gain: 0.9 }); }
}

// ───────────────────────── SPITTER ─────────────────────────
export class Spitter extends Enemy {
  constructor(G, x, z, o = {}) {
    super(G, 'spitter', x, z, o);
    this.radius = 0.68; this.hp = this.maxHp = 85; this.speed = 1.8; this.mass = 3; this.height = 0.7; this.wakeRange = o.wakeRange ?? 13;
    this.gibCount = 6; this.cd = 1 + Math.random(); this.inflate = 0; this.snap = 0; this.bloodColor = [0.42, 0.34, 0.03]; this.dropChance = 0.35; this.turnRate = 3;
    this.neckYaw = 0; this.strafe = Math.random() < 0.5 ? 1 : -1;
    if (this.rig) {
      const defs = [['FL', 0], ['BR', 0], ['FR', 1], ['BL', 1]].map(([n, g]) => ({ a: `leg_${n}_a`, b: `leg_${n}_b`, end: `leg_${n}_end`, group: g }));
      this.legs = new Legs(this, defs, { stepDist: 0.24, stepTime: 0.2, lift: 0.14, lead: 0.15 });
    }
    this.sacMat = this.glowMat('glow_bile');
  }
  onAlert(silent) { if (!silent) this.G.audio.play('spitter_gurgle', { x: this.x, z: this.z }); this.setState('move'); }
  think(dt) {
    const G = this.G, P = G.player; this.cd -= dt; this.snap = Math.max(0, this.snap - dt * 4);
    if (!this.alerted) { this.brake(dt); return; }
    if (this.state === 'aim') {
      this.brake(dt, 6); this.facePlayer(dt, 5); this.inflate = Math.min(1, this.inflate + dt / 0.85);
      if (this.inflate >= 1) {
        this.inflate = 0; this.snap = 1; this.cd = 2.5 + Math.random() * 0.8; this.setState('move');
        const m = this.bonePos('head_end', _v); const lead = Math.min(1.2, this.distToPlayer / 12);
        const tx = P.x + P.vx * 0.55 * lead + (Math.random() - 0.5) * 0.8, tz = P.z + P.vz * 0.55 * lead + (Math.random() - 0.5) * 0.8;
        G.weapons.lob(m.x, m.y, m.z, tx, tz, 0.75 + this.distToPlayer * 0.03, { radius: 1.45, damage: 14, puddle: 4 });
        G.audio.play('spitter_spit', { x: this.x, z: this.z }); G.particles.bile(m.x, m.y, m.z, 6);
      }
      return;
    }
    this.inflate = Math.max(0, this.inflate - dt * 2);
    const d = this.distToPlayer;
    if (d < 5.5 && this.sees) {         // back away
      const a = this.angleToPlayer(); this.vx = damp(this.vx, -Math.sin(a) * this.speed, 4, dt); this.vz = damp(this.vz, -Math.cos(a) * this.speed, 4, dt);
    } else if (d > 11 || !this.sees) { this.seek(dt, this.speed, 4); }
    else { const a = this.angleToPlayer(); this.vx = damp(this.vx, Math.cos(a) * this.speed * 0.5 * this.strafe, 3, dt); this.vz = damp(this.vz, -Math.sin(a) * this.speed * 0.5 * this.strafe, 3, dt); if (this.lastHitWall) this.strafe *= -1; }
    this.facePlayer(dt, 3);
    if (this.cd <= 0 && this.sees && d < 15 && !P.dead) { this.setState('aim'); G.audio.play('spitter_gurgle', { x: this.x, z: this.z, gain: 0.8 }); }
  }
  animate(dt) {
    if (this.sacMat) this.sacMat.emissiveIntensity = 0.9 + this.inflate * 4.5 + Math.sin(this.age * 3) * 0.15;
    if (!this.rig) return;
    const R = this.rig; const breathe = Math.sin(this.age * 2.2) * 0.012;
    R.offset('body', 0, breathe - this.snap * 0.05, 0);
    R.scale('sac', 1 + this.inflate * 0.42 + Math.sin(this.age * 2.2) * 0.025);
    const yawWant = Math.max(-1.1, Math.min(1.1, angDiff(this.facing, this.angleToPlayer())));
    this.neckYaw = damp(this.neckYaw, this.alerted ? yawWant : 0, 5, dt);
    const rear = -this.inflate * 0.22 + this.snap * 0.3;
    for (let i = 1; i <= 4; i++) R.rot('neck_' + i, rear + Math.sin(this.age * 1.7 + i * 0.9) * 0.05, this.neckYaw / 4 + Math.sin(this.age * 1.3 + i) * 0.05, 0);
    R.rot('head', rear * 0.5 + this.snap * 0.3, 0, Math.sin(this.age * 2.9) * 0.08);
    this.legs.update(dt, breathe, 1);
  }
  onDeath() {
    const G = this.G; G.audio.play('spitter_death', { x: this.x, z: this.z });
    G.particles.bile(this.x, 0.8, this.z, 40); G.weapons.puddle(this.x, this.z, 1.6, 3.5, false); G.lights.burst(this.x, 1, this.z, 0xb8ff3a, 30, 8, 0.3);
    if (this.rig) this.rig.scale('sac', 0.15);
  }
  animateDeath(dt) { const k = Math.min(1, this.deathT / 0.6); this.model.scale.set(1 + k * 0.15, 1 - k * 0.45, 1 + k * 0.15); if (this.sacMat) this.sacMat.emissiveIntensity = Math.max(0, 1 - this.deathT); }
}

// ───────────────────────── STALKER ─────────────────────────
// Only moves while the torch is NOT on it. Makes the torch stutter when close.
export class Stalker extends Enemy {
  constructor(G, x, z, o = {}) {
    super(G, 'stalker', x, z, o);
    this.radius = 0.42; this.hp = this.maxHp = 100; this.speed = 6.4; this.mass = 1.5; this.height = 1.3; this.wakeRange = o.wakeRange ?? 7;
    this.gibCount = 5; this.cd = 0; this.lit = false; this.litT = 0; this.ph = Math.random() * 6; this.amt = 0; this.tilt = (Math.random() - 0.5) * 0.8; this.reach = 0; this.slash = 0;
    this.bloodColor = [0.25, 0.02, 0.05]; this.dropChance = 0.5; this.turnRate = 10; this.creakT = 1; this.shrieked = false; this.hitDone = false;
  }
  onAlert(silent) { if (!silent) this.G.audio.play('stalker_whisper', { x: this.x, z: this.z, gain: 1 }); this.setState('hunt'); }
  damageMult(kind) { return (this.lit && kind === 'laser') ? 0.35 : 1; }
  think(dt) {
    const G = this.G, P = G.player; this.cd -= dt;
    this.lit = this.alerted && G.isTorchOn(this.x, this.z);
    if (!this.alerted) { this.brake(dt, 20); return; }
    if (this.lit) {
      this.vx = this.vz = 0; this.litT += dt; this.creakT -= dt;
      if (this.creakT <= 0) { this.creakT = 1.2 + Math.random() * 2.5; G.audio.play('stalker_creak', { x: this.x, z: this.z, gain: 0.6 }); }
      if (this.state === 'wind') this.setState('hunt');
      return;
    }
    this.litT = 0;
    if (this.state === 'wind') {
      this.brake(dt, 20); this.facePlayer(dt, 20); this.reach = damp(this.reach, 1, 20, dt);
      if (this.stateT > 0.24) {
        this.slash = 1; this.setState('recover'); this.cd = 0.9;
        if (this.distToPlayer < 2.0) P.damage(22, this.x, this.z, 5);
        G.audio.play('blade_swing', { x: this.x, z: this.z, gain: 0.5, rate: 0.7 });
      }
      return;
    }
    if (this.state === 'recover') { this.brake(dt, 10); if (this.stateT > 0.5) this.setState('hunt'); return; }
    this.seek(dt, this.speed, 14); this.faceVelocity(dt, 14);
    this.reach = damp(this.reach, this.distToPlayer < 4 ? 0.7 : 0.15, 8, dt);
    if (this.distToPlayer < 1.55 && this.cd <= 0 && !P.dead) {
      this.setState('wind'); if (!this.shrieked) { this.shrieked = true; G.audio.play('stalker_shriek', { x: this.x, z: this.z, gain: 0.9 }); }
    }
  }
  animate(dt) {
    if (!this.rig || this.lit) return;       // frozen mid-pose while lit
    const R = this.rig; const sp = Math.hypot(this.vx, this.vz);
    this.ph += sp * dt * 2.4; this.amt = damp(this.amt, Math.min(1, sp / 3), 10, dt); this.slash = Math.max(0, this.slash - dt * 4);
    const s = Math.sin(this.ph), c = Math.cos(this.ph), a = this.amt, jit = Math.sin(this.age * 31) * 0.02;
    this.model.position.y = -0.1 * a - Math.abs(s) * 0.05 * a;
    R.rot('hips', 0.22 * a + 0.08, s * 0.18 * a, 0);
    R.rot('spine', 0.25 + 0.1 * a, 0, s * 0.05); R.rot('chest', 0.2, -s * 0.2 * a, 0);
    R.rot('neck', -0.25, 0, this.tilt + jit * 4); R.rot('head', -0.35, Math.sin(this.age * 0.7) * 0.2, this.tilt * 0.8);
    R.rot('leg_L_upper', -s * 0.95 * a - 0.15, 0, 0); R.rot('leg_L_lower', Math.max(0, c) * 1.25 * a + 0.3, 0, 0);
    R.rot('leg_R_upper', s * 0.95 * a - 0.15, 0, 0); R.rot('leg_R_lower', Math.max(0, -c) * 1.25 * a + 0.3, 0, 0);
    const r = this.reach, sl = this.slash;
    R.aim('arm_L_upper', _d.set(0.5 - r * 0.25, -1 + r * 0.9 + s * 0.15 * a, 0.2 + r * 0.9 + sl * 0.5)); R.aim('arm_L_lower', _d.set(0.15 - sl * 0.6, -0.9 + r * 0.9 - sl * 0.6, 0.4 + r));
    R.aim('arm_R_upper', _d.set(-0.5 + r * 0.25, -1 + r * 0.9 - s * 0.15 * a, 0.2 + r * 0.9 + sl * 0.5)); R.aim('arm_R_lower', _d.set(-0.15 + sl * 0.6, -0.9 + r * 0.9 - sl * 0.6, 0.4 + r));
    R.aim('arm_L_hand', _d.set(0.1, -0.6 + r * 0.5, 0.8)); R.aim('arm_R_hand', _d.set(-0.1, -0.6 + r * 0.5, 0.8));
  }
  onDeath() { this.G.audio.play('stalker_death', { x: this.x, z: this.z }); this.G.particles.sparks(this.x, 2, this.z, 0, 0, 16, [1, 1, 1], 4); }
  animateDeath(dt) { const k = Math.min(1, this.deathT / 0.5); this.model.rotation.x = k * k * 1.45; this.model.position.y = 0.12 * k; }
}

// ───────────────────────── BRUTE ─────────────────────────
export class Brute extends Enemy {
  constructor(G, x, z, o = {}) {
    super(G, 'brute', x, z, o);
    this.radius = 0.95; this.hp = this.maxHp = 380; this.speed = 2.3; this.mass = 9; this.height = 1.4; this.wakeRange = o.wakeRange ?? 12;
    this.gibCount = 10; this.cd = 1.5; this.chargeCd = 3; this.ph = 0; this.amt = 0; this.arm = 0; this.lean = 0; this.dropChance = 0; this.turnRate = 3.2;
    this.chargeDir = { x: 0, z: 1 }; this.hitDone = false; this.stepSide = 0; this.marker = null; this.exhaust = this.glowMat('glow_orange');
  }
  onAlert() { this.G.audio.play('brute_growl', { x: this.x, z: this.z, gain: 1 }); this.setState('walk'); this.G.shake(0.25); }
  damageMult() { return this.state === 'stunned' ? 1.5 : 1; }
  slamCentre(out) { out.x = this.x + Math.sin(this.facing) * 2.0; out.z = this.z + Math.cos(this.facing) * 2.0; return out; }
  think(dt) {
    const G = this.G, P = G.player; this.cd -= dt; this.chargeCd -= dt;
    if (!this.alerted) { this.brake(dt); return; }
    const d = this.distToPlayer;
    switch (this.state) {
      case 'walk': {
        this.seek(dt, this.speed, 4); this.facePlayer(dt, 3.2);
        if (P.dead) break;
        if (d < 3.1 && this.cd <= 0) { this.setState('slamWind'); const c = this.slamCentre({}); this.marker = G.weapons.telegraph(c.x, c.z, 2.6, 0.75); G.audio.play('brute_growl', { x: this.x, z: this.z, gain: 0.7, rate: 1.2 }); }
        else if (d > 6 && d < 15 && this.sees && this.chargeCd <= 0) { this.setState('chargeWind'); G.audio.play('brute_charge', { x: this.x, z: this.z }); }
        break;
      }
      case 'slamWind':
        this.brake(dt, 8); this.arm = damp(this.arm, 1, 7, dt);
        if (this.stateT < 0.45) { this.facePlayer(dt, 2.5); if (this.marker) { const c = this.slamCentre({}); this.marker.mesh.position.x = c.x; this.marker.mesh.position.z = c.z; this.marker.x = c.x; this.marker.z = c.z; } }
        if (this.stateT > 0.75) {
          const c = this.slamCentre({}); this.arm = -0.25; this.setState('recover'); this.cd = 2.2;
          if (Math.hypot(P.x - c.x, P.z - c.z) < 2.6 + P.radius * 0.5) P.damage(30, c.x, c.z, 10);
          G.shake(1.0); G.hitStop(0.04); G.audio.play('brute_slam', { x: c.x, z: c.z });
          G.particles.sparks(c.x, 0.2, c.z, 0, 0, 30, [1.4, 1.0, 0.5], 7); G.particles.smoke(c.x, 0.3, c.z, 8, 1.0, [0.45, 0.45, 0.5], 1.2, 0.35); G.particles.ring(c.x, 0.15, c.z, 1.0, 30, [1.2, 0.8, 0.4], 7);
          G.lights.burst(c.x, 1, c.z, 0xffc070, 60, 10, 0.2); G.decals.burn(c.x, c.z, 3.4);
        }
        break;
      case 'recover': this.brake(dt, 6); this.arm = damp(this.arm, 0, 3, dt); if (this.stateT > 1.0) this.setState('walk'); break;
      case 'chargeWind':
        this.brake(dt, 8); this.facePlayer(dt, 6); this.lean = damp(this.lean, 1, 5, dt);
        if (this.stateT > 0.85) { const a = this.facing; this.chargeDir.x = Math.sin(a); this.chargeDir.z = Math.cos(a); this.hitDone = false; this.setState('charge'); }
        break;
      case 'charge': {
        // slight homing early in the charge
        if (this.stateT < 0.5) { const a = this.facing + angDiff(this.facing, this.angleToPlayer()) * Math.min(1, dt * 1.6); this.facing = a; this.chargeDir.x = Math.sin(a); this.chargeDir.z = Math.cos(a); }
        this.vx = this.chargeDir.x * 11.5; this.vz = this.chargeDir.z * 11.5;
        if (Math.random() < 0.5) G.particles.smoke(this.x, 0.2, this.z, 1, 0.6, [0.4, 0.4, 0.45], 0.5, 0.2);
        if (!this.hitDone && d < this.radius + P.radius + 0.3) { this.hitDone = true; if (P.damage(25, this.x - this.chargeDir.x, this.z - this.chargeDir.z, 11)) { G.hitStop(0.05); } }
        const blocked = this.lastHitWall && (this.G.grid.hitNx * this.chargeDir.x + this.G.grid.hitNz * this.chargeDir.z) < -0.5;
        if (blocked && this.stateT > 0.12) {
          this.setState('stunned'); this.chargeCd = 6; this.vx = this.vz = 0; G.shake(0.9); G.audio.play('brute_slam', { x: this.x, z: this.z, rate: 0.85 });
          G.particles.sparks(this.x + this.chargeDir.x, 1, this.z + this.chargeDir.z, -this.chargeDir.x, -this.chargeDir.z, 24, [1.3, 1, 0.6], 7); G.particles.smoke(this.x, 1, this.z, 6, 0.9, [0.45, 0.45, 0.5], 1, 0.3);
        } else if (this.stateT > 1.5) { this.setState('recover'); this.chargeCd = 5; }
        break;
      }
      case 'stunned': this.brake(dt, 12); this.lean = damp(this.lean, -0.3, 4, dt); if (this.stateT > 1.9) { this.setState('walk'); } break;
      default: this.setState('walk');
    }
    if (this.state !== 'chargeWind' && this.state !== 'charge' && this.state !== 'stunned') this.lean = damp(this.lean, 0, 4, dt);
    this.pushPlayer();
  }
  animate(dt) {
    if (this.exhaust) this.exhaust.emissiveIntensity = 1.2 + this.lean * 5 + (this.state === 'slamWind' ? 3 : 0);
    if (!this.rig) return;
    const R = this.rig; const sp = Math.hypot(this.vx, this.vz);
    const prev = this.ph; this.ph += sp * dt * (this.state === 'charge' ? 1.1 : 2.3); this.amt = damp(this.amt, Math.min(1, sp / 1.5), 8, dt);
    if (Math.floor(this.ph / Math.PI) !== Math.floor(prev / Math.PI)) { this.G.audio.play('brute_step', { x: this.x, z: this.z, gain: 0.8 }); if (this.distToPlayer < 12) this.G.shake(0.12); }
    const s = Math.sin(this.ph), c = Math.cos(this.ph), a = this.amt, stun = this.state === 'stunned' ? Math.sin(this.age * 9) * 0.06 : 0;
    const breath = Math.sin(this.age * 1.6) * 0.02;
    this.model.position.y = -Math.abs(s) * 0.06 * a;
    R.rot('hips', 0.05 + this.lean * 0.25, s * 0.1 * a, s * 0.1 * a + stun);
    R.rot('spine', 0.08 + this.lean * 0.3 + breath, 0, -s * 0.05 * a); R.rot('chest', 0.05 + this.lean * 0.15 + breath, -s * 0.12 * a, 0);
    R.rot('head', 0.15 - this.lean * 0.3, Math.sin(this.age * 0.9) * 0.2, stun * 3);
    R.rot('leg_L_upper', -s * 0.5 * a, 0, 0); R.rot('leg_L_lower', Math.max(0, c) * 0.6 * a, 0, 0);
    R.rot('leg_R_upper', s * 0.5 * a, 0, 0); R.rot('leg_R_lower', Math.max(0, -c) * 0.6 * a, 0, 0);
    const arm = this.arm;   // 1 = raised overhead, <0 = smashed down
    R.rot('arm_R_upper', -arm * 2.0 + s * 0.12 * a - this.lean * 0.9, 0, -Math.max(0, arm) * 0.25);
    R.rot('arm_R_lower', -Math.max(0, arm) * 0.5 - this.lean * 0.3, 0, 0);
    R.rot('arm_L_upper', -s * 0.2 * a + Math.sin(this.age * 2.1) * 0.08, 0, 0);
  }
  onDeath() {
    const G = this.G; G.audio.play('brute_death', { x: this.x, z: this.z }); G.shake(0.8);
    if (this.marker) this.marker.t = this.marker.dur;
    G.spawnPickup('health', this.x + 0.6, this.z); G.spawnPickup('energy', this.x - 0.6, this.z + 0.3);
  }
  animateDeath(dt) {
    const k = Math.min(1, this.deathT / 0.9), e = k * k;
    this.model.rotation.x = e * 1.25; this.model.position.y = 0.25 * e;
    if (this.deathT < 0.95 && this.deathT + dt >= 0.95) { this.G.shake(0.7); this.G.particles.smoke(this.x, 0.3, this.z, 8, 1, [0.4, 0.4, 0.45], 0.8, 0.3); this.G.audio.play('brute_step', { x: this.x, z: this.z, gain: 1, rate: 0.7 }); }
    if (this.exhaust) this.exhaust.emissiveIntensity = Math.max(0, 1.2 - this.deathT);
  }
}
