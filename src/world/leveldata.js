import { Grid, FLOOR } from './grid.js';

// World layout. Rooms are carved in tile coordinates (1 tile = 2 m), everything else is in world metres.
// North is -Z (up the screen). The player starts in the south and works north.
export const ZONES = ['dock', 'corridor', 'assembly', 'warehouse', 'furnace', 'antechamber', 'boss', 'exit'];
export const Z = { DOCK: 0, CORRIDOR: 1, ASSEMBLY: 2, WAREHOUSE: 3, FURNACE: 4, ANTE: 5, BOSS: 6, EXIT: 7 };

export function buildGrid() {
  const g = new Grid(31, 87);
  // exit alcove + passage
  g.carve(13, 1, 16, 3, FLOOR.TREAD, Z.EXIT);
  g.carve(14, 4, 15, 5, FLOOR.TREAD, Z.EXIT);
  // boss chamber (octagon)
  g.carve(7, 6, 22, 21, FLOOR.PLATE, Z.BOSS);
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4 - i; j++) {
    g.fillVoid(7 + j, 6 + i, 7 + j, 6 + i); g.fillVoid(22 - j, 6 + i, 22 - j, 6 + i);
    g.fillVoid(7 + j, 21 - i, 7 + j, 21 - i); g.fillVoid(22 - j, 21 - i, 22 - j, 21 - i);
  }
  g.setFloorType(12, 11, 17, 16, FLOOR.GRATE);
  g.carve(14, 22, 15, 23, FLOOR.TREAD, Z.ANTE);
  // antechamber
  g.carve(11, 24, 18, 27, FLOOR.CONCRETE, Z.ANTE);
  g.carve(14, 28, 15, 29, FLOOR.TREAD, Z.FURNACE);
  // furnace hall
  g.carve(6, 30, 23, 41, FLOOR.CONCRETE, Z.FURNACE);
  g.setFloorType(12, 33, 17, 38, FLOOR.GRATE);
  g.setFloorType(6, 40, 23, 41, FLOOR.TREAD);
  g.carve(8, 42, 9, 43, FLOOR.TREAD, Z.WAREHOUSE);
  // warehouse
  g.carve(6, 44, 23, 53, FLOOR.CONCRETE, Z.WAREHOUSE);
  g.carve(20, 54, 21, 55, FLOOR.TREAD, Z.ASSEMBLY);
  // assembly hall + generator room
  g.carve(5, 56, 24, 67, FLOOR.PLATE, Z.ASSEMBLY);
  g.setFloorType(5, 61, 24, 62, FLOOR.TREAD);
  g.carve(25, 61, 25, 62, FLOOR.TREAD, Z.ASSEMBLY);
  g.carve(26, 59, 29, 64, FLOOR.TREAD, Z.ASSEMBLY);
  // corridor
  g.carve(14, 68, 15, 75, FLOOR.TREAD, Z.CORRIDOR);
  // loading dock + office
  g.carve(9, 76, 20, 84, FLOOR.PLATE, Z.DOCK);
  g.setFloorType(9, 82, 20, 84, FLOOR.CONCRETE);
  g.carve(8, 79, 8, 80, FLOOR.TREAD, Z.DOCK);
  g.carve(4, 77, 7, 81, FLOOR.CONCRETE, Z.DOCK);
  g.buildWalls();
  return g;
}

