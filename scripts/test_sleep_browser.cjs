#!/usr/bin/env node
"use strict";
const {chromium}=require("playwright"),fs=require("node:fs"),assert=require("node:assert/strict");
const BASE="http://127.0.0.1:8787";
(async()=>{
 const path=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(p=>fs.existsSync(p));
 const browser=await chromium.launch({headless:true,executablePath:path,args:["--no-sandbox","--autoplay-policy=no-user-gesture-required"]});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:"reduce"});
  const errors=[];page.on("pageerror",e=>errors.push(String(e)));
  await page.goto(BASE+"/collections/white-noise-for-sleep/",{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>!!window.WNCBridge && !!document.querySelector('button[data-wnc-play="white-noise"]'),null,{timeout:30000});
  assert.match(await page.title(),/White Noise for Sleep — Listen to 6/);
  assert.equal(await page.locator('audio[data-sound="white-noise"]').getAttribute("controls"),null,"Bridge hides native fallback once active");
  assert.equal(await page.locator("main [data-wnc-compare]").count(),6,"Six instant sound choices");
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),false,"No autoplay; the default White Noise chip may be selected but not playing");
  assert.equal(await page.locator("main .sleep-faq details").count(),4,"Four bedtime FAQs");
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,"No 390px mobile overflow");
  await page.locator('button[data-wnc-play="white-noise"]').click();
  await page.waitForFunction(()=>window.WNCBridge?.snapshot().playing && window.WNCBridge.snapshot().activeIds[0]==="white-noise",null,{timeout:20000});
  await page.locator('select[data-wnc-page-timer]').selectOption("900");
  const deadline=await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt);
  const chosen=page.locator('main a[data-wnc-compare="brown-noise"]');
  await chosen.click();
  await page.waitForFunction(()=>window.WNCBridge?.snapshot().playing && window.WNCBridge.snapshot().activeIds[0]==="brown-noise",null,{timeout:22000});
  assert.equal(page.url().split("?")[0],BASE+"/collections/white-noise-for-sleep/","A/B keeps bedtime collection URL");
  assert.equal(await chosen.getAttribute("aria-current"),"true","Accessibility active source selected");
  assert.ok(Math.abs((await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt))-deadline)<1500,"Timer deadline does not reset when switching colors");
  await page.locator('main a[data-wnc-compare="soft-white-noise"]').click();
  await page.waitForFunction(()=>window.WNCBridge?.snapshot().playing && window.WNCBridge.snapshot().activeIds[0]==="soft-white-noise",null,{timeout:22000});
  assert.ok(Math.abs((await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt))-deadline)<1500,"Sleep timer retained when switching synthesized variants");
  await page.locator('main a.sleep-details[href="/sounds/soft-white-noise/"]').click();
  await page.waitForURL(BASE+"/sounds/soft-white-noise/",{timeout:20000});
  assert.deepEqual(await page.evaluate(()=>window.WNCBridge.snapshot().activeIds),["soft-white-noise"]);
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),true,"Music stays on during page navigation");
  await page.goBack({waitUntil:"domcontentloaded"});
  await page.waitForURL(BASE+"/collections/white-noise-for-sleep/",{timeout:20000});
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),true,"Audio survives browser history");
  await page.setViewportSize({width:320,height:740});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,"Small 320px screen does not overflow");
  assert.equal(errors.length,0,"Browser JS errors: "+errors.join("; "));
  const noJs=await browser.newContext({viewport:{width:360,height:740},javaScriptEnabled:false});
  try{
   const fallback=await noJs.newPage();
   await fallback.goto(BASE+"/collections/white-noise-for-sleep/",{waitUntil:"domcontentloaded"});
   assert.equal(await fallback.locator('audio[data-sound="white-noise"]').getAttribute("controls"),"","Native MP3 control stays available with JS off");
   assert.equal(await fallback.locator('main a.sleep-details').count(),6,"All sound detail links available without JS");
   assert.equal(await fallback.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,"Fallback layout fits small devices");
   await fallback.close();
  }finally{await noJs.close()}
  console.log("ADULT_SLEEP_BROWSER_PASS: six choices, no autoplay, 15min timer retained through A/B, SPA playback, 320/390px and non-JS MP3 fallback");
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
