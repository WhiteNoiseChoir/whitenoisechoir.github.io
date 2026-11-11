#!/usr/bin/env node
"use strict";
const {chromium}=require("playwright"),fs=require("node:fs"),assert=require("node:assert/strict");
const ROOT="http://127.0.0.1:8787";
const batch=JSON.parse(fs.readFileSync("catalog/batch18-20261108.json","utf8"));
const catalog=JSON.parse(fs.readFileSync("catalog/library.json","utf8"));
const byId=Object.fromEntries(catalog.sounds.map(s=>[s.id,s]));
(async()=>{
 const exec=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(p=>fs.existsSync(p));
 const browser=await chromium.launch({headless:true,executablePath:exec,args:["--no-sandbox","--autoplay-policy=no-user-gesture-required"]});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:"reduce"});
  // This historical playback test uses the archived sound listing.
  await page.route(ROOT+"/sounds/",route=>route.continue({url:ROOT+"/sounds/archive.html"}));
  const errors=[];page.on("pageerror",e=>errors.push(String(e)));
  for(const id of batch.editorially_upgraded){
    const s=byId[id],url=ROOT+"/sounds/"+s.slug+"/";
    await page.goto(url,{waitUntil:"domcontentloaded",timeout:30000});
    assert.equal(await page.locator('audio[data-sound]').getAttribute("data-sound"),id,"correct audio source in deep link: "+id);
    const canonical=await page.locator('link[rel="canonical"]').getAttribute("href");
    assert.equal(canonical,"https://whitenoisechoir.com/sounds/"+s.slug+"/");
    await page.waitForFunction(()=>window.WNCBridge&&document.querySelector("button[data-wnc-play]"),null,{timeout:25000});
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth);
    assert.ok(overflow<=1,"no horizontal overflow for "+id+": "+overflow);
    assert.equal(await page.locator('button[data-wnc-play="'+id+'"]').count(),1,"real player control "+id);
    assert.ok((await page.locator('main .batch18-choice').count())>=3,"interactive comparisons "+id);
    if(["desk-fan","air-conditioner","airplane-cabin","low-rumble","gentle-wind","shower"].includes(s.slug)){
      assert.equal(await page.locator("main .noise-band-row").count(),5,s.slug+" measured spectrum");
      assert.equal(await page.locator("main details.brown-faq").count(),5,s.slug+" topic FAQs");
      await page.setViewportSize({width:320,height:740});
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),s.slug+" mobile 320px no overflow");
      await page.setViewportSize({width:390,height:844});
    }
  }
  await page.goto(ROOT+"/sounds/blue-noise/",{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>window.WNCBridge&&document.querySelector('button[data-wnc-play="blue-noise"]'));
  await page.locator('button[data-wnc-play="blue-noise"]').click();
  await page.waitForFunction(()=>window.WNCBridge.snapshot().playing&&window.WNCBridge.snapshot().activeIds[0]==="blue-noise",{timeout:20000});
  await page.locator('select[data-wnc-page-timer]').selectOption("900");
  const deadline=await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt);
  await page.locator('a[data-wnc-compare="violet-noise"]').click();
  await page.waitForFunction(()=>window.WNCBridge.snapshot().playing&&window.WNCBridge.snapshot().activeIds[0]==="violet-noise",null,{timeout:20000});
  assert.equal(page.url().split("?")[0],ROOT+"/sounds/blue-noise/","A/B stays on same URL");
  assert.ok(Math.abs((await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt))-deadline)<1500,"timer is not extended by A/B");
  assert.equal(await page.locator('a[data-wnc-compare="violet-noise"]').getAttribute("aria-current"),"true");
  await page.locator('main .crumb a[href="/sounds/"]').click();
  await page.waitForURL(ROOT+"/sounds/",{timeout:20000});
  assert.equal((await page.evaluate(()=>window.WNCBridge.snapshot().playing)),true,"playing persists after moving to library");
  assert.equal((await page.evaluate(()=>window.WNCBridge.snapshot().activeIds[0])),"violet-noise","same master source stays active");
  // New release: one-player Shower -> real Waterfall comparison and timer preservation.
  await page.goto(ROOT+"/sounds/shower/",{waitUntil:"domcontentloaded"});
  await page.waitForFunction(()=>window.WNCBridge&&document.querySelector('button[data-wnc-play="shower-synth"]'));
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),false,"No autoplay on Shower");
  await page.locator('button[data-wnc-play="shower-synth"]').click();
  await page.waitForFunction(()=>window.WNCBridge.snapshot().playing&&window.WNCBridge.snapshot().activeIds[0]==="shower-synth",{timeout:20000});
  await page.locator('select[data-wnc-page-timer]').selectOption("900");
  const showerDeadline=await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt);
  await page.locator('a[data-wnc-compare="waterfall-real"]').click();
  await page.waitForFunction(()=>window.WNCBridge.snapshot().playing&&window.WNCBridge.snapshot().activeIds[0]==="waterfall-real",{timeout:20000});
  assert.equal(page.url().split("?")[0],ROOT+"/sounds/shower/","Shower A/B stays in-page");
  assert.ok(Math.abs((await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt))-showerDeadline)<1500,"Shower A/B must preserve timer");
  await page.locator('main .crumb a[href="/sounds/"]').click();
  await page.waitForURL(ROOT+"/sounds/",{timeout:20000});
  assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().activeIds[0]),"waterfall-real","Shower A/B persists after navigation");
  assert.equal(errors.length,0,"no console errors: "+errors.join("; "));
  console.log("PASS: 14 source IDs, 6 measured device/environment charts at 320/390px, Shower->Waterfall and Blue->Violet A/B, timer and navigation persistence");
 }finally{await browser.close()}
})().catch(err=>{console.error(err);process.exit(1)});
