const ownerShell = "<!doctype html>\n<html lang=\"vi\">\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n<meta name=\"description\" content=\"Tìm âm thanh, phối nhiều lớp trên timeline và xuất bản phối WAV hoặc video MP4.\">\n<title>WhiteNoiseChoir Studio · Phòng phối âm</title>\n<meta name=\"robots\" content=\"noindex,nofollow\">\n<link rel=\"stylesheet\" href=\"/studio.css\"><link rel=\"stylesheet\" href=\"/studio-owner.css\">\n<body data-owner-studio=\"1\">\n<header class=\"studio-header\">\n  <a class=\"brand\" href=\"/vi/\" aria-label=\"WhiteNoiseChoir Studio\">\n    <span class=\"brand-mark\" aria-hidden=\"true\"><i></i><i></i><i></i><i></i></span>\n    WhiteNoiseChoir <span>Studio</span>\n  </a>\n  <nav class=\"studio-nav\" aria-label=\"Điều hướng\"><a href=\"/library/\">Bản phối công khai</a><a href=\"/\" lang=\"en\">English</a><button id=\"export-link\" class=\"primary\" type=\"button\">Xuất bản phối <span aria-hidden=\"true\">↘</span></button></nav>\n</header>\n<main>\n  <div id=\"mix-controls\" class=\"project-bar\">\n    <div class=\"project-name\">\n      <h1>Phòng phối âm</h1>\n      <input id=\"title\" type=\"text\" aria-label=\"Tên bản phối\" maxlength=\"100\" placeholder=\"Đặt tên bản phối\">\n    </div>\n    <div class=\"project-actions\">\n      <label class=\"preset-picker\"><span>Bản mẫu</span>\n        <select id=\"preset\" aria-label=\"Mở bản mẫu\">\n          <option value=\"\">Chọn bản mẫu</option>\n          <option value=\"streamside\">Suối rừng</option>\n          <option value=\"cabin-rain-night\">Cabin mưa đêm</option>\n          <option value=\"cabin-rain-night-v2\">Cabin mưa đêm · V2</option>\n          <option value=\"cabin-rain-night-v3\">Cabin mưa đêm · V3</option>\n        </select>\n      </label>\n      <button id=\"undo\" type=\"button\" aria-label=\"Hoàn tác\" title=\"Hoàn tác (Ctrl+Z)\">↶</button>\n      <button id=\"redo\" type=\"button\" aria-label=\"Làm lại\" title=\"Làm lại (Ctrl+Shift+Z)\">↷</button>\n      <button id=\"owner-save\" type=\"button\">Lưu bản thử</button><button id=\"owner-publish\" class=\"primary\" type=\"button\">Public</button><button id=\"share\" type=\"button\" hidden>Chia sẻ</button>\n      <details class=\"project-menu\">\n        <summary>Dự án</summary>\n        <div class=\"project-menu-items\">\n          <button id=\"clear\" type=\"button\">Tạo bản phối mới</button>\n          <button id=\"save-project\" type=\"button\">Tải dự án JSON</button>\n          <label class=\"file-picker\">Mở dự án JSON<input type=\"file\" id=\"open-project\" accept=\".json,application/json\" aria-label=\"Mở dự án JSON\"></label>\n        </div>\n      </details>\n    </div>\n  </div>\n\n  <p id=\"owner-result\" class=\"message\" role=\"status\"></p>\n  <div id=\"mix-editor\" class=\"studio-grid\">\n    <aside class=\"panel library-panel\" aria-labelledby=\"library-heading\">\n      <div class=\"panel-heading\">\n        <h2 id=\"library-heading\">Thư viện âm thanh</h2>\n        <output id=\"library-count\" aria-live=\"polite\"></output>\n      </div>\n      <label class=\"library-search\">\n        <span aria-hidden=\"true\">⌕</span>\n        <input id=\"library-query\" type=\"search\" placeholder=\"Tìm mưa, sóng, tiếng quạt…\" autocomplete=\"off\" aria-label=\"Tìm âm thanh\">\n        <kbd aria-hidden=\"true\">/</kbd>\n      </label>\n      <select id=\"library-group\" aria-label=\"Lọc nhóm âm thanh\"><option value=\"\">Tất cả nhóm</option></select>\n      <p id=\"library-status\" class=\"message\" role=\"status\"></p>\n      <p id=\"owner-catalog-status\" class=\"message\" role=\"status\">Đang tải danh mục R2…</p>\n      <div id=\"library\" class=\"library-list\"></div><button id=\"library-more\" class=\"library-more\" type=\"button\" hidden>Hiện thêm</button>\n      <audio id=\"library-audio\" preload=\"none\" hidden></audio>\n    </aside>\n\n    <section class=\"panel timeline-panel\" aria-labelledby=\"timeline-heading\">\n      <div class=\"panel-heading timeline-heading\">\n        <div><h2 id=\"timeline-heading\">Dòng thời gian</h2><output id=\"layer-count\"></output></div>\n        <label class=\"zoom-control\"><span>Thu phóng</span>\n          <select id=\"zoom\" aria-label=\"Thu phóng dòng thời gian\">\n            <option value=\"1\">Vừa khung</option><option value=\"2\">2×</option><option value=\"4\">4×</option><option value=\"8\">8×</option>\n          </select>\n        </label>\n      </div>\n      <div class=\"transport\">\n        <button id=\"play\" class=\"primary\" type=\"button\" aria-keyshortcuts=\"Space\">Phát</button>\n        <button id=\"reset\" type=\"button\" title=\"Về đầu\">Về đầu</button>\n        <button id=\"tail\" type=\"button\">Nghe điểm lặp</button>\n        <output id=\"time\" class=\"transport-time\"></output>\n      </div>\n      <input id=\"seek\" type=\"range\" min=\"0\" step=\".01\" aria-label=\"Vị trí phát\">\n      <div id=\"timeline-scroll\" class=\"timeline-scroll\" tabindex=\"0\" aria-label=\"Các lớp trên dòng thời gian\">\n        <div id=\"timeline-canvas\">\n          <div class=\"timeline-row timeline-ruler\"><span class=\"track-column\">Lớp âm thanh</span><div id=\"time-ruler\"></div></div>\n          <div id=\"tracks\"></div>\n        </div>\n      </div>\n      <div class=\"master-strip\">\n        <label for=\"master\">Âm lượng tổng</label>\n        <input id=\"master\" type=\"range\" min=\"0\" max=\"100\" step=\"1\" value=\"100\">\n        <output id=\"master-value\" for=\"master\">100%</output>\n        <meter id=\"peak\" min=\"-60\" max=\"0\" low=\"-24\" high=\"-3\" optimum=\"-12\" value=\"-60\" aria-label=\"Mức đỉnh âm thanh (dBFS)\"></meter>\n      </div>\n      <p id=\"status\" class=\"message studio-status\" role=\"status\"></p>\n    </section>\n\n    <aside class=\"panel inspector-panel\" aria-labelledby=\"inspector-heading\">\n      <div class=\"panel-heading\"><h2 id=\"inspector-heading\">Thông số lớp</h2></div>\n      <div id=\"inspector\"></div>\n    </aside>\n  </div>\n\n<section id=\"video-studio\" class=\"panel\" aria-labelledby=\"export-heading\">\n<h2 id=\"export-heading\">Xuất âm thanh và video</h2>\n<div class=\"export-grid\">\n<div class=\"export-step\">\n<h3>1. Xuất âm thanh WAV</h3>\n<p class=\"muted\">Thời lượng WAV đã xuất sẽ dùng cho video nền và video thành phẩm.</p>\n<div class=\"row\"><label>Thời lượng (phút) <input id=\"minutes\" type=\"number\" min=\"0.1\" max=\"180\" step=\"0.1\"></label><button id=\"render\" class=\"primary\">Xuất WAV</button></div>\n<progress id=\"audio-progress\" max=\"100\" value=\"0\" aria-label=\"Tiến độ xuất âm thanh\"></progress>\n<p id=\"audio-status\" role=\"status\">Chưa xuất âm thanh.</p>\n<div id=\"audio-result\"></div>\n</div>\n<div class=\"export-step\">\n<h3>2. Tải clip lên và kéo dài video nền</h3>\n<label for=\"video-prompt\">Câu lệnh tạo clip bằng AI</label>\n<textarea id=\"video-prompt\" maxlength=\"3000\" placeholder=\"Nhập câu lệnh cho bản phối này\"></textarea>\n<div class=\"row\">\n<button id=\"copy-prompt\">Sao chép câu lệnh</button><span id=\"prompt-status\" role=\"status\" class=\"muted\"></span>\n</div>\n<div class=\"row video-actions\">\n<label class=\"file-picker\">Chọn clip ngắn <input type=\"file\" id=\"video-input\" accept=\"video/*,.mov,.mkv\" aria-label=\"Chọn clip ngắn\"></label>\n<span id=\"clip-name\" class=\"muted\">Chưa chọn clip</span>\n<button id=\"render-video\" class=\"primary\" disabled>Kéo dài video nền</button>\n</div>\n<video id=\"video-preview\" controls muted loop playsinline hidden aria-label=\"Xem trước clip ngắn\"></video>\n<progress id=\"video-progress\" max=\"100\" value=\"0\" aria-label=\"Tiến độ kéo dài video nền\"></progress>\n<p id=\"video-status\" role=\"status\">Xuất WAV và chọn clip để bắt đầu.</p>\n<div id=\"video-result\"></div>\n</div>\n<div class=\"export-step\">\n<h3>3. Ghép âm thanh vào video</h3>\n<p class=\"muted\">Ghép bản WAV ở bước 1 vào video nền ở bước 2. Video thành phẩm dùng âm thanh của bản phối.</p>\n<button id=\"mux-video\" class=\"primary\" disabled>Ghép và xuất MP4</button>\n<progress id=\"mux-progress\" max=\"100\" value=\"0\" aria-label=\"Tiến độ ghép âm thanh và video\"></progress>\n<p id=\"mux-status\" role=\"status\">Đang chờ video nền.</p>\n<div id=\"mux-result\"></div>\n</div>\n</div>\n</section>\n<details class=\"audio-check\"><summary>Kiểm tra âm thanh</summary><p>Phát thử bản ghi tiếng suối gốc.</p><audio id=\"audio-check\" controls preload=\"none\"></audio></details>\n<dialog id=\"owner-dialog\" aria-labelledby=\"owner-dialog-title\">\n<form id=\"owner-form\">\n<h2 id=\"owner-dialog-title\">Lưu bản thử</h2>\n<label>Tên trong đường dẫn <input id=\"owner-slug\" required maxlength=\"100\" pattern=\"[a-z0-9]+(-[a-z0-9]+)*\" autocomplete=\"off\"></label>\n<div id=\"owner-publish-fields\" hidden>\n<label>Tên trên thư viện tiếng Anh <input id=\"owner-public-title\" maxlength=\"100\"></label>\n<label>Tệp thành phẩm <input id=\"owner-media\" type=\"file\" accept=\".mp3,.wav,.m4a,.mp4\"></label>\n<p id=\"owner-media-hint\" class=\"message\"></p>\n</div>\n<p id=\"owner-feedback\" class=\"message\" role=\"status\"></p>\n<button id=\"owner-submit\" class=\"primary\" type=\"submit\">Lưu bản thử</button>\n<button id=\"owner-cancel\" type=\"button\">Đóng</button>\n</form>\n</dialog>\n</main>\n\n<script src=\"/studio-locale.js\"></script>\n<script src=\"/studio-catalog.js\"></script>\n<script src=\"/studio-legacy-recipes.js\"></script>\n<!--STUDIO_DRAFT--><script src=\"/studio-engine.js?owner=1\"></script>\n<script src=\"/studio-ui.js\"></script>\n<script src=\"/studio-owner.js\"></script>\n</body>\n</html>\n";
const legacySourceKeys = ["asset-library/raw/sha256/be/be201d2fd0d110fc3ef5d8af060e5ac48439fd54e9f26ce6b69825182748a95b.wav","asset-library/raw/sha256/0a/0a3c133128b94306396567cfc22ded8363645869d762c2bbc76b5c3519017cff.m4a","asset-library/raw/sha256/0b/0bf24b2b08299380add4e29b6ed0c9ed37ffaa26a19e3908e5b572d75ef7cabe.m4a","asset-library/raw/sha256/06/06c95f291596cfc813ff54d636ae926493ed6cd9c8a10d30f049a70460048af1.mp3","asset-library/raw/sha256/2b/2b5e3902314cbb5d54c26164dc4264a1fdebf61f5012e6f378f6f3e313c7e91a.m4a",null,null,"asset-library/raw/sha256/bf/bfc073e6226f2a21a87567b898c5e5674a53284353128da0d1e0f69b97e8b62f.mp3",null,null,null,null,null,null,null];
const {createSession, hasSession, headersFor, readMedia} = (() => {
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


return {createSession, hasSession, headersFor, readMedia};
})();

