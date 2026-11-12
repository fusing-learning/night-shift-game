"""gibs.glb + growths.glb (static). Run: Blender -b --python props.py [-- norender]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, mlib
importlib.reload(mlib)
from mlib import *

RENDER = "norender" not in sys.argv
reset()
rnd = random.Random(5)
UP = Vector((0, 0, 1))


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


def vert_mats(obj):
    me = obj.data
    names = [m.name for m in me.materials]
    vm = np.zeros(len(me.vertices), int)
    for p in me.polygons:
        for v in p.vertices:
            vm[v] = p.material_index
    return np.array(names)[vm]


def recentre(obj, ground=False):
    co = get_co(obj)
    c = (co.min(0) + co.max(0)) / 2
    if ground:
        c[2] = co[:, 2].min()
    set_co(obj, co - c)


def meat_paint(obj, seed=0, fat=0.35):
    co = get_co(obj)
    vn = vert_mats(obj)
    occ = blur(ao(obj, rays=16, dist=0.06), obj, 1)
    n1 = nfield(co, 18, (seed, 1, 2), octaves=2)
    n2 = nfield(co, 45, (2, seed, 5))
    col = mix(np.array([0.3, 0.02, 0.035]), np.array([0.14, 0.03, 0.08]), smoothstep(-0.3, 0.4, n1))
    col = mix(col, np.array([0.45, 0.07, 0.07]), smoothstep(0.2, 0.6, n2) * 0.5)
    col = mix(col, np.array([0.74, 0.66, 0.48]), smoothstep(0.35, 0.6, nfield(co, 12, (seed, 7, 1))) * fat)
    col = mix(col, np.array([0.07, 0.01, 0.02]), smoothstep(0.1, 0.5, occ))
    bone = mix(np.array([0.8, 0.74, 0.58]), np.array([0.45, 0.15, 0.12]), np.clip(occ * 1.5 + smoothstep(0.2, 0.6, n2) * 0.3, 0, 1))
    col = np.where((vn == "bone")[:, None], bone, col)
    set_colors(obj, col)


# ====================================================================== GIBS
gibs = []
# 1: torn flesh lump
o = metaballs("mb_g1", [dict(type="BALL", co=(0, 0, 0), r=0.08), dict(type="BALL", co=(0.06, 0.02, 0.02), r=0.06),
                        dict(type="BALL", co=(-0.05, -0.03, 0.01), r=0.055), dict(type="BALL", co=(0.0, 0.06, -0.02), r=0.05)], res=0.01)
lumps(o, s1=(25, 0.012), s2=(70, 0.004), seed=1)
o = decimate(o, 280)
set_material(o, "flesh_dark")
o.name = "gib_1"
gibs.append(o)
# 2: chunk with splintered bone sticking out
o = metaballs("mb_g2", [dict(type="ELLIPSOID", co=(0, 0, 0), r=0.08, s=(1.3, 1, 0.8)), dict(type="BALL", co=(0.07, 0.0, 0.02), r=0.05)], res=0.012)
lumps(o, s1=(22, 0.012), s2=(60, 0.004), seed=2)
o = decimate(o, 220)
set_material(o, "flesh_dark")
b = cyl_between("bone", Vector((-0.02, 0, 0)), Vector((-0.17, 0.03, 0.06)), 0.022, 0.016, seg=6)
tip = cone_between("bt", Vector((-0.17, 0.03, 0.06)), Vector((-0.21, 0.035, 0.085)), 0.017, seg=5)
b = join([b, tip], "b2")
set_material(b, "bone")
o = join([o, b], "gib_2")
gibs.append(o)
# 3: rib fragment with meat
pts = bez([Vector((-0.14, 0, 0)), Vector((-0.04, 0.05, 0.02)), Vector((0.06, 0.06, 0.02)), Vector((0.15, 0.02, 0))], 3)
rib = skin_tubes("rib", [[(p, 0.018) for p in pts]], subsurf=0)
rib = decimate(rib, 150)
set_material(rib, "bone")
m = metaballs("mb_g3", [dict(type="ELLIPSOID", co=(-0.02, 0.04, 0.0), r=0.04, s=(1.6, 1, 0.8)), dict(type="BALL", co=(0.08, 0.05, 0.01), r=0.03)], res=0.01)
lumps(m, s1=(30, 0.008), s2=(80, 0.003), seed=3)
m = decimate(m, 130)
set_material(m, "flesh_dark")
o = join([rib, m], "gib_3")
gibs.append(o)
# 4: severed hand
ch = [[(Vector((0, -0.08, 0.03)), 0.042), (Vector((0, -0.05, 0.03)), 0.045), (Vector((0, 0.0, 0.025)), 0.055), (Vector((0, 0.045, 0.025)), 0.05)]]
for fi, (a, L_) in enumerate([(-55, 0.08), (-15, 0.115), (0, 0.13), (14, 0.12), (30, 0.1)]):
    d = Quaternion(UP, math.radians(a)) @ Vector((0, 1, 0))
    b0 = Vector((0.012 * (fi - 2), 0.02, 0.025)) + d * 0.02
    curl = (0.3, 0.8, 0.2, 0.9, 0.5)[fi]
    ch.append([(b0 + d * 0.02, 0.024), (b0 + d * L_ * 0.55 + UP * 0.012, 0.021), (b0 + d * L_ * 1.05 - UP * 0.02 * curl + UP * 0.03 * curl, 0.017)])
o = skin_tubes("hand", ch, subsurf=1)
o = remesh(o, 0.007)
smooth(o, 2)
o = decimate(o, 290)
set_material(o, "flesh")
o.data.materials.append(material("flesh_dark"))
for p in o.data.polygons:
    if p.center.y < -0.07:
        p.material_index = 1
o.name = "gib_4"
gibs.append(o)
# 5: tooth-studded jaw piece
m = metaballs("mb_g5", [dict(type="CAPSULE", a=(-0.06, 0, 0), b=(0.06, 0.02, 0), r=0.035), dict(type="BALL", co=(0, -0.02, -0.01), r=0.04)], res=0.01)
lumps(m, s1=(25, 0.008), s2=(70, 0.003), seed=5)
m = decimate(m, 160)
set_material(m, "flesh_dark")
teeth = []
for i in range(7):
    x = -0.06 + i * 0.02
    base = Vector((x, 0.01 + 0.003 * i, 0.025))
    teeth.append(cone_between("t", base, base + Vector((rnd.uniform(-0.01, 0.01), 0.005, 0.03 + rnd.uniform(0, 0.015))), 0.008, seg=4))
t = join(teeth, "teeth")
set_material(t, "bone")
o = join([m, t], "gib_5")
gibs.append(o)
# 6: intestine loop
pts = bez([Vector((-0.1, -0.05, 0)), Vector((0.0, -0.08, 0.01)), Vector((0.09, 0.0, 0.02)), Vector((0.02, 0.07, 0.03)), Vector((-0.07, 0.03, 0.05)), Vector((-0.02, -0.02, 0.07))], 3)
o = skin_tubes("gut", [[(p, 0.022 + 0.005 * math.sin(i * 1.7)) for i, p in enumerate(pts)]], subsurf=1)
o = remesh(o, 0.008)
smooth(o, 2)
o = decimate(o, 280)
set_material(o, "flesh_dark")
o.name = "gib_6"
gibs.append(o)

for m_ in list(bpy.data.meshes):
    if m_.users == 0:
        bpy.data.meshes.remove(m_)
for i, g in enumerate(gibs):
    g.name = "gib_%d" % (i + 1)
    recentre(g)
    shade_smooth(g)
    meat_paint(g, seed=i, fat=0.15 if i == 3 else 0.35)
    if g.name == "gib_4":  # the hand stays pale/grey-pink with a raw stump
        co = get_co(g)
        vn = vert_mats(g)
        occ = blur(ao(g, rays=16, dist=0.04), g, 1)
        skin = mix(np.array([0.52, 0.4, 0.37]), np.array([0.28, 0.16, 0.24]), smoothstep(-0.2, 0.5, nfield(co, 20, (1, 1, 1))) * 0.6)
        skin = mix(skin, np.array([0.1, 0.02, 0.03]), smoothstep(0.1, 0.5, occ))
        stump = np.array([0.35, 0.03, 0.05])
        col = np.where((vn == "flesh_dark")[:, None], stump, skin)
        set_colors(g, col)
    g.data.name = g.name
    print("GIB", g.name, tri_count(g), (get_co(g).max(0) - get_co(g).min(0)).round(3), [m.name for m in g.data.materials])
export_glb(os.path.join(OUT_DIR, "gibs.glb"), gibs)
if RENDER:
    for i, g in enumerate(gibs):
        g.location = ((i % 3 - 1) * 0.42, (i // 3 - 0.5) * 0.42, 0.15)
    render_sheet(os.path.join(PREV_DIR, "gibs_sheet.png"), (0, 0, 0.1), 0.55, views=("front", "top"))
for g in gibs:
    bpy.data.objects.remove(g, do_unlink=True)

# ====================================================================== GROWTHS


def flesh_paint(obj, seed=0, ao_dist=0.25, extra=None):
    co = get_co(obj)
    vn = vert_mats(obj)
    occ = blur(ao(obj, rays=16, dist=ao_dist), obj, 1)
    curv = blur(curvature(obj), obj, 2)
    n1 = nfield(co, 2.5, (seed, 2, 3), octaves=3)
    n2 = nfield(co, 8, (5, seed, 2), octaves=2)
    vein = 1 - smoothstep(0.0, 0.06, np.abs(nfield(co, 5, (9, seed, 1), octaves=2)))
    col = mix(np.array([0.55, 0.42, 0.37]), np.array([0.44, 0.4, 0.37]), smoothstep(-0.3, 0.4, n1))
    col = mix(col, np.array([0.28, 0.12, 0.17]), smoothstep(0.05, 0.6, -n2) * 0.6)
    col = mix(col, np.array([0.62, 0.55, 0.42]), smoothstep(0.25, 0.6, n2) * 0.5)
    col = mix(col, np.array([0.17, 0.08, 0.16]), vein * 0.6)
    col = mix(col, np.array([0.2, 0.15, 0.13]), (1 - smoothstep(0.0, 0.08, np.abs(co[:, 2]))) * 0.5)
    cav = np.clip(smoothstep(0.08, 0.45, occ) + np.clip(curv, 0, None) * 0.5, 0, 1)
    col = mix(col, np.array([0.08, 0.012, 0.025]), cav * 0.85)
    col *= (1 - 0.25 * occ)[:, None]
    dark = np.array([0.32, 0.03, 0.05]) * (1 - 0.5 * occ[:, None]) + 0.05 * n2[:, None]
    col = np.where((vn == "flesh_dark")[:, None], dark, col)
    sv = 1 - smoothstep(0.0, 0.07, np.abs(nfield(co, 9, (8, 1, seed), octaves=2)))
    sac = mix(np.array([0.66, 0.76, 0.22]), np.array([0.14, 0.12, 0.03]), sv * 0.85)
    col = np.where((vn == "glow_bile")[:, None], sac, col)
    rust = mix(np.array([0.2, 0.19, 0.18]), np.array([0.42, 0.16, 0.05]), smoothstep(-0.3, 0.3, nfield(co, 10, (1, 1, 1), octaves=2)))
    col = np.where((vn == "metal")[:, None], rust * (1 - 0.4 * occ[:, None]), col)
    if extra:
        col = extra(co, vn, col)
    set_colors(obj, col)


def tendril_tree(origin, direction, length, r0, depth, rng, flat=True, out=None, spread=0.6):
    """branching polyline chains hugging the floor"""
    if out is None:
        out = []
    n = max(3, int(length / 0.08))
    pts = [origin]
    d = direction.normalized()
    for i in range(n):
        d = (d + Vector((rng.uniform(-spread, spread), rng.uniform(-spread, spread), 0)) * 0.3).normalized()
        if flat:
            d.z = 0
            d.normalize()
        pts.append(pts[-1] + d * (length / n))
    ch = [(p, r0 * (1 - 0.8 * i / n) + 0.004) for i, p in enumerate(pts)]
    out.append(ch)
    if depth > 0:
        for k in range(rng.randint(1, 2)):
            j = rng.randint(1, n - 1)
            nd = Quaternion(UP, rng.choice([-1, 1]) * rng.uniform(0.5, 1.1)) @ d
            tendril_tree(pts[j], nd, length * 0.55, ch[j][1] * 0.8, depth - 1, rng, flat, out, spread)
    return out


def pods(name, specs, tendrils, seed, burst=None, target=2400):
    rng = random.Random(seed)
    parts = [metaballs("mb_" + name, [dict(type="ELLIPSOID", co=(0, 0, 0.0), r=0.3, s=(1.35, 1.25, 0.4))], res=0.02)]
    centers = []
    for (x, y, h, glow) in specs:
        r = h * 0.36
        c = Vector((x, y, h * 0.5))
        tilt = Vector((x, y, 0)) * 0.8
        q = UP.rotation_difference((UP + tilt).normalized())
        egg = prim("ico", "egg", loc=(0, 0, 0), scale=(r, r, r * 1.4), sub=3)
        ec = get_co(egg)
        zn = np.clip(ec[:, 2] / (r * 1.4), -1, 1)
        ec[:, :2] *= (1 - 0.18 * np.clip(zn, 0, 1))[:, None]   # egg taper
        M = np.array(q.to_matrix())
        set_co(egg, ec @ M.T + np.array(c))
        parts.append(egg)
        centers.append((c, r, glow, q))
    chains = []
    for k in range(tendrils):
        a = 2 * math.pi * k / tendrils + rng.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), math.sin(a), 0))
        tendril_tree(d * 0.25 + UP * 0.02, d, rng.uniform(0.45, 0.7), 0.04, 2, rng, out=chains)
    parts.append(skin_tubes(name + "_t", chains, subsurf=1))
    o = join(parts, name)
    o = remesh(o, 0.014)
    smooth(o, 2)
    c = get_co(o)
    if burst is not None:
        bc, br, _, _ = centers[burst]
        dxy = np.linalg.norm(c[:, :2] - np.array(bc[:2]), axis=1)
        top = (c[:, 2] > bc.z + br * 0.2) & (dxy < br * 0.8)
        c[top, 2] -= (br * 1.1) * (1 - dxy[top] / (br * 0.8)) ** 0.7
    c[:, 2] = np.maximum(c[:, 2], 0)
    set_co(o, c)
    lumps(o, s1=(6, 0.01), s2=(20, 0.004), seed=seed)
    c = get_co(o)
    c[:, 2] = np.maximum(c[:, 2], 0)
    set_co(o, c)
    o = decimate(o, target)

    def mf(fc, fn):
        idx = np.zeros(len(fc), int)
        for (c, r, glow, q) in centers:
            loc = (fc - np.array(c)) @ np.array(q.to_matrix())
            d = np.linalg.norm(loc / np.array([1, 1, 1.4]), axis=1)
            if glow:
                idx[(d < r * 1.06) & (loc[:, 2] > -r * 0.9)] = 2
        if burst is not None:
            c, r, _, _ = centers[burst]
            d = np.linalg.norm(fc[:, :2] - np.array(c[:2]), axis=1)
            idx[(d < r * 0.82) & (fc[:, 2] > 0.05)] = 1
        return idx
    assign_faces(o, ["flesh", "flesh_dark", "glow_bile"], mf)
    shade_smooth(o)
    recentre(o, ground=True)
    flesh_paint(o, seed=seed, ao_dist=0.15)
    return o


growths = []
growths.append(pods("growth_pods_a", [(0.0, 0.0, 0.5, True), (0.18, 0.1, 0.36, False), (-0.16, 0.12, 0.4, False), (0.05, -0.2, 0.3, True),
                                       (-0.2, -0.12, 0.26, False), (0.25, -0.12, 0.22, False), (0.3, 0.25, 0.17, True),
                                       (-0.3, 0.2, 0.18, False), (-0.05, 0.28, 0.24, False)], 7, 3))
growths.append(pods("growth_pods_b", [(0.0, 0.05, 0.42, False), (0.24, -0.08, 0.5, False), (-0.22, -0.1, 0.34, True),
                                       (-0.05, -0.28, 0.24, False), (0.1, 0.3, 0.2, False), (-0.28, 0.18, 0.16, False)], 6, 8, burst=1))

# ---------------------------------------------------------------- mound
el = [dict(type="ELLIPSOID", co=(0, 0, 0.05), r=0.6, s=(1.25, 1.1, 0.85)),
      dict(type="BALL", co=(0.3, 0.15, 0.25), r=0.33), dict(type="BALL", co=(-0.3, -0.1, 0.3), r=0.32)]
mb = metaballs("mb_mound", el, res=0.03)
parts = [mb]
BVm = BVHTree.FromPolygons([v.co.copy() for v in mb.data.vertices], [tuple(p.vertices) for p in mb.data.polygons])


def msurf(x, y):
    hit = BVm.ray_cast(Vector((x, y, 3)), Vector((0, 0, -1)), 5)
    return hit[0], (hit[1] if hit[1].z > 0 else -hit[1])


rng = random.Random(3)
# heaped torsos
for (x, y, ang) in [(0.1, 0.05, 0.3), (-0.4, 0.25, 1.9), (0.45, -0.25, -1.0), (-0.25, -0.4, 0.8), (0.4, 0.4, 2.6)]:
    p, n = msurf(x, y)
    t0 = n.cross(Vector((0.3, 1, 0.1))).normalized()
    b0 = n.cross(t0)
    ax = (t0 * math.cos(ang) + b0 * math.sin(ang)).normalized()
    sd = n.cross(ax).normalized()
    rot = Matrix((sd, n, ax)).transposed().to_quaternion()
    parts.append(prim("ico", "tor", loc=p, rot=rot, scale=(0.2, 0.13, 0.27), sub=3))
    for s_ in (1, -1):
        parts.append(prim("ico", "bl", loc=p + n * 0.08 + sd * 0.09 * s_ + ax * 0.1, rot=rot, scale=(0.08, 0.04, 0.1), sub=2))
    parts.append(prim("ico", "hd", loc=p + ax * 0.36 + n * 0.0, rot=rot, scale=(0.1, 0.11, 0.12), sub=2))
# arms reaching out of the heap
for (x, y) in [(0.5, -0.4), (-0.55, 0.25), (-0.15, -0.5), (0.2, 0.5), (0.05, 0.1)]:
    p, n = msurf(x, y)
    out = Vector((x, y, 0)).normalized() if abs(x) + abs(y) > 0.3 else Vector((0.3, -1, 0)).normalized()
    d1 = (n * 0.8 + out * 0.6 + UP * 0.3).normalized()
    el_ = p + d1 * 0.2
    d2 = (out + UP * (0.2 if (x + y) > 0 else -0.6)).normalized()
    wr = el_ + d2 * 0.17
    hs = d2.cross(UP).normalized()
    ch = [[(p - d1 * 0.12, 0.065), (p + d1 * 0.08, 0.06), (el_, 0.05), (el_ + d2 * 0.12, 0.05), (wr, 0.036), (wr + d2 * 0.05, 0.046)]]
    for fi in range(-2, 3):
        fd = (d2 + hs * fi * 0.3).normalized()
        f0 = wr + d2 * 0.07 + hs * fi * 0.02
        ch.append([(f0, 0.02), (f0 + fd * 0.07, 0.018), (f0 + fd * 0.12 - UP * 0.04, 0.014)])
    parts.append(skin_tubes("mh", ch, subsurf=1))
# a leg jutting out
parts.append(skin_tubes("leg", [[(Vector((-0.3, 0.1, 0.4)), 0.09), (Vector((-0.65, 0.35, 0.55)), 0.075), (Vector((-0.72, 0.45, 0.25)), 0.06), (Vector((-0.78, 0.5, 0.06)), 0.05), (Vector((-0.86, 0.52, 0.05)), 0.045)]], subsurf=1))

o = join(parts, "growth_mound")
o = remesh(o, 0.013)
smooth(o, 2)
lumps(o, s1=(4, 0.03), s2=(14, 0.008), seed=4)
c = get_co(o)
c[:, 2] = np.maximum(c[:, 2], 0)
set_co(o, c)
o = decimate(o, 3500)
assign_faces(o, ["flesh", "flesh_dark"], lambda fc, fn: np.zeros(len(fc), int))
shade_smooth(o)
pipe = [cyl_between("pipe", Vector((0.05, -0.1, 0.2)), Vector((0.3, -0.05, 1.0)), 0.07, seg=10),
        cyl_between("flange", Vector((0.256, -0.059, 0.86)), Vector((0.268, -0.056, 0.9)), 0.1, seg=10),
        cyl_between("pend", Vector((0.3, -0.05, 1.0)), Vector((0.31, -0.048, 1.04)), 0.085, seg=10, caps=False)]
pipe = join(pipe, "pipe")
set_material(pipe, "metal")
o = join([o, pipe], "growth_mound")
recentre(o, ground=True)
co_ = get_co(o)
co_[:, :2] -= 0  # keep
flesh_paint(o, seed=4, ao_dist=0.25)
growths.append(o)

# ---------------------------------------------------------------- wall growth (wall at +Y, bulges toward -Y)
W, H = 2.0, 2.5
nx, nz = 34, 42
bm = bmesh.new()
grid = {}
for i in range(nx + 1):
    for j in range(nz + 1):
        x = -W / 2 + W * i / nx
        z = H * j / nz
        ex = 1 - (2 * abs(x) / W) ** 2
        ez = math.sin(math.pi * z / H) ** 0.7
        bulge = 0.22 * ex * ez + 0.06 * noise.noise(Vector((x * 2, 0, z * 2)))
        grid[i, j] = bm.verts.new((x + 0.04 * noise.noise(Vector((x * 3, 1, z * 3))), 0.08 - bulge, z))
holes = 0
for i in range(nx):
    for j in range(nz):
        x = -W / 2 + W * (i + 0.5) / nx
        z = H * (j + 0.5) / nz
        nv_ = noise.noise(Vector((x * 2.2, 5, z * 2.2)))
        edge = max(abs(x) / (W / 2), abs(z - H / 2) / (H / 2))
        if nv_ > 0.28 - 0.5 * max(0, edge - 0.75):
            holes += 1
            continue
        bm.faces.new((grid[i, j], grid[i + 1, j], grid[i + 1, j + 1], grid[i, j + 1]))
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
me = bpy.data.meshes.new("membrane")
bm.to_mesh(me)
bm.free()
mem = link(bpy.data.objects.new("membrane", me))
sol = mem.modifiers.new("sol", "SOLIDIFY")
sol.thickness = 0.035
mem = apply_mods(mem)
# tendrils climbing the sheet (vertical branching)
rng = random.Random(9)
chains = []
for k in range(7):
    x0 = rng.uniform(-0.9, 0.9)
    pts = [Vector((x0, 0.06, 0.0))]
    d = Vector((rng.uniform(-0.3, 0.3), 0, 1)).normalized()
    n = 22
    for i in range(n):
        d = (d + Vector((rng.uniform(-0.25, 0.25), 0, rng.uniform(-0.05, 0.1)))).normalized()
        p = pts[-1] + d * (2.4 / n)
        ex = max(0, 1 - (2 * abs(p.x) / W) ** 2)
        ez = math.sin(math.pi * min(max(p.z, 0), H) / H) ** 0.7
        p.y = 0.08 - 0.22 * ex * ez - 0.02
        pts.append(p)
    chains.append([(p, 0.05 * (1 - 0.7 * i / n) + 0.01) for i, p in enumerate(pts)])
tw = skin_tubes("wt", chains, subsurf=1)
# a body pressed through the membrane: torso + head + reaching arm
body_el = [dict(type="ELLIPSOID", co=(0.15, -0.12, 1.3), r=0.2, s=(1.0, 0.7, 1.5)),
           dict(type="BALL", co=(0.17, -0.16, 1.72), r=0.12), dict(type="CAPSULE", a=(0.32, -0.1, 1.5), b=(0.55, -0.25, 1.85), r=0.055),
           dict(type="CAPSULE", a=(-0.02, -0.1, 1.45), b=(-0.2, -0.2, 1.2), r=0.05)]
bod = metaballs("mb_wb", body_el, res=0.02)
pw = []
for (x, z, r) in [(-0.55, 0.6, 0.1), (-0.45, 0.75, 0.08), (0.6, 1.1, 0.12), (-0.3, 1.9, 0.07), (0.5, 0.45, 0.09)]:
    ex = max(0, 1 - (2 * abs(x) / W) ** 2)
    ez = math.sin(math.pi * z / H) ** 0.7
    pw.append(prim("ico", "wpod", loc=(x, 0.08 - 0.22 * ex * ez - r * 0.5, z), scale=(r, r * 0.8, r * 1.3), sub=2))
org = join([mem, tw, bod], "growth_wall")
org = remesh(org, 0.022)
smooth(org, 2)
lumps(org, s1=(5, 0.015), s2=(16, 0.005), seed=6)
c = get_co(org)
c[:, 1] = np.minimum(c[:, 1], 0.1)
c[:, 2] = np.maximum(c[:, 2], 0)
set_co(org, c)
org = decimate(org, 2600)
assign_faces(org, ["flesh", "flesh_dark"], lambda fc, fn: (fn[:, 1] > 0.4).astype(int))  # wall-facing side darker/raw
shade_smooth(org)
pw = join(pw, "wpods")
pw = decimate(pw, 380)
set_material(pw, "glow_bile")
o = join([org, pw], "growth_wall")
co_ = get_co(o)
co_[:, 0] -= (co_[:, 0].min() + co_[:, 0].max()) / 2
co_[:, 0] *= 1.0 / np.abs(co_[:, 0]).max()
co_[:, 2] -= co_[:, 2].min()
set_co(o, co_)
flesh_paint(o, seed=6, ao_dist=0.2)
growths.append(o)

# ---------------------------------------------------------------- floor tendril network
rng = random.Random(12)
chains = []
for k in range(5):
    a = 2 * math.pi * k / 5 + rng.uniform(-0.3, 0.3)
    d = Vector((math.cos(a), math.sin(a), 0))
    tendril_tree(d * 0.1, d, rng.uniform(1.0, 1.35), 0.05, 3, rng, out=chains, spread=0.8)
t = skin_tubes("tendr", chains, subsurf=0)
print("tendril raw tris", tri_count(t))
t = decimate(t, 1950)
c = get_co(t)
c[:, 2] = np.maximum(c[:, 2] - 0.012, 0)  # half-sunk, flat bottom
set_co(t, c)
# small central knot
assign_faces(t, ["flesh"], lambda fc, fn: np.zeros(len(fc), int))
shade_smooth(t)
co_ = get_co(t)
co_[:, :2] -= (co_[:, :2].min(0) + co_[:, :2].max(0)) / 2
co_[:, :2] *= 1.5 / np.abs(co_[:, :2]).max(0)
set_co(t, co_)
t.name = "growth_tendrils"
flesh_paint(t, seed=12, ao_dist=0.05)
growths.append(t)

# ---------------------------------------------------------------- hanging cocoon (origin at strand top)
# upside-down wrapped body: feet tied to the strand at z=-3, head at z=-4.8
el = [dict(type="ELLIPSOID", co=(0, 0, -3.75), r=0.18, s=(1.0, 0.8, 2.6)),     # legs bundle
      dict(type="ELLIPSOID", co=(0, 0, -4.25), r=0.22, s=(1.15, 0.85, 1.5)),    # torso
      dict(type="BALL", co=(0, -0.02, -4.66), r=0.13),                           # head
      dict(type="ELLIPSOID", co=(0, 0, -3.1), r=0.1, s=(1, 1, 1.4))]             # tied feet
for s in (1, -1):
    el.append(dict(type="CAPSULE", a=(0.2 * s, 0.02, -4.05), b=(0.17 * s, -0.04, -4.5), r=0.07))   # arms bound to sides
coc = metaballs("mb_coc", el, res=0.015)
strand = skin_tubes("strand", [[(Vector((0, 0, 0)), 0.02), (Vector((0.01, 0, -1.5)), 0.016), (Vector((0, 0.01, -2.9)), 0.022), (Vector((0, 0, -3.15)), 0.05)]], subsurf=1)
o = join([coc, strand], "cocoon_hanging")
o = remesh(o, 0.012)
smooth(o, 2)
# spiral wrapping ridges
def wrap(c, n):
    ang = np.arctan2(c[:, 1], c[:, 0])
    band = np.abs(np.sin(c[:, 2] * 22 + ang * 1.0 + nfield(c, 4, (1, 2, 3)) * 1.5))
    band2 = np.abs(np.sin(c[:, 2] * 15 - ang * 1.0 + 1.3))
    on = (c[:, 2] < -3.0).astype(float)
    return (smoothstep(0.75, 1.0, band) * 0.012 + smoothstep(0.85, 1.0, band2) * 0.01 - 0.004) * on
displace(o, wrap)
lumps(o, s1=(6, 0.01), s2=(18, 0.004), seed=7, mask=(get_co(o)[:, 2] < -3.0).astype(float))
o = decimate(o, 1950)
assign_faces(o, ["flesh", "flesh_dark"], lambda fc, fn: ((fc[:, 2] < -4.55) & (fn[:, 1] < -0.4)).astype(int))  # seeping face area
shade_smooth(o)


def coc_extra(co, vn, col):
    seep = smoothstep(0.1, 0.5, nfield(co, 5, (3, 3, 3))) * (co[:, 2] < -3.0)
    col = mix(col, np.array([0.62, 0.58, 0.48]), (co[:, 2] < -3.0) * 0.35)
    col = mix(col, np.array([0.3, 0.05, 0.06]), seep * 0.6)
    strand_ = (co[:, 2] > -3.05)
    col = np.where(strand_[:, None], np.array([0.5, 0.46, 0.4]) * (0.8 + 0.2 * nfield(co, 20, (1, 1, 1))[:, None]), col)
    return col


flesh_paint(o, seed=7, ao_dist=0.12, extra=coc_extra)
growths.append(o)

for m_ in list(bpy.data.meshes):
    if m_.users == 0:
        bpy.data.meshes.remove(m_)
for g, nm in zip(growths, ["growth_pods_a", "growth_pods_b", "growth_mound", "growth_wall", "growth_tendrils", "cocoon_hanging"]):
    g.name = nm
    g.data.name = g.name
    co_ = get_co(g)
    print("GROWTH", g.name, tri_count(g), "min", co_.min(0).round(3), "max", co_.max(0).round(3), [m.name for m in g.data.materials])
export_glb(os.path.join(OUT_DIR, "growths.glb"), growths)

if RENDER:
    lay = {"growth_pods_a": (-2.2, 1.6, 0), "growth_pods_b": (0.0, 1.6, 0), "growth_mound": (2.2, 1.6, 0),
           "growth_wall": (-2.2, -1.2, 0), "growth_tendrils": (0.4, -1.4, 0), "cocoon_hanging": (2.6, -1.0, 5.0)}
    for g in growths:
        g.location = lay[g.name]
    render_sheet(os.path.join(PREV_DIR, "growths_sheet.png"), (0, 0.2, 0.9), 3.4)
    render_game(os.path.join(PREV_DIR, "growths_game.png"), os.path.join(PREV_DIR, "growths_game_zoom.png"), target=(0, 0.2, 0.3), spot=70, zoom=2.0)
