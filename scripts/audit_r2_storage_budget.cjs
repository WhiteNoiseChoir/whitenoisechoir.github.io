#!/usr/bin/env node
"use strict";
/** Exact approved-HLS size and source-identity audit for future R2-backed slimming.
 * Non-destructive. No production files are removed by this script.
 */
const fs=require("node:fs"),cp=require("node:child_process"),crypto=require("node:crypto"),assert=require("node:assert/strict");
const ledger=JSON.parse(fs.readFileSync("audits/r2-hls-immutable-source-inventory.json","utf8"));
const hls=JSON.parse(fs.readFileSync("audio/continuous/manifest.json","utf8"));
const cat=JSON.parse(fs.readFileSync("catalog/library.json","utf8"));
const files=cp.execFileSync("git",["ls-files","-z"],{maxBuffer:10000000}).toString().split("\0").filter(Boolean);
const gitBlobSha=p=>{
 const bytes=fs.readFileSync(p);
 return crypto.createHash("sha1").update(Buffer.from("blob "+bytes.length+"\0")).update(bytes).digest("hex");
};
const repoPaths=new Set(files);
const sourceIds=new Set(hls.records.map(x=>x.id));
assert.equal(cat.sounds.length,35);
assert.equal(sourceIds.size,35);
assert.deepEqual([...sourceIds].sort(),[...new Set(ledger.files.map(x=>x.path.split("/")[2]))].sort());
assert.equal(hls.applies_to.length,35);
assert.equal(ledger.files.length,ledger.files_count);
assert.equal(ledger.files_count,360);
assert.equal(ledger.retirable_bytes,514374326);
assert.equal(ledger.source_count,35);
assert.equal(ledger.source_commit,"6703736c3ea9ae57d611628d2d2fd2ff99fdf7d8");
const expectedPaths=new Set();
let archivedBytes=0,playlistCount=0,segmentCount=0;
for(const entry of ledger.files){
 assert.match(entry.path,/^audio\/continuous\/[a-z0-9-]+\/(?:continuous\.m3u8|part_\d{3}\.ts)$/);
 assert.ok(sourceIds.has(entry.path.split("/")[2]),"Unapproved stream in prune ledger: "+entry.path);
 assert.ok(!expectedPaths.has(entry.path),"Duplicate path "+entry.path);
 expectedPaths.add(entry.path);
 assert.equal(gitBlobSha(entry.path),entry.git_blob_sha1,"HLS source changed: "+entry.path);
 assert.equal(fs.statSync(entry.path).size,entry.size,"HLS byte size changed: "+entry.path);
 archivedBytes+=entry.size;
 if(entry.path.endsWith(".m3u8"))playlistCount++;
 else segmentCount++;
}
assert.equal(playlistCount,35);
assert.equal(segmentCount,325);
assert.equal(archivedBytes,ledger.retirable_bytes);
const liveHls=files.filter(p=>p.startsWith("audio/continuous/")&&sourceIds.has(p.split("/")[2]));
assert.equal(liveHls.length,ledger.files_count,"Unexpected new approved local HLS files");
assert.ok(liveHls.every(p=>expectedPaths.has(p)));
const sourceBytes=files.reduce((n,p)=>n+fs.statSync(p).size,0);
const masterFiles=files.filter(p=>/^audio\/[^/]+\.mp3$/.test(p));
const mastersSize=masterFiles.reduce((n,p)=>n+fs.statSync(p).size,0);
for(const row of hls.records){
 assert.ok(repoPaths.has(row.master_file),"Backup MP3 file missing "+row.id);
 assert.ok(repoPaths.has(row.playlist_file),"Approved source HLS missing "+row.id);
 assert.equal(gitBlobSha(row.playlist_file),ledger.files.find(x=>x.path===row.playlist_file)?.git_blob_sha1);
}
const base=fs.readFileSync("index.html","utf8");
assert.match(base,/https:\/\/media\.whitenoisechoir\.com\//);
assert.match(base,/audio_origin=github/);
const summary={
 status:"R2_SOURCE_SNAPSHOT_PASS",project:"WhiteNoiseChoir",
 sources:sourceIds.size,hls_playlist_files:playlistCount,hls_segment_files:segmentCount,
 hls_source_bytes:archivedBytes,master_mp3_files:masterFiles.length,master_mp3_bytes:mastersSize,
 tracked_files:files.length,tracked_bytes:sourceBytes,
 recommended_pages_limit_bytes:1000000000,
 current_headroom_bytes:1000000000-sourceBytes,
 theoretical_after_archiving_35_hls_bytes:sourceBytes-archivedBytes,
 theoretical_after_archiving_35_hls_percent_of_current:Number(((sourceBytes-archivedBytes)/sourceBytes*100).toFixed(2)),
 original_github_hls_fallback_must_be_replaced_before_deleting:true,
 no_deletion_performed:true,
 pages_artifact_size_not_proven:true
};
assert.ok(sourceBytes<1000000000,"GitHub tracked tree exceeds the documented 1GB limit");
assert.ok(sourceBytes-archivedBytes>0);
console.log("R2_STORAGE_PRUNE_DRY_RUN",JSON.stringify(summary));
