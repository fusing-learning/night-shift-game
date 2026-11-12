"""Pipes, ducts, cables, chain, fan."""
import math
from mathutils import Vector, Matrix
from lib import *


def pipe_flange_x(P, x, z, r, y=0.0, sgn=1):
    flange(P, (x, y, z), 'x', r * 1.45, 0.045, nb=8, boltr=0.02, rb=r * 1.15)


def floor_bracket(P, x, y, z, r, axis='x'):
    """U-strap bracket from floor to a pipe whose axis (along `axis`) is at height z."""
    if axis == 'x':
        P.box((x, y, z - r - 0.0), (0.09, r * 2 + 0.06, 0.03), DK, bev=0.006) if False else None
        P.cyl((x, y, z), r + 0.012, 0.09, 'x', DK, seg=20, bev=0.006)
        for sy in (-1, 1):
            P.box((x, y + sy * (r + 0.03), z / 2 - 0.0), (0.07, 0.035, z), DK, bev=0.006)
            P.box((x, y + sy * (r + 0.03), z + 0.0), (0.09, 0.05, 0.03), DK, bev=0.006)
        P.box((x, y, 0.02), (0.2, 2 * r + 0.28, 0.04), DK, bev=0.008)
        for sy in (-1, 1):
            for sx in (-1, 1):
                bolt(P, (x + sx * 0.06, y + sy * (r + 0.1), 0.05), 'z', 0.018, 0.02, BA)
    else:
        P.cyl((x, y, z), r + 0.012, 0.09, 'y', DK, seg=20, bev=0.006)
        for sx in (-1, 1):
            P.box((x + sx * (r + 0.03), y, z / 2), (0.035, 0.07, z), DK, bev=0.006)
            P.box((x + sx * (r + 0.03), y, z), (0.05, 0.09, 0.03), DK, bev=0.006)
        P.box((x, y, 0.02), (2 * r + 0.28, 0.2, 0.04), DK, bev=0.008)
        for sx in (-1, 1):
            for sy in (-1, 1):
                bolt(P, (x + sx * (r + 0.1), y + sy * 0.06, 0.05), 'z', 0.018, 0.02, BA)


@prop('pipe_straight')
def pipe_straight():
    P = Prop('pipe_straight')
    z, r = 0.4, 0.175
    P.cyl((0, 0, z), r, 3.92, 'x', PL, seg=20, bev=0.004)
    for x, L in ((-1.0, 0.7), (0.9, 0.6), (1.6, 0.35)):
        P.cyl((x, 0, z), r + 0.003, L, 'x', RU, seg=20, bev=0.0)
    P.torus((0.0, 0, z), r, 0.012, 'x', DK, seg=20, rseg=4)
    for x in (-0.6, 0.35, 1.2):
        P.torus((x, 0, z), r, 0.01, 'x', DK, seg=20, rseg=4)
    for sx in (-1, 1):
        pipe_flange_x(P, sx * 1.96, z, r)
        P.cyl((sx * 1.9, 0, z), r + 0.02, 0.06, 'x', DK, seg=20)
    for x in (-1.1, 1.1):
        floor_bracket(P, x, 0, z, r)
    P.cyl((0.45, 0, z + r + 0.02), 0.03, 0.05, 'z', BA, seg=8)
    return P


@prop('pipe_elbow')
def pipe_elbow():
    P = Prop('pipe_elbow')
    z, r, Rb, L = 0.4, 0.175, 0.5, 1.2
    arc = [(Rb + Rb * math.cos(math.radians(a)), -Rb + Rb * math.sin(math.radians(a)), z) for a in range(90, 181, 10)]
    pts = [(L, 0, z), (Rb + 0.3, 0, z)] + arc + [(0, -Rb - 0.3, z), (0, -L, z)]
    P.tube(pts, r, PL, seg=20, caps=False)
    # rust patch on outer bend
    arc2 = [(Rb + (Rb + 0.003) * 0 + (Rb) * math.cos(math.radians(a)), -Rb + Rb * math.sin(math.radians(a)), z) for a in range(110, 161, 10)]
    P.tube(arc2, r + 0.004, RU, seg=20, caps=False)
    pipe_flange_x(P, L - 0.04, z, r)
    flange(P, (0, -L + 0.04, z), 'y', r * 1.45, 0.045, nb=8, boltr=0.02, rb=r * 1.15)
    P.cyl((L - 0.1, 0, z), r + 0.02, 0.06, 'x', DK, seg=20)
    P.cyl((0, -L + 0.1, z), r + 0.02, 0.06, 'y', DK, seg=20)
    P.torus((Rb + 0.3, 0, z), r, 0.01, 'x', DK, seg=20, rseg=4)
    P.torus((0, -Rb - 0.3, z), r, 0.01, 'y', DK, seg=20, rseg=4)
    floor_bracket(P, 0.95, 0, z, r)
    floor_bracket(P, 0, -0.95, z, r, 'y')
    # corner brace
    P.box((0.55, -0.55, 0.02), (0.1, 0.1, 0.04), DK, bev=0.008)
    P.cyl((0.55, -0.55, 0.19), 0.04, 0.34, 'z', DK, seg=10)
    P.xf_all(Matrix.Identity(4))
    return P


