import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';

// Loads textures + models and owns the shared material library.
// Every loader tolerates missing files so the game can boot with placeholders.

const NOISE_GLSL = /* glsl */`
float hash21(vec2 p){ p = fract(p*vec2(123.34, 456.21)); p += dot(p, p+45.32); return fract(p.x*p.y); }
float vnoise(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
  return mix(mix(hash21(i),hash21(i+vec2(1,0)),f.x), mix(hash21(i+vec2(0,1)),hash21(i+vec2(1,1)),f.x), f.y); }
float fbm(vec2 p){ float a=0.5, s=0.0; for(int i=0;i<4;i++){ s+=a*vnoise(p); p=p*2.03+17.1; a*=0.5; } return s; }
`;

export class Assets {
  constructor(renderer) {
    this.renderer = renderer;
    this.texLoader = new THREE.TextureLoader();
    this.gltfLoader = new GLTFLoader();
    this.texManifest = {};
    this.tex = {};          // slot -> {color, normal, ...}
    this.models = {};       // name -> gltf scene
    this.props = {};        // prop name -> Object3D
    this.propInfo = {};
    this.mats = {};         // shared prop/level materials
    this.maxAniso = renderer.capabilities.getMaxAnisotropy();
    this.onProgress = () => {};
  }

  async json(url) {
    try { const r = await fetch(url); if (!r.ok) return null; const t = await r.text(); if (t.trim().startsWith('<')) return null; return JSON.parse(t); }
    catch { return null; }
  }

  loadTex(url, srgb) {
    return new Promise((res) => {
      this.texLoader.load(url, (t) => {
        t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = Math.min(8, this.maxAniso);
        t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace; res(t);
      }, undefined, () => res(null));
    });
  }

  async loadAll() {
    const jobs = [];
    let done = 0; const tick = (p) => p.then((v) => { done++; this.onProgress(done / jobs.length); return v; });
    this.texManifest = (await this.json('/textures/manifest.json')) || {};
    for (const [slot, info] of Object.entries(this.texManifest)) {
      this.tex[slot] = { tile: info.tileSizeMeters || 2 };
      for (const m of info.maps || []) {
        jobs.push(tick(this.loadTex(`/textures/${slot}/${m}.jpg`, m === 'color').then((t) => {
          if (t) { t.repeat.setScalar(1 / this.tex[slot].tile); this.tex[slot][m] = t; }
        })));
      }
    }
    for (const name of ['props', 'player', 'gun', 'crawler', 'spitter', 'stalker', 'brute', 'boss', 'gibs', 'growths']) {
      jobs.push(tick(this.loadModel(name)));
    }
    jobs.push(tick(this.json('/models/props.json').then((j) => { this.propInfo = j || {}; })));
    await Promise.all(jobs);
    this.buildEnvironment();
    this.buildMaterials();
    this.indexProps();
  }

  loadModel(name) {
    return new Promise((res) => {
      this.gltfLoader.load(`/models/${name}.glb`, (g) => { this.models[name] = g.scene; res(g.scene); }, undefined, () => res(null));
    });
  }

  // Dim, cold studio-ish environment so metals and wet surfaces have something to reflect.
  buildEnvironment() {
    const scene = new THREE.Scene();
    const sky = new THREE.Mesh(new THREE.SphereGeometry(50, 32, 16), new THREE.ShaderMaterial({
      side: THREE.BackSide,
      vertexShader: 'varying vec3 vP; void main(){ vP = position; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
      fragmentShader: `varying vec3 vP; void main(){ float h = normalize(vP).y; vec3 c = mix(vec3(0.0015,0.003,0.005), vec3(0.03,0.055,0.085), smoothstep(-0.1,1.0,h)); gl_FragColor = vec4(c,1.0); }`,
    }));
    scene.add(sky);
    const box = new THREE.BoxGeometry(1, 1, 1);
    const panel = (x, y, z, sx, sz, col, k) => { const m = new THREE.Mesh(box, new THREE.MeshBasicMaterial({ color: new THREE.Color(col).multiplyScalar(k) })); m.position.set(x, y, z); m.scale.set(sx, 0.2, sz); scene.add(m); };
    panel(0, 30, 0, 14, 14, 0x9fc4ff, 6); panel(22, 24, -10, 10, 4, 0x7fa8ff, 3); panel(-20, 22, 14, 5, 12, 0x88b0ff, 2.2);
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    this.envMap = pmrem.fromScene(scene, 0.04).texture;
    pmrem.dispose();
  }

