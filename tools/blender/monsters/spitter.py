"""Bellows - spitter.glb. Run: Blender -b --python spitter.py [-- norender]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, mlib
importlib.reload(mlib)
from mlib import *

RENDER = "norender" not in sys.argv
reset()
rnd = random.Random(11)

SAC_C = Vector((0, 0.12, 0.9))
SAC_R = 0.35
NECK = [Vector(p) for p in [(0, -0.52, 0.6), (0, -0.78, 0.86), (0, -1.02, 1.04), (0, -1.28, 1.11), (0, -1.5, 1.05)]]
AX = Vector((0, -1, 0.18)).normalized()
MOUTH = NECK[-1] + AX * 0.24
# legs: hip, knee, foot
LEGS = {}
for key, sx, sy in (("FL", 1, -1), ("FR", -1, -1), ("BL", 1, 1), ("BR", -1, 1)):
    fy = -0.42 if sy < 0 else 0.42
    hip = Vector((0.32 * sx, fy, 0.42))
    knee = Vector((0.66 * sx, fy * 1.3, 0.74))
    foot = Vector((0.84 * sx, fy * 1.45, 0.0))
    LEGS[key] = (hip, knee, foot)


def bez(pts, n):
    """Catmull-Rom through pts"""
    out = []
    P = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    for i in range(1, len(P) - 2):
        for k in range(n):
            t = k / n
            p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return out


# ------------------------------------------------------------ body volumes
el = []
el.append(dict(type="ELLIPSOID", co=(0, 0.05, 0.5), r=0.4, s=(1.2, 1.65, 0.8)))
el.append(dict(type="ELLIPSOID", co=(0, 0.12, 0.26), r=0.38, s=(1.15, 1.5, 0.55)))  # saggy belly
el.append(dict(type="ELLIPSOID", co=(0, 0.15, 0.14), r=0.25, s=(1.2, 1.6, 0.5)))  # belly bag nearly dragging
el.append(dict(type="ELLIPSOID", co=(0, 0.38, 0.25), r=0.25, s=(1.3, 1.0, 0.8)))   # rear droop
el.append(dict(type="ELLIPSOID", co=(0, -0.42, 0.52), r=0.26, s=(1.1, 1.0, 1.0)))   # chest under neck
# fat rolls on the flanks
for s in (1, -1):
    for i, (y, z) in enumerate([(-0.3, 0.38), (0.0, 0.33), (0.3, 0.36)]):
        el.append(dict(type="CAPSULE", a=(0.47 * s, y - 0.18, z), b=(0.47 * s, y + 0.18, z - 0.02), r=0.1))
    el.append(dict(type="CAPSULE", a=(0.36 * s, -0.25, 0.16), b=(0.36 * s, 0.45, 0.16), r=0.09))
# raised cradle lip around the sac
for i in range(14):
    a = 2 * math.pi * i / 14
    el.append(dict(type="BALL", co=(SAC_C.x + math.cos(a) * 0.33, SAC_C.y + math.sin(a) * 0.36, 0.72 + 0.03 * math.sin(a * 3)), r=0.085))
body = metaballs("mb_body", el, res=0.02)
parts = [body]
# hanging skin flaps at rear and under chin
for s in (1, -1):
    parts.append(prim("ico", "flap", loc=(0.22 * s, 0.68, 0.24), rot=(0.4, 0.3 * s, 0), scale=(0.16, 0.05, 0.16), sub=2))
parts.append(prim("ico", "wattle", loc=(0, -0.58, 0.36), rot=(0.3, 0, 0), scale=(0.15, 0.06, 0.13), sub=2))

# ------------------------------------------------------------ neck (ribbed windpipe)
npts = bez(NECK, 8)
ch = []
for i, p in enumerate(npts):
    t = i / (len(npts) - 1)
    ch.append((p, 0.13 - 0.05 * t))
ch.append((MOUTH - AX * 0.12, 0.09))
neck = skin_tubes("neck", [ch], subsurf=1)
parts.append(neck)
rings = []
for i in range(2, len(npts) - 1, 1):
    p = npts[i]
    d = (npts[i + 1] - npts[i - 1]).normalized()
    t = i / (len(npts) - 1)
    r = 0.13 - 0.05 * t
    q = Vector((0, 0, 1)).rotation_difference(d)
    if i % 2 == 0:
        rings.append(prim("torus", "ring", loc=p, rot=q, R=r + 0.012, r=0.024, seg=16, seg2=6))
parts += rings

# ------------------------------------------------------------ lamprey head (lathe)
def lathe(name, prof, center, axis, seg=28):
    q = Vector((0, 0, 1)).rotation_difference(axis)
    bm = bmesh.new()
    rows = []
    for k in range(seg):
        a = 2 * math.pi * k / seg
        row = []
        for (r, h) in prof:
            v = Vector((r * math.cos(a), r * math.sin(a), h))
            row.append(bm.verts.new(center + q @ v))
        rows.append(row)
    n = len(prof)
    for k in range(seg):
        r0, r1 = rows[k], rows[(k + 1) % seg]
        for j in range(n - 1):
            bm.faces.new((r0[j], r1[j], r1[j + 1], r0[j + 1]))
        bm.faces.new((r0[n - 1], r1[n - 1], r1[0], r0[0]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


prof = [(0.04, -0.2), (0.11, -0.06), (0.17, 0.0), (0.205, 0.02), (0.225, -0.01), (0.215, -0.07),
        (0.17, -0.16), (0.12, -0.26), (0.08, -0.3)]
head = lathe("funnel", prof, MOUTH, AX)
parts.append(head)

# stubby crab legs
lch = []
for key, (hip, knee, foot) in LEGS.items():
    up = Vector((0, 0, 1))
    ank = foot + up * 0.09
    lch.append([(hip, 0.13), (hip + (knee - hip) * 0.5, 0.105), (knee, 0.07), (knee + (ank - knee) * 0.25, 0.08),
                (knee + (ank - knee) * 0.6, 0.06), (ank, 0.04)])
parts.append(skin_tubes("legs", lch, subsurf=1))
kn = [dict(type="BALL", co=knee + Vector((0, 0, 0.02)), r=0.075) for (hip, knee, foot) in LEGS.values()]
parts.append(metaballs("mb_knees", kn, res=0.02))

org = join(parts, "spitter_org")
org = remesh(org, 0.014)
smooth(org, 3)
co = get_co(org)
# fat rolls / folds: horizontal sine creases on body, finer lumps
lumps(org, s1=(3.0, 0.03), s2=(11.0, 0.01), seed=5)
cv = blur(curvature(org), org, 3)
wr = np.abs(nfield(get_co(org), 28, (4, 1, 2), octaves=2))
displace(org, lambda c, n: -(smoothstep(0.02, 0.3, cv) * (1 - smoothstep(0.0, 0.3, wr)) * 0.012))
# loose horizontal skin folds on the flanks / belly
def folds(c, n):
    fl = smoothstep(0.15, 0.45, np.abs(c[:, 0])) * (1 - smoothstep(0.62, 0.8, c[:, 2])) * (1 - smoothstep(0.55, 0.8, np.abs(c[:, 1] + 0.05)))
    fl *= smoothstep(-1.0, -0.5, -np.abs(c[:, 1] + 0.3) * 0) if False else 1
    w = np.abs(np.sin(c[:, 2] * 26 + nfield(c, 3, (1, 5, 2)) * 2.5 + c[:, 1] * 3))
    return -(1 - smoothstep(0.0, 0.45, w)) * 0.022 * fl * (np.abs(c[:, 2] - 0.4) < 0.4)
bodyonly = (np.linalg.norm(get_co(org)[:, :2] - np.array([0, 0.05]), axis=1) < 0.65).astype(float)
displace(org, lambda c, n: folds(c, n) * bodyonly)
smooth(org, 1)
_c = get_co(org)
_c[:, 2] = np.maximum(_c[:, 2], 0.0)
set_co(org, _c)
org = decimate(org, 6300)
shade_smooth(org)

Qm = AX.rotation_difference(Vector((0, 0, 1)))


def mouth_local(c):
    rel = c - np.array(MOUTH)
    M = np.array(Qm.to_matrix())
    loc = rel @ M.T
    return np.linalg.norm(loc[:, :2], axis=1), loc[:, 2]


def mat_fn(c, n):
    r, h = mouth_local(c)
    inner = (h > -0.24) & (h < 0.012) & (r < 0.05 + (h + 0.2) / 0.2 * 0.125 + 0.015)
    return np.where(inner, 1, 0)


assign_faces(org, ["flesh", "flesh_dark"], mat_fn)

# ------------------------------------------------------------ teeth / claws
q = Vector((0, 0, 1)).rotation_difference(AX)
teeth = []
for (h, r, cnt, L) in [(-0.005, 0.16, 18, 0.05), (-0.055, 0.125, 14, 0.045), (-0.11, 0.09, 11, 0.04), (-0.16, 0.06, 8, 0.03)]:
    for k in range(cnt):
        a = 2 * math.pi * (k + 0.5 * (cnt % 2)) / cnt + h * 7
        radial = Vector((math.cos(a), math.sin(a), 0))
        base = MOUTH + q @ (radial * r + Vector((0, 0, h)))
        tipd = q @ (-radial * 0.85 + Vector((0, 0, 0.45)))
        teeth.append(cone_between("t", base, base + tipd.normalized() * L * rnd.uniform(0.8, 1.2), 0.009, seg=4))
claws = []
for key, (hip, knee, foot) in LEGS.items():
    out = Vector((foot.x - knee.x, foot.y - knee.y, 0)).normalized()
    side = Vector((-out.y, out.x, 0))
    for o in (-1, 0, 1):
        b = foot + Vector((0, 0, 0.06)) + side * o * 0.045
        claws.append(cone_between("c", b, b + (out * 0.9 + side * o * 0.35 + Vector((0, 0, -0.45))).normalized() * 0.11, 0.024, seg=5))
for key, (hip, knee, foot) in LEGS.items():
    b = knee + Vector((0, 0, 0.04))
    out = Vector((knee.x, knee.y, 0)).normalized()
    claws.append(cone_between("spur", b, b + (out * 0.4 + Vector((0, 0, 1))).normalized() * 0.12, 0.03, seg=5))
bonep = join(teeth + claws, "bones")
set_material(bonep, "bone")

# ------------------------------------------------------------ bile sac
sac = prim("ico", "sac", loc=SAC_C, scale=(SAC_R, SAC_R * 1.08, SAC_R * 0.92), sub=4)
sco = get_co(sac)
rel = sco - np.array(SAC_C)
vn = rel / np.linalg.norm(rel, axis=1, keepdims=True)
bump = nfield(sco, 6, (3, 3, 3)) * 0.02 + (1 - smoothstep(0, 0.08, np.abs(nfield(sco, 5, (8, 1, 1), octaves=2)))) * 0.012
set_co(sac, sco + vn * bump[:, None])
sac = decimate(sac, 1400)
shade_smooth(sac)
set_material(sac, "glow_bile")
# small bile blisters on the back
blis = []
for i in range(7):
    a = rnd.uniform(0, 2 * math.pi)
    p = Vector((math.cos(a) * rnd.uniform(0.42, 0.52), 0.05 + math.sin(a) * rnd.uniform(0.5, 0.62), 0))
    p.z = 0.62 - (p.length - 0.45) * 0.4
    r = rnd.uniform(0.04, 0.07)
    blis.append(prim("ico", "bl", loc=p, scale=(r, r, r * 0.8), sub=2))
blis = join(blis, "blisters")
set_material(blis, "glow_bile")

# ------------------------------------------------------------ hoses + clamps
hoses = []
for (a, mid, b, r) in [((0.18, 0.2, 0.12), (0.25, 0.35, 0.05), (0.3, 0.7, 0.02), 0.022),
                       ((-0.15, 0.0, 0.1), (-0.3, 0.1, 0.03), (-0.35, 0.55, 0.02), 0.02),
                       ((0.05, 0.55, 0.22), (0.1, 0.85, 0.1), (0.05, 1.05, 0.02), 0.026),
                       ((-0.38, -0.2, 0.45), (-0.55, -0.15, 0.25), (-0.5, 0.1, 0.06), 0.018),
                       ((0.28, -0.2, 0.72), (0.5, -0.05, 0.85), (0.5, 0.25, 0.6), 0.024),
                       ((-0.25, 0.42, 0.74), (-0.45, 0.55, 0.8), (-0.55, 0.45, 0.45), 0.022),
                       ((-0.3, -0.15, 0.72), (-0.58, -0.2, 0.62), (-0.7, -0.1, 0.2), 0.02)]:
    pts = bez([Vector(a), Vector(mid), Vector(b)], 5)
    hoses.append(skin_tubes("hose", [[(p, r) for p in pts]], subsurf=1))
hoses = join(hoses, "hoses")
hoses = decimate(hoses, 500)
set_material(hoses, "rubber")
clamps = []
p0, p1 = npts[1], npts[2]
d = (p1 - p0).normalized()
clamps.append(prim("torus", "clamp", loc=p0 + d * 0.02, rot=Vector((0, 0, 1)).rotation_difference(d), R=0.135, r=0.022, seg=14, seg2=4, smooth=False))
clamps.append(prim("cube", "bolt", loc=p0 + d * 0.02 + Vector((0.15, 0, 0)), rot=Vector((0, 0, 1)).rotation_difference(d), scale=(0.05, 0.04, 0.03), smooth=False))
for key in ("FL", "BR"):
    hip, knee, foot = LEGS[key]
    d = (knee - hip).normalized()
    clamps.append(prim("torus", "lc", loc=hip + (knee - hip) * 0.65, rot=Vector((0, 0, 1)).rotation_difference(d), R=0.085, r=0.016, seg=12, seg2=4, smooth=False))
SEAM = bez([Vector((0.0, -0.48, 0.74)), Vector((0.04, -0.35, 0.79)), Vector((-0.02, -0.25, 0.79))], 4)
_bv = BVHTree.FromPolygons([v.co.copy() for v in org.data.vertices], [tuple(pp.vertices) for pp in org.data.polygons])
for i in range(len(SEAM)):
    hit = _bv.ray_cast(SEAM[i] + Vector((0, 0, 0.5)), Vector((0, 0, -1)), 2.0)
    if hit[0] is not None:
        SEAM[i] = hit[0]
for i, p in enumerate(SEAM[1:]):
    d = (SEAM[min(i + 2, len(SEAM) - 1)] - SEAM[i]).normalized()
    perp = Vector((-d.y, d.x, 0)).normalized()
    clamps.append(prim("cube", "staple", loc=p + Vector((0, 0, 0.004)), rot=Vector((1, 0, 0)).rotation_difference(perp), scale=(0.07, 0.012, 0.012), smooth=False))
clamps = join(clamps, "clamps")
set_material(clamps, "metal")

mesh = join([org, bonep, sac, blis, hoses, clamps], "spitter")


# ------------------------------------------------------------ paint
co = get_co(mesh)
nv = len(co)
me = mesh.data
names = [m.name for m in me.materials]
pm = np.zeros(len(me.polygons), int)
me.polygons.foreach_get("material_index", pm)
vmat = np.zeros(nv, int)
for p in me.polygons:
    for v in p.vertices:
        vmat[v] = p.material_index
vname = np.array(names)[vmat]

occ = blur(ao(mesh, rays=20, dist=0.3), mesh, 1)
curv = blur(curvature(mesh), mesh, 2)
n1 = nfield(co, 3, (1, 2, 3), octaves=3)
n2 = nfield(co, 9, (5, 1, 2), octaves=2)
vein = 1 - smoothstep(0.0, 0.06, np.abs(nfield(co, 4.5, (9, 9, 1), octaves=2)))
vein2 = 1 - smoothstep(0.0, 0.05, np.abs(nfield(co, 11, (3, 7, 1))))
# stretch marks: thin streaks along the vertical direction on the flanks
sm = 1 - smoothstep(0.0, 0.12, np.abs(np.sin(co[:, 1] * 70 + nfield(co, 6, (2, 2, 2)) * 3)))
sm *= smoothstep(0.1, 0.5, np.abs(co[:, 0])) * smoothstep(0.1, 0.3, co[:, 2]) * (1 - smoothstep(0.55, 0.7, co[:, 2]))
sm *= smoothstep(0.0, 0.4, nfield(co, 2.5, (6, 1, 1)) + 0.2)

pale = np.array([0.56, 0.41, 0.34])
greyp = np.array([0.46, 0.4, 0.35])
bruise = np.array([0.26, 0.11, 0.16])
col = mix(pale, greyp, smoothstep(-0.3, 0.4, n1))
col = mix(col, bruise, smoothstep(0.05, 0.6, -n1) * 0.7)
col = mix(col, np.array([0.45, 0.17, 0.18]), smoothstep(0.25, 0.7, n2) * 0.35)
# belly darker, mottled purple
belly = 1 - smoothstep(0.15, 0.4, co[:, 2])
col = mix(col, np.array([0.3, 0.15, 0.18]), belly * 0.55)
blot = smoothstep(0.15, 0.55, nfield(co, 2.2, (7, 3, 1), octaves=2))
col = mix(col, np.array([0.3, 0.1, 0.12]), blot * 0.5)
col = mix(col, np.array([0.62, 0.56, 0.42]), smoothstep(0.2, 0.6, nfield(co, 1.7, (2, 9, 4), octaves=2)) * 0.4)
col = mix(col, np.array([0.68, 0.6, 0.55]), sm * 0.55)
col = mix(col, np.array([0.16, 0.1, 0.2]), np.clip(vein * 0.6 + vein2 * 0.3, 0, 1) * 0.7)
# neck rings paler cartilage
nd = np.full(nv, 9.0)
for i in range(len(npts) - 1):
    a, b = np.array(npts[i]), np.array(npts[i + 1])
    ab = b - a
    t = np.clip(((co - a) @ ab) / (ab @ ab), 0, 1)
    nd = np.minimum(nd, np.linalg.norm(co - (a + t[:, None] * ab), axis=1))
onneck = 1 - smoothstep(0.12, 0.2, nd)
col = mix(col, np.array([0.62, 0.55, 0.47]), onneck * smoothstep(-0.2, 0.6, -curv) * 0.6)
# raw red around neck root and around sac cradle
dr = np.linalg.norm(co - np.array(NECK[0] + Vector((0, -0.08, 0.05))), axis=1)
col = mix(col, np.array([0.38, 0.06, 0.08]), (1 - smoothstep(0.12, 0.3, dr)) * 0.6)
ds = np.linalg.norm((co - np.array(SAC_C)) / np.array([1, 1, 1.2]), axis=1)
col = mix(col, np.array([0.4, 0.1, 0.1]), (1 - smoothstep(SAC_R + 0.02, SAC_R + 0.16, ds)) * 0.55)
col = mix(col, np.array([0.17, 0.13, 0.12]), (1 - smoothstep(0.0, 0.2, co[:, 2])) * 0.6)
cav = np.clip(smoothstep(0.08, 0.45, occ) + np.clip(curv, 0, None) * 0.5, 0, 1)
col = mix(col, np.array([0.09, 0.015, 0.03]), cav * 0.85)
col *= (1 - 0.3 * occ)[:, None]

sd = np.full(nv, 9.0)
for i in range(len(SEAM) - 1):
    a, b = np.array(SEAM[i]), np.array(SEAM[i + 1])
    ab = b - a
    t = np.clip(((co - a) @ ab) / (ab @ ab), 0, 1)
    sd = np.minimum(sd, np.linalg.norm(co - (a + t[:, None] * ab), axis=1))
col = mix(col, np.array([0.2, 0.03, 0.05]), (1 - smoothstep(0.01, 0.05, sd)) * 0.9)
# per-material overrides
r, h = mouth_local(co)
dark = np.array([0.3, 0.03, 0.05]) * (1 - 0.6 * occ[:, None]) + 0.06 * n2[:, None]
col = np.where((vname == "flesh_dark")[:, None], dark, col)
bonec = mix(np.array([0.4, 0.22, 0.16]), np.array([0.82, 0.76, 0.6]), smoothstep(-0.3, 0.5, n2) * 0.5 + 0.4)
col = np.where((vname == "bone")[:, None], bonec, col)
# sac: yellow-green with dark veins
sv = 1 - smoothstep(0.0, 0.07, np.abs(nfield(co, 6, (8, 1, 1), octaves=2)))
sv2 = 1 - smoothstep(0.0, 0.05, np.abs(nfield(co, 13, (1, 8, 4))))
sacc = mix(np.array([0.62, 0.72, 0.2]), np.array([0.8, 0.78, 0.32]), smoothstep(-0.4, 0.4, n1))
sacc = mix(sacc, np.array([0.12, 0.1, 0.03]), np.clip(sv * 0.9 + sv2 * 0.6, 0, 1))
sv3 = 1 - smoothstep(0.0, 0.04, np.abs(nfield(co, 24, (5, 2, 9))))
sacc = mix(sacc, np.array([0.45, 0.1, 0.05]), sv3 * 0.6)
sacc = mix(sacc, np.array([0.3, 0.12, 0.06]), (1 - smoothstep(0.55, 0.75, co[:, 2])) * 0.7)
col = np.where((vname == "glow_bile")[:, None], sacc, col)
rub = np.array([0.13, 0.12, 0.12]) * (1 + 0.3 * n2[:, None]) * (1 - 0.4 * occ[:, None])
col = np.where((vname == "rubber")[:, None], rub, col)
rust = mix(np.array([0.32, 0.3, 0.28]), np.array([0.4, 0.17, 0.06]), smoothstep(-0.3, 0.3, nfield(co, 25, (1, 1, 1), octaves=2)))
col = np.where((vname == "metal")[:, None], rust * (1 - 0.4 * occ[:, None]), col)
set_colors(mesh, col)

# ------------------------------------------------------------ rig
bones = [dict(name="root", head=(0, 0, 0), tail=(0, 0, 0.2), deform=False),
         dict(name="body", head=(0, 0.45, 0.48), tail=(0, -0.4, 0.5), parent="root"),
         dict(name="sac", head=SAC_C, tail=SAC_C + Vector((0, 0, SAC_R)), parent="body"),
         dict(name="sac_end", head=SAC_C + Vector((0, 0, SAC_R)), tail=SAC_C + Vector((0, 0, SAC_R + 0.08)), parent="sac", connect=True, deform=False)]
segs = {"body": ((0, 0.45, 0.45), (0, -0.4, 0.5))}
scale = {"body": 0.38}
prev = "body"
for i in range(4):
    nm = "neck_%d" % (i + 1)
    bones.append(dict(name=nm, head=NECK[i], tail=NECK[i + 1], parent=prev, connect=i > 0))
    segs[nm] = (tuple(NECK[i]), tuple(NECK[i + 1]))
    scale[nm] = 0.1
    prev = nm
bones.append(dict(name="head", head=NECK[4], tail=MOUTH, parent="neck_4", connect=True))
bones.append(dict(name="head_end", head=MOUTH, tail=MOUTH + AX * 0.1, parent="head", connect=True, deform=False))
segs["head"] = (tuple(NECK[4]), tuple(MOUTH))
scale["head"] = 0.14
for key, (hip, knee, foot) in LEGS.items():
    a, b, e = "leg_%s_a" % key, "leg_%s_b" % key, "leg_%s_end" % key
    out = Vector((foot.x, foot.y, 0)).normalized()
    bones += [dict(name=a, head=hip, tail=knee, parent="body"),
              dict(name=b, head=knee, tail=foot, parent=a, connect=True),
              dict(name=e, head=foot, tail=foot + out * 0.08, parent=b, connect=True, deform=False)]
    segs[a] = (tuple(hip + (knee - hip) * 0.3), tuple(knee))
    segs[b] = (tuple(knee), tuple(foot))
    scale[a] = 0.11
    scale[b] = 0.09
arm = armature("spitter_rig", bones)
cands = list(segs.keys()) + ["sac"]
segs["sac"] = (tuple(SAC_C), tuple(SAC_C))
scale["sac"] = 0.01
rigid = []
for i in range(nv):
    vn_ = vname[i]
    if vn_ == "glow_bile" and np.linalg.norm(co[i] - np.array(SAC_C)) < SAC_R * 1.3:
        rigid.append("sac")
    elif vn_ == "glow_bile" or vn_ == "rubber":
        rigid.append("body")
    elif vn_ == "bone":
        rigid.append("head" if co[i, 1] < -1.3 else None)
    else:
        rigid.append(None)


def region(c):
    m = np.ones((len(c), len(cands)))
    m[:, cands.index("sac")] = 0  # sac only via rigid
    return m


weights(mesh, segs, scale, cands, rigid=rigid, power=4, smooth_iters=3, region=region)
bind(mesh, arm)
report(mesh, arm)
export_glb(os.path.join(OUT_DIR, "spitter.glb"), [arm, mesh])

if RENDER:
    P = PREV_DIR
    render_sheet(os.path.join(P, "spitter_sheet.png"), (0, -0.3, 0.6), 1.2)
    render_game(os.path.join(P, "spitter_game.png"), os.path.join(P, "spitter_game_zoom.png"), target=(0, -0.3, 0.5))
    pb = arm.pose.bones
    for nm, r in (("neck_1", (-0.3, 0, 0.25)), ("neck_2", (-0.35, 0, 0.3)), ("neck_3", (0.3, 0, 0.3)), ("neck_4", (0.4, 0, 0.2)),
                  ("head", (0.3, 0.3, 0)), ("leg_FL_a", (0.4, 0, 0)), ("leg_FL_b", (-0.6, 0, 0)), ("leg_BR_a", (-0.4, 0, 0.3)),
                  ("leg_BR_b", (0.7, 0, 0))):
        pb[nm].rotation_mode = "XYZ"
        pb[nm].rotation_euler = r
    pb["sac"].scale = (1.35, 1.35, 1.35)
    bpy.context.view_layer.update()
    render_sheet(os.path.join(P, "spitter_pose.png"), (0, -0.3, 0.6), 1.2, views=("front", "side"))
