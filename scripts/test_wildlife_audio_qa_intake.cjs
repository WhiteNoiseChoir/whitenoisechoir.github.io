#!/usr/bin/env node
"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs");
const qa=JSON.parse(fs.readFileSync("catalog/wildlife-audio-qa-wave1.json","utf8"));
const src=JSON.parse(fs.readFileSync(qa.linked_candidate_manifest,"utf8"));
assert.equal(src.records.length,14);assert.equal(qa.auditions.length,5);
assert.equal(new Set(qa.auditions.map(a=>a.candidate_id)).size,5);
const m=new Map(src.records.map(x=>[x.candidate_id,x]));
for(const a of qa.auditions){
assert.equal(m.get(a.candidate_id)?.source_url,a.source_url);
assert.equal(a.qa_status,"NOT_RUN");assert.equal(a.human_review,"PENDING");
assert.equal(a.download_status,"BLOCKED_LOGIN_REQUIRED");
}
assert.equal(qa.production_integration,false);
assert.equal(qa.public_review_page_ready,false);
assert.equal(qa.review_audio_paths.length,0);
console.log("Wildlife QA intake manifest PASS: zero fake audio, zero production promotions.");
