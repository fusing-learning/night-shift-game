"""Furniture, vehicles, wall dressing, lights, doors, pickups."""
import math
from mathutils import Vector, Matrix
from lib import *
from props_a import draw_barrel, draw_crate_small, draw_crate_metal
from props_c import hazard_y, gauge, lamp, hexnut


def wheel(P, c, r, w, tyre=RB, hub=BA, axis='x', lugs=True):
    x, y, z = c
    P.cyl(c, r, w, axis, tyre, seg=20, bev=min(0.02, r * 0.1))
    P.cyl(c, r * 0.55, w + 0.02, axis, DK, seg=14, bev=0.004)
    P.cyl(c, r * 0.22, w + 0.04, axis, hub, seg=10, bev=0.003)
    if lugs:
        for k in range(6):
            a = 2 * math.pi * k / 6
            d = r * 0.38
            off = (0, math.cos(a) * d, math.sin(a) * d) if axis == 'x' else (math.cos(a) * d, 0, math.sin(a) * d)
            sg = 1 if True else -1
            p = (x + off[0], y + off[1], z + off[2])
            if axis == 'x':
                bolt(P, (p[0] + (w / 2 + 0.01) * (1 if x >= 0 else -1), p[1], p[2]), 'x', 0.018, 0.02)


@prop('cart')
def cart():
    P = Prop('cart')
    P.box((0, -0.02, 0.33), (1.0, 1.46, 0.05), WO, bev=0.01)
    for sx in (-1, 1):
        P.box((sx * 0.47, -0.02, 0.28), (0.06, 1.5, 0.08), DK, bev=0.008)
    for y in (-0.6, 0.0, 0.5):
        P.box((0, y, 0.285), (0.9, 0.06, 0.06), DK, bev=0.006)
    for sy in (-1, 1):
        P.box((0, sy * 0.73 - 0.02, 0.37), (1.0, 0.03, 0.05), PL, bev=0.006) if False else None
    # lower shelf
    P.box((0, -0.02, 0.14), (0.9, 1.3, 0.025), DK, bev=0.006)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.box((sx * 0.43, sy * 0.58 - 0.02, 0.17), (0.04, 0.04, 0.24), DK, bev=0.004)
            # caster
            cx, cy = sx * 0.43, sy * 0.62
            P.cyl((cx, cy, 0.265), 0.045, 0.02, 'z', BA, seg=10)
            P.box((cx, cy, 0.2), (0.06, 0.1, 0.12), DK, bev=0.006)
            P.cyl((cx, cy - sy * 0.0, 0.1), 0.1, 0.05, 'x', RB, seg=14, bev=0.01)
            P.cyl((cx, cy, 0.1), 0.045, 0.07, 'x', BA, seg=8, bev=0.0)
    # handle
    for sx in (-1, 1):
        P.box((sx * 0.45, 0.75, 0.62), (0.04, 0.05, 0.72), PL, bev=0.006)
        P.box((sx * 0.45, 0.75, 0.3), (0.06, 0.08, 0.1), DK, bev=0.006)
    P.tube(catmull([(-0.45, 0.75, 0.98), (-0.4, 0.75, 1.0), (0.4, 0.75, 1.0), (0.45, 0.75, 0.98)], 3), 0.022, BA, seg=8)
    P.box((0, 0.75, 0.65), (0.86, 0.025, 0.03), BA, bev=0.003)
    # cargo: a crate and a bag
    P.place(draw_crate_small, (0.0, -0.3, 0.355), (0, 0, 12))
    P.box((-0.18, 0.35, 0.42), (0.5, 0.35, 0.16), CL, bev=0.04, seg=2, rot=(0, 0, 20))
    hazard_x(P, -0.45, 0.45, 0.255, 0.31, -0.745, 0.01, 8)
    return P


