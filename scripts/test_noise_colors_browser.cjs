#!/usr/bin/env node
"use strict";
const {chromium}=require("playwright"),fs=require("node:fs"),assert=require("node:assert/strict");
const BASE="http://127.0.0.1:8787";
const cases=[
 {slug:"blue-noise",id:"blue-noise",peer:"violet-noise",peerSlug:"violet-noise"},
 {slug:"violet-noise",id:"violet-noise",peer:"blue-noise",peerSlug:"blue-noise"},
 {slug:"soft-white-noise",id:"soft-white-noise",peer:"white-noise",peerSlug:"white-noise"},
 {slug:"deep-brown-noise",id:"deep-brown-noise",peer:"brown-noise",peerSlug:"brown-noise"},
 {slug:"warm-pink-noise",id:"warm-pink-noise",peer:"pink-noise",peerSlug:"pink-noise"},
 {slug:"neutral-mid-noise",id:"mid-noise",peer:"blue-noise",peerSlug:"blue-noise"}
];
(async()=>{
 const executablePath=["/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].find(x=>fs.existsSync(x));
 const browser=await chromium.launch({headless:true,executablePath,args:["--no-sandbox","--autoplay-policy=no-user-gesture-required"]});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},reducedMotion:"reduce"});
  const errors=[];page.on("pageerror",e=>errors.push(String(e)));
  for(const c of cases){
   await page.goto(BASE+"/sounds/"+c.slug+"/",{waitUntil:"domcontentloaded"});
   await page.waitForFunction(id=>!!window.WNCBridge&&!!document.querySelector('button[data-wnc-play="'+id+'"]'),c.id,{timeout:30000});
   assert.equal(await page.locator("main .noise-band-row").count(),5,c.slug+" measured band visual");
   assert.equal(await page.locator("main details.brown-faq").count(),5,c.slug+" five FAQs");
   assert.equal(await page.locator('audio[data-sound="'+c.id+'"]').getAttribute("controls"),null,c.slug+" audio enhanced");
   assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),false,c.slug+" no autoplay");
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,c.slug+" 390px fits");
   await page.setViewportSize({width:320,height:740});
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,c.slug+" 320px fits");
   await page.setViewportSize({width:390,height:844});
   if(c.id==="mid-noise"){
    assert.equal(await page.locator('main [data-wnc-compare="green-noise"]').count(),0,"Do not play unapproved Green");
   }
   if(c.id!=="blue-noise"&&c.id!=="violet-noise")continue;
   await page.locator('button[data-wnc-play="'+c.id+'"]').click();
   await page.waitForFunction(id=>window.WNCBridge?.snapshot().playing&&window.WNCBridge.snapshot().activeIds[0]===id,c.id,{timeout:20000});
   await page.locator("select[data-wnc-page-timer]").selectOption("900");
   const deadline=await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt);
   const link=page.locator('main a[data-wnc-compare="'+c.peer+'"]');
   await link.click();
   await page.waitForFunction(id=>window.WNCBridge?.snapshot().playing&&window.WNCBridge.snapshot().activeIds[0]===id,c.peer,{timeout:20000});
   assert.equal(page.url().split("?")[0],BASE+"/sounds/"+c.slug+"/",c.slug+" A/B stays in place");
   assert.equal(await link.getAttribute("aria-current"),"true",c.slug+" active A/B is accessible");
   assert.ok(Math.abs((await page.evaluate(()=>window.WNCBridge.snapshot().expiresAt))-deadline)<1500,c.slug+" timer preserved");
   await page.locator('main .batch18-compare p.muted a[href="/sounds/'+c.peerSlug+'/"]').first().click();
   await page.waitForURL(BASE+"/sounds/"+c.peerSlug+"/",{timeout:20000});
   assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),true,c.slug+" navigation preserves playback");
   assert.deepEqual(await page.evaluate(()=>window.WNCBridge.snapshot().activeIds),[c.peer],c.slug+" navigation source preserved");
   await page.goBack({waitUntil:"domcontentloaded"});
   await page.waitForURL(BASE+"/sounds/"+c.slug+"/",{timeout:20000});
   assert.equal(await page.evaluate(()=>window.WNCBridge.snapshot().playing),true,c.slug+" back navigation preserves playback");
  }
  assert.equal(errors.length,0,"Browser errors "+errors.join("; "));
  const nojs=await browser.newContext({javaScriptEnabled:false,viewport:{width:360,height:740}});
  try{
   const fallback=await nojs.newPage();
   await fallback.goto(BASE+"/sounds/blue-noise/",{waitUntil:"domcontentloaded"});
   assert.equal(await fallback.locator('audio[data-sound="blue-noise"]').getAttribute("controls"),"","Native MP3 available without JS");
   assert.equal(await fallback.locator("main .noise-band-row").count(),5,"Static spectrum accessible without JS");
   assert.equal(await fallback.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),true,"No-JS 360px responsive");
  }finally{await nojs.close()}
  console.log("NOISE_COLORS_BROWSER_PASS: six charts and FAQs, 320/390px, A/B and timer, SPA navigation, native MP3 fallback");
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
