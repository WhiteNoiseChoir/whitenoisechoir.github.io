#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict");
const ROOT=process.cwd();
const SITE="https://whitenoisechoir.com";
const R2="https://media.whitenoisechoir.com";
const OLD="https://whitenoisechoir.github.io";
const read=p=>fs.readFileSync(path.join(ROOT,p),"utf8");
assert.equal(read("CNAME").trim(),"whitenoisechoir.com","GitHub Pages CNAME missing");
const robots=read("robots.txt");
assert.ok(robots.includes("Sitemap: "+SITE+"/sitemap.xml"));
assert.ok(!robots.includes(OLD),"robots.txt still advertises github.io");
const dirs=["sounds","collections","audio-tools","soundscapes"];
let files=["index.html","sources.html"];
for(const root of dirs){
  const visit=(dir)=>{
    for(const d of fs.readdirSync(dir,{withFileTypes:true})){
      const full=path.join(dir,d.name);
      if(d.isDirectory())visit(full);
      else if(d.name==="index.html")files.push(full.replace(/\\/g,"/"));
    }
  };
  visit(root);
}
assert.equal(files.length,60,"The public site HTML count changed; review all pages before domain cutover");
let canonicalCount=0,ldCount=0,indexable=0;
const seen=new Set();
for(const p of files){
  const html=read(p),url=SITE+(p==="index.html"?"/":p.endsWith("/index.html")?"/"+p.slice(0,-"index.html".length):"/"+p);
  const canon=html.match(/<link\b[^>]*rel=["']canonical["'][^>]*href=["']([^"']+)["']/i);
  assert.ok(canon,"Missing canonical: "+p);
  assert.equal(canon[1],url,"Wrong canonical: "+p);
  assert.ok(!html.includes(OLD),"Old absolute .github.io address in public page "+p);
  assert.ok(!seen.has(url),"Duplicate canonical: "+url);
  seen.add(url);canonicalCount++;
  assert.ok(!html.includes(SITE+"/audio/"),"AudioObject should use R2, not the Pages media backup: "+p);
  const ld=[...html.matchAll(/<script\b[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi)];
  for(const m of ld){
    try{JSON.parse(m[1]);ldCount++}catch(e){throw Error("Invalid JSON-LD at "+p+": "+String(e.message))}
  }
  if(!/<meta\b[^>]*name=["']robots["'][^>]*content=["'][^"']*\bnoindex\b/i.test(html))indexable++;
}
const site=read("sitemap.xml");
assert.ok(!site.includes(OLD),"Sitemap still contains old domain");
const urls=[...site.matchAll(/<loc>([^<]+)<\/loc>/g)].map(x=>x[1]);
assert.equal(urls.length,18,"Preserve 18 approved sitemap URLs");
assert.equal(new Set(urls).size,urls.length,"Duplicate sitemap URL");
for(const url of urls){
  assert.ok(url.startsWith(SITE+"/"),"Wrong sitemap hostname: "+url);
  assert.ok(seen.has(url),"Sitemap references missing noncanonical page: "+url);
  const html=read(files.find(p=>SITE+(p==="index.html"?"/":p.endsWith("/index.html")?"/"+p.slice(0,-10):"/"+p)===url));
  assert.doesNotMatch(html,/<meta\b[^>]*name=["']robots["'][^>]*content=["'][^"']*\bnoindex\b/i,"Sitemap includes noindex "+url);
}
const home=read("index.html");
assert.match(home,/https:\/\/media\.whitenoisechoir\.com\//,"Production player lost R2 transport base");
assert.match(home,/\baudio_origin=github\b/,"One-click GitHub backup URL missing");
assert.equal(JSON.parse(read("catalog/library.json")).sounds.length,35,"35 playable sources required");
const mixSection=home.split("var recipes=")[1];
assert.ok(mixSection,"Mixer presets not found");
assert.equal(JSON.parse(mixSection.split("];")[0]+"]").length,45,"45 mixes must be retained");
const cors=JSON.parse(read("config/r2-media-cors.json"));
assert.ok(cors[0].AllowedOrigins.includes(SITE));
assert.ok(cors[0].AllowedOrigins.includes("https://www.whitenoisechoir.com"));
console.log("CUSTOM_DOMAIN_STAGING_QA_PASS "+JSON.stringify({
  canonicalPages:canonicalCount,validJSONLD:ldCount,indexablePublicPages:indexable,
  sitemapURLs:urls.length,playerSources:35,presets:45,origin:SITE,
  schemaAudioOrigin:R2,backupGH:OLD,
  productionUntouchedUntilMerge:true
}));
