// Global tuning. All distances in metres, times in seconds.
export const CELL = 2;        // tile size
export const SUB = 4;         // collision sub-cells per tile (0.5 m)

export const CAM = {
  fov: 30,
  pitch: 62 * Math.PI / 180,  // above horizontal
  dist: 23,
  bossDist: 31,
  lead: 2.2,                  // how far the camera leans toward the aim point
  lag: 5.0,
};

export const PLAYER = {
  radius: 0.34,
  speed: 4.3,
  hp: 100,
  dodgeSpeed: 11.5,
  dodgeTime: 0.32,
  dodgeIFrames: 0.30,
  dodgeCooldown: 0.85,
  hurtIFrames: 0.55,
};

export const GUN = {
  energyMax: 100,
  shotCost: 5,
  regenDelay: 1.1,
  regenRate: 7,
  fireInterval: 0.17,
  heatPerShot: 0.105,
  coolRate: 0.55,
  overheatLock: 1.5,
  damage: 18,
  speed: 40,
  range: 30,
};

export const BLADE = {
  damage: 42,
  range: 2.15,
  arc: 2.3,            // radians total
  cooldown: 0.46,
  swingTime: 0.22,
  energyOnHit: 5,
  knockback: 5.5,
};

export const DEBUG = new URLSearchParams(location.search);
