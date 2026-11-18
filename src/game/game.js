import * as THREE from 'three';
import { CAM, CELL, DEBUG, PLAYER, GUN } from '../config.js';
import { FLOOR } from '../world/grid.js';
import { buildGrid, LIGHTS, PICKUPS, CHECKPOINTS, Z } from '../world/leveldata.js';
import { Level } from '../world/levelbuild.js';
import { LightRig } from '../gfx/lights.js';
import { Particles, Decals } from '../gfx/particles.js';
import { Player } from './player.js';
import { Weapons } from './weapons.js';
import { Gibs } from './enemies/base.js';
import { Crawler, Spitter, Stalker, Brute } from './enemies/types.js';
import { Boss } from './enemies/boss.js';
import { damp } from './rig.js';

const RED = 0xff2a1a, GREEN = 0x38ff7a;
const _v = new THREE.Vector3(), _focus = new THREE.Vector3();

export class Game {
  constructor({ gfx, assets, audio, input, hud }) {
    this.gfx = gfx; this.scene = gfx.scene; this.assets = assets; this.audio = audio; this.input = input; this.hud = hud;
    this.CAM = CAM; this.time = 0; this.enemies = []; this.pickups = []; this.timers = [];
    this.trauma = 0; this.freeze = 0; this.dmgFx = 0; this.fade = 1; this.fadeTarget = 0; this.fadeSpeed = 0.6; this.fadeColor = new THREE.Color(0, 0, 0);
    this.letterbox = 0; this.cutscene = null; this.godMode = DEBUG.has('god'); this.flashInterference = 1;
    this.stats = { time: 0, deaths: 0, kills: 0 }; this.state = 'title'; this.curZone = Z.DOCK; this.checkpoint = CHECKPOINTS[0];
    this.camDist = CAM.dist; this.focus = new THREE.Vector3(30, 0, 164); this.combatT = 0; this.musicT = 0; this.ambT = 4; this.flowT = 0; this.titleT = 0;
    this.flags = this.freshFlags(); this.cpFlags = this.freshFlags();

    this.scene.environment = assets.envMap; this.scene.environmentIntensity = 0.55;
    this.grid = buildGrid();
    this.level = new Level(this.scene, this.grid, assets);
    this.lights = new LightRig(this.scene, LIGHTS.map((l) => ({ ...l })));
    this.particles = new Particles(this.scene, this.lights.uni);
    this.decals = new Decals(this.scene);
    this.particles.onBloodLand = (x, z) => { if (Math.random() < 0.5) this.decals.splat(x, z, 0.25 + Math.random() * 0.35); };
    this.gibs = new Gibs(this);
    this.weapons = new Weapons(this);
    this.player = new Player(this);
    this.buildPickups();
    this.interactables = [
      { x: 33.4, z: 153.6, r: 1.7, prompt: () => (this.flags.door1 ? null : (this.flags.key ? 'USE KEYCARD' : 'LOCKED — KEYCARD REQUIRED')), can: () => this.flags.key && !this.flags.door1, act: () => this.useKeycard(), deny: () => this.audio.play('door_locked') },
      { x: 59.2, z: 125.8, r: 1.8, prompt: () => (this.flags.power ? null : 'RESTORE POWER'), can: () => !this.flags.power, act: () => this.pullBreaker() },
    ];
    this.decoy = null;
    addEventListener('resize', () => this.onResize()); this.onResize();
    this.loadCheckpoint(CHECKPOINTS[Math.min(4, +(DEBUG.get('cp') || 0))], true);
    if (DEBUG.has('bladelab')) import('../debug/bladelab.js').then((m) => { this.lab = m.initLab(this); });   // blade test room
  }

  freshFlags() { return { key: false, door1: false, scare: 0, power: false, ambush: 0, asmCleared: false, whStalker: false, arena: 0, arenaCleared: false, door4: false, boss: 0, bossDead: false, hints: {} }; }
  onResize() { this.particles.setScale(innerHeight * Math.min(devicePixelRatio || 1, 2) * this.gfx.quality, CAM.fov * Math.PI / 180); }