  // Level/prop surface material backed by a texture slot.
  surface(slot, o = {}) {
    const t = this.tex[slot] || {};
    const m = new THREE.MeshStandardMaterial({
      color: o.color ?? 0xffffff, map: t.color || null, normalMap: t.normal || null,
      roughnessMap: t.roughness || null, metalnessMap: t.metalness || null, aoMap: null,
      roughness: o.roughness ?? 1, metalness: o.metalness ?? (t.metalness ? 0.45 : 0),
      envMapIntensity: o.env ?? 1,
    });
    if (t.normal) m.normalScale.setScalar(o.normalScale ?? 1);
    if (!t.color) { m.color.multiply(new THREE.Color(o.fallback ?? 0x808890)); m.roughness = o.roughness ?? 0.7; }
    if (o.alphaTest && t.opacity) { m.alphaMap = t.opacity; m.alphaTest = o.alphaTest; m.side = THREE.DoubleSide; }
    if (o.emissive) { m.emissive = new THREE.Color(o.emissive); m.emissiveIntensity = o.emissiveIntensity ?? 1; }
    if (o.grime !== false) this.addGrime(m, o);
    return m;
  }

  // World-space grime + wet patches: breaks up tiling and gives puddle-like specular highlights.
  addGrime(m, o = {}) {
    const wet = o.wet ?? 0, grime = o.grime ?? 0.5, panel = o.panel ?? 0, flat = o.flat ?? 0;
    m.onBeforeCompile = (sh) => {
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vWPos;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\n#ifdef USE_INSTANCING\nvWPos = (modelMatrix * instanceMatrix * vec4(position,1.0)).xyz;\n#else\nvWPos = (modelMatrix * vec4(position,1.0)).xyz;\n#endif');
      sh.fragmentShader = sh.fragmentShader
        .replace('#include <common>', '#include <common>\nvarying vec3 vWPos;\nfloat gWet; float gSeam;\n' + NOISE_GLSL)
        .replace('#include <color_fragment>', `#include <color_fragment>
          { diffuseColor.rgb = mix(diffuseColor.rgb, diffuse * 0.42, ${flat.toFixed(2)});
            vec2 gp = vWPos.xz + vWPos.y*0.7;
            float g = fbm(gp*0.35); float g2 = fbm(gp*1.7+9.0);
            diffuseColor.rgb *= mix(1.0, 0.35 + 0.9*g, ${grime.toFixed(2)}) * mix(1.0, 0.75+0.5*g2, ${(grime * 0.6).toFixed(2)});
            gWet = ${wet.toFixed(2)} * smoothstep(0.50, 0.66, fbm(vWPos.xz*0.21+3.0));
            diffuseColor.rgb *= mix(1.0, 0.5, gWet);
            gSeam = 0.0;
            #if ${panel} > 0
            { vec2 ps = ${panel === 2 ? 'vec2(4.0, 4.0)' : 'vec2(4.0, 2.0)'}; vec2 pp = vWPos.xz / ps; pp.x += ${panel === 2 ? '0.0' : '0.5*floor(pp.y)'};
              vec2 cell = floor(pp); vec2 fr = abs(fract(pp) - 0.5) * ps;            // metres from the panel centre
              vec2 edge = ps*0.5 - fr; float dseam = min(edge.x, edge.y);
              gSeam = smoothstep(0.035, 0.008, dseam);
              float tone = 0.88 + 0.2*hash21(cell + 3.1);
              float bolt = ${panel === 2 ? '0.0' : 'smoothstep(0.045, 0.03, length(vec2(edge.x, edge.y) - vec2(0.16)))'};
              diffuseColor.rgb *= tone * (1.0 - 0.75*gSeam) * (1.0 + 0.5*bolt) * (0.75 + 0.25*smoothstep(0.0, 0.35, dseam)); }
            #endif
          }`)
        .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\nroughnessFactor = mix(mix(roughnessFactor, 0.3, gWet), 0.9, gSeam);')
        .replace('#include <normal_fragment_maps>', '#include <normal_fragment_maps>\nnormal = normalize(mix(normal, nonPerturbedNormal, gWet*0.9));');
    };
    m.customProgramCacheKey = () => `grime_${wet}_${grime}_${panel}_${flat}`;
  }

  glow(color, intensity) {
    return new THREE.MeshStandardMaterial({ color: 0x050505, emissive: color, emissiveIntensity: intensity, roughness: 0.4 });
  }

