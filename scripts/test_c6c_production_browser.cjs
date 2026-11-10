#!/usr/bin/env node
"use strict";
// End-to-end browser QA for newly approved C6C production integration.
// Serves short synthetic PCM/WAV under intercepts; never mislabels fixture as 600s master.
const {chromium}=require("playwright"),assert=require("node:assert/strict"),fs=require("node:fs");
const BASE="http://127.0.0.1:8787";
function wav(){
 const sr=22050,n=Math.floor(sr*1.22),p=Buffer.alloc(44+n*2);
 p.write("RIFF");p.writeUInt32LE(p.length-8,4);p.write("WAVEfmt ",8);
 p.writeUInt32LE(16,16);p.writeUInt16LE(1,20);p.writeUInt16LE(1,22);
 p.writeUInt32LE(sr,24);p.writeUInt32LE(sr*2,28);p.writeUInt16LE(2,32);p.writeUInt16LE(16,34);
 p.write("data",36);p.writeUInt32LE(n*2,40);
 for(let i=0;i<n;i++)p.writeInt16LE(Math.round(Math.sin(2*Math.PI*450*i/sr)*3000),44+2*i);
 return p;
}
(async()=>{
 const binary=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(x=>fs.existsSync(x));
 const browser=await chromium.launch({headless:true,...(binary?{executablePath:binary}:{}),args:["--no-sandbox","--autoplay-policy=no-user-gesture-required"]});
 const sound=wav();
 try{
  const page=await browser.newPage({viewport:{width:390,height:840}}),errors=[];
  page.on("pageerror",e=>errors.push(String(e)));
  await page.route(/^https:\/\/media\.whitenoisechoir\.com\/audio\/c6c-[a-z0-9-]+\.mp3$/,r=>r.fulfill({status:200,contentType:"audio/wav",body:sound,headers:{"Access-Control-Allow-Origin":"*"}}));
  await page.goto(BASE+"/?sound=c6c-tower-fan-synth",{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>window.WNCBridge?.rows?.length===45);
  assert.equal(await page.evaluate(()=>window.WNCBridge.recipes.length),45);
  assert.equal(await page.locator("#cards article.card").count(),45);
  assert.equal(await page.locator('#filters button').count(),6);
  assert.ok((await page.locator("#playingTitle").textContent()).includes("Tower Fan"));
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),false);
  await page.evaluate(()=>window.WNCBridge.play(["c6c-tower-fan-synth"],"Tower Fan (Synthetic)"));
  await page.waitForFunction(()=>window.WNCBridge.snapshot().playing===true,null,{timeout:15000});
  await page.waitForTimeout(1700);
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),true,"New MP3 must not stop at 10-minute boundary");
  await page.evaluate(()=>window.WNCBridge.stop());
  await page.goto(BASE+"/sounds/c6c-synthetic/?sound=c6c-vinyl-crackle-synth",{waitUntil:"domcontentloaded"});
  assert.equal(await page.locator("button[data-pick]").count(),10);
  assert.equal(await page.locator("#sound").inputValue(),"c6c-vinyl-crackle-synth");
  assert.equal(await page.locator("#audio").evaluate(a=>a.loop),true);
  await page.route("https://media.whitenoisechoir.com/audio/c6c-vinyl-crackle-synth.mp3",r=>r.fulfill({status:200,contentType:"audio/wav",body:sound}));
  await page.locator("#play").click();
  await page.waitForFunction(()=>!document.querySelector("#audio").paused,null,{timeout:15000});
  await page.waitForTimeout(1600);
  assert.equal(await page.locator("#audio").evaluate(a=>a.paused),false,"Hub MP3 should loop natively");
  await page.locator("#stop").click();
  assert.equal(await page.locator("#audio").evaluate(a=>a.paused),true);
  for(const width of [320,390,768]){
   await page.setViewportSize({width,height:844});
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
   assert.ok(overflow<=3,"Mobile horizontal overflow "+width+": "+overflow);
  }
  assert.deepEqual(errors,[]);
  console.log("C6C_APPROVED_BROWSER_PASS: 45 homepage sources, 45 presets, zero autoplay, production MP3 native loop, direct sound links, 10-source hub and mobile-responsive");
 }finally{await browser.close()}
})().catch(e=>{console.error(e.stack||e);process.exitCode=1});
