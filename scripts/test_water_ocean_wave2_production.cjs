#!/usr/bin/env node
"use strict";
const resolve=require("./resolve_review_media.cjs");
/* Water/Ocean Wave2: validate two exactly promoted MP3s, original 33 SHA pins,
  intentional noindex pages and 45 untouched presets. No physical-device iPhone claims. */
const assert=require("node:assert/strict"),fs=require("node:fs"),crypto=require("node:crypto"),cp=require("node:child_process");
const read=p=>fs.readFileSync(p,"utf8"),json=p=>JSON.parse(read(p)),sha=p=>crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const gitblob=p=>{const v=fs.readFileSync(p);return crypto.createHash("sha1").update(Buffer.from("blob "+v.length+"\0")).update(v).digest("hex")};
const catalog=json("catalog/library.json"),fams=json("catalog/family-registry.json").families,plans=json("catalog/planned-sounds.json").planned,hls=json("audio/continuous/manifest.json");
const review=json("signature/water-ocean-wave2-review/manifest.json"),prov=json("audio/water-ocean-wave2-provenance.json"),lock=json("audio/water-ocean-wave2-existing-33-lock.json");
const names=[["NEW-10","bodetal-brook-review","bodetal-brook-real","bodetal-brook-birds","Bodetal Brook & Birds"],["NEW-13","wakanui-surf-review","crashing-ocean-real","crashing-ocean-waves","Crashing Ocean Waves"]];
assert.equal(prov.status,"OWNER_APPROVED_FOR_AUDIO");assert.equal(prov.tracks.length,2);assert.equal(review.tracks.length,2);assert.equal(review.status,"REVIEW_ONLY_PENDING_OWNER");
assert.equal(catalog.sounds.length,35);assert.equal(new Set(catalog.sounds.map(x=>x.id)).size,35);assert.equal(hls.records.length,35);assert.equal(hls.applies_to.length,35);assert.equal(new Set(hls.applies_to).size,35);
assert.equal(fams.length,13);assert.equal(plans.length,70);assert.equal(plans.filter(x=>x.playable).length,13);assert.equal(plans.filter(x=>!x.playable).length,57);
assert.equal(lock.records.length,33);const oldIds=new Set(lock.records.map(x=>x.id));assert.equal(oldIds.size,33);
for(let fixed of lock.records){const rec=hls.records.find(x=>x.id===fixed.id);assert.ok(rec,"Original HLS missing "+fixed.id);assert.equal(rec.master_sha256,fixed.master_sha256);assert.equal(rec.playlist_sha256,fixed.playlist_sha256);assert.equal(sha(rec.master_file),fixed.master_sha256);assert.equal(sha(rec.playlist_file),fixed.playlist_sha256)}
const reviewSrc=read("signature/water-ocean-wave2-review/index.html");assert.ok(reviewSrc.includes('name="robots" content="noindex,nofollow"'));
const blocked=plans.find(x=>x.plan_id==="NEW-11");assert.equal(blocked.playable,false);assert.equal(blocked.production_id,null);
assert.ok(prov.identity_policy.includes("distant stream and birds"));assert.ok(!prov.identity_policy.toLowerCase().includes("validated true bubbling"));
const hub=read("sounds/water/index.html");assert.ok(hub.includes('name="robots" content="noindex,follow"'));
for(let i=0;i<names.length;i++){
 const [planId,reviewId,id,slug,title]=names[i],track=review.tracks[i],p=plans.find(x=>x.plan_id===planId),metadata=prov.tracks[i],sound=catalog.sounds.find(x=>x.id===id);
 assert.equal(track.id,reviewId);assert.equal(track.plan_id,planId);assert.equal(track.technical_status,"PASS");
 assert.equal(track.source_type,"CC0-1.0");assert.equal(track.independent_source_seconds,605);assert.equal(track.repetitions_approx,0);
 assert.equal(track.duration_seconds,600);
 assert.equal(metadata.production_id,id);assert.equal(metadata.plan_id,planId);assert.equal(metadata.master_sha256,track.master_sha256);
 assert.equal(metadata.owner_listening_status,"APPROVED_BY_OWNER_2026-11-09");assert.equal(metadata.license,"CC0-1.0");
 assert.equal(metadata.source_page,track.source_page);assert.equal(metadata.lossless_original_downloaded,false);
 assert.equal(sha(resolve(metadata.review_mp3)),track.master_sha256);assert.equal(sha(metadata.production_mp3),track.master_sha256);
 assert.ok(!oldIds.has(id));assert.equal(sound.title,title);assert.equal(sound.slug,slug);assert.equal(sound.status,"listening-approved");
 assert.equal(p.playable,true);assert.equal(p.production_id,id);assert.equal(p.owner_listening_approval,"APPROVED_BY_OWNER_2026-11-09");assert.equal(p.seo_status,"noindex,follow");
 const rec=hls.records.find(x=>x.id===id);assert.ok(rec,"HLS track missing "+id);
 assert.equal(rec.master_sha256,track.master_sha256);assert.equal(rec.review_sha256,track.master_sha256);
 assert.equal(rec.source_license,"CC0-1.0");assert.equal(rec.source_page,track.source_page);
 assert.ok(rec.repeated_cycles>=1008);assert.ok(rec.native_stream_duration_hours>=167.9);
 assert.ok(rec.segment_count_per_source_cycle>=9&&rec.segment_count_per_source_cycle<=11);
 assert.ok(Math.abs(rec.source_cycle_seconds-600)<1.5);
 assert.equal(sha(rec.playlist_file),rec.playlist_sha256);
 const m3=read(rec.playlist_file);assert.ok(m3.startsWith("#EXTM3U"));assert.ok(m3.includes("#EXT-X-DISCONTINUITY"));assert.ok(m3.includes("#EXT-X-ENDLIST"));
 const page=read("sounds/"+slug+"/index.html");
 assert.ok(page.includes('name="robots" content="noindex,follow"'));assert.ok(page.includes('data-sound="'+id+'"'));assert.ok(page.includes('<audio controls loop preload="none"'));
 assert.ok(page.includes("/audio/"+id+".mp3")&&page.includes("/audio/continuous/"+id+"/continuous.m3u8"));
 assert.ok(page.includes(track.source_page));assert.ok(page.includes('"@type":"AudioObject"'));
 assert.ok(page.includes("lossy Freesound HQ MP3 preview"));
 assert.ok(hub.includes('href="/sounds/'+slug+'/"]')||hub.includes('href="/sounds/'+slug+'/"'));
 assert.ok(!read("sitemap.xml").includes("/sounds/"+slug+"/"));
 const ff=JSON.parse(cp.execFileSync("ffprobe",["-v","error","-show_entries","format=duration:stream=codec_name,channels,sample_rate","-of","json",metadata.production_mp3],{encoding:"utf8"}));
 assert.ok(Math.abs(Number(ff.format.duration)-600)<=1);assert.ok(ff.streams.some(x=>x.codec_name==="mp3"&&Number(x.channels)===2&&Number(x.sample_rate)===44100));
 console.log("WATER_OCEAN_WAVE2_PRODUCTION_TRACK_PASS "+JSON.stringify({id,master_sha256:track.master_sha256,hls_hours:rec.native_stream_duration_hours,independent_seconds:605}));
}
assert.equal(fams.find(x=>x.id==="water").existing_ids.slice(-1)[0],"bodetal-brook-real");
assert.equal(fams.find(x=>x.id==="ocean").existing_ids.slice(-1)[0],"crashing-ocean-real");
assert.equal(fams.find(x=>x.id==="ocean").route,"/sounds/#ocean-waves");
assert.equal((read("sounds/index.html").match(/data-wnc-existing-id="/g)||[]).length,35);
assert.ok(read("listen.html").includes("13 families · 45 playable sources (35 original catalog + 10 new DSP)"));
assert.equal(JSON.parse(read("listen.html").split("var recipes=")[1].split("];")[0]+"]").length,45);
assert.equal((read("sitemap.xml").match(/<loc>/g)||[]).length,18);
console.log("WATER_OCEAN_WAVE2_PRODUCTION_QA_PASS original33 SHA pinned, 35 HLS, 2 reviewed CC0 WAV-source MP3 derivatives promoted byte-identically, 45 presets, noindex SEO and blocked Bamboo.");
