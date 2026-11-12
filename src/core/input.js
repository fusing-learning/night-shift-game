import * as THREE from 'three';

// Keyboard + mouse. Mouse position is projected onto the ground plane to get a world-space aim point.
export class Input {
  constructor(canvas, camera) {
    this.canvas = canvas; this.camera = camera;
    this.keys = new Set(); this.pressed = new Set();
    this.mouse = new THREE.Vector2(0, -0.3); this.buttons = 0; this.clicked = 0;
    this.aim = new THREE.Vector3();
    this.ray = new THREE.Raycaster(); this.plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -0.6);
    this.enabled = true; this.anyKey = false; this.aimOverride = null;
    addEventListener('keydown', (e) => {
      if (e.repeat) return;
      this.keys.add(e.code); this.pressed.add(e.code); this.anyKey = true;
      if (['Space', 'Tab', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code)) e.preventDefault();
    });
    addEventListener('keyup', (e) => this.keys.delete(e.code));
    addEventListener('blur', () => { this.keys.clear(); this.buttons = 0; });
    addEventListener('mousemove', (e) => { this.mouse.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1); });
    addEventListener('mousedown', (e) => { this.buttons |= (1 << e.button); this.clicked |= (1 << e.button); this.anyKey = true; });
    addEventListener('mouseup', (e) => { this.buttons &= ~(1 << e.button); });
    addEventListener('contextmenu', (e) => e.preventDefault());
  }
  down(code) { return this.keys.has(code); }
  hit(code) { return this.pressed.has(code); }
  get fire() { return (this.buttons & 1) !== 0; }
  get melee() { return (this.clicked & 4) !== 0 || this.pressed.has('Space'); }
  moveAxis(out) {
    let x = 0, z = 0;
    if (this.down('KeyW') || this.down('ArrowUp')) z -= 1;
    if (this.down('KeyS') || this.down('ArrowDown')) z += 1;
    if (this.down('KeyA') || this.down('ArrowLeft')) x -= 1;
    if (this.down('KeyD') || this.down('ArrowRight')) x += 1;
    const l = Math.hypot(x, z) || 1; out.x = x / l; out.z = z / l; return x !== 0 || z !== 0;
  }
  updateAim() {
    if (this.aimOverride) { this.aim.set(this.aimOverride.x, 0.6, this.aimOverride.z); return; }
    this.ray.setFromCamera(this.mouse, this.camera);
    this.ray.ray.intersectPlane(this.plane, this.aim);
  }
  endFrame() { this.pressed.clear(); this.clicked = 0; this.anyKey = false; }
}
