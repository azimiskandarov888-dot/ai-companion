# Generated art, exactly as it came out

Drop files here **untouched** — full resolution, magenta background still on,
nothing cropped. Cutting out the background, measuring where the base sits and
writing the manifest all happen later, from these originals. A file that has
already been edited cannot be re-cut differently when we change our minds.

Cut-outs with alpha go in `../cut/`. Never edit anything in this folder.

## Names

Use these exactly. The manifest is keyed off them, and a renamed file is a
broken asset.

### Objects — side view, base on the bottom edge, magenta background

| file | what | metres |
|---|---|---|
| `tree-leafy-11.png` | big leafy tree | 11 |
| `tree-leafy-8.png` | medium leafy tree | 8 |
| `tree-pine-13.png` | tall pine | 13 |
| `tree-crooked-7.png` | old crooked tree | 7 |
| `tree-broad-6.png` | wide flat-crowned tree | 6 |
| `bush-08.png` | small bush | 0.8 |
| `bush-large-14.png` | large leafy bush | 1.4 |
| `bush-flowering-06.png` | low flowering bush | 0.6 |
| `rock-12.png` | large rock | 1.2 |
| `rock-04.png` | small rock | 0.4 |
| `stones-015.png` | handful of pebbles | 0.15 |
| `log-3.png` | fallen log — **he sits on this** | 3 |
| `branch-1.png` | fallen bare branch | 1 |
| `grass-04.png` | tall grass tuft | 0.4 |
| `grass-025.png` | short grass clump | 0.25 |
| `flowers-02.png` | tiny wildflowers | 0.2 |

### Frame — hangs from the top, not standing on the bottom

| file | what |
|---|---|
| `frame-left.png` | branches from the top left corner |
| `frame-right.png` | branches from the top right corner |
| `frame-top.png` | branches across the top edge |

### Bands — very wide, tile left to right, magenta background

| file | what |
|---|---|
| `ridge-near.png` | forested hills, five layers |
| `ridge-far.png` | distant ridges, dissolved in haze |
| `ground-near.png` | grass, shallow angle, grass strokes |
| `ground-mid.png` | grass, flatter, softer |
| `ground-far.png` | grass, nearly edge-on, no detail |

## The rules every object file obeys

1. Whole object in frame, nothing cropped
2. Base touching the bottom edge
3. Light from the **upper right** — every asset, forever
4. No cast shadow (code draws it, to match each scene's sun)
5. Nothing else in frame
6. Flat solid magenta background, no gradient in it

Rules 3 and 4 are the ones that make separate pictures behave as one world.