@prop('pipe_valve')
def pipe_valve():
    P = Prop('pipe_valve')
    z, r = 0.4, 0.14
    P.cyl((0, 0, z), r, 1.12, 'x', PL, seg=18, bev=0.004)
    for sx in (-1, 1):
        flange(P, (sx * 0.57, 0, z), 'x', r * 1.5, 0.045, nb=8, boltr=0.018, rb=r * 1.2)
    # valve body
    P.sphere((0, 0, z), 0.25, DK, sc=(1.15, 0.95, 0.95), seg=14, rings=10)
    P.cyl((0, 0, z), 0.18, 0.5, 'x', DK, seg=16)
    P.cyl((0, 0, z + 0.28), 0.12, 0.2, 'z', DK, seg=14)
    flange(P, (0, 0, z + 0.4), 'z', 0.15, 0.04, nb=6, boltr=0.016, rb=0.115, body=PL)
    P.cyl((0, 0, z + 0.55), 0.075, 0.26, 'z', DK, seg=12)
    P.cyl((0, 0, z + 0.66), 0.018, 0.34, 'z', BA, seg=8)
    for sy in (-1, 1):
        P.box((0, sy * 0.075, z + 0.58), (0.03, 0.02, 0.3), DK, bev=0.005)
    P.box((0, 0, z + 0.73), (0.03, 0.2, 0.03), DK, bev=0.005) if False else None
    # red handwheel
    P.torus((0, 0, z + 0.78), 0.2, 0.022, 'z', RD, seg=20, rseg=6)
    for k in range(4):
        P.box((0, 0, z + 0.78), (0.4, 0.028, 0.028), RD, rot=(0, 0, k * 45), bev=0.004)
    P.cyl((0, 0, z + 0.8), 0.045, 0.06, 'z', RD, seg=10)
    P.cyl((0, 0, z + 0.845), 0.022, 0.04, 'z', BA, seg=8)
    floor_bracket(P, -0.38, 0, z, r)
    floor_bracket(P, 0.38, 0, z, r)
    return P