const origin = 'https://whitenoisechoir.com';
const mainHost = new URL(origin).hostname;
const mediaHost = 'media.whitenoisechoir.com';
const slugPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const sourcePattern = /^asset-library\/(?:commons|raw|kenney|cc0-github-mirror)\/sha256\/([a-f0-9]{2})\/([a-f0-9]{64})\.(aac|flac|m4a|mp3|mp4|ogg|oga|opus|wav|webm)$/;
const mediaTypes = new Map([['audio/mpeg','mp3'],['audio/wav','wav'],['audio/mp4','m4a'],['video/mp4','mp4']]);
const accessKeys = new Map();
const encoder = new TextEncoder();
const decoder = new TextDecoder();
const noStore = {'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'};
const privateResponse = {...noStore,'X-Robots-Tag':'noindex, nofollow'};
const htmlEscape = value => String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
const json = (value,status=200) => Response.json(value,{status,headers:noStore});
const empty = status => new Response(null,{status,headers:noStore});
const validSlug = value => value.length<=100 && slugPattern.test(value);
const fileKey = slug => 'drafts/'+slug+'.json';
const releaseKey = slug => 'published/'+slug+'.json';
const allowedSlug = slug => validSlug(slug) && !['api','catalog-setup'].includes(slug);
const decode64 = value => Uint8Array.from(atob(value.replaceAll('-','+').replaceAll('_','/')),c=>c.charCodeAt(0));

