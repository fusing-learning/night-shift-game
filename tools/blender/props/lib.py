"""Prop-building helpers (bmesh based). Units metres, Blender Z up."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, Euler

PL = 'metal_plate'; RU = 'metal_rust'; DK = 'metal_dark'; BA = 'metal_bare'
YE = 'metal_yellow'; RD = 'metal_red'; RB = 'rubber'; BE = 'belt'; CO = 'concrete'
WO = 'wood'; GL = 'glass'; CL = 'cloth'; SC = 'screen'
GW = 'glow_white'; GR = 'glow_red'; GA = 'glow_amber'; GC = 'glow_cyan'
GG = 'glow_green'; GF = 'glow_furnace'

# name: (colour, metallic, roughness, emission strength)
MAT_DEFS = {
    PL: ((0.10, 0.16, 0.22), 0.7, 0.55, 0), RU: ((0.30, 0.13, 0.06), 0.5, 0.8, 0),
    DK: ((0.025, 0.027, 0.032), 0.8, 0.5, 0), BA: ((0.55, 0.56, 0.58), 1.0, 0.35, 0),
    YE: ((0.75, 0.52, 0.03), 0.3, 0.6, 0), RD: ((0.45, 0.04, 0.03), 0.3, 0.55, 0),
    RB: ((0.015, 0.015, 0.016), 0.0, 0.85, 0), BE: ((0.04, 0.04, 0.045), 0.0, 0.9, 0),
    CO: ((0.25, 0.25, 0.24), 0.0, 0.95, 0), WO: ((0.30, 0.17, 0.07), 0.0, 0.85, 0),
    GL: ((0.25, 0.35, 0.35), 0.0, 0.2, 0), CL: ((0.17, 0.19, 0.12), 0.0, 0.95, 0),
    SC: ((0.05, 0.6, 0.15), 0.0, 0.3, 1.5), GW: ((1, 1, 0.9), 0, 0.3, 6),
    GR: ((1, 0.05, 0.03), 0, 0.3, 6), GA: ((1, 0.45, 0.03), 0, 0.3, 6),
    GC: ((0.1, 0.8, 1), 0, 0.3, 6), GG: ((0.1, 1, 0.2), 0, 0.3, 6),
    GF: ((1, 0.28, 0.03), 0, 0.3, 8),
}


def get_mat(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    col, met, rough, em = MAT_DEFS[name]
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Metallic'].default_value = met
    b.inputs['Roughness'].default_value = rough
    if em > 0:
        b.inputs['Emission Color'].default_value = (*col, 1)
        b.inputs['Emission Strength'].default_value = em
    return m


REG = {}


def prop(name):
    def deco(f):
        REG[name] = f
        return f
    return deco


def catmull(pts, n=8, closed=False):
    pts = [Vector(p) for p in pts]
    out = []
    N = len(pts)
    rng = range(N) if closed else range(N - 1)
    for i in rng:
        p0 = pts[(i - 1) % N] if (closed or i > 0) else pts[0] * 2 - pts[1]
        p1 = pts[i]
        p2 = pts[(i + 1) % N]
        p3 = pts[(i + 2) % N] if (closed or i + 2 < N) else pts[-1] * 2 - pts[-2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(pts[-1])
    return out


def R(rx=0, ry=0, rz=0):
    return Euler((math.radians(rx), math.radians(ry), math.radians(rz)), 'XYZ').to_matrix().to_4x4()


AXM = {'z': Matrix.Identity(4), 'x': Matrix.Rotation(math.radians(90), 4, 'Y'),
       'y': Matrix.Rotation(math.radians(-90), 4, 'X')}


class Prop:
    def __init__(s, name, parent=None, pivot=(0, 0, 0)):
        s.name = name
        s.bm = bmesh.new()
        s.mats = []
        s.children = []
        s.parent = parent
        s.pivot = Vector(pivot)
        s.uvfn = None

    def child(s, name, pivot):
        c = Prop(name, s, pivot)
        s.children.append(c)
        return c

    def mi(s, m):
        if m not in s.mats:
            s.mats.append(m)
        return s.mats.index(m)

    # ---------------------------------------------------------------- merge
    def _merge(s, tmp, m, M=None):
        if M is not None:
            bmesh.ops.transform(tmp, matrix=M, verts=tmp.verts)
        mi = s.mi(m)
        bm = s.bm
        vm = {v: bm.verts.new(v.co) for v in tmp.verts}
        for f in tmp.faces:
            try:
                nf = bm.faces.new([vm[v] for v in f.verts])
            except ValueError:
                continue
            nf.material_index = mi
            nf.smooth = True
        tmp.free()

    @staticmethod
    def _bevel(tmp, edges, w, seg=1):
        if w > 0.002 and edges:
            bmesh.ops.bevel(tmp, geom=edges, offset=w, segments=seg, profile=0.5, affect='EDGES', clamp_overlap=True)

    # ---------------------------------------------------------- primitives
    def box(s, c, sz, m=PL, rot=(0, 0, 0), bev=None, seg=1):
        tmp = bmesh.new()
        bmesh.ops.create_cube(tmp, size=1.0)
        bmesh.ops.scale(tmp, vec=Vector(sz), verts=tmp.verts)
        w = min(0.012, min(sz) * 0.3) if bev is None else bev
        if min(sz) < 0.04:
            w = 0
        if seg > 1 and min(sz) < 0.3:
            seg = 1
        s._bevel(tmp, list(tmp.edges), w, seg)
        s._merge(tmp, m, Matrix.Translation(c) @ R(*rot))

    def cyl(s, c, r, h, axis='z', m=PL, seg=16, r2=None, bev=None, rot=(0, 0, 0), sc=(1, 1, 1), caps=True, bottom=True):
        seg = max(6, min(seg, int(8 + max(r, r2 or 0) * 40)))
        tmp = bmesh.new()
        bmesh.ops.create_cone(tmp, cap_ends=caps, cap_tris=False, segments=seg, radius1=r,
                              radius2=r if r2 is None else r2, depth=h)
        w = min(0.008, r * 0.25, h * 0.25) if bev is None else bev
        if r < 0.045 or h < 0.04:
            w = 0
        if caps and not bottom:
            bf = [f for f in tmp.faces if f.normal.z < -0.99]
            bmesh.ops.delete(tmp, geom=bf, context='FACES_ONLY')
        if caps and bottom and w > 0.002:
            ed = [e for e in tmp.edges if abs(abs(e.verts[0].co.z) - h / 2) < 1e-5 and abs(abs(e.verts[1].co.z) - h / 2) < 1e-5
                  and abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-5]
            s._bevel(tmp, ed, w, 1)
        if sc != (1, 1, 1):
            for v in tmp.verts:
                v.co = Vector((v.co.x * sc[0], v.co.y * sc[1], v.co.z * sc[2]))
        s._merge(tmp, m, Matrix.Translation(c) @ R(*rot) @ AXM[axis])

    def sphere(s, c, r, m=PL, sc=(1, 1, 1), seg=12, rings=8, half=False, rot=(0, 0, 0)):
        tmp = bmesh.new()
        bmesh.ops.create_uvsphere(tmp, u_segments=seg, v_segments=rings, radius=r)
        if half:
            bmesh.ops.delete(tmp, geom=[v for v in tmp.verts if v.co.z < -1e-4], context='VERTS')
        for v in tmp.verts:
            v.co = Vector((v.co.x * sc[0], v.co.y * sc[1], v.co.z * sc[2]))
        s._merge(tmp, m, Matrix.Translation(c) @ R(*rot))

    def torus(s, c, R_, r, axis='z', m=PL, seg=16, rseg=6, sc=(1, 1, 1), rot=(0, 0, 0)):
        seg = max(8, min(seg, int(8 + R_ * 40)))
        rseg = 4 if r < 0.03 else min(rseg, 5)
        tmp = bmesh.new()
        V = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            row = []
            for j in range(rseg):
                b = 2 * math.pi * j / rseg
                rr = R_ + r * math.cos(b)
                row.append(tmp.verts.new((rr * math.cos(a) * sc[0], rr * math.sin(a) * sc[1], r * math.sin(b) * sc[2])))
            V.append(row)
        for i in range(seg):
            for j in range(rseg):
                tmp.faces.new([V[i][j], V[(i + 1) % seg][j], V[(i + 1) % seg][(j + 1) % rseg], V[i][(j + 1) % rseg]])
        s._merge(tmp, m, Matrix.Translation(c) @ R(*rot) @ AXM[axis])

    def band(s, c, r, axis='z', m=DK, seg=24, w=0.05, h=0.014):
        """Weld-bead ridge wrapped around a cylinder of radius r (2 faces per segment)."""
        s.lathe([(r, -w / 2), (r + h, 0), (r, w / 2)], c=c, axis=axis, m=m, seg=seg)

    def tube(s, pts, r, m=RB, seg=8, caps=True, radii=None):
        pts = [Vector(p) for p in pts]
        n = len(pts)
        if n < 2:
            return
        seg = max(6, min(seg, int(7 + r * 60)))
        tan = []
        for i in range(n):
            a = pts[max(i - 1, 0)]
            b = pts[min(i + 1, n - 1)]
            t = (b - a)
            tan.append(t.normalized() if t.length > 1e-9 else Vector((1, 0, 0)))
        up = Vector((0, 0, 1)) if abs(tan[0].z) < 0.9 else Vector((1, 0, 0))
        nrm = tan[0].cross(up).normalized()
        tmp = bmesh.new()
        rings = []
        for i in range(n):
            if i > 0:
                nrm = nrm - tan[i] * nrm.dot(tan[i])
                if nrm.length < 1e-6:
                    nrm = tan[i].orthogonal()
                nrm.normalize()
            bn = tan[i].cross(nrm)
            rr = r if radii is None else radii[i]
            ring = [tmp.verts.new(pts[i] + (nrm * math.cos(2 * math.pi * j / seg) + bn * math.sin(2 * math.pi * j / seg)) * rr)
                    for j in range(seg)]
            rings.append(ring)
        # nrm x bn = tan  -> ring ccw about tan
        for i in range(n - 1):
            for j in range(seg):
                k = (j + 1) % seg
                try:
                    tmp.faces.new([rings[i][j], rings[i][k], rings[i + 1][k], rings[i + 1][j]])
                except ValueError:
                    pass
        if caps:
            tmp.faces.new(rings[0][::-1])
            tmp.faces.new(rings[-1])
        s._merge(tmp, m)

    def lathe(s, prof, c=(0, 0, 0), axis='z', m=PL, seg=24, rot=(0, 0, 0), close=False, sc=(1, 1, 1)):
        seg = max(8, min(seg, int(8 + max(p[0] for p in prof) * 40)))
        tmp = bmesh.new()
        pts = list(prof) + ([prof[0]] if close else [])
        rings = []
        for (r, z) in pts:
            if abs(r) < 1e-6:
                rings.append([tmp.verts.new((0, 0, z))] * seg)
            else:
                rings.append([tmp.verts.new((r * math.cos(2 * math.pi * j / seg) * sc[0], r * math.sin(2 * math.pi * j / seg) * sc[1], z * sc[2]))
                              for j in range(seg)])
        for i in range(len(pts) - 1):
            a, b = rings[i], rings[i + 1]
            for j in range(seg):
                k = (j + 1) % seg
                out = []
                for v in (a[j], a[k], b[k], b[j]):
                    if not out or out[-1] is not v:
                        out.append(v)
                if len(out) > 1 and out[0] is out[-1]:
                    out.pop()
                if len(set(out)) >= 3:
                    try:
                        tmp.faces.new(out)
                    except ValueError:
                        pass
        s._merge(tmp, m, Matrix.Translation(c) @ R(*rot) @ AXM[axis])

    def extrude(s, poly, plane='xz', a0=0.0, a1=0.1, m=PL, rot=(0, 0, 0), c=(0, 0, 0), bev=0.0):
        """poly: 2D points. plane 'xz' extrudes along Y (a0..a1), 'yz' along X, 'xy' along Z."""
        tmp = bmesh.new()

        def p3(p, a):
            if plane == 'xz':
                return (p[0], a, p[1])
            if plane == 'yz':
                return (a, p[0], p[1])
            return (p[0], p[1], a)
        A = [tmp.verts.new(p3(p, a0)) for p in poly]
        B = [tmp.verts.new(p3(p, a1)) for p in poly]
        n = len(poly)
        tmp.faces.new(A)
        tmp.faces.new(B[::-1])
        for i in range(n):
            j = (i + 1) % n
            tmp.faces.new([A[i], A[j], B[j], B[i]])
        bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
        if bev > 0:
            s._bevel(tmp, list(tmp.edges), bev, 1)
        s._merge(tmp, m, Matrix.Translation(c) @ R(*rot))

    def loft(s, rings, m=CL, caps=True):
        tmp = bmesh.new()
        V = [[tmp.verts.new(p) for p in ring] for ring in rings]
        n = len(V[0])
        for i in range(len(V) - 1):
            for j in range(n):
                k = (j + 1) % n
                tmp.faces.new([V[i][j], V[i][k], V[i + 1][k], V[i + 1][j]])
        if caps:
            tmp.faces.new(V[0])
            tmp.faces.new(V[-1][::-1])
        bmesh.ops.recalc_face_normals(tmp, faces=tmp.faces)
        s._merge(tmp, m)

    def sheet(s, fn, x0, x1, y0, y1, nx, ny, m=CL, thick=0.01):
        tmp = bmesh.new()
        T = [[tmp.verts.new((x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny,
                             fn(x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny))) for j in range(ny + 1)] for i in range(nx + 1)]
        Bt = [[tmp.verts.new((v.co.x, v.co.y, v.co.z - thick)) for v in row] for row in T]
        for i in range(nx):
            for j in range(ny):
                tmp.faces.new([T[i][j], T[i + 1][j], T[i + 1][j + 1], T[i][j + 1]])
                tmp.faces.new([Bt[i][j + 1], Bt[i + 1][j + 1], Bt[i + 1][j], Bt[i][j]])
        for i in range(nx):
            tmp.faces.new([T[i][0], Bt[i][0], Bt[i + 1][0], T[i + 1][0]])
            tmp.faces.new([T[i + 1][ny], Bt[i + 1][ny], Bt[i][ny], T[i][ny]])
        for j in range(ny):
            tmp.faces.new([T[0][j + 1], Bt[0][j + 1], Bt[0][j], T[0][j]])
            tmp.faces.new([T[nx][j], Bt[nx][j], Bt[nx][j + 1], T[nx][j + 1]])
        s._merge(tmp, m)

    # ------------------------------------------------------------ transform
    def mark(s):
        return len(s.bm.verts)

    def xf_from(s, n0, M):
        s.bm.verts.ensure_lookup_table()
        vs = list(s.bm.verts)[n0:]
        bmesh.ops.transform(s.bm, matrix=M, verts=vs)

    def place(s, fn, pos=(0, 0, 0), rot=(0, 0, 0), scale=1.0, *a, **k):
        n0 = s.mark()
        fn(s, *a, **k)
        s.xf_from(n0, Matrix.Translation(pos) @ R(*rot) @ Matrix.Scale(scale, 4))

    def shift(s, v):
        bmesh.ops.translate(s.bm, vec=Vector(v), verts=list(s.bm.verts))
        if s.parent is not None:
            s.pivot = s.pivot + Vector(v)
        for c in s.children:
            c.shift(v)

    def ground(s):
        mz = min(v.co.z for v in s.bm.verts)
        for c in s.children:
            mz = min(mz, min(v.co.z for v in c.bm.verts))
        if mz < -0.0005:
            s.shift((0, 0, -mz))
        return s

    def xf_all(s, M):
        bmesh.ops.transform(s.bm, matrix=M, verts=list(s.bm.verts))

    def dent(s, centre, radius, depth, direction):
        centre = Vector(centre)
        d = Vector(direction).normalized()
        for v in s.bm.verts:
            L = (v.co - centre).length
            if L < radius:
                v.co += d * depth * (1 - (L / radius) ** 2)

    # --------------------------------------------------------------- finish
    def stats(s):
        return sum(len(f.verts) - 2 for f in s.bm.faces)

    def build(s, scene_coll, parent_obj=None):
        bm = s.bm
        # drop undersides sitting on the floor
        dead = [f for f in bm.faces if f.normal.z < -0.9 and max(v.co.z for v in f.verts) <= 0.012]
        bm.normal_update()
        dead = [f for f in bm.faces if f.normal.z < -0.9 and max(v.co.z for v in f.verts) <= 0.012]
        if dead:
            bmesh.ops.delete(bm, geom=dead, context='FACES')
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0004)
        big = [f for f in bm.faces if len(f.verts) > 4]
        if big:
            bmesh.ops.triangulate(bm, faces=big)
        bm.normal_update()
        for f in bm.faces:
            f.smooth = True
        for e in bm.edges:
            fs = e.link_faces
            e.smooth = not (len(fs) == 2 and fs[0].normal.angle(fs[1].normal, 0) > math.radians(52))
        # world-scale box projection UVs (1 uv = 1 m)
        uvl = bm.loops.layers.uv.new('UVMap')
        for f in bm.faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                p = l.vert.co
                if ax == 0:
                    uv = (p.y, p.z)
                elif ax == 1:
                    uv = (p.x, p.z)
                else:
                    uv = (p.x, p.y)
                l[uvl].uv = uv
        # shift to pivot
        if s.pivot.length > 0:
            bmesh.ops.translate(bm, vec=-s.pivot, verts=list(bm.verts))
        mesh = bpy.data.meshes.new(s.name)
        bm.to_mesh(mesh)
        for m in s.mats:
            mesh.materials.append(get_mat(m))
        obj = bpy.data.objects.new(s.name, mesh)
        scene_coll.objects.link(obj)
        obj.location = s.pivot
        if parent_obj is not None:
            obj.parent = parent_obj
        wn = obj.modifiers.new('WN', 'WEIGHTED_NORMAL')
        wn.keep_sharp = True
        wn.weight = 50
        bm.free()
        for c in s.children:
            c.build(scene_coll, obj)
        return obj


# ------------------------------------------------------------ shared details
def bolt(P, c, axis='z', r=0.02, h=0.015, m=BA):
    P.cyl(c, r, h, axis, m, seg=6, bev=0)


def flange(P, c, axis, r, t, nb=6, m=BA, boltr=0.018, body=PL, rb=None):
    """Flange disc with bolt heads on both faces (axis x/y/z)."""
    P.cyl(c, r, t, axis, body, seg=20, bev=min(0.006, t * 0.2))
    nb = 4 if r < 0.2 else min(nb, 6)
    rb = rb if rb is not None else r * 0.78
    c = Vector(c)
    for i in range(nb):
        a = 2 * math.pi * i / nb
        d = [math.cos(a) * rb, math.sin(a) * rb]
        for sgn in (1, -1):
            if axis == 'x':
                p = c + Vector((sgn * (t / 2 + boltr * 0.4), d[0], d[1]))
            elif axis == 'y':
                p = c + Vector((d[0], sgn * (t / 2 + boltr * 0.4), d[1]))
            else:
                p = c + Vector((d[0], d[1], sgn * (t / 2 + boltr * 0.4)))
            if axis == 'z' and sgn < 0 and c.z < 0.1:
                continue
            bolt(P, p, axis, boltr, boltr * 0.9, m)


def hazard_x(P, x0, x1, z0, z1, y, depth=0.012, n=8, a=YE, b=DK):
    w = (x1 - x0) / n
    for i in range(n):
        P.box((x0 + w * (i + 0.5), y, (z0 + z1) / 2), (w, depth, z1 - z0), a if i % 2 == 0 else b, bev=0.003)


def hazard_z(P, z0, z1, x, y, sz, n=8, a=YE, b=DK, axis='y'):
    h = (z1 - z0) / n
    for i in range(n):
        zz = z0 + h * (i + 0.5)
        P.box((x, y, zz), (sz[0], sz[1], h) if True else None, a if i % 2 == 0 else b, bev=0.003)


def chevron_poly(w, h, slant):
    return [(0, 0), (w, 0), (w, h) if slant == 0 else (w, h), (0, h)]


def rng_for(name):
    return random.Random(sum(ord(c) * (i + 3) for i, c in enumerate(name)))


def arch_pts(cx, cz, rin, rout, a0, a1, n):
    out = []
    for i in range(n):
        t0 = math.radians(a0 + (a1 - a0) * i / n)
        t1 = math.radians(a0 + (a1 - a0) * (i + 1) / n)
        out.append([(cx + rin * math.cos(t0), cz + rin * math.sin(t0)), (cx + rout * math.cos(t0), cz + rout * math.sin(t0)),
                    (cx + rout * math.cos(t1), cz + rout * math.sin(t1)), (cx + rin * math.cos(t1), cz + rin * math.sin(t1))])
    return out


def chain(P, x, y, z0, z1, link=0.12, r=0.02, m=DK, big=0.05):
    link *= 1.3
    """Vertical chain from z1 (top) down to z0, alternating oval links."""
    z = z1 - link / 2
    i = 0
    L = link / (2 * big) * 1.05
    while z > z0:
        if i % 2 == 0:
            P.torus((x, y, z), big, r, 'y', m, seg=6, rseg=4, sc=(1, L, 1))
        else:
            P.torus((x, y, z), big, r, 'x', m, seg=6, rseg=4, sc=(L, 1, 1))
        z -= link * 0.78
        i += 1


def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
