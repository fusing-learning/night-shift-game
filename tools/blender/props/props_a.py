"""Containers & clutter."""
import math
from mathutils import Vector, Matrix
from lib import *


# ------------------------------------------------------------ reusable bits
def draw_barrel(P, body=PL, dense=False):
    prof = [(0, 0), (0.25, 0), (0.275, 0.025)]
    z = 0.12
    while z < 0.92:
        prof.append((0.28, z))
        z += 0.1 if dense else 0.27
    prof += [(0.28, 0.925), (0.30, 0.935), (0.30, 0.95), (0.262, 0.95), (0.262, 0.935), (0, 0.935)]
    P.lathe(prof, m=body, seg=20 if dense else 14)
    P.lathe([(0.2835, 0.0), (0.2835, 0.16)], m=RU, seg=20 if dense else 14)   # rusty lower skirt (thin shell)
    for z in (0.3, 0.64):
        P.band((0, 0, z), 0.28, 'z', DK, seg=20 if dense else 14, w=0.045, h=0.02)
    P.cyl((0.12, 0.06, 0.95), 0.038, 0.03, 'z', BA, seg=8)
    P.cyl((-0.1, -0.12, 0.95), 0.025, 0.025, 'z', BA, seg=8)
    P.torus((0.12, 0.06, 0.955), 0.038, 0.007, 'z', DK, seg=8, rseg=4)
    P.cyl((0, 0, 0.945), 0.2, 0.012, 'z', RU, seg=16, bev=0)


@prop('barrel')
def barrel():
    P = Prop('barrel')
    draw_barrel(P, dense=True)
    P.dent((0.28, 0.0, 0.5), 0.22, 0.03, (-1, 0, 0))
    return P


@prop('barrel_tipped')
def barrel_tipped():
    P = Prop('barrel_tipped')
    draw_barrel(P, RU, dense=True)
    P.dent((0.28, 0.0, 0.5), 0.22, 0.03, (-1, 0, 0))
    P.xf_all(Matrix.Translation((0, 0, 0.30)) @ R(0, 90, 0) @ Matrix.Translation((0, 0, -0.475)) @ Matrix.Translation((0, 0, 0)))
    P.xf_all(R(0, 0, 18))
    P.cyl((-0.55, -0.25, 0.006), 0.5, 0.012, 'z', RB, seg=20, sc=(1.2, 0.9, 1), bev=0)
    P.cyl((-0.15, -0.1, 0.01), 0.18, 0.012, 'z', RB, seg=14, sc=(1.4, 0.8, 1), bev=0)
    return P


def draw_crate_small(P):
    P.box((0, 0, 0.215), (0.66, 0.46, 0.34), PL)
    P.box((0, 0, 0.45), (0.7, 0.5, 0.1), PL, bev=0.015)
    P.box((0, 0, 0.025), (0.64, 0.4, 0.05), DK)
    P.box((0, 0, 0.502), (0.5, 0.06, 0.008), YE, bev=0.002)
    P.box((0, 0, 0.502), (0.06, 0.34, 0.008), YE, bev=0.002)
    for sx in (-1, 1):
        for k in (-1, 1):
            P.box((sx * 0.34, k * 0.12, 0.3), (0.04, 0.03, 0.05), BA, bev=0.005)
        P.box((sx * 0.365, 0, 0.34), (0.02, 0.22, 0.03), BA, bev=0.005)
    for k in (-1, 1):
        P.box((k * 0.17, -0.245, 0.4), (0.07, 0.025, 0.12), BA, bev=0.005)
        P.box((k * 0.17, -0.256, 0.43), (0.05, 0.012, 0.025), DK, bev=0.003)
    for k in (-1, 1):
        P.box((k * 0.2, 0, 0.27), (0.04, 0.47, 0.12), DK, bev=0.005)


@prop('crate_small')
def crate_small():
    P = Prop('crate_small')
    draw_crate_small(P)
    return P