  buildMaterials() {
    const M = this.mats;
    // level
    M.floor_plate = this.surface('metal_dark', { color: 0x9aa8b8, wet: 1, grime: 0.65, env: 0.9, panel: 1, metalness: 0.3, fallback: 0x70777f });
    M.floor_tread = this.surface('floor_tread', { color: 0x7d8da0, wet: 0.8, grime: 0.6, env: 0.9, metalness: 0.3, panel: 1 });
    M.floor_concrete = this.surface('floor_concrete', { color: 0x6d7886, wet: 1, grime: 0.5, env: 0.6, panel: 2 });
    M.floor_grate = this.surface('floor_grate', { color: 0x9fb0c4, alphaTest: 0.5, grime: 0.3, env: 0.8 });
    M.wall_metal = this.surface('wall_metal', { color: 0x8493a6, grime: 0.6, env: 0.7 });
    M.wall_concrete = this.surface('wall_concrete', { color: 0xb4bfcc, grime: 0.6, env: 0.4 });
    M.wall_top = new THREE.MeshBasicMaterial({ color: 0x010203 });
    M.trim = this.surface('metal_dark', { color: 0x8a96a6, grime: 0.5, env: 0.8 });
    M.hazard = this.surface('metal_painted', { color: 0xb08a22, grime: 0.7, env: 0.5, flat: 0.55 });
    // props (names match the Blender material contract)
    M.metal_plate = this.surface('metal_painted', { color: 0x6c8198, grime: 0.55, env: 0.7, flat: 0.65 });
    M.metal_rust = this.surface('metal_rust', { color: 0xa39a94, grime: 0.4, env: 0.4 });
    M.metal_dark = this.surface('metal_dark', { color: 0x76808c, grime: 0.4, env: 0.9 });
    M.metal_bare = this.surface('metal_dark', { color: 0xd8e0ea, grime: 0.25, env: 1.3, roughness: 0.55 });
    M.metal_yellow = this.surface('metal_painted', { color: 0xc59a1e, grime: 0.6, env: 0.5, flat: 0.55 });
    M.metal_red = this.surface('metal_painted', { color: 0xa32418, grime: 0.6, env: 0.5, flat: 0.55 });
    M.rubber = this.surface('rubber', { color: 0x8a8f96, grime: 0.3, env: 0.5 });
    M.belt = this.surface('rubber', { color: 0x70757c, grime: 0, env: 0.5 });
    if (M.belt.map) { for (const k of ['map', 'normalMap', 'roughnessMap']) if (M.belt[k]) { M.belt[k] = M.belt[k].clone(); M.belt[k].needsUpdate = true; } }
    M.concrete = this.surface('floor_concrete', { color: 0xb0b8c2, grime: 0.5, env: 0.4 });
    M.wood = this.surface('floor_concrete', { color: 0x8a6a48, grime: 0.6, env: 0.2 });
    M.cloth = this.surface('rubber', { color: 0x9aa4ad, grime: 0.6, env: 0.15, roughness: 1 });
    M.glass = new THREE.MeshStandardMaterial({ color: 0x1a2a33, roughness: 0.15, metalness: 0.2, transparent: true, opacity: 0.55, envMapIntensity: 1.5 });
    M.screen = this.glow(0x2bff8a, 0.9);
    M.glow_white = this.glow(0xcfe2ff, 3.2);
    M.glow_red = this.glow(0xff2412, 3.0);
    M.glow_amber = this.glow(0xff9a2a, 2.6);
    M.glow_cyan = this.glow(0x30e0ff, 3.0);
    M.glow_green = this.glow(0x3cff86, 2.6);
    M.glow_furnace = this.glow(0xffffff, 2.4);
    { const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
      g.fillStyle = '#ff5a10'; g.fillRect(0, 0, 256, 256);
      for (let i = 0; i < 90; i++) { const x = Math.random() * 256, y = Math.random() * 256, r = 6 + Math.random() * 30; const gr = g.createRadialGradient(x, y, 0, x, y, r);
        const hot = Math.random() < 0.45; gr.addColorStop(0, hot ? 'rgba(255,225,120,0.9)' : 'rgba(60,8,0,0.85)'); gr.addColorStop(1, hot ? 'rgba(255,140,30,0)' : 'rgba(120,20,0,0)');
        g.fillStyle = gr; for (const ox of [-256, 0, 256]) for (const oy of [-256, 0, 256]) { g.beginPath(); g.arc(x + ox, y + oy, r, 0, 6.3); g.fill(); } }
      const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.SRGBColorSpace; t.repeat.set(0.6, 0.6); M.glow_furnace.emissiveMap = t; this.moltenTex = t; }
    M.glow_orange = this.glow(0xff6a18, 3.0);
    M.glow_bile = this.glow(0xb8ff3a, 1.1);
    M.fallback = new THREE.MeshStandardMaterial({ color: 0x59646f, roughness: 0.7, metalness: 0.3 });
    // organic set dressing (vertex coloured)
    M.flesh = new THREE.MeshStandardMaterial({ color: 0xa69c9c, vertexColors: true, roughness: 0.36, metalness: 0, envMapIntensity: 0.9 });
    M.flesh_dark = new THREE.MeshStandardMaterial({ color: 0xb0a0a0, vertexColors: true, roughness: 0.25, metalness: 0, envMapIntensity: 1.0 });
    M.bone = new THREE.MeshStandardMaterial({ color: 0xffffff, vertexColors: true, roughness: 0.45 });
  }