@prop('forklift')
def forklift():
    P = Prop('forklift')
    # chassis
    P.box((0, 0.5, 0.3), (0.95, 2.0, 0.22), DK, bev=0.02)
    P.box((0, 0.5, 0.58), (1.04, 1.9, 0.38), YE, bev=0.03, seg=2)
    # engine hood
    P.box((0, 0.82, 0.92), (0.96, 0.8, 0.34), YE, bev=0.04, seg=2)
    for i in range(5):
        P.box((0, 0.82, 1.1 + 0.0), (0.7, 0.05, 0.012), DK, bev=0.0) if False else None
    for i in range(6):
        P.box((0.0, 0.5 + i * 0.12, 1.097), (0.6, 0.04, 0.012), DK, bev=0.0)
    P.box((0.0, 1.22, 0.93), (0.5, 0.02, 0.2), DK, bev=0.004)
    P.box((0.3, 0.9, 1.1), (0.3, 0.3, 0.012), RU, bev=0.002)
    # counterweight (rear)
    P.box((0, 1.28, 0.7), (1.1, 0.62, 0.82), YE, bev=0.04, seg=2)
    hazard_x(P, -0.52, 0.52, 0.32, 0.5, 1.595, 0.01, 8)
    P.box((0, 1.31, 1.13), (1.0, 0.5, 0.05), DK, bev=0.01)
    for sx in (-1, 1):
        lamp(P, (sx * 0.38, 1.6, 0.9), GR, 0.04, 'y', 1)
    # seat, floor, pedals
    P.box((0, 0.2, 0.84), (0.6, 0.5, 0.12), RB, bev=0.04, seg=2)
    P.box((0, 0.5, 1.05), (0.58, 0.1, 0.5), RB, bev=0.04, rot=(-12, 0, 0), seg=2)
    P.box((0, -0.25, 0.78), (0.9, 0.5, 0.05), DK, bev=0.01)
    # steering column + wheel
    P.cyl((0, -0.28, 1.0), 0.03, 0.55, 'z', DK, seg=8, rot=(-22, 0, 0))
    P.torus((0, -0.38, 1.28), 0.16, 0.02, 'z', RB, seg=14, rseg=4, rot=(-22, 0, 0))
    P.box((0, -0.38, 1.28), (0.3, 0.03, 0.03), DK, bev=0.002, rot=(-22, 0, 0))
    # overhead guard
    for sx in (-1, 1):
        P.box((sx * 0.5, -0.3, 1.5), (0.06, 0.06, 1.1), DK, bev=0.008)
        P.box((sx * 0.5, 0.95, 1.55), (0.06, 0.06, 1.2), DK, bev=0.008)
        P.box((sx * 0.5, 0.33, 2.08), (0.06, 1.34, 0.06), DK, bev=0.008)
    for y in (-0.28, 0.33, 0.92):
        P.box((0, y, 2.08), (1.06, 0.06, 0.06), DK, bev=0.008)
    for k in range(7):
        P.box((-0.4 + k * 0.133, 0.33, 2.1), (0.035, 1.3, 0.035), YE, bev=0.0)
    P.box((0, 0.33, 2.12), (0.5, 0.6, 0.02), RU, bev=0.003)
    P.sphere((0.4, 0.95, 2.14), 0.07, GA, seg=10, rings=6, half=True)
    P.cyl((0.4, 0.95, 2.11), 0.08, 0.04, 'z', DK, seg=10)
    # fenders and wheels
    for sx in (-1, 1):
        P.box((sx * 0.55, -0.12, 0.7), (0.16, 0.8, 0.07), YE, bev=0.015)
        wheel(P, (sx * 0.52, -0.12, 0.36), 0.36, 0.22)
        wheel(P, (sx * 0.5, 1.2, 0.27), 0.27, 0.2)
        P.box((sx * 0.38, -0.12, 0.45), (0.04, 0.2, 0.3), DK, bev=0.008) if False else None
    # mast: uprights
    for sx in (-1, 1):
        P.box((sx * 0.38, -0.62, 1.2), (0.12, 0.16, 2.2), YE, bev=0.01, seg=2)
        P.box((sx * 0.38, -0.62, 1.2), (0.16, 0.04, 2.1), BA, bev=0.004) if False else None
        P.cyl((sx * 0.23, -0.48, 1.0), 0.04, 1.8, 'z', BA, seg=10)
    for z in (0.35, 1.3, 2.25):
        P.box((0, -0.62, z), (0.88, 0.14, 0.1), DK, bev=0.01)
    P.box((0, -0.5, 1.0), (0.12, 0.08, 1.5), DK, bev=0.008) if False else None
    # lift chain
    chain(P, 0, -0.78, 0.9, 2.2, 0.1, 0.014, DK, 0.03)
    # carriage and forks
    P.box((0, -0.72, 0.5), (1.1, 0.06, 0.7), DK, bev=0.012, seg=2)
    for z in (0.3, 0.7):
        P.box((0, -0.76, z), (1.1, 0.04, 0.06), PL, bev=0.006)
    P.box((0, -0.78, 0.98), (1.0, 0.04, 0.5), DK, bev=0.008)       # load backrest
    for k in range(5):
        P.box((-0.4 + 0.2 * k, -0.8, 0.98), (0.04, 0.04, 0.5), PL, bev=0.0)
    for sx in (-1, 1):
        x = sx * 0.33
        P.box((x, -0.8, 0.32), (0.13, 0.06, 0.7), DK, bev=0.008)
        if sx < 0:
            P.box((x, -1.0, 0.055), (0.12, 0.4, 0.05), DK, bev=0.008)
            ang = 15
            c0 = Vector((x, -1.2, 0.09))
            d = Vector((0, -math.cos(math.radians(ang)), math.sin(math.radians(ang))))
            P.box(c0 + d * 0.2, (0.12, 0.4, 0.05), DK, rot=(-ang, 0, 0), bev=0.008)
        else:
            P.box((x, -1.12, 0.055), (0.12, 0.84, 0.05), DK, bev=0.008)
            P.box((x, -1.68, 0.045), (0.1, 0.14, 0.035), DK, rot=(0, 0, 0), bev=0.004) if False else None
    # hydraulic hose
    P.tube(catmull([(0.3, -0.48, 1.9), (0.5, -0.2, 1.7), (0.55, 0.2, 1.2), (0.45, 0.4, 0.8)], 5), 0.03, RB, seg=8)
    # rust patches / decals on the top
    P.box((-0.2, 0.55, 1.103), (0.3, 0.4, 0.008), RU, bev=0.0)
    P.box((0.0, -0.2, 0.775), (0.7, 0.4, 0.006), DK, bev=0.0) if False else None
    P.box((0.0, 1.31, 1.16), (0.4, 0.3, 0.01), YE, bev=0.0) if False else None
    return P.ground().ground()


@prop('workbench')
def workbench():
    P = Prop('workbench')
    P.box((0, 0, 0.925), (2.2, 0.9, 0.05), WO, bev=0.012)
    P.box((0, 0, 0.885), (2.2, 0.9, 0.03), DK, bev=0.006)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.box((sx * 1.0, sy * 0.38, 0.435), (0.08, 0.08, 0.87), DK, bev=0.01)
            P.box((sx * 1.0, sy * 0.38, 0.02), (0.18, 0.18, 0.04), DK, bev=0.008)
    for sy in (-1, 1):
        P.box((0, sy * 0.38, 0.75), (2.0, 0.05, 0.1), DK, bev=0.006)
    P.box((-0.2, 0, 0.2), (1.9, 0.78, 0.03), PL, bev=0.008)
    P.box((-0.2, 0, 0.215), (1.2, 0.5, 0.2), RU, bev=0.01) if False else None
    # drawer unit on the right
    P.box((0.62, 0.0, 0.57), (0.7, 0.82, 0.6), PL, bev=0.015)
    for i in range(3):
        z = 0.78 - i * 0.2
        P.box((0.62, -0.425, z - 0.06), (0.64, 0.03, 0.17), PL, bev=0.008)
        P.box((0.62, -0.445, z - 0.06), (0.3, 0.025, 0.03), BA, bev=0.005)
        P.box((0.62, -0.42, z + 0.04), (0.66, 0.012, 0.02), DK, bev=0.0)
    # vice on the left
    P.box((-0.8, -0.05, 0.98), (0.3, 0.3, 0.06), DK, bev=0.01)
    P.box((-0.8, -0.18, 1.06), (0.24, 0.07, 0.14), DK, bev=0.01)
    P.box((-0.8, 0.0, 1.03), (0.22, 0.08, 0.1), DK, bev=0.01)
    P.cyl((-0.8, 0.12, 1.03), 0.018, 0.4, 'y', BA, seg=8)
    P.cyl((-0.8, 0.28, 1.03), 0.012, 0.22, 'x', BA, seg=8)
    P.sphere((-0.7, 0.28, 1.03), 0.025, BA, seg=8, rings=5)
    P.sphere((-0.9, 0.28, 1.03), 0.025, BA, seg=8, rings=5)
    # tools on the top
    P.cyl((-0.15, 0.0, 0.973), 0.015, 0.34, 'x', WO, seg=8, rot=(0, 0, 20))
    P.box((-0.0, -0.12, 0.998), (0.1, 0.045, 0.045), DK, rot=(0, 0, 20), bev=0.006)
    P.box((0.25, 0.2, 0.955), (0.32, 0.04, 0.012), BA, rot=(0, 0, -25), bev=0.0)
    P.cyl((0.28, 0.2, 0.955), 0.03, 0.012, 'z', BA, seg=10, bev=0)
    P.cyl((-0.4, 0.15, 0.965), 0.012, 0.22, 'x', RD, seg=8, rot=(0, 0, 60))
    P.cyl((-0.45, -0.25, 0.97), 0.045, 0.1, 'z', GL, seg=10)
    P.box((0.1, 0.25, 0.975), (0.3, 0.12, 0.05), RD, bev=0.01)
    P.tube(catmull([(0.5, 0.3, 0.95), (0.4, 0.0, 0.95), (0.0, -0.3, 0.94), (-0.3, -0.2, 0.94)], 4), 0.012, RB, seg=6)
    # pegboard-like back rail
    P.box((0, 0.42, 1.12), (2.0, 0.025, 0.04), DK, bev=0.0)
    for x in (-0.9, 0.9):
        P.box((x, 0.42, 1.02), (0.04, 0.04, 0.2), DK, bev=0.0)
    return P


