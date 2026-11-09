#!/usr/bin/env node
"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),{chromium}=require("playwright");
(async()=>{
 const path=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(fs.existsSync);
 const b=await chromium.launch({headless:true,executablePath:path,args:["--no-sandbox"]});
 try{
  const page=await b.newPage({viewport:{width:390,height:820}}),errors=[];page.on("pageerror",e=>errors.push(String(e)));
  const tracks=[["bodetal-brook-birds","bodetal-brook-real"],["crashing-ocean-waves","crashing-ocean-real"]];
  for(const [slug,id] of tracks){
   await page.goto("http://127.0.0.1:8787/sounds/"+slug+"/",{waitUntil:"domcontentloaded"});
   assert.equal(await page.locator('meta[name="robots"]').getAttribute("content"),"noindex,follow");
   assert.equal(await page.locator('audio[data-sound="'+id+'"]').count(),1);
   const a=await page.locator('audio[data-sound="'+id+'"]').evaluate(n=>({paused:n.paused,autoplay:n.autoplay,loop:n.loop,hls:n.dataset.hls,mp3:n.dataset.mp3}));
   assert.equal(a.paused,true);assert.equal(a.autoplay,false);assert.equal(a.loop,true);
   assert.ok(a.hls.includes("/audio/continuous/"+id+"/continuous.m3u8"));assert.ok(a.mp3.includes("/audio/"+id+".mp3"));
   for(const width of [320,390]){await page.setViewportSize({width,height:790});let overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);assert.ok(overflow<=1,"Horizontal overflow "+slug+": "+width+" "+overflow)}
  }
  await page.goto("http://127.0.0.1:8787/sounds/",{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>document.querySelectorAll('#wnc-catalog-grid [data-wnc-existing-id]').length===35,{timeout:24000});
  for(const [slug,id] of tracks)assert.equal(await page.locator('[data-wnc-existing-id="'+id+'"]').count(),1);
  await page.goto("http://127.0.0.1:8787/sounds/water/",{waitUntil:"domcontentloaded"});
  for(const [slug] of tracks)assert.equal(await page.locator('a[href="/sounds/'+slug+'/"]').count(),1);
  assert.deepEqual(errors,[]);
  console.log("WATER_OCEAN_WAVE2_PRODUCTION_BROWSER_PASS 2 new noindex genuine sound pages, 35 catalog items, native HLS+MP3 fallback, no autoplay, responsive 320/390");
 }finally{await b.close()}
})().catch(e=>{console.error(e);process.exit(1)});
