#!/usr/bin/env node
"use strict";
/* Wave3 owner signoff is not a claim of lossless source or physical iPhone QA. */
const fs=require("node:fs"),crypto=require("node:crypto"),assert=require("node:assert/strict"),cp=require("node:child_process");
const read=p=>fs.readFileSync(p,"utf8"),json=p=>JSON.parse(read(p)),sha=p=>crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const catalog=json("catalog/library.json"),families=json("catalog/family-registry.json").families,plans=json("catalog/planned-sounds.json").planned,hls=json("audio/continuous/manifest.json");
const review=json("signature/rain-wave3-review/manifest.json"),prov=json("audio/rain-wave3-provenance.json"),previous=json("audio/rain-wave3-existing-28-lock.json");
const ids=["rain-leaves-real","rain-lake-real"];
assert.equal(prov.status,"OWNER_APPROVED_FOR_AUDIO");
assert.equal(review.status,"REVIEW_ONLY_PENDING_OWNER","Keep untouched audition manifest as historical QA input");
assert.equal(prov.tracks.length,2);assert.equal(review.tracks.length,2);
assert.equal(catalog.sounds.length,30);assert.equal(new Set(catalog.sounds.map(x=>x.id)).size,30);
assert.equal(hls.records.length,30);assert.equal(hls.applies_to.length,30);
assert.equal(new Set(hls.applies_to).size,30);assert.equal(families.length,13);
assert.deepEqual(families.find(x=>x.id==="rain").existing_ids.slice(-2),ids);
assert.equal(plans.filter(x=>x.playable).length,8);assert.equal(plans.filter(x=>!x.playable).length,62);
assert.equal(previous.records.length,28);
for(const x of previous.records){
 const now=hls.records.find(y=>y.id===x.id);assert.ok(now,"original HLS lost: "+x.id);
 assert.equal(now.master_sha256,x.master_sha256);assert.equal(now.playlist_sha256,x.playlist_sha256);
 assert.equal(sha(now.master_file),x.master_sha256);assert.equal(sha(now.playlist_file),x.playlist_sha256);
}
for(let i=0;i<ids.length;i++){
 const id=ids[i],row=review.tracks[i],p=prov.tracks[i],snd=catalog.sounds.find(x=>x.id===id),plan=plans.find(x=>x.plan_id===p.plan_id);
 assert.equal(p.production_id,id);assert.equal(p.master_sha256,row.master_sha256);
 assert.equal(p.source_page,row.source_page);assert.equal(p.license,"CC0-1.0");
 assert.equal(p.owner_listening_status,"APPROVED_BY_OWNER_2026-11-09");
 assert.equal(p.original_lossless_downloaded,false);assert.equal(p.independent_source_used_seconds,row.independent_source_seconds);
 assert.equal(sha(p.review_mp3),row.master_sha256);assert.equal(sha(p.production_mp3),row.master_sha256);
 assert.equal(snd.status,"listening-approved");assert.equal(snd.cat,"rain");
 assert.equal(plan.playable,true);assert.equal(plan.production_id,id);assert.equal(plan.seo_status,"noindex,follow");
 const record=hls.records.find(x=>x.id===id);assert.ok(record);
 assert.equal(record.master_sha256,row.master_sha256);assert.equal(record.review_sha256,row.master_sha256);
 assert.equal(record.source_license,"CC0-1.0");assert.equal(record.source_page,row.source_page);
 assert.ok(record.repeated_cycles>=1008);assert.ok(record.native_stream_duration_hours>=167.9);
 assert.ok(record.segment_count_per_source_cycle>=9&&record.segment_count_per_source_cycle<=11);
 assert.equal(sha(record.playlist_file),record.playlist_sha256);
 assert.ok(fs.existsSync("audio/continuous/"+id+"/part_000.ts"));
 const m3=read(record.playlist_file);assert.ok(m3.includes("#EXT-X-DISCONTINUITY"));assert.ok(m3.includes("#EXT-X-ENDLIST"));
 const page=read("sounds/"+snd.slug+"/index.html");
 assert.ok(page.includes('name="robots" content="noindex,follow"'));
 assert.ok(page.includes('data-sound="'+id+'"'));
 assert.ok(page.includes("/audio/"+id+".mp3")&&page.includes("/audio/continuous/"+id+"/continuous.m3u8"));
 assert.ok(page.includes('<audio controls loop preload="none"'));
 assert.ok(page.includes(row.source_page));assert.ok(page.includes('"@type":"AudioObject"'));
 assert.ok(!read("sitemap.xml").includes("/sounds/"+snd.slug+"/"));
 const probe=JSON.parse(cp.execFileSync("ffprobe",["-v","error","-show_entries","format=duration:stream=codec_name,sample_rate,channels","-of","json",p.production_mp3],{encoding:"utf8"}));
 assert.ok(Math.abs(Number(probe.format.duration)-600)<=1);
 assert.ok(probe.streams.some(x=>x.codec_name==="mp3"&&Number(x.channels)===2&&Number(x.sample_rate)===44100));
}
assert.equal((read("sounds/index.html").match(/data-wnc-existing-id="/g)||[]).length,30);
assert.ok(read("index.html").includes("13 families · 30 catalog sources"));
const recipes=JSON.parse(read("index.html").split("var recipes=")[1].split("];")[0]+"]");
assert.equal(recipes.length,45);
assert.equal((read("sitemap.xml").match(/<loc>/g)||[]).length,18);
console.log("RAIN_WAVE3_PRODUCTION_QA_PASS: 30 sources and HLS, original 28 pinned, 2 exact owner-audition MP3, 45 presets, noindex pages, true CC0 licenses");