@prop('shelf_rack')
def shelf_rack():
    P = Prop('shelf_rack')
    zs = (0.3, 1.3, 2.3)
    for x in (-1.25, 0.0, 1.25):
        for y in (-0.35, 0.35):
            P.box((x, y, 1.6), (0.07, 0.07, 3.2), PL, bev=0)
            P.box((x, y, 0.02), (0.16, 0.16, 0.04), DK, bev=0)
    for z in zs:
        for y in (-0.35, 0.35):
            P.box((0, y, z), (2.6, 0.05, 0.12), YE, bev=0.006)
        for x0 in (-0.625, 0.625):
            for i in range(5):
                P.box((x0, -0.25 + i * 0.125, z + 0.075), (1.2, 0.1, 0.02), WO if z != 1.3 else DK, bev=0.0)
    # side braces
    for x in (-1.25, 1.25):
        P.box((x, 0.35, 0.8), (0.03, 0.03, 1.2), BA, rot=(0, 0, 0), bev=0.0) if False else None
        P.box((x, 0, 1.6), (0.04, 0.9, 0.04), DK, rot=(35, 0, 0), bev=0.0) if False else None
        for z in (0.8, 1.8, 2.8):
            P.box((x, 0, z), (0.04, 0.78, 0.04), DK, rot=(0, 0, 0), bev=0.0)
    P.box((0, 0.4, 3.18), (2.6, 0.05, 0.06), YE, bev=0.005)
    P.box((0, -0.4, 3.18), (2.6, 0.05, 0.06), YE, bev=0.005)
    # contents
    P.place(draw_barrel, (-0.7, 0.0, 0.385), (0, 0, 0), 0.8)
    P.place(draw_crate_small, (0.6, 0.0, 0.385), (0, 0, 5), 1.0)
    P.place(draw_crate_small, (1.0, 0.1, 0.385), (0, 0, -12), 0.95)
    P.place(draw_crate_metal, (-0.6, 0.0, 1.385), (0, 0, 8), 0.7, lite=True)
    P.box((0.4, 0.0, 1.55), (0.7, 0.5, 0.3), CL, bev=0.06, seg=2)
    P.box((1.0, 0.0, 1.5), (0.4, 0.4, 0.2), WO, bev=0.01)
    P.box((0.8, -0.05, 1.7), (0.4, 0.4, 0.2), WO, bev=0.01, rot=(0, 0, 25))
    P.cyl((-0.9, 0.0, 2.9), 0.125, 1.0, 'z', PL, seg=14) if False else None
    for i, x in enumerate((-0.9, -0.55, 0.9)):
        P.cyl((x, 0.0, 2.72), 0.12, 0.6, 'x', DK if i != 1 else RU, seg=14, rot=(0, 0, 90) if False else (0, 0, 0)) if False else None
    P.place(draw_barrel, (-0.7, 0.0, 2.385), (0, 0, 0), 0.7, body=YE)
    P.place(draw_crate_small, (0.5, 0.0, 2.385), (0, 0, 15))
    P.box((1.0, 0.0, 2.55), (0.5, 0.4, 0.35), CL, bev=0.08, seg=2)
    return P


@prop('locker_row')
def locker_row():
    P = Prop('locker_row')
    P.box((0, 0.24, 1.0), (1.8, 0.02, 2.0), DK, bev=0.004)
    P.box((0, 0, 1.96), (1.8, 0.5, 0.08), PL, bev=0.012)
    P.box((0, 0, 0.09), (1.8, 0.5, 0.06), DK, bev=0.008)
    for i in range(5):
        P.box((-0.9 + 0.45 * i + (0.011 if i == 0 else -0.011 if i == 4 else 0), 0, 1.0), (0.022, 0.5, 2.0), PL, bev=0.004)
    for sx in (-1, 1):
        for y in (-0.2, 0.2):
            P.box((sx * 0.85, y, 0.03), (0.08, 0.08, 0.06), DK, bev=0.004) if False else None
    P.box((0.3, 0.0, 1.965), (0.8, 0.3, 0.012), RU, bev=0.0)
    hinge_x = [-0.9 + 0.45 * i for i in range(4)]
    for i in range(4):
        x0 = hinge_x[i] + 0.02
        w = 0.41
        # door built relative to hinge at (x0, -0.25)
        def door(P=P, w=w):
            P.box((w / 2, -0.015, 0.0), (w, 0.03, 1.82), PL, bev=0.008)
            for k in range(4):
                P.box((w / 2, -0.032, 0.7 + k * 0.045), (0.28, 0.01, 0.022), DK, bev=0.0)
                P.box((w / 2, -0.032, -0.78 + k * 0.045), (0.28, 0.01, 0.022), DK, bev=0.0)
            P.box((w - 0.06, -0.04, 0.0), (0.03, 0.03, 0.18), BA, bev=0.004)
            P.box((w - 0.06, -0.025, 0.12), (0.05, 0.015, 0.03), DK, bev=0.0)
            P.box((w / 2, -0.035, 0.45), (0.3, 0.008, 0.08), YE if True else DK, bev=0.0)
            P.box((0.01, -0.01, 0.0), (0.02, 0.03, 1.6), DK, bev=0.0)
        ang = 0
        if i == 2:
            ang = -72
        if i == 1:
            ang = 0
        rot = R(0, 0, -ang)
        n0 = P.mark()
        door()
        P.xf_from(n0, Matrix.Translation((x0, -0.25, 1.0)) @ rot)
        # interior shelf and hanging items
        if i == 2:
            P.box((x0 + 0.2, 0.0, 1.55), (0.4, 0.46, 0.02), PL, bev=0.0)
            P.cyl((x0 + 0.2, -0.05, 1.8), 0.012, 0.4, 'x', BA, seg=6)
            P.box((x0 + 0.15, 0.1, 1.15), (0.16, 0.06, 0.55), CL, bev=0.02)
    return P