def draw_crate_metal(P, w=1.2, h=1.2, rust=False, lite=False):
    hw = w / 2
    bv = 0 if lite else 0.012
    P.box((0, 0, h / 2), (w - 0.08, w - 0.08, h - 0.06), RU if rust else PL, bev=0.02, seg=2)
    for sx in (-1, 1):
        for sy in (-1, 1):
            P.box((sx * (hw - 0.05), sy * (hw - 0.05), h / 2), (0.1, 0.1, h), DK, bev=bv, seg=2)
            P.box((sx * (hw - 0.07), sy * (hw - 0.07), h - 0.035), (0.14, 0.14, 0.07), DK, bev=bv)
            P.box((sx * (hw - 0.07), sy * (hw - 0.07), 0.035), (0.14, 0.14, 0.07), DK, bev=bv)
    for z in (0.025, h - 0.04):
        for sg in (-1, 1):
            P.box((0, sg * (hw - 0.05), z), (w - 0.1, 0.08, 0.05), DK, bev=bv)
            P.box((sg * (hw - 0.05), 0, z), (0.08, w - 0.1, 0.05), DK, bev=bv)
    # ribs on the four faces
    for i in ((-1, 1) if lite else range(-2, 3)):
        o = i * 0.2
        if abs(o) < 0.01 and False:
            continue
        for sg in (-1, 1):
            P.box((o, sg * (hw - 0.025), h / 2), (0.05, 0.03, h - 0.3), PL, bev=0.008)
            P.box((sg * (hw - 0.025), o, h / 2), (0.03, 0.05, h - 0.3), PL, bev=0.008)
    # lid seam, top plate
    P.box((0, 0, h * 0.83), (w - 0.06, w - 0.06, 0.022), DK, bev=0.004)
    P.box((0, 0, h - 0.025), (w - 0.2, w - 0.2, 0.03), PL, bev=0.01)
    P.box((0.22, 0.2, h - 0.007), (0.5, 0.36, 0.012), RU, bev=0.004)
    P.box((-0.25, -0.18, h - 0.007), (0.3, 0.3, 0.012), YE, bev=0.004)
    # latch / hasp
    P.box((0, -hw - 0.005, h * 0.83), (0.16, 0.03, 0.26), BA, bev=0.006)
    P.box((0, -hw - 0.02, h * 0.83 - 0.07), (0.07, 0.03, 0.06), RD, bev=0.006)
    P.torus((0, -hw - 0.025, h * 0.83 + 0.06), 0.03, 0.008, 'y', BA, seg=10, rseg=4)
    P.box((0.45, -hw - 0.02, h * 0.6), (0.4, 0.008, 0.06), YE, bev=0.002)
    for sx in (-1, 1):
        P.cyl((sx * 0.35, -hw + 0.01, h * 0.83 + 0.02), 0.03, 0.04, 'y', DK, seg=8)


@prop('crate_metal')
def crate_metal():
    P = Prop('crate_metal')
    draw_crate_metal(P)
    return P


@prop('crate_stack')
def crate_stack():
    P = Prop('crate_stack')
    P.place(draw_crate_metal, (-0.55, 0.05, 0), (0, 0, 4))
    P.place(draw_crate_metal, (0.75, -0.1, 0), (0, 0, -7), 0.9, rust=True, lite=True)
    P.place(draw_crate_metal, (-0.35, 0.05, 1.2), (0, 0, 17), 0.85, lite=True)
    P.place(draw_crate_small, (0.7, -0.15, 1.08), (0, 0, 28))

    # tarp draped over the top crate and one side
    def tz(x, y):
        # top crate occupies about x[-0.9,0.2] y[-0.45,0.55] top at z=2.22
        d = max(abs(x + 0.35) - 0.52, abs(y - 0.05) - 0.52, 0)
        z = 2.275 - 0.9 * d ** 0.8 * (1.6 if x > -0.35 else 0.9)
        wob = 0.012 * math.sin(x * 14 + y * 9)
        return max(z + wob, 0.035 + 0.02 * math.sin(x * 9 + y * 7) ** 2)
    P.sheet(tz, -1.05, 0.55, -0.85, 0.75, 16, 16, CL, 0.012)
    P.box((-1.0, 0.5, 0.05), (0.6, 0.55, 0.08), CL, rot=(0, 0, 25), bev=0.03)
    return P


@prop('pallet')
def pallet():
    P = Prop('pallet')
    for x in (-0.55, 0, 0.55):
        P.box((x, 0, 0.011), (0.12, 1.0, 0.022), WO, bev=0.004)
    for y in (-0.45, 0, 0.45):
        P.box((0, y, 0.075), (1.2, 0.09, 0.106), WO, bev=0.006)
    for i in range(7):
        x = -0.51 + i * 0.17
        if i == 4:
            P.box((x, 0.05, 0.14), (0.14, 0.86, 0.022), WO, rot=(0, 0, 4), bev=0.004)
            P.box((x + 0.1, -0.5, 0.147), (0.07, 0.25, 0.022), WO, rot=(0, 0, -12), bev=0.004)
            continue
        P.box((x, 0, 0.139), (0.14, 1.0, 0.022), WO, bev=0.004)
        for y in (-0.45, 0, 0.45):
            P.cyl((x, y, 0.151), 0.01, 0.006, 'z', BA, seg=6, bev=0)
    return P


