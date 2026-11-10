#!/usr/bin/env node
"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict"),vm=require("node:vm"),cp=require("node:child_process");
const read=p=>fs.readFileSync(p,"utf8"),parse=p=>JSON.parse(read(p));
const inv=parse("framework-preview/master-inventory.json"),reg=parse("catalog/sound-production-registry-c5.json"),lib=parse("catalog/library.json"),plans=parse("catalog/planned-sounds.json").planned,ledger=parse("catalog/sound-release-approvals.json");
const site=read("framework-preview/sound-detail/index.html"),explore=read("sounds/explore/index.html"),sitemap=read("sitemap.xml");
const c=Object.fromEntries(inv.columns.map((k,i)=>[k,i]));
assert.equal(reg.records.length,532);assert.equal(reg.summary.total_records,532);
assert.equal(reg.summary.production_catalog,35);assert.equal(reg.summary.production_listening_pending,1);
assert.equal(reg.summary.production_catalog_other,34);
assert.equal(reg.summary.source_candidates,449);assert.equal(reg.summary.short_sfx,16);
assert.equal(reg.summary.technical_facets,18);assert.equal(reg.summary.soundscape_mixes,14);
assert.equal(reg.summary.plan_qa_pass_recorded,13);
assert.equal(reg.summary.plan_license_recorded,13);
assert.equal(reg.summary.new_urls_approved,0);assert.equal(reg.summary.new_audio_approved,0);
assert.deepEqual(ledger.approvals,[],"owner has not authorized any new releases");
assert.equal(new Set(reg.records.map(r=>r.id)).size,532);
const byProd=new Map(lib.sounds.map(s=>[s.id,s]));
const byPlan=new Map(plans.filter(p=>p.playable).map(p=>[p.production_id,p]));
for(let i=0;i<inv.rows.length;i++){
 const row=inv.rows[i],r=reg.records[i];
 assert.equal(r.id,row[c.id]);assert.equal(r.title_en,row[c.name_en]);assert.equal(r.family_id,row[c.family_id]);
 assert.equal(r.priority,row[c.priority]);assert.equal(r.semantic_review,row[c.semantic_review]==="YES");
 assert.equal(r.gates.allow_generate_new_audio,false);
 assert.equal(r.gates.allow_generate_new_page,false);
 assert.equal(r.gates.allow_index_new_page,false);
 if(row[c.v2_type]==="PRODUCTION_ASSET"){
  assert.ok(r.existing_production,"production reference missing");
  const prod=byProd.get(r.existing_production.id);assert.ok(prod,"unknown production ID");
  assert.equal(r.existing_production.route,"/sounds/"+prod.slug+"/");
  assert.equal(r.existing_production.status,prod.status);
  const p=byPlan.get(prod.id);
  if(p){
   assert.equal(r.evidence.plan_id,p.plan_id);assert.equal(r.evidence.license,p.license);
   assert.equal(r.gates.technical_qa,"PLAN_QA_PASS_RECORDED");
   assert.equal(r.gates.owner_listening,p.owner_listening_approval);
  }else{
   assert.equal(r.gates.technical_qa,"NOT_VERIFIED_IN_C5_REGISTRY");
   assert.equal(r.evidence.license,null);
  }
 }else{
  assert.equal(r.existing_production,null);
  assert.equal(r.evidence.license,null);
  assert.equal(r.gates.seo,"UNAPPROVED_NEW_ROUTE");
 }
}
const green=reg.records.find(r=>r.existing_production?.id==="green-noise");
assert.ok(green);assert.equal(green.current_stage,"PRODUCTION_PENDING_LISTENING");
assert.equal(green.gates.owner_listening,"PENDING_LISTENING_REVIEW");
assert.match(site,/<meta name="robots" content="noindex,nofollow,noarchive">/);
assert.ok(!site.includes('rel="canonical"'),"editorial preview may not claim canonical");
assert.ok(!/<audio\b/i.test(site),"editorial preview may not pretend to stream audio");
assert.ok(!/<script[^>]*type="application\\/ld\\+json"/i.test(site),"editorial preview may not emit JSON-LD for nonexistent audio");
assert.ok(site.includes('fetch("/catalog/sound-production-registry-c5.json"'));
assert.ok(site.includes('id="rights"')&&site.includes('id="technical"')&&site.includes('id="owner"')&&site.includes('id="seo"'));
const js=site.split("<script>")[1]?.split("</script>")[0];assert.ok(js);new vm.Script(js,{filename:"C5 sound detail template"});
assert.ok(explore.includes("View production / SEO checklist"));assert.ok(explore.includes("/framework-preview/sound-detail/?sound="));
assert.ok(!sitemap.includes("/framework-preview/sound-detail/"));
assert.ok(!sitemap.includes("production-registry"));
const audit=JSON.parse(cp.execFileSync(process.execPath,["scripts/sound_release_gate.cjs","--audit"],{encoding:"utf8"}));
assert.equal(audit.records,532);assert.equal(audit.ready_for_new_page,0);
assert.equal(audit.blocked_new_page,497);assert.equal(audit.existing_pages_preserved,35);
const blocked=JSON.parse(cp.execFileSync(process.execPath,["scripts/sound_release_gate.cjs","--id=SND-0040"],{encoding:"utf8"}));
assert.equal(blocked.ready,false);assert.ok(blocked.reasons.length>0);
console.log("PASS C5: 532 sound workflows, 35 existing preserved, 13 explicit evidence records, Green Noise held, zero new release approvals, safe page template");
