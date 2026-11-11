const SITE_ORIGINS = new Set([
  'https://whitenoisechoir.com',
  'https://www.whitenoisechoir.com',
]);
const COOKIE = '__Host-wnc_media';
const SESSION_SECONDS = 2 * 60 * 60;
const encoder = new TextEncoder();
const MEDIA_TYPES = {
  aac: 'audio/aac', aif: 'audio/aiff', aiff: 'audio/aiff', flac: 'audio/flac',
  m4a: 'audio/mp4', mp3: 'audio/mpeg', mp4: 'video/mp4', ogg: 'audio/ogg', oga: 'audio/ogg',
  opus: 'audio/ogg', wav: 'audio/wav', webm: 'video/webm',
};

function headersFor(origin) {
  const headers = new Headers({
    'Cache-Control': 'private, no-store',
    'X-Content-Type-Options': 'nosniff',
    Vary: 'Origin',
  });
  if (SITE_ORIGINS.has(origin)) {
    headers.set('Access-Control-Allow-Origin', origin);
    headers.set('Access-Control-Allow-Credentials', 'true');
    headers.set('Access-Control-Allow-Methods', 'GET, HEAD, POST, OPTIONS');
    headers.set('Access-Control-Allow-Headers', 'Content-Type, Range');
    headers.set('Access-Control-Expose-Headers', 'Accept-Ranges, Content-Range, ETag');
  }
  return headers;
}

async function signingKey(secret) {
  const material = await crypto.subtle.importKey('raw', encoder.encode(secret), 'HKDF', false, ['deriveKey']);
  return crypto.subtle.deriveKey({
    name: 'HKDF',
    hash: 'SHA-256',
    salt: encoder.encode('whitenoisechoir-media-v1'),
    info: encoder.encode('download-session-cookie'),
  }, material, {name: 'HMAC', hash: 'SHA-256'}, false, ['sign', 'verify']);
}

function base64url(bytes) {
  return btoa(String.fromCharCode(...new Uint8Array(bytes))).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');
}

async function newSession(secret) {
  const expiry = Math.floor(Date.now() / 1000) + SESSION_SECONDS;
  const nonce = base64url(crypto.getRandomValues(new Uint8Array(16)));
  const value = 'v1.' + expiry + '.' + nonce;
  const signature = await crypto.subtle.sign('HMAC', await signingKey(secret), encoder.encode(value));
  return value + '.' + base64url(signature);
}

async function hasSession(request, secret) {
  const cookie = request.headers.get('Cookie')?.split(';').map(part => part.trim())
    .find(part => part.startsWith(COOKIE + '='));
  const match = cookie?.slice(COOKIE.length + 1).match(/^(v1\.(\d{10})\.[A-Za-z0-9_-]{22})\.([A-Za-z0-9_-]{43})$/);
  if (!match || Number(match[2]) <= Math.floor(Date.now() / 1000)) return 0;
  const signature = Uint8Array.from(atob(match[3].replaceAll('-', '+').replaceAll('_', '/') + '='), ch => ch.charCodeAt(0));
  const valid = await crypto.subtle.verify('HMAC', await signingKey(secret), signature, encoder.encode(match[1]));
  return valid ? Number(match[2]) : 0;
}

async function readToken(request) {
  const reader = request.body?.getReader();
  if (!reader) return '';
  const decoder = new TextDecoder();
  let size = 0;
  let token = '';
  while (true) {
    const {done, value} = await reader.read();
    if (done) return (token + decoder.decode()).trim();
    size += value.byteLength;
    if (size > 2048) {
      await reader.cancel();
      return '';
    }
    token += decoder.decode(value, {stream: true});
  }
}

async function createSession(request, env, headers, origin) {
  if (!SITE_ORIGINS.has(origin)) return new Response(null, {status: 403, headers});
  const token = await readToken(request);
  if (!token) return new Response(null, {status: 400, headers});
  const body = new URLSearchParams({secret: env.TURNSTILE_SECRET_KEY, response: token});
  const remoteip = request.headers.get('CF-Connecting-IP');
  if (remoteip) body.set('remoteip', remoteip);
  let result;
  try {
    const verification = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method: 'POST',
      body,
      signal: AbortSignal.timeout(8000),
    });
    if (!verification.ok) return new Response(null, {status: 502, headers});
    result = await verification.json();
  } catch {
    return new Response(null, {status: 502, headers});
  }
  if (result?.success !== true || result.hostname !== new URL(origin).hostname || result.action !== 'media_access') {
    return new Response(null, {status: 403, headers});
  }
  const session = await newSession(env.TURNSTILE_SECRET_KEY);
  headers.set('Set-Cookie', COOKIE + '=' + session +
    '; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=' + SESSION_SECONDS);
  return Response.json({expiresAt: Number(session.split('.')[1])}, {headers});
}

function parseRange(header, size) {
  const match = /^bytes=(\d*)-(\d*)$/.exec(header);
  if (!match || (!match[1] && !match[2]) || size === 0) return null;
  const start = Number(match[1]);
  const end = Number(match[2]);
  if (!Number.isSafeInteger(start) || !Number.isSafeInteger(end)) return null;
  if (!match[1]) {
    if (end === 0) return null;
    const length = Math.min(size, end);
    return {offset: size - length, length};
  }
  if (start >= size || (match[2] && end < start)) return null;
  return {offset: start, length: (match[2] ? Math.min(end, size - 1) : size - 1) - start + 1};
}

async function readMedia(request, env, headers, key, extension, url) {
  let range;
  const rangeHeader = request.method === 'GET' && !request.headers.has('If-Range') && request.headers.get('Range');
  if (rangeHeader) {
    const metadata = await env.MEDIA.head(key);
    if (!metadata) return new Response(null, {status: 404, headers});
    range = parseRange(rangeHeader, metadata.size);
    if (!range) {
      headers.set('Content-Range', 'bytes */' + metadata.size);
      return new Response(null, {status: 416, headers});
    }
  }
  const object = request.method === 'HEAD'
    ? await env.MEDIA.head(key)
    : await env.MEDIA.get(key, range ? {range} : undefined);
  if (!object) return new Response(null, {status: 404, headers});
  headers.set('Content-Type', MEDIA_TYPES[extension]);
  headers.set('Accept-Ranges', 'bytes');
  headers.set('Content-Length', String(range?.length ?? object.size));
  headers.set('ETag', object.httpEtag);
  if (url.searchParams.has('download')) {
    const label = url.searchParams.get('download').replace(/[\x00-\x1f\x7f/\\]/g, ' ').trim();
    const filename = encodeURIComponent(Array.from(label || 'WhiteNoiseChoir').slice(0, 100).join('') + '.' + extension)
      .replace(/['()*]/g, ch => '%' + ch.charCodeAt(0).toString(16).toUpperCase());
    headers.set('Content-Disposition', "attachment; filename*=UTF-8''" + filename);
  }
  if (range) headers.set('Content-Range', 'bytes ' + range.offset + '-' + (range.offset + range.length - 1) + '/' + object.size);
  return new Response(request.method === 'HEAD' ? null : object.body, {status: range ? 206 : 200, headers});
}

export {createSession, hasSession, headersFor, readMedia};
