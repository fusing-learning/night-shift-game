"""The Kid — player character. 1.00 m tall, faces -Y.
Run: /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/blender/humanoids/player.py [-- norender]
"""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, hlib
importlib.reload(hlib)
from hlib import *

NORENDER = 'norender' in sys.argv
reset()

# ------------------------------------------------------------------ skeleton
def arm_pts(s):
    S = V((0.125 * s, 0.0, 0.615))
    E = V((0.200 * s, 0.022, 0.487))
    W = V((0.268 * s, -0.006, 0.366))
    H = V((0.300 * s, -0.016, 0.300))
    End = H + (H - W).normalized() * 0.02
    return S, E, W, H, End


def leg_pts(s):
    Hp = V((0.072 * s, 0.0, 0.395))
    K = V((0.080 * s, -0.022, 0.235))
    A = V((0.085 * s, 0.0, 0.088))
    T = V((0.085 * s, -0.095, 0.030))
    End = V((0.085 * s, -0.135, 0.030))
    return Hp, K, A, T, End


bones = [
    ('root', (0, 0, 0), (0, 0, 0.08), None, False, False),
    ('hips', (0, 0, 0.40), (0, 0, 0.49), 'root', False, True),
    ('spine', (0, 0, 0.49), (0, 0, 0.57), 'hips', True, True),
    ('chest', (0, 0, 0.57), (0, 0, 0.66), 'spine', True, True),
    ('head', (0, 0, 0.66), (0, 0, 0.95), 'chest', True, True),
    ('head_end', (0, 0, 0.95), (0, 0, 1.0), 'head', True, False),
]
for side, s in (('L', 1), ('R', -1)):
    S, E, W, H, End = arm_pts(s)
    bones += [
        ('arm_%s_upper' % side, S, E, 'chest', False, True),
        ('arm_%s_lower' % side, E, W, 'arm_%s_upper' % side, True, True),
        ('arm_%s_hand' % side, W, H, 'arm_%s_lower' % side, True, True),
        ('arm_%s_end' % side, H, End, 'arm_%s_hand' % side, True, False),
    ]
    Hp, K, A, T, En = leg_pts(s)
    bones += [
        ('leg_%s_upper' % side, Hp, K, 'hips', False, True),
        ('leg_%s_lower' % side, K, A, 'leg_%s_upper' % side, True, True),
        ('leg_%s_foot' % side, A, T, 'leg_%s_lower' % side, True, True),
        ('leg_%s_end' % side, T, En, 'leg_%s_foot' % side, True, False),
    ]
arm_ob = build_armature('Kid_Rig', bones)

parts = []

# ------------------------------------------------------------------ suit (cloth)
el = [
    ('ell', (0, 0.008, 0.525), (0.122, 0.098, 0.135)),          # baggy torso
    ('ell', (0, -0.018, 0.47), (0.11, 0.09, 0.07)),             # belly sag
    ('ell', (0, 0.0, 0.405), (0.118, 0.092, 0.07)),             # seat / hips
    ('ball', (0, 0.0, 0.64), 0.07),                             # neck / collar
]
for side, s in (('L', 1), ('R', -1)):
    S, E, W, H, End = arm_pts(s)
    el += [('ball', S + V((-0.012 * s, 0, 0.0)), 0.058),       # shoulder
           ('cap', S, E, 0.047), ('cap', E, W, 0.043),
           ('ball', E, 0.05)]
    # bunched, rolled-up sleeve near the wrist (too long, pushed up)
    for k, (t, r) in enumerate(((0.45, 0.052), (0.62, 0.057), (0.78, 0.056), (0.93, 0.05))):
        c = E.lerp(W, t) + V((0.004 * s * (-1) ** k, 0.004 * (-1) ** k, 0))
        el.append(('ball', c, r))
    # rolled cuff ring
    ax = (W - E).normalized()
    perp1 = ax.cross(V((0, 1, 0))).normalized(); perp2 = ax.cross(perp1)
    for k in range(7):
        a = 2 * math.pi * k / 7
        el.append(('ball', W - ax * 0.005 + (perp1 * math.cos(a) + perp2 * math.sin(a)) * 0.04, 0.024))
    Hp, K, A, T, En = leg_pts(s)
    el += [('cap', Hp + V((0, 0, 0.01)), K, 0.058), ('cap', K, A + V((0, 0, 0.07)), 0.05), ('ball', K + V((0, -0.008, 0)), 0.058)]
    # bunched trouser leg piling onto the boot
    for k, (t, r) in enumerate(((0.4, 0.054), (0.58, 0.058), (0.72, 0.06))):
        c = K.lerp(A, t) + V((0.004 * (-1) ** k * s, 0.003 * (-1) ** k, 0))
        el.append(('ball', c, r))
    lax = (A - K).normalized()
    p1 = lax.cross(V((1, 0, 0))).normalized(); p2 = lax.cross(p1)
    for k in range(8):
        a = 2 * math.pi * k / 8 + 0.3
        el.append(('ball', A + V((0, 0, 0.075)) + (p1 * math.cos(a) + p2 * math.sin(a)) * 0.05, 0.024))

