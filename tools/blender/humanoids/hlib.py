"""Shared helpers for the humanoid character scripts (player, gun, stalker, brute).

Run model scripts headless:
  /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/blender/humanoids/<model>.py

Conventions: metres, Z up, characters face -Y, character LEFT = +X.
"""
import bpy, bmesh, math, os, sys, json, struct
import numpy as np
from mathutils import Vector, Matrix, Quaternion, noise
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT_DIR = os.path.join(ROOT, 'public', 'models')
PREV_DIR = os.path.join(HERE, 'previews')
MB_FACTOR = 0.5747765  # isolated metaball surface radius / element radius (stiffness 2, threshold .6)

V = Vector


# --------------------------------------------------------------------------- scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for c in (bpy.data.objects, bpy.data.meshes, bpy.data.materials, bpy.data.metaballs):
        for x in list(c):
            c.remove(x)


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def mesh_from_bm(bm, name):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    return link(ob)


def apply_mods(ob):
    """Apply all modifiers by evaluating (no operator context needed)."""
    dg = bpy.context.evaluated_depsgraph_get()
    oe = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(oe)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    if old.users == 0 and isinstance(old, bpy.types.Mesh):
        bpy.data.meshes.remove(old)
    return ob


def get_co(ob):
    n = len(ob.data.vertices)
    a = np.empty(n * 3, np.float32)
    ob.data.vertices.foreach_get('co', a)
    return a.reshape(-1, 3).astype(np.float64)


def set_co(ob, co):
    ob.data.vertices.foreach_set('co', co.astype(np.float32).ravel())
    ob.data.update()


def get_normals(ob):
    n = len(ob.data.vertices)
    a = np.empty(n * 3, np.float32)
    ob.data.vertices.foreach_get('normal', a)
    return a.reshape(-1, 3).astype(np.float64)


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


# --------------------------------------------------------------------------- metaballs
def metaball(name, elems, res=0.012):
    """elems: list of tuples
       ('ball', co, r)                      r = desired surface radius when isolated
       ('cap', a, b, r)                     capsule between points a,b
       ('ell', co, (rx,ry,rz), rot_euler)   ellipsoid with semi-axes (approx)
       append '-' as first item ('-ball', ...) for negative elements.
       optional trailing dict {'stiff': s}"""
    mb = bpy.data.metaballs.new(name)
    mb.resolution = res
    mb.render_resolution = res
    mb.threshold = 0.6
    ob = link(bpy.data.objects.new(name, mb))
    for e in elems:
        kind = e[0]
        neg = kind.startswith('-')
        kind = kind.lstrip('-')
        opts = e[-1] if isinstance(e[-1], dict) else {}
        if kind == 'ball':
            el = mb.elements.new(type='BALL')
            el.co = V(e[1]); el.radius = e[2] / MB_FACTOR
        elif kind == 'cap':
            a, b, r = V(e[1]), V(e[2]), e[3]
            d = b - a
            el = mb.elements.new(type='CAPSULE')
            el.co = (a + b) / 2
            el.radius = r / MB_FACTOR
            el.size_x = d.length / 2 / el.radius  # size_x is relative to radius? (checked below)
            el.size_x = d.length / 2
            el.rotation = V((1, 0, 0)).rotation_difference(d.normalized()) if d.length > 1e-6 else Quaternion()
        elif kind == 'ell':
            co, rr = V(e[1]), e[2]
            rot = e[3] if len(e) > 3 and not isinstance(e[3], dict) else (0, 0, 0)
            el = mb.elements.new(type='ELLIPSOID')
            el.co = co
            r = max(rr)
            el.radius = r / MB_FACTOR
            el.size_x, el.size_y, el.size_z = rr[0] / r, rr[1] / r, rr[2] / r
            from mathutils import Euler
            el.rotation = Euler(rot).to_quaternion()
        el.stiffness = opts.get('stiff', 2.0)
        el.use_negative = neg
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.metaballs.remove(mb)
    out = link(bpy.data.objects.new(name + '_m', me))
    return out


def remesh(ob, voxel, smooth_iter=0, smooth_fac=0.5):
    m = ob.modifiers.new('rm', 'REMESH')
    m.mode = 'VOXEL'
    m.voxel_size = voxel
    m.adaptivity = 0
    m.use_smooth_shade = True
    apply_mods(ob)
    if smooth_iter:
        smooth(ob, smooth_iter, smooth_fac)
    return ob


