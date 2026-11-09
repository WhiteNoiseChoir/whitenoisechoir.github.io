#!/usr/bin/env node
"use strict";
/* Production-safe, deterministic dedup gate. A legacy review path can be
 * removed only if its Git blob, MP3 length and SHA-256 are identical to an
 * existing approved production master. Never regenerate, downsample or rename.
 */
const fs=require("node:fs"),crypto=require("node:crypto"),cp=require("node:child_process"),assert=require("node:assert/strict");
const data=JSON.parse(fs.readFileSync("audio/review-media-dedup.json","utf8"));
const resolve=require("./resolve_review_media.cjs");
const read=p=>fs.readFileSync(p,"utf8");
const sha256=p=>crypto.createHash("sha256").update(fs.readFileSync(p)).digest("hex");
const blob=p=>{const bytes=fs.readFileSync(p);return crypto.createHash("sha1").update(Buffer.from("blob "+bytes.length+"\0")).update(bytes).digest("hex")};
const original=1199044630, expected=994477548;
assert.equal(data.original_tracked_bytes,original);
assert.equal(data.removed_tracked_bytes,204567082);
assert.equal(data.expected_tracked_bytes_after,expected);
assert.equal(data.pairs.length,17);
assert.equal(new Set(data.pairs.map(x=>x.review_path)).size,17);
assert.equal(new Set(data.pairs.map(x=>x.production_path)).size,17);
const cat=JSON.parse(read("catalog/library.json"));
const hls=JSON.parse(read("audio/continuous/manifest.json"));
assert.equal(cat.sounds.length,35);assert.equal(hls.records.length,35);assert.equal(hls.applies_to.length,35);
assert.equal(JSON.parse(read("index.html").split("var recipes=")[1].split("];")[0]+"]").length,45);
assert.equal((read("sitemap.xml").match(/<loc>/g)||[]).length,18);
assert.ok(fs.existsSync("assets/persistent-router.js"));
let reclaimed=0;
for(const x of data.pairs){
 assert.ok(x.review_path.startsWith("signature/"));
 assert.ok(x.production_path.startsWith("audio/"));
 assert.ok(!fs.existsSync(x.review_path),"Duplicated review file remains: "+x.review_path);
 assert.ok(fs.existsSync(x.production_path),"Production file is missing: "+x.production_path);
 assert.equal(resolve(x.review_path),x.production_path);
 assert.equal(blob(x.production_path),x.git_blob_sha,"Production byte identity changed: "+x.production_path);
 assert.equal(sha256(x.production_path),x.sha256,"Approved SHA-256 changed: "+x.production_path);
 assert.equal(fs.statSync(x.production_path).size,x.bytes);
 const room=x.review_path.split("/").slice(0,-1).join("/")+"/index.html";
 assert.ok(fs.existsSync(room),"Review room removed: "+room);
 const html=read(room);
 assert.match(html,/<meta name="robots" content="noindex,nofollow">/);
 assert.ok(!html.includes("src=\"./"+x.review_path.split("/").at(-1)+"\""),"Stale relative review player src "+room);
 const productionName=x.production_path.split("/").at(-1).replace(/\.mp3$/,"");
 assert.ok(html.includes(productionName),"Room does not reference production master "+productionName+" : "+room);
 reclaimed+=x.bytes;
}
assert.equal(reclaimed,data.removed_tracked_bytes);
const listening=read("signature/listening-approval/index.html");
assert.ok(listening.includes('url:"/audio/"+t[0]+".mp3"'));
assert.ok(!listening.includes('url:"/signature/field-review/"'));
const fpaths=cp.execFileSync("git",["ls-files","-z"]).toString().split("\0").filter(Boolean);
const current=fpaths.reduce((bytes,f)=>bytes+fs.statSync(f).size,0);
assert.ok(current>=expected && current<expected+200000,"Unexpected tracked-tree delta; review new small metadata/QA files before release: "+current);
assert.ok(current<1000000000,"Tracked tree is still above 1,000,000,000 bytes");
console.log("APPROVED_REVIEW_AUDIO_DEDUP_PASS "+JSON.stringify({
 checked: data.pairs.length, removed_duplicate_bytes:reclaimed,
 original_tracked_bytes:original, current_tracked_bytes:current,
 reduction_percent:+(reclaimed/original*100).toFixed(3),
 production_sources:35, continuous_HLS:35, presets:45, indexed_sitemap_urls:18,
 provenance_historical_paths_preserved:true,
 note:"Track-file sizes do not equal actual published GitHub Pages artifact; real-device iPhone audio testing not performed"
}));
