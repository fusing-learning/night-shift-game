import * as THREE from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { CELL } from '../config.js';
import { TILE, FLOOR } from './grid.js';
import { PROPS, PROP_COLLIDERS, DOORS } from './leveldata.js';

const WALL_H = 4.6, LOW_H = 0.5;

class QuadBuilder {
  constructor() { this.p = []; this.n = []; this.uv = []; this.idx = []; }
  // a,b,c,d counter-clockwise seen from the front; uvs in metres
  quad(a, b, c, d, n, ua, ub, uc, ud) {
    const i = this.p.length / 3;
    this.p.push(...a, ...b, ...c, ...d); for (let k = 0; k < 4; k++) this.n.push(...n);
    this.uv.push(...ua, ...ub, ...uc, ...ud); this.idx.push(i, i + 1, i + 2, i, i + 2, i + 3);
  }
  build() {
    if (!this.idx.length) return null;
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(this.p, 3));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(this.n, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(this.uv, 2));
    g.setIndex(this.idx); return g;
  }
}

function pitTexture(hot) {
  const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
  g.fillStyle = '#000'; g.fillRect(0, 0, 256, 256);
  for (let i = 0; i < 26; i++) {
    const y = Math.random() * 256, w = 3 + Math.random() * 12, a = 0.15 + Math.random() * 0.6;
    g.fillStyle = hot ? `rgba(255,${80 + Math.random() * 90 | 0},20,${a})` : `rgba(40,${150 + Math.random() * 80 | 0},255,${a * 0.5})`;
    if (Math.random() < 0.5) g.fillRect(0, y, 256, w); else g.fillRect(y, 0, w, 256);
  }
  for (let i = 0; i < 60; i++) { g.fillStyle = `rgba(0,0,0,${0.3 + Math.random() * 0.5})`; g.beginPath(); g.arc(Math.random() * 256, Math.random() * 256, 8 + Math.random() * 30, 0, 6.3); g.fill(); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.repeat.set(0.11, 0.11); return t;
}

export class Level {
  constructor(scene, grid, assets) {
    this.scene = scene; this.grid = grid; this.assets = assets;
    this.refs = {};          // id -> prop Object3D
    this.swaying = [];       // hanging things that swing
    this.belts = [];         // conveyor directions
    this.doors = {};
    this.root = new THREE.Group(); scene.add(this.root);
    this.buildShell();
    this.buildProps();
    this.buildDoors();
    grid.rebuildDynamic(Object.values(this.doors).map((d) => d.box));
  }

  add(geo, mat, cast = false) {
    if (!geo) return null;
    const m = new THREE.Mesh(geo, mat); m.receiveShadow = true; m.castShadow = cast; m.matrixAutoUpdate = false; this.root.add(m); return m;
  }

  buildShell() {
    const g = this.grid, M = this.assets.mats;
    const floors = [new QuadBuilder(), new QuadBuilder(), new QuadBuilder(), new QuadBuilder()];
    const pitHot = new QuadBuilder(), pitCold = new QuadBuilder();
    const wall = new QuadBuilder(), top = new QuadBuilder();
    const trim = [];
    const box = (x, y, z, sx, sy, sz) => { const b = new THREE.BoxGeometry(sx, sy, sz); b.translate(x, y, z); trim.push(b); };
    for (let cz = 0; cz < g.h; cz++) for (let cx = 0; cx < g.w; cx++) {
      const t = g.tile(cx, cz); if (t === TILE.VOID) continue;
      const x0 = cx * CELL, x1 = x0 + CELL, z0 = cz * CELL, z1 = z0 + CELL;
      if (t === TILE.FLOOR) {
        const ft = g.floor[cz * g.w + cx];
        floors[ft].quad([x0, 0, z1], [x1, 0, z1], [x1, 0, z0], [x0, 0, z0], [0, 1, 0], [x0, -z1], [x1, -z1], [x1, -z0], [x0, -z0]);
        if (ft === FLOOR.GRATE) {
          const pb = cz < 25 ? pitHot : pitHot; const y = -1.6;
          (cz < 25 ? pitHot : pitCold).quad([x0, y, z1], [x1, y, z1], [x1, y, z0], [x0, y, z0], [0, 1, 0], [x0, -z1], [x1, -z1], [x1, -z0], [x0, -z0]);
          void pb;
        }
        continue;
      }
      const low = g.isLowWall(cx, cz), h = low ? LOW_H : WALL_H;
      top.quad([x0, h, z1], [x1, h, z1], [x1, h, z0], [x0, h, z0], [0, 1, 0], [x0, -z1], [x1, -z1], [x1, -z0], [x0, -z0]);
      const exposed = (nx, nz) => { const tt = g.tile(nx, nz); return tt === TILE.FLOOR || (!low && g.isLowWall(nx, nz)); };
      // south face
      if (exposed(cx, cz + 1)) {
        wall.quad([x0, 0, z1], [x1, 0, z1], [x1, h, z1], [x0, h, z1], [0, 0, 1], [x0, 0], [x1, 0], [x1, h], [x0, h]);
        if (!low && g.isFloor(cx, cz + 1)) {
          box(x0 + 1, 0.45, z1 + 0.03, 2, 0.9, 0.06);                 // kick plate
          box(x0 + 1, WALL_H - 0.2, z1 + 0.07, 2, 0.4, 0.14);          // top beam
          if (cx % 2 === 0) box(x0, WALL_H / 2, z1 + 0.09, 0.28, WALL_H, 0.18); // pilaster
          box(x0 + 1, 2.35, z1 + 0.035, 2, 0.12, 0.07);                // mid rail
        }
      }
      if (exposed(cx + 1, cz)) {
        wall.quad([x1, 0, z1], [x1, 0, z0], [x1, h, z0], [x1, h, z1], [1, 0, 0], [-z1, 0], [-z0, 0], [-z0, h], [-z1, h]);
        if (!low && g.isFloor(cx + 1, cz)) { box(x1 + 0.03, 0.45, z0 + 1, 0.06, 0.9, 2); box(x1 + 0.07, WALL_H - 0.2, z0 + 1, 0.14, 0.4, 2); if (cz % 2 === 0) box(x1 + 0.09, WALL_H / 2, z0, 0.18, WALL_H, 0.28); }
      }
      if (exposed(cx - 1, cz)) {
        wall.quad([x0, 0, z0], [x0, 0, z1], [x0, h, z1], [x0, h, z0], [-1, 0, 0], [z0, 0], [z1, 0], [z1, h], [z0, h]);
        if (!low && g.isFloor(cx - 1, cz)) { box(x0 - 0.03, 0.45, z0 + 1, 0.06, 0.9, 2); box(x0 - 0.07, WALL_H - 0.2, z0 + 1, 0.14, 0.4, 2); if (cz % 2 === 0) box(x0 - 0.09, WALL_H / 2, z0, 0.18, WALL_H, 0.28); }
      }
    }
    this.add(floors[FLOOR.PLATE].build(), M.floor_plate);
    this.add(floors[FLOOR.TREAD].build(), M.floor_tread);
    this.add(floors[FLOOR.CONCRETE].build(), M.floor_concrete);
    const grate = this.add(floors[FLOOR.GRATE].build(), M.floor_grate, true);
    if (grate) grate.castShadow = false;
    this.pitHot = new THREE.MeshBasicMaterial({ map: pitTexture(true), color: 0x993311, fog: false });
    this.pitCold = new THREE.MeshBasicMaterial({ map: pitTexture(true), color: 0xaa3a10, fog: false });
    this.add(pitHot.build(), this.pitHot); this.add(pitCold.build(), this.pitCold);
    this.add(wall.build(), M.wall_metal, true);
    this.add(top.build(), M.wall_top, true);
    if (trim.length) {
      // box-project UVs in metres
      const merged = mergeGeometries(trim.map((b) => b.toNonIndexed()));
      const pos = merged.attributes.position, nor = merged.attributes.normal, uv = merged.attributes.uv;
      for (let i = 0; i < pos.count; i++) {
        const ax = Math.abs(nor.getX(i)), ay = Math.abs(nor.getY(i));
        if (ax > 0.5) uv.setXY(i, pos.getZ(i), pos.getY(i)); else if (ay > 0.5) uv.setXY(i, pos.getX(i), pos.getZ(i)); else uv.setXY(i, pos.getX(i), pos.getY(i));
      }
      this.add(merged, M.trim, true);
    }
  }

  buildProps() {
    const g = this.grid, A = this.assets;
    g.bakeTiles();
    for (const p of PROPS) {
      if (p.skip) continue;
      let o = A.makeProp(p.name);
      if (!o) {
        // placeholder so the layout is playable before the art lands
        const c = PROP_COLLIDERS[p.name]; if (!c) continue;
        o = new THREE.Mesh(new THREE.BoxGeometry(c[0] * 2, 1.2, c[1] * 2), A.mats.fallback); o.geometry.translate(0, 0.6, c[3] || 0);
        o.castShadow = o.receiveShadow = true;
      }
      o.position.set(p.x, p.y || 0, p.z); o.rotation.y = p.rot;
      o.updateMatrixWorld(true);
      this.root.add(o);
      if (p.id) this.refs[p.id] = o;
      if (p.sway) this.swaying.push({ o, amp: p.sway, seed: Math.random() * 10, baseRot: p.rot });
      if (p.belt) this.belts.push(p);
      const c = PROP_COLLIDERS[p.name];
      if (c) {
        const off = c[3] || 0;
        g.stampBox(p.x + Math.sin(p.rot) * off, p.z + Math.cos(p.rot) * off, c[0], c[1], p.rot, c[2]);
      }
    }
  }

  buildDoors() {
    const A = this.assets;
    for (const d of DOORS) {
      let mesh = A.makeProp('door_shutter');
      if (!mesh) { mesh = new THREE.Mesh(new THREE.BoxGeometry(4, 4, 0.15), A.mats.metal_plate); mesh.geometry.translate(0, 2, 0); mesh.castShadow = mesh.receiveShadow = true; }
      mesh.position.set(d.x, 0, d.z); this.root.add(mesh);
      const door = { ...d, mesh, open: d.state === 'open' ? 1 : 0, target: d.state === 'open' ? 1 : 0, box: { x: d.x, z: d.z, hw: 2, hd: 0.5, active: d.state !== 'open' } };
      mesh.position.y = door.open * 4.05;
      this.doors[d.id] = door;
    }
  }

  setDoor(id, open) {
    const d = this.doors[id]; if (!d) return false;
    const was = d.target; d.target = open ? 1 : 0; d.state = open ? 'open' : 'closed';
    return was !== d.target;
  }
  isDoorOpen(id) { return this.doors[id]?.target === 1; }

  update(dt, time, powered) {
    let dirty = false;
    for (const d of Object.values(this.doors)) {
      if (d.open !== d.target) {
        const sp = d.target ? 0.55 : 2.2;      // opens slowly, slams shut
        d.open = d.target ? Math.min(1, d.open + dt * sp) : Math.max(0, d.open - dt * sp);
        d.mesh.position.y = d.open * 4.05;
        const active = d.open < 0.55;
        if (active !== d.box.active) { d.box.active = active; dirty = true; }
      }
    }
    if (dirty) this.grid.rebuildDynamic(Object.values(this.doors).map((d) => d.box));
    for (const s of this.swaying) {
      s.o.rotation.z = Math.sin(time * 0.7 + s.seed) * 0.035 * s.amp + Math.sin(time * 1.9 + s.seed * 3) * 0.012 * s.amp;
      s.o.rotation.x = Math.cos(time * 0.55 + s.seed * 2) * 0.03 * s.amp;
    }
    const belt = this.assets.mats.belt;
    if (powered && belt.map) { const o = (time * 0.35) % 1; belt.map.offset.x = o; if (belt.normalMap) belt.normalMap.offset.x = o; if (belt.roughnessMap) belt.roughnessMap.offset.x = o; }
    if (this.assets.moltenTex) { this.assets.moltenTex.offset.x = time * 0.02; this.assets.moltenTex.offset.y = Math.sin(time * 0.3) * 0.05; }
    const fan = this.refs.fan1?.getObjectByName('blades'); if (fan) fan.rotation.z += dt * (powered ? 9 : 0.6);
  }
}
