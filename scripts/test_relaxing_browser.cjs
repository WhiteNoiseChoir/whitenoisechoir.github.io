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
  await page.goto(BASE+"/collections/relaxing-sounds/",{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>!!window.WNCBridge&&!!document.querySelector('button[data-wnc-play="rain-on-window-real"]'),null,{timeout:30000});
  assert.match(await page.title(),/Relaxing Sounds: Rain, Ocean/);
  assert.equal(await page.locator('audio[data-sound="rain-on-window-real"]').getAttribute("controls"),null,"Progressive player enhanced");
  assert.equal(await page.locator('main [data-wnc-compare]').count(),8,"Eight instant sound choices");
  assert.equal(await page.locator('main [data-wnc-compare][aria-current="true"]').count(),0,"No sound is auto-selected");
  assert.ok(await page.locator('main .relax-faq details').count()===4,"Four accessible FAQs");
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,"390px page fits without horizontal overflow");
  const source=page.locator('button[data-wnc-play="rain-on-window-real"]');
  await source.click();
  await page.waitForFunction(()=>window.WNCBridge?.snapshot().playing&&window.WNCBridge.snapshot().activeIds[0]==="rain-on-window-real",null,{timeout:20000});
  await page.locator('select[data-wnc-page-timer]').selectOption("900");
  const deadline=await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt);
  const next=page.locator('main a[data-wnc-compare="ocean-waves-real"]');
  await next.click();
  await page.waitForFunction(()=>window.WNCBridge?.snapshot().playing&&window.WNCBridge.snapshot().activeIds[0]==="ocean-waves-real",null,{timeout:22000});
  assert.equal(page.url().split("?")[0],BASE+"/collections/relaxing-sounds/","Sound comparison remains in place");
  assert.equal(await next.getAttribute("aria-current"),"true","Selected sound marked for assistive technology");
  assert.ok(Math.abs((await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt))-deadline)<1500,"Sleep Timer preserves deadline through sound comparison");
  await page.locator('main .relax-water .relax-details[href="/sounds/ocean-waves/"]').first().click();
  await page.waitForURL(BASE+"/sounds/ocean-waves/",{timeout:20000});
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),true,"Persistent audio survives sound details navigation");
  assert.deepEqual((await page.evaluate(()=>window.WNCBridge.snapshot().activeIds)),["ocean-waves-real"]);
  await page.goBack({waitUntil:"domcontentloaded"});
  await page.waitForURL(BASE+"/collections/relaxing-sounds/",{timeout:20000});
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),true,"Audio stays active on return");
  await page.locator('main .relax-next-grid a[href="/collections/white-noise-for-sleep/"]').click();
  await page.waitForURL(BASE+"/collections/white-noise-for-sleep/",{timeout:20000});
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),true,"Audio persists across collection navigation");
  await page.goto(BASE+"/collections/relaxing-sounds/",{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>!!window.WNCBridge,null,{timeout:30000});
  await page.setViewportSize({width:320,height:740});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,"Small iPhone screen must not overflow at 320px");
  assert.equal(errors.length,0,"JavaScript errors: "+errors.join("; "));
  await page.close();
  console.log("RELAXING_MOBILE_BROWSER_PASS: 8 sources, no autoplay, A/B switch, 15-min deadline stable, SPA navigation continuity, 320/390px");
 }finally{await browser.close()}
})().catch(err=>{console.error(err);process.exit(1)});
