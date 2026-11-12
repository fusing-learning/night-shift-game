"""Scuttler - crawler.glb. Run: Blender -b --python crawler.py [-- norender]"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, mlib
importlib.reload(mlib)
from mlib import *

RENDER = "norender" not in sys.argv
reset()
rnd = random.Random(7)

BODY_Z = 0.34
# leg layout: angle from forward (-Y) toward the side
LEGS = [("L1", 35, 1), ("L2", 90, 1), ("L3", 145, 1), ("R1", 35, -1), ("R2", 90, -1), ("R3", 145, -1)]
FOOT_R = 0.75


def leg_dir(ang, side):
    a = math.radians(ang)
    return Vector((side * math.sin(a), -math.cos(a), 0))


def leg_points(name, ang, side):
    d = leg_dir(ang, side)
    k = {"1": 0.0, "2": 0.03, "3": -0.02}[name[1]]
    hip = d * 0.15 + Vector((0, 0, BODY_Z + 0.02))
    knee = d * (0.47 + k * 0.5) + Vector((0, 0, 0.70 + k))
    foot = d * FOOT_R
    return d, hip, knee, foot


# ------------------------------------------------------------ body
el = []
el.append(dict(type="ELLIPSOID", co=(0, 0.02, BODY_Z - 0.01), r=0.17, s=(1.15, 1.25, 0.75)))
# split maw: swollen vertical lips with a negative slit
for s in (1, -1):
    el.append(dict(type="CAPSULE", a=(0.06 * s, -0.215, BODY_Z - 0.11), b=(0.06 * s, -0.235, BODY_Z + 0.12), r=0.065))
el.append(dict(type="CAPSULE", a=(0, -0.30, BODY_Z - 0.12), b=(0, -0.31, BODY_Z + 0.13), r=0.036, neg=True, stiff=3))
el.append(dict(type="ELLIPSOID", co=(0, -0.21, BODY_Z), r=0.07, s=(0.45, 1.6, 2.0), neg=True, stiff=3))
# saggy underside + dangling cord root
el.append(dict(type="ELLIPSOID", co=(0, 0.04, BODY_Z - 0.1), r=0.12, s=(1.1, 1.3, 0.6)))
core = metaballs("mb_body", el, res=0.012)
# fused infant crania (egg shapes, crown pointing outward/up) -> sharp creases after remesh
parts = [core]
heads = [((0.10, 0.06, BODY_Z + 0.07), 0.13, (0.5, 0.3)), ((-0.11, 0.04, BODY_Z + 0.06), 0.125, (-0.5, 0.2)),
         ((0.01, 0.16, BODY_Z + 0.06), 0.12, (0.0, 0.6)), ((0.0, -0.08, BODY_Z + 0.09), 0.12, (0.05, -0.4)),
         ((0.155, -0.10, BODY_Z + 0.0), 0.09, (0.9, -0.5)), ((-0.16, -0.09, BODY_Z + 0.01), 0.095, (-0.9, -0.4)),
         ((0.12, 0.22, BODY_Z - 0.02), 0.085, (0.6, 0.8)), ((-0.11, 0.21, BODY_Z - 0.01), 0.09, (-0.6, 0.8))]
for i, (c, r, (dx, dy)) in enumerate(heads):
    dirv = Vector((dx, dy, 1.0)).normalized()
    q = Vector((0, 0, 1)).rotation_difference(dirv)
    parts.append(prim("ico", "cran%d" % i, loc=c, rot=q, scale=(r * 0.92, r * 0.85, r * 1.12), sub=3))
# a small fused back with shoulder blades + spine at the rear
for s in (1, -1):
    parts.append(prim("ico", "blade", loc=(0.06 * s, 0.27, BODY_Z + 0.02), rot=(0.3, 0.4 * s, 0.2 * s), scale=(0.055, 0.035, 0.02), sub=2))
for i in range(6):
    t = i / 5
    parts.append(prim("ico", "vert", loc=(0.0, 0.29 - t * 0.17, BODY_Z + 0.0 + 0.06 * math.sin(t * 2.5)), scale=(0.02, 0.018, 0.016), sub=1))
# two vestigial curled infant arms on the back
vest = []
for s, base in ((1, Vector((0.17, 0.12, BODY_Z + 0.06))), (-1, Vector((-0.07, -0.02, BODY_Z + 0.16)))):
    p1 = base + Vector((0.05 * s, 0.02, 0.05))
    p2 = p1 + Vector((0.03 * s, -0.04, 0.0))
    p3 = p2 + Vector((-0.01 * s, -0.03, -0.02))
    vest.append([(base, 0.028), (p1, 0.022), (p2, 0.018), (p3, 0.016)])
parts.append(skin_tubes("vest", vest, subsurf=1))
body = join(parts, "body_parts")

# ------------------------------------------------------------ legs (skin tubes)
chains = []
elb = []
for name, ang, side in LEGS:
    d, hip, knee, foot = leg_points(name, ang, side)
    up = Vector((0, 0, 1))
    wrist = foot - d * 0.055 + up * 0.035
    sh = hip + (knee - hip) * 0.12
    kw = knee + (wrist - knee)
    chains.append([(hip, 0.065), (sh, 0.062), (hip + (knee - hip) * 0.4, 0.056), (hip + (knee - hip) * 0.75, 0.042),
                   (knee, 0.04), (knee + (wrist - knee) * 0.18, 0.047), (knee + (wrist - knee) * 0.45, 0.036),
                   (knee + (wrist - knee) * 0.8, 0.023), (wrist, 0.021), (foot + up * 0.024, 0.03)])
    # elbow knob pointing up/out
    elb.append(dict(type="BALL", co=knee + up * 0.012 + d * 0.012, r=0.034))
    # fingers fanned outward, curling to the ground
    side_v = Vector((-d.y, d.x, 0))
    for fi, (fa, fl) in enumerate([(-62, 0.075), (-25, 0.12), (-3, 0.135), (19, 0.125), (42, 0.1)]):
        q = Quaternion((0, 0, 1), math.radians(fa * side))
        fd = q @ d
        b0 = foot + up * 0.024 + fd * 0.028
        chains.append([(b0, 0.017), (b0 + fd * fl * 0.4 + up * 0.03, 0.014),
                       (b0 + fd * fl * 0.75 + up * 0.022, 0.011), (b0 + fd * fl + up * 0.006, 0.008)])
legs = skin_tubes("legs", chains, subsurf=1)
knobs = metaballs("mb_knobs", elb, res=0.01)
org = join([body, legs, knobs], "crawler_org")
org = remesh(org, 0.0065)
smooth(org, 3)

co = get_co(org)
rxy = np.linalg.norm(co[:, :2], axis=1)
bodymask = 1 - smoothstep(0.24, 0.34, rxy)
lumps(org, s1=(6.0, 0.022), s2=(22.0, 0.006), seed=3, mask=0.12 + 0.88 * bodymask)
# wrinkles gathered in the creases
cv = blur(curvature(org), org, 3)
wr = np.abs(nfield(get_co(org), 60, (2, 2, 2), octaves=2))
displace(org, lambda c, n: -(smoothstep(0.02, 0.25, cv) * (1 - smoothstep(0.0, 0.25, wr)) * 0.006))
smooth(org, 1)
org = decimate(org, 4550)
shade_smooth(org)


def mat_fn(c, n):
    mouth = (c[:, 1] < -0.17) & (np.abs(c[:, 0]) < 0.045) & (c[:, 2] > BODY_Z - 0.13) & (c[:, 2] < BODY_Z + 0.14)
    return np.where(mouth, 1, 0)


assign_faces(org, ["flesh", "flesh_dark"], mat_fn)

# ------------------------------------------------------------ needle teeth
teeth = []
for s in (1, -1):
    for i in range(9):
        z = BODY_Z - 0.09 + i * 0.022 + (0.011 if s < 0 else 0)
        L = 0.04 + 0.02 * math.sin(i / 8 * math.pi) + rnd.uniform(-0.006, 0.006)
        a = Vector((0.04 * s, -0.25 + rnd.uniform(-0.01, 0.01), z))
        b = a + Vector((-0.9 * s, -0.55, rnd.uniform(-0.25, 0.25))).normalized() * L
        teeth.append(cone_between("tooth", a, b, 0.0065, seg=4))
# top/bottom fangs
for z, dz in ((BODY_Z + 0.115, -1), (BODY_Z - 0.115, 1)):
    a = Vector((0, -0.25, z))
    teeth.append(cone_between("fang", a, a + Vector((0, -0.25, dz)).normalized() * 0.06, 0.009, seg=5))
teeth = join(teeth, "teeth")
set_material(teeth, "bone")

mesh = join([org, teeth], "crawler")
shade_smooth(mesh)

# ------------------------------------------------------------ paint
co = get_co(mesh)
nv = len(co)
me = mesh.data
vmat = np.zeros(nv, int)
for p in me.polygons:
    for v in p.vertices:
        vmat[v] = max(vmat[v], p.material_index)
names = [m.name for m in me.materials]
is_bone = vmat == names.index("bone")
is_dark = vmat == names.index("flesh_dark")

occ = blur(ao(mesh, rays=24, dist=0.12), mesh, 1)
curv = blur(curvature(mesh), mesh, 2)
n1 = nfield(co, 7, (1, 2, 3), octaves=3)
n2 = nfield(co, 18, (5, 1, 2))
vein = 1 - smoothstep(0.0, 0.07, np.abs(nfield(co, 9, (9, 9, 1), octaves=2)))
vein2 = 1 - smoothstep(0.0, 0.05, np.abs(nfield(co, 22, (3, 7, 1))))
suture = 1 - smoothstep(0.0, 0.05, cellular(co, 9, 4))

pale = np.array([0.5, 0.38, 0.36])
bonew = np.array([0.64, 0.58, 0.5])
bruise = np.array([0.2, 0.12, 0.24])
red = np.array([0.55, 0.22, 0.24])
col = mix(pale, bonew, smoothstep(0.1, 0.6, n1))
col = mix(col, bruise, smoothstep(0.05, 0.6, -n1) * 0.85)
col = mix(col, red * 1.1, smoothstep(0.3, 0.8, n2) * 0.25)
# body: crania tops paler, sutures
rxy = np.linalg.norm(co[:, :2], axis=1)
onbody = 1 - smoothstep(0.26, 0.36, rxy)
top = smoothstep(BODY_Z, BODY_Z + 0.15, co[:, 2]) * onbody
col = mix(col, bonew * 1.05, top * 0.2)
tints = [(0.62, 0.46, 0.43), (0.47, 0.42, 0.5), (0.62, 0.56, 0.43), (0.42, 0.28, 0.34), (0.58, 0.4, 0.4),
         (0.5, 0.47, 0.47), (0.36, 0.3, 0.4), (0.6, 0.5, 0.44)]
for (c, r, _), t in zip(heads, tints):
    dc = np.linalg.norm(co - np.array(c), axis=1)
    col = mix(col, np.array(t), (1 - smoothstep(r * 0.6, r * 1.15, dc)) * 0.65)
blot = smoothstep(0.1, 0.5, nfield(co, 4, (7, 3, 1), octaves=2))
col = mix(col, np.array([0.26, 0.1, 0.15]), blot * 0.55)
col = mix(col, np.array([0.2, 0.05, 0.08]), suture * top * 0.8)
# veins (blue-purple) mostly on legs + body sides
col = mix(col, np.array([0.14, 0.1, 0.28]), np.clip(vein * 0.6 + vein2 * 0.35, 0, 1) * (0.5 + 0.5 * (1 - top)))
# joints: elbows bruised red
for name, ang, side in LEGS:
    d, hip, knee, foot = leg_points(name, ang, side)
    de = np.linalg.norm(co - np.array(knee), axis=1)
    col = mix(col, np.array([0.42, 0.1, 0.16]), (1 - smoothstep(0.02, 0.1, de)) * 0.7)
    dh = np.linalg.norm(co - np.array(foot), axis=1)
    col = mix(col, np.array([0.16, 0.11, 0.1]), (1 - smoothstep(0.04, 0.16, dh)) * 0.65)
# grime toward the ground
col = mix(col, np.array([0.2, 0.16, 0.15]), (1 - smoothstep(0.0, 0.14, co[:, 2])) * 0.6)
# crevices: AO + concavity
cav = np.clip(smoothstep(0.08, 0.45, occ) + np.clip(curv, 0, None) * 0.6, 0, 1)
col = mix(col, np.array([0.09, 0.015, 0.03]), cav * 0.92)
col *= (1 - 0.35 * occ)[:, None]
# convex highlights a touch paler
col = mix(col, bonew, np.clip(-curv, 0, 1) * 0.25)
# mouth interior + teeth
dm = np.array([0.32, 0.04, 0.06]) * (1 - 0.6 * occ[:, None]) + 0.05 * n2[:, None]
col = np.where(is_dark[:, None], dm, col)
tooth = mix(np.array([0.82, 0.76, 0.58]), np.array([0.42, 0.12, 0.12]), smoothstep(0.035, 0.0, np.abs(co[:, 0])) * 0)
tip = smoothstep(-0.255, -0.29, co[:, 1])
tooth = mix(np.array([0.45, 0.2, 0.17]), np.array([0.85, 0.8, 0.64]), 0.35 + 0.65 * tip)
col = np.where(is_bone[:, None], tooth, col)
set_colors(mesh, col)

# ------------------------------------------------------------ rig
bones = [dict(name="root", head=(0, 0, 0), tail=(0, 0, 0.15), deform=False),
         dict(name="body", head=(0, 0.12, BODY_Z), tail=(0, -0.2, BODY_Z), parent="root"),
         dict(name="body_end", head=(0, -0.2, BODY_Z), tail=(0, -0.26, BODY_Z), parent="body", connect=True, deform=False)]
segs = {"body": ((0, 0.12, BODY_Z), (0, -0.12, BODY_Z))}
scale = {"body": 0.2}
for name, ang, side in LEGS:
    d, hip, knee, foot = leg_points(name, ang, side)
    a, b, e = "leg_%s_a" % name, "leg_%s_b" % name, "leg_%s_end" % name
    bones += [dict(name=a, head=hip, tail=knee, parent="body"),
              dict(name=b, head=knee, tail=foot, parent=a, connect=True),
              dict(name=e, head=foot, tail=foot + d * 0.06, parent=b, connect=True, deform=False)]
    segs[a] = (tuple(hip + (knee - hip) * 0.15), tuple(knee))
    segs[b] = (tuple(knee), tuple(foot))
    scale[a] = 0.06
    scale[b] = 0.05
arm = armature("crawler_rig", bones)
cands = list(segs.keys())
rigid = [("body" if b else None) for b in is_bone]
weights(mesh, segs, scale, cands, rigid=rigid, power=4, smooth_iters=3)
bind(mesh, arm)
report(mesh, arm)

export_glb(os.path.join(OUT_DIR, "crawler.glb"), [arm, mesh])

if RENDER:
    P = PREV_DIR
    render_sheet(os.path.join(P, "crawler_sheet.png"), (0, 0, 0.3), 0.8)
    render_game(os.path.join(P, "crawler_game.png"), os.path.join(P, "crawler_game_zoom.png"), target=(0, 0, 0.3))
    # deformation test
    pb = arm.pose.bones
    pb["body"].rotation_mode = "XYZ"
    pb["body"].rotation_euler = (0.25, 0.0, 0.3)
    for name, ang, side in LEGS:
        for suf, r in (("a", (0.5, 0, 0.4)), ("b", (-0.9, 0, 0))):
            p = pb["leg_%s_%s" % (name, suf)]
            p.rotation_mode = "XYZ"
            p.rotation_euler = r if name[1] != "2" else (-r[0], 0, -r[2])
    bpy.context.view_layer.update()
    render_sheet(os.path.join(P, "crawler_pose.png"), (0, 0, 0.3), 0.8, views=("front", "top"))
