"""The Usher — stalker. 2.3 m, emaciated, porcelain egg-mask head. Faces -Y.
Run: /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/blender/humanoids/stalker.py
"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, hlib
importlib.reload(hlib)
from hlib import *

NORENDER = 'norender' in sys.argv
reset()
random.seed(7)

# ------------------------------------------------------------------ skeleton
HIP = V((0, 0.0, 1.12)); SP = V((0, 0.02, 1.26)); CH = V((0, 0.03, 1.55)); NK = V((0, -0.03, 1.86))
HD = V((-0.045, -0.115, 1.99)); HT = V((-0.135, -0.16, 2.225))
HEND = HT + (HT - HD).normalized() * 0.05


def arm_pts(s):
    S = V((0.2 * s, 0.0, 1.8))
    d = V((0.5 * s, 0, -0.866))
    E = S + d * 0.55 + V((0, 0.06, 0))
    W = E + d * 0.55 + V((0, -0.09, 0))
    hd = V((0.33 * s, -0.12, -0.94)).normalized()
    H = W + hd * 0.45
    return S, E, W, H, H + hd * 0.03, hd


def leg_pts(s):
    Hp = V((0.09 * s, 0.0, 1.12))
    K = V((0.13 * s, -0.14, 0.62))
    A = V((0.14 * s, 0.12, 0.17))
    B = V((0.14 * s, -0.08, 0.03))
    T = V((0.14 * s, -0.21, 0.012))
    return Hp, K, A, B, T


bones = [
    ('root', (0, 0, 0), (0, 0, 0.15), None, False, False),
    ('hips', HIP, SP, 'root', False, True),
    ('spine', SP, CH, 'hips', True, True),
    ('chest', CH, NK, 'spine', True, True),
    ('neck', NK, HD, 'chest', True, True),
    ('head', HD, HT, 'neck', True, True),
    ('head_end', HT, HEND, 'head', True, False),
]
for side, s in (('L', 1), ('R', -1)):
    S, E, W, H, End, hd = arm_pts(s)
    bones += [('arm_%s_upper' % side, S, E, 'chest', False, True),
              ('arm_%s_lower' % side, E, W, 'arm_%s_upper' % side, True, True),
              ('arm_%s_hand' % side, W, H, 'arm_%s_lower' % side, True, True),
              ('arm_%s_end' % side, H, End, 'arm_%s_hand' % side, True, False)]
    Hp, K, A, B, T = leg_pts(s)
    bones += [('leg_%s_upper' % side, Hp, K, 'hips', False, True),
              ('leg_%s_lower' % side, K, A, 'leg_%s_upper' % side, True, True),
              ('leg_%s_foot' % side, A, B, 'leg_%s_lower' % side, True, True),
              ('leg_%s_end' % side, B, T, 'leg_%s_foot' % side, True, False)]
arm_ob = build_armature('Usher_Rig', bones)
parts = []

# ------------------------------------------------------------------ body volumes (flesh)
el = [
    ('ell', (0, 0.0, 1.13), (0.095, 0.065, 0.07)),                      # tiny pelvis
    ('cap', (0, 0.0, 1.16), (0, 0.02, 1.42), 0.052),                     # wasted waist
    ('ell', (0, 0.015, 1.64), (0.13, 0.092, 0.2), (0.1, 0, 0)),          # ribcage
    ('cap', (-0.06, -0.02, 1.80), (0.06, -0.02, 1.80), 0.06),            # upper chest / trapezius
    ('cap', (0, 0.02, 1.81), (0, -0.03, 1.87), 0.055),
    ('cap', NK, HD + V((0, 0.0, 0.02)), 0.034),                          # neck
    ('cap', NK + V((0, 0.02, 0)), HD + V((0.0, 0.03, -0.02)), 0.03),
]
# vertebrae ridge
for k in range(18):
    t = k / 17
    p = V((0, 0.055, 1.18)).lerp(V((0, 0.085, 1.82)), t)
    p.y += 0.035 * math.sin(t * math.pi) - 0.0
    el.append(('ball', p, 0.022 if k % 2 == 0 else 0.017))
for k in range(4):                                                         # neck vertebrae
    el.append(('ball', NK.lerp(HD, k / 4) + V((0, 0.03, 0)), 0.016))
# ribs: arcs from the spine around the ribcage
for k in range(7):
    z = 1.76 - k * 0.045
    rx = 0.13 * math.sqrt(max(0.15, 1 - ((z - 1.64) / 0.2) ** 2))
    for s in (1, -1):
        pts = []
        for a in np.linspace(0.35, 2.55, 6):
            pts.append(V((s * math.sin(a) * (rx + 0.004), 0.015 + math.cos(a) * 0.094, z - 0.05 * (a / 2.6))))
        for i in range(len(pts) - 1):
            el.append(('cap', pts[i], pts[i + 1], 0.0115))
for s in (1, -1):
    el += [('ell', (0.085 * s, 0.075, 1.71), (0.055, 0.022, 0.07), (0.25, 0, 0.3 * s)),   # shoulder blades
           ('cap', (0.02 * s, -0.04, 1.83), (0.2 * s, -0.01, 1.82), 0.026),              # clavicle
           ('ell', (0.06 * s, 0.0, 1.06), (0.04, 0.05, 0.045))]                            # hip bones
    S, E, W, H, End, hd = arm_pts(s)
    el += [('ball', S, 0.05), ('cap', S, E, 0.033), ('cap', S, S.lerp(E, 0.35), 0.04), ('ball', E, 0.038), ('cap', E, W, 0.027),
           ('cap', E + V((0, 0.01, 0)), E.lerp(W, 0.4), 0.03),
           ('ball', W, 0.026)]
    # palm
    el.append(('cap', W + hd * 0.01, W + hd * 0.09, 0.022))
    Hp, K, A, B, T = leg_pts(s)
    el += [('cap', Hp, K, 0.038), ('cap', Hp + V((0, 0.0, -0.02)), Hp.lerp(K, 0.45), 0.044),
           ('ball', K, 0.042), ('cap', K, A, 0.028), ('cap', K, K.lerp(A, 0.35), 0.033),
           ('ball', A, 0.033), ('cap', A, B, 0.026)]
    for k, ang in enumerate((-0.35, 0.0, 0.35)):       # three long toes
        dirv = V((math.sin(ang) * s * 0.6, -math.cos(ang), -0.08)).normalized()
        el.append(('cap', B, B + dirv * 0.12, 0.016))

body = metaball('Body', el, res=0.008)
remesh(body, 0.006, smooth_iter=4, smooth_fac=0.5)

# ---- cloth wrapping function (helical bands per body segment)
WRAPS = []   # (A, B, pitch, duty, slant, phase)
WRAPS.append((V((0, 0.0, 1.0)), V((0, -0.02, 1.9)), 0.13, 0.86, 1.6, 0.0))
WRAPS.append((NK, HD, 0.07, 0.6, 1.5, 0.3))
for s in (1, -1):
    S, E, W, H, End, hd = arm_pts(s)
    WRAPS.append((S - (E - S).normalized() * 0.06, E, 0.11, 0.86, 1.8 * s, 0.2))
    WRAPS.append((E, W, 0.1, 0.68, -1.7 * s, 0.5))
    WRAPS.append((W, W + hd * 0.1, 0.05, 0.0, 1.0, 0.0))
    Hp, K, A, B, T = leg_pts(s)
    WRAPS.append((Hp + V((0, 0, 0.05)), K, 0.12, 0.86, -1.6 * s, 0.1))
    WRAPS.append((K, A, 0.1, 0.7, 1.8 * s, 0.7))
    WRAPS.append((A, T, 0.07, 0.3, 1.5, 0.0))


def wrap_value(co):
    """Returns (cloth mask bool array, band coordinate) for points."""
    best = np.full(len(co), 1e9); hval = np.zeros(len(co)); duty = np.zeros(len(co))
    for (A, B, pitch, du, slant, ph) in WRAPS:
        a = np.array(A); b = np.array(B)
        d, t = seg_dist(co, a, b)
        L = np.linalg.norm(b - a)
        ax = (b - a) / L
        ref = np.cross(ax, [0, 1, 0]) if abs(ax[1]) < 0.9 else np.cross(ax, [1, 0, 0])
        ref /= np.linalg.norm(ref); ref2 = np.cross(ax, ref)
        rel = co - a
        theta = np.arctan2(rel @ ref2, rel @ ref)
        h = (t * L) / pitch + slant * theta / (2 * np.pi) + ph
        m = d < best
        best[m] = d[m]; hval[m] = h[m]; duty[m] = du
    wob = nz(co, 3.5, (2, 7, 1)) * 0.45                       # bands wander
    rag = nz(co, 45, (3, 1, 4)) * 0.08 + nz(co, 13, (9, 2, 2)) * 0.12
    hh = hval + wob + rag
    idx = np.floor(hh)
    var = 0.75 + 0.35 * np.mod(np.sin(idx * 12.9898) * 43758.5453, 1.0)   # per-band width variation
    fr = np.mod(hh, 1.0)
    cloth = fr < duty * var
    # second, crossing wrap on the torso and shoulders (crisscross binding)
    torso = (co[:, 2] > 1.0) & (co[:, 2] < 1.9) & (np.abs(co[:, 0]) < 0.24)
    th = np.arctan2(co[:, 1] - 0.01, co[:, 0])
    h2 = co[:, 2] / 0.16 - th / (2 * np.pi) * 1.4 + rag + wob
    cloth |= torso & (np.mod(h2, 1.0) < 0.35)
    # torn holes
    tear = nz(co, 6, (11, 3, 5)) > 0.48
    cloth &= ~tear
    # exposed spine ridge down the back and a torn chest window showing ribs
    spine = (np.abs(co[:, 0]) < 0.028 + 0.01 * nz(co, 20, (1, 1, 1))) & (co[:, 1] > 0.04) & (co[:, 2] > 1.15) & (co[:, 2] < 1.84)
    ribwin = (np.linalg.norm((co - np.array([0.07, -0.06, 1.6])) * np.array([1, 1, 0.7]), axis=1) < 0.075 + 0.015 * nz(co, 25, (5, 5, 5)))
    cloth &= ~(spine | ribwin)
    return cloth, fr


co = get_co(body)
cl, fr = wrap_value(co)
nr = get_normals(body)
lift = np.where(cl, 0.005, 0.0) * (1 + 0.4 * nz(co, 30, (2, 2, 2)))
set_co(body, co + nr * lift[:, None])
smooth(body, 1, 0.35)
displace_noise(body, [(16, 0.003), (55, 0.0012)])
decimate(body, 5600)
shade_smooth(body)

# assign materials per face: flesh / cloth
body.data.materials.clear()
body.data.materials.append(get_mat('flesh')); body.data.materials.append(get_mat('cloth'))
body.data.update()
fc = np.array([p.center[:] for p in body.data.polygons])
fcl, _ = wrap_value(fc)
body.data.polygons.foreach_set('material_index', fcl.astype(np.int32))


def paint_body(co, nr, mats, vidx):
    vco = get_co(body)
    n = len(co)
    big = nz(vco, 5, (1, 1, 1), 2)[vidx]
    mid = nz(vco, 18, (4, 4, 4))[vidx]
    veins = np.abs(nz(vco, 14, (8, 2, 6), 2))[vidx]
    flesh = np.tile(np.array([0.47, 0.48, 0.48]), (n, 1))
    flesh *= (1 + 0.08 * big + 0.05 * mid)[:, None]
    flesh = lerp(flesh, np.array([0.42, 0.34, 0.40]), 0.6 * smoothstep(0.15, 0.55, big))     # bruising
    flesh = lerp(flesh, np.array([0.30, 0.34, 0.44]), 0.7 * (1 - smoothstep(0.0, 0.06, veins)))  # veins
    # joints and finger roots reddened / dirty
    knob = np.zeros(n)
    for s in (1, -1):
        S, E, W, H, End, hd = arm_pts(s)
        Hp, K, A, B, T = leg_pts(s)
        for P, r in ((E, 0.06), (W, 0.07), (K, 0.07), (A, 0.06)):
            knob = np.maximum(knob, 1 - smoothstep(0.0, r, np.linalg.norm(co - np.array(P), axis=1)))
    flesh = lerp(flesh, np.array([0.5, 0.38, 0.38]), 0.5 * knob)
    cloth = np.tile(np.array([0.095, 0.105, 0.13]), (n, 1))
    cloth *= (1 + 0.25 * mid + 0.15 * big)[:, None]
    # dust on upward faces, frayed lighter edges
    cloth = lerp(cloth, np.array([0.22, 0.22, 0.23]), 0.5 * np.clip(nr[:, 2], 0, 1) * smoothstep(0.0, 0.5, nz(vco, 25, (7, 1, 1))[vidx] + 0.3))
    col = np.where((mats == 'cloth')[:, None], cloth, flesh)
    # grime toward the ground (feet & shins dirtier)
    gr = 1 - smoothstep(0.0, 0.5, co[:, 2])
    col = lerp(col, np.array([0.2, 0.18, 0.16]), 0.55 * gr)
    return col

paint_part(body, paint_body)
parts.append(Part(body))

# ------------------------------------------------------------------ needle fingers (flesh, rigid to hand)
bm = bmesh.new()
for s in (1, -1):
    S, E, W, H, End, hd = arm_pts(s)
    base = W + hd * 0.09
    side = hd.cross(V((0, 1, 0))).normalized()
    fwd = hd.cross(side).normalized()
    for k, (spread, ln, fw) in enumerate(((-0.42, 0.33, 0.1), (-0.13, 0.36, 0.22), (0.15, 0.35, 0.22), (0.45, 0.31, 0.05))):
        dirv = (hd * math.cos(spread) + side * math.sin(spread) + fwd * fw * -1).normalized()
        k0 = base + side * (spread * 0.04)
        k1 = k0 + dirv * ln * 0.42
        d2 = (dirv + fwd * -0.12 + V((0, 0, -0.05))).normalized()
        k2 = k1 + d2 * ln * 0.58
        bm_cyl(bm, k0, k1, 0.0105, 0.008, seg=6)
        bm_sphere(bm, k1, 0.0095, u=6, v=4)
        bm_cyl(bm, k1, k2, 0.0078, 0.0012, seg=6, caps=False)
        bm_sphere(bm, k0, 0.012, u=6, v=4)
fing = mesh_from_bm(bm, 'Fingers')
shade_smooth(fing)


def paint_fing(co, nr, m, v):
    col = np.tile(np.array([0.6, 0.6, 0.58]), (len(co), 1))
    tipness = np.zeros(len(co))
    for s in (1, -1):
        S, E, W, H, End, hd = arm_pts(s)
        t = np.clip(((co - np.array(W)) @ np.array(hd)) / 0.45, 0, 1)
        sel = (co[:, 0] * s) > 0
        tipness[sel] = t[sel]
    col = lerp(col, np.array([0.18, 0.16, 0.16]), smoothstep(0.65, 1.0, tipness))   # blackened needle tips
    return col

paint_part(fing, paint_fing)
set_mat(fing, 'flesh')
parts.append(Part(fing, bone=None, allowed=None))
fing_part = parts[-1]
# rigid per side: split assignment by side using allowed bones
fing_part.allowed = None

# ------------------------------------------------------------------ hanging tatters (cloth, double sided)
body.data.update()
bvh = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())


def tatter(bm, start, dirv, length, w0, w1, nseg=9, sway=0.03, twist=0.4):
    loc, n, i, d = bvh.find_nearest(V(start))
    start = loc + n * 0.006
    dirv = V(dirv).normalized()
    side = dirv.cross(n).normalized()
    left, right = [], []
    for k in range(nseg + 1):
        t = k / nseg
        p = start + dirv * (length * t) + n * (0.02 * t) + side * (sway * math.sin(t * 5 + length * 9))
        w = (w0 * (1 - t) + w1 * t) * (1 + 0.25 * math.sin(k * 2.3 + w0 * 50))
        sd = (side * math.cos(twist * t) + n * math.sin(twist * t)).normalized()
        left.append(p - sd * w / 2); right.append(p + sd * w / 2)
    # ragged tip: drop last right vertex a bit
    right[-1] = right[-1] - dirv * 0.04
    for off, flip in ((0.0, False), (0.0018, True)):
        L = [bm.verts.new(p + n * off) for p in left]; R = [bm.verts.new(p + n * off) for p in right]
        for k in range(nseg):
            f = (L[k], R[k], R[k + 1], L[k + 1])
            bm.faces.new(tuple(reversed(f)) if flip else f)


bmT = bmesh.new()
T_HIPS, T_ARM = [], []
groups = {}


def add_group(name, fn):
    before = len(bmT.verts)
    fn()
    groups.setdefault(name, []).append((before, len(bmT.verts)))


# waist strips (loincloth-like rags), front and back
for k, (x, y) in enumerate(((-0.06, -0.08), (0.04, -0.085), (0.09, -0.02), (-0.09, 0.04), (0.0, 0.08), (0.07, 0.07))):
    add_group('waist', lambda x=x, y=y, k=k: tatter(bmT, (x, y, 1.1), (x * 0.6, y * 0.6, -1), 0.38 + 0.12 * (k % 3), 0.06, 0.025))
# shoulder / back strips trailing down the back
for k, x in enumerate((-0.11, -0.03, 0.08)):
    add_group('back', lambda x=x, k=k: tatter(bmT, (x, 0.1, 1.76), (x * 0.4, 0.25, -1), 0.45 + 0.1 * k, 0.07, 0.03, twist=0.2))
# arm strips hanging from elbows and wrists
for s in (1, -1):
    S, E, W, H, End, hd = arm_pts(s)
    side = 'L' if s > 0 else 'R'
    add_group('arm_' + side, lambda E=E, s=s: tatter(bmT, E + V((0, 0.02, -0.02)), (0.1 * s, 0.1, -1), 0.32, 0.05, 0.02))
    add_group('fore_' + side, lambda W=W, E=E, s=s: tatter(bmT, E.lerp(W, 0.75) + V((0, 0.0, 0)), (0.15 * s, 0.05, -1), 0.28, 0.04, 0.015))
    add_group('shoulder_' + side, lambda S=S, s=s: tatter(bmT, S + V((0.0, 0.04, 0.02)), (0.3 * s, 0.4, -1), 0.3, 0.06, 0.02))
tat = mesh_from_bm(bmT, 'Tatters')
shade_smooth(tat)
paint_part(tat, lambda co, nr, m, v: np.tile(np.array([0.1, 0.11, 0.135]), (len(co), 1)) * (1 + 0.35 * nz(co, 20, (1, 5, 2)))[:, None] * (0.75 + 0.35 * smoothstep(0.2, 1.4, co[:, 2]))[:, None])
set_mat(tat, 'cloth')

# split tatters into weighting groups (separate parts for allowed bone sets)
def split_part(src, ranges, allowed):
    bm = bmesh.new(); bm.from_mesh(src.data)
    bm.verts.ensure_lookup_table()
    keep = set()
    for a, b in ranges:
        keep.update(range(a, b))
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context='VERTS')
    me = bpy.data.meshes.new(src.name + '_' + allowed[0])
    bm.to_mesh(me); bm.free()
    for m in src.data.materials:
        me.materials.append(m)
    ob = link(bpy.data.objects.new(me.name, me))
    return ob

ALLOW = {
    'waist': ['hips', 'leg_L_upper', 'leg_R_upper'],
    'back': ['chest', 'spine'],
    'arm_L': ['arm_L_upper', 'arm_L_lower'], 'arm_R': ['arm_R_upper', 'arm_R_lower'],
    'fore_L': ['arm_L_lower'], 'fore_R': ['arm_R_lower'],
    'shoulder_L': ['arm_L_upper', 'chest'], 'shoulder_R': ['arm_R_upper', 'chest'],
}
for gname, ranges in groups.items():
    ob = split_part(tat, ranges, ALLOW[gname])
    parts.append(Part(ob, allowed=ALLOW[gname]))
bpy.data.objects.remove(tat)

# fingers: split per side so they can be rigid to each hand
fco = get_co(fing)
bm = bmesh.new(); bm.from_mesh(fing.data); bm.verts.ensure_lookup_table()
parts.remove(fing_part)
for side, s in (('L', 1), ('R', -1)):
    b2 = bm.copy(); b2.verts.ensure_lookup_table()
    bmesh.ops.delete(b2, geom=[v for v in b2.verts if v.co.x * s < 0], context='VERTS')
    me = bpy.data.meshes.new('Fing' + side); b2.to_mesh(me); b2.free()
    me.materials.append(get_mat('flesh'))
    ob = link(bpy.data.objects.new('Fing' + side, me))
    parts.append(Part(ob, bone='arm_%s_hand' % side))
bm.free()
bpy.data.objects.remove(fing)

# ------------------------------------------------------------------ porcelain egg head
hz = (HT - HD).normalized()
hy = (V((0, 1, 0)) - hz * hz.y).normalized()
hx = hy.cross(hz)
HM = Matrix((hx, hy, hz)).transposed()          # local -> world rotation
EC = HD + hz * 0.145                             # egg centre
EA, EB, EC_ = 0.135, 0.15, 0.175                 # semi axes x, y(depth), z(height)


def egg_local(theta, phi, scale=1.0):
    z = math.cos(phi)
    k = 1 + 0.13 * z
    # slightly flattened face plane on the front (-y)
    y = EB * k * math.sin(phi) * math.sin(theta)
    if y < 0:
        y *= 0.9
    return V((EA * k * math.sin(phi) * math.cos(theta), y, EC_ * z)) * scale


def egg_world(theta, phi, scale=1.0):
    return EC + HM @ egg_local(theta, phi, scale)


def make_egg(bm, scale, flip, U=34, Vn=22):
    top = bm.verts.new(egg_world(0, 0, scale)); bot = bm.verts.new(egg_world(0, math.pi, scale))
    rows = []
    for j in range(1, Vn):
        phi = math.pi * j / Vn
        rows.append([bm.verts.new(egg_world(2 * math.pi * i / U, phi, scale)) for i in range(U)])
    fs = []
    for i in range(U):
        fs.append((top, rows[0][i], rows[0][(i + 1) % U]))
        fs.append((bot, rows[-1][(i + 1) % U], rows[-1][i]))
    for j in range(len(rows) - 1):
        for i in range(U):
            fs.append((rows[j][i], rows[j + 1][i], rows[j + 1][(i + 1) % U], rows[j][(i + 1) % U]))
    for f in fs:
        f = tuple(reversed(f)) if not flip else f
        bm.faces.new(f)


bm = bmesh.new()
make_egg(bm, 1.0, False)
make_egg(bm, 0.93, True, 22, 14)
bm.normal_update()
egg = mesh_from_bm(bm, 'Egg')
# ensure outward normals on outer shell
bm = bmesh.new(); bm.from_mesh(egg.data)
c = np.array(EC)
for f in bm.faces:
    out = (f.calc_center_median() - EC).dot(f.normal) > 0
    rad = (f.calc_center_median() - EC).length
    # outer shell faces should point out, inner shell faces in
    pass
bm.free()

# cutters
EYE_L = (0.048, 0.035, 0.03, 0.0)       # local x, z, radius, vertical stretch tilt
EYE_R = (-0.045, 0.004, 0.019, 0.3)
cutters = []


def cutter_eye(lx, lz, r, tilt, stretch):
    bmc = bmesh.new()
    a = V((lx, -0.05, lz)); b = V((lx, -0.25, lz))
    vs = bm_cyl(bmc, a, b, r, seg=16)
    for v in vs:
        p = v.co.copy()
        p.z = lz + (p.z - lz) * stretch
        p.x = lx + (p.x - lx) + (p.z - lz) * tilt
        v.co = EC + HM @ p
    ob = mesh_from_bm(bmc, 'cut_eye')
    cutters.append(ob)


cutter_eye(*EYE_L[:3], 0.0, 1.15)
cutter_eye(*EYE_R[:3], 0.35, 1.7)
# shard at the top, slightly back and to its left
SH_C = V((0.035, 0.03, 0.0))
bmc = bmesh.new()
poly = []
for k in range(11):
    a = 2 * math.pi * k / 11
    r = 0.05 * (0.6 + 0.6 * ((k * 7) % 5) / 4)
    poly.append(V((SH_C.x + math.cos(a) * r, SH_C.y + math.sin(a) * r * 0.8)))
lo = [bmc.verts.new(EC + HM @ V((p.x, p.y, 0.1))) for p in poly]
hi = [bmc.verts.new(EC + HM @ V((p.x, p.y, 0.3))) for p in poly]
bmc.faces.new(list(reversed(lo))); bmc.faces.new(hi)
for k in range(len(poly)):
    bmc.faces.new((lo[k], lo[(k + 1) % len(poly)], hi[(k + 1) % len(poly)], hi[k]))
cutters.append(mesh_from_bm(bmc, 'cut_shard'))

for ct in cutters:
    m = egg.modifiers.new('bool', 'BOOLEAN')
    m.operation = 'DIFFERENCE'
    m.object = ct
    try:
        m.solver = 'EXACT'
    except Exception:
        pass
apply_mods(egg)
egg.data.materials.clear()
for ct in cutters:
    bpy.data.objects.remove(ct)
shade_smooth(egg, sharp_angle=55)
print('EGG tris', tri_count(egg))


def paint_egg(co, nr, mats, vidx):
    rel = (co - np.array(EC)) @ np.array(HM)          # world -> local (HM orthonormal)
    # radial position relative to the outer surface
    vco = get_co(egg)
    n = len(co)
    base = np.array([0.78, 0.76, 0.70])
    col = np.tile(base, (n, 1))
    col *= (1 + 0.03 * nz(vco, 12, (3, 3, 3))[vidx])[:, None]
    # inner surface / void = near black
    nrl = nr @ np.array(HM)
    outward = np.einsum('ij,ij->i', rel / (np.linalg.norm(rel, axis=1, keepdims=True) + 1e-9), nrl)
    rr = np.sqrt((rel[:, 0] / EA) ** 2 + (rel[:, 1] / EB) ** 2 + (rel[:, 2] / EC_) ** 2)
    inner = (outward < -0.2)
    col[inner] = (0.025, 0.022, 0.025)
    rim = (~inner) & (np.abs(outward) <= 0.5)
    col[rim] = (0.55, 0.5, 0.44)                       # raw biscuit at broken edges
    # tear streaks below the eye holes, grime in the lower half
    for (lx, lz, r) in (EYE_L[:3], EYE_R[:3]):
        dx = np.abs(rel[:, 0] - lx - 0.004 * np.sin(rel[:, 2] * 80))
        below = (rel[:, 2] < lz) & (rel[:, 1] < 0)
        streak = (1 - smoothstep(0.004, 0.014, dx)) * below * (1 - smoothstep(0.0, 0.12, lz - rel[:, 2]))
        col = lerp(col, np.array([0.28, 0.24, 0.22]), 0.8 * streak)
    low = 1 - smoothstep(-0.16, 0.0, rel[:, 2])
    col = lerp(col, np.array([0.5, 0.46, 0.4]), 0.5 * low * (~inner))
    return col

paint_part(egg, paint_egg)
set_mat(egg, 'porcelain')
parts.append(Part(egg, bone='head'))

# hairline cracks as thin decal ribbons on the egg surface
bm = bmesh.new()
egg.data.update()
ebvh = BVHTree.FromObject(egg, bpy.context.evaluated_depsgraph_get())


def to_angles(lp):
    x, y, z = lp.x / EA, lp.y / EB, lp.z / EC_
    phi = math.acos(max(-1, min(1, z / max(1e-6, math.sqrt(x * x + y * y + z * z)))))
    return math.atan2(y, x), phi


def crack(theta, phi, heading, steps, depth=0):
    pts = []
    for k in range(steps):
        p = egg_world(theta, phi, 1.0)
        loc, n, i, d = ebvh.find_nearest(p)
        if d is None or d > 0.006:
            break
        pts.append((loc + n * 0.0012, n))
        heading += random.uniform(-0.6, 0.6)
        theta += math.cos(heading) * 0.085 / max(0.25, math.sin(phi))
        phi += math.sin(heading) * 0.085
        if depth < 2 and random.random() < 0.18:
            crack(theta, phi, heading + random.choice((-1, 1)) * random.uniform(0.6, 1.1), steps // 2, depth + 1)
    if len(pts) < 2:
        return
    L, R = [], []
    for k, (p, n) in enumerate(pts):
        a = pts[max(k - 1, 0)][0]; b = pts[min(k + 1, len(pts) - 1)][0]
        t = (b - a).normalized()
        sd = t.cross(n).normalized()
        w = 0.0032 * (1 - 0.7 * k / len(pts)) * (1 if depth == 0 else 0.7)
        L.append(bm.verts.new(p - sd * w)); R.append(bm.verts.new(p + sd * w))
    for k in range(len(pts) - 1):
        bm.faces.new((L[k], R[k], R[k + 1], L[k + 1]))


# start cracks at the shard rim and eye holes
sh_th, sh_ph = to_angles(V((SH_C.x, SH_C.y, EC_)))
for k in range(5):
    a = 2 * math.pi * k / 5 + 0.4
    crack(sh_th + math.cos(a) * 0.9, sh_ph + 0.38 + 0.1 * math.sin(a), a + (math.pi / 2 if k % 2 else 0) + 1.3, 14)
for (lx, lz, r) in (EYE_L[:3], EYE_R[:3]):
    th, ph = to_angles(V((lx, -EB, lz)))
    crack(th, ph - 0.25, -1.4, 10)
    crack(th + 0.25, ph + 0.15, 0.4, 8)
cr = mesh_from_bm(bm, 'Cracks')
shade_smooth(cr)
paint_part(cr, lambda co, nr, m, v: np.tile(np.array([0.06, 0.05, 0.05]), (len(co), 1)))
set_mat(cr, 'porcelain')
parts.append(Part(cr, bone='head'))

# ------------------------------------------------------------------ assemble
radii = {'hips': 0.1, 'spine': 0.1, 'chest': 0.13, 'neck': 0.045, 'head': 0.12,
         'arm_L_upper': 0.04, 'arm_L_lower': 0.035, 'arm_L_hand': 0.03,
         'arm_R_upper': 0.04, 'arm_R_lower': 0.035, 'arm_R_hand': 0.03,
         'leg_L_upper': 0.05, 'leg_L_lower': 0.04, 'leg_L_foot': 0.035,
         'leg_R_upper': 0.05, 'leg_R_lower': 0.04, 'leg_R_foot': 0.035}
usher = assemble('Usher', parts, arm_ob, radii, power=5, smooth_iters=5)
finish_colors(usher, ao_strength=0.6, ao_dist=0.12, cav_strength=0.55, grime=(0.7, 0.2), height=2.3)
print('TRIS', tri_count(usher))
out = os.path.join(OUT_DIR, 'stalker.glb')
export_glb([arm_ob, usher], out)
glb_report(out)

if not NORENDER:
    render_studio('stalker', 2.3, width_hint=1.9)
    render_game('stalker', 2.3, zoom=8)
    rotate_bone_world(arm_ob, 'leg_L_lower', (1, 0, 0), 60)
    rotate_bone_world(arm_ob, 'leg_R_upper', (1, 0, 0), -45)
    rotate_bone_world(arm_ob, 'arm_R_upper', (0, 1, 0), 90)
    rotate_bone_world(arm_ob, 'arm_L_lower', (1, 0, 0), -70)
    rotate_bone_world(arm_ob, 'chest', (0, 0, 1), 30)
    rotate_bone_world(arm_ob, 'neck', (0, 1, 0), 25)
    render_studio('stalker_deform', 2.3, width_hint=1.9)