  // ───────── helpers used by entities ─────────
  shake(a) { this.trauma = Math.min(1.6, this.trauma + a); }
  hitStop(t) { this.freeze = Math.max(this.freeze, t); }
  fxDamage(amount) { this.dmgFx = Math.min(1, this.dmgFx + 0.35 + amount / 60); }
  after(t, fn) { this.timers.push({ t, fn }); }
  floorIsGrate(x, z) { const cx = Math.floor(x / CELL), cz = Math.floor(z / CELL); return this.grid.floor[cz * this.grid.w + cx] === FLOOR.GRATE; }
  zoneAt(x, z) { const cx = Math.floor(x / CELL), cz = Math.floor(z / CELL); if (cx < 0 || cz < 0 || cx >= this.grid.w || cz >= this.grid.h) return -1; return this.grid.zone[cz * this.grid.w + cx]; }
  isTorchOn(x, z) {
    const P = this.player, L = this.lights; if (!P.flashOn || P.dead || L.flashFlicker < 0.5) return false;
    const dx = x - P.x, dz = z - P.z, d = Math.hypot(dx, dz); if (d > 17) return false; if (d < 0.8) return true;
    const dot = (dx * Math.sin(P.facing) + dz * Math.cos(P.facing)) / d;
    return dot > Math.cos(L.flash.angle * 0.95) && this.grid.los(P.x, P.z, x, z);
  }
  alertNoise(x, z, radius) { for (const e of this.enemies) if (!e.alerted && !e.dead && e.wakeRange > 0 && Math.hypot(e.x - x, e.z - z) < radius && this.zoneAt(e.x, e.z) === this.curZone) e.alert(); }
  spawn(Type, x, z, o = {}) { const e = new Type(this, x, z, { zone: this.zoneAt(x, z), ...o }); this.enemies.push(e); if (o.alert) e.alert(o.silent ?? true); return e; }

