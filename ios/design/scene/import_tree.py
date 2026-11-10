"""Bring a ready-made tree (Poly Haven, CC0) into the main screen: its trunk, branches and leaves as separate meshes, set
on its foot, scaled to his tree's height, with the wind and shade data the page's tree shaders read in its vertices.

    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P scene/import_tree.py -- <tree.gltf> <out> <height m> [turn°] [keep]

With keep (e.g. 0.2) the meshes are thinned for the phone — each part keeps about that share of its triangles (the
trunk and branches a little less) — and the result is written Draco-compressed as one JSON file (<out>.gltf.json, its
data inside), which the page's host serves. Use an output name ending in .gltf for the same delivery format without
thinning; any other output name without keep writes a plain .glb.

Vertex colour (COLOR_0): r = sky visibility: the share of the sky that reaches the vertex, traced through the tree (sky_bake.py), g = branch bend weight, b = branch phase, a = 1 for leaves.
WINDPIVOT holds the branch's attachment and effective length; WINDCLUSTER holds the leaf cluster's branch attachment
and phase. The page textures each mesh with the tree's own photographed maps; the leaves' colour is turned to autumn by
scene/autumn_leaves.py.
"""
import os
import sys

import bpy
import numpy as np
from mathutils.kdtree import KDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sky_bake  # noqa: E402

args = sys.argv[sys.argv.index('--') + 1:]
SRC, OUT, HEIGHT = args[0], args[1], float(args[2])
TURN = float(args[3]) if len(args) > 3 else 0.0
KEEP = float(args[4]) if len(args) > 4 else 0.0
# every leaf card grows about its own middle (SpeedTree's Grow Scale): the crown had sky showing through 15 % of its outline
# (his picture: 9 %), and the leaves on the cards read as specks from 30 m
LEAF_GROW = 1.35

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
bpy.ops.import_scene.gltf(filepath=SRC)
parts = [o for o in bpy.data.objects if o.type == 'MESH']
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

def kind(o):
    names = [o.name, o.data.name] + [m.name for m in o.data.materials if m]
    names = ' '.join(names).lower()
    if 'leaves' in names or 'leaf' in names:
        return 'leaves'
    return 'trunk' if 'trunk' in names else 'branches'

kinds = {o: kind(o) for o in parts}

# all parts together: stand the tree on its foot, turn it, scale it to his tree's height (Blender: z is up)
allv = np.concatenate([np.array([v.co for v in o.data.vertices]) for o in parts])
lo, hi = allv.min(0), allv.max(0)
foot = np.array([(lo[0] + hi[0])/2, (lo[1] + hi[1])/2, lo[2]])
trunk = [o for o in parts if kinds[o] == 'trunk']
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
    if kinds[o] == 'leaves':
        leafv = V if leafv is None else np.concatenate([leafv, V])

# Weld coincident UV/normal splits only for the topology search; the exported mesh keeps its original vertices.
def branch_components(o):
    n = len(o.data.vertices)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[b] = a

    same = {}
    for v in o.data.vertices:
        key = tuple(v.co)
        if key in same:
            union(v.index, same[key])
        else:
            same[key] = v.index
    for e in o.data.edges:
        union(*e.vertices)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())

trunkv = np.concatenate([np.array([v.co for v in o.data.vertices]) for o in trunk])
levels = np.linspace(0, trunkv[:, 2].max(), max(2, int(trunkv[:, 2].max()/0.4) + 1))
centres = []
for z in levels:
    near = trunkv[np.abs(trunkv[:, 2] - z) < 0.5]
    if not len(near):
        near = trunkv[np.argsort(np.abs(trunkv[:, 2] - z))[:256]]
    centres.append(np.median(near[:, :2], axis=0))
centres = np.array(centres)

def centre_at(z):
    return np.stack([np.interp(z, levels, centres[:, axis]) for axis in range(2)], -1)

