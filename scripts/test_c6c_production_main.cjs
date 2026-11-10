#!/usr/bin/env node
"use strict";
/* C6C release overlay: 35 immutable original catalog + 10 approved audio IDs.
 * No broad update of 532 editorial research records or SEO sitemap.
 */
const fs=require("node:fs"),vm=require("node:vm"),assert=require("node:assert/strict");
const load=p=>fs.readFileSync(p,"utf8"),json=p=>JSON.parse(load(p));
const existing=json("catalog/library.json"),approve=json("catalog/c6c-production-audio-approval.json"),manifest=json("catalog/c6c-ten-synthetic-review.json");
const home=load("index.html"),browse=load("sounds/index.html"),hub=load("sounds/c6c-synthetic/index.html"),sitemap=load("sitemap.xml");
assert.equal(existing.sounds.length,35);
assert.equal(approve.items.length,10);
assert.equal(approve.previous_production_sources+approve.additional_sources,45);
assert.equal(approve.existing_presets,45);
assert.equal(approve.seo_indexing_approved,false);
assert.match(approve.owner_approval_reference,/đã đạt hãy lên live/);
const before=home.indexOf("var rows=")+"var rows=".length;
const after=home.indexOf("];",before)+1;
const rows=JSON.parse(home.slice(before,after));
const recipeStart=home.indexOf("var recipes=")+"var recipes=".length;
const recipes=JSON.parse(home.slice(recipeStart,home.indexOf("];",recipeStart)+1));
assert.equal(rows.length,45,"Main player must have 35 old + 10 new audio IDs");
assert.equal(recipes.length,45,"All 45 existing mixes remain unchanged");
assert.equal(new Set(rows.map(r=>r[0])).size,45);
const approvedIds=new Set(approve.items.map(x=>x.production_id));
const oldIds=new Set(existing.sounds.map(s=>s.id));
assert.equal(approvedIds.size,10);
for(const id of oldIds)assert.ok(rows.some(x=>x[0]===id),"Lost legacy source "+id);
assert.ok([...approvedIds].every(id=>!oldIds.has(id)));
for(const x of approve.items){
 assert.ok(manifest.items.some(item=>item.id===x.record_id),"Unrecognized source "+x.record_id);
 assert.ok(rows.some(row=>row[0]===x.production_id&&row[1].includes("Synthetic")),"Missing new sound in homepage "+x.production_id);
 assert.ok(browse.includes('data-c6c-production-id="'+x.production_id+'"'));
 assert.ok(hub.includes('<option value="'+x.production_id+'">'),"C6C hub dropdown missing "+x.production_id);
 assert.ok(hub.includes('data-pick="'+x.production_id+'"'),"C6C playback card missing "+x.production_id);
 assert.ok(x.approved_hls_playlist==="audio/continuous/"+x.production_id+"/continuous.m3u8");
 assert.ok(x.approved_production_mp3==="audio/"+x.production_id+".mp3");
 assert.match(x.approved_review_master_sha256,/^[a-f0-9]{64}$/);
 assert.equal(x.owner_listening_status,"APPROVED_BY_OWNER_2026-11-10");
 assert.equal(x.seo_indexing,false);
}
assert.ok(home.includes("https://media.whitenoisechoir.com/review/c6c-20261110/"));
assert.ok(home.includes('var localMP3=c6cSourceMap[id]?'),"C6C should never use a nonexistent GitHub audio backup");
assert.ok(home.includes('var r2HLS=r2base+"audio/continuous/"+id+"/continuous.m3u8"'));
assert.ok(home.includes("Gentle & Baby")&&home.includes("Hums & Textures"));
assert.ok(browse.includes('/sounds/c6c-synthetic/'));
assert.ok(home.includes('/sounds/c6c-synthetic/'));
assert.ok(hub.includes('<audio id="audio" controls loop preload="metadata"'));
assert.ok(hub.includes("audio.canPlayType")&&hub.includes("contin")&&hub.includes("audio.loop=true"));
assert.ok(hub.includes('name="robots" content="noindex,follow"'),"Separate SEO signoff required");
assert.ok(!sitemap.includes("c6c-synthetic"));
assert.equal((sitemap.match(/<loc>/g)||[]).length,18);
assert.ok(!hub.includes('application/ld+json'));
const script=hub.split("<script>")[1]?.split("</script>")[0];
assert.ok(script);
new vm.Script(script,{filename:"c6c hub JS"});
const inline=home.match(/<script>\s*\(function\(\)/);
assert.ok(inline);
const contents=home.match(/<script>([\s\S]*?)<\/script>/g)||[];
for(const x of contents){const body=x.replace(/^<script>/,"").replace(/<\/script>$/,"");new vm.Script(body,{filename:"WhiteNoiseChoir home script"});}
console.log("C6C_PRODUCTION_INTEGRATION_STATIC_PASS: 45 homepage sound sources, 45 existing mixes, exact ten approved unique DSP, 35 legacy unchanged, 18 sitemap routes unchanged, noindex new hub and iPhone HLS supported");
