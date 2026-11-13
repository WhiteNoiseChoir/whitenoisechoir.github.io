/**
 * WhiteNoiseChoir PRIVATE metadata search gateway (D1).
 * Requires Cloudflare Access on the route AND validates Access JWT here.
 * No public fallback. Not deployed by merely committing this file.
 */
const FIELDS = ["id","source_class","name","scientific_name","sound_family","habitat","region",
 "provider","source_page","license","duration","r2_key","has_r2_audio","qa_status"];
const VI = {
 "rừng":["forest","rainforest","jungle"],"mưa":["rain","rainfall"],"suối":["stream","creek","brook"],
 "sông":["river"],"biển":["ocean","sea","waves"],"gió":["wind","breeze"],"tuyết":["snow","winter"],
 "chim":["birds","bird"],"ếch":["frog","frogs"],"dế":["crickets","cricket"],"ve":["cicadas"],
 "cú":["owl","owls"],"sói":["wolf","wolves"],"đêm":["night","nocturnal"],"piano":["piano"],
 "thác":["waterfall"],"nước":["water"],"ngủ":["sleep","relaxation"],
};
function json(data,status=200) {
 return new Response(JSON.stringify(data),{status,headers:{
 "Content-Type":"application/json; charset=utf-8","Cache-Control":"private, no-store",
 "X-Content-Type-Options":"nosniff","Access-Control-Allow-Origin":"null"
 }});
}
function b64url(input) {
 const s=input.replace(/-/g,"+").replace(/_/g,"/");
 const binary=atob(s+"=".repeat((4-s.length%4)%4));
 return Uint8Array.from(binary,c=>c.charCodeAt(0));
}
async function verifyAccessJwt(request,env) {
 const token=request.headers.get("Cf-Access-Jwt-Assertion");
 if(!token || !env.ACCESS_TEAM_DOMAIN || !env.ACCESS_AUD)return false;
 const parts=token.split(".");
 if(parts.length!==3)return false;
 let header,payload;
 try {header=JSON.parse(new TextDecoder().decode(b64url(parts[0])));
      payload=JSON.parse(new TextDecoder().decode(b64url(parts[1])));}
 catch{return false;}
 const domain=env.ACCESS_TEAM_DOMAIN.replace(/^https?:\/\//,"").replace(/\/$/,"");
 const iss="https://"+domain;
 const now=Math.floor(Date.now()/1000);
 if(header.alg!=="RS256" || !header.kid || payload.iss!==iss ||
    !(Array.isArray(payload.aud)?payload.aud.includes(env.ACCESS_AUD):payload.aud===env.ACCESS_AUD) ||
    typeof payload.exp!=="number" || payload.exp<=now ||
    typeof payload.nbf==="number" && payload.nbf>now+30 ||
    typeof payload.iat==="number" && payload.iat>now+30)return false;
 let certs;
 try {
  const r=await fetch(iss+"/cdn-cgi/access/certs",{cf:{cacheTtl:300,cacheEverything:true}});
  if(!r.ok)return false;
  certs=await r.json();
 }catch{return false;}
 const key=(certs.keys||[]).find(k=>k.kid===header.kid);
 if(!key)return false;
 try {
  const publicKey=await crypto.subtle.importKey("jwk",key,{name:"RSASSA-PKCS1-v1_5",hash:"SHA-256"},false,["verify"]);
  return await crypto.subtle.verify("RSASSA-PKCS1-v1_5",publicKey,b64url(parts[2]),
   new TextEncoder().encode(parts[0]+"."+parts[1]));
 }catch{return false;}
}
function tokens(query) {
 const q=query.normalize("NFKC").toLowerCase();
 const words=(q.match(/[\p{L}\p{N}_-]+/gu)||[]).filter(x=>x.length>1);
 const extra=[];
 for(const [k,v] of Object.entries(VI))if(q.includes(k))extra.push(...v);
 return [...new Set([...words,...extra])].slice(0,24);
}
function fts(query) {
 // User data only becomes quoted FTS5 terms; never SQL string interpolation.
 const t=tokens(query).filter(x=>/^[\p{L}\p{N}_-]{2,50}$/u.test(x));
 return t.map(x=>'"'+x.replaceAll('"','')+'"*').join(" OR ");
}
export default {
 async fetch(request,env) {
  if(request.method!=="GET")return json({error:"method_not_allowed"},405);
  if(!await verifyAccessJwt(request,env))return json({error:"unauthorized"},401);
  if(!env.METADATA_DB)return json({error:"database_not_bound"},503);
  const u=new URL(request.url);
  if(u.pathname==="/health"){
   try {const r=await env.METADATA_DB.prepare("SELECT count(*) as n FROM assets").first();
    return json({status:"ok",indexed_total:r?.n??0,private:true});}
   catch{return json({error:"index_unavailable"},503);}
  }
  if(u.pathname!=="/search")return json({error:"not_found"},404);
  const q=(u.searchParams.get("q")||"").slice(0,240);
  const match=fts(q);
  if(!match)return json({error:"query_required"},400);
  const limit=Math.max(1,Math.min(30,Number.parseInt(u.searchParams.get("limit")||"10",10)||10));
  const cls=u.searchParams.get("class")||"";
  const audio=u.searchParams.get("has_audio")||"";
  const region=(u.searchParams.get("region")||"").slice(0,60);
  const licence=(u.searchParams.get("license")||"").slice(0,60);
  const minDuration=Number(u.searchParams.get("min_duration")||"0");
  const maxDuration=Number(u.searchParams.get("max_duration")||"0");
  let sql="SELECT a.id,a.source_class,a.name,a.scientific_name,a.sound_family,a.habitat,a.region,"+
    "a.provider,a.source_page,a.license,a.duration,a.r2_key,a.has_r2_audio,a.qa_status,"+
    "bm25(search,4,3,2,2,2,1,2,1,2) as rank "+
    "FROM search JOIN assets a ON a.rowid=search.rowid WHERE search MATCH ?";
  const params=[match];
  if(cls==="nature"||cls==="music"){sql+=" AND a.source_class=?";params.push(cls);}
  if(audio==="1"||audio==="0"){sql+=" AND a.has_r2_audio=?";params.push(Number(audio));}
  if(region){sql+=" AND a.region=?";params.push(region);}
  if(licence){sql+=" AND a.license=?";params.push(licence);}
  if(Number.isFinite(minDuration)&&minDuration>0){sql+=" AND a.duration>=?";params.push(minDuration);}
  if(Number.isFinite(maxDuration)&&maxDuration>0){sql+=" AND a.duration<=?";params.push(maxDuration);}
  sql+=" ORDER BY rank ASC LIMIT ?";params.push(limit);
  try {
   const r=await env.METADATA_DB.prepare(sql).bind(...params).all();
   return json({query:q,filters:{class:cls,has_audio:audio,region,license:licence},
     count:r.results.length,results:r.results.map(row=>Object.fromEntries(FIELDS.map(f=>[f,row[f]])))});
  }catch{return json({error:"query_failed"},503);}
 }
};