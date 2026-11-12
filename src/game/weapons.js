import * as THREE from 'three';
import { GUN, BLADE } from '../config.js';
import { SHOT } from '../world/grid.js';
import { angDiff } from './rig.js';

const UP = new THREE.Vector3(0, 1, 0);

// Player bolts, blade strikes and hostile projectiles.
export class Weapons {
  constructor(G) {
    this.G = G; this.bolts = []; this.shots = []; this.puddles = []; this.waves = []; this.marks = [];
    this.boltGeo = new THREE.CapsuleGeometry(0.045, 0.75, 3, 6); this.boltGeo.rotateX(Math.PI / 2);
    this.boltMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(0.8, 4.2, 6.5), fog: false });
    this.blobGeo = new THREE.IcosahedronGeometry(0.24, 1);
    this.bileMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(0.9, 1.5, 0.12), fog: false });
    this.fireMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(2.6, 0.62, 0.08), fog: false });
    const ring = new THREE.RingGeometry(0.95, 1, 56); ring.rotateX(-Math.PI / 2);
    this.ringGeo = ring;
    const disc = new THREE.CircleGeometry(1, 32); disc.rotateX(-Math.PI / 2); this.discGeo = disc;
    // soft, blotchy pool texture for acid / fire puddles
    { const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d'); g.fillStyle = '#000'; g.fillRect(0, 0, 128, 128);
      const gr = g.createRadialGradient(64, 64, 4, 64, 64, 62); gr.addColorStop(0, 'rgba(255,255,255,0.55)'); gr.addColorStop(0.6, 'rgba(255,255,255,0.32)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
      for (let i = 0; i < 46; i++) { const a = Math.random() * 6.283, d = Math.random() * 46, r = 3 + Math.random() * 9; const b = g.createRadialGradient(64 + Math.cos(a) * d, 64 + Math.sin(a) * d, 0, 64 + Math.cos(a) * d, 64 + Math.sin(a) * d, r); b.addColorStop(0, 'rgba(255,255,255,0.7)'); b.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = b; g.fillRect(0, 0, 128, 128); }
      this.poolTex = new THREE.CanvasTexture(c); this.poolTex.colorSpace = THREE.SRGBColorSpace; }
    this.pool = [];
  }

  clear() {
    for (const b of this.bolts) this.G.scene.remove(b.mesh);
    for (const s of this.shots) { this.G.scene.remove(s.mesh); if (s.marker) this.G.scene.remove(s.marker); }
    for (const p of this.puddles) this.G.scene.remove(p.mesh);
    for (const w of this.waves) this.G.scene.remove(w.mesh);
    for (const m of this.marks) this.G.scene.remove(m.mesh);
    this.bolts.length = this.shots.length = this.puddles.length = this.waves.length = this.marks.length = 0;
  }

  // Create one of every effect off-stage so their shaders are compiled before play starts (avoids first-use hitches).
  prewarm() {
    const x = -200, z = -200, A = this.G.audio, play = A.play; A.play = () => null;   // silent
    this.fireBolt(x, z, 1, 0); this.lob(x, 1, z, x + 1, z, 1, {}); this.lob(x, 1, z, x + 1, z, 1, { fire: true }); this.fireball(x, z, 1, 0, 1);
    this.shockwave(x, z, 1, 2, 0); this.puddle(x, z, 1, 1, false); this.puddle(x, z, 1, 1, true); this.telegraph(x, z, 1, 1);
    A.play = play; this.G.trauma = 0;
  }

  // ── player laser ──
  fireBolt(x, z, dx, dz) {
    const G = this.G;
    const mesh = new THREE.Mesh(this.boltGeo, this.boltMat); mesh.position.set(x, 0.62, z); mesh.rotation.y = Math.atan2(dx, dz);
    G.scene.add(mesh);
    this.bolts.push({ x, z, dx, dz, dist: 0, mesh });
    G.lights.burst(x, 0.9, z, 0x50d8ff, 55, 9, 0.09);
    G.particles.glow(x, 0.62, z, 0.9, [0.5, 1.6, 2.4], 0.07);
    G.audio.play('laser_shot', { gain: 0.85, rate: 0.96 + Math.random() * 0.08 });
    G.shake(0.08);
  }

  updateBolts(dt) {
    const G = this.G, grid = G.grid;
    for (let i = this.bolts.length - 1; i >= 0; i--) {
      const b = this.bolts[i]; const step = GUN.speed * dt;
      const nx = b.x + b.dx * step, nz = b.z + b.dz * step;
      let t = grid.raycast(b.x, b.z, nx, nz, SHOT), hitWall = t < 1, wnx = grid.hitNx, wnz = grid.hitNz;
      // enemies along the segment
      let best = null, bt = t;
      for (const e of G.enemies) {
        if (e.dead || e.untargetable) continue;
        const ex = e.x - b.x, ez = e.z - b.z; const proj = (ex * b.dx + ez * b.dz) / step;
        if (proj < -0.2 || proj > bt + e.radius / step) continue;
        const pc = Math.max(0, Math.min(bt, proj)); const cx = b.x + b.dx * step * pc - e.x, cz = b.z + b.dz * step * pc - e.z;
        const r = e.radius + 0.12;
        if (cx * cx + cz * cz < r * r) { const tt = Math.max(0, pc - r / step * 0.6); if (!best || tt < bt) { best = e; bt = tt; } }
      }
      if (best) {
        const hx = b.x + b.dx * step * bt, hz = b.z + b.dz * step * bt;
        best.damage(GUN.damage, b.dx, b.dz, 'laser', hx, hz);
        G.particles.sparks(hx, 0.65, hz, -b.dx, -b.dz, 6, [0.5, 1.0, 1.2], 4);
        G.particles.glow(hx, 0.65, hz, 1.2, [0.5, 1.5, 2.2], 0.1);
        G.lights.burst(hx, 0.8, hz, 0x60dcff, 30, 6, 0.1);
        G.scene.remove(b.mesh); this.bolts.splice(i, 1); continue;
      }
      if (hitWall || b.dist > GUN.range) {
        if (hitWall) {
          const hx = b.x + b.dx * step * t, hz = b.z + b.dz * step * t;
          G.particles.sparks(hx, 0.65, hz, wnx, wnz, 12, [0.6, 1.0, 1.2], 6);
          G.particles.glow(hx, 0.65, hz, 1.4, [0.5, 1.4, 2.0], 0.1);
          G.lights.burst(hx + wnx * 0.3, 0.8, hz + wnz * 0.3, 0x60dcff, 34, 6, 0.12);
          G.particles.smoke(hx + wnx * 0.2, 0.65, hz + wnz * 0.2, 1, 0.25, [0.5, 0.6, 0.7], 0.8, 0.2);
          G.audio.play('laser_hit_metal', { x: hx, z: hz, gain: 0.55, rate: 0.9 + Math.random() * 0.2 });
        }
        G.scene.remove(b.mesh); this.bolts.splice(i, 1); continue;
      }
      b.x = nx; b.z = nz; b.dist += step; b.mesh.position.set(nx, 0.62, nz);
      if (Math.random() < 0.6) G.particles.glow(nx - b.dx * 0.5, 0.62, nz - b.dz * 0.5, 0.35, [0.2, 0.8, 1.2], 0.12, 0.6);
    }
  }

  // ── energy blade ──
  bladeStrike(x, z, facing) {
    const G = this.G; let hits = 0;
    for (const e of G.enemies) {
      if (e.dead || e.untargetable) continue;
      const dx = e.x - x, dz = e.z - z, d = Math.hypot(dx, dz);
      if (d > BLADE.range + e.radius) continue;
      const a = Math.atan2(dx, dz);
      if (d > e.radius + 0.5 && Math.abs(angDiff(facing, a)) > BLADE.arc / 2 + 0.15) continue;
      const nx = dx / (d || 1), nz = dz / (d || 1);
      e.damage(BLADE.damage, nx, nz, 'blade', e.x - nx * e.radius, e.z - nz * e.radius);
      e.knock(nx * BLADE.knockback, nz * BLADE.knockback);
      hits++;
    }
    // deflect projectiles
    for (const s of this.shots) { if (s.kind === 'fire' && Math.hypot(s.x - x, s.z - z) < BLADE.range) s.life = 0; }
    if (hits) {
      G.player.addEnergy(BLADE.energyOnHit * hits);
      G.audio.play('blade_hit', { gain: 1 }); G.shake(0.3); G.hitStop(0.05);
    }
    return hits;
  }

  // ── hostile projectiles ──
  // Lobbed blob that lands on a marked spot and leaves a damaging puddle.
  lob(x, y, z, tx, tz, flight, o = {}) {
    const G = this.G;
    const mat = o.fire ? this.fireMat : this.bileMat;
    const mesh = new THREE.Mesh(this.blobGeo, mat); mesh.scale.setScalar(o.size || 1); G.scene.add(mesh);
    const marker = new THREE.Mesh(this.ringGeo, new THREE.MeshBasicMaterial({ color: o.fire ? new THREE.Color(2.5, 0.5, 0.1) : new THREE.Color(1.0, 1.6, 0.2), transparent: true, opacity: 0.0, depthWrite: false, blending: THREE.AdditiveBlending }));
    const radius = o.radius || 1.5; marker.scale.setScalar(radius); marker.position.set(tx, 0.04, tz); G.scene.add(marker);
    this.shots.push({ kind: 'lob', x, y, z, sx: x, sy: y, sz: z, tx, tz, t: 0, flight, mesh, marker, radius, damage: o.damage || 14, fire: !!o.fire, puddle: o.puddle ?? 4, life: 1 });
  }
  // Slow straight fireball.
  fireball(x, z, dx, dz, speed, o = {}) {
    const G = this.G;
    const mesh = new THREE.Mesh(this.blobGeo, this.fireMat); mesh.scale.setScalar(o.size || 1.1); G.scene.add(mesh);
    this.shots.push({ kind: 'fire', x, y: 0.7, z, dx, dz, speed, mesh, radius: 0.32 * (o.size || 1.1), damage: o.damage || 12, life: o.life || 6 });
  }
  // Expanding ground shockwave ring.
  shockwave(x, z, speed, maxR, damage) {
    const G = this.G;
    const mesh = new THREE.Mesh(this.ringGeo, new THREE.MeshBasicMaterial({ color: new THREE.Color(2.4, 0.7, 0.2), transparent: true, opacity: 0.9, depthWrite: false, blending: THREE.AdditiveBlending }));
    mesh.position.set(x, 0.06, z); G.scene.add(mesh);
    this.waves.push({ x, z, r: 0.5, speed, maxR, damage, mesh, hit: false });
  }
  puddle(x, z, radius, life, fire) {
    const G = this.G;
    const mesh = new THREE.Mesh(this.discGeo, new THREE.MeshBasicMaterial({ color: fire ? new THREE.Color(1.9, 0.42, 0.04) : new THREE.Color(0.5, 0.95, 0.08), map: this.poolTex, transparent: true, opacity: 0.8, depthWrite: false, blending: THREE.AdditiveBlending }));
    mesh.scale.setScalar(radius * 1.25); mesh.rotation.y = Math.random() * 6.283; mesh.position.set(x, 0.035, z); G.scene.add(mesh);
    this.puddles.push({ x, z, radius, life, max: life, mesh, fire, tick: 0 });
  }

  updateHostile(dt) {
    const G = this.G, P = G.player, grid = G.grid;
    for (let i = this.shots.length - 1; i >= 0; i--) {
      const s = this.shots[i];
      if (s.kind === 'lob') {
        s.t += dt / s.flight; const k = Math.min(1, s.t);
        s.x = s.sx + (s.tx - s.sx) * k; s.z = s.sz + (s.tz - s.sz) * k; s.y = s.sy * (1 - k) + Math.sin(k * Math.PI) * (2.2 + s.flight * 2.2) + 0.1;
        s.mesh.position.set(s.x, s.y, s.z); s.mesh.rotation.x += dt * 5; s.mesh.rotation.z += dt * 3;
        s.marker.material.opacity = 0.25 + 0.6 * k * (0.6 + 0.4 * Math.sin(G.time * 30));
        if (Math.random() < 0.5) (s.fire ? G.particles.embers(s.x, s.y, s.z, 1, 0.2) : G.particles.add.emit(s.x, s.y, s.z, 0, -0.5, 0, 0.3, 0.16, 0.02, 0.5, 0.9, 0.1, 0.8, 4, 0));
        if (k >= 1) {
          const d = Math.hypot(P.x - s.tx, P.z - s.tz);
          if (d < s.radius + P.radius * 0.5) P.damage(s.damage, s.tx, s.tz, 3);
          if (s.fire) { G.particles.sparks(s.tx, 0.2, s.tz, 0, 0, 18, [1.4, 0.5, 0.1], 5); G.particles.smoke(s.tx, 0.3, s.tz, 3, 0.6, [0.4, 0.3, 0.25], 1.2); G.lights.burst(s.tx, 0.8, s.tz, 0xff6a18, 40, 8, 0.25); G.decals.burn(s.tx, s.tz, s.radius * 1.6); }
          else { G.particles.bile(s.tx, 0.2, s.tz, 16); G.lights.burst(s.tx, 0.6, s.tz, 0xb8ff3a, 16, 6, 0.25); G.decals.splat(s.tx, s.tz, s.radius * 1.3, [0.10, 0.16, 0.01]); }
          G.audio.play('bile_splat', { x: s.tx, z: s.tz, gain: 0.8 });
          if (s.puddle > 0) this.puddle(s.tx, s.tz, s.radius * 0.9, s.puddle, s.fire);
          G.scene.remove(s.mesh); G.scene.remove(s.marker); this.shots.splice(i, 1);
        }
      } else {
        s.life -= dt;
        const nx = s.x + s.dx * s.speed * dt, nz = s.z + s.dz * s.speed * dt;
        const blocked = grid.raycast(s.x, s.z, nx, nz, SHOT) < 1;
        s.x = nx; s.z = nz; s.mesh.position.set(nx, 0.7, nz); s.mesh.rotation.y += dt * 6;
        if (Math.random() < 0.7) G.particles.embers(nx, 0.7, nz, 1, 0.25);
        if (Math.random() < 0.3) G.particles.glow(nx, 0.7, nz, 0.5, [0.7, 0.18, 0.02], 0.12, 0.6);
        const d = Math.hypot(P.x - nx, P.z - nz);
        let dead = blocked || s.life <= 0;
        if (d < s.radius + P.radius) { if (P.damage(s.damage, nx - s.dx, nz - s.dz, 3)) dead = true; }
        if (dead) { G.particles.sparks(nx, 0.7, nz, -s.dx, -s.dz, 8, [1.4, 0.5, 0.1], 4); G.scene.remove(s.mesh); this.shots.splice(i, 1); }
      }
    }
    for (let i = this.puddles.length - 1; i >= 0; i--) {
      const p = this.puddles[i]; p.life -= dt; p.tick -= dt;
      p.mesh.material.opacity = 0.85 * Math.min(1, p.life / 1.0) * (0.75 + 0.25 * Math.sin(G.time * 9 + i)); p.mesh.rotation.y += dt * 0.4;
      if (Math.random() < dt * 8) (p.fire ? G.particles.embers(p.x, 0.1, p.z, 1, p.radius * 1.4) : G.particles.add.emit(p.x + (Math.random() - 0.5) * p.radius, 0.05, p.z + (Math.random() - 0.5) * p.radius, 0, 0.8, 0, 0.5, 0.1, 0.02, 0.5, 0.9, 0.1, 0.7, -0.5, 0));
      if (p.tick <= 0 && Math.hypot(P.x - p.x, P.z - p.z) < p.radius && P.dodgeT <= 0) { p.tick = 0.45; P.damage(p.fire ? 7 : 5, p.x, p.z, 0.5); }
      if (p.life <= 0) { G.scene.remove(p.mesh); this.puddles.splice(i, 1); }
    }
    for (let i = this.waves.length - 1; i >= 0; i--) {
      const w = this.waves[i]; const pr = w.r; w.r += w.speed * dt;
      w.mesh.scale.setScalar(w.r); w.mesh.material.opacity = 0.9 * (1 - w.r / w.maxR);
      const d = Math.hypot(P.x - w.x, P.z - w.z);
      if (!w.hit && d >= pr - 0.35 && d <= w.r + 0.35 && P.dodgeT <= 0) { if (P.damage(w.damage, w.x, w.z, 6)) w.hit = true; }
      if (Math.random() < 0.6) { const a = Math.random() * 6.283; G.particles.smoke(w.x + Math.cos(a) * w.r, 0.1, w.z + Math.sin(a) * w.r, 1, 0.4, [0.5, 0.4, 0.35], 0.6, 0.18); }
      if (w.r >= w.maxR) { G.scene.remove(w.mesh); this.waves.splice(i, 1); }
    }
  }

  // Ground warning marker for a melee/area attack. Returns a handle (x, z and t can be adjusted).
  telegraph(x, z, radius, dur, color) {
    const G = this.G;
    const mesh = new THREE.Group();
    const c = color || new THREE.Color(2.2, 0.22, 0.08);
    const ring = new THREE.Mesh(this.ringGeo, new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0.9, depthWrite: false, blending: THREE.AdditiveBlending }));
    const fill = new THREE.Mesh(this.discGeo, new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: 0.1, depthWrite: false, blending: THREE.AdditiveBlending }));
    const grow = new THREE.Mesh(this.ringGeo, ring.material);
    ring.scale.setScalar(radius); mesh.add(ring, fill, grow); mesh.position.set(x, 0.05, z); G.scene.add(mesh);
    const m = { mesh, ring, fill, grow, x, z, radius, t: 0, dur }; this.marks.push(m); return m;
  }
  updateMarks(dt) {
    for (let i = this.marks.length - 1; i >= 0; i--) {
      const m = this.marks[i]; m.t += dt; const k = Math.min(1, m.t / m.dur);
      m.fill.scale.setScalar(m.radius); m.fill.material.opacity = 0.03 + 0.07 * k; m.grow.scale.setScalar(Math.max(0.01, m.radius * k)); m.ring.material.opacity = 0.5 + 0.5 * Math.sin(m.t * 26) * k;
      if (m.t >= m.dur + 0.06) { this.G.scene.remove(m.mesh); this.marks.splice(i, 1); }
    }
  }

  update(dt) { this.updateBolts(dt); this.updateHostile(dt); this.updateMarks(dt); }
}
void UP;
