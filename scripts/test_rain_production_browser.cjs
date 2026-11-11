#!/usr/bin/env node
"use strict";
const {chromium}=require("playwright"),fs=require("node:fs"),assert=require("node:assert/strict");
const BASE="http://127.0.0.1:8787",ids=["light-rain-real","rain-tin-roof-real","distant-thunder-real"],slugs=["light-rain","rain-on-tin-roof","distant-thunder"];
(async()=>{
const executablePath=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(fs.existsSync);
const browser=await chromium.launch({headless:true,executablePath,args:["--no-sandbox","--autoplay-policy=no-user-gesture-required"]});
try{
 const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:"reduce"});
  // Exercise the legacy browser against its archived listing.
  await page.route(BASE+"/sounds/",route=>route.continue({url:BASE+"/sounds/archive.html"}));
 const errors=[];page.on("pageerror",e=>errors.push(String(e)));
 for(let i=0;i<3;i++){
  await page.goto(BASE+"/sounds/"+slugs[i]+"/",{waitUntil:"domcontentloaded"});
  assert.equal(await page.locator('meta[name="robots"]').getAttribute("content"),"noindex,follow");
  await page.waitForFunction(id=>!!window.WNCBridge&&!!document.querySelector('button[data-wnc-play="'+id+'"]'),ids[i],{timeout:30000});
  for(const width of [320,390]){
   await page.setViewportSize({width,height:780});
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
   assert.ok(overflow<=1,slugs[i]+" overflow at "+width+": "+overflow);
  }
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),false,"no autoplay on sound page "+slugs[i]);
  await page.locator('button[data-wnc-play="'+ids[i]+'"]').click();
  await page.waitForFunction(id=>{const s=window.WNCBridge?.snapshot();return s?.playing&&s.activeIds[0]===id},ids[i],{timeout:25000});
  const source=await page.evaluate(id=>{const el=document.querySelector('audio[data-sound="'+id+'"]');return {mp3:el.dataset.mp3,hls:el.dataset.hls}},ids[i]);
  assert.ok(source.mp3.includes("/audio/"+ids[i]+".mp3"));
  assert.ok(source.hls.includes("/audio/continuous/"+ids[i]+"/continuous.m3u8"));
  await page.locator('select[data-wnc-page-timer]').selectOption("900");
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().timer),"900");
 }
 await page.goto(BASE+"/sounds/",{waitUntil:"domcontentloaded"});
 await page.waitForFunction(()=>document.querySelectorAll('#wnc-catalog-grid [data-wnc-existing-id]').length===35,null,{timeout:25000});
 await page.locator('#wnc-library-search').fill("tin roof");
 assert.equal(await page.locator('#wnc-catalog-grid .wnc-sound-card:visible').count(),1);
 assert.equal(errors.length,0,"Browser errors: "+errors.join(" | "));
 console.log("RAIN_PRODUCTION_BROWSER_PASS 3 noindex Sound Pages, native HLS/MP3 attrs, persistent playback, timer, mobile 320/390, library filter");
}finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