@prop('pipe_vertical')
def pipe_vertical():
    P = Prop('pipe_vertical')
    cy, r = -0.3, 0.2
    P.cyl((0, cy, 3.0), r, 5.9, 'z', PL, seg=20, bev=0.004)
    for z0, L in ((0.8, 1.0), (3.3, 0.8), (4.8, 0.7)):
        P.cyl((0, cy, z0), r + 0.003, L, 'z', RU, seg=20, bev=0.0)
    flange(P, (0, cy, 0.04), 'z', 0.29, 0.06, nb=8, boltr=0.02, rb=0.24, body=DK)
    for z in (1.5, 3.0, 4.5):
        flange(P, (0, cy, z), 'z', 0.3, 0.05, nb=8, boltr=0.02, rb=0.245)
    P.cyl((0, cy, 5.95), r + 0.03, 0.1, 'z', DK, seg=20)
    for z in (0.6, 2.2, 3.8, 5.4):
        P.box((0, -0.015, z), (0.34, 0.03, 0.2), DK, bev=0.006)
        P.box((0, -0.12, z), (0.1, 0.18, 0.08), DK, bev=0.006)
        P.cyl((0, cy, z), r + 0.025, 0.07, 'z', DK, seg=20)
        for sx in (-1, 1):
            P.cyl((sx * 0.13, -0.036, z + 0.07), 0.018, 0.02, 'y', BA, seg=6, bev=0)
            P.cyl((sx * 0.13, -0.036, z - 0.07), 0.018, 0.02, 'y', BA, seg=6, bev=0)
    # gauge on a stub
    gz = 2.3
    P.cyl((0, cy - r - 0.05, gz), 0.04, 0.12, 'y', DK, seg=10)
    P.cyl((0, cy - r - 0.12, gz), 0.12, 0.07, 'y', DK, seg=20)
    P.cyl((0, cy - r - 0.158, gz), 0.1, 0.012, 'y', GL, seg=20, bev=0)
    P.torus((0, cy - r - 0.158, gz), 0.115, 0.012, 'y', BA, seg=20, rseg=5)
    P.box((0.02, cy - r - 0.168, gz + 0.03), (0.012, 0.006, 0.075), RD, rot=(0, 0, 35), bev=0.001)
    for k in range(9):
        a = math.radians(-120 + k * 30)
        P.box((0.082 * math.sin(a), cy - r - 0.166, gz + 0.082 * math.cos(a)), (0.008, 0.005, 0.02), BA, rot=(0, math.degrees(-a), 0), bev=0.001)
    # small red valve wheel
    vz = 3.6
    P.cyl((0, cy - r - 0.08, vz), 0.045, 0.16, 'y', DK, seg=10)
    P.torus((0, cy - r - 0.17, vz), 0.11, 0.014, 'y', RD, seg=14, rseg=5)
    P.box((0, cy - r - 0.17, vz), (0.22, 0.02, 0.02), RD, bev=0.003)
    P.box((0, cy - r - 0.17, vz), (0.02, 0.02, 0.22), RD, bev=0.003)
    return P


@prop('pipe_bundle')
def pipe_bundle():
    P = Prop('pipe_bundle')
    specs = [(0.7, 0.20, -0.30, PL), (1.3, 0.15, -0.20, DK), (1.95, 0.18, -0.27, PL), (2.8, 0.20, -0.30, RU)]
    for i, (z, r, y, m) in enumerate(specs):
        P.cyl((0, y, z), r, 3.96, 'x', m, seg=14, bev=0.0)
        for x in (-0.5, 1.7):
            P.cyl((x, y, z), r + 0.006, 0.03, 'x', DK, seg=14, caps=False, bev=0)
        for sx in (-1, 1):
            P.cyl((sx * 1.95, y, z), r + 0.03, 0.08, 'x', DK, seg=14, bev=0)
        for x in (-1.3, 1.3):
            # wall bracket
            P.box((x, -0.02, z), (0.1, 0.04, 2 * r + 0.14), DK, bev=0)
            P.box((x, (y + 0.0) / 2 - 0.02, z - r * 0.55), (0.08, abs(y) - r * 0.4, 0.05), DK, bev=0)
            P.cyl((x, y, z), r + 0.02, 0.07, 'x', DK, seg=14, caps=False, bev=0)
    # flanges on two pipes
    for sx, i in ((0.6, 0), (-0.9, 2), (1.1, 1)):
        z, r, y, m = specs[i]
        flange(P, (sx, y, z), 'x', r * 1.4, 0.04, nb=8, boltr=0.016, rb=r * 1.15)
    # junction box
    P.box((-1.0, -0.19, 2.38), (0.56, 0.28, 0.44), PL, bev=0.012)
    P.box((-1.0, -0.34, 2.38), (0.5, 0.03, 0.38), DK, bev=0.008)
    P.cyl((-1.0, -0.37, 2.52), 0.03, 0.02, 'y', GA, seg=8)
    P.box((-1.18, -0.375, 2.3), (0.06, 0.03, 0.06), BA, bev=0.004)
    for sx in (-1, 1):
        for sz in (-1, 1):
            bolt(P, (-1.0 + sx * 0.22, -0.352, 2.38 + sz * 0.17), 'y', 0.016, 0.016)
    P.cyl((-1.0, -0.19, 2.2 - 0.0), 0.04, 0.04, 'z', DK, seg=8)
    # dangling cable
    pts = [(-1.0, -0.19, 2.2), (-0.95, -0.22, 2.0), (-0.8, -0.42, 1.8), (-0.72, -0.52, 1.5), (-0.74, -0.55, 1.25), (-0.8, -0.52, 1.05)]
    P.tube(catmull(pts, 5), 0.025, RB, seg=8)
    P.cyl((-0.8, -0.52, 1.0), 0.04, 0.1, 'z', DK, seg=8)
    # red valve wheel on pipe 2
    P.cyl((0.4, -0.2 - 0.15 - 0.06, 1.3), 0.025, 0.12, 'y', DK, seg=8)
    P.torus((0.4, -0.2 - 0.15 - 0.15, 1.3), 0.1, 0.014, 'y', RD, seg=14, rseg=5)
    P.box((0.4, -0.5, 1.3), (0.2, 0.018, 0.018), RD, bev=0.003)
    P.box((0.4, -0.5, 1.3), (0.018, 0.018, 0.2), RD, bev=0.003)
    return P


