import test from 'node:test';
import assert from 'node:assert/strict';
import { configuration } from './build.mjs';

test('routes the existing server-rendered site and APIs together', () => {
  assert.deepEqual(configuration('https://synthetic-mednova.onrender.com').routes, [{ src: '/(.*)', dest: 'https://synthetic-mednova.onrender.com/$1' }]);
});
test('rejects missing, local, insecure, credential-bearing and non-origin destinations', () => {
  for (const value of [undefined, '', 'http://localhost:8000', 'https://example.com', 'https://x.onrender.com/path', 'https://x.onrender.com?q=1', 'https://user:secret@x.onrender.com']) {
    assert.throws(() => configuration(value));
  }
});
