"""Re-import every GLB in a fresh scene and print a validation report.
Run: Blender -b --python verify.py"""
import bpy, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "public", "models"))
for f in ["crawler.glb", "spitter.glb", "boss.glb", "gibs.glb", "growths.glb"]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    p = os.path.join(OUT, f)
    bpy.ops.import_scene.gltf(filepath=p)
    print("=" * 70)
    print(f, os.path.getsize(p), "bytes")
    for o in bpy.context.scene.objects:
        if o.type == "ARMATURE":
            print("  ARMATURE", o.name, "bones:", len(o.data.bones))
            print("   ", [b.name for b in o.data.bones])
            print("    anims:", len(bpy.data.actions))
        if o.type == "MESH":
            me = o.data
            dg = bpy.context.evaluated_depsgraph_get()
            co = np.array([(o.matrix_world @ v.co)[:] for v in me.vertices])
            tris = sum(len(pp.vertices) - 2 for pp in me.polygons)
            cols = [a.name for a in me.color_attributes]
            vg = [g.name for g in o.vertex_groups]
            # influences
            maxinf = max((len([g for g in v.groups if g.weight > 0]) for v in me.vertices), default=0)
            unweighted = sum(1 for v in me.vertices if sum(g.weight for g in v.groups) < 0.99) if vg else 0
            print("  MESH", o.name, "tris", tris, "verts", len(me.vertices), "colors", cols,
                  "mats", [m.name for m in me.materials])
            print("    bbox(blender Z-up) min", co.min(0).round(3), "max", co.max(0).round(3))
            if vg:
                print("    groups", len(vg), "max influences", maxinf, "under-weighted verts", unweighted,
                      "armature-mod", any(m.type == "ARMATURE" for m in o.modifiers))
            if cols:
                ca = me.color_attributes[0]
                c = np.zeros(len(ca.data) * 4)
                ca.data.foreach_get("color", c)
                c = c.reshape(-1, 4)[:, :3]
                print("    vcol domain", ca.domain, "mean", c.mean(0).round(3), "min", c.min(0).round(3), "max", c.max(0).round(3))
