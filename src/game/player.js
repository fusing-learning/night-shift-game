import * as THREE from 'three';
import { PLAYER, GUN, BLADE } from '../config.js';
import { Rig, damp, angDiff } from './rig.js';

const _v = new THREE.Vector3(), _q = new THREE.Quaternion(), _axis = new THREE.Vector3(), _d = new THREE.Vector3();
const mv = { x: 0, z: 0 };

function arcGeometry(inner, outer, arc, seg = 28) {
  const p = [], t = [], idx = [];
  for (let i = 0; i <= seg; i++) {
    const k = i / seg, a = -arc / 2 + arc * k;
    p.push(Math.sin(a) * inner, 0, Math.cos(a) * inner, Math.sin(a) * outer, 0, Math.cos(a) * outer); t.push(k, 0, k, 1);
    if (i < seg) { const j = i * 2; idx.push(j, j + 1, j + 2, j + 1, j + 3, j + 2); }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(p, 3)); g.setAttribute('aT', new THREE.Float32BufferAttribute(t, 2)); g.setIndex(idx);
  return g;
}

export class Player {
  constructor(G) {
    this.G = G;
    this.x = 0; this.z = 0; this.vx = 0; this.vz = 0; this.facing = Math.PI; this.radius = PLAYER.radius;
    this.hp = PLAYER.hp; this.energy = GUN.energyMax; this.heat = 0; this.overheat = 0; this.fireT = 0; this.regenT = 0;
    this.dodgeT = 0; this.dodgeCd = 0; this.dodgeDx = 0; this.dodgeDz = 1; this.iframes = 0;
    this.bladeT = 0; this.bladeCd = 0; this.bladeHit = false; this.bladeSide = 1; this.bladeGlow = 0;
    this.hasKey = false; this.flashOn = true; this.dead = false; this.deadT = 0; this.hurtFlash = 0;
    this.phase = 0; this.moveAmt = 0; this.stepSide = 0; this.recoil = 0; this.control = true;
    this.kx = 0; this.kz = 0;    // knockback velocity
    this.lean = new THREE.Vector2();
    this.muzzle = new THREE.Vector3(); this.aimDir = new THREE.Vector3(0, 0, -1);

    this.root = new THREE.Group(); G.scene.add(this.root);
    this.model = G.assets.makeCreature('player');
    if (this.model) { this.root.add(this.model); this.rig = new Rig(this.model); }
    else {
      const m = new THREE.Mesh(new THREE.CapsuleGeometry(0.25, 0.45, 4, 10), new THREE.MeshStandardMaterial({ color: 0xcfd3d6, roughness: 0.8 }));
      m.position.y = 0.5; m.castShadow = true; this.root.add(m);
      const v = new THREE.Mesh(new THREE.SphereGeometry(0.1), G.assets.mats.glow_amber); v.position.set(0, 0.8, 0.22); this.root.add(v);
      this.model = m; this.rig = null;
    }
    // gun (kept in root space so it always points where the player faces)
    this.gun = G.assets.models.gun ? G.assets.makeCreature('gun') : new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.1, 0.4), G.assets.mats.metal_dark);
    this.gun.traverse((o) => { if (o.isMesh) o.castShadow = false; });
    this.root.add(this.gun); this.gun.position.set(-0.2, 0.52, 0.3);
    // energy blade
    const bladeMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(1.2, 4.5, 6.0), transparent: true, opacity: 1, fog: false });
    this.blade = new THREE.Mesh(new THREE.BoxGeometry(0.045, 0.045, 1.25), bladeMat); this.blade.geometry.translate(0, 0, 0.72);
    this.bladePivot = new THREE.Group(); this.bladePivot.add(this.blade); this.bladePivot.position.set(0, 0.55, 0); this.root.add(this.bladePivot); this.blade.visible = false;
    this.arc = new THREE.Mesh(arcGeometry(0.55, BLADE.range, BLADE.arc), new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
      uniforms: { uP: { value: 0 }, uDir: { value: 1 }, uA: { value: 0 } },
      vertexShader: 'attribute vec2 aT; varying vec2 vT; void main(){ vT = aT; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
      fragmentShader: `uniform float uP, uDir, uA; varying vec2 vT; void main(){ float k = uDir > 0.0 ? vT.x : 1.0 - vT.x;
        float head = smoothstep(uP + 0.02, uP - 0.02, k); float tail = smoothstep(uP - 0.55, uP, k);
        float r = smoothstep(0.0, 0.5, vT.y) * (0.35 + 0.65*smoothstep(0.55, 1.0, vT.y)) * smoothstep(1.0, 0.93, vT.y);
        gl_FragColor = vec4(vec3(0.25, 0.9, 1.3) * head * tail * tail * r * uA * 2.2, 1.0); }`,
    }));
    this.arc.position.y = 0.55; this.arc.visible = false; this.arc.renderOrder = 8; this.root.add(this.arc);
  }

  place(x, z, facing) { this.x = this.safeX = x; this.z = this.safeZ = z; this.facing = facing; this.vx = this.vz = this.kx = this.kz = 0; this.sync(0); }

  reset() {
    this.hp = PLAYER.hp; this.energy = GUN.energyMax; this.heat = 0; this.overheat = 0; this.dead = false; this.deadT = 0;
    this.dodgeT = 0; this.bladeT = 0; this.iframes = 1.0; this.control = true; this.root.rotation.set(0, 0, 0); this.model.rotation.set(0, 0, 0);
  }

  heal(n) { this.hp = Math.min(PLAYER.hp, this.hp + n); }
  addEnergy(n) { this.energy = Math.min(GUN.energyMax, this.energy + n); }

  damage(amount, fromX, fromZ, knock = 4) {
    const G = this.G;
    if (this.dead || this.iframes > 0 || G.godMode) return false;
    this.hp -= amount; this.iframes = PLAYER.hurtIFrames; this.hurtFlash = 1;
    let dx = this.x - fromX, dz = this.z - fromZ; const l = Math.hypot(dx, dz) || 1; dx /= l; dz /= l;
    this.kx += dx * knock; this.kz += dz * knock;
    G.shake(0.5 + amount / 40); G.fxDamage(amount);
    G.particles.blood(this.x, 0.6, this.z, dx, dz, 8, 3.5);
    G.audio.play('player_hurt', { gain: 1 });
    if (this.hp <= 0) { this.hp = 0; this.die(); }
    return true;
  }
  die() {
    const G = this.G;
    this.dead = true; this.deadT = 0; this.control = false;
    G.audio.play('player_death'); G.particles.blood(this.x, 0.5, this.z, 0, 0, 30, 5);
    for (let i = 0; i < 5; i++) G.decals.splat(this.x + (Math.random() - 0.5), this.z + (Math.random() - 0.5), 1.2);
    G.onPlayerDeath();
  }

  update(dt) {
    const G = this.G, inp = G.input, grid = G.grid;
    this.iframes = Math.max(0, this.iframes - dt); this.hurtFlash = Math.max(0, this.hurtFlash - dt * 3);
    this.dodgeCd -= dt; this.bladeCd -= dt; this.fireT -= dt; this.recoil = Math.max(0, this.recoil - dt * 9);
    if (this.dead) { this.deadT += dt; this.sync(dt); return; }
    const can = this.control && !G.cutscene;

    // aim
    if (can) {
      const dx = inp.aim.x - this.x, dz = inp.aim.z - this.z;
      if (dx * dx + dz * dz > 0.04) { const target = Math.atan2(dx, dz); this.facing += angDiff(this.facing, target) * Math.min(1, dt * 22); }
    }
    const fx = Math.sin(this.facing), fz = Math.cos(this.facing);

    // movement
    const moving = can && inp.moveAxis(mv);
    if (can && inp.hit('ShiftLeft') || can && inp.hit('ShiftRight')) {
      if (this.dodgeCd <= 0 && this.dodgeT <= 0) {
        if (moving) { this.dodgeDx = mv.x; this.dodgeDz = mv.z; } else { this.dodgeDx = -fx; this.dodgeDz = -fz; }
        this.dodgeT = PLAYER.dodgeTime; this.dodgeCd = PLAYER.dodgeCooldown; this.iframes = Math.max(this.iframes, PLAYER.dodgeIFrames);
        G.audio.play('dodge', { gain: 0.8 });
      }
    }
    let tvx = 0, tvz = 0;
    if (this.dodgeT > 0) {
      this.dodgeT -= dt; const k = 0.55 + 0.45 * (this.dodgeT / PLAYER.dodgeTime);
      this.vx = this.dodgeDx * PLAYER.dodgeSpeed * k; this.vz = this.dodgeDz * PLAYER.dodgeSpeed * k;
    } else {
      if (moving) { const slow = this.bladeT > 0 ? 0.6 : 1; tvx = mv.x * PLAYER.speed * slow; tvz = mv.z * PLAYER.speed * slow; }
      this.vx = damp(this.vx, tvx, 16, dt); this.vz = damp(this.vz, tvz, 16, dt);
    }
    this.kx = damp(this.kx, 0, 7, dt); this.kz = damp(this.kz, 0, 7, dt);
    const px = this.x, pz = this.z;
    if (grid.isSolid(this.x, this.z)) { if (this.safeX !== undefined) { this.x = this.safeX; this.z = this.safeZ; } } else { this.safeX = this.x; this.safeZ = this.z; }
    grid.move(this, this.radius, (this.vx + this.kx) * dt, (this.vz + this.kz) * dt);
    if (grid.isSolid(this.x, this.z) && this.safeX !== undefined) { this.x = this.safeX; this.z = this.safeZ; }
    const moved = Math.hypot(this.x - px, this.z - pz);
    const speed = moved / Math.max(dt, 1e-4);
    this.moveAmt = damp(this.moveAmt, Math.min(1, speed / PLAYER.speed), 12, dt);
    const prevPhase = this.phase; this.phase += moved * 5.2;
    if (this.dodgeT <= 0 && Math.floor(this.phase / Math.PI) !== Math.floor(prevPhase / Math.PI) && speed > 1) {
      G.audio.play(G.floorIsGrate(this.x, this.z) ? 'footstep_grate' : 'footstep_metal', { gain: 0.5, rate: 0.92 + Math.random() * 0.16 });
    }

    // flashlight toggle
    if (can && inp.hit('KeyF')) { this.flashOn = !this.flashOn; G.audio.play('flashlight_click'); }

    // gun
    if (this.overheat > 0) { this.overheat -= dt; if (this.overheat <= 0) { this.heat = 0.35; G.audio.play('laser_ready', { gain: 0.7 }); } }
    else this.heat = Math.max(0, this.heat - GUN.coolRate * dt);
    this.regenT -= dt; if (this.regenT <= 0) this.energy = Math.min(GUN.energyMax, this.energy + GUN.regenRate * dt);
    this.muzzle.set(this.x + fx * 0.62 - fz * -0.02, 0.62, this.z + fz * 0.62);
    if (can && inp.fire && this.fireT <= 0 && this.dodgeT <= 0 && this.bladeT <= 0) {
      if (this.overheat > 0) { /* locked */ }
      else if (this.energy < GUN.shotCost) { this.fireT = 0.3; G.audio.play('laser_empty', { gain: 0.8 }); G.hud.pulse('energy'); }
      else {
        this.fireT = GUN.fireInterval; this.energy -= GUN.shotCost; this.regenT = GUN.regenDelay; this.heat += GUN.heatPerShot; this.recoil = 1;
        const spread = (Math.random() - 0.5) * 0.035 * (1 + this.heat);
        const a = this.facing + spread;
        G.weapons.fireBolt(this.muzzle.x, this.muzzle.z, Math.sin(a), Math.cos(a));
        G.alertNoise(this.x, this.z, 18);
        if (this.heat >= 1) { this.overheat = GUN.overheatLock; G.audio.play('laser_overheat'); G.particles.smoke(this.muzzle.x, 0.7, this.muzzle.z, 5, 0.3, [0.6, 0.8, 0.9], 1.5, 0.35); G.hud.pulse('heat'); }
      }
    }

    // blade
    if (can && inp.melee && this.bladeCd <= 0 && this.dodgeT <= 0) {
      this.bladeT = BLADE.swingTime; this.bladeCd = BLADE.cooldown; this.bladeHit = false; this.bladeSide = -this.bladeSide; this.bladeGlow = 1;
      G.audio.play('blade_swing', { gain: 0.9, rate: 0.95 + Math.random() * 0.1 }); G.audio.play('blade_ignite', { gain: 0.35, rate: 1.3 });
      G.lights.burst(this.x + fx, 0.8, this.z + fz, 0x40d8ff, 26, 7, 0.22);
    }
    if (this.bladeT > 0) {
      this.bladeT -= dt;
      const p = 1 - this.bladeT / BLADE.swingTime;
      if (!this.bladeHit && p > 0.35) { this.bladeHit = true; G.weapons.bladeStrike(this.x, this.z, this.facing); }
    }
    this.bladeGlow = Math.max(0, this.bladeGlow - dt * 3.2);
    this.sync(dt);
  }

  // push transform + procedural pose to the scene
  sync(dt) {
    const G = this.G; const fx = Math.sin(this.facing), fz = Math.cos(this.facing);
    this.root.position.set(this.x, 0, this.z); this.root.rotation.y = this.facing;
    this.aimDir.set(fx, 0, fz);
    // local-space movement direction
    const lvx = this.vx * fz - this.vz * fx, lvz = this.vx * fx + this.vz * fz;
    const sp = Math.hypot(lvx, lvz) || 1; const mx = lvx / sp, mz = lvz / sp;
    const amt = this.moveAmt, ph = this.phase;
    const m = this.model;
    // dodge roll: spin around the axis perpendicular to the dodge direction
    if (this.dodgeT > 0 && !this.dead) {
      const k = 1 - this.dodgeT / PLAYER.dodgeTime;
      const ldx = this.dodgeDx * fz - this.dodgeDz * fx, ldz = this.dodgeDx * fx + this.dodgeDz * fz;
      _axis.set(ldz, 0, -ldx).normalize(); m.quaternion.setFromAxisAngle(_axis, k * Math.PI * 2);
      m.position.y = (this.rig ? 0 : 0.5) + Math.sin(k * Math.PI) * 0.25; if (this.rig) m.position.y += 0.3 * Math.sin(k * Math.PI);
    } else if (this.dead) {
      const k = Math.min(1, this.deadT / 0.55); m.quaternion.setFromAxisAngle(_axis.set(1, 0, 0), -k * k * Math.PI / 2); m.position.y = (this.rig ? 0 : 0.5) + 0.12 * k;
    } else {
      this.lean.x = damp(this.lean.x, lvx * 0.035, 10, dt || 0.016); this.lean.y = damp(this.lean.y, lvz * 0.035, 10, dt || 0.016);
      m.rotation.set(this.lean.y, 0, -this.lean.x); m.position.y = (this.rig ? 0 : 0.5) + Math.abs(Math.sin(ph)) * 0.035 * amt;
    }
    const swingP = this.bladeT > 0 ? 1 - this.bladeT / BLADE.swingTime : -1;
    const R = this.rig;
    if (R && R.ok) {
      _axis.set(-mz, 0, mx);
      const s = Math.sin(ph) * 0.75 * amt, c = Math.cos(ph);
      R.rot('hips', 0, Math.sin(ph) * 0.12 * amt, 0);
      const twist = swingP >= 0 ? this.bladeSide * (0.9 - swingP * 1.8) : 0;
      R.rot('spine', 0.08 * amt, twist * 0.5, 0); R.rot('chest', 0.05, twist * 0.5, 0);
      R.rot('head', -0.05, -twist * 0.6, 0);
      // legs
      R.rel('leg_L_upper', _q.setFromAxisAngle(_axis, s)); R.rel('leg_L_lower', _q.setFromAxisAngle(_axis, -Math.max(0, c) * 0.95 * amt - 0.05));
      R.rel('leg_R_upper', _q.setFromAxisAngle(_axis, -s)); R.rel('leg_R_lower', _q.setFromAxisAngle(_axis, -Math.max(0, -c) * 0.95 * amt - 0.05));
      R.rot('leg_L_foot', 0, 0, 0); R.rot('leg_R_foot', 0, 0, 0);
      // right arm holds the gun out in front
      const rec = this.recoil * 0.16;
      R.aim('arm_R_upper', _d.set(-0.28, -0.55 + rec, 0.8)); R.aim('arm_R_lower', _d.set(0.12, -0.05 + rec * 2, 1)); R.aim('arm_R_hand', _d.set(0, 0, 1));
      // left arm: blade arm
      if (swingP >= 0 || this.bladeGlow > 0.3) {
        const a = this.bladeSide * (1.15 - Math.max(0, swingP) * 2.3);
        R.aim('arm_L_upper', _d.set(Math.sin(a) + 0.2, -0.15, Math.cos(a))); R.aim('arm_L_lower', _d.set(Math.sin(a), 0, Math.cos(a))); R.aim('arm_L_hand', _d.set(Math.sin(a), 0, Math.cos(a)));
      } else {
        R.aim('arm_L_upper', _d.set(0.25, -0.75, 0.35 - s * 0.25)); R.aim('arm_L_lower', _d.set(-0.25, -0.3, 0.9)); R.aim('arm_L_hand', _d.set(-0.3, 0, 1));
      }
      // gun follows the right hand
      const hand = R.bones.arm_R_hand || R.bones.arm_R_end;
      if (hand) { m.updateWorldMatrix(true, true); hand.bone.getWorldPosition(_v); this.root.worldToLocal(_v); this.gun.position.set(_v.x, _v.y + 0.02, _v.z + 0.02 - this.recoil * 0.05); }
    }
    this.gun.visible = !this.dead && this.dodgeT <= 0;
    // blade + arc
    const show = swingP >= 0 || this.bladeGlow > 0.25;
    this.blade.visible = show && !this.dead;
    if (show) {
      const a = this.bladeSide * (BLADE.arc / 2) * (1 - Math.min(1, Math.max(0, swingP < 0 ? 1 : swingP)) * 2);
      this.bladePivot.rotation.y = a; this.blade.material.opacity = Math.min(1, this.bladeGlow * 2 + (swingP >= 0 ? 1 : 0));
    }
    this.arc.visible = this.bladeGlow > 0.02 && !this.dead;
    if (this.arc.visible) {
      const u = this.arc.material.uniforms; u.uDir.value = -this.bladeSide; u.uP.value = swingP >= 0 ? swingP * 1.15 : 1.4; u.uA.value = Math.min(1, this.bladeGlow * 1.6);
    }
    // hurt flash on materials
    const mats = this.model.userData?.materials;
    if (mats) for (const mt of mats) if (!mt.userData.glow) { mt.emissive.setRGB(this.hurtFlash * 0.9, 0, 0); }
    // flashlight
    const flick = (this.iframes > 0 && this.hurtFlash > 0.4) ? 0.4 : 1;
    G.lights.flashFlicker = damp(G.lights.flashFlicker, flick * G.flashInterference, 30, dt || 0.016);
    _v.set(this.x + fx * 0.3, 1.45, this.z + fz * 0.3); _d.set(fx, -0.24, fz);
    G.lights.setFlashlight(_v, _d, this.flashOn && !this.dead);
  }
}
