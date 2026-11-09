// Builds the living world for the iOS app (report «Экраны защита и скорость фронтенда», stage 1).
//
// ios/design/world.html stays the one source: it is the page we design in and publish. This turns it into a closed,
// local copy inside the app — BobCompanion/World/ — that needs nothing from the internet:
//   · the page's own module script, with three.js r184 and @takram's sky, bundled into one file (world.js) from the
//     versions pinned in package.json — no CDN, no importmap; their licences go to world.js.LEGAL.txt;
//   · its styles in world.css, so the policy can forbid inline ones;
//   · a strict Content-Security-Policy: scripts only from the app itself, WebAssembly allowed (the Draco decoder needs
//     it: without 'wasm-unsafe-eval' the tree never loads — measured 2026-11-06) but no eval, nothing to the network;
//   · only the files the world loads: the Draco decoder, the tree and its shadow, their maps (full and the lighter set).
// The app serves this folder through its own scheme (WorldView.swift), which sends the same policy as a header.
//
//   cd ios/world && npm install && npm run build

import { build } from 'esbuild';
import { readFileSync, writeFileSync, mkdirSync, rmSync, copyFileSync, existsSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const design = join(here, '../design'), out = join(here, '../BobCompanion/World');
const page = readFileSync(join(design, 'world.html'), 'utf8');

// ── the page's parts
const take = (re, what) => { const m = page.match(re); if (!m) throw new Error(`world.html: ${what} not found`); return m; };
const style = take(/<style>([\s\S]*?)<\/style>/, 'the <style>')[1];
const script = take(/<script type="module">([\s\S]*?)<\/script>/, 'the module script')[1];
// the markup between the style and the scripts (the canvas, the line of numbers, the developer panel, the test note)
const body = page.slice(page.indexOf('</style>') + '</style>'.length, page.indexOf('<script type="importmap">')).trim();
if (/\son[a-z]+\s*=/i.test(body)) throw new Error('world.html: inline event handlers would break the policy');

export const CSP = ["default-src 'none'", "script-src 'self' 'wasm-unsafe-eval'", "style-src 'self'", "img-src 'self' data: blob:",
  "connect-src 'self'", "worker-src 'self' blob:", "object-src 'none'", "base-uri 'none'", "form-action 'none'", "frame-ancestors 'none'"].join('; ');

rmSync(out, {recursive: true, force: true});
mkdirSync(join(out, 'field-assets/draco'), {recursive: true}); mkdirSync(join(out, 'field-assets/ph'), {recursive: true});

// ── one bundle, from the pinned versions
await build({
  stdin: {contents: script, resolveDir: here, sourcefile: 'world.html', loader: 'js'},
  bundle: true, format: 'esm', target: ['safari17'], minify: true, legalComments: 'external',
  outfile: join(out, 'world.js'), logLevel: 'warning',   // ('three' stays its own build: @takram imports WebGLRenderer from it,
});                                                        //  which three/webgpu does not have — as on the CDN, both load)

writeFileSync(join(out, 'world.css'), style.trim() + '\n');
writeFileSync(join(out, 'index.html'), `<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta http-equiv="Content-Security-Policy" content="${CSP}">
<title>Мир Боба</title>
<link rel="stylesheet" href="world.css">
</head>
<body class="clean">
${body}
<script type="module" src="world.js"></script>
</body>
</html>
`);

// ── only what the world loads
const copy = (from, to = from) => { copyFileSync(join(design, from), join(out, to)); };
for (const f of ['draco_decoder.js', 'draco_decoder.wasm', 'draco_wasm_wrapper.js']) copy(`field-assets/draco/${f}`);
for (const f of ['jacaranda.gltf.json', 'jacaranda-shadow.gltf.json']) copy(`field-assets/ph/${f}`);
for (const part of ['trunk', 'branches']) for (const kind of ['diff', 'nor_gl']) for (const size of ['', '-512'])
  copy(`field-assets/ph/jacaranda_tree_${part}_${kind}_1k${size}.jpg`);
for (const size of ['', '-512']){ copy(`field-assets/ph/jacaranda_leaves_autumn${size}.jpg`); copy(`field-assets/ph/jacaranda_tree_leaves_nor_gl_1k${size}.jpg`); copy(`field-assets/ph/jacaranda_leaves_mask${size}.jpg`); }

writeFileSync(join(out, 'CSP.txt'), CSP + '\n');   // (WorldView.swift sends exactly this as the header)
const size = f => statSync(join(out, f)).size;
console.log(`World built into ${out}\n  world.js ${(size('world.js')/1024).toFixed(0)} KB · index.html, world.css, CSP.txt` +
  (existsSync(join(out, 'world.js.LEGAL.txt')) ? ' · world.js.LEGAL.txt' : ''));
