import test from "node:test";
import assert from "node:assert/strict";
import {
  validateOwnerMusicEntry, selectOwnerMusicRows,
  retrieveOwnerMusic, registerOwnerMusicRows, MUSIC_GATEWAY_ORIGIN
} from "../studio-private-music-optin.mjs";

const SHA="1".repeat(64);
const SOURCE={
  sha256:SHA,assetRef:"r2-"+SHA,r2_bucket:"wnc-music-private",
  r2_key:"internal/owner-generated/flow-music/inbox/The Warmth of a Rainy Night.mp3",
  source_object_etag:"abc12300deadbeef",source_object_size_bytes:4500000,
  name:"The Warmth of a Rainy Night",group:"music",duration_seconds:178.22,
  origin_type:"AI_GENERATED",generation_platform:"GOOGLE_FLOW_MUSIC",
  technical_status:"MEASURED_NOT_LISTENING_APPROVED",
  playback_status:"PRIVATE_AUTH_GATEWAY_REQUIRED",
  audio_semantics_verified:false,studio_ready:false,publication_approved:false
};
const META={
  schema:"wnc_owner_generated_music_gateway_v1",
  visibility:"PRIVATE_R2_ONLY",audio_origin_exposed:false,
  requires_authenticated_gateway:true,studio_ready:0,
  publication_approved:0,entries:[SOURCE]
};
test("strict owner music metadata is accepted as private audition only",()=>{
  const row=validateOwnerMusicEntry(SOURCE);
  assert.equal(row.id,"r2-"+SHA);
  assert.equal(row.url,MUSIC_GATEWAY_ORIGIN+"/v1/owner/audio/"+SHA);
  assert.equal(row.ownerGeneratedMusic,true);
  assert.equal(row.privateMusic,true);
  assert.equal(row.studioReady,false);
  assert.equal(row.publicationApproved,false);
  assert.equal(row.assetStatus,"PRIVATE_AUDITION_ONLY_NOT_PUBLICATION_APPROVED");
});
test("owner AI material is never fetched on foreign origin",async()=>{
  let calls=0;
  const result=await retrieveOwnerMusic({enabled:true,pageOrigin:"https://evil.example",fetcher:async()=>{
    calls++;throw Error("not expected");
  }});
  assert.equal(result.status,"DISABLED");assert.equal(calls,0);
});
test("owner catalog uses only credentialed Access endpoint with no redirects",async()=>{
  const calls=[];
  const result=await retrieveOwnerMusic({
    enabled:true,pageOrigin:"https://whitenoisechoir.com",
    fetcher:async(url,options)=>{
      calls.push({url,options});
      return {ok:true,headers:{get:()=> "application/json"},json:async()=>structuredClone(META)};
    }
  });
  assert.equal(calls[0].url,MUSIC_GATEWAY_ORIGIN+"/v1/owner/catalog");
  assert.equal(calls[0].options.credentials,"include");
  assert.equal(calls[0].options.redirect,"error");
  assert.equal(result.rows.length,1);
});
test("Cloudflare Access denial prevents owner registration",async()=>{
  await assert.rejects(()=>retrieveOwnerMusic({
    enabled:true,pageOrigin:"https://whitenoisechoir.com",
    fetcher:async()=>({ok:false,status:403})
  }),/Access/i);
});
test("private origin and rights gates cannot be bypassed",()=>{
  for(const patch of [
    {r2_bucket:"whitenoisechoir-media"},
    {r2_key:"internal/licensed-music/unsafe.mp3"},
    {origin_type:"LICENSED_HUMAN_MUSIC"},
    {generation_platform:"SOME_OTHER_PROVIDER"},
    {audio_semantics_verified:true},
    {studio_ready:true},
    {publication_approved:true}
  ]){
    const item={...SOURCE,...patch};
    assert.equal(validateOwnerMusicEntry(item),null);
  }
});
test("strict schema and non-public Access required",()=>{
  assert.throws(()=>selectOwnerMusicRows({...META,visibility:"PUBLIC"}));
  assert.throws(()=>selectOwnerMusicRows({...META,requires_authenticated_gateway:false}));
});
test("verified catalog appends once and does not overwrite other assets",()=>{
  const rows=selectOwnerMusicRows(META),assets=[],rawAssetIndex=new Map();
  assert.equal(registerOwnerMusicRows(rows,{assets,rawAssetIndex}),1);
  assert.equal(registerOwnerMusicRows(rows,{assets,rawAssetIndex}),0);
  assert.equal(assets.length,1);
  assert.equal(assets[0].id,"r2-"+SHA);
});
test("exact placeholder can be replaced; unrelated asset never overwritten",()=>{
  const rows=selectOwnerMusicRows(META);
  const asset={id:"r2-"+SHA,pending:true,group:"other"};
  const assets=[asset],rawAssetIndex=new Map([[asset.id,0]]);
  assert.equal(registerOwnerMusicRows(rows,{assets,rawAssetIndex}),1);
  assert.equal(assets[0].ownerGeneratedMusic,true);
  const nonowner={id:"r2-"+SHA,name:"other Nature asset"};
  const other=[nonowner];
  assert.equal(registerOwnerMusicRows(rows,{assets:other,rawAssetIndex:new Map([[nonowner.id,0]])}),0);
  assert.equal(other[0],nonowner);
});