async function accessPublicKey(team,kid) {
  const cached = accessKeys.get(team);
  if (cached?.until>Date.now() && cached.keys.has(kid)) return cached.keys.get(kid);
  if (cached?.until>Date.now() && cached.fetched+15000>Date.now()) return null;
  const response = await fetch('https://'+team+'/cdn-cgi/access/certs',{signal:AbortSignal.timeout(5000)});
  if (!response.ok) return null;
  const payload = await response.json();
  const keys = new Map(payload.keys.filter(key=>key.kty==='RSA' && key.alg==='RS256' && key.kid).map(key=>[key.kid,key]));
  const now = Date.now();
  accessKeys.set(team,{keys,fetched:now,until:now+300000});
  return keys.get(kid);
}

export async function authorized(request,env) {
  const team = env.ACCESS_TEAM_DOMAIN;
  const owners = (env.STUDIO_OWNER_EMAILS || '').split(',').map(email=>email.trim().toLowerCase()).filter(Boolean);
  const token = request.headers.get('Cf-Access-Jwt-Assertion');
  if (!team || !/^[a-z0-9-]+\.cloudflareaccess\.com$/.test(team) || !env.ACCESS_AUD || !owners.length ||
      !token || token.length>8192 || !/^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){2}$/.test(token)) return false;
  try {
    const [header,claims,signature] = token.split('.');
    const {alg,kid} = JSON.parse(decoder.decode(decode64(header)));
    const {iss,aud,exp,nbf,email,type} = JSON.parse(decoder.decode(decode64(claims)));
    const now = Date.now()/1000;
    if (alg!=='RS256' || typeof kid!=='string' || iss!=='https://'+team || type!=='app' ||
        !(Array.isArray(aud)?aud:[aud]).includes(env.ACCESS_AUD) || !Number.isFinite(exp) || exp<=now ||
        (nbf!==undefined && (!Number.isFinite(nbf) || nbf>now+5)) ||
        typeof email!=='string' || !owners.includes(email.toLowerCase())) return false;
    const jwk = await accessPublicKey(team,kid);
    if (!jwk) return false;
    const key = await crypto.subtle.importKey('jwk',jwk,{name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['verify']);
    return await crypto.subtle.verify('RSASSA-PKCS1-v1_5',key,decode64(signature),encoder.encode(header+'.'+claims));
  } catch { return false; }
}

