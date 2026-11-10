#!/usr/bin/env node
"use strict";
/* Editorial, provenance and crawlability checks for Relaxing Sounds collection. */
const fs=require("node:fs"),assert=require("node:assert/strict");
const read=p=>fs.readFileSync(p,"utf8"),json=p=>JSON.parse(read(p));
const path="collections/relaxing-sounds/index.html";
const html=read(path);
const catalog=json("catalog/library.json");
const manifest=json("audio/continuous/manifest.json");
const sources=json("audio/cc0-sources.json");
const byId=Object.fromEntries(catalog.sounds.map(s=>[s.id,s]));
const relax=catalog.collec.find(c=>c.slug==="relaxing-sounds");
assert.ok(relax,"Relaxing collection missing");
const expected=[
 "rain-on-window-real","ocean-waves-real","fireplace-real","heavy-rain-real",
 "waterfall-real","wind-synth","pink-noise","brown-noise"
];
assert.deepEqual(relax.ids,expected,"Exact editorially selected eight sound IDs");
assert.equal(new Set(relax.ids).size,8,"No duplicate audio selections");
assert.ok(expected.every(id=>byId[id]),"Every collection sound must exist");
assert.ok(expected.every(id=>manifest.applies_to.includes(id)),"All eight tracks have live continuous HLS");
const ld=[...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].map(x=>JSON.parse(x[1])).flat();
const page=ld.find(x=>x["@type"]==="CollectionPage");
const crumb=ld.find(x=>x["@type"]==="BreadcrumbList");
assert.ok(page&&crumb,"CollectionPage and BreadcrumbList structured data required");
assert.equal(page.url,"https://whitenoisechoir.com/collections/relaxing-sounds/");
assert.equal(page.mainEntity.numberOfItems,8);
assert.deepEqual(page.mainEntity.itemListElement.map(x=>x.url),expected.map(id=>"https://whitenoisechoir.com/sounds/"+byId[id].slug+"/"));
assert.equal(crumb.itemListElement.length,3);
assert.match(html,/<title>Relaxing Sounds:/);
assert.match(html,/<meta name="description" content="[^"]{100,165}"/);
assert.match(html,/<link rel="canonical" href="https:\/\/whitenoisechoir\.com\/collections\/relaxing-sounds\/"/);
assert.ok(!/<meta name="robots" content="noindex/.test(html),"Finished editorial page is indexable");
assert.ok(!/<audio[^>]+autoplay/.test(html),"Audio must not autoplay");
assert.match(html,/<audio controls loop preload="none" data-sound="rain-on-window-real"/);
assert.ok(html.includes('/audio/continuous/rain-on-window-real/continuous.m3u8'),"Preserve iPhone HLS URL");
assert.ok(html.includes('/assets/persistent-router.js'),"Preserve shared audio player engine");
assert.match(html,/data-wnc-status/,"Live status is visible and accessible");
const listen=[...html.matchAll(/data-wnc-compare="([^"]+)"/g)].map(x=>x[1]);
assert.deepEqual(listen,expected,"Exactly eight in-place comparison sound sources in expected order");
for(const id of listen){
 const sound=byId[id],url="/sounds/"+sound.slug+"/";
 assert.ok(html.includes('href="'+url+'" data-wnc-compare="'+id+'"'),id+" progressive listen fallback");
 assert.ok(html.includes('href="'+url+'">Sound details</a>'),id+" crawlable details link");
}
for(const id of ["rain-on-window-real","ocean-waves-real","fireplace-real","heavy-rain-real","waterfall-real"]){
 const row=sources.find(x=>x.id===id);
 assert.ok(row&&row.license==="CC0-1.0","Natural field audio must have CC0 original provenance: "+id);
}
assert.match(html,/Gentle Wind is a simulation, not an outdoor field recording/);
assert.match(html,/does not mean a never-repeating field recording/);
assert.match(html,/1:30/);
assert.match(html,/3:10/);
assert.match(html,/6:15/);
assert.match(html,/timer is not a safety device/);
assert.match(html,/not medical treatment/);
assert.match(html,/aria-live="polite"/);
assert.ok([...html.matchAll(/<details>/g)].length>=4,"Useful accessible FAQ");
const plain=html.replace(/<script[\s\S]*?<\/script>/g," ").replace(/<[^>]+>/g," ").replace(/\s+/g," ");
const count=plain.trim().split(" ").filter(Boolean).length;
assert.ok(count>=650&&count<=1800,"Should be a substantial but focused collection; words="+count);
const sitemap=read("sitemap.xml");
const locs=[...sitemap.matchAll(/<loc>(.*?)<\/loc>/g)].map(x=>x[1]);
const canonical="https://whitenoisechoir.com/collections/relaxing-sounds/";
assert.equal(locs.filter(x=>x===canonical).length,1,"Exactly one indexable collection URL");
const css=read("assets/library.css");
assert.match(css,/\.relax-card-grid\{/);
assert.match(css,/@media\(max-width:510px\)/,"Dedicated small phone layout");
assert.match(read("collections/index.html"),/8 playable sounds · listen instantly/,"Collection discovery updated");
console.log("RELAXING_PAGE_QA_PASS "+JSON.stringify({tracks:listen.length,words:count,indexable:true,faq:4,provenance:"5 CC0 sources plus 3 DSP tracks",progressiveAudio:true,sharedPlayer:true}));