@prop('duct')
def duct():
    P = Prop('duct')
    z0, z1 = 3.0, 3.9
    zc = (z0 + z1) / 2
    P.box((0, 0, zc), (3.9, 0.9, 0.9), PL, bev=0.02, seg=2)
    for i in range(-3, 4):
        x = i * 0.55
        P.box((x, 0, zc), (0.05, 0.96, 0.96), DK, bev=0.012)
    for sx in (-1, 1):
        P.box((sx * 1.97, 0, zc), (0.06, 1.04, 1.04), DK, bev=0.01)
        for sy in (-1, 1):
            for sz in (-1, 1):
                bolt(P, (sx * 1.97, sy * 0.46, zc + sz * 0.46), 'x', 0.022, 0.02)
    # standing seams on top
    for y in (-0.28, 0.28):
        P.box((0, y, z1 + 0.012), (3.8, 0.04, 0.02), DK, bev=0.004)
    P.box((0.9, 0.0, z1 + 0.006), (0.9, 0.4, 0.012), RU, bev=0.003)
    # access hatch on front
    P.box((-0.5, -0.466, zc), (0.5, 0.025, 0.4), PL, bev=0.008)
    for sx in (-1, 1):
        for sz in (-1, 1):
            bolt(P, (-0.5 + sx * 0.21, -0.482, zc + sz * 0.16), 'y', 0.016, 0.014)
    P.box((-0.5, -0.49, zc), (0.12, 0.02, 0.04), BA, bev=0.004)
    P.cyl((1.05, -0.47, zc), 0.1, 0.02, 'y', DK, seg=14)
    # legs
    for x in (-1.45, 1.45):
        P.box((x, 0, z0 - 0.06), (0.14, 1.02, 0.1), DK, bev=0.01)
        for sy in (-1, 1):
            P.box((x, sy * 0.44, z0 / 2 - 0.05), (0.1, 0.1, z0 - 0.1), PL, bev=0.01)
            P.box((x, sy * 0.44, 0.03), (0.3, 0.3, 0.06), DK, bev=0.01)
            for k in (-1, 1):
                bolt(P, (x + k * 0.11, sy * 0.44 + k * 0.11, 0.07), 'z', 0.02, 0.025)
        P.box((x, 0, 0.9), (0.06, 0.8, 0.06), DK, bev=0.006)
        for sy in (-1, 1):
            P.box((x, sy * 0.22, 1.9), (0.04, 0.05, 2.3), BA, rot=(sy * 22, 0, 0), bev=0.005) if False else None
    return P


