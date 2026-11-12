import { CELL, SUB } from '../config.js';

export const TILE = { VOID: 0, FLOOR: 1, WALL: 2 };
export const FLOOR = { PLATE: 0, TREAD: 1, GRATE: 2, CONCRETE: 3 };
export const MOVE = 1, SHOT = 2;   // solid mask bits

// Tile map + 0.5 m collision grid + flow-field navigation.
export class Grid {
  constructor(w, h) {
    this.w = w; this.h = h;
    this.tiles = new Uint8Array(w * h);
    this.floor = new Uint8Array(w * h);
    this.zone = new Int8Array(w * h).fill(-1);
    this.sw = w * SUB; this.sh = h * SUB; this.s = CELL / SUB;
    const n = this.sw * this.sh;
    this.solid = new Uint8Array(n);
    this.staticSolid = new Uint8Array(n);
    this.navBlocked = new Uint8Array(n);
    this.dist = new Uint16Array(n).fill(65535);
    this.queue = new Int32Array(n);
    this.hitNx = 0; this.hitNz = 0;
  }
  tile(cx, cz) { return (cx < 0 || cz < 0 || cx >= this.w || cz >= this.h) ? TILE.VOID : this.tiles[cz * this.w + cx]; }
  isFloor(cx, cz) { return this.tile(cx, cz) === TILE.FLOOR; }
  carve(x0, z0, x1, z1, floorType = FLOOR.PLATE, zone = -1) {
    for (let z = z0; z <= z1; z++) for (let x = x0; x <= x1; x++) {
      const i = z * this.w + x;
      this.tiles[i] = TILE.FLOOR; this.floor[i] = floorType; if (zone >= 0) this.zone[i] = zone;
    }
  }
  setFloorType(x0, z0, x1, z1, floorType) {
    for (let z = z0; z <= z1; z++) for (let x = x0; x <= x1; x++) {
      const i = z * this.w + x; if (this.tiles[i] === TILE.FLOOR) this.floor[i] = floorType;
    }
  }
  fillVoid(x0, z0, x1, z1) {
    for (let z = z0; z <= z1; z++) for (let x = x0; x <= x1; x++) this.tiles[z * this.w + x] = TILE.VOID;
  }
  buildWalls() {
    const { w, h, tiles } = this;
    for (let z = 0; z < h; z++) for (let x = 0; x < w; x++) {
      if (tiles[z * w + x] !== TILE.VOID) continue;
      let near = false;
      for (let dz = -1; dz <= 1 && !near; dz++) for (let dx = -1; dx <= 1; dx++) {
        if (this.tile(x + dx, z + dz) === TILE.FLOOR) { near = true; break; }
      }
      if (near) tiles[z * w + x] = TILE.WALL;
    }
  }
  // A wall tile is rendered "cut away" (low) if there is floor directly north of it,
  // so it never hides the room behind it from the camera in the south.
  isLowWall(cx, cz) { return this.tile(cx, cz) === TILE.WALL && this.isFloor(cx, cz - 1); }
  isTallWall(cx, cz) { return this.tile(cx, cz) === TILE.WALL && !this.isFloor(cx, cz - 1); }

  bakeTiles() {
    const { sw, sh } = this;
    for (let sz = 0; sz < sh; sz++) for (let sx = 0; sx < sw; sx++) {
      const t = this.tiles[((sz / SUB) | 0) * this.w + ((sx / SUB) | 0)];
      this.staticSolid[sz * sw + sx] = t === TILE.FLOOR ? 0 : (MOVE | SHOT);
    }
    this.solid.set(this.staticSolid);
  }
  // Rasterise an oriented box footprint (world metres) into a solid layer.
  stampBox(cx, cz, hw, hd, rot, mask, layer = this.staticSolid) {
    const c = Math.cos(rot), s = Math.sin(rot), sub = this.s;
    const ext = Math.abs(hw * c) + Math.abs(hd * s), exd = Math.abs(hw * s) + Math.abs(hd * c);
    const x0 = Math.max(0, Math.floor((cx - ext) / sub)), x1 = Math.min(this.sw - 1, Math.floor((cx + ext) / sub));
    const z0 = Math.max(0, Math.floor((cz - exd) / sub)), z1 = Math.min(this.sh - 1, Math.floor((cz + exd) / sub));
    const pad = sub * 0.35;
    for (let z = z0; z <= z1; z++) for (let x = x0; x <= x1; x++) {
      const px = (x + 0.5) * sub - cx, pz = (z + 0.5) * sub - cz;
      // inverse-rotate by rot about Y (three.js convention: x' = x c + z s ; z' = -x s + z c)
      const lx = px * c - pz * s, lz = px * s + pz * c;
      if (Math.abs(lx) <= hw + pad && Math.abs(lz) <= hd + pad) layer[z * this.sw + x] |= mask;
    }
  }
  stampCircle(cx, cz, r, mask, layer = this.staticSolid) { this.stampBox(cx, cz, r * 0.9, r * 0.9, 0, mask, layer); }

