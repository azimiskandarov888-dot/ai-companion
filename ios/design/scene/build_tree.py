"""Build his tree as a real 3D tree in Blender, the way game trees are made: a trunk and branches that are meshes, and
thousands of single leaves on the twigs, each turned its own way — so the sun lights every leaf for itself, leaves shade
one another, and the crown reads as a volume.

The shape comes from his picture (mj-15). The trunk follows his trunk. The branches grow by space colonisation (Runions,
Lane & Prusinkiewicz 2007) toward points that fill his crown: each point lies on the ray from the main screen's camera
through a leafy pixel of his picture, at some depth, so from that camera the crown fills his tree's outline. The vertices
carry what the page needs: the shade deep in the crown, how far each part is from the trunk (how much it bends in the
wind), a phase per branch, and each leaf's stalk (where it turns when it flutters).

    /Applications/Blender.app/Contents/MacOS/Blender -b -P scene/build_tree.py
        reads scene/assets/tree-mask.png and field-assets/tree-trace.json; writes field-assets/tree.gltf.json (glTF with
        its data inside; named .json so the page's host serves it)
        (two meshes: "bark" and "leaves"; COLOR_0 = shade, bend, phase, flutter; _PIVOT = where a leaf hangs)
"""
import base64
import json
import math
import pathlib
import random

import bmesh  # noqa: F401  (Blender's)
import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

HERE = pathlib.Path(__file__).resolve().parent
MASK, TRACE, OUT = HERE / 'assets' / 'tree-mask.png', HERE.parent / 'field-assets' / 'tree-trace.json', HERE.parent / 'field-assets' / 'tree.gltf.json'

# the main screen's camera and where the trunk stands, as in field.html (CAM; field.tree().base)
CAM, LOOK, FOV = np.array([0, 2.1, -7.]), np.array([0, 11.4, 43.]), 25.
BASE = np.array([4.05, 5.53, 39.43])
# the tree's numbers
TREE = dict(seed=7,
            points=7000,            # points that fill the crown, for the branches to grow toward
            depth=4.5,              # how far the crown reaches toward us and away in its middle, m
            reach=3.2, kill=0.5,    # a branch feels a point this far away, m; a point is reached this close, m
            step=0.26,              # a branch grows this much a step, m
            up=0.10,                # how much branches lean up as they grow
            tip=0.011, pipe=2.4,    # a twig's radius, m; how branches add up into their parent (da Vinci's rule)
            twig=0.045,             # leaves grow where branches are thinner than this, m
            sprays=2,               # sprays of leaves (a twig with 10–14 leaves, one card) on each such point
            spray=(0.38, 0.6),      # a spray's length, m
            cover=0.62,             # a spray stays only where at least this much of his picture around it is leaves
            near_wood=0.06,         # ... and where his limbs are not right there (so they show)
            bare=0.013)             # twigs thinner than this are left to the sprays (their own twig is drawn on the card)


def mask():
    img = bpy.data.images.load(str(MASK))
    img.colorspace_settings.name = 'Non-Color'
    w, h = img.size
    px = np.empty(w*h*4, np.float32)
    img.pixels.foreach_get(px)
    return px.reshape(h, w, 4)[::-1, :, :3]                     # Blender's images start at the bottom


def thin(img):
    """Zhang–Suen thinning: a shape down to its one-pixel middle line."""
    img = img.astype(np.uint8).copy()
    while True:
        changed = False
        for step in (0, 1):
            P = np.pad(img, 1)
            p2, p3, p4, p5 = P[:-2, 1:-1], P[:-2, 2:], P[1:-1, 2:], P[2:, 2:]
            p6, p7, p8, p9 = P[2:, 1:-1], P[2:, :-2], P[1:-1, :-2], P[:-2, :-2]
            seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            B = sum(q.astype(np.int16) for q in seq[:8])
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(np.int16) for i in range(8))
            c1, c2 = (p2*p4*p6, p4*p6*p8) if step == 0 else (p2*p4*p8, p2*p6*p8)
            k = (img == 1) & (B >= 2) & (B <= 6) & (A == 1) & (c1 == 0) & (c2 == 0)
            if k.any():
                img[k] = 0; changed = True
        if not changed:
            return img


def camera():
    F = (LOOK - CAM)/np.linalg.norm(LOOK - CAM)
    R = np.cross(F, [0, 1, 0]); R /= np.linalg.norm(R)
    U = np.cross(R, F)
    return F, R, U


