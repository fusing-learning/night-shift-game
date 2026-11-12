"""Shared helpers for scripted creature models (Blender 5.x, headless).

Conventions: metres, Z up, creatures face -Y, creature's left = +X.
"""
import bpy, bmesh, math, os, random
import numpy as np
from mathutils import Vector, Matrix, Quaternion, noise
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT_DIR = os.path.join(ROOT, "public", "models")
PREV_DIR = os.path.join(HERE, "previews")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(PREV_DIR, exist_ok=True)

MB_K = 0.5749870  # surface radius / metaball radius for stiffness 2, threshold .6


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def V(*a):
    return Vector(a if len(a) == 3 else a[0])

# ---------------------------------------------------------------- builders

def metaballs(name, elems, res=0.02):
    """elems: dicts with type BALL/CAPSULE/ELLIPSOID, co, r (surface radius),
    for CAPSULE: a,b endpoints (overrides co); ELLIPSOID: s=(sx,sy,sz) multipliers,
    rot (Quaternion or euler tuple), neg, stiff."""
    mb = bpy.data.metaballs.new(name)
    mb.resolution = res
    mb.render_resolution = res
    mb.threshold = 0.6
    for e in elems:
        t = e.get("type", "BALL")
        el = mb.elements.new(type=t)
        r = e["r"]
        el.radius = r / MB_K
        el.stiffness = e.get("stiff", 2.0)
        el.use_negative = e.get("neg", False)
        if t == "CAPSULE" and "a" in e:
            a, b = Vector(e["a"]), Vector(e["b"])
            d = b - a
            el.co = (a + b) / 2
            el.size_x = d.length / 2
            el.rotation = Vector((1, 0, 0)).rotation_difference(d.normalized())
        else:
            el.co = Vector(e["co"])
            if t == "CAPSULE":
                el.size_x = e.get("half", 0.1)
            if t == "ELLIPSOID":
                s = e.get("s", (1, 1, 1))
                el.size_x, el.size_y, el.size_z = s
            rot = e.get("rot")
            if rot is not None:
                if isinstance(rot, Quaternion):
                    el.rotation = rot
                else:
                    from mathutils import Euler
                    el.rotation = Euler(rot).to_quaternion()
    obj = link(bpy.data.objects.new(name, mb))
    return to_mesh_obj(obj, name + "_m")


def skin_tubes(name, chains, subsurf=1):
    """chains: list of lists of (co, radius). Each chain is a polyline.
    Returns mesh object (applied)."""
    verts, edges, radii = [], [], []
    for ch in chains:
        base = len(verts)
        for i, (co, r) in enumerate(ch):
            verts.append(tuple(co))
            radii.append(r)
            if i > 0:
                edges.append((base + i - 1, base + i))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, edges, [])
    obj = link(bpy.data.objects.new(name, me))
    m = obj.modifiers.new("skin", "SKIN")
    m.use_smooth_shade = True
    roots = set()
    k = 0
    for ch in chains:
        roots.add(k)
        k += len(ch)
    for i, r in enumerate(radii):
        sv = me.skin_vertices[0].data[i]
        sv.radius = (r, r)
        sv.use_root = i in roots
    if subsurf:
        s = obj.modifiers.new("ss", "SUBSURF")
        s.levels = subsurf
    return to_mesh_obj(obj, name + "_m")


def to_mesh_obj(obj, name=None):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    me.transform(obj.matrix_world)
    nm = name or obj.name
    new = link(bpy.data.objects.new(nm, me))
    bpy.data.objects.remove(obj, do_unlink=True)
    new.name = nm
    return new


def apply_mods(obj):
    return to_mesh_obj(obj, obj.name)


