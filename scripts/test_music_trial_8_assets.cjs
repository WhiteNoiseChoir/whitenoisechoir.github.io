#!/usr/bin/env node
// Safe non-browser regression: append-only catalog, private 8-source 10-minute trial.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const read = p => fs.readFileSync(path.join(root,p),'utf8');
const musicTrialSlug = 'music-eight-source-preview-20261113';
const sandbox = {};
const entries = vm.runInNewContext(read('studio-catalog.js') + '; studioPublishedAssets',sandbox);
assert(Array.isArray(entries), 'Studio assets script must evaluate');
assert.equal(entries.filter(x => x.group === 'music').length,8);
const sha = new Set();
for (const a of entries.filter(x => x.group === 'music')) {
  assert(/^asset-library\/raw\/sha256\/[a-f0-9]{2}\/[a-f0-9]{64}\.(?:mp3|ogg|oga)$/i.test(a.key));
  assert.equal(a.sha256, /\/([a-f0-9]{64})\.[a-z]+$/i.exec(a.key)[1]);
  assert(a.assetStatus === 'STORED_R2_TECHNICAL_PASS_LISTENING_PENDING');
  assert.equal(a.publicationApproved,false);
  assert(/^CC-BY-(?:3\.0|4\.0)$/.test(a.license));
  assert(!sha.has(a.sha256), 'Duplicate music source');
  sha.add(a.sha256);
}
const trials = JSON.parse(read('data/studio-trials.json'));
const row = trials.find(t => t.slug === musicTrialSlug);
assert(row && row.project);
assert.equal(row.project.length,600);
assert.equal(row.project.tracks.length,13);
assert.equal(new Set(row.project.tracks.map(t=>t.assetRef)).size,8);
for (const t of row.project.tracks) {
  assert(sha.has(t.assetRef.replace(/^r2-/,'')), 'Missing asset ref');
  assert(t.gain>0 && t.gain<=1);
  assert(t.start>=0 && t.start+t.duration<=600);
  assert(t.duration>0 && t.fadeIn>=0 && t.fadeOut>=0);
}
const page = read('vi/'+musicTrialSlug+'/index.html');
assert(page.includes('id="studio-trial"'));
assert(page.includes('noindex,nofollow'));
assert(page.includes('Bản phối thử nội bộ'));
const raw = /<script type="application\/json" id="studio-trial">([^]*?)<\/script>/.exec(page)?.[1];
assert(raw, 'Missing embedded project');
const embedded = JSON.parse(raw);
assert.equal(embedded.slug,musicTrialSlug);
assert.deepEqual(JSON.parse(JSON.stringify(embedded.project)),row.project);
assert(!JSON.stringify(JSON.parse(read('data/published-mixes.json'))).includes(musicTrialSlug));
assert(read('studio-ui.js').includes("music: studioEnglish ? 'Music instruments'"));
console.log('MUSIC_TRIAL_QA_PASS',JSON.stringify({
  unique_music_assets:sha.size,track_layers:row.project.tracks.length,
  length_seconds:row.project.length,private_draft:true,
  production_publication:false,source_recheck_not_claimed:true
}));