  // dynamic boxes (doors): rebuilt from staticSolid + active dynamic boxes
  rebuildDynamic(boxes) {
    this.solid.set(this.staticSolid);
    for (const b of boxes) if (b.active) this.stampBox(b.x, b.z, b.hw, b.hd, 0, MOVE | SHOT, this.solid);
    this.bakeNav();
  }
  bakeNav() {
    const { sw, sh, solid, navBlocked } = this;
    for (let z = 0; z < sh; z++) for (let x = 0; x < sw; x++) {
      let b = 0;
      for (let dz = -1; dz <= 1 && !b; dz++) for (let dx = -1; dx <= 1; dx++) {
        const xx = x + dx, zz = z + dz;
        if (xx < 0 || zz < 0 || xx >= sw || zz >= sh || (solid[zz * sw + xx] & MOVE)) { b = 1; break; }
      }
      navBlocked[z * sw + x] = b;
    }
  }
  isSolid(x, z, mask = MOVE) {
    const sx = Math.floor(x / this.s), sz = Math.floor(z / this.s);
    if (sx < 0 || sz < 0 || sx >= this.sw || sz >= this.sh) return true;
    return (this.solid[sz * this.sw + sx] & mask) !== 0;
  }
  // Push a circle out of solid cells. Mutates p {x,z}. Returns true if it touched something.
  collide(p, r, mask = MOVE) {
    const s = this.s, sw = this.sw, sh = this.sh; let hit = false;
    this.hitNx = 0; this.hitNz = 0;
    for (let iter = 0; iter < 3; iter++) {
      let any = false;
      const x0 = Math.floor((p.x - r) / s), x1 = Math.floor((p.x + r) / s);
      const z0 = Math.floor((p.z - r) / s), z1 = Math.floor((p.z + r) / s);
      for (let z = z0; z <= z1; z++) for (let x = x0; x <= x1; x++) {
        const sol = (x < 0 || z < 0 || x >= sw || z >= sh) ? 3 : this.solid[z * sw + x];
        if (!(sol & mask)) continue;
        const nx = Math.max(x * s, Math.min(p.x, x * s + s)), nz = Math.max(z * s, Math.min(p.z, z * s + s));
        let dx = p.x - nx, dz = p.z - nz; const d2 = dx * dx + dz * dz;
        if (d2 >= r * r) continue;
        if (d2 > 1e-9) {
          const d = Math.sqrt(d2), push = r - d; dx /= d; dz /= d;
          p.x += dx * push; p.z += dz * push; this.hitNx += dx; this.hitNz += dz;
        } else {
          // centre inside the cell: push out through the nearest face
          const l = p.x - x * s, rr = x * s + s - p.x, t = p.z - z * s, b = z * s + s - p.z;
          const m = Math.min(l, rr, t, b);
          if (m === l) { p.x = x * s - r; this.hitNx -= 1; } else if (m === rr) { p.x = x * s + s + r; this.hitNx += 1; }
          else if (m === t) { p.z = z * s - r; this.hitNz -= 1; } else { p.z = z * s + s + r; this.hitNz += 1; }
        }
        any = true; hit = true;
      }
      if (!any) break;
    }
    const l = Math.hypot(this.hitNx, this.hitNz); if (l > 0) { this.hitNx /= l; this.hitNz /= l; }
    return hit;
  }
  // Move with sub-stepping. Returns true on collision.
  move(p, r, dx, dz, mask = MOVE) {
    const len = Math.hypot(dx, dz); if (len < 1e-6) return this.collide(p, r, mask);
    const steps = Math.max(1, Math.ceil(len / (r * 0.6))); let hit = false, nx = 0, nz = 0;
    for (let i = 0; i < steps; i++) {
      p.x += dx / steps; p.z += dz / steps;
      if (this.collide(p, r, mask)) { hit = true; nx = this.hitNx; nz = this.hitNz; }
    }
    this.hitNx = nx; this.hitNz = nz;
    return hit;
  }
  // DDA ray through the sub grid. Returns fraction 0..1 of the segment travelled before a hit (1 = clear).
  raycast(x0, z0, x1, z1, mask = SHOT) {
    const s = this.s, sw = this.sw, sh = this.sh;
    let cx = Math.floor(x0 / s), cz = Math.floor(z0 / s);
    const dx = x1 - x0, dz = z1 - z0;
    const stepX = dx > 0 ? 1 : -1, stepZ = dz > 0 ? 1 : -1;
    const tdx = dx !== 0 ? Math.abs(s / dx) : Infinity, tdz = dz !== 0 ? Math.abs(s / dz) : Infinity;
    let tmx = dx !== 0 ? ((dx > 0 ? (cx + 1) * s - x0 : x0 - cx * s) / Math.abs(dx)) : Infinity;
    let tmz = dz !== 0 ? ((dz > 0 ? (cz + 1) * s - z0 : z0 - cz * s) / Math.abs(dz)) : Infinity;
    let t = 0;
    for (let i = 0; i < 400; i++) {
      if (cx < 0 || cz < 0 || cx >= sw || cz >= sh) return t;
      if (this.solid[cz * sw + cx] & mask) return t;
      if (tmx < tmz) { t = tmx; if (t >= 1) return 1; tmx += tdx; cx += stepX; this.hitNx = -stepX; this.hitNz = 0; }
      else { t = tmz; if (t >= 1) return 1; tmz += tdz; cz += stepZ; this.hitNx = 0; this.hitNz = -stepZ; }
    }
    return 1;
  }
  los(x0, z0, x1, z1) { return this.raycast(x0, z0, x1, z1, SHOT) >= 1; }

