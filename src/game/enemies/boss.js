import * as THREE from 'three';
import { Enemy, damp, angDiff } from './base.js';
import { Legs, Crawler } from './types.js';

const _v = new THREE.Vector3(), _c = { x: 0, z: 0 };

// "The Foreman": three-phase final boss.
export class Boss extends Enemy {
  constructor(G, x, z, o = {}) {
    super(G, 'boss', x, z, { ...o, dormant: true });
    this.radius = 2.5; this.gridRadius = 1.7; this.hp = this.maxHp = 2000; this.mass = 200; this.height = 1.5; this.wakeRange = 0;
    this.phase = 1; this.gap = 1.5; this.spawnT = 0; this.spawnCd = 9; this.turnRate = 1.5; this.noSeparate = true; this.corpse = true; this.gibCount = 0;
    this.armSide = 0; this.combo = 0; this.chargeDir = { x: 0, z: 1 }; this.hitDone = false; this.fury = 0; this.volleyLeft = 0; this.volleyT = 0; this.ringsLeft = 0; this.ringT = 0;
    this.marker = null; this.slamTarget = new THREE.Vector3(); this.raise = new THREE.Vector3(); this.glow = 0; this.hurtT = 0; this.rear = 0; this.dying = 0; this.lastAttack = '';
    this.furnaceMat = this.glowMat('glow_furnace'); this.sacMat = this.glowMat('glow_bile'); this.eyeMat = this.glowMat('glow_red');
    this.untargetable = true; this.state = 'dormant'; this.name = 'THE FOREMAN'; this.flashGain = 0.35;
    if (this.rig) {
      this.arms = new Legs(this, [
        { a: 'arm_L_upper', b: 'arm_L_lower', end: 'arm_L_hand', group: 0 }, { a: 'arm_R_upper', b: 'arm_R_lower', end: 'arm_R_hand', group: 1 },
      ], { stepDist: 0.9, stepTime: 0.42, lift: 0.7, lead: 0.5, keepY: true });
    }
  }
  separate() {}
  alert() {}                       // woken by the encounter script only
  wake() {
    if (this.state !== 'dormant') return;
    this.alerted = true; this.dormant = false; this.setState('intro'); this.G.audio.play('boss_roar', { gain: 1 }); this.G.shake(1.2);
  }
  damageMult(kind, dx, dz) {
    const toAttacker = Math.atan2(-dx, -dz);
    return Math.abs(angDiff(this.facing, toAttacker)) < 1.0 ? 1.4 : 0.8;
  }
  onDamage(dmg) {
    const G = this.G; this.hurtT -= dmg;
    if (this.hurtT <= 0) { this.hurtT = 140; G.audio.play('boss_hurt', { x: this.x, z: this.z, gain: 0.8 }); }
    const frac = this.hp / this.maxHp;
    if (this.phase === 1 && frac <= 0.66) this.startPhase(2);
    else if (this.phase === 2 && frac <= 0.33) this.startPhase(3);
  }
  startPhase(n) {
    const G = this.G; this.phase = n; this.setState('phase'); this.untargetable = true; this.endOverride(); this.vx = this.vz = 0;
    if (this.marker) { this.marker.t = this.marker.dur; this.marker = null; }
    G.audio.play('boss_phase', { gain: 1 }); G.shake(1.4); G.onBossPhase(n);
    // it coughs up supplies as it tears itself open
    const P = G.player, a = Math.atan2(P.x - this.x, P.z - this.z);
    for (const [kind, off] of [['health', 0.5], ['energy', -0.5]]) { let px = this.x + Math.sin(a + off) * 5.5, pz = this.z + Math.cos(a + off) * 5.5; if (G.grid.isSolid(px, pz)) { px = P.x; pz = P.z; } G.spawnPickup(kind, px, pz); }
    this.turnRate = n === 2 ? 1.9 : 2.4;
  }
  die() {
    if (this.state === 'dying' || this.dead) return;
    const G = this.G; this.hp = 0; this.setState('dying'); this.untargetable = true; this.endOverride(); this.vx = this.vz = 0;
    if (this.marker) { this.marker.t = this.marker.dur; this.marker = null; }
    G.audio.play('boss_death', { gain: 1 }); G.onBossDying();
  }
  endOverride() { if (this.arms) for (const l of this.arms.legs) l.override = null; }
  furnacePos(out) {
    if (this.rig?.bones.furnace) return this.rig.bones.furnace.bone.getWorldPosition(out);
    return out.set(this.x + Math.sin(this.facing) * 2.2, 1.6, this.z + Math.cos(this.facing) * 2.2);
  }
  spawnCrawlers(n) {
    const G = this.G; G.audio.play('boss_spawn', { x: this.x, z: this.z });
    for (let i = 0; i < n; i++) {
      const a = this.facing + Math.PI + (i - (n - 1) / 2) * 0.7 + (Math.random() - 0.5) * 0.3; let px = this.x + Math.sin(a) * 3.2, pz = this.z + Math.cos(a) * 3.2;
      if (G.grid.isSolid(px, pz)) { px = this.x + Math.sin(a) * 2; pz = this.z + Math.cos(a) * 2; }
      const c = new Crawler(G, px, pz, { dormant: false, spawnFx: true, zone: this.zone }); c.alert(true); c.fromBoss = true; c.dropChance = 0.6; G.enemies.push(c);
    }
    this.fury = 1;
  }