@prop('vent_fan')
def vent_fan():
    P = Prop('vent_fan')
    cz = 2.5
    ym = -0.25
    # square housing frame (outer 2.5, hole 2.3)
    P.box((0, -0.25, cz + 1.2), (2.5, 0.5, 0.1), PL, bev=0.015)
    P.box((0, -0.25, cz - 1.2), (2.5, 0.5, 0.1), PL, bev=0.015)
    for sx in (-1, 1):
        P.box((sx * 1.2, -0.25, cz), (0.1, 0.5, 2.3), PL, bev=0.015)
    # front lip frame and rust
    P.box((0, -0.5, cz + 1.2), (2.5, 0.04, 0.12), DK, bev=0.008)
    P.box((0, -0.5, cz - 1.2), (2.5, 0.04, 0.12), DK, bev=0.008)
    for sx in (-1, 1):
        P.box((sx * 1.2, -0.5, cz), (0.12, 0.04, 2.3), DK, bev=0.008)
        for sz in (-1, 1):
            P.box((sx * 1.15, -0.04, cz + sz * 1.15), (0.2, 0.08, 0.2), DK, bev=0.01)
            bolt(P, (sx * 1.2, -0.53, cz + sz * 1.2), 'y', 0.03, 0.025)
    hazard_x(P, -1.15, 1.15, cz + 1.12, cz + 1.2, -0.522, 0.008, 12) if False else None
    # round shroud
    P.lathe([(1.14, 0.0), (1.14, 0.45), (1.1, 0.45), (1.1, 0.0)], c=(0, -0.5, cz), axis='y', m=DK, seg=36, rot=(0, 0, 0), close=True)
    # back plate (dark)
    P.cyl((0, -0.02, cz), 1.1, 0.03, 'y', DK, seg=36, bev=0)
    for z in (cz + 1.17, cz - 1.17):
        pass
    # motor hub and struts
    P.cyl((0, -0.2, cz), 0.26, 0.28, 'y', DK, seg=18)
    P.cyl((0, -0.36, cz), 0.12, 0.05, 'y', BA, seg=12)
    for k in range(3):
        P.box((0, -0.12, cz), (2.2, 0.05, 0.07), DK, rot=(0, k * 60 + 30, 0), bev=0.006)
    # grille: rings and spokes
    gy = -0.55
    for R_ in (0.28, 0.58, 0.88, 1.12):
        P.torus((0, gy, cz), R_, 0.017, 'y', BA, seg=36, rseg=5)
    for k in range(12):
        P.box((0, gy, cz), (2.24, 0.022, 0.026), BA, rot=(0, k * 15, 0), bev=0.003) if k < 12 else None
    P.cyl((0, gy, cz), 0.08, 0.04, 'y', DK, seg=12)
    P.cyl((0, gy - 0.025, cz), 0.04, 0.02, 'y', RD, seg=10)
    # grille supports to the housing
    for sx in (-1, 1):
        for sz in (-1, 1):
            P.box((sx * 1.0, -0.5, cz + sz * 1.0), (0.05, 0.1, 0.05), DK, bev=0.005)
    # warning sticker
    P.box((0.0, -0.522, cz + 1.2), (0.5, 0.008, 0.07), YE, bev=0.002)
    # child blades
    B = P.child('blades', (0, -0.3, cz))
    B.cyl((0, -0.3, cz), 0.22, 0.12, 'y', DK, seg=16)
    B.cyl((0, -0.38, cz), 0.09, 0.05, 'y', BA, seg=10)
    for k in range(6):
        n0 = B.mark()
        B.box((0.64, 0, 0), (0.86, 0.34, 0.03), PL, rot=(0, 0, 0), bev=0.006)
        B.box((0.64, 0.0, 0.0), (0.84, 0.05, 0.034), RU, bev=0.003)
        # pitch about radial axis, then spin around Y axis, then move
        B.xf_from(n0, R(0, 0, 0))
        # build blade in XY (flat) then rotate about X by pitch to be in XZ-ish plane about Y axis
        B.xf_from(n0, Matrix.Translation((0, -0.3, cz)) @ R(0, k * 60, 0) @ R(115, 0, 0))
    return P


# ------------------------------------------------------------------ cables
def cable_path(ctrl, r, hump=None, n=7):
    pts = catmull([(x, y, r) for x, y in ctrl], n)
    out = []
    for p in pts:
        z = r
        if hump:
            for (hx, hy, hr) in hump:
                d = math.hypot(p.x - hx, p.y - hy)
                if d < hr:
                    z += 2.2 * r * (1 - (d / hr) ** 2)
        out.append(Vector((p.x, p.y, z)))
    return out


def center_xy(pts):
    cx = (max(p.x for p in pts) + min(p.x for p in pts)) / 2
    cy = (max(p.y for p in pts) + min(p.y for p in pts)) / 2
    return cx, cy


def plug(P, p, d, r, m=DK):
    d = Vector(d).normalized()
    c = p + d * r * 1.2
    ang = math.degrees(math.atan2(d.y, d.x))
    P.cyl((c.x, c.y, r), r * 1.45, r * 2.4, 'x', m, seg=10, rot=(0, 0, ang))
    c2 = p + d * r * 2.6
    P.cyl((c2.x, c2.y, r), r * 1.1, r * 0.6, 'x', BA, seg=8, rot=(0, 0, ang), bev=0.0)


