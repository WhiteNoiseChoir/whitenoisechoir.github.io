#!/usr/bin/env node
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const trials=JSON.parse(fs.readFileSync('data/studio-trials.json','utf8'));
const v1=trials.find(t=>t.slug==='the-ocean-beneath-the-ice-v1');
const v2=trials.find(t=>t.slug==='the-ocean-beneath-the-ice-v2');
assert(v1?.project && v2?.project);
const orig=vm.runInNewContext(fs.readFileSync('studio-catalog.js','utf8')+'; studioPublishedAssets',{});
const known=new Map(orig.map(x=>[x.sha256 && 'r2-'+x.sha256,x]));
const bad='r2-b621edf7701897ae4d1c4242ee78ea028e82f8cd79d42063bfc1e4bffe3dedfb';
assert.equal(v2.project.length,600);
assert.equal(v2.project.tracks.length,10);
assert.equal(new Set(v2.project.tracks.map(t=>t.assetRef)).size,8);
for(const track of v2.project.tracks){
  const asset=known.get(track.assetRef);
  assert(asset,'Source absent from append-only Studio catalog: '+track.label);
  assert.notEqual(track.assetRef,bad,'V1 EncodingError source was reused in V2');
  assert(track.gain>=0.1&&track.gain<=1,'Gain below 10% / out of range');
  assert(track.start>=0&&track.duration>0&&track.start+track.duration<=600);
  assert(track.fadeIn>=0&&track.fadeOut>=0&&track.fadeIn+track.fadeOut<track.duration);
  if(!track.loop) assert((track.offset||0)+track.duration<=asset.duration+.001,'Out of source duration: '+track.label);
}
const route='vi/the-ocean-beneath-the-ice-v2/index.html';
const html=fs.readFileSync(route,'utf8');
const row=JSON.parse(html.match(/<script type="application\/json" id="studio-trial">([\s\S]*?)<\/script>/)?.[1]||'null');
assert.equal(row.slug,v2.slug);
assert.equal(JSON.stringify(row.project),JSON.stringify(v2.project));
assert(html.includes('noindex,nofollow')&&!html.includes(bad));
assert(trials.some(x=>x.slug==='cabin-rain-night-v3') && trials.some(x=>x.slug==='music-eight-source-preview-20261113'));
assert(!JSON.stringify(JSON.parse(fs.readFileSync('data/published-mixes.json','utf8'))).includes('the-ocean-beneath-the-ice-v2'));
console.log('OCEAN_ICE_V2_STATIC_QA_PASS',JSON.stringify({sources:8,tracks:10,seconds:600,excludedBrokenWav:true,allGainAtLeast10Percent:true,oldTrialsPreserved:true,liveBrowserPlaybackVerified:false}));