  // Material for creature meshes: keeps vertex colours, picks shading by contract name.
  creatureMaterial(name, hasColors) {
    const base = { vertexColors: !!hasColors, color: 0xffffff, envMapIntensity: 0.9 };
    const n = name || 'flesh';
    if (n.startsWith('glow_')) {
      const col = { glow_amber: 0xffa030, glow_cyan: 0x30e0ff, glow_orange: 0xff6a18, glow_red: 0xff2412, glow_bile: 0xb8ff3a, glow_furnace: 0xff5a12 }[n] ?? 0xffffff;
      const m = this.glow(col, n === 'glow_bile' ? 1.3 : 2.6); m.userData.glow = n;
      if (hasColors) {
        m.vertexColors = true; m.color.set(0x222222);
        m.onBeforeCompile = (sh) => { sh.fragmentShader = sh.fragmentShader.replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n#ifdef USE_COLOR\ntotalEmissiveRadiance *= (0.15 + 1.6*vColor.rgb*vColor.rgb);\n#endif'); };
        m.customProgramCacheKey = () => 'glowvc';
      }
      return m;
    }
    const P = {
      flesh: { roughness: 0.34, color: 0xa39a98 }, flesh_dark: { roughness: 0.22, color: 0xa89696 }, bone: { roughness: 0.42, color: 0xb5b0a8 }, cloth: { roughness: 0.95, envMapIntensity: 0.2 },
      metal: { roughness: 0.5, metalness: 0.8, envMapIntensity: 1.2 }, rubber: { roughness: 0.75, envMapIntensity: 0.4 },
      porcelain: { roughness: 0.14, envMapIntensity: 1.6, color: 0xc8c8c8 },
    }[n] || { roughness: 0.6 };
    const m = new THREE.MeshStandardMaterial({ ...base, ...P });
    m.userData.kind = n;
    return m;
  }

  indexProps() {
    const assign = (root, lib) => root.traverse((o) => {
      if (!o.isMesh) return;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      const out = mats.map((m) => lib[m.name] || lib[(m.name || '').replace(/\.\d+$/, '')] || this.mats.fallback);
      o.material = Array.isArray(o.material) ? out : out[0];
      o.castShadow = true; o.receiveShadow = true;
    });
    for (const file of ['props', 'growths', 'gibs']) {
      const scene = this.models[file]; if (!scene) continue;
      assign(scene, this.mats);
      for (const child of [...scene.children]) this.props[child.name] = child;
    }
  }

  // New instance of a static prop (shares geometry + materials). Returns null if unknown.
  makeProp(name) {
    const src = this.props[name]; if (!src) return null;
    const o = src.clone(true);
    o.position.set(0, 0, 0);
    return o;
  }

  // New skinned creature instance with its own materials.
  makeCreature(name) {
    const src = this.models[name]; if (!src) return null;
    const root = SkeletonUtils.clone(src);
    const mats = [];
    root.traverse((o) => {
      if (!o.isMesh) return;
      const hasColors = !!o.geometry.attributes.color;
      const conv = (m) => { const nm = (m.name || '').replace(/\.\d+$/, ''); const c = this.creatureMaterial(nm, hasColors); c.name = nm; mats.push(c); return c; };
      o.material = Array.isArray(o.material) ? o.material.map(conv) : conv(o.material);
      o.castShadow = true; o.receiveShadow = true; o.frustumCulled = false;
    });
    root.userData.materials = mats;
    return root;
  }
}