@prop('ladder')
def ladder():
    P = Prop('ladder')
    for sx in (-1, 1):
        P.box((sx * 0.22, 0, 1.75), (0.045, 0.08, 3.5), BA, bev=0.008)
        P.box((sx * 0.22, 0.0, 1.75), (0.015, 0.082, 3.46), DK, bev=0.0) if False else None
        P.box((sx * 0.22, 0, 0.025), (0.07, 0.1, 0.05), RB, bev=0.006)
    for z in [0.25 + 0.3 * i for i in range(11)]:
        P.cyl((0, 0, z), 0.015, 0.4, 'x', BA, seg=8)
    P.box((0, 0, 3.4), (0.44, 0.06, 0.05), YE, bev=0.005)
    P.box((0, -0.045, 3.2), (0.3, 0.012, 0.15), YE, bev=0.0)
    P.box((0.0, 0.045, 1.0), (0.46, 0.02, 0.06), RU, bev=0.0)
    return P


# ---------------------------------------------------------------- electrical
@prop('electrical_box')
def electrical_box():
    P = Prop('electrical_box')
    zc = 1.5
    P.box((0, -0.15, zc), (0.9, 0.3, 1.4), PL, bev=0.015, seg=2)
    P.box((0, -0.312, zc), (0.8, 0.025, 1.3), PL, bev=0.01)
    P.box((0, -0.3, zc), (0.84, 0.006, 1.34), DK, bev=0.0)
    for sz in (-1, 1):
        P.box((-0.42, -0.32, zc + sz * 0.5), (0.04, 0.04, 0.16), DK, bev=0.005)
    P.box((0.28, -0.33, zc - 0.0), (0.04, 0.03, 0.14), BA, bev=0.005) if False else None
    # louvres at the top
    for k in range(4):
        P.box((-0.2, -0.325, zc + 0.5 - k * 0.04), (0.3, 0.015, 0.02), DK, bev=0.0)
    # sign
    P.extrude([(0, -0.1), (0.1, 0.07), (-0.1, 0.07)], 'xz', -0.332, -0.318, YE, c=(-0.25, 0, zc + 0.24), bev=0.0)
    P.box((-0.25, -0.34, zc + 0.26), (0.02, 0.01, 0.07), DK, bev=0.0)
    P.box((-0.25, -0.34, zc + 0.165), (0.025, 0.01, 0.025), DK, bev=0.0)
    lamp(P, (0.25, -0.325, zc + 0.5), GR, 0.04)
    # dials
    gauge(P, (-0.2, -0.32, zc + 0.0), 0.07, 'y', -1, 40)
    gauge(P, (-0.2 + 0.18, -0.32, zc + 0.0), 0.07, 'y', -1, 70) if False else None
    # lever base plate
    P.box((0.2, -0.325, zc - 0.25), (0.26, 0.03, 0.62), DK, bev=0.01)
    P.box((0.2, -0.345, zc - 0.5), (0.2, 0.03, 0.12), BA, bev=0.006)
    P.box((0.2, -0.345, zc + 0.05), (0.04, 0.025, 0.1), BA, bev=0.004)
    for sx in (-1, 1):
        for sz in (-1, 1):
            bolt(P, (sx * 0.4, -0.33, zc + sz * 0.62), 'y', 0.018, 0.016)
    # conduit up the wall
    for x in (-0.25, 0.1, 0.32):
        P.cyl((x, -0.05, 2.75), 0.03, 1.1, 'z', BA, seg=8)
        for z in (2.5, 3.0):
            P.box((x, -0.03, z), (0.07, 0.06, 0.03), DK, bev=0.0)
    P.box((0, -0.06, 2.22), (0.8, 0.12, 0.05), DK, bev=0.004) if False else None
    for x in (-0.25, 0.1, 0.32):
        P.cyl((x, -0.05, 2.22), 0.045, 0.04, 'z', DK, seg=8)
    P.cyl((-0.25, -0.05, 0.55), 0.03, 0.8, 'z', BA, seg=8)
    # lever (child). pivot at base, UP position (off)
    piv = (0.2, -0.375, zc - 0.5)
    C = P.child('lever', piv)
    C.cyl((0.2, -0.375, zc - 0.5), 0.05, 0.05, 'y', DK, seg=10)
    C.box((0.2, -0.375, zc - 0.25 + 0.0), (0.04, 0.03, 0.46), BA, bev=0.005) if False else None
    C.box((0.2, -0.375, zc - 0.3), (0.035, 0.025, 0.42), BA, bev=0.004)
    C.box((0.2, -0.38, zc - 0.2), (0.05, 0.02, 0.1), DK, bev=0.004) if False else None
    C.cyl((0.2, -0.38, zc - 0.03), 0.032, 0.18, 'z', RD, seg=10)
    C.sphere((0.2, -0.38, zc + 0.07), 0.04, RD, seg=10, rings=6)
    return P


