import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';
import worker from './worker.mjs';

const origin = 'https://whitenoisechoir.com';
const host = 'https://downloads.whitenoisechoir.com';
const key = 'asset-library/raw/sha256/aa/example.wav';
const data = new TextEncoder().encode('test-media');
const metadata = {size: data.length, httpEtag: '"sample"'};

function makeEnv() {
  let reads = 0;
  return {
    TURNSTILE_SECRET_KEY: 'test-key-used-only-by-the-test',
    get reads() { return reads; },
    MEDIA: {
      async head(name) { reads++; return name === key ? metadata : null; },
      async get(name, options) {
        reads++;
        if (name !== key) return null;
        const range = options?.range;
        const body = range ? data.subarray(range.offset, range.offset + range.length) : data;
        return {...metadata, body};
      },
    },
  };
}

function request(env, path, {method = 'GET', headers, body} = {}) {
  return worker.fetch(new Request(host + path, {method, headers, body}), env);
}

function stubSiteverify(t) {
  const used = new Set();
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(url, 'https://challenges.cloudflare.com/turnstile/v0/siteverify');
    assert.equal(options.method, 'POST');
    assert.equal(options.body.get('secret'), 'test-key-used-only-by-the-test');
    const token = options.body.get('response');
    const success = token.startsWith('valid-') && !used.has(token);
    used.add(token);
    return Response.json({
      success,
      hostname: token.endsWith('-hostname') ? 'example.com' : 'whitenoisechoir.com',
      action: token.endsWith('-action') ? 'other' : 'media_access',
    });
  });
}

async function authorize(env, token = 'valid-1') {
  const response = await request(env, '/session', {method: 'POST', headers: {Origin: origin}, body: token});
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('Access-Control-Allow-Origin'), origin);
  assert.equal(response.headers.get('Access-Control-Allow-Credentials'), 'true');
  const header = response.headers.get('Set-Cookie');
  assert.match(header, /^__Host-wnc_media=.*; Path=\/; HttpOnly; Secure; SameSite=Strict; Max-Age=7200$/);
  assert.ok((await response.json()).expiresAt > Date.now() / 1000);
  return header.split(';')[0];
}

test('denies anonymous or foreign requests without reaching R2', async () => {
  const env = makeEnv();
  const path = '/media/' + key;
  const unauthorized = await request(env, path, {headers: {Origin: origin, Range: 'bytes=0-1'}});
  assert.equal(unauthorized.status, 401);
  assert.equal(unauthorized.headers.get('Cache-Control'), 'private, no-store');
  assert.equal((await request(env, path, {headers: {Origin: 'https://example.com'}})).status, 403);
  assert.equal((await request(env, path, {method: 'PUT'})).status, 405);
  assert.equal((await request(env, '/media/audio/unrelated.mp3')).status, 404);
  assert.equal((await request(env, '/media/asset-library/report.json')).status, 404);
  const preflight = await request(env, path, {method: 'OPTIONS', headers: {Origin: origin}});
  assert.equal(preflight.status, 204);
  assert.equal(preflight.headers.get('Access-Control-Allow-Origin'), origin);
  assert.equal(env.reads, 0);
});

test('rejects invalid, replayed or cross-site challenges and unsigned cookies', async t => {
  stubSiteverify(t);
  const env = makeEnv();
  const headers = {Origin: origin};
  for (const token of ['invalid', 'valid-hostname', 'valid-action']) {
    assert.equal((await request(env, '/session', {method: 'POST', headers, body: token})).status, 403);
  }
  assert.equal((await request(env, '/session', {method: 'POST', headers, body: 'x'.repeat(2049)})).status, 400);
  assert.equal((await request(env, '/session', {method: 'POST', body: 'valid-2'})).status, 403);
  const cookie = await authorize(env);
  assert.equal((await request(env, '/session', {method: 'POST', headers, body: 'valid-1'})).status, 403);
  const forged = cookie.replace(/v1\.\d{10}\./, 'v1.1999999999.');
  assert.equal((await request(env, '/media/' + key, {headers: {Cookie: forged}})).status, 401);
  assert.equal(env.reads, 0);
});

test('serves verified browser playback, range and download', async t => {
  stubSiteverify(t);
  const env = makeEnv();
  const cookie = await authorize(env);
  const headers = {Cookie: cookie, Origin: origin};
  const path = '/media/' + key;
  assert.equal((await request(env, '/session', {headers})).status, 200);
  const download = await request(env, path + '?download=ti%E1%BA%BFng%20m%C6%B0a', {headers});
  assert.equal(download.status, 200);
  assert.equal(await download.text(), 'test-media');
  assert.equal(download.headers.get('Content-Type'), 'audio/wav');
  assert.equal(download.headers.get('Content-Disposition'), "attachment; filename*=UTF-8''ti%E1%BA%BFng%20m%C6%B0a.wav");
  const partial = await request(env, path, {headers: {...headers, Range: 'bytes=0-3'}});
  assert.equal(partial.status, 206);
  assert.equal(partial.headers.get('Content-Range'), 'bytes 0-3/10');
  assert.equal(await partial.text(), 'test');
  const invalidRange = await request(env, path, {headers: {...headers, Range: 'bytes=11-'}});
  assert.equal(invalidRange.status, 416);
  assert.equal(invalidRange.headers.get('Content-Range'), 'bytes */10');
  const head = await request(env, path, {method: 'HEAD', headers});
  assert.equal(head.status, 200);
  assert.equal(head.headers.get('Content-Length'), '10');
  assert.equal(await head.text(), '');
  assert.equal((await request(env, '/media/asset-library/missing.wav', {headers})).status, 404);
});

test('shares a verification across concurrent Mixer loads and renews a lost session', async t => {
  stubSiteverify(t);
  const env = makeEnv();
  const source = await readFile(new URL('../../protected-media.js', import.meta.url), 'utf8');
  let challenges = 0;
  let cookie;
  const browser = {
    URL,
    AbortSignal,
    setTimeout,
    clearTimeout,
    document: {getElementById: () => ({})},
    window: {turnstile: {
      render(container, options) {
        assert.equal(options.appearance, 'interaction-only');
        assert.equal(options.action, 'media_access');
        challenges++;
        queueMicrotask(() => options.callback('valid-' + challenges));
        return 'widget';
      },
      remove() {},
    }},
    async fetch(url, options) {
      assert.equal(options.credentials, 'include');
      const headers = new Headers({Origin: origin});
      if (cookie) headers.set('Cookie', cookie);
      const response = await worker.fetch(new Request(url, {...options, headers}), env);
      const setCookie = response.headers.get('Set-Cookie');
      if (setCookie) cookie = setCookie.split(';')[0];
      return response;
    },
  };
  const client = vm.runInNewContext(source + '\nprotectedMedia', browser);
  assert.equal(client.manages(key), true);
  assert.equal(client.manages('audio/stream.mp3'), false);
  const responses = await Promise.all([client.fetchRecording(key), client.fetchRecording(key)]);
  assert.deepEqual(responses.map(x => x.status), [200, 200]);
  assert.equal(challenges, 1);
  cookie = undefined;
  assert.equal((await client.fetchRecording(key)).status, 200);
  assert.equal(challenges, 2);
});
