"""Regenerates public/models/props.glb. Usage:
   Blender -b --python tools/blender/props/build_props.py [-- name1 name2 ...] [--out path]
"""
import sys, os, importlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
import lib
for mod in ('props_a', 'props_b', 'props_c', 'props_d'):
    if os.path.exists(os.path.join(HERE, mod + '.py')):
        importlib.import_module(mod)

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
args = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
out = os.path.join(ROOT, 'public', 'models', 'props.glb')
if '--out' in args:
    i = args.index('--out'); out = args[i + 1]; args = args[:i] + args[i + 2:]
names = args or list(lib.REG.keys())

lib.clean_scene()
coll = bpy.context.scene.collection
tris = {}
for n in names:
    try:
        P = lib.REG[n]()
    except Exception:
        import traceback; print('FAILED', n); traceback.print_exc(); continue
    tris[n] = P.stats() + sum(c.stats() for c in P.children)
    P.build(coll)
print('BUILT', len(tris), 'props; tris', sum(tris.values()))
for n, t in tris.items():
    print('TRIS', n, t)
os.makedirs(os.path.dirname(out), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=False, export_apply=True,
                          export_yup=True, export_cameras=False, export_lights=False, export_animations=False)
print('EXPORTED', out, os.path.getsize(out))
