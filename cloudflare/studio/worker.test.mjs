import assert from 'node:assert/strict';
import test from 'node:test';
import worker from './worker.mjs';

const main = 'https://whitenoisechoir.com';
const team = 'owner-test.cloudflareaccess.com';
const email = 'owner@example.test';
const audience = 'test-application';
const algorithm = {name:'RSASSA-PKCS1-v1_5',modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:'SHA-256'};
const keys = await crypto.subtle.generateKey(algorithm,true,['sign','verify']);
const jwk = {...await crypto.subtle.exportKey('jwk',keys.publicKey),kid:'owner-test'};
const realFetch = globalThis.fetch;
globalThis.fetch = async (url,options) => {
  if (url==='https://challenges.cloudflare.com/turnstile/v0/siteverify') {
    assert.equal(options.body.get('response'),'fixture-turnstile-token');
    return Response.json({success:true,hostname:'whitenoisechoir.com',action:'media_access'});
  }
  assert.equal(url,'https://'+team+'/cdn-cgi/access/certs');
  return Response.json({keys:[jwk]});
};
const encode = obj => Buffer.from(JSON.stringify(obj)).toString('base64url');
async function token(claims) {
  const signed = encode({alg:'RS256',kid:jwk.kid})+'.'+encode({
    aud:[audience],iss:'https://'+team,exp:Date.now()/1000+60,type:'app',email,...claims,
  });
  const signature = await crypto.subtle.sign(algorithm.name,keys.privateKey,Buffer.from(signed));
  return signed+'.'+Buffer.from(signature).toString('base64url');
}
class MemoryBucket {
  rows = new Map();
  async put(key,value,options={}) {
    const bytes = new Uint8Array(await new Response(value).arrayBuffer());
    this.rows.set(key,{bytes,options});
    return this.head(key);
  }
  async delete(key) { this.rows.delete(key); }
  async head(key) {
    const row = this.rows.get(key);
    return row && {size:row.bytes.length,httpEtag:'"test"'};
  }
  async get(key,options) {
    const row = this.rows.get(key);
    if (!row) return null;
    const range = options?.range;
    const bytes = range ? row.bytes.subarray(range.offset,range.offset+range.length) : row.bytes;
    return {...await this.head(key),body:bytes,json:async()=>JSON.parse(Buffer.from(bytes).toString())};
  }
  async list({prefix}) {
    return {objects:[...this.rows].filter(([key])=>key.startsWith(prefix))
      .map(([key,row])=>({key,customMetadata:row.options.customMetadata})),truncated:false};
  }
}

