import * as THREE from 'three';
import { DEBUG } from './config.js';
import { Gfx } from './gfx/renderer.js';
import { Assets } from './core/assets.js';
import { AudioEngine } from './core/audio.js';
import { Input } from './core/input.js';
import { Hud } from './ui/hud.js';
import { Game } from './game/game.js';
import { Bot } from './debug/bot.js';

const canvas = document.getElementById('game');
const gfx = new Gfx(canvas);
const hud = new Hud();
const audio = new AudioEngine();
const assets = new Assets(gfx.renderer);
const input = new Input(canvas, gfx.camera);
let game = null, paused = false, started = false, entered = false;

async function boot() {
  let pa = 0, pb = 0; const show = () => hud.setLoading(pa * 0.6 + pb * 0.4);
  assets.onProgress = (p) => { pa = p; show(); };
  await Promise.all([assets.loadAll(), audio.load((p) => { pb = p; show(); })]);
  hud.setLoading(1, 'PREPARING');
  game = new Game({ gfx, assets, audio, input, hud });
  window.game = game;                                   // debugging / automated playtests
  if (DEBUG.has('bot')) game.bot = new Bot(game);
  // deterministic stepping for automated playtests (the pane may be throttled when hidden)
  window.step = (seconds, dt = 1 / 60) => { const n = Math.round(seconds / dt); for (let i = 0; i < n; i++) { if (game.bot) game.bot.update(dt); game.update(dt); input.endFrame(); } gfx.render(game.time); return game.time; };
  window.raf = (n = 3) => new Promise((r) => { let i = 0; const f = () => { if (++i >= n) r(); else requestAnimationFrame(f); }; requestAnimationFrame(f); setTimeout(r, 250); });
  // copy the GL frame into a 2D overlay so screenshots are reliable even when the pane is not compositing
  window.snap = () => { let c = document.getElementById('dbgsnap'); if (!c) { c = document.createElement('canvas'); c.id = 'dbgsnap'; c.style.cssText = 'position:fixed;inset:0;width:100vw;height:100vh;z-index:5;pointer-events:none'; document.body.appendChild(c); }
    gfx.render(game.time); c.width = canvas.width; c.height = canvas.height; c.getContext('2d').drawImage(canvas, 0, 0); };
  // save the current frame to disk through the dev server (see vite.config.js)
  window.shot = async (name, w = 1280) => { gfx.render(game.time); const c = document.createElement('canvas'); c.width = w; c.height = Math.round(w * canvas.height / canvas.width); c.getContext('2d').drawImage(canvas, 0, 0, c.width, c.height);
    const blob = await new Promise((r) => c.toBlob(r, 'image/jpeg', 0.88)); const res = await fetch('/__shot?name=' + name, { method: 'POST', body: blob }); return res.text(); };
  window.tp = async (x, z, mx = 0, my = 0.4, secs = 1.5) => { input.mouse.set(mx, my); game.player.place(x, z, Math.PI); game.focus.set(x, 0, z - 2); window.step(secs); window.snap(); await window.raf(2); return `${game.player.x.toFixed(1)},${game.player.z.toFixed(1)} zone ${game.curZone} enemies ${game.enemies.length}`; };
  // warm up shaders so the first seconds of play don't hitch
  game.weapons.prewarm(); game.player.blade.visible = game.player.arc.visible = true;
  gfx.renderer.compile(gfx.scene, gfx.camera);
  game.weapons.clear(); game.player.blade.visible = game.player.arc.visible = false;
  hud.ready();
  if (DEBUG.has('autostart')) start();
  requestAnimationFrame(loop);
}

// First click only wakes the audio (browsers require a gesture) and brings in the title theme; the second starts the run.
function enter() {
  if (entered || !game) return; entered = true;
  audio.init(); audio.resume(); if (DEBUG.has('mute')) audio.toggleMute();
  audio.setMusic('title', 1.5); document.getElementById('start').textContent = 'CLICK TO BEGIN';
}
function start() {
  if (started || !game) return; if (!entered) enter(); started = true;
  hud.hideTitle(); game.begin();
}

addEventListener('mousedown', () => { if (!entered) enter(); else if (!started) start(); else if (game?.state === 'ending' && !document.getElementById('end').classList.contains('hidden')) location.reload(); });
addEventListener('keydown', (e) => {
  if (!started) { if (e.code === 'Enter' || e.code === 'Space') { if (!entered) enter(); else start(); } return; }
  if (e.code === 'Escape' && game.state === 'play') { paused = !paused; hud.showPause(paused); if (audio.ctx) paused ? audio.ctx.suspend() : audio.ctx.resume(); }
  if (e.code === 'KeyM') audio.toggleMute();
});
addEventListener('blur', () => { if (started && game?.state === 'play' && !DEBUG.has('nopause')) { paused = true; hud.showPause(true); audio.ctx?.suspend(); } });

const clock = new THREE.Clock();
let fpsT = 0, fpsN = 0, slow = 0;
function loop() {
  requestAnimationFrame(loop);
  const dt = Math.min(clock.getDelta(), 0.1);
  if (!paused) {
    if (game.bot) game.bot.update(dt);
    game.update(dt * (game.timeScale || 1));
    input.endFrame();
  }
  gfx.render(game.time);
  // adaptive resolution: if the machine can't hold ~50 fps, drop internal resolution a notch
  fpsT += dt; fpsN++;
  if (fpsT >= 2) { const fps = fpsN / fpsT; window.__fps = fps; fpsT = 0; fpsN = 0; if (fps < 48 && started) { if (++slow >= 2 && gfx.quality > 0.6) { gfx.setQuality(gfx.quality - 0.15); game.onResize(); slow = 0; } } else slow = 0; }
}
boot();
