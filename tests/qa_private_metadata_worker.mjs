// End-to-end contract checks for private Worker authentication and query routing.
// No production credentials, R2 content or Cloudflare resources are used.
import assert from "node:assert/strict";
import {webcrypto} from "node:crypto";
import worker from "../internal/metadata-ai-search/worker.mjs";
globalThis.crypto ||= webcrypto;
const keys=await webcrypto.subtle.generateKey({name:"RSASSA-PKCS1-v1_5",modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:"SHA-256"},true,["sign","verify"]);
const jwk=await webcrypto.subtle.exportKey("jwk",keys.publicKey);
jwk.kid="test-key";
const b64=x=>Buffer.from(typeof x==="string"?x:JSON.stringify(x)).toString("base64url");
async function token(override={}) {
 const header=b64({alg:"RS256",kid:"test-key"});
 const payload=b64({iss:"https://team.cloudflareaccess.com",aud:["wnc-test-aud"],exp:Math.floor(Date.now()/1000)+120,...override});
 const body=header+"."+payload;
 const signature=await webcrypto.subtle.sign("RSASSA-PKCS1-v1_5",keys.privateKey,new TextEncoder().encode(body));
 return body+"."+Buffer.from(signature).toString("base64url");
}
let queries=[];
const fixtureRow = {
 id:"nature:example",source_class:"nature",name:"Bird",scientific_name:"Aves",sound_family:"birds",
 habitat:"rainforest",region:"southeast-asia",provider:"Test",source_page:"https://example.org/audio",
 license:"CC0-1.0",duration:18,has_r2_audio:1,qa_status:"pending"
};
const db = {
 prepare(sql) {
  return {
   first: async () => ({n:22239}),
   bind(...args) {
    queries.push({sql,args});
    return {all: async () => ({results:[fixtureRow]})};
   }
  };
 }
};
const env={ACCESS_TEAM_DOMAIN:"team.cloudflareaccess.com",ACCESS_AUD:"wnc-test-aud",METADATA_DB:db};
const originalFetch=globalThis.fetch;
globalThis.fetch=async url=>{
 assert.equal(url,"https://team.cloudflareaccess.com/cdn-cgi/access/certs");
 return new Response(JSON.stringify({keys:[jwk]}),{status:200,headers:{"Content-Type":"application/json"}});
};
const request=(path,t,method="GET")=>new Request("https://private.example"+path,{method,headers:t?{"Cf-Access-Jwt-Assertion":t}:{}});
async function expectStatus(path,t,status,method="GET") {
 const r=await worker.fetch(request(path,t,method),env);
 assert.equal(r.status,status,path);
 assert.equal(r.headers.get("Cache-Control"),"private, no-store");
 return r.json();
}
try {
 assert.equal((await expectStatus("/search?q=birds",null,401)).error,"unauthorized");
 assert.equal((await expectStatus("/search?q=birds","invalid.jwt.token",401)).error,"unauthorized");
 assert.equal((await expectStatus("/search?q=birds",await token({aud:["wrong-aud"]}),401)).error,"unauthorized");
 assert.equal((await expectStatus("/search?q=birds",await token({exp:1}),401)).error,"unauthorized");
 const valid=await token();
 assert.equal((await expectStatus("/health",valid,200)).indexed_total,22239);
 assert.equal((await expectStatus("/search?q=chim%20r%E1%BB%ABng&class=nature&has_audio=1&region=southeast-asia&limit=3",valid,200)).count,1);
 const q=queries.at(-1);
 assert.match(q.sql,/search MATCH \?/);
 assert.ok(q.args[0].includes("birds"),"Vietnamese term must expand");
 assert.ok(q.args.includes("nature"));
 assert.ok(q.args.includes(1));
 assert.ok(q.args.includes("southeast-asia"));
 assert.equal(q.args.at(-1),3);
 assert.equal((await expectStatus("/search?q=",valid,400)).error,"query_required");
 assert.equal((await expectStatus("/nope",valid,404)).error,"not_found");
 assert.equal((await expectStatus("/search?q=birds",valid,405,"POST")).error,"method_not_allowed");
 // SQL injection remains bound as a single MATCH parameter, never part of SQL source.
 await expectStatus("/search?q="+encodeURIComponent('bird" OR 1=1 --'),valid,200);
 const inj=queries.at(-1);
 assert.ok(!inj.sql.includes("1=1"));
 assert.equal(inj.args.length,2);
 console.log("AI_METADATA_WORKER_CONTRACT_QA_PASS",JSON.stringify({
  tests:["missing token","malformed token","wrong audience","expired token","health count",
   "Vietnamese expansion and filters","empty query","404","method guard","SQL parameterization"],
  indexed_baseline_fixture:22239,production_deployment_tested:false}));
}finally {globalThis.fetch=originalFetch;}