@prop('gas_cylinder')
def gas_cylinder():
    P = Prop('gas_cylinder')
    prof = [(0, 0), (0.1, 0), (0.122, 0.04), (0.125, 0.1), (0.125, 1.05), (0.118, 1.15), (0.095, 1.25), (0.06, 1.31), (0.05, 1.33), (0, 1.33)]
    P.lathe(prof, m=PL, seg=20)
    P.lathe([(0.1275, 0.72), (0.1275, 0.95)], m=YE, seg=20)
    P.lathe([(0.1262, 1.0), (0.1262, 1.02)], m=DK, seg=20)
    P.torus((0, 0, 0.03), 0.11, 0.02, 'z', DK, seg=16, rseg=5)
    P.cyl((0, 0, 1.345), 0.055, 0.04, 'z', DK, seg=12)
    # valve guard cap
    P.lathe([(0.085, 1.33), (0.085, 1.5), (0.0, 1.5)], m=RD, seg=12)
    for a in (0, 90, 180, 270):
        pass
    P.box((0.0, -0.088, 1.43), (0.06, 0.012, 0.09), DK, bev=0.004)
    P.cyl((0.0, 0, 1.5), 0.02, 0.02, 'z', BA, seg=8)
    P.cyl((0.1, 0, 1.2), 0.016, 0.06, 'x', BA, seg=8)
    return P


@prop('bucket')
def bucket():
    P = Prop('bucket')
    P.lathe([(0, 0), (0.125, 0), (0.172, 0.335), (0.178, 0.35), (0.166, 0.35), (0.122, 0.035), (0, 0.035)], m=RU, seg=20)
    P.torus((0, 0, 0.345), 0.172, 0.01, 'z', BA, seg=20, rseg=5)
    P.torus((0, 0, 0.15), 0.15, 0.008, 'z', DK, seg=20, rseg=5)
    P.cyl((0, 0, 0.04), 0.12, 0.012, 'z', RB, seg=16, bev=0)  # sludge
    pts = [(-0.178, 0, 0.30), (-0.17, 0, 0.335), (-0.1, 0, 0.35), (0, 0, 0.355), (0.1, 0, 0.35), (0.17, 0, 0.335), (0.178, 0, 0.30)]
    P.tube(catmull(pts, 4), 0.007, BA, seg=6)
    for sx in (-1, 1):
        P.box((sx * 0.178, 0, 0.30), (0.02, 0.03, 0.03), BA, bev=0.004)
    return P


@prop('toolbox')
def toolbox():
    P = Prop('toolbox')
    P.box((0, 0, 0.1), (0.6, 0.25, 0.2), RD, bev=0.012)
    P.box((0, 0, 0.215), (0.56, 0.23, 0.04), RD, bev=0.012)
    P.box((0, 0, 0.012), (0.58, 0.23, 0.024), DK, bev=0.004)
    for sx in (-1, 1):
        P.box((sx * 0.3, 0, 0.1), (0.02, 0.2, 0.1), DK, bev=0.004)
        P.box((sx * 0.2, -0.127, 0.17), (0.07, 0.01, 0.07), BA, bev=0.004)
    pts = [(-0.14, 0, 0.235), (-0.12, 0, 0.29), (0, 0, 0.305), (0.12, 0, 0.29), (0.14, 0, 0.235)]
    P.tube(catmull(pts, 4), 0.012, DK, seg=6)
    P.box((0, -0.127, 0.14), (0.5, 0.008, 0.012), BA, bev=0.002)
    P.box((0.12, 0.02, 0.236), (0.28, 0.03, 0.012), BA, bev=0.002, rot=(0, 0, 14))
    return P


