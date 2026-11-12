import * as THREE from 'three';
import { LIT_GLSL } from './lights.js';

const VERT = (lit) => /* glsl */`
attribute vec4 aColor; attribute float aSize;
varying vec4 vColor;
uniform float uScale;
${lit ? LIT_GLSL : ''}
void main(){
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * mv;
  gl_PointSize = aSize * uScale / -mv.z;
  vColor = aColor;
  ${lit ? 'vColor.rgb *= sceneLight(position) * 0.32;' : ''}
}`;
const FRAG = /* glsl */`
varying vec4 vColor; uniform float uSoft;
void main(){ vec2 c = gl_PointCoord - 0.5; float d = length(c)*2.0; float a = smoothstep(1.0, uSoft, d);
  gl_FragColor = vec4(vColor.rgb, vColor.a * a); }`;

class Pool {
  constructor(scene, max, lit, uni, blending, soft) {
    this.max = max; this.n = 0;
    this.px = new Float32Array(max * 3); this.col = new Float32Array(max * 4); this.size = new Float32Array(max);
    this.vx = new Float32Array(max * 3); this.life = new Float32Array(max); this.maxLife = new Float32Array(max);
    this.s0 = new Float32Array(max); this.s1 = new Float32Array(max); this.a0 = new Float32Array(max);
    this.grav = new Float32Array(max); this.drag = new Float32Array(max); this.flags = new Uint8Array(max);
    const g = this.geo = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(this.px, 3).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aColor', new THREE.BufferAttribute(this.col, 4).setUsage(THREE.DynamicDrawUsage));
    g.setAttribute('aSize', new THREE.BufferAttribute(this.size, 1).setUsage(THREE.DynamicDrawUsage));
    this.mat = new THREE.ShaderMaterial({
      vertexShader: VERT(lit), fragmentShader: FRAG, transparent: true, depthWrite: false, blending,
      uniforms: { uScale: { value: 800 }, uSoft: { value: soft }, ...(lit ? uni : {}) },
    });
    this.points = new THREE.Points(g, this.mat); this.points.frustumCulled = false; this.points.renderOrder = 10;
    scene.add(this.points);
  }
  emit(x, y, z, vx, vy, vz, life, s0, s1, r, g, b, a, grav, drag, flags = 0) {
    if (this.n >= this.max) return;
    const i = this.n++;
    this.px[i * 3] = x; this.px[i * 3 + 1] = y; this.px[i * 3 + 2] = z;
    this.vx[i * 3] = vx; this.vx[i * 3 + 1] = vy; this.vx[i * 3 + 2] = vz;
    this.life[i] = this.maxLife[i] = life; this.s0[i] = s0; this.s1[i] = s1; this.a0[i] = a;
    this.col[i * 4] = r; this.col[i * 4 + 1] = g; this.col[i * 4 + 2] = b; this.col[i * 4 + 3] = a;
    this.grav[i] = grav; this.drag[i] = drag; this.flags[i] = flags; this.size[i] = s0;
  }
  kill(i) {
    const j = --this.n; if (i === j) return;
    for (let k = 0; k < 3; k++) { this.px[i * 3 + k] = this.px[j * 3 + k]; this.vx[i * 3 + k] = this.vx[j * 3 + k]; }
    for (let k = 0; k < 4; k++) this.col[i * 4 + k] = this.col[j * 4 + k];
    this.life[i] = this.life[j]; this.maxLife[i] = this.maxLife[j]; this.s0[i] = this.s0[j]; this.s1[i] = this.s1[j]; this.a0[i] = this.a0[j];
    this.grav[i] = this.grav[j]; this.drag[i] = this.drag[j]; this.flags[i] = this.flags[j]; this.size[i] = this.size[j];
  }
  update(dt, onGround) {
    for (let i = this.n - 1; i >= 0; i--) {
      const l = this.life[i] -= dt;
      if (l <= 0) { this.kill(i); continue; }
      const k = 1 - Math.min(1, this.drag[i] * dt);
      this.vx[i * 3] *= k; this.vx[i * 3 + 2] *= k; this.vx[i * 3 + 1] = this.vx[i * 3 + 1] * k - this.grav[i] * dt;
      this.px[i * 3] += this.vx[i * 3] * dt; this.px[i * 3 + 1] += this.vx[i * 3 + 1] * dt; this.px[i * 3 + 2] += this.vx[i * 3 + 2] * dt;
      if (this.px[i * 3 + 1] < 0.03 && this.grav[i] > 0) {
        if (this.flags[i] & 1) { onGround && onGround(this.px[i * 3], this.px[i * 3 + 2], this.flags[i], this.col, i * 4); this.kill(i); continue; }
        this.px[i * 3 + 1] = 0.03; this.vx[i * 3 + 1] *= -0.3; this.vx[i * 3] *= 0.6; this.vx[i * 3 + 2] *= 0.6;
      }
      const t = 1 - l / this.maxLife[i];
      this.size[i] = this.s0[i] + (this.s1[i] - this.s0[i]) * t;
      this.col[i * 4 + 3] = this.a0[i] * (this.flags[i] & 2 ? Math.sin(Math.min(1, t * 1.02) * Math.PI) : (1 - t * t));
    }
    const g = this.geo; g.setDrawRange(0, this.n);
    g.attributes.position.needsUpdate = true; g.attributes.aColor.needsUpdate = true; g.attributes.aSize.needsUpdate = true;
  }
}