suit = metaball('Suit', el, res=0.01)
remesh(suit, 0.005, smooth_iter=6, smooth_fac=0.6)
# fabric: compression folds (horizontal bands), big lumps, fine weave-ish noise
displace_noise(suit, [(9, 0.006, (1, 1, 1)), (26, 0.0045, (0.35, 0.35, 1.8)), (70, 0.0012, (1, 1, 1))])
smooth(suit, 1, 0.4)
decimate(suit, 3300)
shade_smooth(suit)

# patch layout: (centre, half-size xyz, tone)
PATCHES = [
    ((0.06, -0.10, 0.55), (0.045, 0.06, 0.04), (0.46, 0.5, 0.53)),
    ((-0.07, 0.09, 0.47), (0.05, 0.06, 0.05), (0.62, 0.53, 0.36)),
    ((0.08, -0.03, 0.24), (0.06, 0.06, 0.035), (0.44, 0.47, 0.5)),
    ((-0.21, 0.02, 0.50), (0.04, 0.06, 0.04), (0.6, 0.52, 0.4)),
    ((-0.09, -0.07, 0.31), (0.05, 0.06, 0.04), (0.5, 0.47, 0.4)),
    ((0.02, 0.10, 0.60), (0.05, 0.05, 0.035), (0.45, 0.49, 0.52)),
    ((0.15, 0.0, 0.62), (0.05, 0.05, 0.04), (0.58, 0.5, 0.38)),
    ((0.1, 0.08, 0.37), (0.05, 0.05, 0.045), (0.5, 0.53, 0.55)),
]


def paint_suit(co, nr, mats, vidx):
    n = len(co)
    base = np.array([0.70, 0.67, 0.60])
    col = np.tile(base, (n, 1))
    vco = get_co(suit)
    big = nz(vco, 6, (1, 2, 3))[vidx]
    mid = nz(vco, 22, (5, 1, 2))[vidx]
    col *= (1 + 0.08 * big + 0.05 * mid)[:, None]
    # patches + seam stitch borders
    for c, hs, tone in PATCHES:
        d = np.max(np.abs(co - np.array(c)) / np.array(hs), axis=1)
        inside = d < 1.0
        col[inside] = np.array(tone) * (1 + 0.05 * big[inside])[:, None]
        seam = (d > 0.85) & (d < 1.15)
        col[seam] *= 0.45
    # dirt stains: knees, cuffs, seat
    stain = smoothstep(0.25, 0.75, nz(vco, 9, (7, 7, 7), 2)[vidx] * 0.5 + 0.5)
    brown = np.array([0.36, 0.30, 0.22])
    col = lerp(col, brown, 0.55 * stain)
    # grime rising from boots
    gr = 1 - smoothstep(0.06, 0.32, co[:, 2])
    col = lerp(col, np.array([0.25, 0.22, 0.18]), 0.6 * gr)
    # faded grey hazard band on upper arms
    for s in (1, -1):
        S, E, W, H, End = arm_pts(s)
        d, t = seg_dist(co, np.array(S), np.array(E))
        band = (d < 0.075) & (np.abs(t - 0.55) < 0.12)
        col[band] = lerp(col[band], np.array([0.62, 0.45, 0.16]), 0.55)
    return col