// Collision footprints: [halfWidth, halfDepth, mask, offsetZ]. mask 1 = blocks movement, 3 = also blocks shots/sight.
export const PROP_COLLIDERS = {
  crate_metal: [0.6, 0.6, 3], crate_small: [0.35, 0.25, 1], crate_stack: [1.2, 0.7, 3],
  barrel: [0.27, 0.27, 3], barrel_tipped: [0.5, 0.33, 1], gas_cylinder: [0.13, 0.13, 1],
  cart: [0.5, 0.8, 1], forklift: [0.65, 1.55, 3], workbench: [1.1, 0.45, 1], shelf_rack: [1.3, 0.4, 3],
  locker_row: [0.9, 0.25, 3], pipe_straight: [2, 0.2, 1], pipe_elbow: [0.4, 0.4, 1], pipe_valve: [0.6, 0.25, 1],
  pipe_bundle: [2, 0.25, 1, 0.3], conveyor: [2, 0.75, 3], conveyor_end: [0.6, 0.75, 3],
  machine_press: [1.6, 1.5, 3], machine_a: [1.75, 0.9, 3], machine_b: [1.1, 1.1, 3], control_console: [0.9, 0.45, 3],
  generator: [1.3, 0.75, 3], tank_vertical: [1.15, 1.15, 3], tank_horizontal: [2.25, 0.85, 3], furnace: [2.25, 1.75, 3],
  keycard_reader: [0.2, 0.2, 1], pillar: [0.42, 0.42, 3], railing: [1, 0.06, 1], lamp_work: [0.25, 0.25, 1],
  growth_mound: [0.6, 0.55, 1], electrical_box: [0.45, 0.15, 1, 0.15],
};

const P = (name, x, z, rot = 0, o = {}) => ({ name, x, z, rot: rot * Math.PI / 180, ...o });

