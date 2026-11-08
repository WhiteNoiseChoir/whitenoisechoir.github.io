#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
const file=p=>fs.readFileSync(p,"utf8");
const catalog=JSON.parse(file("catalog/library.json")),sounds=catalog.sounds,cats=catalog.categories,collections=catalog.collec;
assert.equal(sounds.length,25,"22 sound IDs retained");
assert.equal(cats.length,12,"12 category hubs");
assert.equal(collections.length,7,"7 collections retained");
assert.equal(new Set(sounds.map(s=>s.id)).size,25,"unique IDs");
assert.equal(new Set(sounds.map(s=>s.slug)).size,25,"unique slugs");
const editoriallyIndexable=new Set(["heavy-rain-real","waterfall-real","blue-noise","violet-noise","shower-synth"]);
const indexableSound=s=>s.status==="approved"||s.status==="arranged"||editoriallyIndexable.has(s.id);
const pages=["index.html","sounds/index.html","collections/index.html",...cats.map(c=>"sounds/"+c.slug+"/index.html"),...sounds.map(s=>"sounds/"+s.slug+"/index.html"),...collections.map(c=>"collections/"+c.slug+"/index.html"),"soundscapes/index.html","audio-tools/index.html"];
assert.equal(pages.length,49,"expected homepage + 45 library pages");
for(const path of pages){
 const html=file(path);
 assert.match(html,/<title>.+<\/title>/,"title: "+path);
 assert.match(html,/<h1[ >]/,"h1: "+path);
 assert.match(html,/<link rel="canonical"/,"canonical: "+path);
 if(path!=="index.html")assert.match(html,/\/assets\/persistent-router\.js/,"shared router: "+path);
}
for(const s of sounds){
 const page=file("sounds/"+s.slug+"/index.html");
 assert.ok(page.includes('data-sound="'+s.id+'"'),"correct player ID "+s.id);
 assert.ok(page.includes('/audio/'+s.id+'.mp3'),"correct audio path "+s.id);
 assert.ok(page.includes('/audio/continuous/'+s.id+'/continuous.m3u8'),"correct HLS path "+s.id);
 assert.match(page,/<audio controls loop preload="none"/,"progressive native audio fallback: "+s.id);
 assert.match(page,/application\/ld\+json/,"structured audio content: "+s.id);
 if(indexableSound(s))assert.ok(!page.includes('name="robots" content="noindex'),"approved sound indexable: "+s.id);
 else assert.ok(page.includes('name="robots" content="noindex,follow"'),"pending sound noindex: "+s.id);
}
const sitemap=file("sitemap.xml");const locs=[...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(x=>new URL(x[1]).pathname);
assert.equal(locs.length,18,"field, Noise Colors and Shower editorial releases passed their gates");
for(const pathname of locs){
 const local=pathname==="/"? "index.html" : pathname.replace(/^\//,"")+"index.html";
 assert.ok(fs.existsSync(local),"sitemap page exists "+local);
 assert.ok(!file(local).includes('name="robots" content="noindex,follow"'),"sitemap must exclude noindex "+local);
}
for(const name of ["nature","urban","gentle-sounds","fire","fan-noise"])assert.ok(file("sounds/"+name+"/index.html").includes('noindex,follow'),"do not index low-value single/empty hub "+name);
for(const slug of ["deep-sleep-sounds","focus-sounds","noise-masking","pet-calming-sounds"])assert.ok(file("collections/"+slug+"/index.html").includes('noindex,follow'),"hold weak collection "+slug);
new vm.Script(file("assets/persistent-router.js"),{filename:"assets/persistent-router.js"});
new vm.Script(file("assets/library-player.js"),{filename:"assets/library-player.js"});
const home=file("index.html");assert.match(home,/window\.WNCBridge\s*=/,"legacy audio engine exports a shared bridge");
assert.match(home,/function playTracks\(ids,name\)/,"original stream engine preserved");
assert.match(file("assets/persistent-router.js"),/history\.pushState/);
assert.match(file("assets/persistent-router.js"),/new DOMParser/);
assert.match(file("assets/persistent-router.js"),/replaceWith\(live\)/);
const manifest=JSON.parse(file("audio/continuous/manifest.json"));assert.equal(manifest.applies_to.length,25);
for(const s of sounds)assert.ok(manifest.applies_to.includes(s.id),"HLS source preserved: "+s.id);
assert.ok(file("sounds/green-noise/index.html").includes('name="robots" content="noindex,follow"'),"unreviewed Green Noise must not index");
assert.ok(!locs.includes("/sounds/green-noise/"),"unreviewed Green Noise absent from sitemap");
assert.ok(!file("collections/relaxing-sounds/index.html").includes('name="robots" content="noindex'),"finished relaxation page must be indexable");
assert.ok(locs.includes("/collections/relaxing-sounds/"),"finished relaxation page must be in sitemap");
console.log("PASS: 49 page routing shell, 25 playable sources, 12 hubs, 7 collections, provenance, AudioObject, noindex and sitemap checks");