paint_part(suit, paint_suit)
set_mat(suit, 'cloth')
parts.append(Part(suit))

# ------------------------------------------------------------------ boots (rubber)
for side, s in (('L', 1), ('R', -1)):
    Hp, K, A, T, En = leg_pts(s)
    x = A.x
    b = metaball('Boot' + side, [
        ('ell', (x, -0.04, 0.052), (0.074, 0.12, 0.058)),
        ('cap', (x, 0.01, 0.05), (x, 0.0, 0.14), 0.064),
        ('ball', (x, -0.115, 0.052), 0.062),
        ('ell', (x, 0.03, 0.045), (0.064, 0.055, 0.047)),
    ], res=0.008)
    remesh(b, 0.005, 3)
    co = get_co(b)
    co[:, 2] = np.maximum(co[:, 2], 0.0)
    # sole lip: widen bottom band
    lip = co[:, 2] < 0.028
    cx = np.array([x, -0.04])
    co[lip, :2] = cx + (co[lip, :2] - cx) * 1.07
    set_co(b, co)
    displace_noise(b, [(30, 0.002)])
    decimate(b, 520)
    co = get_co(b); co[:, 2] = np.maximum(co[:, 2], 0.0); set_co(b, co)
    shade_smooth(b)

    def paint_boot(co, nr, mats, vidx, x=x):
        n = len(co)
        col = np.tile(np.array([0.17, 0.19, 0.17]), (n, 1))
        sole = co[:, 2] < 0.03
        col[sole] = (0.09, 0.085, 0.08)
        toe = co[:, 1] < -0.1
        col[toe & ~sole] *= 1.25  # scuffed toe cap
        mud = smoothstep(0.0, 0.6, nz(co, 25, (3, 9, 1)) * 0.5 + 0.3) * (1 - smoothstep(0.02, 0.09, co[:, 2]))
        col = lerp(col, np.array([0.3, 0.25, 0.18]), 0.7 * mud)
        # laces / straps band
        band = (np.abs(co[:, 2] - 0.105) < 0.01) & ~sole
        col[band] = (0.4, 0.38, 0.33)
        return col
    paint_part(b, paint_boot)
    set_mat(b, 'rubber')
    parts.append(Part(b, allowed=['leg_%s_foot' % side, 'leg_%s_lower' % side]))

# ------------------------------------------------------------------ mittens (rubber)
for side, s in (('L', 1), ('R', -1)):
    S, E, W, H, End = arm_pts(s)
    ax = (H - W).normalized()
    c = W.lerp(H, 0.6)
    m = metaball('Mitt' + side, [
        ('cap', W + ax * 0.01, H, 0.044),
        ('ell', c, (0.048, 0.042, 0.05)),
        ('ball', c + V((-0.03 * s, -0.035, 0.01)), 0.024),   # thumb
        ('cap', W - ax * 0.015, W + ax * 0.01, 0.042),        # gauntlet
    ], res=0.006)
    remesh(m, 0.004, 3)
    displace_noise(m, [(30, 0.002)])
    decimate(m, 360)
    shade_smooth(m)

    def paint_mitt(co, nr, mats, vidx, W=W):
        col = np.tile(np.array([0.2, 0.23, 0.2]), (len(co), 1))
        cuff = np.linalg.norm(co - np.array(W), axis=1) < 0.035
        col[cuff] = (0.13, 0.14, 0.13)
        col *= (1 + 0.15 * nz(co, 30, (2, 2, 2)))[:, None]
        return col
    paint_part(m, paint_mitt)
    set_mat(m, 'rubber')
    parts.append(Part(m, bone='arm_%s_hand' % side))

