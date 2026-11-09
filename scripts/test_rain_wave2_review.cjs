#!/usr/bin/env node
"use strict";
const resolve=require("./resolve_review_media.cjs");
/* Second-wave review only. It must never change the 25 production audio IDs. */
const fs=require("node:fs"),crypto=require("node:crypto"),assert=require("node:assert/strict");
const read=p=>fs.readFileSync(p,"utf8"),json=p=>JSON.parse(read(p));
const sha=p=>crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const root="signature/rain-wave2-review",html=read(root+"/index.html"),manifest=json(root+"/manifest.json");
const plans=json("catalog/planned-sounds.json").planned,catalog=json("catalog/library.json"),hls=json("audio/continuous/manifest.json");
const expected=[
["NEW-03","rain-on-tent-review","venaportae",174874,2],
["NEW-04","rain-car-roof-review","gyzhor",874299,1],
["NEW-07","rolling-thunder-review","Borgory",870414,2]
];
assert.equal(manifest.status,"REVIEW_ONLY_PENDING_OWNER");
assert.equal(manifest.tracks.length,3);
assert.equal(catalog.sounds.length,35);
assert.equal(hls.records.length,35);
assert.equal((read("sitemap.xml").match(/<loc>/g)||[]).length,18);
assert.ok(html.includes('name="robots" content="noindex,nofollow"'));
assert.ok(html.includes("Tua tới 9:55")&&html.includes('id="copy"'));
assert.ok(!read("sitemap.xml").includes("/signature/rain-wave2-review/"));
assert.ok(!read("index.html").includes("rain-on-tent-review"));
assert.ok(!read("sounds/index.html").includes("rain-on-tent-review"));
const oldIds=new Set(catalog.sounds.map(x=>x.id));
for(let i=0;i<expected.length;i++){
 const [planId,id,creator,soundId,channels]=expected[i],m=manifest.tracks[i];
 assert.equal(m.id,id);assert.equal(m.plan_id,planId);
 assert.equal(m.creator,creator);
 assert.equal(m.source_type,"CC0-1.0");
 assert.ok(m.source_page.includes("/sounds/"+soundId+"/"));
 assert.equal(m.review_status,"PENDING_OWNER_LISTENING");
 assert.equal(m.publication_status,"REVIEW_ONLY_NOT_IN_PRODUCTION");
 assert.equal(m.technical_status,"PASS");
 assert.equal(m.duration_seconds,600);
 assert.equal(m.output_codec,"mp3");
 assert.equal(m.sample_rate,44100);
 assert.equal(m.channels,2);
 assert.ok(m.master_bytes>13_000_000);
 assert.ok(m.peak_dbfs<=-5.5,"safe sample peak");
 assert.ok(m.independent_source_seconds>50&&m.independent_source_seconds<=605);
 assert.equal(m.downloaded_preview_channels,channels,"true source channels must be disclosed, especially car roof mono");
 const audio=resolve(root+"/"+id+".mp3");
 assert.ok(fs.existsSync(audio));
 assert.equal(fs.statSync(audio).size,m.master_bytes);
 assert.equal(sha(audio),m.master_sha256);
 assert.ok(html.includes('data-track="'+id+'"'));
 assert.ok(!oldIds.has(id));
 assert.ok(!hls.applies_to.includes(id));
 const item=plans.find(x=>x.plan_id===planId);
 assert.equal(item.readiness,"released_audio_seo_pending");
 assert.equal(item.playable,true);
 assert.equal(item.production_id,["rain-on-tent-real","rain-car-roof-real","rolling-thunder-real"][i]);
 assert.equal(item.owner_listening_approval,"APPROVED_BY_OWNER_2026-11-09");
 assert.ok(item.seo_page.startsWith("/sounds/"));
}
assert.ok(manifest.media_quality_policy.toLowerCase().includes("lossy"));
console.log("RAIN_WAVE2_REVIEW_QA_PASS: 3 actual independent CC0 preview-derived 600s MP3 auditions, 25 production IDs untouched, noindex review room, true car-mono source disclosed");
