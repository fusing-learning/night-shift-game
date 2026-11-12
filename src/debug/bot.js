// Autoplayer for automated playtests (?bot). Plays the whole level with simple heuristics so the
// full flow, scripting and balance can be exercised without a human at the controls.
export class Bot {
  constructor(G) {
    this.G = G; this.dist = new Uint16Array(G.grid.dist.length); this.fieldT = 0; this.target = null; this.out = { x: 0, z: 0 };
    this.strafe = 1; this.strafeT = 0; this.log = []; this.lastZone = -1; this.stuckT = 0; this.lx = 0; this.lz = 0; this.skill = 1;
  }
  goal() {
    const f = this.G.flags, P = this.G.player;
    if (!f.key) return { x: 12, z: 157.6 };
    if (!f.door1) return { x: 33.3, z: 154.0, use: true };
    if (!f.power) return { x: 58.6, z: 125.8, use: true };
    if (!f.asmCleared) return { x: 34, z: 123, hold: true };
    if (!f.arenaCleared) { if (f.arena === 0) return { x: 30, z: 74 }; return { x: 30, z: 72, hold: true }; }
    if (!f.bossDead) { if (!f.door4) return { x: 30, z: 51.5 }; if (f.boss === 0) return { x: 30, z: 38 }; return { x: 30, z: 30, hold: true }; }
    void P; return { x: 30, z: 4.5 };
  }
  field(tx, tz) { const g = this.G.grid, keep = g.dist; g.dist = this.dist; g.computeFlow(tx, tz, 400); g.dist = keep; }
  flow(x, z) { const g = this.G.grid, keep = g.dist; g.dist = this.dist; const d = g.flow(x, z, this.out); g.dist = keep; return d; }
  update(dt) {
    const G = this.G, P = G.player, inp = G.input, K = inp.keys;
    for (const k of ['KeyW', 'KeyA', 'KeyS', 'KeyD']) K.delete(k);
    inp.buttons = 0;
    if (G.state === 'dead') { if (G.hud.deathShown) inp.anyKey = true; return; }
    if (G.state !== 'play' || P.dead) return;
    if (G.curZone !== this.lastZone) { this.lastZone = G.curZone; this.log.push(`t=${G.stats.time.toFixed(0)} zone ${G.curZone} hp ${P.hp.toFixed(0)} deaths ${G.stats.deaths}`); }
    const goal = this.goal();
    this.fieldT -= dt; if (this.fieldT <= 0 || !this.target || this.target.x !== goal.x || this.target.z !== goal.z) { this.fieldT = 0.5; this.target = goal; this.field(goal.x, goal.z); }
    // threats
    let near = null, nd = 1e9;
    for (const e of G.enemies) { if (e.dead || e.untargetable || !e.alerted) continue; const d = Math.hypot(e.x - P.x, e.z - P.z) - e.radius; if (d < nd && (d < 6 || G.grid.los(P.x, P.z, e.x, e.z))) { nd = d; near = e; } }
    let mx = 0, mz = 0;
    const dGoal = Math.hypot(goal.x - P.x, goal.z - P.z);
    if (!(goal.hold && dGoal < 6) && dGoal > 0.7) { const fd = this.flow(P.x, P.z); mx = this.out.x; mz = this.out.z; void fd; }
    let aimX = P.x + mx * 5, aimZ = P.z + mz * 5;
    if (near && nd < 20) {
      aimX = near.x + near.vx * 0.12; aimZ = near.z + near.vz * 0.12;
      const ex = (near.x - P.x) / (nd + near.radius || 1), ez = (near.z - P.z) / (nd + near.radius || 1);
      const want = near.type === 'boss' ? 8.5 : (near.type === 'brute' ? 6.5 : (near.type === 'spitter' ? 3 : 3.2));
      this.strafeT -= dt; if (this.strafeT <= 0) { this.strafeT = 1 + Math.random() * 2; this.strafe *= -1; }
      if (nd < want) { mx = -ex + -ez * this.strafe * 0.8; mz = -ez + ex * this.strafe * 0.8; }
      else if (goal.hold || nd < want + 4) { mx = -ez * this.strafe + ex * 0.3; mz = ex * this.strafe + ez * 0.3; }
      // stay out of walls: if the retreat direction is blocked, slide along the flow field instead
      if (G.grid.isSolid(P.x + mx * 1.2, P.z + mz * 1.2)) { this.strafe *= -1; this.flow(P.x, P.z); mx = this.out.x * 0.6 - ez * this.strafe; mz = this.out.z * 0.6 + ex * this.strafe; }
      if (nd < 2.0 && P.bladeCd <= 0) inp.pressed.add('Space');
      else if (P.overheat <= 0 && P.energy >= 5 && P.heat < 0.86 && G.grid.los(P.x, P.z, near.x, near.z)) inp.buttons = 1;
      else if (P.energy < 5 && nd < 4.5 && near.type !== 'boss' && near.type !== 'brute') { mx = ex; mz = ez; }    // out of juice: go carve
      if (near.type === 'stalker' && !P.flashOn) inp.pressed.add('KeyF');
    }
    // dodge out of telegraphed areas
    for (const m of G.weapons.marks) if (Math.hypot(P.x - m.x, P.z - m.z) < m.radius + 0.4 && m.t > m.dur * 0.35 && P.dodgeCd <= 0) { mx = P.x - m.x; mz = P.z - m.z; inp.pressed.add('ShiftLeft'); }
    for (const s of G.weapons.shots) {
      if (s.kind === 'lob' && s.t > 0.45 && Math.hypot(P.x - s.tx, P.z - s.tz) < s.radius + 0.5) { mx += (P.x - s.tx) * 2; mz += (P.z - s.tz) * 2; if (s.t > 0.75 && P.dodgeCd <= 0) inp.pressed.add('ShiftLeft'); }
      if (s.kind === 'fire') { const d = Math.hypot(P.x - s.x, P.z - s.z); if (d < 2.2) { mx += -s.dz * 2; mz += s.dx * 2; if (d < 1.3 && P.dodgeCd <= 0) inp.pressed.add('ShiftLeft'); } }
    }
    for (const w of G.weapons.waves) { const d = Math.hypot(P.x - w.x, P.z - w.z); if (d - w.r < 1.6 && d - w.r > -0.5 && P.dodgeCd <= 0 && w.damage > 0) { mx = w.x - P.x; mz = w.z - P.z; inp.pressed.add('ShiftLeft'); } }
    for (const p of G.weapons.puddles) { const d = Math.hypot(P.x - p.x, P.z - p.z); if (d < p.radius + 0.6) { mx += (P.x - p.x) / (d || 1) * 2; mz += (P.z - p.z) / (d || 1) * 2; } }
    // grab pickups when hurt / low
    if (P.hp < 60 || P.energy < 40) for (const p of G.pickups) { if (p.taken) continue; if ((p.kind === 'health' && P.hp < 70) || (p.kind === 'energy' && P.energy < 50)) { const d = Math.hypot(p.x - P.x, p.z - P.z); if (d < 9 && G.grid.los(P.x, P.z, p.x, p.z) && (!near || nd > 3)) { mx = (p.x - P.x) / d; mz = (p.z - P.z) / d; } } }
    if (goal.use && dGoal < 1.5) inp.pressed.add('KeyE');
    if (mz < -0.3) K.add('KeyW'); if (mz > 0.3) K.add('KeyS'); if (mx < -0.3) K.add('KeyA'); if (mx > 0.3) K.add('KeyD');
    inp.aimOverride = { x: aimX, z: aimZ };
    // unstick
    this.stuckT += dt; if (this.stuckT > 2) { if (Math.hypot(P.x - this.lx, P.z - this.lz) < 0.3 && dGoal > 2 && !near) { inp.pressed.add('ShiftLeft'); this.strafe *= -1; } this.lx = P.x; this.lz = P.z; this.stuckT = 0; }
  }
}
