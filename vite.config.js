import { defineConfig } from 'vite';
import fs from 'node:fs';
import path from 'node:path';

// Dev-only helper: POST /__shot?name=foo with a JPEG body saves it under SHOT_DIR (used by automated playtests).
const shotDir = process.env.SHOT_DIR || path.resolve('.shots');
const shots = () => ({
  name: 'debug-shots',
  apply: 'serve',
  configureServer(server) {
    server.middlewares.use('/__shot', (req, res) => {
      if (req.method !== 'POST') { res.statusCode = 405; return res.end(); }
      const name = (new URL(req.url, 'http://x').searchParams.get('name') || 'shot').replace(/[^a-z0-9_-]/gi, '_');
      const chunks = []; req.on('data', (c) => chunks.push(c));
      req.on('end', () => { fs.mkdirSync(shotDir, { recursive: true }); const f = path.join(shotDir, name + '.jpg'); fs.writeFileSync(f, Buffer.concat(chunks)); res.end(f); });
    });
  },
});

// base './' keeps every asset URL relative, so the build also works from a subfolder (GitHub Pages serves it at /<repo>/)
export default defineConfig({ base: './', plugins: [shots()], build: { chunkSizeWarningLimit: 1200 } });