function html(content,status=200,headers=noStore) {
  return new Response(content,{status,headers:{...headers,'Content-Type':'text/html; charset=utf-8'}});
}
async function objectJson(bucket,key) {
  const value = await bucket.get(key);
  return value ? value.json() : null;
}
async function jsonBody(request,maxBytes) {
  if (!request.body || request.headers.get('Content-Type')?.split(';',1)[0]!=='application/json') return null;
  const reader = request.body.getReader();
  const bodyDecoder = new TextDecoder();
  const chunks = [];
  let size = 0;
  try {
    for (;;) {
      const {done,value} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size>maxBytes) { await reader.cancel();return null; }
      chunks.push(bodyDecoder.decode(value,{stream:true}));
    }
    chunks.push(bodyDecoder.decode());
    return JSON.parse(chunks.join(''));
  } catch { return null; }
}

function studioHtml(draft) {
  const jsonText = JSON.stringify(draft).replaceAll('<','\\u003c');
  return ownerShell.replace('<!--STUDIO_DRAFT-->',()=>draft?'<script type="application/json" id="studio-trial">'+jsonText+'</script>':'');
}

async function saveDraft(request,env,slug) {
  const payload = await jsonBody(request,128*1024);
  const project = payload?.project;
  if (typeof project?.title!=='string' || !project.title.trim() || project.title.length>100 ||
      !Number.isFinite(project.length) || project.length<6 || project.length>10800 ||
      !Array.isArray(project.tracks) || project.tracks.length>32 ||
      project.tracks.some(track=>!track || !Number.isFinite(track.start) || !Number.isFinite(track.gain) ||
        (track.assetRef!==undefined && (typeof track.assetRef!=='string' || track.assetRef.length>90)))) {
    return json({error:'Dự án không hợp lệ.'},400);
  }
  const draft = {slug,title:project.title.trim(),project,revision:crypto.randomUUID(),updatedAt:new Date().toISOString()};
  await env.STUDIO_STATE.put(fileKey(slug),JSON.stringify(draft),{httpMetadata:{contentType:'application/json'}});
  return json({url:'/vi/'+slug+'/',revision:draft.revision});
}

