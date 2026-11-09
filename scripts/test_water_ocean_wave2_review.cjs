#!/usr/bin/env node
"use strict";
const resolve=require("./resolve_review_media.cjs");
const fs=require("node:fs"),crypto=require("node:crypto"),assert=require("node:assert/strict"),cp=require("node:child_process");
const read=p=>fs.readFileSync(p,"utf8"),j=p=>JSON.parse(read(p)),sha=p=>crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const dir="signature/water-ocean-wave2-review",m=j(dir+"/manifest.json"),html=read(dir+"/index.html");
const catalog=j("catalog/library.json"),hls=j("audio/continuous/manifest.json"),plans=j("catalog/planned-sounds.json").planned;
const rows=[["NEW-10","bodetal-brook-review","Borgory",651194],["NEW-13","wakanui-surf-review","Desmond178",721591]];
assert.equal(m.status,"REVIEW_ONLY_PENDING_OWNER");assert.equal(m.tracks.length,2);
assert.equal(catalog.sounds.length,35);assert.equal(hls.records.length,35);assert.equal(hls.applies_to.length,35);
assert.equal(plans.filter(x=>!x.playable).length,57);assert.equal(plans.filter(x=>x.playable).length,13);
assert.equal(JSON.parse(read("index.html").split("var recipes=")[1].split("];")[0]+"]").length,45);
assert.equal((read("sitemap.xml").match(/<loc>/g)||[]).length,18);
assert.ok(html.includes('name="robots" content="noindex,nofollow"'));
assert.ok(html.includes("Tua tới 9:55")&&html.includes('id="copy"'));
assert.ok(html.includes("BLOCKED_SOURCE_NOT_VERIFIED")&&html.includes("NEW-11"));
assert.ok(!read("sitemap.xml").includes(dir));
const bamboo=plans.find(x=>x.plan_id==="NEW-11");assert.equal(bamboo.playable,false);assert.equal(bamboo.production_id,null);
for(let i=0;i<rows.length;i++){
 const [plan,id,creator,sourceId]=rows[i],x=m.tracks[i],target=resolve(dir+"/"+id+".mp3"),p=plans.find(x=>x.plan_id===plan);
 assert.equal(x.plan_id,plan);assert.equal(x.id,id);assert.equal(x.creator,creator);assert.equal(x.source_type,"CC0-1.0");
 assert.ok(x.source_page.endsWith("/sounds/"+sourceId+"/"));assert.equal(x.technical_status,"PASS");
 assert.equal(x.review_status,"PENDING_OWNER_LISTENING");assert.equal(x.publication_status,"REVIEW_ONLY_NOT_IN_PRODUCTION");
 assert.ok(x.duration_seconds>=599&&x.duration_seconds<=601);
 assert.equal(x.output_codec,"mp3");assert.equal(x.channels,2);assert.equal(x.sample_rate,44100);
 assert.equal(x.independent_source_seconds,605);assert.equal(x.repetitions_approx,0);
 assert.ok(fs.existsSync(target)&&fs.statSync(target).size>13_000_000);
 assert.equal(sha(target),x.master_sha256);assert.ok(x.peak_dbfs<=-5.5);
 assert.equal(p.readiness,"released_audio_seo_pending");assert.equal(p.playable,true);assert.equal(p.production_id,["bodetal-brook-real","crashing-ocean-real"][i]);assert.equal(p.owner_listening_approval,"APPROVED_BY_OWNER_2026-11-09");
 assert.ok(html.includes('data-track="'+id+'"'));
 const info=JSON.parse(cp.execFileSync("ffprobe",["-v","error","-show_entries","format=duration:stream=codec_name,channels,sample_rate","-of","json",target],{encoding:"utf8"}));
 assert.ok(Math.abs(Number(info.format.duration)-600)<=1);
 assert.ok(info.streams.some(z=>z.codec_name==="mp3"&&Number(z.channels)===2&&Number(z.sample_rate)===44100));
 console.log("WAVE2_REVIEW_TRACK_PASS "+JSON.stringify({id,sha:x.master_sha256,independent_seconds:x.independent_source_seconds,peak:x.peak_dbfs}));
}
assert.ok(m.media_quality_policy.toLowerCase().includes("lossy"));
console.log("WATER_OCEAN_WAVE2_REVIEW_QA_PASS two independent CC0 review masters, third bamboo source blocked, 33 old HLS+audio and 45 presets unchanged.");
