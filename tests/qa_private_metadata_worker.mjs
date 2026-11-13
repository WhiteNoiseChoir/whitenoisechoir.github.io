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
 license:"CC0-1.0",duration:18,r2_key:"private/test-audio.mp3",has_r2_audio:1,qa_status:"pending"
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
 const searchResult=await expectStatus("/search?q=chim%20r%E1%BB%ABng&class=nature&has_audio=1&region=southeast-asia&limit=3",valid,200);
 assert.equal(searchResult.count,1);
 assert.equal(searchResult.results[0].r2_key,"private/test-audio.mp3");
 assert.equal(searchResult.results[0].source_page,"https://example.org/audio");
 assert.equal(searchResult.results[0].qa_status,"pending");
 const q=queries.at(-1);
 assert.match(q.sql,/search MATCH \?/);
 assert.ok(q.args[0].includes("birds"),"Vietnamese term must expand");
 assert.ok(q.args.includes("nature"));
 assert.ok(q.args.includes(1));
 assert.ok(q.args.includes("southeast-asia"));
 assert.equal(q.args.at(-1),3);
 const strict=await expectStatus("/search?q=forest%20stream&mode=all&class=nature&has_audio=1&limit=5",valid,200);
 assert.equal(strict.mode,"all");
 const strictSql=queries.at(-1);
 assert.match(strictSql.args[0],/ AND /);
 assert.match(strictSql.args[0],/\("forest"\*\)/);
 assert.match(strictSql.args[0],/\("stream"\*\)/);
 // Strict Vietnamese terms must not require every English synonym simultaneously.
 await expectStatus("/search?q=chim%20r%E1%BB%ABng&mode=all",valid,200);
 const viStrict=queries.at(-1).args[0];
 assert.match(viStrict,/ AND /);
 assert.match(viStrict,/ OR /);
 assert.ok(!viStrict.includes('"birds"* AND "bird"*'));

 // Five production-oriented composition retrieval contracts (mocked D1, no private data).
 // These prove request routing and bound parameters, NOT actual matching inventory.
 const scenarios=[
  {name:"forest birds",url:"/search?q=chim%20r%E1%BB%ABng&mode=all&class=nature&has_audio=1&limit=5",terms:["bird","forest"],cls:"nature",audio:1},
  {name:"woodland creek",url:"/search?q=su%E1%BB%91i%20r%E1%BB%ABng&mode=all&class=nature&has_audio=1&limit=5",terms:["stream","forest"],cls:"nature",audio:1},
  {name:"night rain",url:"/search?q=m%C6%B0a%20%C4%91%C3%AAm&mode=all&class=nature&has_audio=1&limit=5",terms:["rain","night"],cls:"nature",audio:1},
  {name:"forest stream",url:"/search?q=forest%20stream&mode=all&class=nature&has_audio=1&limit=5",terms:["forest","stream"],cls:"nature",audio:1},
  {name:"ambient piano candidates",url:"/search?q=piano%20ambient&mode=any&class=music&has_audio=0&limit=5",terms:["piano","ambient"],cls:"music",audio:0}
 ];
 for(const scenario of scenarios){
  const response=await expectStatus(scenario.url,valid,200);
  assert.equal(response.count,1,scenario.name);
  assert.equal(response.results[0].source_page,fixtureRow.source_page,scenario.name);
  assert.equal(response.results[0].r2_key,fixtureRow.r2_key,scenario.name);
  assert.equal(response.results[0].qa_status,fixtureRow.qa_status,scenario.name);
  const bound=queries.at(-1);
  for(const term of scenario.terms)assert.ok(bound.args[0].includes(term),scenario.name+" missing "+term);
  assert.ok(bound.args.includes(scenario.cls),scenario.name+" class");
  assert.ok(bound.args.includes(scenario.audio),scenario.name+" audio filter");
  assert.equal(bound.args.at(-1),5,scenario.name+" top N");
  assert.ok(!bound.sql.includes(scenario.terms[0]),scenario.name+" SQL must bind MATCH");
 }
 assert.ok(strictSql.args.includes("nature"));
 assert.ok(strictSql.args.includes(1));
 assert.equal(strictSql.args.at(-1),5);
 const loose=await expectStatus("/search?q=forest%20stream&mode=any",valid,200);
 assert.equal(loose.mode,"any");
 assert.match(queries.at(-1).args[0],/ OR /);
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
   "Vietnamese expansion and filters","strict AND mode / audio SQL filter","default OR backward compatibility","R2 key/source/QA response","empty query","404","method guard","SQL parameterization","five composition query contracts (mocked D1)"],
  indexed_baseline_fixture:22239,production_deployment_tested:false}));
}finally {globalThis.fetch=originalFetch;}
