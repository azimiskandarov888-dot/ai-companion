"""Sky visibility for mesh vertices, in pure numpy (no Blender).

The tree is turned into an absorbing volume: each triangle deposits its area, spread over sub-points, into a grid of
cells as extinction sigma (per metre). For a vertex, the sky visibility is the share of the sky that reaches it: for
sampled directions d over the upper hemisphere, V = mean of exp(-tau) where tau is the optical depth from the vertex
outward along d.

Coordinates are metres, z up. Grid values live at cell centres: centre of index i is origin + (i + 0.5)·cell.
"""
import time

import numpy as np


def hemisphere_dirs(n):
    """n equal-solid-angle unit directions over the upper hemisphere (Fibonacci), float64 (n, 3)."""
    i = np.arange(n, dtype=np.float64)
    z = (i + 0.5)/n
    r = np.sqrt(1 - z*z)
    phi = i*np.pi*(3 - np.sqrt(5))
    return np.stack([r*np.cos(phi), r*np.sin(phi), z], 1)


def subtriangle_bary(k=4):
    """Barycentric weights (b0, b1, b2) of the centroids of the k×k sub-triangles of a triangle, (k², 3)."""
    pts = []
    for i in range(k):
        for j in range(k):
            if i + j <= k - 1:
                pts.append(((i + 1/3)/k, (j + 1/3)/k))
    for i in range(k):
        for j in range(k):
            if i + j <= k - 2:
                pts.append(((i + 2/3)/k, (j + 2/3)/k))
    P = np.array(pts, dtype=np.float64)
    return np.stack([1 - P[:, 0] - P[:, 1], P[:, 0], P[:, 1]], 1)


def deposit(sigma, origin, cell, points, weights):
    """Add each weight into the cell that holds its point (in place on sigma). Points outside the grid are dropped."""
    idx = np.floor((points - origin)/cell).astype(np.int64)
    inside = np.all((idx >= 0) & (idx < np.array(sigma.shape)), axis=1)
    flat = np.ravel_multi_index(tuple(idx[inside].T), sigma.shape)
    add = np.bincount(flat, weights=np.asarray(weights, np.float64)[inside], minlength=sigma.size)
    sigma += add.reshape(sigma.shape).astype(sigma.dtype)


def optical_depth(sigma, cell, d):
    """tau at each cell: integral of sigma from the cell centre along +d to the grid edge (sigma = 0 outside)."""
    d = np.asarray(d, dtype=np.float64)
    a = int(np.argmax(np.abs(d)))
    others = [ax for ax in range(3) if ax != a]
    flip = d[a] < 0
    S = np.moveaxis(np.asarray(sigma, np.float32), a, -1)
    if flip:
        S = S[..., ::-1]
    S = np.ascontiguousarray(S)
    da = abs(d[a])
    su = float(d[others[0]]/da)
    sv = float(d[others[1]]/da)
    L = cell/da
    i0 = int(np.floor(su)); fu = su - i0
    j0 = int(np.floor(sv)); fv = sv - j0

    def shift(X):
        """X sampled bilinearly at (i + su, j + sv) for every (i, j), 0 outside."""
        P = np.pad(X, 2)
        n0, n1 = X.shape
        a00 = P[2 + i0:2 + i0 + n0, 2 + j0:2 + j0 + n1]
        a10 = P[3 + i0:3 + i0 + n0, 2 + j0:2 + j0 + n1]
        a01 = P[2 + i0:2 + i0 + n0, 3 + j0:3 + j0 + n1]
        a11 = P[3 + i0:3 + i0 + n0, 3 + j0:3 + j0 + n1]
        return ((1 - fu)*(1 - fv)*a00 + fu*(1 - fv)*a10 + (1 - fu)*fv*a01 + fu*fv*a11).astype(np.float32)

    N = S.shape[-1]
    T = np.empty_like(S)
    T[..., N - 1] = 0.5*L*S[..., N - 1]
    for k in range(N - 2, -1, -1):
        T[..., k] = 0.5*L*(S[..., k] + shift(S[..., k + 1])) + shift(T[..., k + 1])
    if flip:
        T = T[..., ::-1]
    return np.moveaxis(T, -1, a).astype(np.float32)


def trilinear(grid, origin, cell, pts):
    """Grid values (cell centres) at points. Inside the grid box: interpolated, clamped to the edge cells.
    Outside the box: 0."""
    shape = np.array(grid.shape)
    pts = np.asarray(pts, np.float64)
    inside = np.all((pts >= origin) & (pts <= origin + shape*cell), axis=1)
    f = np.clip((pts - origin)/cell - 0.5, 0, shape - 1)
    i0 = np.minimum(np.floor(f).astype(np.int64), shape - 2)
    t = f - i0
    out = np.zeros(len(pts), np.float32)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = ((t[:, 0] if dx else 1 - t[:, 0])*(t[:, 1] if dy else 1 - t[:, 1])
                     *(t[:, 2] if dz else 1 - t[:, 2]))
                out += (w*grid[i0[:, 0] + dx, i0[:, 1] + dy, i0[:, 2] + dz]).astype(np.float32)
    out[~inside] = 0
    return out


def sky_visibility(sigma, origin, cell, points, normals=None, n_dirs=96, offset=1.0, down=False):
    """Share of the sky reaching each point, float32 in [0, 1]. With down=True the same over the lower hemisphere: the
    share of the ground (the field below) seen through the tree.

    Without normals: up-weighted over the hemisphere (weight d_z). With normals (zero row = none): weighted by
    max(0, n·d) for that row, falling back to the up-weighting where the normal sees no sampled direction.
    """
    points = np.asarray(points, np.float64)
    M = len(points)
    dirs = hemisphere_dirs(n_dirs)
    if down:
        dirs = dirs*np.array([1.0, 1.0, -1.0])
    A_up = np.zeros(M, np.float64)
    W_up = 0.0
    if normals is not None:
        normals = np.asarray(normals, np.float64)
        nl = np.linalg.norm(normals, axis=1)
        has_n = nl > 1e-9
        nn = np.zeros_like(normals)
        nn[has_n] = normals[has_n]/nl[has_n, None]
        A_n = np.zeros(M, np.float64)
        W_n = np.zeros(M, np.float64)
    t0 = time.time()
    for k, d in enumerate(dirs):
        tau = optical_depth(sigma, cell, d)
        T = np.exp(-trilinear(tau, origin, cell, points + d*offset*cell)).astype(np.float64)
        A_up += T*abs(d[2])
        W_up += abs(d[2])
        if normals is not None:
            w = np.maximum(0, nn @ d)
            A_n += T*w
            W_n += w
        if (k + 1) % 16 == 0:
            print(f'  {"ground" if down else "sky"}: {k + 1}/{n_dirs} directions, {time.time() - t0:.1f} s')
    V = A_up/W_up
    if normals is not None:
        use = has_n & (W_n > 1e-3)
        V[use] = A_n[use]/W_n[use]
    return np.clip(V, 0, 1).astype(np.float32)
