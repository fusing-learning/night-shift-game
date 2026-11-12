"""Machines & set pieces."""
import math
from mathutils import Vector, Matrix
from lib import *


def hazard_y(P, y0, y1, z0, z1, x, depth=0.012, n=8, a=YE, b=DK):
    w = (y1 - y0) / n
    for i in range(n):
        P.box((x, y0 + w * (i + 0.5), (z0 + z1) / 2), (depth, w, z1 - z0), a if i % 2 == 0 else b, bev=0.003)


def gauge(P, c, r=0.09, axis='y', sgn=-1, needle=35):
    x, y, z = c
    P.cyl((x, y, z), r, 0.05, axis, BA, seg=18)
    P.cyl((x, y + sgn * 0.027, z), r * 0.82, 0.012, axis, GL, seg=18, bev=0)
    P.box((x + 0.01, y + sgn * 0.036, z + 0.02), (0.01, 0.005, r * 0.7), RD, rot=(0, needle, 0), bev=0.001)
    P.box((x, y + sgn * 0.032, z), (r * 1.1, 0.004, r * 0.1), DK, bev=0.001) if False else None


def lamp(P, c, m, r=0.04, axis='y', sgn=-1):
    x, y, z = c
    P.cyl((x, y - sgn * 0.01, z), r * 1.25, 0.02, axis, DK, seg=10)
    P.sphere((x, y + sgn * 0.005, z), r, m, seg=10, rings=6, sc=(1, 0.8, 1))


def hexnut(P, c, r=0.04, h=0.03, m=DK):
    P.cyl(c, r, h, 'z', m, seg=6, bev=0.003)