def prim(kind, name, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), **kw):
    bm = bmesh.new()
    if kind == "sphere":
        bmesh.ops.create_uvsphere(bm, u_segments=kw.get("u", 12), v_segments=kw.get("v", 8), radius=1.0)
    elif kind == "ico":
        bmesh.ops.create_icosphere(bm, subdivisions=kw.get("sub", 2), radius=1.0)
    elif kind == "cyl":
        bmesh.ops.create_cone(bm, cap_ends=kw.get("caps", True), cap_tris=False, segments=kw.get("seg", 12),
                              radius1=kw.get("r1", 1.0), radius2=kw.get("r2", 1.0), depth=kw.get("depth", 1.0))
    elif kind == "cube":
        bmesh.ops.create_cube(bm, size=1.0)
    elif kind == "torus":
        R, r, s1, s2 = kw.get("R", 1), kw.get("r", .2), kw.get("seg", 16), kw.get("seg2", 6)
        verts = []
        for i in range(s1):
            a = 2 * math.pi * i / s1
            for j in range(s2):
                b = 2 * math.pi * j / s2
                verts.append(bm.verts.new(((R + r * math.cos(b)) * math.cos(a), (R + r * math.cos(b)) * math.sin(a), r * math.sin(b))))
        for i in range(s1):
            for j in range(s2):
                bm.faces.new((verts[i * s2 + j], verts[((i + 1) % s1) * s2 + j],
                              verts[((i + 1) % s1) * s2 + (j + 1) % s2], verts[i * s2 + (j + 1) % s2]))
    from mathutils import Euler
    M = Matrix.LocRotScale(Vector(loc), Euler(rot).to_quaternion() if not isinstance(rot, Quaternion) else rot, Vector(scale))
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = link(bpy.data.objects.new(name, me))
    for p in me.polygons:
        p.use_smooth = kw.get("smooth", True)
    return obj


def cyl_between(name, a, b, r1, r2=None, seg=8, caps=True):
    a, b = Vector(a), Vector(b)
    d = b - a
    q = Vector((0, 0, 1)).rotation_difference(d.normalized())
    o = prim("cyl", name, loc=(a + b) / 2, rot=q, r1=r1, r2=r1 if r2 is None else r2, depth=d.length, seg=seg, caps=caps)
    return o


def cone_between(name, a, b, r, seg=5):
    return cyl_between(name, a, b, r, 0.0005, seg=seg)


def join(objs, name):
    objs = [o for o in objs if o is not None]
    if len(objs) == 1:
        objs[0].name = name
        return objs[0]
    with bpy.context.temp_override(active_object=objs[0], object=objs[0],
                                   selected_objects=objs, selected_editable_objects=objs):
        bpy.ops.object.join()
    objs[0].name = name
    objs[0].data.name = name
    return objs[0]


def remesh(obj, voxel):
    m = obj.modifiers.new("rm", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = voxel
    m.adaptivity = 0
    m.use_smooth_shade = True
    return apply_mods(obj)


def decimate(obj, target_tris):
    for _ in range(6):
        t = tri_count(obj)
        if t <= target_tris:
            return obj
        m = obj.modifiers.new("dec", "DECIMATE")
        m.decimate_type = "COLLAPSE"
        m.ratio = max(0.02, target_tris / t * 0.98)
        m.use_collapse_triangulate = True
        obj = apply_mods(obj)
    return obj


def triangulate(obj):
    m = obj.modifiers.new("tri", "TRIANGULATE")
    return apply_mods(obj)


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def shade_smooth(obj):
    obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))

# ---------------------------------------------------------------- numpy mesh

def get_co(obj):
    me = obj.data
    a = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", a)
    return a.reshape(-1, 3)


def set_co(obj, co):
    obj.data.vertices.foreach_set("co", co.ravel())
    obj.data.update()


def get_normals(obj):
    me = obj.data
    me.update()
    a = np.zeros(len(me.vertices) * 3)
    me.vertex_normals.foreach_get("vector", a)
    return a.reshape(-1, 3)