export const PROPS = [
  // ───────── DOCK (x 18..42, z 152..170) ─────────
  P('forklift', 23, 163.5, 28), P('crate_stack', 38.3, 166.2, 8), P('crate_metal', 39.8, 163.3, 20), P('crate_small', 37.2, 163.2, -15),
  P('pallet', 35.6, 168.4, 5), P('barrel', 20.2, 168.6), P('barrel', 19.4, 167.4), P('barrel', 20.6, 166.9), P('barrel_tipped', 22.4, 157.6, 40),
  P('shelf_rack', 41.3, 157.5, -90), P('pillar', 24, 156), P('pillar', 36, 156),
  P('body_bag', 33.0, 157.4, 70), P('body_bag', 34.4, 158.7, 110), P('body_bag', 31.6, 158.9, 15),
  P('growth_mound', 35.6, 155.2, 0), P('growth_tendrils', 33.6, 157.2, 20), P('growth_pods_a', 36.4, 157.4, 100),
  P('door_frame', 30, 151, 0, { id: 'frame1' }), P('keycard_reader', 33.4, 153.1, 0, { id: 'reader1' }),
  
  P('pipe_bundle', 22.5, 152, 0), P('wall_vent', 38.5, 152, 0), P('wall_sign', 26.4, 152, 0), P('wall_fusebox', 34.6, 152, 0),
  P('wall_vent', 18, 155.5, 90, { id: 'ventDock' }), P('pipe_vertical', 18, 166, 90), P('pipe_vertical', 42, 162, -90),
  P('cable_floor_a', 27, 160, 0), P('cable_floor_b', 32.5, 166, 90), P('debris_a', 26, 154.2), P('debris_b', 40, 169, 60),
  P('cone', 27, 166.3), P('cone', 28.3, 165.2, 30), P('cart', 20.5, 160.5, -10), P('ladder', 41.6, 153, -90), 
  // office (x 8..16, z 154..164)
  P('control_console', 12, 154.9, 0, { id: 'officeConsole' }), P('locker_row', 15.6, 156.4, -90), P('workbench', 8.8, 160.5, 90),
  P('toolbox', 9, 163.2, 30), P('bucket', 14.8, 163.2), P('growth_pods_b', 10, 156.3, 0), P('body_bag', 13.2, 161.2, -30),
  P('wall_fusebox', 9.6, 154, 0), P('growth_tendrils', 12.5, 160, 90), P('crate_small', 15.2, 162.4, 20),

  // ───────── CORRIDOR (x 28..32, z 136..152) ─────────
  P('pipe_vertical', 28, 148, 90), P('pipe_vertical', 32, 143, -90), P('cable_floor_c', 30.2, 144.5, 90), P('debris_c', 29.2, 140.5, 30),
  P('lamp_wall', 28, 145.5, 90), P('growth_wall', 32, 140.6, -90), P('wall_vent', 32, 147.5, -90), P('lamp_wall', 32, 138, -90),
  P('growth_tendrils', 30.4, 141, 0),

  // ───────── ASSEMBLY HALL (x 10..50, z 112..136) ─────────
  P('conveyor', 14, 118, 0, { belt: 1 }), P('conveyor', 18, 118, 0, { belt: 1 }), P('conveyor', 22, 118, 0, { belt: 1 }), P('conveyor', 26, 118, 0, { belt: 1 }),
  P('conveyor_end', 28.6, 118, 0),
  P('conveyor_end', 19.4, 128.5, 180), P('conveyor', 22, 128.5, 0, { belt: -1 }), P('conveyor', 26, 128.5, 0, { belt: -1 }), P('conveyor', 30, 128.5, 0, { belt: -1 }),
  P('conveyor', 34, 128.5, 0, { belt: -1 }), P('conveyor', 38, 128.5, 0, { belt: -1 }), P('conveyor_end', 40.6, 128.5, 0),
  P('chain_hook', 24, 128.5, 0, { sway: 1 }), P('chain_hook', 30, 128.5, 90, { sway: 1 }), P('chain_hook', 36, 128.5, 0, { sway: 1 }),
  P('chain_hook', 16, 118, 90, { sway: 1 }), P('chain_hook', 22, 118, 0, { sway: 1 }),
  P('machine_a', 11, 124, 90), P('machine_b', 12.2, 131.2, 0), P('machine_press', 46.6, 132, -90, { id: 'press1' }),
  P('machine_a', 34, 113, 0), P('tank_vertical', 12.4, 114.4), P('tank_horizontal', 21, 113.2, 0), P('control_console', 43.5, 126.5, 200),
  P('crate_metal', 47.6, 115.2, 10), P('barrel', 48.6, 117.4), P('barrel', 47.8, 118.3), P('pallet', 45.6, 117.6, 20), P('crate_small', 45.8, 117.5, 40),
  P('pillar', 24, 123.2), P('pillar', 36, 123.2),
  P('pipe_bundle', 15.5, 112, 0), P('pipe_bundle', 28, 112, 0), P('vent_fan', 47, 112, 0, { id: 'fan1' }),
  P('wall_vent', 10, 119.5, 90, { id: 'ventAsmA' }), P('wall_vent', 10, 128.6, 90, { id: 'ventAsmB' }), P('wall_sign', 38.4, 112, 0),
  P('door_frame', 42, 111, 0, { id: 'frame2' }),
  
  P('growth_pods_b', 15, 134.2, 40), P('growth_mound', 48.2, 127.3, 0), P('cocoon_hanging', 27.5, 115.5, 0, { y: 6.2 }), P('cocoon_hanging', 34.5, 133.5, 0, { y: 6.4 }),
  P('growth_tendrils', 16, 132.5, 0), P('growth_wall', 24.5, 112, 0),
  P('cable_floor_a', 44, 121, 45), P('cable_floor_b', 23, 133, 0), P('debris_a', 33, 119, 0), P('debris_c', 17, 126, 80), P('cart', 32.5, 124.5, 70),
  P('body_bag', 20.6, 121.6, 60), P('duct', 40, 134.4, 0), P('gas_cylinder', 10.6, 116.6), P('gas_cylinder', 11.1, 117.2), 
  P('shelf_rack', 49.3, 120, -90), P('locker_row', 16.5, 135.6, 180),
  // generator room (x 52..60, z 118..130)
  P('generator', 55.6, 120.2, 0, { id: 'generator' }), P('electrical_box', 60, 125.8, -90, { id: 'breaker' }), P('tank_horizontal', 55.5, 128.8, 0),
  P('gas_cylinder', 52.6, 119), P('gas_cylinder', 53.2, 119.4), P('cable_coil', 53.6, 126.4), P('cable_floor_c', 56, 124, 0),
  P('wall_fusebox', 58.8, 118, 0), P('lamp_wall', 60, 121.5, -90), P('toolbox', 58.6, 122.2, 50),

  // ───────── WAREHOUSE (x 12..48, z 88..108) ─────────
  ...[18, 24, 30, 36].flatMap((x) => [
    P('shelf_rack', x, 92.2, 90), P('shelf_rack', x, 94.9, 90), P('shelf_rack', x, 101.6, 90), P('shelf_rack', x, 104.3, 90),
  ]),
  P('crate_stack', 45.8, 91.5, 80), P('crate_stack', 46, 101.5, 95), P('forklift', 43, 96.5, -25), P('crate_metal', 13.2, 106.6, 5), P('crate_metal', 13.4, 94, 0),
  P('pallet', 21, 107, 10), P('barrel', 27, 107.2), P('barrel', 27.9, 106.8), P('barrel_tipped', 33, 89.6, -20), P('crate_small', 21.4, 89.4, 20),
  P('body_bag', 21, 97.6, 80), P('body_bag', 33.2, 99.3, 100), P('body_bag', 39.5, 93, 10), P('body_bag', 15, 100.5, -10),
  P('cocoon_hanging', 21, 99.6, 0, { y: 6.3 }), P('cocoon_hanging', 33, 96.6, 0, { y: 6.6 }), P('cocoon_hanging', 27, 106.4, 0, { y: 6.2 }), P('cocoon_hanging', 39.4, 99, 0, { y: 6.5 }),
  P('cocoon_hanging', 15, 96.8, 0, { y: 6.4 }),
  P('growth_tendrils', 27, 98, 0), P('growth_tendrils', 39, 104, 90), P('growth_pods_a', 14, 98.2, 0), P('growth_pods_b', 40.2, 106.4, 200), P('growth_wall', 30, 88, 0),
  P('growth_mound', 46.2, 106.2, 0), P('growth_wall', 12, 102, 90),
  P('lamp_wall', 12, 97, 90), P('lamp_wall', 48, 98, -90), P('lamp_wall', 24, 88, 0), P('lamp_wall', 38, 88, 0),
  P('door_frame', 18, 87, 0, { id: 'frameE' }), P('debris_b', 30, 98.2, 0), P('debris_a', 42, 105, 30), P('cart', 15.5, 91, 80), P('ladder', 47.6, 95, -90),
  P('pipe_vertical', 48, 104.5, -90), P('wall_sign', 42, 88, 0),

  // ───────── FURNACE HALL (x 12..48, z 60..84) ─────────
  P('furnace', 19.5, 61.8, 0, { id: 'furnN1' }), P('furnace', 40.5, 61.8, 0, { id: 'furnN2' }),
  P('furnace', 13.8, 72, 90, { id: 'furnW' }), P('furnace', 46.2, 72, -90, { id: 'furnE' }),
  P('crucible', 19.5, 66.6, 0, { sway: 0.4 }), P('crucible', 18.4, 72, 0, { sway: 0.4 }), P('crucible', 41.6, 72, 0, { sway: 0.4 }),
  P('pillar', 22, 64.6), P('pillar', 38, 64.6), P('pillar', 22, 80.5), P('pillar', 38, 80.5),
  P('railing', 24, 68, 90), P('railing', 24, 76, 90), P('railing', 36, 68, 90), P('railing', 36, 76, 90),
  P('tank_vertical', 46.4, 81.8), P('machine_b', 13.4, 78.6, 0), P('tank_horizontal', 44, 61.2, 0, { skip: 1 }),
  P('pipe_straight', 14.2, 65.6, 90), P('pipe_valve', 14.2, 62.6, 90), P('pipe_straight', 45.8, 65.6, 90),
  P('barrel', 26.4, 61.2), P('barrel', 27.2, 61.9), P('barrel', 33.4, 61.3), P('gas_cylinder', 47.3, 77.2), P('gas_cylinder', 46.8, 77.8),
  P('cart', 27, 82.2, 20), P('debris_a', 40, 76, 0), P('debris_c', 20, 68, 60), P('debris_b', 33, 81, 100),
  P('door_frame', 30, 59, 0, { id: 'frame3' }), P('growth_mound', 44.2, 83, 0), P('growth_tendrils', 42, 81, 30), P('growth_pods_a', 14, 83, 20),
  P('chain_hook', 18, 76, 30, { sway: 1 }), P('chain_hook', 42, 67, 0, { sway: 1 }), P('cable_floor_a', 40, 70, 100), P('cable_floor_c', 20, 74, 0),
  P('lamp_wall', 12, 66, 90), P('lamp_wall', 48, 78, -90), P('crate_metal', 16.6, 67.2, 15), P('crate_small', 43.6, 66.6, 30),

  // ───────── ANTECHAMBER (x 22..38, z 48..56) ─────────
  P('growth_wall', 26.2, 48, 0), P('growth_wall', 34, 48, 0), P('growth_mound', 23.6, 50), P('growth_pods_a', 36.4, 50.4, 60), P('growth_pods_b', 24, 54.6, 0),
  P('growth_tendrils', 30, 51.5, 0), P('growth_tendrils', 34, 53.5, 120), P('cocoon_hanging', 25.2, 53, 0, { y: 6.2 }), P('cocoon_hanging', 35.4, 54.2, 0, { y: 6.5 }),
  P('cocoon_hanging', 27.4, 50.2, 0, { y: 6.8 }), P('cocoon_hanging', 33, 49.8, 0, { y: 6.4 }),
  P('lamp_work', 36.6, 55, 215), P('body_bag', 28, 54.6, 85), P('door_frame', 30, 47, 0, { id: 'frame4' }), P('crate_small', 37, 53, 10), P('cable_floor_b', 30, 53, 90),

  // ───────── BOSS CHAMBER (x 14..46, z 12..44, centre 30,28) ─────────
  P('pillar', 21.5, 19.5), P('pillar', 38.5, 19.5), P('pillar', 21.5, 36.5), P('pillar', 38.5, 36.5),
  P('growth_mound', 16.2, 25, 0), P('growth_mound', 43.8, 31, 0), P('growth_mound', 24, 13.6, 0), P('growth_mound', 37, 42.4, 0),
  P('growth_pods_a', 17, 32, 0), P('growth_pods_b', 43, 23, 90), P('growth_pods_a', 35, 14, 180), P('growth_pods_b', 23, 42, 0), P('growth_pods_a', 42, 38, 40),
  P('growth_tendrils', 19, 28, 0), P('growth_tendrils', 41, 27, 180), P('growth_tendrils', 30, 15.5, 90), P('growth_tendrils', 30, 41, 270),
  P('growth_wall', 26, 12, 0), P('growth_wall', 34.2, 12, 0), P('growth_wall', 14, 26, 90), P('growth_wall', 46, 30, -90), P('growth_wall', 14, 31, 90), P('growth_wall', 46, 24, -90),
  P('cocoon_hanging', 18.5, 22, 0, { y: 6.6 }), P('cocoon_hanging', 41.5, 34.5, 0, { y: 6.3 }), P('cocoon_hanging', 25, 16, 0, { y: 6.8 }), P('cocoon_hanging', 36, 16.5, 0, { y: 6.4 }),
  P('cocoon_hanging', 18, 35, 0, { y: 6.5 }), P('cocoon_hanging', 42.5, 20.5, 0, { y: 6.7 }),
  P('chain_hook', 26, 20, 0, { sway: 1 }), P('chain_hook', 34.5, 36, 90, { sway: 1 }), P('cable_floor_a', 22, 26, 20), P('cable_floor_b', 38, 31, 200), P('cable_floor_c', 28, 38.5, 90),
  P('cable_floor_a', 35, 19, 130), P('debris_a', 26, 40, 0), P('debris_b', 36, 24, 0), P('debris_c', 19.6, 38.8, 0),
  P('door_frame', 30, 11, 0, { id: 'frameX' }), P('tank_vertical', 16, 18.6, 0, { skip: 1 }),
  // exit alcove (x 26..34, z 2..8)
  P('crate_small', 27, 3, 20), P('cable_floor_c', 31, 5.5, 0),
];

