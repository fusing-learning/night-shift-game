"""Contact-sheet / closeup renders of props.glb.
Blender -b --python render_previews.py -- --glb props.glb --names a,b,c --out out.png --view game|3q [--cols 4] [--res 1600x1000]
"""
import sys, os, math
import bpy
from mathutils import Vector

a = sys.argv[sys.argv.index('--') + 1:]
def opt(k, d=None):
    return a[a.index(k) + 1] if k in a else d
glb = opt('--glb'); out = opt('--out'); view = opt('--view', 'game')
names = opt('--names', '').split(',') if opt('--names') else None
cols = int(opt('--cols', 4)); resx, resy = map(int, opt('--res', '1600x1000').split('x'))
az = float(opt('--az', 28))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
alltops = [o for o in bpy.context.scene.objects if o.parent is None]
if names:
    for o in alltops:
        if o.name not in names:
            for c in list(o.children_recursive):
                bpy.data.objects.remove(c, do_unlink=True)
            bpy.data.objects.remove(o, do_unlink=True)
tops = [o for o in bpy.context.scene.objects if o.parent is None]
if names:
    tops.sort(key=lambda o: names.index(o.name))
else:
    tops.sort(key=lambda o: o.name)


def bbox(o):
    pts = []
    for ob in [o] + list(o.children_recursive):
        if ob.type == 'MESH':
            pts += [ob.matrix_world @ v.co for v in ob.data.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx

bbs = {o.name: bbox(o) for o in tops}
sp = max(max(mx.x - mn.x, mx.y - mn.y) for mn, mx in bbs.values()) + 1.2
n = len(tops)
rows = math.ceil(n / cols)
cols = min(cols, n)
for i, o in enumerate(tops):
    r, c = divmod(i, cols)
    o.location = Vector(((c - (cols - 1) / 2) * sp, ((rows - 1) / 2 - r) * sp, 0))
    # label
    mn, mx = bbs[o.name]
    cu = bpy.data.curves.new('lbl', 'FONT'); cu.body = o.name; cu.size = 0.28; cu.align_x = 'CENTER'
    lo = bpy.data.objects.new('lbl', cu)
    lo.location = (o.location.x, o.location.y + mn.y - 0.45, 0.01)
    bpy.context.scene.collection.objects.link(lo)
    m = bpy.data.materials.new('lblm'); m.use_nodes = True
    m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.9, 0.9, 0.3, 1)
    m.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (0.9, 0.9, 0.3, 1)
    m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 0.6
    lo.data.materials.append(m)

W = cols * sp; H = rows * sp
maxz = max(mx.z for mn, mx in bbs.values())

# ground
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.002))
g = bpy.context.object; g.scale = (W + 40, H + 40, 1)
gm = bpy.data.materials.new('ground'); gm.use_nodes = True
gb = gm.node_tree.nodes['Principled BSDF']
gb.inputs['Base Color'].default_value = (0.035, 0.045, 0.055, 1); gb.inputs['Roughness'].default_value = 0.7
g.data.materials.append(gm)

sc = bpy.context.scene
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
wb = world.node_tree.nodes['Background']

cam = bpy.data.cameras.new('cam'); co = bpy.data.objects.new('cam', cam); sc.collection.objects.link(co)
sc.camera = co
cam.sensor_fit = 'VERTICAL'
aspect = resx / resy
cx, cy = 0, 0
if view == 'game':
    cam.angle = math.radians(30)
    pitch = 62
    vf = math.radians(30); hf = 2 * math.atan(math.tan(vf / 2) * aspect)
    d1 = (W + 1) / (2 * math.tan(hf / 2))
    d2 = (H * math.sin(math.radians(pitch)) + maxz * math.cos(math.radians(pitch)) + 1) / (2 * math.tan(vf / 2))
    d = max(d1, d2) * 1.08
    tgt = Vector((0, 0, maxz * 0.25))
    dirv = Vector((0, -math.cos(math.radians(pitch)), math.sin(math.radians(pitch))))
    co.location = tgt + dirv * d
    co.rotation_euler = ((math.pi / 2 - math.radians(pitch)) , 0, 0)
    # sun, cool hard
    wb.inputs['Color'].default_value = (0.02, 0.045, 0.06, 1); wb.inputs['Strength'].default_value = 1.0
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.5; sun.color = (0.6, 0.8, 1.0); sun.angle = math.radians(2)
    so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(25), math.radians(8), math.radians(-20))
    fl = bpy.data.lights.new('fl', 'SUN'); fl.energy = 0.6; fl.color = (1.0, 0.7, 0.45); fl.angle = math.radians(6)
    fo = bpy.data.objects.new('fl', fl); sc.collection.objects.link(fo)
    fo.rotation_euler = (math.radians(80), 0, math.radians(35))
else:
    cam.angle = math.radians(32)
    vf = math.radians(32); hf = 2 * math.atan(math.tan(vf / 2) * aspect)
    el = 33
    Rr = 0.5 * math.sqrt(W * W + H * H + maxz * maxz)
    d = Rr / math.sin(min(vf, hf) / 2) * 0.66
    tgt = Vector((0, 0, maxz * 0.35))
    dirv = Vector((math.sin(math.radians(az)) * math.cos(math.radians(el)), -math.cos(math.radians(az)) * math.cos(math.radians(el)), math.sin(math.radians(el))))
    co.location = tgt + dirv * d
    look = (tgt - co.location).to_track_quat('-Z', 'Y')
    co.rotation_euler = look.to_euler()
    wb.inputs['Color'].default_value = (0.35, 0.4, 0.45, 1); wb.inputs['Strength'].default_value = 1.0
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 2.2; sun.angle = math.radians(25)
    so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(50), math.radians(10), math.radians(25))

sc.render.resolution_x = resx; sc.render.resolution_y = resy
sc.render.filepath = out
sc.render.image_settings.file_format = 'PNG'
sc.view_settings.view_transform = 'AgX'
try:
    sc.render.engine = 'BLENDER_EEVEE'
    sc.eevee.taa_render_samples = 24
except Exception as e:
    print('eevee fail', e)
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 24
bpy.ops.render.render(write_still=True)
print('RENDERED', out)