async function publish(request,env,slug) {
  const draft = await objectJson(env.STUDIO_STATE,fileKey(slug));
  if (!draft) return json({error:'Hãy lưu bản thử trước khi Public.'},409);
  const type = request.headers.get('Content-Type')?.split(';',1)[0];
  const extension = mediaTypes.get(type);
  if (!extension || !request.body || request.headers.get('Content-Length')==='0') {
    return json({error:'Chọn tệp MP3, WAV, M4A hoặc MP4 thành phẩm.'},415);
  }
  if (request.headers.get('X-Studio-Draft')!==draft.revision) return json({error:'Bản thử đã thay đổi. Hãy lưu lại.'},409);
  const key = 'published-media/'+slug+'/'+crypto.randomUUID()+'.'+extension;
  const object = await env.STUDIO_STATE.put(key,request.body,{httpMetadata:{contentType:type}});
  if (!object?.size) {
    await env.STUDIO_STATE.delete(key).catch(()=>{});
    return json({error:'Tệp thành phẩm rỗng.'},400);
  }
  const publicTitle = new URL(request.url).searchParams.get('title')?.trim().slice(0,100);
  const record = {slug,title:publicTitle || draft.title,key,extension,publishedAt:new Date().toISOString()};
  try {
    await env.STUDIO_STATE.put(releaseKey(slug),JSON.stringify(record),{
      httpMetadata:{contentType:'application/json'},
      customMetadata:{title:record.title,publishedAt:record.publishedAt},
    });
  } catch (error) {
    await env.STUDIO_STATE.delete(key).catch(()=>{});
    throw error;
  }
  return json({url:'/library/'+slug+'/'},201);
}