def smooth(ob, iters, fac=0.5):
    m = ob.modifiers.new('sm', 'SMOOTH')
    m.iterations = iters
    m.factor = fac
    apply_mods(ob)


def decimate(ob, target_tris):
    t = tri_count(ob)
    if t > target_tris:
        m = ob.modifiers.new('dec', 'DECIMATE')
        m.decimate_type = 'COLLAPSE'
        m.ratio = target_tris / t
        m.use_collapse_triangulate = True
        apply_mods(ob)
    return ob


def fbm(p, octaves=3):
    return noise.fractal(V(p), 1.0, 2.0, octaves, noise_basis='PERLIN_NEW')


def displace_noise(ob, layers, mask_fn=None):
    """layers: list of (freq, amplitude[, stretch(xyz)]) — displaces along vertex normals."""
    ob.data.update()
    co = get_co(ob)
    nr = get_normals(ob)
    d = np.zeros(len(co))
    for L in layers:
        f, a = L[0], L[1]
        st = np.array(L[2]) if len(L) > 2 else np.ones(3)
        off = np.array(L[3]) if len(L) > 3 else np.array([13.1, 7.7, 3.3])
        for i, p in enumerate(co):
            q = p * st * f + off
            d[i] += a * noise.noise(V(q), noise_basis='PERLIN_NEW')
    if mask_fn is not None:
        d *= mask_fn(co, nr)
    set_co(ob, co + nr * d[:, None])


def shade_smooth(ob, sharp_angle=None):
    me = ob.data
    me.shade_smooth()
    if sharp_angle is not None:
        bm = bmesh.new(); bm.from_mesh(me)
        for e in bm.edges:
            if len(e.link_faces) == 2:
                if e.calc_face_angle(0) > math.radians(sharp_angle):
                    e.smooth = False
        bm.to_mesh(me); bm.free()


# --------------------------------------------------------------------------- primitives (bmesh)
def bm_cyl(bm, a, b, r1, r2=None, seg=12, caps=True):
    a, b = V(a), V(b)
    r2 = r1 if r2 is None else r2
    d = b - a
    q = V((0, 0, 1)).rotation_difference(d.normalized())
    M = Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4()
    return bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg,
                                 radius1=r1, radius2=r2, depth=d.length, matrix=M)['verts']


def bm_box(bm, center, size, rot=(0, 0, 0), bevel=0.0):
    from mathutils import Euler
    M = Matrix.Translation(center) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*size, 1))
    vs = bmesh.ops.create_cube(bm, size=1.0, matrix=M)['verts']
    if bevel > 0:
        es = list({e for v in vs for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=es, offset=bevel, segments=1, affect='EDGES', profile=0.5)
    return vs


def bm_sphere(bm, c, r, u=12, v=8, scale=(1, 1, 1), rot=(0, 0, 0)):
    from mathutils import Euler
    M = Matrix.Translation(c) @ Euler(rot).to_matrix().to_4x4() @ Matrix.Diagonal((*scale, 1))
    return bmesh.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r, matrix=M)['verts']


def bm_torus(bm, c, R, r, axis=(0, 0, 1), seg=16, rseg=6, scale=(1, 1, 1)):
    c = V(c)
    q = V((0, 0, 1)).rotation_difference(V(axis).normalized())
    rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ring = []
        for j in range(rseg):
            b = 2 * math.pi * j / rseg
            p = V(((R + r * math.cos(b)) * math.cos(a) * scale[0],
                   (R + r * math.cos(b)) * math.sin(a) * scale[1],
                   r * math.sin(b) * scale[2]))
            ring.append(bm.verts.new(c + q @ p))
        rings.append(ring)
    for i in range(seg):
        for j in range(rseg):
            bm.faces.new((rings[i][j], rings[(i + 1) % seg][j], rings[(i + 1) % seg][(j + 1) % rseg], rings[i][(j + 1) % rseg]))
    return [v for r_ in rings for v in r_]


def frames_along(pts):
    pts = [V(p) for p in pts]
    T = []
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]; b = pts[min(i + 1, len(pts) - 1)]
        T.append((b - a).normalized())
    up = V((0, 0, 1)) if abs(T[0].z) < 0.9 else V((1, 0, 0))
    N = [T[0].cross(up).normalized()]
    for i in range(1, len(pts)):
        n = N[-1] - T[i] * N[-1].dot(T[i])
        N.append(n.normalized())
    B = [T[i].cross(N[i]) for i in range(len(pts))]
    return pts, T, N, B