def get_edges(obj):
    me = obj.data
    e = np.zeros(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", e)
    return e.reshape(-1, 2)


def neighbor_avg(vals, edges, n):
    s = np.zeros((n,) + vals.shape[1:])
    c = np.zeros(n)
    np.add.at(s, edges[:, 0], vals[edges[:, 1]])
    np.add.at(s, edges[:, 1], vals[edges[:, 0]])
    np.add.at(c, edges[:, 0], 1)
    np.add.at(c, edges[:, 1], 1)
    c = np.maximum(c, 1)
    return s / c.reshape((-1,) + (1,) * (vals.ndim - 1))


def smooth(obj, iters=4, lam=0.5, mu=-0.53, mask=None):
    """Taubin smoothing. mask: per-vertex factor 0..1"""
    co = get_co(obj)
    e = get_edges(obj)
    n = len(co)
    m = np.ones(n) if mask is None else mask
    m = m[:, None]
    for _ in range(iters):
        co = co + lam * m * (neighbor_avg(co, e, n) - co)
        co = co + mu * m * (neighbor_avg(co, e, n) - co)
    set_co(obj, co)


def nfield(P, scale=1.0, off=(0, 0, 0), basis="PERLIN_NEW", octaves=1, ridged=False):
    out = np.zeros(len(P))
    o = Vector(off)
    for i, p in enumerate(P):
        v = Vector(p) * scale + o
        if octaves > 1:
            out[i] = noise.fractal(v, 0.6, 2.0, octaves, noise_basis=basis)
        else:
            out[i] = noise.noise(v, noise_basis=basis)
    if ridged:
        out = np.abs(out)
    return out


def vnoise3(P, scale, off=(0, 0, 0)):
    out = np.zeros((len(P), 3))
    o = Vector(off)
    for i, p in enumerate(P):
        out[i] = noise.noise_vector(Vector(p) * scale + o)
    return out


def displace(obj, amount_fn):
    """amount_fn(co, n) -> per-vertex scalar offset along normal."""
    co = get_co(obj)
    n = get_normals(obj)
    d = amount_fn(co, n)
    set_co(obj, co + n * d[:, None])


def lumps(obj, s1=(4.0, 0.03), s2=(14.0, 0.008), seed=0, mask=None, cells=None):
    def f(co, n):
        a = nfield(co, s1[0], (seed, 1.3 * seed, 0.7), octaves=2) * s1[1]
        b = nfield(co, s2[0], (seed + 11, 3.1, seed), octaves=1) * s2[1]
        d = a + b
        if cells is not None:
            d += cellular(co, cells[0], seed) * cells[1]
        return d if mask is None else d * mask
    displace(obj, f)


def cellular(P, scale, seed=0):
    out = np.zeros(len(P))
    for i, p in enumerate(P):
        d, _ = noise.voronoi(Vector(p) * scale + Vector((seed, seed * .5, 0)), distance_metric="DISTANCE", exponent=2.5)
        out[i] = d[1] - d[0]
    return np.clip(out, 0, 1)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def curvature(obj):
    co = get_co(obj)
    n = get_normals(obj)
    e = get_edges(obj)
    avg = neighbor_avg(co, e, len(co))
    d = avg - co
    L = np.linalg.norm(d, axis=1) + 1e-9
    # concave -> positive (neighbours lie "above" along normal)
    c = (d * n).sum(1) / (np.mean(np.linalg.norm(co[e[:, 0]] - co[e[:, 1]], axis=1)) + 1e-9)
    return c


def ao(obj, rays=20, dist=0.3, extra=None):
    """vertex ambient occlusion, 0 = open, 1 = fully occluded.
    extra: list of objects that also occlude."""
    me = obj.data
    co = get_co(obj)
    nr = get_normals(obj)
    verts = [Vector(c) for c in co]
    polys = [tuple(p.vertices) for p in me.polygons]
    if extra:
        for o in extra:
            base = len(verts)
            mw = o.matrix_world
            verts += [mw @ v.co for v in o.data.vertices]
            polys += [tuple(base + i for i in p.vertices) for p in o.data.polygons]
    bvh = BVHTree.FromPolygons(verts, polys)
    rng = np.random.default_rng(3)
    dirs = rng.normal(size=(rays, 3))
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    out = np.zeros(len(co))
    for i in range(len(co)):
        n = nr[i]
        p = Vector(co[i] + n * 0.004)
        occ = 0.0
        tot = 0.0
        for d in dirs:
            dd = d if d.dot(n) > 0 else -d
            w = dd.dot(n)
            hit = bvh.ray_cast(p, Vector(dd), dist)
            tot += w
            if hit[0] is not None:
                occ += w * (1.0 - hit[3] / dist) ** 0.5
        out[i] = occ / tot
    return out


def blur(vals, obj, iters=2):
    e = get_edges(obj)
    for _ in range(iters):
        vals = 0.5 * vals + 0.5 * neighbor_avg(vals, e, len(vals))
    return vals

# ---------------------------------------------------------------- colour / materials

MAT_DEFS = {
    "flesh": dict(rough=0.32, emit=None),
    "flesh_dark": dict(rough=0.25, emit=None),
    "bone": dict(rough=0.45, emit=None),
    "metal": dict(rough=0.55, metallic=0.7, emit=None),
    "rubber": dict(rough=0.6, emit=None),
    "glow_bile": dict(rough=0.15, emit=(0.75, 0.95, 0.15), strength=3.0),
    "glow_furnace": dict(rough=0.4, emit=(1.0, 0.42, 0.06), strength=12.0),
    "glow_red": dict(rough=0.3, emit=(1.0, 0.05, 0.02), strength=14.0),
}
COLOR_ATTR = "Col"


def material(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    d = MAT_DEFS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = COLOR_ATTR
    nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = d["rough"]
    if "metallic" in d:
        bsdf.inputs["Metallic"].default_value = d["metallic"]
    if name.startswith("flesh"):
        bsdf.inputs["Coat Weight"].default_value = 0.35
        bsdf.inputs["Coat Roughness"].default_value = 0.12
    if d.get("emit"):
        e = d["emit"]
        bsdf.inputs["Emission Color"].default_value = (*e, 1)
        bsdf.inputs["Emission Strength"].default_value = d["strength"]
    return m


def set_material(obj, name):
    obj.data.materials.clear()
    obj.data.materials.append(material(name))
    obj.data.polygons.foreach_set("material_index", [0] * len(obj.data.polygons))


def assign_faces(obj, names, fn):
    """fn(face_centers, face_normals) -> index array into names"""
    me = obj.data
    me.materials.clear()
    for n in names:
        me.materials.append(material(n))
    c = np.zeros(len(me.polygons) * 3)
    me.polygons.foreach_get("center", c)
    nn = np.zeros(len(me.polygons) * 3)
    me.polygons.foreach_get("normal", nn)
    idx = fn(c.reshape(-1, 3), nn.reshape(-1, 3)).astype(np.int32)
    me.polygons.foreach_set("material_index", idx)


def set_colors(obj, rgb):
    me = obj.data
    if COLOR_ATTR in me.color_attributes:
        me.color_attributes.remove(me.color_attributes[COLOR_ATTR])
    ca = me.color_attributes.new(COLOR_ATTR, "FLOAT_COLOR", "POINT")
    rgb = np.array(rgb, float)
    bad = ~np.isfinite(rgb).all(1)
    if bad.any():
        rgb[bad] = np.nanmean(rgb[~bad], axis=0)
    rgba = np.ones((len(me.vertices), 4))
    rgba[:, :3] = np.clip(rgb, 0, 1)
    ca.data.foreach_set("color", rgba.ravel())
    me.color_attributes.active_color = ca
    for i, a in enumerate(me.color_attributes):
        if a.name == COLOR_ATTR:
            me.color_attributes.render_color_index = i


def mix(a, b, t):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    t = np.asarray(t, float)
    if t.ndim == 1:
        t = t[:, None]
    return a * (1 - t) + b * t

# ---------------------------------------------------------------- rig


def armature(name, bones):
    """bones: list of dicts name, head, tail, parent, connect, deform"""
    ad = bpy.data.armatures.new(name)
    ao_ = link(bpy.data.objects.new(name, ad))
    bpy.context.view_layer.objects.active = ao_
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for b in bones:
        e = ad.edit_bones.new(b["name"])
        e.head = Vector(b["head"])
        e.tail = Vector(b["tail"])
        e.use_deform = b.get("deform", True)
        if b.get("roll") is not None:
            e.roll = b["roll"]
        eb[b["name"]] = e
    for b in bones:
        if b.get("parent"):
            eb[b["name"]].parent = eb[b["parent"]]
            eb[b["name"]].use_connect = b.get("connect", False)
    bpy.ops.object.mode_set(mode="OBJECT")
    return ao_


def chain(prefix, pts, parent, deform_last_end=True):
    """helper: pts list of joint positions; returns bones names prefix_a.. plus _end"""
    pass


def weights(obj, bone_segs, bone_scale, candidates=None, rigid=None, power=4.0, smooth_iters=3,
            region=None):
    """bone_segs: name -> (head, tail). bone_scale: name -> influence radius.
    candidates: list of bone names (deforming) to consider.
    rigid: per-vertex array of bone name or None (forced 100%).
    region: optional fn(co) -> (n, nb) multiplier mask over candidates."""
    co = get_co(obj)
    names = list(candidates)
    nb = len(names)
    D = np.zeros((len(co), nb))
    for j, nm in enumerate(names):
        a, b = (np.array(x, float) for x in bone_segs[nm])
        ab = b - a
        t = np.clip(((co - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
        p = a + t[:, None] * ab
        D[:, j] = np.linalg.norm(co - p, axis=1) / bone_scale.get(nm, 0.1)
    W = 1.0 / np.maximum(D, 1e-4) ** power
    if region is not None:
        W *= region(co)
    W /= W.sum(1, keepdims=True) + 1e-12
    locked = np.zeros(len(co), bool)
    if rigid is not None:
        for i, r in enumerate(rigid):
            if r is not None:
                W[i] = 0
                W[i, names.index(r)] = 1
                locked[i] = True
    e = get_edges(obj)
    for _ in range(smooth_iters):
        Wn = 0.5 * W + 0.5 * neighbor_avg(W, e, len(co))
        W = np.where(locked[:, None], W, Wn)
    # top 4
    order = np.argsort(-W, axis=1)
    keep = np.zeros_like(W, bool)
    np.put_along_axis(keep, order[:, :4], True, axis=1)
    W = np.where(keep, W, 0)
    W[W < 0.01] = 0
    s = W.sum(1, keepdims=True)
    bad = s[:, 0] <= 0
    W[bad, order[bad, 0]] = 1
    W /= W.sum(1, keepdims=True)
    obj.vertex_groups.clear()
    vgs = [obj.vertex_groups.new(name=nm) for nm in names]
    for j in range(nb):
        nz = np.nonzero(W[:, j])[0]
        for i in nz:
            vgs[j].add([int(i)], float(W[i, j]), "REPLACE")
    return W, names


def bind(mesh_obj, arm_obj):
    mesh_obj.parent = arm_obj
    m = mesh_obj.modifiers.new("Armature", "ARMATURE")
    m.object = arm_obj

# ---------------------------------------------------------------- export / render


def export_glb(path, objs):
    for o in bpy.context.scene.objects:
        o.select_set(o in objs)
    bpy.context.view_layer.objects.active = objs[0]
    kw = dict(filepath=path, export_format="GLB", use_selection=True, export_yup=True,
              export_apply=True, export_skins=True, export_animations=False,
              export_cameras=False, export_lights=False, export_vertex_color="ACTIVE",
              export_all_influences=False, export_morph=False, export_materials="EXPORT")
    bpy.ops.export_scene.gltf(**kw)
    print("EXPORTED", path, os.path.getsize(path), "bytes")


def _setup_render(w, h, samples=32):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.eevee.taa_render_samples = samples
    try:
        sc.eevee.use_shadows = True
        sc.eevee.shadow_ray_count = 2
        sc.eevee.shadow_step_count = 8
    except Exception:
        pass
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast" if "AgX - Medium High Contrast" in [i.identifier for i in sc.view_settings.bl_rna.properties["look"].enum_items] else "None"
    if sc.world is None:
        sc.world = bpy.data.worlds.new("w")
    sc.world.use_nodes = True
    return sc


def _world(col, strength=1.0):
    w = bpy.context.scene.world
    bg = w.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (*col, 1)
    bg.inputs[1].default_value = strength


def _cam(name, loc, target, fov_deg=30, ortho=None):
    cd = bpy.data.cameras.new(name)
    cd.sensor_fit = "VERTICAL"
    cd.angle_y = math.radians(fov_deg)
    cd.clip_start = 0.05
    cd.clip_end = 200
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    c = link(bpy.data.objects.new(name, cd))
    c.location = Vector(loc)
    d = Vector(target) - Vector(loc)
    up = "Y" if abs(d.normalized().z) < 0.999 else "Y"
    c.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return c


def _light(name, kind, loc, target, energy, color=(1, 1, 1), size=0.1, spot=None, blend=0.2):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    ld.use_shadow = True
    if hasattr(ld, "shadow_soft_size"):
        ld.shadow_soft_size = size
    if kind == "AREA":
        ld.size = size
    if kind == "SPOT":
        ld.spot_size = math.radians(spot or 45)
        ld.spot_blend = blend
    o = link(bpy.data.objects.new(name, ld))
    o.location = Vector(loc)
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


_tmp = []


def _clear_rig():
    for o in list(bpy.context.scene.objects):
        if o.name.startswith("_r_"):
            bpy.data.objects.remove(o, do_unlink=True)


def _ground(size=60, col=(0.05, 0.05, 0.055)):
    o = prim("cube", "_r_ground", loc=(0, 0, -0.01), scale=(size, size, 0.02))
    m = bpy.data.materials.new("_r_groundmat")
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = 0.7
    o.data.materials.append(m)
    return o


PREVIEW_GLOW = {"glow_bile": 1.3, "glow_furnace": 1.8, "glow_red": 5.0}


def preview_glow():
    """after export: drive emission by vertex colour so painted detail shows in previews"""
    for name, st in PREVIEW_GLOW.items():
        m = bpy.data.materials.get(name)
        if not m:
            continue
        nt = m.node_tree
        b = nt.nodes.get("Principled BSDF")
        vc = [n for n in nt.nodes if n.bl_idname == "ShaderNodeVertexColor"][0]
        nt.links.new(vc.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = st


def _render(path):
    preview_glow()
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def _stitch(paths, out, cols=None):
    imgs = []
    for p in paths:
        im = bpy.data.images.load(p)
        w, h = im.size
        a = np.zeros(w * h * 4, dtype=np.float32)
        im.pixels.foreach_get(a)
        imgs.append(a.reshape(h, w, 4))
        bpy.data.images.remove(im)
    H = max(i.shape[0] for i in imgs)
    imgs = [np.pad(i, ((H - i.shape[0], 0), (0, 0), (0, 0))) for i in imgs]
    full = np.concatenate(imgs, axis=1)
    h, w = full.shape[:2]
    img = bpy.data.images.new("stitch", w, h, alpha=True)
    img.pixels.foreach_set(full.ravel())
    img.filepath_raw = out
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)
    for p in paths:
        try:
            os.remove(p)
        except OSError:
            pass
    print("PREVIEW", out)


def render_sheet(out, center, radius, views=("front", "back", "top"), px=440, extra_lights=True):
    """neutral turnaround: front-3/4, back-3/4, top"""
    _clear_rig()
    _setup_render(px, px, 24)
    _world((0.18, 0.18, 0.2), 1.0)
    c = Vector(center)
    _ground(col=(0.12, 0.12, 0.13))
    _light("_r_key", "AREA", c + Vector((3, -4, 5)) * radius, c, 500 * radius * radius, size=2 * radius)
    _light("_r_fill", "AREA", c + Vector((-4, -1, 2)) * radius, c, 150 * radius * radius, color=(0.8, 0.85, 1), size=3 * radius)
    _light("_r_rim", "AREA", c + Vector((0, 5, 3)) * radius, c, 350 * radius * radius, size=2 * radius)
    dist = radius / math.sin(math.radians(15)) * 1.05
    tmp = []
    for v in views:
        if v == "front":
            d = Vector((0.55, -0.75, 0.38))
        elif v == "back":
            d = Vector((-0.55, 0.75, 0.42))
        elif v == "side":
            d = Vector((1, 0, 0.15))
        elif v == "front0":
            d = Vector((0.0, -1, 0.2))
        else:
            d = Vector((0, -0.001, 1))
        d.normalize()
        cam = _cam("_r_cam_" + v, c + d * dist, c, 30)
        bpy.context.scene.camera = cam
        p = os.path.join(PREV_DIR, "_tmp_%s.png" % v)
        _render(p)
        tmp.append(p)
    _stitch(tmp, out)
    _clear_rig()


def render_game(out, zoom_out=None, target=(0, 0, 0.3), px=900, spot=40, zoom=4.0):
    """game camera: 22 m, 62 deg pitch, 30 deg vfov, from -Y."""
    _clear_rig()
    _setup_render(px, int(px * 9 / 16), 32)
    _world((0, 0, 0), 0.0)
    _ground(col=(0.045, 0.047, 0.05))
    t = Vector(target)
    pitch = math.radians(62)
    loc = t + Vector((0, -math.cos(pitch), math.sin(pitch))) * 22
    # cool spot from above-front
    _light("_r_spot", "SPOT", t + Vector((1.5, -3.5, 9.0)), t, 2600, color=(0.72, 0.86, 1.0), size=0.03, spot=spot, blend=0.35)
    # flashlight at ground level from player
    _light("_r_flash", "SPOT", t + Vector((-0.6, -5.5, 1.1)), t + Vector((0, 0, 0.2)), 900, color=(1.0, 0.95, 0.85), size=0.02, spot=28, blend=0.25)
    cam = _cam("_r_gcam", loc, t, 30)
    bpy.context.scene.camera = cam
    _render(out)
    print("PREVIEW", out)
    if zoom_out:
        cam.data.angle_y = 2 * math.atan(math.tan(math.radians(15)) / zoom)
        _render(zoom_out)
        print("PREVIEW", zoom_out)
    _clear_rig()


def report(obj, arm=None):
    co = get_co(obj)
    print("REPORT", obj.name, "tris", tri_count(obj), "bbox min", co.min(0).round(3), "max", co.max(0).round(3))
    print("MATS", [m.name for m in obj.data.materials])
    if arm:
        print("BONES", [b.name for b in arm.data.bones])