function libraryHtml(title,body) {
  return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+
    '<title>'+htmlEscape(title)+' · WhiteNoiseChoir</title><link rel="stylesheet" href="/studio.css"><body>'+
    '<header class="studio-header"><a class="brand" href="/">WhiteNoiseChoir</a><nav class="studio-nav" aria-label="Navigation">'+
    '<a href="/">Sound Studio</a><a href="/library/">Published mixes</a></nav></header>'+
    '<main class="published-library">'+body+'</main></body></html>';
}
async function listPublished(bucket) {
  const records = [];
  let cursor;
  do {
    const page = await bucket.list({prefix:'published/',include:['customMetadata'],limit:1000,cursor});
    for (const item of page.objects) {
      const slug = item.key.slice('published/'.length,-'.json'.length);
      if (allowedSlug(slug) && item.customMetadata?.title && item.customMetadata.publishedAt) records.push({slug,...item.customMetadata});
    }
    cursor = page.truncated ? page.cursor : undefined;
  } while (cursor);
  return records.sort((a,b)=>b.publishedAt.localeCompare(a.publishedAt));
}

async function catalog(bucket,key,publicCatalog=false) {
  const object = await bucket.get(key);
  if (!object) return empty(404);
  return new Response(object.body,{headers:{...(publicCatalog?noStore:privateResponse),
    'Content-Type':'application/json','Cache-Control':publicCatalog?'public, max-age=120':'private, no-store'}});
}

async function publicMedia(request,env,url,id,legacyIndex) {
  const limit = env.DOWNLOAD_RATE;
  const ip = request.headers.get('CF-Connecting-IP');
  if (!env.TURNSTILE_SECRET_KEY || !limit || !ip || env.PUBLIC_CATALOG_ENABLED!=='true') return empty(503);
  if (!await hasSession(request,env.TURNSTILE_SECRET_KEY)) return empty(401);
  if (!(await limit.limit({key:ip})).success) return new Response(null,{status:429,headers:{...noStore,'Retry-After':'60'}});
  const key = legacyIndex===undefined
    ? (await objectJson(env.STUDIO_STATE,'catalog/sources/'+id.slice(0,2)+'.json'))?.[id]
    : legacySourceKeys[legacyIndex];
  const match = sourcePattern.exec(key || '');
  if (!match || !match[2].startsWith(match[1])) return empty(404);
  if (url.searchParams.has('download')) {
    if (match[3]!=='mp3') return empty(404);
    url.searchParams.set('download','WhiteNoiseChoir-'+(id || 'source-'+legacyIndex).slice(0,20));
  }
  return readMedia(request,env,new Headers(noStore),key,match[3],url);
}

