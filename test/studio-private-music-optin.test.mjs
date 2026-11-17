import test from "node:test";
import assert from "node:assert/strict";
import {validateMusicEntry,selectMusicRows,retrievePrivateMusic,registerMusicRows,MUSIC_GATEWAY_ORIGIN}
  from "../studio-private-music-optin.mjs";

const SHA="a".repeat(64);
const TRACK={
  sha256:SHA,assetRef:"r2-"+SHA,r2_bucket:"wnc-music-private",
  r2_key:`internal/licensed-music/v1/sha256/aa/${SHA}.mp3`,
  group:"music",name:"Quiet Piano",creator:"Scott Buckley",source_url:"https://www.scottbuckley.com.au/library/piano/",
  license:"CC BY 4.0",attribution:"Scott Buckley · CC BY 4.0",duration_seconds:211,
  technical_status:"MEASURED_NOT_LISTENING_APPROVED",
  playback_status:"PRIVATE_AUTH_GATEWAY_REQUIRED",studio_ready:false,publication_approved:false,
  integrated_lufs:-15.5,true_peak_dbtp:-1.06
};
const SNAP={
  schema:"wnc_private_music_studio_bridge_v1",visibility:"PRIVATE_R2_ONLY",
  audio_origin_exposed:false,requires_authenticated_gateway:true,studio_ready:0,
  publication_approved:0,entries:[TRACK]
};
const valid=()=>structuredClone(SNAP);

test("disabled loader cannot network and returns zero entries",async()=>{
  let calls=0;
  const result=await retrievePrivateMusic({enabled:false,pageOrigin:"https://whitenoisechoir.com",
    fetcher:async()=>{calls++;throw Error("must not fetch")}});
  assert.equal(result.status,"DISABLED");assert.equal(calls,0);
});
test("foreign origin even with enabled flag cannot network",async()=>{
  let calls=0;
  const result=await retrievePrivateMusic({enabled:true,pageOrigin:"https://attacker.example",
    fetcher:async()=>{calls++;throw Error("must not fetch")}});
  assert.equal(result.status,"DISABLED");assert.equal(calls,0);
});
test("catalog requests only protected gateway with credentials and no redirect",async()=>{
  const calls=[];
  const res=await retrievePrivateMusic({enabled:true,pageOrigin:"https://whitenoisechoir.com",
    fetcher:async(url,options)=>{
      calls.push({url,options});
      return {ok:true,headers:{get:()=> "application/json"},json:async()=>valid()};
    }});
  assert.equal(res.rows.length,1);
  assert.equal(calls[0].url,MUSIC_GATEWAY_ORIGIN+"/v1/catalog");
  assert.equal(calls[0].options.credentials,"include");
  assert.equal(calls[0].options.redirect,"error");
  assert.equal(res.rows[0].url,MUSIC_GATEWAY_ORIGIN+"/v1/audio/"+SHA);
});
test("Access refusal never mutates data",async()=>{
  await assert.rejects(retrievePrivateMusic({enabled:true,pageOrigin:"https://whitenoisechoir.com",
    fetcher:async()=>({ok:false,status:403})}),/access/i);
});
test("login HTML is not accepted as Music JSON",async()=>{
  await assert.rejects(retrievePrivateMusic({enabled:true,pageOrigin:"https://whitenoisechoir.com",
    fetcher:async()=>({ok:true,headers:{get:()=> "text/html"}})}),/content/);
});
test("missing schema cannot be used",()=>assert.throws(()=>selectMusicRows({...valid(),schema:"unexpected"})));
test("public snapshot cannot be used",()=>assert.throws(()=>selectMusicRows({...valid(),visibility:"PUBLIC"})));
test("wrong private storage bucket rejected",()=>{
  const s=valid();s.entries[0].r2_bucket="whitenoisechoir-media";
  assert.equal(selectMusicRows(s).length,0);
});
test("SHA/key mismatch rejected",()=>{
  const s=valid();s.entries[0].r2_key="internal/licensed-music/v1/sha256/cc/other.mp3";
  assert.equal(selectMusicRows(s).length,0);
});
test("noncommercial rights never displayed",()=>{
  const s=valid();s.entries[0].license="CC BY-NC 4.0";
  assert.equal(selectMusicRows(s).length,0);
});
test("publication permission not inferred",()=>{
  const s=valid();s.entries[0].studio_ready=true;
  assert.equal(selectMusicRows(s).length,0);
});
test("duplicate SHA rows do not duplicate assets",()=>{
  const s=valid();s.entries=[TRACK,TRACK];assert.equal(selectMusicRows(s).length,1);
});
test("approved catalog has technical status, not sleep clearance",()=>{
  const a=selectMusicRows(valid())[0];
  assert.equal(a.privateMusic,true);
  assert.equal(a.studioReady,false);assert.equal(a.publicationApproved,false);
  assert.equal(a.assetStatus,"PRIVATE_AUDITION_ONLY_NOT_STUDIO_APPROVED");
});
test("valid registration is append-only and refreshes once",()=>{
  const rows=selectMusicRows(valid()), assets=[],rawAssetIndex=new Map();let renderCalls=0;
  const reg=()=>renderCalls++;
  const ctx={assets,rawAssetIndex,rebuildCatalog:reg,refreshLibraryGroups:reg,renderLibrary:reg,render:reg};
  assert.equal(registerMusicRows(rows,ctx),1);
  assert.equal(registerMusicRows(rows,ctx),0);
  assert.equal(assets.length,1);assert.equal(renderCalls,4);
  assert.equal(assets[0].id,"r2-"+SHA);
});
test("unverified local row cannot masquerade as approved asset",()=>{
  const rows=[{...selectMusicRows(valid())[0],license:"CC BY-NC 4.0"}];
  const assets=[],rawAssetIndex=new Map();
  assert.equal(registerMusicRows(rows,{assets,rawAssetIndex}),0);
  assert.equal(assets.length,0);
});
test("existing Nature asset never overwritten on SHA collision",()=>{
  const rows=selectMusicRows(valid());
  const orig={id:"r2-"+SHA,name:"Other original asset"};
  const assets=[orig],rawAssetIndex=new Map([[orig.id,0]]);
  assert.equal(registerMusicRows(rows,{assets,rawAssetIndex}),0);
  assert.equal(assets[0],orig);
});
