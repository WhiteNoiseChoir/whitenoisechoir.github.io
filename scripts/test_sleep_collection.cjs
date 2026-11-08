#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict");
const read=p=>fs.readFileSync(p,"utf8"),json=p=>JSON.parse(read(p));
const url="https://whitenoisechoir.github.io/collections/white-noise-for-sleep/";
const html=read("collections/white-noise-for-sleep/index.html");
const catalog=json("catalog/library.json"), hls=json("audio/continuous/manifest.json");
const sounds=Object.fromEntries(catalog.sounds.map(x=>[x.id,x]));
const page=catalog.collec.find(x=>x.slug==="white-noise-for-sleep");
const ids=["white-noise","pink-noise","brown-noise","soft-white-noise","warm-pink-noise","deep-brown-noise"];
assert.ok(page,"Adult sleep collection missing");
assert.deepEqual(page.ids,ids,"Six exact approved sleep noise files");
assert.equal(new Set(page.ids).size,6,"No duplicated sources");
for(const id of ids){
 assert.ok(sounds[id],"Sound ID must exist: "+id);
 assert.ok(["approved","listening-approved"].includes(sounds[id].status),"Must only curate reviewed audio: "+id);
 assert.ok(hls.applies_to.includes(id),"Native HLS exists: "+id);
}
assert.ok(!ids.includes("green-noise"),"Green Noise is not part of approved six-sound collection");
const schema=[...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].flatMap(x=>JSON.parse(x[1]));
const coll=schema.find(x=>x["@type"]==="CollectionPage");
const crumb=schema.find(x=>x["@type"]==="BreadcrumbList");
assert.ok(coll&&crumb,"CollectionPage and BreadcrumbList schema present");
assert.equal(coll.url,url);
assert.equal(coll.mainEntity.numberOfItems,6);
assert.deepEqual(coll.mainEntity.itemListElement.map(x=>x.url),ids.map(id=>"https://whitenoisechoir.github.io/sounds/"+sounds[id].slug+"/"));
assert.equal(crumb.itemListElement.length,3);
assert.match(html,/<title>White Noise for Sleep — Listen to 6 Continuous Sounds/);
assert.match(html,/<meta name="description" content="[^"]{90,180}"/);
assert.ok(html.includes('<link rel="canonical" href="'+url+'">'),"Canonical unchanged");
assert.ok(!html.includes('name="robots" content="noindex'),"Existing indexable page stays indexable");
assert.ok(!/<audio[^>]+autoplay/i.test(html),"No autoplay");
assert.ok(html.includes('<audio controls loop preload="none" data-sound="white-noise"'),"Native fallback audio");
assert.ok(html.includes('data-hls="/audio/continuous/white-noise/continuous.m3u8'),"iPhone-native HLS URL");
assert.ok(html.includes('/assets/persistent-router.js'),"Reusable audio player");
assert.ok(html.includes('data-wnc-status aria-live="polite"'),"Accessible live status");
const clicks=[...html.matchAll(/data-wnc-compare="([^"]+)"/g)].map(x=>x[1]);
assert.deepEqual(clicks,ids,"Six instant-change buttons; no duplicates");
for(const id of clicks){
 const sound=sounds[id];
 assert.ok(html.includes('href="/sounds/'+sound.slug+'/" class="sleep-instant" data-wnc-compare="'+id+'"'),"Progressive audio selection: "+id);
 assert.ok(html.includes('class="sleep-details" href="/sounds/'+sound.slug+'/">Sound details</a>'),"Crawlable technical details: "+id);
}
for(const phrase of ["Begin quietly","Audio does not start automatically","treatment of sleep problems","timer is a convenience","not a guaranteed safety shutoff","ten minutes","sleep timer","44.1 kHz","does not start automatically"]){
 assert.ok(html.toLowerCase().includes(phrase.toLowerCase()),"Missing safety/product disclosure: "+phrase);
}
assert.equal([...html.matchAll(/<details>/g)].length,4,"Four focused FAQ disclosures");
const stripped=html.replace(/<script[\s\S]*?<\/script>/g," ").replace(/<[^>]*>/g," ").replace(/&[a-z]+;/g," ").replace(/\s+/g," ").trim();
const words=stripped.split(" ").filter(Boolean).length;
assert.ok(words>=650&&words<1800,"Substantive but intent-specific text: "+words);
const sitemap=read("sitemap.xml"), loc=[...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(x=>x[1]);
assert.equal(loc.filter(x=>x===url).length,1,"Preserve existing sitemap canonical");
assert.equal(loc.length,13,"No new indexable URL or broad index release");
assert.ok(read("collections/index.html").includes("6 playable sounds · listen instantly"),"Collection card updated");
const css=read("assets/library.css");
assert.match(css,/\.sleep-sound-grid\{/);
assert.match(css,/@media\(max-width:510px\)/,"Responsive 510px layout");
console.log("SLEEP_COLLECTION_QA_PASS "+JSON.stringify({sounds:ids.length,words,faq:4,indexable:true,sourceIds:ids,player:"HLS with native MP3 fallback",sitemapUrls:loc.length}));
