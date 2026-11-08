#!/usr/bin/env node
"use strict";
const {chromium}=require("playwright"),fs=require("node:fs"),assert=require("node:assert/strict");
const BASE="http://127.0.0.1:8787";
(async()=>{
 const bin=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(p=>fs.existsSync(p));
 const browser=await chromium.launch({headless:true,executablePath:bin,args:["--no-sandbox","--autoplay-policy=no-user-gesture-required"]});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:"reduce"});
  const errs=[];page.on("pageerror",e=>errs.push(String(e)));
  await page.goto(BASE+"/collections/baby-sleep-sounds/",{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>window.WNCBridge && !!document.querySelector('button[data-wnc-play="soft-white-noise"]'),null,{timeout:30000});
  assert.match(await page.title(),/Baby Sleep Sounds — Gentle Background Audio/);
  assert.equal(await page.locator('audio[data-sound="soft-white-noise"]').getAttribute("controls"),null,"Enhanced page hides redundant native controls");
  assert.equal(await page.locator('main a[data-wnc-compare]').count(),3,"Three infant audio options");
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),false,"No baby audio starts automatically");
  assert.equal(await page.locator('main .baby-safety-list li').count(),3,"Safety before audio");
  assert.equal(await page.locator('main .baby-faq details').count(),5,"Five infant caregiver FAQs");
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,"No mobile overflow at 390px");
  await page.locator('button[data-wnc-play="soft-white-noise"]').click();
  await page.waitForFunction(()=>window.WNCBridge?.snapshot().playing&&window.WNCBridge.snapshot().activeIds[0]==="soft-white-noise",null,{timeout:20000});
  await page.locator('select[data-wnc-page-timer]').selectOption("900");
  const deadline=await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt);
  await page.locator('main a.baby-compare[data-wnc-compare="pink-noise"]').click();
  await page.waitForFunction(()=>window.WNCBridge?.snapshot().playing&&window.WNCBridge.snapshot().activeIds[0]==="pink-noise",null,{timeout:20000});
  assert.equal(page.url().split("?")[0],BASE+"/collections/baby-sleep-sounds/","Audio selection does not navigate away");
  assert.equal(await page.locator('main a.baby-compare[data-wnc-compare="pink-noise"]').getAttribute("aria-current"),"true","Current sound accessible");
  assert.ok(Math.abs((await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt))-deadline)<1500,"Timer retains deadline after sound switch");
  await page.locator('main a.baby-compare[data-wnc-compare="rain-on-window-real"]').click();
  await page.waitForFunction(()=>window.WNCBridge?.snapshot().playing&&window.WNCBridge.snapshot().activeIds[0]==="rain-on-window-real",null,{timeout:20000});
  assert.ok(Math.abs((await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt))-deadline)<1500,"Timer retained when switching from DSP to CC0 recording");
  await page.locator('main a.baby-sound-details[href="/sounds/rain-on-window/"]').click();
  await page.waitForURL(BASE+"/sounds/rain-on-window/",{timeout:20000});
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),true,"Audio remains active during detail navigation");
  assert.deepEqual(await page.evaluate(()=>window.WNCBridge.snapshot().activeIds),["rain-on-window-real"]);
  await page.goBack({waitUntil:"domcontentloaded"});
  await page.waitForURL(BASE+"/collections/baby-sleep-sounds/",{timeout:20000});
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),true,"Audio persists through history navigation");
  await page.setViewportSize({width:320,height:740});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,"No 320px mobile overflow");
  assert.equal(errs.length,0,"JavaScript page errors: "+errs.join("; "));
  const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:360,height:740}});
  try{
   const fallback=await nojs.newPage();
   await fallback.goto(BASE+"/collections/baby-sleep-sounds/",{waitUntil:"domcontentloaded"});
   assert.equal(await fallback.locator('audio[data-sound="soft-white-noise"]').getAttribute("controls"),"","Progressive MP3 audio works without JavaScript");
   assert.equal(await fallback.locator('a.baby-sound-details').count(),3,"Detail links available without JS");
   assert.equal(await fallback.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,"No JS-disabled page overflow");
  }finally{await nojs.close()}
  console.log("BABY_MOBILE_BROWSER_PASS: no autoplay, pediatric cautions, three A/B sounds, timer preserved, SPA navigation, responsive layout and no-JS fallback");
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