  computeFlow(px, pz, maxDist = 160) {
    const { sw, sh, dist, queue, navBlocked, solid } = this;
    dist.fill(65535);
    let sx = Math.floor(px / this.s), sz = Math.floor(pz / this.s);
    if (sx < 0 || sz < 0 || sx >= sw || sz >= sh) return;
    let head = 0, tail = 0;
    queue[tail++] = sz * sw + sx; dist[sz * sw + sx] = 0;
    while (head < tail) {
      const i = queue[head++], d = dist[i]; if (d >= maxDist) continue;
      const x = i % sw, z = (i / sw) | 0;
      // 4-neighbours
      if (x > 0) { const j = i - 1; if (dist[j] === 65535 && !(navBlocked[j] && d > 2) && !(solid[j] & MOVE)) { dist[j] = d + 1; queue[tail++] = j; } }
      if (x < sw - 1) { const j = i + 1; if (dist[j] === 65535 && !(navBlocked[j] && d > 2) && !(solid[j] & MOVE)) { dist[j] = d + 1; queue[tail++] = j; } }
      if (z > 0) { const j = i - sw; if (dist[j] === 65535 && !(navBlocked[j] && d > 2) && !(solid[j] & MOVE)) { dist[j] = d + 1; queue[tail++] = j; } }
      if (z < sh - 1) { const j = i + sw; if (dist[j] === 65535 && !(navBlocked[j] && d > 2) && !(solid[j] & MOVE)) { dist[j] = d + 1; queue[tail++] = j; } }
    }
  }
  // Direction of steepest descent toward the flow target. Returns path distance in metres (Infinity if unreachable).
  flow(x, z, out) {
    const { sw, sh, dist } = this;
    const sx = Math.floor(x / this.s), sz = Math.floor(z / this.s);
    let best = 65535, bx = 0, bz = 0;
    for (let dz = -1; dz <= 1; dz++) for (let dx = -1; dx <= 1; dx++) {
      const xx = sx + dx, zz = sz + dz;
      if (xx < 0 || zz < 0 || xx >= sw || zz >= sh) continue;
      const d = dist[zz * sw + xx];
      if (d === 65535) continue;
      if (dx !== 0 && dz !== 0 && (dist[sz * sw + xx] === 65535 || dist[zz * sw + sx] === 65535)) continue;
      const cost = d + (dx !== 0 && dz !== 0 ? 0.42 : 0);
      if (cost < best) { best = cost; bx = dx; bz = dz; }
    }
    if (best === 65535) {
      // hugging a wall (inside the nav margin): look a little further out for the nearest routable cell
      for (let r = 2; r <= 4 && best === 65535; r++) for (let dz = -r; dz <= r; dz++) for (let dx = -r; dx <= r; dx++) {
        if (Math.max(Math.abs(dx), Math.abs(dz)) !== r) continue;
        const xx = sx + dx, zz = sz + dz; if (xx < 0 || zz < 0 || xx >= sw || zz >= sh) continue;
        const d = dist[zz * sw + xx]; if (d === 65535) continue;
        if (this.raycast(x, z, (xx + 0.5) * this.s, (zz + 0.5) * this.s, MOVE) < 1) continue;
        if (d + r < best) { best = d + r; bx = dx; bz = dz; }
      }
      if (best === 65535) { out.x = 0; out.z = 0; return Infinity; }
    }
    // aim at the centre of the chosen cell for smoothness
    const tx = (sx + bx + 0.5) * this.s - x, tz = (sz + bz + 0.5) * this.s - z;
    const l = Math.hypot(tx, tz) || 1; out.x = tx / l; out.z = tz / l;
    return best * this.s;
  }
  pathDist(x, z) {
    const sx = Math.floor(x / this.s), sz = Math.floor(z / this.s);
    if (sx < 0 || sz < 0 || sx >= this.sw || sz >= this.sh) return Infinity;
    const d = this.dist[sz * this.sw + sx]; return d === 65535 ? Infinity : d * this.s;
  }
}