def bm_tube(bm, pts, radius, seg=8, caps=True, flat=1.0, twist_ref=None):
    """Tube through points; radius scalar or list; flat scales the B axis (for straps)."""
    pts, T, N, B = frames_along(pts)
    if twist_ref is not None:  # orient N toward reference direction
        for i in range(len(pts)):
            n = V(twist_ref) - T[i] * V(twist_ref).dot(T[i])
            if n.length > 1e-6:
                N[i] = n.normalized(); B[i] = T[i].cross(N[i])
    rings = []
    for i, p in enumerate(pts):
        r = radius[i] if isinstance(radius, (list, tuple)) else radius
        ring = []
        for j in range(seg):
            a = 2 * math.pi * j / seg
            ring.append(bm.verts.new(p + N[i] * (math.cos(a) * r) + B[i] * (math.sin(a) * r * flat)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        for j in range(seg):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % seg], rings[i + 1][(j + 1) % seg], rings[i + 1][j]))
    if caps:
        bm.faces.new(list(reversed(rings[0])))
        bm.faces.new(rings[-1])
    return [v for r_ in rings for v in r_]


def bezier_pts(p0, p1, p2, p3, n):
    p0, p1, p2, p3 = map(V, (p0, p1, p2, p3))
    out = []
    for i in range(n):
        t = i / (n - 1)
        out.append(p0 * (1 - t) ** 3 + p1 * 3 * t * (1 - t) ** 2 + p2 * 3 * t * t * (1 - t) + p3 * t ** 3)
    return out


# --------------------------------------------------------------------------- materials
MAT_DEF = {
    'flesh':       dict(rough=0.32, metal=0.0, spec=0.6, sss=0.0),
    'cloth':       dict(rough=0.85, metal=0.0, spec=0.3),
    'metal':       dict(rough=0.45, metal=0.85, spec=0.5),
    'rubber':      dict(rough=0.6, metal=0.0, spec=0.4),
    'porcelain':   dict(rough=0.12, metal=0.0, spec=0.8, coat=0.6),
    'glow_amber':  dict(rough=0.3, emit=(1.0, 0.55, 0.12), estr=2.0),
    'glow_cyan':   dict(rough=0.3, emit=(0.2, 0.9, 1.0), estr=2.0),
    'glow_orange': dict(rough=0.3, emit=(1.0, 0.35, 0.05), estr=2.0),
    'glow_red':    dict(rough=0.3, emit=(1.0, 0.08, 0.05), estr=2.0),
}


