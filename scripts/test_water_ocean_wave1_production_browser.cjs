#!/usr/bin/env node
"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),{chromium}=require("playwright");
(async()=>{
 const path=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(fs.existsSync);
 const browser=await chromium.launch({headless:true,executablePath:path,args:["--no-sandbox"]});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844}}),errors=[];
  page.on("pageerror",e=>errors.push(String(e)));
  const tracks=[["rushing-river","rushing-river-real"],["forest-stream","forest-stream-real"],["gentle-ocean-waves","gentle-ocean-real"]];
  for(const [slug,id] of tracks){
   await page.goto("http://127.0.0.1:8787/sounds/"+slug+"/",{waitUntil:"domcontentloaded"});
   assert.equal(await page.locator('meta[name="robots"]').getAttribute("content"),"noindex,follow");
   assert.equal(await page.locator('audio[data-sound="'+id+'"]').count(),1,"Missing real player for "+slug);
   const player=await page.locator('audio[data-sound="'+id+'"]').evaluate(a=>({paused:a.paused,loop:a.loop,auto:a.autoplay,hls:a.dataset.hls,mp3:a.dataset.mp3}));
   assert.equal(player.paused,true);assert.equal(player.loop,true);assert.equal(player.auto,false);
   assert.ok(player.hls.includes("/audio/continuous/"+id+"/continuous.m3u8"));
   assert.ok(player.mp3.includes("/audio/"+id+".mp3"));
   for(const width of [320,390]){
    await page.setViewportSize({width,height:760});
    let overflow=await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth);
    assert.ok(overflow<=1,"Mobile overflow "+slug+" at "+width+": "+overflow);
   }
  }
  await page.goto("http://127.0.0.1:8787/sounds/",{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>document.querySelectorAll('#wnc-catalog-grid [data-wnc-existing-id]').length===33,{timeout:20000});
  for(const [slug,id] of tracks)assert.equal(await page.locator('[data-wnc-existing-id="'+id+'"]').count(),1,"Catalog excludes "+id);
  await page.goto("http://127.0.0.1:8787/sounds/water/",{waitUntil:"domcontentloaded"});
  for(const [slug] of tracks)assert.equal(await page.locator('a[href="/sounds/'+slug+'/"]').count(),1);
  assert.deepEqual(errors,[],"Browser JS errors");
  console.log("WATER_OCEAN_WAVE1_BROWSER_QA_PASS 33 catalog source cards, 3 noindex player pages, native HLS/MP3, no autoplay and 320/390 responsive");
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
