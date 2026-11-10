#!/usr/bin/env node
"use strict";
// Browser verifies the real C6C UI with a 1.25s test WAV replacing remote MP3 URLs.
// It must cross at least one automatic loop, stop when OFF, preserve choices on switch.
const {chromium}=require("playwright"),assert=require("node:assert/strict"),fs=require("node:fs");
function wav(){
 const rate=22050,n=Math.round(rate*1.25),b=Buffer.alloc(44+n*2);
 b.write("RIFF",0);b.writeUInt32LE(b.length-8,4);b.write("WAVEfmt ",8);
 b.writeUInt32LE(16,16);b.writeUInt16LE(1,20);b.writeUInt16LE(1,22);
 b.writeUInt32LE(rate,24);b.writeUInt32LE(rate*2,28);
 b.writeUInt16LE(2,32);b.writeUInt16LE(16,34);
 b.write("data",36);b.writeUInt32LE(n*2,40);
 for(let i=0;i<n;i++)b.writeInt16LE(Math.round(Math.sin(i*2*Math.PI*440/rate)*4000),44+i*2);
 return b;
}
(async()=>{
 const binary=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(fs.existsSync);
 const browser=await chromium.launch({headless:true,...(binary?{executablePath:binary}:{}),args:["--no-sandbox","--autoplay-policy=no-user-gesture-required"]});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];
  page.on("pageerror",e=>errors.push(String(e)));
  const fixture=wav();
  await page.route(/^https:\/\/media\.whitenoisechoir\.com\/review\/c6c-20261110\/SND-\d{4}\.mp3$/,route=>route.fulfill({status:200,contentType:"audio/wav",body:fixture,headers:{"Accept-Ranges":"bytes","Access-Control-Allow-Origin":"*"}}));
  await page.goto("http://127.0.0.1:8787/signature/c6c-online-review/",{waitUntil:"domcontentloaded"});
  assert.equal(await page.locator("#sound option").count(),10);
  assert.equal(await page.locator("#loop").isChecked(),true);
  assert.equal(await page.locator("#audio").evaluate(a=>a.loop),true);
  await page.waitForFunction(()=>Number.isFinite(document.querySelector("#audio").duration),null,{timeout:15000});
  await page.evaluate(()=>{
   window.__cycles=0;const a=document.querySelector("#audio");let prior=0;
   a.addEventListener("timeupdate",()=>{if(prior>0.7&&a.currentTime<0.3)window.__cycles++;prior=a.currentTime;});
  });
  await page.locator("#play").click();
  await page.waitForFunction(()=>window.__cycles>0,null,{timeout:15000});
  assert.equal(await page.locator("#audio").evaluate(a=>a.paused),false,"Audio must not stop at end when loop is ON");
  await page.locator("#loop").uncheck();
  assert.equal(await page.locator("#audio").evaluate(a=>a.loop),false);
  await page.locator("#restart").click();
  await page.waitForFunction(()=>document.querySelector("#audio").ended===true,null,{timeout:15000});
  assert.equal(await page.locator("#audio").evaluate(a=>a.paused),true);
  await page.locator("#sound").selectOption("SND-0083");
  assert.equal(await page.locator("#audio").evaluate(a=>a.loop),false,"Explicit user OFF persisted");
  await page.locator("#loop").check();
  assert.equal(await page.locator("#audio").evaluate(a=>a.loop),true);
  for(const width of [320,390,768]){
   await page.setViewportSize({width,height:844});
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
   assert.ok(overflow<=2,"Mobile overflow width "+width+"px: "+overflow);
  }
  assert.deepEqual(errors,[]);
  console.log("C6C_TEN_SOUND_BROWSER_PASS: ten choices, native loop after simulated end, manual OFF stops, switch remembers OFF, responsive 320/390/768");
 }finally{await browser.close()}
})().catch(e=>{console.error(e.stack||e);process.exitCode=1});