def get_mat(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    d = MAT_DEF[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = 'Color'
    nt.links.new(vc.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = d.get('rough', 0.5)
    bsdf.inputs['Metallic'].default_value = d.get('metal', 0.0)
    if 'Coat Weight' in bsdf.inputs and d.get('coat'):
        bsdf.inputs['Coat Weight'].default_value = d['coat']
    if 'emit' in d:
        bsdf.inputs['Emission Color'].default_value = (*d['emit'], 1)
        bsdf.inputs['Emission Strength'].default_value = d['estr']
    return m


def set_mat(ob, name):
    ob.data.materials.clear()
    ob.data.materials.append(get_mat(name))
    for p in ob.data.polygons:
        p.material_index = 0


# --------------------------------------------------------------------------- parts & painting
class Part:
    """A mesh object plus metadata: rigid bone (or None), allowed bones, paint fn."""
    def __init__(self, ob, mat=None, bone=None, allowed=None, paint=None, mats=None):
        self.ob, self.bone, self.allowed, self.paint = ob, bone, allowed, paint
        if mat:
            set_mat(ob, mat)


def mat_names_of(ob):
    return [m.name if m else '' for m in ob.data.materials]


def corner_arrays(ob):
    me = ob.data
    nl = len(me.loops)
    vidx = np.empty(nl, np.int32); me.loops.foreach_get('vertex_index', vidx)
    np_ = len(me.polygons)
    ls = np.empty(np_, np.int32); me.polygons.foreach_get('loop_start', ls)
    lt = np.empty(np_, np.int32); me.polygons.foreach_get('loop_total', lt)
    mi = np.empty(np_, np.int32); me.polygons.foreach_get('material_index', mi)
    face_of_loop = np.repeat(np.arange(np_), lt)
    names = mat_names_of(ob) or ['']
    mi = np.clip(mi, 0, len(names) - 1)
    mat_of_loop = np.array([names[i] for i in mi[face_of_loop]]) if np_ else np.array([])
    return vidx, face_of_loop, mat_of_loop


def ensure_color(ob):
    me = ob.data
    ca = me.color_attributes.get('Color')
    if ca is None:
        ca = me.color_attributes.new('Color', 'FLOAT_COLOR', 'CORNER')
    me.color_attributes.active_color = ca
    try:
        me.color_attributes.render_color_index = list(me.color_attributes).index(ca)
    except Exception:
        pass
    return ca


def get_corner_colors(ob):
    ca = ensure_color(ob)
    a = np.empty(len(ob.data.loops) * 4, np.float32)
    ca.data.foreach_get('color', a)
    return a.reshape(-1, 4).astype(np.float64)


def set_corner_colors(ob, col):
    ca = ensure_color(ob)
    c = np.clip(col, 0, 1).astype(np.float32)
    if c.shape[1] == 3:
        c = np.concatenate([c, np.ones((len(c), 1), np.float32)], 1)
    ca.data.foreach_set('color', c.ravel())


def paint_part(ob, fn):
    """fn(co[N,3] per corner, nrm[N,3], mat[N], vidx[N]) -> rgb[N,3]"""
    ob.data.update()
    co = get_co(ob); nr = get_normals(ob)
    vidx, f, mats = corner_arrays(ob)
    rgb = fn(co[vidx], nr[vidx], mats, vidx)
    set_corner_colors(ob, rgb)


def nz(p, f=1.0, off=(0, 0, 0), oct=1):
    """Vectorised-ish perlin over an (N,3) array; returns array in ~[-1,1]."""
    out = np.empty(len(p))
    o = np.array(off)
    if oct == 1:
        for i, q in enumerate(p):
            out[i] = noise.noise(V(q * f + o), noise_basis='PERLIN_NEW')
    else:
        for i, q in enumerate(p):
            out[i] = noise.fractal(V(q * f + o), 1.0, 2.0, oct, noise_basis='PERLIN_NEW')
    return out


def per_vertex_noise(ob_co, vidx, f, off=(0, 0, 0), oct=1):
    """Compute noise once per vertex, return per corner."""
    v = nz(ob_co, f, off, oct)
    return v[vidx]


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    a = np.asarray(a, float); b = np.asarray(b, float)
    t = np.asarray(t, float)
    if t.ndim == 1 and (a.ndim == 1 and a.shape[0] == 3):
        t = t[:, None]
    elif t.ndim == 1:
        t = t[:, None]
    return a * (1 - t) + b * t


def vertex_ao(ob, rays=20, dist=0.25, bias=0.002):
    """Returns per-vertex ambient visibility (1 = open, 0 = occluded)."""
    ob.data.update()
    co = get_co(ob); nr = get_normals(ob)
    polys = [tuple(p.vertices) for p in ob.data.polygons]
    bvh = BVHTree.FromPolygons([V(c) for c in co], polys, all_triangles=False)
    rng = np.random.default_rng(3)
    # fixed hemisphere directions (cosine weighted around +Z), rotated per vertex
    u1 = rng.random(rays); u2 = rng.random(rays)
    r = np.sqrt(u1); th = 2 * np.pi * u2
    local = np.stack([r * np.cos(th), r * np.sin(th), np.sqrt(1 - u1)], 1)
    vis = np.ones(len(co))
    for i in range(len(co)):
        n = V(nr[i])
        if n.length < 1e-6:
            continue
        q = V((0, 0, 1)).rotation_difference(n)
        o = V(co[i]) + n * bias
        hits = 0.0
        for d in local:
            dd = q @ V(d)
            h = bvh.ray_cast(o, dd, dist)
            if h[0] is not None:
                hits += 1.0 - (h[3] / dist) * 0.5
        vis[i] = 1.0 - hits / rays
    return vis


def vertex_curvature(ob):
    """Positive = convex, negative = concave (per vertex, unnormalised)."""
    ob.data.update()
    co = get_co(ob); nr = get_normals(ob)
    ne = len(ob.data.edges)
    e = np.empty(ne * 2, np.int32); ob.data.edges.foreach_get('vertices', e); e = e.reshape(-1, 2)
    acc = np.zeros(len(co)); cnt = np.zeros(len(co))
    d = co[e[:, 1]] - co[e[:, 0]]
    L = np.linalg.norm(d, axis=1) + 1e-9
    # convex: neighbour lies below tangent plane
    c0 = -np.einsum('ij,ij->i', nr[e[:, 0]], d) / L
    c1 = np.einsum('ij,ij->i', nr[e[:, 1]], d) / L
    np.add.at(acc, e[:, 0], c0); np.add.at(cnt, e[:, 0], 1)
    np.add.at(acc, e[:, 1], c1); np.add.at(cnt, e[:, 1], 1)
    return acc / np.maximum(cnt, 1)


def finish_colors(ob, ao_strength=0.6, ao_dist=0.2, cav_strength=0.5, grime=(0.5, 0.35), height=1.0, exclude=('glow',)):
    """Multiply corner colours by AO, cavity and ground grime. exclude: material prefixes left untouched."""
    col = get_corner_colors(ob)[:, :3]
    vidx, f, mats = corner_arrays(ob)
    ao = vertex_ao(ob, dist=ao_dist)
    cur = vertex_curvature(ob)
    cs = np.std(cur) + 1e-9
    cav = np.clip(-cur / (2.5 * cs), 0, 1)  # concave -> 1
    edge = np.clip(cur / (2.5 * cs), 0, 1)
    co = get_co(ob)
    g_lo, g_frac = grime
    gr = g_lo + (1 - g_lo) * smoothstep(0.0, g_frac * height, co[:, 2])
    k = (1 - ao_strength * (1 - ao)) * (1 - cav_strength * cav) * gr * (1 + 0.15 * edge)
    kk = k[vidx]
    skip = np.array([any(m.startswith(e) for e in exclude) for m in mats])
    kk[skip] = 1.0
    col = col * kk[:, None]
    set_corner_colors(ob, col)


# --------------------------------------------------------------------------- armature
def build_armature(name, bones):
    """bones: list of (name, head, tail, parent, connected, deform, roll)"""
    arm = bpy.data.armatures.new(name)
    ob = link(bpy.data.objects.new(name, arm))
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.edit_bones
    for (bn, h, t, par, con, dfm, *rest) in bones:
        b = eb.new(bn)
        b.head = V(h); b.tail = V(t)
        if rest:
            b.roll = rest[0]
        else:
            # roll so that local Z axis points as close to -Y (forward) / +Y as possible: use align_roll
            fwd = V((0, -1, 0))
            if abs((b.tail - b.head).normalized().dot(fwd)) > 0.95:
                b.align_roll(V((0, 0, 1)))
            else:
                b.align_roll(fwd)
        b.use_deform = dfm
        if par:
            b.parent = eb[par]
            b.use_connect = con
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob


def bone_segments(arm_ob):
    out = {}
    for b in arm_ob.data.bones:
        out[b.name] = (np.array(b.head_local), np.array(b.tail_local), b.use_deform)
    return out


def seg_dist(p, a, b):
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    proj = a + t[:, None] * ab
    return np.linalg.norm(p - proj, axis=1), t


def compute_weights(ob, arm_ob, radii, rigid_bone_of_vert, allowed_of_vert, power=5.0, smooth_iters=6,
                    bias=None):
    """radii: {bone: influence radius}. rigid_bone_of_vert: list (None or bone name).
       allowed_of_vert: list (None or set of names).  bias: optional fn(co, bone)->multiplier array"""
    segs = bone_segments(arm_ob)
    names = [n for n, s in segs.items() if s[2]]
    co = get_co(ob)
    Nv = len(co)
    W = np.zeros((Nv, len(names)))
    for j, n in enumerate(names):
        a, b, _ = segs[n]
        d, t = seg_dist(co, a, b)
        r = radii.get(n, 0.1)
        w = 1.0 / (1e-4 + (d / r)) ** power
        if bias:
            w *= bias(co, n)
        W[:, j] = w
    locked = np.zeros(Nv, bool)
    for i in range(Nv):
        rb = rigid_bone_of_vert[i]
        if rb is not None:
            W[i] = 0; W[i, names.index(rb)] = 1; locked[i] = True
        elif allowed_of_vert[i] is not None:
            mask = np.array([n in allowed_of_vert[i] for n in names])
            W[i, ~mask] = 0
    W /= W.sum(1, keepdims=True) + 1e-12
    # smoothing over mesh neighbours
    ne = len(ob.data.edges)
    e = np.empty(ne * 2, np.int32); ob.data.edges.foreach_get('vertices', e); e = e.reshape(-1, 2)
    for _ in range(smooth_iters):
        acc = np.zeros_like(W); cnt = np.zeros(Nv)
        np.add.at(acc, e[:, 0], W[e[:, 1]]); np.add.at(acc, e[:, 1], W[e[:, 0]])
        np.add.at(cnt, e[:, 0], 1); np.add.at(cnt, e[:, 1], 1)
        avg = acc / np.maximum(cnt, 1)[:, None]
        has = cnt > 0
        upd = has & ~locked
        W[upd] = 0.5 * W[upd] + 0.5 * avg[upd]
    # re-apply allowed masks, top 4, normalise
    for i in range(Nv):
        if allowed_of_vert[i] is not None and not locked[i]:
            mask = np.array([n in allowed_of_vert[i] for n in names])
            W[i, ~mask] = 0
    idx = np.argsort(-W, axis=1)[:, :4]
    W4 = np.take_along_axis(W, idx, 1)
    W4[W4 < 0.01] = 0
    s = W4.sum(1, keepdims=True)
    bad = (s[:, 0] <= 0)
    if bad.any():
        print('WARNING: %d verts with no weight, assigning nearest' % bad.sum())
    W4 = W4 / np.maximum(s, 1e-12)
    # write vertex groups
    for g in list(ob.vertex_groups):
        ob.vertex_groups.remove(g)
    groups = {n: ob.vertex_groups.new(name=n) for n in names}
    for i in range(Nv):
        for k in range(4):
            w = float(W4[i, k])
            if w > 0:
                groups[names[idx[i, k]]].add([i], w, 'REPLACE')
    return names


def assemble(name, parts, arm_ob, radii, power=5.0, smooth_iters=6, bias=None):
    """Join parts into one mesh, weight it, parent to armature."""
    # tag vertices with part index
    rigid = []
    allowed = []
    for k, p in enumerate(parts):
        n = len(p.ob.data.vertices)
        rigid += [p.bone] * n
        allowed += [set(p.allowed) if p.allowed else None] * n
    obs = [p.ob for p in parts]
    for p in parts:
        print('PART', p.ob.name, tri_count(p.ob))
    for o in obs:
        ensure_color(o)
    ctx = bpy.context
    for o in ctx.view_layer.objects:
        o.select_set(False)
    for o in obs:
        o.select_set(True)
    ctx.view_layer.objects.active = obs[0]
    # NOTE: join order = active first then others in selection order; enforce by joining one by one
    base = obs[0]
    order_rigid = list(rigid[:len(base.data.vertices)])
    order_allowed = list(allowed[:len(base.data.vertices)])
    off = len(base.data.vertices)
    for p in parts[1:]:
        n = len(p.ob.data.vertices)
        for o in ctx.view_layer.objects:
            o.select_set(False)
        p.ob.select_set(True); base.select_set(True)
        ctx.view_layer.objects.active = base
        bpy.ops.object.join()
        order_rigid += [p.bone] * n
        order_allowed += [set(p.allowed) if p.allowed else None] * n
    base.name = name
    base.data.name = name
    assert len(base.data.vertices) == len(order_rigid)
    names = compute_weights(base, arm_ob, radii, order_rigid, order_allowed, power, smooth_iters, bias)
    base.parent = arm_ob
    m = base.modifiers.new('Armature', 'ARMATURE')
    m.object = arm_ob
    return base


# --------------------------------------------------------------------------- export & verify
def export_glb(objs, path):
    ctx = bpy.context
    for o in ctx.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    ctx.view_layer.objects.active = objs[0]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
                              export_skins=True, export_animations=False, export_apply=True,
                              export_cameras=False, export_lights=False, export_vertex_color='ACTIVE',
                              export_all_vertex_colors=False, export_influence_nb=4, export_def_bones=False,
                              export_materials='EXPORT', export_image_format='NONE', export_extras=False,
                              export_morph=False)
    print('EXPORTED', path, os.path.getsize(path), 'bytes')


def glb_report(path):
    """Parse the GLB JSON directly (no Blender) and print key facts."""
    with open(path, 'rb') as f:
        data = f.read()
    ln = struct.unpack('<I', data[12:16])[0]
    js = json.loads(data[20:20 + ln])
    tris = 0; cols = False; mins = []; maxs = []
    for m in js['meshes']:
        for pr in m['primitives']:
            acc = js['accessors'][pr['indices']]
            tris += acc['count'] // 3
            if 'COLOR_0' in pr['attributes']:
                cols = True
            pa = js['accessors'][pr['attributes']['POSITION']]
            mins.append(pa['min']); maxs.append(pa['max'])
    mats = [m['name'] for m in js.get('materials', [])]
    joints = []
    for s in js.get('skins', []):
        joints = [js['nodes'][j]['name'] for j in s['joints']]
    nodes = [n.get('name') for n in js['nodes']]
    mn = np.min(mins, 0); mx = np.max(maxs, 0)
    rep = dict(file=os.path.basename(path), bytes=len(data), tris=tris, COLOR_0=cols, materials=mats,
               joints=joints, nodes=nodes, gltf_min=[round(x, 3) for x in mn], gltf_max=[round(x, 3) for x in mx],
               animations=len(js.get('animations', [])))
    print('GLBREPORT', json.dumps(rep))
    return rep


# --------------------------------------------------------------------------- rendering
def _eevee(scene, samples=32):
    scene.render.engine = 'BLENDER_EEVEE'
    try:
        scene.eevee.taa_render_samples = samples
    except Exception:
        pass
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'None'


def _world(scene, color, strength=1.0):
    w = scene.world or bpy.data.worlds.new('W')
    scene.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (*color, 1)
    bg.inputs['Strength'].default_value = strength


def look_at(ob, target):
    d = V(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def make_cam(name, loc, target, lens=None, fov=None, ortho=None):
    cd = bpy.data.cameras.new(name)
    ob = link(bpy.data.objects.new(name, cd))
    ob.location = V(loc)
    look_at(ob, target)
    cd.sensor_fit = 'VERTICAL'
    if fov:
        cd.angle = math.radians(fov)
    if ortho:
        cd.type = 'ORTHO'; cd.ortho_scale = ortho
    cd.clip_end = 200
    return ob


def make_light(name, kind, loc, target=None, energy=100, color=(1, 1, 1), size=0.1, spot=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy; ld.color = color
    if hasattr(ld, 'shadow_soft_size'):
        ld.shadow_soft_size = size
    if kind == 'SPOT' and spot:
        ld.spot_size = math.radians(spot); ld.spot_blend = 0.25
    if kind == 'AREA':
        ld.size = size
    ob = link(bpy.data.objects.new(name, ld))
    ob.location = V(loc)
    if target is not None:
        look_at(ob, target)
    return ob


def render_to(scene, cam, path, w, h):
    scene.camera = cam
    scene.render.resolution_x = w; scene.render.resolution_y = h
    scene.render.resolution_percentage = 100
    scene.render.filepath = path
    scene.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)
    return path


def stitch(paths, out, cols=None):
    imgs = []
    for p in paths:
        im = bpy.data.images.load(p)
        a = np.empty(im.size[0] * im.size[1] * 4, np.float32)
        im.pixels.foreach_get(a)
        imgs.append(a.reshape(im.size[1], im.size[0], 4))
        bpy.data.images.remove(im)
    h = max(i.shape[0] for i in imgs)
    imgs = [np.pad(i, ((0, h - i.shape[0]), (0, 0), (0, 0))) for i in imgs]
    big = np.concatenate(imgs, 1)
    im = bpy.data.images.new('stitch', big.shape[1], big.shape[0], alpha=True)
    im.pixels.foreach_set(big.ravel())
    im.filepath_raw = out; im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)
    for p in paths:
        try:
            os.remove(p)
        except Exception:
            pass


class Rig:
    """Temporary render rig objects so they can be removed between setups."""
    def __init__(self):
        self.objs = []

    def add(self, o):
        self.objs.append(o); return o

    def clear(self):
        for o in self.objs:
            bpy.data.objects.remove(o, do_unlink=True)
        self.objs = []


def render_studio(tag, height, center_z=None, extra_dist=1.0, width_hint=None):
    scene = bpy.context.scene
    _eevee(scene, 32)
    _world(scene, (0.22, 0.23, 0.25), 1.0)
    rig = Rig()
    cz = center_z if center_z is not None else height * 0.5
    c = V((0, 0, cz))
    size = max(height, width_hint or 0)
    dist = size * 2.6 * extra_dist
    rig.add(make_light('key', 'AREA', (-2.5 * size, -2.5 * size, 3 * size), c, energy=300 * size * size, size=size * 1.5, color=(1, 0.97, 0.92)))
    rig.add(make_light('rim', 'AREA', (2.5 * size, 2.5 * size, 2.5 * size), c, energy=250 * size * size, size=size * 1.5, color=(0.8, 0.9, 1.0)))
    rig.add(make_light('top', 'AREA', (0, 0, 4 * size), c, energy=150 * size * size, size=size * 2))
    fov = 30
    shots = []
    for i, (az, el) in enumerate([(35, 15), (180 + 35, 20), (0, 89.5)]):
        a = math.radians(az); e = math.radians(el)
        loc = c + V((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * dist
        cam = rig.add(make_cam('scam%d' % i, loc, c, fov=fov))
        if el > 89:
            cam.rotation_euler = (0, 0, 0)
            cam.location = c + V((0, 0, dist))
        p = os.path.join(PREV_DIR, '_tmp_%s_%d.png' % (tag, i))
        shots.append(render_to(scene, cam, p, 600, 800))
    out = os.path.join(PREV_DIR, '%s_turnaround.png' % tag)
    stitch(shots, out)
    rig.clear()
    print('RENDERED', out)
    return out


def render_game(tag, height, center_z=None, zoom=10):
    scene = bpy.context.scene
    _eevee(scene, 32)
    _world(scene, (0, 0, 0), 0.0)
    rig = Rig()
    gm = bpy.data.meshes.new('ground')
    bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=15); bm.to_mesh(gm); bm.free()
    g = rig.add(link(bpy.data.objects.new('ground', gm)))
    gmat = bpy.data.materials.get('ground_prev') or bpy.data.materials.new('ground_prev')
    gmat.use_nodes = True
    b = next(n for n in gmat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs['Base Color'].default_value = (0.06, 0.065, 0.07, 1); b.inputs['Roughness'].default_value = 0.7
    gm.materials.append(gmat)
    cz = center_z if center_z is not None else height * 0.45
    el = math.radians(62)
    cam_loc = V((0, -22 * math.cos(el), 22 * math.sin(el)))
    rig.add(make_light('spot', 'SPOT', (0, -3.0, 9.0), (0, 0, 0), energy=3500, color=(0.72, 0.85, 1.0), size=0.02, spot=38))
    cam = rig.add(make_cam('gcam', cam_loc, (0, 0, 0), fov=30))
    full = render_to(scene, cam, os.path.join(PREV_DIR, '%s_game.png' % tag), 900, 506)
    cam2 = rig.add(make_cam('gcam4', cam_loc, (0, 0, cz), fov=math.degrees(2 * math.atan(math.tan(math.radians(15)) / 4))))
    crop = render_to(scene, cam2, os.path.join(PREV_DIR, '%s_game_crop4x.png' % tag), 900, 506)
    cam3 = rig.add(make_cam('gcam10', cam_loc, (0, 0, cz), fov=math.degrees(2 * math.atan(math.tan(math.radians(15)) / zoom))))
    render_to(scene, cam3, os.path.join(PREV_DIR, '%s_game_crop%dx.png' % (tag, zoom)), 900, 506)
    rig.clear()
    print('RENDERED', full, crop)


def rotate_bone_world(arm_ob, bname, axis, deg):
    pb = arm_ob.pose.bones[bname]
    bpy.context.view_layer.update()
    M = pb.matrix.copy()
    h = M.to_translation()
    R = Matrix.Translation(h) @ Matrix.Rotation(math.radians(deg), 4, V(axis)) @ Matrix.Translation(-h)
    pb.matrix = R @ M
    bpy.context.view_layer.update()


def reset_pose(arm_ob):
    for pb in arm_ob.pose.bones:
        pb.matrix_basis = Matrix()
    bpy.context.view_layer.update()