// Ambient dust: GPU-wrapped cloud that follows the camera focus and is only visible where light hits it.
function makeDust(scene, uni) {
  const N = 1400, pos = new Float32Array(N * 3), seed = new Float32Array(N);
  for (let i = 0; i < N; i++) { pos[i * 3] = Math.random(); pos[i * 3 + 1] = Math.random(); pos[i * 3 + 2] = Math.random(); seed[i] = Math.random(); }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 1));
  const m = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { ...uni, uTime: { value: 0 }, uFocus: { value: new THREE.Vector3() }, uBox: { value: new THREE.Vector3(34, 6, 26) }, uScale: { value: 800 } },
    vertexShader: /* glsl */`
      attribute float aSeed; uniform float uTime, uScale; uniform vec3 uFocus, uBox; varying vec3 vCol;
      ${LIT_GLSL}
      void main(){
        vec3 drift = vec3(sin(aSeed*40.0)*0.12, 0.05 + aSeed*0.05, cos(aSeed*27.0)*0.12) * uTime;
        drift += 0.25*vec3(sin(uTime*0.4+aSeed*60.0), sin(uTime*0.3+aSeed*33.0), cos(uTime*0.35+aSeed*81.0));
        vec3 p = position*uBox + drift;
        vec3 o = uFocus - uBox*vec3(0.5,0.0,0.5);
        p = mod(p - o, uBox) + o; p.y = mod(position.y*uBox.y + drift.y, uBox.y) + 0.05;
        vec4 mv = modelViewMatrix*vec4(p,1.0); gl_Position = projectionMatrix*mv;
        gl_PointSize = max(1.5, (0.014 + aSeed*0.03) * uScale / -mv.z);
        vCol = sceneLight(p) * (0.25 + 0.75*aSeed);
      }`,
    fragmentShader: /* glsl */`varying vec3 vCol; void main(){ vec2 c = gl_PointCoord-0.5; float a = smoothstep(0.5,0.1,length(c)); gl_FragColor = vec4(vCol*a*0.05, 1.0); }`,
  });
  const p = new THREE.Points(g, m); p.frustumCulled = false; p.renderOrder = 9; scene.add(p);
  return p;
}