@prop('cone')
def cone():
    P = Prop('cone')
    P.box((0, 0, 0.0175), (0.35, 0.35, 0.035), DK, bev=0.012, seg=2)
    h0, h1, r0, r1 = 0.03, 0.6, 0.135, 0.028

    def rr(z):
        return r0 + (r1 - r0) * (z - h0) / (h1 - h0)
    P.cyl((0, 0, (h0 + h1) / 2), r0, h1 - h0, 'z', YE, seg=16, r2=r1, bev=0.004)
    za, zb = 0.2, 0.34
    P.lathe([(rr(za) + 0.003, za), (rr(zb) + 0.003, zb)], m=PL, seg=16)
    P.torus((0, 0, 0.598), 0.026, 0.012, 'z', DK, seg=10, rseg=4)
    P.torus((0, 0, 0.045), 0.135, 0.012, 'z', YE, seg=16, rseg=4)
    return P


# ---------------------------------------------------------------- debris
def _brick(P, c, rz, tilt=(0, 0, 0)):
    P.box(c, (0.22, 0.105, 0.065), CO, rot=(tilt[0], tilt[1], rz), bev=0.006)


def _bent_sheet(P, c, rz, sx=0.7, sy=0.5, m=PL, ang=22):
    n0 = P.mark()
    P.box((0, 0, 0.012), (sx, sy * 0.5, 0.02), m, bev=0.004)
    P.box((0, sy * 0.5 * math.cos(math.radians(ang)) * 0.98, 0.012 + sy * 0.25 * math.sin(math.radians(ang))), (sx, sy * 0.5, 0.02), m, rot=(ang, 0, 0), bev=0.004)
    P.xf_from(n0, Matrix.Translation(c) @ R(0, 0, rz))


def _pipe(P, c, rz, L=0.7, r=0.04, m=PL):
    P.cyl((c[0], c[1], r), r, L, 'x', m, seg=10, rot=(0, 0, rz))
    n0 = P.mark()
    P.torus((L / 2, 0, r), r * 0.95, r * 0.25, 'x', DK, seg=10, rseg=4)
    P.xf_from(n0, Matrix.Translation((c[0], c[1], 0)) @ R(0, 0, rz) @ Matrix.Translation((-L / 2 + 0.03, 0, 0)))


def _panel(P, c, rz, ang=15, sc=1.0):
    pol = [(-0.45 * sc, -0.2 * sc), (0.4 * sc, -0.28 * sc), (0.5 * sc, 0.1 * sc), (0.1 * sc, 0.32 * sc), (-0.15 * sc, 0.15 * sc), (-0.35 * sc, 0.28 * sc)]
    n0 = P.mark()
    P.extrude(pol, 'xy', 0.0, 0.025, PL)
    for p in pol[:4]:
        P.cyl((p[0] * 0.8, p[1] * 0.8, 0.03), 0.014, 0.012, 'z', BA, seg=6, bev=0)
    P.xf_from(n0, Matrix.Translation(c) @ R(ang * 0.5, ang, rz))


def _bolt_loose(P, c, rz):
    P.cyl((c[0], c[1], 0.012), 0.012, 0.05, 'x', BA, seg=6, rot=(0, 0, rz), bev=0)
    P.cyl((c[0], c[1], 0.012), 0.02, 0.014, 'x', BA, seg=6, rot=(0, 0, rz), bev=0)


def _chunk(P, c, s, rz, m=CO):
    P.sphere(c, 1.0, m, sc=(s[0], s[1], s[2]), seg=7, rings=5, rot=(rz * 0.3, rz * 0.2, rz))


def _plank(P, c, rz, L=0.8):
    P.box((c[0], c[1], 0.02), (L, 0.1, 0.035), WO, rot=(0, 0, rz), bev=0.004)


@prop('debris_a')
def debris_a():
    P = Prop('debris_a')
    _bent_sheet(P, (-0.2, 0.2, 0), 25, 0.9, 0.6)
    _bent_sheet(P, (0.3, -0.45, 0), -40, 0.6, 0.45, RU, 30)
    _pipe(P, (0.1, 0.55), 15, 0.9, 0.045)
    _pipe(P, (-0.45, -0.3), 100, 0.5, 0.035, RU)
    for i, (x, y, r) in enumerate([(0.5, 0.1, 20), (0.58, 0.22, 70), (0.35, 0.3, 5), (-0.6, 0.5, 50)]):
        _brick(P, (x, y, 0.033 + (0.065 if i == 1 else 0)), r)
    for p in [(-0.1, -0.1, 30), (0.7, -0.2, 120), (-0.7, 0.0, 10), (0.2, 0.0, 60)]:
        _bolt_loose(P, p[:2], p[2])
    _chunk(P, (-0.5, 0.2, 0.06), (0.1, 0.07, 0.06), 30)
    return P.ground()


