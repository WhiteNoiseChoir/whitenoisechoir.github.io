#!/usr/bin/env node
"use strict";
/* Wildlife QA Intake: metadata check + optional local ffprobe. Never promotes to production. */
const fs=require("node:fs"),path=require("node:path"),crypto=require("node:crypto"),cp=require("node:child_process"),assert=require("node:assert/strict");
const manifest=JSON.parse(fs.readFileSync("catalog/wildlife-audio-qa-wave1.json","utf8"));
const candidates=JSON.parse(fs.readFileSync(manifest.linked_candidate_manifest,"utf8"));
const byId=new Map(candidates.records.map(x=>[x.candidate_id,x]));
assert.equal(manifest.production_integration,false);
assert.equal(manifest.public_review_page_ready,false);
assert.equal(manifest.auditions.length,5);
for(const a of manifest.auditions){
 const c=byId.get(a.candidate_id);
 assert.ok(c,"missing candidate "+a.candidate_id);
 assert.equal(c.source_url,a.source_url);
 assert.equal(a.qa_status,"NOT_RUN");
 assert.equal(a.human_review,"PENDING");
 assert.equal(a.download_status,"BLOCKED_LOGIN_REQUIRED");
}
const files=process.argv.slice(2);
const results=[];
for(const filename of files){
 const id=path.basename(filename).split(".")[0];
 const m=manifest.auditions.find(x=>x.candidate_id===id);
 assert.ok(m,"Unrecognized candidate file (name by ID): "+filename);
 assert.ok(fs.statSync(filename).isFile());
 const hash=crypto.createHash("sha256").update(fs.readFileSync(filename)).digest("hex");
 const inspect=cp.spawnSync("ffprobe",["-v","error","-show_entries","format=duration,format_name:stream=index,codec_name,sample_rate,channels","-of","json",filename],{encoding:"utf8"});
 assert.equal(inspect.status,0,"ffprobe unavailable/failed; install ffmpeg tools");
 const details=JSON.parse(inspect.stdout),seconds=Number(details.format?.duration);
 assert.ok(Number.isFinite(seconds)&&seconds>0,"bad duration");
 results.push({id,filename,bytes:fs.statSync(filename).size,sha256:hash,duration_seconds:seconds,source_page_duration_seconds:m.expected_duration_seconds,format:details.format?.format_name,streams:details.streams,warning:"Automated identification only; not acoustic QA, rights confirmation or listening approval"});
}
console.log(JSON.stringify({metadata_gate:"PASS",audition_queue:manifest.auditions.length,files_inspected:results.length,results,ready_for_production:false},null,2));
