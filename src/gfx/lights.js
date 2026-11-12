import * as THREE from 'three';

const N_SPOT = 5, N_SHADOW = 2, N_POINT = 6, N_FX = 3;

function glowTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d'); const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.12, 'rgba(255,255,255,0.75)');
  gr.addColorStop(0.35, 'rgba(255,255,255,0.18)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

const ShaftShader = {
  vertexShader: /* glsl */`varying vec3 vN; varying vec3 vV; varying float vH;
    void main(){ vec4 mv = modelViewMatrix*vec4(position,1.0); vN = normalize(normalMatrix*normal); vV = normalize(-mv.xyz); vH = uv.y; gl_Position = projectionMatrix*mv; }`,
  fragmentShader: /* glsl */`uniform vec3 uColor; uniform float uInt; varying vec3 vN; varying vec3 vV; varying float vH;
    void main(){ float f = abs(dot(normalize(vN), normalize(vV))); f = pow(f, 2.2);
      float h = smoothstep(0.0, 0.25, vH) * (0.25 + 0.75*vH);
      gl_FragColor = vec4(uColor * uInt * f * h, 1.0); }`,
};

// Owns every real light in the scene. Fixtures (dozens) are mapped onto a small fixed pool so the
// shader light count never changes (no recompiles, bounded cost).
export class LightRig {
  constructor(scene, fixtures) {
    this.scene = scene; this.fixtures = fixtures; this.byId = {};
    this.time = 0; this.shaftGain = 0.007;
    this.hemi = new THREE.HemisphereLight(0x263c56, 0x05080c, 0.62);
    scene.add(this.hemi);

    // player flashlight
    const fl = this.flash = new THREE.SpotLight(0xd6e8ff, 0, 26, 0.48, 0.45, 0.7);
    fl.castShadow = true; fl.shadow.mapSize.set(2048, 2048); fl.shadow.camera.near = 0.25; fl.shadow.camera.far = 26;
    fl.shadow.bias = -0.0006; fl.shadow.normalBias = 0.03;
    scene.add(fl, fl.target);
    this.flashOn = true; this.flashBase = 52; this.flashFlicker = 1;
    this.flashPos = new THREE.Vector3(); this.flashDir = new THREE.Vector3(0, 0, -1);

    // faint warm lamp on the player's suit so they never vanish completely
    this.suit = new THREE.PointLight(0xffb060, 0.9, 3.2, 1.4); scene.add(this.suit);
    this.spots = [];
    for (let i = 0; i < N_SPOT; i++) {
      const l = new THREE.SpotLight(0xffffff, 0, 20, 0.6, 0.9, 1.5);
      if (i < N_SHADOW) { l.castShadow = true; l.shadow.mapSize.set(1024, 1024); l.shadow.camera.near = 2; l.shadow.camera.far = 24; l.shadow.bias = -0.0006; l.shadow.normalBias = 0.05; }
      scene.add(l, l.target); this.spots.push({ light: l, fx: null, fade: 0 });
    }
    this.points = [];
    for (let i = 0; i < N_POINT; i++) { const l = new THREE.PointLight(0xffffff, 0, 10, 1.6); scene.add(l); this.points.push({ light: l, fx: null, fade: 0 }); }
    this.fx = [];
    for (let i = 0; i < N_FX; i++) { const l = new THREE.PointLight(0xffffff, 0, 10, 1.8); scene.add(l); this.fx.push({ light: l, t: 0, dur: 1, peak: 0 }); }
    this.fxNext = 0;

    // visible bulbs + light shafts for the fixtures
    const tex = glowTexture();
    const coneGeo = new THREE.CylinderGeometry(0.25, 1, 1, 28, 1, true); coneGeo.translate(0, -0.5, 0);
    for (const f of fixtures) {
      if (f.id) this.byId[f.id] = f;
      f.mult = 1; f.cur = f.on ? f.intensity : 0; f.col = new THREE.Color(f.color); f.seed = Math.random() * 100;
      const sm = new THREE.SpriteMaterial({ map: tex, color: f.col, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, fog: false });
      const s = f.sprite = new THREE.Sprite(sm);
      if (f.kind === 'spot') {
        f.ox = f.ox ?? -4.6; f.oz = f.oz ?? -2.2;
        f.px = f.x + f.ox; f.pz = f.z + f.oz; f.dir = new THREE.Vector3(-f.ox, -f.y, -f.oz); f.len = f.dir.length(); f.dir.normalize();
        s.visible = false; f.noSprite = true;
        const lampY = f.len;
        const m = new THREE.ShaderMaterial({ ...ShaftShader, uniforms: { uColor: { value: f.col.clone() }, uInt: { value: 0 } }, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
        const cone = f.shaft = new THREE.Mesh(coneGeo, m);
        const rad = Math.tan(f.angle) * lampY * 0.9;
        cone.position.set(f.px, f.y, f.pz); cone.scale.set(rad, lampY, rad); cone.renderOrder = 5;
        cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), f.dir);
        scene.add(cone);
      } else { s.position.set(f.x, f.y, f.z); s.scale.setScalar(f.fire ? 0.01 : 0.6); }
      scene.add(s);
    }
    // uniforms shared with lit particles / dust
    this.uni = {
      uFlashPos: { value: this.flashPos }, uFlashDir: { value: this.flashDir }, uFlashCos: { value: Math.cos(0.5) }, uFlashInt: { value: 0 },
      uSpotPos: { value: Array.from({ length: N_SPOT }, () => new THREE.Vector3()) },
      uSpotCol: { value: Array.from({ length: N_SPOT }, () => new THREE.Vector3()) },
      uSpotDir: { value: Array.from({ length: N_SPOT }, () => new THREE.Vector3(0, -1, 0)) },
      uSpotCos: { value: new Float32Array(N_SPOT) },
      uPointPos: { value: Array.from({ length: N_POINT + N_FX }, () => new THREE.Vector3()) },
      uPointCol: { value: Array.from({ length: N_POINT + N_FX }, () => new THREE.Vector3()) },
      uAmbient: { value: new THREE.Vector3(0.012, 0.02, 0.032) },
    };
  }

  setFixture(id, props) { const f = this.byId[id]; if (f) Object.assign(f, props); if (f && props.color !== undefined) { f.col.set(props.color); f.sprite.material.color.copy(f.col); if (f.shaft) f.shaft.material.uniforms.uColor.value.copy(f.col); } return f; }

  // One-shot flash (muzzle, impacts, explosions).
  burst(x, y, z, color, intensity, range = 8, dur = 0.12) {
    const s = this.fx[this.fxNext]; this.fxNext = (this.fxNext + 1) % N_FX;
    s.light.position.set(x, y, z); s.light.color.set(color); s.light.distance = range; s.t = dur; s.dur = dur; s.peak = intensity;
  }

  setFlashlight(origin, dir, on) {
    this.flashOn = on;
    this.flashPos.copy(origin); this.flashDir.copy(dir).normalize();
    this.flash.position.copy(origin); this.suit.position.set(origin.x, 1.1, origin.z);
    this.flash.target.position.copy(origin).addScaledVector(this.flashDir, 6);
    this.flash.target.updateMatrixWorld();
  }

  flickerValue(f, t) {
    if (!f.flicker) return 1;
    const n = Math.sin(t * 13.7 + f.seed) * Math.sin(t * 7.1 + f.seed * 2.3) * Math.sin(t * 23.3 + f.seed * 0.7);
    if (f.flicker === 1) return 0.88 + 0.12 * n;
    if (f.flicker === 2) { const k = Math.sin(t * 1.3 + f.seed) + Math.sin(t * 3.7 + f.seed * 1.9) * 0.6; return (k > 1.15 ? (Math.sin(t * 61 + f.seed) > 0 ? 0.08 : 0.75) : 0.9 + 0.1 * n); }
    if (f.flicker === 3) return (Math.sin(t * 9) > 0 ? 1 : 0.12);
    return 1;
  }

  assign(pool, kind, fx, fz, dt) {
    // rank fixtures of this kind by distance to the focus
    const cands = [];
    for (const f of this.fixtures) {
      if (f.kind !== kind || f.cur < 0.01) continue;
      const d = Math.hypot(f.x - fx, f.z - fz); if (d > 34) continue;
      cands.push([d - (f.priority || 0), f]);
    }
    cands.sort((a, b) => a[0] - b[0]);
    const want = new Set(cands.slice(0, pool.length).map((c) => c[1]));
    for (const s of pool) {
      if (s.fx && want.has(s.fx)) { want.delete(s.fx); s.fade = Math.min(1, s.fade + dt * 3.5); }
      else { s.fade = Math.max(0, s.fade - dt * 3.5); if (s.fade === 0) s.fx = null; }
    }
    for (const f of want) { const s = pool.find((p) => !p.fx); if (!s) break; s.fx = f; s.fade = 0; }
  }

  update(dt, focusX, focusZ) {
    const t = this.time += dt;
    for (const f of this.fixtures) {
      const target = f.on ? f.intensity : 0;
      f.cur += (target - f.cur) * Math.min(1, dt * 6);
      f.mult = this.flickerValue(f, t) * (f.dim ?? 1);
      const vis = f.cur > 0.01 ? f.mult * Math.min(1, f.cur / Math.max(1, f.intensity || 1)) : 0;
      f.sprite.material.opacity = vis; f.sprite.visible = vis > 0.01 && !f.noSprite;
      if (f.shaft) { f.shaft.material.uniforms.uInt.value = vis * this.shaftGain * Math.min(1.6, f.intensity / 400); f.shaft.visible = vis > 0.01; }
    }
    this.assign(this.spots, 'spot', focusX, focusZ, dt);
    this.assign(this.points, 'point', focusX, focusZ, dt);
    const U = this.uni;
    this.spots.forEach((s, i) => {
      const l = s.light, f = s.fx;
      if (!f) { l.intensity = 0; U.uSpotCol.value[i].set(0, 0, 0); return; }
      l.position.set(f.px, f.y, f.pz); l.target.position.set(f.x, 0, f.z); l.angle = f.angle; l.distance = f.len + f.range;
      l.color.copy(f.col); l.intensity = f.cur * f.mult * s.fade;
      U.uSpotPos.value[i].set(f.px, f.y, f.pz); U.uSpotDir.value[i].copy(f.dir); U.uSpotCos.value[i] = Math.cos(f.angle);
      U.uSpotCol.value[i].set(f.col.r, f.col.g, f.col.b).multiplyScalar(l.intensity);
    });
    this.points.forEach((s, i) => {
      const l = s.light, f = s.fx;
      if (!f) { l.intensity = 0; U.uPointCol.value[i].set(0, 0, 0); return; }
      l.position.set(f.x, f.y, f.z); l.distance = f.range; l.color.copy(f.col); l.intensity = f.cur * f.mult * s.fade;
      U.uPointPos.value[i].copy(l.position); U.uPointCol.value[i].set(f.col.r, f.col.g, f.col.b).multiplyScalar(l.intensity);
    });
    this.fx.forEach((s, i) => {
      if (s.t > 0) { s.t -= dt; const k = Math.max(0, s.t / s.dur); s.light.intensity = s.peak * k * k; } else s.light.intensity = 0;
      const j = N_POINT + i; U.uPointPos.value[j].copy(s.light.position);
      U.uPointCol.value[j].set(s.light.color.r, s.light.color.g, s.light.color.b).multiplyScalar(s.light.intensity);
    });
    const fi = this.flashOn ? this.flashBase * this.flashFlicker : 0;
    this.flash.intensity += (fi - this.flash.intensity) * Math.min(1, dt * 30);
    U.uFlashInt.value = this.flash.intensity; U.uFlashCos.value = Math.cos(this.flash.angle);
  }
}

// GLSL shared by lit particles: approximate incoming light at a world position.
export const LIT_GLSL = /* glsl */`
uniform vec3 uFlashPos, uFlashDir, uAmbient; uniform float uFlashCos, uFlashInt;
uniform vec3 uSpotPos[${N_SPOT}]; uniform vec3 uSpotCol[${N_SPOT}]; uniform vec3 uSpotDir[${N_SPOT}]; uniform float uSpotCos[${N_SPOT}];
uniform vec3 uPointPos[${N_POINT + N_FX}]; uniform vec3 uPointCol[${N_POINT + N_FX}];
vec3 sceneLight(vec3 p){
  vec3 l = uAmbient;
  vec3 d = p - uFlashPos; float dist = length(d); float c = dot(d/max(dist,1e-3), uFlashDir);
  l += vec3(0.8,0.9,1.0) * uFlashInt * smoothstep(uFlashCos, mix(uFlashCos,1.0,0.6), c) / (0.6 + pow(dist, 0.7)) * smoothstep(26.0, 12.0, dist);
  for(int i=0;i<${N_SPOT};i++){ vec3 e = p - uSpotPos[i]; float dd = length(e); float cc = dot(e/max(dd,1e-3), uSpotDir[i]);
    l += uSpotCol[i] * smoothstep(uSpotCos[i], mix(uSpotCos[i],1.0,0.7), cc) / (1.0 + dd*dd); }
  for(int i=0;i<${N_POINT + N_FX};i++){ vec3 e = p - uPointPos[i]; l += uPointCol[i] / (1.0 + dot(e,e)*1.5); }
  return l;
}`;