@prop('keycard_reader')
def keycard_reader():
    P = Prop('keycard_reader')
    P.box((0, 0, 0.03), (0.4, 0.4, 0.06), DK, bev=0.012)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bolt(P, (sx * 0.15, sy * 0.15, 0.065), 'z', 0.022, 0.02)
    P.box((0, 0, 0.55), (0.2, 0.2, 0.98), PL, bev=0.015, seg=2)
    hazard_z(P, 0.08, 0.28, 0, -0.1, (0.2, 0.012), 4) if False else None
    for i in range(4):
        P.box((0, -0.103, 0.12 + i * 0.05), (0.2, 0.008, 0.05), YE if i % 2 == 0 else DK, bev=0.0)
    # slanted head
    P.box((0, 0.0, 1.12), (0.3, 0.3, 0.26), DK, rot=(0, 0, 0), bev=0.02, seg=2)
    n0 = P.mark()
    P.box((0, 0, 0), (0.28, 0.04, 0.24), PL, bev=0.008)
    P.box((0, -0.022, 0.035), (0.2, 0.012, 0.012), BA, bev=0.0)       # card slot lip
    P.box((0, -0.026, 0.035), (0.14, 0.01, 0.008), RB, bev=0.0)
    P.box((0, -0.024, -0.06), (0.14, 0.01, 0.09), SC, bev=0.0)
    for k in range(3):
        P.cyl((-0.08 + 0.08 * k, -0.022, 0.085 + 0.0), 0.011, 0.01, 'y', BA, seg=6, bev=0)
    P.xf_from(n0, Matrix.Translation((0, -0.15, 1.15)) @ R(-35, 0, 0))
    P.box((0, 0.02, 1.27), (0.28, 0.24, 0.03), DK, bev=0.006)
    P.sphere((0, 0.05, 1.285), 0.045, GR, seg=10, rings=6, half=True)
    P.cyl((0, 0.05, 1.28), 0.055, 0.02, 'z', DK, seg=10)
    P.tube(catmull([(0.1, 0.05, 0.12), (0.2, 0.1, 0.08), (0.2, 0.2, 0.03)], 4), 0.02, RB, seg=6)
    return P


@prop('pillar')
def pillar():
    P = Prop('pillar')
    P.box((0, 0, 0.04), (0.8, 0.8, 0.08), DK, bev=0.012)
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * 0.33, sy * 0.33
            P.cyl((x, y, 0.11), 0.03, 0.12, 'z', BA, seg=8)
            hexnut(P, (x, y, 0.15), 0.05, 0.04, DK)
    P.box((0, 0, 3.5), (0.6, 0.6, 6.9), PL, bev=0.015)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.box((sx * 0.3, sy * 0.3, 3.5), (0.1, 0.1, 6.8), DK, bev=0.01)
    for z in (0.6, 2.3, 4.2, 6.0):
        P.box((0, 0, z), (0.66, 0.66, 0.14), PL, bev=0.01)
        P.box((0, 0, z + 0.09), (0.64, 0.64, 0.03), DK, bev=0.004)
    for sx in (-1, 1):
        P.box((sx * 0.3, 0.0, 0.2), (0.06, 0.04, 0.24), DK, bev=0.004) if False else None
    for k in range(4):
        P.extrude([(0, 0), (0.28, 0), (0, 0.38)], 'xz', -0.015, 0.015, DK, c=(0.12 + 0.0, -0.3 + (0.3 + 0.3 - 0.3 + 0) * 0, 0.08), bev=0.0) if False else None
    P.box((0, 0, 7.02), (0.74, 0.74, 0.08), DK, bev=0.012) if False else None
    P.box((0, 0, 6.99), (0.74, 0.74, 0.04), DK, bev=0.01)
    # hazard lower metre
    for sg in (-1, 1):
        hazard_z_y(P, 0.1, 1.1, 0, sg * 0.305, (0.62, 0.012), 10)
        hazard_z_x(P, 0.1, 1.1, sg * 0.305, 0, (0.012, 0.62), 10)
    # rivets along plate seams
    for z in [1.4 + 0.45 * i for i in range(12)]:
        if abs(z - 2.3) < 0.15 or abs(z - 4.2) < 0.15 or abs(z - 6.0) < 0.15:
            continue
        for sg in (-1, 1):
            for off in (-0.2, 0.2):
                P.cyl((off, sg * 0.3, z), 0.016, 0.014, 'y', BA, seg=6, bev=0) if sg < 0 else P.cyl((off, sg * 0.3, z), 0.016, 0.014, 'y', BA, seg=6, bev=0)
                P.cyl((sg * 0.3, off, z), 0.016, 0.014, 'x', BA, seg=6, bev=0)
    P.box((0, -0.305, 3.4), (0.3, 0.01, 0.2), YE, bev=0.0)
    return P


def hazard_z_y(P, z0, z1, x, y, sz, n):
    h = (z1 - z0) / n
    for i in range(n):
        P.box((x, y, z0 + h * (i + 0.5)), (sz[0], sz[1], h), YE if i % 2 == 0 else DK, bev=0.0)


def hazard_z_x(P, z0, z1, x, y, sz, n):
    hazard_z_y(P, z0, z1, x, y, sz, n)


@prop('railing')
def railing():
    P = Prop('railing')
    for x in (-0.9, 0.9):
        P.box((x, 0, 0.55), (0.05, 0.05, 1.1), YE, bev=0.006)
        P.box((x, 0, 0.015), (0.14, 0.14, 0.03), DK, bev=0.006)
        for sx in (-1, 1):
            for sy in (-1, 1):
                bolt(P, (x + sx * 0.05, sy * 0.05, 0.04), 'z', 0.014, 0.014)
    P.cyl((0, 0, 1.075), 0.025, 2.0, 'x', YE, seg=10, bev=0.0)
    P.cyl((0, 0, 0.6), 0.02, 2.0, 'x', YE, seg=8, bev=0.0)
    P.box((0, 0, 0.1), (2.0, 0.02, 0.12), DK, bev=0.004)
    for x in (-0.9, 0.9):
        P.box((x, 0, 1.075), (0.07, 0.07, 0.07), DK, bev=0.006)
    for x in (-0.45, 0.0, 0.45):
        P.cyl((x, 0, 0.58), 0.012, 0.52, 'z', YE, seg=6, bev=0.0) if False else None
    return P