test('owner can edit a private draft and publish only a selected media file',async()=>{
  const env = {
    ACCESS_TEAM_DOMAIN:team,ACCESS_AUD:audience,STUDIO_OWNER_EMAILS:email,
    STUDIO_STATE:new MemoryBucket(),MEDIA:new MemoryBucket(),
  };
  const auth = {'Cf-Access-Jwt-Assertion':await token()};
  const call = (path,options)=>worker.fetch(new Request(main+path,options),env);
  const save = (headers,title='Cảnh mưa <test>')=>call('/vi/api/drafts/canh-mua',{
    method:'PUT',headers:{'Content-Type':'application/json',...headers},
    body:JSON.stringify({project:{title,length:60,tracks:[{asset:0,start:0,gain:1}]}}),
  });
  assert.equal((await call('/vi/')).status,401);
  assert.equal((await call('/vi/canh-mua/')).status,401);
  assert.equal((await call('/vi/',{headers:{'Cf-Access-Jwt-Assertion':await token({email:'other@example.test'})}})).status,401);
  assert.equal((await call('/vi/',{headers:{'Cf-Access-Jwt-Assertion':await token({aud:['other']})}})).status,401);
  assert.equal((await call('/vi/',{headers:{'Cf-Access-Jwt-Assertion':await token({exp:1})}})).status,401);
  assert.equal((await save(auth)).status,403);
  const editor = await call('/vi/',{headers:auth});
  assert.equal(editor.status,200);
  assert.equal(editor.headers.get('x-robots-tag'),'noindex, nofollow');
  assert.match(await editor.text(),/id="owner-publish"/);
  const write = {...auth,Origin:main};
  const saved = await (await save(write)).json();
  assert.equal(saved.url,'/vi/canh-mua/');
  const draft = await (await call(saved.url,{headers:auth})).text();
  assert.match(draft,/id="studio-trial"/);
  assert.match(draft,/Cảnh mưa \\u003ctest>/);
  assert.equal((await call('/library/canh-mua/')).status,404);
  assert.doesNotMatch(await (await call('/library/')).text(),/Cảnh mưa/);

  const release = revision=>call('/vi/api/drafts/canh-mua/publish',{
    method:'POST',headers:{...write,'Content-Type':'audio/mpeg','X-Studio-Draft':revision},
    body:new Uint8Array([0xff,0xfb,1,2,3,4]),
  });
  assert.equal((await release('stale')).status,409);
  const result = await release(saved.revision);
  assert.equal(result.status,201);
  assert.deepEqual(await result.json(),{url:'/library/canh-mua/'});
  assert.match(await (await call('/library/')).text(),/Cảnh mưa &lt;test&gt;/);
  const view = await (await call('/library/canh-mua/')).text();
  assert.match(view,/<audio controls/);
  assert.match(view,/Download MP3/);
  assert.doesNotMatch(view,/studio-engine|studio-trial|tracks/);
  const audio = await call('/api/studio/mixes/canh-mua/media',{headers:{Range:'bytes=1-2'}});
  assert.equal(audio.status,206);
  assert.deepEqual([...new Uint8Array(await audio.arrayBuffer())],[0xfb,1]);
});
test('anonymous public catalog has no raw origin fallback',async()=>{
  const env = {STUDIO_STATE:new MemoryBucket(),MEDIA:new MemoryBucket()};
  assert.equal((await worker.fetch(new Request(main+'/api/studio/catalog'),env)).status,404);
  env.PUBLIC_CATALOG_ENABLED='true';
  env.TURNSTILE_SECRET_KEY='test-only-secret';
  env.DOWNLOAD_RATE={limit:async()=>({success:true})};
  const request = new Request(main+'/api/studio/mp3/'+'0'.repeat(32),{headers:{'CF-Connecting-IP':'203.0.113.1'}});
  assert.equal((await worker.fetch(request,env)).status,401);
  const id = '0'.repeat(32);
  const source = 'asset-library/raw/sha256/be/'+'be'+'0'.repeat(62)+'.mp3';
  await env.STUDIO_STATE.put('catalog/mp3/00.json',JSON.stringify({[id]:source}));
  await env.STUDIO_STATE.put('catalog/public.json',JSON.stringify({version:1,sounds:[{id,title:'Fixture MP3'}]}));
  await env.MEDIA.put(source,new Uint8Array([0xff,0xfb,0,1]));
  const metadata = await worker.fetch(new Request(main+'/api/studio/catalog'),env);
  assert.doesNotMatch(await metadata.text(),/asset-library|https:\/\/media/);
  const started = await worker.fetch(new Request(main+'/api/studio/session',{
    method:'POST',headers:{Origin:main},body:'fixture-turnstile-token',
  }),env);
  assert.equal(started.status,200);
  const cookie = started.headers.get('Set-Cookie').split(';')[0];
  const download = new Request(request.url+'?download=1',{headers:{Cookie:cookie,'CF-Connecting-IP':'203.0.113.1'}});
  const allowed = await worker.fetch(download,env);
  assert.equal(allowed.status,200);
  assert.match(allowed.headers.get('Content-Disposition'),/^attachment;/);
  assert.equal(allowed.headers.get('Content-Type'),'audio/mpeg');
  env.DOWNLOAD_RATE={limit:async()=>({success:false})};
  assert.equal((await worker.fetch(download,env)).status,429);
  const raw = new Request('https://media.whitenoisechoir.com/asset-library/raw/');
  assert.equal((await worker.fetch(raw,env)).status,404);
});
test.after(()=>{globalThis.fetch=realFetch;});