// Doors: 4 m wide shutters. They block while closed.
export const DOORS = [
  { id: 'door1', x: 30, z: 151, state: 'locked' },   // keycard
  { id: 'door2', x: 42, z: 111, state: 'locked' },   // needs power + clear
  { id: 'doorE', x: 18, z: 87, state: 'open' },      // furnace arena entry (slams shut)
  { id: 'door3', x: 30, z: 59, state: 'locked' },    // opens when arena cleared
  { id: 'door4', x: 30, z: 47, state: 'closed' },    // boss door (opens on approach)
  { id: 'doorX', x: 30, z: 11, state: 'locked' },    // exit
];

// Fixed light fixtures. The renderer keeps a small pool of real lights and assigns them to the nearest fixtures.
// kind: 'spot' (downward pool) | 'point'. power: needs the generator. flicker: 0 none, 1 gentle, 2 broken, 3 strobe.
const L = (kind, x, y, z, color, intensity, o = {}) => ({ kind, x, y, z, color, intensity, range: 16, angle: 0.62, flicker: 0, on: true, ...o });
const COOL = 0xb2d2f2, COLD = 0x98c0ea, RED = 0xff2a1a, AMBER = 0xffa040, FIRE = 0xff6a18, GREEN = 0x58ff9a, CYAN = 0x40e0ff, WHITE = 0xe8f1ff;
export const LIGHTS = [
  // dock
  L('spot', 30, 7.5, 164, COOL, 322, { flicker: 1, zone: Z.DOCK }),
  L('spot', 33.2, 7.5, 157.6, COLD, 266, { flicker: 2, zone: Z.DOCK }),
  L('point', 30, 4.3, 152.4, RED, 14, { range: 9, zone: Z.DOCK, id: 'beacon1' }),
  L('point', 12, 1.5, 155.8, GREEN, 5, { range: 7, zone: Z.DOCK, flicker: 1 }),
  L('spot', 12, 6.5, 159.5, COLD, 99, { zone: Z.DOCK, flicker: 2, angle: 0.5 }),
  // corridor
  L('point', 28.6, 2.8, 145.5, RED, 9, { range: 8, zone: Z.CORRIDOR }),
  L('spot', 30, 7, 138.4, COLD, 186, { zone: Z.CORRIDOR, flicker: 2, angle: 0.4, id: 'corridorScare' }),
  // assembly hall
  L('spot', 18, 7.5, 123, COOL, 347, { zone: Z.ASSEMBLY, power: true }),
  L('spot', 30, 7.5, 122.5, COOL, 347, { zone: Z.ASSEMBLY, power: true, flicker: 1 }),
  L('spot', 42, 7.5, 122, COOL, 347, { zone: Z.ASSEMBLY, power: true }),
  L('spot', 30, 7.5, 133, COLD, 186, { zone: Z.ASSEMBLY, flicker: 2 }),
  L('point', 42, 4.3, 112.4, RED, 14, { range: 9, zone: Z.ASSEMBLY, id: 'beacon2' }),
  L('point', 13, 2.2, 124, AMBER, 5, { range: 6, zone: Z.ASSEMBLY, power: true }),
  L('point', 55.6, 1.6, 121.4, CYAN, 7, { range: 7, zone: Z.ASSEMBLY, id: 'genGlow', flicker: 1 }),
  L('point', 59.4, 2.6, 121.5, RED, 8, { range: 8, zone: Z.ASSEMBLY, id: 'genLamp' }),
  // warehouse
  L('point', 12.6, 2.8, 97, RED, 7, { range: 9, zone: Z.WAREHOUSE }),
  L('point', 47.4, 2.8, 98, RED, 7, { range: 9, zone: Z.WAREHOUSE }),
  L('point', 24, 2.8, 88.6, RED, 6, { range: 8, zone: Z.WAREHOUSE, flicker: 2 }),
  L('point', 38, 2.8, 88.6, RED, 6, { range: 8, zone: Z.WAREHOUSE }),
  L('point', 18, 4.3, 88.2, AMBER, 9, { range: 8, zone: Z.WAREHOUSE, id: 'beaconE' }),
  // furnace hall
  L('point', 19.5, 1.6, 65.2, FIRE, 60, { range: 15, zone: Z.FURNACE, flicker: 1, fire: true }),
  L('point', 40.5, 1.6, 65.2, FIRE, 60, { range: 15, zone: Z.FURNACE, flicker: 1, fire: true }),
  L('point', 17.2, 1.6, 72, FIRE, 60, { range: 15, zone: Z.FURNACE, flicker: 1, fire: true }),
  L('point', 42.8, 1.6, 72, FIRE, 60, { range: 15, zone: Z.FURNACE, flicker: 1, fire: true }),
  L('spot', 30, 8, 72, COLD, 260, { zone: Z.FURNACE, angle: 0.75 }),
  L('point', 40.5, 2.2, 67, FIRE, 22, { range: 9, zone: Z.FURNACE, fire: true }),
  L('point', 30, 4.3, 60.4, RED, 14, { range: 9, zone: Z.FURNACE, id: 'beacon3' }),
  // antechamber
  L('spot', 30, 7, 52.5, COLD, 161, { zone: Z.ANTE, flicker: 2, angle: 0.55 }),
  L('point', 36.2, 1.8, 54.4, WHITE, 16, { range: 9, zone: Z.ANTE }),
  // boss
  L('spot', 30, 10, 23, COLD, 558, { zone: Z.BOSS, angle: 0.5, id: 'bossKey' }),
  L('spot', 30, 10, 34, COLD, 310, { zone: Z.BOSS, angle: 0.7, id: 'bossFill', on: false }),
  L('point', 20, 3, 28, RED, 0, { range: 16, zone: Z.BOSS, id: 'bossRedA' }),
  L('point', 40, 3, 28, RED, 0, { range: 16, zone: Z.BOSS, id: 'bossRedB' }),
  L('point', 30, 1.0, 28, FIRE, 0, { range: 14, zone: Z.BOSS, id: 'bossPit', fire: true }),
  // exit
  L('spot', 30, 7.5, 5, WHITE, 0, { zone: Z.EXIT, id: 'exitLight', angle: 0.7 }),
  L('point', 30, 2, 6, WHITE, 0, { range: 14, zone: Z.EXIT, id: 'exitGlow' }),
];

