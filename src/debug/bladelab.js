// Blade test room, enabled with ?bladelab in the URL.
// Drops the player in the furnace hall (god mode) with passive targets that come back after they're cleared.
//   B / 0-3   switch blade style          R   next target layout
import { Crawler, Spitter, Stalker, Brute } from '../game/enemies/types.js';
import { CHECKPOINTS } from '../world/leveldata.js';
import { STYLES } from '../game/blade.js';

const HOME = { x: 32, z: 74 };
// [type, angle from facing (rad), distance (m)]
const LAYOUTS = [
  { name: 'PACK', list: [[Crawler, -0.75, 1.9], [Crawler, -0.38, 1.9], [Crawler, 0, 1.9], [Crawler, 0.38, 1.9], [Crawler, 0.75, 1.9], [Crawler, -0.2, 2.8], [Crawler, 0.2, 2.8]] },
  { name: 'SURROUNDED', list: Array.from({ length: 8 }, (_, i) => [Crawler, i / 8 * Math.PI * 2, 1.9]) },
  { name: 'MIXED', list: [[Brute, 0, 2.6], [Crawler, -1.0, 1.7], [Crawler, 1.0, 1.7], [Stalker, -0.5, 3.4], [Spitter, 0.6, 3.6]] },
  { name: 'TRIO', list: [[Crawler, -0.85, 1.8], [Crawler, 0, 2.1], [Crawler, 0.85, 1.8]] },
];

export function initLab(G) {
  const P = G.player, B = P.bladeSys;
  G.godMode = true;
  G.loadCheckpoint(CHECKPOINTS[4], true);
  for (const e of G.enemies) e.remove(); G.enemies.length = 0; G.boss = null;
  P.place(HOME.x, HOME.z, Math.PI); G.focus.set(HOME.x, 0, HOME.z - 2);

  const el = document.createElement('div');
  el.style.cssText = 'position:fixed;right:24px;top:28px;z-index:20;pointer-events:none;font:11px/1.7 ui-monospace,Menlo,monospace;letter-spacing:.12em;'
    + 'color:#bfe9f7;background:rgba(2,10,16,.62);padding:10px 14px;border:1px solid rgba(110,210,255,.22);max-width:360px;text-transform:uppercase';
  document.body.appendChild(el);

  const lab = { layout: 0, wait: 0, targets: [], shown: '' };
  const spawn = () => {
    for (const e of G.enemies) if (e.lab) e.remove();
    lab.targets = []; lab.wait = 0;
    const f = P.facing;
    for (const [Type, a, d] of LAYOUTS[lab.layout].list) {
      const [x, z] = G.freeSpot(P.x + Math.sin(f + a) * d, P.z + Math.cos(f + a) * d);
      const e = G.spawn(Type, x, z, { wakeRange: 0, facing: Math.atan2(P.x - x, P.z - z) });
      G.particles.glow(x, 0.4, z, 1.2, [0.2, 0.5, 0.7], 0.25);
      e.lab = true; e.dropChance = 0;
      e.think = function (dt) { this.brake(dt, 6); if (this.alerted) this.facePlayer(dt, 3); };   // stands still, never attacks
      lab.targets.push(e);
    }
  };
  spawn();
  lab.spawn = (layout = lab.layout) => { lab.layout = layout; spawn(); };   // used by automated captures

  lab.update = (dt) => {
    const inp = G.input;
    for (let i = 0; i < STYLES.length; i++) if (inp.hit('Digit' + i) && B.style !== i) { B.setStyle(i); P.bladeT = 0; P.bladeGlow = 0; }
    if (inp.hit('KeyR')) { lab.layout = (lab.layout + 1) % LAYOUTS.length; spawn(); }
    if (lab.targets.every((e) => e.dead || e.removed)) { lab.wait += dt; if (lab.wait > 1.1) spawn(); }
    const st = STYLES[B.style], txt = `${B.style}${st.name}${lab.layout}`;
    if (txt !== lab.shown) {
      lab.shown = txt;
      el.innerHTML = `<div style="color:#fff;letter-spacing:.3em">BLADE ${B.style} · ${st.name}</div><div style="opacity:.75;margin:4px 0 8px;text-transform:none;letter-spacing:.02em">${st.desc}</div>`
        + `<div style="opacity:.6">B / 0-3 &nbsp;style &nbsp;·&nbsp; R &nbsp;targets: ${LAYOUTS[lab.layout].name}</div>`;
    }
  };
  return lab;
}
