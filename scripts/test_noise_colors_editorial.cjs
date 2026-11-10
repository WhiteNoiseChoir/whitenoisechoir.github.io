#!/usr/bin/env node
"use strict";
/* 6 Noise Colors editorial gates: audio provenance, actual QA spectra, safe SEO release. */
const fs=require("node:fs"),assert=require("node:assert/strict");
const read=p=>fs.readFileSync(p,"utf8"),json=p=>JSON.parse(read(p));
const root="https://whitenoisechoir.com";
const catalog=json("catalog/library.json"),extended=json("audio/extended-dsp-manifest.json"),hls=json("audio/continuous/manifest.json");
const byId=Object.fromEntries(catalog.sounds.map(x=>[x.id,x]));
const byExtended=Object.fromEntries(extended.tracks.map(x=>[x.id,x]));
const sitemap=[...read("sitemap.xml").matchAll(/<loc>([^<]+)<\/loc>/g)].map(x=>x[1]);
const pilot=[
 ["blue-noise",true],["violet-noise",true],["soft-white-noise",false],
 ["deep-brown-noise",false],["warm-pink-noise",false],["mid-noise",false]
];
assert.equal(sitemap.length,18,"Selective 18 URL sitemap including Shower");
assert.equal(catalog.sounds.length,35,"Retain 22 sources");
assert.equal(hls.applies_to.length,35,"Retain all HLS sources");
const records=[];
for(const [id,allowIndex] of pilot){
 const s=byId[id],master=byExtended[id];
 assert.ok(s&&master,"Known 10 minute source: "+id);
 assert.equal(master.qa.technical_status,"PASS",id+" technical QA");
 assert.equal(master.qa.listening_approval,"APPROVED_BY_OWNER",id+" listening approval");
 assert.equal(master.qa.duration_seconds,600,id+" 10 minute independent DSP");
 assert.ok(hls.applies_to.includes(id),id+" existing HLS preserved");
 const slug=s.slug,path="sounds/"+slug+"/index.html",html=read(path),url=root+"/sounds/"+slug+"/";
 assert.equal(html.includes('name="robots" content="noindex,follow"'),!allowIndex,id+" index policy");
 assert.equal(sitemap.filter(x=>x===url).length,allowIndex?1:0,id+" sitemap");
 assert.match(html,/<title>[^<]+<\/title>/,"title");
 assert.match(html,/<meta name="description" content="[^"]+"/,"description");
 assert.ok(html.includes('<link rel="canonical" href="'+url+'">'),id+" canonical unchanged");
 assert.ok(html.includes('data-sound="'+id+'"'),id+" player audio ID");
 assert.ok(html.includes('/audio/'+id+'.mp3'),id+" master path");
 assert.ok(html.includes('/audio/continuous/'+id+'/continuous.m3u8'),id+" HLS path");
 assert.match(html,/<audio controls loop preload="none"/,id+" no-JS MP3 fallback");
 assert.ok(!/<audio\b[^>]*\bautoplay/i.test(html),id+" no autoplay");
 assert.ok(html.includes('class="noise-spectrum-panel"'),id+" spectrum section");
 assert.ok(html.includes('class="noise-distinction"'),id+" unique explanation");
 assert.equal((html.match(/class="noise-band-row"/g)||[]).length,5,id+" five reported sampled bands");
 for(const value of master.qa.spectral_band_amplitude_dbfs){
  assert.ok(html.includes(value.toFixed(2)+" dBFS"),id+" actual measured band value "+value);
 }
 const slope=master.qa.spectral_slope_db_per_decade.toFixed(2)+" dB per decade";
 assert.ok(html.includes(slope),id+" actual decoded spectral slope");
 assert.ok(html.includes(master.qa.integrated_loudness_lufs.toFixed(1)+" LUFS"),id+" actual LUFS");
 assert.ok(html.includes('not calibrated SPL')||html.includes('not calibrated SPL or loudness at your ears'),id+" safety disclosure");
 assert.equal((html.match(/class="brown-faq"/g)||[]).length,5,id+" five FAQs");
 const cmp=[...html.matchAll(/data-wnc-compare="([^"]+)"/g)].map(x=>x[1]);
 assert.ok(cmp.length>=3,id+" A/B alternatives");
 assert.equal(new Set(cmp).size,cmp.length,id+" no duplicate comparisons");
 assert.ok(cmp.includes(id),id+" self A/B compare");
 assert.ok(cmp.every(x=>byId[x]),id+" every comparable track exists");
 assert.ok(!cmp.includes("green-noise"),id+" do not recommend unapproved Green Noise as instant A/B option");
 const graph=[...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].flatMap(x=>JSON.parse(x[1]));
 const ao=graph.find(x=>x["@type"]==="AudioObject"),web=graph.find(x=>x["@type"]==="WebPage"),crumb=graph.find(x=>x["@type"]==="BreadcrumbList");
 assert.ok(ao&&web&&crumb,id+" AudioObject, WebPage, BreadcrumbList");
 assert.equal(ao.contentUrl,root+"/audio/"+id+".mp3");
 assert.equal(ao.duration,"PT10M");
 assert.equal(web.url,url);
 assert.equal(web.mainEntity["@id"],root+"/sounds/"+slug+"/#audio");
 assert.ok(html.includes("https://technav.ieee.org/topic/colored-noise/"),id+" acoustics reference");
 assert.ok(html.includes("https://www.audiology.org/audiologists-know-about-noise-in-every-color/"),id+" safe volume reference");
 const words=html.replace(/<script[\s\S]*?<\/script>/g," ").replace(/<[^>]+>/g," ").replace(/&[a-z]+;/g," ").replace(/\s+/g," ").trim().split(/\s+/).length;
 assert.ok(words>=880&&words<1600,id+" content quality size "+words);
 records.push({id,slug,indexable:allowIndex,words,faq:5,bandCount:5,slope:master.qa.spectral_slope_db_per_decade});
}
for(const id of ["green-noise","soft-white-noise","deep-brown-noise","warm-pink-noise","mid-noise"]){
 const s=byId[id],url=root+"/sounds/"+s.slug+"/";
 assert.ok(read("sounds/"+s.slug+"/index.html").includes('name="robots" content="noindex,follow"'),id+" noindex remains");
 assert.ok(!sitemap.includes(url),id+" absent from sitemap");
}
const existing=[ "white-noise","pink-noise","brown-noise","rain-on-window-real","fireplace-real","heavy-rain-real","waterfall-real" ];
for(const id of existing){const s=byId[id];assert.ok(!read("sounds/"+s.slug+"/index.html").includes('name="robots" content="noindex'),id+" existing indexable preserved");}
const approved=byId["blue-noise"],purple=byId["violet-noise"];
assert.ok(sitemap.includes(root+"/sounds/"+approved.slug+"/"));
assert.ok(sitemap.includes(root+"/sounds/"+purple.slug+"/"));
assert.equal(catalog.sounds.filter(s=>!read("sounds/"+s.slug+"/index.html").includes('name="robots" content="noindex')).length,10,"Exactly ten indexable Sound Pages");
const hub=read("sounds/noise-colors/index.html");
assert.equal((hub.match(/class="noise-colors-quick-table"/g)||[]).length,1,"Hub spectrum summary table");
for(const [id] of pilot)assert.ok(hub.includes('href="/sounds/'+byId[id].slug+'/"'),"Hub links "+id);
assert.ok(hub.includes("Green Noise")&&hub.includes("awaiting listening approval"),"Green remains held");
assert.ok(!/<a class="tile" href="\/sounds\/blue-noise\/">[\s\S]*?listening review pending[\s\S]*?<\/a>/.test(hub),"No obsolete pending state for Blue");
const css=read("assets/persistent.css");
assert.ok(css.includes(".noise-band-row{"),"Spectrum CSS");
assert.ok(css.includes("@media(max-width:350px)"),"Small mobile CSS");
console.log("NOISE_COLORS_EDITORIAL_QA_PASS "+JSON.stringify({records,sitemap:sitemap.length,indexableSoundPages:10,allSounds:35,unapprovedGreenNoindex:true}));