# ------------------------------------------------------------------ lights
@prop('lamp_hanging')
def lamp_hanging():
    P = Prop('lamp_hanging')
    P.cyl((0, 0, 6.97), 0.1, 0.06, 'z', DK, seg=12)
    P.cyl((0, 0, 6.05), 0.016, 1.9, 'z', RB, seg=6)
    P.cyl((0, 0, 5.2), 0.07, 0.14, 'z', DK, seg=10)
    prof = [(0.58, 4.5), (0.53, 4.6), (0.32, 4.84), (0.14, 5.04), (0.12, 5.12), (0.08, 5.16), (0.0, 5.16)]
    P.lathe(prof, m=PL, seg=28)
    prof2 = [(0, 5.12), (0.1, 5.09), (0.3, 4.8), (0.52, 4.56), (0.55, 4.5)]
    P.lathe(prof2, m=DK, seg=28)
    P.torus((0, 0, 4.5), 0.575, 0.02, 'z', BA, seg=28, rseg=5)
    P.cyl((0, 0, 4.54), 0.38, 0.018, 'z', GW, seg=24, bev=0)
    P.sphere((0, 0, 4.72), 0.11, GW, seg=12, rings=8)
    P.cyl((0, 0, 4.88), 0.06, 0.1, 'z', DK, seg=10)
    return P


@prop('lamp_wall')
def lamp_wall():
    P = Prop('lamp_wall')
    zc = 2.8
    P.box((0, -0.02, zc), (0.34, 0.04, 0.34), DK, bev=0.012)
    for sx in (-1, 1):
        for sz in (-1, 1):
            bolt(P, (sx * 0.14, -0.05, zc + sz * 0.14), 'y', 0.016, 0.015)
    P.cyl((0, -0.1, zc), 0.15, 0.12, 'y', PL, seg=20)
    P.sphere((0, -0.16, zc), 0.12, GR, sc=(1, 0.85, 1), seg=16, rings=8, half=True, rot=(90, 0, 0))
    P.cyl((0, -0.16, zc), 0.13, 0.02, 'y', DK, seg=18)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        pts = []
        for t in range(6):
            tt = t / 5 * (math.pi / 2)
            rr = 0.14 * math.cos(tt)
            pts.append((rr * math.cos(a), -0.14 - 0.1 * math.sin(tt), zc + rr * math.sin(a)))
        P.tube(pts, 0.008, BA, seg=6)
    P.torus((0, -0.17, zc), 0.1, 0.008, 'y', BA, seg=14, rseg=4)
    P.box((0, -0.12, zc + 0.19), (0.3, 0.2, 0.025), DK, rot=(-12, 0, 0), bev=0.006)
    return P


@prop('lamp_work')
def lamp_work():
    P = Prop('lamp_work')
    top = Vector((0, 0, 1.45))
    for k in range(3):
        a = math.radians(-90 + 120 * k)
        foot = Vector((0.6 * math.cos(a), 0.6 * math.sin(a), 0.0))
        P.tube([top, foot + Vector((0, 0, 0.02))], 0.016, YE, seg=8)
        P.box((foot.x, foot.y, 0.02), (0.06, 0.06, 0.04), RB, bev=0.008)
        mid = top.lerp(foot, 0.4)
        P.cyl((mid.x, mid.y, mid.z), 0.02, 0.05, 'z', DK, seg=8)
    P.cyl((0, 0, 1.45), 0.04, 0.12, 'z', DK, seg=10)
    P.cyl((0, 0, 1.38), 0.025, 0.4, 'z', BA, seg=8)
    P.cyl((0, 0, 1.25), 0.04, 0.05, 'z', DK, seg=10)
    # head
    n0 = P.mark()
    P.box((0, 0, 0), (0.54, 0.12, 0.38), DK, bev=0.012)
    P.box((0, -0.065, 0), (0.46, 0.012, 0.3), GW, bev=0.0)
    for k in range(3):
        P.box((0, -0.075, -0.09 + 0.09 * k), (0.48, 0.012, 0.012), DK, bev=0.0)
    for sx in (-1, 1):
        P.box((sx * 0.2, 0.09, 0.0), (0.04, 0.08, 0.34), DK, bev=0.005)
    P.cyl((0, 0.0, 0.2), 0.02, 0.4, 'x', DK, seg=6, bev=0) if False else None
    P.tube(catmull([(-0.2, 0.0, 0.2), (-0.1, 0.0, 0.27), (0.1, 0.0, 0.27), (0.2, 0.0, 0.2)], 3), 0.014, BA, seg=6)
    P.xf_from(n0, Matrix.Translation((0, 0, 1.6)) @ R(30, 0, 0))
    for sx in (-1, 1):
        P.cyl((sx * 0.29, 0.0, 1.6), 0.025, 0.05, 'x', BA, seg=8)
    # trailing cable
    P.tube(catmull([(0.1, 0.13, 1.62), (0.14, 0.25, 1.2), (0.1, 0.35, 0.4), (0.15, 0.45, 0.03), (0.3, 0.7, 0.03), (0.1, 0.9, 0.03), (-0.1, 0.8, 0.03), (-0.2, 1.0, 0.03)], 5), 0.014, RB, seg=6)
    return P.ground()


