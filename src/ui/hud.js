import { PLAYER, GUN } from '../config.js';

const $ = (id) => document.getElementById(id);

// DOM overlay: vitals, prompts, boss bar, title / death / end screens.
export class Hud {
  constructor() {
    this.el = { hud: $('hud'), hp: $('hpFill'), hpLag: $('hpLag'), en: $('enFill'), heat: $('heatFill'), objective: $('objective'), toast: $('toast'), prompt: $('prompt'), hint: $('hint'),
      boss: $('boss'), bossName: $('bossName'), bossFill: $('bossFill'), bossLag: $('bossLag'), cursor: $('cursor'), title: $('title'), death: $('death'), end: $('end'), pause: $('pause'), stats: $('stats') };
    this.deathShown = false; this.promptText = null; this.toastT = 0; this.hintT = 0; this.last = {};
    addEventListener('mousemove', (e) => { this.el.cursor.style.transform = `translate(${e.clientX}px, ${e.clientY}px)`; });
  }
  setLoading(p, text) { $('loadFill').style.width = `${Math.round(p * 100)}%`; if (text) $('loadText').textContent = text; }
  ready() { $('loading').classList.add('hidden'); $('start').classList.remove('hidden'); }
  hideTitle() { this.el.title.classList.add('out'); this.el.hud.classList.remove('hidden'); setTimeout(() => this.el.title.classList.add('hidden'), 1500); }
  objective(t) { if (this.last.obj === t) return; this.last.obj = t; this.el.objective.textContent = t || ''; }
  toast(t) { this.el.toast.textContent = t; this.el.toast.classList.add('on'); this.toastT = 2.6; }
  hint(t, dur = 5) { this.el.hint.textContent = t; this.el.hint.classList.add('on'); this.hintT = dur; }
  prompt(t) { if (t === this.promptText) return; this.promptText = t; if (t) { this.el.prompt.textContent = t; this.el.prompt.classList.add('on'); } else this.el.prompt.classList.remove('on'); }
  pulse(kind) { const b = (kind === 'energy' ? this.el.en : this.el.heat).parentElement; b.classList.remove('flash'); void b.offsetWidth; b.classList.add('flash'); }
  bossBar(frac, name) {
    if (frac === null) { this.el.boss.classList.remove('on'); return; }
    this.el.boss.classList.add('on'); if (name) this.el.bossName.textContent = name;
    const s = `scaleX(${frac.toFixed(4)})`; this.el.bossFill.style.transform = s; this.el.bossLag.style.transform = s;
  }
  flashBoss() { const b = this.el.boss; b.classList.remove('flash'); void b.offsetWidth; b.classList.add('flash'); }
  showDeath(on) { this.deathShown = on; this.el.death.classList.toggle('hidden', !on); }
  showPause(on) { this.el.pause.classList.toggle('hidden', !on); }
  showEnd(stats) {
    const m = Math.floor(stats.time / 60), s = Math.floor(stats.time % 60);
    this.el.stats.innerHTML = `TIME &nbsp; ${m}:${String(s).padStart(2, '0')}<br>DEATHS &nbsp; ${stats.deaths}<br>KILLS &nbsp; ${stats.kills}`;
    this.el.hud.classList.add('hidden'); this.el.end.classList.remove('hidden');
  }
  update(P, G) {
    const hp = Math.max(0, P.hp / PLAYER.hp), en = P.energy / GUN.energyMax, heat = P.overheat > 0 ? 1 : Math.min(1, P.heat);
    if (hp !== this.last.hp) { this.last.hp = hp; const s = `scaleX(${hp.toFixed(3)})`; this.el.hp.style.transform = s; this.el.hpLag.style.transform = s; this.el.hp.classList.toggle('low', hp < 0.35); }
    if (en !== this.last.en) { this.last.en = en; this.el.en.style.transform = `scaleX(${en.toFixed(3)})`; }
    if (heat !== this.last.heat) { this.last.heat = heat; this.el.heat.style.transform = `scaleX(${heat.toFixed(3)})`; }
    const locked = P.overheat > 0;
    if (locked !== this.last.locked) { this.last.locked = locked; this.el.heat.parentElement.classList.toggle('locked', locked); this.el.cursor.classList.toggle('hot', locked); }
    const firing = G.input.fire && !locked;
    if (firing !== this.last.firing) { this.last.firing = firing; this.el.cursor.classList.toggle('fire', firing); }
    const dt = 1 / 60;
    if (this.toastT > 0) { this.toastT -= dt; if (this.toastT <= 0) this.el.toast.classList.remove('on'); }
    if (this.hintT > 0) { this.hintT -= dt; if (this.hintT <= 0) this.el.hint.classList.remove('on'); }
  }
}