wind = {}
branch_v, branch_pivot, branch_phase, branch_weight = [], [], [], []
component_count = 0
for o in [o for o in parts if kinds[o] == 'branches']:
    V = np.array([v.co for v in o.data.vertices])
    pivots = np.zeros((len(V), 4), np.float32)
    pivots[:, 3] = 1
    weights = np.zeros(len(V), np.float32)
    phases = np.zeros(len(V), np.float32)
    for ids in branch_components(o):
        component_count += 1
        P = V[ids]
        radial = P[:, :2] - centre_at(P[:, 2])
        root = int(np.argmin(np.sum(radial*radial, axis=1)))
        pivot = P[root]
        distance = np.linalg.norm(P - pivot, axis=1)
        radius = max(0.35, float(np.percentile(distance, 95)))
        ramp = min(1.4, max(0.25, radius*0.3))
        q = np.clip(distance/ramp, 0, 1)
        flex = np.clip(2.5/radius, 0.65, 1.4)
        phase = (np.sin(pivot[0]*0.9 + pivot[1]*1.3)*0.5 + 0.5)*0.6 + (np.sin(pivot[2]*1.7 + pivot[0]*0.5)*0.5 + 0.5)*0.4
        pivots[ids, :3] = pivot
        pivots[ids, 3] = np.clip(radius/flex, 0.45, 8)
        weights[ids] = q*q*(3 - 2*q)
        phases[ids] = phase
    wind[o] = (pivots, weights, phases)
    branch_v.append(V); branch_pivot.append(pivots)
    branch_phase.append(phases); branch_weight.append(weights)

branch_v = np.concatenate(branch_v)
branch_pivot = np.concatenate(branch_pivot)
branch_phase = np.concatenate(branch_phase)
branch_weight = np.concatenate(branch_weight)
kd = KDTree(len(branch_v))
for i, p in enumerate(branch_v):
    kd.insert(p, i)
kd.balance()

# Small spatial leaf clusters inherit the branch at their actual nearest bark attachment. A whole leaf goes into one
# cluster, by where its middle is, so its corners never turn about different branches (split by vertex, 4 leaves in 10
# tore into shards in the wind).
def leaf_middles(o):
    V = np.array([v.co for v in o.data.vertices])
    middle = np.empty_like(V)
    for ids in branch_components(o):
        middle[ids] = V[ids].mean(0)
    return middle

leaf_middle = np.concatenate([leaf_middles(o) for o in parts if kinds[o] == 'leaves'])
# grow every leaf card about its own middle; the middles stay put, so the wind data (per card) is unchanged
leaf_parts = [o for o in parts if kinds[o] == 'leaves']
grown = []
at = 0
for o in leaf_parts:
    n = len(o.data.vertices)
    middle = leaf_middle[at:at + n]
    at += n
    V0 = np.empty((n, 3), np.float64)
    o.data.vertices.foreach_get('co', V0.ravel())
    V1 = middle + LEAF_GROW*(V0 - middle)
    o.data.vertices.foreach_set('co', V1.astype(np.float32).ravel()); o.data.update()
    grown.append(V1)
leafv = np.concatenate(grown)
print(f'leaf cards grown ×{LEAF_GROW} about their middles: {len(leafv)} vertices')
cell = 0.55
cells = np.floor(leaf_middle/cell).astype(np.int64) + 512
keys = (cells[:, 0] << 42) | (cells[:, 1] << 21) | cells[:, 2]
_, cluster_ids = np.unique(keys, return_inverse=True)
count = int(cluster_ids.max()) + 1
sums = np.stack([np.bincount(cluster_ids, weights=leafv[:, axis], minlength=count) for axis in range(3)], 1)
cluster_centres = sums/np.bincount(cluster_ids, minlength=count)[:, None]
leaf_pivots = np.zeros((count, 4), np.float32)
leaf_clusters = np.zeros((count, 4), np.float32)
leaf_weights = np.zeros(count, np.float32)
leaf_phases = np.zeros(count, np.float32)
for i, p in enumerate(cluster_centres):
    co, nearest, _ = kd.find(p)
    leaf_pivots[i] = branch_pivot[nearest]
    leaf_clusters[i, :3] = co
    leaf_clusters[i, 3] = float((np.sin(np.dot(co, [19.19, 47.77, 91.13]))*24634.6345) % 1)
    leaf_weights[i] = branch_weight[nearest]
    leaf_phases[i] = branch_phase[nearest]
