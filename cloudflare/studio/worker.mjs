import ownerShell from './owner-shell.mjs';
import {createSession, hasSession, headersFor, readMedia} from './media.mjs';

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
  const record = {slug,title:draft.title,key,extension,publishedAt:new Date().toISOString()};
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
    '<a href="/">MP3 Sounds</a><a href="/library/">Published mixes</a></nav></header>'+
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

async function publicMedia(request,env,url,id) {
  const limit = env.DOWNLOAD_RATE;
  const ip = request.headers.get('CF-Connecting-IP');
  if (!env.TURNSTILE_SECRET_KEY || !limit || !ip || env.PUBLIC_CATALOG_ENABLED!=='true') return empty(503);
  if (!await hasSession(request,env.TURNSTILE_SECRET_KEY)) return empty(401);
  if (!(await limit.limit({key:ip})).success) return new Response(null,{status:429,headers:{...noStore,'Retry-After':'60'}});
  const map = await objectJson(env.STUDIO_STATE,'catalog/mp3/'+id.slice(0,2)+'.json');
  const key = map?.[id];
  const match = sourcePattern.exec(key || '');
  if (!match || !match[2].startsWith(match[1]) || match[3]!=='mp3') return empty(404);
  if (url.searchParams.has('download')) url.searchParams.set('download','WhiteNoiseChoir-'+id.slice(0,12));
  return readMedia(request,env,new Headers(noStore),key,'mp3',url);
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
        if (method==='GET') return await hasSession(request,env.TURNSTILE_SECRET_KEY) ? json({verified:true}) : empty(401);
        return empty(405);
      }
      const audio = /^\/api\/studio\/mp3\/([a-f0-9]{32})$/.exec(path);
      if (audio && (method==='GET' || method==='HEAD')) return publicMedia(request,env,url,audio[1]);
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
