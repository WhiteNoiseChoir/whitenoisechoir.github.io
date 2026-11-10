#!/usr/bin/env node
"use strict";
// Real Chromium browser test with a short local WAV mock: does not change remote
// R2 assets or the original 10-minute MP3 recordings.
const {chromium}=require("playwright");
const fs=require("node:fs"),assert=require("node:assert/strict");
function wav(seconds=1.25,sampleRate=22050){
 const count=Math.floor(seconds*sampleRate),b=Buffer.alloc(44+count*2);
 b.write("RIFF",0);b.writeUInt32LE(b.length-8,4);b.write("WAVEfmt ",8);
 b.writeUInt32LE(16,16);b.writeUInt16LE(1,20);b.writeUInt16LE(1,22);
 b.writeUInt32LE(sampleRate,24);b.writeUInt32LE(sampleRate*2,28);
 b.writeUInt16LE(2,32);b.writeUInt16LE(16,34);
 b.write("data",36);b.writeUInt32LE(count*2,40);
 for(let i=0;i<count;i++)b.writeInt16LE(Math.round(Math.sin(i*2*Math.PI*440/sampleRate)*5000),44+2*i);
 return b;
}
(async()=>{
 const binary=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(f=>fs.existsSync(f));
 const browser=await chromium.launch({headless:true,...(binary?{executablePath:binary}:{}),args:["--no-sandbox","--autoplay-policy=no-user-gesture-required"]});
 const page=await browser.newPage({viewport:{width:390,height:844}});
 const errors=[];
 page.on("pageerror",e=>errors.push(String(e)));
 try{
  const sound=wav();
  await page.route(/^https:\/\/media\.whitenoisechoir\.com\/review\/c6b-20261110\/SND-00(?:39|40)-(?:balanced|raw)\.mp3$/,async route=>{
   await route.fulfill({status:200,contentType:"audio/wav",body:sound,
    headers:{"Accept-Ranges":"bytes","Access-Control-Allow-Origin":"*","Cache-Control":"no-store"}});
  });
  await page.goto("http://127.0.0.1:8787/signature/c6b-online-review/",{waitUntil:"domcontentloaded"});
  assert.equal(await page.locator("#loop").isChecked(),true,"Review loop must default ON");
  assert.equal(await page.locator("#player").getAttribute("loop"),"","Native HTML audio loop attribute required");
  assert.equal(await page.locator("#player").evaluate(a=>a.loop),true);
  await page.waitForFunction(()=>Number.isFinite(document.querySelector("#player").duration),{timeout:10000});
  await page.evaluate(()=>{
   window.__c6bLoops=0;
   const a=document.querySelector("#player");let last=0;
   a.addEventListener("timeupdate",()=>{
    if(last>0.7 && a.currentTime<0.3)window.__c6bLoops++;
    last=a.currentTime;
   });
  });
  await page.locator("#listen").click();
  await page.waitForFunction(()=>window.__c6bLoops>=1,null,{timeout:12000});
  assert.equal(await page.locator("#player").evaluate(a=>a.paused),false,"Audio must continue after crossing the end");
  await page.locator("#loop").uncheck();
  assert.equal(await page.locator("#player").evaluate(a=>a.loop),false,"Explicit opt-out must disable native looping");
  await page.locator("#restart").click();
  await page.waitForFunction(()=>document.querySelector("#player").ended===true,null,{timeout:10000});
  assert.equal(await page.locator("#player").evaluate(a=>a.paused),true,"Opted-out player must stop at end");
  await page.locator("#track").selectOption("SND-0040-raw");
  assert.equal(await page.locator("#player").evaluate(a=>a.loop),false,"User loop choice must persist on track switch");
  await page.locator("#loop").check();
  assert.equal(await page.locator("#player").evaluate(a=>a.loop),true,"User can re-enable looping");
  for(const width of [320,390,768]){
   await page.setViewportSize({width,height:844});
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
   assert.ok(overflow<=2,"Horizontal overflow at "+width+": "+overflow);
  }
  assert.deepEqual(errors,[],"Browser JavaScript errors");
  console.log("C6B_AUTO_LOOP_BROWSER_PASS: 1.25s mock crosses seam and stays playing; OFF stops; source change preserves setting; 320/390/768 mobile-safe");
 }finally{await browser.close()}
})().catch(e=>{console.error(e.stack||e);process.exitCode=1});
