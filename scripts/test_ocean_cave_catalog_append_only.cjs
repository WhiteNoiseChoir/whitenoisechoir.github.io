'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const file=fs.readFileSync('studio-catalog.js','utf8');
const assets=vm.runInNewContext(file+'\nstudioPublishedAssets');
assert.equal(assets.length,103,'98 preexisting + 5 new assets');
assert.equal(assets[0].key,'audio/white-noise.mp3');
assert.equal(assets[97].key,'asset-library/raw/sha256/d8/d854e476e3272b35701dd677d3421d44f1cd650fe48833d1726c11c78f8aeaf7.mp3');
const expected=[
'247c0ef181c8ba8d190a6194f6ea02d9defb23b70194c52c7f9187b5b7b1cc61',
'fcfca178eca2eac536e8c2a4ed5cf8096e44c921acd587047b3d9f1d7845435c',
'53b5c28c0edc36f049e77e65f2cf8a86135103328c44c1507c416e6469d18096',
'fc795f95f352b354867d69a587daecb8815334e28e3b56a7798c5f3005349054',
'3c490e736365fdd617ce8405470d8878fc6146d9a8dba448d622addb01cfff3b'
];
const keys=new Set();
for(const asset of assets){
  if(!asset.key)continue;
  assert(!keys.has(asset.key),'Duplicate catalog audio key: '+asset.key);
  keys.add(asset.key);
}
for(let i=0;i<5;i++){
  const a=assets[98+i],sha=expected[i];
  assert.equal(a.sha256,sha);
  assert.equal(a.key,'asset-library/raw/sha256/'+sha.slice(0,2)+'/'+sha+'.flac');
  assert.equal(a.license,'CC0-1.0');
  assert.equal(a.publicationApproved,false);
  assert.match(a.assetStatus,/LISTENING_QA_PENDING/);
  assert.match(a.source,/^https:\/\/opengameart.org\/content\//);
  assert(a.duration>1&&a.duration<25);
}
console.log('OCEAN_CAVE_CATALOG_PASS 98 legacy stable + 5 verified-R2-keys licensed audio pending listening QA');
