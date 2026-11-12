import * as THREE from 'three';
import { Rig, damp, angDiff } from '../rig.js';

const flowOut = { x: 0, z: 0 };
const _v = new THREE.Vector3();

// Shared behaviour: perception, steering (line of sight -> direct, otherwise flow field), separation, damage, death.
export class Enemy {
  constructor(G, type, x, z, o = {}) {
    this.G = G; this.type = type; this.x = x; this.z = z; this.vx = 0; this.vz = 0; this.kx = 0; this.kz = 0;
    this.facing = o.facing ?? Math.random() * 6.283; this.radius = 0.4; this.hp = this.maxHp = 30; this.speed = 3; this.mass = 1;
    this.state = 'idle'; this.stateT = 0; this.dead = false; this.removed = false; this.alerted = false; this.dormant = o.dormant ?? true;
    this.wakeRange = o.wakeRange ?? 9; this.flash = 0; this.untargetable = false; this.zone = o.zone ?? -1; this.group = o.group || null;
    this.losT = Math.random() * 0.2; this.sees = false; this.distToPlayer = 99; this.turnRate = 8; this.age = 0; this.deathT = 0;
    this.bloodColor = [0.5, 0.02, 0.02]; this.flashGain = 1; this.gibCount = 4; this.corpse = true; this.height = 0.6; this.dropChance = 0.12;
    this.root = new THREE.Group(); this.root.position.set(x, 0, z); G.scene.add(this.root);
    this.model = G.assets.makeCreature(type);
    if (this.model) { this.root.add(this.model); this.rig = new Rig(this.model); this.mats = this.model.userData.materials || []; }
    else { this.model = this.placeholder(); this.root.add(this.model); this.rig = null; this.mats = [this.model.material]; }
    this.spawnT = o.spawnFx ? 0.5 : 0; if (o.spawnFx) this.spawnBurst();
  }
  placeholder() {
    const m = new THREE.Mesh(new THREE.CapsuleGeometry(0.3, 0.4, 4, 8), new THREE.MeshStandardMaterial({ color: 0xc9b3ae, roughness: 0.4 }));
    m.position.y = 0.5; m.castShadow = true; return m;
  }
  spawnBurst() {
    const G = this.G; G.particles.smoke(this.x, 0.3, this.z, 6, 0.7, [0.4, 0.45, 0.5], 1.2, 0.3); G.particles.blood(this.x, 0.4, this.z, 0, 0, 8, 3, this.bloodColor);
  }
  setState(s) { this.state = s; this.stateT = 0; }

  alert(silent) {
    if (this.alerted || this.dead) return;
    this.alerted = true; this.dormant = false; this.onAlert(silent);
    // wake the rest of the pack
    if (this.group) for (const e of this.G.enemies) if (e !== this && e.group === this.group) e.alert(true);
  }
  onAlert() {}

  perceive(dt) {
    const P = this.G.player, G = this.G;
    const dx = P.x - this.x, dz = P.z - this.z; this.distToPlayer = Math.hypot(dx, dz);
    this.losT -= dt;
    if (this.losT <= 0) { this.losT = 0.12 + Math.random() * 0.08; this.sees = this.distToPlayer < 30 && G.grid.los(this.x, this.z, P.x, P.z); }
    if (!this.alerted && !P.dead) {
      const range = this.wakeRange * (P.flashOn ? 1 : 0.45);
      if (this.distToPlayer < range && this.sees) this.alert();
      else if (this.distToPlayer < 1.6) this.alert();
    }
  }

  // Accelerate toward the player (or a point) at `speed`. Returns the unit direction used.
  seek(dt, speed, accel = 9, tx, tz) {
    const G = this.G, P = G.player; let dx, dz;
    if (tx !== undefined) { dx = tx - this.x; dz = tz - this.z; }
    else if (this.sees && this.distToPlayer < 16) { dx = P.x - this.x; dz = P.z - this.z; }
    else { const d = G.grid.flow(this.x, this.z, flowOut); if (d === Infinity) { dx = P.x - this.x; dz = P.z - this.z; } else { dx = flowOut.x; dz = flowOut.z; } }
    const l = Math.hypot(dx, dz) || 1; dx /= l; dz /= l;
    this.vx = damp(this.vx, dx * speed, accel, dt); this.vz = damp(this.vz, dz * speed, accel, dt);
    flowOut.x = dx; flowOut.z = dz; return flowOut;
  }
  brake(dt, k = 10) { this.vx = damp(this.vx, 0, k, dt); this.vz = damp(this.vz, 0, k, dt); }
  face(angle, dt, rate = this.turnRate) { this.facing += angDiff(this.facing, angle) * Math.min(1, dt * rate); }
  facePlayer(dt, rate) { const P = this.G.player; this.face(Math.atan2(P.x - this.x, P.z - this.z), dt, rate); }
  faceVelocity(dt, rate) { if (this.vx * this.vx + this.vz * this.vz > 0.05) this.face(Math.atan2(this.vx, this.vz), dt, rate); }
  angleToPlayer() { const P = this.G.player; return Math.atan2(P.x - this.x, P.z - this.z); }