# ----------------------------------------------------------------- doors
@prop('door_frame')
def door_frame():
    P = Prop('door_frame')
    for sx in (-1, 1):
        P.box((sx * 2.15, -0.35, 2.0), (0.3, 0.7, 4.0), PL, bev=0.02, seg=2)
        P.box((sx * 2.29, -0.35, 2.0), (0.02, 0.7, 4.0), DK, bev=0.0)
        P.box((sx * 1.95, -0.62, 2.0), (0.1, 0.1, 4.0), DK, bev=0.012)
        P.box((sx * 1.95, -0.08, 2.0), (0.1, 0.16, 3.95), DK, bev=0.01)   # guide channel
        P.box((sx * 2.1, -0.35, 0.04), (0.4, 0.7, 0.08), DK, bev=0.01)
        # chevrons
        for i in range(10):
            z0 = 0.15 + i * 0.37
            P.extrude([(0, 0), (0.24, 0.12), (0.24, 0.3), (0, 0.18)], 'xz', -0.708, -0.696, YE if i % 2 == 0 else DK,
                      c=(sx * 2.15 - 0.12, 0, z0), bev=0.0) if True else None
        for z in (0.6, 2.0, 3.4):
            for k in (-1, 1):
                bolt(P, (sx * 2.15 + k * 0.09, -0.71, z), 'y', 0.022, 0.02)
        P.cyl((sx * 2.15, -0.42, 4.0 - 0.08), 0.1, 0.1, 'y', DK, seg=10) if False else None
    # sill
    P.box((0, -0.35, 0.02), (4.0, 0.7, 0.04), CO, bev=0.006)
    P.box((0, -0.5, 0.05), (4.0, 0.1, 0.02), BA, bev=0.003)
    # roll housing
    P.box((0, -0.35, 4.22), (4.6, 0.7, 0.44), PL, bev=0.03, seg=2)
    P.box((0, -0.375, 4.22), (4.2, 0.7, 0.2), DK, bev=0.01) if False else None
    hazard_x(P, -2.2, 2.2, 4.02, 4.1, -0.705, 0.012, 22)
    for i in range(6):
        P.box((-1.5 + i * 0.6, -0.705, 4.32), (0.4, 0.01, 0.04), DK, bev=0.0)
    for sx in (-1, 1):
        P.box((sx * 2.29, -0.35, 4.22), (0.02, 0.7, 0.44), DK, bev=0.0)
        for sz in (-1, 1):
            bolt(P, (sx * 1.9, -0.71, 4.22 + sz * 0.15), 'y', 0.022, 0.02)
    P.box((0, -0.7, 4.42), (4.6, 0.04, 0.03), DK, bev=0.004) if False else None
    P.cyl((-1.0, -0.72, 4.22), 0.06, 0.03, 'y', DK, seg=10) if False else None
    P.box((1.4, -0.36, 4.0 - 0.0), (0.6, 0.04, 0.04), DK, bev=0.0) if False else None
    P.tube(catmull([(1.9, -0.65, 4.4), (2.05, -0.71, 3.8), (2.2, -0.72, 2.5), (2.18, -0.72, 1.2)], 5), 0.02, RB, seg=8)
    for i in range(8):
        P.box((-1.9 + i * 0.55, -0.35, 4.452), (0.14, 0.5, 0.012), DK, bev=0.0)
    for sx in (-1, 1):
        P.box((sx * 1.6, -0.35, 4.46), (0.5, 0.4, 0.02), RU, bev=0.0)
        P.cyl((sx * 1.0, -0.15, 4.5), 0.06, 0.1, 'z', BA, seg=8)
    P.box((0.9, -0.35, 4.48), (0.5, 0.35, 0.06), DK, bev=0.008)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bolt(P, (sx * 2.15, -0.35 + sy * 0.28, 4.45), 'z', 0.03, 0.02)
    # beacon child
    C = P.child('beacon', (0, -0.35, 4.44))
    C.cyl((0, -0.35, 4.46), 0.12, 0.04, 'z', DK, seg=14)
    C.sphere((0, -0.35, 4.47), 0.1, GR, seg=14, rings=8, half=True, sc=(1, 1, 0.9))
    C.torus((0, -0.35, 4.5), 0.09, 0.008, 'z', DK, seg=14, rseg=4)
    P.shift((0, 0.35, 0))
    return P


@prop('door_shutter')
def door_shutter():
    P = Prop('door_shutter')
    n = 36
    sh = 4.0 / n
    for i in range(n):
        z = 0.15 + (i + 0.5) * (3.85 / n)
        hh = 3.85 / n
        if 2.15 < z < 2.55:
            for sx in (-1, 1):
                P.box((sx * 1.4, 0, z), (1.2 + 0.0, 0.07, hh * 0.92), PL if i % 3 else RU, bev=0.008)
            continue
        P.box((0, 0, z), (3.9, 0.07, hh * 0.92), PL if i % 4 else RU, bev=0.008)
        if i % 3 == 0:
            P.box((0, -0.045, z), (3.9, 0.02, 0.02), DK, bev=0.0)
    # window slit
    P.box((0, 0.0, 2.35), (1.6, 0.03, 0.34), GL, bev=0.0)
    for sz in (-1, 1):
        P.box((0, -0.03, 2.35 + sz * 0.19), (1.7, 0.05, 0.03), DK, bev=0.004)
    for sx in (-1, 1):
        P.box((sx * 0.84, -0.03, 2.35), (0.04, 0.05, 0.4), DK, bev=0.004)
    # side guides
    for sx in (-1, 1):
        P.box((sx * 1.98, 0, 2.05), (0.06, 0.12, 3.95), DK, bev=0.008)
    # bottom bar with handle
    P.box((0, 0, 0.07), (4.0, 0.15, 0.14), YE, bev=0.012)
    hazard_x(P, -1.95, 1.95, 0.03, 0.11, -0.077, 0.01, 20)
    P.tube(catmull([(-0.3, -0.08, 0.5), (-0.3, -0.12, 0.5), (0.3, -0.12, 0.5), (0.3, -0.08, 0.5)], 2), 0.018, BA, seg=8)
    P.box((0, -0.075, 0.5), (0.8, 0.02, 0.16), DK, bev=0.004)
    P.box((0, 0.0, 3.95), (4.0, 0.12, 0.1), DK, bev=0.01)
    return P


# ---------------------------------------------------------------- pickups
@prop('pickup_energy')
def pickup_energy():
    P = Prop('pickup_energy')
    P.cyl((0, 0, 0.035), 0.1, 0.07, 'z', DK, seg=14, bev=0.008)
    P.cyl((0, 0, 0.345), 0.1, 0.07, 'z', DK, seg=14, bev=0.008)
    P.cyl((0, 0, 0.19), 0.065, 0.28, 'z', GC, seg=14, bev=0.0)
    P.torus((0, 0, 0.07), 0.09, 0.012, 'z', BA, seg=14, rseg=4)
    P.torus((0, 0, 0.31), 0.09, 0.012, 'z', BA, seg=14, rseg=4)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        P.cyl((0.092 * math.cos(a), 0.092 * math.sin(a), 0.19), 0.011, 0.28, 'z', BA, seg=6, bev=0)
    P.tube(catmull([(-0.05, 0, 0.375), (-0.04, 0, 0.395), (0.04, 0, 0.395), (0.05, 0, 0.375)], 3), 0.008, BA, seg=6) if False else None
    P.box((0, 0, 0.372), (0.12, 0.03, 0.012), BA, bev=0.0)
    return P


