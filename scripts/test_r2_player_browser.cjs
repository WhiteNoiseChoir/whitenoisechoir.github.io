#!/usr/bin/env node
"use strict";
/* Exercise the actual browser player under simulated R2 503, then emergency rollback.
 * Production source files and their original relative URLs must remain usable.
 */
const {chromium}=require("playwright"),fs=require("node:fs"),assert=require("node:assert/strict");
const BASE="http://127.0.0.1:8787";
(async()=>{
 const binary=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(p=>fs.existsSync(p));
 const browser=await chromium.launch({headless:true,executablePath:binary,args:["--no-sandbox","--autoplay-policy=no-user-gesture-required"]});
 try{
  for(const [name,path,shouldContactR2] of [
   ["r2-outage","/",true],
   ["emergency-rollback","/?audio_origin=github",false]
  ]){
   const page=await browser.newPage({viewport:{width:390,height:800},reducedMotion:"reduce"});
   const errors=[],requests=[];
   page.on("pageerror",e=>errors.push(String(e)));
   page.on("request",req=>{if(req.url().startsWith("https://media.whitenoisechoir.com/"))requests.push(req.url())});
   await page.addInitScript(()=>{
    const Native=window.Audio;
    window.__audioInstances=[];
    window.Audio=function(){const a=new Native();window.__audioInstances.push(a);return a;};
    window.Audio.prototype=Native.prototype;
   });
   await page.route("https://media.whitenoisechoir.com/**",route=>route.abort("failed"));
   await page.goto(BASE+path,{waitUntil:"domcontentloaded"});
   await page.waitForFunction(()=>!!window.WNCBridge);
   assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),false,"No autoplay on page load");
   const result=await page.evaluate(()=>window.WNCBridge.play(["white-noise"],"White Noise"));
   console.log("R2_BROWSER_DIAGNOSTIC",JSON.stringify({
     scenario:name,requests:requests.length,
     state:await page.evaluate(()=>({
       tracks:window.__audioInstances?.map(a=>({src:a.src,paused:a.paused,error:a.error?.code||null})),
       playing:window.WNCBridge?.snapshot()?.playing,
       status:document.querySelector("#status")?.textContent
     })),
     errors
   }));
   await page.waitForFunction(()=>!!window.__audioInstances[0]&&window.__audioInstances[0].src.includes("/audio/white-noise.mp3"),null,{timeout:18000});
   const actual=await page.evaluate(()=>({
      src:window.__audioInstances[0].src,
      isPlaying:window.WNCBridge.snapshot().playing,
      paused:window.__audioInstances[0].paused,
      sounds:window.WNCBridge.rows.length,
      recipes:window.WNCBridge.recipes.length,
   }));
   assert.equal(actual.sounds,35);
   assert.equal(actual.recipes,45);
   assert.ok(actual.src.startsWith(BASE+"/audio/white-noise.mp3"),name+" must use GitHub as verified audio backup");
   assert.equal(actual.isPlaying,true,name+" should continue playing despite simulated R2 failure");
   assert.equal(actual.paused,false,name+" backing player is paused");
   assert.equal(requests.length>0,shouldContactR2,name+" R2 request routing incorrect");
   assert.equal(errors.length,0,name+" browser JS errors: "+errors.join(";"));
   await page.evaluate(()=>window.WNCBridge.stop());
   assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),false);
   console.log("R2_BROWSER_FALLBACK_PASS",JSON.stringify({scenario:name,attempted_R2:requests.length,src:actual.src,playing_after_fallback:actual.isPlaying,no_autoplay:true}));
   await page.close();
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