# ------------------------------------------------------------------ helmet (metal) + visor (glow_amber)
HC = V((0, 0, 0.825)); HR = 0.148
VIS_DIR = V((0, -math.cos(math.radians(22)), math.sin(math.radians(22)))).normalized()
bm = bmesh.new()
bm_sphere(bm, HC, HR, u=24, v=14)
# collar ring + flange
bm_torus(bm, (0, 0, 0.705), 0.128, 0.02, seg=20, rseg=5)
bm_cyl(bm, (0, 0, 0.67), (0, 0, 0.705), 0.125, 0.135, seg=24)
# collar rivets
for k in range(12):
    a = 2 * math.pi * k / 12 + 0.13
    bm_sphere(bm, (math.cos(a) * 0.145, math.sin(a) * 0.145, 0.705), 0.009, u=6, v=3)
# visor frame torus and rivets
VR = 0.082
vf = HC + VIS_DIR * (HR - 0.004)
bm_torus(bm, vf, VR + 0.012, 0.015, axis=VIS_DIR, seg=24, rseg=5)
q = V((0, 0, 1)).rotation_difference(VIS_DIR)
for k in range(8):
    a = 2 * math.pi * k / 8 + math.pi / 8
    p = vf + q @ V((math.cos(a) * (VR + 0.012), math.sin(a) * (VR + 0.012), 0.014))
    bm_sphere(bm, p, 0.0065, u=6, v=3)
# side ports (blind, dark)
for s in (1, -1):
    d = V((s * 0.97, 0.1, 0.18)).normalized()
    bm_torus(bm, HC + d * (HR - 0.003), 0.04, 0.011, axis=d, seg=12, rseg=4)
    bm_cyl(bm, HC + d * (HR - 0.02), HC + d * (HR + 0.004), 0.038, seg=12)
# top valve + lifting eye
bm_cyl(bm, (0, 0.015, HC.z + HR - 0.01), (0, 0.015, HC.z + HR + 0.01), 0.028, 0.024, seg=12)
bm_torus(bm, (0, 0.015, 0.9795), 0.016, 0.0045, axis=(1, 0, 0), seg=10, rseg=4)
# rear air nozzle stub (hose to backpack reads from above)
bm_cyl(bm, HC + V((0.05, 0.12, -0.05)), HC + V((0.07, 0.17, -0.07)), 0.022, seg=10)
helmet = mesh_from_bm(bm, 'Helmet')
shade_smooth(helmet, sharp_angle=50)


def paint_helmet(co, nr, mats, vidx):
    n = len(co)
    brass = np.array([0.56, 0.44, 0.26])
    steel = np.array([0.40, 0.40, 0.41])
    r = np.linalg.norm(co - np.array(HC), axis=1)
    col = np.tile(brass, (n, 1))
    collar = co[:, 2] < 0.72
    col[collar] = steel
    tarn = nz(co, 14, (4, 4, 4), 2)
    col = lerp(col, np.array([0.30, 0.34, 0.27]), smoothstep(0.0, 0.5, tarn) * 0.7)   # verdigris tarnish
    dents = nz(co, 40, (9, 1, 5))
    col *= (1 + 0.12 * dents)[:, None]
    # dark side-port glass
    for s in (1, -1):
        d = np.array(V((s * 0.97, 0.1, 0.18)).normalized())
        port = (co - np.array(HC)) @ d > HR - 0.022
        port &= np.linalg.norm((co - np.array(HC)) - np.outer((co - np.array(HC)) @ d, d), axis=1) < 0.036
        col[port] = (0.12, 0.13, 0.14)
    # streaky grime running down from the top
    streak = smoothstep(0.2, 0.8, nz(co * np.array([1, 1, 0.12]), 30, (3, 3, 3)) * 0.5 + 0.5)
    col *= (1 - 0.3 * streak)[:, None]
    return col

