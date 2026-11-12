"""Re-imports public/models/props.glb in a fresh Blender and writes public/models/props.json.
Blender -b --python tools/blender/props/verify_props.py [-- glb json]"""
import sys, os, json
import bpy
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
a = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
glb = a[0] if a else os.path.join(ROOT, 'public', 'models', 'props.glb')
out = a[1] if len(a) > 1 else os.path.join(ROOT, 'public', 'models', 'props.json')
sys.path.insert(0, HERE)
from spec_names import SPEC
ALLOWED = set('metal_plate metal_rust metal_dark metal_bare metal_yellow metal_red rubber belt concrete wood glass cloth screen glow_white glow_red glow_amber glow_cyan glow_green glow_furnace'.split())
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
objs = list(bpy.context.scene.objects)
tops = [o for o in objs if o.parent is None]
res = []
problems = []
for o in sorted(tops, key=lambda o: o.name):
    parts = [o] + list(o.children_recursive)
    pts = []; tris = 0; mats = set()
    for p in parts:
        if p.type != 'MESH':
            continue
        pts += [p.matrix_world @ v.co for v in p.data.vertices]
        tris += sum(len(poly.vertices) - 2 for poly in p.data.polygons)
        for m in p.data.materials:
            mats.add(m.name)
        if not p.data.uv_layers:
            problems.append(f'{p.name}: no UVs')
    mn = Vector((min(q.x for q in pts), min(q.y for q in pts), min(q.z for q in pts)))
    mx = Vector((max(q.x for q in pts), max(q.y for q in pts), max(q.z for q in pts)))
    # Blender (x,y,z) -> glTF (x,z,-y)
    g = lambda v: [round(v.x, 3), round(v.z, 3), round(-v.y, 3)]
    gmin = [round(mn.x, 3), round(mn.z, 3), round(-mx.y, 3)]
    gmax = [round(mx.x, 3), round(mx.z, 3), round(-mn.y, 3)]
    size = [round(gmax[i] - gmin[i], 3) for i in range(3)]
    bad = [m for m in mats if m not in ALLOWED]
    if bad: problems.append(f'{o.name}: bad materials {bad}')
    if (o.location.length > 1e-6): problems.append(f'{o.name}: not at origin')
    if abs(mn.z) > 0.03 and o.name not in ('pickup_key',) and mn.z > 0.03:
        pass
    res.append({'name': o.name, 'size': size, 'bbox_min': gmin, 'bbox_max': gmax, 'tris': tris,
                'children': sorted(c.name for c in o.children_recursive), 'materials': sorted(mats)})
names = [r['name'] for r in res]
for n in SPEC:
    if n not in names:
        problems.append(f'MISSING {n}')
doc = {'units': 'metres', 'axes': 'glTF: +Y up, prop front faces +Z (-Y in Blender); wall props have back on z=0 plane and protrude toward +Z',
       'total_tris': sum(r['tris'] for r in res), 'file_bytes': os.path.getsize(glb), 'props': res}
json.dump(doc, open(out, 'w'), indent=1)
print('VERIFY props', len(res), 'tris', doc['total_tris'], 'bytes', doc['file_bytes'])
for r in res:
    print('P', r['name'], r['size'], 'min', r['bbox_min'], r['tris'], r['children'])
print('PROBLEMS', problems)
