"""Re-import each exported GLB in a fresh scene and print a verification report.
Run: /Applications/Blender.app/Contents/MacOS/Blender -b --python tools/blender/humanoids/verify.py
"""
import bpy, os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hlib import OUT_DIR, glb_report

EXPECT = {
    'player.glb': ['root', 'hips', 'spine', 'chest', 'head', 'head_end'] +
                  ['arm_%s_%s' % (s, p) for s in 'LR' for p in ('upper', 'lower', 'hand', 'end')] +
                  ['leg_%s_%s' % (s, p) for s in 'LR' for p in ('upper', 'lower', 'foot', 'end')],
    'stalker.glb': ['root', 'hips', 'spine', 'chest', 'neck', 'head', 'head_end'] +
                   ['arm_%s_%s' % (s, p) for s in 'LR' for p in ('upper', 'lower', 'hand', 'end')] +
                   ['leg_%s_%s' % (s, p) for s in 'LR' for p in ('upper', 'lower', 'foot', 'end')],
    'brute.glb': ['root', 'hips', 'spine', 'chest', 'head', 'head_end',
                  'arm_R_upper', 'arm_R_lower', 'arm_R_hand', 'arm_R_end',
                  'arm_L_upper', 'arm_L_lower', 'arm_L_end'] +
                 ['leg_%s_%s' % (s, p) for s in 'LR' for p in ('upper', 'lower', 'end')],
    'gun.glb': [],
}

for fn, bones in EXPECT.items():
    path = os.path.join(OUT_DIR, fn)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.data.polygons and 'Color' in o.data.attributes]
    arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    tris = 0; mins = []; maxs = []; mats = set(); maxinf = 0; unweighted = 0; badnorm = 0
    for o in meshes:
        dg = bpy.context.evaluated_depsgraph_get()
        me = o.data
        tris += sum(len(p.vertices) - 2 for p in me.polygons)
        co = np.array([(o.matrix_world @ v.co)[:] for v in me.vertices])
        mins.append(co.min(0)); maxs.append(co.max(0))
        mats |= {m.name for m in me.materials if m}
        for v in me.vertices:
            ws = [g.weight for g in v.groups if g.weight > 0]
            maxinf = max(maxinf, len(ws))
            if arms and not ws:
                unweighted += 1
            elif arms and abs(sum(ws) - 1) > 0.02:
                badnorm += 1
    mn = np.min(mins, 0); mx = np.max(maxs, 0)
    names = [b.name for b in arms[0].data.bones] if arms else []
    missing = [b for b in bones if b not in names]
    extra = [b for b in names if b not in bones]
    rep = dict(file=fn, size_kb=round(os.path.getsize(path) / 1024, 1), tris=tris,
               vertex_colors=bool(meshes), materials=sorted(mats),
               bbox_min=[round(x, 3) for x in mn], bbox_max=[round(x, 3) for x in mx],
               size=[round(x, 3) for x in (mx - mn)], bones=len(names), missing_bones=missing, extra_bones=extra,
               max_influences=maxinf, unweighted_verts=unweighted, unnormalised_verts=badnorm)
    if arms:
        A = arms[0]
        for bn in ('head_end', 'leg_L_end', 'arm_L_end', 'arm_R_end'):
            if bn in A.data.bones:
                b = A.data.bones[bn]
                rep[bn + '_head'] = [round(x, 3) for x in (A.matrix_world @ b.head_local)]
        rep['armature_identity'] = A.matrix_world == A.matrix_world.Identity(4)
    if fn == 'gun.glb':
        mz = bpy.data.objects.get('muzzle')
        rep['muzzle_world'] = [round(x, 3) for x in mz.matrix_world.translation] if mz else None
    print('VERIFY', json.dumps(rep))
    glb_report(path)
