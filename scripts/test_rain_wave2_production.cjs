#!/usr/bin/env node
"use strict";
// New owner-approved sources must be exact audition bytes, old 25 untouched.
const fs=require("node:fs"),crypto=require("node:crypto"),assert=require("node:assert/strict");
const txt=p=>fs.readFileSync(p,"utf8"),json=p=>JSON.parse(txt(p));
const hash=p=>crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const catalog=json("catalog/library.json"),plans=json("catalog/planned-sounds.json").planned,
 families=json("catalog/family-registry.json").families,hls=json("audio/continuous/manifest.json");
const provenance=json("audio/rain-wave2-provenance.json"),review=json("signature/rain-wave2-review/manifest.json");
const previous=json("audio/rain-first-wave-provenance.json"),old22=json("audio/original-22-hls-lock.json");
const ids=["rain-on-tent-real","rain-car-roof-real","rolling-thunder-real"];
assert.equal(catalog.sounds.length,33);assert.equal(new Set(catalog.sounds.map(x=>x.id)).size,33);
assert.equal(families.length,13);assert.equal(hls.records.length,33);assert.equal(hls.applies_to.length,33);
assert.deepEqual(families.find(x=>x.id==="rain").existing_ids.slice(5,8),ids);
assert.equal(provenance.status,"OWNER_APPROVED_FOR_AUDIO");assert.equal(provenance.tracks.length,3);
assert.equal(plans.filter(x=>x.playable).length,11);
const playlistIds=new Set(hls.records.map(x=>x.id));assert.equal(playlistIds.size,33);
for(const old of old22.records){
 const rec=hls.records.find(x=>x.id===old.id);assert.ok(rec,"original source lost: "+old.id);
 assert.equal(rec.master_sha256,old.master_sha256);assert.equal(rec.playlist_sha256,old.playlist_sha256);
 assert.equal(hash(rec.playlist_file),old.playlist_sha256);
}
for(const old of previous.tracks){
 assert.equal(hash(old.production_mp3),old.master_sha256,"Wave1 source changed "+old.production_id);
 const r=hls.records.find(x=>x.id===old.production_id);assert.ok(r);
 assert.equal(r.master_sha256,old.master_sha256);assert.equal(hash(r.playlist_file),r.playlist_sha256);
}
for(let i=0;i<3;i++){
 const a=provenance.tracks[i],source=review.tracks[i],id=ids[i],catalogRow=catalog.sounds.find(s=>s.id===id),plan=plans.find(p=>p.plan_id===a.plan_id);
 assert.equal(a.production_id,id);assert.equal(a.master_sha256,source.master_sha256);
 assert.equal(hash(a.review_mp3),a.master_sha256,"review master altered "+id);
 assert.equal(hash(a.production_mp3),a.master_sha256,"production master differs from audition "+id);
 assert.equal(a.original_wav_downloaded,false);assert.equal(a.source_preview,"lossy_HQ_MP3_preview_not_WAV");
 assert.equal(a.owner_listening_status,"APPROVED_BY_OWNER_2026-11-09");
 assert.equal(catalogRow.status,"listening-approved");assert.equal(catalogRow.cat,"rain");
 assert.equal(plan.playable,true);assert.equal(plan.production_id,id);assert.equal(plan.seo_status,"noindex,follow");
 const rec=hls.records.find(r=>r.id===id);
 assert.ok(rec);assert.equal(rec.master_sha256,a.master_sha256);assert.equal(rec.source_license,"CC0-1.0");
 assert.equal(rec.source_page,a.source_page);assert.equal(hash(rec.playlist_file),rec.playlist_sha256);
 assert.ok(rec.native_stream_duration_hours>=167.9);
 assert.ok(rec.repeated_cycles>=1008);assert.ok(rec.segment_count_per_source_cycle>=9);
 assert.ok(fs.existsSync("audio/continuous/"+id+"/part_000.ts"));
 const m3=txt(rec.playlist_file);assert.ok(m3.includes("#EXT-X-DISCONTINUITY"));assert.ok(m3.includes("#EXT-X-ENDLIST"));
 const path="sounds/"+catalogRow.slug+"/index.html",page=txt(path);
 assert.ok(page.includes('name="robots" content="noindex,follow"'));
 assert.ok(page.includes('data-sound="'+id+'"'));
 assert.ok(page.includes('/audio/'+id+'.mp3')&&page.includes('/audio/continuous/'+id+'/continuous.m3u8'));
 assert.ok(page.includes('<audio controls loop preload="none"'));
 assert.ok(page.includes(a.source_page)&&page.includes('"@type":"AudioObject"'));
 assert.ok(!txt("sitemap.xml").includes("/sounds/"+catalogRow.slug+"/"));
}
assert.ok(txt("sounds/rain/index.html").includes("Rolling Thunder"));
assert.equal((txt("sounds/index.html").match(/data-wnc-existing-id="/g)||[]).length,33);
assert.ok(txt("index.html").includes("13 families · 33 catalog sources"));
const recipes=JSON.parse(txt("index.html").split("var recipes=")[1].split("];")[0]+"]");
assert.equal(recipes.length,45);
assert.equal((txt("sitemap.xml").match(/<loc>/g)||[]).length,18);
console.log("RAIN_WAVE2_PRODUCTION_QA_PASS 28 HLS, original 25 protected, 3 SHA-identical approved masters, 45 presets, noindex review separation");