  // ───────── pickups ─────────
  buildPickups() { for (const p of PICKUPS) this.spawnPickup(p.kind, p.x, p.z, p.id, true); }
  // nearest spot with room to stand, so drops never land inside props or walls
  freeSpot(x, z) {
    const g = this.grid, ok = (px, pz) => !g.isSolid(px, pz) && !g.isSolid(px + 0.4, pz) && !g.isSolid(px - 0.4, pz) && !g.isSolid(px, pz + 0.4) && !g.isSolid(px, pz - 0.4);
    if (ok(x, z)) return [x, z];
    for (let r = 0.5; r <= 4; r += 0.5) for (let a = 0; a < 12; a++) { const px = x + Math.cos(a / 12 * 6.283) * r, pz = z + Math.sin(a / 12 * 6.283) * r; if (ok(px, pz) && g.los(x, z, px, pz) !== undefined) return [px, pz]; }
    return [this.player.x, this.player.z];
  }
  spawnPickup(kind, x, z, id, fixed = false) {
    if (!fixed) [x, z] = this.freeSpot(x, z);
    const name = { energy: 'pickup_energy', health: 'pickup_health', key: 'pickup_key' }[kind];
    let mesh = this.assets.makeProp(name);
    if (!mesh) { const col = { energy: 'glow_cyan', health: 'glow_green', key: 'glow_amber' }[kind]; mesh = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.35, 0.22), this.assets.mats[col]); mesh.geometry.translate(0, 0.18, 0); }
    mesh.traverse((o) => { if (o.isMesh) o.castShadow = false; });
    const holder = new THREE.Group(); holder.add(mesh); holder.position.set(x, 0.25, z); this.scene.add(holder);
    if (kind === 'key') { mesh.rotation.x = -0.9; mesh.scale.setScalar(1.6); }
    const p = { kind, x, z, id, fixed, holder, taken: false, zone: this.zoneAt(x, z), seed: Math.random() * 6 };
    this.pickups.push(p); return p;
  }
  updatePickups(dt) {
    const P = this.player, col = { energy: [0.2, 0.9, 1.2], health: [0.2, 1.1, 0.5], key: [1.2, 0.7, 0.2] };
    for (let i = this.pickups.length - 1; i >= 0; i--) {
      const p = this.pickups[i]; if (p.taken) continue;
      p.holder.rotation.y += dt * 1.6; p.holder.position.y = 0.3 + Math.sin(this.time * 2.4 + p.seed) * 0.08;
      if (Math.random() < dt * 5) this.particles.glow(p.x + (Math.random() - 0.5) * 0.3, 0.3 + Math.random() * 0.5, p.z + (Math.random() - 0.5) * 0.3, 0.12, col[p.kind], 0.5, 0.8);
      if (Math.random() < dt * 1.2) this.particles.glow(p.x, 0.45, p.z, 1.1, col[p.kind].map((c) => c * 0.25), 0.5, 0.6);
      const d = Math.hypot(P.x - p.x, P.z - p.z);
      if (d > 0.95 || P.dead) continue;
      if (p.kind === 'health' && P.hp >= PLAYER.hp) continue;
      if (p.kind === 'energy' && P.energy >= GUN.energyMax - 1) continue;
      p.taken = true; p.holder.visible = false;
      this.particles.sparks(p.x, 0.5, p.z, 0, 0, 12, col[p.kind], 3); this.lights.burst(p.x, 0.8, p.z, new THREE.Color(...col[p.kind]).getHex(), 20, 6, 0.3);
      if (p.kind === 'energy') { P.addEnergy(50); this.audio.play('pickup_energy'); }
      else if (p.kind === 'health') { P.heal(35); this.audio.play('pickup_health'); }
      else { this.audio.play('pickup_key'); this.onKeyTaken(); }
      if (!p.fixed) { this.scene.remove(p.holder); this.pickups.splice(i, 1); }
    }
  }

  // ───────── checkpoints / world state ─────────
  setCheckpoint(i) {
    const cp = CHECKPOINTS[i]; if (!cp || this.checkpoint.id >= cp.id) return;
    this.checkpoint = cp; this.cpFlags = JSON.parse(JSON.stringify(this.flags));
    this.audio.play('checkpoint', { gain: 0.8 }); this.hud.toast('CHECKPOINT');
  }
  loadCheckpoint(cp, first = false) {
    this.checkpoint = cp;
    if (first) {
      const f = this.flags;
      if (cp.id >= 1) { f.key = f.door1 = true; f.scare = 2; }
      if (cp.id >= 2) { f.power = true; f.ambush = 3; f.asmCleared = true; }
      if (cp.id >= 4) { f.arena = 3; f.arenaCleared = true; }
      this.cpFlags = JSON.parse(JSON.stringify(f));
    }
    this.flags = JSON.parse(JSON.stringify(this.cpFlags));
    for (const e of this.enemies) e.remove(); this.enemies.length = 0;
    this.weapons.clear(); this.gibs.clear(); this.timers.length = 0; this.ambushT = 0; this.arenaT = 0; this.cutscene = null; this.letterbox = 0; this.boss = null;
    if (this.decoy) { this.scene.remove(this.decoy.root); this.decoy = null; }
    for (let i = this.pickups.length - 1; i >= 0; i--) {
      const p = this.pickups[i];
      if (!p.fixed) { this.scene.remove(p.holder); this.pickups.splice(i, 1); continue; }
      if (p.zone >= cp.zone && !(p.kind === 'key' && this.flags.key)) { p.taken = false; p.holder.visible = true; }
      if (p.kind === 'key' && this.flags.key) { p.taken = true; p.holder.visible = false; }
    }
    this.applyFlags(true);
    for (let z = cp.zone; z <= Z.BOSS; z++) this.spawnZone(z);
    const P = this.player; P.reset(); P.hasKey = this.flags.key; P.place(cp.x, cp.z, cp.face);
    this.curZone = cp.zone; this.focus.set(cp.x, 0, cp.z - 2); this.camDist = CAM.dist;
    this.audio.stopLoops(); this.hud.bossBar(null);
    this.setObjective();
  }
  applyFlags(instant) {
    const f = this.flags, L = this.lights, lv = this.level;
    const door = (id, open) => { lv.setDoor(id, open); if (instant) { const d = lv.doors[id]; d.open = d.target; d.mesh.position.y = d.open * 4.05; d.box.active = d.open < 0.55; } };
    door('door1', f.door1); door('door2', f.asmCleared); door('doorE', !(f.arena > 0 && !f.arenaCleared)); door('door3', f.arenaCleared);
    door('door4', f.door4 && !(f.boss > 0 && !f.bossDead)); door('doorX', f.bossDead);
    this.grid.rebuildDynamic(Object.values(lv.doors).map((d) => d.box));
    L.setFixture('beacon1', { color: f.door1 ? GREEN : RED }); L.setFixture('beacon2', { color: f.asmCleared ? GREEN : RED }); L.setFixture('beacon3', { color: f.arenaCleared ? GREEN : RED });
    L.setFixture('genLamp', { color: f.power ? GREEN : RED });
    for (const fx of L.fixtures) if (fx.power) fx.on = f.power;
    L.setFixture('corridorScare', { on: true, dim: 1 });
    L.setFixture('bossKey', { color: 0x8fb4ff, intensity: 900, flicker: 0 }); L.setFixture('bossFill', { on: false });
    L.setFixture('bossRedA', { intensity: 0, flicker: 0 }); L.setFixture('bossRedB', { intensity: 0, flicker: 0 }); L.setFixture('bossPit', { intensity: 0 });
    L.setFixture('exitLight', { intensity: f.bossDead ? 1100 : 0 }); L.setFixture('exitGlow', { intensity: f.bossDead ? 40 : 0 });
    lv.pitHot.color.setHex(0x993311);
    const lever = lv.refs.breaker?.getObjectByName('lever'); if (lever) lever.rotation.x = f.power ? 2.2 : 0;
    this.gfx.u.uTint.value.setRGB(0.78, 1.0, 1.1);
  }
  spawnZone(z) {
    const f = this.flags;
    if (z === Z.DOCK) {
      this.spawn(Crawler, 32.4, 156.2, { group: 'dock', wakeRange: 6.5, facing: 0.6 });
    } else if (z === Z.CORRIDOR && f.scare < 2) {
      const d = this.decoy = new Stalker(this, 30, 137.8, { facing: 0, wakeRange: 0 }); d.untargetable = true; d.root.rotation.y = 0;
      if (d.rig) { d.rig.rot('neck', -0.2, 0, 0.5); d.rig.rot('head', -0.3, 0, 0.4); }
    } else if (z === Z.ASSEMBLY && !f.asmCleared) {
      this.spawn(Crawler, 16, 121.6, { group: 'a1' }); this.spawn(Crawler, 17.6, 122.6, { group: 'a1' });
      this.spawn(Crawler, 36.4, 116.2, { group: 'a2' }); this.spawn(Crawler, 38.2, 117.2, { group: 'a2' }); this.spawn(Crawler, 34.6, 115.4, { group: 'a2' });
      this.spawn(Spitter, 21, 115.6, { facing: 2.6 });
    } else if (z === Z.WAREHOUSE) {
      this.spawn(Stalker, 27, 98, { facing: 1.57, wakeRange: 7.5 }); this.spawn(Stalker, 14.6, 103.6, { facing: 1.2, wakeRange: 7 });
      this.spawn(Crawler, 33, 90.2, { group: 'w1' }); this.spawn(Crawler, 34.6, 89.6, { group: 'w1' });
    } else if (z === Z.FURNACE && !f.arenaCleared) {
      this.brute = this.spawn(Brute, 30, 63.8, { facing: 0, wakeRange: 0 });
    } else if (z === Z.BOSS && !f.bossDead) {
      this.boss = this.spawn(Boss, 30, 21.5, { facing: 0 });
      // quiet mercy: each death to the boss shaves a little off its health (down to 70%)
      const k = Math.max(0.7, 1 - 0.08 * (this.bossRetries || 0)); this.boss.maxHp *= k; this.boss.hp = this.boss.maxHp;
    }
  }
  setObjective() {
    const f = this.flags; let t = '';
    if (!f.key) t = 'FIND A WAY THROUGH THE SHUTTER'; else if (!f.door1) t = 'USE THE KEYCARD ON THE SHUTTER';
    else if (!f.power) t = this.curZone >= Z.ASSEMBLY ? 'RESTORE POWER' : ''; else if (!f.asmCleared) t = 'SURVIVE';
    else if (f.arena > 0 && !f.arenaCleared) t = 'SURVIVE'; else if (f.boss > 0 && !f.bossDead) t = ''; else if (f.bossDead) t = 'LEAVE';
    this.hud.objective(t);
  }

  // ───────── scripted events ─────────
  onKeyTaken() {
    const f = this.flags; f.key = true; this.player.hasKey = true; this.setObjective();
    for (const fx of this.lights.fixtures) if (fx.zone === Z.DOCK && fx.kind === 'spot') { fx.dim = 0.03; }
    this.audio.play('stinger_scare', { gain: 0.9 }); this.shake(0.5);
    this.after(0.9, () => { for (const fx of this.lights.fixtures) if (fx.zone === Z.DOCK) fx.dim = 1; });
    this.after(0.5, () => {
      this.audio.play('steam_burst', { x: 18.5, z: 155.5 }); this.particles.smoke(18.6, 2.4, 155.5, 10, 0.8, [0.5, 0.55, 0.6], 0.6, 0.4);
      for (const [x, z] of [[19.4, 155.2], [19.8, 156.8], [20.4, 154.4], [21.2, 156]]) this.spawn(Crawler, x, z, { alert: true, spawnFx: true, silent: false });
    });
  }
  useKeycard() {
    const f = this.flags; f.door1 = true; this.audio.play('pickup_key'); this.after(0.35, () => { this.audio.play('door_open', { x: 30, z: 151 }); this.applyFlags(); });
    this.setObjective();
  }
  pullBreaker() {
    const f = this.flags; f.power = true; this.audio.play('switch_lever', { x: 59.2, z: 125.8 });
    const lever = this.level.refs.breaker?.getObjectByName('lever'); if (lever) lever.rotation.x = 2.2;
    this.particles.sparks(59.6, 1.8, 125.8, -1, 0, 20, [0.6, 0.9, 1.2], 5); this.lights.burst(59.4, 1.8, 125.8, 0x80d0ff, 50, 9, 0.3);
    this.after(0.5, () => this.audio.play('power_up', { gain: 1 }));
    this.after(1.6, () => { this.applyFlags(); this.setObjective(); });
    f.ambush = 1;
    this.after(3.2, () => {
      this.audio.play('stinger_scare', { gain: 0.8 }); this.audio.play('steam_burst', { x: 11, z: 119.5 });
      for (const [x, z] of [[11.6, 120.2], [12.6, 121.4], [11.8, 122.4]]) this.spawn(Crawler, x, z, { alert: true, spawnFx: true, ambush: true }).ambush = true;
      this.spawn(Spitter, 24.6, 114, { alert: true, spawnFx: true }).ambush = true;
      f.ambush = 2;
    });
    this.after(9.5, () => {
      this.audio.play('steam_burst', { x: 11, z: 128.6 });
      for (const [x, z] of [[11.6, 128.4], [12.4, 129.8], [12.2, 127.4], [13.4, 128.8]]) this.spawn(Crawler, x, z, { alert: true, spawnFx: true }).ambush = true;
      this.spawn(Spitter, 15.4, 133.4, { alert: true, spawnFx: true }).ambush = true;
      f.ambush = 3;
    });
  }
  startArena() {
    const f = this.flags; f.arena = 1; this.applyFlags(); this.audio.play('door_locked'); this.audio.play('brute_slam', { x: 18, z: 87, gain: 0.7 }); this.shake(0.5);
    this.brute?.alert(); this.setObjective();
    this.after(2.5, () => { for (const [x, z] of [[43, 81.4], [42, 82.6], [15.4, 81.6], [16.4, 82.8]]) this.spawn(Crawler, x, z, { alert: true, spawnFx: true }); });
  }
  arenaWave2() {
    const f = this.flags; f.arena = 2; this.audio.play('stinger_scare', { gain: 0.7 });
    this.spawn(Spitter, 16.4, 63.4, { alert: true, spawnFx: true }); this.spawn(Spitter, 43.6, 80.6, { alert: true, spawnFx: true });
    this.after(1.5, () => { for (const [x, z] of [[26, 62.4], [34, 62.4], [44, 66.6], [16, 77], [44, 78], [16, 66]]) this.spawn(Crawler, x, z, { alert: true, spawnFx: true }); this.spawn(Stalker, 45, 62.6, { alert: true, spawnFx: true, silent: false }); f.arena = 3; });
  }
  startBoss() {
    const f = this.flags, B = this.boss; f.boss = 1; this.applyFlags(); this.audio.play('brute_slam', { x: 30, z: 47, gain: 0.8 });
    this.audio.setMusic('none', 0.5); this.setObjective();
    this.cutscene = { t: 0, dur: 4.6 };
    this.after(1.3, () => { B.wake(); this.lights.setFixture('bossFill', { on: true }); this.lights.setFixture('bossPit', { intensity: 30 }); });
    this.after(4.6, () => { this.cutscene = null; this.hud.bossBar(1, B.name); f.boss = 2; this.audio.setMusic('boss', 0.4); });
  }
  onBossPhase(n) {
    const L = this.lights;
    if (n === 2) { L.setFixture('bossKey', { color: 0xffb070, intensity: 700 }); L.setFixture('bossRedA', { intensity: 26 }); L.setFixture('bossRedB', { intensity: 26 }); L.setFixture('bossPit', { intensity: 60 }); this.level.pitHot.color.setHex(0xdd4a14); }
    else { L.setFixture('bossKey', { color: 0xff5540, intensity: 800, flicker: 1 }); L.setFixture('bossRedA', { intensity: 55, flicker: 3 }); L.setFixture('bossRedB', { intensity: 55, flicker: 3 }); L.setFixture('bossPit', { intensity: 90 }); this.level.pitHot.color.setHex(0xff5a18); this.audio.loop('amb_alarm', 0.5); }
    this.hud.flashBoss();
  }
  onBossDying() { this.audio.setMusic('none', 0.4); this.audio.loop('amb_alarm', 0); for (const e of this.enemies) if (e.fromBoss && !e.dead) e.die(0, 0); this.hud.bossBar(null); this.hitStop(0.25); }
  onBossDead() {
    const f = this.flags, L = this.lights; f.bossDead = true; f.boss = 3;
    L.setFixture('bossKey', { color: 0x9fbfff, intensity: 600, flicker: 0 }); L.setFixture('bossRedA', { intensity: 0 }); L.setFixture('bossRedB', { intensity: 0 }); L.setFixture('bossPit', { intensity: 8 });
    this.level.pitHot.color.setHex(0x551a08);
    this.after(2.5, () => { this.audio.setMusic('quiet', 3); this.audio.play('door_open', { x: 30, z: 11 }); this.level.setDoor('doorX', true); L.setFixture('exitLight', { intensity: 1100 }); L.setFixture('exitGlow', { intensity: 40 }); this.setObjective(); });
  }
  onEnemyKilled(e) {
    this.stats.kills++; const P = this.player;
    if (Math.random() < e.dropChance && e.type !== 'boss') this.spawnPickup(P.hp < 45 && Math.random() < 0.5 ? 'health' : 'energy', e.x, e.z);
  }
  onPlayerDeath() {
    this.stats.deaths++; if (this.flags.boss > 0 && !this.flags.bossDead) this.bossRetries = (this.bossRetries || 0) + 1; this.state = 'dead'; this.audio.setMusic('none', 0.3); this.audio.stopLoops(); this.audio.play('mus_death', { gain: 1 });
    this.fadeTarget = 0.82; this.fadeSpeed = 0.5; this.fadeColor.setRGB(0.05, 0, 0);
    this.after(1.4, () => this.hud.showDeath(true));
  }
  respawn() {
    this.hud.showDeath(false); this.fade = 1; this.fadeTarget = 0; this.fadeSpeed = 1.2; this.fadeColor.setRGB(0, 0, 0);
    this.loadCheckpoint(this.checkpoint); this.state = 'play'; this.audio.setMusic('explore');
    this.input.buttons = 0; this.input.clicked = 0; this.player.fireT = 0.5; this.player.bladeCd = 0.5;
  }
  begin() {
    this.input.buttons = 0; this.input.clicked = 0; this.input.pressed.clear(); this.player.fireT = 0.6; this.player.bladeCd = 0.6;   // the starting click must not fire
    this.state = 'play'; this.fadeTarget = 0; this.fadeSpeed = 0.5; this.audio.play('ui_start'); this.audio.setMusic('explore', 2.5);
    this.after(1.5, () => this.hud.hint('WASD  MOVE      MOUSE  AIM      LMB  FIRE', 6));
    this.after(8.5, () => this.hud.hint('RMB / SPACE  BLADE      SHIFT  DODGE      F  TORCH', 6));
    // own line so the hint stays clear of the vitals on narrow windows
    if (this.player.bladeSys.style === 2) this.after(15, () => this.hud.hint('TAP BLADE 3×  —  SLASH, BACKHAND, SPIN', 5));
    this.setObjective();
  }
  finish() {
    this.state = 'ending'; this.player.control = false; this.fadeColor.setRGB(1, 1, 1); this.fadeTarget = 1; this.fadeSpeed = 0.35;
    this.audio.setMusic('none', 2); this.audio.play('mus_ending', { gain: 1 });
    this.after(3.4, () => this.hud.showEnd(this.stats));
  }

  updateScript(dt) {
    const f = this.flags, P = this.player, z = this.zoneAt(P.x, P.z), L = this.lights;
    if (z >= 0 && z !== this.curZone) { this.curZone = z; this.setObjective(); }
    // checkpoints
    if (z === Z.ASSEMBLY && P.z < 135.4) this.setCheckpoint(1);
    if (z === Z.WAREHOUSE && P.z < 107.4) this.setCheckpoint(2);
    if (z === Z.FURNACE && P.z < 84) this.setCheckpoint(3);
    if (z === Z.ANTE && P.z < 55.4 && f.arenaCleared) this.setCheckpoint(4);
    // corridor scare: a figure under the far light that is gone after the flicker
    if (f.scare === 0 && z === Z.CORRIDOR && P.z < 147.5) { f.scare = 1; this.audio.play('stinger_discover', { gain: 0.9 }); }
    if (f.scare === 1 && P.z < 143.6) {
      f.scare = 2; L.setFixture('corridorScare', { dim: 0 }); this.audio.play('spark_zap', { x: 30, z: 138 }); L.flashFlicker = 0.02;
      this.after(0.25, () => { if (this.decoy) { this.scene.remove(this.decoy.root); this.decoy = null; } });
      this.after(0.7, () => { L.setFixture('corridorScare', { dim: 1 }); this.audio.play('stalker_whisper', { x: 30, z: 132, gain: 0.8 }); });
    }
    // assembly ambush -> shutter
    if (f.ambush === 3 && !f.asmCleared) { this.ambushT = (this.ambushT || 0) + dt; if (this.ambushT > 70) for (const e of this.enemies) if (e.ambush && !e.dead) e.die(0, 0); }
    if (f.arena === 3 && !f.arenaCleared) { this.arenaT = (this.arenaT || 0) + dt; if (this.arenaT > 150) for (const e of this.enemies) if (e.zone === Z.FURNACE && !e.dead) e.die(0, 0); }
    if (f.ambush === 3 && !f.asmCleared && !this.enemies.some((e) => e.ambush && !e.dead)) {
      f.asmCleared = true; this.audio.play('door_open', { x: 42, z: 111 }); this.applyFlags(); this.setObjective(); this.hud.toast('SHUTTER RELEASED');
    }
    // warehouse: one more comes up behind you
    if (z === Z.WAREHOUSE && !f.whStalker && P.x < 31) { f.whStalker = true; this.spawn(Stalker, 43.5, 104.5, { alert: true, silent: false }); }
    // furnace arena
    if (z === Z.FURNACE && f.arena === 0 && !f.arenaCleared && P.z < 80.5 && P.z > 60) this.startArena();
    if (f.arena === 1 && this.brute && (this.brute.dead || this.brute.hp < this.brute.maxHp * 0.5)) this.arenaWave2();
    if (f.arena === 3 && !f.arenaCleared && !this.enemies.some((e) => e.zone === Z.FURNACE && !e.dead)) {
      f.arenaCleared = true; this.applyFlags(); this.audio.play('door_open', { x: 30, z: 59 }); this.setObjective(); this.hud.toast('SHUTTER RELEASED');
    }
    // boss door + fight
    if (!f.door4 && z === Z.ANTE && P.z < 53) { f.door4 = true; this.applyFlags(); this.audio.play('door_open', { x: 30, z: 47 }); }
    if (f.boss === 0 && z === Z.BOSS && P.z < 41.5) this.startBoss();
    if (f.boss === 2 && this.boss && this.boss.state !== 'dying') this.hud.bossBar(Math.max(0, this.boss.hp / this.boss.maxHp), this.boss.name);
    if (f.bossDead && this.state === 'play' && z === Z.EXIT && P.z < 7.4) this.finish();
    // interactions
    let best = null;
    for (const it of this.interactables) { const p = it.prompt(); if (!p) continue; if (Math.hypot(P.x - it.x, P.z - it.z) < it.r) { best = it; this.hud.prompt(it.can() ? `E   ${p}` : p); } }
    if (!best) this.hud.prompt(null);
    else if (this.input.hit('KeyE')) { if (best.can()) best.act(); else best.deny?.(); }
  }

  updateAudioMood(dt) {
    const P = this.player, A = this.audio; this.musicT -= dt;
    A.setListener(P.x, P.z);
    // sustained loops
    let furn = 0; if (this.curZone === Z.FURNACE || this.curZone === Z.ANTE || this.curZone === Z.WAREHOUSE) { const d = Math.hypot(P.x - 30, P.z - 70); furn = Math.max(0, 1 - d / 34); }
    A.loop('amb_furnace', furn * 0.8);
    const B = this.boss; let breath = 0; if (B && !B.dead && (this.curZone === Z.ANTE || this.curZone === Z.BOSS)) breath = B.state === 'dormant' ? Math.max(0, 1 - Math.hypot(P.x - B.x, P.z - B.z) / 40) : 0.25;
    A.loop('amb_boss_breath', breath);
    A.loop('heartbeat', P.dead ? 0 : (P.hp < 35 ? 0.4 + (35 - P.hp) / 35 * 0.6 : 0), P.hp < 18 ? 1.25 : 1);
    if (this.musicT > 0 || this.state !== 'play') return;
    this.musicT = 0.3;
    if (this.flags.boss >= 1 && !this.flags.bossDead) return;      // boss music is scripted
    if (this.flags.bossDead) return;
    let near = 0, hot = 0;
    for (const e of this.enemies) { if (e.dead || e.untargetable && e.type !== 'boss') continue; const d = e.distToPlayer; if (e.alerted && d < 22 && e.type !== 'stalker') hot++; else if (d < 10 || (e.alerted && d < 25)) near++; }
    if (hot > 0) this.combatT = 3; else this.combatT -= 0.3;
    A.setMusic(this.combatT > 0 ? 'combat' : (near > 0 ? 'tension' : 'explore'), 1.5);
    // sparse world one-shots
    this.ambT -= 0.3;
    if (this.ambT <= 0) { this.ambT = 5 + Math.random() * 9; const a = Math.random() * 6.283, r = 10 + Math.random() * 14;
      A.play(Math.random() < 0.6 ? 'metal_clank' : 'drip', { x: P.x + Math.cos(a) * r, z: P.z + Math.sin(a) * r, gain: 0.8, ref: 14 }); }
  }

  updateCamera(dt) {
    const P = this.player, cam = this.gfx.camera, inp = this.input;
    let tx = P.x, tz = P.z - 1.2, dist = CAM.dist;
    if (this.state === 'title') { tx = 30 + Math.sin(this.titleT * 0.12) * 2; tz = 161.5; dist = 27; }
    else if (this.cutscene && this.boss) { const k = Math.min(1, this.cutscene.t / 1.2); tx = P.x + (this.boss.x - P.x) * 0.75 * k; tz = P.z + (this.boss.z + 3 - P.z) * 0.75 * k; dist = CAM.bossDist; }
    else {
      let lx = inp.aim.x - P.x, lz = inp.aim.z - P.z; const l = Math.hypot(lx, lz); const m = Math.min(l, 9) / 9 * CAM.lead; if (l > 0.01) { tx += lx / l * m; tz += lz / l * m; }
      if (this.flags.boss >= 1 && !this.flags.bossDead && this.boss) { dist = CAM.bossDist; tx += (this.boss.x - P.x) * 0.22; tz += (this.boss.z - P.z) * 0.22; }
    }
    this.focus.x = damp(this.focus.x, tx, CAM.lag, dt); this.focus.z = damp(this.focus.z, tz, CAM.lag, dt);
    this.camDist = damp(this.camDist, dist, 1.6, dt);
    const tr = this.trauma * this.trauma, t = this.time;
    const sx = (Math.sin(t * 47.1) + Math.sin(t * 31.7 + 1.3)) * 0.22 * tr, sz = (Math.sin(t * 41.3 + 2.1) + Math.sin(t * 27.9)) * 0.22 * tr;
    cam.position.set(this.focus.x + sx, this.camDist * Math.sin(CAM.pitch), this.focus.z + this.camDist * Math.cos(CAM.pitch) + sz);
    cam.lookAt(_v.set(this.focus.x + sx, 0.4, this.focus.z + sz));
    cam.rotation.z += Math.sin(t * 53) * 0.006 * tr;
  }

  update(rawDt) {
    let dt = Math.min(rawDt, 0.05);
    if (this.freeze > 0) { this.freeze -= rawDt; dt *= 0.06; }
    this.time += dt; this.titleT += rawDt;
    const P = this.player, inp = this.input, u = this.gfx.u;
    inp.updateAim();
    for (let i = this.timers.length - 1; i >= 0; i--) { const tm = this.timers[i]; tm.t -= dt; if (tm.t <= 0) { this.timers.splice(i, 1); tm.fn(); } }

    if (this.state === 'play' || this.state === 'dead' || this.state === 'ending') {
      if (this.state === 'play') this.stats.time += dt;
      if (this.cutscene) this.cutscene.t += dt;
      // stalkers nearby make the torch stutter
      let interf = 1; for (const e of this.enemies) if (e.type === 'stalker' && e.alerted && !e.dead && e.distToPlayer < 9) { const t = this.time; if (Math.sin(t * 2.3) + Math.sin(t * 5.9) * 0.7 + Math.sin(t * 11.3) * 0.3 > 1.05) interf = 0.02; }
      this.flashInterference = interf;
      this.flowT -= dt; if (this.flowT <= 0) { this.flowT = 0.2; this.grid.computeFlow(P.x, P.z); }
      P.update(dt);
      for (const e of this.enemies) e.update(dt);
      for (let i = this.enemies.length - 1; i >= 0; i--) if (this.enemies[i].removed) this.enemies.splice(i, 1);
      this.weapons.update(dt); this.gibs.update(dt); this.updatePickups(dt);
      if (this.state === 'play') { this.updateScript(dt); this.lab?.update(dt); }
      if (this.state === 'dead' && this.hud.deathShown && (inp.anyKey)) this.respawn();
      this.updateAudioMood(dt);
    } else { P.sync(dt); }

    // furnace embers + pit glow life
    for (const fx of this.lights.fixtures) if (fx.fire && fx.cur > 1 && Math.abs(fx.x - this.focus.x) < 24 && Math.abs(fx.z - this.focus.z) < 18 && Math.random() < dt * 5) this.particles.embers(fx.x, fx.y, fx.z, 1, 1.6);
    this.level.update(dt, this.time, this.flags.power);
    this.updateCamera(dt);
    this.lights.update(dt, this.focus.x, this.focus.z);
    this.particles.update(dt, this.time, _focus.set(this.focus.x, 0, this.focus.z));
    // post fx
    this.trauma = Math.max(0, this.trauma - dt * 1.9); this.dmgFx = Math.max(0, this.dmgFx - dt * 1.4);
    this.fade += Math.sign(this.fadeTarget - this.fade) * Math.min(Math.abs(this.fadeTarget - this.fade), rawDt * this.fadeSpeed);
    this.letterbox = damp(this.letterbox, this.cutscene ? 0.085 : 0, 4, dt);
    u.uDamage.value = this.dmgFx; u.uLowHealth.value = P.dead ? 0.6 : Math.max(0, 1 - P.hp / 35); u.uFade.value = this.fade; u.uFadeColor.value.copy(this.fadeColor);
    u.uLetterbox.value = this.letterbox; u.uPulse.value = Math.min(1, this.trauma);
    this.hud.update(P, this);
  }
}