export class Particles {
  constructor(scene, lightUni) {
    this.add = new Pool(scene, 3000, false, null, THREE.AdditiveBlending, 0.0);
    this.lit = new Pool(scene, 3000, true, lightUni, THREE.NormalBlending, 0.55);
    this.dust = makeDust(scene, lightUni);
    this.onBloodLand = null;
  }
  setScale(pxHeight, fovRad) { const s = pxHeight / (2 * Math.tan(fovRad / 2)); this.add.mat.uniforms.uScale.value = s; this.lit.mat.uniforms.uScale.value = s; this.dust.material.uniforms.uScale.value = s; }
  update(dt, time, focus) {
    this.add.update(dt, null);
    this.lit.update(dt, (x, z, flags, col, ci) => this.onBloodLand && this.onBloodLand(x, z, col[ci], col[ci + 1], col[ci + 2]));
    this.dust.material.uniforms.uTime.value = time; this.dust.material.uniforms.uFocus.value.copy(focus);
  }
  // ── effect presets ──
  sparks(x, y, z, nx, nz, n = 10, color = [0.5, 0.9, 1.0], speed = 6) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * 6.283, s = speed * (0.3 + Math.random());
      this.add.emit(x, y, z, nx * s * 0.7 + Math.cos(a) * s * 0.6, 1.5 + Math.random() * 4, nz * s * 0.7 + Math.sin(a) * s * 0.6,
        0.18 + Math.random() * 0.35, 0.09, 0.02, color[0] * 3, color[1] * 3, color[2] * 3, 1, 14, 1.5);
    }
  }
  glow(x, y, z, size, color, life = 0.12, a = 1) { this.add.emit(x, y, z, 0, 0, 0, life, size, size * 1.6, color[0], color[1], color[2], a, 0, 0); }
  blood(x, y, z, dx, dz, n = 14, speed = 5, color = [0.55, 0.02, 0.02]) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * 6.283, s = speed * (0.2 + Math.random());
      this.lit.emit(x + (Math.random() - 0.5) * 0.2, y + Math.random() * 0.3, z + (Math.random() - 0.5) * 0.2,
        dx * s * 0.8 + Math.cos(a) * s * 0.5, 1 + Math.random() * 4.5, dz * s * 0.8 + Math.sin(a) * s * 0.5,
        0.6 + Math.random() * 0.6, 0.07 + Math.random() * 0.09, 0.04, color[0] * 0.9, color[1] * 0.9, color[2] * 0.9, 1, 13, 0.6, Math.random() < 0.55 ? 1 : 0);
    }
    for (let i = 0; i < Math.ceil(n / 5); i++) {  // red mist
      this.lit.emit(x, y + 0.2, z, dx * 1.5 + (Math.random() - 0.5), 0.5 + Math.random(), dz * 1.5 + (Math.random() - 0.5), 0.5 + Math.random() * 0.4, 0.3, 1.1, color[0] * 0.7, color[1] * 0.7, color[2] * 0.7, 0.22, 0, 2.5, 2);
    }
  }
  smoke(x, y, z, n = 4, size = 0.6, color = [0.5, 0.55, 0.6], rise = 0.8, a = 0.25) {
    for (let i = 0; i < n; i++) this.lit.emit(x + (Math.random() - 0.5) * 0.3, y, z + (Math.random() - 0.5) * 0.3, (Math.random() - 0.5) * 0.6, rise * (0.5 + Math.random()), (Math.random() - 0.5) * 0.6,
      0.9 + Math.random() * 0.9, size * 0.5, size * 2.2, color[0] * 1.2, color[1] * 1.2, color[2] * 1.2, a, 0, 1.2, 2);
  }
  embers(x, y, z, n = 2, spread = 1.5) {
    for (let i = 0; i < n; i++) this.add.emit(x + (Math.random() - 0.5) * spread, y + Math.random() * 0.5, z + (Math.random() - 0.5) * spread, (Math.random() - 0.5) * 0.8, 0.8 + Math.random() * 1.6, (Math.random() - 0.5) * 0.8,
      1.5 + Math.random() * 2, 0.05, 0.01, 3.0, 0.9 + Math.random() * 0.6, 0.15, 1, -0.3, 0.4);
  }
  bile(x, y, z, n = 12) {
    for (let i = 0; i < n; i++) { const a = Math.random() * 6.283, s = 1 + Math.random() * 4;
      this.add.emit(x, y, z, Math.cos(a) * s, 1 + Math.random() * 3.5, Math.sin(a) * s, 0.4 + Math.random() * 0.4, 0.14, 0.03, 0.9, 1.6, 0.15, 1, 12, 1); }
  }
  ring(x, y, z, radius, n, color, speed = 0) {
    for (let i = 0; i < n; i++) { const a = i / n * 6.283; this.add.emit(x + Math.cos(a) * radius, y, z + Math.sin(a) * radius, Math.cos(a) * speed, 0.2, Math.sin(a) * speed, 0.35, 0.22, 0.05, color[0], color[1], color[2], 0.9, 0, 2); }
  }
}

