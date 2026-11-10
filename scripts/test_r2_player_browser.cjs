#!/usr/bin/env node
"use strict";
/** Browser failover for balanced R2: eight core GH HLS, 27 R2-only HLS and
 * all 35 original GH MP3 backups, including ?audio_origin=github override.
 */
const {chromium}=require("playwright"),fs=require("node:fs"),assert=require("node:assert/strict");
const BASE="http://127.0.0.1:8787";
(async()=>{
 const binary=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(p=>fs.existsSync(p));
 const browser=await chromium.launch({headless:true,executablePath:binary,args:["--no-sandbox","--autoplay-policy=no-user-gesture-required"]});
 try{
  const cases=[
   {name:"core-r2-outage",id:"white-noise",url:"/",contact:true,localHLS:true,blockLocal:false},
   {name:"core-both-hls-out",id:"white-noise",url:"/",contact:true,localHLS:false,blockLocal:true},
   {name:"core-emergency-gh",id:"white-noise",url:"/?audio_origin=github",contact:false,localHLS:true,blockLocal:false},
   {name:"retired-blue-r2-outage",id:"blue-noise",url:"/",contact:true,localHLS:false,blockLocal:false},
   {name:"retired-rain-r2-outage",id:"rain-leaves-real",url:"/",contact:true,localHLS:false,blockLocal:false},
   {name:"retired-blue-emergency-gh",id:"blue-noise",url:"/?audio_origin=github",contact:false,localHLS:false,blockLocal:false}
  ];
  for(const t of cases){
   const page=await browser.newPage({viewport:{width:390,height:800},reducedMotion:"reduce"});
   const errors=[],requests=[],localHLSRequests=[];
   page.on("pageerror",e=>errors.push(String(e)));
   page.on("request",req=>{
    const url=req.url();
    if(url.startsWith("https://media.whitenoisechoir.com/"))requests.push(url);
    if(url.includes("/audio/continuous/"+t.id+"/continuous.m3u8")&&!url.startsWith("https://media."))localHLSRequests.push(url);
   });
   await page.addInitScript(()=>{
    const Native=window.Audio;
    window.__audioInstances=[];
    window.Audio=function(){const a=new Native();window.__audioInstances.push(a);return a;};
    window.Audio.prototype=Native.prototype;
   });
   await page.route("https://media.whitenoisechoir.com/**",route=>route.abort("failed"));
   if(t.blockLocal)await page.route("**/audio/continuous/"+t.id+"/continuous.m3u8*",route=>route.abort("failed"));
   await page.goto(BASE+t.url,{waitUntil:"domcontentloaded"});
   await page.waitForFunction(()=>!!window.WNCBridge);
   assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),false,"No autoplay on page load");
   await page.evaluate(id=>window.WNCBridge.play([id],id),t.id);
   const expected=t.localHLS?"/audio/continuous/"+t.id+"/continuous.m3u8":"/audio/"+t.id+".mp3";
   await page.waitForFunction(p=>{
    const a=window.__audioInstances[0];
    return !!a&&a.src.startsWith(location.origin+p);
   },expected,{timeout:18000});
   const actual=await page.evaluate(()=>({
    src:window.__audioInstances[0].src,
    isPlaying:window.WNCBridge.snapshot().playing,
    paused:window.__audioInstances[0].paused,
    sounds:window.WNCBridge.rows.length,
    recipes:window.WNCBridge.recipes.length
   }));
   assert.equal(actual.sounds,45);assert.equal(actual.recipes,45);
   assert.ok(actual.src.startsWith(BASE+expected),t.name+" wrong backup "+actual.src);
   assert.equal(actual.isPlaying,true,t.name+" playback stopped");
   assert.equal(actual.paused,false,t.name+" media paused");
   assert.equal(requests.length>0,t.contact,t.name+" unexpected R2 request routing");
   if(!t.localHLS&&!t.blockLocal)
    assert.equal(localHLSRequests.length,0,t.name+" must NEVER request retired GH HLS");
   else
    assert.ok(localHLSRequests.length>0,t.name+" should attempt native GH HLS backup");
   assert.equal(errors.length,0,t.name+" JS errors "+errors.join(";"));
   await page.evaluate(()=>window.WNCBridge.stop());
   assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),false);
   console.log("R2_BALANCED_BROWSER_FALLBACK_PASS",JSON.stringify({scenario:t.name,id:t.id,
    gh_hls:t.localHLS,remote_attempts:requests.length,local_hls_requests:localHLSRequests.length,
    src:actual.src,playing:actual.isPlaying,no_autoplay:true}));
   await page.close();
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
