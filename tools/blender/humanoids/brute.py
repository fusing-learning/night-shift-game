"""The Hauler — brute. 2.3 m hunched, ~1.9 m wide, giant piston arm on its RIGHT (-X). Faces -Y.
Run: /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/blender/humanoids/brute.py
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, hlib
importlib.reload(hlib)
from hlib import *

NORENDER = 'norender' in sys.argv
reset()
random.seed(11)

# ------------------------------------------------------------------ skeleton
HIP = V((0, 0.12, 0.88)); SPN = V((0, 0.12, 1.12)); CHS = V((0, 0.07, 1.52)); CHT = V((0, -0.2, 1.9))
HDH = V((0, -0.28, 1.73)); HDT = V((0, -0.6, 1.54)); HDE = HDT + (HDT - HDH).normalized() * 0.06
# right (−X): giant piston arm, block resting on the ground in front
RS = V((-0.66, -0.08, 1.82)); RE = V((-0.95, 0.13, 1.06)); RW = V((-0.86, -0.62, 0.43)); RH = V((-0.86, -0.70, 0.07))
REND = V((-0.86, -0.71, 0.0))
# left (+X): withered arm curled against the chest
LS = V((0.47, -0.16, 1.76)); LE = V((0.53, -0.24, 1.42)); LW = V((0.22, -0.55, 1.52)); LEND = V((0.17, -0.57, 1.56))


def leg_pts(s):
    return V((0.34 * s, 0.12, 0.9)), V((0.49 * s, -0.07, 0.49)), V((0.41 * s, 0.03, 0.1)), V((0.41 * s, -0.2, 0.02))


bones = [
    ('root', (0, 0, 0), (0, 0, 0.15), None, False, False),
    ('hips', HIP, SPN, 'root', False, True),
    ('spine', SPN, CHS, 'hips', True, True),
    ('chest', CHS, CHT, 'spine', True, True),
    ('head', HDH, HDT, 'chest', False, True),
    ('head_end', HDT, HDE, 'head', True, False),
    ('arm_R_upper', RS, RE, 'chest', False, True),
    ('arm_R_lower', RE, RW, 'arm_R_upper', True, True),
    ('arm_R_hand', RW, RH, 'arm_R_lower', True, True),
    ('arm_R_end', RH, REND, 'arm_R_hand', True, False),
    ('arm_L_upper', LS, LE, 'chest', False, True),
    ('arm_L_lower', LE, LW, 'arm_L_upper', True, True),
    ('arm_L_end', LW, LEND, 'arm_L_lower', True, False),
]
for side, s in (('L', 1), ('R', -1)):
    Hp, K, A, T = leg_pts(s)
    bones += [('leg_%s_upper' % side, Hp, K, 'hips', False, True),
              ('leg_%s_lower' % side, K, A, 'leg_%s_upper' % side, True, True),
              ('leg_%s_end' % side, A, T, 'leg_%s_lower' % side, True, False)]
arm_ob = build_armature('Hauler_Rig', bones)
parts = []
BODY_BONES = ['hips', 'spine', 'chest', 'head', 'arm_R_upper', 'arm_R_lower', 'arm_R_hand',
              'leg_L_upper', 'leg_L_lower', 'leg_R_upper', 'leg_R_lower']

# ------------------------------------------------------------------ body volumes
el = [
    ('ell', (0, 0.08, 1.68), (0.55, 0.42, 0.44), (0.55, 0, 0)),      # massive rounded back
    ('ell', (0.0, 0.3, 1.36), (0.42, 0.26, 0.34)),                  # lower back mass
    ('ell', (0, -0.1, 1.3), (0.34, 0.29, 0.28)),                    # gut
    ('ell', (0, 0.1, 0.99), (0.32, 0.26, 0.16)),                    # pelvis
    ('ell', (0.1, -0.26, 1.47), (0.27, 0.17, 0.22)),                # chest front (left arm curls here)
    ('ell', (-0.32, -0.02, 1.8), (0.3, 0.3, 0.28)),                 # right trapezius toward the big arm
    ('ell', (0.32, -0.04, 1.76), (0.22, 0.24, 0.2)),                # left shoulder (smaller)
    ('cap', (0, -0.2, 1.72), HDH.lerp(HDT, 0.35), 0.11),            # short neck sunk between the shoulders
    ('ell', HDH.lerp(HDT, 0.62), (0.1, 0.105, 0.11)),               # tiny shrivelled head
    ('ell', (0, -0.3, 1.9), (0.3, 0.17, 0.13)),                     # brow of the hump overhanging the head
    ('ball', (0.27, -0.33, 1.76), 0.16), ('ball', (-0.3, -0.3, 1.78), 0.19),   # shoulders flanking the head
    ('cap', (0, 0.3, 2.0), (0, 0.62, 1.3), 0.07),                   # spine ridge under the skin
    ('ell', (0.26, 0.2, 1.84), (0.24, 0.28, 0.2), (0.5, 0, 0)),     # back muscle lobes (cleft along spine)
    ('ell', (-0.3, 0.16, 1.86), (0.28, 0.28, 0.21), (0.5, 0, 0)),
    ('-cap', (-0.32, 0.6, 1.24), (0.32, 0.6, 1.24), 0.035, {'stiff': 1.0}),     # fat folds, lower back
    ('-cap', (-0.28, 0.52, 1.08), (0.28, 0.52, 1.08), 0.03, {'stiff': 1.0}),
    # giant right arm
    ('ball', RS + V((0.0, 0.0, 0.05)), 0.33),
    ('cap', RS, RE, 0.25),
    ('ell', RS.lerp(RE, 0.42) + V((-0.07, -0.05, 0)), (0.31, 0.29, 0.34)),  # swollen bicep mass
    ('ball', RE, 0.21),
    ('cap', RE, RE.lerp(RW, 0.4), 0.19),
    ('ell', RE.lerp(RW, 0.2) + V((-0.05, 0.02, 0)), (0.22, 0.21, 0.22)),
    ('cap', RE.lerp(RW, 0.38), RE.lerp(RW, 0.5) + V((-0.06, 0.04, 0)), 0.09),     # flesh clinging to the cylinder
    ('ball', RS.lerp(RE, 0.25) + V((-0.22, 0.1, 0.05)), 0.13),                   # tumorous lumps
    ('ball', RS.lerp(RE, 0.6) + V((-0.2, -0.08, 0.0)), 0.12),
    ('ball', RS.lerp(RE, 0.45) + V((-0.05, 0.22, 0.0)), 0.11),
]
for s in (1, -1):
    Hp, K, A, T = leg_pts(s)
    el += [('cap', Hp, K, 0.21), ('ell', Hp.lerp(K, 0.4) + V((0.04 * s, 0, 0)), (0.22, 0.22, 0.26)),
           ('ball', K, 0.18), ('cap', K, A, 0.155), ('ell', K.lerp(A, 0.3), (0.17, 0.18, 0.17)),
           ('ell', A + V((0, -0.06, -0.03)), (0.17, 0.24, 0.1)),
           ('ball', T + V((0.06 * s, 0.03, 0.04)), 0.07), ('ball', T + V((-0.04 * s, 0.04, 0.04)), 0.065)]
body = metaball('Body', el, res=0.022)
remesh(body, 0.012, smooth_iter=5, smooth_fac=0.6)
co = get_co(body)
co[:, 2] = np.maximum(co[:, 2], 0.0)
set_co(body, co)

# --- seams (graft lines) traced on the high-res surface, then pressed in
bvh_hi = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())


def surf_path(pts, off=0.0):
    out = []
    for p in pts:
        loc, n, i, d = bvh_hi.find_nearest(V(p))
        out.append((loc + n * off, n))
    return out


SEAMS = []
PLATE_C = [(-0.22, 0.3, 2.15), (0.3, 0.32, 2.0), (-0.05, 0.55, 1.65), (-0.62, 0.05, 2.15), (0.42, -0.12, 2.0)]
SEAMS.append(surf_path([V((0.42, 0.42, 1.45)).lerp(V((-0.15, 0.18, 2.2)), t) for t in np.linspace(0, 1, 26)]))
SEAMS.append(surf_path([V((0.05, 0.6, 1.25)).lerp(V((-0.35, 0.45, 1.0)), t) for t in np.linspace(0, 1, 14)]))
ax = (RE - RS).normalized(); p1 = ax.cross(V((0, 0, 1))).normalized(); p2 = ax.cross(p1)
ring = [RS + ax * 0.06 + (p1 * math.cos(a) + p2 * math.sin(a)) * 0.42 for a in np.linspace(0, 2 * math.pi, 34)]
SEAMS.append(surf_path(ring))
SEAMS.append(surf_path([V((0.45, -0.1, 2.0)).lerp(V((0.55, 0.25, 1.6)), t) for t in np.linspace(0, 1, 12)]))
seam_pts = np.array([p[:] for sm in SEAMS for p, n in sm])


def seam_dist(c):
    d = np.full(len(c), 9.0)
    for k in range(0, len(seam_pts), 1):
        d = np.minimum(d, np.linalg.norm(c - seam_pts[k], axis=1))
    return d

co = get_co(body); nr = get_normals(body)
sd = seam_dist(co)
pucker = -0.012 * (1 - smoothstep(0.0, 0.03, sd)) + 0.006 * (smoothstep(0.02, 0.04, sd) * (1 - smoothstep(0.04, 0.07, sd)))
set_co(body, co + nr * pucker[:, None])
displace_noise(body, [(2.6, 0.03), (8, 0.01, (1, 1, 1), (3, 1, 7)), (30, 0.0025)])
smooth(body, 1, 0.3)
decimate(body, 9800)
co = get_co(body); co[:, 2] = np.maximum(co[:, 2], 0.0); set_co(body, co)
shade_smooth(body)


def flesh_paint(co, nr, vco, vidx, veiny=1.0):
    n = len(co)
    big = nz(vco, 2.5, (1, 1, 1), 2)[vidx]
    mid = nz(vco, 9, (4, 4, 4))[vidx]
    veins = np.abs(nz(vco, 6, (8, 2, 6), 3))[vidx]
    col = np.tile(np.array([0.44, 0.34, 0.31]), (n, 1))
    col *= (1 + 0.1 * big + 0.06 * mid)[:, None]
    bruise = smoothstep(0.12, 0.5, nz(vco, 3.5, (9, 9, 1), 2)[vidx])
    col = lerp(col, np.array([0.32, 0.17, 0.21]), 0.8 * bruise)
    yel = smoothstep(0.2, 0.55, nz(vco, 4, (2, 6, 3), 2)[vidx]) * (1 - bruise)
    col = lerp(col, np.array([0.55, 0.52, 0.34]), 0.5 * yel)
    col = lerp(col, np.array([0.2, 0.12, 0.2]), veiny * 0.85 * (1 - smoothstep(0.0, 0.06, veins)))
    col = lerp(col, np.array([0.5, 0.48, 0.5]), 0.3 * smoothstep(0.3, 0.8, big))  # greyish dead patches
    return col


def paint_body(co, nr, mats, vidx):
    vco = get_co(body)
    arm_w = 1 - smoothstep(0.3, 0.6, np.linalg.norm(co - np.array(RE), axis=1))
    col = flesh_paint(co, nr, vco, vidx, veiny=1.0)
    # seams: dark crusted lines with red, irritated margins
    sd = seam_dist(co)
    col = lerp(col, np.array([0.62, 0.3, 0.28]), 0.6 * (1 - smoothstep(0.02, 0.07, sd)))
    col = lerp(col, np.array([0.15, 0.06, 0.06]), 1 - smoothstep(0.008, 0.02, sd))
    for pc in PLATE_C:
        dd = np.linalg.norm(co - np.array(pc), axis=1)
        col = lerp(col, np.array([0.5, 0.22, 0.2]), 0.55 * (1 - smoothstep(0.15, 0.3, dd)))
    # tiny head: darker, leathery
    hd = np.linalg.norm(co - np.array(HDH.lerp(HDT, 0.62)), axis=1)
    col = lerp(col, np.array([0.35, 0.27, 0.25]), 1 - smoothstep(0.08, 0.16, hd))
    # grime on legs and feet
    col = lerp(col, np.array([0.24, 0.2, 0.17]), 0.7 * (1 - smoothstep(0.0, 0.55, co[:, 2])))
    return col

paint_part(body, paint_body)
set_mat(body, 'flesh')
parts.append(Part(body, allowed=BODY_BONES))

# ------------------------------------------------------------------ withered left arm (separate so it stays free of the chest)
la = [('ball', LS, 0.07), ('cap', LS, LE, 0.05), ('ball', LE, 0.052), ('cap', LE, LW, 0.04),
      ('cap', LE, LE.lerp(LW, 0.3), 0.046), ('ell', LW, (0.045, 0.035, 0.05))]
d = (LEND - LW).normalized()
for k, (a, ln) in enumerate(((-0.5, 0.07), (0.0, 0.08), (0.5, 0.065))):
    q = Quaternion(V((0.3, 0.2, 1)).normalized(), a)
    f1 = LW + q @ d * 0.03
    f2 = f1 + q @ d * ln
    f3 = f2 + V((0, 0.03, -0.035))   # curled claw tips
    la += [('cap', f1, f2, 0.016), ('cap', f2, f3, 0.012)]
larm = metaball('LArm', la, res=0.009)
remesh(larm, 0.007, 3)
displace_noise(larm, [(18, 0.004), (50, 0.0015)])
decimate(larm, 750)
shade_smooth(larm)
paint_part(larm, lambda co, nr, m, v: lerp(flesh_paint(co, nr, get_co(larm), v, 1.4), np.array([0.42, 0.36, 0.38]), 0.35))
set_mat(larm, 'flesh')
parts.append(Part(larm, allowed=['chest', 'arm_L_upper', 'arm_L_lower']))

# ------------------------------------------------------------------ piston, rod, wrist housing (metal, arm_R_lower)
ax = (RW - RE).normalized()
bm = bmesh.new()
C0 = RE.lerp(RW, 0.22); C1 = RE.lerp(RW, 0.7)
bm_cyl(bm, C0, C1, 0.12, seg=16)
for t in (0.47, 0.6, 0.69):
    c = RE.lerp(RW, t)
    bm_cyl(bm, c - ax * 0.018, c + ax * 0.018, 0.128, seg=16)     # cylinder flanges / clamp rings
for t in (0.3, 0.42):
    c = RE.lerp(RW, t)
    bm_cyl(bm, c - ax * 0.03, c + ax * 0.03, 0.195 if t < 0.4 else 0.14, seg=16)   # clamps biting into flesh
# flange bolts
for k in range(6):
    a = 2 * math.pi * k / 6
    perp1 = ax.cross(V((1, 0, 0))).normalized(); perp2 = ax.cross(perp1)
    p = RE.lerp(RW, 0.69) + (perp1 * math.cos(a) + perp2 * math.sin(a)) * 0.128 + ax * 0.02
    bm_cyl(bm, p, p + ax * 0.02, 0.012, seg=6)
piston = mesh_from_bm(bm, 'Piston')
shade_smooth(piston, sharp_angle=40)


def rusty(co, nr, m, v, base=(0.36, 0.36, 0.37), amount=1.0):
    col = np.tile(np.array(base), (len(co), 1))
    col *= (1 + 0.15 * nz(co, 20, (1, 2, 3)))[:, None]
    rust = smoothstep(-0.1, 0.5, nz(co, 6, (5, 5, 5), 3))
    col = lerp(col, np.array([0.42, 0.2, 0.09]), amount * 0.85 * rust)
    streak = smoothstep(0.3, 0.7, nz(co * np.array([1, 1, 0.15]), 18, (2, 9, 4)))
    col = lerp(col, np.array([0.3, 0.13, 0.06]), amount * 0.6 * streak)
    return col

paint_part(piston, lambda co, nr, m, v: rusty(co, nr, m, v, amount=0.7))
set_mat(piston, 'metal')
parts.append(Part(piston, bone='arm_R_lower'))

bm = bmesh.new()
bm_cyl(bm, C1, RW + ax * 0.02, 0.055, seg=14)                         # chrome rod
rod = mesh_from_bm(bm, 'Rod')
shade_smooth(rod, sharp_angle=60)
paint_part(rod, lambda co, nr, m, v: np.tile(np.array([0.8, 0.8, 0.82]), (len(co), 1)) * (1 - 0.25 * smoothstep(0.3, 0.8, nz(co, 30, (1, 1, 1))))[:, None])
set_mat(rod, 'metal')
parts.append(Part(rod, bone='arm_R_lower'))

# ------------------------------------------------------------------ press block (metal, arm_R_hand)
bm = bmesh.new()
BC = V((-0.86, -0.72, 0.18))
bm_box(bm, BC, (0.52, 0.44, 0.34), bevel=0.025)
bm_box(bm, BC + V((0, 0, -0.15)), (0.56, 0.48, 0.05), bevel=0.012)                 # striking plate
bm_box(bm, BC + V((0, 0, 0.19)), (0.3, 0.26, 0.06), bevel=0.012)                  # mount
bm_cyl(bm, RW + V((0.15, 0, 0)), RW + V((-0.15, 0, 0)), 0.075, seg=14)           # wrist trunnion
for s in (1, -1):
    bm_box(bm, RW + V((s * 0.12, 0.0, -0.06)), (0.04, 0.16, 0.16), bevel=0.01)   # trunnion cheeks
    for k in range(3):                                                            # side ribs
        bm_box(bm, BC + V((s * 0.27, -0.14 + k * 0.14, 0.0)), (0.03, 0.04, 0.28), bevel=0.006)
for sx in (-0.2, 0.2):
    for sy in (-0.16, 0.16):
        bm_cyl(bm, BC + V((sx, sy, 0.17)), BC + V((sx, sy, 0.19)), 0.022, seg=6)    # bolt heads
block = mesh_from_bm(bm, 'Block')
shade_smooth(block, sharp_angle=40)


def paint_block(co, nr, m, v):
    col = rusty(co, nr, m, v, base=(0.3, 0.3, 0.31), amount=0.8)
    # faded hazard chevrons on the front and sides
    side = (np.abs(nr[:, 2]) < 0.5) & (co[:, 2] > 0.06) & (co[:, 2] < 0.32)
    stripe = np.mod((co[:, 0] + co[:, 1] + co[:, 2]) / 0.09, 1.0) < 0.5
    paint = side & stripe & (nz(co, 14, (3, 3, 3)) < 0.25)
    col[paint] = lerp(col[paint], np.array([0.62, 0.45, 0.08]), 0.8)
    # polished striking face edge
    col[co[:, 2] < 0.04] = (0.5, 0.5, 0.5)
    return col

paint_part(block, paint_block)
set_mat(block, 'metal')
parts.append(Part(block, bone='arm_R_hand'))

# ------------------------------------------------------------------ back hardware: plates, rivets, staples, exhausts (metal)
body.data.update()
bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())


def frame_at(c):
    loc, n, i, d = bvh.find_nearest(V(c))
    t1 = n.cross(V((0, 0, 1)) if abs(n.z) < 0.9 else V((1, 0, 0))).normalized()
    t2 = n.cross(t1)
    return loc, n, t1, t2


def plate(bm, c, w, h, rot=0.0, thick=0.022, nseg=4, cut=0.25):
    loc, n, t1, t2 = frame_at(c)
    q = Quaternion(n, rot)
    t1 = q @ t1; t2 = q @ t2
    grid = []
    for j in range(nseg + 1):
        row = []
        for i in range(nseg + 1):
            u = (i / nseg - 0.5) * w; v = (j / nseg - 0.5) * h
            if i == nseg and j == nseg:          # clipped corner
                u -= w * cut * 0.5; v -= h * cut * 0.5
            p = loc + t1 * u + t2 * v + n * 0.08
            l2, n2, _, _ = bvh.find_nearest(p)
            row.append((l2 + n2 * 0.006, n2))
        grid.append(row)
    top = [[bm.verts.new(p + nn * thick) for (p, nn) in row] for row in grid]
    bot = [[bm.verts.new(p) for (p, nn) in row] for row in grid]
    N = nseg
    for j in range(N):
        for i in range(N):
            bm.faces.new((top[j][i], top[j][i + 1], top[j + 1][i + 1], top[j + 1][i]))
            bm.faces.new((bot[j][i], bot[j + 1][i], bot[j + 1][i + 1], bot[j][i + 1]))
    border = [(0, i) for i in range(N)] + [(i, N) for i in range(N)] + [(N, N - i) for i in range(N)] + [(N - i, 0) for i in range(N)]
    for k in range(len(border)):
        a = border[k]; b = border[(k + 1) % len(border)]
        bm.faces.new((bot[a[0]][a[1]], bot[b[0]][b[1]], top[b[0]][b[1]], top[a[0]][a[1]]))
    # bolts at corners and mid-edges
    for (j, i) in ((0, 0), (0, N), (N, 0), (0, N // 2), (N // 2, 0), (N, N // 2), (N // 2, N)):
        if (j, i) == (N, N):
            continue
        p, nn = grid[j][i]
        jj = min(max(j, 1), N - 1); ii = min(max(i, 1), N - 1)
        pin = grid[jj][ii][0]
        pb = p + (pin - p) * 0.35 + nn * (thick + 0.004)
        bm_sphere(bm, pb, 0.016, u=6, v=3)


bm = bmesh.new()
plate(bm, (-0.22, 0.3, 2.15), 0.42, 0.34, 0.2)
plate(bm, (0.3, 0.32, 2.0), 0.36, 0.4, -0.35, cut=0.35)
plate(bm, (-0.05, 0.55, 1.65), 0.38, 0.3, 0.1)
plate(bm, (-0.62, 0.05, 2.15), 0.34, 0.3, 0.6)                       # over the graft shoulder
plate(bm, (0.42, -0.12, 2.0), 0.26, 0.22, 0.3, cut=0.4)
# rivet row along the spine ridge
for t in np.linspace(0, 1, 15):
    c = V((0.0, -0.05, 2.2)).lerp(V((0.0, 0.7, 1.3)), t)
    loc, n, t1, t2 = frame_at(c + V((0, 0.3, 0.3)))
    bm_sphere(bm, loc + n * 0.004, 0.022, u=6, v=3)
# staples across seams
for sm in SEAMS:
    for k in range(1, len(sm) - 1, 2):
        (p, n) = sm[k]
        loc, n2, _, _ = bvh.find_nearest(p)
        tdir = (sm[k + 1][0] - sm[k - 1][0]).normalized()
        sdir = tdir.cross(n2).normalized()
        c = loc + n2 * 0.006
        M = Matrix((sdir, tdir, n2)).transposed().to_4x4()
        M.translation = c
        vs = bmesh.ops.create_cube(bm, size=1.0, matrix=M @ Matrix.Diagonal((0.07, 0.012, 0.012, 1)))['verts']
# exhaust stacks behind the shoulders
EXH = []
for s, base in ((1, V((0.26, 0.34, 1.96))), (-1, V((-0.3, 0.28, 2.02)))):
    loc, n, t1, t2 = frame_at(base)
    dirv = (V((0.15 * s, 0.45, 1.0))).normalized()
    a = loc - dirv * 0.06; b = loc + dirv * 0.17
    bm_cyl(bm, a, b, 0.07, seg=14, caps=False)
    bm_cyl(bm, b - dirv * 0.0, b - dirv * 0.012, 0.07, 0.058, seg=14, caps=False)   # inner lip
    bm_torus(bm, b, 0.072, 0.012, axis=dirv, seg=14, rseg=4)
    bm_cyl(bm, loc - dirv * 0.02, loc + dirv * 0.05, 0.1, 0.085, seg=14)             # base collar
    bm_torus(bm, a.lerp(b, 0.55), 0.073, 0.009, axis=dirv, seg=14, rseg=4)
    EXH.append((b, dirv))
hw = mesh_from_bm(bm, 'Hardware')
shade_smooth(hw, sharp_angle=40)
paint_part(hw, lambda co, nr, m, v: rusty(co, nr, m, v, base=(0.34, 0.33, 0.33), amount=1.0))
set_mat(hw, 'metal')
parts.append(Part(hw, allowed=['chest', 'spine', 'hips', 'arm_R_upper']))

# glowing insides of the stacks
bm = bmesh.new()
for b, dirv in EXH:
    bm_cyl(bm, b - dirv * 0.09, b - dirv * 0.05, 0.062, seg=14)
glow = mesh_from_bm(bm, 'ExhGlow')
shade_smooth(glow)
paint_part(glow, lambda co, nr, m, v: np.tile(np.array([1.0, 0.55, 0.18]), (len(co), 1)))
set_mat(glow, 'glow_orange')
parts.append(Part(glow, bone='chest'))

# ------------------------------------------------------------------ welding helmet shell (metal, head)
HC = HDH.lerp(HDT, 0.62)
fwd = V((0, -1, -0.55)).normalized()
up = V((0, 0, 1)) - fwd * fwd.z; up.normalize()
rt = fwd.cross(up)
bm = bmesh.new()
NA, NE = 10, 7
outer, inner = [], []
for j in range(NE + 1):
    e = -0.75 + 1.95 * j / NE
    ro, ri = [], []
    for i in range(NA + 1):
        a_ = -1.35 + 2.7 * i / NA
        d = fwd * (math.cos(e) * math.cos(a_)) + rt * (math.cos(e) * math.sin(a_)) + up * math.sin(e)
        rr = 0.145 * (1.0 + 0.12 * math.cos(e) * math.cos(a_))      # snout-like front bulge
        ro.append(bm.verts.new(HC + d * rr)); ri.append(bm.verts.new(HC + d * (rr - 0.012)))
    outer.append(ro); inner.append(ri)
for j in range(NE):
    for i in range(NA):
        bm.faces.new((outer[j][i], outer[j + 1][i], outer[j + 1][i + 1], outer[j][i + 1]))
        bm.faces.new((inner[j][i], inner[j][i + 1], inner[j + 1][i + 1], inner[j + 1][i]))
for i in range(NA):
    bm.faces.new((outer[0][i], outer[0][i + 1], inner[0][i + 1], inner[0][i]))
    bm.faces.new((outer[NE][i + 1], outer[NE][i], inner[NE][i], inner[NE][i + 1]))
for j in range(NE):
    bm.faces.new((outer[j + 1][0], outer[j][0], inner[j][0], inner[j + 1][0]))
    bm.faces.new((outer[j][NA], outer[j + 1][NA], inner[j + 1][NA], inner[j][NA]))
for s_ in (1, -1):                       # hinge pivots
    p = HC + rt * (0.15 * s_) + up * 0.02
    bm_cyl(bm, p, p + rt * (0.03 * s_), 0.025, seg=8)
for a_ in (-0.9, -0.3, 0.3, 0.9):        # rivets along the brow
    d = fwd * (math.cos(0.45) * math.cos(a_)) + rt * (math.cos(0.45) * math.sin(a_)) + up * math.sin(0.45)
    bm_sphere(bm, HC + d * 0.162, 0.012, u=6, v=3)
strap = [HC + (rt * math.cos(a_) + (-fwd) * math.sin(a_)) * 0.12 + up * 0.0 for a_ in np.linspace(-0.2, math.pi + 0.2, 9)]
bm_tube(bm, strap, 0.02, seg=4, flat=0.3, twist_ref=up)
mask = mesh_from_bm(bm, 'Mask')
shade_smooth(mask, sharp_angle=50)


def paint_mask(co, nr, m, v):
    col = rusty(co, nr, m, v, base=(0.3, 0.31, 0.32), amount=0.7)
    rel = co - np.array(HC)
    rn = rel / (np.linalg.norm(rel, axis=1, keepdims=True) + 1e-9)
    el = np.arcsin(np.clip(rn @ np.array(up), -1, 1))
    az = np.arctan2(rn @ np.array(rt), rn @ np.array(fwd))
    slit = (np.abs(el - 0.12) < 0.09) & (np.abs(az) < 0.75)
    col[slit] = (0.05, 0.06, 0.06)       # dark glass slit
    # scorch around the slit
    col = lerp(col, np.array([0.12, 0.1, 0.09]), 0.6 * (1 - smoothstep(0.08, 0.2, np.abs(el - 0.12))) * (np.abs(az) < 1.0))
    return col

paint_part(mask, paint_mask)
set_mat(mask, 'metal')
parts.append(Part(mask, bone='head'))

# ------------------------------------------------------------------ hoses into the big arm (rubber)
bm = bmesh.new()
HOSES = [
    ((-0.32, 0.38, 1.98), (-0.55, 0.6, 2.0), (-1.05, 0.35, 1.5), RE.lerp(RW, 0.3) + V((-0.1, 0.06, 0.05))),
    ((-0.1, 0.42, 1.9), (-0.4, 0.75, 1.6), (-1.0, 0.4, 1.2), RE.lerp(RW, 0.77) + V((-0.08, 0.0, 0.02))),
    ((-0.45, 0.25, 2.05), (-0.75, 0.3, 2.1), (-0.9, 0.2, 1.75), RS.lerp(RE, 0.45) + V((-0.15, 0.12, 0.0))),
]
HOSE_PTS = []
for h in HOSES:
    l0, n0, _, _ = frame_at(h[0])
    h = (l0 - n0 * 0.02, l0 + n0 * 0.3 + (V(h[1]) - V(h[0])) * 0.5, h[2], h[3])
    pts = bezier_pts(*h, 18)
    HOSE_PTS += pts
    bm_tube(bm, pts, 0.032, seg=6)
    bm_cyl(bm, pts[-1] - (pts[-1] - pts[-2]).normalized() * 0.04, pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.02, 0.045, seg=8)
hoses = mesh_from_bm(bm, 'Hoses')
shade_smooth(hoses)
hp = np.array([p[:] for p in HOSE_PTS])


def paint_hoses(co, nr, m, v):
    col = np.tile(np.array([0.17, 0.16, 0.15]), (len(co), 1))
    idx = np.argmin(np.linalg.norm(co[:, None, :] - hp[None], axis=2), axis=1)
    col[idx % 2 == 0] *= 1.5
    col *= (1 + 0.2 * nz(co, 12))[:, None]
    return col

paint_part(hoses, paint_hoses)
set_mat(hoses, 'rubber')
parts.append(Part(hoses, allowed=['chest', 'arm_R_upper', 'arm_R_lower']))

# ------------------------------------------------------------------ assemble
radii = {'hips': 0.35, 'spine': 0.4, 'chest': 0.5, 'head': 0.14,
         'arm_R_upper': 0.27, 'arm_R_lower': 0.22, 'arm_R_hand': 0.25,
         'arm_L_upper': 0.06, 'arm_L_lower': 0.05,
         'leg_L_upper': 0.2, 'leg_L_lower': 0.17, 'leg_R_upper': 0.2, 'leg_R_lower': 0.17}
hauler = assemble('Hauler', parts, arm_ob, radii, power=5, smooth_iters=6)
finish_colors(hauler, ao_strength=0.7, ao_dist=0.35, cav_strength=0.7, grime=(0.6, 0.25), height=2.3)
print('TRIS', tri_count(hauler))
out = os.path.join(OUT_DIR, 'brute.glb')
export_glb([arm_ob, hauler], out)
glb_report(out)

if not NORENDER:
    render_studio('brute', 2.3, width_hint=2.0, extra_dist=1.15)
    render_game('brute', 2.3, zoom=8)
    rotate_bone_world(arm_ob, 'arm_R_upper', (1, 0, 0), 50)
    rotate_bone_world(arm_ob, 'arm_R_lower', (1, 0, 0), 40)
    rotate_bone_world(arm_ob, 'leg_L_upper', (1, 0, 0), -40)
    rotate_bone_world(arm_ob, 'leg_L_lower', (1, 0, 0), 60)
    rotate_bone_world(arm_ob, 'chest', (0, 0, 1), 25)
    rotate_bone_world(arm_ob, 'head', (0, 0, 1), 30)
    rotate_bone_world(arm_ob, 'arm_L_lower', (1, 0, 0), 30)
    render_studio('brute_deform', 2.3, width_hint=2.0, extra_dist=1.15)
