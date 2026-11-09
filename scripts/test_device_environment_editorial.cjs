#!/usr/bin/env node
"use strict";
/* Device/environment editorial release: actual decoded-MP3 facts + conservative search policy. */
const fs=require("node:fs"),assert=require("node:assert/strict");
const read=p=>fs.readFileSync(p,"utf8"),json=p=>JSON.parse(read(p));
const root="https://whitenoisechoir.github.io";
const library=json("catalog/library.json");
const masters=json("audio/extended-dsp-manifest.json");
const hls=json("audio/continuous/manifest.json");
const review=json("audio/review-queue-20261108.json");
const byId=Object.fromEntries(library.sounds.map(s=>[s.id,s]));
const dsp=Object.fromEntries(masters.tracks.map(t=>[t.id,t]));
const listened=Object.fromEntries(review.dsp.map(t=>[t.id,t]));
const urls=[...read("sitemap.xml").matchAll(/<loc>([^<]+)<\/loc>/g)].map(m=>m[1]);
const cases=[
 ["desk-fan-synth","desk-fan",false,"112 Hz"],
 ["air-conditioner-synth","air-conditioner",false,"60 Hz"],
 ["cabin-hum-synth","airplane-cabin",false,"87 Hz"],
 ["low-rumble","low-rumble",false,"280 Hz"],
 ["wind-synth","gentle-wind",false,"1,400 Hz"],
 ["shower-synth","shower",true,"680 Hz"],
];
assert.equal(library.sounds.length,30);
assert.equal(hls.applies_to.length,30);
assert.equal(urls.length,18,"Sitemap must contain 18 editorially selected URLs");
const results=[];
for(const [id,slug,allowIndex,detail] of cases){
 const source=dsp[id],q=source?.qa,entry=byId[id],page="sounds/"+slug+"/index.html";
 assert.ok(source&&entry&&q&&listened[id],"Published source with pinned QA: "+id);
 assert.equal(entry.slug,slug);
 assert.equal(q.technical_status,"PASS");
 assert.equal(q.listening_approval,"APPROVED_BY_OWNER");
 assert.equal(listened[id].human_listening,"APPROVED_BY_OWNER");
 assert.equal(q.duration_seconds,600);
 assert.ok(hls.applies_to.includes(id));
 assert.ok(source.file_sha256===listened[id].source_sha256,id+" pinned audio unchanged");
 const html=read(page),url=root+"/sounds/"+slug+"/";
 assert.equal(html.includes('name="robots" content="noindex,follow"'),!allowIndex,id+" conservative indexing");
 assert.equal(urls.filter(u=>u===url).length,allowIndex?1:0,id+" consistent sitemap");
 assert.ok(html.includes('<link rel="canonical" href="'+url+'">'),id+" canonical");
 assert.ok(html.includes('data-sound="'+id+'"'),id+" correct live player ID");
 assert.ok(html.includes('/audio/'+id+'.mp3'),id+" MP3 preserved");
 assert.ok(html.includes('/audio/continuous/'+id+'/continuous.m3u8'),id+" HLS preserved");
 assert.ok(html.includes('<audio controls loop preload="none"'),id+" progressive audio");
 assert.ok(!/<audio\b[^>]*\bautoplay/i.test(html),id+" no autoplay");
 assert.ok(html.includes('class="noise-spectrum-panel"'),id+" measured plot");
 assert.ok(html.includes('class="noise-distinction"'),id+" source-specific content");
 assert.equal((html.match(/class="noise-band-row"/g)||[]).length,5,id+" 5 actual bands");
 assert.equal((html.match(/class="brown-faq"/g)||[]).length,5,id+" 5 FAQ");
 assert.ok(html.includes(detail),id+" source-specific technical parameter");
 for(const val of q.spectral_band_amplitude_dbfs)assert.ok(html.includes(val.toFixed(2)+" dBFS"),id+" actual band "+val);
 assert.ok(html.includes(q.spectral_slope_db_per_decade.toFixed(2)+" dB per decade"),id+" fitted slope");
 assert.ok(html.includes(q.integrated_loudness_lufs.toFixed(1)+" LUFS"),id+" measured LUFS");
 assert.ok(html.includes("not calibrated SPL or loudness at your ears"),id+" decibels disclaimer");
 assert.ok(html.includes("not a field recording")||html.includes("not a recording")||html.includes("not a microphone recording"),id+" synthetic disclosure");
 const comps=[...html.matchAll(/data-wnc-compare="([^"]+)"/g)].map(m=>m[1]);
 assert.equal(comps.length,4,id+" 4 A/B choices");
 assert.equal(new Set(comps).size,comps.length,id+" independent A/B source IDs");
 assert.ok(comps.includes(id));
 assert.ok(comps.every(k=>byId[k]),id+" only catalog IDs");
 assert.ok(!comps.includes("green-noise"),id+" never instant-play pending Green Noise");
 const scripts=[...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].flatMap(m=>JSON.parse(m[1]));
 const audio=scripts.find(x=>x["@type"]==="AudioObject");
 const web=scripts.find(x=>x["@type"]==="WebPage");
 const crumbs=scripts.find(x=>x["@type"]==="BreadcrumbList");
 assert.ok(audio&&web&&crumbs,id+" audio, webpage and breadcrumb JSON-LD");
 assert.equal(audio.contentUrl,root+"/audio/"+id+".mp3");
 assert.equal(audio.duration,"PT10M");
 assert.equal(web.url,url);
 assert.equal(web.mainEntity["@id"],url+"#audio");
 const title=html.match(/<title>([^<]+)<\/title>/)?.[1];
 const meta=html.match(/<meta name="description" content="([^"]+)"/)?.[1];
 assert.ok(title&&title.length>40&&title.length<105,id+" title");
 assert.ok(meta&&meta.length>100&&meta.length<190,id+" description");
 const words=html.replace(/<script[\s\S]*?<\/script>/g," ").replace(/<[^>]+>/g," ").replace(/&[a-z]+;/g," ").replace(/\s+/g," ").trim().split(/\s+/).length;
 assert.ok(words>=1000&&words<=1700,id+" source-specific useful editorial depth "+words);
 results.push({id,slug,indexable:allowIndex,words,faq:5,bands:5,comparisons:4});
}
const indexed=library.sounds.filter(s=>!read("sounds/"+s.slug+"/index.html").includes('name="robots" content="noindex,follow"'));
assert.equal(indexed.length,10,"Exactly 10 indexable source pages");
assert.ok(!indexed.some(s=>s.id==="green-noise"),"Pending Green remains blocked");
assert.ok(read("sounds/green-noise/index.html").includes('name="robots" content="noindex,follow"'));
assert.ok(!urls.includes(root+"/sounds/green-noise/"));
assert.ok(read("assets/persistent.css").includes(".noise-band-row{"),"Existing mobile chart CSS reused");
console.log("DEVICE_ENVIRONMENT_EDITORIAL_QA_PASS "+JSON.stringify({results,sitemapUrls:urls.length,indexable:10,noindex:12,otherCollectionsUnchanged:true}));