export const PICKUPS = [
  { kind: 'energy', x: 38.4, z: 161 }, { kind: 'key', x: 12, z: 157.3, id: 'keycard' },
  { kind: 'health', x: 47.4, z: 113.6 }, { kind: 'energy', x: 13.2, z: 134.6 }, { kind: 'energy', x: 57.6, z: 123.4 },
  { kind: 'health', x: 44.4, z: 105.6 }, { kind: 'energy', x: 14, z: 90 }, { kind: 'energy', x: 40.4, z: 100.6 },
  { kind: 'energy', x: 41, z: 82.6 }, { kind: 'health', x: 15.4, z: 62 }, { kind: 'energy', x: 33.6, z: 62.4 },
  { kind: 'health', x: 25, z: 52 }, { kind: 'energy', x: 35, z: 52 }, { kind: 'energy', x: 33.4, z: 54.6 }, { kind: 'health', x: 27, z: 49.6 },
];

export const CHECKPOINTS = [
  { id: 0, zone: Z.DOCK, x: 30, z: 167.2, face: Math.PI },
  { id: 1, zone: Z.ASSEMBLY, x: 30, z: 134.6, face: Math.PI },
  { id: 2, zone: Z.WAREHOUSE, x: 42, z: 106.8, face: Math.PI },
  { id: 3, zone: Z.FURNACE, x: 18, z: 83.6, face: Math.PI },
  { id: 4, zone: Z.ANTE, x: 30, z: 54.6, face: Math.PI },
];

export const START = CHECKPOINTS[0];