export default {
  async fetch(request,env) {
    const url = new URL(request.url);
    const path = url.pathname;
    if (url.hostname===mediaHost) return empty(404);
    if (url.hostname!==mainHost) return empty(404);
    if (!env.STUDIO_STATE || !env.MEDIA) return empty(503);
    const method = request.method;
    try {
      if (path==='/api/studio/catalog' && method==='GET') {
        return env.PUBLIC_CATALOG_ENABLED==='true' ? catalog(env.STUDIO_STATE,'catalog/public.json',true) : empty(404);
      }
      if (path==='/api/studio/session') {
        if (env.PUBLIC_CATALOG_ENABLED!=='true' || !env.TURNSTILE_SECRET_KEY) return empty(503);
        const headers = headersFor(request.headers.get('Origin'));
        if (method==='POST') return createSession(request,env,headers,request.headers.get('Origin'));
        if (method==='GET') {
          const expiresAt = await hasSession(request,env.TURNSTILE_SECRET_KEY);
          return expiresAt ? json({expiresAt}) : empty(401);
        }
        return empty(405);
      }
      const audio = /^\/api\/studio\/sources\/([a-f0-9]{32})$/.exec(path);
      if (audio && (method==='GET' || method==='HEAD')) return publicMedia(request,env,url,audio[1]);
      const legacy = /^\/api\/studio\/legacy\/(\d{1,2})$/.exec(path);
      if (legacy && (method==='GET' || method==='HEAD')) return publicMedia(request,env,url,undefined,Number(legacy[1]));
      const media = /^\/api\/studio\/mixes\/([^/]+)\/media$/.exec(path);
      if (media && allowedSlug(media[1]) && (method==='GET' || method==='HEAD')) {
        const record = await objectJson(env.STUDIO_STATE,releaseKey(media[1]));
        if (!record) return empty(404);
        return readMedia(request,{MEDIA:env.STUDIO_STATE},new Headers(noStore),record.key,record.extension,url);
      }
      if ((path==='/library/' || path==='/library') && method==='GET') {
        const records = await listPublished(env.STUDIO_STATE);
        const cards = records.map(record=>'<article class="panel published-card"><h2><a href="/library/'+record.slug+'/">'+
          htmlEscape(record.title)+'</a></h2></article>').join('');
        return html(libraryHtml('Published mixes','<h1>Published mixes</h1>'+
          (cards?'<div class="published-grid">'+cards+'</div>':'<p>No mixes have been published yet.</p>')));
      }
      const library = /^\/library\/([^/]+)\/?$/.exec(path);
      if (library && allowedSlug(library[1]) && method==='GET') {
        const record = await objectJson(env.STUDIO_STATE,releaseKey(library[1]));
        if (!record) return empty(404);
        const player = record.extension==='mp4'?'video':'audio';
        const source = '/api/studio/mixes/'+record.slug+'/media';
        return html(libraryHtml(record.title,'<h1>'+htmlEscape(record.title)+'</h1><'+player+' controls preload="metadata" src="'+source+
          '"></'+player+'>'+(record.extension==='mp3'?'<p><a download href="'+source+'?download='+encodeURIComponent(record.slug)+'">Download MP3</a></p>':'')));
      }
      if (path!=='/vi' && !path.startsWith('/vi/')) return empty(404);
      if (!await authorized(request,env)) return html('<!doctype html><html lang="vi"><meta charset="utf-8"><title>Studio nội bộ</title><h1>Studio nội bộ</h1><p>Đăng nhập qua Cloudflare Access để tiếp tục.</p>',401,privateResponse);
      if (!['GET','HEAD'].includes(method) && request.headers.get('Origin')!==origin) return empty(403);
      if (path==='/vi/api/catalog' && method==='GET') return catalog(env.STUDIO_STATE,'catalog/owner.json');
      if (path.startsWith('/vi/api/source/') && (method==='GET'||method==='HEAD')) {
        const key = decodeURIComponent(path.slice('/vi/api/source/'.length));
        const match = sourcePattern.exec(key);
        return match && match[2].startsWith(match[1]) ? readMedia(request,env,new Headers(privateResponse),key,match[3],url) : empty(404);
      }
      const draft = /^\/vi\/api\/drafts\/([^/]+)$/.exec(path);
      if (draft && allowedSlug(draft[1]) && method==='PUT') return saveDraft(request,env,draft[1]);
      const release = /^\/vi\/api\/drafts\/([^/]+)\/publish$/.exec(path);
      if (release && allowedSlug(release[1]) && method==='POST') return publish(request,env,release[1]);
      if ((path==='/vi/' || path==='/vi') && method==='GET') return html(studioHtml(null),200,privateResponse);
      const trial = /^\/vi\/([^/]+)\/?$/.exec(path);
      if (trial && allowedSlug(trial[1]) && method==='GET') {
        const project = await objectJson(env.STUDIO_STATE,fileKey(trial[1]));
        const cabin = trial[1]==='cabin-rain-night-v3' ? {slug:trial[1],title:'Cabin trong mưa đêm · V3',preset:trial[1]} : null;
        if (!project && !cabin) return empty(404);
        return html(studioHtml(project || cabin),200,privateResponse);
      }
      return empty(404);
    } catch {
      return json({error:'Studio tạm thời không xử lý được yêu cầu.'},503);
    }
  },
};