def main():
    random.seed(TREE['seed']); rng = np.random.default_rng(TREE['seed'])
    T = json.loads(TRACE.read_text())
    m = mask()
    H, half, cx = T['picture'][1], T['picture'][1]/2, T['picture'][0]/2
    tv = math.tan(math.radians(FOV)/2)
    F, R, U = camera()

    def ray(px, py):
        d = F[None] + R[None]*((np.asarray(px) - cx)/half*tv)[:, None] + U[None]*((half - np.asarray(py))/half*tv)[:, None]
        return d/np.linalg.norm(d, axis=1, keepdims=True)

    rb = ray([T['trunkBase'][0]], [T['trunkBase'][1]])[0]
    D = (BASE[2] - CAM[2])/rb[2]                                # along the ray through his trunk's foot
    origin = np.array([BASE[0], BASE[1], BASE[2]])              # the tree's own (0, 0, 0): its foot on our hill
    at = lambda px, py, dz: CAM[None] + ray(px, py)*(D + np.asarray(dz))[:, None] - origin[None]

    # the points of the crown: leafy pixels of his picture, each at a depth — the crown bulges in its middle
    leafy = (m[..., 0] > 0.6) & (m[..., 1] < 0.3)
    ys, xs = np.nonzero(leafy)
    pick = rng.choice(len(xs), TREE['points'], replace=False)
    px, py = xs[pick] + rng.random(len(pick)), ys[pick] + rng.random(len(pick))
    en = np.minimum(1, m[ys[pick], xs[pick], 2]/0.55)
    thick = TREE['depth']*np.sqrt(en*(2 - en))
    pts = at(px, py, rng.uniform(-1, 1, len(pick))*thick)

    # the trunk: his trunk's middle, followed up the wood of his picture to where it forks (near its foot plumes stand in
    # front of it, so it starts where it first shows whole)
    wood = m[..., 1] > 0.5
    def run(y, x0, x1):                                         # the widest stretch of wood in a row, between x0 and x1
        xs = np.nonzero(wood[y, x0:x1])[0] + x0
        if not len(xs): return None
        parts = np.split(xs, np.nonzero(np.diff(xs) > 1)[0] + 1)
        p = max(parts, key=len); return p[0], p[-1]
    y0 = next(y for y in range(int(T['trunkBase'][1]), 1400, -1) if (r_ := run(y, 120, 340)) and r_[1] - r_[0] >= 40)
    l, r = run(y0, 120, 340); x, miss, trunk = (l + r)/2, 0, []
    for y in range(y0, 1050, -1):
        rr = run(y, int(x) - 45, int(x) + 45)
        if not rr or rr[1] - rr[0] < 14:
            miss += 1
            if miss > 15: break
            continue
        miss = 0; l, r = rr
        if (r - l) > 2.2*max(1, np.median([t[2]*2 for t in trunk[-8:]] or [r - l])): break   # it forks: the wood spreads
        x = 0.8*x + 0.2*(l + r)/2
        if y % 20 == 0: trunk.append((x, y, (r - l)/2))
    tp = at([t[0] for t in trunk], [t[1] for t in trunk], np.zeros(len(trunk)))
    mpp = D*2*tv/H
    trunk_r = float(np.median([t[2] for t in trunk[:10]]))*mpp
    nodes = [np.array([tp[0][0], -0.3, tp[0][2]])] + [p for p in tp]
    parent = [-1] + list(range(len(tp)))
    # his big limbs: the thick wood of his picture above the fork, down to its middle lines, followed out from the top of
    # the trunk; each limb wanders a little toward us or away as it goes
    thick = wood.copy()
    for _ in range(3):                                          # only wood wider than about 6 px
        thick = thick & np.roll(thick, 1, 0) & np.roll(thick, -1, 0) & np.roll(thick, 1, 1) & np.roll(thick, -1, 1)
    for _ in range(3):
        thick = thick | np.roll(thick, 1, 0) | np.roll(thick, -1, 0) | np.roll(thick, 1, 1) | np.roll(thick, -1, 1)
    thick &= wood
    thick[int(trunk[-1][1]) + 10:] = False                       # above the fork only
    sk = thin(thick).astype(bool)
    sy, sx = np.nonzero(sk)
    if len(sx):
        tx, ty = trunk[-1][0], trunk[-1][1]
        start = int(np.argmin((sx - tx)**2 + (sy - ty)**2))
        seen, queue = {(sy[start], sx[start]): None}, [(sy[start], sx[start])]
        allpx = np.stack([sy, sx], 1)
        while True:
            while queue:                                        # the limbs, as a tree of pixels from the trunk's top
                y, x = queue.pop(0)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        q = (y + dy, x + dx)
                        if (dy or dx) and 0 <= q[0] < sk.shape[0] and 0 <= q[1] < sk.shape[1] and sk[q] and q not in seen:
                            seen[q] = (y, x); queue.append(q)
            # leaves in front break his limbs into pieces: jump to the nearest piece not yet reached, if it is close
            vis = np.array(list(seen.keys())); un = np.array([q for q in map(tuple, allpx) if q not in seen])
            if not len(un): break
            d2 = ((un[:, None, :] - vis[None, ::3, :])**2).sum(-1)
            k = np.unravel_index(np.argmin(d2), d2.shape)
            if d2[k] > (90 if len(seen) < 60 else 36)**2: break     # the first gap, from the trunk's top, can be wide
            a_, b_ = tuple(un[k[0]]), tuple(vis[::3][k[1]])
            seen[a_] = b_; queue.append(a_)
        node_of, depth_of, steps = {(sy[start], sx[start]): len(nodes) - 1}, {(sy[start], sx[start]): 0.0}, {}
        order = list(seen)                                      # in the order they were reached: each after its parent
        for q in order[1:]:
            pq = seen[q]
            if pq not in node_of: continue
            steps[q] = steps.get(pq, 0) + 1
            depth_of[q] = float(np.clip(depth_of[pq] + rng.normal(0, 0.06), -2.5, 2.5))
            if steps[q] % 12 == 0 or not any(seen.get((q[0] + dy, q[1] + dx)) == q for dy in (-1, 0, 1) for dx in (-1, 0, 1)):
                nodes.append(at([q[1]], [q[0]], [depth_of[q]])[0]); parent.append(node_of[pq]); node_of[q] = len(nodes) - 1
            else:
                node_of[q] = node_of[pq]
        print(f'limbs from his picture: {len(nodes) - len(tp) - 1} points')
    fixed = len(nodes)                                          # the trunk and his limbs: kept whatever grows from them
    print(f'trunk: {len(trunk)} points up to {tp[-1][1]:.1f} m, radius {trunk_r:.2f} m; crown points {len(pts)}; D {D:.1f} m')

    # space colonisation: every point pulls the nearest branch tip toward it; reached points are dropped
    alive = np.ones(len(pts), bool)
    for it in range(260):
        kd = KDTree(len(nodes))
        for i, n in enumerate(nodes):
            if i >= len(tp) - 1: kd.insert(n, i)                # branches grow from the fork and his limbs, not low on the trunk
        kd.balance()
        pull = {}
        for k in np.nonzero(alive)[0]:
            co, i, d = kd.find(pts[k])
            if d < TREE['kill']:
                alive[k] = False
            elif d < TREE['reach']:
                v = (pts[k] - np.asarray(co))/d
                pull[i] = pull.get(i, 0) + v
        if not pull:
            break
        for i, v in pull.items():
            v = v/np.linalg.norm(v) + np.array([0, TREE['up'], 0])
            nodes.append(nodes[i] + TREE['step']*v/np.linalg.norm(v)); parent.append(i)
        if not alive.any():
            break
    nodes = np.array(nodes); parent = np.array(parent)
    print(f'branches: {len(nodes)} points after {it + 1} steps; crown points left {alive.sum()}')

    # smoother branches: each point a little toward the middle of its neighbours
    kids = [[] for _ in nodes]
    for i, p in enumerate(parent):
        if p >= 0: kids[p].append(i)
    for _ in range(3):
        new = nodes.copy()
        for i in range(len(trunk) + 1, len(nodes)):
            if kids[i]:
                new[i] = 0.5*nodes[i] + 0.25*nodes[parent[i]] + 0.25*np.mean(nodes[kids[i]], axis=0)
        nodes = new

    # radii: a branch carries as much as all it bears (r^n = sum of children's r^n), the trunk as thick as his
    rad = np.zeros(len(nodes))
    for i in range(len(nodes) - 1, -1, -1):
        rad[i] = TREE['tip'] if not kids[i] else sum(rad[k]**TREE['pipe'] for k in kids[i])**(1/TREE['pipe'])
    rad *= trunk_r/rad[1]
    rad = np.maximum(rad, TREE['tip'])

    # how far from the foot along the branches (how much each part bends in the wind), and a phase per branch
    dist = np.zeros(len(nodes))
    for i in range(1, len(nodes)):
        dist[i] = dist[parent[i]] + np.linalg.norm(nodes[i] - nodes[parent[i]])
    bend = np.clip((dist/dist.max())**1.5*(1 - np.clip(rad/0.25, 0, 1)), 0, 1)
    phase = np.zeros(len(nodes))
    for i in range(1, len(nodes)):
        main = parent[i] >= 0 and kids[parent[i]] and max(kids[parent[i]], key=lambda k: rad[k]) == i
        phase[i] = phase[parent[i]] if main else random.random()

    # the leaves: sprays on the thin twigs (one card carries a twig with 10–14 photographed leaves, the way game trees fill
    # their crowns), each going on outward from its twig, turned its own way, mostly up and out toward the light
    C = nodes[rad < 0.05].mean(axis=0)
    lv, lf, lu, lc, lp = [], [], [], [], []
    bears = np.zeros(len(nodes), bool)                          # does a branch carry any leaves (itself or further out)
    def box(a, r):                                              # the mean of a picture over a square around each pixel
        S = np.pad(a.astype(np.float64), ((r + 1, r), (r + 1, r)), mode='edge').cumsum(0).cumsum(1)
        return (S[2*r + 1:, 2*r + 1:] - S[:-2*r - 1, 2*r + 1:] - S[2*r + 1:, :-2*r - 1] + S[:-2*r - 1, :-2*r - 1])/(2*r + 1)**2
    leafy_cover = box((m[..., 0] > 0.6) & (m[..., 1] < 0.3), 22)
    wood_near = box(m[..., 1] > 0.5, 12)
    twigs = np.nonzero((rad < TREE['twig']) & (np.arange(len(nodes)) > len(trunk)))[0]
    up = np.array([0, 1., 0])
    for i in twigs:
        out = nodes[i] - C; out /= (np.linalg.norm(out) or 1)
        go = nodes[i] - nodes[parent[i]]; go /= (np.linalg.norm(go) or 1)
        for _ in range(TREE['sprays']):
            size = random.uniform(*TREE['spray'])
            a = go*0.5 + out*0.5 + up*0.25 + rng.normal(0, 0.45, 3); a /= np.linalg.norm(a)      # along the spray
            n = up*0.5 + out*0.5 + rng.normal(0, 0.6, 3); n -= a*np.dot(n, a); n /= (np.linalg.norm(n) or 1)
            b = np.cross(n, a)
            stalk = nodes[i] + rng.normal(0, 0.04, 3)
            # only where his picture has leaves: where it shows sky through the crown, or a limb, there are none (so the
            # crown keeps his clumps and holes, and his limbs show)
            ok = True
            for f_, need in ((0.5, TREE['cover']), (1.0, 0.45)):     # its middle well inside his leaves, its tip inside them too
                d = stalk + a*size*f_ + origin - CAM; z = float(np.dot(d, F))
                qi, qj = int(half - half*float(np.dot(d, U))/(z*tv)), int(cx + half*float(np.dot(d, R))/(z*tv))
                if not (0 <= qi < m.shape[0] and 0 <= qj < m.shape[1]) or leafy_cover[qi, qj] < need or (f_ == 0.5 and wood_near[qi, qj] > TREE['near_wood']):
                    ok = False
            if not ok:
                continue
            bears[i] = True
            v = random.randrange(4); r = v//2
            u0, u1, v0, v1 = (v % 2)*0.5, (v % 2)*0.5 + 0.5, 1 - (r + 1)/2, 1 - r/2
            k0 = len(lv)
            for sa, sb, u, vv in ((0, -1, u0, v0), (0, 1, u1, v0), (1, 1, u1, v1), (1, -1, u0, v1)):
                lv.append(stalk + a*sa*size + b*sb*size*0.5); lu.append((u, vv))
                lc.append([1, min(1, bend[i] + 0.1), phase[i], 1]); lp.append(stalk)
            lf.append((k0, k0 + 1, k0 + 2, k0 + 3))
    # the bark: a tube along each chain of branches (each chain follows its thickest child)
    verts, faces, uvs, cols, piv = [], [], [], [], []
    for i in range(len(nodes) - 1, 0, -1):                      # what carries leaves further out carries them too
        if bears[i]: bears[parent[i]] = True
    bears[:fixed] = True                                        # his trunk and limbs stay, leaves or not
    kids = [[k for k in ks if bears[k]] for ks in kids]
    starts = [0] + [i for i in range(1, len(nodes)) if bears[i] and max(kids[parent[i]], key=lambda k: rad[k]) != i and rad[i] >= TREE['bare']]
    for s in starts:
        chain = ([parent[s]] if parent[s] >= 0 else []) + [s]
        while kids[chain[-1]] and max(rad[k] for k in kids[chain[-1]]) >= TREE['bare']:
            chain.append(max(kids[chain[-1]], key=lambda k: rad[k]))
        if len(chain) < 2:
            continue
        sides = int(np.clip(round(rad[chain[0]]*60), 4, 16))
        Nv, length, base = None, 0.0, len(verts)
        for j, i in enumerate(chain):
            a, b = nodes[chain[max(0, j - 1)]], nodes[chain[min(len(chain) - 1, j + 1)]]
            t = b - a; t /= (np.linalg.norm(t) or 1)
            if Nv is None:
                Nv = np.cross(t, [0, 1, 0] if abs(t[1]) < 0.9 else [1, 0, 0])
            Nv = Nv - t*np.dot(Nv, t); Nv /= np.linalg.norm(Nv)
            Bv = np.cross(t, Nv)
            if j: length += np.linalg.norm(nodes[i] - nodes[chain[j - 1]])
            r = rad[i]*(1 + 0.6*math.exp(-max(nodes[i][1], 0)/0.5) if i <= len(trunk) else 1)
            for k in range(sides + 1):
                ang = k/sides*2*math.pi
                d = Nv*math.cos(ang) + Bv*math.sin(ang)
                verts.append(nodes[i] + d*r)
                uvs.append((k/sides*max(1, round(2*math.pi*rad[chain[0]]/0.6)), length/0.6))
                cols.append([1, bend[i], phase[i], 0]); piv.append(nodes[i])
        for j in range(len(chain) - 1):
            for k in range(sides):
                a0 = base + j*(sides + 1) + k; b0 = a0 + sides + 1
                faces.append((a0, a0 + 1, b0 + 1, b0))
    bark = (np.array(verts), faces, np.array(uvs), np.array(cols), np.array(piv))

    leaves = (np.array(lv), lf, np.array(lu), np.array(lc), np.array(lp))
    print(f'bark: {len(verts)} vertices, {len(faces)} quads; sprays: {len(lf)}')

    # the shade deep in the crown: the more leaves around a point, the less sky reaches it
    kd = KDTree(len(lv)//4)
    for q in range(len(lv)//4): kd.insert(np.mean(lv[q*4:q*4 + 4], axis=0), q)
    kd.balance()
    for V, cl in ((bark[0], bark[3]), (leaves[0], leaves[3])):
        for q in range(len(V)):
            cl[q][0] = max(0.35, math.exp(-len(kd.find_range(V[q], 1.6))/22))

    # into Blender (its z is up: ours (x, y, z) is Blender's (x, -z, y)), and out as glTF
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    for name, (V, Fc, UV, CL, PV) in (('bark', bark), ('leaves', leaves)):
        me = bpy.data.meshes.new(name)
        me.from_pydata([(v[0], -v[2], v[1]) for v in V], [], Fc)
        uv = me.uv_layers.new(name='UVMap')
        loop_uv = np.array([UV[l.vertex_index] for l in me.loops]).ravel()
        uv.data.foreach_set('uv', loop_uv)
        col = me.color_attributes.new(name='Col', type='BYTE_COLOR', domain='POINT')
        col.data.foreach_set('color', np.clip(CL, 0, 1).astype(np.float32).ravel())
        pv = me.attributes.new(name='pivot', type='FLOAT_VECTOR', domain='POINT')
        pv.data.foreach_set('vector', np.array([(p[0], -p[2], p[1]) for p in PV], np.float32).ravel())
        me.polygons.foreach_set('use_smooth', [name == 'bark']*len(me.polygons))
        me.update()
        ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
    glb = OUT.with_name('tree-export.glb')
    kw = dict(filepath=str(glb), export_format='GLB', use_selection=False, export_yup=True, export_apply=True,
              export_texcoords=True, export_normals=True, export_attributes=True, export_materials='NONE')
    try:
        bpy.ops.export_scene.gltf(**kw, export_vertex_color='ACTIVE')
    except TypeError as e:
        print('exporter:', e); bpy.ops.export_scene.gltf(**kw)
    # the binary glTF unpacked into one JSON file with its data inside (glTF allows the buffer as a base64 data URI)
    raw = glb.read_bytes(); glb.unlink()
    jlen = int.from_bytes(raw[12:16], 'little'); doc = json.loads(raw[20:20 + jlen])
    blen = int.from_bytes(raw[20 + jlen:24 + jlen], 'little'); bin_ = raw[28 + jlen:28 + jlen + blen]
    doc['buffers'] = [{'byteLength': len(bin_), 'uri': 'data:application/octet-stream;base64,' + base64.b64encode(bin_).decode()}]
    OUT.write_text(json.dumps(doc, separators=(',', ':')))
    print(f'{OUT.stat().st_size//1024} KB → {OUT}')


main()
