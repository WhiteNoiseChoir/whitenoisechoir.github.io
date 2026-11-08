#!/usr/bin/env node
"use strict";
/* Baby-sleep page: pediatric guidance, index policy, existing sound IDs, progressive audio. */
const fs=require("node:fs"),assert=require("node:assert/strict");
const read=p=>fs.readFileSync(p,"utf8"),json=p=>JSON.parse(read(p));
const url="https://whitenoisechoir.github.io/collections/baby-sleep-sounds/";
const html=read("collections/baby-sleep-sounds/index.html");
const library=json("catalog/library.json"),hls=json("audio/continuous/manifest.json");
const byId=Object.fromEntries(library.sounds.map(s=>[s.id,s]));
const collection=library.collec.find(x=>x.slug==="baby-sleep-sounds");
const ids=["soft-white-noise","pink-noise","rain-on-window-real"];
assert.ok(collection,"Baby Sleep Sounds collection missing");
assert.deepEqual(collection.ids,ids,"Three exact source audio files");
assert.equal(new Set(ids).size,3,"Unique baby audio IDs");
for(const id of ids){
 assert.ok(byId[id]&&hls.applies_to.includes(id),"Playable MP3/HLS source required: "+id);
 assert.ok(["approved","listening-approved","arranged"].includes(byId[id].status),"Use reviewed audio only: "+id);
}
const graph=[...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].flatMap(x=>JSON.parse(x[1]));
const page=graph.find(x=>x["@type"]==="CollectionPage");
const crumbs=graph.find(x=>x["@type"]==="BreadcrumbList");
assert.ok(page&&crumbs,"CollectionPage and BreadcrumbList JSON-LD");
assert.equal(page.url,url);
assert.equal(page.mainEntity.numberOfItems,3);
assert.deepEqual(page.mainEntity.itemListElement.map(x=>x.url),ids.map(id=>"https://whitenoisechoir.github.io/sounds/"+byId[id].slug+"/"));
assert.equal(crumbs.itemListElement.length,3);
assert.match(html,/<title>Baby Sleep Sounds — Gentle Background Audio &amp; Safety \| WhiteNoiseChoir/);
const descr=html.match(/<meta name="description" content="([^"]+)"/)?.[1]||"";
assert.ok(descr.length>=100&&descr.length<=170,"Original description length");
assert.ok(html.includes('<link rel="canonical" href="'+url+'">'),"Maintain canonical");
assert.ok(!html.includes('name="robots" content="noindex'),"Already-indexable baby collection remains indexable");
assert.ok(!/<audio[^>]+autoplay/i.test(html),"No autoplay infant background sound");
assert.match(html,/<audio controls loop preload="none" data-sound="soft-white-noise"/,"Progressive native MP3 fallback");
assert.ok(html.includes('/audio/continuous/soft-white-noise/continuous.m3u8'),"HLS preserved for compatible iPhone");
assert.ok(html.includes('/assets/persistent-router.js'),"Shared player preserved");
assert.ok(html.includes('data-wnc-status aria-live="polite"'),"Screen reader live status");
const clicks=[...html.matchAll(/data-wnc-compare="([^"]+)"/g)].map(x=>x[1]);
assert.deepEqual(clicks,ids,"Three independent in-page compare controls");
for(const id of ids){
 const path="/sounds/"+byId[id].slug+"/";
 assert.ok(html.includes('href="'+path+'" class="baby-compare" data-wnc-compare="'+id+'"'),"Progressive compare link: "+id);
 assert.ok(html.includes('href="'+path+'" class="baby-sound-details"'),"Crawlable detail link: "+id);
}
const mustContain=[
 "Keep the device well away from the crib",
 "lowest practical volume",
 "Limit listening time",
 "not a guaranteed safety cutoff",
 "Continuous playback is a technical capability",
 "not a recommendation to leave sound running all night",
 "Never place a phone, speaker or cords in the baby's sleep space",
 "audio files, not clinically calibrated sound machines",
 "firm, flat sleep surface",
 "No track on this site is guaranteed",
 "screen volume percentages",
 "as far from the infant as possible"
];
for(const phrase of mustContain)assert.ok(html.toLowerCase().includes(phrase.toLowerCase()),"Missing evidence-sensitive warning: "+phrase);
assert.ok(html.includes("https://www.aap.org/en/patient-care/environmental-health/promoting-healthy-environments-for-children/noise/"),"AAP hearing guidance cited");
assert.ok(html.includes("https://www.aap.org/en/patient-care/safe-sleep/"),"AAP safe sleep source cited");
assert.equal([...html.matchAll(/<details>/g)].length,5,"Five caregiver FAQs");
assert.ok(!/safe (?:at|below) \d+ dB/i.test(html),"No invented calibrated audio safe threshold");
assert.ok(!/guaranteed safe volume|guaranteed to sleep|prevent(?:s)? sids/i.test(html),"No false clinical promises");
const plain=html.replace(/<script[\s\S]*?<\/script>/g," ").replace(/<[^>]+>/g," ").replace(/&[a-z]+;/g," ").replace(/\s+/g," ").trim();
const words=plain.split(" ").filter(Boolean).length;
assert.ok(words>=720&&words<1800,"Informative but focused parent guide words="+words);
const loc=[...read("sitemap.xml").matchAll(/<loc>([^<]+)<\/loc>/g)].map(x=>x[1]);
assert.equal(loc.filter(x=>x===url).length,1,"Existing canonical in sitemap exactly once");
assert.equal(loc.length,17,"Noise Colors editorial indexing added; baby collection remains unchanged");
assert.match(read("collections/index.html"),/3 playable sounds · safety first/);
const css=read("assets/library.css");
assert.match(css,/\.baby-sound-grid\{/);
assert.match(css,/@media\(max-width:520px\)/);
console.log("BABY_COLLECTION_QA_PASS "+JSON.stringify({soundIds:ids,words,sources:"AAP noise and safe sleep",faq:5,indexable:true,autoplay:false,hls:true,sitemap:loc.length}));
