import assert from 'node:assert/strict';
import {validateMusicEntry,selectMusicRows,registerMusicRows} from '../studio-private-music-optin.mjs';

const sha='9756ade3d2f95a353cc82d5bd0cbad0ce450cada5bc6f1aca09192255e80254f';
const entry={
  sha256:sha, assetRef:'r2-'+sha,
  r2_bucket:'wnc-music-private',
  r2_key:`internal/licensed-music/v1/sha256/${sha.slice(0,2)}/${sha}.mp3`,
  name:'Relaxing Piano Music',creator:'Clavier-Music',group:'music',
  source_url:'https://pixabay.com/music/modern-classical-relaxing-piano-music-248868/',
  download_origin:'Pixabay',license:'Pixabay Content License',
  license_evidence_url:'https://pixabay.com/service/license-summary/',
  license_review:'PENDING_HUMAN_PUBLICATION_REVIEW',
  attribution:'Clavier-Music – Relaxing Piano Music (Pixabay)',
  duration_seconds:127.272,technical_status:'DECODED_NOT_LISTENING_APPROVED',
  playback_status:'PRIVATE_AUTH_GATEWAY_REQUIRED',studio_ready:false,
  publication_approved:false
};
const accepted=validateMusicEntry(entry);
assert(accepted,'Reviewed private Pixabay entry is recognized');
assert.equal(accepted.privateMusic,true);
assert.equal(accepted.publicationApproved,false);
assert.equal(accepted.url,`https://wnc-private-music-gateway.whitescreen-dev.workers.dev/v1/audio/${sha}`);

for(const changes of [
  {publication_approved:true}, {studio_ready:true},
  {assetRef:'r2-'+'1'.repeat(64)}, {license:'unknown'},
  {license_review:'APPROVED'}, {license_evidence_url:'https://evil.test'},
  {source_url:'https://pixabay.com.evil.test/music/x/y'},
  {technical_status:'UNVERIFIED'}
]) assert.equal(validateMusicEntry({...entry,...changes}),null,JSON.stringify(changes));

const list=selectMusicRows({
  schema:'wnc_private_music_studio_bridge_v1',visibility:'PRIVATE_R2_ONLY',
  audio_origin_exposed:false,requires_authenticated_gateway:true,
  studio_ready:0,publication_approved:0,entries:[entry,entry]
});
assert.equal(list.length,1,'Duplicate assetRef deduplicated');

const assets=[{id:'r2-'+sha,name:'Nguồn chưa mở khóa',duration:0,pending:true,group:'other'}];
const rawAssetIndex=new Map([['r2-'+sha,0]]);
let changes=0;
const hooks={assets,rawAssetIndex,rebuildCatalog(){changes++},refreshLibraryGroups(){},renderLibrary(){},render(){}};
assert.equal(registerMusicRows(list,hooks),1,'Existing placeholder must be upgraded');
assert.equal(assets.length,1,'No duplicate track');
assert.equal(assets[0].name,'Relaxing Piano Music');
assert.equal(assets[0].pending,undefined);
assert.equal(changes,1);
assert.equal(registerMusicRows(list,hooks),0,'Do not overwrite real entries');
console.log('Private Music contract tests passed');