def build_cable(P, ctrl, r, m=RB, hump=None, bands=(), shift=(0, 0), end_a=True, end_b=True):
    pts = cable_path(ctrl, r, hump)
    cx, cy = center_xy(pts)
    pts = [Vector((p.x - cx + shift[0], p.y - cy + shift[1], p.z)) for p in pts]
    P.tube(pts, r, m, seg=8, caps=True)
    if end_a:
        plug(P, pts[0], pts[0] - pts[2], r)
    if end_b:
        plug(P, pts[-1], pts[-1] - pts[-3], r)
    for i in bands:
        p = pts[int(i * (len(pts) - 1))]
        P.cyl((p.x, p.y, p.z), r * 1.3, r * 0.9, 'x', DK, seg=8, rot=(0, 0, 0)) if False else None
    return pts


@prop('cable_floor_a')
def cable_floor_a():
    P = Prop('cable_floor_a')
    ctrl = [(-2.8, 0.0), (-2.0, 0.5), (-1.2, 0.2), (-0.5, -0.4), (0.3, -0.2), (0.6, 0.5), (0.1, 0.9), (-0.3, 0.4), (0.4, -0.3), (1.3, -0.5), (2.0, 0.1), (2.7, 0.35)]
    build_cable(P, ctrl, 0.045, RB, hump=[(0.45, 0.0, 0.3)])
    ctrl2 = [(-2.4, -0.2), (-1.8, -0.1), (-1.0, -0.55), (0.0, -0.9), (1.0, -0.8), (1.9, -0.5)]
    build_cable(P, ctrl2, 0.03, RD, shift=(0, 0))
    return P.ground()


@prop('cable_floor_b')
def cable_floor_b():
    P = Prop('cable_floor_b')
    ctrl = [(-2.0, -1.2), (-1.3, -0.6), (-1.6, 0.2), (-0.9, 0.7), (-0.2, 0.2), (-0.5, -0.5), (0.3, -0.7), (1.0, -0.1), (0.7, 0.8), (1.5, 1.2), (2.3, 0.9)]
    build_cable(P, ctrl, 0.06, RB, hump=[(-1.4, -0.2, 0.3), (-0.4, -0.2, 0.3)])
    return P.ground()


@prop('cable_floor_c')
def cable_floor_c():
    P = Prop('cable_floor_c')
    ctrl = [(-3.2, 0.5), (-2.5, 0.2), (-1.8, 0.7), (-1.1, 0.4), (-0.6, -0.3), (0.2, -0.6), (0.9, -0.2), (0.5, 0.4), (-0.1, 0.2), (0.2, -0.3), (1.2, -0.7), (2.2, -0.4), (3.1, -0.9)]
    pts = build_cable(P, ctrl, 0.1, RB, hump=[(0.15, -0.35, 0.4), (-0.35, -0.05, 0.4)], end_a=False)
    # ribbed hose clamps and metal fitting
    for i in range(6, len(pts) - 6, 14):
        p = pts[i]
        t = (pts[i + 1] - pts[i - 1]).normalized()
        ang = math.degrees(math.atan2(t.y, t.x))
        P.cyl((p.x, p.y, p.z), 0.105, 0.04, 'x', BA, seg=10, rot=(0, 0, ang))
    p = pts[0]
    t = (pts[2] - pts[0]).normalized()
    ang = math.degrees(math.atan2(t.y, t.x))
    P.cyl((p.x, p.y, p.z), 0.13, 0.25, 'x', YE, seg=12, rot=(0, 0, ang))
    P.cyl((p.x - t.x * 0.14, p.y - t.y * 0.14, p.z), 0.08, 0.1, 'x', BA, seg=10, rot=(0, 0, ang))
    return P.ground()