print(f'Wind: {component_count} welded branch components, {count} attached leaf clusters')

pack_min = np.array([-HEIGHT, 0, -HEIGHT])
pack_size = np.array([2*HEIGHT, HEIGHT, 2*HEIGHT])
def pack_wind(values, has_length=False):
    packed = values.copy()
    packed[:, :3] = (np.stack([values[:, 0], values[:, 2], -values[:, 1]], 1) - pack_min)/pack_size
    if has_length:
        packed[:, 3] /= HEIGHT
    return np.round(np.clip(packed, 0, 1)*255)/255

# sky visibility per vertex (sky_bake.py): every triangle is sampled into a 0.1 m grid as an absorber (leaves: their
# leaflets as a semi-transparent volume, bark nearly opaque); then each vertex traces the sky through the tree
SKY_CELL = 0.1
mask_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(sky_bake.__file__))),
                         'field-assets', 'ph', 'jacaranda_cluster_mask.jpg')
sky_parts = {}
for o in parts:
    me = o.data
    me.calc_loop_triangles()
    n = len(me.loop_triangles)
    tri_v = np.empty(n*3, np.int32); me.loop_triangles.foreach_get('vertices', tri_v)
    tri_l = np.empty(n*3, np.int32); me.loop_triangles.foreach_get('loops', tri_l)
    co = np.empty(len(me.vertices)*3, np.float32); me.vertices.foreach_get('co', co)
    nrm = np.empty(len(me.vertices)*3, np.float32); me.vertices.foreach_get('normal', nrm)
    uv = np.zeros((len(me.loops), 2), np.float32)
    if me.uv_layers.active is not None:
        flat = np.empty(len(me.loops)*2, np.float32); me.uv_layers.active.data.foreach_get('uv', flat)
        uv = flat.reshape(-1, 2)
    sky_parts[o] = dict(tv=tri_v.reshape(-1, 3), tl=tri_l.reshape(-1, 3), co=co.reshape(-1, 3), nrm=nrm.reshape(-1, 3), uv=uv)

allco = np.concatenate([sky_parts[o]['co'] for o in parts])
lo = allco.min(0) - 0.3
sky_shape = np.ceil((allco.max(0) - allco.min(0) + 0.6)/SKY_CELL).astype(int)
sigma = np.zeros(sky_shape, np.float32)
B = sky_bake.subtriangle_bary(4).astype(np.float32)

def samples(o):
    """Per chunk of triangles: 16 points per triangle (P), their UVs (U), the triangle areas (area)."""
    s = sky_parts[o]
    for start in range(0, len(s['tv']), 200000):
        tv = s['tv'][start:start + 200000]; tl = s['tl'][start:start + 200000]
        tri = np.stack([s['co'][tv[:, i]] for i in range(3)], 1)
        area = 0.5*np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
        yield np.einsum('kb,nbc->nkc', B, tri), np.einsum('kb,nbc->nkc', B, s['uv'][tl]), area

img = bpy.data.images.load(os.path.abspath(mask_path))
W, H = img.size
px = np.empty(W*H*4, np.float32); img.pixels.foreach_get(px)
bpy.data.images.remove(img)
px = px.reshape(H, W, 4)                                        # Blender rows run bottom-up, like the UVs

def leaflet(U, flipped):
    col = np.floor(U[..., 0]*W).astype(np.int64) % W
    v = 1 - U[..., 1] if flipped else U[..., 1]
    row = np.floor(v*H).astype(np.int64) % H
    return px[row, col, 0] > 0.5

direct = flipped = total = 0
for o in parts:
    if kinds[o] != 'leaves':
        continue
    for P, U, area in samples(o):
        direct += int(leaflet(U, False).sum()); flipped += int(leaflet(U, True).sum()); total += U.shape[0]*U.shape[1]
print(f'mask share: direct {direct/total:.3f}, flipped {flipped/total:.3f}')
use_flip = flipped > direct
if use_flip:
    print('mask: the direct reading is the lower one, so the flipped reading is used')

