"""Laser sidearm for the Kid. Static mesh, origin at the grip, barrel -Y (glTF +Z), top +Z.
Run: /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/blender/humanoids/gun.py
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, hlib
importlib.reload(hlib)
from hlib import *

NORENDER = 'norender' in sys.argv
reset()
parts = []
AXZ = 0.07          # barrel axis height
TIP = -0.318        # muzzle tip (y)


def part(bm, name, mat, paint, sharp=35):
    ob = mesh_from_bm(bm, name)
    shade_smooth(ob, sharp_angle=sharp)
    paint_part(ob, paint)
    set_mat(ob, mat)
    parts.append(ob)
    return ob


def gunmetal(co, nr, m, v):
    col = np.tile(np.array([0.15, 0.16, 0.18]), (len(co), 1))
    col *= (1 + 0.18 * nz(co, 40, (1, 2, 3)))[:, None]
    rust = smoothstep(0.25, 0.7, nz(co, 25, (5, 5, 5), 2))
    col = lerp(col, np.array([0.33, 0.18, 0.1]), 0.7 * rust)
    # salvaged panel: faded hazard orange on the right side of the receiver
    pan = (co[:, 0] < -0.024) & (co[:, 1] > -0.15) & (co[:, 1] < -0.02) & (co[:, 2] > 0.04) & (co[:, 2] < 0.1)
    col[pan] = lerp(col[pan], np.array([0.55, 0.3, 0.08]), 0.8)
    # top edge wear
    col *= (1 + 0.25 * np.clip(nr[:, 2], 0, 1) * (nz(co, 90) > 0.2))[:, None]
    return col

# ---------------------------------------------------------------- metal body
bm = bmesh.new()
bm_box(bm, (0, -0.045, 0.0675), (0.05, 0.25, 0.066), bevel=0.007)               # receiver
bm_box(bm, (0, -0.02, 0.105), (0.036, 0.16, 0.012), bevel=0.003)                 # top rail
bm_cyl(bm, (0, 0.078, AXZ), (0, 0.102, AXZ), 0.03, 0.026, seg=14)                # rear cap
bm_cyl(bm, (0, 0.102, AXZ), (0, 0.106, AXZ), 0.016, seg=10)
bm_cyl(bm, (0, -0.17, AXZ), (0, -0.292, AXZ), 0.025, seg=16)                     # barrel shroud
for k in range(4):                                                               # cooling collars
    y = -0.185 - k * 0.026
    bm_cyl(bm, (0, y, AXZ), (0, y - 0.01, AXZ), 0.031, seg=12)
bm_cyl(bm, (0, -0.292, AXZ), (0, -0.312, AXZ), 0.029, 0.036, seg=16)            # flared muzzle
for s in (1, -1):                                                                # side heat-sink fins
    for k in range(4):
        bm_box(bm, (s * 0.03, -0.12 + k * 0.022, 0.065), (0.012, 0.006, 0.05))
bm_box(bm, (0, -0.21, 0.035), (0.034, 0.075, 0.03), bevel=0.004)                 # under-barrel cell box
bm_box(bm, (0, 0.006, 0.026), (0.008, 0.05, 0.006))                              # trigger guard bottom
bm_box(bm, (0, -0.016, 0.0), (0.008, 0.006, 0.05))                               # trigger guard front
bm_box(bm, (0, 0.003, 0.018), (0.006, 0.008, 0.026), rot=(0.3, 0, 0))            # trigger
bm_box(bm, (0, -0.285, 0.1), (0.006, 0.012, 0.016))                              # front sight
bm_box(bm, (0, 0.06, 0.118), (0.024, 0.012, 0.014), bevel=0.002)                 # rear sight
for s in (1, -1):                                                                # bolts
    for y in (-0.15, 0.04):
        bm_sphere(bm, (s * 0.026, y, 0.05), 0.0045, u=6, v=3, rot=(0, math.pi / 2, 0))
# cell cage: end caps and rings
for y in (-0.135, 0.045):
    bm_cyl(bm, (0, y, 0.128), (0, y + (0.012 if y > 0 else -0.012), 0.128), 0.026, seg=12)
for k in range(4):
    y = -0.11 + k * 0.045
    bm_torus(bm, (0, y, 0.128), 0.022, 0.0035, axis=(0, 1, 0), seg=12, rseg=4)
for s in (1, -1):
    bm_cyl(bm, (s * 0.021, -0.135, 0.111), (s * 0.021, 0.045, 0.111), 0.004, seg=5)
part(bm, 'Body', 'metal', gunmetal)

# ---------------------------------------------------------------- glow: cell + emitter
bm = bmesh.new()
bm_cyl(bm, (0, -0.135, 0.128), (0, 0.045, 0.128), 0.0175, seg=12)
# subdivide length for coil banding
bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs((e.verts[0].co - e.verts[1].co).y) > 0.1], cuts=17)
bm_torus(bm, (0, TIP + 0.004, AXZ), 0.027, 0.0055, axis=(0, 1, 0), seg=16, rseg=5)
bm_cyl(bm, (0, -0.300, AXZ), (0, -0.306, AXZ), 0.022, seg=14)
bm_box(bm, (0.018, -0.21, 0.035), (0.002, 0.04, 0.006))                         # charge strip on cell box
part(bm, 'Glow', 'glow_cyan',
     lambda co, nr, m, v: np.where((co[:, 2] > 0.11)[:, None],
                                   lerp(np.array([0.25, 0.75, 0.95]), np.array([0.85, 1.0, 1.0]),
                                        (np.round((co[:, 1] + 0.135) / 0.01).astype(int) % 2).astype(float) * 0.9),
                                   np.tile(np.array([0.7, 1.0, 1.0]), (len(co), 1))), sharp=60)

# ---------------------------------------------------------------- rubber: grip, tape, cable
bm = bmesh.new()
bm_box(bm, (0, 0.012, -0.012), (0.03, 0.042, 0.105), rot=(-0.26, 0, 0), bevel=0.008)
for k, z in enumerate((-0.045, -0.015, 0.015)):
    y = 0.012 - z * math.tan(0.26)
    bm_box(bm, (0, y, z), (0.034, 0.046, 0.017), rot=(-0.26 + 0.05 * (-1) ** k, 0, 0.03 * (-1) ** k))
bm_box(bm, (0, 0.03, -0.066), (0.034, 0.05, 0.012), rot=(-0.26, 0, 0), bevel=0.003)     # butt pad
cable = bezier_pts((0, 0.104, AXZ - 0.012), (0.0, 0.17, 0.02), (0.018, 0.1, -0.13), (0.0, 0.035, -0.07), 16)
bm_tube(bm, cable, 0.0065, seg=6)
cable2 = bezier_pts((0.016, -0.17, 0.038), (0.04, -0.12, 0.0), (0.03, -0.06, 0.02), (0.02, -0.02, 0.045), 9)
bm_tube(bm, cable2, 0.004, seg=5)


def paint_rubber(co, nr, m, v):
    col = np.tile(np.array([0.16, 0.15, 0.14]), (len(co), 1))
    tape = (co[:, 2] < 0.03) & (co[:, 2] > -0.06) & (np.abs(co[:, 0]) > 0.0155)
    col[tape] = (0.36, 0.33, 0.24)              # dirty cloth tape
    col *= (1 + 0.2 * nz(co, 70))[:, None]
    return col

part(bm, 'Rubber', 'rubber', paint_rubber, sharp=50)

# ---------------------------------------------------------------- join
for o in bpy.context.view_layer.objects:
    o.select_set(False)
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
gun = parts[0]
gun.name = 'Gun'; gun.data.name = 'Gun'
finish_colors(gun, ao_strength=0.5, ao_dist=0.03, cav_strength=0.3, grime=(1.0, 0.1), height=1.0)
print('TRIS', tri_count(gun))

muzzle = link(bpy.data.objects.new('muzzle', None))
muzzle.empty_display_size = 0.02
muzzle.location = (0, TIP, AXZ)
muzzle.parent = gun

out = os.path.join(OUT_DIR, 'gun.glb')
export_glb([gun, muzzle], out)
glb_report(out)

if not NORENDER:
    gun.location = (0, 0, 0.3)       # lift for previews only (after export)
    render_studio('gun', 0.42, center_z=0.32, extra_dist=1.5)
    gun.location = (0, 0, 0.6)       # roughly held height
    render_game('gun', 0.5, center_z=0.6, zoom=12)
