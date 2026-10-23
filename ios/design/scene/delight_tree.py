"""Take the light out of his tree, the way games take it out of photographed assets ("de-lighting"), so the page can light
it with its own sun: what the tree is — its own colour (albedo) — apart from how the light fell on it in his picture, and
which way each bit of it faces (normals).

    python3 scene/delight_tree.py [cache-folder]
        needs torch and diffusers (Marigold v1.1 by prs-eth, CreativeML Open RAIL++-M; about 5 GB of models, downloaded
        once); reads framing/mj-15-hd.jpg and scene/assets/tree-mask.png (from scene/trace_tree.py); writes
        field-assets/tree-albedo.webp (colour, and how much of each pixel is tree) and field-assets/tree-normal.webp
        (which way it faces: x right, y up, z toward us; and in its alpha, 0.5 for wood up to 1 for leaf).
        With a cache folder the models' answers are kept there and reused.

Marigold-IID-Lighting splits the picture into albedo × diffuse shading + what is left (shine); Marigold-Normals gives the
normals. Both work at 1024 px on the long side, close to the size the tree is drawn on the phone.
"""
import pathlib
import sys

import cv2
import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
PICTURE, MASK = HERE.parent / 'framing' / 'mj-15-hd.jpg', HERE / 'assets' / 'tree-mask.png'
ALBEDO, NORMAL = HERE.parent / 'field-assets' / 'tree-albedo.webp', HERE.parent / 'field-assets' / 'tree-normal.webp'
RES, STEPS, ENSEMBLE = 1024, 4, 1                     # at 1280 the Apple GPU gives NaN
BARK = (0.05, 0.038, 0.03)                 # the wood's own colour, linear: the model reads the dark trunk as olive
CAVITY = 0.85                              # how dark the gaps between the leaves are kept


def marigold(img, cache):
    """Albedo, diffuse shading and normals of the image; each is kept in the cache as soon as it is made, and taken from
    there next time."""
    have = lambda *names: cache and all((cache / f'tree-{n}.npy').exists() for n in names)
    if have('albedo', 'shading', 'normals'):
        return [np.load(cache / f'tree-{n}.npy').astype(np.float32) for n in ('albedo', 'shading', 'normals')]
    import torch
    from diffusers import MarigoldIntrinsicsPipeline, MarigoldNormalsPipeline
    dev = 'mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu'
    dt = torch.float32 if dev == 'cpu' else torch.bfloat16              # half precision overflows into NaN on Apple GPUs
    run = dict(num_inference_steps=STEPS, ensemble_size=ENSEMBLE, processing_resolution=RES, match_input_resolution=True,
               output_type='np')
    def keep(n, a):
        if np.isnan(a).any():
            raise ValueError(f'{n}: the model gave NaN')
        if cache:
            cache.mkdir(parents=True, exist_ok=True); np.save(cache / f'tree-{n}.npy', a.astype(np.float16))

    def load(cls, name):
        for attempt in range(3):                                   # the download can break off; it goes on where it stopped
            try:
                return cls.from_pretrained(name, variant='fp16', dtype=dt).to(dev)
            except OSError as e:
                print(f'loading {name} failed ({e.__class__.__name__}), trying again'); err = e
        raise err

    if not have('albedo', 'shading'):
        pipe = load(MarigoldIntrinsicsPipeline, 'prs-eth/marigold-iid-lighting-v1-1')
        p = pipe(img, generator=torch.Generator().manual_seed(0), **run).prediction
        for n, a in zip(pipe.target_properties['target_names'], p):
            keep(n, a)
            if n == 'albedo': albedo = a
            if n == 'shading': shading = a
        del pipe
    else:
        albedo, shading = [np.load(cache / f'tree-{n}.npy') for n in ('albedo', 'shading')]
    if not have('normals'):
        pipe = load(MarigoldNormalsPipeline, 'prs-eth/marigold-normals-v1-1')
        normals = pipe(img, generator=torch.Generator().manual_seed(0), **run).prediction[0]
        keep('normals', normals)
    else:
        normals = np.load(cache / 'tree-normals.npy')
    return [a.astype(np.float32) for a in (albedo, shading, normals)]


def spread(a, solid):
    """Beyond the tree, each pixel takes its nearest solid tree pixel's value: nothing of his sky leaks in at the edges."""
    _, near = cv2.distanceTransformWithLabels((1 - solid).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    near = np.argwhere(solid == 1)[near - 1]                       # the labels count the solid pixels in reading order
    return np.where((solid == 0)[..., None], a[near[..., 0], near[..., 1]], a)


def main():
    mask = np.asarray(Image.open(MASK).convert('RGB')).astype(np.float32)/255
    tree, wood = mask[..., 0], mask[..., 1]
    h, w = tree.shape
    img = Image.open(PICTURE).convert('RGB').crop((0, 0, w, h))
    cache = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
    albedo, shading, normals = marigold(img, cache)
    # the gaps between the leaves stay dark whatever the light (ambient occlusion, as games bake it into foliage): where
    # the picture's light is lower than all around it — only the darker side, so no highlight is kept
    lum = shading @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    cavity = np.clip(lum/np.maximum(cv2.GaussianBlur(lum, (0, 0), 8), 1e-4), 0, 1)
    albedo = albedo*(1 - CAVITY*(1 - cavity))[..., None]
    # the wood: its own dark brown, with the model's light and dark kept as its texture. The traced wood misses the
    # trunk's sunlit side (too light to look like wood in his picture); the model's colour finds it: not orange but olive
    wl = albedo @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    barky = ((albedo[..., 1] > 0.6*albedo[..., 0]) & (wl < 0.25) & (tree > 0.5)).astype(np.float32)
    wood = np.maximum(wood, cv2.GaussianBlur(cv2.morphologyEx(barky, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)), (5, 5), 0))
    w = wood > 0.5
    albedo = np.where((wood > 0.1)[..., None], (1 - wood[..., None])*albedo + wood[..., None]*np.array(BARK, np.float32)*(wl/max(wl[w].mean(), 1e-4))[..., None], albedo)
    solid = (tree > 0.6).astype(np.uint8)                          # beyond it, where the tree's edge fades into the sky
    albedo = spread(albedo, solid)
    normals = spread(normals, solid)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True) + 1e-6
    srgb = np.where(albedo <= 0.0031308, albedo*12.92, 1.055*np.power(np.clip(albedo, 0, 1), 1/2.4) - 0.055)
    Image.fromarray((np.dstack([srgb, tree]).clip(0, 1)*255 + 0.5).astype(np.uint8), 'RGBA').save(
        ALBEDO, quality=92, alpha_quality=100, method=6, exact=True)   # exact: WebP would otherwise change colour where alpha is 0
    leaf = 0.5 + 0.5*(1 - wood)                                    # leaf 1, wood 0.5: never fully see-through, so nothing drops the normals
    Image.fromarray((np.dstack([normals*0.5 + 0.5, leaf]).clip(0, 1)*255 + 0.5).astype(np.uint8), 'RGBA').save(
        NORMAL, quality=95, alpha_quality=100, method=6, exact=True)
    m = tree > 0.97
    print(f'albedo (linear) on the tree: mean {albedo[m].mean(0).round(3)}, shading mean {shading[m].mean(0).round(3)}')
    print(f'{ALBEDO.stat().st_size//1024} KB → {ALBEDO}\n{NORMAL.stat().st_size//1024} KB → {NORMAL}')


if __name__ == '__main__':
    main()
