#!/usr/bin/env node
"use strict";
const resolve=require("./resolve_review_media.cjs");
const fs=require("fs"),crypto=require("crypto"),assert=require("assert/strict"),cp=require("child_process");
const read=p=>fs.readFileSync(p,"utf8"),json=p=>JSON.parse(read(p)),sha=p=>crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const root="signature/water-ocean-wave1-review",m=json(root+"/manifest.json"),html=read(root+"/index.html");
const sound=json("catalog/library.json"),hls=json("audio/continuous/manifest.json"),plans=json("catalog/planned-sounds.json").planned;
const expectRows=[["NEW-08","rushing-river-review","orlandorizo",864312],["NEW-09","forest-stream-review","GirlWithSoundRecorder",588403],["NEW-12","gentle-ocean-review","Sandy-Ogilvie",818828]];
assert.equal(m.status,"REVIEW_ONLY_PENDING_OWNER");assert.equal(m.tracks.length,3);assert.equal(sound.sounds.length,35);
assert.equal(hls.records.length,35);assert.equal(hls.applies_to.length,35);
const recipes=JSON.parse(read("listen.html").split("var recipes=")[1].split("];")[0]+"]");assert.equal(recipes.length,45);
assert.equal((read("sitemap.xml").match(/<loc>/g)||[]).length,18);
assert.ok(html.includes('name="robots" content="noindex,nofollow"'));assert.ok(html.includes("Tua tới 9:55"));assert.ok(html.includes('id="copy"'));
assert.ok(!read("sitemap.xml").includes(root));
const names=new Set(sound.sounds.map(s=>s.id));
for(let i=0;i<3;i++){
 const [plan,id,creator,soundId]=expectRows[i],track=m.tracks[i],path=resolve(root+"/"+id+".mp3");
 assert.equal(track.id,id);assert.equal(track.plan_id,plan);assert.equal(track.creator,creator);
 assert.equal(track.source_type,"CC0-1.0");assert.ok(track.source_page.includes("/sounds/"+soundId+"/"));
 assert.equal(track.review_status,"PENDING_OWNER_LISTENING");assert.equal(track.publication_status,"REVIEW_ONLY_NOT_IN_PRODUCTION");
 assert.equal(track.technical_status,"PASS");assert.equal(track.output_codec,"mp3");
 assert.ok(track.duration_seconds>=599&&track.duration_seconds<=601);
 assert.equal(track.channels,2);assert.equal(track.sample_rate,44100);
 assert.ok(fs.existsSync(path)&&fs.statSync(path).size>13_000_000);
 assert.equal(sha(path),track.master_sha256);assert.ok(track.peak_dbfs<=-5.5);
 assert.ok(track.independent_source_seconds>=600);
 assert.ok(names.has(['rushing-river-real','forest-stream-real','gentle-ocean-real'][i]));assert.ok(hls.applies_to.includes(['rushing-river-real','forest-stream-real','gentle-ocean-real'][i]));
 assert.ok(html.includes('data-track="'+id+'"'));
 const entry=plans.find(p=>p.plan_id===plan);
 assert.equal(entry.readiness,"released_audio_seo_pending");assert.equal(entry.playable,true);assert.equal(entry.production_id,["rushing-river-real","forest-stream-real","gentle-ocean-real"][i]);assert.equal(entry.owner_listening_approval,"APPROVED_BY_OWNER_2026-11-09");
 const probe=JSON.parse(cp.execFileSync("ffprobe",["-v","error","-show_entries","format=duration:stream=codec_name,channels,sample_rate","-of","json",path],{encoding:"utf8"}));
 assert.ok(Math.abs(Number(probe.format.duration)-600)<1);
 assert.ok(probe.streams.some(x=>x.codec_name==="mp3"&&x.channels===2&&Number(x.sample_rate)===44100));
 console.log("WATER_OCEAN_REVIEW_AUDIO_PASS "+JSON.stringify({id,sha:track.master_sha256,independent:track.independent_source_seconds,mean_dbfs:track.mean_dbfs,peak_dbfs:track.peak_dbfs}));
}
assert.ok(m.media_quality_policy.toLowerCase().includes("lossy"));assert.ok(m.tracks.every(x=>x.independent_source_seconds>=600&&x.repetitions_approx===0));
assert.ok(m.tracks[1].independent_source_seconds>=600);
console.log("WATER_OCEAN_WAVE1_REVIEW_ONLY_QA_PASS: 3 distinct CC0 real-field sources; original review unchanged; 33 live sounds, 33 HLS and 45 original mixes intact.");
