import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { GTAOPass } from 'three/addons/postprocessing/GTAOPass.js';

// Final grade: tone map, cold tint, vignette, grain, chromatic aberration, damage + fades.
const FinalShader = {
  uniforms: {
    tDiffuse: { value: null }, uTime: { value: 0 }, uExposure: { value: 1.0 },
    uVignette: { value: 1.0 }, uGrain: { value: 0.022 }, uAberration: { value: 0.0018 },
    uDamage: { value: 0 }, uLowHealth: { value: 0 }, uFade: { value: 0 }, uFadeColor: { value: new THREE.Color(0, 0, 0) },
    uTint: { value: new THREE.Color(0.78, 1.0, 1.1) }, uSaturation: { value: 0.86 }, uAspect: { value: 1.6 },
    uLetterbox: { value: 0 }, uPulse: { value: 0 },
  },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
  fragmentShader: /* glsl */`
    precision highp float;
    uniform sampler2D tDiffuse; uniform float uTime, uExposure, uVignette, uGrain, uAberration, uDamage, uLowHealth, uFade, uSaturation, uAspect, uLetterbox, uPulse;
    uniform vec3 uFadeColor, uTint; varying vec2 vUv;
    vec3 aces(vec3 x){ return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14), 0.0, 1.0); }
    float hash(vec2 p){ vec3 p3 = fract(vec3(p.xyx)*0.1031); p3 += dot(p3, p3.yzx+33.33); return fract((p3.x+p3.y)*p3.z); }
    void main(){
      vec2 c = vUv - 0.5; float r2 = dot(c*vec2(1.0, 1.0/uAspect*1.25), c*vec2(1.0, 1.0/uAspect*1.25));
      float ab = uAberration * (0.25 + r2*7.0) * (1.0 + uDamage*4.0 + uPulse*3.0);
      vec3 col;
      col.r = texture2D(tDiffuse, vUv + c*ab).r;
      col.g = texture2D(tDiffuse, vUv).g;
      col.b = texture2D(tDiffuse, vUv - c*ab).b;
      col *= uExposure;
      col = aces(col);
      float l = dot(col, vec3(0.2126, 0.7152, 0.0722));
      float sat = uSaturation * (1.0 - uLowHealth*0.55);
      col = mix(vec3(l), col, sat);
      // cold tint, strongest in the shadows; keep hot colours hot
      col *= mix(uTint, vec3(1.0), smoothstep(0.0, 0.75, l));
      col += vec3(0.0, 0.004, 0.009) * (1.0 - l);
      // vignette
      float v = smoothstep(0.95, 0.12, r2 * 2.3 * uVignette);
      col *= mix(0.04, 1.0, v);
      // damage + low health: red creeping in from the edges
      float edge = smoothstep(0.13, 0.5, r2);
      col = mix(col, vec3(0.55, 0.0, 0.0), edge * clamp(uDamage*0.85 + uLowHealth*(0.28+0.12*sin(uTime*5.0)), 0.0, 0.9));
      // film grain
      float g = hash(gl_FragCoord.xy + fract(uTime*7.31)*917.0) - 0.5;
      col += g * uGrain * (0.35 + 0.65*smoothstep(0.0, 0.25, l));
      col = max(col, 0.0);
      col = mix(col, uFadeColor, uFade);
      float lb = step(abs(c.y), 0.5 - uLetterbox);
      col *= lb;
      // linear -> sRGB
      col = mix(col*12.92, 1.055*pow(col, vec3(1.0/2.4)) - 0.055, step(0.0031308, col));
      gl_FragColor = vec4(col, 1.0);
    }`,
};

export class Gfx {
  constructor(canvas) {
    const r = this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance', stencil: false });
    r.shadowMap.enabled = true; r.shadowMap.type = THREE.PCFShadowMap;
    r.toneMapping = THREE.NoToneMapping;
    r.outputColorSpace = THREE.LinearSRGBColorSpace;   // the final pass does the sRGB encode itself
    r.setClearColor(0x000000, 1);
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x03070c, 0.022);
    this.camera = new THREE.PerspectiveCamera(30, 1, 1, 120);
    this.quality = 1;
    const rt = new THREE.WebGLRenderTarget(4, 4, { type: THREE.HalfFloatType, samples: 4 });
    this.composer = new EffectComposer(r, rt);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    if (!new URLSearchParams(location.search).has('noao')) {
      this.ao = new GTAOPass(this.scene, this.camera, 256, 256);
      this.ao.updateGtaoMaterial({ radius: 0.7, distanceExponent: 1.4, thickness: 1.4, scale: 1.25, samples: 12, screenSpaceRadius: false });
      this.ao.blendIntensity = 1.0;
      this.composer.addPass(this.ao);
    }
    this.bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.5, 0.7, 1.0);
    this.composer.addPass(this.bloom);
    this.final = new ShaderPass(FinalShader);
    this.composer.addPass(this.final);
    this.u = this.final.uniforms;
    this.resize();
    addEventListener('resize', () => this.resize());
  }
  resize() {
    const w = innerWidth, h = innerHeight;
    const pr = Math.min(devicePixelRatio || 1, 2) * this.quality;
    this.renderer.setPixelRatio(pr); this.renderer.setSize(w, h, false);
    this.composer.setPixelRatio(pr); this.composer.setSize(w, h);
    this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
    this.u.uAspect.value = w / h;
  }
  setQuality(q) { this.quality = q; this.resize(); }
  render(time) {
    this.u.uTime.value = time;
    this.composer.render();
  }
}