  separate(dt) {
    for (const e of this.G.enemies) {
      if (e === this || e.dead || e.noSeparate) continue;
      const dx = this.x - e.x, dz = this.z - e.z, r = this.radius + e.radius, d2 = dx * dx + dz * dz;
      if (d2 >= r * r || d2 < 1e-6) continue;
      const d = Math.sqrt(d2), push = (r - d) * 0.5 * Math.min(1, dt * 14) * (e.mass / (this.mass + e.mass)) * 2;
      this.x += dx / d * push; this.z += dz / d * push;
    }
  }
  // Solid body vs player (heavy things shove the player).
  pushPlayer() {
    const P = this.G.player; if (P.dodgeT > 0) return;
    const dx = P.x - this.x, dz = P.z - this.z, r = this.radius + P.radius, d2 = dx * dx + dz * dz;
    if (d2 >= r * r || d2 < 1e-6) return;
    const d = Math.sqrt(d2), k = this.mass > 3 ? 1 : 0.5, push = Math.min(0.6, (r - d) * k);
    // move the player with full collision so nothing can ever be shoved into a wall
    this.G.grid.move(P, P.radius, dx / d * push, dz / d * push);
    if (k < 1) { this.x -= dx / d * (r - d) * 0.5; this.z -= dz / d * (r - d) * 0.5; }
  }
  integrate(dt) {
    this.kx = damp(this.kx, 0, 6, dt); this.kz = damp(this.kz, 0, 6, dt);
    const g = this.G.grid;
    const hit = g.move(this, this.gridRadius ?? Math.min(this.radius, 0.9), (this.vx + this.kx) * dt, (this.vz + this.kz) * dt);
    const hx = g.hitNx, hz = g.hitNz;
    if (g.isSolid(this.x, this.z)) { if (this.safeX !== undefined) { this.x = this.safeX; this.z = this.safeZ; } } else { this.safeX = this.x; this.safeZ = this.z; }
    g.hitNx = hx; g.hitNz = hz;
    return hit;
  }
  knock(kx, kz) { this.kx += kx / this.mass; this.kz += kz / this.mass; }

  damageMult() { return 1; }
  damage(amount, dx, dz, kind, hx, hz) {
    if (this.dead) return;
    const G = this.G; const mult = this.damageMult(kind, dx, dz);
    const dmg = amount * mult; this.hp -= dmg; this.flash = 1;
    const px = hx ?? this.x, pz = hz ?? this.z;
    if (mult >= 0.5) {
      G.particles.blood(px, this.height, pz, dx, dz, kind === 'blade' ? 16 : 7, kind === 'blade' ? 6 : 4, this.bloodColor);
      if (Math.random() < (kind === 'blade' ? 0.9 : 0.35)) G.decals.splat(px + dx * (0.5 + Math.random()), pz + dz * (0.5 + Math.random()), 0.6 + Math.random() * 0.7, this.decalColor());
      if (kind === 'laser') G.audio.play('laser_hit_flesh', { x: px, z: pz, gain: 0.7, rate: 0.9 + Math.random() * 0.2 });
    } else {
      G.particles.sparks(px, this.height, pz, -dx, -dz, 8, [1, 1, 1], 5); G.audio.play('laser_hit_metal', { x: px, z: pz, gain: 0.5, rate: 1.3 });
    }
    this.alert(); this.onDamage(dmg, kind, dx, dz);
    if (this.hp <= 0) this.die(dx, dz);
  }
  onDamage() {}
  decalColor() { return [this.bloodColor[0] * 0.42, this.bloodColor[1] * 0.3, this.bloodColor[2] * 0.3]; }

  die(dx = 0, dz = 0) {
    if (this.dead) return;
    const G = this.G; this.dead = true; this.deathT = 0; this.untargetable = true; this.vx = this.vz = 0;
    G.particles.blood(this.x, this.height, this.z, dx, dz, 26, 6, this.bloodColor);
    for (let i = 0; i < 3; i++) G.decals.splat(this.x + (Math.random() - 0.5) * this.radius * 2, this.z + (Math.random() - 0.5) * this.radius * 2, 0.9 + this.radius, this.decalColor());
    G.gibs.burst(this.x, this.height, this.z, this.gibCount, dx, dz);
    G.audio.play('gore_splat', { x: this.x, z: this.z, gain: 0.8 });
    this.onDeath(dx, dz);
    G.onEnemyKilled(this);
    if (!this.corpse) this.remove();
  }
  onDeath() {}
  remove() { if (this.removed) return; this.removed = true; this.G.scene.remove(this.root); }

