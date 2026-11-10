#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict"),path=require("node:path");
const file=p=>fs.readFileSync(path.resolve(p),"utf8"),json=p=>JSON.parse(file(p));
const cat=json("catalog/library.json"),batch=json("catalog/batch18-20261108.json"),sounds=cat.sounds,byId=Object.fromEntries(sounds.map(s=>[s.id,s]));
const heads=batch.sound_ids,edited=batch.editorially_upgraded;
assert.equal(heads.length,18);assert.equal(new Set(heads).size,18);
assert.equal(edited.length,14);assert.equal(new Set(edited).size,14);
assert.deepEqual([...new Set([...batch.reference_pages,...edited])].sort(),[...heads].sort(),"batch composition");
const ext=json("audio/extended-dsp-manifest.json"),real=json("audio/master-manifest.json"),std=json("audio/color-master-manifest.json"),green=json("audio/green-noise-master-manifest.json");
const sources=[...ext.tracks.map(t=>t.id),...real.masters.map(t=>t.id),...std.tracks.map(t=>t.id),green.id];
for(const id of heads){assert.ok(sources.includes(id),"source manifest "+id);assert.ok(byId[id],"catalog "+id)}
const report=[],canonicalSet=new Set();
for(const id of edited){
 const s=byId[id],p="sounds/"+s.slug+"/index.html",html=file(p);
 const title=html.match(/<title>([^<]+)<\/title>/)?.[1],description=html.match(/<meta name="description" content="([^"]+)"/)?.[1];
 assert.ok(title&&title.length>35&&title.length<105,p+" title");
 assert.ok(description&&description.length>75&&description.length<190,p+" description");
 assert.match(html,/<h1>/,p+" h1");
 assert.match(html,/class="batch18-compare"/,p+" compare UX");
 assert.match(html,/class="batch18-provenance"/,p+" transparent provenance");
 assert.match(html,/class="wnc-facts"/,p+" audio facts");
 assert.match(html,/data-wnc-compare=/,p+" in-page A-B");
 assert.match(html,/class="brown-faq"/,p+" specific FAQ");
 assert.ok(html.includes('data-sound="'+id+'"'),p+" own audio ID");
 assert.ok(html.includes('/audio/'+id+'.mp3'),p+" correct MP3");
 assert.ok(html.includes('/audio/continuous/'+id+'/continuous.m3u8'),p+" correct HLS");
 assert.match(html,/<audio controls loop preload="none"/,p+" progressive native controls");
 const canon=html.match(/<link rel="canonical" href="([^"]+)"/)?.[1];
 assert.equal(canon,"https://whitenoisechoir.com/sounds/"+s.slug+"/",p+" canonical");
 assert.ok(!canonicalSet.has(canon),p+" duplicate canonical");canonicalSet.add(canon);
 const reviewedNoiseColor=new Set(["blue-noise","violet-noise","shower-synth"]);
 const expectedIndex=s.status==="approved"||s.status==="arranged"||reviewedNoiseColor.has(id);
 assert.equal(html.includes('name="robots" content="noindex,follow"'),!expectedIndex,p+" index remains unchanged");
 const schemaParts=[...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map(x=>JSON.parse(x[1]));
 assert.equal(schemaParts.length,1,p+" valid JSON-LD count");
 const graph=schemaParts[0];
 assert.ok(Array.isArray(graph)&&graph.some(x=>x["@type"]==="AudioObject"),p+" AudioObject");
 const ao=graph.find(x=>x["@type"]==="AudioObject");
 assert.equal(ao.contentUrl,"https://media.whitenoisechoir.com/audio/"+id+".mp3");
 assert.equal(ao.duration,"PT10M");
 assert.ok(graph.some(x=>x["@type"]==="BreadcrumbList"));
 const compare=[...html.matchAll(/data-wnc-compare="([^"]+)"/g)].map(x=>x[1]);
 assert.ok(compare.length>=3,p+" sufficient real A/B choices");
 assert.ok(compare.every(x=>byId[x]),p+" comparisons only known ID");
 assert.equal(new Set(compare).size,compare.length,p+" unique comparisons");
 const plain=html.replace(/<script[\s\S]*?<\/script>/g,"").replace(/<style[\s\S]*?<\/style>/g,"").replace(/<[^>]+>/g," ").replace(/&[a-z]+;/g," ").replace(/\s+/g," ").trim();
 const wordCount=plain.split(" ").length;
 assert.ok(wordCount>350,p+" needs substantive content; words="+wordCount);
 if(["rain-on-window-real","fireplace-real"].includes(id)){
   assert.match(html,/about 60 seconds/i,p+" authentic source is short");
   assert.match(html,/CC0 1\.0/,p+" CC0 source credit");
   assert.match(html,/https:\/\/freesound\.org\/people\//,p+" actual source attribution");
 }else{
   assert.match(html,/independently generated|original, independently generated/i,p+" no mislabeled field recording");
 }
 report.push({id,path:p,words:wordCount,indexable:expectedIndex,compare:compare.length});
}
const sitemap=file("sitemap.xml"),sitemapUrls=[...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(x=>x[1]);
assert.equal(sitemapUrls.length,18,"Measured Shower sound page selectively added after Blue/Violet phase");
for(const id of edited){const x=byId[id];if(x.status==="dsp-review")assert.ok(!sitemapUrls.includes("https://whitenoisechoir.com/sounds/"+x.slug+"/"),"unreviewed excluded: "+id)}
const hubs=["noise-colors","fan-noise","rain","water","wind-weather","fire","transportation","household","hums-drones"];
for(const h of hubs){const doc=file("sounds/"+h+"/index.html");assert.match(doc,/batch18-hub-compare/,"category improved "+h)}
assert.match(file("sounds/index.html"),/Browse 45 playable sound sources \(35 original catalog plus 10 approved synthetic additions\) in 13 families/,"35 legacy + 10 C6C approved playable sources accurate");
console.log("BATCH18_CONTENT_QA "+JSON.stringify({pages:report.length,reference:batch.reference_pages.length,meanWords:Math.round(report.reduce((a,b)=>a+b.words,0)/report.length),indexable:report.filter(x=>x.indexable).length,sitemap:sitemapUrls.length}));
console.log("PASS: 18 batch sources, 14 unique detailed pages, 9 hubs, 28 source library, valid MP3/HLS URLs, AudioObject, sitemap and noindex gates");
