#!/usr/bin/env node
"use strict";
const {chromium}=require("playwright"),fs=require("node:fs"),assert=require("node:assert/strict");
const BASE="http://127.0.0.1:8787";
const cases=[
 {slug:"heavy-rain",id:"heavy-rain-real",other:"rain-on-window-real",next:"rain-on-window"},
 {slug:"waterfall",id:"waterfall-real",other:"ocean-waves-real",next:"ocean-waves"},
 {slug:"ocean-waves",id:"ocean-waves-real",other:"waterfall-real",next:"waterfall"},
 {slug:"box-fan",id:"box-fan-real",other:"desk-fan-synth",next:"desk-fan"}
];
(async()=>{
 const executablePath=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(p=>fs.existsSync(p));
 const browser=await chromium.launch({headless:true,executablePath,args:["--no-sandbox","--autoplay-policy=no-user-gesture-required"]});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:"reduce"});
  const errors=[];page.on("pageerror",x=>errors.push(String(x)));
  for(const c of cases){
   await page.goto(BASE+"/sounds/"+c.slug+"/",{waitUntil:"domcontentloaded"});
   await page.waitForFunction(id=>!!window.WNCBridge&&!!document.querySelector('button[data-wnc-play="'+id+'"]'),c.id,{timeout:30000});
   assert.equal(await page.locator("main .field-choice").count(),4,c.slug+" has 4 A/B choices");
   assert.equal(await page.locator('main details.field-faq').count(),4,c.slug+" has 4 FAQ details");
   assert.equal(await page.locator('audio[data-sound="'+c.id+'"]').getAttribute("controls"),null,"Enhanced player controls active");
   assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),false,c.slug+" no autoplay");
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,c.slug+" 390px viewport");
   await page.locator('button[data-wnc-play="'+c.id+'"]').click();
   await page.waitForFunction(id=>window.WNCBridge?.snapshot().playing&&window.WNCBridge.snapshot().activeIds[0]===id,c.id,{timeout:22000});
   await page.locator('select[data-wnc-page-timer]').selectOption("900");
   const deadline=await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt);
   const other=page.locator('main a.field-choice[data-wnc-compare="'+c.other+'"]');
   await other.click();
   await page.waitForFunction(id=>window.WNCBridge?.snapshot().playing&&window.WNCBridge.snapshot().activeIds[0]===id,c.other,{timeout:22000});
   assert.equal(page.url().split("?")[0],BASE+"/sounds/"+c.slug+"/",c.slug+" A/B stays on source page");
   assert.equal(await other.getAttribute("aria-current"),"true",c.slug+" selected source marked accessible");
   assert.ok(Math.abs((await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt))-deadline)<1500,c.slug+" timer deadline preserved");
   await page.locator('main a.field-detail-links a[href="/sounds/'+c.next+'/"]').first().click();
   await page.waitForURL(BASE+"/sounds/"+c.next+"/",{timeout:20000});
   assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),true,c.slug+" audio persists on link navigation");
   assert.deepEqual(await page.evaluate(()=>window.WNCBridge.snapshot().activeIds),[c.other],c.slug+" current audio preserved across page");
   await page.goBack({waitUntil:"domcontentloaded"});
   await page.waitForURL(BASE+"/sounds/"+c.slug+"/",{timeout:20000});
   assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),true,c.slug+" history retains playback");
   await page.setViewportSize({width:320,height:740});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,c.slug+" no overflow at 320px");
   await page.setViewportSize({width:390,height:844});
  }
  assert.equal(errors.length,0,"Browser page errors: "+errors.join("; "));
  const nj=await browser.newContext({javaScriptEnabled:false,viewport:{width:360,height:740}});
  try{
   const fallback=await nj.newPage();
   await fallback.goto(BASE+"/sounds/heavy-rain/",{waitUntil:"domcontentloaded"});
   assert.equal(await fallback.locator('audio[data-sound="heavy-rain-real"]').getAttribute("controls"),"","Native MP3 controls when JS off");
   assert.equal(await fallback.locator("main a.field-choice").count(),4,"A/B choices have crawlable destinations without JS");
   assert.equal(await fallback.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,"No-JS 360px viewport");
   await fallback.close();
  }finally{await nj.close()}
  console.log("FIELD_SOUND_BROWSER_PASS: 4 field sources, owner-approved HLS/MP3, A/B, 15-min timer retained, SPA navigation, 320/390px, native no-JS fallback");
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