  update(dt) {
    this.age += dt; this.stateT += dt; this.flash = Math.max(0, this.flash - dt * 5);
    if (this.dead) {
      this.deathT += dt; this.animateDeath(dt);
      if (this.deathT > 26) { this.root.position.y -= dt * 0.25; if (this.root.position.y < -1.2) this.remove(); }
      return;
    }
    this.perceive(dt);
    if (this.spawnT > 0) { this.spawnT -= dt; this.root.scale.setScalar(Math.max(0.05, 1 - this.spawnT / 0.5)); } else if (this.root.scale.x !== 1 && !this.customScale) this.root.scale.setScalar(1);
    this.think(dt);
    this.separate(dt);
    this.lastHitWall = this.integrate(dt);
    this.root.position.x = this.x; this.root.position.z = this.z; this.root.rotation.y = this.facing;
    this.animate(dt);
    const f = this.flash;
    for (const m of this.mats) if (!m.userData.glow && m.emissive) m.emissive.setRGB(f * 0.3 * this.flashGain, f * 0.24 * this.flashGain, f * 0.2 * this.flashGain);
  }
  think() {}
  animate() {}
  animateDeath(dt) {
    // default: slump and flatten
    const k = Math.min(1, this.deathT / 0.5);
    this.model.rotation.x = -k * 1.2; this.model.position.y = (this.rig ? 0 : 0.5) * (1 - k) + 0.1 * k;
  }
  // world position of a bone
  bonePos(name, out = _v) { const b = this.rig?.bones[name]; if (!b) return out.set(this.x, this.height, this.z); return b.bone.getWorldPosition(out); }
  glowMat(name) { return this.mats.find((m) => m.userData.glow === name); }
}

// Small physics gore chunks.
export class Gibs {
  constructor(G) {
    this.G = G; this.items = []; this.src = [];
    for (let i = 1; i <= 6; i++) { const p = G.assets.props['gib_' + i]; if (p) this.src.push(p); }
    this.fallbackGeo = new THREE.DodecahedronGeometry(0.1, 0); this.fallbackMat = new THREE.MeshStandardMaterial({ color: 0x5a0d0d, roughness: 0.3 });
  }
  burst(x, y, z, n, dx = 0, dz = 0, speed = 5) {
    for (let i = 0; i < n; i++) {
      if (this.items.length > 60) { const old = this.items.shift(); this.G.scene.remove(old.o); }
      let o;
      if (this.src.length) { o = this.src[(Math.random() * this.src.length) | 0].clone(); o.traverse((m) => { if (m.isMesh) { m.castShadow = true; } }); }
      else { o = new THREE.Mesh(this.fallbackGeo, this.fallbackMat); o.castShadow = true; }
      const a = Math.random() * 6.283, s = speed * (0.3 + Math.random() * 0.8);
      o.position.set(x + (Math.random() - 0.5) * 0.3, y + Math.random() * 0.3, z + (Math.random() - 0.5) * 0.3); o.scale.setScalar(0.7 + Math.random() * 0.8);
      this.G.scene.add(o);
      this.items.push({ o, vx: dx * s * 0.8 + Math.cos(a) * s * 0.6, vy: 2 + Math.random() * 4, vz: dz * s * 0.8 + Math.sin(a) * s * 0.6, sx: (Math.random() - 0.5) * 14, sz: (Math.random() - 0.5) * 14, life: 14 + Math.random() * 6, rest: false, trail: 0.5 });
    }
  }
  clear() { for (const g of this.items) this.G.scene.remove(g.o); this.items.length = 0; }
  update(dt) {
    const G = this.G;
    for (let i = this.items.length - 1; i >= 0; i--) {
      const g = this.items[i]; g.life -= dt;
      if (!g.rest) {
        g.vy -= 16 * dt; const p = g.o.position; const nx = p.x + g.vx * dt, nz = p.z + g.vz * dt;
        if (G.grid.isSolid(nx, nz, 2)) { g.vx *= -0.35; g.vz *= -0.35; } else { p.x = nx; p.z = nz; }
        p.y += g.vy * dt; g.o.rotation.x += g.sx * dt; g.o.rotation.z += g.sz * dt;
        g.trail -= dt; if (g.trail > 0 && Math.random() < 0.4) G.particles.blood(p.x, p.y, p.z, 0, 0, 1, 0.6);
        if (p.y < 0.07) { p.y = 0.07; if (Math.abs(g.vy) < 1.6) { g.rest = true; if (Math.random() < 0.6) G.decals.splat(p.x, p.z, 0.5); } else { g.vy *= -0.35; g.vx *= 0.55; g.vz *= 0.55; g.sx *= 0.5; g.sz *= 0.5; } }
      }
      if (g.life < 1) g.o.position.y -= dt * 0.15;
      if (g.life <= 0) { G.scene.remove(g.o); this.items.splice(i, 1); }
    }
  }
}
export { damp, angDiff };
