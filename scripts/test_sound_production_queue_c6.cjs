#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict"),vm=require("node:vm"),cp=require("node:child_process");
const read=p=>fs.readFileSync(p,"utf8"),parse=p=>JSON.parse(read(p));
const q=parse("catalog/sound-production-queue-c6.json");
const reg=parse("catalog/sound-production-registry-c5.json");
const lib=parse("catalog/library.json");
const approval=parse("catalog/sound-release-approvals.json");
const html=read("framework-preview/c6-listening/index.html");
const sitemap=read("audits/sitemap-before-studio.xml");
assert.equal(q.items.length,10);assert.equal(q.summary.total_p0_candidates,10);
assert.equal(new Set(q.items.map(x=>x.record_id)).size,10);
assert.equal(reg.records.length,532);assert.equal(lib.sounds.length,35);
assert.deepEqual(approval.approvals,[],"C6 must not silently approve a release");
assert.equal(q.immutable_baseline.production_sources,35);
assert.equal(q.immutable_baseline.presets,45);
assert.equal(q.immutable_baseline.registry_records,532);
assert.equal(q.target.independent_original_seconds_min,600);
assert.equal(q.target.original_10min_distinct_from_looped_10min,true);
const byId=new Map(reg.records.map(r=>[r.id,r]));
for(let i=0;i<q.items.length;i++){
const c=q.items[i],r=byId.get(c.record_id);
assert.ok(r,"Unknown registry ID "+c.record_id);
assert.equal(c.rank,i+1);
assert.equal(c.priority,"P0");
assert.equal(c.editorial_class,"SOURCE_CANDIDATE");
assert.equal(r.priority,"P0");assert.equal(r.editorial_class,"SOURCE_CANDIDATE");
assert.equal(r.existing_production,null,"existing sound may not be proposed as new");
assert.equal(c.title_en,r.title_en);
assert.equal(c.family_id,r.family_id);
assert.equal(c.source_refs,r.evidence.source_refs);
assert.equal(c.source_audit.status,"UNSOURCED");
assert.equal(c.source_audit.license,null);
assert.equal(c.source_audit.license_evidence_url,null);
assert.equal(c.source_audit.provenance_url,null);
assert.equal(c.source_audit.original_asset_sha256,null);
assert.equal(c.source_audit.independent_seconds,null);
assert.equal(c.master_audit.status,"NOT_PRODUCED");
assert.equal(c.master_audit.master_sha256,null);
assert.equal(c.master_audit.whole_file_decode,"NOT_RUN");
assert.equal(c.master_audit.cross_source_dedup,"NOT_RUN");
assert.equal(c.review_audio,null);
assert.equal(c.owner_listening.status,"NOT_REQUESTED");
assert.equal(c.release_status,"BLOCKED");
assert.equal(c.seo.allow_index,false);
assert.equal(c.seo.new_route,null);
assert.ok(c.editorial_intents.length>=1&&c.acoustic_brief&&c.dedup_instructions);
for(const ref of c.compare_existing_ids){if(!ref.startsWith("none:"))assert.ok(lib.sounds.some(s=>s.id===ref),"unknown comparison source "+ref)}
}
for(const [k,v] of Object.entries(q.summary)){
if(k!=="total_p0_candidates")assert.equal(v,0,"C6 no premature QA/acquisition/release "+k)
}
assert.ok(html.includes('<meta name="robots" content="noindex,nofollow,noarchive">'));
assert.ok(!html.includes('rel="canonical"'));
assert.ok(!html.includes('application/ld+json'));
assert.ok(html.includes('id="seek"')&&html.includes('id="near-end"'));
assert.ok(html.includes('disabled aria-label="Seek position within recording"'));
assert.ok(html.includes('function safeReview(r)'));
assert.ok(html.includes('s.independent_seconds>=600'));
assert.ok(html.includes('a.technical_qa_pass===true'));
assert.ok(html.includes('audio.currentTime=audio.duration-5'));
assert.ok(html.includes('fetch("/catalog/sound-production-queue-c6.json"'));
const js=html.split("<script>")[1]?.split("</script>")[0];assert.ok(js);
new vm.Script(js,{filename:"C6 review room"});
assert.equal(q.research_summary.individual_source_pages_inspected,2);
assert.equal(q.research_summary.metadata_leads_meeting_600s_on_page,2);
assert.equal(q.research_summary.downloaded_originals,0);
assert.equal(q.research_summary.rights_provenance_confirmed,0);
for(const id of ["SND-0039","SND-0040"]){
 const row=q.items.find(r=>r.record_id===id);
 assert.equal(row.metadata_discovery.length,1);
 assert.equal(row.metadata_discovery[0].discovery_status,"PAGE_METADATA_ONLY_NOT_ACQUIRED");
 assert.ok(row.metadata_discovery[0].displayed_duration_seconds>=600);
 assert.equal(row.metadata_discovery[0].declared_license_on_page,"Creative Commons 0");
 assert.equal(row.source_audit.license,null);
}
assert.ok(!sitemap.includes("c6-listening"));
assert.ok(!sitemap.includes("sound-production-queue-c6"));
const blocked=JSON.parse(cp.execFileSync(process.execPath,["scripts/sound_release_gate.cjs","--id=SND-0040"],{encoding:"utf8"}));
assert.equal(blocked.ready,false,"C5 owner release gate must remain closed");
console.log("C6_AUDIT_PASS: ten independently sourced P0 candidates queued; 35 production and 45 presets preserved; source/rights/QA/owner/SEO gates closed; locked seekable audition room non-indexed");
