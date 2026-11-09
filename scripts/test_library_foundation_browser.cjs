#!/usr/bin/env node
"use strict";
/* Foundation UI on desktop mobile widths, source search and persistent playback. */
const {chromium}=require("playwright"),fs=require("node:fs"),assert=require("node:assert/strict");
const BASE="http://127.0.0.1:8787";
(async()=>{
 const executablePath=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(x=>fs.existsSync(x));
 const browser=await chromium.launch({headless:true,executablePath,args:["--no-sandbox","--autoplay-policy=no-user-gesture-required"]});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:"reduce"});
  const errors=[];page.on("pageerror",e=>errors.push(String(e)));
  await page.goto(BASE+"/sounds/",{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>!!window.WNCBridge&&!!document.querySelector("#wnc-library-search"),null,{timeout:30000});
  assert.equal(await page.locator("#wnc-family-grid > a").count(),13,"13 family navigation cards");
  assert.equal(await page.locator("#wnc-catalog-grid > .wnc-sound-card").count(),33,"28 real catalog sources only");
  assert.equal(await page.locator(".wnc-roadmap-family").count(),13,"13 planned family detail sections");
  assert.equal(await page.locator("main [data-wnc-play^='NEW-']").count(),0,"planned IDs never playable");
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),false,"no autoplay");
  for(const width of [320,390]){
   await page.setViewportSize({width,height:760});
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
   assert.ok(overflow<=1,width+"px has no horizontal scroll: "+overflow);
  }
  await page.locator("#wnc-library-search").fill("waterfall");
  assert.equal(await page.locator("#wnc-catalog-grid .wnc-sound-card:visible").count(),1,"search only current audio sources");
  await page.locator("#wnc-library-search").fill("");
  assert.equal(await page.locator("#wnc-catalog-grid .wnc-sound-card:visible").count(),33,"search restores all 28");
  await page.locator('a[data-wnc-family="ocean"]').click();
  await page.waitForFunction(()=>location.hash==="#ocean-waves",{timeout:10000});
  assert.equal(await page.locator("#ocean-waves[open]").count(),1,"virtual family lands in its details section");
  assert.ok(await page.locator('#ocean-waves a[href="/sounds/ocean-waves/"]').count()===1,"real Ocean Sound Page preserved");
  await page.locator('a[href="/sounds/white-noise/"][data-wnc-existing-id="white-noise"]').click();
  await page.waitForURL(BASE+"/sounds/white-noise/",{timeout:20000});
  await page.waitForFunction(()=>!!document.querySelector('button[data-wnc-play="white-noise"]'),null,{timeout:20000});
  await page.locator('button[data-wnc-play="white-noise"]').click();
  await page.waitForFunction(()=>window.WNCBridge?.snapshot().playing&&window.WNCBridge.snapshot().activeIds[0]==="white-noise",null,{timeout:20000});
  await page.locator('select[data-wnc-page-timer]').selectOption("900");
  const deadline=await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt);
  await page.locator('main .crumb a[href="/sounds/"]').first().click();
  await page.waitForURL(BASE+"/sounds/",{timeout:20000});
  await page.waitForFunction(()=>document.querySelectorAll("#wnc-family-grid > a").length===13,null,{timeout:15000});
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().activeIds[0]),"white-noise","same master after foundation navigation");
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),true,"playing persists when browsing 13 families");
  assert.ok(Math.abs((await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt))-deadline)<2000,"sleep timer deadline preserved");
  assert.equal(errors.length,0,"no browser runtime errors: "+errors.join("; "));
  console.log("FOUNDATION_BROWSER_PASS "+JSON.stringify({families:13,liveSources:33,mobileWidths:[320,390],oceanVirtualNavigation:true,search:true,persistentPlayback:true,timer:true}));
 }finally{await browser.close()}
})().catch(err=>{console.error(err);process.exit(1)});