@prop('debris_b')
def debris_b():
    P = Prop('debris_b')
    _panel(P, (0.0, 0.05, 0.18), 15, 18, 1.3)
    _plank(P, (-0.1, -0.55), 10, 1.0)
    _plank(P, (0.35, -0.5), -50, 0.6)
    for p in [(0.55, 0.45, 0.14), (-0.55, 0.45, 0.1), (-0.6, -0.1, 0.08)]:
        _chunk(P, (p[0], p[1], p[2] * 0.6), (p[2] * 1.3, p[2], p[2] * 0.7), p[0] * 90)
    _pipe(P, (-0.1, 0.65), -8, 0.6, 0.03, DK)
    for p in [(0.6, -0.1, 10), (0.45, -0.3, 80), (-0.35, 0.3, 33), (0.0, -0.3, 0), (-0.2, 0.55, 90)]:
        _bolt_loose(P, p[:2], p[2])
    _brick(P, (0.65, 0.0, 0.033), 35)
    return P.ground()


@prop('debris_c')
def debris_c():
    P = Prop('debris_c')
    # ring of a ripped drum lid and tyre
    P.torus((-0.2, 0.2, 0.06), 0.2, 0.06, 'z', RB, seg=18, rseg=8)
    P.cyl((0.4, -0.2, 0.02), 0.28, 0.025, 'z', RU, seg=18, rot=(6, -4, 0), bev=0.006)
    P.torus((0.4, -0.2, 0.04), 0.27, 0.01, 'z', DK, seg=18, rseg=4, rot=(6, -4, 0))
    _pipe(P, (0.05, -0.55), -20, 0.95, 0.05, PL)
    _pipe(P, (0.4, 0.5), 60, 0.55, 0.04, RU)
    _pipe(P, (-0.55, -0.35), 95, 0.4, 0.03, DK)
    _bent_sheet(P, (-0.5, 0.55, 0), -15, 0.55, 0.4)
    _brick(P, (0.65, 0.4, 0.033), 12)
    _brick(P, (0.7, 0.25, 0.033), -8)
    _brick(P, (0.66, 0.33, 0.098), 5)
    _chunk(P, (-0.6, -0.6, 0.05), (0.14, 0.1, 0.05), 70)
    for p in [(0.1, 0.2, 40), (0.2, 0.0, 80), (-0.2, -0.1, 10)]:
        _bolt_loose(P, p[:2], p[2])
    P.cyl((0.2, 0.35, 0.012), 0.015, 0.03, 'x', DK, seg=8, bev=0)
    return P.ground()


@prop('body_bag')
def body_bag():
    P = Prop('body_bag')
    tab = [(-0.95, 0.10, 0.05), (-0.88, 0.16, 0.10), (-0.62, 0.15, 0.13), (-0.3, 0.19, 0.17), (-0.05, 0.30, 0.20),
           (0.2, 0.28, 0.22), (0.38, 0.35, 0.28), (0.55, 0.35, 0.27), (0.68, 0.14, 0.14), (0.78, 0.14, 0.2), (0.88, 0.12, 0.17), (0.95, 0.05, 0.09)]
    path = catmull([(h, w, z) for (h, w, z) in [(y, w, hh) for (y, w, hh) in tab]], 3)
    rings = []
    N = 14
    for (y, w, hh) in path:
        ring = []
        for j in range(N):
            a = math.pi * j / (N - 1)      # 0..pi over the top
            ring.append((w * math.cos(a), y, 0.012 + hh * math.sin(a) ** 0.8 if True else 0))
        # flat bottom: mirror points back along the floor
        ring = [(w * math.cos(math.pi * j / (N - 1)), y, max(0.006, hh * math.sin(math.pi * j / (N - 1)))) for j in range(N)]
        rings.append(ring)
    P.loft(rings, CL, True)
    # zip seam and pull tab
    top = [(0.0, y, hh + 0.006) for (y, w, hh) in path[2:-4]]
    P.tube(top, 0.011, BA, seg=6, caps=True)
    P.box((0.0, -0.55, 0.15), (0.035, 0.07, 0.014), BA, bev=0.003, rot=(8, 0, 0))
    # side straps / handles
    for y in (-0.5, -0.05, 0.4):
        for sx in (-1, 1):
            i = min(range(len(path)), key=lambda k: abs(path[k][0] - y))
            w = path[i][1]
            P.box((sx * (w + 0.005), y, 0.065), (0.03, 0.14, 0.03), RB, bev=0.006)
    return P