  chooseAttack() {
    const G = this.G, d = this.distToPlayer, p = this.phase; const opts = [];
    if (d < 7.5) opts.push(['slam', 4]);
    opts.push(['volley', d > 6 ? 3 : 1.5]);
    if (p >= 2 && d > 7) opts.push(['charge', 3]);
    if (p >= 3) opts.push(['ring', 3]);
    let total = 0; for (const o of opts) { if (o[0] === this.lastAttack) o[1] *= 0.35; total += o[1]; }
    let r = Math.random() * total, pick = opts[0][0]; for (const o of opts) { r -= o[1]; if (r <= 0) { pick = o[0]; break; } }
    this.lastAttack = pick;
    if (pick === 'slam') { this.combo = p >= 3 ? 3 : (p === 2 ? 2 : 1); this.beginSlam(); }
    else if (pick === 'volley') { this.setState('volleyWind'); G.audio.play('boss_spit', { x: this.x, z: this.z, rate: 0.8, gain: 0.7 }); }
    else if (pick === 'charge') { this.setState('chargeWind'); G.audio.play('boss_roar', { x: this.x, z: this.z, rate: 1.15, gain: 0.9 }); }
    else if (pick === 'ring') { this.setState('ringWind'); G.audio.play('boss_roar', { x: this.x, z: this.z, rate: 1.3, gain: 0.8 }); }
  }
  beginSlam() {
    const G = this.G, P = G.player; this.armSide = 1 - this.armSide; this.setState('slamWind');
    // aim at the player, clamped to arm reach
    let dx = P.x + P.vx * 0.25 - this.x, dz = P.z + P.vz * 0.25 - this.z; const d = Math.hypot(dx, dz) || 1; const reach = Math.max(3.2, Math.min(6.4, d));
    this.slamTarget.set(this.x + dx / d * reach, 0, this.z + dz / d * reach);
    this.windTime = this.phase >= 3 ? 0.66 : (this.phase === 2 ? 0.84 : 1.0);
    this.marker = G.weapons.telegraph(this.slamTarget.x, this.slamTarget.z, 3.1, this.windTime);
    if (this.arms) { const l = this.arms.legs[this.armSide]; this.raise.set((this.x + this.slamTarget.x) / 2, 4.2, (this.z + this.slamTarget.z) / 2); l.override = this.raise; l.overrideRate = 7; }
  }

