#!/usr/bin/env node
"use strict";
/* Field-source page SEO gate: four approved masters, two selective releases, transparency. */
const fs=require("node:fs"),assert=require("node:assert/strict");
const read=p=>fs.readFileSync(p,"utf8"),obj=p=>JSON.parse(read(p));
const site="https://whitenoisechoir.github.io";
const library=obj("catalog/library.json"),source=obj("audio/cc0-sources.json"),hls=obj("audio/continuous/manifest.json");
const sources=Object.fromEntries(source.map(x=>[x.id,x]));
const soundById=Object.fromEntries(library.sounds.map(x=>[x.id,x]));
const streams=Object.fromEntries(hls.records.map(x=>[x.id,x]));
const examples=[
 ["box-fan-real","box-fan","PT1M8S",false],
 ["heavy-rain-real","heavy-rain","PT3M10S",true],
 ["ocean-waves-real","ocean-waves","PT1M30S",false],
 ["waterfall-real","waterfall","PT6M15S",true],
];
const all=library.sounds;
assert.equal(all.length,22);
const sitemap=[...read("sitemap.xml").matchAll(/<loc>([^<]+)<\/loc>/g)].map(x=>x[1]);
assert.equal(sitemap.length,17,"17 URL selective sitemap after Noise Colors phase");
const report=[];
for(const [id,slug,iso,indexable] of examples){
 const path="sounds/"+slug+"/index.html",html=read(path),cc=sources[id],stream=streams[id],url=site+"/sounds/"+slug+"/";
 assert.ok(cc&&stream&&cc.production_status==="OWNER_APPROVED_FIELD_RECORDING",id+" source approved");
 assert.equal(cc.license,"CC0-1.0",id+" source license");
 assert.ok(cc.source.startsWith("https://freesound.org/people/"),id+" source URL");
 assert.equal(stream.master_sha256,cc.production_master_sha256,id+" master SHA aligned");
 assert.equal(stream.original_source_length_category,"APPROVED_CC0_FIELD_RECORDING");
 assert.ok(Math.abs(stream.source_cycle_seconds-cc.derived_duration_seconds)<0.75,id+" HLS duration matches MP3");
 assert.ok(html.includes('data-sound="'+id+'"'),id+" working player");
 assert.ok(html.includes('/audio/'+id+'.mp3?v=cc0-full-approved'),id+" cache busted MP3");
 assert.ok(html.includes('/audio/continuous/'+id+'/continuous.m3u8?v=continuous-hls-v4'),id+" cache busted HLS");
 assert.match(html,/<audio controls loop preload="none"/,id+" progressive native audio");
 assert.ok(!/<audio\b[^>]*\bautoplay/i.test(html),id+" does not autoplay");
 assert.ok(html.includes('href="'+url+'"')||html.includes('rel="canonical" href="'+url+'"'),id+" canonical");
 const title=html.match(/<title>([^<]+)<\/title>/)?.[1],description=html.match(/<meta name="description" content="([^"]+)"/)?.[1];
 assert.ok(title&&title.length>45&&title.length<=104,id+" SEO title");
 assert.ok(description&&description.length>100&&description.length<200,id+" specific description");
 assert.equal(html.includes('name="robots" content="noindex,follow"'),!indexable,id+" selective index policy");
 assert.equal(sitemap.filter(x=>x===url).length,indexable?1:0,id+" sitemap matches index");
 assert.ok(html.includes('data-wnc-compare-status aria-live="polite"'),id+" accessible A/B feedback");
 const compares=[...html.matchAll(/data-wnc-compare="([^"]+)"/g)].map(x=>x[1]);
 assert.equal(compares.length,4,id+" four comparison tracks");
 assert.equal(new Set(compares).size,4,id+" unique actual source files");
 assert.ok(compares.includes(id),id+" self comparison");
 for(const comp of compares){assert.ok(soundById[comp],"Unknown sound ID "+comp);
  const dest="/sounds/"+soundById[comp].slug+"/";assert.ok(html.includes('href="'+dest+'" data-wnc-compare="'+comp+'"'),id+" comparison must link to actual sound");}
 const graph=[...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].flatMap(x=>JSON.parse(x[1]));
 const audio=graph.find(x=>x["@type"]==="AudioObject"),crumb=graph.find(x=>x["@type"]==="BreadcrumbList"),webpage=graph.find(x=>x["@type"]==="WebPage");
 assert.ok(audio&&crumb&&webpage,id+" AudioObject/WebPage/BreadcrumbList schema");
 assert.equal(audio.contentUrl,site+"/audio/"+id+".mp3");
 assert.equal(audio.duration,iso);
 assert.equal(audio.license,"https://creativecommons.org/publicdomain/zero/1.0/");
 assert.equal(webpage.url,url);
 assert.equal(webpage.mainEntity["@id"],site+"/sounds/"+slug+"/#audio");
 assert.ok(html.includes(cc.source),id+" original source transparent attribution");
 assert.ok(html.includes(String(cc.derived_duration_seconds)),id+" actual original independent source length");
 assert.ok(!/awaiting a longer version review|pending listening approval|review pending/i.test(html),id+" no stale status");
 assert.ok((html.match(/<details class="field-faq">/g)||[]).length>=4,id+" contextual FAQs");
 assert.ok(html.includes('class="field-explain"'),id+" individual explanatory section");
 const plain=html.replace(/<script[\s\S]*?<\/script>/g," ").replace(/<style[\s\S]*?<\/style>/g," ").replace(/<[^>]*>/g," ").replace(/&[a-z]+;/g," ").replace(/\s+/g," ").trim();
 const wordCount=plain.split(/\s+/).length;
 assert.ok(wordCount>=670,id+" needs useful distinct content, words="+wordCount);
 report.push({id,url,indexable,words:wordCount,sourceSeconds:cc.derived_duration_seconds,comparisons:compares.length,faq:4});
}
assert.ok(!sitemap.includes(site+"/sounds/green-noise/"),"unreviewed Green Noise stays excluded");
const statuses=all.map(s=>({id:s.id,noindex:read("sounds/"+s.slug+"/index.html").includes('name="robots" content="noindex,follow"')}));
const indexable=statuses.filter(x=>!x.noindex);
assert.equal(indexable.length,9,"Nine individually approved indexable Sound Pages; others remain noindex");
assert.ok(!statuses.find(x=>x.id==="green-noise").noindex===false,"Green Noise remains noindex");
assert.ok(read("assets/persistent.css").includes(".field-choice-grid{"),"Shared field page comparison CSS");
console.log("FIELD_SOUND_EDITORIAL_QA_PASS "+JSON.stringify({pages:report,indexedSoundCount:indexable.length,noindexCount:statuses.length-indexable.length,sitemapUrls:sitemap.length}));
