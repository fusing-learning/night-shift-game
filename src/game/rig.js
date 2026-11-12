import * as THREE from 'three';

const _q = new THREE.Quaternion(), _q2 = new THREE.Quaternion(), _v = new THREE.Vector3(), _v2 = new THREE.Vector3();
const _m = new THREE.Matrix4();
export const AX = new THREE.Vector3(1, 0, 0), AY = new THREE.Vector3(0, 1, 0), AZ = new THREE.Vector3(0, 0, 1);

// Procedural animation helper for skinned GLBs.
// All poses are expressed as rotations in MODEL space (model faces +Z, Y up, left = +X) relative to the rest pose,
// so animation code never depends on how the bones were rolled in Blender.
export class Rig {
  constructor(root) {
    this.root = root; this.bones = {}; this.ok = false;
    root.updateWorldMatrix(true, true);
    const inv = _m.copy(root.matrixWorld).invert();
    const rootQ = root.getWorldQuaternion(new THREE.Quaternion()).invert();
    root.traverse((o) => {
      if (!o.isBone) return;
      const b = { bone: o, name: o.name, restLocalQ: o.quaternion.clone(), restLocalP: o.position.clone(), restScale: o.scale.clone() };
      b.restModelQ = rootQ.clone().multiply(o.getWorldQuaternion(new THREE.Quaternion()));
      b.pos = o.getWorldPosition(new THREE.Vector3()).applyMatrix4(inv);   // rest head position in model space
      b.total = new THREE.Quaternion();                                     // accumulated model-space delta this frame
      this.bones[o.name] = b;
    });
    for (const b of Object.values(this.bones)) {
      const p = b.bone.parent;
      b.parent = p && p.isBone ? this.bones[p.name] : null;
      b.parentRestModelQInv = (p ? rootQ.clone().multiply(p.getWorldQuaternion(new THREE.Quaternion())) : new THREE.Quaternion()).invert();
      // direction toward first child bone (rest, model space)
      const child = b.bone.children.find((c) => c.isBone);
      if (child) { const cp = this.bones[child.name].pos; b.dir = cp.clone().sub(b.pos); b.len = b.dir.length(); b.dir.normalize(); }
      else { b.dir = new THREE.Vector3(0, 1, 0); b.len = 0; }
    }
    this.ok = Object.keys(this.bones).length > 0;
    this.scaleRef = 1;
  }
  has(name) { return !!this.bones[name]; }
  // Rotate bone by q (model-space axes, carried along by its parent's pose).
  rel(name, q) {
    const b = this.bones[name]; if (!b) return;
    b.bone.quaternion.copy(b.parentRestModelQInv).multiply(q).multiply(b.restModelQ);
    if (b.parent) b.total.copy(b.parent.total).multiply(q); else b.total.copy(q);
  }
  // Convenience: euler angles about model X (pitch forward/back), Y (yaw), Z (roll).
  rot(name, x = 0, y = 0, z = 0) {
    _q.setFromEuler(_e.set(x, y, z, 'YXZ')); this.rel(name, _q);
  }
  // Set the bone's TOTAL model-space delta (ignores parent's pose). Parent must have been posed first this frame.
  total(name, D) {
    const b = this.bones[name]; if (!b) return;
    if (b.parent) _q2.copy(b.parent.total).invert().multiply(D); else _q2.copy(D);
    b.bone.quaternion.copy(b.parentRestModelQInv).multiply(_q2).multiply(b.restModelQ);
    b.total.copy(D);
  }
  // Point the bone along a model-space direction.
  aim(name, dir) {
    const b = this.bones[name]; if (!b) return;
    _q.setFromUnitVectors(b.dir, _v.copy(dir).normalize()); this.total(name, _q);
  }
  offset(name, x, y, z) { const b = this.bones[name]; if (!b) return; b.bone.position.copy(b.restLocalP); _v.set(x, y, z).applyQuaternion(b.parentRestModelQInv); b.bone.position.add(_v); }
  scale(name, s) { const b = this.bones[name]; if (b) b.bone.scale.copy(b.restScale).multiplyScalar(s); }
  reset(name) { const b = this.bones[name]; if (!b) return; b.bone.quaternion.copy(b.restLocalQ); b.total.identity(); }
  resetAll() { for (const b of Object.values(this.bones)) { b.bone.quaternion.copy(b.restLocalQ); b.bone.position.copy(b.restLocalP); b.total.identity(); } }

  // Analytic two-bone IK in model space. `shift` = model-space translation applied to the chain root (e.g. body bob).
  // The parent of `a` must have an identity total delta (or pass it via parentTotal).
  ik(a, bName, endName, target, pole, shift) {
    const A = this.bones[a], B = this.bones[bName], E = this.bones[endName]; if (!A || !B || !E) return;
    const origin = _v.copy(A.pos); if (shift) origin.add(shift);
    const L1 = A.len, L2 = B.len || E.pos.distanceTo(B.pos);
    const d = _v2.copy(target).sub(origin); let dist = d.length();
    dist = Math.min(Math.max(dist, Math.abs(L1 - L2) + 1e-3), L1 + L2 - 1e-3); d.normalize();
    const along = (L1 * L1 - L2 * L2 + dist * dist) / (2 * dist);
    const h = Math.sqrt(Math.max(0, L1 * L1 - along * along));
    // pole perpendicular to d
    const pp = _p.copy(pole).addScaledVector(d, -pole.dot(d)); if (pp.lengthSq() < 1e-6) pp.set(0, 1, 0); pp.normalize();
    const knee = _k.copy(origin).addScaledVector(d, along).addScaledVector(pp, h);
    const u1 = _u1.copy(knee).sub(origin).normalize();
    const tip = _t.copy(origin).addScaledVector(d, dist);
    const u2 = _u2.copy(tip).sub(knee).normalize();
    const pt = A.parent ? A.parent.total : _ident;
    // account for a rotated parent: express desired directions in the parent's rest-aligned frame
    _q.setFromUnitVectors(A.dir, u1); this.total(a, _q);
    _q.setFromUnitVectors(B.dir, u2); this.total(bName, _q);
    void pt;
  }
}
const _e = new THREE.Euler(), _p = new THREE.Vector3(), _k = new THREE.Vector3(), _t = new THREE.Vector3(), _u1 = new THREE.Vector3(), _u2 = new THREE.Vector3();
const _ident = new THREE.Quaternion();
export const damp = (a, b, k, dt) => a + (b - a) * (1 - Math.exp(-k * dt));
export const angDiff = (a, b) => { let d = (b - a) % (Math.PI * 2); if (d > Math.PI) d -= Math.PI * 2; if (d < -Math.PI) d += Math.PI * 2; return d; };