// Ground decals (blood, bile, scorch) as instanced quads with a small ring buffer per texture.
function splatTexture(seed, kind) {
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  let s = seed * 9301 + 49297; const rnd = () => ((s = (s * 9301 + 49297) % 233280) / 233280);
  g.fillStyle = '#000'; g.fillRect(0, 0, 128, 128);      // alphaMap reads the green channel, so paint on black
  g.fillStyle = '#fff';
  if (kind === 'scorch') {
    const gr = g.createRadialGradient(64, 64, 2, 64, 64, 62); gr.addColorStop(0, 'rgba(255,255,255,0.7)'); gr.addColorStop(0.35, 'rgba(255,255,255,0.35)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 128, 128);
    for (let i = 0; i < 40; i++) { const a = rnd() * 6.283, d = rnd() * 50; g.fillStyle = `rgba(255,255,255,${0.1 + rnd() * 0.25})`; g.beginPath(); g.arc(64 + Math.cos(a) * d, 64 + Math.sin(a) * d, 2 + rnd() * 7, 0, 6.283); g.fill(); }
  } else {
    const blob = (x, y, r) => { g.beginPath(); g.arc(x, y, r, 0, 6.283); g.fill(); };
    blob(64, 64, 18 + rnd() * 12);
    for (let i = 0; i < 26; i++) { const a = rnd() * 6.283, d = rnd() * rnd() * 54, r = 2 + rnd() * 9 * (1 - d / 60); blob(64 + Math.cos(a) * d, 64 + Math.sin(a) * d, r);
      if (rnd() < 0.4) { g.lineWidth = 1 + rnd() * 3; g.strokeStyle = '#fff'; g.beginPath(); g.moveTo(64, 64); g.lineTo(64 + Math.cos(a) * d, 64 + Math.sin(a) * d); g.stroke(); } }
  }
  const t = new THREE.CanvasTexture(c); return t;
}

export class Decals {
  constructor(scene) {
    this.sets = [];
    const geo = new THREE.PlaneGeometry(1, 1); geo.rotateX(-Math.PI / 2);
    const mk = (tex, n, mat) => {
      const m = new THREE.InstancedMesh(geo, mat(tex), n); m.count = n; m.frustumCulled = false; m.receiveShadow = true; m.renderOrder = 2;
      const z = new THREE.Matrix4().makeScale(0, 0, 0); for (let i = 0; i < n; i++) { m.setMatrixAt(i, z); m.setColorAt(i, new THREE.Color(1, 1, 1)); }
      scene.add(m); return { mesh: m, next: 0, n };
    };
    const wetMat = (tex) => new THREE.MeshStandardMaterial({ color: 0xffffff, alphaMap: tex, transparent: true, roughness: 0.12, metalness: 0, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2, envMapIntensity: 1.6 });
    const dryMat = (tex) => new THREE.MeshBasicMaterial({ color: 0xffffff, alphaMap: tex, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 });
    this.blood = [1, 2, 3].map((s) => mk(splatTexture(s, 'blood'), 110, wetMat));
    this.scorch = mk(splatTexture(9, 'scorch'), 80, dryMat);
    this.m = new THREE.Matrix4(); this.q = new THREE.Quaternion(); this.c = new THREE.Color(); this.y = 0.012;
  }
  place(set, x, z, size, color) {
    const i = set.next; set.next = (set.next + 1) % set.n;
    this.q.setFromAxisAngle(THREE.Object3D.DEFAULT_UP, Math.random() * 6.283);
    this.y += 0.0004; if (this.y > 0.03) this.y = 0.012;
    this.m.compose(new THREE.Vector3(x, this.y, z), this.q, new THREE.Vector3(size, 1, size));
    set.mesh.setMatrixAt(i, this.m); set.mesh.setColorAt(i, this.c.setRGB(color[0], color[1], color[2]));
    set.mesh.instanceMatrix.needsUpdate = true; set.mesh.instanceColor.needsUpdate = true;
  }
  splat(x, z, size = 1, color = [0.07, 0.002, 0.002]) { this.place(this.blood[(Math.random() * 3) | 0], x, z, size * (0.7 + Math.random() * 0.7), color); }
  burn(x, z, size = 0.8) { this.place(this.scorch, x, z, size * 0.75, [0, 0, 0]); }
  clear() { const z = new THREE.Matrix4().makeScale(0, 0, 0); for (const s of [...this.blood, this.scorch]) { for (let i = 0; i < s.n; i++) s.mesh.setMatrixAt(i, z); s.mesh.instanceMatrix.needsUpdate = true; } }
}