paint_part(helmet, paint_helmet)
set_mat(helmet, 'metal')
parts.append(Part(helmet, bone='head'))

# visor glass: spherical cap slightly proud of the helmet
bm = bmesh.new()
cap_r = HR + 0.006
ang = math.asin(VR / HR)
rings, segs = 9, 24
center_v = bm.verts.new(HC + VIS_DIR * cap_r)
prev = None
ring_list = []
for i in range(1, rings + 1):
    t = ang * i / rings
    ring = []
    for j in range(segs):
        a = 2 * math.pi * j / segs
        local = V((math.sin(t) * math.cos(a), math.sin(t) * math.sin(a), math.cos(t)))
        ring.append(bm.verts.new(HC + (q @ local) * cap_r))
    ring_list.append(ring)
for j in range(segs):
    bm.faces.new((center_v, ring_list[0][j], ring_list[0][(j + 1) % segs]))
for i in range(rings - 1):
    for j in range(segs):
        bm.faces.new((ring_list[i][j], ring_list[i + 1][j], ring_list[i + 1][(j + 1) % segs], ring_list[i][(j + 1) % segs]))
visor = mesh_from_bm(bm, 'Visor')
shade_smooth(visor)


def paint_visor(co, nr, mats, vidx):
    d = (co - np.array(HC)) @ np.array(VIS_DIR)
    t = np.clip((cap_r - d) / (cap_r - cap_r * math.cos(ang)), 0, 1)
    # hot centre, dimmer rim, plus a horizontal filament band
    col = lerp(np.array([1.0, 0.8, 0.5]), np.array([0.8, 0.36, 0.08]), t ** 0.9)
    # the kid's face: a soft shadowed oval behind the glass, lit from inside
    loc = (co - np.array(HC)) - np.outer((co - np.array(HC)) @ np.array(VIS_DIR), np.array(VIS_DIR))
    up = np.array(q @ V((0, 1, 0)))
    side = np.array(q @ V((1, 0, 0)))
    ly = loc @ up; lx = loc @ side
    # orient so that 'up' in the visor frame is world-up
    upw = np.array(V((0, 0, 1)) - VIS_DIR * VIS_DIR.z).astype(float); upw /= np.linalg.norm(upw)
    sw = np.cross(upw, np.array(VIS_DIR))
    ly = loc @ upw; lx = loc @ sw
    face = 1 - smoothstep(0.6, 1.0, np.sqrt((lx / 0.05) ** 2 + ((ly + 0.012) / 0.06) ** 2))
    col = col * (1 - 0.45 * face)[:, None]
    eyes = np.zeros(len(co))
    for ex in (-0.02, 0.02):
        eyes = np.maximum(eyes, 1 - smoothstep(0.004, 0.011, np.sqrt((lx - ex) ** 2 + (ly - 0.0) ** 2)))
    col = col * (1 - 0.5 * eyes)[:, None]
    return col

paint_part(visor, paint_visor)
set_mat(visor, 'glow_amber')
parts.append(Part(visor, bone='head'))

# ------------------------------------------------------------------ backpack (metal) + charge bar (glow_cyan)
bm = bmesh.new()
BP = V((0, 0.14, 0.535))
bm_box(bm, BP, (0.2, 0.095, 0.215), bevel=0.012)
bm_box(bm, BP + V((0, 0.0, 0.118)), (0.17, 0.08, 0.02), bevel=0.005)        # lid
for s in (1, -1):                                                         # side ribs
    for z in (-0.06, 0.0, 0.06):
        bm_box(bm, BP + V((s * 0.104, 0.0, z)), (0.012, 0.08, 0.018))
    bm_cyl(bm, BP + V((s * 0.065, 0.05, -0.09)), BP + V((s * 0.065, 0.055, -0.125)), 0.018, seg=10)  # feet / ports
