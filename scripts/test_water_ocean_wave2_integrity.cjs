#!/usr/bin/env node
"use strict";
const resolve=require("./resolve_review_media.cjs");
/* Independent final Wave 2 integrity/SEO/source-length audit.
   Does not rewrite or approve any user-review audio for production. */
const fs=require("node:fs"),assert=require("node:assert/strict"),crypto=require("node:crypto");
const read=p=>fs.readFileSync(p,"utf8"),j=p=>JSON.parse(read(p)),sha=p=>crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const dir="signature/water-ocean-wave2-review",review=j(dir+"/manifest.json"),catalog=j("catalog/library.json"),hls=j("audio/continuous/manifest.json"),plans=j("catalog/planned-sounds.json").planned;
assert.equal(review.status,"REVIEW_ONLY_PENDING_OWNER");assert.equal(review.tracks.length,2);
assert.equal(catalog.sounds.length,35);assert.equal(hls.records.length,35);assert.equal(hls.applies_to.length,35);
assert.equal(plans.filter(x=>!x.playable).length,57);
assert.equal(JSON.parse(read("index.html").split("var recipes=")[1].split("];")[0]+"]").length,45);
assert.equal((read("sitemap.xml").match(/<loc>/g)||[]).length,18);
const checks=[
{id:"bodetal-brook-review",plan:"NEW-10",creator:"Borgory",src:"https://freesound.org/people/Borgory/sounds/651194/",sha256:"e3e1bb330426a363842cb93890a40f33049c37a0c4d7351b802428914e4f5725",duration:637.542},
{id:"wakanui-surf-review",plan:"NEW-13",creator:"Desmond178",src:"https://freesound.org/people/Desmond178/sounds/721591/",sha256:"4969a0791d0a7bedfffc79ea5aca581ac3aeb9e23dff5c610f151ef48f7faed1",duration:2726.3}
];
for(let i=0;i<2;i++){
 const a=checks[i],row=review.tracks[i],p=plans.find(x=>x.plan_id===a.plan);
 assert.equal(row.id,a.id);assert.equal(row.plan_id,a.plan);assert.equal(row.creator,a.creator);
 assert.equal(row.source_page,a.src);assert.ok(Math.abs(row.source_duration_seconds-a.duration)<0.1);
 assert.equal(row.source_type,"CC0-1.0");assert.equal(row.technical_status,"PASS");
 assert.equal(row.review_status,"PENDING_OWNER_LISTENING");
 assert.equal(row.publication_status,"REVIEW_ONLY_NOT_IN_PRODUCTION");
 assert.equal(row.independent_source_seconds,605);assert.equal(row.repetitions_approx,0);
 assert.equal(row.master_sha256,a.sha256);assert.equal(sha(resolve(dir+"/"+a.id+".mp3")),a.sha256);
 assert.ok(row.master_bytes>13_000_000);
 assert.ok(row.peak_dbfs<=-9);
 assert.equal(p.playable,true);assert.equal(p.production_id,["bodetal-brook-real","crashing-ocean-real"][i]);assert.equal(p.owner_listening_approval,"APPROVED_BY_OWNER_2026-11-09");
}
const partial=review.tracks[1];
assert.equal(partial.downloaded_preview_bitrate_kbps,null,"Never infer preview bitrate from 45minute header of truncated download");
assert.equal(partial.preview_bitrate_evidence,"UNKNOWN_PARTIAL_RANGE_CANNOT_COMPUTE_FROM_HEADER_DURATION");
const bamboo=plans.find(x=>x.plan_id==="NEW-11");
assert.equal(bamboo.playable,false);assert.equal(bamboo.production_id,null);
const html=read(dir+"/index.html");
assert.ok(html.includes("NEW-11")&&html.includes("Bamboo Water Fountain")&&html.includes("CHƯA CÓ MASTER"));
assert.ok(html.includes('name="robots" content="noindex,nofollow"'));
assert.equal((html.match(/data-track="/g)||[]).length,2);
assert.ok(!read("sitemap.xml").includes(dir));assert.ok(!read("index.html").includes("bodetal-brook-review"));
assert.ok(!read("sounds/index.html").includes("wakanui-surf-review"));
const mainManifest=hls.records.map(x=>x.id);
assert.ok(!mainManifest.includes("bodetal-brook-review"));assert.ok(!mainManifest.includes("wakanui-surf-review"));
console.log("WATER_OCEAN_WAVE2_INDEPENDENT_INTEGRITY_PASS 2 owner-approved CC0 masters pinned, 33 old production sources preserved, 45 mixes, partial source bitrate unknown, bamboo unverified.");