for o in parts:
    for P, U, area in samples(o):
        if kinds[o] == 'leaves':
            w = (area/16)[:, None]*leaflet(U, use_flip)*0.5/SKY_CELL**3
        elif kinds[o] == 'trunk' or kinds[o] == 'branches':
            w = np.broadcast_to((area/16)[:, None]*3.0/SKY_CELL**3, P.shape[:2])
        else:
            continue
        sky_bake.deposit(sigma, lo, SKY_CELL, P.reshape(-1, 3), np.asarray(w, np.float64).ravel())

allnrm = np.concatenate([np.zeros_like(sky_parts[o]['nrm']) if kinds[o] == 'leaves' else sky_parts[o]['nrm']
                         for o in parts])
V_all = sky_bake.sky_visibility(sigma, lo, SKY_CELL, allco, normals=allnrm, n_dirs=96, offset=1.0)
sky_v = {}
at = 0
for o in parts:
    m = len(sky_parts[o]['co'])
    sky_v[o] = V_all[at:at + m]; at += m
    p5, p50, p95 = np.percentile(sky_v[o], [5, 50, 95])
    print(f'sky {kinds[o]}: {m} vertices, V p5 {p5:.3f} p50 {p50:.3f} p95 {p95:.3f}')
del sigma

leaf_offset = 0
for o in parts:
    V = np.array([v.co for v in o.data.vertices])
    ao = np.clip(sky_v[o], 0.02, 1)
    leaf = kinds[o] == 'leaves'
    if leaf:
        ids = cluster_ids[leaf_offset:leaf_offset + len(V)]
        pivots = leaf_pivots[ids]
        clusters = leaf_clusters[ids]
        weights = leaf_weights[ids]
        phases = leaf_phases[ids]
        leaf_offset += len(V)
    elif kinds[o] == 'branches':
        pivots, weights, phases = wind[o]
        clusters = np.zeros((len(V), 4), np.float32)
    else:
        pivots = np.zeros((len(V), 4), np.float32)
        pivots[:, 3] = 1
        clusters = np.zeros((len(V), 4), np.float32)
        weights = np.zeros(len(V), np.float32)
        phases = np.zeros(len(V), np.float32)
    col = np.stack([ao, weights, phases, np.full(len(V), float(leaf))], 1).astype(np.float32)
    for a in list(o.data.color_attributes):
        o.data.color_attributes.remove(a)
    ca = o.data.color_attributes.new(name='Col', type='BYTE_COLOR', domain='POINT')
    ca.data.foreach_set('color', col.ravel())
    for name, values, has_length in [('WINDPIVOT', pivots, True), ('WINDCLUSTER', clusters, False)]:
        a = o.data.color_attributes.new(name=name, type='BYTE_COLOR', domain='POINT')
        a.data.foreach_set('color', pack_wind(values, has_length).astype(np.float32).ravel())
    o.data.color_attributes.active_color_index = 0
    material = o.active_material.name if o.active_material else kinds[o]
    o.name = o.data.name = kinds[o] + '_' + material
    print(f'{o.name}: {len(o.data.polygons)} faces')

if KEEP:                                                        # thinned for the phone: far away, a leaf is a few pixels
    for o in parts:
        m = o.modifiers.new('thin', 'DECIMATE'); m.ratio = KEEP if o.name.startswith('leaves') else KEEP*0.6
        bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='thin')
        print(f'{o.name}: thinned to {len(o.data.polygons)} faces')
for o in parts:
    o.select_set(True)
kw = dict(export_format='GLB', use_selection=False, export_yup=True, export_texcoords=True, export_normals=True,
          export_materials='NONE', export_vertex_color='ACTIVE', export_attributes=True)
if not KEEP and not OUT.endswith('.gltf'):
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
    out = pathlib.Path(OUT + ('' if OUT.endswith('.gltf') else '.gltf') + '.json'); out.write_text(json.dumps(doc, separators=(',', ':')))
    print('→', out, out.stat().st_size//1024, 'KB')
