"""Checks for sky_bake.py: python3 ios/design/scene/test_sky_bake.py  (prints "all ok")."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

import sky_bake as sb

CELL = 0.1
ORIGIN = np.zeros(3)


def sky(sigma, pts, normals=None):
    return sb.sky_visibility(sigma, ORIGIN, CELL, np.array(pts, np.float64), normals=normals)


# empty grid: full sky
empty = np.zeros((40, 40, 40), np.float32)
V = sky(empty, [(2, 2, 2), (0.5, 3.5, 1)])
assert np.all(np.abs(V - 1) < 1e-5), V

# opaque slab, z-cells 30..33 (z 3.0..3.4), all x, y. On a 40x40 m slab: on the 4 m grid, rays from below that leave
# sideways never reach the slab, and outside the grid sigma is 0, so V would be ~0.42 there. A 40 m wide slab
# keeps the sideways escape negligible, so the check measures the slab itself.
slab = np.zeros((400, 400, 40), np.float32)
slab[:, :, 30:34] = 100
V = sb.sky_visibility(slab, ORIGIN, CELL, np.array([(20, 20, 1.0), (20, 20, 3.9)]))
print('slab V below', V[0], 'above', V[1])
assert V[0] < 0.02, V[0]
assert V[1] > 0.97, V[1]

# wall, x-cells 20..23 (x 2.0..2.4), all y, z
wall = np.zeros((40, 40, 40), np.float32)
wall[20:24, :, :] = 100
A = (1.9, 2.0, 0.5)
V_up = sky(wall, [A])[0]
V_pos = sky(wall, [A], normals=[(1, 0, 0)])[0]
V_neg = sky(wall, [A], normals=[(-1, 0, 0)])[0]
print('wall up', V_up, 'n+x', V_pos, 'n-x', V_neg)
assert 0.35 < V_up < 0.65, V_up
assert V_pos < 0.12, V_pos
assert V_neg > 0.88, V_neg

# optical depth, sigma = 1 everywhere
ones = np.ones((40, 40, 40), np.float32)
tau = sb.optical_depth(ones, CELL, (0, 0, 1))
for k in (0, 10, 39):
    exact = 4.0 - (k + 0.5)*CELL
    assert abs(tau[20, 20, k] - exact) < 0.06, (k, tau[20, 20, k], exact)
d = np.array([1.0, 1.0, 1.0])/np.sqrt(3)
tau = sb.optical_depth(ones, CELL, d)
exact = (4.0 - 2.05)/d[0]
print('diagonal tau', tau[20, 20, 20], 'exact', exact)
assert abs(tau[20, 20, 20] - exact) < 0.05*exact

# hemisphere directions
D = sb.hemisphere_dirs(96)
assert np.allclose(np.linalg.norm(D, axis=1), 1)
assert np.all(D[:, 2] > 0)
assert abs(D[:, 2].mean() - 0.5) < 0.01

# sub-triangle barycentric weights
B = sb.subtriangle_bary(4)
assert B.shape == (16, 3)
assert np.all(B >= 0)
assert np.allclose(B.sum(1), 1)
assert np.allclose(B.mean(0), 1/3, atol=0.02)

# ground share (down=True): the same point looks at the lower hemisphere; a slab above it does not block that,
# a slab below it does
above = np.zeros((40, 40, 40), np.float32)
above[:, :, 30:34] = 100
below = np.zeros((40, 40, 40), np.float32)
below[:, :, 2:6] = 100
P = np.array([(2, 2, 1.0)])
G_above = sb.sky_visibility(above, ORIGIN, CELL, P, down=True)[0]
G_below = sb.sky_visibility(below, ORIGIN, CELL, P, down=True)[0]
print('ground: slab above', G_above, 'slab below', G_below)
assert G_above > 0.97, G_above
assert G_below < 0.35, G_below
assert G_below < G_above, (G_below, G_above)

print('all ok')