# bar housing on the back face, wraps onto the top
bm_box(bm, BP + V((0.035, 0.052, -0.005)), (0.042, 0.012, 0.19), bevel=0.004)
bm_box(bm, BP + V((0.035, 0.012, 0.13)), (0.042, 0.085, 0.01), bevel=0.003)
# vent grille (left of bar)
for k in range(5):
    bm_box(bm, BP + V((-0.045, 0.05, -0.06 + k * 0.03)), (0.07, 0.008, 0.01))
# bolts
for sx in (1, -1):
    for sz in (1, -1):
        bm_sphere(bm, BP + V((sx * 0.085, 0.049, sz * 0.095)), 0.006, u=6, v=4)
pack = mesh_from_bm(bm, 'Pack')
shade_smooth(pack, sharp_angle=40)


def paint_pack(co, nr, mats, vidx):
    col = np.tile(np.array([0.27, 0.29, 0.30]), (len(co), 1))
    rust = smoothstep(0.1, 0.6, nz(co, 18, (2, 8, 4), 2))
    col = lerp(col, np.array([0.40, 0.22, 0.12]), rust * 0.8)
    chip = nz(co, 60, (1, 1, 1)) > 0.45
    col[chip] = (0.5, 0.5, 0.48)
    # stencil-ish yellow warning stripe on the lid
    lid = co[:, 2] > BP.z + 0.11
    stripe = lid & (np.sin((co[:, 0] + co[:, 1]) * 120) > 0)
    col[stripe] = lerp(col[stripe], np.array([0.6, 0.48, 0.12]), 0.75)
    return col

paint_part(pack, paint_pack)
set_mat(pack, 'metal')
parts.append(Part(pack, bone='chest'))

bm = bmesh.new()
for k in range(6):      # vertical segments on the back
    z = BP.z - 0.085 + k * 0.03
    bm_box(bm, BP + V((0.035, 0.0595, z - BP.z)), (0.026, 0.006, 0.022), bevel=0.0)
for k in range(3):      # segments on the top of the lid
    bm_box(bm, BP + V((0.035, 0.04 - k * 0.026, 0.1365)), (0.028, 0.02, 0.006), bevel=0.0)
bar = mesh_from_bm(bm, 'ChargeBar')
shade_smooth(bar, sharp_angle=30)
paint_part(bar, lambda co, nr, m, v: lerp(np.array([0.35, 0.9, 1.0]), np.array([0.7, 1.0, 1.0]), smoothstep(0.45, 0.66, co[:, 2])))
set_mat(bar, 'glow_cyan')
parts.append(Part(bar, bone='chest'))

# ------------------------------------------------------------------ straps, belt, hose (rubber)
suit.data.update()
sbvh = BVHTree.FromObject(suit, bpy.context.evaluated_depsgraph_get())


def onsurf(pts, off):
    out = []
    for p in pts:
        loc, n, i, d = sbvh.find_nearest(V(p))
        out.append(loc + n * off)
    return out


bm = bmesh.new()
for s in (1, -1):
    path = bezier_pts((s * 0.065, 0.10, 0.63), (s * 0.08, 0.02, 0.73), (s * 0.085, -0.13, 0.62), (s * 0.075, -0.1, 0.44), 11)
    path = onsurf(path, 0.006)
    bm_tube(bm, path, 0.017, seg=4, caps=True, flat=0.28)
# belt
belt = [V((math.cos(a) * 0.2, math.sin(a) * 0.2, 0.44)) for a in np.linspace(0, 2 * math.pi, 21)]
belt = onsurf(belt, 0.005)
belt[-1] = belt[0]
bm_tube(bm, belt[:-1] + [belt[0]], 0.016, seg=4, caps=False, flat=0.35, twist_ref=(0, 0, 1))
# hose: backpack -> right hip, with a sagging loop
hose = bezier_pts(BP + V((-0.07, 0.03, -0.11)), BP + V((-0.12, 0.10, -0.25)), V((-0.22, 0.09, 0.34)), V((-0.14, 0.0, 0.42)), 18)
bm_tube(bm, hose, 0.0135, seg=7)
rub = mesh_from_bm(bm, 'Straps')
shade_smooth(rub)
hose_np = np.array([h[:] for h in hose])