@prop('cable_coil')
def cable_coil():
    P = Prop('cable_coil')
    r = 0.035
    pts = []
    turns, per = 4, 16
    for i in range(turns * per + 1):
        t = i / per
        a = 2 * math.pi * t
        rad = 0.46 - 0.05 * t
        pts.append((rad * math.cos(a), rad * math.sin(a), r))
    for i in range(1, 3 * per + 1):
        t = i / per
        a = 2 * math.pi * (turns + t)
        rad = 0.46 - 0.05 * turns + 0.045 * t
        pts.append((rad * math.cos(a), rad * math.sin(a), r * 3.0))
    pts2 = [Vector(p) for p in pts]
    # tails
    tail = [Vector((0.55, -0.2, r)), Vector((0.62, -0.05, r))]
    head = [Vector((0.9 * 0.5, -0.5, r)), Vector((0.3, -0.62, r))]
    P.tube(pts2, r, RB, seg=7)
    P.tube(catmull([(0.58, -0.45, r), (0.5, -0.25, r), (pts[0][0], pts[0][1], r)], 4), r, RB, seg=7)
    P.tube(catmull([pts[-1], (pts[-1][0] * 1.0, pts[-1][1] * 1.0, r * 3), (0.1, 0.3, 0.12)], 4), r, RB, seg=7) if False else None
    for ang in (30, 150, 270):
        a = math.radians(ang)
        P.box((0.42 * math.cos(a), 0.42 * math.sin(a), r * 2), (0.07, 0.04, 0.115), YE, rot=(0, 0, ang), bev=0.004) if False else None
    P.torus((0, 0, r * 2.0), 0.395, 0.045, 'z', RB, seg=24, rseg=6) if False else None
    for ang in (60, 200, 320):
        a = math.radians(ang)
        P.box((0.35 * math.cos(a), 0.35 * math.sin(a), r * 3.3), (0.32, 0.03, 0.012), YE, rot=(0, 0, ang + 90), bev=0.002)
    return P


@prop('cable_hanging')
def cable_hanging():
    P = Prop('cable_hanging')
    specs = [(0.9, -0.22, 0.045, RB), (1.35, 0.0, 0.055, RB), (1.7, 0.24, 0.035, RD)]
    for sag, yo, r, m in specs:
        pts = []
        for i in range(25):
            t = i / 24
            x = -3 + 6 * t
            # catenary-ish
            z = 5 - sag * (1 - (2 * t - 1) ** 2) ** 0.9
            pts.append((x, yo + 0.04 * math.sin(t * 3), z))
        P.tube(pts, r, m, seg=8)
        for sx in (-1, 1):
            P.cyl((sx * 3.0, yo, 5.0), r * 1.6, 0.14, 'x', DK, seg=10)
            P.box((sx * 3.06, yo, 5.0), (0.1, 0.22, 0.22), DK, bev=0.01)
    for sx in (-1, 1):
        P.box((sx * 3.15, 0, 5.0), (0.08, 0.7, 0.4), PL, bev=0.01)
        for sy in (-1, 1):
            for sz in (-1, 1):
                bolt(P, (sx * 3.2, sy * 0.25, 5.0 + sz * 0.14), 'x', 0.02, 0.02)
    # cable ties/clamps in the middle bundling
    for t in (0.35, 0.65):
        x = -3 + 6 * t
        P.box((x, 0.0, 5 - 1.3 * (1 - (2 * t - 1) ** 2) ** 0.9), (0.05, 0.6, 0.05), DK, bev=0.006) if False else None
    return P


@prop('chain_hook')
def chain_hook():
    P = Prop('chain_hook')
    P.box((0, 0, 6.96), (0.5, 0.3, 0.08), DK, bev=0.01)
    P.torus((0, 0, 6.88), 0.07, 0.022, 'y', DK, seg=10, rseg=4)
    chain(P, 0, 0, 3.1, 6.9, 0.13, 0.021, DK, 0.055)
    # swivel block
    P.cyl((0, 0, 3.08), 0.07, 0.14, 'z', DK, seg=10)
    P.torus((0, 0, 3.0), 0.05, 0.016, 'x', BA, seg=10, rseg=4)
    P.cyl((0, 0, 2.92), 0.05, 0.1, 'z', RU, seg=10)
    # J hook
    sh = [(0, 0, 2.95), (0, 0, 2.5), (0, 0, 2.15)]
    arc = []
    for a in range(180, 361, 15):
        arc.append((0.27 + 0.27 * math.cos(math.radians(a)), 0, 2.15 + 0.35 * math.sin(math.radians(a)) if False else 2.15 + 0.33 * math.sin(math.radians(a))))
    tip = [(0.58, 0, 2.3), (0.55, 0, 2.55)]
    pts = catmull(sh[:1] + sh[1:] + arc[1:] + tip, 3)
    n = len(pts)
    radii = [0.042 - 0.032 * max(0, (i - n * 0.8) / (n * 0.2)) for i in range(n)]
    P.tube(pts, 0.04, DK, seg=10, radii=radii)
    P.cyl((0.55, 0, 2.58), 0.008, 0.06, 'z', BA, seg=6, r2=0.003) if False else None
    return P
