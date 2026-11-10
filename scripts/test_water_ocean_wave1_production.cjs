#!/usr/bin/env node
"use strict";
const resolve=require("./resolve_review_media.cjs");
/* Water/Ocean Wave 1 promotion: exact owner-approved MP3 bytes, 30-original SHA guard,
   33 total HLS, no SEO cannibalization and no claim of physical iPhone QA. */
const fs=require("node:fs"),assert=require("node:assert/strict"),crypto=require("node:crypto"),cp=require("node:child_process");
const file=p=>fs.readFileSync(p),read=p=>file(p).toString("utf8"),json=p=>JSON.parse(read(p));
const sha=p=>crypto.createHash("sha256").update(file(p)).digest("hex");
const gitblob=p=>{const v=file(p);return crypto.createHash("sha1").update(Buffer.from("blob "+v.length+"\0")).update(v).digest("hex")};
const catalog=json("catalog/library.json"),fams=json("catalog/family-registry.json").families,plans=json("catalog/planned-sounds.json").planned,hls=json("audio/continuous/manifest.json"),review=json("signature/water-ocean-wave1-review/manifest.json"),prov=json("audio/water-ocean-wave1-provenance.json"),lock=json("audio/water-ocean-wave1-existing-30-lock.json");
const newIDs=["rushing-river-real","forest-stream-real","gentle-ocean-real"],slugs=["rushing-river","forest-stream","gentle-ocean-waves"],origPlans=["NEW-08","NEW-09","NEW-12"];
assert.equal(prov.status,"OWNER_APPROVED_FOR_AUDIO");assert.equal(review.status,"REVIEW_ONLY_PENDING_OWNER");
assert.equal(prov.tracks.length,3);assert.equal(review.tracks.length,3);
assert.equal(catalog.sounds.length,35);assert.equal(new Set(catalog.sounds.map(x=>x.id)).size,35);
assert.equal(hls.records.length,35);assert.equal(hls.applies_to.length,35);assert.equal(new Set(hls.applies_to).size,35);
assert.equal(fams.length,13);assert.equal(plans.length,70);assert.equal(plans.filter(x=>x.playable).length,13);assert.equal(plans.filter(x=>!x.playable).length,57);
assert.equal(lock.records.length,30);assert.equal(new Set(lock.records.map(x=>x.id)).size,30);
const oldIDs=new Set(lock.records.map(x=>x.id)),liveIDs=new Set(hls.records.map(x=>x.id));
for(const pinned of lock.records){
 const row=hls.records.find(x=>x.id===pinned.id);
 assert.ok(row,"Original 30 HLS track lost: "+pinned.id);
 assert.equal(row.master_sha256,pinned.master_sha256);assert.equal(row.playlist_sha256,pinned.playlist_sha256);
 assert.equal(sha(row.master_file),pinned.master_sha256);assert.equal(sha(row.playlist_file),pinned.playlist_sha256);
}
// Domain-migration audit (2026-11-10): historical old-host Ocean page blob
// 13f684200c1b276276018895c5a0af9896c40a7e at 4100e4085b3e6b4160a10b840b4c1c0b71dd9bb9
// was intentionally transformed by 4d72ee391464d4bc149dfdacd6707f4cb6d9ec7c:
// all whitenoisechoir.github.io occurrences -> whitenoisechoir.com,
// and contentUrl https://whitenoisechoir.com/audio/ocean-waves-real.mp3
// -> https://media.whitenoisechoir.com/audio/ocean-waves-real.mp3.
// In-memory diff was verified against GitHub content before updating this guard.
// Pin the new reviewed blob and verify canonical + media URL without touching either file.
const oceanPage=read("sounds/ocean-waves/index.html");
assert.equal(gitblob("sounds/ocean-waves/index.html"),"1ffb0a6e4e8368f3c37418cbfe2bbca4f6312573","Reviewed post-domain-migration Ocean canonical page must remain byte-identical");
assert.ok(oceanPage.includes('<link rel="canonical" href="https://whitenoisechoir.com/sounds/ocean-waves/">'),"Ocean canonical must use production .com");
assert.ok(oceanPage.includes('"contentUrl":"https://media.whitenoisechoir.com/audio/ocean-waves-real.mp3"'),"Ocean structured audio URL must use approved R2 media hostname");
assert.ok(!oceanPage.includes("whitenoisechoir.github.io"),"Retired Ocean SEO hostname must not recur");
assert.ok(oceanPage.includes('name="robots" content="noindex,follow"'),"Ocean existing robots directive unchanged");
assert.equal(gitblob("assets/persistent-router.js"),"e7c039730a8869ab037736cabbce9eb7b6cef65d","Persistent playback code must be unchanged");
// Sitemap 1dc9eadc8c721d2ea2de27c91e46deeb6a6e5836
// (blob a3aebac7cc125f357d858730f4480f415ea298ea) became this blob at
// d37468ebd4ca09bb90ef4056406f3313358312cd via hostname substitution ONLY.
// Exact 18 URL paths below were verified identical before/after; no C6 candidate pages added.
const sitemap=read("sitemap.xml");
assert.equal(gitblob("sitemap.xml"),"1fb26b9e9186b3f9dba89234cc60c7bc3bb2228d","Reviewed .com sitemap must remain byte-identical");
const indexedRoutes=[...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m=>{
 assert.ok(m[1].startsWith("https://whitenoisechoir.com/"),"Unexpected sitemap hostname");
 return m[1].slice("https://whitenoisechoir.com".length);
});
assert.deepEqual(indexedRoutes,[
 "/","/sounds/","/collections/","/sounds/noise-colors/","/sounds/rain/",
 "/sounds/white-noise/","/sounds/pink-noise/","/sounds/brown-noise/",
 "/sounds/rain-on-window/","/sounds/fireplace/","/sounds/blue-noise/",
 "/sounds/violet-noise/","/sounds/heavy-rain/","/sounds/waterfall/",
 "/sounds/shower/","/collections/relaxing-sounds/",
 "/collections/white-noise-for-sleep/","/collections/baby-sleep-sounds/"
],"Existing 18 indexable routes only; no thin/unapproved variants");
const hub=read("sounds/water/index.html");assert.ok(hub.includes('name="robots" content="noindex,follow"'));
assert.ok(read("sounds/index.html").includes('id="ocean-waves"'),"Original Ocean family virtual anchor retained");
for(let i=0;i<3;i++){
 const id=newIDs[i],slug=slugs[i],row=review.tracks[i],p=prov.tracks[i],snd=catalog.sounds.find(x=>x.id===id),plan=plans.find(x=>x.plan_id===origPlans[i]);
 assert.ok(!oldIDs.has(id));assert.ok(liveIDs.has(id));
 assert.equal(row.plan_id,origPlans[i]);assert.equal(row.technical_status,"PASS");
 assert.equal(row.source_type,"CC0-1.0");assert.equal(row.duration_seconds,600);
 assert.equal(row.independent_source_seconds,605);assert.equal(row.repetitions_approx,0);
 assert.equal(p.production_id,id);assert.equal(p.plan_id,origPlans[i]);assert.equal(p.master_sha256,row.master_sha256);
 assert.equal(p.owner_listening_status,"APPROVED_BY_OWNER_2026-11-09");
 assert.equal(p.license,"CC0-1.0");assert.equal(p.lossless_original_downloaded,false);
 assert.equal(p.source_page,row.source_page);assert.equal(p.independent_source_used_seconds,605);
 assert.equal(sha(resolve(p.review_mp3)),row.master_sha256);assert.equal(sha(p.production_mp3),row.master_sha256);
 assert.equal(snd.slug,slug);assert.equal(snd.cat,"water");assert.equal(snd.status,"listening-approved");
 assert.equal(plan.production_id,id);assert.equal(plan.playable,true);assert.equal(plan.seo_status,"noindex,follow");
 assert.equal(plan.owner_listening_approval,"APPROVED_BY_OWNER_2026-11-09");
 const h=hls.records.find(x=>x.id===id);assert.ok(h);
 assert.equal(h.master_sha256,row.master_sha256);assert.equal(h.review_sha256,row.master_sha256);
 assert.equal(h.source_license,"CC0-1.0");assert.equal(h.source_page,row.source_page);
 assert.equal(h.original_source_length_category,"10_MINUTE_MASTER_FROM_CC0_PREVIEW");
 assert.ok(h.native_stream_duration_hours>=167.9);assert.ok(h.repeated_cycles>=1008);
 assert.ok(h.segment_count_per_source_cycle>=9&&h.segment_count_per_source_cycle<=11);
 assert.ok(Math.abs(h.source_cycle_seconds-600)<=1.5);
 assert.equal(sha(h.playlist_file),h.playlist_sha256);
 assert.ok(fs.existsSync("audio/continuous/"+id+"/part_000.ts"));
 const m3=read(h.playlist_file);assert.ok(m3.startsWith("#EXTM3U"));assert.ok(m3.includes("#EXT-X-DISCONTINUITY"));assert.ok(m3.includes("#EXT-X-ENDLIST"));
 const soundPage=read("sounds/"+slug+"/index.html");
 assert.ok(soundPage.includes('name="robots" content="noindex,follow"'));assert.ok(soundPage.includes('data-sound="'+id+'"'));
 assert.ok(soundPage.includes("/audio/"+id+".mp3")&&soundPage.includes("/audio/continuous/"+id+"/continuous.m3u8"));
 assert.ok(soundPage.includes('<audio controls loop preload="none"'));assert.ok(soundPage.includes(row.source_page));
 assert.ok(soundPage.includes('"@type":"AudioObject"'));assert.ok(soundPage.includes("lossy Freesound HQ MP3 preview"));
 assert.ok(hub.includes('href="/sounds/'+slug+'/"'));assert.ok(!read("sitemap.xml").includes("/sounds/"+slug+"/"));
 const probe=JSON.parse(cp.execFileSync("ffprobe",["-v","error","-show_entries","format=duration:stream=codec_name,channels,sample_rate","-of","json",p.production_mp3],{encoding:"utf8"}));
 assert.ok(Math.abs(Number(probe.format.duration)-600)<=1);
 assert.ok(probe.streams.some(z=>z.codec_name==="mp3"&&z.channels===2&&Number(z.sample_rate)===44100));
 console.log("WATER_OCEAN_WAVE1_PRODUCTION_TRACK_PASS "+JSON.stringify({id,sha256:row.master_sha256,hls_hours:h.native_stream_duration_hours,independent_seconds:605}));
}
assert.deepEqual(fams.find(f=>f.id==="water").existing_ids.slice(-3,-1),newIDs.slice(0,2));
assert.equal(fams.find(f=>f.id==="ocean").existing_ids.slice(-2,-1)[0],newIDs[2]);
assert.equal(fams.find(f=>f.id==="ocean").route,"/sounds/#ocean-waves");
assert.equal((read("sounds/index.html").match(/data-wnc-existing-id="/g)||[]).length,35);
assert.ok(read("index.html").includes("13 families · 35 catalog sources"));
assert.equal(JSON.parse(read("index.html").split("var recipes=")[1].split("];")[0]+"]").length,45);
assert.equal((read("sitemap.xml").match(/<loc>/g)||[]).length,18);
console.log("WATER_OCEAN_WAVE1_PRODUCTION_QA_PASS original30 protected, 3 owner-approved exact MP3, 33 HLS with static 7day, 45 original presets, Ocean canonical migrated with verified provenance; 18 sitemap paths preserved.");