  think(dt) {
    const G = this.G, P = G.player, d = this.distToPlayer;
    this.fury = Math.max(0, this.fury - dt); this.glow = damp(this.glow, 0, 3, dt); this.rear = damp(this.rear, 0, 4, dt);
    const speed = [0, 1.5, 1.9, 2.5][this.phase];
    switch (this.state) {
      case 'dormant': this.vx = this.vz = 0; return;
      case 'intro': this.rear = 1; if (this.stateT > 3.0) { this.untargetable = false; this.setState('idle'); this.gap = 0.8; } return;
      case 'phase': {
        this.rear = 1; this.glow = 1;
        if (this.stateT < 0.15) { // shove the player away
          const a = this.angleToPlayer(); if (d < 8) { P.kx += Math.sin(a) * 9; P.kz += Math.cos(a) * 9; }
          G.weapons.shockwave(this.x, this.z, 12, 12, 0);
        }
        if (Math.random() < dt * 14) { const a = Math.random() * 6.283; G.particles.blood(this.x + Math.sin(a) * 2, 1.5 + Math.random(), this.z + Math.cos(a) * 2, Math.sin(a), Math.cos(a), 6, 5); }
        if (this.stateT > 1.6 && !this.spawnedPhase) { this.spawnedPhase = true; this.spawnCrawlers(this.phase === 2 ? 4 : 5); }
        if (this.stateT > 3.0) { this.spawnedPhase = false; this.untargetable = false; this.setState('idle'); this.gap = 0.5; this.spawnCd = 12; }
        return;
      }
      case 'dying': {
        this.dying += dt; this.glow = 1;
        if (Math.random() < dt * 9) {
          const a = Math.random() * 6.283, r = Math.random() * 2.4; const px = this.x + Math.sin(a) * r, pz = this.z + Math.cos(a) * r;
          G.particles.blood(px, 1 + Math.random() * 1.5, pz, Math.sin(a), Math.cos(a), 14, 6); G.gibs.burst(px, 1.5, pz, 2, Math.sin(a), Math.cos(a), 6); G.decals.splat(px + Math.sin(a) * 2, pz + Math.cos(a) * 2, 1.8);
          G.lights.burst(px, 2, pz, 0xff6a18, 50, 10, 0.2); G.shake(0.35); G.audio.play('gore_splat', { x: px, z: pz, gain: 0.7 });
        }
        if (this.stateT > 5.2) {
          this.dead = true; this.deathT = 0; G.shake(1.5); G.gibs.burst(this.x, 2, this.z, 18, 0, 0, 9); G.particles.blood(this.x, 2, this.z, 0, 0, 60, 9);
          for (let i = 0; i < 10; i++) G.decals.splat(this.x + (Math.random() - 0.5) * 7, this.z + (Math.random() - 0.5) * 7, 2.2);
          G.audio.play('brute_slam', { x: this.x, z: this.z, rate: 0.6 }); G.onEnemyKilled(this); G.onBossDead();
        }
        return;
      }
      case 'idle': {
        this.facePlayer(dt, this.turnRate);
        if (d > 4.6) this.seek(dt, speed, 2.5, P.x, P.z); else this.brake(dt, 3);
        this.gap -= dt; this.spawnCd -= dt;
        if (P.dead) return;
        if (this.phase >= 2 && this.spawnCd <= 0 && G.enemies.filter((e) => e.fromBoss && !e.dead).length < 4) { this.spawnCd = 13; this.spawnCrawlers(3); this.gap = Math.max(this.gap, 0.8); }
        else if (this.gap <= 0) this.chooseAttack();
        break;
      }
      case 'slamWind': {
        this.brake(dt, 5); this.face(Math.atan2(this.slamTarget.x - this.x, this.slamTarget.z - this.z), dt, 2.5);
        if (this.stateT >= this.windTime) {
          const t = this.slamTarget; if (this.arms) { const l = this.arms.legs[this.armSide]; l.override = t; l.overrideRate = 38; }
          if (Math.hypot(P.x - t.x, P.z - t.z) < 3.1 + P.radius * 0.5) P.damage(24, t.x, t.z, 11);
          G.weapons.shockwave(t.x, t.z, 9.5, 10, 10);
          G.shake(1.3); G.hitStop(0.05); G.audio.play('boss_slam', { x: t.x, z: t.z });
          G.particles.sparks(t.x, 0.3, t.z, 0, 0, 40, [1.4, 0.9, 0.4], 9); G.particles.smoke(t.x, 0.4, t.z, 12, 1.3, [0.45, 0.42, 0.45], 1.4, 0.4);
          G.lights.burst(t.x, 1.5, t.z, 0xffb060, 90, 14, 0.25); G.decals.burn(t.x, t.z, 4.5);
          this.marker = null; this.setState('slamHit');
        }
        break;
      }
      case 'slamHit':
        this.brake(dt, 5);
        if (this.stateT > (this.phase >= 3 ? 0.3 : 0.45)) {
          this.endOverride(); this.combo--;
          if (this.combo > 0 && this.distToPlayer < 9 && !P.dead) this.beginSlam();
          else { this.setState('recover'); this.recoverT = this.phase >= 3 ? 0.9 : 1.3; }
        }
        break;
      case 'volleyWind':
        this.brake(dt, 4); this.facePlayer(dt, 2.5); this.glow = damp(this.glow, 1, 6, dt); this.rear = 0.6;
        if (this.stateT > 0.8) { this.volleyLeft = [0, 4, 6, 7][this.phase]; this.volleyT = 0; this.setState('volley'); }
        break;
      case 'volley':
        this.brake(dt, 4); this.facePlayer(dt, 1.5); this.glow = 1; this.volleyT -= dt;
        if (this.volleyT <= 0 && this.volleyLeft > 0) {
          this.volleyLeft--; this.volleyT = 0.14;
          const m = this.furnacePos(_v); const sp = 3.4 + this.phase;
          const tx = P.x + P.vx * 0.7 + (Math.random() - 0.5) * sp * 2, tz = P.z + P.vz * 0.7 + (Math.random() - 0.5) * sp * 2;
          G.weapons.lob(m.x, m.y, m.z, tx, tz, 0.95 + Math.random() * 0.35, { radius: 1.45, damage: 13, puddle: 2.5, fire: true, size: 1.3 });
          G.audio.play('boss_spit', { x: this.x, z: this.z, gain: 0.7, rate: 0.95 + Math.random() * 0.2 }); G.particles.embers(m.x, m.y, m.z, 6, 0.6); G.lights.burst(m.x, m.y, m.z, 0xff6a18, 40, 9, 0.12);
        }
        if (this.volleyLeft <= 0 && this.volleyT <= -0.3) { this.setState('recover'); this.recoverT = 0.9; }
        break;
      case 'chargeWind':
        this.brake(dt, 6); this.facePlayer(dt, 3.5); this.rear = 1;
        if (this.stateT > 1.0) { this.chargeDir.x = Math.sin(this.facing); this.chargeDir.z = Math.cos(this.facing); this.hitDone = false; this.setState('charge'); }
        else if (!this.marker) { /* line telegraph: a row of markers along the path */
          for (let i = 1; i <= 4; i++) G.weapons.telegraph(this.x + Math.sin(this.facing) * i * 3.4, this.z + Math.cos(this.facing) * i * 3.4, 2.0, 1.0 - this.stateT);
          this.marker = { t: 0, dur: 0 };
        }
        break;
      case 'charge': {
        this.marker = null; this.vx = this.chargeDir.x * 13; this.vz = this.chargeDir.z * 13;
        if (Math.random() < 0.7) G.particles.smoke(this.x + (Math.random() - 0.5) * 3, 0.3, this.z + (Math.random() - 0.5) * 3, 1, 1, [0.4, 0.38, 0.4], 0.6, 0.25);
        if (!this.hitDone && d < this.radius + P.radius + 0.2) { this.hitDone = true; P.damage(26, this.x - this.chargeDir.x, this.z - this.chargeDir.z, 13); }
        const blocked = this.lastHitWall && (G.grid.hitNx * this.chargeDir.x + G.grid.hitNz * this.chargeDir.z) < -0.4;
        if ((blocked && this.stateT > 0.15) || this.stateT > 1.25) {
          if (blocked) { G.shake(1.2); G.audio.play('boss_slam', { x: this.x, z: this.z, rate: 0.8 }); G.particles.sparks(this.x + this.chargeDir.x * 2, 1.5, this.z + this.chargeDir.z * 2, -this.chargeDir.x, -this.chargeDir.z, 40, [1.3, 1, 0.6], 9); }
          this.vx = this.vz = 0; this.setState('recover'); this.recoverT = blocked ? 2.2 : 1.2;
        }
        break;
      }
      case 'ringWind':
        this.brake(dt, 6); this.glow = damp(this.glow, 1, 5, dt); this.rear = 0.8;
        if (this.stateT > 0.75) { this.ringsLeft = 3; this.ringT = 0; this.setState('ring'); }
        break;
      case 'ring':
        this.brake(dt, 6); this.glow = 1; this.ringT -= dt;
        if (this.ringT <= 0 && this.ringsLeft > 0) {
          const k = 3 - this.ringsLeft; this.ringsLeft--; this.ringT = 0.7; const n = 12;
          for (let i = 0; i < n; i++) { const a = (i + k * 0.5) / n * 6.283; G.weapons.fireball(this.x + Math.sin(a) * 2.4, this.z + Math.cos(a) * 2.4, Math.sin(a), Math.cos(a), 5.0, { damage: 10 }); }
          G.audio.play('boss_spit', { x: this.x, z: this.z, rate: 0.7 }); G.lights.burst(this.x, 2, this.z, 0xff6a18, 80, 14, 0.2); G.shake(0.4);
        }
        if (this.ringsLeft <= 0 && this.ringT <= -0.2) { this.setState('recover'); this.recoverT = 1.4; }
        break;
      case 'recover':
        this.brake(dt, 5); this.facePlayer(dt, this.turnRate * 0.5);
        if (this.stateT > (this.recoverT || 1)) { this.setState('idle'); this.gap = [0, 1.1, 0.8, 0.5][this.phase] + Math.random() * 0.4; }
        break;
    }
    this.pushPlayer();
  }

