#!/usr/bin/env node
"use strict";
/*
 * WhiteNoiseChoir C5 audio/SEO release gate.
 * Read-only: it never generates MP3s, HTML, canonical URLs or sitemap entries.
 * --audit summarizes all records; --id=SND-XXXX checks one item.
 * --require-ready makes an unapproved candidate a nonzero exit.
 */
const fs=require("node:fs"),path=require("node:path");
const reg=JSON.parse(fs.readFileSync("catalog/sound-production-registry-c5.json","utf8"));
const ledger=JSON.parse(fs.readFileSync("catalog/sound-release-approvals.json","utf8"));
const byId=new Map(reg.records.map(r=>[r.id,r]));
if(byId.size!==reg.records.length)throw new Error("Duplicate registry IDs");
const approvals=new Map();
for(const a of ledger.approvals){
 if(!a||!byId.has(a.record_id)||approvals.has(a.record_id))throw new Error("Approval ledger contains bad/duplicate ID");
 approvals.set(a.record_id,a);
}
function evaluate(id){
 const row=byId.get(id);
 if(!row)throw new Error("Unknown sound record "+id);
 const a=approvals.get(id),why=[];
 if(row.existing_production)why.push("Existing sound page must be maintained, not duplicated");
 if(row.editorial_class!=="SOURCE_CANDIDATE")why.push("Only independent source candidates can be promoted to a new sound page");
 if(!a){why.push("No explicit release approval record");return {id,ready:false,reasons:why}}
 if(a.owner_approved!==true||!a.owner_approval_reference)why.push("Owner listening approval and reference missing");
 if(a.rights_verified!==true||!a.license||!a.provenance_url)why.push("Rights, license and provenance not approved");
 if(a.technical_qa_pass!==true||!a.master_sha256||!/^[a-f0-9]{64}$/i.test(a.master_sha256))why.push("Acoustic technical QA and valid master SHA-256 required");
 if(a.seo_review_pass!==true||!a.unique_intent_reason)why.push("Unique SEO intent approval missing");
 if(!/^\/sounds\/[a-z0-9-]+\/$/.test(a.approved_route||""))why.push("Safe exact approved route required");
 if(a.approved_route&&fs.existsSync(path.join("."+a.approved_route,"index.html")))why.push("Approved path already exists");
 if(row.gates.allow_generate_new_page!==true||row.gates.allow_index_new_page!==true)why.push("Record new-page and indexing gates still closed");
 return {id,ready:why.length===0,reasons:why};
}
const arg=process.argv.find(x=>x.startsWith("--id="));
if(arg){
 const result=evaluate(arg.slice(5));
 console.log(JSON.stringify(result,null,2));
 if(process.argv.includes("--require-ready")&&!result.ready)process.exitCode=1;
}else{
 const summary={records:reg.records.length,release_approvals:ledger.approvals.length,ready_for_new_page:0,blocked_new_page:0,existing_pages_preserved:0};
 for(const item of reg.records){
  if(item.existing_production)summary.existing_pages_preserved++;
  else if(evaluate(item.id).ready)summary.ready_for_new_page++;
  else summary.blocked_new_page++;
 }
 console.log(JSON.stringify(summary,null,2));
 if(summary.ready_for_new_page>0)throw Error("Unexpected new page readiness without owner production merge");
}
