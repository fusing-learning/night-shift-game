"""The Foreman - boss.glb. Run: Blender -b --python boss.py [-- norender]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, mlib
importlib.reload(mlib)
from mlib import *

RENDER = "norender" not in sys.argv
reset()
rnd = random.Random(23)
UP = Vector((0, 0, 1))

TILT = math.radians(35)
F = Vector((0, -1.52, 1.42))                    # furnace opening centre
D = Vector((0, -math.cos(TILT), math.sin(TILT)))  # direction it faces
FU = Vector((0, math.sin(TILT), math.cos(TILT)))  # "up" inside the opening plane
FR = Vector((1, 0, 0))
FRAD = 0.66

# forelimbs: shoulder, elbow, wrist, palm contact
ARMS = {}
for side, s in (("L", 1), ("R", -1)):
    ARMS[side] = (Vector((1.12 * s, -0.55, 1.95)), Vector((1.88 * s, -1.15, 1.4)),
                  Vector((1.5 * s, -1.95, 0.34)), Vector((1.42 * s, -2.22, 0.0)))
NECK = [Vector((0.12, -1.1, 2.4)), Vector((0.45, -1.58, 2.48)), Vector((0.6, -1.95, 2.24))]
HEADC = Vector((0.63, -2.03, 2.1))
HEADDIR = Vector((0.15, -0.95, 0.05)).normalized()  # where the mask faces
TAIL = [Vector((0.0, 1.7, 0.62)), Vector((0.15, 2.02, 0.22)), Vector((-0.1, 2.3, 0.12)), Vector((0.05, 2.55, 0.1))]


def bez(pts, n):
    out = []
    P = [pts[0] * 2 - pts[1]] + list(pts) + [pts[-1] * 2 - pts[-2]]
    for i in range(1, len(P) - 2):
        for k in range(n):
            t = k / n
            p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return out


def tangent_frame(n):
    t = n.cross(Vector((0.3, 1, 0.1))).normalized()
    return t, n.cross(t).normalized()


# ------------------------------------------------------------ core mass
core_el = [
    dict(type="ELLIPSOID", co=(0, 0.3, 1.1), r=1.22, s=(1.18, 1.3, 0.92)),
    dict(type="ELLIPSOID", co=(0, -0.72, 1.4), r=0.98, s=(1.18, 0.85, 1.02)),
    dict(type="BALL", co=(0.15, 0.5, 1.75), r=0.78),
    dict(type="BALL", co=(-0.45, 0.95, 1.6), r=0.62),
    dict(type="BALL", co=(0.5, 1.15, 1.5), r=0.55),
    dict(type="ELLIPSOID", co=(0, 1.5, 0.95), r=0.82, s=(1.1, 1, 0.9)),
    dict(type="BALL", co=(0.2, 1.95, 0.5), r=0.52),
    dict(type="BALL", co=(0, -1.12, 2.15), r=0.45),     # brow over the furnace
]
for s in (1, -1):
    core_el += [dict(type="BALL", co=(1.08 * s, -0.55, 1.9), r=0.52),
                dict(type="BALL", co=(1.18 * s, 0.45, 0.85), r=0.62),
                dict(type="BALL", co=(0.98 * s, 1.35, 0.7), r=0.55),
                dict(type="BALL", co=(0.72 * s, -1.2, 1.1), r=0.42)]   # cheeks of the furnace
cav = [dict(type="ELLIPSOID", co=tuple(F - D * 0.42), r=0.74, neg=True, stiff=4),
       dict(type="ELLIPSOID", co=tuple(F - D * 0.05), r=0.64, s=(1, 1, 1), neg=True, stiff=4)]
proxy = metaballs("mb_proxy", core_el + cav, res=0.06)
BV = BVHTree.FromPolygons([v.co.copy() for v in proxy.data.vertices], [tuple(p.vertices) for p in proxy.data.polygons])


def surf(x, y, z0=6.0):
    hit = BV.ray_cast(Vector((x, y, z0)), Vector((0, 0, -1)), 12)
    if hit[0] is None:
        return Vector((x, y, 0)), UP.copy()
    n = hit[1]
    if n.z < 0:
        n = -n
    return hit[0], n


def surf_near(p):
    loc, n, i, d = BV.find_nearest(p)
    return loc, n


main_el = core_el + cav
# egg sacs on the back with flesh cradles
SACS = []
for (x, y) in [(-0.78, 0.15), (0.88, 0.5), (-0.42, 1.35), (0.6, 1.5)]:
    p, n = surf(x, y)
    n = (n + UP).normalized()
    c = p + n * 0.12
    SACS.append((c, n))
    t, b = tangent_frame(n)
    for k in range(10):
        a = 2 * math.pi * k / 10
        main_el.append(dict(type="BALL", co=tuple(p + (t * math.cos(a) + b * math.sin(a)) * 0.29 + n * 0.02), r=0.1))
bpy.data.objects.remove(proxy, do_unlink=True)
body = metaballs("mb_core", main_el, res=0.05)
parts = [body]

# fused human torsos half sunk into the back
TORSOS = []
for (x, y, ang) in [(-0.25, -0.05, 0.4), (0.55, 0.95, -1.1), (-0.95, 1.0, 1.9), (0.1, 1.95, 1.5), (-1.25, 0.05, -0.3),
                    (1.25, -0.1, 0.9), (0.05, 0.75, 2.6), (1.25, 1.4, -0.6), (-0.6, -0.65, 0.1)]:
    p, n = surf(x, y)
    t0, b0 = tangent_frame(n)
    ax = (t0 * math.cos(ang) + b0 * math.sin(ang)).normalized()
    sd = n.cross(ax).normalized()
    c = p + n * 0.02
    M = Matrix((sd, n, ax)).transposed()
    rot = M.to_quaternion()
    parts.append(prim("ico", "ribs", loc=c, rot=rot, scale=(0.27, 0.17, 0.36), sub=3))
    for s in (1, -1):
        parts.append(prim("ico", "blade", loc=c + sd * 0.13 * s + n * 0.1 + ax * 0.14, rot=rot, scale=(0.11, 0.05, 0.13), sub=2))
        parts.append(prim("ico", "butt", loc=c + sd * 0.1 * s + ax * -0.42 + n * 0.0, rot=rot, scale=(0.13, 0.12, 0.13), sub=2))
        parts.append(prim("ico", "shoulder", loc=c + sd * 0.25 * s + ax * 0.27, rot=rot, scale=(0.09, 0.09, 0.1), sub=2))
    for k in range(7):
        parts.append(prim("ico", "vert", loc=c + n * (0.15 - 0.02 * abs(k - 3) / 3) + ax * (0.3 - k * 0.1), scale=(0.035, 0.035, 0.03), sub=1))
    TORSOS.append((c, n, ax, sd))
    # every other torso still has its (faceless) head, half absorbed
    if len(TORSOS) % 2 == 1:
        parts.append(prim("ico", "head", loc=c + ax * 0.5 + n * 0.02, rot=rot, scale=(0.12, 0.13, 0.14), sub=2))

# hands pressing out from inside the stretched flank skin
for (x, y, z0) in [(1.3, 0.3, 1.0), (-1.35, 0.6, 0.95), (1.05, 1.5, 0.75), (-1.0, 1.55, 0.9), (0.4, 2.05, 0.8), (-1.25, -0.25, 1.25)]:
    p, n = surf_near(Vector((x, y, z0)))
    t, b = tangent_frame(n)
    a0 = rnd.uniform(0, 6.28)
    hd = t * math.cos(a0) + b * math.sin(a0)
    hs = n.cross(hd).normalized()
    parts.append(prim("ico", "palm", loc=p, rot=Matrix((hs, hd, n)).transposed().to_quaternion(), scale=(0.1, 0.11, 0.06), sub=2))
    fl = []
    for fi in range(-2, 3):
        fd = (hd + hs * fi * 0.28).normalized()
        f0 = p + fd * 0.09 + hs * fi * 0.025 + n * 0.015
        fl.append([(f0, 0.026), (f0 + fd * (0.13 - abs(fi) * 0.015), 0.022)])
    parts.append(skin_tubes("press", fl, subsurf=0))

# colossal forelimbs
for side, (S, E, W, P) in ARMS.items():
    s = 1 if side == "L" else -1
    ch = [(S + (S - E) * 0.2, 0.5), (S, 0.46), (S + (E - S) * 0.45, 0.42), (S + (E - S) * 0.8, 0.36), (E, 0.33),
          (E + (W - E) * 0.18, 0.37), (E + (W - E) * 0.45, 0.33), (E + (W - E) * 0.75, 0.27), (W, 0.24)]
    parts.append(skin_tubes("arm" + side, [ch], subsurf=1))
    fwd = Vector((P.x - W.x, P.y - W.y, 0)).normalized()
    sdv = Vector((-fwd.y, fwd.x, 0))
    # elbow knob + muscle lumps
    arm_el = [dict(type="BALL", co=tuple(E + Vector((0.12 * s, 0, 0.08))), r=0.3),
              dict(type="ELLIPSOID", co=tuple(P + UP * 0.12 - fwd * 0.05), r=0.3, s=(1.15, 1.25, 0.45),
                   rot=Vector((0, 1, 0)).rotation_difference(fwd)),
              dict(type="BALL", co=tuple(S + (E - S) * 0.4 + UP * 0.12), r=0.33)]
    parts.append(metaballs("mb_arm" + side, arm_el, res=0.04))
    fingers = []
    for fa in (-30, 0, 28):
        fd = Quaternion(UP, math.radians(fa)) @ fwd
        b0 = P + UP * 0.14 + fd * 0.2
        L = 0.4 if fa == 0 else 0.34
        fingers.append([(b0, 0.13), (b0 + fd * L * 0.4 + UP * 0.1, 0.12), (b0 + fd * L * 0.75 + UP * 0.06, 0.1), (b0 + fd * L + UP * -0.05, 0.075)])
    parts.append(skin_tubes("fing" + side, fingers, subsurf=1))

# neck sags out from the brow
nch = [(p, 0.15 - 0.05 * i / 2) for i, p in enumerate(NECK)]
neck_pts = bez(NECK, 4)
neck_ch = [(p, 0.15 - 0.06 * i / (len(neck_pts) - 1)) for i, p in enumerate(neck_pts)]
parts.append(skin_tubes("neck", [neck_ch], subsurf=1))

org = join(parts, "boss_org")
print("ORG", len(org.data.vertices), [len(p.data.vertices) for p in []])
org = remesh(org, 0.028)
smooth(org, 3)
c = get_co(org)
c[:, 2] = np.maximum(c[:, 2], 0.0)
set_co(org, c)
lumps(org, s1=(1.6, 0.06), s2=(5.5, 0.018), seed=9)
cv = blur(curvature(org), org, 3)
wr = np.abs(nfield(get_co(org), 9, (4, 1, 2), octaves=2))
displace(org, lambda c, n: -(smoothstep(0.02, 0.3, cv) * (1 - smoothstep(0.0, 0.3, wr)) * 0.03))
smooth(org, 1)
c = get_co(org)
c[:, 2] = np.maximum(c[:, 2], 0.0)
set_co(org, c)
print("ORG2", len(org.data.vertices))
org = decimate(org, 27000)
print("ORG3", len(org.data.vertices))
shade_smooth(org)


def furnace_local(c):
    rel = c - np.array(F)
    h = rel @ np.array(D)
    r = np.linalg.norm(rel - h[:, None] * np.array(D), axis=1)
    return r, h


def mat_fn(c, n):
    r, h = furnace_local(c)
    inner = (r < FRAD + 0.2) & (h < 0.12) & (h > -1.2)
    return np.where(inner, 1, 0)


assign_faces(org, ["flesh", "flesh_dark"], mat_fn)
BVo = BVHTree.FromPolygons([v.co.copy() for v in org.data.vertices], [tuple(p.vertices) for p in org.data.polygons])


def osurf(x, y):
    hit = BVo.ray_cast(Vector((x, y, 6)), Vector((0, 0, -1)), 12)
    if hit[0] is None:
        return None, None
    n = hit[1] if hit[1].z > 0 else -hit[1]
    return hit[0], n


def osurf_s(x, y):
    for k in range(20):
        f = 1 - k * 0.04
        p, n = osurf(x * f, (y - 0.4) * f + 0.4)
        if p is not None:
            return p, n
    raise RuntimeError("no surface at %s %s" % (x, y))


# ------------------------------------------------------------ decorative reaching arms (weighted to body)
darms = []
cands = []
for k in range(80):
    x, y = rnd.uniform(-1.45, 1.45), rnd.uniform(-0.9, 2.1)
    if any((Vector((x, y)) - c.xy).length < 0.45 for c, n in SACS):
        continue
    hp, hn = osurf(x, y)
    if hp is None or hp.z < 0.9:
        continue
    if all((Vector((x, y)) - Vector(q)).length > 0.42 for q in cands):
        cands.append((x, y))
    if len(cands) >= 12:
        break
DARM_BASES = []
for (x, y) in cands:
    p, n = osurf(x, y)
    t, b = tangent_frame(n)
    a = rnd.uniform(0, 2 * math.pi)
    lean = (t * math.cos(a) + b * math.sin(a))
    outward = Vector((x, y - 0.4, 0)).normalized()
    d1 = (n * 0.8 + lean * 0.45 + outward * 0.7).normalized()
    L1 = rnd.uniform(0.26, 0.36)
    base = p - n * 0.08
    el_ = base + d1 * (L1 + 0.08)
    d2 = (d1 + lean * 0.9 + outward * 0.5 - UP * 0.55).normalized()
    wr_ = el_ + d2 * rnd.uniform(0.25, 0.33)
    ch = [[(base, 0.085), (base + d1 * 0.12, 0.075), (el_, 0.058), (el_ + (wr_ - el_) * 0.5, 0.056), (wr_, 0.042)]]
    hd = (d2 + lean * 0.2).normalized()
    hs = hd.cross(n).normalized()
    palm = wr_ + hd * 0.05
    ch.append([(wr_, 0.044), (palm, 0.058)])
    curl = rnd.uniform(0.0, 1.0)
    for fi in range(-2, 3):
        fd = (hd + hs * fi * 0.32).normalized()
        f0 = palm + fd * 0.04 + hs * fi * 0.02
        L = 0.15 - abs(fi) * 0.015
        f1 = f0 + fd * L * 0.5
        f2 = f1 + (fd * (1 - curl) - d1 * curl * 0.6).normalized() * L * 0.5
        ch.append([(f0, 0.022), (f1, 0.019), (f2, 0.015)])
    DARM_BASES.append(p)
    darms.append(skin_tubes("darm", ch, subsurf=1))
darms = join(darms, "darms")
darms = remesh(darms, 0.013)
smooth(darms, 2)
darms = decimate(darms, 3400)
shade_smooth(darms)
set_material(darms, "flesh")

# ------------------------------------------------------------ ribcage splayed open around the furnace
ribs = []
for k in range(9):
    a = math.radians(-150 + k * (300 / 8))
    radial = FR * math.sin(a) + FU * math.cos(a)
    p0 = F - D * 0.6 + radial * (FRAD - 0.05)
    p1 = F - D * 0.1 + radial * (FRAD + 0.32)
    p2 = F + D * 0.3 + radial * (FRAD + 0.5)
    p3 = F + D * 0.6 + radial * (FRAD + 0.22)
    if abs(a) > math.radians(110):   # lower ribs shorter
        p2 = F + D * 0.22 + radial * (FRAD + 0.42)
        p3 = F + D * 0.42 + radial * (FRAD + 0.25)
    pts = bez([p0, p1, p2, p3], 3)
    ribs.append([(q, 0.12 - 0.085 * (i / (len(pts) - 1)) ** 1.5) for i, q in enumerate(pts)])
ribs = skin_tubes("ribs", ribs, subsurf=1)
ribs = decimate(ribs, 2200)
shade_smooth(ribs)
set_material(ribs, "bone")

# claws on the big hands
claws = []
for side, (S, E, W, P) in ARMS.items():
    fwd = Vector((P.x - W.x, P.y - W.y, 0)).normalized()
    for fa in (-30, 0, 28):
        fd = Quaternion(UP, math.radians(fa)) @ fwd
        L = 0.4 if fa == 0 else 0.34
        tip = P + UP * 0.14 + fd * (0.2 + L) + UP * -0.05
        claws.append(cone_between("claw", tip - fd * 0.06 + UP * 0.03, tip + fd * 0.16 - UP * 0.08, 0.065, seg=6))
claws = join(claws, "claws")
set_material(claws, "bone")

# ------------------------------------------------------------ furnace: glow bowl, iron ring, grate
q = Vector((0, 0, 1)).rotation_difference(D)
bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=1.0)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z > 0.05], context="VERTS")
for v in bm.verts:
    w = Vector((math.cos(v.co.x * 9) * 0.03, math.sin(v.co.y * 7) * 0.03, 0))
    v.co = F - D * 0.08 + q @ (Vector((v.co.x * 0.64, v.co.y * 0.64, v.co.z * 0.55)) + w)
me = bpy.data.meshes.new("bowl")
bm.to_mesh(me)
bm.free()
bowl = link(bpy.data.objects.new("bowl", me))
# glowing coal lumps in the bowl
coals = [bowl]
for k in range(16):
    a = rnd.uniform(0, 2 * math.pi)
    rr = rnd.uniform(0, 0.42)
    p = F - D * rnd.uniform(0.38, 0.55) + (FR * math.cos(a) + FU * math.sin(a)) * rr
    coals.append(prim("ico", "coal", loc=p, scale=(0.09, 0.08, 0.07), rot=(a, a * 2, 0), sub=1, smooth=False))
glow = join(coals, "glow")
shade_smooth(glow)
set_material(glow, "glow_furnace")

iron = [prim("torus", "rim", loc=F + D * 0.02, rot=q, R=FRAD + 0.04, r=0.085, seg=28, seg2=6)]
for k in range(10):
    a = 2 * math.pi * (k + 0.5) / 10
    p = F + D * 0.1 + (FR * math.cos(a) + FU * math.sin(a)) * (FRAD + 0.04)
    iron.append(prim("cyl", "rivet", loc=p, rot=q, r1=0.035, r2=0.03, depth=0.04, seg=6, smooth=False))
for xo in (-0.44, -0.22, 0.0, 0.22, 0.44):
    hh = math.sqrt(max(FRAD ** 2 - xo ** 2, 0.01)) + 0.02
    a_ = F - D * 0.04 + FR * xo - FU * hh
    b_ = F - D * 0.04 + FR * xo + FU * hh
    iron.append(cyl_between("bar", a_, b_, 0.032, seg=6))
for yo in (-0.25, 0.25):
    hh = math.sqrt(FRAD ** 2 - yo ** 2) + 0.02
    iron.append(cyl_between("xbar", F - D * 0.0 + FU * yo - FR * hh, F - D * 0.0 + FU * yo + FR * hh, 0.028, seg=6))
iron = join(iron, "iron")
set_material(iron, "metal")

# ------------------------------------------------------------ head in welding mask
qh = Vector((0, -1, 0)).rotation_difference(HEADDIR)
hparts = [prim("ico", "skull", loc=HEADC, rot=qh, scale=(0.11, 0.13, 0.135), sub=3)]
hparts.append(prim("ico", "jaw", loc=HEADC + qh @ Vector((0, -0.04, -0.09)), rot=qh, scale=(0.08, 0.08, 0.06), sub=2))
head_org = join(hparts + [skin_tubes("neck2", [[(p, r * 0.9) for p, r in neck_ch[-4:]]], subsurf=1)], "head_org")
head_org = remesh(head_org, 0.012)
smooth(head_org, 2)
head_org = decimate(head_org, 900)
shade_smooth(head_org)
set_material(head_org, "flesh")


def mask_plate(name, z0, z1, R=0.155, span=150, seg=10):
    bm = bmesh.new()
    vs = []
    for i in range(seg + 1):
        a = math.radians(-span / 2 + span * i / seg)
        for (z, rr) in ((z0, R), (z1, R), (z1, R + 0.022), (z0, R + 0.022)):
            vs.append(bm.verts.new((rr * math.sin(a), -rr * math.cos(a), z)))
    for i in range(seg):
        for k in range(4):
            a0, a1 = vs[i * 4 + k], vs[i * 4 + (k + 1) % 4]
            b0, b1 = vs[(i + 1) * 4 + k], vs[(i + 1) * 4 + (k + 1) % 4]
            bm.faces.new((a0, b0, b1, a1))
    bm.faces.new([vs[k] for k in range(4)][::-1])
    bm.faces.new([vs[seg * 4 + k] for k in range(4)])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = link(bpy.data.objects.new(name, me))
    o.data.transform(Matrix.LocRotScale(HEADC, qh, Vector((1, 1, 1))))
    o.data.polygons.foreach_set("use_smooth", [False] * len(o.data.polygons))
    return o


def hbox(name, c, size, taper=1.0, chin=0.0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        x, y, z = v.co
        f = 1.0 if z > 0 else taper
        v.co = Vector((x * size[0] * f, y * size[1] - (chin if (z < 0 and y < 0) else 0), z * size[2])) + Vector(c)
        v.co = HEADC + qh @ v.co
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = link(bpy.data.objects.new(name, me))
    o.data.polygons.foreach_set("use_smooth", [False] * len(o.data.polygons))
    return o


mask = [hbox("shell", (0, -0.12, -0.01), (0.31, 0.12, 0.37), taper=0.78, chin=0.05),
        hbox("brim", (0, -0.1, 0.19), (0.29, 0.16, 0.035)),
        hbox("lensframe", (0, -0.185, 0.045), (0.22, 0.02, 0.085))]
for s_ in (1, -1):
    mask.append(prim("cyl", "hinge", loc=HEADC + qh @ Vector((0.165 * s_, -0.05, 0.03)), rot=qh @ Quaternion((0, 1, 0), math.pi / 2),
                     r1=0.04, r2=0.04, depth=0.035, seg=8, smooth=False))
    for zz in (-0.08, -0.14):
        mask.append(prim("cyl", "rivet", loc=HEADC + qh @ Vector((0.1 * s_, -0.185 - 0.02 * (zz < -0.1), zz)), rot=qh @ Quaternion((1, 0, 0), math.pi / 2),
                         r1=0.014, r2=0.012, depth=0.02, seg=6, smooth=False))
mask = join(mask, "mask")
set_material(mask, "metal")
slit = hbox("slit", (0, -0.198, 0.045), (0.17, 0.012, 0.022))
set_material(slit, "glow_red")
strap = prim("torus", "strap", loc=HEADC + qh @ Vector((0, 0.03, 0.06)), rot=qh @ Quaternion((1, 0, 0), math.pi / 2 - 0.3), R=0.135, r=0.016, seg=16, seg2=4)
set_material(strap, "rubber")

# ------------------------------------------------------------ egg sacs
sacs = []
for i, (c, n) in enumerate(SACS):
    o = prim("ico", "sac%d" % (i + 1), loc=c, rot=UP.rotation_difference(n), scale=(0.3, 0.3, 0.34), sub=3)
    sc = get_co(o)
    rel = sc - np.array(c)
    vn = rel / np.linalg.norm(rel, axis=1, keepdims=True)
    bump = nfield(sc, 7, (i, 3, 3)) * 0.02 + (1 - smoothstep(0, 0.08, np.abs(nfield(sc, 6, (8, i, 1), octaves=2)))) * 0.012
    set_co(o, sc + vn * bump[:, None])
    shade_smooth(o)
    set_material(o, "glow_bile")
    sacs.append(o)

# ------------------------------------------------------------ exhaust stacks + hoses + cable stitches
STACKS = []
metal = []
for (x, y, h, r, lean) in [(0.3, -0.3, 0.42, 0.15, (0.05, 0.3)), (-1.08, 0.75, 0.62, 0.13, (-0.5, 0.1)),
                           (1.12, 0.95, 0.66, 0.14, (0.5, 0.25)), (-0.05, 0.95, 0.38, 0.12, (-0.1, 0.5))]:
    p, n = osurf(x, y)
    d = Vector((lean[0], lean[1], 1)).normalized()
    base = p - d * 0.25
    top = p + d * h
    metal.append(cyl_between("stack", base, top, r, seg=12, caps=False))
    metal.append(cyl_between("flangeb", p + d * 0.02, p + d * 0.08, r + 0.07, seg=12))
    metal.append(cyl_between("flangem", p + d * h * 0.55, p + d * (h * 0.55 + 0.05), r + 0.035, seg=12))
    metal.append(cyl_between("lip", top - d * 0.06, top + d * 0.01, r + 0.03, seg=12, caps=False))
    metal.append(cyl_between("inner", top - d * 0.25, top + d * 0.005, r - 0.015, seg=12, caps=True))
    # rain cap
    metal.append(cone_between("cap", top + d * 0.09, top + d * 0.19, r + 0.08, seg=12))
    metal.append(cyl_between("capst", top - d * 0.02, top + d * 0.1, 0.015, seg=4))
    STACKS.append((p, d, h, r))
for (p, d, h, r) in STACKS:
    for k in range(6):
        a = 2 * math.pi * k / 6
        t, b = tangent_frame(d)
        metal.append(prim("cube", "bolt", loc=p + d * 0.085 + (t * math.cos(a) + b * math.sin(a)) * (r + 0.045), rot=UP.rotation_difference(d), scale=(0.035, 0.035, 0.03), smooth=False))
# rusted plates bolted onto shoulders
for side, (S, E, W, P) in ARMS.items():
    s = 1 if side == "L" else -1
    loc, n = surf_near(S + Vector((0.25 * s, 0.1, 0.45)))
    metal.append(prim("cube", "plate", loc=loc + n * 0.02, rot=UP.rotation_difference(n), scale=(0.42, 0.3, 0.035), smooth=False))
    t, b = tangent_frame(n)
    for (u, v) in ((-0.17, -0.11), (0.17, -0.11), (-0.17, 0.11), (0.17, 0.11)):
        metal.append(prim("cyl", "rivet", loc=loc + n * 0.045 + t * u + b * v, rot=UP.rotation_difference(n), r1=0.03, r2=0.025, depth=0.03, seg=6, smooth=False))
metal = join(metal, "stacks")
set_material(metal, "metal")
# metal bands on forearms (rigid to lower arm)
bands = {}
for side, (S, E, W, P) in ARMS.items():
    d = (W - E).normalized()
    bl = []
    for t_, rr in ((0.38, 0.4), (0.62, 0.33)):
        c = E + (W - E) * t_
        bl.append(prim("torus", "band", loc=c, rot=UP.rotation_difference(d), R=rr, r=0.04, seg=16, seg2=4, smooth=False))
    # hydraulic piston along the forearm
    pa = E + (W - E) * 0.2 + Vector((0.3 if side == "L" else -0.3, 0.05, 0.12))
    pb = E + (W - E) * 0.8 + Vector((0.2 if side == "L" else -0.2, 0.0, 0.08))
    bl.append(cyl_between("piston", pa, pa + (pb - pa) * 0.6, 0.075, seg=10))
    bl.append(cyl_between("rod", pa + (pb - pa) * 0.55, pb, 0.04, seg=8))
    bands[side] = join(bl, "bands" + side)
    set_material(bands[side], "metal")

rub = []
for (a, b, lift, r) in [((0.3, -0.3, 0.45), (0.95, 0.05, None), 0.4, 0.055), ((-1.08, 0.75, 0.4), (-1.5, 0.15, None), 0.35, 0.05),
                         ((1.12, 0.95, 0.5), (1.45, 1.75, None), 0.35, 0.05), ((-0.05, 0.95, 0.35), (-0.4, 1.95, None), 0.45, 0.045),
                         ((0.45, -0.75, None), (0.78, -1.32, None), 0.45, 0.06), ((-0.4, -0.7, None), (-0.75, -1.3, None), 0.5, 0.05),
                         ((0.3, -0.3, 0.3), (-0.3, -0.5, None), 0.3, 0.04)]:
    if a[2] is not None:
        st = min(STACKS, key=lambda s: (s[0].xy - Vector(a[:2])).length)
        pa = st[0] + st[1] * a[2] + Vector((b[0] - a[0], b[1] - a[1], 0)).normalized() * (st[3] + 0.02)
    else:
        pa, _ = osurf_s(a[0], a[1])
        pa = pa - _ * 0.05
    pb, nb = osurf_s(b[0], b[1])
    pb = pb - nb * 0.06
    mid = (pa + pb) / 2 + UP * lift
    pts = bez([pa, mid, pb], 6)
    rub.append([(q_, r) for q_ in pts])
# cable stitches across seams in the stretched skin
SEAMS = [[(-1.25, -0.2), (-0.9, 0.5), (-0.75, 1.1), (-0.2, 1.75)], [(0.4, 0.15), (0.85, 0.95), (1.3, 1.5)],
         [(-0.75, -0.5), (0.0, -0.6), (0.75, -0.45)]]
SEAM3 = []
for sm in SEAMS:
    pts3 = [osurf_s(x, y)[0] for (x, y) in sm]
    dense = bez(pts3, 6)
    dense = [osurf_s(p.x, p.y)[0] for p in dense]
    SEAM3.append(dense)
    for i in range(0, len(dense) - 1):
        p, n = osurf_s(dense[i].x, dense[i].y)
        d = (dense[i + 1] - dense[i]).normalized()
        sd = n.cross(d).normalized()
        rub.append([(p + sd * 0.09 - n * 0.02, 0.016), (p + sd * 0.0 + d * 0.04 + n * 0.035, 0.018), (p - sd * 0.09 + d * 0.08 - n * 0.02, 0.016)])
rub = skin_tubes("hoses", rub, subsurf=1)
rub = decimate(rub, 3000)
shade_smooth(rub)
set_material(rub, "rubber")

# ------------------------------------------------------------ tail of intestines + hoses
tail_pts = bez(TAIL, 6)
tparts = []
offs = [(0.0, 0.0, 0.16, "gut"), (0.28, 0.06, 0.11, "gut"), (-0.26, 0.04, 0.12, "gut"), (0.16, -0.05, 0.07, "hose"),
        (-0.12, 0.12, 0.06, "hose"), (0.36, 0.1, 0.05, "hose"), (-0.38, 0.0, 0.05, "hose")]
gut_ch, hose_ch = [], []
for j, (ox, oz, r, kind) in enumerate(offs):
    ch = []
    for i, p in enumerate(tail_pts):
        t = i / (len(tail_pts) - 1)
        d = (tail_pts[min(i + 1, len(tail_pts) - 1)] - tail_pts[max(i - 1, 0)]).normalized()
        sd = d.cross(UP).normalized()
        wob = math.sin(t * 9 + j * 1.7) * 0.12 * t
        pp = p + sd * (ox * (1 + t * 0.8) + wob) + UP * (oz * (1 - t))
        pp.z = max(pp.z, r * 0.8) if t > 0.3 else pp.z
        rr = r * (1 - 0.35 * t)
        if kind == "gut":
            rr *= 1.0 + 0.22 * math.sin(i * 1.9 + j)
        ch.append((pp - d * 0.0, rr))
    # start inside the rump
    ch.insert(0, (ch[0][0] - (tail_pts[1] - tail_pts[0]).normalized() * 0.5 + UP * 0.1, ch[0][1]))
    (gut_ch if kind == "gut" else hose_ch).append(ch)
guts = skin_tubes("guts", gut_ch, subsurf=1)
guts = remesh(guts, 0.022)
smooth(guts, 2)
guts = decimate(guts, 2200)
shade_smooth(guts)
set_material(guts, "flesh")
thoses = skin_tubes("thoses", hose_ch, subsurf=1)
thoses = decimate(thoses, 1100)
shade_smooth(thoses)
set_material(thoses, "rubber")

# ------------------------------------------------------------ rig
bones = [dict(name="root", head=(0, 0, 0), tail=(0, 0, 0.5), deform=False),
         dict(name="body", head=(0, 1.4, 1.25), tail=(0, -0.25, 1.55), parent="root"),
         dict(name="chest", head=(0, -0.25, 1.55), tail=(0, -1.05, 1.95), parent="body", connect=True),
         dict(name="furnace", head=F, tail=F + D * 0.5, parent="chest", deform=False),
         dict(name="neck", head=NECK[0], tail=NECK[1], parent="chest"),
         dict(name="head", head=NECK[1], tail=HEADC + HEADDIR * 0.16, parent="neck", connect=True),
         dict(name="head_end", head=HEADC + HEADDIR * 0.16, tail=HEADC + HEADDIR * 0.3, parent="head", connect=True, deform=False)]
for side, (S, E, W, P) in ARMS.items():
    fwd = Vector((P.x - W.x, P.y - W.y, 0)).normalized()
    bones += [dict(name="arm_%s_upper" % side, head=S, tail=E, parent="chest"),
              dict(name="arm_%s_lower" % side, head=E, tail=W, parent="arm_%s_upper" % side, connect=True),
              dict(name="arm_%s_hand" % side, head=W, tail=P, parent="arm_%s_lower" % side, connect=True),
              dict(name="arm_%s_end" % side, head=P, tail=P + fwd * 0.3, parent="arm_%s_hand" % side, connect=True, deform=False)]
bones += [dict(name="tail_1", head=TAIL[0], tail=TAIL[1], parent="body"),
          dict(name="tail_2", head=TAIL[1], tail=TAIL[2], parent="tail_1", connect=True),
          dict(name="tail_3", head=TAIL[2], tail=TAIL[3], parent="tail_2", connect=True),
          dict(name="tail_end", head=TAIL[3], tail=TAIL[3] + Vector((0, 0.25, 0)), parent="tail_3", connect=True, deform=False)]
for i, (c, n) in enumerate(SACS):
    bones.append(dict(name="sac_%d" % (i + 1), head=c, tail=c + n * 0.35, parent="body"))
arm = armature("boss_rig", bones)

SEG = {"body": ((0, 1.5, 1.1), (0, -0.1, 1.45)), "chest": ((0, -0.35, 1.55), (0, -1.1, 1.8)),
       "neck": (tuple(NECK[0]), tuple(NECK[1])), "head": (tuple(NECK[1]), tuple(HEADC))}
SC = {"body": 0.95, "chest": 0.8, "neck": 0.12, "head": 0.12}
for side, (S, E, W, P) in ARMS.items():
    SEG["arm_%s_upper" % side] = (tuple(S + (E - S) * 0.15), tuple(E))
    SEG["arm_%s_lower" % side] = (tuple(E), tuple(W))
    SEG["arm_%s_hand" % side] = (tuple(W), tuple(P + (P - W).normalized() * 0.3))
    SC["arm_%s_upper" % side] = 0.42
    SC["arm_%s_lower" % side] = 0.36
    SC["arm_%s_hand" % side] = 0.3
for i in range(3):
    SEG["tail_%d" % (i + 1)] = (tuple(TAIL[i]), tuple(TAIL[i + 1]))
    SC["tail_%d" % (i + 1)] = 0.25


def rigid(obj, bone):
    obj.vertex_groups.clear()
    g = obj.vertex_groups.new(name=bone)
    g.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")


# main mass: body / chest / arms / neck root
main_c = ["body", "chest", "neck", "head"] + [k for k in SEG if k.startswith("arm_")]
co = get_co(org)


def main_region(c):
    m = np.ones((len(c), len(main_c)))
    # neck/head only near the neck tube
    nd = np.linalg.norm(c - np.array(NECK[0]), axis=1)
    m[:, main_c.index("neck")] = (c[:, 1] < -1.15).astype(float) * (c[:, 2] > 2.0)
    m[:, main_c.index("head")] = (c[:, 1] < -1.45).astype(float) * (c[:, 2] > 1.9)
    return m


weights(org, SEG, SC, main_c, power=4, smooth_iters=4, region=main_region)
weights(head_org, SEG, SC, ["chest", "neck", "head"], power=4, smooth_iters=2,
        rigid=[("head" if (Vector(p) - HEADC).length < 0.2 else None) for p in get_co(head_org)])
weights(guts, SEG, SC, ["body", "tail_1", "tail_2", "tail_3"], power=4, smooth_iters=3)
weights(thoses, SEG, SC, ["body", "tail_1", "tail_2", "tail_3"], power=4, smooth_iters=3)
for o in (darms, metal, rub):
    rigid(o, "body")
for o in (ribs, glow, iron):
    rigid(o, "chest")
for o in (mask, slit, strap):
    rigid(o, "head")
for side in ("L", "R"):
    rigid(bands[side], "arm_%s_lower" % side)
for i, o in enumerate(sacs):
    rigid(o, "sac_%d" % (i + 1))
# claws -> hand bones
claws.vertex_groups.clear()
gl, gr = claws.vertex_groups.new(name="arm_L_hand"), claws.vertex_groups.new(name="arm_R_hand")
for v in claws.data.vertices:
    (gl if v.co.x > 0 else gr).add([v.index], 1.0, "REPLACE")

for o_ in [org, darms, ribs, claws, glow, iron, head_org, mask, metal, rub, guts, thoses]:
    c_ = get_co(o_)
    pass
mesh = join([org, darms, ribs, claws, glow, iron, head_org, mask, slit, strap] + sacs + [metal, bands["L"], bands["R"], rub, guts, thoses], "boss")
shade_smooth(mesh)
for p in mesh.data.polygons:
    if mesh.data.materials[p.material_index].name in ("metal",):
        p.use_smooth = False

# ------------------------------------------------------------ paint
co = get_co(mesh)
nv = len(co)
me = mesh.data
names = [m.name for m in me.materials]
vmat = np.zeros(nv, int)
for p in me.polygons:
    for v in p.vertices:
        vmat[v] = p.material_index
vname = np.array(names)[vmat]
print("painting", nv)
occ = blur(ao(mesh, rays=16, dist=0.45), mesh, 1)
curv = blur(curvature(mesh), mesh, 2)
n1 = nfield(co, 1.3, (1, 2, 3), octaves=3)
n2 = nfield(co, 4.5, (5, 1, 2), octaves=2)
n3 = nfield(co, 12, (2, 8, 1))
vein = 1 - smoothstep(0.0, 0.05, np.abs(nfield(co, 2.2, (9, 9, 1), octaves=3)))
vein2 = 1 - smoothstep(0.0, 0.04, np.abs(nfield(co, 6, (3, 7, 1))))

pale = np.array([0.55, 0.42, 0.37])
corpse = np.array([0.44, 0.41, 0.38])
waxy = np.array([0.6, 0.53, 0.4])
bruise = np.array([0.24, 0.11, 0.17])
col = mix(pale, corpse, smoothstep(-0.3, 0.4, n1))
col = mix(col, waxy, smoothstep(0.15, 0.6, n2) * 0.7)
blot = smoothstep(0.1, 0.5, nfield(co, 0.9, (7, 3, 1), octaves=2))
col = mix(col, np.array([0.3, 0.1, 0.12]), blot * 0.55)
col = mix(col, np.array([0.5, 0.47, 0.42]), smoothstep(0.2, 0.6, nfield(co, 0.7, (2, 9, 4))) * 0.5)
col = mix(col, bruise, smoothstep(0.1, 0.6, -n2) * 0.65)
col = mix(col, np.array([0.45, 0.14, 0.15]), smoothstep(0.3, 0.7, n3) * 0.25)
# per-torso tints so the fused bodies read as separate people
tints = [(0.62, 0.5, 0.42), (0.38, 0.33, 0.36), (0.6, 0.42, 0.36), (0.5, 0.48, 0.42), (0.36, 0.22, 0.25),
         (0.62, 0.55, 0.45), (0.45, 0.36, 0.4), (0.55, 0.38, 0.33), (0.42, 0.4, 0.33)]
for (c, n, ax, sd), t in zip(TORSOS, tints):
    rel = co - np.array(c)
    dd = np.sqrt((rel @ np.array(sd) / 0.36) ** 2 + (rel @ np.array(ax) / 0.6) ** 2 + (rel @ np.array(n) / 0.35) ** 2)
    col = mix(col, np.array(t), (1 - smoothstep(0.7, 1.15, dd)) * 0.7)
col = mix(col, np.array([0.17, 0.07, 0.14]), np.clip(vein * 0.6 + vein2 * 0.3, 0, 1) * 0.6)
# seams: raw dark red lines under the cable stitching
sd_ = np.full(nv, 9.0)
for dense in SEAM3:
    for i in range(len(dense) - 1):
        a, b = np.array(dense[i]), np.array(dense[i + 1])
        ab = b - a
        t = np.clip(((co - a) @ ab) / (ab @ ab + 1e-9), 0, 1)
        sd_ = np.minimum(sd_, np.linalg.norm(co - (a + t[:, None] * ab), axis=1))
col = mix(col, np.array([0.3, 0.04, 0.06]), (1 - smoothstep(0.02, 0.1, sd_)) * 0.9)
col = mix(col, np.array([0.5, 0.25, 0.25]), ((1 - smoothstep(0.1, 0.2, sd_)) * smoothstep(0.05, 0.1, sd_)) * 0.4)
# around the sacs: inflamed
for c, n in SACS:
    dsac = np.linalg.norm(co - np.array(c), axis=1)
    col = mix(col, np.array([0.42, 0.08, 0.1]), (1 - smoothstep(0.3, 0.55, dsac)) * 0.6)
# furnace: scorched flesh, heat-reddened halo
fr, fh = furnace_local(co)
scorch = (1 - smoothstep(FRAD + 0.1, FRAD + 0.75, fr)) * (1 - smoothstep(0.2, 0.9, fh)) * (fh > -1.0)
col = mix(col, np.array([0.48, 0.12, 0.05]), scorch * 0.55)
col = mix(col, np.array([0.06, 0.04, 0.035]), (1 - smoothstep(FRAD + 0.05, FRAD + 0.35, fr)) * (fh > -1.0) * (fh < 0.5) * (0.6 + 0.4 * smoothstep(-0.2, 0.4, n3)))
# soot from the stacks: dark streaks running down
for (p, d, h, r) in STACKS:
    rel = co - np.array(p)
    dxy = np.linalg.norm(rel[:, :2], axis=1)
    streak = (1 - smoothstep(r + 0.1, r + 0.6 + 0.3 * n2, dxy)) * (rel[:, 2] < 0.15)
    col = mix(col, np.array([0.07, 0.06, 0.055]), streak * 0.75)
# arms: bruised knuckles, filthy hands
for side, (S, E, W, P) in ARMS.items():
    dh = np.linalg.norm(co - np.array(P), axis=1)
    col = mix(col, np.array([0.18, 0.12, 0.1]), (1 - smoothstep(0.3, 0.9, dh)) * 0.6)
    de = np.linalg.norm(co - np.array(E), axis=1)
    col = mix(col, np.array([0.4, 0.12, 0.16]), (1 - smoothstep(0.2, 0.5, de)) * 0.5)
# decorative arms: paler, dead, darker fingertips
for p in DARM_BASES:
    db = np.linalg.norm(co - np.array(p), axis=1)
    col = mix(col, np.array([0.25, 0.04, 0.06]), (1 - smoothstep(0.03, 0.14, db)) * 0.8)
# grime toward the floor
col = mix(col, np.array([0.13, 0.1, 0.09]), (1 - smoothstep(0.0, 0.5, co[:, 2])) * 0.65)
cav_ = np.clip(smoothstep(0.08, 0.45, occ) + np.clip(curv, 0, None) * 0.5, 0, 1)
col = mix(col, np.array([0.08, 0.012, 0.025]), cav_ * 0.88)
col *= (1 - 0.3 * occ)[:, None]
col = mix(col, np.array([0.68, 0.62, 0.55]), np.clip(-curv, 0, 1) * 0.2)

# per-material
isn = lambda nm: (vname == nm)[:, None]
dark = np.array([0.3, 0.035, 0.04]) * (1 - 0.5 * occ[:, None]) + 0.05 * n2[:, None]
dark = mix(dark, np.array([0.06, 0.035, 0.03]), smoothstep(-0.1, 0.4, n3) * 0.5)
col = np.where(isn("flesh_dark"), dark, col)
bonec = mix(np.array([0.82, 0.76, 0.6]), np.array([0.4, 0.17, 0.12]), np.clip(occ * 1.3 + smoothstep(0.2, 0.6, n2) * 0.4, 0, 1))
fr_, fh_ = fr, fh
bonec = mix(bonec, np.array([0.12, 0.08, 0.06]), (1 - smoothstep(FRAD + 0.1, FRAD + 0.5, fr_)) * (fh_ < 0.3) * 0.5)
col = np.where(isn("bone"), bonec, col)
rust = mix(np.array([0.2, 0.19, 0.18]), np.array([0.42, 0.16, 0.05]), smoothstep(-0.35, 0.35, nfield(co, 6, (1, 1, 1), octaves=3)))
rust = mix(rust, np.array([0.55, 0.28, 0.1]), smoothstep(0.3, 0.6, nfield(co, 16, (4, 1, 1))) * 0.6)
rust = mix(rust, np.array([0.4, 0.38, 0.35]), np.clip(-curv * 1.5, 0, 1) * 0.5)  # worn edges
rust *= (1 - 0.45 * occ)[:, None]
# soot at the top of stacks
for (p, d, h, r) in STACKS:
    top = np.array(p + d * h)
    dt = np.linalg.norm(co - top, axis=1)
    rust = mix(rust, np.array([0.05, 0.045, 0.04]), (1 - smoothstep(0.1, 0.45, dt)))
col = np.where(isn("metal"), rust, col)
rubc = np.array([0.14, 0.13, 0.13]) * (1 + 0.35 * n3[:, None]) * (1 - 0.4 * occ[:, None])
col = np.where(isn("rubber"), rubc, col)
sv = 1 - smoothstep(0.0, 0.07, np.abs(nfield(co, 5, (8, 1, 1), octaves=2)))
sv2 = 1 - smoothstep(0.0, 0.05, np.abs(nfield(co, 12, (1, 8, 4))))
sacc = mix(np.array([0.62, 0.74, 0.2]), np.array([0.82, 0.8, 0.35]), smoothstep(-0.4, 0.4, n2))
sacc = mix(sacc, np.array([0.12, 0.1, 0.03]), np.clip(sv * 0.9 + sv2 * 0.55, 0, 1))
col = np.where(isn("glow_bile"), sacc, col)
hot = mix(np.array([1.0, 0.62, 0.15]), np.array([0.8, 0.14, 0.02]), smoothstep(0.1, 0.8, fr / FRAD))
hot = mix(hot, np.array([0.25, 0.05, 0.02]), smoothstep(0.25, 0.6, n3) * 0.6)
col = np.where(isn("glow_furnace"), hot, col)
col = np.where(isn("glow_red"), np.array([1.0, 0.15, 0.08]), col)
set_colors(mesh, col)

bind(mesh, arm)
report(mesh, arm)
export_glb(os.path.join(OUT_DIR, "boss.glb"), [arm, mesh])
print("FURNACE", tuple(round(x, 3) for x in F), "dir", tuple(round(x, 3) for x in D))

if RENDER:
    P = PREV_DIR
    render_sheet(os.path.join(P, "boss_sheet.png"), (0, 0, 1.4), 3.0)
    render_game(os.path.join(P, "boss_game.png"), os.path.join(P, "boss_game_zoom.png"), target=(0, -0.3, 1.0), spot=62, zoom=2.2)
    pb = arm.pose.bones
    for nm, r in (("arm_L_upper", (0.6, 0, 0.3)), ("arm_L_lower", (-0.8, 0, 0)), ("arm_R_upper", (-0.3, 0.2, -0.2)),
                  ("arm_R_lower", (0.5, 0, 0)), ("neck", (0.4, 0, 0.3)), ("head", (0.5, 0.3, 0)),
                  ("tail_1", (0, 0, 0.4)), ("tail_2", (0.2, 0, 0.5)), ("tail_3", (0, 0, 0.6)), ("chest", (0.15, 0, 0.1))):
        pb[nm].rotation_mode = "XYZ"
        pb[nm].rotation_euler = r
    pb["sac_1"].scale = (1.3, 1.3, 1.3)
    bpy.context.view_layer.update()
    render_sheet(os.path.join(P, "boss_pose.png"), (0, 0, 1.4), 3.0, views=("front", "back"))
