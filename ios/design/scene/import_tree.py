"""Bring a ready-made tree (Poly Haven, CC0) into the main screen: its trunk, branches and leaves as separate meshes, set
on its foot, scaled to his tree's height, with the wind and shade data the page's tree shaders read in its vertices.

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P scene/import_tree.py -- <tree.gltf> <out> <height m> [turn°] [keep]

With keep (e.g. 0.2) the meshes are thinned for the phone — each part keeps about that share of its triangles (the
trunk and branches a little less) — and the result is written Draco-compressed as one JSON file (<out>.gltf.json, its
data inside), which the page's host serves; without it, a plain .glb.

Vertex colour (COLOR_0): r = shade deep in the crown, g = how much it bends in the wind (more toward the top and the
crown's edge), b = phase (nearby parts move together), a = 1 for leaves. The page textures each mesh with the tree's
own photographed maps; the leaves' colour is turned to autumn by scene/autumn_leaves.py.
"""
import sys

import bpy
import numpy as np

args = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT, HEIGHT = args[0], args[1], float(args[2])
TURN = float(args[3]) if len(args) > 3 else 0.0
KEEP = float(args[4]) if len(args) > 4 else 0.0

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
bpy.ops.import_scene.gltf(filepath=SRC)
obs = [o for o in bpy.data.objects if o.type == 'MESH']
for o in obs:
    o.select_set(True)
bpy.context.view_layer.objects.active = obs[0]
if len(obs) > 1:
    bpy.ops.object.join()
ob = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.mesh.separate(type='MATERIAL')
parts = [o for o in bpy.data.objects if o.type == 'MESH']

# all parts together: stand the tree on its foot, turn it, scale it to his tree's height (Blender: z is up)
allv = np.concatenate([np.array([v.co for v in o.data.vertices]) for o in parts])
lo, hi = allv.min(0), allv.max(0)
foot = np.array([(lo[0] + hi[0])/2, (lo[1] + hi[1])/2, lo[2]])
trunk = [o for o in parts if 'trunk' in o.active_material.name.lower()]
if trunk:                                                       # the foot: the middle of the trunk's lowest metre
    tv = np.array([v.co for v in trunk[0].data.vertices]); low = tv[tv[:, 2] < lo[2] + 0.05*(hi[2] - lo[2])]
    foot[:2] = low[:, :2].mean(0)
s = HEIGHT/(hi[2] - lo[2])
c, d = np.cos(np.radians(TURN)), np.sin(np.radians(TURN))
leafv = None
for o in parts:
    V = (np.array([v.co for v in o.data.vertices]) - foot)*s
    V = np.stack([c*V[:, 0] - d*V[:, 1], d*V[:, 0] + c*V[:, 1], V[:, 2]], 1)
    o.data.vertices.foreach_set('co', V.astype(np.float32).ravel()); o.data.update()
    if 'leaves' in o.active_material.name.lower():
        leafv = V if leafv is None else np.concatenate([leafv, V])

# the crown's density on a grid: the more leaves around and above a point, the less sky reaches it
cell = 0.6
gmin = leafv.min(0) - cell*3
gsize = np.ceil((leafv.max(0) + cell*3 - gmin)/cell).astype(int)
grid = np.zeros(gsize, np.float32)
idx = ((leafv - gmin)/cell).astype(int)
np.add.at(grid, (idx[:, 0], idx[:, 1], idx[:, 2]), 1)
for ax in range(3):                                             # a soft blur, a few cells wide
    for _ in range(2):
        grid = (np.roll(grid, 1, ax) + 2*grid + np.roll(grid, -1, ax))/4
above = np.cumsum(grid[:, :, ::-1], axis=2)[:, :, ::-1]          # leaves above each cell
dens = grid + 0.35*above
dens /= np.percentile(dens[dens > 0], 95)
centre = leafv.mean(0); rad = np.percentile(np.linalg.norm(leafv[:, :2] - centre[:2], axis=1), 95)
top = leafv[:, 2].max()

for o in parts:
    V = np.array([v.co for v in o.data.vertices])
    gi = np.clip(((V - gmin)/cell).astype(int), 0, gsize - 1)
    ao = np.clip(np.exp(-1.6*dens[gi[:, 0], gi[:, 1], gi[:, 2]]), 0.22, 1)
    out = np.clip(np.linalg.norm(V[:, :2] - centre[:2], axis=1)/rad, 0, 1)
    bend = np.clip((V[:, 2]/top)**1.6*(0.4 + 0.6*out), 0, 1)
    phase = (np.sin(V[:, 0]*0.9 + V[:, 1]*1.3)*0.5 + 0.5)*0.6 + (np.sin(V[:, 2]*1.7 + V[:, 0]*0.5)*0.5 + 0.5)*0.4
    leaf = 1.0 if 'leaves' in o.active_material.name.lower() else 0.0
    col = np.stack([ao, bend, phase, np.full(len(V), leaf)], 1).astype(np.float32)
    for a in list(o.data.color_attributes):
        o.data.color_attributes.remove(a)
    ca = o.data.color_attributes.new(name='Col', type='BYTE_COLOR', domain='POINT')
    ca.data.foreach_set('color', col.ravel())
    o.name = o.data.name = ('leaves' if leaf else 'bark') + '_' + o.active_material.name
    print(f'{o.name}: {len(o.data.polygons)} faces')

if KEEP:                                                        # thinned for the phone: far away, a leaf is a few pixels
    for o in parts:
        m = o.modifiers.new('thin', 'DECIMATE'); m.ratio = KEEP if o.name.startswith('leaves') else KEEP*0.6
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='thin')
        print(f'{o.name}: thinned to {len(o.data.polygons)} faces')
for o in parts:
    o.select_set(True)
kw = dict(export_format='GLB', use_selection=False, export_yup=True, export_texcoords=True, export_normals=True,
          export_materials='NONE', export_vertex_color='ACTIVE')
if not KEEP:
    bpy.ops.export_scene.gltf(filepath=OUT, **kw); print('→', OUT)
else:
    import base64, json, pathlib
    glb = pathlib.Path(OUT + '.tmp.glb')
    bpy.ops.export_scene.gltf(filepath=str(glb), export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=7,
                              export_draco_position_quantization=14, export_draco_normal_quantization=10,
                              export_draco_texcoord_quantization=12, export_draco_color_quantization=8, **kw)
    raw = glb.read_bytes(); glb.unlink()
    jlen = int.from_bytes(raw[12:16], 'little'); doc = json.loads(raw[20:20 + jlen])
    blen = int.from_bytes(raw[20 + jlen:24 + jlen], 'little'); bin_ = raw[28 + jlen:28 + jlen + blen]
    doc['buffers'] = [{'byteLength': len(bin_), 'uri': 'data:application/octet-stream;base64,' + base64.b64encode(bin_).decode()}]
    out = pathlib.Path(OUT + '.gltf.json'); out.write_text(json.dumps(doc, separators=(',', ':')))
    print('→', out, out.stat().st_size//1024, 'KB')