# ================================================================== PRESS
@prop('machine_press')
def machine_press():
    P = Prop('machine_press')
    # base bed
    P.box((0, 0, 0.3), (3.2, 3.0, 0.6), DK, bev=0.035, seg=2)
    P.box((0, 0, 0.675), (2.9, 2.7, 0.15), PL, bev=0.02, seg=2)
    P.box((0, 0, 0.76), (1.5, 1.3, 0.025), BA, bev=0.006)           # die plate
    P.box((0.05, 0.0, 0.84), (0.9, 0.7, 0.13), RU, bev=0.015)         # workpiece slab
    for x in (-1.1, -0.55, 0.55, 1.1):
        P.box((x, 0, 0.752), (0.08, 2.5, 0.012), DK, bev=0.002)       # T-slots
    hazard_x(P, -1.5, 1.5, 0.12, 0.34, -1.505, 0.012, 10)
    hazard_x(P, -1.5, 1.5, 0.12, 0.34, 1.505, 0.012, 6)
    hazard_y(P, -1.5, 1.5, 0.12, 0.34, -1.605, 0.012, 10)
    hazard_y(P, -1.5, 1.5, 0.12, 0.34, 1.605, 0.012, 6)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.box((sx * 1.55, sy * 1.0, 0.025), (0.2, 0.4, 0.05), DK, bev=0.008)
            bolt(P, (sx * 1.2, sy * 1.0, 0.76), 'z', 0.03, 0.02)
    # columns
    cols = [(sx * 1.2, sy * 1.0) for sx in (-1, 1) for sy in (-1, 1)]
    for (x, y) in cols:
        P.cyl((x, y, 2.4), 0.14, 3.5, 'z', BA, seg=18, bev=0.004)
        P.cyl((x, y, 0.85), 0.24, 0.2, 'z', DK, seg=14)
        hexnut(P, (x, y, 3.88), 0.22, 0.1, DK)
        hexnut(P, (x, y, 4.62), 0.22, 0.1, DK)
        P.cyl((x, y, 4.72), 0.12, 0.1, 'z', BA, seg=12)
        P.cyl((x, y, 1.0), 0.19, 0.06, 'z', RU, seg=14, caps=False, bev=0)
    # crosshead
    P.box((0, 0, 4.25), (3.0, 2.6, 0.6), PL, bev=0.035, seg=2)
    P.box((0, 0, 4.58), (2.7, 2.3, 0.06), PL, bev=0.01)
    hazard_x(P, -1.35, 1.35, 4.607, 4.612, -1.12, 0.0, 1) if False else None
    for i in range(14):
        P.box((-1.25 + i * 0.192, -1.1, 4.612), (0.1, 0.12, 0.006), YE if i % 2 == 0 else DK, bev=0.0)
        P.box((-1.25 + i * 0.192, 1.1, 4.612), (0.1, 0.12, 0.006), YE if i % 2 == 0 else DK, bev=0.0)
    for k, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        a = math.degrees(math.atan2(sy * 1.0, sx * 1.2))
        P.box((sx * 0.95, sy * 0.78, 4.66), (0.9, 0.09, 0.14), DK, rot=(0, 0, a), bev=0.01)
    for x in (-0.95, 0.95):
        P.box((x, 0.0, 4.60), (0.5, 0.7, 0.012), RU, bev=0.0) if x < 0 else P.box((x, 0.0, 4.6), (0.4, 0.5, 0.012), BA, bev=0.0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.cyl((sx * 1.28, sy * 1.08, 4.84), 0.018, 0.5, 'z', YE, seg=6, bev=0) if False else None
    for sy in (-1, 1):
        P.cyl((0, sy * 1.22, 4.82), 0.016, 2.5, 'x', YE, seg=6, bev=0)
        P.cyl((0, sy * 1.22, 4.68), 0.016, 2.5, 'x', YE, seg=6, bev=0)
    for sx in (-1, 1):
        P.cyl((sx * 1.28, 0, 4.82), 0.016, 2.4, 'y', YE, seg=6, bev=0)
        P.cyl((sx * 1.28, 0, 4.68), 0.016, 2.4, 'y', YE, seg=6, bev=0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.box((sx * 1.28, sy * 1.22, 4.82), (0.045, 0.045, 0.45), YE, bev=0.0)
    P.box((0, -1.32, 4.25), (2.4, 0.04, 0.3), DK, bev=0.008)
    for sx in (-1, 1):
        P.box((sx * 1.51, 0, 4.25), (0.03, 2.0, 0.3), DK, bev=0.008)
    hazard_x(P, -1.5, 1.5, 3.98, 4.08, -1.315, 0.01, 15)
    # main hydraulic cylinder + flange ring
    P.cyl((0, 0, 4.81), 0.62, 0.38, 'z', DK, seg=28, bev=0.012)
    P.cyl((0, 0, 4.64), 0.78, 0.06, 'z', PL, seg=28)
    for k in range(12):
        a = 2 * math.pi * k / 12
        bolt(P, (0.7 * math.cos(a), 0.7 * math.sin(a), 4.69), 'z', 0.03, 0.03)
    P.band((0, 0, 4.95), 0.62, 'z', BA, seg=28, w=0.07, h=0.03)
    P.band((0, 0, 4.78), 0.62, 'z', BA, seg=28, w=0.05, h=0.02)
    P.cyl((0, 0, 4.98), 0.2, 0.04, 'z', BA, seg=14)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        P.extrude([(0.62, 0), (0.95, 0), (0.62, 0.4)], 'xz', -0.04, 0.04, DK, rot=(0, 0, math.degrees(a)), c=(0, 0, 4.62 - 0.0 + 0.0), bev=0.0) if False else None
    # oil reservoir, lamp
    P.cyl((-1.0, 0.6, 4.78), 0.22, 0.34, 'z', DK, seg=14)
    P.cyl((-1.0, 0.6, 4.99), 0.12, 0.08, 'z', RD, seg=10)
    P.cyl((1.25, -0.9, 4.65), 0.06, 0.1, 'z', DK, seg=10)
    P.sphere((1.25, -0.9, 4.72), 0.09, GA, seg=10, rings=6, half=True)
    # side hydraulic stubs on cylinder
    for sgn in (-1, 1):
        P.cyl((sgn * 0.75, 0.0, 4.82), 0.07, 0.3, 'x', BA, seg=10)
        P.cyl((sgn * 0.92, 0.0, 4.82), 0.12, 0.04, 'x', PL, seg=12)
    # control box on the bed
    cb = (1.25, -1.3, 0.75)
    P.box((cb[0], cb[1], cb[2] + 0.45), (0.5, 0.25, 0.9), PL, bev=0.015)
    P.box((cb[0], cb[1] - 0.134, cb[2] + 0.55), (0.42, 0.02, 0.5), DK, bev=0.008)
    P.box((cb[0] + 0.0, cb[1] - 0.15, cb[2] + 0.64), (0.3, 0.015, 0.16), SC, bev=0.002)
    lamp(P, (cb[0] - 0.14, cb[1] - 0.15, cb[2] + 0.45), GG, 0.025)
    lamp(P, (cb[0] - 0.05, cb[1] - 0.15, cb[2] + 0.45), GR, 0.025)
    lamp(P, (cb[0] + 0.05, cb[1] - 0.15, cb[2] + 0.45), GA, 0.025)
    P.cyl((cb[0] + 0.14, cb[1] - 0.16, cb[2] + 0.45), 0.04, 0.03, 'y', RD, seg=10)
    for k in range(4):
        P.cyl((cb[0] - 0.15 + 0.1 * k, cb[1] - 0.15, cb[2] + 0.34), 0.02, 0.025, 'y', BA, seg=8)
    P.box((cb[0], cb[1], cb[2] + 0.92), (0.54, 0.29, 0.04), DK, bev=0.01)
    P.cyl((cb[0], cb[1] - 0.01, cb[2] + 0.07), 0.05, 0.14, 'z', DK, seg=8) if False else None
    # hoses from cylinder to the control box
    pts = [(0.62, -0.25, 4.82), (0.95, -0.9, 4.74), (1.3, -1.42, 4.5), (1.5, -1.43, 3.6), (1.55, -1.43, 2.4), (1.45, -1.4, 1.5), (1.3, -1.34, 1.66)]
    P.tube(catmull(pts, 4), 0.04, RB, seg=8)
    pts = [(-0.62, -0.2, 4.7), (-0.9, -0.75, 4.78), (-1.2, -1.2, 4.7), (-1.4, -1.38, 4.5)]
    P.tube(catmull(pts, 6), 0.035, RB, seg=8)
    P.cyl((-1.42, -1.4, 4.45), 0.06, 0.12, 'z', BA, seg=8)
    # piston child
    C = P.child('piston', (0, 0, 4.55))
    C.cyl((0, 0, 3.95), 0.3, 1.2, 'z', BA, seg=20, bev=0.004)
    C.cyl((0, 0, 3.6), 0.34, 0.14, 'z', DK, seg=20)
    C.box((0, 0, 3.0), (1.9, 1.6, 0.35), DK, bev=0.03, seg=2)
    C.box((0, 0, 3.2), (1.5, 1.25, 0.08), PL, bev=0.015)
    C.box((0, 0, 2.84), (1.7, 1.4, 0.03), BA, bev=0.008)
    for (x, y) in cols:
        C.cyl((x, y, 3.0), 0.235, 0.55, 'z', DK, seg=16)
        C.cyl((x, y, 3.0), 0.255, 0.1, 'z', RU, seg=16, caps=False, bev=0)
        C.box((x * 0.8, y * 0.8, 3.0), (0.5, 0.4, 0.3), DK, bev=0.015)
    hazard_x(C, -0.9, 0.9, 2.86, 3.12, -0.805, 0.01, 8)
    hazard_x(C, -0.9, 0.9, 2.86, 3.12, 0.805, 0.01, 8)
    hazard_y(C, -0.8, 0.8, 2.86, 3.12, -0.955, 0.01, 8)
    hazard_y(C, -0.8, 0.8, 2.86, 3.12, 0.955, 0.01, 8)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bolt(C, (sx * 0.6, sy * 0.5, 3.245), 'z', 0.025, 0.02)
    return P


# ================================================================ MACHINE A
@prop('machine_a')
def machine_a():
    P = Prop('machine_a')
    P.box((0, 0, 0.1), (3.4, 1.7, 0.2), DK, bev=0.02, seg=2)
    hazard_x(P, -1.6, 1.6, 0.03, 0.17, -0.855, 0.012, 16)
    P.box((0, 0, 1.0), (3.4, 1.7, 1.6), PL, bev=0.025, seg=2)
    P.box((0, 0, 1.85), (3.5, 1.8, 0.1), DK, bev=0.02, seg=2)
    P.box((0, 0, 1.9), (3.3, 1.6, 0.03), PL, bev=0.008)
    for i in range(6):
        P.box((-1.4 + i * 0.12, -0.45, 1.92), (0.07, 0.5, 0.02), DK, bev=0.0)
    P.box((-1.2, 0.0, 1.925), (0.5, 0.5, 0.02), DK, bev=0.004) if False else None
    for sx in (-1, 1):
        for sy in (-1, 1):
            bolt(P, (sx * 1.6, sy * 0.75, 1.93), 'z', 0.03, 0.02)
    P.box((-1.15, 0.45, 1.95), (0.7, 0.55, 0.05), DK, bev=0.01)
    P.cyl((-1.15, 0.45, 1.99), 0.2, 0.04, 'z', BA, seg=14)
    for k in range(4):
        P.box((-1.15, 0.45 - 0.13 + k * 0.09, 2.015), (0.3, 0.02, 0.012), DK, bev=0.0)
    P.box((1.35, -0.1, 1.915), (0.9, 0.7, 0.012), YE, bev=0.0) if False else None
    y = -0.855
    # panels
    for (x, w) in ((-1.15, 0.95), (-0.1, 0.9), (1.05, 1.1)):
        P.box((x, y - 0.012, 0.95), (w, 0.025, 1.15), PL, bev=0.01)
        for sx in (-1, 1):
            for sz in (-1, 1):
                bolt(P, (x + sx * (w / 2 - 0.05), y - 0.03, 0.95 + sz * 0.53), 'y', 0.022, 0.02)
    # vents on left panel
    P.box((-1.15, y - 0.028, 0.95), (0.7, 0.02, 0.8), DK, bev=0.003)
    for i in range(8):
        P.box((-1.15, y - 0.045, 0.62 + i * 0.1), (0.68, 0.025, 0.05), PL, rot=(-25, 0, 0), bev=0.004)
    # centre panel handle + dials
    P.box((-0.1, y - 0.05, 0.75), (0.5, 0.04, 0.05), BA, bev=0.006)
    for k, sx in enumerate((-0.3, -0.1, 0.1, 0.3)):
        gauge(P, (-0.1 + sx * 0.95 - 0.0, y - 0.04, 1.28), 0.075, 'y', -1, 20 + 40 * k)
    # screen on right panel
    P.box((1.05, y - 0.04, 1.2), (0.78, 0.05, 0.5), DK, bev=0.01)
    P.box((1.05, y - 0.068, 1.2), (0.66, 0.012, 0.38), SC, bev=0.002)
    for k in range(5):
        P.cyl((0.78 + 0.13 * k, y - 0.045, 0.78), 0.025, 0.03, 'y', BA if k % 2 else RD, seg=8)
    P.box((1.05, y - 0.04, 0.55), (0.8, 0.03, 0.2), DK, bev=0.006)
    for k in range(6):
        P.box((0.75 + 0.1 * k, y - 0.06, 0.55), (0.04, 0.02, 0.1), YE if k % 3 == 0 else PL, bev=0.003)
    # lamps
    for k, m in enumerate((GA, GA, GR)):
        lamp(P, (-1.55 + 0.17 * k, y - 0.03, 1.7), m, 0.045)
    P.box((-1.38, y - 0.012, 1.7), (0.6, 0.02, 0.12), DK, bev=0.004)
    # top pipes
    for x in (-1.2, 0.1, 1.15):
        P.cyl((x, 0.25, 2.05), 0.11, 0.3, 'z', PL, seg=14)
        flange(P, (x, 0.25, 1.93), 'z', 0.17, 0.04, nb=6, boltr=0.016, rb=0.13)
        P.sphere((x, 0.25, 2.26), 0.12, PL, seg=10, rings=6)
    P.cyl((-0.05, 0.25, 2.26), 0.1, 2.5, 'x', PL, seg=14, bev=0.004)
    for x, m in ((-0.65, RU), (0.7, RU)):
        P.cyl((x, 0.25, 2.26), 0.104, 0.3, 'x', m, seg=14, bev=0)
    for sx in (-1, 1):
        flange(P, (sx * 1.34, 0.25, 2.26), 'x', 0.16, 0.04, nb=6, boltr=0.016, rb=0.12)
    P.cyl((0.1, 0.25, 2.38), 0.03, 0.12, 'z', RD, seg=8)
    P.cyl((0.1, 0.25, 2.45), 0.07, 0.02, 'z', RD, seg=8) if False else None
    P.torus((0.1, 0.25, 2.4), 0.07, 0.014, 'z', RD, seg=10, rseg=4)
    # exhaust hood on right end
    P.box((1.75, 0.2, 1.4), (0.14, 0.9, 0.7), DK, bev=0.015)
    for i in range(6):
        P.box((1.83, 0.2, 1.15 + i * 0.1), (0.03, 0.8, 0.05), PL, bev=0.004, rot=(0, 18, 0))
    # side conduit + cable
    P.cyl((-1.74, 0.0, 1.1), 0.035, 1.5, 'z', BA, seg=8)
    pts = [(-1.7, 0.0, 0.95), (-1.9 + 0.1, -0.2, 0.7), (-1.72, -0.5, 0.35), (-1.55, -0.7, 0.04)]
    P.tube(catmull(pts, 5), 0.03, RB, seg=8)
    # nameplate & rust
    P.box((0.0, y - 0.03, 1.65), (0.6, 0.012, 0.12), YE, bev=0.002)
    P.box((0.6, 0.0, 1.905), (1.0, 0.6, 0.012), RU, bev=0.003)
    P.box((-1.0, -0.3, 1.905), (0.8, 0.5, 0.01), YE, bev=0.002) if False else None
    for sx in (-1, 1):
        P.box((sx * 1.7, -0.5, 1.5), (0.03, 0.2, 0.08), BA, bev=0.004)
    return P


# ================================================================ MACHINE B
@prop('machine_b')
def machine_b():
    P = Prop('machine_b')
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * 0.68, sy * 0.68
            P.box((x, y, 0.4), (0.14, 0.14, 0.8), DK, bev=0.012)
            P.box((x, y, 0.025), (0.3, 0.3, 0.05), DK, bev=0.01)
            for k in (-1, 1):
                bolt(P, (x + k * 0.1, y + k * 0.1, 0.06), 'z', 0.02, 0.02)
    for z in (0.68,):
        for s in (-1, 1):
            P.box((0, s * 0.68, z), (1.4, 0.08, 0.1), DK, bev=0.01)
            P.box((s * 0.68, 0, z), (0.08, 1.4, 0.1), DK, bev=0.01)
    prof = [(0, 0.5), (0.25, 0.5), (0.8, 0.72), (0.86, 0.82), (0.86, 2.2), (0.8, 2.35), (0.5, 2.46), (0.45, 2.5), (0.45, 2.55), (0, 2.55)]
    P.lathe(prof, m=PL, seg=28)
    P.lathe([(0.8655, 0.86), (0.8655, 1.25)], m=RU, seg=28)
    P.lathe([(0.8655, 1.75), (0.8655, 2.0)], m=RU, seg=28)
    for z in (1.0, 1.5, 2.1):
        P.band((0, 0, z), 0.862, 'z', DK, seg=28)
    P.band((0, 0, 0.78), 0.85, 'z', DK, seg=28, w=0.08)
    # motor stack
    P.box((0, 0, 2.77), (0.74, 0.74, 0.44), DK, bev=0.02, seg=2)
    P.cyl((0, 0, 3.08), 0.32, 0.24, 'z', PL, seg=20)
    for k in range(5):
        P.band((0, 0, 2.98 + k * 0.05), 0.322, 'z', DK, seg=20, w=0.04, h=0.012)
    P.sphere((0, 0, 3.2), 0.3, DK, sc=(1, 1, 0.3), seg=16, rings=6, half=True)
    P.box((0.25, 0.25, 2.98), (0.2, 0.22, 0.17), DK, bev=0.01)
    P.cyl((0.0, 0.0, 3.2 + 0.07), 0.05, 0.05, 'z', BA, seg=8) if False else None
    # manway
    flange(P, (0, -0.8, 1.45), 'y', 0.33, 0.06, nb=10, boltr=0.022, rb=0.26)
    P.cyl((0, -0.88, 1.45), 0.26, 0.04, 'y', DK, seg=20)
    P.box((0, -0.92, 1.45), (0.4, 0.04, 0.05), BA, bev=0.006)
    P.cyl((0, -0.92, 1.45), 0.04, 0.05, 'y', RD, seg=8)
    # sight glass port
    P.cyl((-0.45, -0.75, 1.95), 0.1, 0.12, 'y', DK, seg=14)
    P.cyl((-0.45, -0.82, 1.95), 0.07, 0.02, 'y', GL, seg=12, bev=0)
    # gauge panel
    P.box((0.52, -0.94, 1.95), (0.72, 0.09, 0.34), DK, bev=0.012)
    for sx in (-1, 1):
        P.box((0.52 + sx * 0.25, -0.8, 1.95), (0.06, 0.28, 0.06), DK, bev=0.006)
    for k in range(3):
        gauge(P, (0.52 + (k - 1) * 0.22, -1.0, 1.95), 0.085, 'y', -1, 15 + 50 * k)
    lamp(P, (0.52, -1.0, 2.2), GA, 0.04)
    P.box((0.52, -0.94, 2.2), (0.3, 0.06, 0.06), DK, bev=0.006) if False else None
    # ladder
    for sy in (-1, 1):
        P.box((1.0, sy * 0.22, 1.3), (0.045, 0.045, 2.5), BA, bev=0.006)
    for z in [0.15 + 0.25 * i for i in range(9)]:
        P.cyl((1.0, 0, z), 0.016, 0.44, 'y', BA, seg=8)
    for z in (0.6, 1.5, 2.3):
        for sy in (-1, 1):
            P.box((0.94, sy * 0.22, z), (0.14, 0.04, 0.06), DK, bev=0.006) if False else None
    for z in (1.0, 2.0):
        for sy in (-1, 1):
            P.box((0.92, sy * 0.22, z), (0.2, 0.05, 0.05), DK, bev=0.006)
    # outlet pipe + valve
    P.cyl((0, 0, 0.35), 0.09, 0.3, 'z', PL, seg=12)
    P.sphere((0, 0, 0.22), 0.11, PL, seg=10, rings=6)
    P.cyl((-0.5, 0, 0.22), 0.09, 0.8, 'x', PL, seg=12)
    flange(P, (-0.88, 0, 0.22), 'x', 0.14, 0.04, nb=6, boltr=0.014, rb=0.11)
    P.cyl((-0.55, 0, 0.3), 0.11, 0.14, 'x', DK, seg=12)
    P.cyl((-0.55, 0, 0.4), 0.03, 0.2, 'z', BA, seg=8)
    P.torus((-0.55, 0, 0.52), 0.11, 0.014, 'z', RD, seg=14, rseg=5)
    P.box((-0.55, 0, 0.52), (0.22, 0.02, 0.02), RD, bev=0.003)
    # hoses
    pts = [(0.28, 0.2, 3.0), (0.5, 0.35, 2.85), (0.8, 0.45, 2.55), (0.95, 0.5, 2.0), (0.82, 0.5, 1.4), (0.7, 0.45, 0.95)]
    P.tube(catmull(pts, 6), 0.04, RB, seg=8)
    pts = [(-0.3, 0.3, 2.52), (-0.55, 0.5, 2.7), (-0.9, 0.6, 2.4), (-0.95, 0.6, 1.6), (-0.82, 0.5, 1.0)]
    P.tube(catmull(pts, 6), 0.035, RD, seg=8)
    P.cyl((-0.82, 0.5, 0.95), 0.06, 0.1, 'z', BA, seg=8)
    P.cyl((0.7, 0.45, 0.9), 0.06, 0.1, 'z', BA, seg=8)
    # top vent pipe
    P.cyl((-0.25, 0.1, 2.7), 0.05, 0.3, 'z', BA, seg=10) if False else None
    hazard_z(P, 0.0, 0.3, 0.0, -0.69, (0.0, 0.0), 0) if False else None
    return P


# ============================================================== CONSOLE
@prop('control_console')
def control_console():
    P = Prop('control_console')
    th = math.atan2(0.3, 0.55)
    thd = math.degrees(th)
    poly = [(-0.4, 0.04), (0.45, 0.04), (0.45, 1.3), (0.1, 1.3), (0.1, 1.05), (-0.45, 0.75), (-0.4, 0.75)]
    P.extrude(poly, 'yz', -0.88, 0.88, PL, bev=0.012)
    P.box((0, 0, 0.02), (1.8, 0.9, 0.04), DK, bev=0.008)
    for sx in (-1, 1):
        P.box((sx * 0.9, 0, 0.75), (0.04, 0.88, 1.4), DK, bev=0.01) if False else None
        P.extrude([(-0.4, 0.04), (0.45, 0.04), (0.45, 1.3), (0.1, 1.3), (0.1, 1.05), (-0.45, 0.75), (-0.4, 0.75)], 'yz', sx * 0.88 - 0.02 + 0.02 * sx, sx * 0.9 + 0.0, DK, bev=0.004) if False else None
    P.box((0, -0.43, 0.38), (1.5, 0.03, 0.55), DK, bev=0.01)       # front lower door
    for sx in (-1, 1):
        P.box((sx * 0.45, -0.45, 0.38), (0.5, 0.02, 0.48), PL, bev=0.008)
        P.box((sx * 0.45, -0.46, 0.4), (0.04, 0.02, 0.18), BA, bev=0.003)
    hazard_x(P, -0.85, 0.85, 0.05, 0.14, -0.405, 0.01, 12)

    def sp(s, off=0.0):
        n = Vector((0, -math.sin(th), math.cos(th)))
        p = Vector((0, -0.45 + 0.55 * s, 0.75 + 0.3 * s))
        return p + n * off

    # panel strips
    for s in (0.22, 0.5, 0.78):
        p = sp(s, 0.004)
        P.box((-0.1, p.y, p.z), (1.5, 0.1, 0.01), DK, rot=(thd, 0, 0), bev=0.002)
    cols = [GR, GA, GG, GC, BA, DK, GA, GR, BA, GG]
    for r, s in enumerate((0.22, 0.5, 0.78)):
        for c in range(10):
            x = -0.78 + c * 0.13
            if (r, c) in ((2, 9), (2, 8)):
                continue
            p = sp(s, 0.02)
            m = cols[(c + r * 3) % len(cols)]
            P.cyl((x, p.y, p.z), 0.028, 0.026, 'z', m, seg=10, rot=(thd, 0, 0), bev=0.003)
    for c in range(4):
        p = sp(0.5, 0.035)
        P.cyl((0.8 - 0.0, p.y + 0.0, p.z), 0.0001, 0.0001, 'z', BA, seg=3) if False else None
    # big lever
    base = sp(0.5, 0.01)
    P.box((0.75, base.y, base.z), (0.2, 0.18, 0.05), DK, rot=(thd, 0, 0), bev=0.01)
    P.cyl((0.75, base.y, base.z + 0.04), 0.045, 0.06, 'z', BA, seg=10, rot=(thd, 0, 0))
    tip = Vector((0.75, base.y + 0.18, base.z + 0.3))
    P.tube([Vector((0.75, base.y, base.z + 0.05)), Vector((0.75, base.y + 0.09, base.z + 0.17)), tip], 0.022, BA, seg=8)
    P.sphere(tip, 0.06, RD, seg=10, rings=7)
    p = sp(0.5, 0.02)
    # small toggles
    for k in range(3):
        pp = sp(0.78, 0.02)
        P.cyl((0.4 + k * 0.1, pp.y, pp.z + 0.01), 0.012, 0.05, 'z', BA, seg=6, rot=(thd + 20, 0, 0)) if False else None
    # back riser: screens
    P.box((-0.3, 0.095, 1.18), (0.95, 0.04, 0.3), DK, bev=0.01)
    P.box((-0.3, 0.07, 1.18), (0.8, 0.012, 0.22), SC, bev=0.002)
    P.box((0.52, 0.095, 1.18), (0.4, 0.04, 0.3), DK, bev=0.01)
    P.box((0.52, 0.07, 1.18), (0.3, 0.012, 0.2), SC, bev=0.002)
    for k in range(4):
        gauge(P, (0.04 + 0.0, 0.0, 0.0), 0.0) if False else None
    P.box((0.0, 0.1, 1.32), (1.8, 0.35, 0.03), DK, bev=0.008)
    for k, m in enumerate((GR, GA, GR, GA, GR)):
        lamp(P, (-0.7 + k * 0.35, 0.0, 1.35), m, 0.035, 'z', 1) if False else P.sphere((-0.7 + k * 0.35, 0.2, 1.335), 0.035, m, seg=10, rings=6, half=True)
    for k in range(3):
        P.cyl((0.75 - 0.15 * k, 0.1, 1.07), 0.025, 0.02, 'y', GR if k == 1 else GA, seg=8, rot=(0, 0, 0)) if False else None
    P.box((-0.1, 0.46, 0.7), (1.0, 0.03, 0.5), DK, bev=0.006)
    for i in range(6):
        P.box((-0.1, 0.48, 0.5 + 0.08 * i), (0.9, 0.02, 0.03), PL, bev=0.003)
    return P


# ================================================================ GENERATOR
@prop('generator')
def generator():
    P = Prop('generator')
    # skid
    for sy in (-1, 1):
        P.box((0, sy * 0.62, 0.1), (2.6, 0.16, 0.2), DK, bev=0.015)
    for x in (-1.1, -0.3, 0.5, 1.2):
        P.box((x, 0, 0.2), (0.12, 1.4, 0.08), DK, bev=0.01)
    P.box((0, 0, 0.25), (2.5, 1.35, 0.06), PL, bev=0.01)
    # engine block (left)
    P.box((-0.6, 0, 0.72), (1.1, 0.85, 0.82), DK, bev=0.025, seg=2)
    P.box((-0.6, 0, 1.2), (1.0, 0.7, 0.16), PL, bev=0.02)
    for i in range(4):
        P.box((-0.9 + i * 0.2, 0, 1.33), (0.15, 0.5, 0.12), DK, bev=0.015)
        P.box((-0.9 + i * 0.2, 0, 1.4), (0.1, 0.4, 0.03), BA, bev=0.005)
    for i in range(5):
        P.box((-0.6, -0.43, 0.45 + i * 0.12), (0.9, 0.025, 0.06), PL, bev=0.005)
    P.box((-0.1, -0.2, 0.9), (0.3, 0.5, 0.35), RU, bev=0.015)
    # alternator drum
    P.cyl((0.6, 0, 0.88), 0.5, 1.0, 'x', PL, seg=24, bev=0.02)
    for x in (0.2, 0.45, 0.7, 0.95):
        P.torus((x, 0, 0.88), 0.5, 0.012, 'x', DK, seg=24, rseg=4)
    P.cyl((1.15, 0, 0.88), 0.43, 0.1, 'x', DK, seg=24)
    for k in range(8):
        P.box((1.19, 0.0, 0.88), (0.02, 0.76, 0.04), BA, rot=(k * 22.5, 0, 0), bev=0.003)
    P.cyl((1.21, 0, 0.88), 0.07, 0.04, 'x', BA, seg=10)
    # terminal box on alternator, cyan status strip
    P.box((0.6, 0.0, 1.43), (0.5, 0.35, 0.18), DK, bev=0.012)
    P.box((0.6, -0.178, 1.43), (0.42, 0.012, 0.035), GC, bev=0.002)
    P.box((0.6, -0.18, 1.35), (0.3, 0.012, 0.015), GC, bev=0.002) if False else None
    # control panel on front of alternator
    P.box((0.6, -0.52, 0.95), (0.44, 0.04, 0.34), DK, bev=0.01)
    P.box((0.6, -0.545, 1.0), (0.3, 0.012, 0.16), SC, bev=0.002)
    lamp(P, (0.48, -0.545, 0.83), GA, 0.022)
    lamp(P, (0.6, -0.545, 0.83), GC, 0.022)
    lamp(P, (0.72, -0.545, 0.83), GR, 0.022)
    # radiator at -x end
    P.box((-1.25, 0, 0.8), (0.12, 1.2, 1.0), DK, bev=0.015)
    for i in range(10):
        P.box((-1.33, 0, 0.35 + i * 0.1), (0.04, 1.1, 0.04), BA, bev=0.004)
    P.cyl((-1.2, 0, 0.8), 0.45, 0.04, 'x', DK, seg=20) if False else None
    for R_ in (0.2, 0.4):
        P.torus((-1.37, 0, 0.8), R_, 0.012, 'x', YE, seg=18, rseg=4) if False else None
    P.box((-1.38, 0, 1.33), (0.06, 1.2, 0.07), YE, bev=0.006)
    P.cyl((-1.25, -0.35, 1.35), 0.05, 0.1, 'z', RD, seg=10)
    # fuel tank on top-back
    P.box((0.25, 0.4, 1.62), (1.4, 0.4, 0.3), YE, bev=0.03, seg=2) if False else None
    P.cyl((-0.1, 0.38, 1.55), 0.17, 1.2, 'x', RU, seg=16, bev=0.015)
    P.cyl((0.15, 0.38, 1.73), 0.05, 0.06, 'z', BA, seg=8)
    P.cyl((0.15, 0.38, 1.77), 0.065, 0.025, 'z', RD, seg=8)
    for x in (-0.55, 0.35):
        P.box((x, 0.38, 1.4), (0.08, 0.38, 0.1), DK, bev=0.006)
    # exhaust
    P.cyl((-0.85, 0.05, 1.62), 0.07, 0.6, 'z', DK, seg=10)
    P.cyl((-0.85, 0.05, 1.7), 0.15, 0.5, 'z', RU, seg=14, bev=0.015)
    P.cyl((-0.85, 0.05, 1.93), 0.08, 0.3, 'z', DK, seg=10) if False else None
    P.cyl((-0.85, 0.05, 1.92), 0.1, 0.03, 'z', DK, seg=12)
    P.cyl((-0.85, 0.05, 1.89), 0.05, 0.1, 'z', BA, seg=8) if False else None
    # lifting frame (yellow)
    for sx in (-0.2, 1.2):
        for sy in (-1, 1):
            P.box((sx, sy * 0.58, 1.1), (0.06, 0.06, 1.6), YE, bev=0.008) if False else None
    for x in (-0.6, 1.0):
        P.torus((x, 0, 1.64), 0.08, 0.016, 'y', YE, seg=12, rseg=4) if False else None
    P.box((-0.55, -0.3, 1.6), (0.06, 0.06, 0.03), YE, bev=0.005)
    # cables out the front
    pts = [(0.9, -0.52, 1.1), (1.05, -0.6, 0.85), (0.95, -0.72, 0.45), (0.6, -0.72, 0.07), (0.2, -0.7, 0.04), (-0.3, -0.72, 0.04)]
    P.tube(catmull(pts, 6), 0.04, RB, seg=8)
    pts = [(0.3, -0.52, 1.05), (0.2, -0.62, 0.8), (0.1, -0.7, 0.4), (-0.4, -0.7, 0.08), (-0.8, -0.7, 0.04)]
    P.tube(catmull(pts, 6), 0.03, RD, seg=8)
    P.cyl((1.0, -0.52, 1.06), 0.05, 0.1, 'y', BA, seg=8)
    hazard_x(P, -1.2, 1.2, 0.15, 0.24, -0.71, 0.01, 12) if False else None
    return P


# ================================================================ TANKS
@prop('tank_vertical')
def tank_vertical():
    P = Prop('tank_vertical')
    for k in range(6):
        a = math.radians(60 * k + 30)
        x, y = 0.95 * math.cos(a), 0.95 * math.sin(a)
        P.box((x, y, 0.4), (0.18, 0.18, 0.8), DK, bev=0.012)
        P.box((x, y, 0.03), (0.34, 0.34, 0.06), DK, bev=0.01)
        bolt(P, (x, y, 0.07), 'z', 0.03, 0.02)
        P.box((x * 1.02, y * 1.02, 0.8), (0.28, 0.28, 0.06), DK, bev=0.008, rot=(0, 0, math.degrees(a)))
    prof = [(0, 0.72), (0.5, 0.72), (1.1, 0.8), (1.2, 0.9), (1.2, 4.3), (1.1, 4.55), (0.8, 4.75), (0.5, 4.88), (0.0, 4.9)]
    P.lathe(prof, m=PL, seg=32)
    P.lathe([(1.2035, 0.9), (1.2035, 1.5)], m=RU, seg=32)
    P.lathe([(1.2035, 3.3), (1.2035, 4.0)], m=RU, seg=32)
    for z in (1.5, 2.3, 3.1, 3.9):
        P.band((0, 0, z), 1.2, 'z', DK, seg=32, w=0.08, h=0.03)
    P.band((0, 0, 0.92), 1.2, 'z', DK, seg=32, w=0.08, h=0.03)
    # top manhole + vent
    P.cyl((0.3, 0.1, 4.92), 0.38, 0.1, 'z', DK, seg=20)
    P.cyl((0.3, 0.1, 4.99), 0.3, 0.05, 'z', PL, seg=20)
    for k in range(8):
        a = 2 * math.pi * k / 8
        bolt(P, (0.3 + 0.34 * math.cos(a), 0.1 + 0.34 * math.sin(a), 5.0), 'z', 0.025, 0.02)
    P.cyl((-0.45, 0.2, 4.95), 0.07, 0.14, 'z', BA, seg=10)
    P.sphere((-0.45, 0.2, 5.0), 0.09, DK, seg=10, rings=6, half=True) if False else None
    # side manway front-right
    flange(P, (-0.6, -1.05, 2.0), 'y', 0.3, 0.05, nb=8, boltr=0.022, rb=0.24) if False else None
    # ladder + cage on front
    lx = -0.65
    for sx in (-1, 1):
        P.box((lx + sx * 0.2, -1.38, 2.5), (0.05, 0.05, 4.1), BA, bev=0.006)
    for z in [0.45 + 0.28 * i for i in range(15)]:
        P.cyl((lx, -1.38, z), 0.016, 0.4, 'x', BA, seg=8)
    for z in (1.0, 2.2, 3.4, 4.2):
        for sx in (-1, 1):
            a = math.atan2(-1.38, lx)
            P.box((lx + sx * 0.2, -1.28, z), (0.06, 0.2, 0.05), DK, bev=0.006)
    for z in (2.5, 3.2, 3.9):
        P.torus((lx, -1.38, z), 0.36, 0.014, 'y', DK, seg=14, rseg=4) if False else None
    # pipe stubs
    P.cyl((1.4, 0.0, 1.2), 0.1, 0.5, 'x', PL, seg=12)
    flange(P, (1.65, 0.0, 1.2), 'x', 0.16, 0.04, nb=6, boltr=0.016, rb=0.125)
    P.cyl((0.9, 0.9, 1.8), 0.08, 0.4, 'x', PL, seg=12, rot=(0, 0, 45))
    P.cyl((-1.3, 0.2, 0.95), 0.12, 0.35, 'x', PL, seg=12)
    flange(P, (-1.42, 0.2, 0.95), 'x', 0.18, 0.04, nb=6, boltr=0.016, rb=0.14)
    P.cyl((-1.25, 0.2, 1.1), 0.03, 0.2, 'z', BA, seg=8)
    P.torus((-1.25, 0.2, 1.22), 0.08, 0.012, 'z', RD, seg=12, rseg=4)
    # faded hazard diamond on front
    P.extrude([(0, -0.5), (0.5, 0), (0, 0.5), (-0.5, 0)], 'xz', -1.255, -1.12, YE, c=(0.45, 0, 2.7), bev=0.0)
    P.extrude([(0, -0.4), (0.4, 0), (0, 0.4), (-0.4, 0)], 'xz', -1.265, -1.12, PL, c=(0.45, 0, 2.7))
    P.extrude([(0, -0.33), (0.33, 0), (0, 0.33), (-0.33, 0)], 'xz', -1.275, -1.12, YE, c=(0.45, 0, 2.7))
    P.box((0.45, -1.285, 2.74), (0.07, 0.02, 0.26), DK, bev=0.003)
    P.box((0.45, -1.285, 2.52), (0.07, 0.02, 0.07), DK, bev=0.003)
    P.box((0.45, -1.285, 2.7), (0.7, 0.012, 0.02), RU, bev=0.002) if False else None
    return P


@prop('tank_horizontal')
def tank_horizontal():
    P = Prop('tank_horizontal')
    zc = 1.2
    prof = [(0, 0), (0.4, 0.07), (0.7, 0.18), (0.85, 0.28), (0.9, 0.38), (0.9, 4.12), (0.85, 4.22), (0.7, 4.32), (0.4, 4.43), (0, 4.5)]
    P.lathe(prof, c=(-2.25, 0, zc), axis='x', m=PL, seg=32)
    for x0, L in ((-1.6, 1.0), (0.2, 1.1), (1.5, 0.6)):
        P.lathe([(0.9035, x0), (0.9035, x0 + L)], c=(0, 0, zc), axis='x', m=RU, seg=32) if False else None
    P.cyl((-1.1, 0, zc), 0.9035, 0.9, 'x', RU, seg=32, bev=0.0, caps=False)
    P.cyl((1.4, 0, zc), 0.9035, 0.7, 'x', RU, seg=32, bev=0.0, caps=False)
    for x in (-1.95, -0.7, 0.7, 1.95):
        P.band((x, 0, zc), 0.9, 'x', DK, seg=32, w=0.07, h=0.025)
    for x in (-1.45, 1.45):
        # saddle
        pts = []
        poly = [(-0.8, 0.0), (0.8, 0.0), (0.8, 0.55), (0.55, 0.62), (0.0, 0.3), (-0.55, 0.62), (-0.8, 0.55)]
        P.extrude([(-0.65, 0.0), (0.65, 0.0), (0.65, 0.35), (0.5, 0.43), (0.0, 0.18), (-0.5, 0.43), (-0.65, 0.35)], 'yz', x - 0.15, x + 0.15, CO, bev=0.01)
        P.cyl((x, 0, zc), 0.93, 0.12, 'x', DK, seg=32, caps=False, bev=0) if False else None
        P.band((x, 0, zc), 0.92, 'x', DK, seg=32, w=0.1, h=0.03)
        P.box((x, 0, 0.04), (0.5, 1.5, 0.08), CO, bev=0.01)
        for sy in (-1, 1):
            P.box((x, sy * 0.75, 0.3), (0.06, 0.1, 0.5), DK, bev=0.008)
            bolt(P, (x, sy * 0.75, 0.1), 'z', 0.03, 0.04)
    # manhole on top
    P.cyl((0.4, 0, zc + 0.9), 0.3, 0.1, 'z', DK, seg=18)
    P.cyl((0.4, 0, zc + 0.96), 0.24, 0.04, 'z', PL, seg=18)
    for k in range(8):
        a = 2 * math.pi * k / 8
        bolt(P, (0.4 + 0.27 * math.cos(a), 0.27 * math.sin(a), zc + 0.98), 'z', 0.022, 0.02)
    P.box((0.4, 0, zc + 1.0), (0.3, 0.05, 0.04), BA, bev=0.005)
    # nozzles
    P.cyl((-1.2, 0.0, zc + 0.95), 0.06, 0.2, 'z', PL, seg=10)
    flange(P, (-1.2, 0.0, zc + 1.06), 'z', 0.11, 0.035, nb=6, boltr=0.014, rb=0.085)
    P.cyl((1.6, -0.5, zc + 0.7), 0.06, 0.4, 'z', PL, seg=10, rot=(0, 0, 0)) if False else None
    P.cyl((-2.3, 0, zc), 0.1, 0.2, 'x', PL, seg=12)
    flange(P, (-2.4, 0, zc), 'x', 0.17, 0.04, nb=6, boltr=0.016, rb=0.13)
    P.cyl((2.3, 0, zc), 0.1, 0.2, 'x', PL, seg=12)
    flange(P, (2.4, 0, zc), 'x', 0.17, 0.04, nb=6, boltr=0.016, rb=0.13)
    # fill pipe + valve in the front
    P.cyl((0.1, -0.95, zc - 0.5), 0.07, 0.3, 'y', PL, seg=10) if False else None
    P.cyl((1.0, -0.88, zc - 0.3), 0.07, 0.3, 'y', PL, seg=10)
    P.cyl((1.0, -1.05, zc - 0.3), 0.1, 0.14, 'y', DK, seg=12)
    P.cyl((1.0, -1.05, zc - 0.17), 0.025, 0.12, 'z', BA, seg=8)
    P.torus((1.0, -1.05, zc - 0.1), 0.09, 0.013, 'z', RD, seg=12, rseg=4)
    # sight gauge
    P.cyl((-0.4, -0.93, zc + 0.1), 0.02, 0.8, 'z', GL, seg=8, bev=0)
    for z in (-0.3, 0.5):
        P.box((-0.4, -0.93, zc + z), (0.06, 0.06, 0.06), DK, bev=0.006)
    P.box((-0.4, -0.95, zc + 0.1), (0.08, 0.02, 0.9), DK, bev=0.004) if False else None
    # hazard sticker
    P.box((0.5, -0.9, zc + 0.35), (0.5, 0.01, 0.35), YE, rot=(0, 0, 0), bev=0.002, ) if False else None
    return P


# ================================================================ FURNACE
@prop('furnace')
def furnace():
    P = Prop('furnace')
    y0, y1 = -0.3, 1.75
    yc, D = (y0 + y1) / 2, y1 - y0
    # plinth
    P.box((0, yc, 0.15), (4.2, D + 0.1, 0.3), CO, bev=0.03, seg=2)
    # main brick body: back mass, upper wall
    P.box((0, 1.15, 2.6), (4.0, 1.2, 4.6), CO, bev=0.03, seg=2)               # y 0.55..1.75
    # piers (left/right of the mouth) y -0.5..0.55
    for sx in (-1, 1):
        P.box((sx * 1.45, (y0 + 0.55) / 2, 1.55), (1.1, 1.05, 2.5), CO, bev=0.025, seg=2)
    # upper wall front (above arch)
    P.box((0, (y0 + 0.55) / 2, 3.4), (4.0, 1.05, 1.9), CO, bev=0.03, seg=2)
    # spandrel next to arch
    for sx in (-1, 1):
        P.box((sx * 1.1, (y0 + 0.55) / 2, 2.05), (0.5, 1.05, 1.5), CO, bev=0.02)
    # arch ring (bricks as wedges), extruded along Y
    for poly in arch_pts(0, 1.35, 0.9, 1.22, 0, 180, 12):
        P.extrude(poly, 'xz', y0, 0.55, PL, bev=0.0)
    # steel lintel plates at the arch face
    for poly in arch_pts(0, 1.35, 0.9, 1.05, 0, 180, 12):
        P.extrude(poly, 'xz', y0 - 0.04, y0, DK, bev=0.0)
    # interior: dark side walls, back glow wall, glowing hearth
    P.box((0, 0.6, 1.05), (1.8, 0.08, 1.2), GF, bev=0.0) if False else None
    P.box((0, 0.62, 1.55), (1.8, 0.06, 2.0), GF, bev=0.0)
    P.box((0, (y0 + 0.6) / 2, 0.33), (1.84, 1.1, 0.06), GF, bev=0.0)
    P.box((0, (y0 + 0.6) / 2, 0.2), (1.9, 1.15, 0.2), DK, bev=0.0)
    for sx in (-1, 1):
        P.box((sx * 0.92, (y0 + 0.6) / 2, 0.8), (0.04, 1.1, 1.0), DK, bev=0.0)
    # glow lintel bleed (interior ceiling)
    P.box((0, (y0 + 0.6) / 2, 2.3), (1.4, 1.0, 0.05), GF, bev=0.0) if False else None
    # sill + slag spout and channel
    P.box((0, y0 - 0.2, 0.3), (1.2, 0.4, 0.06), DK, bev=0.01)
    P.box((0, y0 - 0.2, 0.34), (0.5, 0.4, 0.03), GF, bev=0.0)
    P.extrude([(y0 - 0.4, 0.31), (y0 - 0.9, 0.04), (y0 - 0.9, 0.0), (y0 - 0.4, 0.0)], 'yz', -0.3, 0.3, DK, bev=0.0)
    P.extrude([(y0 - 0.4, 0.34), (y0 - 0.9, 0.065), (y0 - 0.9, 0.04), (y0 - 0.4, 0.31)], 'yz', -0.14, 0.14, GF, bev=0.0)
    ch0 = y0 - 0.9
    P.box((0, (ch0 - 1.75) / 2, 0.02), (0.34, ch0 + 1.75 + 0.0 if False else abs(-1.75 - ch0) * -1 + 0.0 + (ch0 - -1.75) * 0 + abs(ch0 + 1.75), 0.04), DK, bev=0.004) if False else None
    P.box((0, (ch0 - 1.75) / 2, 0.02), (0.36, abs(1.75 + ch0), 0.04), DK, bev=0.004)
    P.box((0, (ch0 - 1.75) / 2, 0.042), (0.24, abs(1.75 + ch0), 0.012), GF, bev=0.0)
    for sx in (-1, 1):
        P.box((sx * 0.2, (ch0 - 1.75) / 2, 0.045), (0.05, abs(1.75 + ch0), 0.05), DK, bev=0.006)
    # steel bands and frame
    for z in (0.32, 2.75, 4.2):
        P.box((0, y0 - 0.03, z), (4.04, 0.06, 0.12), PL, bev=0.01)
    for sx in (-1, 1):
        P.box((sx * 2.03, yc, 2.3), (0.08, D, 4.4), PL, bev=0.015)
        P.box((sx * 1.28, y0 - 0.03, 1.35), (0.1, 0.06, 2.6), PL, bev=0.01)
        for z in [0.6 + 0.4 * i for i in range(6)]:
            P.cyl((sx * 2.0, y0 - 0.06, z), 0.025, 0.02, 'y', BA, seg=6, bev=0) if False else None
    # tie rods + end plates
    for z in (0.95, 3.65):
        P.cyl((0, y0 - 0.09, z), 0.032, 4.4, 'x', BA, seg=10, bev=0)
        for sx in (-1, 1):
            P.box((sx * 2.14, y0 - 0.09, z), (0.1, 0.2, 0.36), DK, bev=0.01)
            hexnut(P, (sx * 2.27, y0 - 0.09, z), 0.07, 0.07, DK) if False else P.cyl((sx * 2.2, y0 - 0.09, z), 0.07, 0.08, 'x', DK, seg=6)
    # buttresses along sides
    for sx in (-1, 1):
        for yy in (-0.15, 1.15):
            P.extrude([(0, 0), (0.22, 0), (0.22, 2.6), (0.1, 3.4), (0, 3.4)] if sx > 0 else [(-0.22, 0), (0, 0), (0, 3.4), (-0.1, 3.4), (-0.22, 2.6)], 'xz', yy - 0.3, yy + 0.3, CO, c=(sx * 2.02 + (0 if sx > 0 else 0), 0, 0.0), bev=0.0)
            P.box((sx * 2.2, yy, 0.12), (0.5, 0.7, 0.24), CO, bev=0.02) if False else None
    # door frame (guides), door, counterweights
    for sx in (-1, 1):
        P.box((sx * 1.36, y0 - 0.2, 2.5), (0.2, 0.22, 5.0), DK, bev=0.015, seg=2)
        P.box((sx * 1.36, y0 - 0.2, 0.05), (0.4, 0.4, 0.1), DK, bev=0.01)
    P.box((0, y0 - 0.2, 4.88), (2.9, 0.26, 0.24), DK, bev=0.015, seg=2)
    P.cyl((0.0, y0 - 0.2, 4.72), 0.1, 2.6, 'x', BA, seg=12, bev=0)
    for sx in (-1, 1):
        P.cyl((sx * 0.9, y0 - 0.2, 4.72), 0.2, 0.1, 'x', DK, seg=16)
        P.cyl((sx * 1.55, y0 - 0.2, 4.72), 0.15, 0.1, 'x', DK, seg=14) if False else None
    # door slab (raised above the mouth)
    P.box((0, y0 - 0.25, 3.75), (2.4, 0.16, 1.5), DK, bev=0.02, seg=2)
    P.box((0, y0 - 0.34, 3.75), (2.1, 0.03, 1.2), PL, bev=0.01)
    for sx in (-1, 1):
        for sz in (-1, 1):
            bolt(P, (sx * 0.95, y0 - 0.37, 3.75 + sz * 0.5), 'y', 0.035, 0.03)
    P.box((0, y0 - 0.355, 3.75), (1.6, 0.015, 0.2), RU, bev=0.003)
    P.box((0.0, y0 - 0.4, 3.2), (0.8, 0.06, 0.08), BA, bev=0.006) if False else None
    for sx in (-1, 1):
        P.tube([(sx * 0.9, y0 - 0.2, 4.5), (sx * 0.9, y0 - 0.2, 4.75), (sx * 1.15, y0 - 0.2, 4.9), (sx * 1.7, y0 - 0.2, 4.82), (sx * 1.7, y0 - 0.2, 2.9)], 0.028, DK, seg=6, caps=False) if False else None
        # chain to counterweight (outside guides)
        P.tube([(sx * 0.9, y0 - 0.2, 4.5), (sx * 0.9, y0 - 0.2, 4.72)], 0.03, DK, seg=6, caps=False)
        P.tube(catmull([(sx * 0.9, y0 - 0.2, 4.72), (sx * 1.1, y0 - 0.2, 4.93), (sx * 1.4, y0 - 0.2, 4.93)], 3), 0.03, DK, seg=6, caps=False)
        chain(P, sx * 1.62, y0 - 0.2, 2.9, 4.8, 0.14, 0.02, DK, 0.05)
        P.box((sx * 1.62, y0 - 0.2, 2.3), (0.4, 0.4, 1.1), RU, bev=0.02, seg=2)
        P.box((sx * 1.62, y0 - 0.2, 2.9), (0.2, 0.2, 0.1), DK, bev=0.01)
    # chimney: hood + stack to z=7
    P.box((0, 1.1, 4.7), (3.0, 1.3, 0.55), CO, bev=0.03, seg=1)
    P.box((0, 1.1, 4.99), (3.1, 1.4, 0.08), DK, bev=0.015)
    P.lathe([(0, 4.95), (0.95, 4.95), (0.95, 5.2), (0.7, 5.8), (0.6, 6.2), (0.58, 6.9), (0.66, 6.95), (0.66, 7.0), (0.5, 7.0), (0.5, 6.9), (0, 6.9)], c=(0, 1.1, 0), m=CO, seg=24) if False else None
    P.lathe([(0, 4.95), (0.8, 4.95), (0.78, 5.2), (0.58, 5.6), (0.52, 6.0), (0.5, 6.9), (0.6, 6.93), (0.6, 7.0), (0.44, 7.0), (0.44, 6.95), (0, 6.95)], c=(0, 0.95, 0), m=CO, seg=24)
    for z, r in ((5.25, 0.77), (5.7, 0.56), (6.3, 0.51), (6.75, 0.505)):
        P.band((0, 0.95, z), r, 'z', DK, seg=24, w=0.09, h=0.03)
    P.lathe([(0.515, 6.0), (0.515, 6.5)], c=(0, 0.95, 0), m=RU, seg=24)
    # steel straps on the hood
    for sx in (-1, 1):
        P.box((sx * 1.2, 1.1, 4.7), (0.12, 1.34, 0.6), PL, bev=0.01)
    # side pipes
    P.tube(catmull([(2.0, 0.9, 2.2), (2.3, 0.9, 2.2), (2.4, 0.9, 2.6), (2.4, 0.9, 4.0), (2.2, 0.9, 4.4)], 4), 0.1, DK, seg=12, caps=False) if False else None
    P.cyl((-2.28, 1.1, 2.2), 0.1, 3.6, 'z', DK, seg=12) if False else None
    # glow hints on piers (vents)
    for sx in (-1, 1):
        P.box((sx * 1.55, y0 - 0.02, 0.7), (0.5, 0.03, 0.2), DK, bev=0.005)
        P.box((sx * 1.55, y0 - 0.035, 0.7), (0.4, 0.012, 0.08), GF, bev=0.0)
    # brick courses (raised thin lines) on front and top
    for z in [2.6 + 0.3 * i for i in range(6)]:
        P.box((0, y0 - 0.005, z), (3.96, 0.012, 0.014), DK, bev=0.0)
    for sx in (-1, 1):
        for z in [0.4 + 0.3 * i for i in range(7)]:
            P.box((sx * 1.55, y0 - 0.005, z), (0.98, 0.012, 0.014), DK, bev=0.0)
    for y in [0.0 + 0.3 * i for i in range(6)]:
        P.box((0, y, 4.205), (3.96, 0.014, 0.012), DK, bev=0.0) if y < 0.9 or abs(y - 1.1) > 0.8 else None
    for sx in (-1, 1):
        P.box((sx * 1.2, 0.55, 4.215), (0.22, 1.9, 0.04), PL, bev=0.006)
        P.box((sx * 0.5, 0.9, 4.215), (0.5, 0.6, 0.03), RU, bev=0.0) if False else None
    P.box((-1.5, 0.15, 4.22), (0.8, 0.7, 0.04), DK, bev=0.008)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bolt(P, (-1.5 + sx * 0.3, 0.15 + sy * 0.28, 4.25), 'z', 0.03, 0.02)
    P.box((1.55, 0.3, 4.215), (0.8, 0.5, 0.012), RU, bev=0.0)
    P.cyl((1.5, 1.3, 4.3), 0.07, 0.2, 'z', BA, seg=8)
    P.cyl((-1.5, 1.4, 4.3), 0.07, 0.2, 'z', BA, seg=8)
    P.torus((1.5, 1.3, 4.4), 0.06, 0.016, 'z', DK, seg=10, rseg=4)
    # warning label
    P.box((-1.6, y0 - 0.03, 1.7), (0.5, 0.01, 0.35), YE, bev=0.002)
    P.box((-1.6, y0 - 0.04, 1.7), (0.08, 0.01, 0.25), DK, bev=0.002)
    return P


@prop('crucible')
def crucible():
    P = Prop('crucible')
    z0 = 2.2
    prof = [(0, z0), (0.45, z0), (0.65, z0 + 0.12), (0.78, z0 + 0.5), (0.82, z0 + 1.08), (0.82, z0 + 1.12), (0.72, z0 + 1.12),
            (0.7, z0 + 0.5), (0.58, z0 + 0.25), (0, z0 + 0.22)]
    P.lathe(prof, m=DK, seg=28)
    P.lathe([(0.8, z0 + 0.7), (0.835, z0 + 1.0)], m=RU, seg=28) if False else None
    P.lathe([(0.8225, z0 + 0.7), (0.8225, z0 + 1.1)], m=RU, seg=28)
    P.cyl((0, 0, z0 + 1.0), 0.71, 0.02, 'z', GF, seg=28, bev=0)
    for z in (z0 + 0.3, z0 + 0.65):
        P.torus((0, 0, z), 0.73 if z < z0 + 0.5 else 0.795, 0.03, 'z', BA, seg=28, rseg=5) if False else None
    P.band((0, 0, z0 + 0.35), 0.74, 'z', BA, seg=28, w=0.08, h=0.03)
    P.band((0, 0, z0 + 1.1), 0.82, 'z', BA, seg=28, w=0.08, h=0.035)
    # pour spout
    P.extrude([(-0.2, 0), (0.2, 0), (0.12, 0.2), (-0.12, 0.2)], 'xy', z0 + 0.95, z0 + 1.1, DK, c=(0, -0.78, 0), bev=0.0) if False else None
    P.box((0, -0.85, z0 + 1.07), (0.34, 0.2, 0.06), DK, bev=0.01)
    # trunnions and bail
    for sx in (-1, 1):
        P.cyl((sx * 0.9, 0, z0 + 0.72), 0.075, 0.24, 'x', BA, seg=12)
        P.box((sx * 0.82, 0, z0 + 0.72), (0.12, 0.34, 0.2), DK, bev=0.01)
        P.tube([(sx * 0.98, 0, z0 + 0.72), (sx * 0.9, 0, z0 + 1.6), (sx * 0.05, 0, z0 + 2.35)], 0.04, DK, seg=8)
    P.torus((0, 0, z0 + 2.4), 0.14, 0.035, 'y', BA, seg=14, rseg=5)
    P.box((0, 0, z0 + 2.27), (0.3, 0.14, 0.12), DK, bev=0.01)
    chain(P, 0, 0, z0 + 2.5, 6.9, 0.17, 0.028, DK, 0.07)
    P.box((0, 0, 6.96), (0.5, 0.3, 0.08), DK, bev=0.01)
    return P


# ================================================================ CONVEYORS
def conveyor_core(P, x0, x1, legs, with_far_roller=True, roller_far=True):
    L = x1 - x0
    xc = (x0 + x1) / 2
    for sy in (-1, 1):
        P.box((xc, sy * 0.69, 0.78), (L, 0.1, 0.24), DK, bev=0.012, seg=2)
        P.box((xc, sy * 0.66, 0.95), (L - 0.1, 0.035, 0.1), BA, bev=0.006)
        P.box((xc, sy * 0.72, 0.9), (L - 0.2, 0.03, 0.04), YE, bev=0.004) if False else None
    for x in legs:
        for sy in (-1, 1):
            P.box((x, sy * 0.69, 0.33), (0.09, 0.09, 0.66), PL, bev=0.01)
            P.box((x, sy * 0.69, 0.025), (0.22, 0.22, 0.05), DK, bev=0.01)
            bolt(P, (x + 0.07, sy * 0.69 + 0.07, 0.06), 'z', 0.02, 0.02)
        P.box((x, 0, 0.3), (0.06, 1.3, 0.06), DK, bev=0.006)
        P.box((x, 0, 0.66), (0.09, 1.32, 0.06), DK, bev=0.006)
    # support deck & belt strip
    P.box((xc, 0, 0.9), (L - 0.1, 1.28, 0.03), DK, bev=0.004)


@prop('conveyor')
def conveyor():
    P = Prop('conveyor')
    conveyor_core(P, -2.0, 2.0, (-1.75, -0.6, 0.6, 1.75))
    # belt top strip, separate flat surface
    P.box((0, 0, 0.945), (3.8, 1.2, 0.03), BE, bev=0.0)
    # side belt wrap and end rollers
    for sx in (-1, 1):
        P.cyl((sx * 1.9, 0, 0.86), 0.1, 1.34, 'y', BA, seg=18, bev=0.004)
        P.cyl((sx * 1.9, 0, 0.86), 0.04, 1.5, 'y', DK, seg=10, bev=0.0)
        for sy in (-1, 1):
            P.box((sx * 1.9, sy * 0.69, 0.86), (0.28, 0.06, 0.28), DK, bev=0.01) if False else None
            P.cyl((sx * 1.9, sy * 0.74, 0.86), 0.075, 0.04, 'y', DK, seg=12)
    for sy in (-1, 1):
        P.box((0, sy * 0.66, 0.985), (3.7, 0.04, 0.025), YE, bev=0.004)
    for x in (-1.5, -0.5, 0.5, 1.5):
        for sy in (-1, 1):
            P.box((x, sy * 0.72, 0.9), (0.16, 0.05, 0.2), DK, bev=0.006)
    # idler rollers
    for k in range(-4, 5):
        P.cyl((k * 0.4, 0, 0.88), 0.032, 1.3, 'y', BA, seg=8, bev=0)
    # photo-eye sensor on bracket
    P.box((0.3, -0.74, 0.96), (0.06, 0.06, 0.12), DK, bev=0.0)
    P.box((0.3, -0.74, 1.12), (0.1, 0.1, 0.07), PL, bev=0.008) if False else None
    lamp(P, (0.3, -0.74, 1.0), GR, 0.025, 'y', 1)
    P.box((0.3, 0.74, 0.96), (0.06, 0.06, 0.12), DK, bev=0.0)
    P.box((-1.2, 0.0, 0.62), (0.5, 0.35, 0.18), PL, bev=0.01) if False else None
    P.box((1.0, 0.74, 0.55), (0.3, 0.1, 0.2), DK, bev=0.01)
    lamp(P, (1.0, 0.8, 0.6), GA, 0.025, 'y', 1)
    # cable run
    pts = [(1.0, 0.8, 0.5), (1.1, 0.78, 0.3), (1.5, 0.74, 0.15), (2.0, 0.74, 0.04)]
    P.tube(catmull(pts, 4), 0.02, RB, seg=6) if False else None
    for x in (-1.1, 0.0, 1.1):
        P.box((x, -0.7, 0.9), (0.28, 0.04, 0.12), PL, bev=0.006) if False else None
    return P


@prop('conveyor_end')
def conveyor_end():
    P = Prop('conveyor_end')
    conveyor_core(P, -0.6, 0.6, (-0.45, 0.4))
    P.box((-0.05, 0, 0.945), (1.0, 1.2, 0.03), BE, bev=0.0)
    P.cyl((0.5, 0, 0.86), 0.1, 1.34, 'y', BA, seg=18, bev=0.004)
    P.cyl((0.5, 0, 0.86), 0.04, 1.5, 'y', DK, seg=10, bev=0.0)
    for sy in (-1, 1):
        P.cyl((0.5, sy * 0.74, 0.86), 0.075, 0.04, 'y', DK, seg=12)
    P.cyl((-0.55, 0, 0.88), 0.05, 1.3, 'y', BA, seg=10)
    # end cap plate
    P.box((0.62, 0, 0.8), (0.04, 1.4, 0.3), DK, bev=0.008)
    # motor + gearbox under the frame
    P.cyl((-0.1, 0.1, 0.42), 0.2, 0.7, 'y', PL, seg=18, bev=0.012)
    for k in range(5):
        P.torus((-0.1, -0.12 + k * 0.1, 0.42), 0.205, 0.012, 'y', DK, seg=18, rseg=4)
    P.box((-0.1, -0.5, 0.42), (0.4, 0.22, 0.38), DK, bev=0.02, seg=2)
    P.cyl((-0.1, 0.5, 0.42), 0.17, 0.12, 'y', DK, seg=14)
    P.box((-0.1, 0.0, 0.62), (0.18, 0.25, 0.08), DK, bev=0.008) if False else None
    P.box((-0.1, 0.12, 0.64), (0.2, 0.24, 0.14), DK, bev=0.012)
    lamp(P, (-0.1, 0.12, 0.72), GA, 0.03, 'z', 1) if False else P.sphere((-0.1, 0.12, 0.71), 0.035, GA, seg=10, rings=6, half=True)
    # chain drive + guard on the -y side
    P.box((0.15, -0.76, 0.62), (0.9, 0.07, 0.4), YE, bev=0.015, seg=2)
    for k in range(4):
        P.box((0.15, -0.8, 0.5 + k * 0.08), (0.7, 0.012, 0.03), DK, bev=0.002)
    for sx in (-1, 1):
        for sz in (-1, 1):
            bolt(P, (0.15 + sx * 0.4, -0.8, 0.62 + sz * 0.15), 'y', 0.02, 0.02)
    P.cyl((0.5, -0.8, 0.86), 0.12, 0.04, 'y', YE, seg=14)
    # guard cage over the head roller
    for sy in (-1, 1):
        P.box((0.5, sy * 0.45, 1.08), (0.22, 0.03, 0.2), YE, bev=0.005) if False else None
    for sy in (-0.5, 0, 0.5):
        P.tube([(0.35, sy, 0.97), (0.5, sy, 1.04), (0.65, sy, 0.97)], 0.014, YE, seg=6)
    P.cyl((0.5, 0, 1.04), 0.014, 1.0, 'y', YE, seg=6)
    return P
