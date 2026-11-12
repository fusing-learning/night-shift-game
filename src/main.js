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
let game = null, paused = false, started = false;

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
  window.tp = async (x, z, mx = 0, my = 0.4, secs = 1.5) => { input.mouse.set(mx, my); game.player.place(x, z, Math.PI); game.focus.set(x, 0, z - 2); window.step(secs); await window.raf(4); return `${game.player.x.toFixed(1)},${game.player.z.toFixed(1)} zone ${game.curZone} enemies ${game.enemies.length}`; };
  // warm up shaders so the first seconds of play don't hitch
  gfx.renderer.compile(gfx.scene, gfx.camera);
  hud.ready();
  if (DEBUG.has('autostart')) start();
  requestAnimationFrame(loop);
}

function start() {
  if (started || !game) return; started = true;
  audio.init(); audio.resume(); if (DEBUG.has('mute')) audio.toggleMute();
  hud.hideTitle(); game.begin();
}

addEventListener('mousedown', () => { if (!started) start(); else if (game?.state === 'ending' && !document.getElementById('end').classList.contains('hidden')) location.reload(); });
addEventListener('keydown', (e) => {
  if (!started) { if (e.code === 'Enter' || e.code === 'Space') start(); return; }
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