def paint_rub(co, nr, mats, vidx):
    col = np.tile(np.array([0.2, 0.19, 0.18]), (len(co), 1))
    # corrugated hose rings
    d = np.min(np.linalg.norm(co[:, None, :] - hose_np[None], axis=2), axis=1)
    on_hose = d < 0.02
    idx = np.argmin(np.linalg.norm(co[:, None, :] - hose_np[None], axis=2), axis=1)
    ring = (idx % 2 == 0) & on_hose
    col[on_hose] = (0.16, 0.2, 0.22)
    col[ring] = (0.28, 0.31, 0.32)
    col *= (1 + 0.15 * nz(co, 25))[:, None]
    return col

paint_part(rub, paint_rub)
set_mat(rub, 'rubber')
parts.append(Part(rub, allowed=['hips', 'spine', 'chest']))

# small metal bits: buckle, hose couplings, chest lamp housing
bm = bmesh.new()
bm_box(bm, onsurf([(0, -0.2, 0.44)], 0.012)[0], (0.04, 0.012, 0.03), bevel=0.004)
bm_cyl(bm, hose[0], hose[0] + V((0, 0, 0.02)), 0.019, seg=8)
bm_cyl(bm, hose[-1] + V((0.012, 0.0, 0.0)), hose[-1] - V((0.012, 0, 0)), 0.02, seg=8)
for s in (1, -1):
    p = onsurf([(s * 0.075, -0.2, 0.555)], 0.008)[0]
    bm_box(bm, p, (0.026, 0.01, 0.02), bevel=0.003)   # strap clips
bits = mesh_from_bm(bm, 'Bits')
shade_smooth(bits, sharp_angle=40)
paint_part(bits, lambda co, nr, m, v: np.tile(np.array([0.45, 0.43, 0.4]), (len(co), 1)) * (1 + 0.2 * nz(co, 50))[:, None])
set_mat(bits, 'metal')
parts.append(Part(bits, allowed=['hips', 'spine', 'chest']))

# ------------------------------------------------------------------ assemble, weight, finish
radii = {'hips': 0.11, 'spine': 0.1, 'chest': 0.11, 'head': 0.12,
         'arm_L_upper': 0.055, 'arm_L_lower': 0.05, 'arm_L_hand': 0.045,
         'arm_R_upper': 0.055, 'arm_R_lower': 0.05, 'arm_R_hand': 0.045,
         'leg_L_upper': 0.065, 'leg_L_lower': 0.06, 'leg_L_foot': 0.06,
         'leg_R_upper': 0.065, 'leg_R_lower': 0.06, 'leg_R_foot': 0.06}
kid = assemble('Kid', parts, arm_ob, radii, power=5, smooth_iters=5)
finish_colors(kid, ao_strength=0.55, ao_dist=0.12, cav_strength=0.45, grime=(0.65, 0.3), height=1.0)
print('TRIS', tri_count(kid))

out = os.path.join(OUT_DIR, 'player.glb')
export_glb([arm_ob, kid], out)
glb_report(out)

if not NORENDER:
    render_studio('player', 1.0)
    render_game('player', 1.0)
    # deformation test
    rotate_bone_world(arm_ob, 'leg_L_lower', (1, 0, 0), 60)
    rotate_bone_world(arm_ob, 'leg_R_upper', (1, 0, 0), -45)
    rotate_bone_world(arm_ob, 'arm_R_upper', (0, 1, 0), 90)
    rotate_bone_world(arm_ob, 'arm_L_lower', (1, 0, 0), -70)
    rotate_bone_world(arm_ob, 'chest', (0, 0, 1), 30)
    rotate_bone_world(arm_ob, 'head', (1, 0, 0), 20)
    render_studio('player_deform', 1.0)
