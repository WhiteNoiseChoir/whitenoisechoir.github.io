#!/usr/bin/env node
"use strict";
/** Post-prune production audit; no network, no dependency, no mutation. */
const fs=require("node:fs"),cp=require("node:child_process"),crypto=require("node:crypto"),assert=require("node:assert/strict");
const j=p=>JSON.parse(fs.readFileSync(p,"utf8"));
const ledger=j("audits/r2-hls-immutable-source-inventory.json");
const m=j("audio/continuous/manifest.json"),lib=j("catalog/library.json");
const keep=new Set(["white-noise","pink-noise","brown-noise","rain-on-window-real",
 "box-fan-real","heavy-rain-real","ocean-waves-real","waterfall-real"]);
const ids=new Set(m.records.map(x=>x.id));
assert.equal(ids.size,35);assert.equal(lib.sounds.length,35);
assert.equal(keep.size,8);assert([...keep].every(x=>ids.has(x)));
assert.equal(ledger.files.length,360);assert.equal(ledger.retirable_bytes,514374326);
const tracked=cp.execFileSync("git",["ls-files","-z"]).toString().split("\0").filter(Boolean);
const listed=new Set(tracked);
const gitblob=p=>{
 const b=fs.readFileSync(p),prefix=Buffer.from("blob "+b.length+"\0");
 return crypto.createHash("sha1").update(prefix).update(b).digest("hex");
};
const missing=[],preserved=[];
for(const entry of ledger.files){
 const id=entry.path.split("/")[2],exists=listed.has(entry.path);
 assert.equal(exists,keep.has(id),"Wrong GitHub HLS fallback retention "+entry.path);
 if(exists){
  assert.equal(fs.statSync(entry.path).size,entry.size);
  assert.equal(gitblob(entry.path),entry.git_blob_sha1);
  preserved.push(entry);
 }else{
  assert.ok(!fs.existsSync(entry.path),"Retired HLS must NOT be present in production checkout: "+entry.path);
  missing.push(entry);
 }
}
assert.equal(missing.length,297);
assert.equal(preserved.length,63);
const reclaimed=missing.reduce((n,x)=>n+x.size,0);
assert.equal(reclaimed,430033063);
assert.equal(preserved.reduce((n,x)=>n+x.size,0),84341263);
for(const r of m.records){
 assert.ok(listed.has(r.master_file),"All 35 original GitHub MP3s must remain "+r.id);
 const buf=fs.readFileSync(r.master_file),hash=crypto.createHash("sha256").update(buf).digest("hex");
 assert.equal(hash,r.master_sha256,"Approved audio master changed "+r.id);
 const page=(lib.sounds.find(x=>x.id===r.id)||{});
 const pagePath="sounds/"+page.slug+"/index.html";
 assert.ok(fs.existsSync(pagePath),"Source detail page missing "+r.id);
 const html=fs.readFileSync(pagePath,"utf8");
 const expectedHls=(keep.has(r.id)?"/":"https://media.whitenoisechoir.com/")+
  "audio/continuous/"+r.id+"/continuous.m3u8";
 assert.ok(html.includes('data-hls="'+expectedHls+'"'),"Broken HLS data link "+r.id);
 assert.ok(html.includes('/audio/'+r.id+'.mp3'),"GitHub MP3 remains referenced "+r.id);
}
const player=fs.readFileSync("index.html","utf8");
for(const id of keep)assert.ok(player.includes('"'+id+'"'),"Critical fallback missing in player: "+id);
assert.ok(player.includes("hasGitHubHLS?"));
assert.ok(player.includes('audio_origin=github'));
assert.ok(player.includes("https://media.whitenoisechoir.com/"));
assert.equal((fs.readFileSync("sitemap.xml","utf8").match(/<loc>/g)||[]).length,18);
const bytes=tracked.reduce((n,p)=>n+fs.statSync(p).size,0);
assert.ok(bytes<600000000,"HEAD tree unexpectedly large "+bytes);
assert.ok(bytes>500000000,"Critical GitHub MP3s unexpectedly missing "+bytes);
console.log("R2_BALANCED_PRUNE_LAYOUT_PASS "+JSON.stringify({
 sources:ids.size,GH_HLS_BackupSources:keep.size,
 R2_Only_HLS_Sources:ids.size-keep.size,
 retired_files:missing.length,retired_bytes:reclaimed,
 retained_HLS_files:preserved.length,retained_HLS_bytes:84341263,
 approved_MP3_preserved:35,repo_files:tracked.length,repo_tree_bytes:bytes,
 original_GitHub_MP3_path_protected:true,SEO_sitemap_urls:18
}));