@prop('pickup_health')
def pickup_health():
    P = Prop('pickup_health')
    P.box((0, 0, 0.075), (0.4, 0.25, 0.15), PL, bev=0.012)
    P.box((0, 0, 0.17), (0.38, 0.23, 0.06), PL, bev=0.012)
    P.box((0, 0, 0.142), (0.4, 0.25, 0.008), DK, bev=0.0)
    P.box((0, 0, 0.203), (0.2, 0.06, 0.012), GG, bev=0.0)
    P.box((0, 0, 0.203), (0.06, 0.2, 0.012), GG, bev=0.0)
    P.box((0, -0.127, 0.14), (0.08, 0.02, 0.05), BA, bev=0.004)
    for sx in (-1, 1):
        P.box((sx * 0.14, 0.126, 0.13), (0.05, 0.015, 0.06), DK, bev=0.0)
    P.box((0.19, 0.0, 0.1), (0.02, 0.2, 0.025), GG, bev=0.0) if False else None
    P.tube(catmull([(-0.1, 0, 0.2), (-0.09, 0, 0.23), (0.09, 0, 0.23), (0.1, 0, 0.2)], 3), 0.01, DK, seg=6)
    return P


@prop('pickup_key')
def pickup_key():
    P = Prop('pickup_key')
    P.box((0, 0, 0), (0.3, 0.2, 0.012), YE, bev=0.004)
    P.box((-0.07, 0.03, 0.0095), (0.06, 0.045, 0.008), GA, bev=0.0)
    P.box((0, -0.075, 0.0075), (0.28, 0.035, 0.004), DK, bev=0.0)
    P.cyl((0.12, 0.07, 0.0), 0.012, 0.014, 'z', DK, seg=8, bev=0)
    P.box((0.05, 0.03, 0.0075), (0.12, 0.012, 0.004), DK, bev=0.0)
    P.box((0.05, 0.0, 0.0075), (0.12, 0.012, 0.004), DK, bev=0.0)
    return P


# ------------------------------------------------------------ wall dressing
@prop('wall_vent')
def wall_vent():
    P = Prop('wall_vent')
    zc = 2.6
    P.box((0, -0.03, zc), (1.2, 0.06, 1.2), DK, bev=0.01) if False else None
    for sz in (-1, 1):
        P.box((0, -0.06, zc + sz * 0.55), (1.2, 0.12, 0.1), PL, bev=0.012)
        P.box((sz * 0.55, -0.06, zc), (0.1, 0.12, 1.0), PL, bev=0.012)
    P.box((0, -0.02, zc), (1.0, 0.04, 1.0), DK, bev=0.0)
    for i in range(8):
        P.box((0, -0.08, zc - 0.43 + i * 0.123), (1.0, 0.035, 0.09), PL if i % 3 else RU, rot=(-32, 0, 0), bev=0.004)
    P.box((0, -0.12, zc), (0.04, 0.03, 1.0), BA, bev=0.0)
    for sx in (-1, 1):
        for sz in (-1, 1):
            bolt(P, (sx * 0.55, -0.125, zc + sz * 0.55), 'y', 0.022, 0.02)
    return P


@prop('wall_sign')
def wall_sign():
    P = Prop('wall_sign')
    zc = 2.2
    P.box((0, -0.015, zc), (1.0, 0.03, 0.7), YE, bev=0.008)
    for sz in (-1, 1):
        P.box((0, -0.032, zc + sz * 0.31), (0.92, 0.012, 0.03), DK, bev=0.0)
    for sx in (-1, 1):
        P.box((sx * 0.46, -0.032, zc), (0.03, 0.012, 0.58), DK, bev=0.0)
    P.extrude([(0, 0.23), (0.28, -0.2), (-0.28, -0.2)], 'xz', -0.04, -0.03, DK, c=(0, 0, zc))
    P.extrude([(0, 0.15), (0.2, -0.15), (-0.2, -0.15)], 'xz', -0.046, -0.03, YE, c=(0, 0, zc - 0.02))
    P.box((0, -0.05, zc + 0.01), (0.04, 0.01, 0.15), DK, bev=0.0)
    P.box((0, -0.05, zc - 0.13), (0.04, 0.01, 0.04), DK, bev=0.0)
    for sx in (-1, 1):
        for sz in (-1, 1):
            bolt(P, (sx * 0.42, -0.034, zc + sz * 0.28), 'y', 0.016, 0.012)
    P.box((0.3, -0.036, zc - 0.3), (0.3, 0.008, 0.03), RU, bev=0.0)
    return P


@prop('wall_fusebox')
def wall_fusebox():
    P = Prop('wall_fusebox')
    zc = 1.4
    P.box((0, -0.09, zc), (0.6, 0.18, 0.8), PL, bev=0.012)
    P.box((0, -0.185, zc), (0.54, 0.012, 0.72), DK, bev=0.0)
    P.box((0.0, -0.19, zc + 0.2), (0.4, 0.006, 0.2), DK, bev=0.0) if False else None
    P.box((-0.24, -0.19, zc), (0.03, 0.025, 0.12), BA, bev=0.0) if False else None
    P.box((0.2, -0.195, zc - 0.05), (0.07, 0.03, 0.22), BA, bev=0.004)
    P.sphere((-0.18, -0.19, zc + 0.3), 0.03, GG, seg=8, rings=6, half=True, rot=(90, 0, 0))
    P.box((-0.1, -0.19, zc - 0.2), (0.22, 0.008, 0.16), YE, bev=0.0)
    P.extrude([(0, 0.06), (0.06, -0.05), (-0.06, -0.05)], 'xz', -0.2, -0.195, DK, c=(-0.1, 0, zc - 0.2))
    for sx in (-1, 1):
        for sz in (-1, 1):
            bolt(P, (sx * 0.27, -0.195, zc + sz * 0.36), 'y', 0.015, 0.012)
        P.box((sx * 0.31, -0.06, zc + 0.3), (0.025, 0.05, 0.1), DK, bev=0.0)
    P.cyl((0.0, -0.06, 2.1), 0.025, 0.65, 'z', BA, seg=8)
    P.cyl((0.0, -0.06, 1.82), 0.04, 0.04, 'z', DK, seg=8)
    P.tube(catmull([(0.0, -0.06, 2.4), (0.1, -0.06, 2.5), (0.5, -0.06, 2.5)], 4), 0.025, BA, seg=8)
    P.cyl((-0.2, -0.06, 0.85), 0.025, 0.2, 'z', BA, seg=8) if False else None
    P.tube(catmull([(-0.15, -0.06, 1.0), (-0.2, -0.1, 0.7), (-0.12, -0.2, 0.3), (0.05, -0.3, 0.03)], 4), 0.02, RB, seg=6)
    for z in (2.2, 2.4):
        P.box((0, -0.04, z), (0.09, 0.04, 0.03), DK, bev=0.0)
    return P