  animate(dt) {
    const G = this.G; const t = this.age;
    const hot = 1.1 + this.glow * 3.6 + (this.phase - 1) * 0.6 + Math.sin(t * 5) * 0.2;
    if (this.furnaceMat) this.furnaceMat.emissiveIntensity = this.state === 'dormant' ? 0.5 + Math.sin(t * 1.2) * 0.2 : hot;
    if (this.sacMat) this.sacMat.emissiveIntensity = 0.8 + Math.sin(t * 2.5) * 0.3 + this.fury * 4;
    if (this.eyeMat) this.eyeMat.emissiveIntensity = this.state === 'dormant' ? 0 : 3 + this.phase;
    if (this.state !== 'dormant' && Math.random() < dt * (3 + this.glow * 20)) { const m = this.furnacePos(_v); G.particles.embers(m.x, m.y, m.z, 1, 0.8); }
    if (this.state === 'dying' && this.model) { this.model.rotation.z = Math.sin(t * 23) * 0.04; this.model.rotation.x = Math.sin(t * 17) * 0.03; }
    if (!this.rig) return;
    const R = this.rig; const dormant = this.state === 'dormant';
    const breath = Math.sin(t * (dormant ? 0.9 : 1.7)) * (dormant ? 0.05 : 0.07) + this.rear * 0.35 - (this.state === 'slamHit' ? 0.18 : 0);
    R.offset('body', 0, breath, 0);
    R.rot('body', -this.rear * 0.16 + (this.state === 'charge' ? 0.18 : 0), 0, Math.sin(t * 0.8) * 0.02);
    R.rot('chest', Math.sin(t * 1.7 + 0.6) * 0.03 - this.rear * 0.1, 0, 0);
    const yaw = dormant ? 0 : Math.max(-0.6, Math.min(0.6, angDiff(this.facing, this.angleToPlayer())));
    R.rot('neck', (dormant ? 0.5 : 0.1) + Math.sin(t * 1.1) * 0.06 - this.rear * 0.5, yaw * 0.5, Math.sin(t * 0.7) * 0.1);
    R.rot('head', (dormant ? 0.4 : 0) + Math.sin(t * 2.3) * 0.05, yaw * 0.5, Math.sin(t * 1.9) * (this.state === 'dying' ? 0.5 : 0.08));
    for (let i = 1; i <= 3; i++) R.rot('tail_' + i, 0, Math.sin(t * 1.3 - i * 0.9) * 0.2, 0);
    for (let i = 1; i <= 4; i++) R.scale('sac_' + i, 1 + Math.sin(t * 2.5 + i * 1.7) * 0.07 + this.fury * 0.3);
    R.rot('arm_L_hand', 0, 0, 0); R.rot('arm_R_hand', 0, 0, 0);
    if (this.arms) this.arms.update(dt, breath, 1);
  }
  animateDeath(dt) {
    const k = Math.min(1, this.deathT / 1.2), e = k * k;
    this.model.scale.set(1 + e * 0.12, 1 - e * 0.42, 1 + e * 0.12); this.model.rotation.z = e * 0.12;
    if (this.furnaceMat) this.furnaceMat.emissiveIntensity = Math.max(0.05, 3 * (1 - k));
    if (this.sacMat) this.sacMat.emissiveIntensity = Math.max(0, 1 - k); if (this.eyeMat) this.eyeMat.emissiveIntensity = 0;
    this.deathT = Math.min(this.deathT, 20);   // the corpse stays
  }
}
void _c;
