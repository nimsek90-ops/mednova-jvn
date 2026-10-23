import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export function configuration(origin) {
  if (!origin) throw new Error('Set MEDNOVA_BACKEND_ORIGIN to the verified HTTPS Render backend origin.');
  const url = new URL(origin);
  if (url.protocol !== 'https:' || !url.hostname.endsWith('.onrender.com') || url.username || url.password || url.search || url.hash || url.pathname !== '/' || url.port) {
    throw new Error('MEDNOVA_BACKEND_ORIGIN must be an HTTPS *.onrender.com origin without credentials, a port, a path or query.');
  }
  return { version: 3, routes: [{ src: '/(.*)', dest: `${url.origin}/$1` }] };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const config = configuration(process.env.MEDNOVA_BACKEND_ORIGIN);
  await mkdir('.vercel/output', { recursive: true });
  await writeFile('.vercel/output/config.json', JSON.stringify(config, null, 2));
  console.log('Vercel routing output generated. Pages, APIs, forms and private files use the same browser origin.');
}
